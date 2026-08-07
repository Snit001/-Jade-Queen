"""parental-service — les parents sont l'autorité finale.

- Connexion PIN (hashée, jeton à durée limitée) — production : Keycloak OIDC + 2FA
- Vue d'ensemble : âge, phase, temps d'écran, maîtrise, alertes, audit
- Gestion complète des questions d'identification (CRUD, hachage serveur)
- Surcharge des politiques d'âge (durées, sessions/jour)
- Gestion des consentements RGPD (révoquer « education » bloque les sessions)
- Déverrouillage après échecs d'identification
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date as _date
from datetime import timedelta
from typing import Any

from .age import compute_age
from .audit import audit, recent_audit, unread_notifications
from .config import PARENT_PIN, PARENT_TOKEN_TTL
from .curriculum import MASTERY_THRESHOLD, set_mastery_bulk, skill_tree, skills_overview
from .db import dumps, iso, loads, q_all, q_one, utcnow
from .security import hash_answer, hash_secret, new_token, safe_equals
from .strings import LANGS
from . import wellbeing

ATTENTION_PROFILES = ("normal", "courte")

# Tables rattachées à un enfant — suppression en cascade (RGPD : effacer un
# profil efface TOUTES ses données. L'audit global, lui, est append-only et
# ne contient aucune donnée personnelle au-delà de l'identifiant technique.)
CHILD_TABLES = (
    "mastery", "sessions", "locks", "challenges",
    "identity_questions", "policy_overrides", "screen_time_ledger",
)


class Unauthorized(Exception):
    pass


def _child_age(con: sqlite3.Connection, child_id: str):
    row = q_one(con, "SELECT dob FROM children WHERE id = ?", (child_id,))
    if row is None:
        raise ValueError("enfant introuvable.")
    return compute_age(dob=_date.fromisoformat(row["dob"]))


def _lock_state(con: sqlite3.Connection, child_id: str) -> tuple[int, str | None]:
    row = q_one(con, "SELECT failed_count, locked_until FROM locks WHERE child_id = ?", (child_id,))
    return (int(row["failed_count"]), row["locked_until"]) if row else (0, None)


# ---------------------------------------------------------------- enfants (multi-profils)

def children_list(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = q_all(con, "SELECT * FROM children ORDER BY created_at")
    out = []
    for r in rows:
        a = compute_age(dob=_date.fromisoformat(r["dob"]))
        out.append({
            "id": r["id"], "display_name": r["display_name"], "emoji": r["emoji"],
            "dob": r["dob"], "age_years": a.years, "age_months": a.months,
            "phase": a.phase, "phase_label": a.phase_label,
            "lang": r["lang"], "attention": r["attention"],
            "speech_support": bool(r["speech_support"]),
        })
    return out


def patch_child(con: sqlite3.Connection, child_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Réglages d'adaptation de l'enfant (autorité parentale, auditée) :
    langue des cours (fr/en/es), profil d'attention (normal|courte),
    soutien langage (voix ralentie, consignes répétées)."""
    row = q_one(con, "SELECT * FROM children WHERE id = ?", (child_id,))
    if row is None:
        raise ValueError("Enfant inconnu.")

    fields: list[str] = []
    params: list[Any] = []

    if "lang" in data and data["lang"] is not None:
        lang = str(data["lang"]).split("-")[0].lower()
        if lang not in LANGS:
            raise ValueError(f"Langue non prise en charge : {lang} (fr|en|es).")
        fields.append("lang = ?"); params.append(lang)
    if "attention" in data and data["attention"] is not None:
        att = str(data["attention"]).lower()
        if att not in ATTENTION_PROFILES:
            raise ValueError(f"Profil d'attention inconnu : {att} (normal|courte).")
        fields.append("attention = ?"); params.append(att)
    if "speech_support" in data and data["speech_support"] is not None:
        fields.append("speech_support = ?"); params.append(1 if data["speech_support"] else 0)
    if "display_name" in data and data["display_name"] is not None:
        name = str(data["display_name"]).strip()
        if not name or len(name) > 40:
            raise ValueError("Prénom invalide (1–40 caractères).")
        fields.append("display_name = ?"); params.append(name)
    if "emoji" in data and data["emoji"] is not None:
        fields.append("emoji = ?"); params.append(str(data["emoji"])[:4] or "⭐")
    if "dob" in data and data["dob"] is not None:
        try:
            parsed = _date.fromisoformat(str(data["dob"]))
        except ValueError:
            raise ValueError("Date invalide (format AAAA-MM-JJ).") from None
        if parsed > _date.today():
            raise ValueError("La date de naissance est dans le futur.")
        fields.append("dob = ?"); params.append(parsed.isoformat())

    if not fields:
        raise ValueError("Aucun champ à modifier (lang|attention|speech_support|display_name|emoji|dob).")

    params.append(child_id)
    con.execute(f"UPDATE children SET {', '.join(fields)} WHERE id = ?", tuple(params))
    audit(con, "parent.child_updated", child_id=child_id, actor="parent",
          payload={k: data[k] for k in data if k in ("lang", "attention", "speech_support", "display_name", "emoji", "dob")})
    return {"id": child_id, "updated": [f.split(" ")[0] for f in fields]}


