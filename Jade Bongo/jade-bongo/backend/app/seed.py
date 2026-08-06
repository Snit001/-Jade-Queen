"""Données initiales (idempotentes) : profil de Jade, graphe de compétences
Phase 1, questions d'identification par défaut, consentements RGPD.

⚠ Les questions par défaut sont des PLACEHOLDERS : les parents les remplacent
depuis le Dashboard (les vraies réponses ne sont jamais stockées en clair).
"""
from __future__ import annotations

import sqlite3

from .audit import audit
from .db import dumps, iso, q_one
from .security import hash_answer
from .config import LOCK_MAX_FAILURES  # noqa: F401  (réexport utile aux tests)

CHILD_ID = "jade"
CHILD_DOB = "2022-09-03"

SKILLS: list[dict] = [
    {
        "id": "coul-1", "ord_i": 1, "domain": "couleurs", "label": "Les couleurs", "emoji": "🎨",
        "game": {
            "type": "tap",
            "instruction_tpl": "Touche la couleur : {label} {emoji}",
            "items": [
                {"id": "red", "label": "rouge", "emoji": "🔴"},
                {"id": "blue", "label": "bleu", "emoji": "🔵"},
                {"id": "green", "label": "vert", "emoji": "🟢"},
                {"id": "yellow", "label": "jaune", "emoji": "🟡"},
            ],
            "rounds": 3,
        },
    },
    {
        "id": "anim-1", "ord_i": 2, "domain": "animaux", "label": "Les animaux", "emoji": "🐱",
        "game": {
            "type": "tap",
            "instruction_tpl": "Touche l'animal : {label} {emoji}",
            "items": [
                {"id": "cat", "label": "chat", "emoji": "🐱"},
                {"id": "dog", "label": "chien", "emoji": "🐶"},
                {"id": "rabbit", "label": "lapin", "emoji": "🐰"},
                {"id": "duck", "label": "canard", "emoji": "🦆"},
            ],
            "rounds": 3,
        },
    },
    {
        "id": "form-1", "ord_i": 3, "domain": "formes", "label": "Les formes", "emoji": "🔷",
        "game": {
            "type": "tap",
            "instruction_tpl": "Touche la forme : {label} {emoji}",
            "items": [
                {"id": "circle", "label": "cercle", "emoji": "⭕"},
                {"id": "square", "label": "carré", "emoji": "🟦"},
                {"id": "triangle", "label": "triangle", "emoji": "🔺"},
                {"id": "star", "label": "étoile", "emoji": "⭐"},
            ],
            "rounds": 3,
        },
    },
    {
        "id": "num-1", "ord_i": 4, "domain": "nombres", "label": "Compter jusqu'à 3", "emoji": "🔢",
        "game": {"type": "count", "object_emoji": "🍎", "min": 1, "max": 3, "rounds": 3},
    },
    {
        "id": "song-1", "ord_i": 5, "domain": "comptines", "label": "Comptine : Une souris verte", "emoji": "🎵",
        "game": {
            "type": "song",
            "title": "Une souris verte",
            "lines": [
                "Une souris verte 🐭",
                "Qui courait dans l'herbe 🌿",
                "Je l'attrape par la queue 🐾",
                "Je la montre à ces messieurs 🎩",
            ],
        },
    },
]

SKILL_EDGES = [("coul-1", "anim-1"), ("anim-1", "form-1"), ("form-1", "num-1"), ("num-1", "song-1")]

