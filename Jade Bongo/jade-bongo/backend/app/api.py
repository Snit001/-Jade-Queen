"""API REST de Jade Bɔngɔ́ (FastAPI) — v2.0 « plafond ouvert » : trilingue,
graphe sans limite d'âge, accélération, évaluation initiale, profils d'adaptation.

Périmètres de sécurité :
- /api/identity/*, /api/children, /api/age, /api/health → public (payload minimal, aucune donnée sensible)
- /api/session/*, /api/learning/*, /api/mentor/* → jeton de session enfant (via identification)
- /api/parent/*, /api/command/* → jeton parent (via PIN)

Multi-enfants : chaque enfant a son âge-moteur, ses questions, sa progression,
ses verrous et ses limites — parfaitement isolés des autres.
Note transactionnelle : les exceptions HTTP sont levées APRÈS commit, afin que
verrous, vetos et audits soient TOUJOURS persistés — même en cas d'erreur.
"""
from __future__ import annotations

from typing import Any, Callable, TypeVar

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from . import curriculum, llmgateway, parental, portier, wellbeing
from .audit import mark_notifications_read, recent_audit
from .age import compute_age
from .db import q_all, q_one, session as db_session
from .strings import norm_lang

router = APIRouter(prefix="/api")
T = TypeVar("T")


def _tx(fn: Callable[[Any], T]) -> T:
    """Exécute fn(con) dans une transaction ; propage le résultat après commit."""
    with db_session() as con:
        return fn(con)


def resolve_child_id(child_id: str | None) -> str:
    """Enfant explicite (multi-profils) ou premier profil par défaut."""
    def work(con: Any) -> str:
        if child_id:
            row = q_one(con, "SELECT id FROM children WHERE id = ?", (child_id,))
            if row is None:
                raise HTTPException(404, "Enfant inconnu.")
            return str(row["id"])
        row = q_one(con, "SELECT id FROM children ORDER BY created_at LIMIT 1")
        if row is None:
            raise HTTPException(500, "Aucun profil enfant initialisé.")
        return str(row["id"])
    return _tx(work)


def require_session_token(token: str) -> dict[str, Any]:
    """Valide le jeton et renvoie le statut — avec child_id de la session."""
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


class ChildIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)
    dob: str
    emoji: str = "⭐"
    lang: str = "fr"                                # fr | en | es — gouverne tout le profil


class ChildPatch(BaseModel):
    lang: str | None = None
    attention: str | None = None
    speech_support: bool | None = None
    display_name: str | None = None
    emoji: str | None = None
    dob: str | None = None


class MasteryIn(BaseModel):
    skill_ids: list[str] = Field(min_length=1, max_length=100)
    action: str = "mastered"  # mastered | reset


# ------------------------------------------------------------------- public

@router.get("/health")
def health() -> dict[str, Any]:
    n = _tx(lambda con: int(q_one(con, "SELECT COUNT(*) AS n FROM skills")["n"]))
    return {"status": "ok", "service": "Jade Bɔngɔ́", "version": "2.1.0",
            "skills_total": n, "langs": ["fr", "en", "es"]}


@router.get("/age")
def age_public(child_id: str | None = None) -> dict[str, Any]:
    cid = resolve_child_id(child_id)
    row = _tx(lambda con: q_one(con, "SELECT dob FROM children WHERE id = ?", (cid,)))
    profile = _tx(lambda con: wellbeing.child_profile(con, cid))
    from datetime import date as _d
    age = compute_age(dob=_d.fromisoformat(row["dob"])).as_dict()
    age["child"] = profile  # langue + profil d'adaptation (rien de sensible)
    # Exposition minimale : rien de personnel sans identification.
    age["policy"] = {
        "session_max_minutes": age["policy"]["session_max_minutes"],
        "identification": age["policy"]["identification"],
        "requires_parent_present": age["policy"]["requires_parent_present"],
    }
    return age


@router.get("/children")
def children_public() -> list[dict[str, str]]:
    """Sélecteur de profils (écran d'accueil) : prénom + emoji + LANGUE du profil
    (rien de sensible — la langue doit être connue AVANT identification pour
    traduire toute l'interface de l'enfant concerné)."""
    rows = _tx(lambda con: q_all(con, "SELECT id, display_name, emoji, lang FROM children ORDER BY created_at"))
    return [{"id": r["id"], "display_name": r["display_name"], "emoji": r["emoji"], "lang": r["lang"]} for r in rows]


# ------------------------------------------------------------------- identification

@router.post("/identity/challenge")
def identity_challenge(child_id: str | None = None) -> Any:
    cid = resolve_child_id(child_id)
    error: HTTPException | None = None
    payload: Any = None

    def work(con: Any) -> None:
        nonlocal payload, error
        try:
            payload = portier.create_challenge(con, cid)
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
def learning_step(token: str, lang: str | None = None) -> dict[str, Any]:
    """Prochaine étape — localisée. La langue effective = paramètre `lang`
    (appareil de la famille multilingue) ou, à défaut, la langue du profil."""
    session = require_session_token(token)

    def work(con: Any) -> dict[str, Any]:
        profile = wellbeing.child_profile(con, session["child_id"])
        effective_lang = norm_lang(lang) if lang else profile["lang"]
        step = curriculum.next_step(con, session["child_id"], effective_lang)
        step["child"] = profile
        step["child"]["lang"] = effective_lang
        return step

    return _tx(work)


@router.post("/learning/outcome")
def learning_outcome(body: OutcomeIn) -> dict[str, Any]:
    session = require_session_token(body.token)

    def work(con: Any) -> dict[str, Any]:
        try:
            return curriculum.record_outcome(
                con, session["child_id"], body.skill_id, body.success,
                session_id=session["session_id"],
                lang=wellbeing.child_profile(con, session["child_id"])["lang"],
            )
        except ValueError:
            raise HTTPException(404, "Compétence inconnue.") from None

    return _tx(work)


