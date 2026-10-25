"""Canonical manual Pro grant with exact one-use WebAuthn and atomic audit."""
from datetime import datetime, timezone
import json
import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError
from sqlalchemy import select, text

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_payment_review import PositiveId, StrictModel
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, _authorized_admin, authenticate_admin_pwa_session
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.user import User
from app.services.subscription_service import SubscriptionService

# First-party Admin PWA policy only. The legacy Telegram admin service keeps
# its separate existing contract; never silently change Telegram access rules.
PWA_MANUAL_GRANT_MAX_DAYS = 365

logger = logging.getLogger(__name__)
StepId = Annotated[str, Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")]


class CommandError(RuntimeError):
    def __init__(self, code, status):
        super().__init__(code)
        self.status = status


class AccessSnapshot(StrictModel):
    status: Annotated[str, Field(max_length=32)]
    payment_status: Annotated[str, Field(max_length=32)] | None
    start_date: Annotated[str, Field(max_length=40)] | None
    end_date: Annotated[str, Field(max_length=40)] | None
    selected_plan_type: Annotated[str, Field(max_length=32)] | None
    payment_preview_available: bool
    payment_preview_payment_id: PositiveId | None
    paid_active: bool


class PrepareAccessGrant(StrictModel):
    user_id: PositiveId
    duration_days: Annotated[int, Field(strict=True, ge=1, le=PWA_MANUAL_GRANT_MAX_DAYS)]


class AccessGrantCommand(PrepareAccessGrant):
    expected: AccessSnapshot

    def operation(self):
        return {"action": "users.grant_access", "target": str(self.user_id), "payload": self.model_dump()}


class ExecuteAccessGrant(AccessGrantCommand):
    step_up_id: StepId


def access_snapshot(user):
    return AccessSnapshot(**{key: (_utc(getattr(user, key)).isoformat() if getattr(user, key) else None)
                             for key in ("start_date", "end_date")},
        **{key: getattr(user, key) for key in ("status", "payment_status", "selected_plan_type",
                                              "payment_preview_available", "payment_preview_payment_id")},
        paid_active=bool(user.payment_status == "approved" and user.end_date
                         and _utc(user.end_date) > datetime.now(timezone.utc)))


async def _target(db, user_id, *, lock=True):
    query = select(User).where(User.id == user_id).execution_options(populate_existing=True)
    user = await db.scalar(query.with_for_update() if lock else query)
    if user is None:
        raise CommandError("user_not_found", 404)
    # Blocking and granting are distinct confirmations. Never implicitly unblock.
    if user.status == "blocked":
        raise CommandError("target_blocked", 409)
    return user


async def prepare_access_grant(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with db.begin():
        actor = await authenticate_admin_pwa_session(db, session_cookie, settings_obj)
        if actor is None or actor.auth_method != "webauthn":
            raise CommandError("admin_pwa_unauthorized", 401)
        user = await _target(db, request.user_id, lock=False)
        command = AccessGrantCommand(**request.model_dump(), expected=access_snapshot(user))
    return command.operation()


async def execute_access_grant(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    command = AccessGrantCommand.model_validate(request.model_dump(exclude={"step_up_id"}))
    operation = command.operation()
    async with db.begin():
        if db.get_bind().dialect.name == "postgresql":
            await db.execute(text("SET LOCAL lock_timeout = '5000'"))
            await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db, session_cookie=session_cookie,
                step_up_id=request.step_up_id, settings_obj=settings_obj, **operation):
            raise CommandError("admin_pwa_step_up_denied", 403)
        step = await db.get(AdminPwaStepUp, request.step_up_id)
        user = await _target(db, command.user_id)
        session = await db.get(AdminPwaSession, step.session_id)
        now = datetime.now(timezone.utc)
        if (not _enabled(settings_obj) or not _authorized_admin(await db.get(User, step.user_id), settings_obj)
                or min(_utc(step.expires_at), _utc(session.expires_at)) <= now):
            raise CommandError("admin_pwa_step_up_denied", 403)
        if access_snapshot(user) != command.expected:
            raise CommandError("confirmation_changed", 409)
        _, extended = await SubscriptionService(db).grant_manual_paid_access(user, command.duration_days)
        audit_id = str(uuid4())
        result = {"user_id": user.id, "duration_days": command.duration_days,
                  "extended": extended, "before": command.expected.model_dump(),
                  "after": access_snapshot(user).model_dump()}
        db.add(AdminPwaCommandAudit(id=audit_id, step_up_id=step.id, actor_user_id=step.user_id,
            target_user_id=user.id, action=operation["action"], target=operation["target"],
            payload_hash=operation_digest(**operation), result_json=json.dumps(result, sort_keys=True)))
        await db.flush()
    return {"command_id": audit_id, **result}


def create_admin_pwa_access_grant_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-access"])

    async def handle(request, execute):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            model = ExecuteAccessGrant if execute else PrepareAccessGrant
            command = model.model_validate(await _body(request, 4096))
        except ValidationError:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                result = await (execute_access_grant if execute else prepare_access_grant)(db,
                    session_cookie=cookie, request=command, settings_obj=settings_obj)
        except CommandError as error:
            return _reply(error.status, str(error))
        except Exception:
            logger.exception("Admin PWA access command unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        return JSONResponse({"ok": True, **result}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/users/prepare-access")
    async def prepare(request: Request):
        return await handle(request, False)

    @router.post("/api/admin/v1/users/grant-access")
    async def execute(request: Request):
        return await handle(request, True)

    return router
