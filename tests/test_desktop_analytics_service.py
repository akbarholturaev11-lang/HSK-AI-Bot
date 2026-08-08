import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.db.models.course_miniapp_event import (
    CLIENT_COURSE_MINIAPP_EVENT_NAMES,
    COURSE_MINIAPP_EVENT_NAMES,
)
from app.services.desktop_analytics_service import DesktopAnalyticsService


NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def _totals(**values):
    result = {}
    for event_name, counts in values.items():
        result[event_name] = {
            "events": counts[0],
            "users": counts[1],
        }
    return result


def _row(
    event_name,
    telegram_id,
    *,
    age_hours=0,
    platform=None,
    app_version=None,
    source="desktop",
    session_id=None,
    device_id=None,
    entry_source=None,
    row_id=0,
):
    payload = {}
    if platform is not None:
        payload["platform"] = platform
    if app_version is not None:
        payload["app_version"] = app_version
    if entry_source is not None:
        payload["entry_source"] = entry_source
    if device_id is not None:
        payload["device_id"] = device_id
    return SimpleNamespace(
        id=row_id,
        event_name=event_name,
        telegram_id=telegram_id,
        source=source,
        session_id=session_id,
        payload_json=json.dumps(payload),
        created_at=NOW - timedelta(hours=age_hours),
    )


