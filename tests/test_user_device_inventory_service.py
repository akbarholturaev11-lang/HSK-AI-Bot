import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.desktop import DesktopDevice
from app.db.models.user import User
from app.services.app_promo_decision_service import AppPromoDecisionService
from app.services.user_device_inventory_service import (
    UserDeviceInventoryService,
    normalize_client_platform,
)


NOW = datetime.now(timezone.utc)


def _user(user_id: int, telegram_id: int) -> User:
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=f"User {user_id}",
        language="uz",
        level="hsk1",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        daily_practice_streak=0,
        created_at=NOW,
        last_active_at=NOW,
    )


def _device(
    *,
    device_id: str,
    user_id: int,
    telegram_id: int,
    platform: str,
    revoked: bool = False,
    version: str = "1.0.0",
    last_seen: datetime | None = None,
) -> DesktopDevice:
    return DesktopDevice(
        id=device_id,
        user_id=user_id,
        telegram_id=telegram_id,
        installation_key_hash=(device_id * 64)[:64],
        platform=platform,
        app_version=version,
        first_open_at=NOW - timedelta(days=3),
        last_seen_at=last_seen or NOW,
        revoked_at=(NOW - timedelta(days=1)) if revoked else None,
        created_at=NOW - timedelta(days=4),
    )


class ClientPlatformNormalizationTests(unittest.TestCase):
    def test_known_platforms_are_normalized_without_storing_raw_user_agent(self):
        self.assertEqual(normalize_client_platform("android"), "android")
        self.assertEqual(normalize_client_platform("iPhone"), "ios")
        self.assertEqual(normalize_client_platform("mac"), "macos")
        self.assertEqual(normalize_client_platform("win32"), "windows")
        self.assertEqual(normalize_client_platform("something-weird"), "unknown")


class DeviceIntelligenceDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([_user(1, 1001), _user(2, 2002), _user(3, 3003)])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_presence_is_compact_per_platform_and_updates_foreground(self):
        async with self.sessions() as session:
            service = UserDeviceInventoryService(session)
            first = await service.record_miniapp_presence(
                telegram_id=1001,
                platform="android",
                source="status",
            )
            first_seen = first.first_seen_at
            await service.record_miniapp_presence(
                telegram_id=1001,
                platform="android",
                source="status_again",
            )
            await service.record_miniapp_presence(
                telegram_id=1001,
                platform="ios",
                source="other_phone",
            )
            await session.commit()

        async with self.sessions() as session:
            snapshot = await UserDeviceInventoryService(session).snapshot(1001)

        platforms = [row["platform"] for row in snapshot["presences"]]
        self.assertCountEqual(platforms, ["android", "ios"])
        android = next(row for row in snapshot["presences"] if row["platform"] == "android")
        self.assertTrue(android["first_seen_at"])
        self.assertTrue(android["last_foreground_at"])
        self.assertEqual(android["source"], "status_again")
        self.assertEqual(first_seen.isoformat(), android["first_seen_at"])

    async def test_native_install_uses_existing_registry_and_revoked_is_not_installed(self):
        async with self.sessions() as session:
            session.add_all(
                [
                    _device(
                        device_id="android-live",
                        user_id=1,
                        telegram_id=1001,
                        platform="android",
                    ),
                    _device(
                        device_id="windows-old",
                        user_id=1,
                        telegram_id=1001,
                        platform="windows",
                        revoked=True,
                    ),
                ]
            )
            await session.commit()

        async with self.sessions() as session:
            service = UserDeviceInventoryService(session)
            installed = await service.installed_native_platforms(1001)
            snapshot = await service.snapshot(1001)

        self.assertEqual(installed, {"android"})
        self.assertEqual(len(snapshot["native_devices"]), 2)
        self.assertEqual(snapshot["installed_native_platforms"], ["android"])
        revoked = next(row for row in snapshot["native_devices"] if row["platform"] == "windows")
        self.assertFalse(revoked["installed"])

    async def test_snapshot_does_not_confuse_background_contact_with_foreground_open(self):
        async with self.sessions() as session:
            session.add(
                _device(
                    device_id="android-bg",
                    user_id=1,
                    telegram_id=1001,
                    platform="android",
                    last_seen=NOW,
                )
            )
            await session.commit()

        async with self.sessions() as session:
            snapshot = await UserDeviceInventoryService(session).snapshot(1001)
        row = snapshot["native_devices"][0]
        self.assertTrue(row["last_contact_at"])
        self.assertEqual(row["last_foreground_at"], "")

        async with self.sessions() as session:
            session.add(
                CourseMiniAppEvent(
                    user_id=1,
                    telegram_id=1001,
                    event_name="android_app_opened",
                    source="android_app",
                    payload_json='{"platform":"android","device_id":"android-bg"}',
                    created_at=NOW,
                )
            )
            await session.commit()

        async with self.sessions() as session:
            snapshot = await UserDeviceInventoryService(session).snapshot(1001)
        self.assertTrue(snapshot["native_devices"][0]["last_foreground_at"])

    async def test_aggregate_splits_miniapp_only_native_only_and_both(self):
        async with self.sessions() as session:
            service = UserDeviceInventoryService(session)
            await service.record_miniapp_presence(
                telegram_id=1001, platform="android", source="status"
            )
            await service.record_miniapp_presence(
                telegram_id=2002, platform="ios", source="status"
            )
            session.add_all(
                [
                    _device(
                        device_id="native-both",
                        user_id=1,
                        telegram_id=1001,
                        platform="android",
                    ),
                    _device(
                        device_id="native-only",
                        user_id=3,
                        telegram_id=3003,
                        platform="windows",
                    ),
                ]
            )
            await session.commit()

        async with self.sessions() as session:
            result = await UserDeviceInventoryService(session).aggregate()

        self.assertEqual(result["miniapp_users_total"], 2)
        self.assertEqual(result["native_users_total"], 2)
        self.assertEqual(result["miniapp_and_native_users"], 1)
        self.assertEqual(result["miniapp_only_users"], 1)
        self.assertEqual(result["native_only_users"], 1)
        self.assertEqual(result["miniapp_to_native_pct"], 50.0)
        self.assertEqual(result["miniapp_users_by_platform"]["android"], 1)
        self.assertEqual(result["miniapp_users_by_platform"]["ios"], 1)


class PlatformPromoDecisionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user(1, 1001))
            await session.commit()
        self.targets = {
            "android": True,
            "windows": True,
            "macos": True,
            "ios": False,
        }

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _decide(self, platform: str):
        async with self.sessions() as session:
            return await AppPromoDecisionService(session).decide(
                telegram_id=1001,
                current_platform=platform,
                available_targets=self.targets,
            )

    async def test_android_without_native_install_is_eligible_for_android_only(self):
        result = await self._decide("android")
        self.assertTrue(result["eligible"])
        self.assertEqual(result["target_platform"], "android")

    async def test_same_platform_install_permanently_suppresses_auto_promo(self):
        async with self.sessions() as session:
            session.add(
                _device(
                    device_id="android-installed",
                    user_id=1,
                    telegram_id=1001,
                    platform="android",
                )
            )
            await session.commit()

        result = await self._decide("android")
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "already_installed")

    async def test_windows_install_does_not_suppress_android_promo(self):
        async with self.sessions() as session:
            session.add(
                _device(
                    device_id="windows-installed",
                    user_id=1,
                    telegram_id=1001,
                    platform="windows",
                )
            )
            await session.commit()

        result = await self._decide("android")
        self.assertTrue(result["eligible"])
        self.assertEqual(result["target_platform"], "android")

    async def test_seen_on_android_starts_14_day_server_cooldown(self):
        async with self.sessions() as session:
            service = AppPromoDecisionService(session)
            marked = await service.mark(
                telegram_id=1001,
                target_platform="android",
                action="seen",
            )
            self.assertTrue(marked)
            await session.commit()

        result = await self._decide("android")
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "cooldown")
        self.assertGreater(result["cooldown_remaining_seconds"], 0)

    async def test_android_cooldown_does_not_block_windows(self):
        async with self.sessions() as session:
            service = AppPromoDecisionService(session)
            await service.mark(
                telegram_id=1001,
                target_platform="android",
                action="dismissed",
            )
            await session.commit()

        windows = await self._decide("windows")
        self.assertTrue(windows["eligible"])
        self.assertEqual(windows["target_platform"], "windows")

    async def test_ios_has_no_automatic_cross_platform_ad(self):
        result = await self._decide("ios")
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "no_matching_native_app")
        self.assertIsNone(result["target_platform"])

    async def test_revoked_android_device_no_longer_suppresses_android(self):
        async with self.sessions() as session:
            session.add(
                _device(
                    device_id="android-revoked",
                    user_id=1,
                    telegram_id=1001,
                    platform="android",
                    revoked=True,
                )
            )
            await session.commit()

        result = await self._decide("android")
        self.assertTrue(result["eligible"])

    async def test_legacy_recent_impression_is_respected_during_migration(self):
        async with self.sessions() as session:
            session.add(
                CourseMiniAppEvent(
                    user_id=1,
                    telegram_id=1001,
                    event_name="desktop_promo_seen",
                    source="home_prompt",
                    created_at=NOW - timedelta(days=1),
                )
            )
            await session.commit()

        result = await self._decide("windows")
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "cooldown")


if __name__ == "__main__":
    unittest.main()
