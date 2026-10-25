"""First-party HSK 3.0 global settings with exact passkey confirmation/audit.

Uses the same two shared services as Telegram Admin and never grants an
external MCP capability. Turning OFF paid checkout is not silently relabelled
as free access: the learner entitlement service remains authoritative.
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
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, authenticate_admin_pwa_session, _authorized_admin
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.bot_setting import BotSetting
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.course_levels import hsk30_content_levels, level_spec
from app.services.admin_hsk30_analytics_service import AdminHsk30AnalyticsService
from app.services.hsk30_feature_service import (
    HSK30_ENABLED_SETTINGS_KEY, HSK30_LIVE_LEVELS_SETTINGS_KEY, Hsk30FeatureService,
)
from app.services.hsk30_unlock_service import (
    HSK30_UNLOCK_PRICE_KEY, HSK30_UNLOCK_PAYMENT_ENABLED_KEY, Hsk30UnlockService,
    MIN_HSK30_UNLOCK_PRICE_TJS, MAX_HSK30_UNLOCK_PRICE_TJS,
)

logger = logging.getLogger(__name__)
_KEYS = tuple(sorted((
    HSK30_ENABLED_SETTINGS_KEY, HSK30_LIVE_LEVELS_SETTINGS_KEY,
    HSK30_UNLOCK_PRICE_KEY, HSK30_UNLOCK_PAYMENT_ENABLED_KEY,
)))


def _available():
    return tuple(level for level in hsk30_content_levels()
                 if level_spec(level) is not None and level_spec(level).selectable)


class EmptyHsk30Request(StrictModel):
    pass


class Hsk30AnalyticsRequest(StrictModel):
    days: Literal[7, 30, 90, 0] = 30



class Hsk30SettingsInput(StrictModel):
    enabled: bool
    unlock_payment_enabled: bool
    unlock_price_tjs: Annotated[int, Field(strict=True,
        ge=MIN_HSK30_UNLOCK_PRICE_TJS, le=MAX_HSK30_UNLOCK_PRICE_TJS)]
    live_levels: list[str]

    @model_validator(mode="after")
    def validate_levels(self):
        if len(self.live_levels) > 10 or len(set(self.live_levels)) != len(self.live_levels):
            raise ValueError("Invalid level selection")
        if any(type(level) is not str or level not in _available() for level in self.live_levels):
            raise ValueError("Unavailable HSK 3.0 level")
        # Order is canonical and frozen into the exact WebAuthn commitment.
        if self.live_levels != [level for level in _available() if level in self.live_levels]:
            raise ValueError("Noncanonical level order")
        return self


class Hsk30SettingsCommand(Hsk30SettingsInput):
    expected_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def operation(self):
        return {"action": "hsk30.settings", "target": "global", "payload": self.model_dump()}


class ExecuteHsk30Settings(Hsk30SettingsCommand):
    step_up_id: StepId


async def _snapshot(db, *, lock=False):
    if lock:
        # Row locks cannot serialize first writes to absent settings. These
        # shared transaction locks also coordinate with legacy service writes.
        repo = BotSettingRepository(db)
        for key in _KEYS:
            await repo.lock_key(key)
    statement = select(BotSetting.key, BotSetting.value, BotSetting.updated_at).where(
        BotSetting.key.in_(_KEYS)).order_by(BotSetting.key).limit(len(_KEYS))
    rows = (await db.execute(statement.with_for_update() if lock else statement)).all()
    values = {row.key: {"value": row.value, "updated_at": _utc(row.updated_at).isoformat()}
              for row in rows}
    raw = json.dumps([[key, values.get(key)] for key in _KEYS],
                     ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


async def _read(db):
    feature, unlock = Hsk30FeatureService(db), Hsk30UnlockService(db)
    return {"enabled": await feature.is_enabled(),
            "unlock_payment_enabled": await unlock.payment_enabled(),
            "unlock_price_tjs": await unlock.price_tjs(),
            "live_levels": list(await feature.live_levels()),
            "available_levels": list(_available())}


async def read_hsk30_settings(db, *, session_cookie, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with read_transaction(db):
        actor = await authenticate_admin_pwa_session(db, session_cookie, settings_obj)
        if actor is None or actor.auth_method != "webauthn":
            raise CommandError("admin_pwa_unauthorized", 401)
        current = await _read(db)
    return {"hsk30": current}


async def read_hsk30_analytics(db, *, session_cookie, request, settings_obj):
    """Expose aggregate-only HSK 3.0 funnel to this first-party PWA."""
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with read_transaction(db):
        actor = await authenticate_admin_pwa_session(db, session_cookie, settings_obj)
        if actor is None or actor.auth_method != "webauthn":
            raise CommandError("admin_pwa_unauthorized", 401)
        snapshot = await AdminHsk30AnalyticsService(db).snapshot(days=request.days, user_limit=0)
    return {"analytics": {
        "period_days": snapshot["period_days"],
        "generated_at": snapshot["generated_at"],
        "course_funnel": snapshot["course_funnel"],
        "payment_funnel": snapshot["payment_funnel"],
        "selected_level_users": snapshot["selected_level_users"],
        "track_activated_users": snapshot["track_activated_users"],
        "payments": {"approved": snapshot["payments"]["approved"]},
        "coverage_note": snapshot["coverage_note"]
    }}


async def prepare_hsk30_settings(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with read_transaction(db):
        actor = await authenticate_admin_pwa_session(db, session_cookie, settings_obj)
        if actor is None or actor.auth_method != "webauthn":
            raise CommandError("admin_pwa_unauthorized", 401)
        digest = await _snapshot(db)
        current = await _read(db)
        command = Hsk30SettingsCommand(**request.model_dump(), expected_hash=digest)
    return {"operation": command.operation(), "current": current}


async def execute_hsk30_settings(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    command = Hsk30SettingsCommand.model_validate(request.model_dump(exclude={"step_up_id"}))
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
        # Lock the four exact shared settings in deterministic order and then
        # re-evaluate actor/session/receipt expiry at the write boundary.
        current_hash = await _snapshot(db, lock=True)
        stamp = datetime.now(timezone.utc)
        if (not _enabled(settings_obj) or not _authorized_admin(actor, settings_obj)
                or session.revoked_at is not None
                or min(_utc(step.expires_at), _utc(session.expires_at)) <= stamp):
            raise CommandError("admin_pwa_step_up_denied", 403)
        if current_hash != command.expected_hash:
            raise CommandError("confirmation_changed", 409)
        feature, unlock = Hsk30FeatureService(db), Hsk30UnlockService(db)
        await feature.set_enabled(command.enabled)
        await unlock.set_payment_enabled(command.unlock_payment_enabled)
        await unlock.set_price_tjs(command.unlock_price_tjs)
        await feature.set_live_levels(command.live_levels)
        after = await _read(db)
        audit_id = str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id, step_up_id=step.id,
            actor_user_id=int(actor.id), target_user_id=None, action=operation["action"],
            target=operation["target"], payload_hash=operation_digest(**operation),
            result_json=json.dumps({"before_hash":current_hash, "after":after},
                                   sort_keys=True, separators=(",", ":"))))
        await db.flush()
    return {"command_id": audit_id, "hsk30": after}


def create_admin_pwa_hsk30_settings_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-hsk30-settings"])

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
                                  **({} if schema is EmptyHsk30Request else {"request": parsed}))
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error("Admin PWA HSK 3.0 settings unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        return JSONResponse({"ok": True, **data}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/hsk30/read")
    async def read(request: Request):
        return await handle(request, read_hsk30_settings, EmptyHsk30Request)

    @router.post("/api/admin/v1/hsk30/analytics")
    async def analytics(request: Request):
        return await handle(request, read_hsk30_analytics, Hsk30AnalyticsRequest)

    @router.post("/api/admin/v1/hsk30/prepare")
    async def prepare(request: Request):
        return await handle(request, prepare_hsk30_settings, Hsk30SettingsInput)

    @router.post("/api/admin/v1/hsk30/save")
    async def save(request: Request):
        return await handle(request, execute_hsk30_settings, ExecuteHsk30Settings)

    return router