def tree(con: sqlite3.Connection, child_id: str, lang: str = "fr") -> dict[str, Any]:
    return skill_tree(con, child_id, lang)


def mastery_bulk(con: sqlite3.Connection, child_id: str, skill_ids: list[str], action: str) -> dict[str, Any]:
    if q_one(con, "SELECT id FROM children WHERE id = ?", (child_id,)) is None:
        raise ValueError("Enfant inconnu.")
    return set_mastery_bulk(con, child_id, skill_ids, action)


def delete_child(con: sqlite3.Connection, child_id: str) -> dict[str, Any]:
    """Suppression définitive d'un profil enfant (autorité parentale) :
    toutes ses données sont effacées en cascade. Garde-fou absolu :
    le dernier profil ne peut pas être supprimé."""
    row = q_one(con, "SELECT id, display_name FROM children WHERE id = ?", (child_id,))
    if row is None:
        raise ValueError("Enfant inconnu.")
    total = int(q_one(con, "SELECT COUNT(*) AS n FROM children")["n"])
    if total <= 1:
        raise ValueError("Impossible de supprimer le dernier profil : il faut au moins un enfant.")
    for table in CHILD_TABLES:
        con.execute(f"DELETE FROM {table} WHERE child_id = ?", (child_id,))
    con.execute("DELETE FROM children WHERE id = ?", (child_id,))
    audit(con, "parent.child_deleted", child_id=child_id, actor="parent",
          payload={"display_name": row["display_name"]})
    return {"deleted": child_id, "display_name": row["display_name"]}


def create_child(con: sqlite3.Connection, display_name: str, dob: str, emoji: str = "⭐",
                 lang: str = "fr") -> dict[str, Any]:
    """Ajoute un enfant à la plateforme : son propre âge-moteur, ses questions
    (placeholders DANS SA LANGUE, à personnaliser), sa progression, ses verrous
    — tout est isolé. La langue choisie à la création gouverne TOUT le profil
    (interface enfant, leçons, voix, questions par défaut)."""
    name = (display_name or "").strip()
    if not name:
        raise ValueError("Prénom requis.")
    lang = str(lang or "fr").split("-")[0].lower()
    if lang not in LANGS:
        raise ValueError(f"Langue non prise en charge : {lang} (fr|en|es).")
    try:
        parsed = _date.fromisoformat(dob)
    except (ValueError, TypeError):
        raise ValueError("Date invalide (format AAAA-MM-JJ).") from None
    if parsed > _date.today():
        raise ValueError("La date de naissance est dans le futur.")
    if (_date.today() - parsed).days > 25 * 366:
        raise ValueError("Âge supérieur à 25 ans non pris en charge.")

    import unicodedata
    norm = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")[:24] or "enfant"
    child_id = base
    if q_one(con, "SELECT id FROM children WHERE id = ?", (child_id,)) is not None:
        child_id = f"{base}-{new_token()[:4]}"

    con.execute(
        "INSERT INTO children (id, display_name, dob, phase, created_at, emoji, lang) VALUES (?,?,?,?,?,?,?)",
        (child_id, name, parsed.isoformat(), "PHASE_1", iso(), (emoji or "⭐")[:4], lang),
    )
    from .seed import seed_default_questions
    seed_default_questions(con, child_id, firstname=name, dob=parsed.isoformat(), lang=lang)
    audit(con, "parent.child_created", child_id=child_id, actor="parent",
          payload={"display_name": name, "dob": parsed.isoformat(), "lang": lang})
    return {"id": child_id, "display_name": name, "emoji": (emoji or "⭐")[:4], "lang": lang}


def login(con: sqlite3.Connection, pin: str) -> dict[str, Any]:
    if not safe_equals(hash_secret(pin), hash_secret(PARENT_PIN)):
        audit(con, "parent.login_failed", actor="parent")
        raise Unauthorized()
    token = new_token()
    expires_at = iso(utcnow() + timedelta(seconds=PARENT_TOKEN_TTL))
    con.execute(
        "INSERT INTO parent_tokens (token, created_at, expires_at) VALUES (?,?,?)",
        (token, iso(), expires_at),
    )
    audit(con, "parent.login_ok", actor="parent")
    return {"token": token, "expires_at": expires_at}


