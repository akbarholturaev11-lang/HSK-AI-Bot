"""Task 3.2 step 3: per-platform V10 predicates over the stored-row fixture.

Uses the same disposable PostgreSQL schema as the V10 baseline. This is
projection evidence only; event-to-UI chain tests come in task 3.4.
"""
import json
import unittest
from unittest.mock import patch

from app.admin_api.pwa_analytics_course_platform import course_platform_metrics
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from tests.test_admin_pwa_v10_regression import NOW, PRIVATE, URL, ago, capture, postgres_fixture

PLATFORMS = ("android", "telegram", "iphone_pwa")
PAYMENT_KEYS = ("payments", "revenue_usd", "paying_histories", "canonical_payers", "new_paying_accounts",
                "first_payments", "renewal_payments", "unpriced_payments", "unknown_currency_payments")
OVERALL_ONLY = {"ai_usd": "not_instrumented", "ai_requests": "not_instrumented", "tokens": "not_instrumented",
                "ai_models": "not_instrumented", "arpu_usd": "not_instrumented",
                "active_denominator": "not_instrumented", "net_usd": "not_applicable",
                "manual_profit_usd": "not_applicable", "expense_usd": "not_applicable",
                "tagged_marketing_usd": "not_applicable", "tagged_cac_usd": "not_applicable"}


@unittest.skipUnless(URL, "set ANALYTICS_TEST_DATABASE_URL for the real PostgreSQL platform scope tests")
class FinancePlatformScopeTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.projections = None

    async def asyncSetUp(self):
        if FinancePlatformScopeTests.projections is None:
            async with postgres_fixture(URL) as sessions:
                FinancePlatformScopeTests.projections = await capture(sessions)

    def money(self, platform, period="all_time"):
        return self.projections["money", platform, period]

    def test_each_platform_counts_only_its_server_set_payment_source(self):
        # User 1 pays on PWA (TJS, then Lava), Mini App and Android; user 3 pays
        # once on Android; the bot keeps one canonical and one orphan history.
        expected = {
            "android": dict(payments=2, revenue_usd=20.0, paying_histories=2, canonical_payers=2,
                            new_paying_accounts=1, first_payments=1, renewal_payments=1,
                            unpriced_payments=0, unknown_currency_payments=0),
            "telegram": dict(payments=3, revenue_usd=20.815, paying_histories=3, canonical_payers=2,
                             new_paying_accounts=1, first_payments=2, renewal_payments=1,
                             unpriced_payments=1, unknown_currency_payments=1),
            "iphone_pwa": dict(payments=2, revenue_usd=16.552, paying_histories=1, canonical_payers=1,
                               new_paying_accounts=1, first_payments=1, renewal_payments=1,
                               unpriced_payments=0, unknown_currency_payments=0),
        }
        for platform, values in expected.items():
            with self.subTest(platform=platform):
                response = self.money(platform)
                self.assertIs(response["available"], True)
                self.assertEqual({key: response["metrics"][key] for key in PAYMENT_KEYS}, values)

    def test_platform_payment_counts_partition_the_overall_history(self):
        # The fixture has no desktop payment, so the three views add up exactly.
        overall = self.money("overall")["metrics"]
        for key in ("payments", "first_payments", "renewal_payments", "unpriced_payments"):
            with self.subTest(key=key):
                self.assertEqual(sum(self.money(p)["metrics"][key] for p in PLATFORMS), overall[key])
        self.assertAlmostEqual(sum(self.money(p)["metrics"]["revenue_usd"] for p in PLATFORMS),
                               overall["revenue_usd"], places=4)
        lava = [self.money(p)["metrics"]["lava"] for p in PLATFORMS]
        for key in ("active_subscriptions", "renewals", "refunded", "chargebacks"):
            with self.subTest(lava=key):
                self.assertEqual(sum(row[key] for row in lava), overall["lava"][key])

    def test_renewal_keeps_the_cross_platform_first_payment(self):
        # User 1's first payment was on the PWA, so the Android Lava payment is a renewal.
        weekly = self.money("android", "weekly")["metrics"]
        self.assertEqual((weekly["payments"], weekly["first_payments"], weekly["renewal_payments"],
                          weekly["new_paying_accounts"]), (1, 0, 1, 0))
        self.assertEqual(weekly["channels"], [{"channel": "lava", "payments": 1, "usd": 10.0, "renewal_payments": 1}])

    def test_lava_lifecycle_uses_the_route_owned_invoice_source(self):
        self.assertEqual(self.money("android")["metrics"]["lava"],
                         {"active_subscriptions": 1, "renewals": 0, "cancelled": 0, "refunded": 0, "chargebacks": 0})
        self.assertEqual(self.money("telegram")["metrics"]["lava"],
                         {"active_subscriptions": 0, "renewals": 1, "cancelled": 0, "refunded": 0, "chargebacks": 0})
        self.assertEqual(self.money("iphone_pwa")["metrics"]["lava"],
                         {"active_subscriptions": 1, "renewals": 0, "cancelled": 0, "refunded": 1, "chargebacks": 0})

    def test_company_wide_and_unattributed_measures_are_never_platform_values(self):
        for platform in PLATFORMS:
            for period in ("weekly", "monthly", "all_time"):
                with self.subTest(platform=platform, period=period):
                    response = self.money(platform, period)
                    self.assertFalse(set(OVERALL_ONLY) & set(response["metrics"]))
                    states = response["metric_states"]
                    for key, reason in OVERALL_ONLY.items():
                        state = "not_applicable" if reason == "not_applicable" else "unavailable"
                        self.assertEqual(states[key], {"state": state, "reason": reason})
                    self.assertEqual(states["payments"], {"state": "available", "reason": None})
                    self.assertNotIn(PRIVATE, json.dumps(response))

    def test_desktop_filters_stay_unavailable(self):
        for platform in ("macos", "windows"):
            response = self.money(platform)
            self.assertEqual((response["available"], response["metrics"], response["reason"]),
                             (False, None, "attribution_not_audited"))


