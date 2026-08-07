"""curriculum-service — le parcours étape par étape de Jade (v2.0 « plafond ouvert »).

PRINCIPE FONDATEUR (demande des parents) :
- Le graphe ne connaît AUCUNE limite d'âge. Une compétence est débloquée
  dès que ses prérequis sont maîtrisés (≥ 90 %). L'âge ne pilote que la
  protection (temps d'écran, accompagnement) — jamais le contenu.
- Accélération : une compétence validée du premier coup (peu d'essais,
  aisance intacte) déclenche un événement `learning.acceleration` et la
  proposition immédiate du niveau suivant. On nourrit l'enfant rapide,
  SANS jamais desserrer le bien-être.
- Anti-frustration : 3 échecs consécutifs dans une session → le système
  propose une pause respiration (bien-être préventif).

- Mastery Learning : une étape n'est validée qu'à 90 % de maîtrise
- Répétition espacée (SM-2 : ease factor, intervalles croissants, reviews dues)
- Localisation : noms de compétences et jeux servis dans la langue de l'enfant
- Chaque événement est audité (transparence parents)
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date
from datetime import timedelta
from typing import Any

from .audit import audit, notify
from .db import iso, loads, q_all, q_one, utcnow
from .strings import domain_name, norm_lang

MASTERY_THRESHOLD = 0.9
GAIN_ON_SUCCESS = 0.25
LOSS_ON_FAILURE = 0.15
# Accélération : maîtrise acquise en très peu d'essais, sans jamais d'échec
# (ease jamais descendue sous la valeur initiale 2.5).
ACCEL_MAX_ATTEMPTS = 5
# Anti-frustration : échecs consécutifs dans la session → pause proposée
BREAK_SUGGEST_AFTER = 3


# ------------------------------------------------------------------ localisation

def skill_name(skill_row: sqlite3.Row, lang: str) -> str:
    names = loads(skill_row["names_json"], None) or {}
    return names.get(lang) or names.get("fr") or skill_row["label"]


def localize_game(game: dict[str, Any], lang: str) -> dict[str, Any]:
    """Renvoie une copie du jeu prête à afficher dans la langue demandée.

    - instruction_tpl, intro, tasks, title, lines : traduits
    - items/options : label résolu (labels.{lang}), labels supprimés
    - contenu des langues étrangères (en-*, es-*) : le label est le même dans
      toutes les langues (c'est justement le mot à apprendre) — déjà géré.
    """
    g = dict(game)

    def tr(node: Any) -> Any:
        if isinstance(node, dict) and set(node) >= {"fr", "en", "es"}:
            return node.get(lang) or node.get("fr")
        return node

    if isinstance(g.get("instruction_tpl"), dict):
        g["instruction_tpl"] = tr(g["instruction_tpl"])
    if isinstance(g.get("intro"), dict):
        g["intro"] = tr(g["intro"])
    if isinstance(g.get("title"), dict):
        g["title"] = tr(g["title"])
    if isinstance(g.get("lines"), dict):
        g["lines"] = g["lines"].get(lang) or g["lines"].get("fr") or []
    if isinstance(g.get("tasks"), list):
        g["tasks"] = [tr(t) for t in g["tasks"]]

    def fix_items(items: list[dict]) -> list[dict]:
        out = []
        for it in items:
            it2 = dict(it)
            if "labels" in it2:
                labels = it2.pop("labels")
                it2["label"] = labels.get(lang) or labels.get("fr") or ""
            out.append(it2)
        return out

    if isinstance(g.get("items"), list):
        g["items"] = fix_items(g["items"])
    if isinstance(g.get("options"), list):
        g["options"] = fix_items(g["options"])
    if isinstance(g.get("scenes"), list):
        scenes = []
        for sc in g["scenes"]:
            sc2 = dict(sc)
            sc2["q"] = tr(sc2.get("q"))
            sc2["options"] = fix_items(sc2.get("options", []))
            scenes.append(sc2)
        g["scenes"] = scenes
    if isinstance(g.get("sets"), list):
        sets = []
        for st in g["sets"]:
            st2 = dict(st)
            st2["hint"] = tr(st2.get("hint"))
            st2["options"] = fix_items(st2.get("options", []))
            sets.append(st2)
        g["sets"] = sets
    return g


# ------------------------------------------------------------------ graphe

def mastery_map(con: sqlite3.Connection, child_id: str) -> dict[str, float]:
    return {
        r["skill_id"]: float(r["mastery"])
        for r in q_all(con, "SELECT skill_id, mastery FROM mastery WHERE child_id = ?", (child_id,))
    }


def _prereqs(con: sqlite3.Connection, skill_id: str) -> list[str]:
    return [r["from_skill"] for r in q_all(con, "SELECT from_skill FROM skill_edges WHERE to_skill = ?", (skill_id,))]


def prerequisites_met(con: sqlite3.Connection, skill_id: str, mmap: dict[str, float]) -> bool:
    return all(mmap.get(p, 0.0) >= MASTERY_THRESHOLD for p in _prereqs(con, skill_id))


def skill_status(con: sqlite3.Connection, skill_id: str, mmap: dict[str, float]) -> str:
    if mmap.get(skill_id, 0.0) >= MASTERY_THRESHOLD:
        return "mastered"
    return "unlocked" if prerequisites_met(con, skill_id, mmap) else "locked"


def next_step(con: sqlite3.Connection, child_id: str, lang: str = "fr") -> dict[str, Any]:
    """Prochaine étape : révision due d'abord (SM-2), sinon compétence débloquée
    la plus accessible (niveau croissant). AUCUNE barrière d'âge : le graphe
    entier est ouvert, seuls les prérequis guident le chemin."""
    lang = norm_lang(lang)
    mmap = mastery_map(con, child_id)
    now = iso()

    # 1) Révisions dues (répétition espacée : on ne progresse pas sans consolider)
    due = [
        r for r in q_all(
            con,
            """SELECT m.skill_id FROM mastery m
               WHERE m.child_id = ? AND m.next_review_at IS NOT NULL
                 AND m.next_review_at <= ? AND m.mastery > 0
               ORDER BY m.next_review_at""",
            (child_id, now),
        )
    ]
    for d in due:
        skill_row = q_one(con, "SELECT * FROM skills WHERE id = ?", (d["skill_id"],))
        if skill_row is not None:
            return _payload(con, skill_row, mode="review", mmap=mmap, lang=lang)

    # 2) Compétence débloquée de plus bas niveau (le plafond est ouvert)
    rows = q_all(con, "SELECT * FROM skills ORDER BY level, ord_i")
    for s in rows:
        if mmap.get(s["id"], 0.0) < MASTERY_THRESHOLD and prerequisites_met(con, s["id"], mmap):
            return _payload(con, s, mode="new", mmap=mmap, lang=lang)

    return {"mode": "done", "skill": None, "game": None, "lang": lang,
            "progress": _progress(con, mmap)}


def _payload(con: sqlite3.Connection, skill_row: sqlite3.Row, *, mode: str,
             mmap: dict[str, float], lang: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "lang": lang,
        "skill": {
            "id": skill_row["id"],
            "domain": skill_row["domain"],
            "domain_label": domain_name(skill_row["domain"], lang),
            "level": int(skill_row["level"]),
            "label": skill_name(skill_row, lang),
            "emoji": skill_row["emoji"],
            "mastery": round(mmap.get(skill_row["id"], 0.0), 2),
        },
        "game": localize_game(loads(skill_row["game_json"], {}), lang),
        "progress": _progress(con, mmap),
    }


def _progress(con: sqlite3.Connection, mmap: dict[str, float]) -> dict[str, Any]:
    total = int(q_one(con, "SELECT COUNT(*) AS n FROM skills")["n"])
    mastered = sum(1 for v in mmap.values() if v >= MASTERY_THRESHOLD)
    return {"mastered": mastered, "total": total, "pct": round(100 * mastered / total) if total else 0}


# ------------------------------------------------------------------ résultats

def record_outcome(con: sqlite3.Connection, child_id: str, skill_id: str,
                   success: bool, session_id: str | None = None,
                   lang: str = "fr") -> dict[str, Any]:
    """Met à jour la maîtrise + programme la révision espacée + détecte
    l'accélération (flambée) et le besoin de pause (anti-frustration)."""
    if q_one(con, "SELECT id FROM skills WHERE id = ?", (skill_id,)) is None:
        raise ValueError("unknown_skill")

    row = q_one(con, "SELECT * FROM mastery WHERE child_id = ? AND skill_id = ?", (child_id, skill_id))
    mastery = float(row["mastery"]) if row else 0.0
    ease = float(row["ease"]) if row else 2.5
    interval_h = float(row["interval_h"]) if row else 1.0
    streak = int(row["streak"]) if row else 0
    attempts = int(row["attempts"]) if row else 0
    before = mastery
    attempts += 1

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
        """INSERT INTO mastery (child_id, skill_id, mastery, ease, interval_h, streak, attempts, next_review_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(child_id, skill_id) DO UPDATE SET
             mastery = excluded.mastery, ease = excluded.ease, interval_h = excluded.interval_h,
             streak = excluded.streak, attempts = excluded.attempts,
             next_review_at = excluded.next_review_at, updated_at = excluded.updated_at""",
        (child_id, skill_id, mastery, ease, interval_h, streak, attempts, next_review, iso()),
    )

    audit(
        con, "learning.outcome", child_id=child_id, actor="child",
        payload={"skill_id": skill_id, "success": success,
                 "mastery_before": round(before, 2), "mastery_after": round(mastery, 2)},
    )

    # 🌬️ Anti-frustration : échecs d'affilée → pause respiration proposée
    consec_fails = 0
    suggest_break = False
    if session_id:
        if success:
            con.execute("UPDATE sessions SET consec_fails = 0 WHERE id = ?", (session_id,))
        else:
            con.execute("UPDATE sessions SET consec_fails = consec_fails + 1 WHERE id = ?", (session_id,))
        srow = q_one(con, "SELECT consec_fails FROM sessions WHERE id = ?", (session_id,))
        consec_fails = int(srow["consec_fails"]) if srow else 0
        suggest_break = (not success) and consec_fails >= BREAK_SUGGEST_AFTER and consec_fails % BREAK_SUGGEST_AFTER == 0
        if suggest_break:
            audit(con, "wellbeing.break_suggested", child_id=child_id,
                  payload={"session_id": session_id, "consec_fails": consec_fails})

    # 🏆 Jalon franchi
    accelerated = False
    mastered_now = before < MASTERY_THRESHOLD <= mastery
    if mastered_now:
        skill = q_one(con, "SELECT label, emoji FROM skills WHERE id = ?", (skill_id,))
        audit(con, "learning.mastery_reached", child_id=child_id, payload={"skill_id": skill_id})
        notify(con, "learning.milestone",
               {"skill_id": skill_id, "label": skill["label"] if skill else skill_id,
                "emoji": skill["emoji"] if skill else "⭐"})
        # 🚀 ACCÉLÉRATION : validée du premier coup → on sert vite, on sert haut
        accelerated = attempts <= ACCEL_MAX_ATTEMPTS and ease >= 2.5
        if accelerated:
            audit(con, "learning.acceleration", child_id=child_id,
                  payload={"skill_id": skill_id, "attempts": attempts})
            notify(con, "learning.acceleration",
                   {"skill_id": skill_id, "attempts": attempts,
                    "label": skill["label"] if skill else skill_id})

    return {
        "skill_id": skill_id,
        "mastery": round(mastery, 2),
        "streak": streak,
        "ease": round(ease, 2),
        "interval_h": round(interval_h, 1),
        "next_review_at": next_review,
        "mastered": mastery >= MASTERY_THRESHOLD,
        "mastered_now": mastered_now,
        "accelerated": accelerated,
        "consec_fails": consec_fails,
        "suggest_break": suggest_break,
    }