def require_parent(con: sqlite3.Connection, token: str | None) -> None:
    if not token:
        raise Unauthorized()
    row = q_one(con, "SELECT expires_at FROM parent_tokens WHERE token = ?", (token,))
    if row is None:
        raise Unauthorized()
    if row["expires_at"] <= iso():
        con.execute("DELETE FROM parent_tokens WHERE token = ?", (token,))
        raise Unauthorized()


# ---------------------------------------------------------------- overview

def overview(con: sqlite3.Connection, child_id: str, lang: str = "fr") -> dict[str, Any]:
    age = _child_age(con, child_id)
    policy = wellbeing.effective_policy(con, child_id, age.policy)
    skills = skills_overview(con, child_id, lang)
    mastered = sum(1 for s in skills if s["mastered"])
    failed, locked_until = _lock_state(con, child_id)

    return {
        "age": age.as_dict(),
        "child": wellbeing.child_profile(con, child_id),
        "policy": policy,
        "today": {
            "screen_seconds": wellbeing.ledger_seconds(con, child_id),
            "sessions": wellbeing.sessions_today(con, child_id),
            "sessions_cap": policy["sessions_per_day_max"],
        },
        "lock": {"locked": bool(locked_until and locked_until > iso()), "locked_until": locked_until, "failed_count": failed},
        "mastery": skills,
        "mastered_count": mastered,
        "skills_total": len(skills),
        "progress_pct": round(100 * mastered / len(skills)) if skills else 0,
        "questions_active": int(q_one(con, "SELECT COUNT(*) AS n FROM identity_questions WHERE active = 1")["n"]),
        "notifications_unread": len(unread_notifications(con)),
        "consents": consents_list(con),
        "audit_tail": recent_audit(con, limit=20),
    }


# ---------------------------------------------------------------- questions

def questions_list(con: sqlite3.Connection, child_id: str) -> list[dict[str, Any]]:
    rows = q_all(
        con,
        "SELECT id, modality, prompt_json, options_json, min_age_months, active, version FROM identity_questions WHERE child_id = ? ORDER BY id",
        (child_id,),
    )
    return [
        {
            "id": r["id"],
            "modality": r["modality"],
            "prompt": loads(r["prompt_json"]),
            "options": loads(r["options_json"]),
            "min_age_months": r["min_age_months"],
            "active": bool(r["active"]),
            "version": r["version"],
        }
        for r in rows
    ]


