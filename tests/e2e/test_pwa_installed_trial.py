"""Installed/profile PWA trial uses the real Li scenes and verified-route fixtures."""
import ast
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

from tests.e2e.test_pwa_learning_parity import LearningPage, STATIC, ORIGIN
from tests.e2e.test_pwa_progressive_sections import pwa_document


def real_pwa_document():
    tree = ast.parse(Path("app/api/pwa_auth.py").read_text())
    value = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "_PWA_INLINE_PRO_HTML" for t in node.targets))
    injected = ast.literal_eval(value.func.value)
    return pwa_document().replace("</body>", injected + "</body>")


class TrialPage(LearningPage):
    def __init__(self, language="uz", *, eligible=True, standalone=False, hsk30=False):
        super().__init__(lang=language)
        self.installed = standalone
        self.trial = {"eligible": eligible, "active": False, "ends_at": None, "days": 7}
        self.data["study_setup"] = {"goal": "hsk_exam", "daily_minutes": 20,
                                    "preferred_focus": "listening", "pending": False}
        self.data["user"].update(plan="free", state="FREE", is_paid=False)
        if hsk30:
            self.data["level"] = "nhsk1"
        self.status_reads = []
        self.starts = []
        self.onboarding_writes = []
        self.status_fail = False
        self.start_fail = False
        self.start_lost_ack = False
        self.hold_start = False
        self.start_held = []
        self.status_owner = self.owner_id
        self.child_owner = self.owner_id
        self.status_held = []
        self.hold_status = False
        self.hold_bridge = False
        self.bridge_held = []

    def serve(self, route):
        path = urlsplit(route.request.url).path
        if path.endswith("/iphone-pwa-inline-pro-bridge.js") and self.hold_bridge:
            self.bridge_held.append(route)
        elif path == "/iphone-pwa/course":
            route.fulfill(content_type="text/html", body=real_pwa_document())
        elif path == "/iphone-pwa/onboarding/li":
            route.fulfill(content_type="text/html", path=str(STATIC / "course_v3_li_onboarding.html"),
                          headers={"X-Frame-Options": "SAMEORIGIN", "Content-Security-Policy": "frame-ancestors 'self'"})
        elif path == "/iphone-pwa":
            route.fulfill(content_type="text/html", body="<h1>Sign in</h1>")
        elif path == "/api/v3/pwa-auth/session":
            owner = self.child_owner if route.request.frame.parent_frame else self.owner_id
            route.fulfill(json={"ok": True, "user_id": owner, "csrf": "test-csrf"})
        elif path == "/api/v3/pwa/onboarding/status":
            route.fulfill(headers={"X-HSK-PWA-User-ID": str(self.child_owner)}, json={
                "ok": True, "saved": True, "level": self.data["level"], "profile": {
                    "goal": "hsk_exam", "goals": ["hsk_exam"], "daily_minutes": 20,
                    "preferred_focus": "listening", "streak_target_days": 14,
                },
            })
        elif path == "/api/v3/pwa/onboarding":
            self.onboarding_writes.append(route.request.post_data_json)
            route.fulfill(status=503, json={"ok": False})
        elif path == "/api/v3/pwa/profile":
            route.fulfill(headers={"X-HSK-PWA-User-ID": str(self.owner_id)}, json={
                "ok": True, "stats": {"answer_accuracy": {"overall": {"percent": 77}, "today": {"percent": 50}}},
            })
        elif path == "/api/v3/pwa/trial/status":
            self.status_reads.append(route.request)
            if self.hold_status:
                self.status_held.append(route)
                return
            route.fulfill(status=503 if self.status_fail else 200,
                          headers={"X-HSK-PWA-User-ID": str(self.status_owner)},
                          json={"ok": not self.status_fail, "trial": self.trial})
        elif path == "/api/v3/pwa/trial/start":
            self.starts.append(route.request)
            assert route.request.headers["x-hsk-pwa-csrf"] == "test-csrf"
            assert route.request.post_data_json == {}
            if self.hold_start:
                self.start_held.append(route)
                return
            if self.start_fail:
                route.fulfill(status=503, json={"ok": False})
                return
            self.trial.update(eligible=False, active=True, ends_at="2026-12-01T00:00:00+00:00")
            self.data["user"].update(plan="trial", state="TRIAL_ACTIVE", is_paid=True,
                                     access_ends_at=self.trial["ends_at"])
            if self.start_lost_ack:
                route.abort()
            else:
                route.fulfill(json={"ok": True, "ends_at": self.trial["ends_at"]})
        elif path == "/iphone-pwa/checkout":
            # Payment logic has its own real checkout suites. Here the
            # existing iframe destination proves the explicit paid handoff.
            route.fulfill(content_type="text/html", body='<h1 id="existing-checkout">Checkout</h1>')
        else:
            super().serve(route)

    def open(self, browser, width=390):
        context = browser.new_context(viewport={"width": width, "height": 844},
                                      reduced_motion="reduce", is_mobile=True)
        page = context.new_page()
        if self.installed:
            page.add_init_script("Object.defineProperty(navigator,'standalone',{get:()=>true})")
        page.set_default_timeout(12000)
        page.route("**/*", self.serve)
        page.goto(ORIGIN + "/iphone-pwa/course?lang=" + self.lang, wait_until="networkidle")
        page.wait_for_function("window.HskPwaTrialOffer && window.MAP && MAP.authenticated")
        return page


