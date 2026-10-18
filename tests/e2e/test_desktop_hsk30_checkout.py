"""The shared desktop checkout supports provider-only HSK 3.0 purchases."""
import pytest

from tests.e2e.test_desktop_ui_preview import (
    _install_native_fixture,
    _lesson_payload,
    browser_page,
    desktop_ui_url,
)


@pytest.mark.parametrize("platform,provider", [("macos", "google"), ("windows", "apple")])
def test_provider_only_hsk30_checkout_from_existing_profile_setting(
    desktop_ui_url, browser_page, platform, provider,
):
    page, errors = browser_page
    _install_native_fixture(
        page, {1: _lesson_payload(1, [])}, is_paid=False,
        provider_only=True, platform=platform, hsk30_unlock=True,
    )
    page.goto(desktop_ui_url, wait_until="networkidle")
    page.locator("#workspace").wait_for(state="visible")
    page.locator("#rail-profile-button").click()
    page.locator('[data-role="course-version"]').select_option("hsk30")
    page.locator('[data-testid="subscription-plan"][data-plan="hsk30_unlock"]').wait_for()
    assert page.locator('[data-testid="subscription-plan"]').count() == 1
    assert page.locator('[data-testid="subscription-plan"] .planPrice').inner_text() == "10\nTJS"
    page.get_by_role("button", name="To‘lov ma’lumotlarini ko‘rish").click()
    page.get_by_text("Fixture Visa: 0000 0000 0000 0000").wait_for()
    page.locator("#payment-screenshot").set_input_files({
        "name": f"{provider}-receipt.png", "mimeType": "image/png",
        "buffer": b"\x89PNG\r\n\x1a\nfixture",
    })
    page.locator("#payment-submit").click()
    page.get_by_role("heading", name="To‘lov yuborildi").wait_for()
    pending = page.evaluate("window.__DESKTOP_FIXTURE__.subscription.pendingPayment")
    assert (pending["plan_type"], pending["amount"], pending["currency"]) == ("hsk30_unlock", 10, "TJS")
    assert page.evaluate("window.__DESKTOP_FIXTURE__.subscription.submissions") == 1
    assert errors == []
