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
    assert body["version"] == "2.6.1"
    assert body["skills_total"] == 103               # l'arbre complet + Créer & Inventer
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
    assert tree["total"] == 103
    assert tree["counts"]["mastered"] + tree["counts"]["unlocked"] + tree["counts"]["locked"] == 103
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

def test_isolation_multi_profils():
    """LE cas signalé : régler le profil A en espagnol NE DOIT PAS impacter
    le profil B (anglophone) — ni sa langue, ni ses questions, ni ses leçons."""
    rA = client.post("/api/parent/children", headers=h(),
                     json={"display_name": "Alba", "dob": "2022-08-01", "emoji": "🇪🇸", "lang": "fr"})
    rB = client.post("/api/parent/children", headers=h(),
                     json={"display_name": "Lily", "dob": "2022-08-01", "emoji": "🇬🇧", "lang": "en"})
    A, B = rA.json()["id"], rB.json()["id"]

    texts_B_avant = {q["prompt"]["text"] for q in client.get(
        "/api/parent/questions?child_id=" + B, headers=h()).json()}

    # Alba : français → espagnol
    r = client.patch(f"/api/parent/children/{A}", headers=h(), json={"lang": "es"})
    assert r.status_code == 200 and "lang" in r.json()["updated"]

    # Alba : TOUT est en espagnol (langue + questions)
    texts_A = {q["prompt"]["text"] for q in client.get(
        "/api/parent/questions?child_id=" + A, headers=h()).json()}
    assert "¿Cómo te llamas?" in texts_A and "Comment tu t'appelles ?" not in texts_A

    # Lily : STRICTEMENT RIEN n'a bougé
    listed = client.get("/api/parent/children", headers=h()).json()
    assert next(c for c in listed if c["id"] == B)["lang"] == "en"
    assert next(c for c in listed if c["id"] == A)["lang"] == "es"
    texts_B_apres = {q["prompt"]["text"] for q in client.get(
        "/api/parent/questions?child_id=" + B, headers=h()).json()}
    assert texts_B_apres == texts_B_avant

    # Profil d'adaptation : pareil — l'attention d'Alba ne touche pas Lily
    client.patch(f"/api/parent/children/{A}", headers=h(), json={"attention": "courte", "speech_support": True})
    listed2 = client.get("/api/parent/children", headers=h()).json()
    lily = next(c for c in listed2 if c["id"] == B)
    assert lily["attention"] == "normal" and lily["speech_support"] is False

    # Leçons : chacune dans SA langue
    con = connect()
    try:
        from app import curriculum as _c
        assert _c.next_step(con, B, "en")["skill"]["label"] == "Count up to 3"
        assert _c.next_step(con, A, "es")["skill"]["label"] == "Contar hasta 3"
    finally:
        con.close()


def test_changement_langue_preserve_questions_persos():
    """Passer un profil dans une autre langue remplace SEULEMENT les
    placeholders intacts — jamais une question écrite/modifiée par le parent."""
    cid = make_child("Noah", "2022-04-12")
    # 1) question créée par le parent
    client.post("/api/parent/questions?child_id=" + cid, headers=h(), json={
        "modality": "voice", "text": "Comment s'appelle ton doudou ?",
        "emoji": "🧸", "accepted_answers": ["doudou"]})
    # 2) placeholder modifié par le parent (version > 1)
    defaults = client.get("/api/parent/questions?child_id=" + cid, headers=h()).json()
    q1 = next(q for q in defaults if "default-q1" in q["id"])
    client.patch(f"/api/parent/questions/{q1['id']}?child_id=" + cid, headers=h(),
                 json={"text": "Ton surnom secret ?"})

    # français → anglais
    client.patch(f"/api/parent/children/{cid}", headers=h(), json={"lang": "en"})
    texts = {q["prompt"]["text"] for q in client.get(
        "/api/parent/questions?child_id=" + cid, headers=h()).json()}
    assert "Comment s'appelle ton doudou ?" in texts          # perso préservée
    assert "Ton surnom secret ?" in texts                     # placeholder modifié préservé
    assert any(t.startswith("Touch the") or t.startswith("How old") or t == "What is your name?" for t in texts)


# ---------------------------------------------------------------- v2.1 : suppression de profil (suite)

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


# ---------------------------------------------------------------- v2.3 : 🚀 Créer & Inventer