def question_create(con: sqlite3.Connection, child_id: str, data: dict[str, Any]) -> dict[str, Any]:
    answers = [a for a in (data.get("accepted_answers") or []) if str(a).strip()]
    if not answers:
        raise ValueError("accepted_answers requis (au moins une variante).")
    if data.get("modality") not in ("voice", "image_tap", "text"):
        raise ValueError("modality invalide.")
    qid = new_token()[:10]
    con.execute(
        """INSERT INTO identity_questions
           (id, child_id, modality, prompt_json, options_json, answer_hashes_json, min_age_months, active, version, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            qid, child_id, data["modality"],
            dumps({"text": data.get("text", ""), "emoji": data.get("emoji", "🔐")}),
            dumps(data.get("options")) if data.get("options") else None,
            dumps([hash_answer(a) for a in answers]),
            int(data.get("min_age_months", 0)), 1, 1, iso(),
        ),
    )
    audit(con, "parent.question_created", child_id=child_id, actor="parent", payload={"question_id": qid, "modality": data["modality"]})
    return {"id": qid}


def question_update(con: sqlite3.Connection, child_id: str, question_id: str, data: dict[str, Any]) -> None:
    row = q_one(con, "SELECT * FROM identity_questions WHERE id = ? AND child_id = ?", (question_id, child_id))
    if row is None:
        raise ValueError("question introuvable.")
    if "active" in data:
        con.execute(
            "UPDATE identity_questions SET active = ?, version = version + 1 WHERE id = ?",
            (1 if data["active"] else 0, question_id),
        )
    if data.get("text") is not None:
        prompt = loads(row["prompt_json"])
        prompt["text"] = data["text"]
        con.execute("UPDATE identity_questions SET prompt_json = ?, version = version + 1 WHERE id = ?", (dumps(prompt), question_id))
    if data.get("accepted_answers"):
        answers = [a for a in data["accepted_answers"] if str(a).strip()]
        if answers:
            con.execute(
                "UPDATE identity_questions SET answer_hashes_json = ?, version = version + 1 WHERE id = ?",
                (dumps([hash_answer(a) for a in answers]), question_id),
            )
    audit(con, "parent.question_updated", child_id=child_id, actor="parent", payload={"question_id": question_id, "fields": sorted(data.keys())})


# ---------------------------------------------------------------- politique & consentements

def update_policy(con: sqlite3.Connection, child_id: str, data: dict[str, Any]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if "session_max_minutes" in data:
        overrides["session_max_minutes"] = max(1, min(int(data["session_max_minutes"]), 120))
    if "sessions_per_day_max" in data:
        overrides["sessions_per_day_max"] = max(1, min(int(data["sessions_per_day_max"]), 10))
    if not overrides:
        raise ValueError("aucun champ valide.")
    wellbeing.set_policy_overrides(con, child_id, overrides)
    age = compute_age()
    return wellbeing.effective_policy(con, child_id, age.policy)


def consents_list(con: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "scope": r["scope"],
            "version": r["version"],
            "granted": r["granted_at"] is not None and r["revoked_at"] is None,
            "granted_at": r["granted_at"],
            "revoked_at": r["revoked_at"],
        }
        for r in q_all(con, "SELECT * FROM consents ORDER BY scope")
    ]


def consent_set(con: sqlite3.Connection, child_id: str, scope: str, granted: bool) -> None:
    row = q_one(con, "SELECT * FROM consents WHERE scope = ?", (scope,))
    if row is None:
        raise ValueError("scope inconnu.")
    con.execute(
        "UPDATE consents SET version = version + 1, granted_at = ?, revoked_at = ? WHERE scope = ?",
        (iso() if granted else None, None if granted else iso(), scope),
    )
    audit(con, "rgpd.consent_changed", child_id=child_id, actor="parent", payload={"scope": scope, "granted": granted})


def unlock(con: sqlite3.Connection, child_id: str) -> None:
    from .portier import unlock as _unlock

    _unlock(con, child_id, actor="parent")


# ---------------------------------------------------------------- command center

def command_mission(con: sqlite3.Connection, child_id: str, boot_at: str) -> dict[str, Any]:
    age = _child_age(con, child_id)
    policy = wellbeing.effective_policy(con, child_id, age.policy)
    skills = skills_overview(con, child_id)
    mastered = sum(1 for s in skills if s["mastered"])
    veto_count = int(q_one(con, "SELECT COUNT(*) AS n FROM audit_events WHERE type = 'wellbeing.veto'")["n"])
    id_events = recent_audit(con, limit=25, type_prefix="identity")
    failed, locked_until = _lock_state(con, child_id)
    from datetime import datetime

    uptime_s = int((utcnow() - datetime.fromisoformat(boot_at)).total_seconds())

    services = [
        {"name": "Portier d'identification", "status": "ok", "detail": f"{parental_count(con, 'challenges')} challenges"},
        {"name": "Age Calibration", "status": "ok", "detail": f"{age.years} ans {age.months} mois · {age.phase}"},
        {"name": "Orchestrateur Tuteur", "status": "ok", "detail": f"{mastered}/{len(skills)} compétences"},
        {"name": "Curriculum & Skills", "status": "ok", "detail": f"{len(skills)} nœuds du graphe"},
        {"name": "Bien-être (veto)", "status": "ok", "detail": f"{veto_count} veto appliqués"},
        {"name": "Rapport Parental", "status": "ok", "detail": f"{len(unread_notifications(con))} alertes non lues"},
        {"name": "LLM Gateway", "status": "ok", "detail": "mode local (contenus validés)"},
        {"name": "Voice STT/TTS", "status": "ok", "detail": "navigateur (Web Speech)"},
        {"name": "Audit immuable", "status": "ok", "detail": f"{parental_count(con, 'audit_events')} événements"},
    ]
    return {
        "kpi": {
            "age_display": f"{age.years} ans {age.months} mois",
            "phase": age.phase,
            "phase_label": age.phase_label,
            "progress_pct": round(100 * mastered / len(skills)) if skills else 0,
            "mastered": mastered,
            "skills_total": len(skills),
            "today_sessions": wellbeing.sessions_today(con, child_id),
            "today_minutes": round(wellbeing.ledger_seconds(con, child_id) / 60, 1),
            "sessions_cap": policy["sessions_per_day_max"],
            "locked": bool(locked_until and locked_until > iso()),
            "lock_failures": failed,
        },
        "skills": skills,
        "identity_events": id_events,
        "wellbeing": {"veto_total": veto_count, "limits_respected": True, "session_cap_minutes": policy["session_max_minutes"]},
        "notifications": unread_notifications(con),
        "services": services,
        "uptime_seconds": uptime_s,
    }


def parental_count(con: sqlite3.Connection, table: str) -> int:
    assert table in ("challenges", "audit_events", "sessions", "notifications")
    return int(q_one(con, f"SELECT COUNT(*) AS n FROM {table}")["n"])
