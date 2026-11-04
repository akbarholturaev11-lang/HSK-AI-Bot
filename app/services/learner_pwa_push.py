"""Opt-in, learner-account-bound Web Push for existing PWA notice sources.

This service never shares Admin PWA subscriptions or identity. Outbox rows keep
only event ownership metadata; notification text is intentionally generic.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import uuid4

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError

from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.account_notice_delivery import AccountNoticeDelivery
from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.learner_pwa_push import LearnerPwaPushOutbox, LearnerPwaPushSubscription
from app.db.models.user import User
from app.db.models.payment import Payment
from app.services.user_access_state_service import UserAccessState, UserAccessStateService
from app.services.webpush_transport import send_webpush


logger = logging.getLogger(__name__)
_B64 = re.compile(r"^[A-Za-z0-9_-]+$")
_MAX_ACTIVE_SUBSCRIPTIONS = 4
_MAX_ATTEMPTS = 4
_LEASE_SECONDS = 45
_MAX_BATCH = 50
_PUSH_PATH = "/iphone-pwa/course?notice=1"
_NO_STORE_EVENT = {"course", "account", "payment"}


class PushKeys(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    p256dh: str = Field(min_length=80, max_length=96)
    auth: str = Field(min_length=20, max_length=32)


class SubscribeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    endpoint: str = Field(min_length=30, max_length=2048)
    keys: PushKeys


class RevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    subscription_id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _decode(value: str) -> bytes:
    if not isinstance(value, str) or not _B64.fullmatch(value):
        raise ValueError("invalid_key_encoding")
    raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != value:
        raise ValueError("noncanonical_encoding")
    return raw


def _validate_subscription(command: SubscribeRequest) -> str | None:
    try:
        url = urlsplit(command.endpoint)
        host = (url.hostname or "").lower()
        if (
            url.scheme != "https" or not host.endswith(".push.apple.com")
            or host == ".push.apple.com" or not url.path.startswith("/")
            or not url.path[1:] or url.query or url.fragment
            or url.username is not None or url.password is not None
            or url.port is not None or url.netloc.lower() != host
        ):
            return None
        public_key = _decode(command.keys.p256dh)
        auth_secret = _decode(command.keys.auth)
        if len(public_key) != 65 or public_key[:1] != b"\x04" or len(auth_secret) != 16:
            return None
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), public_key)
        return hashlib.sha256(command.endpoint.encode("utf-8")).hexdigest()
    except (TypeError, ValueError, UnicodeError):
        return None


def subscription_config(settings_obj):
    if (
        getattr(settings_obj, "PWA_AUTH_ENABLED", False) is not True
        or getattr(settings_obj, "PWA_PUSH_ENABLED", False) is not True
    ):
        return None
    try:
        public = str(getattr(settings_obj, "PWA_PUSH_VAPID_PUBLIC_KEY", ""))
        public_bytes = _decode(public)
        if len(public_bytes) != 65 or public_bytes[:1] != b"\x04":
            return None
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), public_bytes)
        storage = Fernet(str(getattr(settings_obj, "PWA_PUSH_STORAGE_KEY", "")).encode("ascii"))
        return public, storage
    except (TypeError, ValueError, UnicodeError):
        return None


def sender_config(settings_obj):
    """Fail closed unless feature flags, storage key and matching VAPID pair pass."""
    if getattr(settings_obj, "PWA_PUSH_SEND_ENABLED", False) is not True:
        return None
    base = subscription_config(settings_obj)
    if base is None:
        return None
    try:
        encoded_private = str(getattr(settings_obj, "PWA_PUSH_VAPID_PRIVATE_KEY", ""))
        raw_private = _decode(encoded_private)
        if len(raw_private) != 32:
            return None
        private_key = ec.derive_private_key(int.from_bytes(raw_private, "big"), ec.SECP256R1())
        expected_public = private_key.public_key().public_bytes(
            Encoding.X962, PublicFormat.UncompressedPoint,
        )
        if expected_public != _decode(base[0]):
            return None
        subject = str(getattr(settings_obj, "PWA_PUSH_VAPID_SUBJECT", ""))
        if not 8 <= len(subject) <= 200 or any(char.isspace() for char in subject):
            return None
        parsed = urlsplit(subject)
        if parsed.scheme == "mailto":
            if not parsed.path or "@" not in parsed.path or parsed.query or parsed.fragment:
                return None
        elif parsed.scheme == "https":
            if not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                return None
        else:
            return None
        return encoded_private, subject, base[1]
    except (TypeError, ValueError, UnicodeError):
        return None


def _active_device_sessions_query(now):
    return select(DesktopSession.device_id).where(
        DesktopSession.device_id == DesktopDevice.id,
        DesktopSession.revoked_at.is_(None),
        DesktopSession.expires_at > now,
    )


async def active_subscriptions(session, user_id: int, *, now: datetime | None = None, limit=5):
    """Return metadata only for current, authenticated PWA installations."""
    stamp = _utc(now or datetime.now(timezone.utc))
    rows = (await session.execute(
        select(LearnerPwaPushSubscription.id, LearnerPwaPushSubscription.device_id)
        .join(DesktopDevice, DesktopDevice.id == LearnerPwaPushSubscription.device_id)
        .where(
            DesktopDevice.user_id == user_id,
            DesktopDevice.platform == "pwa",
            DesktopDevice.revoked_at.is_(None),
            LearnerPwaPushSubscription.revoked_at.is_(None),
            _active_device_sessions_query(stamp).exists(),
        )
        .order_by(LearnerPwaPushSubscription.updated_at.desc(), LearnerPwaPushSubscription.id)
        .limit(limit)
    )).all()
    return [(str(subscription_id), str(device_id)) for subscription_id, device_id in rows]


async def enqueue_event(session, *, user_id, source, source_id, language, now=None) -> int:
    """Atomically enqueue one content-free event for each current PWA device."""
    if type(user_id) is not int or user_id <= 0 or source not in _NO_STORE_EVENT:
        return 0
    if type(source_id) is not int or source_id <= 0:
        return 0
    stamp = _utc(now or datetime.now(timezone.utc))
    endpoints = await active_subscriptions(session, user_id, now=stamp)
    if len(endpoints) > _MAX_ACTIVE_SUBSCRIPTIONS:
        logger.warning("Learner PWA push inventory exceeds reviewed limit")
        endpoints = endpoints[:_MAX_ACTIVE_SUBSCRIPTIONS]
    language = language if language in {"uz", "ru", "tj"} else "ru"
    event_key = hashlib.sha256(f"{user_id}:{source}:{source_id}".encode("ascii")).hexdigest()
    queued = 0
    for subscription_id, _device_id in endpoints:
        row = LearnerPwaPushOutbox(
            id=str(uuid4()), user_id=user_id, subscription_id=subscription_id,
            event_key=event_key, source=source, source_id=source_id, language=language,
            state="pending", attempts=0, created_at=stamp, updated_at=stamp,
            next_attempt_at=stamp,
        )
        try:
            async with session.begin_nested():
                session.add(row)
                await session.flush()
            queued += 1
        except IntegrityError:
            # A repeated source event must not create a second delivery.
            continue
    return queued


async def revoke_device_subscriptions(session, device_id: str, *, now=None) -> int:
    stamp = _utc(now or datetime.now(timezone.utc))
    rows = (await session.scalars(select(LearnerPwaPushSubscription).where(
        LearnerPwaPushSubscription.device_id == device_id,
        LearnerPwaPushSubscription.revoked_at.is_(None),
    ).with_for_update())).all()
    for row in rows:
        row.revoked_at = stamp
        row.updated_at = stamp
        await session.execute(update(LearnerPwaPushOutbox).where(
            LearnerPwaPushOutbox.subscription_id == row.id,
            LearnerPwaPushOutbox.state.in_(("pending", "retry", "leased")),
        ).values(state="cancelled", lease_owner=None, lease_expires_at=None,
                 next_attempt_at=None, updated_at=stamp))
    return len(rows)


async def subscription_status(session, *, device_id: str):
    row = (await session.scalars(select(LearnerPwaPushSubscription).where(
        LearnerPwaPushSubscription.device_id == device_id,
        LearnerPwaPushSubscription.revoked_at.is_(None),
    ).limit(1))).one_or_none()
    return row


async def subscribe(session, *, user_id: int, device_id: str, command: SubscribeRequest,
                    fernet: Fernet, now=None):
    digest = _validate_subscription(command)
    if digest is None:
        raise ValueError("invalid_subscription")
    stamp = _utc(now or datetime.now(timezone.utc))
    await session.execute(select(User.id).where(User.id == user_id).with_for_update())
    device = (await session.execute(select(DesktopDevice).where(
        DesktopDevice.id == device_id,
        DesktopDevice.user_id == user_id,
        DesktopDevice.platform == "pwa",
        DesktopDevice.revoked_at.is_(None),
    ).with_for_update())).scalar_one_or_none()
    login = (await session.execute(select(DesktopSession).where(
        DesktopSession.device_id == device_id,
        DesktopSession.revoked_at.is_(None),
        DesktopSession.expires_at > stamp,
    ).order_by(DesktopSession.expires_at.desc(), DesktopSession.id).limit(1)
      .with_for_update())).scalar_one_or_none()
    if device is None or login is None:
        return None

    existing = (await session.scalars(select(LearnerPwaPushSubscription).where(
        LearnerPwaPushSubscription.endpoint_hash == digest,
    ).with_for_update())).one_or_none()
    if existing is not None and existing.device_id != device_id:
        previous = await session.get(DesktopDevice, existing.device_id, with_for_update=True)
        if previous is None or previous.platform != "pwa":
            return None
        active_previous_session = await session.scalar(select(DesktopSession.id).where(
            DesktopSession.device_id == existing.device_id,
            DesktopSession.revoked_at.is_(None), DesktopSession.expires_at > stamp,
        ).limit(1))
        if active_previous_session is not None:
            # The same endpoint cannot be claimed while a different account session is active.
            return None
        await session.execute(update(LearnerPwaPushOutbox).where(
            LearnerPwaPushOutbox.subscription_id == existing.id,
            LearnerPwaPushOutbox.state.in_(("pending", "retry", "leased")),
        ).values(state="cancelled", lease_owner=None, lease_expires_at=None,
                 next_attempt_at=None, updated_at=stamp))
        existing.device_id = device_id
        existing.revoked_at = None

    by_device = (await session.scalars(select(LearnerPwaPushSubscription).where(
        LearnerPwaPushSubscription.device_id == device_id,
    ).with_for_update())).one_or_none()
    target = existing or by_device
    if target is None:
        count = await session.scalar(
            select(func.count()).select_from(LearnerPwaPushSubscription)
            .join(DesktopDevice, DesktopDevice.id == LearnerPwaPushSubscription.device_id)
            .where(DesktopDevice.user_id == user_id, DesktopDevice.platform == "pwa",
                   DesktopDevice.revoked_at.is_(None), LearnerPwaPushSubscription.revoked_at.is_(None))
        ) or 0
        if count >= _MAX_ACTIVE_SUBSCRIPTIONS:
            raise OverflowError("device_limit")
        target = LearnerPwaPushSubscription(
            id=str(uuid4()), device_id=device_id, endpoint_hash=digest,
            encrypted_payload="", created_at=stamp, updated_at=stamp,
        )
        session.add(target)
    elif target.device_id != device_id:
        return None

    payload = json.dumps(
        {"endpoint": command.endpoint, "keys": command.keys.model_dump()},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    target.endpoint_hash = digest
    target.encrypted_payload = fernet.encrypt(payload.encode("ascii")).decode("ascii")
    target.updated_at = stamp
    target.revoked_at = None
    await session.flush()
    return {"subscription_id": target.id}


async def revoke(session, *, device_id: str, subscription_id: str, now=None):
    stamp = _utc(now or datetime.now(timezone.utc))
    row = (await session.scalars(select(LearnerPwaPushSubscription).where(
        LearnerPwaPushSubscription.id == subscription_id,
        LearnerPwaPushSubscription.device_id == device_id,
    ).with_for_update())).one_or_none()
    if row is None:
        return False
    if row.revoked_at is None:
        row.revoked_at = stamp
        row.updated_at = stamp
        await session.execute(update(LearnerPwaPushOutbox).where(
            LearnerPwaPushOutbox.subscription_id == row.id,
            LearnerPwaPushOutbox.state.in_(("pending", "retry", "leased")),
        ).values(state="cancelled", lease_owner=None, lease_expires_at=None,
                 next_attempt_at=None, updated_at=stamp))
        await session.flush()
    return True


def _http_status(exception):
    status = getattr(exception, "status_code", None)
    if status is None:
        status = getattr(getattr(exception, "response", None), "status_code", None)
    return int(status) if isinstance(status, int) and 100 <= status <= 599 else None


async def _smart_study_event_allowed(session, notification) -> bool:
    """Smart reminders use their selected adapter and never generic fanout."""
    return False


async def _event_exists(session, row) -> bool:
    if row.source == "account":
        return await session.scalar(select(AccountNoticeDelivery.id).where(
            AccountNoticeDelivery.id == row.source_id,
            AccountNoticeDelivery.user_id == row.user_id,
        )) is not None
    if row.source == "course":
        notification = await session.get(CourseUserNotification, row.source_id)
        if notification is None or notification.user_id != row.user_id:
            return False
        if notification.key == "smart_study":
            return await _smart_study_event_allowed(session, notification)
        return True
    if row.source == "payment":
        # Payment status remains authoritative; the push is only a generic
        # pointer back to the authenticated PWA notice center.
        return await session.scalar(select(Payment.id).where(
            Payment.id == row.source_id,
            Payment.user_id == row.user_id,
            Payment.payment_status.in_(("approved", "rejected")),
            Payment.reviewed_at.is_not(None),
        )) is not None
    return False


async def _claim_one(session_factory, *, now: datetime, worker_id: str):
    async with session_factory() as session:
        async with session.begin():
            due = or_(
                LearnerPwaPushOutbox.state.in_(("pending", "retry"))
                & (LearnerPwaPushOutbox.next_attempt_at <= now),
                (LearnerPwaPushOutbox.state == "leased")
                & (LearnerPwaPushOutbox.lease_expires_at <= now),
            )
            rows = (await session.scalars(
                select(LearnerPwaPushOutbox)
                .join(LearnerPwaPushSubscription,
                      LearnerPwaPushSubscription.id == LearnerPwaPushOutbox.subscription_id)
                .where(
                    LearnerPwaPushSubscription.revoked_at.is_(None),
                    LearnerPwaPushOutbox.attempts < _MAX_ATTEMPTS,
                    due,
                )
                .order_by(LearnerPwaPushOutbox.created_at, LearnerPwaPushOutbox.id)
                .limit(_MAX_BATCH)
                .with_for_update(skip_locked=True, of=LearnerPwaPushOutbox)
            )).all()
            for row in rows:
                # Recheck the canonical owner and its current PWA session immediately
                # before leasing. The session is revoked transactionally by logout.
                owner_ok = await session.scalar(select(User.id).where(User.id == row.user_id))
                subscription = await session.get(
                    LearnerPwaPushSubscription, row.subscription_id, with_for_update=True,
                )
                if owner_ok is None or subscription is None or subscription.revoked_at is not None:
                    row.state = "cancelled"
                    row.updated_at = now
                    row.next_attempt_at = None
                    row.lease_owner = None
                    row.lease_expires_at = None
                    continue
                device = (await session.execute(select(DesktopDevice).where(
                    DesktopDevice.id == subscription.device_id,
                    DesktopDevice.user_id == row.user_id,
                    DesktopDevice.platform == "pwa",
                    DesktopDevice.revoked_at.is_(None),
                ).with_for_update())).scalar_one_or_none()
                if device is None:
                    row.state = "cancelled"
                    row.updated_at = now
                    row.next_attempt_at = None
                    row.lease_owner = None
                    row.lease_expires_at = None
                    continue
                live_session = await session.scalar(select(DesktopSession.id).where(
                    DesktopSession.device_id == device.id,
                    DesktopSession.revoked_at.is_(None),
                    DesktopSession.expires_at > now,
                ).order_by(DesktopSession.expires_at.desc(), DesktopSession.id).limit(1))
                deletion_pending = await session.scalar(select(AccountDeletionRequest.id).where(
                    AccountDeletionRequest.user_id == row.user_id,
                    AccountDeletionRequest.status.in_(("submitted", "processing")),
                ).limit(1))
                user = await session.get(User, row.user_id)
                if (live_session is None or deletion_pending is not None or user is None
                        or UserAccessStateService.classify(user) == UserAccessState.BLOCKED
                        or not await _event_exists(session, row)):
                    row.state = "cancelled"
                    row.updated_at = now
                    row.next_attempt_at = None
                    row.lease_owner = None
                    row.lease_expires_at = None
                    continue
                row.state = "leased"
                row.lease_owner = worker_id
                row.lease_expires_at = now + timedelta(seconds=_LEASE_SECONDS)
                row.updated_at = now
                row.attempts += 1
                row.next_attempt_at = None
                await session.flush()
                return row.id, subscription.id, subscription.encrypted_payload, row.source, row.language
    return None


async def _finish(session_factory, *, outbox_id, subscription_id, worker_id, status, now):
    async with session_factory() as session:
        async with session.begin():
            row = await session.get(LearnerPwaPushOutbox, outbox_id, with_for_update=True)
            if row is None or row.state != "leased" or row.lease_owner != worker_id:
                return "lost_lease"
            subscription = await session.get(
                LearnerPwaPushSubscription, subscription_id, with_for_update=True,
            )
            row.updated_at = now
            row.last_http_status = status
            row.lease_owner = None
            row.lease_expires_at = None
            row.next_attempt_at = None
            if subscription is None or subscription.revoked_at is not None:
                row.state = "cancelled"
            elif status in (200, 201, 202):
                row.state = "accepted"
            elif status in (404, 410):
                subscription.revoked_at = now
                subscription.updated_at = now
                row.state = "dead"
            elif row.attempts >= _MAX_ATTEMPTS or (
                status is not None and 400 <= status < 500 and status not in (408, 429)
            ):
                row.state = "dead"
            else:
                row.state = "retry"
                row.next_attempt_at = now + timedelta(seconds=min(3600, 60 * (2 ** row.attempts)))
            await session.flush()
            return row.state


async def _load_event_language(session_factory, outbox_id):
    async with session_factory() as session:
        row = await session.get(LearnerPwaPushOutbox, outbox_id)
        if row is None:
            return "ru"
        user = await session.get(User, row.user_id)
        lang = getattr(user, "language", None) if user is not None else None
        return lang if lang in {"uz", "ru", "tj"} else row.language


async def dispatch_batch(session_factory, *, settings_obj, limit=10, sender=None, now=None):
    """Send bounded visible pushes; provider acceptance is not device display proof."""
    if type(limit) is not int or not 1 <= limit <= _MAX_BATCH:
        raise ValueError("invalid_dispatch_limit")
    config = sender_config(settings_obj)
    if config is None:
        return {"enabled": False, "claimed": 0, "accepted": 0, "retry": 0,
                "dead": 0, "cancelled": 0, "lost_lease": 0}
    private_key, subject, fernet = config
    worker_id = str(uuid4())
    results = {"enabled": True, "claimed": 0, "accepted": 0, "retry": 0,
               "dead": 0, "cancelled": 0, "lost_lease": 0}
    for _ in range(limit):
        current = _utc(now or datetime.now(timezone.utc))
        item = await _claim_one(session_factory, now=current, worker_id=worker_id)
        if item is None:
            break
        outbox_id, subscription_id, sealed, source, stored_language = item
        results["claimed"] += 1
        status = None
        try:
            payload = json.loads(fernet.decrypt(sealed.encode("ascii")).decode("ascii"))
            if not isinstance(payload, dict) or set(payload) != {"endpoint", "keys"}:
                raise ValueError("corrupt_subscription")
            if not isinstance(payload.get("endpoint"), str) or not isinstance(payload.get("keys"), dict):
                raise ValueError("corrupt_subscription")
        except Exception:
            # Locally corrupt ciphertext/payload cannot recover by retrying.
            status = 400
        if status is None:
            try:
                from app.services.notification_i18n import notification_message
                language = await _load_event_language(session_factory, outbox_id) or stored_language
                title = notification_message("pwa.push.title", language, "HSK AI")
                body = notification_message(
                    "pwa.push.body", language,
                    "У вас новое уведомление. Откройте HSK AI.",
                )
                public_payload = json.dumps(
                    {"title": title, "body": body, "url": _PUSH_PATH,
                     "tag": "hsk-" + outbox_id.replace("-", "")[:24]},
                    ensure_ascii=False, separators=(",", ":"),
                )
                if sender is None:
                    status = await send_webpush(payload, public_payload, private_key, subject)
                else:
                    status = await sender(payload, public_payload, private_key, subject, source)
            except Exception as exc:
                status = _http_status(exc)
                logger.warning("Learner PWA push provider failure; code=%s", status)
        state = await _finish(session_factory, outbox_id=outbox_id,
            subscription_id=subscription_id, worker_id=worker_id, status=status,
            now=_utc(now or datetime.now(timezone.utc)))
        results[state] += 1
    return results
