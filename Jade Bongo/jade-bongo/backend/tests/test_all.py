"""Suite de tests Jade Bɔngɔ́ — unitaires, intégration API, sécurité, bien-être.

Exécution : cd backend && python -m pytest -q
La base est isolée dans un répertoire temporaire (env positionné AVANT import).
"""
from __future__ import annotations

import os
import pathlib
import tempfile

_TMP = tempfile.mkdtemp(prefix="jade-test-")
os.environ["JADE_DB_PATH"] = str(pathlib.Path(_TMP) / "test.db")
os.environ["JADE_PARENT_PIN"] = "1234"

from datetime import date, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.age import compute_age  # noqa: E402
from app.db import connect, iso, q_one, utcnow  # noqa: E402
from app.main import app  # noqa: E402
from app.security import hash_answer, normalize, verify_candidate  # noqa: E402
from app import wellbeing  # noqa: E402
from app.curriculum import next_step, record_outcome  # noqa: E402

client = TestClient(app)
CHILD = "jade"

# ---------------------------------------------------------------- age engine

def test_age_exact_phases():
    a = compute_age(today=date(2026, 8, 5))
    assert (a.years, a.months, a.phase) == (3, 11, "PHASE_1")
    assert compute_age(today=date(2026, 9, 3)).years == 4            # anniversaire
    assert compute_age(today=date(2025, 9, 2)).total_months == 35    # veille d'anniversaire
    assert compute_age(today=date(2029, 9, 3)).phase == "PHASE_2"    # 7 ans
    assert compute_age(today=date(2035, 9, 4)).phase == "PHASE_3"    # 13 ans
    assert compute_age(today=date(2040, 9, 4)).phase == "PHASE_4"    # 18 ans
    assert compute_age(today=date(2026, 8, 5)).policy["session_max_minutes"] == 15

# ---------------------------------------------------------------- sécurité

def test_security_normalisation_et_hachage():
    assert normalize("  Trois  Ans, ! ") == "trois ans"
    h = hash_answer("Doudou")
    assert verify_candidate("doudou", [h])
    assert verify_candidate("  DOUDOU ", [h])
    assert not verify_candidate("nounours", [h])
    assert not verify_candidate("", [h])

def test_seeded_answers_hashed_not_cleared():
    con = connect()
    row = q_one(con, "SELECT answer_hashes_json FROM identity_questions WHERE id = 'q2'")
    con.close()
    import json
    hashes = json.loads(row["answer_hashes_json"])
    assert all("red" not in h for h in hashes)          # jamais en clair
    assert verify_candidate("red", hashes)
    assert not verify_candidate("blue", hashes)

# ---------------------------------------------------------------- santé de l'API

def test_health_and_age_public():
    assert client.get("/api/health").json()["service"] == "Jade Bɔngɔ́"
    age = client.get("/api/age").json()
    assert age["phase"] == "PHASE_1"
    assert "display_name" not in age and "dob" not in age   # rien de personnel sans identification

# ---------------------------------------------------------------- parcours complet heureux

SESSION = {}

def test_happy_flow_identification_session_apprentissage():
    ch = client.post("/api/identity/challenge").json()
    assert len(ch["questions"]) >= 1
    last = None
    for q in ch["questions"]:
        last = client.post("/api/identity/answer", json={
            "challenge_id": ch["challenge_id"], "question_id": q["id"],
            "answer": "", "parent_validated": True,          # adulte présent valide la réponse
        }).json()
        assert last["correct"] is True
    assert last["done"] is True and last["session"]
    SESSION["token"] = last["session"]["token"]
    assert last["session"]["remaining_seconds"] > 0

    step = client.get("/api/learning/step", params={"token": SESSION["token"]}).json()
    assert step["mode"] == "new" and step["skill"]["id"] == "coul-1"   # 1re étape du graphe

    r = client.post("/api/learning/outcome", json={"token": SESSION["token"], "skill_id": "coul-1", "success": True}).json()
    assert r["mastery"] == pytest.approx(0.25)

    status = client.get("/api/session/status", params={"token": SESSION["token"]}).json()
    assert status["status"] == "active" and status["remaining_seconds"] > 0

def test_bad_token_rejected():
    assert client.get("/api/learning/step", params={"token": "faux"}).status_code == 401

# ---------------------------------------------------------------- verrouillage anti-intrusion

def test_lockout_apres_3_echecs_puis_deverrouillage_parent():
    ch = client.post("/api/identity/challenge").json()
    qid = ch["questions"][0]["id"]
    for _ in range(2):
        r = client.post("/api/identity/answer", json={"challenge_id": ch["challenge_id"], "question_id": qid, "answer": "mauvaise reponse xyz"})
        assert r.status_code == 200 and r.json()["correct"] is False
    r = client.post("/api/identity/answer", json={"challenge_id": ch["challenge_id"], "question_id": qid, "answer": "mauvaise reponse xyz"})
    assert r.status_code == 423                                          # verrouillé
    assert client.post("/api/identity/challenge").status_code == 423     # reste verrouillé

    bad = client.post("/api/parent/login", json={"pin": "0000"})
    assert bad.status_code == 403
    good = client.post("/api/parent/login", json={"pin": "1234"})
    assert good.status_code == 200
    ptoken = good.json()["token"]
    unlock = client.post("/api/parent/unlock", headers={"Authorization": f"Bearer {ptoken}"})
    assert unlock.status_code == 200
    assert client.post("/api/identity/challenge").status_code == 200     # déverrouillé
    SESSION["ptoken"] = ptoken