# ------------------------------------------------------------------ vues parents

def skills_overview(con: sqlite3.Connection, child_id: str, lang: str = "fr") -> list[dict[str, Any]]:
    """Vue compacte : toutes les compétences avec maîtrise + statut de déblocage."""
    lang = norm_lang(lang)
    mmap = mastery_map(con, child_id)
    rows = q_all(
        con,
        """SELECT s.*, COALESCE(m.streak, 0) AS m_streak, m.next_review_at
           FROM skills s LEFT JOIN mastery m ON m.skill_id = s.id AND m.child_id = ?
           ORDER BY s.domain, s.level, s.ord_i""",
        (child_id,),
    )
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "ord": r["ord_i"], "domain": r["domain"],
            "domain_label": domain_name(r["domain"], lang),
            "level": int(r["level"]),
            "label": skill_name(r, lang), "emoji": r["emoji"],
            "mastery": round(mmap.get(r["id"], 0.0), 2),
            "streak": int(r["m_streak"]),
            "status": skill_status(con, r["id"], mmap),
            "mastered": mmap.get(r["id"], 0.0) >= MASTERY_THRESHOLD,
            "next_review_at": r["next_review_at"],
        })
    return out


def skill_tree(con: sqlite3.Connection, child_id: str, lang: str = "fr") -> dict[str, Any]:
    """Arbre complet par domaine — sert l'« Évaluation initiale » ET la carte du ciel."""
    lang = norm_lang(lang)
    overview = skills_overview(con, child_id, lang)
    domains: dict[str, dict[str, Any]] = {}
    for s in overview:
        d = domains.setdefault(s["domain"], {"domain": s["domain"], "domain_label": s["domain_label"], "skills": []})
        d["skills"].append(s)
    counts = {"mastered": sum(1 for s in overview if s["status"] == "mastered"),
              "unlocked": sum(1 for s in overview if s["status"] == "unlocked"),
              "locked": sum(1 for s in overview if s["status"] == "locked")}
    return {"lang": lang, "domains": list(domains.values()), "counts": counts, "total": len(overview)}