@router.get("/mentor/encourage")
def mentor_encourage(token: str, mood: str = "success") -> dict[str, Any]:
    session = require_session_token(token)

    def who(con: Any) -> tuple[str, str]:
        row = q_one(con, "SELECT display_name, lang FROM children WHERE id = ?", (session["child_id"],))
        return (row["display_name"], row["lang"]) if row else ("", "fr")

    name, lang = _tx(who)
    kind = mood if mood in ("success", "retry", "session_end", "acceleration", "suggest_break") else "success"
    return llmgateway.encourage(kind, name=name, lang=lang)


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


@router.get("/parent/children")
def parent_children(authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
    require_parent_token(authorization)
    return _tx(parental.children_list)


@router.post("/parent/children")
def parent_child_create(body: ChildIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_parent_token(authorization)

    def work(con: Any) -> dict[str, Any]:
        try:
            return parental.create_child(con, body.display_name, body.dob, body.emoji, body.lang)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    return _tx(work)


@router.patch("/parent/children/{child_id}")
def parent_child_patch(child_id: str, body: ChildPatch,
                       authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Réglages d'adaptation : langue des cours, profil d'attention, soutien langage."""
    require_parent_token(authorization)

    def work(con: Any) -> dict[str, Any]:
        try:
            return parental.patch_child(con, child_id, body.model_dump(exclude_none=True))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    return _tx(work)


@router.delete("/parent/children/{child_id}")
def parent_child_delete(child_id: str,
                        authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Suppression définitive d'un profil enfant + toutes ses données (cascade)."""
    require_parent_token(authorization)

    def work(con: Any) -> dict[str, Any]:
        try:
            return parental.delete_child(con, child_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    return _tx(work)


@router.get("/parent/tree")
def parent_tree(child_id: str | None = None, lang: str | None = None,
                authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """L'arbre complet des compétences (carte du ciel + évaluation initiale)."""
    require_parent_token(authorization)
    cid = resolve_child_id(child_id)
    return _tx(lambda con: parental.tree(con, cid, norm_lang(lang) if lang else
                                         wellbeing.child_profile(con, cid)["lang"]))


@router.post("/parent/mastery")
def parent_mastery(body: MasteryIn, child_id: str | None = None,
                   authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Évaluation initiale : « elle sait déjà ! » — marque les compétences
    (avec la chaîne des prérequis, automatiquement) ou les remet à zéro."""
    require_parent_token(authorization)
    cid = resolve_child_id(child_id)

    def work(con: Any) -> dict[str, Any]:
        try:
            return parental.mastery_bulk(con, cid, body.skill_ids, body.action)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    return _tx(work)


@router.get("/parent/overview")
def parent_overview(child_id: str | None = None, lang: str | None = None,
                    authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_parent_token(authorization)
    cid = resolve_child_id(child_id)
    return _tx(lambda con: parental.overview(
        con, cid, norm_lang(lang) if lang else wellbeing.child_profile(con, cid)["lang"]))


@router.get("/parent/audit")
def parent_audit(limit: int = 100, type_prefix: str | None = None,
                 authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
    require_parent_token(authorization)
    return _tx(lambda con: recent_audit(con, limit=min(limit, 500), type_prefix=type_prefix))


@router.get("/parent/questions")
def parent_questions(child_id: str | None = None,
                     authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
    require_parent_token(authorization)
    cid = resolve_child_id(child_id)
    return _tx(lambda con: parental.questions_list(con, cid))


@router.post("/parent/questions")
def parent_question_create(body: QuestionIn, child_id: str | None = None,
                           authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_parent_token(authorization)
    cid = resolve_child_id(child_id)

    def work(con: Any) -> dict[str, Any]:
        try:
            return parental.question_create(con, cid, body.model_dump())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    return _tx(work)


@router.patch("/parent/questions/{question_id}")
def parent_question_update(question_id: str, body: QuestionPatch, child_id: str | None = None,
                           authorization: str | None = Header(default=None)) -> dict[str, str]:
    require_parent_token(authorization)
    cid = resolve_child_id(child_id)

    def work(con: Any) -> str:
        try:
            parental.question_update(con, cid, question_id, body.model_dump(exclude_none=True))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        return "updated"

    return {"status": _tx(work)}


@router.post("/parent/unlock")
def parent_unlock(child_id: str | None = None,
                  authorization: str | None = Header(default=None)) -> dict[str, str]:
    require_parent_token(authorization)
    cid = resolve_child_id(child_id)
    _tx(lambda con: parental.unlock(con, cid))
    return {"status": "unlocked"}


@router.patch("/parent/policy")
def parent_policy(body: PolicyPatch, child_id: str | None = None,
                  authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_parent_token(authorization)
    cid = resolve_child_id(child_id)

    def work(con: Any) -> dict[str, Any]:
        try:
            return parental.update_policy(con, cid, body.model_dump(exclude_none=True))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    return _tx(work)


@router.post("/parent/consents")
def parent_consent(body: ConsentIn, authorization: str | None = Header(default=None)) -> dict[str, str]:
    require_parent_token(authorization)

    def work(con: Any) -> str:
        try:
            parental.consent_set(con, resolve_child_id(None), body.scope, body.granted)
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
def command_mission(child_id: str | None = None,
                    authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_parent_token(authorization)
    from .main import BOOT_AT

    cid = resolve_child_id(child_id)
    return _tx(lambda con: parental.command_mission(con, cid, BOOT_AT))
