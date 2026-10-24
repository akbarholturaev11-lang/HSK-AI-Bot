"""Fail-closed Apple Web Push subscription management — NO sender or permission prompt.

Private Admin PWA only. Endpoints/keys remain Fernet-encrypted at rest; the
public list never reveals delivery endpoints, key material or owner secrets.
"""
import base64
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit
from uuid import uuid4

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, select

from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_step_up import _locked_session
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa_push import AdminPwaPushSubscription

logger = logging.getLogger(__name__)
_HEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_B64 = re.compile(r"^[A-Za-z0-9_-]+$")
_MAX_ACTIVE = 4


class PushKeys(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    p256dh: str = Field(min_length=80, max_length=96)
    auth: str = Field(min_length=20, max_length=32)


class SubscribeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    platform: str = Field(pattern=r"^(iphone|mac)$", max_length=6)
    endpoint: str = Field(min_length=30, max_length=2048)
    keys: PushKeys


class RevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    subscription_id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class EmptyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def _decode(value: str) -> bytes:
    if not isinstance(value, str) or not _B64.fullmatch(value):
        raise ValueError("invalid_key_encoding")
    raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if base64.urlsafe_b64encode(raw).rstrip(b"=").decode() != value:
        raise ValueError("noncanonical_encoding")
    return raw


def _configuration(settings_obj):
    if (not getattr(settings_obj, "ADMIN_PWA_ENABLED", False)
            or not getattr(settings_obj, "ADMIN_PWA_PUSH_ENABLED", False)
            or getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", None) != "https://hskai.app"):
        return None
    try:
        public = str(getattr(settings_obj, "ADMIN_PWA_PUSH_VAPID_PUBLIC_KEY", ""))
        key = str(getattr(settings_obj, "ADMIN_PWA_PUSH_STORAGE_KEY", ""))
        pub_bytes = _decode(public)
        if len(pub_bytes) != 65 or pub_bytes[:1] != b"\x04":
            return None
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), pub_bytes)
        fernet = Fernet(key.encode("ascii"))
        return public, fernet
    except (ValueError, TypeError, UnicodeError):
        return None


def _validate_subscription(command: SubscribeRequest):
    try:
        url = urlsplit(command.endpoint)
        host = (url.hostname or "").lower()
        if (url.scheme != "https" or not host.endswith(".push.apple.com")
                or host == ".push.apple.com" or not url.path.startswith("/")
                or not url.path[1:] or url.query or url.fragment
                or url.username is not None or url.password is not None
                or url.port is not None or url.netloc != host):
            return None
        pub = _decode(command.keys.p256dh)
        auth = _decode(command.keys.auth)
        if len(pub) != 65 or pub[:1] != b"\x04" or len(auth) != 16:
            return None
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), pub)
        return hashlib.sha256(command.endpoint.encode("utf-8")).hexdigest()
    except (ValueError, TypeError, UnicodeError):
        return None


async def _authenticated(db, cookie, settings_obj, stamp):
    pair = await _locked_session(db, cookie, settings_obj, stamp)
    return pair[1] if pair is not None else None


async def push_list(db, *, cookie, settings_obj, stamp=None):
    stamp = stamp or datetime.now(timezone.utc)
    async with db.begin():
        actor = await _authenticated(db, cookie, settings_obj, stamp)
        if actor is None:
            return None
        rows = (await db.scalars(select(AdminPwaPushSubscription).where(
            AdminPwaPushSubscription.user_id == actor.id,
            AdminPwaPushSubscription.revoked_at.is_(None),
        ).order_by(AdminPwaPushSubscription.created_at.desc()).limit(_MAX_ACTIVE))).all()
        return [{"id": row.id, "platform": row.platform,
                 "created_at": row.created_at.isoformat(),
                 "updated_at": row.updated_at.isoformat()} for row in rows]


