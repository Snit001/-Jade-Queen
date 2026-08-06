"""Jade Bɔngɔ́ — backend complet (FastAPI).

Cartographie avec jade-bongo/ARCHITECTURE_JADE_BONGO.md :
- portier.py        → portier-service (identification obligatoire, verrous, jetons)
- age.py            → age-calibration-service (âge exact 03/09/2022, phases, politiques)
- curriculum.py     → curriculum-service (graphe de compétences, mastery, SM-2)
- wellbeing.py      → wellbeing-service (veto temps d'écran, sessions/jour, ledger)
- parental.py       → parental-service (PIN, questions CRUD, politiques, consentements, command center)
- llmgateway.py     → llm-gateway-service (garde-fous enfant, mode local validé, connecteurs LLM)
- audit.py          → audit-service (append-only, notifications parents)
- voice             → côté navigateur (Web Speech API : STT/TTS streaming)
- security.py       → Vault-lite (PBKDF2 + pepper, jamais de clair)
- db.py             → schéma « jade » complet (SQLite ici / PostgreSQL en prod, port hexagonal)
- api.py / main.py  → exposition REST + interfaces statiques
"""
