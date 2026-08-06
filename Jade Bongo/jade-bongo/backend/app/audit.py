"""audit-service — journal append-only (transparence totale, conformité RGPD).

Règle Prompt Maître : chaque interaction avec Jade est auditable par ses
responsables légaux. Aucune suppression, aucune modification — insertion seule.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from .db import dumps, iso, q_all


def audit(
    con: sqlite3.Connection,
    type_: str,
    *,
    child_id: str | None = None,
    actor: str = "system",
    payload: dict[str, Any] | None = None,
) -> None:
    con.execute(
        "INSERT INTO audit_events (ts, child_id, actor, type, payload_json) VALUES (?,?,?,?,?)",
        (iso(), child_id, actor, type_, dumps(payload or {})),
    )


def notify(con: sqlite3.Connection, kind: str, payload: dict[str, Any] | None = None) -> None:
    """Notification parentale : verrou, limite atteinte, jalon franchi…"""
    con.execute(
        "INSERT INTO notifications (kind, payload_json, created_at) VALUES (?,?,?)",
        (kind, dumps(payload or {}), iso()),
    )


def recent_audit(con: sqlite3.Connection, limit: int = 100, type_prefix: str | None = None) -> list[dict[str, Any]]:
    if type_prefix:
        rows = q_all(
            con,
            "SELECT * FROM audit_events WHERE type LIKE ? ORDER BY id DESC LIMIT ?",
            (f"{type_prefix}%", limit),
        )
    else:
        rows = q_all(con, "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,))
    import json

    return [
        {
            "id": r["id"],
            "ts": r["ts"],
            "actor": r["actor"],
            "type": r["type"],
            "payload": json.loads(r["payload_json"]),
        }
        for r in rows
    ]


def unread_notifications(con: sqlite3.Connection) -> list[dict[str, Any]]:
    import json

    rows = q_all(con, "SELECT * FROM notifications WHERE read_at IS NULL ORDER BY id DESC LIMIT 50")
    return [
        {"id": r["id"], "kind": r["kind"], "payload": json.loads(r["payload_json"]), "created_at": r["created_at"]}
        for r in rows
    ]


def mark_notifications_read(con: sqlite3.Connection) -> int:
    cur = con.execute("UPDATE notifications SET read_at = ? WHERE read_at IS NULL", (iso(),))
    return cur.rowcount
