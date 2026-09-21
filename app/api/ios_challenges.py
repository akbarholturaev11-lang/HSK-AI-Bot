"""Native iOS challenge adapter backed by the shared challenge service."""

from __future__ import annotations
import logging
from typing import Literal
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.api.desktop_rating import MAX_LEADERBOARD_ITEMS, _access_token, challenge_ref
from app.repositories.user_repo import UserRepository
from app.services.course_challenge_service import CourseChallengeService
from app.services.course_gamification_service import CourseGamificationService
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService

logger = logging.getLogger(__name__)

class IOSChallengeError(RuntimeError):
    def __init__(self, code: str, status_code: int = 400):
        super().__init__(code); self.code=code; self.status_code=status_code

class CreateRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    opponent_ref: str = Field(min_length=8,max_length=64)
    level: str = Field(default="",max_length=16)
    language: str = Field(default="",max_length=8)

class RespondRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    action: Literal["accept","decline"]

class Answer(BaseModel):
    model_config=ConfigDict(extra="forbid")
    question_id: str = Field(min_length=1,max_length=80)
    selected_index: int = Field(ge=0,le=32)

class SubmitRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    answers: list[Answer] = Field(default_factory=list,max_length=40)
    duration_seconds: int = Field(default=0,ge=0,le=7200)

async def _payload(request, model):
    try: return model.model_validate(await request.json())
    except (ValidationError,ValueError,TypeError): raise IOSChallengeError("ios_challenge_request_invalid",422)

def create_ios_challenge_router(*,session_factory,settings_obj,bot,challenge_service_factory=CourseChallengeService,gamification_service_factory=CourseGamificationService):
    router=APIRouter(tags=["ios-challenges"])

    async def user(session,request):
        context=await DesktopAuthService(session,settings_obj).authenticate(_access_token(request))
        value=await UserRepository(session).get_by_telegram_id(int(context.user.telegram_id))
        if not value: raise IOSChallengeError("ios_challenge_user_not_found",404)
        return value

    def response(result): return JSONResponse(content=result,headers={"Cache-Control":"no-store"})

    @router.get("/api/v3/ios/challenges")
    async def list_challenges(request:Request):
        try:
            async with session_factory() as session:
                current=await user(session,request)
                return response(await challenge_service_factory(session).list_for_user(int(current.telegram_id)))
        except (DesktopAuthError,IOSChallengeError) as exc:
            return JSONResponse(status_code=exc.status_code,content={"ok":False,"error":getattr(exc,"code","ios_challenge_unavailable")})

    @router.post("/api/v3/ios/challenges")
    async def create(request:Request):
        try:
            payload=await _payload(request,CreateRequest)
            async with session_factory() as session:
                current=await user(session,request)
                board=await gamification_service_factory(session).leaderboard(current,limit=MAX_LEADERBOARD_ITEMS)
                secret=str(getattr(settings_obj,"DESKTOP_AUTH_SIGNING_SECRET","") or "")
                opponent=0
                for row in board.get("leaderboard") or []:
                    if isinstance(row,dict) and challenge_ref(row.get("telegram_id"),secret)==payload.opponent_ref:
                        opponent=int(row.get("telegram_id") or 0); break
                if opponent<=0: raise IOSChallengeError("challenge_opponent_not_found",404)
                result=await challenge_service_factory(session).create(int(current.telegram_id),opponent_telegram_id=opponent,level=payload.level,lang=payload.language,bot=bot)
                await session.commit()
                return response(result)
        except (DesktopAuthError,IOSChallengeError) as exc:
            return JSONResponse(status_code=exc.status_code,content={"ok":False,"error":getattr(exc,"code","ios_challenge_unavailable")})

    @router.post("/api/v3/ios/challenges/{challenge_id}/respond")
    async def respond(challenge_id:int,request:Request):
        try:
            payload=await _payload(request,RespondRequest)
            async with session_factory() as session:
                current=await user(session,request)
                result=await challenge_service_factory(session).respond(int(current.telegram_id),challenge_id,payload.action,bot=bot)
                await session.commit(); return response(result)
        except (DesktopAuthError,IOSChallengeError) as exc:
            return JSONResponse(status_code=exc.status_code,content={"ok":False,"error":getattr(exc,"code","ios_challenge_unavailable")})

    @router.post("/api/v3/ios/challenges/{challenge_id}/start")
    async def start(challenge_id:int,request:Request):
        try:
            async with session_factory() as session:
                current=await user(session,request)
                result=await challenge_service_factory(session).start(int(current.telegram_id),challenge_id)
                await session.commit(); return response(result)
        except (DesktopAuthError,IOSChallengeError) as exc:
            return JSONResponse(status_code=exc.status_code,content={"ok":False,"error":getattr(exc,"code","ios_challenge_unavailable")})

    @router.post("/api/v3/ios/challenges/{challenge_id}/submit")
    async def submit(challenge_id:int,request:Request):
        try:
            payload=await _payload(request,SubmitRequest)
            async with session_factory() as session:
                current=await user(session,request)
                result=await challenge_service_factory(session).submit(int(current.telegram_id),challenge_id,[{"question_id":x.question_id,"selected_index":x.selected_index} for x in payload.answers],duration_seconds=payload.duration_seconds,bot=bot)
                await session.commit(); return response(result)
        except (DesktopAuthError,IOSChallengeError) as exc:
            return JSONResponse(status_code=exc.status_code,content={"ok":False,"error":getattr(exc,"code","ios_challenge_unavailable")})

    return router
