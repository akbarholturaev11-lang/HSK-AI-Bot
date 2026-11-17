"""Diagnostic intake: validation, idempotency, admission, retention (task 1.2)."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from uuid import uuid4

from sqlalchemy import event, func, insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401  (register every table)
from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage
from app.db.models.diagnostic import DiagnosticIncident, DiagnosticReceipt
from app.db.models.user import User
from app.services.monitoring import catalog
from app.services.monitoring.intake import (
    IntakeRejected, current_mode, ingest, ingest_server, is_owner_account, parse_batch,
)
from app.services.monitoring.retention import MAX_BATCHES_PER_PASS, purge_diagnostics, run_diagnostic_retention
from tests.monitoring_chain import PG_URL, pg_sessions

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


def event_body(**overrides):
    item = {"event_id": str(uuid4()), "client_time": int(NOW.timestamp() * 1000), "app_version": "1.8.0",
            "build": 40, "channel": "play", "feature_code": "lessons", "failure_code": "api_5xx",
            "site_code": "lesson_open", "outcome": "failed"}
    item.update(overrides)
    return item


def batch(*items):
    return {"schema": catalog.SCHEMA, "events": list(items) or [event_body()]}


class ParseTests(unittest.TestCase):
    def test_forbidden_or_unknown_fields_reject_the_whole_request(self):
        for key in ("token", "cookie", "initData", "password", "message", "stack", "url", "body",
                    "user_id", "telegram_id", "fingerprint", "severity", "screenshot", "device_id"):
            with self.subTest(key=key), self.assertRaises(IntakeRejected) as caught:
                parse_batch(batch(event_body(), event_body(**{key: "x"})), platform="android", now=NOW)
            self.assertEqual(caught.exception.code, "forbidden_field")
        with self.assertRaises(IntakeRejected):
            parse_batch({**batch(), "user_id": 7}, platform="android", now=NOW)

    def test_unknown_code_rejects_only_that_event(self):
        events, rejected = parse_batch(batch(event_body(), event_body(failure_code="made_up"),
                                             event_body(site_code="free text")), platform="android", now=NOW)
        self.assertEqual((len(events), rejected), (1, 2))

    def test_oversized_batch_and_wrong_schema_are_rejected(self):
        with self.assertRaises(IntakeRejected):
            parse_batch(batch(*[event_body() for _ in range(catalog.MAX_EVENTS_PER_BATCH + 1)]),
                        platform="android", now=NOW)
        with self.assertRaises(IntakeRejected):
            parse_batch({"schema": "diag.v0", "events": [event_body()]}, platform="android", now=NOW)

    def test_values_are_bounded(self):
        bad = (dict(app_version="1.0 <script>"), dict(build=-1), dict(build="40"), dict(channel="beta"),
               dict(category="free"), dict(event_id="not-a-uuid"), dict(platform="iphone_pwa"),
               dict(outcome="crashed"), dict(failure_code="server_5xx"),
               dict(feature_code=[]), dict(site_code={}), dict(category=[]),
               dict(app_version="opaque_non_version_identifier"),
               dict(site_code="lava_ledger"), dict(site_code="v3_lesson_start"))
        for override in bad:
            with self.subTest(override=override):
                events, rejected = parse_batch(batch(event_body(**override)), platform="android", now=NOW)
                self.assertEqual((events, rejected), ([], 1))

    def test_web_build_is_bound_to_a_valid_content_token(self):
        valid = event_body(channel=None, app_version="20261113-abcdef123456", build=20261113)
        events, rejected = parse_batch(batch(valid), platform="iphone_pwa", now=NOW)
        self.assertEqual((events[0].build, rejected), (20261113, 0))
        for changes in (dict(build=20261114), dict(app_version=None),
                        dict(app_version="20261131-abcdef123456", build=20261131),
                        dict(app_version="20991231-abcdef123456", build=20991231)):
            with self.subTest(changes=changes):
                self.assertEqual(parse_batch(batch({**valid, **changes}), platform="iphone_pwa", now=NOW),
                                 ([], 1))

    def test_skewed_client_time_is_flagged_and_dropped(self):
        old = int((NOW - timedelta(days=30)).timestamp() * 1000)
        (parsed,), _ = parse_batch(batch(event_body(client_time=old)), platform="android", now=NOW)
        self.assertTrue(parsed.client_time_untrusted)
        self.assertIsNone(parsed.client_time)

    def test_mode_and_owner_stage(self):
        self.assertEqual(current_mode(SimpleNamespace(MONITORING_MODE="OWNERS")), "owners")
        self.assertEqual(current_mode(SimpleNamespace(MONITORING_MODE="everything")), "off")
        settings = SimpleNamespace(admin_id_list=[9001])
        self.assertTrue(is_owner_account(settings, 9001))
        self.assertFalse(is_owner_account(settings, None))


class SqliteIntakeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)

        @event.listens_for(self.engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db, db.begin():
            db.add_all([User(id=1, telegram_id=1001, status="free"), User(id=2, telegram_id=9001, status="free")])

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def send(self, body, *, owner=1, mode="all", admitted=True, now=NOW):
        events, rejected = parse_batch(body, platform="android", now=now)
        async with self.sessions() as db, db.begin():
            result = await ingest(db, owner_user_id=owner, events=events, mode=mode,
                                  owner_admitted=admitted, now=now)
        result.rejected += rejected
        return result

    async def counts(self):
        async with self.sessions() as db:
            incidents = (await db.execute(select(DiagnosticIncident))).scalars().all()
            receipts = await db.scalar(select(func.count()).select_from(DiagnosticReceipt))
        return incidents, receipts

    async def test_retry_is_idempotent_and_groups_by_fingerprint(self):
        item = event_body()
        first = await self.send(batch(item))
        retry = await self.send(batch(item))
        other_version = await self.send(batch(event_body(app_version="1.9.0", build=41)))
        self.assertEqual((first.accepted, retry.duplicates, other_version.accepted), (1, 1, 1))
        (incident,), receipts = await self.counts()
        self.assertEqual((incident.occurrence_count, receipts), (2, 2))
        self.assertEqual((incident.first_version, incident.last_version, incident.last_build), ("1.8.0", "1.9.0", 41))
        self.assertEqual(incident.severity, "high")

    async def test_recovery_only_lowers_severity(self):
        await self.send(batch(event_body(outcome="recovered")))
        (incident,), _ = await self.counts()
        self.assertEqual(incident.severity, "normal")
        await self.send(batch(event_body()))
        (incident,), _ = await self.counts()
        self.assertEqual(incident.severity, "high")

    async def test_off_pauses_and_owners_admits_only_owners(self):
        paused = await self.send(batch(), mode="off")
        self.assertEqual(paused.response(), {"accepted": 0, "paused": True})
        dropped = await self.send(batch(), mode="owners", admitted=False)
        self.assertEqual((dropped.accepted, dropped.dropped), (0, 1))
        self.assertEqual(await self.counts(), ([], 0))
        admitted = await self.send(batch(), owner=2, mode="owners", admitted=True)
        self.assertEqual(admitted.accepted, 1)

    async def test_cap_refuses_and_counts_as_data_loss(self):
        for _ in range(catalog.HOURLY_CAP_PER_ACCOUNT // catalog.MAX_EVENTS_PER_BATCH):
            await self.send(batch(*[event_body() for _ in range(catalog.MAX_EVENTS_PER_BATCH)]))
        over = await self.send(batch(event_body(), event_body()))
        self.assertEqual((over.accepted, over.refused), (0, 2))
        (incident,), receipts = await self.counts()
        self.assertEqual((receipts, incident.refused_count), (catalog.HOURLY_CAP_PER_ACCOUNT, 2))
        later = await self.send(batch(event_body()), now=NOW + timedelta(hours=1, seconds=1))
        self.assertEqual(later.accepted, 1)

    async def test_cap_deduplicates_repeated_uuid_and_does_not_create_empty_incidents(self):
        for _ in range(catalog.HOURLY_CAP_PER_ACCOUNT // catalog.MAX_EVENTS_PER_BATCH):
            await self.send(batch(*[event_body() for _ in range(catalog.MAX_EVENTS_PER_BATCH)]))
        refused = event_body()
        other = event_body(site_code="lesson_complete")
        result = await self.send(batch(refused, refused, other))
        (incident,), receipts = await self.counts()
        self.assertEqual((result.accepted, result.refused, result.duplicates), (0, 2, 1))
        self.assertEqual((incident.refused_count, receipts), (1, catalog.HOURLY_CAP_PER_ACCOUNT))

    async def test_only_a_fresh_failure_reopens_a_resolved_incident(self):
        first = await self.send(batch())
        incident_id = first.touched[0][0].id
        fixed_at = NOW + timedelta(minutes=1)
        async with self.sessions() as db, db.begin():
            db.add(AdminPwaInboxTriage(source="diagnostic", source_id=incident_id, status="resolved",
                                       priority="normal", revision=1, updated_at=fixed_at, resolved_at=fixed_at))
        receive_at = NOW + timedelta(minutes=2)
        fresh = int(receive_at.timestamp() * 1000)
        await self.send(batch(event_body(), event_body(client_time=fresh, outcome="recovered")), now=receive_at)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaInboxTriage, ("diagnostic", incident_id))).status, "resolved")
        await self.send(batch(event_body(client_time=fresh)), now=receive_at)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaInboxTriage, ("diagnostic", incident_id))).status, "read")
            self.assertEqual((await db.get(DiagnosticIncident, incident_id)).occurrence_count, 4)

    async def test_server_rows_have_no_owner_and_coalesce(self):
        async with self.sessions() as db, db.begin():
            await ingest_server(db, feature_code="lessons", failure_code="server_5xx",
                                site_code="v3_lesson_start", occurrences=3, now=NOW)
        (incident,), receipts = await self.counts()
        self.assertEqual((incident.platform, incident.occurrence_count, receipts), ("server", 3, 1))
        async with self.sessions() as db:
            with self.assertRaises(IntakeRejected):
                await ingest_server(db, feature_code="lessons", failure_code="api_5xx", site_code="x")

    async def test_account_deletion_removes_receipts_and_keeps_aggregates(self):
        from app.repositories.user_repo import UserRepository
        await self.send(batch(event_body(), event_body()))
        async with self.sessions() as db, db.begin():
            self.assertTrue(await UserRepository(db).delete_by_user_id(1))
        (incident,), receipts = await self.counts()
        self.assertEqual((receipts, incident.occurrence_count), (0, 2))

    async def test_purge_is_bounded_and_keeps_open_incidents(self):
        await self.send(batch(*[event_body() for _ in range(5)]), now=NOW - timedelta(days=31))
        async with self.sessions() as db, db.begin():
            self.assertEqual(await purge_diagnostics(db, now=NOW, limit=3), (3, 0))
        async with self.sessions() as db, db.begin():
            self.assertEqual(await purge_diagnostics(db, now=NOW, limit=3), (2, 0))
        (incident,), receipts = await self.counts()
        self.assertEqual(receipts, 0)
        async with self.sessions() as db, db.begin():
            db.add(AdminPwaInboxTriage(source="diagnostic", source_id=incident.id, status="resolved",
                                       priority="normal", revision=1, updated_at=NOW))
            row = await db.get(DiagnosticIncident, incident.id)
            row.last_seen_at = NOW - timedelta(days=181)
        async with self.sessions() as db, db.begin():
            self.assertEqual(await purge_diagnostics(db, now=NOW), (0, 1))
        self.assertEqual(await self.counts(), ([], 0))


@unittest.skipUnless(PG_URL, "set MONITORING_TEST_DATABASE_URL or ANALYTICS_TEST_DATABASE_URL")
class PostgresIntakeTests(unittest.IsolatedAsyncioTestCase):
    async def send(self, sessions, owner, *items):
        events, _ = parse_batch(batch(*items), platform="android", now=NOW)
        async with sessions() as db, db.begin():
            return await ingest(db, owner_user_id=owner, events=events, now=NOW)

    async def test_concurrent_workers_create_one_incident(self):
        async with pg_sessions(PG_URL) as sessions:
            await asyncio.gather(self.send(sessions, 1, event_body()), self.send(sessions, 2, event_body()))
            async with sessions() as db:
                incidents = (await db.execute(select(DiagnosticIncident))).scalars().all()
            self.assertEqual([row.occurrence_count for row in incidents], [2])

    async def test_retry_at_the_hourly_cap_never_inflates_refused_counts(self):
        async with pg_sessions(PG_URL) as sessions:
            initial = event_body()
            await self.send(sessions, 1, initial)
            for n in range(1, catalog.HOURLY_CAP_PER_ACCOUNT, catalog.MAX_EVENTS_PER_BATCH):
                count = min(catalog.MAX_EVENTS_PER_BATCH, catalog.HOURLY_CAP_PER_ACCOUNT - n)
                await self.send(sessions, 1, *[event_body() for _ in range(count)])
            result = await self.send(sessions, 1, initial)
            self.assertEqual((result.duplicates, result.refused), (1, 0))

    async def test_cap_holds_under_parallel_requests(self):
        async with pg_sessions(PG_URL) as sessions:
            per_request = catalog.MAX_EVENTS_PER_BATCH
            requests = catalog.HOURLY_CAP_PER_ACCOUNT // per_request + 2
            await asyncio.gather(*[self.send(sessions, 1, *[event_body() for _ in range(per_request)])
                                   for _ in range(requests)])
            async with sessions() as db:
                stored = await db.scalar(select(func.count()).select_from(DiagnosticReceipt))
                refused = await db.scalar(select(func.sum(DiagnosticIncident.refused_count)))
            self.assertEqual(stored, catalog.HOURLY_CAP_PER_ACCOUNT)
            self.assertEqual(refused, requests * per_request - catalog.HOURLY_CAP_PER_ACCOUNT)

    async def test_retention_skips_a_locked_receipt_and_does_not_double_count(self):
        async with pg_sessions(PG_URL) as sessions:
            old = NOW - timedelta(days=31)
            events, _ = parse_batch(batch(event_body(), event_body()), platform="android", now=old)
            async with sessions() as db, db.begin():
                await ingest(db, owner_user_id=1, events=events, now=old)
            async with sessions() as locker, locker.begin():
                locked = await locker.scalar(select(DiagnosticReceipt.id)
                                             .order_by(DiagnosticReceipt.id).limit(1).with_for_update())
                async with sessions() as worker, worker.begin():
                    self.assertEqual(await purge_diagnostics(worker, now=NOW, limit=2), (1, 0))
                    self.assertEqual((await worker.scalars(select(DiagnosticReceipt.id))).all(), [locked])
            async with sessions() as worker, worker.begin():
                self.assertEqual(await purge_diagnostics(worker, now=NOW, limit=2), (1, 0))

    async def test_hourly_retention_catches_up_in_bounded_batches_without_deleting_fresh_rows(self):
        old = NOW - timedelta(days=31)
        expired = catalog.PURGE_BATCH * MAX_BATCHES_PER_PASS + 3
        async with pg_sessions(PG_URL) as sessions:
            await self.send(sessions, 1, event_body())
            async with sessions() as db, db.begin():
                incident_id = await db.scalar(select(DiagnosticIncident.id))
                await db.execute(insert(DiagnosticReceipt), [
                    dict(incident_id=incident_id, user_id=1, event_id=str(uuid4()),
                         received_at=old, outcome="failed")
                    for _ in range(expired)
                ])
            settings = SimpleNamespace(DB_POOL_SIZE=5, DB_MAX_OVERFLOW=3)
            self.assertEqual(await run_diagnostic_retention(sessions, settings, now=NOW), (expired - 3, 0))
            async with sessions() as db:
                self.assertEqual(await db.scalar(select(func.count()).select_from(DiagnosticReceipt)), 4)
            self.assertEqual(await run_diagnostic_retention(sessions, settings, now=NOW), (3, 0))
            async with sessions() as db:
                self.assertEqual((await db.scalars(select(DiagnosticReceipt.received_at))).all(), [NOW])
                self.assertIsNotNone(await db.get(DiagnosticIncident, incident_id))

    async def test_resolved_incident_waits_for_bounded_receipt_cleanup(self):
        old = NOW - timedelta(days=181)
        async with pg_sessions(PG_URL) as sessions:
            events, _ = parse_batch(batch(*[event_body() for _ in range(5)]), platform="android", now=old)
            async with sessions() as db, db.begin():
                await ingest(db, owner_user_id=1, events=events, now=old)
                incident_id = await db.scalar(select(DiagnosticIncident.id))
                db.add(AdminPwaInboxTriage(source="diagnostic", source_id=incident_id, status="resolved",
                                           priority="normal", revision=1, updated_at=old))
            async with sessions() as locker, locker.begin():
                await locker.scalar(select(DiagnosticReceipt.id)
                                    .order_by(DiagnosticReceipt.id).limit(1).with_for_update())
                async with sessions() as worker, worker.begin():
                    self.assertEqual(await purge_diagnostics(worker, now=NOW, limit=2), (2, 0))
                    self.assertEqual(await worker.scalar(select(func.count()).select_from(DiagnosticReceipt)), 3)
            async with sessions() as worker, worker.begin():
                self.assertEqual(await purge_diagnostics(worker, now=NOW, limit=2), (2, 0))
            async with sessions() as worker, worker.begin():
                self.assertEqual(await purge_diagnostics(worker, now=NOW, limit=2), (1, 1))
                self.assertIsNone(await worker.get(DiagnosticIncident, incident_id))

    async def test_account_deletion_lowers_the_affected_count(self):
        from app.repositories.user_repo import UserRepository
        async with pg_sessions(PG_URL) as sessions:
            await self.send(sessions, 1, event_body())
            await self.send(sessions, 2, event_body())
            async with sessions() as db, db.begin():
                await UserRepository(db).delete_by_user_id(1)
            async with sessions() as db:
                affected = await db.scalar(select(func.count(func.distinct(DiagnosticReceipt.user_id))))
                incident = (await db.execute(select(DiagnosticIncident))).scalar_one()
            self.assertEqual((affected, incident.occurrence_count), (1, 2))


if __name__ == "__main__":
    unittest.main()