async def push_subscribe(db, *, cookie, settings_obj, command, fernet, stamp=None):
    digest = _validate_subscription(command)
    if digest is None:
        raise ValueError("invalid_subscription")
    stamp = stamp or datetime.now(timezone.utc)
    async with db.begin():
        actor = await _authenticated(db, cookie, settings_obj, stamp)
        if actor is None:
            return None
        existing = (await db.scalars(select(AdminPwaPushSubscription).where(
            AdminPwaPushSubscription.endpoint_hash == digest,
        ).with_for_update())).one_or_none()
        if existing is not None and existing.user_id != actor.id:
            return None
        if existing is None:
            active = (await db.scalar(select(func.count()).select_from(AdminPwaPushSubscription).where(
                AdminPwaPushSubscription.user_id == actor.id,
                AdminPwaPushSubscription.revoked_at.is_(None)))) or 0
            if active >= _MAX_ACTIVE:
                raise OverflowError("device_limit")
        payload = json.dumps({"endpoint": command.endpoint, "keys": command.keys.model_dump()},
                             sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        sealed = fernet.encrypt(payload.encode("ascii")).decode("ascii")
        if existing is None:
            existing = AdminPwaPushSubscription(
                id=str(uuid4()), user_id=int(actor.id), endpoint_hash=digest,
                encrypted_payload=sealed, platform=command.platform,
                created_at=stamp, updated_at=stamp,
            )
            db.add(existing)
        else:
            existing.encrypted_payload = sealed
            existing.platform = command.platform
            existing.updated_at = stamp
            existing.revoked_at = None
        await db.flush()
        return {"subscription_id": existing.id, "platform": existing.platform}


async def push_revoke(db, *, cookie, settings_obj, subscription_id, stamp=None):
    stamp = stamp or datetime.now(timezone.utc)
    async with db.begin():
        actor = await _authenticated(db, cookie, settings_obj, stamp)
        if actor is None:
            return None
        row = (await db.scalars(select(AdminPwaPushSubscription).where(
            AdminPwaPushSubscription.id == subscription_id,
            AdminPwaPushSubscription.user_id == actor.id,
        ).with_for_update())).one_or_none()
        if row is None:
            return None
        if row.revoked_at is None:
            row.revoked_at = stamp
            row.updated_at = stamp
            await db.flush()
        return True


def create_admin_pwa_push_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-push"])
    # Every route uses same-origin POST + current WebAuthn admin session.
    async def handle(request, operation):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        if not getattr(settings_obj, "ADMIN_PWA_PUSH_ENABLED", False):
            return _reply(404, "not_found")
        config = _configuration(settings_obj)
        if config is None:
            return _reply(503, "admin_pwa_push_unconfigured")
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        schema = SubscribeRequest if operation == "subscribe" else RevokeRequest if operation == "revoke" else EmptyRequest
        try:
            model = schema.model_validate(await _body(request, 4096))
        except ValidationError:
            return _reply(400, "admin_pwa_invalid_payload")
        if operation == "subscribe" and _validate_subscription(model) is None:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                if operation == "subscribe":
                    result = await push_subscribe(db, cookie=cookie, settings_obj=settings_obj,
                                                  command=model, fernet=config[1])
                elif operation == "revoke":
                    result = await push_revoke(db, cookie=cookie, settings_obj=settings_obj,
                                               subscription_id=model.subscription_id)
                else:
                    result = await push_list(db, cookie=cookie, settings_obj=settings_obj)
        except OverflowError:
            return _reply(409, "admin_pwa_push_device_limit")
        except Exception:
            # NEVER log push endpoint, encryption keys, subscription or request body.
            logger.error("Admin PWA push subscription operation unavailable")
            return _reply(503, "admin_pwa_push_unavailable")
        if result is None:
            return _reply(403, "admin_pwa_push_denied")
        if operation == "list":
            data = {"subscriptions": result, "vapid_public_key": config[0],
                    "sending_enabled": False}
        elif operation == "subscribe":
            data = result | {"sending_enabled": False}
        else:
            data = {"revoked": True}
        return JSONResponse({"ok": True, **data}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/push/list")
    async def list_devices(request: Request):
        return await handle(request, "list")

    @router.post("/api/admin/v1/push/subscribe")
    async def subscribe(request: Request):
        return await handle(request, "subscribe")

    @router.post("/api/admin/v1/push/revoke")
    async def revoke(request: Request):
        return await handle(request, "revoke")

    return router