@pytest.fixture
def browser():
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv("PWA_E2E_ENGINE", "chromium")).launch()
        yield browser
        browser.close()


def trial_frame(page):
    frame = page.frame_locator("#pwa-checkout-layer iframe")
    frame.locator(".li-pro-welcome").wait_for()
    return frame


def profile(page):
    page.locator('#nav [data-s="profile"]').click()
    page.locator('.hp-promo-slide[data-promo-kind="pro"] .hp-promo-action').wait_for()
    page.evaluate("HskProfileCarousel.pause()")


@pytest.mark.parametrize("language", ["uz", "ru", "tj"])
@pytest.mark.parametrize("width", [320, 430])
def test_installed_first_open_shows_real_trial_scenes_once_without_rewriting_profile(browser, language, width):
    fixture = TrialPage(language, standalone=True)
    page = fixture.open(browser, width)
    frame = trial_frame(page)
    assert fixture.starts == [] and fixture.onboarding_writes == []
    assert page.evaluate("localStorage.getItem('hskai.pwa.trial.presented.v1:31')") == "1"
    for state in ("trial1", "trial2", "trial3"):
        frame.locator("#footer .cta").first.click()
        page.wait_for_function("state => document.querySelector('#pwa-checkout-layer iframe').contentWindow.screen===state", arg=state)
        assert frame.locator("#stage").evaluate("el => el.scrollWidth<=el.clientWidth+1")
        assert frame.locator(".li-trial-close").bounding_box()["width"] >= 44
        assert fixture.starts == []
    directory = os.getenv("HSK_TRIAL_REVIEW_DIR")
    if directory:
        Path(directory).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(directory) / f'{os.getenv("PWA_E2E_ENGINE", "chromium")}-{width}-{language}-trial.png'))
    frame.locator(".li-trial-close").click()
    assert page.locator("#pwa-checkout-layer").count() == 0
    assert not page.locator(".wrap").evaluate("el => el.inert")
    page.reload(wait_until="networkidle")
    assert page.locator("#pwa-checkout-layer").count() == 0
    assert fixture.starts == [] and fixture.onboarding_writes == []


def test_profile_pro_is_first_and_current_hsk30_has_no_repeat_card(browser):
    fixture = TrialPage(hsk30=True)
    page = fixture.open(browser)
    profile(page)
    assert page.locator(".hp-promo-slide").first.get_attribute("data-promo-kind") == "pro"
    assert page.locator("#hsk-profile-promo-root").get_attribute("data-promo-kind") == "pro"
    assert page.locator('.hp-promo-slide[data-promo-kind="hsk30"]').count() == 0
    page.locator('.hp-promo-slide[data-promo-kind="pro"] .hp-promo-action').click()
    frame = trial_frame(page)
    assert fixture.starts == [] and fixture.onboarding_writes == []
    frame.locator("#footer .cta.ghost").click()
    page.locator('#pwa-checkout-layer iframe[src*="/iphone-pwa/checkout?"]').wait_for()
    assert "source=profile" in page.locator("#pwa-checkout-layer iframe").get_attribute("src")
    assert fixture.starts == []


@pytest.mark.parametrize("lost_ack", [False, True])
def test_explicit_trial_confirmation_and_lost_ack_refresh_the_real_map(browser, lost_ack):
    fixture = TrialPage(standalone=True)
    fixture.start_lost_ack = lost_ack
    page = fixture.open(browser)
    frame = trial_frame(page)
    for _ in range(3):
        frame.locator("#footer .cta").first.click()
    assert fixture.starts == []
    frame.locator("#footer .cta").first.click()
    frame.locator(".done-hero").wait_for()
    assert len(fixture.starts) == 1
    frame.locator("#footer .cta").first.click()
    page.wait_for_function("MAP.user.state==='TRIAL_ACTIVE'")
    assert page.locator("#pwa-checkout-layer").count() == 0
    assert fixture.onboarding_writes == []


