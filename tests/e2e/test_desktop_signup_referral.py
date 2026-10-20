"""Signup invitations on the shared macOS/Windows shell, without a real provider."""
import json
import shutil
import subprocess
import sys

import pytest

from test_desktop_ui_preview import (
    browser_page, desktop_ui_url, playwright, _install_native_fixture, _lesson_payload,
)


@pytest.mark.parametrize("platform,provider,language,code", [
    ("macos", "google", "uz", "abcdef12"),
    ("windows", "google", "ru", "ref_abcdef12"),
    ("macos", "apple", "tj", "ra_abcdef12"),
    ("windows", "apple", "uz", "ri_abcdef12"),
    ("macos", "telegram", "ru", "ref_abcdef12"),
    ("windows", "telegram", "tj", "ri_abcdef12"),
])
def test_invitation_is_optional_bounded_and_frozen_per_signup(
    desktop_ui_url, browser_page, platform, provider, language, code,
):
    page, errors = browser_page
    page.set_viewport_size({"width": 720, "height": 560})
    page.add_init_script(script=f"""
      window.__AUTH_CALLS = [];
      window.__TAURI__ = {{ core: {{ invoke: async (command, args = {{}}) => {{
        window.__AUTH_CALLS.push({{ command, args }});
        if (command === 'desktop_app_info') return {{ productName: 'HSK AI', version: 'test', platform: {json.dumps(platform)} }};
        if (command === 'desktop_auth_status') return {{ linked: false }};
        if (command === 'desktop_oauth_providers') return {{ providers: ['google', 'apple'] }};
        if (['desktop_link_start', 'desktop_oauth_start'].includes(command)) {{
          return new Promise(resolve => {{ window.__FINISH_START = () => resolve({{ status: 'pending', displayCode: 'HSK4827X', expiresIn: 300 }}); }});
        }}
        if (command === 'desktop_oauth_open') return {{ ok: true }};
        if (command === 'desktop_link_poll') return {{ status: 'pending' }};
        throw new Error('desktop_operation_not_allowed');
      }} }} }};
    """)
    page.goto(desktop_ui_url, wait_until="networkidle")
    page.locator("#auth-language").select_option(language)
    invitation = page.locator("#auth-referral")
    invitation.fill("ra_abcdef12?admin=true")
    button = page.locator("#start-link" if provider == "telegram" else f"#auth-{provider}")
    button.click()
    playwright.expect(invitation).to_have_attribute("aria-invalid", "true")
    assert page.evaluate("window.__AUTH_CALLS.filter(c => ['desktop_link_start','desktop_oauth_start'].includes(c.command)).length") == 0
    assert page.locator("#auth-error").inner_text()
    invitation.fill(code)
    button.click()
    playwright.expect(invitation).to_be_disabled()
    starts = page.evaluate("window.__AUTH_CALLS.filter(c => ['desktop_link_start','desktop_oauth_start'].includes(c.command))")
    assert len(starts) == 1
    expected = {"language": language, "referralCode": code}
    if provider != "telegram":
        expected["provider"] = provider
    assert starts[0]["args"] == expected
    # An external DOM mutation cannot change metadata already sent to native code.
    invitation.evaluate("node => { node.value = 'ra_12345678'; }")
    page.evaluate("window.__FINISH_START()")
    playwright.expect(invitation).to_be_disabled()
    assert page.evaluate("window.__AUTH_CALLS.filter(c => ['desktop_link_start','desktop_oauth_start'].includes(c.command))[0].args.referralCode") == code
    assert errors == []


@pytest.mark.parametrize("platform", ["macos", "windows"])
def test_provider_only_account_shares_universal_invite_with_nonempty_qr(
    desktop_ui_url, browser_page, platform, tmp_path,
):
    page, errors = browser_page
    link = "https://telegram-chinese-bot-production.up.railway.app/apps?ref=abcdef12&mode=trial"
    _install_native_fixture(page, {1: _lesson_payload(1, [])}, provider_only=True, platform=platform)
    page.goto(desktop_ui_url, wait_until="networkidle")
    page.locator("#workspace").wait_for(state="visible")
    page.evaluate("""link => {
      const originalInvoke = window.__TAURI__.core.invoke;
      window.__TAURI__.core.invoke = async (command, args) => {
        if (command === 'desktop_referral_overview') return { ok: true, code: 'abcdef12', link, invited: 0, activated: 0, trial_required: 5, trial_progress: 0, items: [] };
        return originalInvoke(command, args);
      };
    }""", link)
    page.locator("#rail-profile-button").click()
    page.locator(".invite-main").click()
    playwright.expect(page.locator(".referral-link-row")).to_contain_text(link)
    qr = page.locator(".referral-qr-image")
    playwright.expect(qr).to_be_visible()
    assert qr.get_attribute("src").startswith("data:image/svg+xml;charset=utf-8,")
    assert qr.evaluate("node => node.complete && node.naturalWidth > 0")
    screenshot = tmp_path / f"universal-invite-{platform}.png"
    qr.screenshot(path=str(screenshot))
    # Decode actual rendered pixels with the stock macOS detector. This catches
    # capacity and format-bit mistakes a nonempty SVG assertion cannot detect.
    if sys.platform == "darwin" and shutil.which("swift"):
        decoder = tmp_path / "decode.swift"
        decoder.write_text(r'''import Foundation
import CoreImage
let image = CIImage(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))!
let detector = CIDetector(ofType: CIDetectorTypeQRCode, context: nil, options: [CIDetectorAccuracy: CIDetectorAccuracyHigh])!
let payloads = detector.features(in: image).compactMap { ($0 as? CIQRCodeFeature)?.messageString }
guard payloads == [CommandLine.arguments[2]] else { print("QR payload mismatch: \(payloads)"); exit(1) }
''')
        decoded = subprocess.run(["swift", str(decoder), str(screenshot), link], capture_output=True, text=True, timeout=60)
        assert decoded.returncode == 0, decoded.stdout + decoded.stderr
    assert errors == []
