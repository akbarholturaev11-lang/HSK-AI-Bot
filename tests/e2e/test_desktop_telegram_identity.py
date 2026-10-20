"""Authenticated Telegram attachment on the shared macOS / Windows shell."""
import pytest

from test_desktop_ui_preview import (
    browser_page, desktop_ui_url, playwright, _install_native_fixture, _lesson_payload,
)


def _profile(page, desktop_ui_url, platform, *, linked=False, start_mode="ready", poll_mode="pending"):
    _install_native_fixture(page, {1: _lesson_payload(1, [])}, provider_only=not linked, platform=platform)
    page.set_viewport_size({"width": 720, "height": 560})
    page.goto(desktop_ui_url, wait_until="networkidle")
    page.locator("#workspace").wait_for(state="visible")
    page.evaluate("""options => {
      const previous = window.__TAURI__.core.invoke;
      window.__IDENTITY = { ...options, calls: [], pollResolves: [] };
      window.__TAURI__.core.invoke = async (command, args = {}) => {
        const fixture = window.__IDENTITY;
        fixture.calls.push({command, args});
        if (command === 'desktop_identity_methods') return {telegram_linked: fixture.linked};
        if (command === 'desktop_telegram_identity_start') {
          if (fixture.startMode === 'deferred') return new Promise(resolve => { fixture.finishStart = resolve; });
          return { status: 'pending', expiresIn: 300 };
        }
        if (command === 'desktop_identity_link_open' || command === 'desktop_identity_link_cancel') return null;
        if (command === 'desktop_identity_link_poll') {
          if (fixture.pollMode === 'session_expired') throw new Error('desktop_session_revoked');
          if (fixture.pollMode === 'deferred') return new Promise(resolve => fixture.pollResolves.push(resolve));
          if (fixture.pollMode === 'conflict') return {status: 'denied', error: 'oauth_identity_bound_to_other_user'};
          if (fixture.pollMode === 'linked') { fixture.linked = true; return {status: 'linked'}; }
          return {status: fixture.pollMode};
        }
        return previous(command, args);
      };
    }""", {"linked": linked, "startMode": start_mode, "pollMode": poll_mode})
    page.locator("#rail-profile-button").click()
    if not linked:
        playwright.expect(page.locator('[data-role="telegram-identity-connect"]')).to_be_enabled()


def _connect(page):
    page.locator('[data-role="telegram-identity-connect"]').click()
    dialog = page.locator(".identity-link-shell")
    playwright.expect(dialog).to_be_visible()
    return dialog


def _calls(page, command):
    return page.evaluate("command => window.__IDENTITY.calls.filter(call => call.command === command)", command)


@pytest.mark.parametrize("platform", ["macos", "windows"])
def test_native_account_adds_telegram_without_replacing_session_or_progress(desktop_ui_url, browser_page, platform):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform)
    before = page.evaluate("JSON.stringify(window.__DESKTOP_FIXTURE__.map)")
    dialog = _connect(page)
    playwright.expect(dialog.get_by_role("status")).to_contain_text("Botda")
    page.wait_for_function("window.__IDENTITY.calls.some(call => call.command === 'desktop_identity_link_poll')")
    assert len(_calls(page, "desktop_identity_link_open")) == 1
    attempt = _calls(page, "desktop_telegram_identity_start")[0]["args"]["attemptId"]
    assert len(attempt) == 36
    assert _calls(page, "desktop_identity_link_open")[0]["args"] == {"attemptId": attempt}
    # Tab is contained in the sheet even at a narrow desktop window size.
    dialog.get_by_role("button", name="Yopish", exact=True).focus()
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.closest('.identity-link-shell') !== null")
    assert dialog.evaluate("node => { const r = node.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight; }")
    page.evaluate("window.__IDENTITY.pollMode = 'linked'")
    playwright.expect(dialog).to_have_count(0, timeout=8000)
    playwright.expect(page.locator(".profile-account")).to_contain_text("Telegram ulangan")
    assert page.locator('[data-role="telegram-identity-connect"]').count() == 0
    assert _calls(page, "desktop_identity_link_cancel") == []
    assert _calls(page, "desktop_link_start") == []
    assert _calls(page, "desktop_link_poll") == []
    assert _calls(page, "desktop_oauth_start") == []
    assert page.evaluate("JSON.stringify(window.__DESKTOP_FIXTURE__.map)") == before
    assert errors == []


@pytest.mark.parametrize("platform,language,conflict", [
    ("macos", "uz", "boshqa akkauntga ulangan"),
    ("windows", "ru", "другому аккаунту"),
    ("macos", "tj", "ҳисоби дигар"),
])
def test_bound_telegram_conflict_is_localized_and_does_not_attach(desktop_ui_url, browser_page, platform, language, conflict):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform, poll_mode="conflict")
    page.locator('[data-role="language"]').select_option(language)
    dialog = _connect(page)
    playwright.expect(dialog.get_by_role("status")).to_contain_text(conflict)
    assert "oauth_identity" not in dialog.inner_text()
    assert _calls(page, "desktop_identity_link_cancel")
    page.keyboard.press("Escape")
    playwright.expect(dialog).to_have_count(0)
    playwright.expect(page.locator('[data-role="telegram-identity-connect"]')).to_be_enabled()
    assert errors == []


