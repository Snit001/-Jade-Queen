"""v2.0 « plafond ouvert » — trilingue, graphe sans limite d'âge,
accélération, anti-frustration, évaluation initiale, profils d'adaptation.

Tourne dans la même base temporaire que test_all.py (env déjà positionné).
Chaque test crée sa propre enfant → parfaite isolation de la progression.
"""
from __future__ import annotations

import os
import pathlib
import tempfile

# Rend ce fichier autonome (exécutable seul) : si test_all a déjà fixé l'env,
# ces affectations sont sans effet car la config est déjà importée.
if "JADE_DB_PATH" not in os.environ:
    os.environ["JADE_DB_PATH"] = str(pathlib.Path(tempfile.mkdtemp(prefix="jade-test-v2-")) / "test.db")
    os.environ["JADE_PARENT_PIN"] = "1234"

from datetime import date  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app import curriculum, wellbeing
from app.age import compute_age
from app.db import connect
from app.main import app

client = TestClient(app)
H: dict = {"h": None}


def login() -> str:
    r = client.post("/api/parent/login", json={"pin": "1234"})
    assert r.status_code == 200
    return r.json()["token"]


def h():
    if H["h"] is None:
        H["h"] = {"Authorization": f"Bearer {login()}"}
    return H["h"]


def make_child(name: str, dob: str) -> str:
    r = client.post("/api/parent/children", headers=h(),
                    json={"display_name": name, "dob": dob, "emoji": "🧪"})
    assert r.status_code == 200
    return r.json()["id"]


# ---------------------------------------------------------------- santé v2

def test_health_v2_open_ceiling():
    body = client.get("/api/health").json()
    assert body["version"] == "2.0.0"
    assert body["skills_total"] == 62               # l'arbre complet
    assert set(body["langs"]) == {"fr", "en", "es"}


# ---------------------------------------------------------------- pas de plafond d'âge

def test_graphe_sans_plafond_age():
    """Une enfant de 2 ans (PHASE_1) peut atteindre les ADDITIONS si elle
    va vite : le graphe ne regarde que les prérequis, jamais l'âge."""
    cid = make_child("Nina", "2024-06-01")
    con = connect()
    try:
        # Évaluation initiale : « elle sait déjà compter jusqu'à 5 et les petites additions »
        curriculum.set_mastery_bulk(con, cid, ["num-add-2"], "mastered")
        con.commit()
        # num-3 est débloquée (num-1, num-2 validés automatiquement en cascade)
        tree = curriculum.skill_tree(con, cid, "fr")
        by_id = {s["id"]: s for d in tree["domains"] for s in d["skills"]}
        assert by_id["num-3"]["status"] == "unlocked"
        assert by_id["num-sub-1"]["status"] == "unlocked"   # branche soustractions ouverte
        assert by_id["num-mult-1"]["status"] == "unlocked"  # marche suivante servie aussitôt
        assert by_id["num-mult-2"]["status"] == "locked"    # loin dans la chaîne
        step = curriculum.next_step(con, cid, "fr")
        assert step["mode"] == "new"                        # le parcours continue, âge indifférent
        # la phase reste PHASE_1 (protection), le contenu reste ouvert (ambition)
        age = compute_age(today=date.today(), dob=date(2024, 6, 1))
        assert age.phase == "PHASE_1"
        assert age.policy["session_max_minutes"] == 15        # limite intouchable
    finally:
        con.close()


def test_evaluation_initiale_cascade_ancetres():
    cid = make_child("Omar", "2023-03-15")
    r = client.post("/api/parent/mastery?child_id=" + cid, headers=h(),
                    json={"skill_ids": ["num-4"], "action": "mastered"})
    assert r.status_code == 200
    body = r.json()
    assert body["updated"] == ["num-4"]
    # « elle compte jusqu'à 22 » → toute la chaîne validée automatiquement
    assert set(body["auto"]) == {"num-1", "num-2", "num-3"}

    tree = client.get("/api/parent/tree?child_id=" + cid, headers=h()).json()
    by_id = {s["id"]: s for d in tree["domains"] for s in d["skills"]}
    assert by_id["num-4"]["status"] == "mastered"
    assert by_id["num-5"]["status"] == "unlocked"     # la suite est servie
    assert by_id["lett-1"]["status"] == "unlocked"    # racine : toujours ouverte
    assert by_id["num-mult-2"]["status"] == "locked"  # loin dans la chaîne

    # Action de remise à zéro
    r2 = client.post("/api/parent/mastery?child_id=" + cid, headers=h(),
                     json={"skill_ids": ["num-4"], "action": "reset"})
    assert r2.status_code == 200
    tree2 = client.get("/api/parent/tree?child_id=" + cid, headers=h()).json()
    by_id2 = {s["id"]: s for d in tree2["domains"] for s in d["skills"]}
    assert by_id2["num-4"]["status"] == "unlocked"


