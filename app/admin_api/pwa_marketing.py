"""Bounded first-party marketing configuration and signed media actions.

Exact current state and passkey proof authorize one existing shared-service
command. Media is restricted to the specific validated assets below; no
arbitrary setting keys, student targeting or MCP access is added.
"""
import asyncio
import hashlib
import html
import io
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, field_validator, model_validator
from sqlalchemy import select, text
from sqlalchemy.orm import defer

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _gate, _reply
from app.admin_api.pwa_payment_review import PositiveId, StrictModel
from app.admin_api.pwa_sessions import (
    ADMIN_PWA_COOKIE_NAME, _authorized_admin, authenticate_admin_pwa_session,
)
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post, _no_duplicate_json_keys
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.bot_setting import BotSetting
from app.db.models.course_ad import CourseAdCreative
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.ad_campaign_repo import AdCampaignRepository
from app.services.broadcast_translation_service import encode_localized_broadcast_text
from app.services.course_ad_service import COURSE_AD_MEDIA_ROOT, CourseAdService
from app.services.course_sales_experiment_service import (
    SALES_EXPERIMENT_SETTINGS_KEY, CourseSalesExperimentService, CourseSalesExperimentSettings,
)
from app.services.desktop_app_promo_settings_service import (
    DESKTOP_APP_PROMO_MEDIA_ROOT, DESKTOP_APP_PROMO_SETTINGS_KEY,
    DesktopAppPromoSettings,
    desktop_app_promo_media_full_path, get_desktop_app_promo_settings,
    save_desktop_app_promo_settings,
)

logger = logging.getLogger(__name__)
_SETTINGS = {"sales_experiment": SALES_EXPERIMENT_SETTINGS_KEY,
             "desktop_promo": DESKTOP_APP_PROMO_SETTINGS_KEY}
_AD_PAGE_SIZE = 30
_PWA_PROMO_IMAGE_MAX_BYTES = 2 * 1024 * 1024
_PWA_PROMO_IMAGE_MAX_PIXELS = 8_000_000
_PWA_PROMO_IMAGE_TYPES = {
    "image/jpeg": ("JPEG", ".jpg"),
    "image/png": ("PNG", ".png"),
    "image/webp": ("WEBP", ".webp"),
}


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
    media_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    media_size: Annotated[int, Field(strict=True, ge=1, le=_PWA_PROMO_IMAGE_MAX_BYTES)] | None = None
    clear_media: bool = False

    @model_validator(mode="after")
    def exact_media_operation(self):
        if (self.media_sha256 is None) != (self.media_size is None):
            raise ValueError("Media digest and byte count must be supplied together")
        if self.clear_media and self.media_sha256 is not None:
            raise ValueError("Clear and replace are separate media operations")
        return self


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


class CampaignTexts(StrictModel):
    uz: Annotated[str, Field(min_length=2, max_length=3500)]
    ru: Annotated[str, Field(min_length=2, max_length=3500)]
    tj: Annotated[str, Field(min_length=2, max_length=3500)]

    @field_validator("uz", "ru", "tj")
    @classmethod
    def valid_text(cls, value):
        value = value.strip()
        try:
            utf16_length = len(value.encode("utf-16-le")) // 2
        except UnicodeEncodeError as exc:
            raise ValueError("Invalid Unicode text") from exc
        if len(value) < 2 or utf16_length > 3500:
            raise ValueError("Invalid Telegram text length")
        if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            raise ValueError("Control characters are not allowed")
        # Existing ad delivery uses Telegram HTML parse mode. Store plain text
        # as escaped entities so authored markup can never become Bot markup.
        escaped = html.escape(value, quote=False)
        if len(escaped.encode("utf-16-le")) // 2 > 3500:
            raise ValueError("Escaped Telegram text is too long")
        return value


class CampaignDraftChange(StrictModel):
    kind: Literal["campaign_draft"]
    title: Annotated[str, Field(min_length=1, max_length=120)]
    texts: CampaignTexts
    languages: Annotated[list[Literal["uz", "ru", "tj"]], Field(min_length=1, max_length=3)]
    track: Literal["hsk20", "hsk30"] | None = None
    level: Literal["beginner", "hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3"] | None = None
    duration_hours: Annotated[int, Field(strict=True, ge=1, le=720)] = 24
    include_active_subscribers: bool = False

    @field_validator("title")
    @classmethod
    def valid_title(cls, value):
        value = value.strip()
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("Invalid Unicode title") from exc
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Invalid campaign title")
        return value

    @field_validator("languages")
    @classmethod
    def unique_languages(cls, value):
        if not value or len(value) != len(set(value)):
            raise ValueError("Select unique target languages")
        return sorted(value)


MarketingChange = Annotated[SalesExperimentChange | DesktopPromoChange | CourseAdChange | CampaignDraftChange,
                            Field(discriminator="kind")]


class PrepareMarketing(StrictModel):
    change: MarketingChange