@pytest.mark.parametrize("platform", ["macos", "windows"])
def test_dismissed_start_never_opens_bot_and_cancels_the_late_proof(desktop_ui_url, browser_page, platform):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform, start_mode="deferred")
    dialog = _connect(page)
    page.wait_for_function("typeof window.__IDENTITY.finishStart === 'function'")
    page.keyboard.press("Escape")
    playwright.expect(dialog).to_have_count(0)
    page.evaluate("window.__IDENTITY.finishStart({status:'pending', expiresIn:300})")
    page.wait_for_function("window.__IDENTITY.calls.filter(call => call.command === 'desktop_identity_link_cancel').length >= 2")
    assert _calls(page, "desktop_identity_link_open") == []
    assert _calls(page, "desktop_identity_link_poll") == []
    playwright.expect(page.locator('[data-role="telegram-identity-connect"]')).to_be_enabled()
    assert errors == []


@pytest.mark.parametrize("platform", ["macos", "windows"])
def test_late_poll_cannot_complete_or_close_a_replacement_sheet(desktop_ui_url, browser_page, platform):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform, poll_mode="deferred")
    _connect(page)
    page.wait_for_function("window.__IDENTITY.pollResolves.length === 1")
    old_attempt = _calls(page, "desktop_telegram_identity_start")[0]["args"]["attemptId"]
    page.keyboard.press("Escape")
    dialog = _connect(page)
    page.wait_for_function("window.__IDENTITY.pollResolves.length === 2")
    new_attempt = _calls(page, "desktop_telegram_identity_start")[1]["args"]["attemptId"]
    assert old_attempt != new_attempt
    page.evaluate("window.__IDENTITY.pollResolves[0]({status:'linked'})")
    playwright.expect(dialog.get_by_role("status")).to_contain_text("Botda")
    assert "Telegram ulangan" not in page.locator(".profile-account").inner_text()
    assert _calls(page, "desktop_identity_link_cancel")[0]["args"]["attemptId"] == old_attempt
    page.keyboard.press("Escape")
    assert errors == []


@pytest.mark.parametrize("platform", ["macos", "windows"])
def test_old_telegram_account_stays_readonly_without_detach_or_new_link(desktop_ui_url, browser_page, platform):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform, linked=True)
    playwright.expect(page.locator(".profile-account")).to_contain_text("Telegram ulangan")
    assert page.locator('[data-role="telegram-identity-connect"]').count() == 0
    assert _calls(page, "desktop_telegram_identity_start") == []
    assert _calls(page, "desktop_identity_link_cancel") == []
    assert errors == []


@pytest.mark.parametrize("platform,status,message", [("macos", "denied", "Telegram ulanmadi"), ("windows", "expired", "Ulash muddati tugadi")])
def test_terminal_bot_approval_states_stop_polling(desktop_ui_url, browser_page, platform, status, message):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform, poll_mode=status)
    dialog = _connect(page)
    playwright.expect(dialog.get_by_role("status")).to_contain_text(message)
    assert len(_calls(page, "desktop_identity_link_poll")) == 1
    assert _calls(page, "desktop_identity_link_cancel")
    assert errors == []


@pytest.mark.parametrize("platform", ["macos", "windows"])
def test_revoked_session_closes_sheet_and_requires_signin(desktop_ui_url, browser_page, platform):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform, poll_mode="session_expired")
    page.locator('[data-role="telegram-identity-connect"]').click()
    playwright.expect(page.locator("#auth-screen")).to_be_visible()
    playwright.expect(page.locator(".identity-link-shell")).to_have_count(0)
    assert _calls(page, "desktop_identity_link_cancel")
    assert errors == []


@pytest.mark.parametrize("platform", ["macos", "windows"])
def test_late_poll_after_logout_cannot_restore_profile_or_session(desktop_ui_url, browser_page, platform):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform, poll_mode="deferred")
    _connect(page)
    page.wait_for_function("window.__IDENTITY.pollResolves.length === 1")
    page.keyboard.press("Escape")
    page.locator(".profile-account .is-danger").click()
    playwright.expect(page.locator("#auth-screen")).to_be_visible()
    page.evaluate("window.__IDENTITY.pollResolves[0]({status:'linked', bootstrap:{user:{user_id:999}}})")
    playwright.expect(page.locator("#auth-screen")).to_be_visible()
    playwright.expect(page.locator("#workspace")).to_be_hidden()
    assert page.locator(".identity-link-shell").count() == 0
    assert len(_calls(page, "desktop_logout")) == 1
    assert errors == []
