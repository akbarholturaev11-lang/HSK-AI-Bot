"""Source-aware Smart migration observations; no new send authority or writes."""

from dataclasses import asdict
from datetime import datetime, time, timedelta, timezone
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.android_push import AndroidPushToken
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice
from app.db.models.user import User
from app.services.smart_reminder_legacy_evidence import (
    LegacyEvidenceUnavailable,
    SmartReminderLegacyEvidenceService,
)
from scripts import audit_smart_reminder_legacy as cli


class SmartReminderLegacyEvidenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=3001, status="free"),
                User(id=2, telegram_id=None, status="free"),
                User(id=3, telegram_id=None, status="free"),
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _snapshot(self, uid=1):
        async with self.sessions() as session:
            return await SmartReminderLegacyEvidenceService(session).snapshot(uid)

    async def _progress(self, *, user_id=1, enabled=True, selected=time(14), offset=5, waiting="none"):
        async with self.sessions() as session:
            session.add(CourseProgress(
                user_id=user_id, level="hsk1", reminder_enabled=enabled,
                reminder_time=selected, reminder_tz_offset=offset, waiting_for=waiting,
            ))
            await session.commit()

    async def _device(self, name, *, user_id=1, platform="android", mirrored=None, revoked=False):
        async with self.sessions() as session:
            session.add(DesktopDevice(
                id=name, user_id=user_id, telegram_id=3001,
                installation_key_hash=name.ljust(64, "x"), platform=platform,
                app_version="999.0.0", last_seen_at=self.now - timedelta(days=900),
                revoked_at=self.now if revoked else None,
            ))
            await session.flush()
            if mirrored is not None:
                session.add(AndroidPushToken(
                    device_id=name, token=f"synthetic-private-token-{name}",
                    study_reminders_enabled=mirrored, notifications_allowed=True,
                    timezone_name="Asia/Tashkent",
                ))
            await session.commit()

    async def _deletion(self, *, status="submitted", active_uid=1, owner=1):
        async with self.sessions() as session:
            session.add(AccountDeletionRequest(
                id="p0-deletion", user_id=owner, active_user_id=active_uid,
                provider="telegram", status=status, secret_hash="a" * 64,
                client_hash="b" * 64, created_at=self.now,
                expires_at=self.now - timedelta(days=1),
            ))
            await session.commit()

    async def test_motivation_default_does_not_create_study_consent(self):
        async with self.sessions() as session:
            session.add(CourseMiniAppProfile(user_id=1))
            await session.commit()
        snapshot = await self._snapshot()
        self.assertTrue(snapshot.motivation_enabled)
        self.assertEqual(snapshot.telegram.study_state, "unknown")
        self.assertIsNone(snapshot.telegram.setting_enabled)
        self.assertFalse(snapshot.dispatch_allowed)

    async def test_saved_telegram_on_keeps_time_without_inventing_lock_or_timestamp(self):
        await self._progress(waiting="reminder_setup", offset=0)
        snapshot = await self._snapshot()
        self.assertEqual(snapshot.telegram.study_state, "legacy_on")
        self.assertEqual(snapshot.telegram.saved_time_local, "14:00:00")
        self.assertEqual(snapshot.telegram.saved_offset_minutes, 0)
        self.assertFalse(snapshot.telegram.manual_lock_proven)
        self.assertIsNone(snapshot.telegram.action_timestamp)
        self.assertFalse(snapshot.dispatch_allowed)

    async def test_false_default_is_not_timestamped_explicit_off(self):
        await self._progress(enabled=False, selected=None)
        snapshot = await self._snapshot()
        self.assertEqual(snapshot.telegram.study_state, "not_enabled")
        self.assertIsNone(snapshot.telegram.action_timestamp)
        self.assertFalse(snapshot.dispatch_allowed)

    async def test_enabled_without_time_is_unknown(self):
        await self._progress(selected=None)
        self.assertEqual((await self._snapshot()).telegram.study_state, "unknown")

    async def test_native_only_account_cannot_gain_telegram_consent(self):
        await self._progress(user_id=2)
        await self._device("other-native-device", user_id=3, mirrored=True)
        snapshot = await self._snapshot(2)
        self.assertFalse(snapshot.telegram.transport_present)
        self.assertEqual(snapshot.telegram.study_state, "unknown")
        self.assertEqual(snapshot.android, ())

    async def test_motivation_off_does_not_erase_telegram_study_on(self):
        await self._progress()
        async with self.sessions() as session:
            session.add(CourseMiniAppProfile(user_id=1, notifications_enabled=False))
            await session.commit()
        snapshot = await self._snapshot()
        self.assertFalse(snapshot.motivation_enabled)
        self.assertEqual(snapshot.telegram.study_state, "legacy_on")

    async def test_mixed_device_mirrors_never_grant_study_os_or_claim_permission(self):
        await self._progress()
        await self._device("android-off", mirrored=False)
        await self._device("android-on", mirrored=True)
        snapshot = await self._snapshot()
        self.assertEqual([d.mirrored_setting_enabled for d in snapshot.android], [False, True])
        for device in snapshot.android:
            self.assertEqual(device.study_consent, "unknown")
            self.assertEqual(device.study_os_permission, "unknown")
            self.assertEqual(device.server_claim_capability, "unknown")
            self.assertIsNone(device.action_timestamp)
        self.assertIn("legacy_android_sender_possible", snapshot.cutover_blockers)
        self.assertFalse(snapshot.dispatch_allowed)

    async def test_revoked_tokenless_old_android_still_blocks_fencing(self):
        await self._device("old-offline-device", revoked=True)
        snapshot = await self._snapshot()
        self.assertTrue(snapshot.android[0].revoked)
        self.assertFalse(snapshot.android[0].push_registered)
        self.assertIsNone(snapshot.android[0].mirrored_setting_enabled)
        self.assertIn("legacy_android_sender_possible", snapshot.cutover_blockers)

    async def test_canonical_owner_wins_over_stale_telegram_metadata_and_desktop(self):
        await self._device("foreign-device", user_id=2, mirrored=True)
        await self._device("desktop-device", platform="macos", mirrored=True)
        self.assertEqual((await self._snapshot()).android, ())

    async def test_bot_block_preserves_observed_on_but_cannot_grant_delivery(self):
        await self._progress()
        async with self.sessions() as session:
            (await session.get(User, 1)).bot_blocked_at = self.now
            await session.commit()
        snapshot = await self._snapshot()
        self.assertTrue(snapshot.telegram.transport_blocked)
        self.assertEqual(snapshot.telegram.study_state, "legacy_on")
        self.assertFalse(snapshot.dispatch_allowed)

    async def test_unknown_fleet_never_becomes_fenced_from_absent_devices(self):
        await self._progress()
        snapshot = await self._snapshot()
        self.assertEqual(snapshot.android, ())
        self.assertIn("legacy_fleet_fencing_unverified", snapshot.cutover_blockers)
        self.assertFalse(snapshot.dispatch_allowed)

    async def test_submitted_deletion_vetoes_an_otherwise_active_account(self):
        await self._deletion()
        with self.assertRaisesRegex(LegacyEvidenceUnavailable, "account_deletion_pending"):
            await self._snapshot()

    async def test_submitted_deletion_with_missing_active_alias_still_vetoes(self):
        await self._deletion(active_uid=None)
        with self.assertRaisesRegex(LegacyEvidenceUnavailable, "account_deletion_pending"):
            await self._snapshot()

    async def test_unsubmitted_deletion_challenge_is_not_an_opt_out(self):
        await self._deletion(status="pending")
        self.assertFalse((await self._snapshot()).dispatch_allowed)

    async def test_blocked_unknown_and_missing_account_are_refused(self):
        for status in ("blocked", "unrecognized"):
            async with self.sessions() as session:
                (await session.get(User, 1)).status = status
                await session.commit()
            with self.subTest(status=status), self.assertRaises(LegacyEvidenceUnavailable):
                await self._snapshot()
        with self.assertRaisesRegex(LegacyEvidenceUnavailable, "account_not_found"):
            await self._snapshot(999)

    async def test_free_trial_and_expired_are_observed_without_paid_access_inference(self):
        for status in ("free", "trial", "expired", "active"):
            async with self.sessions() as session:
                (await session.get(User, 1)).status = status
                await session.commit()
            with self.subTest(status=status):
                self.assertFalse((await self._snapshot()).dispatch_allowed)

    async def test_noncanonical_id_types_are_rejected_before_sql(self):
        async with self.sessions() as session:
            with patch.object(session, "execute", new_callable=AsyncMock) as query:
                for uid in (True, False, None, "1", 1.0, 0, -1):
                    with self.subTest(uid=uid), self.assertRaisesRegex(
                        LegacyEvidenceUnavailable, "canonical_user_id_required",
                    ):
                        await SmartReminderLegacyEvidenceService(session).snapshot(uid)
                query.assert_not_awaited()

    async def test_over_limit_inventory_refuses_instead_of_hiding_offline_install(self):
        for i in range(5):
            await self._device(f"device-{i}", revoked=i == 4)
        with patch("app.services.smart_reminder_legacy_evidence.MAX_DEVICE_OBSERVATIONS", 4):
            with self.assertRaisesRegex(LegacyEvidenceUnavailable, "device_inventory_over_limit"):
                await self._snapshot()

    async def test_reads_never_flush_commit_initialize_profile_or_load_provider_secrets(self):
        await self._device("device-on", mirrored=True)
        statements = []
        def capture(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)
        event.listen(self.engine.sync_engine, "before_cursor_execute", capture)
        try:
            async with self.sessions() as session:
                user = await session.get(User, 1)
                user.language = "ru"  # Pending caller state must not be flushed.
                statements.clear()
                with patch.object(session, "commit", new_callable=AsyncMock) as commit, patch.object(
                    session, "flush", new_callable=AsyncMock,
                ) as flush:
                    snapshot = await SmartReminderLegacyEvidenceService(session).snapshot(1)
                    commit.assert_not_awaited()
                    flush.assert_not_awaited()
                self.assertTrue(all(s.lstrip().upper().startswith("SELECT") for s in statements))
                self.assertFalse(any("android_push_tokens.token" in s for s in statements))
                serialized = json.dumps(asdict(snapshot))
                for private in ("synthetic-private-token", "installation_key_hash", "telegram_id", "full_name"):
                    self.assertNotIn(private, serialized)
                await session.rollback()
            async with self.sessions() as session:
                self.assertNotEqual((await session.get(User, 1)).language, "ru")
                self.assertEqual(await session.scalar(select(func.count()).select_from(CourseMiniAppProfile)), 0)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", capture)