@unittest.skipUnless(URL, "set ANALYTICS_TEST_DATABASE_URL for the real PostgreSQL platform scope tests")
class FunnelPlatformScopeTests(unittest.IsolatedAsyncioTestCase):
    """The fixture's Telegram and Android Lava openings predate the marker."""

    async def asyncSetUp(self):
        def opened(user_id, source, attempt, hours, **payload):
            return ConversionFunnelEvent(event_name="checkout_opened", user_id=user_id, source=source,
                payload_json=json.dumps({"attempt_id": attempt, **payload}), created_at=ago(hours=hours))

        async with postgres_fixture(URL) as sessions:
            async with sessions() as db:
                db.add_all([
                    opened(2, "subscription_miniapp", "tg-new", 7, mode="", transport="telegram"),
                    opened(2, "subscription_miniapp", "tg-new", 6, stage="payment_instructions_viewed",
                           transport="telegram"),
                    # Caller-controlled Android lookalike sent through the Telegram route.
                    opened(2, "android_subscription", "android-spoof", 5, mode="", transport="telegram"),
                    opened(3, "android_subscription", "android-manual", 9, mode="subscription",
                           transport="android"),
                ])
                await db.commit()
            self.projections = await capture(sessions)

    def funnel(self, platform, period="weekly"):
        return self.projections["funnel", platform, period]

    def test_openings_count_only_under_their_route_marker(self):
        attempts = {platform: self.funnel(platform)["metrics"]["attempt_funnel"]["attempts"]
                    for platform in PLATFORMS}
        # Android excludes the unmarked fixture Lava opening and the Telegram lookalike.
        self.assertEqual(attempts, {"android": 1, "telegram": 2, "iphone_pwa": 1})
        steps = {row["key"]: row["accounts"] for row in
                 self.funnel("telegram")["metrics"]["attempt_funnel"]["steps"]}
        self.assertEqual((steps["checkout_opened"], steps["payment_instructions_viewed"]), (1, 1))

    def test_overall_keeps_every_opening_including_unmarked_rows(self):
        overall = self.funnel("overall")["metrics"]
        self.assertEqual(overall["attempt_funnel"]["attempts"], 6)
        self.assertNotIn("attributed_since", overall)

    def test_attributed_since_is_the_first_marked_opening(self):
        self.assertEqual(self.funnel("android")["metrics"]["attributed_since"],
                         {"attempt_funnel": ago(hours=9).isoformat()})
        self.assertEqual(self.funnel("telegram")["metrics"]["attributed_since"],
                         {"attempt_funnel": ago(hours=7).isoformat()})
        self.assertEqual(self.funnel("iphone_pwa")["metrics"]["attributed_since"],
                         {"attempt_funnel": ago(hours=4).isoformat()})

    def test_activity_families_are_not_platform_values(self):
        for platform in PLATFORMS:
            response = self.funnel(platform, "all_time")
            # The PWA view also carries the PWA-only Pro funnel (F8, task 4.1).
            extra = {"pwa_pro_attempt_funnel"} if platform == "iphone_pwa" else set()
            self.assertEqual(set(response["metrics"]), {"attempt_funnel", "attributed_since", *extra})
            states = response["metric_states"]
            self.assertEqual(states["attempt_funnel"], {"state": "available", "reason": None})
            self.assertEqual(states["ai_usage"], {"state": "unavailable", "reason": "not_instrumented"})
            self.assertEqual(states["registration_conversion"]["state"], "unavailable")


