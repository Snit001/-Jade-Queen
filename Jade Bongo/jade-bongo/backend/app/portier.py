"""portier-service — Protocole d'Identification de Jade (la porte blindée).

Règles absolues implémentées :
1. AUCUNE donnée du profil n'est servie avant identification réussie.
2. Tirage aléatoire des questions, adaptées à l'âge et à la phase.
3. Vérification tolérante (variantes acceptées + validation parentale assistée).
4. Échecs répétés → verrouillage + notification immédiate aux parents.
5. Réponses hachées (PBKDF2) — jamais comparées en clair, jamais loguées.
6. Succès → jeton de session à scope minimal (durée = politique d'âge).
"""
from __future__ import annotations

import random
import sqlite3
from datetime import timedelta
from typing import Any

from .age import compute_age
from .audit import audit, notify
from .config import LOCK_MAX_FAILURES, LOCK_MINUTES
from .db import dumps, iso, loads, q_one, utcnow
from .security import PARENT_VALIDATION_TOKEN, new_token, verify_candidate
from . import wellbeing


class Locked(Exception):
    def __init__(self, locked_until: str | None):
        super().__init__("locked")
        self.locked_until = locked_until


class BadRequest(Exception):
    pass


def get_lock(con: sqlite3.Connection, child_id: str) -> tuple[int, str | None]:
    row = q_one(con, "SELECT failed_count, locked_until FROM locks WHERE child_id = ?", (child_id,))
    return (int(row["failed_count"]), row["locked_until"]) if row else (0, None)


def is_locked(con: sqlite3.Connection, child_id: str) -> tuple[bool, str | None, int]:
    _, locked_until = get_lock(con, child_id)
    if not locked_until:
        return False, None, 0
    remaining = int((datetime_parse(locked_until) - utcnow()).total_seconds())
    return (remaining > 0), locked_until, max(0, remaining)


def datetime_parse(ts: str):
    from datetime import datetime

    return datetime.fromisoformat(ts)


def unlock(con: sqlite3.Connection, child_id: str, actor: str = "parent") -> None:
    con.execute(
        "INSERT INTO locks (child_id, failed_count, locked_until) VALUES (?,0,NULL) "
        "ON CONFLICT(child_id) DO UPDATE SET failed_count = 0, locked_until = NULL",
        (child_id,),
    )
    audit(con, "identity.unlocked", child_id=child_id, actor=actor)


def _register_failure(con: sqlite3.Connection, child_id: str) -> tuple[bool, str | None]:
    failed, _ = get_lock(con, child_id)
    failed += 1
    locked_until: str | None = None
    if failed >= LOCK_MAX_FAILURES:
        locked_until = iso(utcnow() + timedelta(minutes=LOCK_MINUTES))
        notify(con, "identity.locked", {"child_id": child_id, "locked_until": locked_until, "minutes": LOCK_MINUTES})
        audit(con, "identity.locked", child_id=child_id, payload={"locked_until": locked_until})
    con.execute(
        "INSERT INTO locks (child_id, failed_count, locked_until) VALUES (?,?,?) "
        "ON CONFLICT(child_id) DO UPDATE SET failed_count = excluded.failed_count, "
        "locked_until = excluded.locked_until",
        (child_id, failed, locked_until),
    )
    return failed >= LOCK_MAX_FAILURES, locked_until


def create_challenge(con: sqlite3.Connection, child_id: str) -> dict[str, Any]:
    """Crée un challenge : tirage aléatoire de questions adaptées à l'âge exact de Jade."""
    locked, locked_until, remaining = is_locked(con, child_id)
    if locked:
        audit(con, "identity.challenge_refused_locked", child_id=child_id, payload={"remaining_seconds": remaining})
        raise Locked(locked_until)

    age = compute_age()
    k = age.policy["identification"]["questions_per_session"]
    allowed_modalities = set(age.policy["identification"]["modalities"])

    rows = [
        r for r in con.execute(
            "SELECT * FROM identity_questions WHERE child_id = ? AND active = 1 AND min_age_months <= ?",
            (child_id, age.total_months),
        ).fetchall()
        if r["modality"] in allowed_modalities
    ]
    if not rows:
        raise BadRequest("Aucune question active : un parent doit en configurer (Dashboard).")
    random.shuffle(rows)
    drawn = rows[: max(1, min(k, len(rows)))]

    challenge_id = new_token()[:16]
    qids = [r["id"] for r in drawn]
    con.execute(
        "INSERT INTO challenges (id, child_id, question_ids_json, results_json, status, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (challenge_id, child_id, dumps(qids), "{}", "open", iso()),
    )
    audit(con, "identity.challenge_created", child_id=child_id, payload={"challenge_id": challenge_id, "questions": len(qids)})

    public_questions = []
    for r in drawn:
        options = loads(r["options_json"])
        if options:
            options = random.sample(options, len(options))  # anti-mémorisation de position
        public_questions.append(
            {
                "id": r["id"],
                "modality": r["modality"],
                "prompt": loads(r["prompt_json"]),
                "options": options,
            }
        )
    return {
        "challenge_id": challenge_id,
        "age_years": age.years,
        "questions": public_questions,
        "requires_parent_present": age.policy["requires_parent_present"],
    }


