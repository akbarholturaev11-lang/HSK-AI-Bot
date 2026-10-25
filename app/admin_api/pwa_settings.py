"""Typed first-party settings commands, exact passkey proof and raw-state CAS.

Only fixed product settings are visible. Provider credentials, environment
secrets, payment/access grants and external MCP are outside this router.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, field_validator
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
from app.services.ai_provider import (
    ACTIVE_GEMINI_MODEL_KEY, GEMINI_MODEL_OPTIONS, _default_gemini_model,
    set_active_gemini_model_cache,
)
from app.services.help_settings_service import HELP_LANGS, HELP_VIDEO_FIELDS, HELP_VIDEO_FIELD_BY_KEY, normalize_help_url
from app.services.subscription_miniapp_service import PAYMENT_DETAILS_KEY, PAYMENT_DETAILS_ALIF_KEY
from app.services.support_contact_service import ADMIN_CONTACT_KEY, normalize_admin_contact, admin_contact_url

logger = logging.getLogger(__name__)
_PAYMENT_KEYS = {"dc_city": PAYMENT_DETAILS_KEY, "alif": PAYMENT_DETAILS_ALIF_KEY}
_ALL_KEYS = tuple(sorted((*_PAYMENT_KEYS.values(), ACTIVE_GEMINI_MODEL_KEY,
    ADMIN_CONTACT_KEY, *(field.setting_key(lang) for field in HELP_VIDEO_FIELDS for lang in HELP_LANGS))))


class EmptySettingsRequest(StrictModel):
    pass


class PaymentDetailsSetting(StrictModel):
    kind: Literal["payment_details"]
    bank: Literal["dc_city", "alif"]
    value: Annotated[str, Field(min_length=1, max_length=1500)]

    @field_validator("value")
    @classmethod
    def nonempty_details(cls, value):
        value = value.strip()
        if not value or any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            raise ValueError("Invalid payment details")
        return value


class AiModelSetting(StrictModel):
    kind: Literal["ai_model"]
    model: Annotated[str, Field(min_length=1, max_length=80)]

    @field_validator("model")
    @classmethod
    def allowed_model(cls, value):
        if value not in GEMINI_MODEL_OPTIONS:
            raise ValueError("Unknown AI model")
        return value


def _safe_help_link(value):
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Invalid help link")
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("https", "http", "tg") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Invalid help link")
        parsed.port
    except ValueError as exc:
        raise ValueError("Invalid help link") from exc


class HelpContactSetting(StrictModel):
    kind: Literal["help_contact"]
    value: Annotated[str, Field(max_length=512)]

    @field_validator("value")
    @classmethod
    def valid_contact(cls, value):
        value = normalize_admin_contact(value)
        if value:
            target = admin_contact_url(value)
            if not target:
                raise ValueError("Invalid help contact")
            _safe_help_link(target)
        return value


class HelpVideoSetting(StrictModel):
    kind: Literal["help_video"]
    key: Literal["course_hsk", "qa_mode", "voice_translator", "subscription"]
    lang: Literal["uz", "ru", "tj"]
    value: Annotated[str, Field(max_length=2048)]

    @field_validator("value")
    @classmethod
    def valid_video(cls, value):
        original = value.strip()
        value = normalize_help_url(value)
        if original and not value:
            raise ValueError("Invalid help video URL")
        if value:
            _safe_help_link(value)
        return value


SettingChange = Annotated[PaymentDetailsSetting | AiModelSetting |
                          HelpContactSetting | HelpVideoSetting, Field(discriminator="kind")]


class PrepareSettings(StrictModel):
    change: SettingChange


class SettingsCommand(PrepareSettings):
    expected_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def operation(self):
        change = self.change
        target = change.kind.replace("_", "-")
        if isinstance(change, PaymentDetailsSetting):
            target += "-" + change.bank.replace("_", "-")
        elif isinstance(change, HelpVideoSetting):
            target += "-" + change.key.replace("_", "-") + "-" + change.lang
        return {"action": "settings.update", "target": target, "payload": self.model_dump()}


class ExecuteSettings(SettingsCommand):
    step_up_id: StepId


def _keys(change):
    if isinstance(change, PaymentDetailsSetting):
        return (_PAYMENT_KEYS[change.bank],)
    if isinstance(change, AiModelSetting):
        return (ACTIVE_GEMINI_MODEL_KEY,)
    if isinstance(change, HelpContactSetting):
        return (ADMIN_CONTACT_KEY,)
    return (HELP_VIDEO_FIELD_BY_KEY[change.key].setting_key(change.lang),)


async def _rows(db, keys, *, lock=False):
    if lock:
        repo = BotSettingRepository(db)
        for key in sorted(keys):
            await repo.lock_key(key)
    query = select(BotSetting).where(BotSetting.key.in_(keys)).order_by(BotSetting.key).limit(len(keys))
    query = query.execution_options(populate_existing=True)
    rows = (await db.scalars(query.with_for_update() if lock else query)).all()
    return {row.key: row for row in rows}


def _revision(rows, keys):
    # Raw state and timestamps, including explicit absence, protect against
    # normalization hiding intervening edits or an ABA write.
    state = [{"key": key, "row": None if key not in rows else {
        "value": rows[key].value, "updated_at": _utc(rows[key].updated_at).isoformat(),
    }} for key in sorted(keys)]
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _get(rows, key):
    row = rows.get(key)
    return row.value if row is not None else None


def _public_settings(rows, settings_obj):
    # Same stored/default semantics as the shared subscription and AI readers,
    # without fetching settings individually or consulting the live AI cache.
    stored_model = (_get(rows, ACTIVE_GEMINI_MODEL_KEY) or "").strip()
    city_details = (_get(rows, PAYMENT_DETAILS_KEY) or "").strip()
    return {
        "payment_details": {
            "dc_city": city_details or (getattr(settings_obj, "PAYMENT_DETAILS", "") or "").strip(),
            "alif": (_get(rows, PAYMENT_DETAILS_ALIF_KEY) or "").strip(),
        },
        "ai_model": {"model": stored_model if stored_model in GEMINI_MODEL_OPTIONS else _default_gemini_model()},
        "help_contact": {"value": normalize_admin_contact(_get(rows, ADMIN_CONTACT_KEY))},
        "help_videos": [{"key": field.key, "lang": lang,
            "value": normalize_help_url(_get(rows, field.setting_key(lang)))}
            for field in HELP_VIDEO_FIELDS for lang in HELP_LANGS],
    }


def _current(rows, change, settings_obj):
    public = _public_settings(rows, settings_obj)
    if isinstance(change, PaymentDetailsSetting):
        value = {"bank": change.bank, "value": public["payment_details"][change.bank]}
    elif isinstance(change, HelpVideoSetting):
        value = next(item for item in public["help_videos"] if item["key"] == change.key and item["lang"] == change.lang)
    else:
        value = public[change.kind]
    return {"kind": change.kind, **value}


async def _authenticate(db, cookie, settings_obj):
    actor = await authenticate_admin_pwa_session(db, cookie, settings_obj)
    if actor is None or actor.auth_method != "webauthn":
        raise CommandError("admin_pwa_unauthorized", 401)
    return actor


async def read_settings(db, *, session_cookie, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with read_transaction(db):
        await _authenticate(db, session_cookie, settings_obj)
        settings = _public_settings(await _rows(db, _ALL_KEYS), settings_obj)
    return {"settings": settings, "options": {
        "payment_banks": list(_PAYMENT_KEYS), "ai_models": list(GEMINI_MODEL_OPTIONS),
        "help_video_keys": [field.key for field in HELP_VIDEO_FIELDS], "help_languages": list(HELP_LANGS),
    }}


async def prepare_settings(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with read_transaction(db):
        await _authenticate(db, session_cookie, settings_obj)
        keys = _keys(request.change)
        rows = await _rows(db, keys)
        command = SettingsCommand(change=request.change, expected_hash=_revision(rows, keys))
        current = _current(rows, request.change, settings_obj)
        if operation_digest(**command.operation()) is None:
            raise CommandError("admin_pwa_invalid_payload", 400)
    return {"operation": command.operation(), "current": current}


async def _write(db, change):
    repo = BotSettingRepository(db)
    if isinstance(change, PaymentDetailsSetting):
        await repo.set(_PAYMENT_KEYS[change.bank], change.value)
    elif isinstance(change, AiModelSetting):
        await repo.set(ACTIVE_GEMINI_MODEL_KEY, change.model)
    elif isinstance(change, HelpContactSetting):
        await repo.set(ADMIN_CONTACT_KEY, change.value)
    else:
        await repo.set(HELP_VIDEO_FIELD_BY_KEY[change.key].setting_key(change.lang), change.value)


async def execute_settings(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    command = SettingsCommand.model_validate(request.model_dump(exclude={"step_up_id"}))
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
        keys = _keys(command.change)
        rows = await _rows(db, keys, lock=True)
        now = datetime.now(timezone.utc)
        if (not _enabled(settings_obj) or not _authorized_admin(actor, settings_obj)
                or session.revoked_at is not None
                or min(_utc(step.expires_at), _utc(session.expires_at)) <= now):
            raise CommandError("admin_pwa_step_up_denied", 403)
        if _revision(rows, keys) != command.expected_hash:
            raise CommandError("confirmation_changed", 409)
        await _write(db, command.change)
        after_rows = await _rows(db, keys)
        revision = _revision(after_rows, keys)
        setting = _current(after_rows, command.change, settings_obj)
        audit_id = str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id, step_up_id=step.id, actor_user_id=actor.id,
            target_user_id=None, action=operation["action"], target=operation["target"],
            payload_hash=operation_digest(**operation), result_json=json.dumps({
                "kind": command.change.kind, "previous_hash": command.expected_hash,
                "result_hash": revision}, sort_keys=True)))
        await db.flush()
    # Updating the in-process model cache before commit could advertise a value
    # whose configuration/audit transaction subsequently failed.
    if isinstance(command.change, AiModelSetting):
        set_active_gemini_model_cache(command.change.model)
    return {"command_id": audit_id, "setting": setting, "revision_hash": revision}


def create_admin_pwa_settings_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-settings"])

    async def handle(request, task, schema):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            parsed = schema.model_validate(await _body(request, 16 * 1024))
        except ValidationError:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                result = await task(db, session_cookie=cookie, settings_obj=settings_obj,
                    **({} if schema is EmptySettingsRequest else {"request": parsed}))
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            # No request values, bank details, contact links or SQL parameters.
            logger.error("Admin PWA settings command unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        return JSONResponse({"ok": True, **result}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/settings/read")
    async def read(request: Request):
        return await handle(request, read_settings, EmptySettingsRequest)

    @router.post("/api/admin/v1/settings/prepare")
    async def prepare(request: Request):
        return await handle(request, prepare_settings, PrepareSettings)

    @router.post("/api/admin/v1/settings/save")
    async def save(request: Request):
        return await handle(request, execute_settings, ExecuteSettings)

    return router
