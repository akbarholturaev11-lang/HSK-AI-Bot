"""Lost-webhook reconciliation for lava.top.

One runner across replicas (a short ``bot_settings`` lease guarded by the
setting's advisory lock). Each tick: drain queued/retry events, re-check open
invoices, hourly re-check active subscriptions for missed renewals and alert on
overdue renewals. Provider calls are paced and never run inside a transaction.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from app.db.models.lava import LavaInvoice, LavaWebhookEvent
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.lava import events, ledger
from app.services.lava.client import LavaError, LavaNotFound
from app.services.lava.terms import LOCAL_CONTRACT_PREFIX

logger = logging.getLogger(__name__)

LEASE_KEY = "lava_reconcile_lease"
LAST_RUN_KEY = "lava_reconcile_last_run_at"
TICK_SECONDS = 60
OPEN_INVOICE_EVERY = timedelta(minutes=5)
RENEWAL_EVERY = timedelta(hours=1)
OPEN_INVOICE_WINDOW = timedelta(hours=48)
RENEWAL_OVERDUE_AFTER = timedelta(hours=24)
PROVIDER_PAUSE_SECONDS = 0.2  # ≤5 requests/s
BATCH = 50


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class LavaReconcileWorker:
    def __init__(self, runtime: events.LavaRuntime, *, instance_id: str | None = None):
        self.runtime = runtime
        self.instance_id = instance_id or f"{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self._last_open: datetime | None = None
        self._last_renewal: datetime | None = None

    async def _acquire_lease(self) -> bool:
        now = _now()
        async with self.runtime.session_factory() as session, session.begin():
            repo = BotSettingRepository(session)
            await repo.lock_key(LEASE_KEY)
            current = await repo.get(LEASE_KEY)
            if current:
                owner, _, expires = current.partition("|")
                try:
                    expires_at = datetime.fromisoformat(expires)
                except ValueError:
                    expires_at = now
                if owner != self.instance_id and expires_at > now:
                    return False
            await repo.set(LEASE_KEY, f"{self.instance_id}|{(now + timedelta(minutes=4)).isoformat()}")
            await repo.set(LAST_RUN_KEY, now.isoformat())
        return True

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - keep the worker alive; never log secrets
                logger.exception("lava.top reconcile tick failed")
            await asyncio.sleep(TICK_SECONDS)

    async def tick(self, *, force: bool = False) -> dict:
        settings_obj = self.runtime.settings
        if not getattr(settings_obj, "LAVA_API_KEY", "") or not getattr(settings_obj, "LAVA_RECONCILE_ENABLED", True):
            return {"skipped": "disabled"}
        if not await self._acquire_lease():
            return {"skipped": "lease"}
        summary = {"events": 0, "invoices": 0, "renewals": 0}
        if getattr(settings_obj, "LAVA_PROCESSING_PAUSED", False) is not True:
            summary["events"] = await self.drain_events()
            now = _now()
            if force or self._last_open is None or now - self._last_open >= OPEN_INVOICE_EVERY:
                self._last_open = now
                summary["invoices"] = await self.check_open_invoices()
            if force or self._last_renewal is None or now - self._last_renewal >= RENEWAL_EVERY:
                self._last_renewal = now
                summary["renewals"] = await self.check_subscriptions()
                await self.alert_overdue_renewals()
        return summary

    async def drain_events(self) -> int:
        async with self.runtime.session_factory() as session:
            ids = list((await session.execute(select(LavaWebhookEvent.id).where(
                LavaWebhookEvent.result.in_(("queued", "retry", "received")),
                LavaWebhookEvent.payload_json.is_not(None),
            ).order_by(LavaWebhookEvent.received_at).limit(BATCH))).scalars())
        for event_id in ids:
            await events.process_event(self.runtime, event_id)
            await asyncio.sleep(PROVIDER_PAUSE_SECONDS)
        return len(ids)

    async def check_open_invoices(self) -> int:
        now = _now()
        async with self.runtime.session_factory() as session:
            rows = list((await session.execute(select(LavaInvoice.id, LavaInvoice.contract_id,
                                                      LavaInvoice.created_at).where(
                LavaInvoice.status.in_(("created", "failed")),
                LavaInvoice.kind.in_(("first", "renewal")),
                ~LavaInvoice.contract_id.like(f"{LOCAL_CONTRACT_PREFIX}%"),
                or_(LavaInvoice.last_checked_at.is_(None),
                    LavaInvoice.last_checked_at < now - timedelta(minutes=4)),
            ).order_by(LavaInvoice.created_at).limit(BATCH))).all())
        checked = 0
        for invoice_id, contract_id, created_at in rows:
            if now - _utc(created_at) > OPEN_INVOICE_WINDOW:
                async with self.runtime.session_factory() as session, session.begin():
                    row = await session.get(LavaInvoice, invoice_id, with_for_update=True)
                    if row is not None and row.status in {"created", "failed"}:
                        row.status = "expired"
                continue
            async with self.runtime.session_factory() as session, session.begin():
                row = await session.get(LavaInvoice, invoice_id, with_for_update=True)
                if row is None or row.status not in {"created", "failed"}:
                    continue
                row.last_checked_at = now
            result, _, _ = await events.verify_and_apply(self.runtime, contract_id)
            checked += 1
            if result == "applied":
                logger.info("lava.top reconcile applied missed invoice %s", invoice_id)
            await asyncio.sleep(PROVIDER_PAUSE_SECONDS)
        return checked

    async def check_subscriptions(self) -> int:
        async with self.runtime.session_factory() as session:
            parents = list((await session.execute(select(LavaInvoice.contract_id).where(
                LavaInvoice.kind.in_(("first", "external")), LavaInvoice.user_id.is_not(None),
                LavaInvoice.status.in_(("paid", "chargeback_won")),
                or_(LavaInvoice.subscription_status.is_(None), LavaInvoice.subscription_status == "active"),
            ).order_by(LavaInvoice.paid_at).limit(200))).scalars())
            known = set((await session.execute(select(LavaInvoice.contract_id).where(
                LavaInvoice.parent_contract_id.in_(parents) if parents else LavaInvoice.id < 0,
                LavaInvoice.status.in_(("paid", "refunded", "chargeback_open", "chargeback_won",
                                        "chargeback_lost")),
            ))).scalars())
        applied = 0
        client = self.runtime.client()
        for parent_id in parents:
            try:
                info = await client.get_subscription(parent_id)
            except LavaNotFound:
                continue
            except LavaError:
                break  # provider trouble: try again next hour
            for renewal_id, status in info.renewals:
                if status == "COMPLETED" and renewal_id not in known:
                    result, _, _ = await events.verify_and_apply(
                        self.runtime, renewal_id, expected_parent=parent_id, renewal=True)
                    applied += result == "applied"
                    await asyncio.sleep(PROVIDER_PAUSE_SECONDS)
            if info.subscription_status == "CANCELLED" or info.cancelled_at:
                await ledger.mark_subscription(self.runtime.session_factory, parent_id, status="cancelled")
            await asyncio.sleep(PROVIDER_PAUSE_SECONDS)
        return applied

    async def alert_overdue_renewals(self) -> None:
        cutoff = _now() - RENEWAL_OVERDUE_AFTER
        async with self.runtime.session_factory() as session, session.begin():
            rows = list((await session.execute(select(LavaInvoice).join(User, User.id == LavaInvoice.user_id).where(
                LavaInvoice.kind.in_(("first", "external")), LavaInvoice.status == "paid",
                or_(LavaInvoice.subscription_status.is_(None), LavaInvoice.subscription_status == "active"),
                or_(LavaInvoice.review_reason.is_(None), LavaInvoice.review_reason != "renewal_overdue"),
                User.end_date < cutoff,
            ).limit(BATCH).with_for_update(of=LavaInvoice))).scalars())
            ids = []
            for row in rows:
                row.review_reason = "renewal_overdue"
                ids.append(row.id)
        for invoice_id in ids:
            await self.runtime.notifier.admin_alert("renewal_overdue", invoice_id=invoice_id)