def test_rubrique_creer_inventer_presente():
    """La formation « créer, concevoir, inventer » : 16 compétences trilingues,
    dont 2 portes d'entrée SANS prérequis (inv-obs, draw-animal) — la
    créativité ne se fait pas attendre (dès 3 ans si l'enfant veut)."""
    from app.seed import SKILLS, SKILL_EDGES
    inv = [s for s in SKILLS if s["domain"] == "invention"]
    assert len(inv) == 23                        # v2.4 : +7 plans « Fabrique & Assemble »
    assert len(SKILLS) == 103
    for s in inv:
        n = s["name"]
        assert set(n) >= {"fr", "en", "es"} and all(str(n[l]).strip() for l in ("fr", "en", "es"))
    cibles = {b for _a, b in SKILL_EDGES}
    entrees = sorted(s["id"] for s in inv if s["id"] not in cibles)
    assert entrees == ["draw-animal", "inv-obs"]            # portes d'entrée libres


def test_aretes_du_graphe_toutes_valides():
    """Chaque prérequis pointe vers une compétence existante (sinon : nœud orphelin)."""
    from app.seed import SKILLS, SKILL_EDGES
    ids = {s["id"] for s in SKILLS}
    assert len(ids) == len(SKILLS)                           # pas d'id dupliqué
    for a, b in SKILL_EDGES:
        assert a in ids and b in ids


def test_ardoise_draw_trilingue():
    """Le nouveau type de jeu « draw » est localisé : la consigne parlée suit
    la langue du profil (fr/en/es) — cohérent avec l'isolation v2.2."""
    from app.seed import SKILLS
    g = next(s for s in SKILLS if s["id"] == "draw-animal")["game"]
    assert g["type"] == "draw" and g["palette"]
    fr = curriculum.localize_game(g, "fr")["intro"]
    en = curriculum.localize_game(g, "en")["intro"]
    es = curriculum.localize_game(g, "es")["intro"]
    assert all(isinstance(x, str) and x for x in (fr, en, es))
    assert "animal" in fr.lower() and "animal" in en.lower() and "animal" in es.lower()
    assert fr != en != es


def test_creation_jamais_notee_erreur():
    """Règle d'or de la rubrique : les jeux de CRÉATION (draw/task) ne
    comportent AUCUNE option 'answer' — on ne peut pas « rater » une création."""
    from app.seed import SKILLS
    for s in SKILLS:
        if s["game"]["type"] in ("draw", "task", "build", "chat", "coloring"):
            assert "answer" not in s["game"] and "scenes" not in s["game"], s["id"]


def test_domaine_invention_traduit_partout():
    from app.strings import DOMAIN_NAMES
    assert DOMAIN_NAMES["invention"] == {"fr": "Créer & Inventer", "en": "Create & Invent", "es": "Crear e Inventar"}


def test_arbre_inclut_la_rubrique_et_20_racines():
    cid = make_child("Zoe", "2022-06-01")
    tree = client.get("/api/parent/tree?child_id=" + cid, headers=h()).json()
    assert tree["total"] == 103
    dom = next(d for d in tree["domains"] if d["domain"] == "invention")
    assert len(dom["skills"]) == 23
    # les racines débloquées comprennent désormais inv-obs et draw-animal
    debloquees = {s["id"] for d in tree["domains"] for s in d["skills"] if s["status"] == "unlocked"}
    assert {"inv-obs", "draw-animal"} <= debloquees
    assert tree["counts"]["unlocked"] >= 14                  # 20 racines (18 + 2 entrées créatives)


# ---------------------------------------------------------------- v2.4 : 🧩 Fabrique & Assemble + 🇨🇩 Lingala

def test_fabrique_plans_garantis_et_trilingues():
    """Chaque plan « build » : ≥3 pièces (labels trilingues), résultat + cri de
    victoire trilingues — et JAMAIS de champ « answer » (échec impossible)."""
    from app.seed import SKILLS
    builds = [s for s in SKILLS if s["game"]["type"] == "build"]
    assert len(builds) == 7
    for s in builds:
        g = s["game"]
        assert len(g["parts"]) >= 3 and "answer" not in g
        assert set(g["cheer"]) >= {"fr", "en", "es"} and set(g["intro"]) >= {"fr", "en", "es"}
        for p in g["parts"]:
            pass                                        # labels via _item — vérifiés à la localisation


def test_fabrique_localisation_complete():
    """Les pièces, le plan et le cri de victoire suivent la langue du profil."""
    from app.seed import SKILLS
    g = next(s for s in SKILLS if s["id"] == "build-robot")["game"]
    fr, en, es = (curriculum.localize_game(g, l) for l in ("fr", "en", "es"))
    assert fr["parts"][2]["label"] == "la tête"
    assert en["parts"][2]["label"] == "the head"
    assert es["parts"][2]["label"] == "la cabeza"
    assert "ROBOT" in fr["cheer"] and "ROBOT" in en["cheer"] and "ROBOT" in es["cheer"]
    assert fr["intro"] != en["intro"] != es["intro"]


