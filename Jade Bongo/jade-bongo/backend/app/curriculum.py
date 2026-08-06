"""curriculum-service — le parcours étape par étape de Jade.

- Graphe de compétences (une étape d'un domaine à la fois, jamais de saut)
- Mastery Learning : une étape n'est validée qu'à 90 % de maîtrise
- Répétition espacée (SM-2 : ease factor, intervalles croissants, reviews dues)
- Chaque événement est audité (transparence parents)
"""
from __future__ import annotations

import sqlite3
from datetime import timedelta
from typing import Any

from .audit import audit, notify
from .db import iso, loads, q_all, q_one, utcnow

MASTERY_THRESHOLD = 0.9
GAIN_ON_SUCCESS = 0.25
LOSS_ON_FAILURE = 0.15


def _mastery_row(con: sqlite3.Connection, child_id: str, skill_id: str) -> sqlite3.Row | None:
    return q_one(con, "SELECT * FROM mastery WHERE child_id = ? AND skill_id = ?", (child_id, skill_id))


def mastery_map(con: sqlite3.Connection, child_id: str) -> dict[str, float]:
    return {
        r["skill_id"]: float(r["mastery"])
        for r in q_all(con, "SELECT skill_id, mastery FROM mastery WHERE child_id = ?", (child_id,))
    }


def _prerequisites_met(con: sqlite3.Connection, child_id: str, skill_id: str, mmap: dict[str, float]) -> bool:
    prereqs = q_all(con, "SELECT from_skill FROM skill_edges WHERE to_skill = ?", (skill_id,))
    return all(mmap.get(p["from_skill"], 0.0) >= MASTERY_THRESHOLD for p in prereqs)


def next_step(con: sqlite3.Connection, child_id: str) -> dict[str, Any]:
    """Prochaine étape : révision due d'abord (SM-2), sinon nouvelle compétence du graphe."""
    skills = q_all(con, "SELECT * FROM skills ORDER BY ord_i")
    mmap = mastery_map(con, child_id)
    now = iso()

    # 1) Révisions dues (répétition espacée : on ne progresse pas sans consolider)
    due = [
        r for r in q_all(
            con,
            "SELECT * FROM mastery WHERE child_id = ? AND next_review_at IS NOT NULL AND next_review_at <= ? AND mastery > 0 ORDER BY next_review_at",
            (child_id, now),
        )
    ]
    if due:
        skill_row = q_one(con, "SELECT * FROM skills WHERE id = ?", (due[0]["skill_id"],))
        if skill_row is not None:
            return _payload(con, child_id, skill_row, mode="review", mmap=mmap)

    # 2) Première compétence non maîtrisée dont les prérequis sont validés
    for s in skills:
        if mmap.get(s["id"], 0.0) < MASTERY_THRESHOLD and _prerequisites_met(con, child_id, s["id"], mmap):
            return _payload(con, child_id, s, mode="new", mmap=mmap)

    return {"mode": "done", "skill": None, "game": None, "progress": _progress(con, child_id, mmap)}


def _payload(con: sqlite3.Connection, child_id: str, skill_row: sqlite3.Row, *, mode: str, mmap: dict[str, float]) -> dict[str, Any]:
    return {
        "mode": mode,
        "skill": {
            "id": skill_row["id"],
            "domain": skill_row["domain"],
            "label": skill_row["label"],
            "emoji": skill_row["emoji"],
            "mastery": round(mmap.get(skill_row["id"], 0.0), 2),
        },
        "game": loads(skill_row["game_json"]),
        "progress": _progress(con, child_id, mmap),
    }


def _progress(con: sqlite3.Connection, child_id: str, mmap: dict[str, float]) -> dict[str, Any]:
    total = len(q_all(con, "SELECT id FROM skills"))
    mastered = sum(1 for v in mmap.values() if v >= MASTERY_THRESHOLD)
    return {"mastered": mastered, "total": total, "pct": round(100 * mastered / total) if total else 0}


def record_outcome(con: sqlite3.Connection, child_id: str, skill_id: str, success: bool) -> dict[str, Any]:
    """Met à jour la maîtrise + planifie la prochaine révision (répétition espacée)."""
    if q_one(con, "SELECT id FROM skills WHERE id = ?", (skill_id,)) is None:
        raise ValueError("unknown_skill")

    row = _mastery_row(con, child_id, skill_id)
    mastery = float(row["mastery"]) if row else 0.0
    ease = float(row["ease"]) if row else 2.5
    interval_h = float(row["interval_h"]) if row else 1.0
    streak = int(row["streak"]) if row else 0
    before = mastery

    if success:
        streak += 1
        mastery = min(1.0, mastery + GAIN_ON_SUCCESS)
        interval_h = max(1.0, interval_h * ease)
        ease = min(2.8, ease + 0.1)
    else:
        streak = 0
        mastery = max(0.0, mastery - LOSS_ON_FAILURE)
        ease = max(1.3, ease - 0.2)
        interval_h = 1.0

    next_review = iso(utcnow() + timedelta(hours=interval_h)) if mastery > 0 else None
    con.execute(
        """INSERT INTO mastery (child_id, skill_id, mastery, ease, interval_h, streak, next_review_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(child_id, skill_id) DO UPDATE SET
             mastery = excluded.mastery, ease = excluded.ease, interval_h = excluded.interval_h,
             streak = excluded.streak, next_review_at = excluded.next_review_at, updated_at = excluded.updated_at""",
        (child_id, skill_id, mastery, ease, interval_h, streak, next_review, iso()),
    )

    audit(
        con, "learning.outcome", child_id=child_id, actor="child",
        payload={"skill_id": skill_id, "success": success, "mastery_before": round(before, 2), "mastery_after": round(mastery, 2)},
    )

    # 🏆 Jalon franchi → notification aux parents (fierté partagée)
    if before < MASTERY_THRESHOLD <= mastery:
        skill = q_one(con, "SELECT label, emoji FROM skills WHERE id = ?", (skill_id,))
        audit(con, "learning.mastery_reached", child_id=child_id, payload={"skill_id": skill_id})
        notify(con, "learning.milestone", {"skill_id": skill_id, "label": skill["label"] if skill else skill_id, "emoji": skill["emoji"] if skill else "⭐"})

    return {
        "skill_id": skill_id,
        "mastery": round(mastery, 2),
        "streak": streak,
        "ease": round(ease, 2),
        "interval_h": round(interval_h, 1),
        "next_review_at": next_review,
        "mastered": mastery >= MASTERY_THRESHOLD,
    }


def skills_overview(con: sqlite3.Connection, child_id: str) -> list[dict[str, Any]]:
    rows = q_all(
        con,
        """SELECT s.id, s.ord_i, s.domain, s.label, s.emoji,
                  COALESCE(m.mastery, 0) AS mastery, COALESCE(m.streak, 0) AS streak,
                  m.next_review_at
           FROM skills s LEFT JOIN mastery m ON m.skill_id = s.id AND m.child_id = ?
           ORDER BY s.ord_i""",
        (child_id,),
    )
    return [
        {
            "id": r["id"], "ord": r["ord_i"], "domain": r["domain"], "label": r["label"], "emoji": r["emoji"],
            "mastery": round(float(r["mastery"]), 2), "streak": int(r["streak"]),
            "mastered": float(r["mastery"]) >= MASTERY_THRESHOLD,
            "next_review_at": r["next_review_at"],
        }
        for r in rows
    ]
