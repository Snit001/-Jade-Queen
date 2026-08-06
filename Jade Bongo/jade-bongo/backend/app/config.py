"""Configuration centrale — tout est paramétrable par variables d'environnement.

Règle Prompt Maître n°5 : zéro valeur critique codée en dur en production.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
FRONTEND_DIR = BASE_DIR.parent / "frontend"                # jade-bongo/frontend/

DB_PATH: str = os.environ.get("JADE_DB_PATH", str(BASE_DIR / "jade.db"))
PEPPER: str = os.environ.get("JADE_PEPPER", "dev-pepper-change-me")
PARENT_PIN: str = os.environ.get("JADE_PARENT_PIN", "0000")

LOCK_MAX_FAILURES: int = int(os.environ.get("JADE_LOCK_MAX_FAILURES", "3"))
LOCK_MINUTES: int = int(os.environ.get("JADE_LOCK_MINUTES", "15"))

# Durée du jeton parent (dashboard) en secondes
PARENT_TOKEN_TTL: int = int(os.environ.get("JADE_PARENT_TOKEN_TTL", "7200"))
