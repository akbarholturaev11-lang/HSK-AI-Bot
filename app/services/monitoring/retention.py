"""Bounded diagnostic retention for the hourly housekeeping loop (D8)."""
from datetime import timedelta

from sqlalchemy import and_, delete, select

from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage
from app.db.models.diagnostic import DiagnosticIncident, DiagnosticReceipt
from app.services.monitoring import catalog


async def purge_diagnostics(db, *, now, limit=catalog.PURGE_BATCH):
    """Delete expired receipts and long-resolved incidents, at most `limit` each.

    Audit rows stay: they hold no telemetry. Returns (receipts, incidents).
    """
    receipt_cutoff = now - timedelta(days=catalog.RECEIPT_RETENTION_DAYS)
    expired = select(DiagnosticReceipt.id).where(
        DiagnosticReceipt.received_at < receipt_cutoff).order_by(DiagnosticReceipt.id).limit(limit)
    receipt_ids = list((await db.execute(expired)).scalars())
    if receipt_ids:
        await db.execute(delete(DiagnosticReceipt).where(DiagnosticReceipt.id.in_(receipt_ids)))

    incident_cutoff = now - timedelta(days=catalog.RESOLVED_INCIDENT_RETENTION_DAYS)
    stale = (select(DiagnosticIncident.id)
             .join(AdminPwaInboxTriage, and_(AdminPwaInboxTriage.source == "diagnostic",
                                             AdminPwaInboxTriage.source_id == DiagnosticIncident.id))
             .where(AdminPwaInboxTriage.status == "resolved",
                    DiagnosticIncident.last_seen_at < incident_cutoff)
             .order_by(DiagnosticIncident.fingerprint).limit(limit)
             .with_for_update(of=DiagnosticIncident, skip_locked=True))
    incident_ids = list((await db.execute(stale)).scalars())
    if incident_ids:
        # Recheck triage in a fresh statement after acquiring the same
        # incident locks used by mark-read, resolve and intake.
        incident_ids = list((await db.scalars(select(AdminPwaInboxTriage.source_id).where(
            AdminPwaInboxTriage.source == "diagnostic", AdminPwaInboxTriage.source_id.in_(incident_ids),
            AdminPwaInboxTriage.status == "resolved",
        ))).all())
    if incident_ids:
        await db.execute(delete(DiagnosticReceipt).where(DiagnosticReceipt.incident_id.in_(incident_ids)))
        await db.execute(delete(AdminPwaInboxTriage).where(
            AdminPwaInboxTriage.source == "diagnostic", AdminPwaInboxTriage.source_id.in_(incident_ids)))
        await db.execute(delete(DiagnosticIncident).where(DiagnosticIncident.id.in_(incident_ids)))
    return len(receipt_ids), len(incident_ids)
