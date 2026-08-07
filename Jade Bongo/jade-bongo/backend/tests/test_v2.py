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
    assert body["version"] == "2.1.0"
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


# ---------------------------------------------------------------- v2.1 : langue du PROFIL

def test_profil_anglophone_tout_en_anglais():
    """La langue suit le PROFIL, pas l'appareil : une enfant anglophone reçoit
    interface, leçons et voix en anglais — même si le téléphone est en français."""
    cid = make_child("Grace", "2022-05-10")
    assert client.patch(f"/api/parent/children/{cid}", headers=h(), json={"lang": "en"}).status_code == 200

    ch = client.post("/api/identity/challenge", params={"child_id": cid}).json()
    last = None
    for q in ch["questions"]:
        last = client.post("/api/identity/answer", json={
            "challenge_id": ch["challenge_id"], "question_id": q["id"],
            "parent_validated": True}).json()
    assert last["done"] and last["session"]
    step = client.get("/api/learning/step", params={"token": last["session"]["token"]}).json()
    assert step["lang"] == "en" and step["child"]["lang"] == "en"
    assert step["skill"]["label"] == "Count up to 3"         # leçon en anglais
    assert step["skill"]["domain_label"] == "Mathematics"
    # le sélecteur public expose la langue (interface traduite AVANT identification)
    pick = client.get("/api/children").json()
    grace = next(c for c in pick if c["id"] == cid)
    assert grace["lang"] == "en"
    assert all(set(c.keys()) == {"id", "display_name", "emoji", "lang"} for c in pick)
    client.post("/api/session/end", json={"token": last["session"]["token"]})


def test_questions_dans_la_langue_du_profil():
    """Création d'un profil anglophone : questions placeholder EN ANGLAIS,
    avec le prénom et l'âge réel déjà acceptés. Idem en espagnol."""
    r = client.post("/api/parent/children", headers=h(),
                    json={"display_name": "Emma", "dob": "2022-05-10", "emoji": "🇺🇸", "lang": "en"})
    assert r.status_code == 200 and r.json()["lang"] == "en"
    cid = r.json()["id"]
    qs = client.get("/api/parent/questions?child_id=" + cid, headers=h()).json()
    texts = {q["prompt"]["text"] for q in qs}
    assert "What is your name?" in texts                     # pas de français !
    assert "How old are you?" in texts

    import json as _json
    from app.security import verify_candidate
    con = connect()
    try:
        q1 = con.execute("SELECT answer_hashes_json FROM identity_questions WHERE child_id = ? AND id LIKE '%q1'",
                         (cid,)).fetchone()
        assert verify_candidate("Emma", _json.loads(q1[0]))  # prénom déjà accepté
        q4 = con.execute("SELECT answer_hashes_json FROM identity_questions WHERE child_id = ? AND id LIKE '%q4'",
                         (cid,)).fetchone()
        assert verify_candidate("4", _json.loads(q4[0]))     # âge réel déjà accepté
    finally:
        con.close()

    # un profil espagnol
    r2 = client.post("/api/parent/children", headers=h(),
                     json={"display_name": "Sofía", "dob": "2021-09-01", "emoji": "🇪🇸", "lang": "es"})
    assert r2.status_code == 200 and r2.json()["lang"] == "es"
    texts_es = {q["prompt"]["text"] for q in client.get(
        "/api/parent/questions?child_id=" + r2.json()["id"], headers=h()).json()}
    assert "¿Cómo te llamas?" in texts_es
    # langue inconnue → refus
    bad = client.post("/api/parent/children", headers=h(),
                      json={"display_name": "X", "dob": "2022-01-01", "lang": "de"})
    assert bad.status_code in (400, 422)


# ---------------------------------------------------------------- v2.1 : suppression de profil

def test_suppression_profil_cascade():
    cid = make_child("Temp", "2023-01-01")
    # un peu de progression, de sécurité et de politique à effacer
    client.post("/api/parent/mastery?child_id=" + cid, headers=h(),
                json={"skill_ids": ["coul-1"], "action": "mastered"})
    client.patch("/api/parent/policy?child_id=" + cid, headers=h(),
                 json={"session_max_minutes": 8})
    r = client.delete(f"/api/parent/children/{cid}", headers=h())
    assert r.status_code == 200 and r.json()["deleted"] == cid

    pick = client.get("/api/children").json()
    assert cid not in {c["id"] for c in pick}
    con = connect()
    try:
        for table in ("mastery", "sessions", "locks", "challenges",
                      "identity_questions", "policy_overrides", "screen_time_ledger"):
            n = con.execute(f"SELECT COUNT(*) FROM {table} WHERE child_id = ?", (cid,)).fetchone()[0]
            assert n == 0, f"{table} : données orphelines"
        # requête parent sur un profil supprimé → 404
    finally:
        con.close()
    assert client.get("/api/parent/overview", headers=h(),
                      params={"child_id": cid}).status_code == 404

    # suppression d'un inconnu → 400
    assert client.delete("/api/parent/children/inconnu", headers=h()).status_code == 400


def test_dernier_profil_non_supprimable():
    """Garde-fou absolu : il doit toujours rester au moins un profil.
    (Dernier test du fichier : réduit la base à un seul enfant.)"""
    from app import parental
    con = connect()
    try:
        ids = [r[0] for r in con.execute("SELECT id FROM children ORDER BY created_at").fetchall()]
        for victim in ids[:-1]:
            parental.delete_child(con, victim)
        con.commit()
        try:
            parental.delete_child(con, ids[-1])
            raise AssertionError("doit refuser de supprimer le dernier profil")
        except ValueError:
            con.rollback()
    finally:
        con.close()
