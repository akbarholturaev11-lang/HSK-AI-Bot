"""Bounded first-party marketing configuration, never outbound broadcasting.

Exact current state and passkey proof authorize one existing shared-service
command. No media/URL input, arbitrary setting keys, student targeting or MCP.
"""
import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, field_validator, model_validator
from sqlalchemy import select, text
from sqlalchemy.orm import defer

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_payment_review import PositiveId, StrictModel
from app.admin_api.pwa_sessions import (
    ADMIN_PWA_COOKIE_NAME, _authorized_admin, authenticate_admin_pwa_session,
)
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.bot_setting import BotSetting
from app.db.models.course_ad import CourseAdCreative
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.course_ad_service import COURSE_AD_MEDIA_ROOT, CourseAdService
from app.services.course_sales_experiment_service import (
    SALES_EXPERIMENT_SETTINGS_KEY, CourseSalesExperimentService, CourseSalesExperimentSettings,
)
from app.services.desktop_app_promo_settings_service import (
    DESKTOP_APP_PROMO_SETTINGS_KEY, DesktopAppPromoSettings, save_desktop_app_promo_settings,
)

logger = logging.getLogger(__name__)
_SETTINGS = {"sales_experiment": SALES_EXPERIMENT_SETTINGS_KEY,
             "desktop_promo": DESKTOP_APP_PROMO_SETTINGS_KEY}
_AD_PAGE_SIZE = 30


class MarketingReadRequest(StrictModel):
    before_id: PositiveId | None = None


class SalesExperimentChange(StrictModel):
    kind: Literal["sales_experiment"]
    mode: Literal["off", "shadow", "ab", "treatment"]
    treatment_percent: Literal[0, 50, 90, 100]

    @field_validator("treatment_percent", mode="before")
    @classmethod
    def require_integer_percent(cls, value):
        if type(value) is not int:
            raise ValueError("Integer percentage required")
        return value


class PromoPlacements(StrictModel):
    home_prompt: bool
    lesson_end_promo: bool
    ad_promo: bool


class PromoPlatforms(StrictModel):
    macos: bool
    windows: bool
    android: bool
    ios: bool


class DesktopPromoChange(StrictModel):
    kind: Literal["desktop_promo"]
    enabled: bool
    daily_limit: Annotated[int, Field(strict=True, ge=1, le=3)]
    require_learning_progress: bool
    placements: PromoPlacements
    platforms: PromoPlatforms


class CourseAdChange(StrictModel):
    kind: Literal["course_ad"]
    ad_id: PositiveId
    operation: Literal["set_active", "delete"]
    is_active: bool | None = None

    @model_validator(mode="after")
    def exact_operation(self):
        if (self.operation == "set_active" and self.is_active is None
                or self.operation == "delete" and self.is_active is not None):
            raise ValueError("Exact course-ad operation required")
        return self


MarketingChange = Annotated[SalesExperimentChange | DesktopPromoChange | CourseAdChange,
                            Field(discriminator="kind")]


class PrepareMarketing(StrictModel):
    change: MarketingChange


class MarketingCommand(PrepareMarketing):
    expected_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def operation(self):
        target = (f"course_ad-{self.change.ad_id}" if self.change.kind == "course_ad"
                  else self.change.kind)
        return {"action": "marketing.update", "target": target, "payload": self.model_dump()}


class ExecuteMarketing(MarketingCommand):
    step_up_id: StepId


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _setting_revision(row):
    if row is not None and len(row.value.encode()) > 16_384:
        raise CommandError("marketing_configuration_unavailable", 503)
    return _hash(None if row is None else {"key": row.key, "value": row.value,
                                          "updated_at": _utc(row.updated_at).isoformat()})


def _setting_payload(kind, row):
    raw = row.value if row else None
    if kind == "sales_experiment":
        source = CourseSalesExperimentSettings.from_raw(raw).public_payload()
        result = {key: source[key] for key in (
            "mode", "treatment_percent", "effective_treatment_percent", "started_at", "saved_at")}
    else:
        settings = DesktopAppPromoSettings.from_raw(raw)
        result = {key: value for key, value in settings.storage_payload().items()
                  if key not in ("media_type", "media_path")}
        # Configuration presence only; this endpoint never stats a disk file
        # or exposes a media URL/path/provider reference to the browser.
        result["has_media"] = bool(settings.media_type and settings.media_path)
    return {**result, "revision_hash": _setting_revision(row), "target": kind}


def _ad_revision(row):
    raw = {key: getattr(row, key) for key in (
        "id", "title", "media_path", "media_type", "media_checksum",
        "language", "ad_type", "placements", "is_active")}
    raw["updated_at"] = _utc(row.updated_at).isoformat()
    return _hash(raw)


def _ad_payload(row):
    return {"id": row.id, "title": row.title[:120], "language": CourseAdService.normalize_language(row.language),
            "ad_type": CourseAdService.normalize_ad_type(row.ad_type),
            "media_type": CourseAdService.normalize_media_type(row.media_type),
            "is_active": bool(row.is_active), "created_at": _utc(row.created_at).isoformat(),
            "revision_hash": _ad_revision(row), "target": f"course_ad-{row.id}"}


def _ad_query():
    # The blob and legacy free-form fields are unnecessary for configuration
    # state/CAS. Never materialize private media or attempt backup restoration.
    return select(CourseAdCreative).options(defer(CourseAdCreative.media_blob),
        defer(CourseAdCreative.localized_copy), defer(CourseAdCreative.platform_links))


async def _authenticate(db, cookie, settings_obj):
    actor = await authenticate_admin_pwa_session(db, cookie, settings_obj)
    if actor is None or actor.auth_method != "webauthn":
        raise CommandError("admin_pwa_unauthorized", 401)
    return actor