QUESTIONS: list[dict] = [
    {
        "id": "q1", "modality": "voice",
        "prompt": {"text": "Comment tu t'appelles ?", "emoji": "👋"},
        "options": None,
        "answers": ["jade", "jade queen", "jade mbo", "jade queen mbo"],
    },
    {
        "id": "q2", "modality": "image_tap",
        "prompt": {"text": "Touche la couleur rouge", "emoji": "❤️"},
        "options": [
            {"id": "red", "label": "rouge", "emoji": "🔴"},
            {"id": "blue", "label": "bleu", "emoji": "🔵"},
            {"id": "green", "label": "vert", "emoji": "🟢"},
            {"id": "yellow", "label": "jaune", "emoji": "🟡"},
        ],
        "answers": ["red"],
    },
    {
        "id": "q3", "modality": "image_tap",
        "prompt": {"text": "Touche le chat", "emoji": "🐾"},
        "options": [
            {"id": "dog", "label": "chien", "emoji": "🐶"},
            {"id": "cat", "label": "chat", "emoji": "🐱"},
            {"id": "rabbit", "label": "lapin", "emoji": "🐰"},
            {"id": "duck", "label": "canard", "emoji": "🦆"},
        ],
        "answers": ["cat"],
    },
    {
        "id": "q4", "modality": "voice",
        "prompt": {"text": "Quel âge as-tu ?", "emoji": "🎂"},
        "options": None,
        "answers": ["3", "trois", "trois ans", "j ai trois ans"],
    },
    {
        "id": "q5", "modality": "image_tap",
        "prompt": {"text": "Touche l'étoile", "emoji": "⭐"},
        "options": [
            {"id": "star", "label": "étoile", "emoji": "⭐"},
            {"id": "heart", "label": "cœur", "emoji": "❤️"},
            {"id": "dot", "label": "rond", "emoji": "🔵"},
            {"id": "tri", "label": "triangle", "emoji": "🔺"},
        ],
        "answers": ["star"],
    },
]

CONSENTS = ["education", "stockage_donnees", "voix_audio", "rapports_parents"]


def seed(con: sqlite3.Connection) -> None:
    """Idempotent : n'insère que ce qui manque."""
    if q_one(con, "SELECT id FROM children WHERE id = ?", (CHILD_ID,)) is None:
        con.execute(
            "INSERT INTO children (id, display_name, dob, phase, created_at) VALUES (?,?,?,?,?)",
            (CHILD_ID, "Jade", CHILD_DOB, "PHASE_1", iso()),
        )
        audit(con, "system.child_created", child_id=CHILD_ID, payload={"display_name": "Jade"})

    existing_skills = {r["id"] for r in con.execute("SELECT id FROM skills").fetchall()}
    for s in SKILLS:
        if s["id"] not in existing_skills:
            con.execute(
                "INSERT INTO skills (id, ord_i, domain, label, emoji, min_phase, game_json) VALUES (?,?,?,?,?,?,?)",
                (s["id"], s["ord_i"], s["domain"], s["label"], s["emoji"], "PHASE_1", dumps(s["game"])),
            )
    existing_edges = {(r["from_skill"], r["to_skill"]) for r in con.execute("SELECT * FROM skill_edges").fetchall()}
    for a, b in SKILL_EDGES:
        if (a, b) not in existing_edges:
            con.execute("INSERT INTO skill_edges (from_skill, to_skill) VALUES (?,?)", (a, b))

    existing_q = {r["id"] for r in con.execute("SELECT id FROM identity_questions").fetchall()}
    for q in QUESTIONS:
        if q["id"] not in existing_q:
            con.execute(
                """INSERT INTO identity_questions
                   (id, child_id, modality, prompt_json, options_json, answer_hashes_json,
                    min_age_months, active, version, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    q["id"], CHILD_ID, q["modality"], dumps(q["prompt"]),
                    dumps(q["options"]) if q["options"] else None,
                    dumps([hash_answer(a) for a in q["answers"]]),
                    0, 1, 1, iso(),
                ),
            )

    for scope in CONSENTS:
        if q_one(con, "SELECT scope FROM consents WHERE scope = ?", (scope,)) is None:
            con.execute(
                "INSERT INTO consents (scope, version, granted_at, revoked_at) VALUES (?,?,?,NULL)",
                (scope, 1, iso()),
            )

    con.commit()
