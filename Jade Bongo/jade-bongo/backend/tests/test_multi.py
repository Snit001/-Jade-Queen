"""Multi-enfants : profils isolés, âge-moteur par enfant, sélecteur public.

Tourne dans la même base temporaire que test_all.py (env déjà positionné).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
H = {}
LEO = "leo"


def login() -> str:
    r = client.post("/api/parent/login", json={"pin": "1234"})
    assert r.status_code == 200
    return r.json()["token"]


def test_creation_profil_et_selecteur_public():
    H["h"] = {"Authorization": f"Bearer {login()}"}

    r = client.post("/api/parent/children", headers=H["h"],
                    json={"display_name": "Léo", "dob": "2024-01-15", "emoji": "🦊"})
    assert r.status_code == 200
    global LEO
    LEO = r.json()["id"]
    assert LEO.startswith("leo")

    pick = client.get("/api/children").json()
    names = {c["display_name"] for c in pick}
    assert {"Jade", "Léo"} <= names
    assert all(set(c.keys()) == {"id", "display_name", "emoji", "lang"} for c in pick)  # minimal + langue (v2.1)

    listed = client.get("/api/parent/children", headers=H["h"]).json()
    leo = next(c for c in listed if c["id"] == LEO)
    assert leo["age_years"] >= 1 and leo["phase"] == "PHASE_1"

    bad = client.post("/api/parent/children", headers=H["h"],
                      json={"display_name": "Futur", "dob": "2999-01-01"})
    assert bad.status_code == 400                        # naissance dans le futur refusée


def test_isolation_verrous_et_progression():
    # Léo se trompe 3 fois → Léo verrouillé
    ch = client.post("/api/identity/challenge", params={"child_id": LEO}).json()
    qid = ch["questions"][0]["id"]
    for _ in range(3):
        client.post("/api/identity/answer", json={
            "challenge_id": ch["challenge_id"], "question_id": qid, "answer": "faux faux"})
    assert client.post("/api/identity/challenge", params={"child_id": LEO}).status_code == 423

    # …mais Jade reste libre (isolation des verrous) ✔
    assert client.post("/api/identity/challenge").status_code == 200

    # Déverrouillage ciblé de Léo par le parent
    assert client.post("/api/parent/unlock", headers=H["h"], params={"child_id": LEO}).status_code == 200
    ch2 = client.post("/api/identity/challenge", params={"child_id": LEO})
    assert ch2.status_code == 200

    # Parcours complets : Léo démarre comme un enfant neuf malgré la progression de Jade
    last = None
    for q in ch2.json()["questions"]:
        last = client.post("/api/identity/answer", json={
            "challenge_id": ch2.json()["challenge_id"], "question_id": q["id"],
            "parent_validated": True}).json()
    assert last["done"] and last["session"]
    step = client.get("/api/learning/step", params={"token": last["session"]["token"]}).json()
    assert step["skill"]["id"] == "num-1"
    assert step["skill"]["mastery"] == 0.0               # progression séparée ✔
    client.post("/api/session/end", json={"token": last["session"]["token"]})


def test_phase_suivant_dob_et_questions_cloisonnees():
    # Une enfant de 7 ans (phase 2) : le challenge ne pioche que des questions
    # autorisées par SA politique d'âge (voix/texte), jamais celles d'un autre enfant.
    r = client.post("/api/parent/children", headers=H["h"],
                    json={"display_name": "Mia", "dob": "2019-06-01", "emoji": "🦋"})
    mia = r.json()["id"]
    ch = client.post("/api/identity/challenge", params={"child_id": mia}).json()
    assert len(ch["questions"]) >= 1
    assert all(q["modality"] == "voice" for q in ch["questions"])      # PHASE_2 : pas d'image_tap
    assert all(q["id"].startswith(f"{mia}-") for q in ch["questions"]) # SES questions à elle


def test_vue_parents_multi_enfants():
    ov_jade = client.get("/api/parent/overview", headers=H["h"]).json()
    ov_leo = client.get("/api/parent/overview", headers=H["h"], params={"child_id": LEO}).json()
    assert ov_jade["skills_total"] == 62                               # v2.0 : arbre complet
    assert ov_leo["skills_total"] == 62
    assert ov_leo["mastered_count"] == 0                               # Léo au début de SON graphe
    assert ov_leo["lock"]["locked"] is False                           # déverrouillé plus haut
