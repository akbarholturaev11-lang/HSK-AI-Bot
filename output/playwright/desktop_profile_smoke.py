import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "output" / "playwright"
BASE_URL = "http://127.0.0.1:8767"


def screenshot(page, name):
    page.screenshot(path=str(ARTIFACTS / name), full_page=True)


def scroll_content(page, top):
    page.evaluate(
        """(top) => {
            const scroll = document.querySelector(".content-scroll");
            if (scroll) scroll.scrollTop = top;
        }""",
        top,
    )
    page.wait_for_timeout(100)


def assert_no_horizontal_overflow(page):
    overflow = page.evaluate(
        """() => ({
            body: document.body.scrollWidth,
            viewport: document.documentElement.clientWidth,
        })"""
    )
    assert overflow["body"] <= overflow["viewport"] + 1, overflow


def assert_profile_contract(page):
    expect(page.locator(".profile-hero")).to_be_visible()
    expect(page.locator(".profile-goal")).to_be_visible()
    expect(page.locator(".invite-card")).to_be_visible()
    expect(page.locator(".sync-card")).to_be_visible()
    expect(page.locator(".profile-stats-grid")).to_be_visible()
    expect(page.locator(".profile-progress-grid")).to_be_visible()
    expect(page.locator(".profile-account")).to_be_visible()

    order = page.evaluate(
        """() => [...document.querySelector("#content-inner").children]
            .map((node) => node.className)
            .filter(Boolean)"""
    )
    expected = [
        "view-heading",
        "profile-two-cols",
        "profile-actions",
        "profile-section-head",
        "profile-stats-grid",
        "profile-progress-grid",
        "soon-block",
        "profile-section-head",
        "profile-two-cols",
        "profile-section-head",
        "profile-account card-panel",
    ]
    assert order == expected, order

    text = page.locator("#content-inner").inner_text()
    for demo_value in ("326", "684", "82 min", "+18%", "53%"):
        assert demo_value not in text, demo_value
    assert "—" in page.locator(".profile-chips").inner_text()
    assert page.locator(".soon-block").count() >= 8


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1180, "height": 780},
            device_scale_factor=1,
        )
        page = context.new_page()
        console_errors = []
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type in ("error", "warning")
            else None,
        )
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        page.goto(f"{BASE_URL}/?mock=1", wait_until="networkidle")
        expect(page.locator("#workspace")).to_be_visible()
        expect(page.locator("#onboarding-layer")).to_be_visible()
        expect(page.locator(".goal-choice")).to_have_count(3)
        expect(page.locator("#onboarding-start")).to_be_disabled()
        screenshot(page, "desktop-onboarding-step-1.png")

        page.locator(".goal-choice").first.click()
        expect(page.locator("#onboarding-start")).to_be_enabled()
        page.locator("#onboarding-start").click()
        expect(page.locator(".widget-intro")).to_be_visible()
        expect(page.locator("#onboarding-body .soon-veil")).to_be_visible()
        screenshot(page, "desktop-onboarding-step-2.png")
        page.locator("#onboarding-start").click()
        expect(page.locator("#onboarding-layer")).to_be_hidden()

        page.locator("#show-profile").click()
        expect(page.locator(".profile-hero")).to_be_visible()
        assert_profile_contract(page)
        page.locator(".soon-block").first.hover()
        screenshot(page, "desktop-profile-uz.png")
        page.locator(".profile-progress-grid").scroll_into_view_if_needed()
        screenshot(page, "desktop-profile-progress.png")
        page.locator(".profile-account").scroll_into_view_if_needed()
        screenshot(page, "desktop-profile-account.png")
        scroll_content(page, 0)

        page.locator(".invite-main").click()
        expect(page.locator(".invite-morph")).to_have_class(re.compile(r"\bis-open\b"))
        expect(page.locator(".invite-tray .invite-action")).to_have_count(4)
        screenshot(page, "desktop-profile-invite-open.png")

        for language in ("ru", "tj", "uz"):
            page.locator('[data-role="language"]').select_option(language)
            expect(page.locator(".profile-hero")).to_be_visible()
            assert_no_horizontal_overflow(page)
            screenshot(page, f"desktop-profile-{language}.png")

        assert not console_errors, console_errors
        browser.close()


if __name__ == "__main__":
    main()