class DesktopAnalyticsServiceTests(unittest.TestCase):
    def test_only_soft_acquisition_events_are_allowed_from_untrusted_miniapp_client(self):
        safe_client_events = {
            "desktop_promo_seen",
            "desktop_promo_dismissed",
            "desktop_download_entry_seen",
            "desktop_download_chooser_opened",
            "desktop_download_destination_selected",
        }
        self.assertTrue(
            safe_client_events.issubset(set(CLIENT_COURSE_MINIAPP_EVENT_NAMES))
        )

        server_only = {
            "desktop_download_requested",
            "desktop_download_started",
            "desktop_download_message_sent",
            "desktop_download_link_clicked",
            "desktop_session_linked",
            "desktop_first_open",
            "desktop_active_day",
        }
        self.assertTrue(server_only.issubset(set(COURSE_MINIAPP_EVENT_NAMES)))
        self.assertTrue(server_only.isdisjoint(set(CLIENT_COURSE_MINIAPP_EVENT_NAMES)))

    def test_funnel_counts_only_source_and_time_ordered_user_cohorts(self):
        rows = []

        def add_journey(user_id, depth, *, token, source="profile"):
            events = [
                ("desktop_download_requested", 10, token, f"desktop_{source}"),
                ("desktop_download_started", 9, token, f"desktop_{source}"),
                ("desktop_download_link_clicked", 8, token, f"desktop_{source}"),
                ("desktop_session_linked", 7, f"device-{user_id}", "desktop_auth"),
                ("desktop_first_open", 6, f"device-{user_id}", "desktop"),
            ]
            for index, (event_name, age, session_id, event_source) in enumerate(
                events[:depth],
                start=1,
            ):
                rows.append(
                    _row(
                        event_name,
                        user_id,
                        age_hours=age,
                        platform="macos",
                        source=event_source,
                        session_id=session_id,
                        entry_source=source if index <= 3 else None,
                        row_id=user_id * 10 + index,
                    )
                )

        add_journey(1, 5, token="request-1")
        add_journey(2, 4, token="request-2")
        add_journey(3, 3, token="request-3")
        add_journey(4, 2, token="request-4")
        add_journey(5, 1, token="request-5")

        # Independent downstream events must not inflate the cohort.
        rows.extend(
            [
                _row(
                    "desktop_download_started",
                    6,
                    age_hours=9,
                    source="desktop_profile",
                    session_id="orphan",
                    entry_source="profile",
                    row_id=61,
                ),
                # Download-start happened before this user's request.
                _row(
                    "desktop_download_started",
                    7,
                    age_hours=11,
                    source="desktop_profile",
                    session_id="request-7",
                    entry_source="profile",
                    row_id=71,
                ),
                _row(
                    "desktop_download_requested",
                    7,
                    age_hours=10,
                    source="desktop_profile",
                    session_id="request-7",
                    entry_source="profile",
                    row_id=72,
                ),
                # Same token but a different source is not the same journey.
                _row(
                    "desktop_download_requested",
                    8,
                    age_hours=10,
                    source="desktop_profile",
                    session_id="request-8",
                    entry_source="profile",
                    row_id=81,
                ),
                _row(
                    "desktop_download_started",
                    8,
                    age_hours=9,
                    source="desktop_home_prompt",
                    session_id="request-8",
                    entry_source="home_prompt",
                    row_id=82,
                ),
                _row(
                    "desktop_first_open",
                    9,
                    age_hours=1,
                    platform="windows",
                    session_id="orphan-device",
                    row_id=91,
                ),
            ]
        )

        snapshot = DesktopAnalyticsService.build_snapshot(
            totals=_totals(
                desktop_download_requested=(8, 7),
                desktop_download_started=(20, 20),
                desktop_download_link_clicked=(15, 15),
                desktop_session_linked=(10, 10),
                desktop_first_open=(12, 12),
            ),
            detail_rows=[],
            cohort_rows=rows,
            now=NOW,
        )

        self.assertEqual(snapshot["funnel"]["download_requested"]["users"], 7)
        self.assertEqual(snapshot["funnel"]["download_started"]["users"], 4)
        self.assertEqual(snapshot["funnel"]["link_clicked"]["users"], 3)
        self.assertEqual(snapshot["funnel"]["session_linked"]["users"], 2)
        self.assertEqual(snapshot["funnel"]["verified_first_open"]["users"], 1)
        self.assertEqual(snapshot["funnel"]["verified_first_open"]["raw_users"], 12)
        self.assertEqual(snapshot["rates"]["download_started_per_request"], 57.1)
        self.assertEqual(snapshot["rates"]["link_click_per_download_started"], 75.0)
        self.assertEqual(snapshot["rates"]["session_linked_per_link_click"], 66.7)
        self.assertEqual(snapshot["rates"]["verified_first_open_per_session_linked"], 50.0)
        self.assertTrue(all(rate <= 100 for rate in snapshot["rates"].values()))
        self.assertIn("click install hisoblanmaydi", snapshot["notes"]["install_definition"].lower())

    def test_promo_conversion_requires_same_eligible_source_after_seen(self):
        rows = [
            # Valid home prompt conversion.
            _row("desktop_promo_seen", 11, age_hours=10, source="home_prompt", row_id=1),
            _row(
                "desktop_download_requested",
                11,
                age_hours=9,
                source="desktop_home_prompt",
                session_id="request-11",
                entry_source="home_prompt",
                row_id=2,
            ),
            # Request before seen must not convert.
            _row(
                "desktop_download_requested",
                12,
                age_hours=10,
                source="desktop_home_prompt",
                session_id="request-12",
                entry_source="home_prompt",
                row_id=3,
            ),
            _row("desktop_promo_seen", 12, age_hours=9, source="home_prompt", row_id=4),
            # Profile request is not a promo conversion.
            _row("desktop_promo_seen", 13, age_hours=10, source="home_prompt", row_id=5),
            _row(
                "desktop_download_requested",
                13,
                age_hours=9,
                source="desktop_profile",
                session_id="request-13",
                entry_source="profile",
                row_id=6,
            ),
            # Multiple requests after one ad promo view still count one user.
            _row("desktop_promo_seen", 14, age_hours=10, source="ad_promo", row_id=7),
            _row(
                "desktop_download_requested",
                14,
                age_hours=9,
                source="desktop_ad_promo",
                session_id="request-14a",
                entry_source="ad_promo",
                row_id=8,
            ),
            _row(
                "desktop_download_requested",
                14,
                age_hours=8,
                source="desktop_ad_promo",
                session_id="request-14b",
                entry_source="ad_promo",
                row_id=9,
            ),
            # A different promo source cannot claim this request.
            _row("desktop_promo_seen", 15, age_hours=10, source="lesson_end_promo", row_id=10),
            _row(
                "desktop_download_requested",
                15,
                age_hours=9,
                source="desktop_ad_promo",
                session_id="request-15",
                entry_source="ad_promo",
                row_id=11,
            ),
            # Profile is excluded even if somebody emits a promo_seen event for it.
            _row("desktop_promo_seen", 16, age_hours=10, source="profile", row_id=12),
            _row(
                "desktop_download_requested",
                16,
                age_hours=9,
                source="desktop_profile",
                session_id="request-16",
                entry_source="profile",
                row_id=13,
            ),
            _row("desktop_promo_seen", 17, age_hours=10, source="home_prompt", row_id=14),
            _row("desktop_promo_dismissed", 17, age_hours=9, source="home_prompt", row_id=15),
        ]

        snapshot = DesktopAnalyticsService.build_snapshot(
            totals=_totals(
                desktop_promo_seen=(100, 99),
                desktop_promo_dismissed=(50, 50),
                desktop_download_requested=(500, 200),
            ),
            detail_rows=[],
            cohort_rows=rows,
            now=NOW,
        )

        promotion = snapshot["promotion"]
        self.assertEqual(promotion["seen"]["users"], 6)
        self.assertEqual(promotion["requested_after_seen"]["users"], 2)
        self.assertEqual(promotion["requested_after_seen"]["events"], 3)
        self.assertEqual(promotion["request_per_seen"], 33.3)
        self.assertEqual(promotion["dismissed"]["users"], 1)
        self.assertEqual(promotion["sources"]["home_prompt"]["seen"]["users"], 4)
        self.assertEqual(
            promotion["sources"]["home_prompt"]["requested_after_seen"]["users"],
            1,
        )
        self.assertEqual(promotion["sources"]["ad_promo"]["request_per_seen"], 100.0)
        self.assertEqual(promotion["by_source"], promotion["sources"])
        self.assertNotIn("profile", promotion["sources"])
        self.assertLessEqual(promotion["request_per_seen"], 100.0)

    def test_entry_source_funnel_includes_profile_without_becoming_promo_seen(self):
        rows = [
            _row(
                "desktop_download_entry_seen",
                21,
                age_hours=10,
                source="profile",
                row_id=1,
            ),
            _row(
                "desktop_download_chooser_opened",
                21,
                age_hours=9,
                source="profile",
                platform="macos",
                row_id=2,
            ),
            _row(
                "desktop_download_destination_selected",
                21,
                age_hours=8,
                source="profile",
                platform="macos",
                row_id=3,
            ),
            _row(
                "desktop_download_requested",
                21,
                age_hours=7,
                source="desktop_profile",
                entry_source="profile",
                platform="macos",
                row_id=4,
            ),
            _row(
                "desktop_download_entry_seen",
                22,
                age_hours=10,
                source="home_prompt",
                row_id=5,
            ),
            _row(
                "desktop_download_chooser_opened",
                22,
                age_hours=9,
                source="home_prompt",
                platform="windows",
                row_id=6,
            ),
            # A request before an impression cannot be attributed.
            _row(
                "desktop_download_requested",
                23,
                age_hours=10,
                source="desktop_profile",
                entry_source="profile",
                row_id=7,
            ),
            _row(
                "desktop_download_entry_seen",
                23,
                age_hours=9,
                source="profile",
                row_id=8,
            ),
        ]

        snapshot = DesktopAnalyticsService.build_snapshot(
            totals=_totals(
                desktop_download_entry_seen=(3, 3),
                desktop_download_chooser_opened=(2, 2),
                desktop_download_destination_selected=(1, 1),
                desktop_download_requested=(2, 2),
            ),
            detail_rows=[],
            cohort_rows=rows,
            now=NOW,
        )

        promotion = snapshot["promotion"]
        profile = promotion["entry_funnel"]["by_source"]["profile"]
        home = promotion["entry_funnel"]["by_source"]["home_prompt"]
        self.assertEqual(profile["seen"]["users"], 2)
        self.assertEqual(profile["chooser_opened"]["users"], 1)
        self.assertEqual(profile["destination_selected"]["users"], 1)
        self.assertEqual(profile["requested_after_seen"]["users"], 1)
        self.assertEqual(profile["request_per_seen"], 50.0)
        self.assertEqual(home["chooser_per_seen"], 100.0)
        self.assertNotIn("profile", promotion["by_source"])

    def test_direct_download_click_may_arrive_before_started_callback(self):
        rows = [
            _row(
                "desktop_download_requested",
                10,
                age_hours=10,
                platform="macos",
                source="desktop_profile",
                session_id="request-10",
                entry_source="profile",
                row_id=1,
            ),
            _row(
                "desktop_download_link_clicked",
                10,
                age_hours=9,
                platform="macos",
                source="desktop_profile",
                session_id="request-10",
                entry_source="profile",
                row_id=2,
            ),
            _row(
                "desktop_download_started",
                10,
                age_hours=8,
                platform="macos",
                source="desktop_profile",
                session_id="request-10",
                entry_source="profile",
                row_id=3,
            ),
            _row(
                "desktop_session_linked",
                10,
                age_hours=7,
                platform="macos",
                source="desktop_auth",
                session_id="device-10",
                row_id=4,
            ),
            _row(
                "desktop_first_open",
                10,
                age_hours=6,
                platform="macos",
                source="desktop_app",
                session_id="device-10",
                row_id=5,
            ),
        ]
        snapshot = DesktopAnalyticsService.build_snapshot(
            totals=_totals(
                desktop_download_requested=(1, 1),
                desktop_download_started=(1, 1),
                desktop_download_link_clicked=(1, 1),
                desktop_session_linked=(1, 1),
                desktop_first_open=(1, 1),
            ),
            detail_rows=[],
            cohort_rows=rows,
            now=NOW,
        )
        self.assertEqual(snapshot["funnel"]["verified_first_open"]["users"], 1)

    def test_active_platform_and_versions_use_server_runtime_proof(self):
        rows = [
            _row(
                "desktop_first_open",
                101,
                age_hours=2,
                platform="macos",
                app_version="1.1.0",
                session_id="opaque-mac-session",
            ),
            _row(
                "desktop_app_opened",
                102,
                age_hours=48,
                platform="windows",
                app_version="1.0.0",
                session_id="opaque-win-session",
            ),
            _row(
                "desktop_active_day",
                103,
                age_hours=240,
                platform="windows",
                app_version="1.2.0",
                session_id="opaque-win-newer",
            ),
            # A request proves acquisition intent, not runtime activity.
            _row(
                "desktop_download_requested",
                104,
                age_hours=1,
                platform="windows",
                source="profile",
            ),
        ]

        snapshot = DesktopAnalyticsService.build_snapshot(
            totals={},
            detail_rows=rows,
            now=NOW,
            latest_versions={"macos": "1.1.0", "windows": "1.1.0"},
        )

        self.assertEqual(snapshot["active"], {
            "dau": 1,
            "wau": 2,
            "mau": 3,
            "proof_events": [
                "desktop_first_open",
                "desktop_app_opened",
                "desktop_active_day",
            ],
        })
        self.assertEqual(snapshot["platforms"]["active_users_30d"]["macos"], 1)
        self.assertEqual(snapshot["platforms"]["active_users_30d"]["windows"], 2)
        self.assertEqual(snapshot["platforms"]["download_requests_30d"]["windows"], 1)
        self.assertEqual(snapshot["versions"]["known_devices_30d"], 3)
        self.assertEqual(snapshot["versions"]["comparable_devices_30d"], 3)
        self.assertEqual(snapshot["versions"]["outdated_devices_30d"], 1)
        self.assertEqual(snapshot["versions"]["outdated_rate_30d"], 33.3)

    def test_source_keeps_attribution_while_payload_carries_platform_and_version(self):
        row = _row(
            "desktop_first_open",
            150,
            platform="macos",
            app_version="2.0.0",
            source="desktop_auth",
            session_id="opaque-session",
        )

        snapshot = DesktopAnalyticsService.build_snapshot(
            totals={},
            detail_rows=[row],
            now=NOW,
            latest_versions={"macos": "2.0.0"},
        )

        self.assertEqual(row.source, "desktop_auth")
        self.assertEqual(snapshot["platforms"]["verified_first_open_30d"]["macos"], 1)
        self.assertEqual(
            snapshot["versions"]["by_platform_30d"]["macos"],
            [{"version": "2.0.0", "devices": 1, "users": 1}],
        )

    def test_latest_event_wins_for_same_opaque_session(self):
        rows = [
            _row(
                "desktop_active_day",
                201,
                age_hours=72,
                platform="windows",
                app_version="1.0.0",
                session_id="opaque-session",
            ),
            _row(
                "desktop_active_day",
                201,
                age_hours=1,
                platform="windows",
                app_version="1.1.0",
                session_id="opaque-session",
            ),
        ]

        snapshot = DesktopAnalyticsService.build_snapshot(
            totals={},
            detail_rows=rows,
            now=NOW,
            latest_versions={"windows": "1.1.0"},
        )

        self.assertEqual(snapshot["versions"]["known_devices_30d"], 1)
        self.assertEqual(snapshot["versions"]["outdated_devices_30d"], 0)
        self.assertEqual(
            snapshot["versions"]["by_platform_30d"]["windows"],
            [{"version": "1.1.0", "devices": 1, "users": 1}],
        )

    def test_relinked_sessions_for_same_device_are_not_double_counted(self):
        rows = [
            _row(
                "desktop_app_opened",
                201,
                age_hours=48,
                platform="windows",
                app_version="1.0.0",
                session_id="session-before-relink",
                device_id="device-stable-201",
            ),
            _row(
                "desktop_app_opened",
                201,
                age_hours=1,
                platform="windows",
                app_version="1.1.0",
                session_id="session-after-relink",
                device_id="device-stable-201",
            ),
        ]
        snapshot = DesktopAnalyticsService.build_snapshot(
            totals={},
            detail_rows=rows,
            now=NOW,
            latest_versions={"windows": "1.1.0"},
        )
        self.assertEqual(snapshot["versions"]["known_devices_30d"], 1)
        self.assertEqual(
            snapshot["versions"]["by_platform_30d"]["windows"],
            [{"version": "1.1.0", "devices": 1, "users": 1}],
        )

    def test_ai_pack_and_sync_conversion_are_real_counts(self):
        snapshot = DesktopAnalyticsService.build_snapshot(
            totals=_totals(
                desktop_ai_pack_started=(8, 6),
                desktop_ai_pack_completed=(5, 3),
                desktop_offline_ai_used=(30, 4),
                desktop_progress_sync_succeeded=(90, 8),
                desktop_progress_sync_failed=(10, 3),
                desktop_update_installed=(7, 5),
            ),
            detail_rows=[],
            now=NOW,
        )

        self.assertEqual(snapshot["ai_pack"]["completion_rate"], 50.0)
        self.assertEqual(snapshot["ai_pack"]["offline_ai_used"]["users"], 4)
        self.assertEqual(snapshot["sync"]["success_rate"], 90.0)
        self.assertEqual(
            snapshot["updates"]["installed"],
            {"events": 7, "users": 5},
        )

    def test_outdated_is_unknown_without_release_version(self):
        snapshot = DesktopAnalyticsService.build_snapshot(
            totals={},
            detail_rows=[
                _row(
                    "desktop_active_day",
                    301,
                    platform="macos",
                    app_version="0.9.0",
                    session_id="opaque-session",
                )
            ],
            now=NOW,
        )

        self.assertIsNone(snapshot["versions"]["outdated_devices_30d"])
        self.assertIsNone(snapshot["versions"]["outdated_rate_30d"])

    def test_platform_fallback_accepts_early_server_source_but_payload_is_standard(self):
        legacy = _row(
            "desktop_first_open",
            401,
            source="desktop_macos",
            session_id="opaque-session",
        )
        snapshot = DesktopAnalyticsService.build_snapshot(
            totals={},
            detail_rows=[legacy],
            now=NOW,
        )

        self.assertEqual(snapshot["platforms"]["verified_first_open_30d"]["macos"], 1)


if __name__ == "__main__":
    unittest.main()
