"""Actual authenticated open reports never become display/learning authority."""
import asyncio
from datetime import timedelta
import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.api.smart_reminder import create_smart_reminder_router
from app.db.models.desktop import DesktopSession
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.smart_reminder_analysis import SmartReminderAnalysisObserver, RAW_RETENTION
from app.services.smart_reminder_open import SmartReminderOpenService
from app.services.smart_reminder_preferences import _utc
from app.services.smart_reminder_telegram_content import send_telegram_content
from tests import test_smart_reminder_analysis as fixture
from tests import test_smart_reminder_preferences as preferences
from tests import test_smart_reminder_telegram as telegram


class NativeOpenChecks:
    postgres = False

    async def asyncSetUp(self):
        cls = fixture.PostgreSQLAnalysisTests if self.postgres else fixture.SQLiteAnalysisTests
        self.fixture = cls(methodName="test_reserved_fact_replay_counts_once_and_source_is_unchanged")
        await self.fixture.asyncSetUp()
        self.case = self.fixture.case
        self.case.settings.SMART_REMINDER_ANALYSIS_ENABLED = True
        self.opens = SmartReminderOpenService(self.case.settings, clock=lambda: self.case.tick)
        observer = SmartReminderAnalysisObserver(self.case.settings, self.case.sessions, clock=lambda: self.case.tick)
        app = FastAPI()
        app.include_router(create_smart_reminder_router(session_factory=self.case.sessions,
            settings_obj=self.case.settings, android_delivery_factory=self.case.service,
            analysis_observer=observer, open_service=self.opens))
        await self.case.client.aclose()
        self.case.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://opens.test")
        self.url = f"/api/v3/android/smart-reminder/jobs/{self.case.job_id}/open"

    async def asyncTearDown(self):
        if hasattr(self, "case"):
            await self.fixture.asyncTearDown()

    async def posted(self, outcome="client_posted_unverified"):
        grant = await self.case.claim()
        self.assertEqual(len(grant["open_proof"]), 64)
        await self.case.receipt(grant, outcome)
        return grant

    async def report(self, proof, *, uid=1, status=200, body=None, url=None):
        r = await self.case.client.post(url or self.url, headers=await self.case.bearer(uid),
            json={"version": 1, "proof": proof} if body is None else body)
        self.assertEqual(r.status_code, status, r.text)
        self.assertEqual(r.headers["cache-control"], "no-store")
        return r.json()

    async def facts(self):
        return [r for r in await self.fixture.rows(fixture.EVENT) if r["stage"] == "client_reported_open"]

    async def test_real_claim_receipt_open_and_retry_keep_one_private_fact_and_source(self):
        grant = await self.posted()
        before = [await self.fixture.rows(t) for t in (fixture.JOB, fixture.ATTEMPT, fixture.GRANT)]
        self.assertTrue((await self.report(grant["open_proof"]))["observed"])
        rows = await self.facts()
        self.case.tick += timedelta(seconds=5)
        self.assertEqual((await self.report(grant["open_proof"]))["reason"], "open_already_observed")
        self.assertEqual(await self.facts(), rows)
        self.assertEqual(before, [await self.fixture.rows(t) for t in (fixture.JOB, fixture.ATTEMPT, fixture.GRANT)])
        self.assertEqual(_utc(rows[0]["expires_at"])-_utc(rows[0]["occurred_at"]), RAW_RETENTION)
        totals = [r for r in await self.fixture.rows(fixture.MONTHLY) if r["stage"] == "client_reported_open"]
        self.assertEqual(totals[0]["fact_count"], 1)
        self.assertNotIn(grant["open_proof"], json.dumps([dict(r) for r in rows], default=str))
        self.assertNotIn("verified_shown", {r["stage"] for r in await self.fixture.rows(fixture.EVENT)})

    async def test_optional_metadata_failure_does_not_change_committed_claim(self):
        with patch.object(self.opens, "_proof", side_effect=RuntimeError("synthetic-private-key-error")), self.assertLogs(
                "app.services.smart_reminder_open", level="WARNING") as logs:
            grant = await self.case.claim()
        self.assertTrue(grant["dispatch_allowed"])
        self.assertNotIn("open_proof", grant)
        self.assertNotIn("synthetic-private-key-error", str(logs.output))
        self.assertEqual(len(await self.fixture.rows(fixture.GRANT)), 1)

    async def test_open_detail_ages_out_without_deleting_operational_source(self):
        grant = await self.posted()
        await self.report(grant["open_proof"])
        self.fixture.moment = self.case.tick + RAW_RETENTION + timedelta(seconds=1)
        await self.fixture.analysis.retention(execute=True)
        self.assertEqual(await self.facts(), [])
        self.assertEqual(len(await self.fixture.rows(fixture.JOB)), 1)
        self.assertEqual(len(await self.fixture.rows(fixture.GRANT)), 1)
        self.assertEqual(next(r["fact_count"] for r in await self.fixture.rows(fixture.MONTHLY)
            if r["stage"] == "client_reported_open"), 1)

    async def test_forged_foreign_and_transferred_native_session_proofs_do_not_count(self):
        grant = await self.posted()
        await self.report("0"*64, status=403)
        await self.report(grant["open_proof"], uid=2, status=404)
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.GRANT).values(session_id=None))
        await self.report(grant["open_proof"], status=403)
        self.assertEqual(await self.facts(), [])

    async def test_unresolved_declined_and_unknown_sources_never_count_as_open(self):
        grant = await self.case.claim()
        self.assertFalse((await self.report(grant["open_proof"]))["observed"])
        await self.case.receipt(grant, "client_outcome_unknown")
        self.assertFalse((await self.report(grant["open_proof"]))["observed"])
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.GRANT).values(receipt_outcome="client_declined_before_post"))
            await session.execute(update(fixture.ATTEMPT).values(state="confirmed_not_displayed"))
        self.assertFalse((await self.report(grant["open_proof"]))["observed"])
        self.assertEqual(await self.facts(), [])

    async def test_disabled_metadata_and_reporting_preserve_original_claim(self):
        self.case.settings.SMART_REMINDER_ANALYSIS_ENABLED = False
        grant = await self.case.claim()
        self.assertTrue(grant["dispatch_allowed"])
        self.assertNotIn("open_proof", grant)
        self.assertEqual((await self.report("0"*64))["reason"], "open_observation_disabled")
        self.assertEqual(await self.fixture.rows(fixture.EVENT), [])

    async def test_auth_precedes_strict_body_and_no_query_or_cookie_fallback(self):
        r = await self.case.client.post(self.url, content="not-json", headers={"Content-Type":"application/json"})
        self.assertEqual(r.status_code, 401)
        for body in ({"version": True, "proof":"a"*64}, {"version":1,"proof":"A"*64},
                     {"version":1,"proof":"a"*64,"user_id":1}, {"version":"1","proof":"a"*64}):
            await self.report("a"*64, body=body, status=422)
        await self.report("a"*64, url=self.url+"?proof="+"a"*64, status=422)
        self.assertEqual(await self.facts(), [])

    async def test_revocation_block_and_deletion_are_current_guards(self):
        grant = await self.posted()
        async with self.case.sessions.begin() as session:
            await session.execute(update(User).where(User.id == 1).values(status="blocked"))
        await self.report(grant["open_proof"], status=403)
        async with self.case.sessions.begin() as session:
            await session.execute(update(User).where(User.id == 1).values(status="active"))
        await self.case._deletion()
        await self.report(grant["open_proof"], status=409)
        self.assertEqual(await self.facts(), [])

    async def test_off_does_not_erase_an_already_externalized_contact(self):
        grant = await self.posted()
        async with self.case.sessions.begin() as session:
            from app.db.models.smart_reminder import SmartReminderPreference
            await session.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id == 1)
                .values(master_enabled=False))
        self.assertTrue((await self.report(grant["open_proof"]))["observed"])
        self.assertEqual(len(await self.fixture.rows(fixture.ATTEMPT)), 1)

    async def test_bad_frozen_day_and_source_binding_do_not_count(self):
        grant = await self.posted()
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(timezone_name="Unknown/Zone"))
        self.assertFalse((await self.report(grant["open_proof"]))["observed"])
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(timezone_name="Etc/UTC"))
            await session.execute(update(fixture.GRANT).values(preference_revision=99))
        self.assertFalse((await self.report(grant["open_proof"]))["observed"])
        self.assertEqual(await self.facts(), [])

    async def test_observation_failure_rolls_back_only_analysis_and_a_later_report_can_recover(self):
        grant = await self.posted()
        before = await self.fixture.rows(fixture.GRANT)
        original = self.opens.analysis._insert
        def fail(session, table):
            if table is fixture.MONTHLY:
                raise RuntimeError("synthetic-private-failure")
            return original(session, table)
        with patch.object(self.opens.analysis, "_insert", fail), self.assertLogs("app.api.smart_reminder", level="ERROR") as logs:
            response = await self.report(grant["open_proof"], status=503)
        self.assertNotIn("synthetic-private-failure", str(logs.output)+str(response))
        self.assertEqual(await self.facts(), [])
        self.assertEqual(await self.fixture.rows(fixture.GRANT), before)
        self.assertTrue((await self.report(grant["open_proof"]))["observed"])

    async def test_populated_stage_extension_roundtrip_preserves_old_facts_and_source(self):
        grant = await self.posted()
        tables = (fixture.EVENT, fixture.MONTHLY, fixture.JOB, fixture.ATTEMPT, fixture.GRANT)
        before = [await self.fixture.rows(t) for t in tables]
        def cycle(c):
            with Operations.context(MigrationContext.configure(c)):
                fixture.baseline_migration.downgrade()
                fixture.return_migration.downgrade()
                fixture.activity_migration.downgrade()
                fixture.study_migration.downgrade()
                fixture.open_migration.downgrade()
                fixture.open_migration.upgrade()
                fixture.study_migration.upgrade()
                fixture.activity_migration.upgrade()
                fixture.return_migration.upgrade()
                fixture.baseline_migration.upgrade()
        async with self.case.engine.begin() as c:
            await c.run_sync(cycle)
        self.assertEqual(before,[await self.fixture.rows(t) for t in tables])
        self.assertTrue((await self.report(grant["open_proof"]))["observed"])

    async def test_populated_open_downgrade_refuses_raw_and_anonymous_only_facts(self):
        grant = await self.posted()
        await self.report(grant["open_proof"])
        def downgrade(c):
            with Operations.context(MigrationContext.configure(c)):
                fixture.open_migration.downgrade()
        async with self.case.engine.begin() as c:
            with self.assertRaisesRegex(RuntimeError, "populated open"):
                await c.run_sync(downgrade)
        async with self.case.sessions.begin() as session:
            await session.execute(delete(fixture.EVENT).where(fixture.EVENT.c.stage == "client_reported_open"))
        async with self.case.engine.begin() as c:
            with self.assertRaisesRegex(RuntimeError, "populated open"):
                await c.run_sync(downgrade)

    async def test_open_detail_uses_existing_retention_and_account_purge(self):
        grant = await self.posted()
        await self.report(grant["open_proof"])
        async with self.case.sessions.begin() as session:
            await UserRepository(session)._delete_account(await session.get(User, 1))
        self.assertEqual(await self.facts(), [])
        self.assertEqual(next(r["fact_count"] for r in await self.fixture.rows(fixture.MONTHLY)
            if r["stage"] == "client_reported_open"), 1)

    async def test_postgres_concurrent_reports_increment_once(self):
        if not self.postgres:
            self.skipTest("PostgreSQL independent source/observation owner locks")
        grant = await self.posted()
        await asyncio.gather(*(self.report(grant["open_proof"]) for _ in range(6)))
        self.assertEqual(len(await self.facts()), 1)
        self.assertEqual(next(r["fact_count"] for r in await self.fixture.rows(fixture.MONTHLY)
            if r["stage"] == "client_reported_open"), 1)


