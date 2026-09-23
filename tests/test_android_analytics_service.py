import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.course_miniapp_event import COURSE_MINIAPP_EVENT_NAMES, CourseMiniAppEvent
from app.db.models.desktop import DesktopDevice
from app.db.models.user import User
from app.services.android_analytics_service import (
    ANDROID_FUNNEL_STAGES,
    ANDROID_UPDATE_EVENT,
    AndroidAnalyticsService,
)


NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


def _device(
    device_id,
    *,
    user_id=1,
    app_version="1.6.4",
    opened_hours_ago=1,
    last_seen_hours_ago=1,
    created_hours_ago=48,
    revoked=False,
):
    return SimpleNamespace(
        id=device_id,
        user_id=user_id,
        app_version=app_version,
        first_open_at=None if opened_hours_ago is None else NOW - timedelta(hours=opened_hours_ago),
        last_seen_at=None if last_seen_hours_ago is None else NOW - timedelta(hours=last_seen_hours_ago),
        revoked_at=NOW - timedelta(hours=1) if revoked else None,
        created_at=NOW - timedelta(hours=created_hours_ago),
    )


def _open_row(telegram_id, *, device_id, hours_ago=1):
    return SimpleNamespace(
        created_at=NOW - timedelta(hours=hours_ago),
        telegram_id=telegram_id,
        payload_json=json.dumps({"platform": "android", "device_id": device_id}),
    )


def _totals(**counts):
    return {
        name: {"users": values[0], "events": values[1]}
        for name, values in counts.items()
    }


def _snapshot(*, totals=None, device_rows=(), open_rows=(), since=None, latest_release=None):
    return AndroidAnalyticsService.build_snapshot(
        totals=totals or {},
        device_rows=device_rows,
        open_rows=open_rows,
        now=NOW,
        since=since,
        latest_release=latest_release,
    )


class AndroidAnalyticsEventNamesTest(unittest.TestCase):
    def test_every_read_event_is_a_declared_event_name(self):
        for name in AndroidAnalyticsService.EVENT_NAMES:
            self.assertIn(name, COURSE_MINIAPP_EVENT_NAMES, name)


class AndroidRegistryTest(unittest.TestCase):
    def test_installed_counts_linked_devices_and_excludes_revoked(self):
        snapshot = _snapshot(
            device_rows=[
                _device("d1", user_id=1),
                _device("d2", user_id=1),
                _device("d3", user_id=2),
                _device("d4", user_id=3, revoked=True),
            ]
        )
        registry = snapshot["registry"]
        self.assertEqual(registry["installed_devices"], 3)
        self.assertEqual(registry["installed_users"], 2)
        self.assertEqual(registry["unlinked_devices"], 1)

    def test_device_that_never_opened_is_counted_apart(self):
        snapshot = _snapshot(
            device_rows=[
                _device("d1", user_id=1, opened_hours_ago=2),
                _device("d2", user_id=2, opened_hours_ago=None),
            ]
        )
        registry = snapshot["registry"]
        self.assertEqual(registry["opened_devices"], 1)
        self.assertEqual(registry["opened_users"], 1)
        self.assertEqual(registry["never_opened_devices"], 1)
        self.assertEqual(snapshot["rates"]["opened_per_installed"], 50.0)

    def test_new_devices_are_bounded_by_the_period(self):
        device_rows = [
            _device("d1", user_id=1, created_hours_ago=2),
            _device("d2", user_id=2, created_hours_ago=24 * 40),
        ]
        weekly = _snapshot(device_rows=device_rows, since=NOW - timedelta(days=7))
        self.assertTrue(weekly["registry"]["period_bounded"])
        self.assertEqual(weekly["registry"]["new_devices_in_period"], 1)
        self.assertEqual(weekly["registry"]["new_users_in_period"], 1)

        all_time = _snapshot(device_rows=device_rows)
        self.assertFalse(all_time["registry"]["period_bounded"])
        self.assertEqual(all_time["registry"]["new_devices_in_period"], 2)

    def test_online_windows_come_from_last_seen(self):
        snapshot = _snapshot(
            device_rows=[
                _device("d1", user_id=1, last_seen_hours_ago=2),
                _device("d2", user_id=2, last_seen_hours_ago=24 * 3),
                _device("d3", user_id=3, last_seen_hours_ago=24 * 29),
                _device("d4", user_id=4, last_seen_hours_ago=24 * 60),
            ]
        )
        registry = snapshot["registry"]
        self.assertEqual(registry["online_devices_1d"], 1)
        self.assertEqual(registry["online_devices_7d"], 2)
        self.assertEqual(registry["online_devices_30d"], 3)
        self.assertEqual(registry["online_users_30d"], 3)