# ---------------------------------------------------------------- parents : questions & politique

def test_parent_questions_crud_et_policy():
    h = {"Authorization": f"Bearer {SESSION['ptoken']}"}
    qs = client.get("/api/parent/questions", headers=h).json()
    assert len(qs) == 5

    new = client.post("/api/parent/questions", headers=h, json={
        "modality": "voice", "text": "Comment s'appelle ton doudou ?", "emoji": "🧸",
        "accepted_answers": ["doudou", "mon doudou"],
    })
    assert new.status_code == 200
    qid = new.json()["id"]
    assert client.patch(f"/api/parent/questions/{qid}", headers=h, json={"active": False}).status_code == 200

    no_answer = client.post("/api/parent/questions", headers=h, json={
        "modality": "voice", "text": "?", "accepted_answers": []})
    assert no_answer.status_code == 422

    pol = client.patch("/api/parent/policy", headers=h, json={"session_max_minutes": 10, "sessions_per_day_max": 3}).json()
    assert pol["session_max_minutes"] == 10 and pol["sessions_per_day_max"] == 3
    # retour aux valeurs standard pour la suite
    client.patch("/api/parent/policy", headers=h, json={"session_max_minutes": 15, "sessions_per_day_max": 5})

# ---------------------------------------------------------------- consentement RGPD

def test_revocation_education_bloque_les_sessions():
    h = {"Authorization": f"Bearer {SESSION['ptoken']}"}
    client.post("/api/parent/consents", headers=h, json={"scope": "education", "granted": False})
    ch = client.post("/api/identity/challenge").json()
    last = None
    for q in ch["questions"]:
        last = client.post("/api/identity/answer", json={
            "challenge_id": ch["challenge_id"], "question_id": q["id"], "parent_validated": True}).json()
    assert last["denied"] == {"reason": "consent_education"}
    client.post("/api/parent/consents", headers=h, json={"scope": "education", "granted": True})

# ---------------------------------------------------------------- curriculum (graphe + SM-2)

def test_curriculum_graphe_et_repetition_espacee():
    con = connect()
    r = record_outcome(con, CHILD, "coul-1", True)
    for _ in range(3):
        r = record_outcome(con, CHILD, "coul-1", True)
    assert r["mastery"] == 1.0 and r["mastered"]                        # ≥ 0.9 → étape validée

    step = next_step(con, CHILD)
    assert step["skill"]["id"] == "anim-1"                              # étape suivante débloquée

    con.execute("UPDATE mastery SET next_review_at = ? WHERE child_id = ? AND skill_id = 'coul-1'",
                (iso(utcnow() - timedelta(hours=1)), CHILD))
    con.commit()
    assert next_step(con, CHILD)["mode"] == "review"                    # révision due d'abord

    r2 = record_outcome(con, CHILD, "anim-1", False)
    assert r2["mastery"] == 0 and r2["streak"] == 0
    con.close()

# ---------------------------------------------------------------- bien-être (veto & limite)

def test_veto_temps_ecran_et_limite_journaliere():
    con = connect()
    policy = {"session_max_minutes": 15, "sessions_per_day_max": 2}

    s1 = wellbeing.issue_session(con, CHILD, policy)
    past = iso(utcnow() - timedelta(seconds=16 * 60))
    con.execute("UPDATE sessions SET started_at = ? WHERE token = ?", (past, s1["token"]))
    con.commit()
    st = wellbeing.session_status(con, s1["token"])
    assert st["status"] == "veto"                                       # ⛔ veto automatique
    assert wellbeing.ledger_seconds(con, CHILD) >= 900                  # temps comptabilisé

    wellbeing.issue_session(con, CHILD, policy)                         # 2e session du jour
    with pytest.raises(wellbeing.SessionDenied):
        wellbeing.can_start_session(con, CHILD, policy)                 # 3e → refusée
    con.close()

# ---------------------------------------------------------------- audit & command center

def test_audit_et_command_center():
    h = {"Authorization": f"Bearer {SESSION['ptoken']}"}
    audit_events = client.get("/api/parent/audit", headers=h, params={"type_prefix": "identity"}).json()
    assert any(e["type"] == "identity.locked" for e in audit_events)    # tout est tracé
    assert all("answer" not in str(e["payload"]) and "red" not in str(e["payload"]) for e in audit_events)

    mission = client.get("/api/command/mission", headers=h).json()
    assert mission["kpi"]["phase"] == "PHASE_1"
    assert mission["kpi"]["skills_total"] == 5
    assert mission["services"] and len(mission["services"]) == 9
    assert client.get("/api/command/mission").status_code == 401        # parent requis
