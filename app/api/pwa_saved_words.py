"""Learner PWA dictionary bookmarks (authenticated account-owned rows).

The UIUX-003 action deliberately does not mutate course mistakes, SRS or XP.
Only browser-cookie/CSRF actor may read or update its own saved words.
"""
import logging
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StrictBool, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.db.models.course_saved_word import CourseSavedWord
from app.services.pwa_auth_service import (
    PWA_SESSION_COOKIE, PwaAuthError, PwaAuthService, require_same_origin
)
from app.services.user_access_state_service import UserAccessState, UserAccessStateService

logger = logging.getLogger(__name__)
_NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
_HANZI = re.compile(r"^[\u3400-\u9fff\uf900-\ufaff]{1,16}$")
_MAX_BODY_BYTES = 512


class SavedWordSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hanzi: str
    saved: StrictBool

    @field_validator("hanzi")
    @classmethod
    def validate_hanzi(cls, value: str) -> str:
        word = value.strip()
        if not _HANZI.fullmatch(word):
            raise ValueError("unsupported_dictionary_word")
        return word


async def _validate(request: Request, settings_obj, model):
    require_same_origin(request, settings_obj)
    if request.headers.get("X-Telegram-Init-Data"):
        raise PwaAuthError("pwa_request_invalid", status_code=422)
    if request.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise PwaAuthError("pwa_request_invalid", status_code=415)
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > _MAX_BODY_BYTES:
            raise PwaAuthError("pwa_request_invalid", status_code=413)
    try:
        return model.model_validate_json(bytes(content))
    except (ValueError, TypeError):
        raise PwaAuthError("pwa_request_invalid", status_code=422)


def create_pwa_saved_words_router(*, session_factory, settings_obj):
    router = APIRouter(tags=["pwa-saved-words"])

    async def actor(request, session):
        learner, _ = await PwaAuthService(session, settings_obj).mutation_actor(
            request.cookies.get(PWA_SESSION_COOKIE),
            request.headers.get("X-HSK-PWA-CSRF"),
        )
        if UserAccessStateService.classify(learner) == UserAccessState.BLOCKED:
            raise PwaAuthError("pwa_session_required", status_code=401)
        return learner

    @router.post("/api/v3/pwa/dictionary/saved/list")
    async def list_saved(request: Request):
        class Empty(BaseModel):
            model_config = ConfigDict(extra="forbid")
        try:
            await _validate(request, settings_obj, Empty)
            async with session_factory() as db:
                learner = await actor(request, db)
                items = await db.scalars(
                    select(CourseSavedWord.hanzi)
                    .where(CourseSavedWord.user_id == learner.id)
                    .order_by(CourseSavedWord.hanzi)
                )
                words = list(items.all())
            return JSONResponse({"ok": True, "words": words}, headers=_NO_STORE)
        except PwaAuthError as exc:
            return JSONResponse({"ok": False, "error": exc.code}, status_code=exc.status_code, headers=_NO_STORE)
        except Exception:
            logger.exception("PWA saved word read unavailable")
            return JSONResponse({"ok": False, "error": "saved_words_unavailable"}, status_code=503, headers=_NO_STORE)

    @router.post("/api/v3/pwa/dictionary/saved/set")
    async def set_saved(request: Request):
        try:
            payload = await _validate(request, settings_obj, SavedWordSet)
            async with session_factory() as db:
                learner = await actor(request, db)
                if payload.saved:
                    existing = await db.scalar(
                        select(CourseSavedWord.id).where(
                            CourseSavedWord.user_id == learner.id,
                            CourseSavedWord.hanzi == payload.hanzi,
                        )
                    )
                    if existing is None:
                        try:
                            async with db.begin_nested():
                                db.add(CourseSavedWord(user_id=learner.id, hanzi=payload.hanzi))
                                await db.flush()
                        except IntegrityError:
                            # Another client may have saved the same word concurrently.
                            pass
                else:
                    await db.execute(
                        delete(CourseSavedWord).where(
                            CourseSavedWord.user_id == learner.id,
                            CourseSavedWord.hanzi == payload.hanzi,
                        )
                    )
                await db.commit()
            return JSONResponse({"ok": True, "hanzi": payload.hanzi, "saved": payload.saved}, headers=_NO_STORE)
        except PwaAuthError as exc:
            return JSONResponse({"ok": False, "error": exc.code}, status_code=exc.status_code, headers=_NO_STORE)
        except Exception:
            logger.exception("PWA saved word write unavailable")
            return JSONResponse({"ok": False, "error": "saved_words_unavailable"}, status_code=503, headers=_NO_STORE)

    return router