class AndroidActiveTest(unittest.TestCase):
    def test_active_windows_count_opens_not_devices_seen_online(self):
        """A phone that only pinged the server in the background is not active.

        The home-screen widget refreshes on its own, so last_seen_at alone
        must never be reported as somebody using the app.
        """

        snapshot = _snapshot(
            device_rows=[_device("d1", user_id=1, last_seen_hours_ago=1)],
            open_rows=[],
        )
        self.assertEqual(snapshot["registry"]["online_devices_1d"], 1)
        self.assertEqual(snapshot["active"]["dau"], 0)
        self.assertEqual(snapshot["active"]["dau_devices"], 0)

    def test_active_windows_split_users_and_devices(self):
        snapshot = _snapshot(
            device_rows=[
                _device("d1", user_id=1),
                _device("d2", user_id=1),
                _device("d3", user_id=2),
                _device("d4", user_id=3),
                _device("d5", user_id=4),
            ],
            open_rows=[
                _open_row(100, device_id="d1", hours_ago=1),
                _open_row(100, device_id="d2", hours_ago=2),
                _open_row(200, device_id="d3", hours_ago=24 * 3),
                _open_row(300, device_id="d4", hours_ago=24 * 20),
                _open_row(400, device_id="d5", hours_ago=24 * 45),
            ],
        )
        active = snapshot["active"]
        self.assertEqual(active["dau"], 1)
        self.assertEqual(active["dau_devices"], 2)
        self.assertEqual(active["wau"], 2)
        self.assertEqual(active["mau"], 3)
        self.assertEqual(active["mau_devices"], 4)

    def test_revoked_device_is_not_active_anymore(self):
        snapshot = _snapshot(
            device_rows=[
                _device("current", user_id=1),
                _device("revoked", user_id=2, revoked=True),
            ],
            open_rows=[
                _open_row(100, device_id="current", hours_ago=1),
                _open_row(200, device_id="revoked", hours_ago=1),
            ],
        )
        active = snapshot["active"]
        self.assertEqual(active["dau"], 1)
        self.assertEqual(active["dau_devices"], 1)
        self.assertEqual(active["mau"], 1)
        self.assertEqual(active["mau_devices"], 1)


class AndroidFunnelTest(unittest.TestCase):
    def test_funnel_reports_every_stage_even_when_empty(self):
        snapshot = _snapshot(
            totals=_totals(
                android_apk_requested=(9, 12),
                android_apk_sent=(8, 10),
                android_session_linked=(5, 5),
            )
        )
        funnel = snapshot["funnel"]
        self.assertEqual(
            [key for key, _ in ANDROID_FUNNEL_STAGES],
            list(funnel),
        )
        self.assertEqual(funnel["apk_requested"], {"users": 9, "events": 12})
        self.assertEqual(funnel["apk_sent"], {"users": 8, "events": 10})
        self.assertEqual(funnel["session_linked"], {"users": 5, "events": 5})
        self.assertEqual(funnel["first_open"], {"users": 0, "events": 0})

    def test_update_totals_are_reported_separately(self):
        snapshot = _snapshot(totals=_totals(**{ANDROID_UPDATE_EVENT: (3, 4)}))
        self.assertEqual(snapshot["updates"]["installed"], {"users": 3, "events": 4})