def submit_answer(
    con: sqlite3.Connection,
    challenge_id: str,
    question_id: str,
    answer: str,
    *,
    parent_validated: bool = False,
) -> dict[str, Any]:
    """Soumet une réponse. Tolérante, jamais pénalisante — mais intraitable sur la sécurité."""
    ch = q_one(con, "SELECT * FROM challenges WHERE id = ?", (challenge_id,))
    if ch is None or ch["status"] != "open":
        raise BadRequest("Challenge inconnu ou déjà terminé.")
    child_id = ch["child_id"]

    locked, locked_until, remaining = is_locked(con, child_id)
    if locked:
        raise Locked(locked_until)

    qrow = q_one(con, "SELECT * FROM identity_questions WHERE id = ? AND child_id = ?", (question_id, child_id))
    if qrow is None:
        raise BadRequest("Question inconnue.")

    results: dict[str, str] = loads(ch["results_json"], {})
    qids: list[str] = loads(ch["question_ids_json"], [])
    if question_id not in qids:
        raise BadRequest("Cette question ne fait pas partie du challenge.")

    stored_hashes: list[str] = loads(qrow["answer_hashes_json"], [])
    correct = parent_validated or verify_candidate(answer, stored_hashes)
    actor = "parent" if (parent_validated or answer == PARENT_VALIDATION_TOKEN) else "child"

    if not correct:
        audit(con, "identity.answer_failed", child_id=child_id, actor="child", payload={"challenge_id": challenge_id})
        now_locked, until = _register_failure(con, child_id)
        con.execute("UPDATE challenges SET failures = failures + 1, status = ? WHERE id = ?",
                    ("locked" if now_locked else "open", challenge_id))
        return {
            "correct": False,
            "locked": now_locked,
            "locked_until": until,
            "remaining_attempts": None if now_locked else max(0, LOCK_MAX_FAILURES - get_lock(con, child_id)[0]),
        }

    # ✅ Bonne réponse : on note, jamais le contenu de la réponse (RGPD).
    results[question_id] = "ok"
    audit(con, "identity.answer_ok", child_id=child_id, actor=actor, payload={"challenge_id": challenge_id})
    done = all(qid in results for qid in qids)
    con.execute("UPDATE challenges SET results_json = ? WHERE id = ?", (dumps(results), challenge_id))

    if not done:
        return {"correct": True, "done": False, "progress": len(results), "total": len(qids)}

    # 🎉 Identification réussie → réinitialisation du compteur + session (sous conditions)
    con.execute("UPDATE challenges SET status = 'completed' WHERE id = ?", (challenge_id,))
    unlock(con, child_id, actor="system")
    audit(con, "identity.succeeded", child_id=child_id, actor=actor, payload={"challenge_id": challenge_id})

    age = compute_age()
    policy = wellbeing.effective_policy(con, child_id, age.policy)
    consent = q_one(con, "SELECT revoked_at FROM consents WHERE scope = 'education'")
    if consent is not None and consent["revoked_at"] is not None:
        return {"correct": True, "done": True, "session": None, "denied": {"reason": "consent_education"}}

    try:
        wellbeing.can_start_session(con, child_id, policy)
    except wellbeing.SessionDenied as exc:
        return {"correct": True, "done": True, "session": None, "denied": {"reason": exc.reason}}

    session = wellbeing.issue_session(con, child_id, policy)
    return {
        "correct": True,
        "done": True,
        "session": {"token": session["token"], "remaining_seconds": session["remaining_seconds"]},
        "denied": None,
    }