@unittest.skipUnless(URL, "set ANALYTICS_TEST_DATABASE_URL for the real PostgreSQL platform scope tests")
class PwaPlatformCardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with postgres_fixture(URL) as sessions:
            self.projections = await capture(sessions)

    def test_pwa_card_counts_only_route_owned_map_opens(self):
        # User 1 opened the PWA map two days ago. User 2's Telegram row carries
        # the PWA source text but the Telegram dedupe prefix, so it is excluded.
        for section in ("platform", "home", "overview"):
            with self.subTest(section=section):
                response = self.projections[section, "iphone_pwa", "weekly"]
                self.assertIs(response["available"], True)
                metrics = response["metrics"]
                self.assertEqual(metrics["platforms"], [
                    {"platform": "iphone_pwa", "active_dau": 0, "active_wau": 1, "active_mau": 1}])
                self.assertIs(metrics["iphone_pwa_available"], True)
                self.assertEqual(metrics["versions"], [])
                states = response["metric_states"]
                self.assertEqual(states["platforms"], {"state": "available", "reason": None})
                self.assertEqual(states["versions"], {"state": "not_applicable", "reason": "not_applicable"})

    def test_overall_card_list_is_unchanged(self):
        overall = self.projections["platform", "overall", "weekly"]["metrics"]
        self.assertNotIn("iphone_pwa", [card["platform"] for card in overall["platforms"]])
        self.assertIs(overall["iphone_pwa_available"], False)


