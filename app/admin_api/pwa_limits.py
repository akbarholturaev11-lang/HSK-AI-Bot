"""First-party PWA entitlement limits, CAS + single-use passkey writes.

The Telegram Mini App remains authoritative through the shared LimitConfigService.
Only FREE/TRIAL_ACTIVE numeric rules can change here, with daily/lifetime windows.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, model_validator
from sqlalchemy import select, text

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_payment_review import StrictModel
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, _authorized_admin, authenticate_admin_pwa_session
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.bot_setting import BotSetting
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.entitlements.limits_config import ENTITLEMENT_LIMITS_KEY, LimitConfigService

logger = logging.getLogger(__name__)
Plan = Literal["FREE", "TRIAL_ACTIVE"]


class EmptyLimitsRequest(StrictModel):
    pass


class NumericRule(StrictModel):
    limit: Annotated[int, Field(strict=True, ge=0, le=10000)]
    window: Literal["daily", "lifetime"]


class TrialChange(StrictModel):
    enabled: bool
    days: Annotated[int, Field(strict=True, ge=1, le=90)]
    disabled_reason: Annotated[str, Field(max_length=200)] = ""


class LimitsUpdateInput(StrictModel):
    plan: Plan | None = None
    rules: dict[str, NumericRule] | None = None
    trial: TrialChange | None = None

    @model_validator(mode="after")
    def one_editor(self):
        rules_change = self.plan is not None and self.rules is not None
        trial_change = self.trial is not None
        if rules_change == trial_change or (trial_change and (self.plan is not None or self.rules is not None)):
            raise ValueError("Exactly one limits editor is required")
        if rules_change and (not self.rules or len(self.rules) > 40):
            raise ValueError("Invalid rule count")
        return self


class LimitsCommand(LimitsUpdateInput):
    expected_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def operation(self):
        return {"action": "limits.update", "target": "global", "payload": self.model_dump(exclude_none=True)}


class ExecuteLimits(LimitsCommand):
    step_up_id: StepId


async def _revision(db, *, lock=False):
    if lock:
        await BotSettingRepository(db).lock_key(ENTITLEMENT_LIMITS_KEY)
    statement = select(BotSetting).where(BotSetting.key == ENTITLEMENT_LIMITS_KEY).execution_options(populate_existing=True)
    row = await db.scalar(statement.with_for_update() if lock else statement)
    return hashlib.sha256((row.value if row else "").encode("utf-8")).hexdigest()


def _apply(current, change):
    # Never replace other plans, unexposed rules, or the AI budget/trial metadata.
    payload = {"plans": {key: dict(value) for key, value in current["plans"].items()},
               "trial": dict(current["trial"])}
    if change.plan is not None:
        existing = payload["plans"][change.plan]
        if set(change.rules) != {key for key, rule in existing.items()
                                if isinstance(rule, dict) and isinstance(rule.get("limit"), int)}:
            raise CommandError("invalid_limits_config", 400)
        for key, rule in change.rules.items():
            existing[key] = rule.model_dump()
    else:
        payload["trial"].update(change.trial.model_dump())
    return payload


async def read_limits(db, *, session_cookie, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with read_transaction(db):
        actor = await authenticate_admin_pwa_session(db, session_cookie, settings_obj)
        if actor is None or actor.auth_method != "webauthn":
            raise CommandError("admin_pwa_unauthorized", 401)
        revision = await _revision(db)
        limits = await LimitConfigService(db).get_payload()
    return {"limits": limits, "revision_hash": revision}


async def prepare_limits(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with read_transaction(db):
        actor = await authenticate_admin_pwa_session(db, session_cookie, settings_obj)
        if actor is None or actor.auth_method != "webauthn":
            raise CommandError("admin_pwa_unauthorized", 401)
        revision = await _revision(db)
        current = await LimitConfigService(db).get_payload()
        _apply(current, request)  # Enforce precise, visible editable subset.
    return {"operation": LimitsCommand(**request.model_dump(), expected_hash=revision).operation(),
            "current": current}


async def save_limits(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    command = LimitsCommand.model_validate(request.model_dump(exclude={"step_up_id"}))
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
        revision = await _revision(db, lock=True)
        now = datetime.now(timezone.utc)
        if (not _enabled(settings_obj) or not _authorized_admin(actor, settings_obj)
                or session.revoked_at is not None
                or min(_utc(step.expires_at), _utc(session.expires_at)) <= now):
            raise CommandError("admin_pwa_step_up_denied", 403)
        if revision != command.expected_hash:
            raise CommandError("confirmation_changed", 409)
        current = await LimitConfigService(db).get_payload()
        payload = _apply(current, command)
        try:
            result = await LimitConfigService(db).save_config(payload, updated_by_telegram_id=actor.telegram_id)
        except ValueError as exc:
            raise CommandError("invalid_limits_config", 400) from exc
        updated = result.public_payload()
        audit_id = str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id, step_up_id=step.id,
            actor_user_id=int(actor.id), target_user_id=None, action=operation["action"],
            target=operation["target"], payload_hash=operation_digest(**operation),
            result_json=json.dumps({"before_hash": revision, "plan": command.plan,
                                    "trial_changed": command.trial is not None,
                                    "after": updated}, sort_keys=True, ensure_ascii=False)))
        await db.flush()
    return {"command_id": audit_id, "limits": updated}


def create_admin_pwa_limits_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-limits"])

    async def handle(request, task, schema):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            parsed = schema.model_validate(await _body(request, 4096))
        except ValidationError:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                data = await task(db, session_cookie=cookie, settings_obj=settings_obj,
                                  **({} if schema is EmptyLimitsRequest else {"request": parsed}))
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error("Admin PWA limits operation unavailable", exc_info=True)
            return _reply(503, "admin_pwa_command_unavailable")
        return JSONResponse({"ok": True, **data}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/limits/read")
    async def read(request: Request):
        return await handle(request, read_limits, EmptyLimitsRequest)

    @router.post("/api/admin/v1/limits/prepare")
    async def prepare(request: Request):
        return await handle(request, prepare_limits, LimitsUpdateInput)

    @router.post("/api/admin/v1/limits/save")
    async def save(request: Request):
        return await handle(request, save_limits, ExecuteLimits)

    return router
