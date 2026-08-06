"""wellbeing-service — le bien-être de Jade prime sur tout, techniquement.

- Limite de sessions par jour (politique d'âge + surcharges parentales)
- Durée maximale par session avec VETO en temps réel
- Compteur d'écran journalier (ledger)
Le veto est un pouvoir réel : la session est terminée par le système, en douceur.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from .audit import audit, notify
from .db import iso, loads, q_one, utcnow
from .security import new_token


class SessionDenied(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def today_str() -> str:
    return utcnow().date().isoformat()


def effective_policy(con: sqlite3.Connection, child_id: str, base_policy: dict[str, Any]) -> dict[str, Any]:
    """Politique d'âge fusionnée avec les surcharges parentales (bornées)."""
    row = q_one(con, "SELECT overrides_json FROM policy_overrides WHERE child_id = ?", (child_id,))
    merged = dict(base_policy)
    if row:
        overrides = loads(row["overrides_json"], {})
        if "session_max_minutes" in overrides:
            merged["session_max_minutes"] = max(1, min(int(overrides["session_max_minutes"]), 120))
        if "sessions_per_day_max" in overrides:
            merged["sessions_per_day_max"] = max(1, min(int(overrides["sessions_per_day_max"]), 10))
    return merged


def set_policy_overrides(con: sqlite3.Connection, child_id: str, overrides: dict[str, Any]) -> None:
    from .db import dumps

    con.execute(
        """INSERT INTO policy_overrides (child_id, overrides_json, updated_at) VALUES (?,?,?)
           ON CONFLICT(child_id) DO UPDATE SET overrides_json = excluded.overrides_json,
           updated_at = excluded.updated_at""",
        (child_id, dumps(overrides), iso()),
    )
    audit(con, "policy.updated", child_id=child_id, actor="parent", payload=overrides)


def sessions_today(con: sqlite3.Connection, child_id: str) -> int:
    row = q_one(
        con,
        "SELECT COUNT(*) AS n FROM sessions WHERE child_id = ? AND day = ? AND status != 'cancelled'",
        (child_id, today_str()),
    )
    return int(row["n"] if row else 0)


def ledger_seconds(con: sqlite3.Connection, child_id: str, day: str | None = None) -> int:
    row = q_one(
        con,
        "SELECT seconds FROM screen_time_ledger WHERE child_id = ? AND day = ?",
        (child_id, day or today_str()),
    )
    return int(row["seconds"] if row else 0)


def add_ledger(con: sqlite3.Connection, child_id: str, seconds: int) -> None:
    if seconds <= 0:
        return
    con.execute(
        """INSERT INTO screen_time_ledger (child_id, day, seconds) VALUES (?,?,?)
           ON CONFLICT(child_id, day) DO UPDATE SET seconds = seconds + excluded.seconds""",
        (child_id, today_str(), seconds),
    )


def can_start_session(con: sqlite3.Connection, child_id: str, policy: dict[str, Any]) -> None:
    """Lève SessionDenied si la journée de Jade est complète."""
    used = sessions_today(con, child_id)
    if used >= policy["sessions_per_day_max"]:
        notify(
            con,
            "wellbeing.daily_limit",
            {"child_id": child_id, "sessions_used": used, "cap": policy["sessions_per_day_max"]},
        )
        audit(con, "wellbeing.daily_limit", child_id=child_id, payload={"sessions_used": used})
        raise SessionDenied("daily_limit")


def issue_session(con: sqlite3.Connection, child_id: str, policy: dict[str, Any]) -> dict[str, Any]:
    max_seconds = int(policy["session_max_minutes"]) * 60
    token = new_token()
    session_id = new_token()[:12]
    con.execute(
        """INSERT INTO sessions (id, child_id, token, started_at, max_seconds, status, day)
           VALUES (?,?,?,?,?,?,?)""",
        (session_id, child_id, token, iso(), max_seconds, "active", today_str()),
    )
    audit(con, "session.started", child_id=child_id, payload={"session_id": session_id, "max_seconds": max_seconds})
    return {"token": token, "session_id": session_id, "max_seconds": max_seconds, "remaining_seconds": max_seconds}


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def get_session(con: sqlite3.Connection, token: str) -> sqlite3.Row | None:
    return q_one(con, "SELECT * FROM sessions WHERE token = ?", (token,))


def session_status(con: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    """Statut temps réel. Applique le veto si le temps est écoulé."""
    row = get_session(con, token)
    if row is None:
        return None
    status = row["status"]
    max_seconds = int(row["max_seconds"])
    elapsed = int((utcnow() - _parse(row["started_at"])).total_seconds())
    remaining = max_seconds - elapsed

    if status == "active" and remaining <= 0:
        # ⛔ VETO BIEN-ÊTRE : la session est terminée par le système.
        con.execute(
            "UPDATE sessions SET status = 'ended_veto', ended_at = ? WHERE id = ?",
            (iso(), row["id"]),
        )
        add_ledger(con, row["child_id"], max_seconds)
        audit(con, "wellbeing.veto", child_id=row["child_id"], payload={"session_id": row["id"], "max_seconds": max_seconds})
        notify(con, "wellbeing.veto", {"child_id": row["child_id"], "minutes": max_seconds // 60})
        return {
            "status": "veto",
            "remaining_seconds": 0,
            "elapsed_seconds": elapsed,
            "session_id": row["id"],
        }

    return {
        "status": status,
        "remaining_seconds": max(0, remaining),
        "elapsed_seconds": elapsed,
        "max_seconds": max_seconds,
        "session_id": row["id"],
    }


def end_session(con: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    row = get_session(con, token)
    if row is None:
        return None
    if row["status"] != "active":
        return {"status": row["status"], "session_id": row["id"]}
    elapsed = int((utcnow() - _parse(row["started_at"])).total_seconds())
    counted = min(elapsed, int(row["max_seconds"]))
    con.execute(
        "UPDATE sessions SET status = 'ended', ended_at = ? WHERE id = ?",
        (iso(), row["id"]),
    )
    add_ledger(con, row["child_id"], counted)
    audit(con, "session.ended", child_id=row["child_id"], payload={"session_id": row["id"], "seconds": counted})
    return {"status": "ended", "session_id": row["id"], "seconds": counted}
