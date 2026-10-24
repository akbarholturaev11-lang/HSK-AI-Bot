"""Commit intake before notification. DB row locks coordinate all API workers."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json

from sqlalchemy import delete, select, update

from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.user import User

RETENTION_DAYS = 30


class NativeReportRateLimited(Exception):
    pass


@dataclass(frozen=True)
class NativeReportAdmission:
    report_id: int
    already_sent: bool


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


async def reserve_native_report(session_factory, *, user_id, description, app_version, screen, screenshot, now=None):
    now = now or datetime.now(timezone.utc)
    if not 5 <= len(description) <= 2000 or len(app_version) > 40 or len(screen) > 80:
        raise ValueError("Invalid native report bounds")
    if screenshot is not None and (len(screenshot) > 550*1024 or not screenshot.startswith(b"\xff\xd8\xff")):
        raise ValueError("Invalid native attachment bounds")
    # Daily content deduplication does not expose an identifier in URLs/logs.
    material = json.dumps([int(now.timestamp())//86400, description, app_version, screen,
                           hashlib.sha256(screenshot).hexdigest() if screenshot is not None else None],
                          ensure_ascii=False, separators=(",", ":")).encode()
    key = hashlib.sha256(material).hexdigest()
    async with session_factory() as db:
        async with db.begin():
            owner = await db.scalar(select(User.id).where(User.id == user_id).with_for_update())
            if owner is None:
                raise ValueError("Native report owner disappeared")
            latest = await db.scalar(select(AdminPwaNativeReport.last_attempt_at)
                .where(AdminPwaNativeReport.user_id == user_id)
                .order_by(AdminPwaNativeReport.last_attempt_at.desc(), AdminPwaNativeReport.id.desc()).limit(1))
            if latest and now-_utc(latest) < timedelta(seconds=60):
                raise NativeReportRateLimited()
            row = await db.scalar(select(AdminPwaNativeReport).where(
                AdminPwaNativeReport.user_id == user_id, AdminPwaNativeReport.deduplication_key == key))
            if row is not None:
                # A still-running attempt has a short lease; no immediate
                # duplicate Telegram delivery after a worker/process crash.
                if row.notification_state == "pending" and now-_utc(row.last_attempt_at) < timedelta(minutes=5):
                    raise NativeReportRateLimited()
                sent = row.notification_state == "sent"
                row.last_attempt_at = now
                if not sent:
                    row.notification_state = "pending"
            else:
                sent = False
                row = AdminPwaNativeReport(user_id=user_id, deduplication_key=key,
                    description=description, app_version=app_version, screen=screen,
                    attachment_bytes=screenshot, notification_state="pending",
                    created_at=now, last_attempt_at=now, expires_at=now+timedelta(days=RETENTION_DAYS))
                db.add(row)
                await db.flush()
                # Every newly accepted native bug report is important by
                # default. Optional push delivery never blocks durable intake.
                from app.config import settings
                if settings.ADMIN_PWA_ENABLED and settings.ADMIN_PWA_PUSH_ENABLED:
                    import logging
                    try:
                        from app.admin_api.pwa_push_outbox import enqueue_automatic_alert
                        async with db.begin_nested():
                            await enqueue_automatic_alert(
                                db, settings_obj=settings, source="android",
                                source_id=row.id, now=now)
                    except Exception:
                        logging.getLogger(__name__).warning(
                            "Optional admin Android error push enqueue failed")
            result = NativeReportAdmission(row.id, sent)
        return result


async def finish_native_report(session_factory, report_id, *, delivered):
    async with session_factory() as db:
        async with db.begin():
            # A delayed failure must never erase another attempt's success.
            await db.execute(update(AdminPwaNativeReport).where(
                AdminPwaNativeReport.id == report_id, AdminPwaNativeReport.notification_state != "sent",
            ).values(notification_state="sent" if delivered else "failed"))


async def purge_expired_native_reports(db, *, now=None, limit=100):
    """Bounded physical deletion; operator job must run daily before rollout."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError("Invalid native report purge bound")
    expired = select(AdminPwaNativeReport.id).where(
        AdminPwaNativeReport.expires_at <= (now or datetime.now(timezone.utc)),
    ).order_by(AdminPwaNativeReport.id).limit(limit)
    result = await db.execute(delete(AdminPwaNativeReport).where(AdminPwaNativeReport.id.in_(expired)))
    return result.rowcount
