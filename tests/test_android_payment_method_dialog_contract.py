"""Verify the direct Android payment picker matches the currency dialog's UX."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBSCRIPTION = ROOT / "android" / "app" / "src" / "direct" / "java" / "com" / "pomp" / "hskai" / "feature" / "subscription"


class PaymentMethodDialogContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.host = (SUBSCRIPTION / "SubscriptionCheckoutHost.kt").read_text(encoding="utf-8")
        cls.model = (SUBSCRIPTION / "SubscriptionCheckoutViewModel.kt").read_text(encoding="utf-8")

    def test_payment_method_and_country_are_centered_without_a_second_currency_picker(self):
        # The ViewModel owns the derived currency: choosing a card country
        # automatically selects its currency. The old separate currency
        # picker no longer exists and should not be required by this test.
        dialog = self.host.split("private fun PaymentMethodDialog(", 1)[1].split("private fun PayContent(", 1)[0]
        country = self.host.split("if (state.regionDialogOpen && !state.loading &&", 1)[1].split(
            "// Optional: only for users who want to change the default bank/wallet.", 1
        )[0]
        for block in (dialog, country):
            self.assertIn("Dialog(", block)
            self.assertIn("usePlatformDefaultWidth = false", block)
            self.assertIn("fillMaxWidth(0.92f)", block)
            self.assertIn("RoundedCornerShape(20.dp)", block)
            self.assertNotIn("ModalBottomSheet", block)
        self.assertIn("onRegion = model::chooseRegion", country)
        self.assertNotIn("private fun CurrencyPreferenceDialog(", self.host)
        self.assertIn('else -> "USD"', self.model)
        self.assertIn("HskSceneSurface(modifier = Modifier.fillMaxSize())", self.host)

    def test_method_selection_is_optional_and_quote_follows_plan_continue(self):
        self.assertIn("listOf(CheckoutStep.PLANS, CheckoutStep.PAY)", self.model)
        self.assertIn("model.chooseBank(bank); methodOpen = false", self.host)
        self.assertIn("model.chooseMethod(method); methodOpen = false", self.host)
        self.assertIn("CheckoutStep.PLANS ->", self.model)
        self.assertIn("loadQuote()", self.model)

    def test_payment_choices_are_limited_to_priced_plan_and_region(self):
        self.assertIn('availablePaymentOptions(\n                        state.region, state.plan', self.host)
        self.assertIn('if (region == "cn") CHINA_METHODS.filter { prices[it]?.containsKey(plan) == true }', self.model)
        self.assertIn('else if (region == "tj" && prices["visa"]?.containsKey(plan) == true) CARD_BANKS', self.model)


if __name__ == "__main__":
    unittest.main()
