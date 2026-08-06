"""API REST de Jade Bɔngɔ́ (FastAPI).

Périmètres de sécurité :
- /api/identity/*, /api/age, /api/health  → public (mais aucune donnée profil)
- /api/session/*, /api/learning/*, /api/mentor/* → jeton de session enfant (via identification)
- /api/parent/*, /api/command/* → jeton parent (via PIN)

Note transactionnelle : toute exception HTTP est levée APRÈS la fermeture du
contexte de base de données, afin que les écritures (verrous, vetos, audits)
soient TOUJOURS persistées — y compris en cas d'erreur.
"""
from __future__ import annotations

from typing import Any, Callable, TypeVar

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from . import curriculum, llmgateway, parental, portier, wellbeing
from .audit import mark_notifications_read, recent_audit
from .age import compute_age
from .db import q_one, session as db_session

router = APIRouter(prefix="/api")
T = TypeVar("T")


def _tx(fn: Callable[[Any], T]) -> T:
    """Exécute fn(con) dans une transaction ; propage le résultat après commit."""
    with db_session() as con:
        return fn(con)


def get_child_id() -> str:
    row = _tx(lambda con: q_one(con, "SELECT id FROM children LIMIT 1"))
    if row is None:
        raise HTTPException(500, "Profil enfant non initialisé.")
    return str(row["id"])


def require_session_token(token: str) -> dict[str, Any]:
    if not token:
        raise HTTPException(401, "Jeton de session requis (identification d'abord).")
    status = _tx(lambda con: wellbeing.session_status(con, token))
    if status is None:
        raise HTTPException(401, "Session inconnue.")
    if status["status"] == "veto":
        raise HTTPException(403, {"reason": "veto", "message": "Pause bien-être : la session est terminée. 🌙"})
    if status["status"] != "active":
        raise HTTPException(403, "Session terminée.")
    return status


def require_parent_token(authorization: str | None) -> None:
    raw = authorization.replace("Bearer ", "", 1).strip() if authorization else None
    try:
        _tx(lambda con: parental.require_parent(con, raw))
    except parental.Unauthorized:
        raise HTTPException(401, "Authentification parent requise.") from None


# ------------------------------------------------------------------- modèles

class AnswerIn(BaseModel):
    challenge_id: str
    question_id: str
    answer: str = ""
    parent_validated: bool = False


class TokenIn(BaseModel):
    token: str


class OutcomeIn(BaseModel):
    token: str
    skill_id: str
    success: bool


class PinIn(BaseModel):
    pin: str


class QuestionIn(BaseModel):
    modality: str
    text: str
    emoji: str = "🔐"
    options: list[dict[str, Any]] | None = None
    accepted_answers: list[str] = Field(min_length=1)
    min_age_months: int = 0


class QuestionPatch(BaseModel):
    text: str | None = None
    accepted_answers: list[str] | None = None
    active: bool | None = None


class PolicyPatch(BaseModel):
    session_max_minutes: int | None = None
    sessions_per_day_max: int | None = None


class ConsentIn(BaseModel):
    scope: str
    granted: bool


# ------------------------------------------------------------------- public

@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "Jade Bɔngɔ́", "version": "1.0.0"}


@router.get("/age")
def age_public() -> dict[str, Any]:
    age = compute_age().as_dict()
    # Exposition minimale : pas de données personnelles sans identification.
    age["policy"] = {
        "session_max_minutes": age["policy"]["session_max_minutes"],
        "identification": age["policy"]["identification"],
        "requires_parent_present": age["policy"]["requires_parent_present"],
    }
    return age


# ------------------------------------------------------------------- identification

@router.post("/identity/challenge")
def identity_challenge() -> Any:
    child_id = get_child_id()
    error: HTTPException | None = None
    payload: Any = None

    def work(con: Any) -> None:
        nonlocal payload, error
        try:
            payload = portier.create_challenge(con, child_id)
        except portier.Locked as exc:
            error = HTTPException(423, {"reason": "locked", "locked_until": exc.locked_until})
        except portier.BadRequest as exc:
            error = HTTPException(400, str(exc))

    _tx(work)
    if error:
        raise error
    return payload


@router.post("/identity/answer")
def identity_answer(body: AnswerIn) -> Any:
    error: HTTPException | None = None
    payload: Any = None

    def work(con: Any) -> None:
        nonlocal payload, error
        try:
            result = portier.submit_answer(
                con, body.challenge_id, body.question_id, body.answer,
                parent_validated=body.parent_validated,
            )
            if result.get("locked"):
                error = HTTPException(423, {"reason": "locked", "locked_until": result.get("locked_until")})
            else:
                payload = result
        except portier.Locked as exc:
            error = HTTPException(423, {"reason": "locked", "locked_until": exc.locked_until})
        except portier.BadRequest as exc:
            error = HTTPException(400, str(exc))

    _tx(work)  # le verrou est PERSISTÉ avant toute levée d'exception
    if error:
        raise error
    return payload