class LocalAuditCliTests(unittest.IsolatedAsyncioTestCase):
    def test_remote_targets_and_query_overrides_are_rejected_without_echoing_credentials(self):
        for value in (
            "", "garbage", "postgresql+asyncpg://qa:private-test@remote.invalid/db",
            "postgresql+asyncpg://qa:private-test@localhost/db?host=remote.invalid",
            "sqlite+aiosqlite:///:memory:", "sqlite+aiosqlite:///missing-file.db",
        ):
            with self.subTest(value=value), self.assertRaises(cli.LocalAuditTargetError) as error:
                cli.validate_local_target(value)
            self.assertNotIn("private-test", str(error.exception))

    async def test_existing_local_sqlite_audit_is_read_only_and_preserves_database(self):
        with TemporaryDirectory() as folder:
            database = Path(folder) / "synthetic-qa.sqlite"
            url = f"sqlite+aiosqlite:///{database}"
            engine = create_async_engine(url)
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            async with async_sessionmaker(engine)() as session:
                session.add(User(id=1, status="free"))
                await session.commit()
            await engine.dispose()
            original = database.read_bytes()
            observed_readonly = []
            original_snapshot = SmartReminderLegacyEvidenceService.snapshot
            async def inspect(service, user_id):
                observed_readonly.append(await service.session.scalar(text("PRAGMA query_only")))
                return await original_snapshot(service, user_id)
            with patch.object(SmartReminderLegacyEvidenceService, "snapshot", inspect):
                result = await cli.audit(cli.validate_local_target(url), 1)
            self.assertEqual(observed_readonly, [1])
            self.assertEqual(result["user_id"], 1)
            self.assertFalse(result["dispatch_allowed"])
            self.assertEqual(database.read_bytes(), original)

    def test_main_sanitizes_unexpected_driver_errors(self):
        with patch("sys.argv", ["audit", "--user-id", "1"]), patch.dict(
            "os.environ", {"SMART_REMINDER_AUDIT_DATABASE_URL": "postgresql+asyncpg://qa:private-test@localhost/db"},
        ), patch.object(cli, "audit", new=AsyncMock(side_effect=ValueError("private-test"))), patch(
            "sys.stderr", new_callable=io.StringIO,
        ) as output:
            self.assertEqual(cli.main(), 2)
        self.assertEqual(output.getvalue().strip(), "audit_database_unavailable")
