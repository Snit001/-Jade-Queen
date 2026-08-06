"""Couche données — schéma complet du schéma « jade » (cf. ARCHITECTURE_JADE_BONGO.md §5).

MVP intégré : SQLite embarqué (WAL). Production : PostgreSQL, mêmes tables,
RLS activée, PII chiffrée via Vault Transit. Interface hexagonale : les services
ne manipulent que des fonctions de ce module → migration sans refonte métier.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from .config import DB_PATH

SCHEMA = """
-- 👶 Enfant (un seul profil sur cette plateforme dédiée)
CREATE TABLE IF NOT EXISTS children (
  id           TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  dob          TEXT NOT NULL,
  phase        TEXT NOT NULL DEFAULT 'PHASE_1',
  created_at   TEXT NOT NULL
);

-- 🔐 Questions d'identification (réponses hachées PBKDF2 — jamais en clair)
CREATE TABLE IF NOT EXISTS identity_questions (
  id                 TEXT PRIMARY KEY,
  child_id           TEXT NOT NULL REFERENCES children(id),
  modality           TEXT NOT NULL,             -- 'voice' | 'image_tap'
  prompt_json        TEXT NOT NULL,             -- {text, emoji}
  options_json       TEXT,                      -- image_tap : [{id, label, emoji}]
  answer_hashes_json TEXT NOT NULL,             -- ["salt$hash", ...] variantes acceptées
  min_age_months     INTEGER NOT NULL DEFAULT 0,
  active             INTEGER NOT NULL DEFAULT 1,
  version            INTEGER NOT NULL DEFAULT 1,
  created_at         TEXT NOT NULL
);

-- 🎫 Sessions d'identification en cours (challenges)
CREATE TABLE IF NOT EXISTS challenges (
  id                TEXT PRIMARY KEY,
  child_id          TEXT NOT NULL REFERENCES children(id),
  question_ids_json TEXT NOT NULL,
  results_json      TEXT NOT NULL DEFAULT '{}',
  failures          INTEGER NOT NULL DEFAULT 0,
  status            TEXT NOT NULL DEFAULT 'open',  -- open | completed | failed | locked
  created_at        TEXT NOT NULL
);

-- 🔒 Verrouillage anti-intrusion (compteur global + date de fin de verrou)
CREATE TABLE IF NOT EXISTS locks (
  child_id     TEXT PRIMARY KEY,
  failed_count INTEGER NOT NULL DEFAULT 0,
  locked_until TEXT
);

-- 🎮 Sessions de jeu (éphémères, scope minimal, veto possible)
CREATE TABLE IF NOT EXISTS sessions (
  id         TEXT PRIMARY KEY,
  child_id   TEXT NOT NULL REFERENCES children(id),
  token      TEXT UNIQUE NOT NULL,
  started_at TEXT NOT NULL,
  max_seconds INTEGER NOT NULL,
  status     TEXT NOT NULL DEFAULT 'active',        -- active | ended | ended_veto | cancelled
  day        TEXT NOT NULL,
  ended_at   TEXT
);

-- 🧩 Graphe de compétences (étape par étape, jamais de saut)
CREATE TABLE IF NOT EXISTS skills (
  id         TEXT PRIMARY KEY,
  ord_i      INTEGER NOT NULL,
  domain     TEXT NOT NULL,
  label      TEXT NOT NULL,
  emoji      TEXT NOT NULL DEFAULT '⭐',
  min_phase  TEXT NOT NULL DEFAULT 'PHASE_1',
  game_json  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS skill_edges (
  from_skill TEXT NOT NULL REFERENCES skills(id),
  to_skill   TEXT NOT NULL REFERENCES skills(id),
  PRIMARY KEY (from_skill, to_skill)
);

-- ⭐ Maîtrise + répétition espacée (SM-2 : ease, intervalle, streak)
CREATE TABLE IF NOT EXISTS mastery (
  child_id       TEXT NOT NULL,
  skill_id       TEXT NOT NULL,
  mastery        REAL NOT NULL DEFAULT 0,
  ease           REAL NOT NULL DEFAULT 2.5,
  interval_h     REAL NOT NULL DEFAULT 1,
  streak         INTEGER NOT NULL DEFAULT 0,
  next_review_at TEXT,
  updated_at     TEXT,
  PRIMARY KEY (child_id, skill_id)
);

-- ⏱ Bien-être : compteur d'écran journalier (veto)
CREATE TABLE IF NOT EXISTS screen_time_ledger (
  child_id TEXT NOT NULL,
  day      TEXT NOT NULL,
  seconds  INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (child_id, day)
);

-- 📜 Consentements RGPD versionnés (révocables à tout moment)
CREATE TABLE IF NOT EXISTS consents (
  scope      TEXT PRIMARY KEY,
  version    INTEGER NOT NULL DEFAULT 1,
  granted_at TEXT,
  revoked_at TEXT
);

-- 🔔 Notifications aux parents (verrous, limites, jalons)
CREATE TABLE IF NOT EXISTS notifications (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  kind        TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at  TEXT NOT NULL,
  read_at     TEXT
);

-- ⚙ Politique d'âge : surcharges parentales (autorité finale)
CREATE TABLE IF NOT EXISTS policy_overrides (
  child_id       TEXT PRIMARY KEY,
  overrides_json TEXT NOT NULL DEFAULT '{}',
  updated_at     TEXT
);

-- 🧾 Audit append-only : TOUT ce qui touche Jade (transparence totale)
CREATE TABLE IF NOT EXISTS audit_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          TEXT NOT NULL,
  child_id    TEXT,
  actor       TEXT NOT NULL DEFAULT 'system',   -- system | child | parent
  type        TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}'
);

-- 🔑 Jetons parents (dashboard / command center)
CREATE TABLE IF NOT EXISTS parent_tokens (
  token      TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or utcnow()).isoformat()


def connect(path: str | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(path or DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


@contextmanager
def session() -> Iterator[sqlite3.Connection]:
    """Contexte transactionnel unique par requête."""
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def q_one(con: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    return con.execute(sql, params).fetchone()


def q_all(con: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return list(con.execute(sql, params).fetchall())


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def loads(raw: str | None, default: Any = None) -> Any:
    if raw is None:
        return default
    return json.loads(raw)
