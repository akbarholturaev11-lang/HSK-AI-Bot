"""Atomic enqueue for an explicitly marked-important Admin PWA inbox item.

Only a current authorized admin's active Apple-device subscriptions are targeted.
This does not perform HTTP, schedule a sender, or send push on every feedback
arrival. The original triage transaction owns this enqueue and its rollback.
"""
import hashlib
from uuid import uuid4

from sqlalchemy import select

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
    if source not in ("bot", "release", "android") or revision < 1 or source_id < 1:
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
