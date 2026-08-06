"""Vault-lite : les réponses d'identification ne sont JAMAIS stockées en clair.

MVP : PBKDF2-HMAC-SHA256 (120 000 itérations) + sel aléatoire + pepper serveur.
Production (cf. architecture) : Argon2id + Vault Transit — interface identique.

Tolérance enfant : via plusieurs variantes acceptées (ex. « 3 », « trois »,
« trois ans ») + validation parentale assistée. En production, un juge
sémantique (LLM) évalue l'intention — jamais un examen, toujours un rituel.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import unicodedata

from .config import PEPPER

_ITERATIONS = 120_000
PARENT_VALIDATION_TOKEN = "__parent_validated__"


def normalize(text: str) -> str:
    """Normalisation tolérante : casse, accents, ponctuation, espaces."""
    t = unicodedata.normalize("NFD", text.strip().lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def hash_answer(answer: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac(
        "sha256", (normalize(answer) + PEPPER).encode(), bytes.fromhex(salt), _ITERATIONS
    )
    return f"{salt}${digest.hex()}"


def _check(normalized_candidate: str, stored: str) -> bool:
    salt, expected = stored.split("$", 1)
    digest = hashlib.pbkdf2_hmac(
        "sha256", (normalized_candidate + PEPPER).encode(), bytes.fromhex(salt), _ITERATIONS
    )
    return hmac.compare_digest(digest.hex(), expected)


def verify_candidate(candidate: str, stored_hashes: list[str]) -> bool:
    """Vrai si la réponse (normalisée) correspond à l'une des variantes acceptées."""
    normalized = normalize(candidate)
    if not normalized:
        return False
    return any(_check(normalized, h) for h in stored_hashes)


def new_token() -> str:
    return secrets.token_urlsafe(24)


def hash_secret(secret: str) -> str:
    """Empreinte non réversible pour PINs (comparaison constante)."""
    return hashlib.sha256((secret + PEPPER).encode()).hexdigest()


def safe_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
