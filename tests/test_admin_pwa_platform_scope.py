"""Task 3.2 step 3: per-platform V10 predicates over the stored-row fixture.

Uses the same disposable PostgreSQL schema as the V10 baseline. This is
projection evidence only; event-to-UI chain tests come in task 3.4.
"""
import json
import unittest

from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from tests.test_admin_pwa_v10_regression import PRIVATE, URL, ago, capture, postgres_fixture

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
            self.assertEqual(set(response["metrics"]), {"attempt_funnel", "attributed_since"})
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


if __name__ == "__main__":
    unittest.main()