class MarketingCommand(PrepareMarketing):
    expected_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def operation(self):
        target = (f"course_ad-{self.change.ad_id}" if self.change.kind == "course_ad"
                  else self.change.kind)
        payload = self.model_dump()
        if self.change.kind == "campaign_draft":
            payload["change"] = self.change.model_dump(exclude={"texts"})
            payload["content_hash"] = _hash(self.change.texts.model_dump())
        return {"action": "marketing.update", "target": target, "payload": payload}


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
    if change.kind == "campaign_draft":
        return None, {"new_draft": True, "revision_hash": _hash({"campaign_draft": "new"})}
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
    result = {"operation": command.operation(), "current": current}
    if request.change.kind == "campaign_draft":
        result["execute_payload"] = command.model_dump()
        result["proposed"] = {"kind": "campaign_draft", **request.change.model_dump(),
                               "status": "paused_draft"}
    return result


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


def _validate_promo_image(data: bytes, content_type: str) -> str:
    """Decode a small raster image and return its server-owned extension."""
    if (not isinstance(data, bytes) or not data or len(data) > _PWA_PROMO_IMAGE_MAX_BYTES
            or content_type not in _PWA_PROMO_IMAGE_TYPES):
        raise CommandError("admin_pwa_invalid_media", 400)
    expected_format, extension = _PWA_PROMO_IMAGE_TYPES[content_type]
    try:
        from PIL import Image
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                width, height = image.size
                if (image.format != expected_format or width < 1 or height < 1
                        or width * height > _PWA_PROMO_IMAGE_MAX_PIXELS
                        or getattr(image, "n_frames", 1) != 1):
                    raise CommandError("admin_pwa_invalid_media", 400)
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                image.load()
    except CommandError:
        raise
    except Exception as exc:
        raise CommandError("admin_pwa_invalid_media", 400) from exc
    return extension


