"""Atomic enqueue for an explicitly marked-important Admin PWA inbox item.

Only a current authorized admin's active Apple-device subscriptions are targeted.
This does not perform HTTP, schedule a sender, or send push on every feedback
arrival. The original triage transaction owns this enqueue and its rollback.
"""
import hashlib
from uuid import uuid4

from sqlalchemy import select

from app.db.models.user import User

from app.db.models.admin_pwa_push import AdminPwaPushSubscription
from app.db.models.admin_pwa_push_outbox import AdminPwaPushOutbox


async def enqueue_important_triage(db, *, settings_obj, actor_id: int, source: str,
                                   source_id: int, revision: int, now) -> int:
    """Add <= 4 immutable device events, in the CALLER's existing transaction.

    No report text, username, raw Telegram identifier, screenshot, Web Push
    endpoint, key or URL gets copied into the outbox.
    """
    if (not getattr(settings_obj, "ADMIN_PWA_ENABLED", False)
            or not getattr(settings_obj, "ADMIN_PWA_PUSH_ENABLED", False)):
        return 0
    if source not in ("bot", "release", "android", "technical") or revision < 1 or source_id < 1:
        raise ValueError("invalid_push_event")
    # Browser enrollment already caps each admin at four devices. Treat any
    # inconsistent DB state conservatively by also bounding enqueue to four.
    rows = (await db.scalars(select(AdminPwaPushSubscription.id).where(
        AdminPwaPushSubscription.user_id == actor_id,
        AdminPwaPushSubscription.revoked_at.is_(None),
    ).order_by(AdminPwaPushSubscription.id).limit(4))).all()
    event_key = hashlib.sha256(
        f"important-v1:{source}:{source_id}:{revision}".encode("ascii")).hexdigest()
    for device_id in rows:
        db.add(AdminPwaPushOutbox(
            id=str(uuid4()), subscription_id=device_id, event_key=event_key,
            source=source, source_id=source_id, triage_revision=revision,
            state="pending", attempts=0, created_at=now, updated_at=now,
            next_attempt_at=now,
        ))
    # The caller is holding the source-row lock and updating its triage CAS
    # revision atomically. The immutable event key and DB unique constraint
    # make duplicates visible as transaction failures, never double-sends.
    if rows:
        await db.flush()
    return len(rows)

async def enqueue_automatic_alert(db, *, settings_obj, source: str, source_id: int, now) -> int:
    """Queue a newly submitted payment receipt or durable Android error.

    Only current allowlisted admins with explicitly enrolled devices qualify.
    Called inside the original creator's transaction and canonical owner lock.
    A fixed event key means re-upload/retry never duplicates delivery.
    This does not send an HTTP push; no message/receipt bytes are persisted here.
    """
    if (not getattr(settings_obj, "ADMIN_PWA_ENABLED", False)
            or not getattr(settings_obj, "ADMIN_PWA_PUSH_ENABLED", False)):
        return 0
    if source not in ("payment", "android", "technical") or source_id < 1:
        raise ValueError("invalid_automatic_alert")
    admins = getattr(settings_obj, "admin_id_list", [])
    if not admins:
        return 0
    event_key = hashlib.sha256(
        f"automatic-important-v1:{source}:{source_id}".encode("ascii")).hexdigest()
    devices = (await db.scalars(select(AdminPwaPushSubscription.id)
        .join(User, User.id == AdminPwaPushSubscription.user_id)
        .where(User.telegram_id.in_(admins),
               AdminPwaPushSubscription.revoked_at.is_(None))
        .order_by(AdminPwaPushSubscription.id).limit(32))).all()
    if not devices:
        return 0
    existing = set((await db.scalars(select(AdminPwaPushOutbox.subscription_id).where(
        AdminPwaPushOutbox.event_key == event_key,
        AdminPwaPushOutbox.subscription_id.in_(devices)))).all())
    for device_id in devices:
        if device_id in existing:
            continue
        db.add(AdminPwaPushOutbox(
            id=str(uuid4()), subscription_id=device_id, event_key=event_key,
            source=source, source_id=source_id, triage_revision=1,
            state="pending", attempts=0, created_at=now, updated_at=now,
            next_attempt_at=now,
        ))
    if len(devices) > len(existing):
        await db.flush()
    return len(devices) - len(existing)