class TelegramOpenChecks:
    postgres = False

    async def asyncSetUp(self):
        cls = telegram.PostgreSQLTelegramTests if self.postgres else telegram.SQLiteTelegramTests
        self.case = cls(methodName="test_one_committed_telegram_attempt_accepts_provider_not_display")
        await self.case.asyncSetUp()
        self.case.settings.SMART_REMINDER_ANALYSIS_ENABLED = True
        self.case.settings.BOT_TOKEN = "123456789:synthetic-test-only-telegram-open-key"
        self.opens = SmartReminderOpenService(self.case.settings, clock=lambda:self.case.tick)
        app=FastAPI()
        app.include_router(create_smart_reminder_router(session_factory=self.case.sessions,
            settings_obj=self.case.settings, open_service=self.opens))
        self.client=AsyncClient(transport=ASGITransport(app=app),base_url="https://open-telegram.test")

    async def asyncTearDown(self):
        if hasattr(self, "client"):
            await self.client.aclose()
        if hasattr(self, "case"):
            await self.case.asyncTearDown()

    async def dispatch(self, *, accepted=True):
        await self.case.active()
        planned=await self.case.prepare()
        self.case.tick=self.case.tick.replace(hour=14)
        lease=await self.case.claim(planned.job_id)
        frames=[]
        async def send(envelope):
            frames.append(envelope)
            if not accepted: raise RuntimeError("synthetic uncertain provider")
            return await send_telegram_content(self.case.bot,envelope)
        result=await self.case.dispatch(lease,send)
        self.assertEqual(result.reason,"telegram_provider_accepted" if accepted else "telegram_unknown")
        url=frames[0].content.markup.inline_keyboard[0][0].web_app.url
        fragment=parse_qs(urlsplit(url).fragment)
        self.assertEqual(fragment["smart_job"],[planned.job_id])
        return planned.job_id,fragment["smart_proof"][0]

    async def report(self, job, proof, *, headers=None, status=200):
        signer=preferences.PreferenceChecks.telegram
        r=await self.client.post(f"/api/v3/smart-reminder/jobs/{job}/open",
            headers=headers if headers is not None else signer(self.case),json={"version":1,"proof":proof})
        self.assertEqual(r.status_code,status,r.text)
        return r.json()

    async def test_actual_telegram_content_fragment_and_signed_owner_report_once(self):
        job,proof=await self.dispatch()
        self.assertTrue((await self.report(job,proof))["observed"])
        self.assertEqual((await self.report(job,proof))["reason"],"open_already_observed")
        facts=[r for r in await self.case.rows(fixture.EVENT) if r["stage"]=="client_reported_open"]
        self.assertEqual(len(facts),1)
        self.assertEqual(facts[0]["channel"],"telegram")
        self.case.bot.send_message.assert_awaited_once()
        sent = self.case.bot.send_message.call_args.kwargs["reply_markup"]
        fragment = parse_qs(urlsplit(sent.inline_keyboard[0][0].web_app.url).fragment)
        self.assertEqual(fragment, {"smart_job":[job],"smart_proof":[proof]})

    async def test_forged_unsigned_stale_and_foreign_transport_cannot_count(self):
        job,proof=await self.dispatch()
        await self.report(job,"0"*64,status=403)
        await self.report(job,proof,headers={},status=401)
        await self.report(job,proof,headers=preferences.PreferenceChecks.telegram(self.case,age=86401),status=401)
        await self.report(job,proof,headers=preferences.PreferenceChecks.telegram(self.case,uid=999999),status=404)
        self.assertEqual([r for r in await self.case.rows(fixture.EVENT) if r["stage"]=="client_reported_open"],[])

    async def test_uncertain_provider_and_next_day_are_not_confirmed_open_sources(self):
        job,proof=await self.dispatch(accepted=False)
        self.assertFalse((await self.report(job,proof))["observed"])
        self.case.tick=self.case.tick.replace(hour=0)+timedelta(days=1)
        self.assertFalse((await self.report(job,proof))["observed"])


class SQLiteNativeOpenTests(NativeOpenChecks,unittest.IsolatedAsyncioTestCase):
    pass

@unittest.skipUnless(fixture.PG_URL,"Owned loopback PostgreSQL required")
class PostgreSQLNativeOpenTests(NativeOpenChecks,unittest.IsolatedAsyncioTestCase):
    postgres=True

class SQLiteTelegramOpenTests(TelegramOpenChecks,unittest.IsolatedAsyncioTestCase):
    pass

@unittest.skipUnless(fixture.PG_URL,"Owned loopback PostgreSQL required")
class PostgreSQLTelegramOpenTests(TelegramOpenChecks,unittest.IsolatedAsyncioTestCase):
    postgres=True