@unittest.skipUnless(URL, "set ANALYTICS_TEST_DATABASE_URL for the real PostgreSQL platform scope tests")
class CoursePlatformScopeTests(unittest.IsolatedAsyncioTestCase):
    """The baseline fixture has only pre-key course rows; these add tagged ones."""

    async def asyncSetUp(self):
        def event(name, user_id, hours, payload, **fields):
            # The analytics writer's compact JSON, with the route key last.
            return CourseMiniAppEvent(event_name=name, user_id=user_id, source="course_v3",
                payload_json=json.dumps(payload, separators=(",", ":")), created_at=ago(hours=hours), **fields)

        async with postgres_fixture(URL) as sessions:
            async with sessions() as db:
                db.add_all([
                    # A caller sent a PWA client key before tagging went live.
                    event("lesson_started", 2, 60, {"lesson_order": 2, "client": "iphone_pwa"}),
                    # First server-built tagged rows: the per-client boundaries.
                    event("lesson_completed", 1, 10, {"lesson_order": 1, "client": "telegram"},
                          level="hsk1", lesson_order=1),
                    event("test_completed", 1, 8, {"score": 1, "client": "iphone_pwa"}),
                    event("training_completed", 3, 6, {"mode": "training", "client": "android"}),
                    # After the boundary: route-tagged starts, one with a nested lookalike.
                    event("lesson_started", 2, 9, {"lesson_order": 2, "client": "telegram"}),
                    event("test_started", 2, 5, {"meta": {"client": "iphone_pwa"}, "client": "telegram"}),
                    event("mistake_review_started", 1, 7, {"count": 3, "client": "iphone_pwa"}),
                    # A completion too large to tag stays Overall-only.
                    event("mistake_review_completed", 3, 4, {"count": 2}),
                    # Starter 0: a tagged Telegram start and its completion, plus
                    # a pre-boundary PWA lookalike start.
                    event("foundation_started", 2, 9, {"foundation_version": "v9", "entry_level": "hsk1",
                                                        "client": "telegram"}),
                    event("foundation_completed", 2, 8, {"foundation_version": "v9"}),
                    event("foundation_started", 1, 60, {"foundation_version": "v9", "client": "iphone_pwa"}),
                ])
                await db.commit()
            self.projections = await capture(sessions)

    def course(self, platform, period="weekly"):
        return self.projections["course", platform, period]["metrics"]

    def features(self, platform):
        rows = self.course(platform)["features"]
        return {row["key"]: (row["paid"], row["free"]) for row in rows}

    def test_features_count_only_the_final_route_key_after_the_boundary(self):
        # User 1 is paid; users 2 and 3 are free.
        self.assertEqual(self.features("telegram"),
                         {"lessons": (0, 1), "tests": (0, 1), "practice": (0, 0), "mistakes": (0, 0)})
        # Neither the pre-boundary lesson start nor the nested key counts as PWA.
        self.assertEqual(self.features("iphone_pwa"),
                         {"lessons": (0, 0), "tests": (1, 0), "practice": (0, 0), "mistakes": (1, 0)})
        # A7: no Android lesson-start writer, so no lessons entry.
        self.assertEqual(self.features("android"), {"tests": (0, 0), "practice": (0, 1), "mistakes": (0, 0)})

    def test_attributed_since_is_the_first_server_built_tagged_row(self):
        for platform, hours in (("telegram", 10), ("iphone_pwa", 8)):
            boundary = ago(hours=hours).isoformat()
            self.assertEqual(self.course(platform)["attributed_since"],
                             {"features": boundary, "foundation": boundary, "completed_user_lessons": boundary})
        self.assertEqual(self.course("android")["attributed_since"], {"features": ago(hours=6).isoformat()})

    def test_completed_lessons_per_platform(self):
        self.assertEqual(self.course("telegram")["completed_user_lessons"], 1)
        # A real zero once PWA attribution exists, not a missing value.
        self.assertEqual(self.course("iphone_pwa")["completed_user_lessons"], 0)
        # A8: the Android-only source counts all history, independent of the key.
        self.assertEqual((self.course("android")["completed_user_lessons"],
                          self.course("android", "all_time")["completed_user_lessons"]), (1, 2))

    def test_foundation_cohort_follows_the_attributed_start(self):
        telegram = self.course("telegram")["foundation"]
        self.assertEqual((telegram["started_users"], telegram["completed_users"]), (1, 1))
        pwa = self.course("iphone_pwa")["foundation"]
        self.assertEqual((pwa["started_users"], pwa["completed_users"]), (0, 0))
        # A10: Android writes no start, so no foundation value or cohort.
        self.assertNotIn("foundation", self.course("android"))
        self.assertEqual(self.projections["course", "android", "weekly"]["metric_states"]["foundation"],
                         {"state": "unavailable", "reason": "not_instrumented"})

    def test_unattributed_course_families_are_not_platform_values(self):
        for platform in PLATFORMS:
            response = self.projections["course", platform, "all_time"]
            keys = {"features", "completed_user_lessons", "attributed_since", "detail_since"}
            if platform != "android":
                keys |= {"foundation", "detail_limited"}
            self.assertEqual(set(response["metrics"]), keys)
            states = response["metric_states"]
            self.assertEqual(states["features"], {"state": "available", "reason": None})
            for key in ("voice_minutes", "chat", "ai_usage", "activation", "sessions"):
                self.assertEqual(states[key], {"state": "unavailable", "reason": "not_instrumented"})
            self.assertNotIn(PRIVATE, json.dumps(response))


