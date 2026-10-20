"""Provider attachment and harmless browser resume on the paired desktop shell."""
import pytest

from test_desktop_ui_preview import (
    browser_page, desktop_ui_url, playwright, _install_native_fixture, _lesson_payload,
)


def _profile(page, url, platform, *, linked=(), available=("google", "apple"), start_mode="ready", poll="pending"):
    _install_native_fixture(page, {1: _lesson_payload(1, [])}, platform=platform)
    page.add_init_script("""
      window.__TAURI__.event = {listen: async (name, callback) => {
        if (name === 'desktop-auth://return') window.__AUTH_RETURN = callback;
        return () => {};
      }};
    """)
    page.set_viewport_size({"width": 720, "height": 560})
    page.goto(url, wait_until="networkidle")
    page.locator("#workspace").wait_for(state="visible")
    page.evaluate("""options => {
      const previous = window.__TAURI__.core.invoke;
      window.__PROVIDER_LINK = {...options, calls: []};
      window.__TAURI__.core.invoke = async (command, args = {}) => {
        const f = window.__PROVIDER_LINK;
        f.calls.push({command, args});
        if (command === 'desktop_identity_methods') return {telegram_linked: true, identities: f.linked};
        if (command === 'desktop_oauth_providers') return {providers: f.available};
        if (command === 'desktop_oauth_identity_start') {
          f.provider = args.provider;
          if (f.startMode === 'deferred') return new Promise(resolve => { f.finishStart = resolve; });
          return {status: 'pending', expiresIn: 300};
        }
        if (command === 'desktop_identity_link_open' || command === 'desktop_identity_link_cancel') return null;
        if (command === 'desktop_identity_link_poll') {
          if (f.poll === 'deferred') return new Promise(resolve => {f.finishPoll = resolve;});
          if (f.poll === 'conflict') return {status: 'failed', error: 'oauth_identity_bound_to_other_user'};
          if (f.poll === 'linked') f.linked.push(f.provider);
          return {status: f.poll};
        }
        return previous(command, args);
      };
    }""", {"linked": list(linked), "available": list(available), "startMode": start_mode, "poll": poll})
    page.locator("#rail-profile-button").click()
    page.wait_for_function("window.__PROVIDER_LINK.calls.some(c => c.command === 'desktop_identity_methods')")


def _calls(page, command):
    return page.evaluate("command => window.__PROVIDER_LINK.calls.filter(c => c.command === command)", command)


@pytest.mark.parametrize("platform", ["macos", "windows"])
@pytest.mark.parametrize("provider", ["google", "apple"])
def test_provider_attachment_uses_existing_account_and_browser_return_only_resumes_poll(desktop_ui_url, browser_page, platform, provider):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform)
    before = page.evaluate("JSON.stringify(window.__DESKTOP_FIXTURE__.map)")
    page.locator(f'[data-role="{provider}-identity-connect"]').click()
    dialog = page.locator(".identity-link-shell")
    playwright.expect(dialog.get_by_role("status")).to_contain_text("Brauzerda")
    page.wait_for_function("window.__PROVIDER_LINK.calls.some(c => c.command === 'desktop_identity_link_poll')")
    starts = _calls(page, "desktop_oauth_identity_start")
    assert len(starts) == 1 and starts[0]["args"]["provider"] == provider
    assert _calls(page, "desktop_identity_link_open")[0]["args"] == {"attemptId": starts[0]["args"]["attemptId"]}
    # A spoofed event body cannot finish attachment; only server polling can.
    page.evaluate("window.__AUTH_RETURN({payload:{status:'linked', access_token:'spoofed'}})")
    playwright.expect(dialog).to_be_visible()
    page.evaluate("window.__PROVIDER_LINK.poll = 'linked'; window.__AUTH_RETURN({payload:null})")
    playwright.expect(dialog).to_have_count(0)
    playwright.expect(page.locator(f'[data-role="{provider}-identity-connect"]')).to_have_count(0)
    assert _calls(page, "desktop_oauth_start") == []
    assert _calls(page, "desktop_link_poll") == []
    assert _calls(page, "desktop_identity_link_cancel") == []
    assert page.evaluate("JSON.stringify(window.__DESKTOP_FIXTURE__.map)") == before
    assert errors == []


@pytest.mark.parametrize("platform,language,provider,message", [
    ("macos", "uz", "google", "boshqa akkauntga"),
    ("windows", "ru", "apple", "другому аккаунту"),
    ("macos", "tj", "apple", "ҳисоби дигар"),
])
def test_provider_conflict_stays_in_own_account_without_merge(desktop_ui_url, browser_page, platform, language, provider, message):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform, poll="conflict")
    page.locator('[data-role="language"]').select_option(language)
    page.locator(f'[data-role="{provider}-identity-connect"]').click()
    dialog = page.locator(".identity-link-shell")
    playwright.expect(dialog.get_by_role("status")).to_contain_text(message)
    before = len(_calls(page, "desktop_identity_link_poll"))
    page.evaluate("window.__AUTH_RETURN({payload:{status:'linked'}})")
    assert len(_calls(page, "desktop_identity_link_poll")) == before
    assert _calls(page, "desktop_identity_link_cancel")
    assert errors == []