def test_used_trial_checkout_and_error_retry_do_not_grant_or_show_false_success(browser):
    fixture = TrialPage(eligible=False, standalone=True)
    page = fixture.open(browser)
    assert page.locator("#pwa-checkout-layer").count() == 0
    fixture.status_fail = True
    page.evaluate("App.goPay('profile_subscription')")
    page.wait_for_function("TRIAL_PROMISE===null")
    assert page.locator("#pwa-checkout-layer").count() == 0
    assert page.evaluate("TRIAL_LOADED") is False
    fixture.status_fail = False
    page.evaluate("App.goPay('profile_subscription')")
    page.locator('#pwa-checkout-layer iframe[src*="/iphone-pwa/checkout?"]').wait_for()
    assert fixture.starts == [] and fixture.onboarding_writes == []


def test_trial_status_owner_replacement_leaves_course_without_offering_or_starting(browser):
    fixture = TrialPage()
    page = fixture.open(browser)
    fixture.status_owner = 99
    page.evaluate("App.goPay('profile_subscription')")
    page.wait_for_url(ORIGIN + "/iphone-pwa")
    assert fixture.starts == [] and fixture.onboarding_writes == []


def test_account_switch_between_parent_check_and_trial_frame_does_not_offer_another_account(browser):
    fixture = TrialPage()
    page = fixture.open(browser)
    fixture.child_owner = 99
    page.evaluate("App.goPay('profile_subscription')")
    page.wait_for_url(ORIGIN + "/iphone-pwa")
    assert fixture.starts == [] and fixture.onboarding_writes == []


def test_failed_activation_keeps_offer_retry_and_never_shows_success(browser):
    fixture = TrialPage(standalone=True)
    fixture.start_fail = True
    page = fixture.open(browser)
    frame = trial_frame(page)
    for _ in range(4):
        frame.locator("#footer .cta").first.click()
    frame.locator(".li-remote-error").wait_for()
    assert frame.locator(".done-hero").count() == 0
    assert len(fixture.starts) == 1
    assert page.evaluate("MAP.user.state") == "FREE"
    page.evaluate("NavBack.goBack()")
    assert page.locator("#pwa-checkout-layer").count() == 0


def test_paid_renewal_does_not_depend_on_trial_status_availability(browser):
    fixture = TrialPage()
    fixture.data["user"].update(plan="pro", state="PRO_ACTIVE", is_paid=True)
    fixture.status_fail = True
    page = fixture.open(browser)
    page.evaluate("App.goPay('profile_renewal')")
    page.locator('#pwa-checkout-layer iframe[src*="/iphone-pwa/checkout?"]').wait_for()
    assert fixture.status_reads == [] and fixture.starts == []


def test_trial_write_cannot_be_dismissed_before_its_result(browser):
    fixture = TrialPage(standalone=True)
    fixture.hold_start = True
    page = fixture.open(browser)
    frame = trial_frame(page)
    for _ in range(4):
        frame.locator("#footer .cta").first.click()
    page.wait_for_timeout(30)
    assert len(fixture.start_held) == 1
    page.evaluate("NavBack.goBack()")
    assert page.locator("#pwa-checkout-layer").count() == 1
    fixture.start_held.pop().fulfill(status=503, json={"ok": False})
    frame.locator(".li-remote-error").wait_for()
    assert frame.locator(".done-hero").count() == 0
    page.evaluate("NavBack.goBack()")
    assert page.locator("#pwa-checkout-layer").count() == 0
    assert page.evaluate("MAP.user.state") == "FREE"


def test_fast_map_waits_for_late_trial_bridge_before_boot_intents(browser):
    fixture = TrialPage(standalone=True)
    fixture.hold_bridge = True
    fixture.data["foundation"].update(required=True, status="required")
    page = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    page.add_init_script("Object.defineProperty(navigator,'standalone',{get:()=>true})")
    page.route("**/*", fixture.serve)
    page.goto(ORIGIN + "/iphone-pwa/course?lang=uz", wait_until="commit")
    page.wait_for_function("window.MAP && MAP.authenticated")
    page.wait_for_function("document.readyState==='loading'")
    page.wait_for_timeout(100)
    assert fixture.bridge_held
    # A single pending load owns the boot continuation; mounting the real
    # bridge later must not run app-open intents beneath the trial layer.
    page.evaluate("window.bootIntentCount=0;window.bootIntentStacks=[];window.startFoundationFromMap=function(){bootIntentCount++;bootIntentStacks.push(new Error().stack);return true};void 0")
    fixture.hold_bridge = False
    fixture.bridge_held.pop().fulfill(content_type="application/javascript", path=str(STATIC / "course_v3_data/iphone-pwa-inline-pro-bridge.js"))
    frame = trial_frame(page)
    assert page.evaluate("bootIntentCount") == 0, page.evaluate("bootIntentStacks")
    frame.locator(".li-trial-close").click()
    page.wait_for_function("bootIntentCount===1")
    assert len(fixture.status_reads) == 2  # parent check + child recheck
    assert fixture.starts == [] and fixture.onboarding_writes == []
    page.close()