def _write_promo_image(data: bytes, extension: str) -> str:
    """Atomically publish a server-named image; never trust a client filename."""
    os.makedirs(DESKTOP_APP_PROMO_MEDIA_ROOT, exist_ok=True)
    token = uuid4().hex
    filename = f"desktop_app_promo_pwa_{token}{extension}"
    final_path = os.path.join(DESKTOP_APP_PROMO_MEDIA_ROOT, filename)
    temporary_path = os.path.join(DESKTOP_APP_PROMO_MEDIA_ROOT, f".admin-pwa-{token}.tmp")
    descriptor = os.open(temporary_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.replace(temporary_path, final_path)
    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise
    return filename


def _cleanup_promo_media(filename):
    # The caller supplies only a server-generated new filename or the current
    # normalized setting value. Reject path manipulation before unlinking.
    if not isinstance(filename, str) or filename != os.path.basename(filename):
        return
    path = desktop_app_promo_media_full_path(filename)
    if path is None:
        return
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning("Desktop promo media requires cleanup")


async def execute_marketing(db, *, session_cookie, request, settings_obj,
                            media_bytes: bytes | None = None,
                            media_content_type: str | None = None):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    command = MarketingCommand.model_validate(request.model_dump(exclude={"step_up_id"}))
    operation = command.operation()
    cleanup = None
    cleanup_promo = None
    new_promo_filename = None
    change = command.change
    if change.kind == "desktop_promo" and change.media_sha256 is not None:
        if (media_bytes is None or len(media_bytes) != change.media_size
                or hashlib.sha256(media_bytes).hexdigest() != change.media_sha256):
            raise CommandError("admin_pwa_invalid_media", 400)
        media_extension = _validate_promo_image(media_bytes, media_content_type or "")
    elif media_bytes is not None:
        raise CommandError("admin_pwa_invalid_media", 400)
    else:
        media_extension = None

    try:
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
            if change.kind == "campaign_draft":
                now = datetime.now(timezone.utc)
                safe_texts = {language: html.escape(text, quote=False)
                              for language, text in change.texts.model_dump().items()}
                campaign = await AdCampaignRepository(db).create(
                    title=change.title,
                    message_text=encode_localized_broadcast_text(safe_texts),
                    content_type="text",
                    media_file_id=None,
                    starts_at=now,
                    ends_at=now + timedelta(hours=change.duration_hours),
                    send_count_total=1,
                    target_languages=change.languages,
                    target_track=change.track,
                    target_level=change.level,
                    include_active_subscribers=change.include_active_subscribers,
                    created_by_telegram_id=actor.telegram_id,
                    is_active=False,
                )
                result = {"id": campaign.id, "title": campaign.title,
                          "status": "paused_draft", "is_active": False,
                          "starts_at": _utc(campaign.starts_at).isoformat(),
                          "ends_at": _utc(campaign.ends_at).isoformat(),
                          "rounds_total": campaign.send_count_total}
            elif change.kind == "sales_experiment":
                await CourseSalesExperimentService(db).save_settings(
                    change.model_dump(exclude={"kind"}), updated_by_telegram_id=actor.telegram_id)
                _, result = await _target(db, change)
            elif change.kind == "desktop_promo":
                previous = await get_desktop_app_promo_settings(db)
                promo_change = change.model_dump(exclude={
                    "kind", "media_sha256", "media_size", "clear_media",
                })
                if change.media_sha256 is not None:
                    new_promo_filename = await asyncio.to_thread(
                        _write_promo_image, media_bytes, media_extension,
                    )
                    promo_change.update(media_type="photo", media_path=new_promo_filename)
                elif change.clear_media:
                    promo_change.update(media_type=None, media_path=None)
                promo = await save_desktop_app_promo_settings(db, promo_change)
                if previous.media_path and previous.media_path != promo.media_path:
                    cleanup_promo = previous.media_path
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
            if change.kind == "campaign_draft":
                audit_result = {"kind": change.kind, "campaign_id": result["id"],
                                "content_hash": _hash(change.texts.model_dump())}
            else:
                audit_result = {"kind": change.kind, "before_hash": command.expected_hash,
                                "after_hash": result.get("revision_hash"),
                                "deleted_id": result.get("deleted_id")}
            db.add(AdminPwaCommandAudit(id=audit_id, step_up_id=step.id,
                actor_user_id=actor.id, target_user_id=None, action=operation["action"],
                target=operation["target"], payload_hash=operation_digest(**operation),
                # Content-free evidence: campaign text, media bytes and local
                # media paths never enter command history.
                result_json=json.dumps(audit_result, sort_keys=True)))
            await db.flush()
    except Exception:
        if new_promo_filename is not None:
            referenced = True  # Preserve the file if commit outcome cannot be determined.
            try:
                await db.rollback()
                async with db.begin():
                    current = await get_desktop_app_promo_settings(db)
                    referenced = current.media_path == new_promo_filename
            except Exception:
                logger.warning("Desktop promo media commit outcome requires operator review")
            if not referenced:
                try:
                    await asyncio.to_thread(_cleanup_promo_media, new_promo_filename)
                except Exception:
                    logger.warning("Uncommitted desktop promo media requires cleanup")
        raise
    if cleanup is not None:
        # Commit is authoritative; best-effort local cleanup never changes a
        # committed result or invites a destructive automatic API retry.
        try:
            await asyncio.to_thread(_cleanup_deleted_media, cleanup)
        except Exception:
            logger.warning("Deleted course ad media requires cleanup")
    if cleanup_promo is not None:
        try:
            await asyncio.to_thread(_cleanup_promo_media, cleanup_promo)
        except Exception:
            logger.warning("Replaced desktop promo media requires cleanup")
    return {"command_id": audit_id, "result": result}


def create_admin_pwa_marketing_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-marketing"])

    async def handle(request, task, schema, *, body_limit=4096):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            parsed = schema.model_validate(await _body(request, body_limit))
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
        return await handle(request, prepare_marketing, PrepareMarketing, body_limit=48_000)

    @router.post("/api/admin/v1/marketing/media/save")
    async def save_media(request: Request):
        failure = _gate(request, settings_obj)
        if failure is not None:
            return failure
        origin = str(getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", "") or "")
        if (request.headers.getlist("origin") != [origin]
                or request.headers.get("sec-fetch-site", "same-origin") != "same-origin"):
            return _reply(403, "admin_pwa_csrf")
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in _PWA_PROMO_IMAGE_TYPES:
            return _reply(415, "unsupported_media_type")
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        encoded_command = request.headers.get("x-admin-pwa-command", "")
        if not encoded_command or len(encoded_command) > 8192:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            raw_command = json.loads(encoded_command, object_pairs_hook=_no_duplicate_json_keys)
            parsed = ExecuteMarketing.model_validate(raw_command)
        except (ValidationError, ValueError, TypeError):
            return _reply(400, "admin_pwa_invalid_payload")
        if (parsed.change.kind != "desktop_promo"
                or parsed.change.media_sha256 is None
                or parsed.change.media_size is None):
            return _reply(400, "admin_pwa_invalid_payload")
        declared_length = request.headers.get("content-length")
        if declared_length:
            try:
                if int(declared_length) > _PWA_PROMO_IMAGE_MAX_BYTES:
                    return _reply(413, "admin_pwa_media_too_large")
            except ValueError:
                return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                async with db.begin():
                    await _authenticate(db, cookie, settings_obj)
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error("Admin PWA marketing media authentication unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > _PWA_PROMO_IMAGE_MAX_BYTES:
                return _reply(413, "admin_pwa_media_too_large")
            data.extend(chunk)
        if len(data) != parsed.change.media_size:
            return _reply(400, "admin_pwa_invalid_media")
        try:
            async with session_factory() as db:
                result = await execute_marketing(
                    db, session_cookie=cookie, request=parsed, settings_obj=settings_obj,
                    media_bytes=bytes(data), media_content_type=content_type,
                )
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error("Admin PWA marketing media command unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        return JSONResponse({"ok": True, **result}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/marketing/save")
    async def save(request: Request):
        return await handle(request, execute_marketing, ExecuteMarketing, body_limit=48_000)

    return router