@pytest.mark.parametrize("platform", ["macos", "windows"])
def test_linked_and_unconfigured_provider_actions_are_hidden(desktop_ui_url, browser_page, platform):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform, linked=("google",), available=("google",))
    playwright.expect(page.locator(".profile-account")).to_contain_text("Google ulangan")
    assert page.locator('[data-role="google-identity-connect"]').count() == 0
    assert page.locator('[data-role="apple-identity-connect"]').count() == 0
    assert _calls(page, "desktop_oauth_identity_start") == []
    assert errors == []


@pytest.mark.parametrize("platform", ["macos", "windows"])
def test_closed_provider_start_cancels_late_proof_and_never_opens_browser(desktop_ui_url, browser_page, platform):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform, start_mode="deferred")
    page.locator('[data-role="google-identity-connect"]').click()
    page.wait_for_function("typeof window.__PROVIDER_LINK.finishStart === 'function'")
    page.keyboard.press("Escape")
    page.evaluate("window.__PROVIDER_LINK.finishStart({status:'pending', expiresIn:300})")
    page.wait_for_function("window.__PROVIDER_LINK.calls.filter(c => c.command === 'desktop_identity_link_cancel').length >= 2")
    assert _calls(page, "desktop_identity_link_open") == []
    assert _calls(page, "desktop_identity_link_poll") == []
    assert errors == []


@pytest.mark.parametrize("platform", ["macos", "windows"])
def test_browser_return_does_not_start_an_auth_flow_when_idle(desktop_ui_url, browser_page, platform):
    page, errors = browser_page
    _profile(page, desktop_ui_url, platform)
    page.evaluate("window.__AUTH_RETURN({payload:{status:'linked', bootstrap:{user:{user_id:999}}}})")
    assert _calls(page, "desktop_oauth_identity_start") == []
    assert _calls(page, "desktop_identity_link_poll") == []
    assert _calls(page, "desktop_link_poll") == []
    playwright.expect(page.locator("#workspace")).to_be_visible()
    assert errors == []


@pytest.mark.parametrize("platform", ["macos", "windows"])
@pytest.mark.parametrize("provider", ["google", "apple"])
def test_provider_signin_return_requires_native_server_poll_before_entering_workspace(desktop_ui_url, browser_page, platform, provider):
    page, errors = browser_page
    _install_native_fixture(page, {1: _lesson_payload(1, [])}, platform=platform)
    page.add_init_script("""
      const original = window.__TAURI__.core.invoke;
      window.__SIGNIN = {calls: [], status: 'pending'};
      window.__TAURI__.event.listen = async (name, callback) => {
        if (name === 'desktop-auth://return') window.__AUTH_RETURN = callback;
        return () => {};
      };
      window.__TAURI__.core.invoke = async (command, args = {}) => {
        const f = window.__SIGNIN;
        f.calls.push({command, args});
        if (command === 'desktop_auth_status') return {linked: false};
        if (command === 'desktop_oauth_providers') return {providers: ['google', 'apple']};
        if (command === 'desktop_oauth_start') return {status:'pending', expiresIn:300};
        if (command === 'desktop_oauth_open') return null;
        if (command === 'desktop_link_poll') return {
          status: f.status,
          bootstrap: f.status === 'linked' ? (await original('desktop_auth_status')).bootstrap : null,
        };
        return original(command, args);
      };
    """)
    page.goto(desktop_ui_url, wait_until="networkidle")
    playwright.expect(page.locator("#auth-screen")).to_be_visible()
    page.locator(f"#auth-{provider}").click()
    page.wait_for_function("window.__SIGNIN.calls.some(c => c.command === 'desktop_oauth_open')")
    page.evaluate("window.__AUTH_RETURN({payload:{status:'linked', bootstrap:{user:{user_id:999}}}})")
    playwright.expect(page.locator("#auth-screen")).to_be_visible()
    page.evaluate("window.__SIGNIN.status = 'linked'; window.__AUTH_RETURN({payload:null})")
    playwright.expect(page.locator("#workspace")).to_be_visible()
    playwright.expect(page.locator("#rail-profile-button")).to_contain_text("Fixture User")
    assert page.evaluate("window.__SIGNIN.calls.filter(c => c.command === 'desktop_oauth_start').length") == 1
    assert page.evaluate("window.__SIGNIN.calls.filter(c => c.command === 'desktop_link_start').length") == 0
    assert errors == []
