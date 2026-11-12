"""Task 3.2 step 3: per-platform V10 predicates over the stored-row fixture.

Uses the same disposable PostgreSQL schema as the V10 baseline. This is
projection evidence only; event-to-UI chain tests come in task 3.4.
"""
import json
import unittest

from tests.test_admin_pwa_v10_regression import PRIVATE, URL, capture, postgres_fixture

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


if __name__ == "__main__":
    unittest.main()
