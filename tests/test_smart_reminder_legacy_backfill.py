"""Legacy import safety on SQLite and a disposable loopback PostgreSQL schema."""

import asyncio
from datetime import datetime, time, timezone
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import event, func, insert, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.smart_reminder import (
    SmartReminderAttempt, SmartReminderCapability, SmartReminderConsent,
    SmartReminderJob, SmartReminderPreference,
)
from app.db.models.user import User
from app.services.smart_reminder_legacy_backfill import SmartReminderLegacyBackfillService
from app.services.smart_reminder_legacy_evidence import LegacyEvidenceUnavailable
from tests import test_smart_reminder_legacy_evidence as evidence_tests


PG_URL = os.environ.get("SMART_REMINDER_TEST_DATABASE_URL", "")
PREF = SmartReminderPreference.__table__
CONSENT = SmartReminderConsent.__table__


class BackfillChecks:
    postgres = False
    _progress = evidence_tests.SmartReminderLegacyEvidenceTests._progress
    _device = evidence_tests.SmartReminderLegacyEvidenceTests._device
    _deletion = evidence_tests.SmartReminderLegacyEvidenceTests._deletion

    async def asyncSetUp(self):
        self.admin = None
        if self.postgres:
            url = make_url(PG_URL)
            if (url.drivername != "postgresql+asyncpg" or
                    url.host not in {"127.0.0.1", "localhost", "::1"} or
                    not (url.database or "").startswith("smart_reminder_qa") or url.query):
                raise RuntimeError("Use a loopback disposable smart_reminder_qa database")
            self.schema = "smart_backfill_" + uuid4().hex
            self.admin = create_async_engine(url)
            async with self.admin.begin() as c:
                await c.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            self.engine = create_async_engine(url, connect_args={
                "server_settings": {"search_path": self.schema}})
        else:
            self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            @event.listens_for(self.engine.sync_engine, "connect")
            def foreign_keys(dbapi, _):
                dbapi.execute("PRAGMA foreign_keys=ON")
        self.now = datetime.now(timezone.utc)
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions.begin() as s:
            s.add_all([User(id=1, telegram_id=3001, status="free"),
                       User(id=2, telegram_id=None, status="free"),
                       User(id=3, telegram_id=None, status="free")])

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.admin is not None:
            async with self.admin.begin() as c:
                await c.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
            await self.admin.dispose()

    async def _apply(self, user_id=1):
        async with self.sessions.begin() as s:
            result = await SmartReminderLegacyBackfillService(s).backfill(user_id)
            self.assertFalse(result.dispatch_allowed)
            for model in (SmartReminderJob, SmartReminderAttempt):
                self.assertEqual(await s.scalar(select(func.count()).select_from(model)), 0)
            return result

    async def _rows(self, table):
        async with self.sessions() as s:
            return [dict(r) for r in (await s.execute(select(table))).mappings()]

    async def test_saved_on_is_channel_only_cold_start_without_action_or_lock(self):
        await self._progress(waiting="reminder_setup", offset=0)
        result = await self._apply()
        self.assertEqual((result.status, result.revision, result.inserted_consents), ("applied", 1, 1))
        pref = (await self._rows(PREF))[0]
        consent = (await self._rows(CONSENT))[0]
        self.assertIsNone(pref["master_enabled"])
        self.assertEqual((pref["time_mode"], pref["channel_mode"]), ("auto", "auto"))
        self.assertEqual((pref["legacy_time_local"], pref["legacy_offset_minutes"]), (time(14), 0))
        for key in ("manual_time_local", "timezone_name", "action_source", "action_at"):
            self.assertIsNone(pref[key])
        self.assertEqual((consent["channel"], consent["state"], consent["source"]),
                         ("telegram", "on", "legacy_course_snapshot"))
        self.assertIsNone(consent["action_at"])
        self.assertEqual(await self._rows(SmartReminderCapability.__table__), [])
        async with self.sessions() as s:
            progress = await s.get(CourseProgress, 1)
            self.assertTrue(progress.reminder_enabled)
            self.assertEqual(progress.waiting_for, "reminder_setup")

    async def test_disabled_is_preserved_without_fabricated_off_action(self):
        await self._progress(enabled=False)
        await self._apply()
        row = (await self._rows(CONSENT))[0]
        self.assertEqual(row["state"], "off")
        self.assertIsNone(row["action_at"])
        self.assertEqual((await self._rows(PREF))[0]["legacy_time_local"], time(14))

    async def test_missing_time_and_missing_settings_stay_unknown(self):
        await self._progress(selected=None)
        await self._apply()
        self.assertEqual((await self._rows(CONSENT))[0]["state"], "unknown")
        await self._apply(2)
        self.assertEqual(len(await self._rows(CONSENT)), 1)
        async with self.sessions() as s:
            self.assertEqual(await s.scalar(select(func.count()).select_from(CourseMiniAppProfile)), 0)

    async def test_native_course_flag_does_not_invent_telegram_transport_or_on(self):
        await self._progress(user_id=2)
        await self._apply(2)
        self.assertEqual((await self._rows(CONSENT))[0]["state"], "unknown")
        async with self.sessions() as s:
            self.assertIsNone((await s.get(User, 2)).telegram_id)

    async def test_android_mirrors_and_motivation_never_establish_consent_or_os_permission(self):
        await self._device("mirror-on", mirrored=True)
        await self._device("mirror-off", mirrored=False)
        await self._device("tokenless", revoked=True)
        async with self.sessions.begin() as s:
            s.add(CourseMiniAppProfile(user_id=1))  # legacy default True
            s.add(SmartReminderCapability(device_id="mirror-on", user_id=1,
                                          study_notifications_allowed=False))
        await self._apply()
        android = [r for r in await self._rows(CONSENT) if r["channel"] == "android"]
        self.assertEqual(len(android), 3)
        self.assertEqual({r["state"] for r in android}, {"unknown"})
        self.assertEqual({r["source"] for r in android}, {
            "legacy_android_mirror_on", "legacy_android_mirror_off", "legacy_android_mirror_missing"})
        self.assertTrue(all(r["action_at"] is None for r in android))
        cap = await self._rows(SmartReminderCapability.__table__)
        self.assertEqual(len(cap), 1)
        self.assertFalse(cap[0]["study_notifications_allowed"])
        self.assertIsNone(cap[0]["autonomous_study_disabled"])

    async def test_every_personal_intent_fences_entire_import_without_revision_change(self):
        await self._progress()
        intents = [dict(master_enabled=False), dict(master_enabled=True), dict(revision=4),
                   dict(grant_epoch=2), dict(action_source="user"), dict(action_at=self.now),
                   dict(time_mode="manual_locked", manual_time_local=time(2), timezone_name="Etc/UTC"),
                   dict(channel_mode="manual_locked", preferred_channel="android"),
                   dict(quiet_start=time(22), quiet_end=time(7)), dict(pause_until=self.now),
                   dict(timezone_name="Asia/Tashkent")]
        for intent in intents:
            with self.subTest(intent=intent):
                async with self.sessions() as s:
                    await s.execute(insert(PREF).values(user_id=1, **intent))
                    before = dict((await s.execute(select(PREF))).mappings().one())
                    result = await SmartReminderLegacyBackfillService(s).backfill(1)
                    self.assertEqual(result.status, "intent_preserved")
                    self.assertEqual(dict((await s.execute(select(PREF))).mappings().one()), before)
                    self.assertEqual(await s.scalar(select(func.count()).select_from(CONSENT)), 0)
                    await s.rollback()

    async def test_existing_channel_off_blocks_competing_legacy_on_and_other_owner_is_untouched(self):
        await self._progress()
        await self._device("android-on", mirrored=True)
        async with self.sessions.begin() as s:
            await s.execute(insert(CONSENT).values(user_id=1, channel="telegram", source_key="user", source="user", state="off", revision=7))
            await s.execute(insert(CONSENT).values(user_id=1, channel="android", source_key="user", source="user", state="off"))
            await s.execute(insert(PREF).values(user_id=2, master_enabled=False, grant_epoch=9))
        before = await self._rows(CONSENT)
        result = await self._apply()
        self.assertEqual(result.inserted_consents, 0)
        self.assertEqual(await self._rows(CONSENT), before)
        other = [r for r in await self._rows(PREF) if r["user_id"] == 2][0]
        self.assertFalse(other["master_enabled"])
        self.assertEqual(other["grant_epoch"], 9)

    async def test_replay_ignores_changed_legacy_on_after_new_off(self):
        await self._progress()
        await self._apply()
        before = await self._rows(CONSENT)
        async with self.sessions.begin() as s:
            await s.execute(update(PREF).values(master_enabled=False, revision=2, grant_epoch=1))
            await s.execute(update(CONSENT).values(state="off", revision=1, source="user"))
        off = await self._rows(CONSENT)
        pref = await self._rows(PREF)
        result = await self._apply()
        self.assertEqual(result.status, "already_current")
        self.assertNotEqual(off, before)
        self.assertEqual(await self._rows(CONSENT), off)
        self.assertEqual(await self._rows(PREF), pref)

    async def test_pristine_existing_time_and_newer_migration_are_never_overwritten(self):
        await self._progress()
        async with self.sessions.begin() as s:
            await s.execute(insert(PREF).values(user_id=1, legacy_time_local=time(3), legacy_offset_minutes=60))
            await s.execute(insert(PREF).values(user_id=2, migration_version=99, revision=6))
        await self._apply()
        self.assertEqual((await self._apply(2)).migration_version, 99)
        rows = {r["user_id"]: r for r in await self._rows(PREF)}
        self.assertEqual((rows[1]["legacy_time_local"], rows[1]["legacy_offset_minutes"]), (time(3), 60))
        self.assertEqual((rows[2]["migration_version"], rows[2]["revision"]), (99, 6))

    async def test_caller_rollback_and_pending_orm_writes_are_respected(self):
        await self._progress()
        async with self.sessions() as s:
            pending = CourseMiniAppProfile(user_id=2)
            s.add(pending)
            await SmartReminderLegacyBackfillService(s).backfill(1)
            self.assertIn(pending, s.new)
            self.assertEqual(await s.scalar(select(func.count()).select_from(CourseMiniAppProfile).execution_options(autoflush=False)), 0)
            await s.rollback()
        self.assertEqual(await self._rows(PREF), [])
        self.assertEqual(await self._rows(CONSENT), [])
        async with self.sessions() as s:
            self.assertTrue((await s.get(CourseProgress, 1)).reminder_enabled)

    async def test_refused_accounts_and_unknown_evidence_write_nothing(self):
        for uid in (True, 0, -1, "1", 999):
            with self.subTest(uid=uid), self.assertRaises(LegacyEvidenceUnavailable):
                await self._apply(uid)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == 1).values(status="blocked"))
            await s.execute(update(User).where(User.id == 2).values(status="unexpected"))
        for uid in (1, 2):
            with self.assertRaises(LegacyEvidenceUnavailable):
                await self._apply(uid)
        await self._deletion(owner=3, active_uid=3)
        with self.assertRaises(LegacyEvidenceUnavailable):
            await self._apply(3)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == 1).values(status="free"))
        with patch("app.services.smart_reminder_legacy_backfill.SmartReminderLegacyEvidenceService.snapshot",
                   new=AsyncMock(return_value=SimpleNamespace(evidence_version=999))):
            with self.assertRaisesRegex(LegacyEvidenceUnavailable, "evidence_version_unsupported"):
                await self._apply()
        self.assertEqual(await self._rows(PREF), [])
        self.assertEqual(await self._rows(CONSENT), [])

    async def test_device_overflow_refuses_before_creating_preferences(self):
        from app.db.models.desktop import DesktopDevice
        async with self.sessions.begin() as s:
            s.add_all([DesktopDevice(id=f"overflow-{i}", user_id=2, telegram_id=None,
                                    installation_key_hash=str(i).ljust(64, "x"), platform="android", app_version="qa")
                       for i in range(129)])
        with self.assertRaisesRegex(LegacyEvidenceUnavailable, "device_inventory_over_limit"):
            await self._apply(2)
        self.assertEqual(await self._rows(PREF), [])

    async def test_bot_block_preserves_historical_source_but_grants_no_dispatch(self):
        await self._progress()
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == 1).values(bot_blocked_at=self.now))
        result = await self._apply()
        self.assertFalse(result.dispatch_allowed)
        self.assertEqual((await self._rows(CONSENT))[0]["state"], "on")

    async def test_concurrent_import_is_serialized_on_canonical_owner(self):
        if not self.postgres:
            self.skipTest("Requires independent PostgreSQL transactions and row locks")
        await self._progress()
        results = await asyncio.wait_for(asyncio.gather(self._apply(), self._apply()), 10)
        self.assertEqual(sorted(r.status for r in results), ["already_current", "applied"])
        self.assertEqual(len(await self._rows(PREF)), 1)
        self.assertEqual(len(await self._rows(CONSENT)), 1)

    async def test_off_holding_owner_lock_wins_against_waiting_import(self):
        if not self.postgres:
            self.skipTest("Requires independent PostgreSQL transactions and row locks")
        await self._progress()
        async with self.sessions.begin() as off:
            await off.scalar(select(User.id).where(User.id == 1).with_for_update())
            task = asyncio.create_task(self._apply())
            try:
                await asyncio.sleep(0.05)
                self.assertFalse(task.done())
                await off.execute(insert(PREF).values(user_id=1, master_enabled=False, revision=1, grant_epoch=1))
            except BaseException:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                raise
        result = await asyncio.wait_for(task, 10)
        self.assertEqual(result.status, "intent_preserved")
        self.assertEqual(await self._rows(CONSENT), [])
        self.assertFalse((await self._rows(PREF))[0]["master_enabled"])


class SQLiteLegacyBackfillTests(BackfillChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(PG_URL, "Set disposable loopback SMART_REMINDER_TEST_DATABASE_URL")
class PostgreSQLLegacyBackfillTests(BackfillChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True