async def _target(db, change, *, lock=False):
    if change.kind == "course_ad":
        query = _ad_query().where(CourseAdCreative.id == change.ad_id).execution_options(populate_existing=True)
        row = await db.scalar(query.with_for_update() if lock else query)
        if row is None:
            raise CommandError("course_ad_not_found", 404)
        return row, _ad_payload(row)
    key = _SETTINGS[change.kind]
    if lock:
        await BotSettingRepository(db).lock_key(key)
    query = select(BotSetting).where(BotSetting.key == key).execution_options(populate_existing=True)
    row = await db.scalar(query.with_for_update() if lock else query)
    return row, _setting_payload(change.kind, row)


async def read_marketing(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with db.begin():
        await _authenticate(db, session_cookie, settings_obj)
        rows = (await db.scalars(select(BotSetting).where(BotSetting.key.in_(_SETTINGS.values())).limit(2))).all()
        stored = {row.key: row for row in rows}
        settings = {kind: _setting_payload(kind, stored.get(key)) for kind, key in _SETTINGS.items()}
        query = _ad_query()
        if request.before_id is not None:
            query = query.where(CourseAdCreative.id < request.before_id)
        ads = (await db.scalars(query.order_by(CourseAdCreative.id.desc()).limit(_AD_PAGE_SIZE + 1))).all()
        items = [_ad_payload(row) for row in ads[:_AD_PAGE_SIZE]]
    return {**settings, "course_ads": {"items": items,
        "next_before_id": items[-1]["id"] if len(ads) > _AD_PAGE_SIZE else None}}


async def prepare_marketing(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with db.begin():
        await _authenticate(db, session_cookie, settings_obj)
        _, current = await _target(db, request.change)
        command = MarketingCommand(change=request.change, expected_hash=current["revision_hash"])
    return {"operation": command.operation(), "current": current}


def _cleanup_deleted_media(filename):
    # The filename comes only from the locked existing creative, never client
    # input. A malformed legacy path is retained for operator cleanup.
    if (not isinstance(filename, str) or filename != os.path.basename(filename)
            or not re.fullmatch(r"[A-Za-z0-9._+-]{1,160}\.(jpg|jpeg|png|webp|mp4|mov|webm|m4v)", filename)):
        return
    try:
        os.unlink(os.path.join(COURSE_AD_MEDIA_ROOT, filename))
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning("Deleted course ad media requires cleanup")


async def execute_marketing(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    command = MarketingCommand.model_validate(request.model_dump(exclude={"step_up_id"}))
    operation = command.operation()
    cleanup = None
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
        row, before = await _target(db, command.change, lock=True)
        now = datetime.now(timezone.utc)
        if (not _enabled(settings_obj) or not _authorized_admin(actor, settings_obj)
                or min(_utc(step.expires_at), _utc(session.expires_at)) <= now):
            raise CommandError("admin_pwa_step_up_denied", 403)
        if before["revision_hash"] != command.expected_hash:
            raise CommandError("confirmation_changed", 409)
        change = command.change
        if change.kind == "sales_experiment":
            await CourseSalesExperimentService(db).save_settings(
                change.model_dump(exclude={"kind"}), updated_by_telegram_id=actor.telegram_id)
            _, result = await _target(db, change)
        elif change.kind == "desktop_promo":
            await save_desktop_app_promo_settings(db, change.model_dump(exclude={"kind"}))
            _, result = await _target(db, change)
        elif change.operation == "set_active":
            await CourseAdService(db).set_active(change.ad_id, change.is_active)
            _, result = await _target(db, change)
        else:
            # Files may be referenced by another old creative. Never remove
            # shared media just because this creative is being deleted.
            shared = await db.scalar(select(CourseAdCreative.id).where(
                CourseAdCreative.media_path == row.media_path,
                CourseAdCreative.id != row.id).limit(1))
            path = await CourseAdService(db).delete(change.ad_id)
            cleanup = path if shared is None else None
            result = {"deleted_id": change.ad_id}
        audit_id = str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id, step_up_id=step.id,
            actor_user_id=actor.id, target_user_id=None, action=operation["action"],
            target=operation["target"], payload_hash=operation_digest(**operation),
            # Content-free evidence: creative copy/media paths never enter
            # command history; kind/target/hash bind the reviewed operation.
            result_json=json.dumps({"kind": change.kind, "before_hash": command.expected_hash,
                                    "after_hash": result.get("revision_hash"),
                                    "deleted_id": result.get("deleted_id")}, sort_keys=True)))
        await db.flush()
    if cleanup is not None:
        # Commit is authoritative; best-effort local cleanup never changes a
        # committed result or invites a destructive automatic API retry.
        try:
            await asyncio.to_thread(_cleanup_deleted_media, cleanup)
        except Exception:
            logger.warning("Deleted course ad media requires cleanup")
    return {"command_id": audit_id, "result": result}


def create_admin_pwa_marketing_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-marketing"])

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
                result = await task(db, session_cookie=cookie, request=parsed, settings_obj=settings_obj)
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error("Admin PWA marketing command unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        return JSONResponse({"ok": True, **result}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/marketing/read")
    async def read(request: Request):
        return await handle(request, read_marketing, MarketingReadRequest)

    @router.post("/api/admin/v1/marketing/prepare")
    async def prepare(request: Request):
        return await handle(request, prepare_marketing, PrepareMarketing)

    @router.post("/api/admin/v1/marketing/save")
    async def save(request: Request):
        return await handle(request, execute_marketing, ExecuteMarketing)

    return router
