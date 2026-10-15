"""Public ownership verification and explicit deletion requests in a real browser."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from app.public_site.account_deletion_render import render_account_deletion

playwright = pytest.importorskip("playwright.sync_api")
expect = playwright.expect
ORIGIN = "http://hsk-ai.local"
SCRIPT = Path(__file__).resolve().parents[2] / "app/static/account-deletion.js"
SECRET = "test-browser-capability-never-in-a-url"


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as session:
        instance = session.chromium.launch(headless=True)
        yield instance
        instance.close()


@pytest.fixture()
def page(browser):
    context = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True)

    def static(route):
        path = urlsplit(route.request.url).path
        if path == "/account-deletion":
            route.fulfill(content_type="text/html", body=render_account_deletion())
        elif path == "/public-assets/account-deletion.js":
            route.fulfill(content_type="application/javascript", body=SCRIPT.read_text())
        else:
            route.fulfill(status=404, body="not found")

    context.route(ORIGIN + "/**", static)
    for provider in ("accounts.google.com", "appleid.apple.com", "t.me"):
        context.route("https://" + provider + "/**", lambda route: route.fulfill(
            content_type="text/html", body="Ownership verified. Return to the original HSK AI tab."
        ))
    instance = context.new_page()
    yield instance
    context.close()


def mock_flow(page, *, providers=("google", "apple", "telegram"), statuses=None,
              confirm_status=200, confirm_payload=None, start_status=200,
              expires_in=600):
    observed = []
    pending_statuses = list(statuses or [{
        "ok": True, "status": "verified", "account_label": "HSK learner",
        "request_id": "public-request", "expires_in": expires_in,
    }])
    status_calls = []

    def handle(route):
        path = urlsplit(route.request.url).path.rsplit("/", 1)[-1]
        body = json.loads(route.request.post_data or "{}")
        observed.append((path, body, route.request.url, route.request.headers))
        status = 200
        if path == "providers":
            payload = {"ok": True, "providers": list(providers)}
        elif path == "start":
            provider = body["provider"]
            payload = {"ok": True, "status": "pending", "request_id": "public-request",
                       "secret": SECRET, "expires_in": expires_in}
            if provider == "telegram":
                payload["bot_deep_link"] = "https://t.me/darsi_chini_bot?start=delete_public-token"
            else:
                host = "accounts.google.com" if provider == "google" else "appleid.apple.com"
                payload["authorize_url"] = "https://" + host + "/authorize?state=opaque-oauth-state"
            status = start_status
            if status != 200:
                payload = {"ok": False, "error": "provider_unavailable"}
        elif path == "status":
            status_calls.append(body)
            payload = pending_statuses[0]
            if len(pending_statuses) > 1:
                pending_statuses.pop(0)
            status = payload.get("http_status", 200)
        elif path == "confirm":
            status = confirm_status
            payload = confirm_payload or {
                "ok": True, "status": "submitted", "request_id": "deletion-receipt",
                "requested_at": "2026-10-15T02:00:00Z", "due_at": "2026-11-14T02:00:00Z",
            }
        else:
            route.fulfill(status=404, body="not found")
            return
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload))

    page.route(ORIGIN + "/api/account-deletion/**", handle)
    return observed, status_calls


def begin(page, provider):
    page.goto(ORIGIN + "/account-deletion", wait_until="networkidle")
    expect(page.locator('[data-provider="' + provider + '"]')).to_be_enabled()
    page.locator('[data-provider="' + provider + '"]').click()


@pytest.mark.parametrize("provider", ["google", "apple"])
def test_mobile_provider_verifies_same_identity_and_requires_explicit_confirmation(page, provider):
    observed, _ = mock_flow(page)
    errors = []
    console_errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    begin(page, provider)
    expect(page.locator("#deletion-confirm")).to_be_visible()
    expect(page.locator("#deletion-account")).to_have_text("HSK learner")
    expect(page.locator("#deletion-submit")).to_be_disabled()
    assert not any(path == "confirm" for path, *_ in observed)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.evaluate("Object.keys(localStorage).length + Object.keys(sessionStorage).length") == 0
    assert SECRET not in page.url
    assert SECRET not in page.content()
    page.locator("#deletion-consent").check()
    page.locator("#deletion-submit").click()
    expect(page.locator("#deletion-receipt")).to_be_visible()
    expect(page.locator("#deletion-reference")).to_have_text("deletion-receipt")
    expect(page.locator("#deletion-status")).to_have_text("Your deletion request has been received.")
    assert page.locator("#deletion-due-at").inner_text() != "Contact support with your request reference."
    confirms = [body for path, body, *_ in observed if path == "confirm"]
    assert confirms == [{"request_id": "public-request", "secret": SECRET, "confirmation": "DELETE"}]
    for _, _, url, headers in observed:
        assert SECRET not in url
        assert "authorization" not in headers
    assert page.locator("body").inner_text().count("does not cancel automatic renewal") == 1
    assert errors == [] and console_errors == []


def test_telegram_verification_still_waits_for_browser_confirmation(page):
    observed, status_calls = mock_flow(page, statuses=[
        {"ok": True, "status": "pending"},
        {"ok": True, "status": "verified", "account_label": "Telegram learner"},
    ])
    begin(page, "telegram")
    expect(page.locator("#deletion-pending")).to_be_visible()
    expect(page.locator("#deletion-verification-link")).to_have_attribute(
        "href", "https://t.me/darsi_chini_bot?start=delete_public-token"
    )
    expect(page.locator("#deletion-confirm")).to_be_visible(timeout=5000)
    assert len(status_calls) == 2
    assert not any(path == "confirm" for path, *_ in observed)
    expect(page.locator("#deletion-receipt")).to_be_hidden()


def test_unconfigured_providers_are_disabled_and_can_be_retried(page):
    observed, _ = mock_flow(page, providers=("telegram",))
    page.goto(ORIGIN + "/account-deletion", wait_until="networkidle")
    expect(page.locator('[data-provider="telegram"]')).to_be_enabled()
    expect(page.locator('[data-provider="google"]')).to_be_disabled()
    expect(page.locator('[data-provider="apple"]')).to_be_disabled()
    assert not any(path == "start" for path, *_ in observed)


def test_empty_provider_configuration_shows_error_and_retry(page):
    observed, _ = mock_flow(page, providers=())
    page.goto(ORIGIN + "/account-deletion", wait_until="networkidle")
    expect(page.locator("#deletion-error")).to_have_text("No verification methods are available right now.")
    expect(page.locator("#deletion-retry")).to_be_visible()
    page.locator("#deletion-retry").click()
    expect(page.locator("#deletion-error")).to_be_visible()
    assert len([item for item in observed if item[0] == "providers"]) == 2
    expect(page.locator("#deletion-receipt")).to_be_hidden()


def test_failed_confirm_never_shows_a_false_receipt_and_allows_retry(page):
    observed, _ = mock_flow(page, confirm_status=503,
                            confirm_payload={"ok": False, "error": "service_unavailable"})
    begin(page, "google")
    expect(page.locator("#deletion-confirm")).to_be_visible()
    page.locator("#deletion-consent").check()
    page.locator("#deletion-submit").click()
    expect(page.locator("#deletion-error")).to_contain_text("has not been confirmed")
    expect(page.locator("#deletion-receipt")).to_be_hidden()
    expect(page.locator("#deletion-submit")).to_be_enabled()
    assert len([item for item in observed if item[0] == "confirm"]) == 1


def test_submitted_receipt_can_explicitly_check_completed_status_without_polling(page):
    observed, status_calls = mock_flow(page, statuses=[
        {"ok": True, "status": "verified", "account_label": "HSK learner"},
        {"ok": True, "status": "completed", "request_id": "deletion-receipt",
         "requested_at": "2026-10-15T02:00:00Z", "due_at": "2026-11-14T02:00:00Z",
         "completed_at": "2026-10-16T02:00:00Z"},
    ])
    begin(page, "google")
    expect(page.locator("#deletion-confirm")).to_be_visible()
    page.locator("#deletion-consent").check()
    page.locator("#deletion-submit").click()
    expect(page.locator("#deletion-check-status")).to_be_visible()
    assert len(status_calls) == 1
    page.locator("#deletion-check-status").click()
    expect(page.locator("#receipt-title")).to_have_text("Account deletion completed")
    expect(page.locator("#deletion-status")).to_have_text("Your account deletion has been completed.")
    expect(page.locator("#deletion-receipt-message")).to_have_text(
        "Your account data has been deleted according to the retention rules below."
    )
    expect(page.locator("#deletion-check-status")).to_be_hidden()
    expect(page.locator("#deletion-completed-at")).to_contain_text("Completed:")
    assert status_calls == [{"request_id": "public-request", "secret": SECRET}] * 2
    assert len([item for item in observed if item[0] == "confirm"]) == 1
    assert page.evaluate("Object.keys(localStorage).length + Object.keys(sessionStorage).length") == 0
    assert SECRET not in page.url and SECRET not in page.content()


def test_receipt_status_error_preserves_submission_and_allows_explicit_retry(page):
    _, status_calls = mock_flow(page, statuses=[
        {"ok": True, "status": "verified", "account_label": "HSK learner"},
        {"ok": False, "error": "service_unavailable", "http_status": 503},
        {"ok": True, "status": "completed", "request_id": "deletion-receipt"},
    ])
    begin(page, "apple")
    expect(page.locator("#deletion-confirm")).to_be_visible()
    page.locator("#deletion-consent").check()
    page.locator("#deletion-submit").click()
    expect(page.locator("#deletion-check-status")).to_be_visible()
    page.locator("#deletion-check-status").click()
    expect(page.locator("#deletion-error")).to_contain_text("saved request remains submitted")
    expect(page.locator("#deletion-receipt")).to_be_visible()
    expect(page.locator("#deletion-check-status")).to_be_enabled()
    page.locator("#deletion-retry").click()
    expect(page.locator("#receipt-title")).to_have_text("Account deletion completed")
    expect(page.locator("#deletion-error")).to_be_hidden()
    assert len(status_calls) == 3


def test_status_network_error_can_retry_without_restarting_identity_proof(page):
    observed, _ = mock_flow(page, statuses=[
        {"ok": False, "error": "service_unavailable", "http_status": 503},
        {"ok": True, "status": "verified", "account_label": "HSK learner"},
    ])
    begin(page, "apple")
    expect(page.locator("#deletion-error")).to_be_visible()
    expect(page.locator("#deletion-receipt")).to_be_hidden()
    page.locator("#deletion-retry").click()
    expect(page.locator("#deletion-confirm")).to_be_visible()
    assert len([item for item in observed if item[0] == "start"]) == 1


def test_pending_polling_stops_at_expiry_and_never_submits(page):
    observed, status_calls = mock_flow(page, statuses=[{"ok": True, "status": "pending"}], expires_in=1)
    begin(page, "google")
    expect(page.locator("#deletion-error")).to_have_text(
        "Verification expired. Choose a sign-in method and verify again.", timeout=4000
    )
    expect(page.locator('[data-provider="google"]')).to_be_enabled()
    expect(page.locator("#deletion-receipt")).to_be_hidden()
    assert len(status_calls) <= 2
    assert not any(path == "confirm" for path, *_ in observed)


def test_unknown_account_cannot_reach_confirmation(page):
    observed, _ = mock_flow(page, statuses=[
        {"ok": True, "status": "failed"},
    ])
    begin(page, "google")
    expect(page.locator("#deletion-error")).to_contain_text("identity already linked")
    expect(page.locator("#deletion-confirm")).to_be_hidden()
    expect(page.locator("#deletion-receipt")).to_be_hidden()
    assert not any(path == "confirm" for path, *_ in observed)


def test_start_failure_preserves_public_instructions_and_retry_controls(page):
    mock_flow(page, start_status=503)
    begin(page, "apple")
    expect(page.locator("#deletion-error")).to_be_visible()
    expect(page.locator('[data-provider="apple"]')).to_be_enabled()
    expect(page.locator("#deletion-confirm")).to_be_hidden()
    expect(page.locator("#deletion-receipt")).to_be_hidden()


def test_provider_label_is_text_and_not_executable_html(page):
    mock_flow(page, statuses=[{
        "ok": True, "status": "verified", "account_label": '<img src=x onerror="window.pwned=true">',
    }])
    begin(page, "google")
    expect(page.locator("#deletion-confirm")).to_be_visible()
    assert page.locator("#deletion-account img").count() == 0
    assert page.evaluate("window.pwned === undefined")


def test_blocked_popup_provides_safe_manual_verification_link(page):
    mock_flow(page, statuses=[{"ok": True, "status": "pending"}])
    page.add_init_script("window.open = () => null;")
    begin(page, "google")
    expect(page.locator("#deletion-error")).to_contain_text("browser blocked")
    expect(page.locator("#deletion-verification-link")).to_be_visible()
    expect(page.locator("#deletion-verification-link")).to_have_attribute("rel", "noopener noreferrer")
    assert SECRET not in page.locator("#deletion-verification-link").get_attribute("href")
    expect(page.locator("#deletion-receipt")).to_be_hidden()


def test_restart_discards_stale_verification_result(page):
    mock_flow(page, statuses=[{"ok": True, "status": "pending"}])
    begin(page, "telegram")
    expect(page.locator("#deletion-pending")).to_be_visible()
    page.locator("#deletion-restart").click()
    expect(page.locator("#deletion-pending")).to_be_hidden()
    expect(page.locator("#deletion-verification-link")).not_to_have_attribute("href", SECRET)
    assert page.locator("#deletion-verification-link").get_attribute("href") is None
    expect(page.locator('[data-provider="google"]')).to_be_enabled()
    expect(page.locator("#deletion-confirm")).to_be_hidden()


def test_public_instructions_remain_available_without_javascript(browser):
    context = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
    context.route(ORIGIN + "/**", lambda route: route.fulfill(content_type="text/html", body=render_account_deletion()))
    page = context.new_page()
    page.goto(ORIGIN + "/account-deletion", wait_until="networkidle")
    # Playwright's text matcher excludes noscript; inspect the parsed fallback DOM.
    assert "JavaScript is needed for Google or Apple verification" in page.locator("noscript").text_content()
    expect(page.locator('noscript a[href="https://t.me/darsi_chini_bot?start=account_deletion"]')).to_be_visible()
    expect(page.locator("#deletion-providers")).to_be_hidden()
    assert "Approved payment records" in page.locator("body").inner_text()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    context.close()