# ---------------------------------------------------------------- trilingue

def test_localisation_espagnole_et_validation_langue():
    cid = make_child("Lucía", "2022-01-20")
    r = client.patch(f"/api/parent/children/{cid}", headers=h(), json={"lang": "es"})
    assert r.status_code == 200 and "lang" in r.json()["updated"]
    r_bad = client.patch(f"/api/parent/children/{cid}", headers=h(), json={"lang": "de"})
    assert r_bad.status_code == 400                         # seulement fr/en/es

    con = connect()
    try:
        step = curriculum.next_step(con, cid, "es")
        assert step["skill"]["id"] == "num-1"
        assert step["skill"]["label"] == "Contar hasta 3"    # nom localisé
        assert step["skill"]["domain_label"] == "Matemáticas"
        assert step["lang"] == "es"
        # le jeu est traduit : items avec labels résolus
        game = step["game"]
        assert game["type"] == "count"
    finally:
        con.close()

    tree_en = client.get(f"/api/parent/tree?child_id={cid}&lang=en", headers=h()).json()
    labels = {s["id"]: s for d in tree_en["domains"] for s in d["skills"]}
    assert labels["num-1"]["label"] == "Count up to 3"


# ---------------------------------------------------------------- profil d'attention

def test_profil_attention_raccourcit_la_session():
    cid = make_child("Tim", "2023-09-10")
    client.patch(f"/api/parent/children/{cid}", headers=h(), json={"attention": "courte"})
    con = connect()
    try:
        policy = wellbeing.effective_policy(
            con, cid, compute_age(today=date.today(), dob=date(2023, 9, 10)).policy)
        s = wellbeing.issue_session(con, cid, policy)
        # 15 min × 2/3 = 10 min — la protection reste absolue, le temps s'adapte
        assert s["max_seconds"] == 10 * 60
        s_normal = wellbeing.issue_session(con, "jade", policy)
        assert s_normal["max_seconds"] == 15 * 60
    finally:
        con.close()


def test_anti_frustration_pause_proposee():
    """3 échecs d'affilée → le système propose une pause (bien-être préventif)."""
    cid = make_child("Aya", "2023-12-01")
    con = connect()
    try:
        policy = compute_age(today=date.today(), dob=date(2023, 12, 1)).policy
        policy = wellbeing.effective_policy(con, cid, policy)
        session = wellbeing.issue_session(con, cid, policy)
        res = None
        for _ in range(3):
            res = curriculum.record_outcome(con, cid, "coul-1", False, session_id=session["session_id"])
        assert res["suggest_break"] is True and res["consec_fails"] == 3
        # un succès remet le compteur à zéro
        ok = curriculum.record_outcome(con, cid, "coul-1", True, session_id=session["session_id"])
        assert ok["consec_fails"] == 0 and ok["suggest_break"] is False
    finally:
        con.close()


# ---------------------------------------------------------------- accélération

def test_acceleration_du_premier_coup():
    """Compétence validée sans aucun échec → événement d'accélération.
    On nourrit l'enfant rapide — le temps d'écran, lui, ne bouge pas."""
    cid = make_child("Zoé", "2022-11-30")
    con = connect()
    try:
        res = None
        for _ in range(4):                                   # 4 × +0.25 → maîtrise 1.0
            res = curriculum.record_outcome(con, cid, "art-music", True)
        assert res["mastered"] is True and res["mastered_now"] is True
        assert res["accelerated"] is True

        # Avec un échec dans le parcours → pas d'accélération (mais réussite quand même)
        curriculum.record_outcome(con, cid, "log-ombre", False)
        res2 = None
        for _ in range(6):
            res2 = curriculum.record_outcome(con, cid, "log-ombre", True)
        assert res2["mastered"] is True
        assert res2["accelerated"] is False                  # ease descendue sous 2.5
    finally:
        con.close()


# ---------------------------------------------------------------- arbre parent

def test_arbre_complet_et_compteurs():
    cid = make_child("Ivy", "2023-05-05")
    tree = client.get("/api/parent/tree?child_id=" + cid, headers=h()).json()
    assert tree["total"] == 62
    assert tree["counts"]["mastered"] + tree["counts"]["unlocked"] + tree["counts"]["locked"] == 62
    # au départ : toutes les racines débloquées, le reste verrouillé
    assert tree["counts"]["unlocked"] >= 12                  # 18 racines exactement
    labels = [s["label"] for d in tree["domains"] for s in d["skills"]]
    assert any("Count up to 3" in l or "Compter jusqu'à 3" in l for l in labels)