# ------------------------------------------------------------------- session

@router.get("/session/status")
def session_status(token: str) -> dict[str, Any]:
    status = _tx(lambda con: wellbeing.session_status(con, token))
    if status is None:
        raise HTTPException(401, "Session inconnue.")
    return status


@router.post("/session/end")
def session_end(body: TokenIn) -> dict[str, Any]:
    result = _tx(lambda con: wellbeing.end_session(con, body.token))
    if result is None:
        raise HTTPException(401, "Session inconnue.")
    return result


# ------------------------------------------------------------------- apprentissage

@router.get("/learning/step")
def learning_step(token: str) -> dict[str, Any]:
    require_session_token(token)
    child_id = get_child_id()
    return _tx(lambda con: curriculum.next_step(con, child_id))


@router.post("/learning/outcome")
def learning_outcome(body: OutcomeIn) -> dict[str, Any]:
    require_session_token(body.token)
    child_id = get_child_id()

    def work(con: Any) -> dict[str, Any]:
        try:
            return curriculum.record_outcome(con, child_id, body.skill_id, body.success)
        except ValueError:
            raise HTTPException(404, "Compétence inconnue.") from None

    return _tx(work)


@router.get("/mentor/encourage")
def mentor_encourage(token: str, mood: str = "success") -> dict[str, Any]:
    require_session_token(token)
    return llmgateway.encourage(mood if mood in ("success", "retry", "session_end") else "success")


# ------------------------------------------------------------------- parents

@router.post("/parent/login")
def parent_login(body: PinIn) -> dict[str, Any]:
    error: HTTPException | None = None
    payload: dict[str, Any] = {}

    def work(con: Any) -> None:
        nonlocal payload, error
        try:
            payload = parental.login(con, body.pin)
        except parental.Unauthorized:
            error = HTTPException(403, "PIN incorrect.")

    _tx(work)  # l'échec est audité AVANT la levée de l'erreur
    if error:
        raise error
    return payload


@router.get("/parent/overview")
def parent_overview(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_parent_token(authorization)
    child_id = get_child_id()
    return _tx(lambda con: parental.overview(con, child_id))


@router.get("/parent/audit")
def parent_audit(limit: int = 100, type_prefix: str | None = None,
                 authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
    require_parent_token(authorization)
    return _tx(lambda con: recent_audit(con, limit=min(limit, 500), type_prefix=type_prefix))


@router.get("/parent/questions")
def parent_questions(authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
    require_parent_token(authorization)
    child_id = get_child_id()
    return _tx(lambda con: parental.questions_list(con, child_id))


@router.post("/parent/questions")
def parent_question_create(body: QuestionIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_parent_token(authorization)
    child_id = get_child_id()

    def work(con: Any) -> dict[str, Any]:
        try:
            return parental.question_create(con, child_id, body.model_dump())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    return _tx(work)


@router.patch("/parent/questions/{question_id}")
def parent_question_update(question_id: str, body: QuestionPatch,
                           authorization: str | None = Header(default=None)) -> dict[str, str]:
    require_parent_token(authorization)
    child_id = get_child_id()

    def work(con: Any) -> str:
        try:
            parental.question_update(con, child_id, question_id, body.model_dump(exclude_none=True))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        return "updated"

    return {"status": _tx(work)}


@router.post("/parent/unlock")
def parent_unlock(authorization: str | None = Header(default=None)) -> dict[str, str]:
    require_parent_token(authorization)
    child_id = get_child_id()
    _tx(lambda con: parental.unlock(con, child_id))
    return {"status": "unlocked"}


@router.patch("/parent/policy")
def parent_policy(body: PolicyPatch, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_parent_token(authorization)
    child_id = get_child_id()

    def work(con: Any) -> dict[str, Any]:
        try:
            return parental.update_policy(con, child_id, body.model_dump(exclude_none=True))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    return _tx(work)


@router.post("/parent/consents")
def parent_consent(body: ConsentIn, authorization: str | None = Header(default=None)) -> dict[str, str]:
    require_parent_token(authorization)
    child_id = get_child_id()

    def work(con: Any) -> str:
        try:
            parental.consent_set(con, child_id, body.scope, body.granted)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        return "updated"

    return {"status": _tx(work)}


@router.post("/parent/notifications/read")
def parent_notifications_read(authorization: str | None = Header(default=None)) -> dict[str, int]:
    require_parent_token(authorization)
    return {"marked": _tx(mark_notifications_read)}


# ------------------------------------------------------------------- command center

@router.get("/command/mission")
def command_mission(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_parent_token(authorization)
    from .main import BOOT_AT

    child_id = get_child_id()
    return _tx(lambda con: parental.command_mission(con, child_id, BOOT_AT))
