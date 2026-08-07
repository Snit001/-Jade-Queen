"""Jade Bɔngɔ́ — serveur principal.

Initialise la base, applique le seed idempotent, monte l'API et les interfaces
statiques (app enfant, dashboard parents, command center).
Production : uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import FRONTEND_DIR
from .db import connect, init_db, iso
from .seed import seed

BOOT_AT = iso()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Jade Bɔngɔ́",
        version="2.1.0",
        description="Programme d'éducation dédié à Jade Queen MBO — identification, parcours étape par étape SANS plafond d'âge, trilingue (fr/en/es), bien-être, transparence parents.",
    )

    # Initialisation base + seed (idempotent)
    con = connect()
    try:
        init_db(con)
        seed(con)
    finally:
        con.close()

    app.include_router(router)

    @app.middleware("http")
    async def security_headers(request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(Exception)
    async def unhandled(request, exc):  # type: ignore[no-untyped-def]
        return JSONResponse(status_code=500, content={"detail": "Erreur interne."})

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    return app


app = create_app()