@unittest.skipUnless(URL, "set ANALYTICS_TEST_DATABASE_URL for the real PostgreSQL platform scope tests")
class CourseFoundationDetailLimitTests(unittest.IsolatedAsyncioTestCase):
    """Audit #13: other learners' Starter 0 rows never fill one client's detail limit."""

    async def test_rows_of_accounts_without_this_clients_start_are_not_read(self):
        def event(name, user_id, hours, payload):
            return CourseMiniAppEvent(event_name=name, user_id=user_id, source="course_v3",
                payload_json=json.dumps(payload, separators=(",", ":")), created_at=ago(hours=hours))

        async with postgres_fixture(URL) as sessions:
            async with sessions() as db:
                db.add_all([
                    event("lesson_completed", 1, 10, {"lesson_order": 1, "client": "telegram"}),
                    event("foundation_started", 2, 9, {"foundation_version": "v9", "client": "telegram"}),
                    event("foundation_completed", 2, 8, {"foundation_version": "v9"}),
                    # A busy learner who started elsewhere (PWA) and an untagged one.
                    event("foundation_started", 3, 9, {"foundation_version": "v9", "client": "iphone_pwa"}),
                    *[event("foundation_completed", user, 7, {"foundation_version": "v9"})
                      for user in (1, 3) for _ in range(4)],
                ])
                await db.commit()
            async with sessions() as db:
                with patch("app.admin_api.pwa_analytics_learning.DETAIL_LIMIT", 3):
                    telegram = await course_platform_metrics(db, platform="telegram", since=ago(days=7), now=NOW)
                with patch("app.admin_api.pwa_analytics_learning.DETAIL_LIMIT", 1):
                    own_rows_over = await course_platform_metrics(db, platform="telegram", since=ago(days=7), now=NOW)
        # Before the fix all 11 window rows were read, so Telegram had no value.
        self.assertIs(telegram["detail_limited"], False)
        self.assertEqual((telegram["foundation"]["started_users"], telegram["foundation"]["completed_users"]), (1, 1))
        # Its own two rows above the limit still refuse a sample.
        self.assertIs(own_rows_over["detail_limited"], True)
        self.assertIsNone(own_rows_over["foundation"])


@unittest.skipUnless(URL, "set ANALYTICS_TEST_DATABASE_URL for the real PostgreSQL platform scope tests")
class CourseWithoutAttributionTests(unittest.IsolatedAsyncioTestCase):
    async def test_pre_key_history_is_no_data_not_zero(self):
        async with postgres_fixture(URL) as sessions:
            projections = await capture(sessions)
        for platform in ("telegram", "iphone_pwa"):
            response = projections["course", platform, "weekly"]
            self.assertIsNone(response["metrics"]["features"])
            self.assertIsNone(response["metrics"]["completed_user_lessons"])
            for key in ("features", "foundation"):
                self.assertEqual(response["metric_states"][key], {"state": "unavailable", "reason": "no_data"})


@unittest.skipUnless(URL, "set ANALYTICS_TEST_DATABASE_URL for the real PostgreSQL platform scope tests")
class CrossPlatformDedupTests(unittest.IsolatedAsyncioTestCase):
    """User 1 opens Android on two devices, the Mini App and the PWA, and pays on all three."""

    async def asyncSetUp(self):
        async with postgres_fixture(URL) as sessions:
            self.projections = await capture(sessions)

    def card(self, platform, section="platform"):
        cards = self.projections[section, platform, "weekly"]["metrics"]["platforms"]
        return next(card for card in cards if card["platform"] == platform)

    def test_one_account_on_three_platforms_counts_once_per_view(self):
        self.assertEqual(self.card("android")["active_dau"], 1)
        self.assertEqual(self.card("telegram")["foreground_accounts_30d"], 1)
        self.assertEqual(self.card("iphone_pwa")["active_wau"], 1)
        money = {p: self.projections["money", p, "all_time"]["metrics"]["canonical_payers"]
                 for p in ("overall", *PLATFORMS)}
        # User 1 pays on every client but is one canonical payer overall.
        self.assertEqual(money, {"overall": 3, "android": 2, "telegram": 2, "iphone_pwa": 1})
        for section in ("money", "course", "funnel", "platform"):
            for platform in PLATFORMS:
                self.assertIs(self.projections[section, platform, "weekly"]["platform_counts_overlap"], True)

    def test_two_android_devices_are_one_account_and_two_devices(self):
        card = self.card("android")
        # android-a and android-b belong to user 1; android-old to user 3.
        self.assertEqual((card["devices"], card["accounts"]), (3, 2))
        self.assertEqual(card["active_dau"], 1)


if __name__ == "__main__":
    unittest.main()
