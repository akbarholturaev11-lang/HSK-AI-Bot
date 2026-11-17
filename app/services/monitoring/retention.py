"""Bounded diagnostic retention for the hourly housekeeping loop (D8)."""
import asyncio
from datetime import timedelta

from sqlalchemy import and_, delete, select

from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage
from app.db.models.diagnostic import DiagnosticIncident, DiagnosticReceipt
from app.services.monitoring import catalog
from app.services.monitoring.intake import IntakeBusy, bound_write, diagnostic_slot

MAX_BATCHES_PER_PASS = 8


async def run_diagnostic_retention(session_factory, settings_obj, *, now, limit=catalog.PURGE_BATCH):
    """Catch up after downtime without holding locks or a pool slot across batches."""
    receipts = incidents = 0
    for _ in range(MAX_BATCHES_PER_PASS):
        try:
            with diagnostic_slot(settings_obj):
                async with session_factory() as db, db.begin():
                    await bound_write(db)
                    removed_receipts, removed_incidents = await purge_diagnostics(db, now=now, limit=limit)
        except IntakeBusy:
            break  # Intake already needs every diagnostic slot; defer to the next pass.
        receipts += removed_receipts
        incidents += removed_incidents
        if max(removed_receipts, removed_incidents) < limit:
            break  # Only fewer rows or temporarily locked rows remain.
        await asyncio.sleep(0)
    return receipts, incidents


async def purge_diagnostics(db, *, now, limit=catalog.PURGE_BATCH):
    """Delete expired receipts and long-resolved incidents, at most `limit` each.

    Audit rows stay: they hold no telemetry. Returns (receipts, incidents).
    """
    receipt_cutoff = now - timedelta(days=catalog.RECEIPT_RETENTION_DAYS)
    expired = select(DiagnosticReceipt.id).where(
        DiagnosticReceipt.received_at < receipt_cutoff
    ).order_by(DiagnosticReceipt.received_at).limit(limit).with_for_update(skip_locked=True)
    receipt_ids = list((await db.execute(expired)).scalars())
    if receipt_ids:
        await db.execute(delete(DiagnosticReceipt).where(DiagnosticReceipt.id.in_(receipt_ids)))

    incident_cutoff = now - timedelta(days=catalog.RESOLVED_INCIDENT_RETENTION_DAYS)
    has_receipts = (select(DiagnosticReceipt.id)
                    .where(DiagnosticReceipt.incident_id == DiagnosticIncident.id).exists())
    stale = (select(DiagnosticIncident.id)
             .join(AdminPwaInboxTriage, and_(AdminPwaInboxTriage.source == "diagnostic",
                                             AdminPwaInboxTriage.source_id == DiagnosticIncident.id))
             .where(AdminPwaInboxTriage.status == "resolved",
                    DiagnosticIncident.last_seen_at < incident_cutoff, ~has_receipts)
             .order_by(DiagnosticIncident.fingerprint).limit(limit)
             .with_for_update(of=DiagnosticIncident, skip_locked=True))
    incident_ids = list((await db.execute(stale)).scalars())
    if incident_ids:
        # Recheck after taking the incident locks shared with intake and triage.
        # Only the bounded receipt pass may remove receipts; do not cascade an
        # entire incident's backlog, or wait for a receipt it skipped.
        incident_ids = list((await db.scalars(
            select(DiagnosticIncident.id).join(AdminPwaInboxTriage, and_(
                AdminPwaInboxTriage.source == "diagnostic",
                AdminPwaInboxTriage.source_id == DiagnosticIncident.id,
            )).where(DiagnosticIncident.id.in_(incident_ids),
                     AdminPwaInboxTriage.status == "resolved",
                     DiagnosticIncident.last_seen_at < incident_cutoff, ~has_receipts)
        )).all())
    if incident_ids:
        await db.execute(delete(AdminPwaInboxTriage).where(
            AdminPwaInboxTriage.source == "diagnostic", AdminPwaInboxTriage.source_id.in_(incident_ids)))
        await db.execute(delete(DiagnosticIncident).where(DiagnosticIncident.id.in_(incident_ids)))
    return len(receipt_ids), len(incident_ids)
