"""Authenticated native iOS assistant API backed by the shared assistant service."""
import asyncio
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from app.api.android_features import _access_token, _validated_payload, AndroidFeatureError
from app.db.models.assistant import AssistantConversation, AssistantRequest
from app.repositories.user_repo import UserRepository
from app.services.desktop_auth_service import DesktopAuthService, DesktopAuthError
from app.services.assistant_service import AssistantService, AssistantInput, AssistantError, decode_media, request_payload, process_request
from app.services.assistant_assessment_service import assessment_finished


class AbandonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=160)


def create_ios_assistant_router(*, session_factory, settings_obj):
    router = APIRouter(prefix="/api/v3/ios/assistant", tags=["ios-assistant"])

    async def user_for(session, request):
        if not getattr(settings_obj, "ANDROID_ASSISTANT_ENABLED", True):
            raise AssistantError("assistant_disabled", 503)
        auth = await DesktopAuthService(session, settings_obj).authenticate(_access_token(request))
        user = await UserRepository(session).get_by_telegram_id(auth.user.telegram_id)
        if user is None or user.status == "blocked":
            raise AssistantError("access_blocked", 403)
        return user

    async def perform(request, operation):
        try:
            async with session_factory() as session:
                user = await user_for(session, request)
                result = await operation(session, user, AssistantService(session, settings_obj))
                return JSONResponse(result, headers={"Cache-Control": "no-store"})
        except (AssistantError, DesktopAuthError, AndroidFeatureError) as error:
            details = getattr(error, "details", {})
            return JSONResponse({**details, "ok": False, "error": error.code},
                status_code=getattr(error, "status", getattr(error, "status_code", 400)), headers={"Cache-Control": "no-store"})

    @router.get("/status")
    async def status(request: Request):
        return await perform(request, lambda session, user, service: service.status(user, request.query_params.get("channel", "ios")))

    @router.post("/conversations")
    async def create(request: Request):
        async def operation(session, user, service):
            return {"ok": True, "conversation": await service.new_conversation(user)}
        return await perform(request, operation)

    @router.get("/conversations")
    async def conversations(request: Request):
        async def operation(session, user, service):
            rows = await session.scalars(select(AssistantConversation).where(AssistantConversation.user_id == user.id)
                .order_by(AssistantConversation.created_at.desc()).limit(50))
            return {"ok": True, "conversations": [{"id": r.id, "title": r.title} for r in rows]}
        return await perform(request, operation)

    @router.get("/conversations/{conversation_id}/messages")
    async def messages(conversation_id: UUID, request: Request, before: str = ""):
        async def operation(session, user, service):
            await service.conversation(user.id, str(conversation_id))
            query = select(AssistantRequest).where(AssistantRequest.user_id == user.id,
                AssistantRequest.conversation_id == str(conversation_id))
            if before:
                anchor = await service.get_request(user.id, before)
                if anchor.conversation_id != str(conversation_id):
                    raise AssistantError("assistant_not_found", 404)
                query = query.where(AssistantRequest.created_at < anchor.created_at)
            rows = list((await session.scalars(query.order_by(AssistantRequest.created_at.desc()).limit(50))).all())
            return {"ok": True, "messages": [request_payload(r) for r in reversed(rows)],
                "next_cursor": rows[-1].client_message_id if len(rows) == 50 else ""}
        return await perform(request, operation)

    @router.post("/conversations/{conversation_id}/messages")
    async def send(conversation_id: UUID, request: Request, background: BackgroundTasks):
        async def operation(session, user, service):
            data = await _validated_payload(request, AssistantInput, max_body_bytes=7_200_000)
            # Decode only after authentication and validation, off the event loop.
            media = await asyncio.to_thread(decode_media, data)
            row, fresh = await service.reserve(user, str(conversation_id), data)
            if fresh:
                background.add_task(process_request, session_factory, row.id, data, media, settings_obj)
            return request_payload(row)
        return await perform(request, operation)

    @router.get("/requests/{client_message_id}")
    async def lookup(client_message_id: UUID, request: Request):
        async def operation(session, user, service):
            return request_payload(await service.get_request(user.id, client_message_id))
        return await perform(request, operation)

    @router.post("/assessments/abandon")
    async def abandon(request: Request):
        async def operation(session, user, service):
            data = await _validated_payload(request, AbandonInput)
            await assessment_finished(session, user.id, data.session_id, "abandoned")
            return {"ok": True}
        return await perform(request, operation)

    return router
