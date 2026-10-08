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

    def test_payment_and_currency_are_both_centered_native_dialogs(self):
        dialog = self.host.split("private fun PaymentMethodDialog(", 1)[1].split("private fun PayContent(", 1)[0]
        currency = self.host.split("private fun CurrencyPreferenceDialog(", 1)[1].split("private fun PlanCard(", 1)[0]
        self.assertIn("Dialog(", dialog)
        self.assertIn("Dialog(", currency)
        self.assertIn("usePlatformDefaultWidth = false", dialog)
        self.assertIn("usePlatformDefaultWidth = false", currency)
        self.assertIn("fillMaxWidth(0.92f)", dialog)
        self.assertIn("fillMaxWidth(0.92f)", currency)
        self.assertNotIn("ModalBottomSheet", dialog)

    def test_method_selection_advances_without_an_extra_confirmation(self):
        self.assertIn("state.step == CheckoutStep.METHOD", self.host)
        self.assertIn("state.step != CheckoutStep.METHOD", self.host)
        self.assertIn("model.chooseBank(bank)\n                model.next()", self.host)
        self.assertIn("model.chooseMethod(method)\n                model.next()", self.host)
        self.assertIn("onDismiss = model::back", self.host)

    def test_payment_choices_are_limited_to_priced_plan_and_region(self):
        self.assertIn('availablePaymentOptions(\n                        state.region, state.plan', self.host)
        self.assertIn('if (region == "cn") CHINA_METHODS.filter { prices[it]?.containsKey(plan) == true }', self.model)
        self.assertIn('else if (region == "tj" && prices["visa"]?.containsKey(plan) == true) CARD_BANKS', self.model)


if __name__ == "__main__":
    unittest.main()
