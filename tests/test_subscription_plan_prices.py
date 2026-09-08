"""Tarif narxlarining yagona manbai.

Loyihada narx uch joyda yozilgan edi:

* `SubscriptionPriceService.DEFAULT_SUBSCRIPTION_PRICES` — haqiqiy manba,
* `payment_service.PLAN_PRICES` — ikkinchi nusxa, unda `3_months` YO'Q edi,
* `subscription.py::_plan_price` zaxirasi — uchinchi nusxa, unda ham yo'q edi.

Ikkinchi va uchinchi nusxalar olib tashlandi. Bu fayl ular qaytib
kelmasligini va uch oylik tarif hamma joyda tanilishini qotiradi.
"""

import unittest
from pathlib import Path

from app.bot.handlers.subscription import PLANS, RECOMMENDED_PLAN
from app.services.entitlements.contract import AVAILABLE_PLANS
from app.services.entitlements.decision import RECOMMENDED_PLAN as CONTRACT_RECOMMENDED
from app.services.subscription_price_service import (
    DEFAULT_SUBSCRIPTION_PRICES,
    PAYMENT_METHODS,
    PLANS as PRICE_PLANS,
)
from app.services.subscription_service import PLAN_DURATIONS


class PlanConsistencyTests(unittest.TestCase):
    def test_every_surface_knows_the_same_three_plans(self):
        expected = {"10_days", "1_month", "3_months"}

        self.assertEqual(expected, set(PRICE_PLANS))
        self.assertEqual(expected, set(PLAN_DURATIONS))
        self.assertEqual(expected, set(PLANS), "bot oqimi uch oylikni rad etmasin")
        self.assertEqual(expected, set(AVAILABLE_PLANS))

    def test_every_method_and_plan_pair_has_a_price(self):
        for method in PAYMENT_METHODS:
            for plan in PRICE_PLANS:
                with self.subTest(method=method, plan=plan):
                    self.assertIn((method, plan), DEFAULT_SUBSCRIPTION_PRICES)

    def test_three_months_is_the_recommended_plan_everywhere(self):
        self.assertEqual("3_months", RECOMMENDED_PLAN)
        self.assertEqual("3_months", CONTRACT_RECOMMENDED)
        self.assertIn(RECOMMENDED_PLAN, PLANS)

    def test_the_three_month_plan_is_cheaper_per_month(self):
        # Tavsiya qilinadigan tarif oyiga hisoblaganda arzonroq bo'lishi kerak,
        # aks holda tavsiya qilishning ma'nosi yo'q.
        for method in PAYMENT_METHODS:
            with self.subTest(method=method):
                monthly = DEFAULT_SUBSCRIPTION_PRICES[(method, "1_month")][0]
                quarterly = DEFAULT_SUBSCRIPTION_PRICES[(method, "3_months")][0]
                self.assertLess(quarterly / 3, monthly)


class NoDuplicatePriceTableTests(unittest.TestCase):
    def test_the_second_price_table_is_gone(self):
        source = Path("app/services/payment_service.py").read_text(encoding="utf-8")
        self.assertNotIn("PLAN_PRICES = {", source)
        self.assertNotIn("def get_plan_price(", source)

    def test_the_handler_falls_back_to_the_shared_defaults(self):
        source = Path("app/bot/handlers/subscription.py").read_text(encoding="utf-8")
        self.assertIn("DEFAULT_SUBSCRIPTION_PRICES[(method, plan_type)]", source)
        # Qattiq yozilgan raqamlar qaytib kelmasin.
        self.assertNotIn('return (66 if plan_type == "1_month" else 29), "¥"', source)
        self.assertNotIn('return (89 if plan_type == "1_month" else 29), "TJS"', source)


if __name__ == "__main__":
    unittest.main()
