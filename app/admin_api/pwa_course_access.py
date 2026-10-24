"""First-party global course access policy command; exact one-use passkey proof.

Never exposes mutation to external MCP. Telegram Admin Mini App continues to
use CourseAccessPolicyService independently, without modified public endpoints.
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, model_validator
from sqlalchemy import select, text

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_payment_review import StrictModel
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, _authorized_admin, authenticate_admin_pwa_session
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.bot_setting import BotSetting
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.course_access_policy_service import (
    COURSE_ACCESS_POLICY_KEY, CourseAccessPolicyService,
)

logger = logging.getLogger(__name__)
_MAX_FREE_DAYS = 365


def _deadline(raw: str | None, mode: str):
    if mode == "subscription":
        if raw is not None:
            raise ValueError("Subscription mode has no free deadline")
        return None
    if not isinstance(raw, str) or not 20 <= len(raw) <= 40:
        raise ValueError("Free-until requires explicit ISO time")
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid deadline") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("UTC offset required")
    stamp = stamp.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if not now < stamp <= now + timedelta(days=_MAX_FREE_DAYS):
        raise ValueError("Free deadline outside 365-day policy")
    return stamp


class CoursePolicyInput(StrictModel):
    mode: Literal["subscription", "free_until"]
    free_until: Annotated[str, Field(max_length=40)] | None = None

    @model_validator(mode="after")
    def validate_deadline(self):
        _deadline(self.free_until, self.mode)
        return self


class CoursePolicyCommand(CoursePolicyInput):
    expected_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def operation(self):
        return {"action": "course.access_policy", "target": "global",
                "payload": self.model_dump()}


class ExecuteCoursePolicy(CoursePolicyCommand):
    step_up_id: StepId


def _hash(value):
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


async def _current(db, *, lock=False):
    if lock:
        # FOR UPDATE alone cannot protect a setting that has no row yet.
        # Shared service/Telegram writers take the same key lock via set().
        await BotSettingRepository(db).lock_key(COURSE_ACCESS_POLICY_KEY)
    statement = select(BotSetting).where(
        BotSetting.key == COURSE_ACCESS_POLICY_KEY).execution_options(populate_existing=True)
    row = await db.scalar(statement.with_for_update() if lock else statement)
    return _hash(row.value if row else None)


async def read_course_policy(db, *, session_cookie, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with db.begin():
        actor = await authenticate_admin_pwa_session(db, session_cookie, settings_obj)
        if actor is None or actor.auth_method != "webauthn":
            raise CommandError("admin_pwa_unauthorized", 401)
        state_hash = await _current(db)
        payload = await CourseAccessPolicyService(db).get_payload()
    return {"course_access": payload, "revision_hash": state_hash}


async def prepare_course_policy(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with db.begin():
        actor = await authenticate_admin_pwa_session(db, session_cookie, settings_obj)
        if actor is None or actor.auth_method != "webauthn":
            raise CommandError("admin_pwa_unauthorized", 401)
        digest = await _current(db)
        current = await CourseAccessPolicyService(db).get_payload()
        command = CoursePolicyCommand(**request.model_dump(), expected_hash=digest)
    return {"operation": command.operation(), "current": current}


async def execute_course_policy(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    command = CoursePolicyCommand.model_validate(request.model_dump(exclude={"step_up_id"}))
    operation = command.operation()
    async with db.begin():
        if db.get_bind().dialect.name == "postgresql":
            await db.execute(text("SET LOCAL lock_timeout = '5000'"))
            await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db, session_cookie=session_cookie,
                step_up_id=request.step_up_id, settings_obj=settings_obj, **operation):
            raise CommandError("admin_pwa_step_up_denied", 403)
        step = await db.get(AdminPwaStepUp, request.step_up_id)
        session = await db.get(AdminPwaSession, step.session_id)
        actor = await db.get(User, step.user_id)
        current_hash = await _current(db, lock=True)
        # The setting lock may have waited while this proof/session expired.
        # Recheck at the actual write boundary after every target lock wait.
        now = datetime.now(timezone.utc)
        if (not _enabled(settings_obj) or not _authorized_admin(actor, settings_obj)
                or min(_utc(step.expires_at), _utc(session.expires_at)) <= now):
            raise CommandError("admin_pwa_step_up_denied", 403)
        if current_hash != command.expected_hash:
            raise CommandError("confirmation_changed", 409)
        try:
            deadline = _deadline(command.free_until, command.mode)
            policy = await CourseAccessPolicyService(db).save_policy(
                mode=command.mode, free_until=deadline, updated_by_telegram_id=actor.telegram_id)
        except ValueError as exc:
            raise CommandError("invalid_course_access_policy", 400) from exc
        audit_id = str(uuid4())
        result = {"course_access": policy.public_payload()}
        db.add(AdminPwaCommandAudit(id=audit_id, step_up_id=step.id,
            actor_user_id=int(actor.id), target_user_id=None, action=operation["action"],
            target=operation["target"], payload_hash=operation_digest(**operation),
            result_json=json.dumps({"mode":command.mode, "free_until":command.free_until,
                                    "previous_hash":command.expected_hash,
                                    "result":result}, sort_keys=True)))
        await db.flush()
    return {"command_id": audit_id, **result}


def create_admin_pwa_course_access_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-course-access"])

    async def handle(request, task, schema=None):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            parsed = schema.model_validate(await _body(request, 2048)) if schema else None
        except ValidationError:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                data = await task(db, session_cookie=cookie, settings_obj=settings_obj,
                                  **({"request": parsed} if schema else {}))
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error("Admin PWA course access operation unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        return JSONResponse({"ok": True, **data}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/course-access/read")
    async def read(request: Request):
        return await handle(request, read_course_policy)

    @router.post("/api/admin/v1/course-access/prepare")
    async def prepare(request: Request):
        return await handle(request, prepare_course_policy, CoursePolicyInput)

    @router.post("/api/admin/v1/course-access/save")
    async def save(request: Request):
        return await handle(request, execute_course_policy, ExecuteCoursePolicy)

    return router