def test_fiches_fabrication_illustrees():
    """Les ateliers manuels ont une fiche : 3 étapes schématisées, traduites."""
    from app.seed import SKILLS
    g = next(s for s in SKILLS if s["id"] == "inv-pont")["game"]
    assert len(g["guide"]) == 3
    fr = curriculum.localize_game(g, "fr")["guide"]
    en = curriculum.localize_game(g, "en")["guide"]
    assert all(st["emoji"] and st["label"] for st in fr)
    assert "chaises" in fr[0]["label"] and "chairs" in en[0]["label"].lower()


def test_domaine_lingala_bantou():
    """6 leçons de lingala 🇨🇩 : titres trilingues ; le MOT lingala est la
    cible (label identique dans les 3 langues — comme les pistes EN/ES)."""
    from app.seed import SKILLS
    ln = [s for s in SKILLS if s["domain"] == "lingala"]
    assert len(ln) == 6
    for s in ln:
        n = s["name"]
        assert set(n) >= {"fr", "en", "es"} and all(str(n[l]).strip() for l in ("fr", "en", "es"))
    nombres = next(s for s in ln if s["id"] == "ln-word-1")["game"]
    labels = {it["labels"]["fr"] for it in nombres["items"]}
    assert {"mokɔ́", "míbalé", "mísáto", "mínei", "mítáno"} == labels
    fr = curriculum.localize_game(nombres, "fr")
    assert "lingala" in fr["instruction_tpl"].lower()
    assert fr["items"][0]["label"] in labels             # la cible reste le mot lingala


def test_aretes_v24_toutes_valides():
    from app.seed import SKILLS, SKILL_EDGES
    ids = {s["id"] for s in SKILLS}
    assert len(ids) == 103
    for a, b in SKILL_EDGES:
        assert a in ids and b in ids


# ---------------------------------------------------------------- v2.5 : 🇵🇹 Portugais, conversations animées, coloriages, moyens de bord

def test_portugais_comme_le_lingala():
    """6 leçons de portugais 🇵🇹, titres trilingues ; le MOT portugais est la
    cible (identique dans les 3 langues), la CONSIGNE suit la langue du profil
    — pour Jade : tout s'apprend sur base du français."""
    from app.seed import SKILLS
    pt = [s for s in SKILLS if s["domain"] == "portugais"]
    assert len(pt) == 6
    for s in pt:
        n = s["name"]
        assert set(n) >= {"fr", "en", "es"} and all(str(n[l]).strip() for l in ("fr", "en", "es"))
    nombres = next(s for s in pt if s["id"] == "pt-word-1")["game"]
    labels = {it["labels"]["fr"] for it in nombres["items"]}
    assert labels == {"um", "dois", "três", "quatro", "cinco"}
    fr = curriculum.localize_game(nombres, "fr")
    assert "portugais" in fr["instruction_tpl"].lower()
    assert fr["items"][0]["label"] in labels


def test_conversations_animees_lingala_et_portugais():
    """Les phrases LN/PT sont des conversations (type « chat ») avec un guide
    gestuel : gestes démonstratifs (wave/clap/bow/sleep), consigne localisée à
    chaque réplique, mot-cible conservé tel quel, cri de victoire trilingue."""
    from app.seed import SKILLS
    gests = {"wave", "clap", "bow", "sleep"}
    for sid in ("ln-phr-1", "ln-phr-2", "pt-chat-1", "pt-chat-2"):
        g = next(s for s in SKILLS if s["id"] == sid)["game"]
        assert g["type"] == "chat" and g["partner"]["emoji"]
        assert len(g["lines"]) == 2 and "answer" not in g
        for ln in g["lines"]:
            assert ln["gesture"] in gests and ln["say_l"] and set(ln["say_i18n"]) >= {"fr", "en", "es"}
        fr, en = (curriculum.localize_game(g, l) for l in ("fr", "en"))
        assert fr["lines"][0]["say_l"] == g["lines"][0]["say_l"]        # le mot-cible ne change pas
        assert fr["lines"][0]["say_i18n"] != en["lines"][0]["say_i18n"] # la consigne, elle, est traduite
        assert set(g["cheer"]) >= {"fr", "en", "es"}


def test_coloriages_precis_et_generes():
    """6 coloriages : grande image à contours (SVG), aucun « answer » possible,
    titre consigne trilingue — l'enfant colorie sous le trait, toujours net."""
    from app.seed import SKILLS
    col = [s for s in SKILLS if s["game"]["type"] == "coloring"]
    assert len(col) == 6
    for s in col:
        g = s["game"]
        assert "<svg" in g["art"] and "stroke" in g["art"] and "answer" not in g
        assert set(g["title"]) >= {"fr", "en", "es"}
    fr = curriculum.localize_game(col[0]["game"], "fr")
    assert isinstance(fr["title"], str) and "maison" in fr["title"].lower()


