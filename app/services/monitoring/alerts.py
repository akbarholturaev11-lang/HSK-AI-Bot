"""Bounded diagnostic alert decisions inside the caller's intake transaction."""
import logging
from datetime import timedelta, timezone

from sqlalchemy import func, select, text

from app.admin_api.pwa_push_outbox import enqueue_automatic_alert
from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage
from app.db.models.admin_pwa_push_outbox import AdminPwaPushOutbox
from app.db.models.diagnostic import DiagnosticReceipt
from app.services.monitoring import catalog

logger = logging.getLogger(__name__)
_ALERT_LOCK = 0x68736B64696167  # "hskdiag", PostgreSQL bigint advisory key


def _aware(stamp):
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


async def decide_alert(db, *, settings_obj, incident, first, escalated, reopened, now):
    if not (getattr(settings_obj, "MONITORING_PUSH_ENABLED", False)
            and getattr(settings_obj, "ADMIN_PWA_ENABLED", False)
            and getattr(settings_obj, "ADMIN_PWA_PUSH_ENABLED", False)):
        return
    # An open incident that was initially capped can qualify on a later event.
    candidate = incident.severity == "high" or (incident.severity == "critical" and incident.alert_epoch == 0)
    if not (reopened or escalated or (first and incident.severity == "critical") or candidate):
        return
    try:
        async with db.begin_nested():
            reason = "reopened" if reopened else None
            if reason is None:
                triage = await db.get(AdminPwaInboxTriage, ("diagnostic", incident.id))
                if triage is not None and triage.status == "resolved":
                    return
                if not escalated and incident.severity == "high":
                    owners = (select(DiagnosticReceipt.user_id)
                              .where(DiagnosticReceipt.incident_id == incident.id,
                                     DiagnosticReceipt.user_id.is_not(None),
                                     DiagnosticReceipt.received_at >= now - timedelta(minutes=catalog.ESCALATION_WINDOW_MINUTES))
                              .distinct().limit(catalog.ESCALATION_ACCOUNTS).subquery())
                    if await db.scalar(select(func.count()).select_from(owners)) < catalog.ESCALATION_ACCOUNTS:
                        return
                    incident.severity = "critical"
                    escalated = True
                reason = "escalated" if escalated else "new"
                if incident.last_alerted_at and _aware(incident.last_alerted_at) > now - timedelta(hours=catalog.ALERT_COOLDOWN_HOURS):
                    return
                if db.get_bind().dialect.name == "postgresql":
                    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _ALERT_LOCK})
                recent = (select(AdminPwaPushOutbox.event_key).where(
                    AdminPwaPushOutbox.source == "diagnostic",
                    AdminPwaPushOutbox.diagnostic_kind.in_(("new", "escalated")),
                    AdminPwaPushOutbox.created_at >= now - timedelta(hours=1),
                ).distinct().limit(catalog.ALERT_GLOBAL_CAP_PER_HOUR).subquery())
                if await db.scalar(select(func.count()).select_from(recent)) >= catalog.ALERT_GLOBAL_CAP_PER_HOUR:
                    return
            epoch = incident.alert_epoch + 1
            queued = await enqueue_automatic_alert(db, settings_obj=settings_obj, source="diagnostic",
                                                   source_id=incident.id, alert_epoch=epoch,
                                                   diagnostic_kind=reason, now=now)
            if queued:
                incident.alert_epoch = epoch
                incident.last_alerted_at = now
                incident.last_alert_reason = reason
    except Exception:  # The savepoint keeps the occurrence and triage durable.
        logger.warning("diagnostic alert enqueue failed")