def set_mastery_bulk(con: sqlite3.Connection, child_id: str, skill_ids: list[str],
                     action: str) -> dict[str, Any]:
    """Évaluation initiale pilotée par les parents :
    - action "mastered" : l'enfant sait déjà → compétence validée (avec tous
      ses ancêtres, automatiquement : déclarer « compter jusqu'à 20 » valide
      la chaîne 1→3→5→10→20).
    - action "reset" : à retravailler → maîtrise remise à zéro.
    Chaque changement est audité (transparence totale).
    """
    if action not in ("mastered", "reset"):
        raise ValueError("action invalide (mastered|reset).")
    known = {r["id"] for r in q_all(con, "SELECT id FROM skills")}
    targets = [sid for sid in dict.fromkeys(skill_ids) if sid in known]
    if not targets and skill_ids:
        raise ValueError("compétences inconnues.")

    updated: list[str] = []
    auto: list[str] = []

    def _mark(sid: str, is_auto: bool) -> None:
        if action == "mastered":
            row = q_one(con, "SELECT mastery FROM mastery WHERE child_id = ? AND skill_id = ?", (child_id, sid))
            if row and float(row["mastery"]) >= MASTERY_THRESHOLD:
                return
            con.execute(
                """INSERT INTO mastery (child_id, skill_id, mastery, ease, interval_h, streak, attempts, next_review_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(child_id, skill_id) DO UPDATE SET
                     mastery = 1.0, ease = 2.5, interval_h = 48.0,
                     next_review_at = excluded.next_review_at, updated_at = excluded.updated_at""",
                (child_id, sid, 1.0, 2.5, 48.0, 0, 0,
                 iso(utcnow() + timedelta(hours=48)), iso()),
            )
            audit(con, "parent.mastery_set", child_id=child_id, actor="parent",
                  payload={"skill_id": sid, "action": "mastered", "auto": is_auto})
            (auto if is_auto else updated).append(sid)
        else:  # reset
            con.execute("DELETE FROM mastery WHERE child_id = ? AND skill_id = ?", (child_id, sid))
            audit(con, "parent.mastery_set", child_id=child_id, actor="parent",
                  payload={"skill_id": sid, "action": "reset", "auto": is_auto})
            (auto if is_auto else updated).append(sid)

    for sid in targets:
        _mark(sid, False)
        if action == "mastered":
            # Valide récursivement tous les ancêtres : la chaîne est cohérente.
            stack = list(_prereqs(con, sid))
            seen: set[str] = set()
            while stack:
                p = stack.pop()
                if p in seen:
                    continue
                seen.add(p)
                _mark(p, True)
                stack.extend(_prereqs(con, p))

    if updated or auto:
        notify(con, "parent.evaluation",
               {"child_id": child_id, "action": action, "count": len(updated) + len(auto)})
    return {"updated": updated, "auto": auto, "action": action}