class AndroidVersionsTest(unittest.TestCase):
    def test_versions_cover_only_devices_seen_in_the_window(self):
        snapshot = _snapshot(
            device_rows=[
                _device("d1", user_id=1, app_version="1.6.4", last_seen_hours_ago=1),
                _device("d2", user_id=2, app_version="1.6.4", last_seen_hours_ago=24 * 2),
                _device("d3", user_id=3, app_version="1.5.0", last_seen_hours_ago=24 * 5),
                _device("d4", user_id=4, app_version="1.0.0", last_seen_hours_ago=24 * 45),
                _device("d5", user_id=5, app_version="1.6.4", revoked=True),
            ],
            latest_release={"version_name": "1.6.4", "version_code": 19},
        )
        versions = snapshot["versions"]
        self.assertEqual(
            versions["rows"],
            [
                {"version": "1.6.4", "devices": 2, "users": 2},
                {"version": "1.5.0", "devices": 1, "users": 1},
            ],
        )
        self.assertEqual(versions["latest"], "1.6.4")
        self.assertEqual(versions["outdated_devices_30d"], 1)
        self.assertEqual(versions["comparable_devices_30d"], 3)

    def test_unknown_release_leaves_outdated_unreported(self):
        snapshot = _snapshot(
            device_rows=[_device("d1", user_id=1, app_version="1.6.4")],
            latest_release=None,
        )
        self.assertIsNone(snapshot["versions"]["outdated_devices_30d"])
        self.assertIsNone(snapshot["versions"]["latest"])

    def test_unparseable_version_is_left_out_of_both_sides(self):
        snapshot = _snapshot(
            device_rows=[
                _device("d1", user_id=1, app_version="dev-build"),
                _device("d2", user_id=2, app_version="1.5.0"),
            ],
            latest_release={"version_name": "1.6.4", "version_code": 19},
        )
        versions = snapshot["versions"]
        self.assertEqual(versions["comparable_devices_30d"], 1)
        self.assertEqual(versions["outdated_devices_30d"], 1)


class AndroidNotesTest(unittest.TestCase):
    def test_snapshot_states_what_install_and_active_mean(self):
        notes = _snapshot()["notes"]
        self.assertIn("install_definition", notes)
        self.assertIn("active_definition", notes)
        self.assertIn("not_measured", notes)
        self.assertTrue(all(str(value).strip() for value in notes.values()))


