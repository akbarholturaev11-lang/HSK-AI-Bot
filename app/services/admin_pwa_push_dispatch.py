"""Apple Web Push delivery from the private, deduplicated outbox.

Worker-only, default OFF. Dispatch is at-least-once: a provider can accept an
HTTP request immediately before a worker crashes. Leases, capped retries and
a per-device cooldown limit duplicates; never promise exactly-once delivery.
No private inbox text or recipient details are sent or logged.
"""
import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import func, or_, select

from app.admin_api.pwa_push import _configuration, _decode, _validate_subscription, SubscribeRequest
from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.admin_pwa_push import AdminPwaPushSubscription
from app.db.models.admin_pwa_push_outbox import AdminPwaPushOutbox
from app.db.models.payment import Payment
from app.db.models.user import User

logger = logging.getLogger(__name__)
_LEASE_SECONDS = 45
_DEVICE_COOLDOWN_SECONDS = 30
_MAX_ATTEMPTS = 4
_GENERIC_PAYLOAD = '{"kind":"important"}'


def _utc(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def sender_config(settings_obj):
    """Verify ALL worker secrets and EC key pairing before touching the outbox."""
    if not getattr(settings_obj, "ADMIN_PWA_PUSH_SEND_ENABLED", False):
        return None
    base = _configuration(settings_obj)
    if base is None:
        return None
    try:
        encoded = str(getattr(settings_obj, "ADMIN_PWA_PUSH_VAPID_PRIVATE_KEY", ""))
        raw = _decode(encoded)
        if len(raw) != 32:
            return None
        private_key = ec.derive_private_key(int.from_bytes(raw, "big"), ec.SECP256R1())
        expected = private_key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        if expected != _decode(base[0]):
            return None
        subject = str(getattr(settings_obj, "ADMIN_PWA_PUSH_VAPID_SUBJECT", ""))
        if not 8 <= len(subject) <= 200 or any(c.isspace() for c in subject):
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
        return (encoded, subject, base[1])
    except (ValueError, TypeError, UnicodeError):
        return None


async def _webpush(subscription, encoded_key, subject):
    """RFC 8291 aes128gcm encryption + RFC 8292 VAPID signing via pywebpush."""
    from pywebpush import webpush
    from py_vapid import Vapid
    # pywebpush is blocking and must never block the async DB/event loop.
    def send():
        result = webpush(
            subscription_info=subscription, data=_GENERIC_PAYLOAD,
            vapid_private_key=Vapid.from_raw(encoded_key.encode("ascii")),
            vapid_claims={"sub": subject}, content_encoding="aes128gcm",
            ttl=180, timeout=8, verbose=False,
        )
        return int(result.status_code)
    return await asyncio.wait_for(asyncio.to_thread(send), timeout=12)


def _http_status(exception):
    # pywebpush exposes status_code; never inspect/log exception text or response body.
    status = getattr(exception, "status_code", None)
    if status is None:
        status = getattr(getattr(exception, "response", None), "status_code", None)
    return int(status) if isinstance(status, int) and 100 <= status <= 599 else None


async def _relevant(db, row, now):
    """Skip no-longer-actionable alerts without resurrecting or exposing content."""
    if row.source == "payment":
        record = await db.get(Payment, row.source_id)
        return (record is not None and record.payment_status == "pending"
                and bool(record.screenshot_file_id))
    if row.source == "android":
        record = await db.get(AdminPwaNativeReport, row.source_id)
        return record is not None and _utc(record.expires_at) > now
    triage = await db.get(AdminPwaInboxTriage, (row.source, row.source_id))
    return triage is not None and triage.priority == "important" and triage.status != "resolved"


async def _claim_one(session_factory, settings_obj, now, worker_id):
    """Claim one due item under DB locks; never hold locks across network IO."""
    async with session_factory() as db:
        async with db.begin():
            query = (select(AdminPwaPushOutbox)
                     .join(AdminPwaPushSubscription,
                           AdminPwaPushSubscription.id == AdminPwaPushOutbox.subscription_id)
                     .join(User, User.id == AdminPwaPushSubscription.user_id)
                     .where(
                         AdminPwaPushSubscription.revoked_at.is_(None),
                         User.telegram_id.in_(getattr(settings_obj, "admin_id_list", [])),
                         AdminPwaPushOutbox.attempts < _MAX_ATTEMPTS,
                         or_(
                             (AdminPwaPushOutbox.state.in_(("pending", "retry"))
                              & (AdminPwaPushOutbox.next_attempt_at <= now)),
                             ((AdminPwaPushOutbox.state == "leased")
                              & (AdminPwaPushOutbox.lease_expires_at <= now)),
                         ))
                     .order_by(AdminPwaPushOutbox.created_at, AdminPwaPushOutbox.id)
                     .limit(24).with_for_update(skip_locked=True, of=AdminPwaPushOutbox))
            rows = (await db.scalars(query)).all()
            for row in rows:
                # Serializing on the subscription row prevents concurrent sends
                # to one iPhone/Mac device even from independent worker processes.
                subscription = await db.get(AdminPwaPushSubscription, row.subscription_id,
                                            with_for_update=True)
                if subscription is None or subscription.revoked_at is not None:
                    row.state = "cancelled"
                    row.updated_at = now
                    continue
                recent = await db.scalar(select(func.max(AdminPwaPushOutbox.updated_at)).where(
                    AdminPwaPushOutbox.subscription_id == subscription.id,
                    AdminPwaPushOutbox.id != row.id,
                    AdminPwaPushOutbox.attempts > 0,
                ))
                if recent is not None and (_utc(now) - _utc(recent)).total_seconds() < _DEVICE_COOLDOWN_SECONDS:
                    # Keep old lease expiry if this was a recovery, but do not
                    # suppress it: next invocation can retry after cooldown.
                    continue
                if not await _relevant(db, row, now):
                    row.state = "cancelled"
                    row.updated_at = now
                    row.next_attempt_at = None
                    continue
                row.state = "leased"
                row.lease_owner = worker_id
                row.lease_expires_at = now + timedelta(seconds=_LEASE_SECONDS)
                row.updated_at = now
                row.attempts += 1
                row.next_attempt_at = None
                await db.flush()
                return row.id, subscription.id, subscription.encrypted_payload
    return None


async def _finish(session_factory, *, event_id, subscription_id, worker_id, status, now):
    async with session_factory() as db:
        async with db.begin():
            row = await db.get(AdminPwaPushOutbox, event_id, with_for_update=True)
            if row is None or row.state != "leased" or row.lease_owner != worker_id:
                return "lost_lease"
            subscription = await db.get(AdminPwaPushSubscription, subscription_id,
                                        with_for_update=True)
            row.last_http_status = status
            row.updated_at = now
            row.lease_owner = None
            row.lease_expires_at = None
            row.next_attempt_at = None
            if subscription is None or subscription.revoked_at is not None:
                row.state = "cancelled"
            elif status in (200, 201, 202):
                row.state = "accepted"
            elif status in (404, 410):
                # Apple explicitly says this endpoint is no longer valid.
                subscription.revoked_at = now
                subscription.updated_at = now
                row.state = "dead"
            elif row.attempts >= _MAX_ATTEMPTS or (status is not None and 400 <= status < 500
                                                      and status not in (408, 429)):
                row.state = "dead"
            else:
                row.state = "retry"
                # Exponential, bounded retry after uncertain delivery or rate limit.
                row.next_attempt_at = now + timedelta(seconds=min(3600, 60 * (2 ** row.attempts)))
            await db.flush()
            return row.state


async def dispatch_batch(session_factory, *, settings_obj, limit=10, sender=None, now=None):
    """Process at most one event per device per invocation; no send while flag OFF.

    Explicit worker invocation is required; importing this module never starts
    a task or alters runtime startup. A known accepted response proves only
    Apple push-service acceptance, not visible device delivery.
    """
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        raise ValueError("invalid_dispatch_limit")
    config = sender_config(settings_obj)
    if config is None:
        return {"enabled": False, "claimed": 0, "accepted": 0, "retry": 0,
                "dead": 0, "cancelled": 0, "lost_lease": 0}
    private_key, subject, fernet = config
    worker_id = str(uuid4())
    results = {"enabled": True, "claimed": 0, "accepted": 0,
               "retry": 0, "dead": 0, "cancelled": 0, "lost_lease": 0}
    sent_to = set()
    for _ in range(limit):
        current = _utc(now or datetime.now(timezone.utc))
        item = await _claim_one(session_factory, settings_obj, current, worker_id)
        if item is None:
            break
        event_id, subscription_id, sealed = item
        if subscription_id in sent_to:
            # No second send on one device during one batch, even with fake clocks.
            state = await _finish(session_factory, event_id=event_id,
                                  subscription_id=subscription_id,
                                  worker_id=worker_id, status=None, now=current)
            results[state] += 1
            break
        sent_to.add(subscription_id)
        results["claimed"] += 1
        status = None
        try:
            import json
            payload = json.loads(fernet.decrypt(sealed.encode("ascii")).decode("ascii"))
            command = SubscribeRequest.model_validate({"platform": "mac", **payload})
            if _validate_subscription(command) is None:
                raise ValueError("corrupt_subscription")
            if sender is None:
                status = await _webpush(payload, private_key, subject)
            else:
                status = await sender(payload, private_key, subject)
        except Exception as exc:
            status = _http_status(exc)
            # No endpoint, key, subject or user/message values in logs.
            logger.warning("Admin PWA Apple push provider failure; code=%s", status)
        state = await _finish(session_factory, event_id=event_id, subscription_id=subscription_id,
                              worker_id=worker_id, status=status,
                              now=_utc(now or datetime.now(timezone.utc)))
        results[state] += 1
    return results