def test_activites_utilisent_des_moyens_de_bord():
    """Les ateliers manuels affichent leur matériel — UNIQUEMENT des objets de
    la maison (papier, ciseaux-adulte, carton, chaises, bassine, rouleaux…) —
    et le texte du matériel est traduit dans les 3 langues."""
    from app.seed import SKILLS
    attends = {"inv-eau", "inv-aimant", "inv-histoire", "inv-robot", "inv-tour", "inv-boite", "inv-pont"}
    trouves = {s["id"] for s in SKILLS if s["game"].get("materiel")}
    assert attends == trouves
    g = next(s for s in SKILLS if s["id"] == "inv-pont")["game"]
    fr = curriculum.localize_game(g, "fr")
    assert "chaises" in fr["materiel"] and ("livres" in fr["materiel"] or "carton" in fr["materiel"])
    en = curriculum.localize_game(g, "en")
    assert "chairs" in en["materiel"].lower()


# ---------------------------------------------------------------- [AJOUT — JARDIN v2.6]
# L'enfant choisit librement SA fleur ou suit le programme — sans jamais
# casser le verrou des prérequis ni le bien-être.

def test_jardin_parterres_fleurs_et_recommandation():
    cid = make_child("Léa", "2022-03-09")
    con = connect()
    try:
        g = curriculum.garden(con, cid, "fr")
        assert g["total"] == 103
        assert g["beds"], "le jardin doit avoir des parterres"
        ids = {f["id"] for b in g["beds"] for f in b["flowers"]}
        # les entrées libres sont VISIBLES (fleurs écloses dès le départ)
        assert "inv-obs" in ids and "draw-animal" in ids
        for b in g["beds"]:
            if not b["closed"]:
                assert any(f["status"] != "locked" for f in b["flowers"])
            for f in b["flowers"]:
                assert f["status"] in ("unlocked", "locked", "mastered")
        # la fleur recommandée = celle que l'adaptatif aurait proposée
        nxt = curriculum.next_step(con, cid, "fr")
        assert g["recommended"] == (nxt["skill"]["id"] if nxt.get("skill") else None)
        recs = [f for b in g["beds"] for f in b["flowers"] if f["recommended"]]
        assert len(recs) == 1 and recs[0]["status"] == "unlocked"
    finally:
        con.close()


def test_jardin_choix_libre_respecte_le_verrou():
    cid = make_child("Tom", "2022-01-15")
    con = connect()
    try:
        # fleur éclose → jeu servi en mode « choice », localisé
        step = curriculum.step_for_skill(con, cid, "inv-obs", "fr")
        assert step is not None
        assert step["mode"] == "choice" and step["skill"]["id"] == "inv-obs"
        assert step["game"], "le jeu de la fleur éclose doit être présent"
        # pousse verrouillée → None (l'app repart au jardin avec un mot doux)
        assert curriculum.step_for_skill(con, cid, "num-add-1", "fr") is None
        # dès que le prérequis est maîtrisé, la fleur s'éclose
        curriculum.set_mastery_bulk(con, cid, ["num-2"], "mastered")
        con.commit()
        step2 = curriculum.step_for_skill(con, cid, "num-add-1", "fr")
        assert step2 is not None and step2["mode"] == "choice"
        # compétence inconnue → None aussi
        assert curriculum.step_for_skill(con, cid, "n-existe-pas", "fr") is None
    finally:
        con.close()


def test_jardin_routes_http_token_et_localisation():
    cid = make_child("Zoé", "2021-11-20")
    con = connect()
    try:
        sess = wellbeing.issue_session(con, cid, {"session_max_minutes": 10})
        con.commit()
        tok = sess["token"]
    finally:
        con.close()

    r = client.get("/api/learning/garden", params={"token": tok, "lang": "en"})
    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "en" and body["total"] == 103 and body["beds"]
    assert body["child"]["lang"] == "en"
    labels = [f["label"] for b in body["beds"] for f in b["flowers"]]
    assert any(l and l[0].isascii() for l in labels)  # libellés anglais présents

    r2 = client.get("/api/learning/step", params={"token": tok, "lang": "fr", "skill_id": "inv-obs"})
    assert r2.status_code == 200 and r2.json()["mode"] == "choice"

    r3 = client.get("/api/learning/step", params={"token": tok, "lang": "fr", "skill_id": "num-add-1"})
    assert r3.status_code == 403  # pousse verrouillée : refuse doucement

    assert client.get("/api/learning/garden", params={"token": "bidon"}).status_code == 401