class AndroidAnalyticsQueriesTest(unittest.IsolatedAsyncioTestCase):
    """The queries themselves: only Android rows, and the right ones."""

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_snapshot_reads_android_rows_and_ignores_desktop(self):
        async with self.sessions() as session:
            session.add_all(
                [
                    User(id=1, telegram_id=101, status="free", payment_status="none"),
                    User(id=2, telegram_id=202, status="free", payment_status="none"),
                    DesktopDevice(
                        id="android-1",
                        user_id=1,
                        telegram_id=101,
                        installation_key_hash="a" * 64,
                        platform="android",
                        app_version="1.6.4",
                        first_open_at=NOW - timedelta(hours=3),
                        last_seen_at=NOW - timedelta(hours=1),
                        created_at=NOW - timedelta(days=2),
                    ),
                    DesktopDevice(
                        id="android-2",
                        user_id=2,
                        telegram_id=202,
                        installation_key_hash="b" * 64,
                        platform="android",
                        app_version="1.5.0",
                        first_open_at=None,
                        last_seen_at=NOW - timedelta(days=40),
                        created_at=NOW - timedelta(days=45),
                    ),
                    DesktopDevice(
                        id="macos-1",
                        user_id=1,
                        telegram_id=101,
                        installation_key_hash="c" * 64,
                        platform="macos",
                        app_version="1.4.0",
                        first_open_at=NOW - timedelta(hours=2),
                        last_seen_at=NOW - timedelta(hours=2),
                        created_at=NOW - timedelta(days=2),
                    ),
                    CourseMiniAppEvent(
                        id=1,
                        telegram_id=101,
                        event_name="android_apk_sent",
                        source="bot",
                        created_at=NOW - timedelta(days=2),
                    ),
                    CourseMiniAppEvent(
                        id=2,
                        telegram_id=101,
                        event_name="android_app_opened",
                        source="android_app",
                        payload_json=json.dumps({"device_id": "android-1"}),
                        created_at=NOW - timedelta(hours=2),
                    ),
                    CourseMiniAppEvent(
                        id=3,
                        telegram_id=303,
                        event_name="desktop_app_opened",
                        source="desktop_app",
                        payload_json=json.dumps({"device_id": "macos-1"}),
                        created_at=NOW - timedelta(hours=2),
                    ),
                ]
            )
            await session.commit()

            snapshot = await AndroidAnalyticsService(session).snapshot(
                now=NOW,
                latest_release={"version_name": "1.6.4", "version_code": 19},
            )

        registry = snapshot["registry"]
        self.assertEqual(registry["installed_devices"], 2)
        self.assertEqual(registry["installed_users"], 2)
        self.assertEqual(registry["opened_devices"], 1)
        self.assertEqual(registry["never_opened_devices"], 1)
        self.assertEqual(registry["online_devices_1d"], 1)
        self.assertEqual(registry["online_devices_30d"], 1)
        self.assertEqual(snapshot["funnel"]["apk_sent"], {"users": 1, "events": 1})
        self.assertEqual(snapshot["active"]["dau"], 1)
        self.assertEqual(snapshot["active"]["dau_devices"], 1)
        self.assertEqual(
            snapshot["versions"]["rows"],
            [{"version": "1.6.4", "devices": 1, "users": 1}],
        )

    async def test_period_bounds_the_funnel_but_not_the_active_windows(self):
        async with self.sessions() as session:
            session.add_all(
                [
                    User(id=1, telegram_id=101, status="free", payment_status="none"),
                    CourseMiniAppEvent(
                        id=1,
                        telegram_id=101,
                        event_name="android_apk_sent",
                        source="bot",
                        created_at=NOW - timedelta(days=20),
                    ),
                    CourseMiniAppEvent(
                        id=2,
                        telegram_id=101,
                        event_name="android_app_opened",
                        source="android_app",
                        payload_json=json.dumps({"device_id": "android-1"}),
                        created_at=NOW - timedelta(days=3),
                    ),
                ]
            )
            await session.commit()

            weekly = await AndroidAnalyticsService(session).snapshot(
                now=NOW,
                since=NOW - timedelta(days=7),
            )

        self.assertEqual(weekly["funnel"]["apk_sent"]["events"], 0)
        self.assertEqual(weekly["active"]["wau"], 1)
        self.assertEqual(weekly["active"]["dau"], 0)



class AndroidAdminCopyTest(unittest.TestCase):
    def test_admin_android_block_is_simple_by_default(self):
        admin = open("app/static/admin.html", encoding="utf-8").read()
        for text_value in (
            "O'rnatilgan",
            "Bugun ishlatgan",
            "7 kunda ishlatgan",
            "30 kunda ishlatgan",
            "Batafsil statistika",
            "Yangilanish kerak:",
        ):
            with self.subTest(text_value=text_value):
                self.assertIn(text_value, admin)

    def test_update_event_is_not_called_a_device_count(self):
        admin = open("app/static/admin.html", encoding="utf-8").read()
        self.assertIn('"Update o\'rnatilgan",num(updates.installed&&updates.installed.events)+" marta"', admin)


if __name__ == "__main__":
    unittest.main()
