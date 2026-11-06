"""lava.top account capability preflight."""
import unittest

import httpx

from app.services.lava.client import LavaClient
from app.services.lava.config import config_from_dict
from app.services.lava.preflight import run_preflight
from tests.lava_fakes import API_KEY, OFFER_ID, FakeLava, lava_settings


def _config(currency="USD", plans=("1_month", "12_months")):
    return config_from_dict({"checkout_mode": "both", "currency": currency,
                             "plans": {plan: {"enabled": True, "offer_id": OFFER_ID} for plan in plans}})


def _codes(report, ok):
    return {check.code for check in report.checks if check.ok is ok}


class LavaPreflightTests(unittest.IsolatedAsyncioTestCase):
    async def test_ready_account_passes_and_test_invoice_proves_checkout(self):
        fake = FakeLava()
        report = await run_preflight(fake.client(), _config(), settings_obj=lava_settings(),
                                     test_invoice_email="owner@example.com")
        self.assertTrue(report.ok, report.as_dict())
        self.assertIn("test_invoice", _codes(report, True))
        self.assertEqual(report.offers[0]["offer_id"], OFFER_ID)
        self.assertNotIn(API_KEY, str(report.as_dict()))

    async def test_wrong_key_is_reported_without_catalog(self):
        client = LavaClient(api_key="wrong", transport=httpx.MockTransport(FakeLava().handler))
        report = await run_preflight(client, _config(), settings_obj=lava_settings())
        self.assertFalse(report.ok)
        self.assertEqual(next(c.detail for c in report.checks if c.code == "api_access"), "unauthorized")

    async def test_non_subscription_product_and_missing_currency_price_fail(self):
        fake = FakeLava()
        fake.product_type = "DIGITAL_PRODUCT"
        report = await run_preflight(fake.client(), _config(), settings_obj=lava_settings())
        self.assertIn("subscription_product", _codes(report, False))
        self.assertIn("offer_1_month", _codes(report, False))
        fake.product_type = "SUBSCRIPTION"
        report = await run_preflight(fake.client(), _config(currency="RUB"), settings_obj=lava_settings())
        self.assertIn("offer_1_month", _codes(report, False))

    async def test_missing_flags_and_key_fail_closed(self):
        report = await run_preflight(None, _config(), settings_obj=lava_settings(LAVA_ENABLED=False,
                                                                                    LAVA_WEBHOOK_SECRET=""))
        self.assertEqual(_codes(report, False), {"sales_flag", "webhook_secret", "api_key"})


if __name__ == "__main__":
    unittest.main()
