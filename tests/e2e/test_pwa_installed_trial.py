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
    def __init__(self, language="uz", *, eligible=True, standalone=False, hsk30=False, goals=None, daily_minutes=20, streak_target_days=14):
        super().__init__(lang=language)
        self.installed = standalone
        self.saved_profile = {"goal": (goals or ["hsk_exam"])[0], "goals": goals or ["hsk_exam"],
                              "daily_minutes": daily_minutes, "preferred_focus": "listening",
                              "streak_target_days": streak_target_days}
        self.hold_runtime = False
        self.runtime_held = []
        self.trial = {"eligible": eligible, "active": False, "ends_at": None, "days": 7}
        self.data["study_setup"] = {"goal": "hsk_exam", "goal_chosen": True, "daily_minutes": 20,
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
        if path.endswith("/li-onboarding-runtime.js") and self.hold_runtime:
            self.runtime_held.append(route)
        elif path.endswith("/iphone-pwa-inline-pro-bridge.js") and self.hold_bridge:
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
                "ok": True, "saved": True, "level": self.data["level"], "profile": self.saved_profile,
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

    def open(self, browser, width=390, *, wait_until="networkidle"):
        context = browser.new_context(viewport={"width": width, "height": 844},
                                      reduced_motion="reduce", is_mobile=True)
        page = context.new_page()
        if self.installed:
            page.add_init_script("Object.defineProperty(navigator,'standalone',{get:()=>true})")
        page.set_default_timeout(12000)
        page.route("**/*", self.serve)
        page.goto(ORIGIN + "/iphone-pwa/course?lang=" + self.lang, wait_until=wait_until)
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
@pytest.mark.parametrize("chosen", [True, False, None])
def test_profile_goal_requires_a_verified_real_choice(browser, language, chosen):
    fixture = TrialPage(language)
    if chosen is None:
        fixture.data["study_setup"].pop("goal_chosen")
    else:
        fixture.data["study_setup"]["goal_chosen"] = chosen
    page = fixture.open(browser, 320)
    profile(page)
    goal = page.locator("#s-profile .profile-goal-row")
    assert goal.count() == (1 if chosen is True else 0)
    if chosen is True:
        assert goal.inner_text().strip() == page.evaluate("studySetupT().goals.hsk_exam")
    assert not fixture.onboarding_writes and not fixture.starts


@pytest.mark.parametrize("language,width,theme", [
    ("uz", 320, "light"), ("ru", 390, "dark"), ("tj", 430, "light"),
    ("uz", 430, "dark"), ("ru", 320, "light"), ("tj", 390, "dark"),
])
def test_profile_one_hierarchy_preserves_all_verified_access_states(browser, language, width, theme):
    """The real server-map fixture changes presentation, never entitlement logic."""
    for state in ("FREE", "EXPIRED", "BLOCKED", "TEMP_ACCESS", "TRIAL_ACTIVE", "PRO_ACTIVE"):
        fixture = TrialPage(language)
        fixture.data["user"].update(state=state, is_paid=state.endswith("ACTIVE") or state == "TEMP_ACCESS")
        fixture.data["progress"].update(completed=8, streak=7)
        page = fixture.open(browser, width)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_viewport_size({"width": width, "height": 568 if width == 320 else 932})
        page.evaluate("theme=>document.documentElement.dataset.hskTheme=theme", theme)
        profile(page)
        assert page.locator("#s-profile .profile-pro-link").count() == 0
        assert page.locator("#s-profile .profile-compact-ach .arow").count() == 1
        assert page.locator("#s-profile .profile-compact-ach small").inner_text() == "8 / 100"
        assert page.locator("#s-profile .p45-profile-streak-link").inner_text().strip() == "7"
        expected = page.evaluate("""state=>state==='PRO_ACTIVE'?'HSK AI Pro':
          state==='TRIAL_ACTIVE'?profileCopy().trial:state==='TEMP_ACCESS'?
          ({uz:'Vaqtinchalik ruxsat',ru:'Временный доступ',tj:'Дастрасии муваққатӣ'})[LANG]:profileCopy().free""", state)
        assert page.locator("#s-profile .profile-access-badge").inner_text().strip() == expected
        selectors = [".profile-head", ".phero", ".profile-accuracy", ".p45-profile-streak-heading",
                     ".card2", ".profile-compact-ach", "#hsk-profile-promo-root", ".profile-friends-link"]
        boxes = [page.locator("#s-profile " + selector).bounding_box() for selector in selectors]
        assert all(a["y"] + a["height"] <= b["y"] + 1 for a, b in zip(boxes, boxes[1:]))
        assert page.locator("#s-profile").evaluate("el=>el.scrollWidth<=el.clientWidth+1")
        buttons = page.locator("#s-profile .profile-friends-link, #hsk-profile-promo-root button")
        for button in buttons.all():
            box = button.bounding_box()
            assert box and box["width"] >= 44 and box["height"] >= 44
        friends = page.locator("#s-profile .profile-friends-link")
        friends.scroll_into_view_if_needed()
        page.evaluate("window.scrollTo(0,document.scrollingElement.scrollHeight)")
        assert friends.bounding_box()["y"] + friends.bounding_box()["height"] <= page.locator("#nav").bounding_box()["y"]
        assert not fixture.starts and not fixture.onboarding_writes and not errors
        directory = os.getenv("HSK_PROFILE_REVIEW_DIR")
        if directory and state in ("FREE", "PRO_ACTIVE"):
            Path(directory).mkdir(parents=True, exist_ok=True)
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_function("window.scrollY<1")
            page.screenshot(path=str(Path(directory) / f'{os.getenv("PWA_E2E_ENGINE", "chromium")}-{width}-{language}-{theme}-{state}.png'), full_page=True)
        page.context.close()


@pytest.mark.parametrize("language", ["uz", "ru", "tj"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_profile_large_text_keeps_pro_terms_controls_and_last_item_reachable(browser, language, theme):
    for state in ("FREE", "TEMP_ACCESS", "TRIAL_ACTIVE", "PRO_ACTIVE"):
        fixture = TrialPage(language)
        fixture.data["user"].update(state=state, is_paid=state != "FREE")
        page = fixture.open(browser, 320)
        page.set_viewport_size({"width": 320, "height": 568})
        page.evaluate("t=>document.documentElement.dataset.hskTheme=t", theme)
        profile(page)
        page.evaluate("PROF.display_name=\'Жуда узун исм / Очень длинное имя / Номи хеле дароз\';renderProfile();HskProfileCarousel.pause()")
        page.evaluate("""() => {
          const root=document.getElementById('s-profile'), rules=[];
          for(const el of root.querySelectorAll('strong,small,p,.ah span,.profile-access-badge,.profile-goal-row .goal,.hp-promo-action,.profile-friends-link span')){
            rules.push([el,parseFloat(getComputedStyle(el).fontSize)*2]);
          }
          for(const [el,size] of rules)el.style.setProperty('font-size',size+'px','important');
        }""")
        assert page.locator("#s-profile").evaluate("el=>el.scrollWidth<=el.clientWidth+1")
        action = page.locator('.hp-promo-slide[data-promo-kind="pro"] .hp-promo-action')
        action.scroll_into_view_if_needed()
        assert action.evaluate("el=>el.scrollWidth<=el.clientWidth+1 && el.scrollHeight<=el.clientHeight+1")
        # Essential Pro status/terms must not be silently line-clamped.
        assert page.locator('.hp-promo-slide.hp-promo-pro .hp-promo-copy p').evaluate("el=>el.scrollHeight<=el.clientHeight+1")
        friends = page.locator("#s-profile .profile-friends-link")
        friends.scroll_into_view_if_needed()
        page.evaluate("window.scrollTo(0,document.scrollingElement.scrollHeight)")
        box = friends.bounding_box()
        assert box["y"] + box["height"] <= page.locator("#nav").bounding_box()["y"]
        assert page.locator("#s-profile .profile-compact-ach small").is_visible()
        assert not fixture.starts
        page.context.close()


def test_profile_carousel_failure_has_one_trial_first_fallback_and_late_mount_stays_in_slot(browser):
    from tests.pwa_layout_geometry import capture_geometry, assert_reserved_layout

    fixture = TrialPage("ru")
    original = fixture.serve
    def serve(route):
        if urlsplit(route.request.url).path.endswith("/profile-carousel.js"):
            route.fulfill(content_type="application/javascript", body="")
        else:
            original(route)
    fixture.serve = serve
    page = fixture.open(browser, 430)
    page.locator('#nav [data-s="profile"]').click()
    fallback = page.locator("#hsk-profile-promo-root .profile-pro-link")
    fallback.wait_for()
    anchors = {"pro": "#hsk-profile-promo-root", "friends": "#s-profile .profile-friends-link"}
    before = capture_geometry(page, anchors)
    fallback.click()
    trial_frame(page)
    assert not fixture.starts
    page.keyboard.press("Escape")
    page.locator("#pwa-checkout-layer").wait_for(state="detached")
    # Execute the real optional bundle after failure, without replacing Profile.
    page.add_script_tag(content=(STATIC / "course_v3_data/profile-carousel.js").read_text())
    page.evaluate("HskProfileCarousel.pause()")
    assert page.locator("#s-profile .profile-pro-link").count() == 0
    assert page.locator('.hp-promo-slide[data-promo-kind="pro"]').count() == 1
    assert_reserved_layout(before, capture_geometry(page, anchors))


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
        indicator=frame.get_by_role("progressbar", name="HSK AI Pro")
        assert indicator.get_attribute("aria-valuenow") == state[-1]
        assert indicator.get_attribute("aria-valuemax") == "4"
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
    assert frame.locator("#footer .cta").count() == 1
    assert page.locator('.hp-promo-slide[data-promo-kind="apps"]').count() == 0
    frame.locator(".li-trial-close").click()
    assert page.locator("#pwa-checkout-layer").count() == 0
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
    page.keyboard.press("Escape")
    assert page.locator("#pwa-checkout-layer").count() == 1
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


def test_confirmed_trial_resumes_required_foundation_after_the_access_map_refresh(browser):
    fixture = TrialPage(standalone=True)
    fixture.data["foundation"].update(required=True, status="required")
    page = fixture.open(browser)
    frame = trial_frame(page)
    page.evaluate("window.foundationResumes=[];window.startFoundationFromMap=function(){foundationResumes.push(MAP.user.state);return true};void 0")
    for _ in range(4):
        frame.locator("#footer .cta").first.click()
    frame.locator(".done-hero").wait_for()
    frame.locator("#footer .cta").first.click()
    page.wait_for_function("MAP.user.state==='TRIAL_ACTIVE'")
    page.wait_for_function("foundationResumes.length===1", timeout=3000)
    assert page.evaluate("foundationResumes") == ["TRIAL_ACTIVE"]
    assert len(fixture.starts) == 1 and fixture.onboarding_writes == []


def release_trial_status(fixture):
    fixture.hold_status = False
    for route in fixture.status_held:
        route.fulfill(headers={"X-HSK-PWA-User-ID": str(fixture.status_owner)},
                      json={"ok": True, "trial": fixture.trial})
    fixture.status_held.clear()


def test_late_installed_eligibility_does_not_interrupt_a_new_profile_intent(browser):
    fixture = TrialPage(standalone=True)
    fixture.hold_status = True
    fixture.data["foundation"].update(required=True, status="required")
    page = fixture.open(browser, wait_until="domcontentloaded")
    page.wait_for_function("TRIAL_PROMISE!==null")
    page.evaluate("window.foundationResumes=0;window.startFoundationFromMap=function(){foundationResumes++;return true};void 0")
    profile(page)
    assert fixture.status_held
    release_trial_status(fixture)
    page.wait_for_function("TRIAL_PROMISE===null")
    assert page.evaluate("SCREEN") == "profile"
    assert page.evaluate("foundationResumes") == 0
    assert page.locator("#pwa-checkout-layer").count() == 0
    page.evaluate("App.goPay('profile_subscription');void 0")
    trial_frame(page)
    assert fixture.starts == [] and fixture.onboarding_writes == []


def test_late_profile_purchase_read_preserves_a_new_course_sheet(browser):
    fixture = TrialPage()
    page = fixture.open(browser)
    profile(page)
    fixture.hold_status = True
    page.evaluate("App.goPay('profile_subscription');void 0")
    page.wait_for_function("TRIAL_PROMISE!==null")
    page.evaluate("App.show('course');App.openSheet('<p id=learner-current-sheet>Current lesson choice</p>');void 0")
    assert fixture.status_held
    release_trial_status(fixture)
    page.wait_for_function("TRIAL_PROMISE===null")
    assert page.locator("#sheet.on #learner-current-sheet").is_visible()
    assert page.locator("#pwa-checkout-layer").count() == 0
    assert fixture.starts == [] and fixture.onboarding_writes == []


@pytest.mark.parametrize("standalone", [False, True])
def test_trial_keyboard_focus_is_contained_and_escape_restores_the_parent(browser, standalone):
    fixture = TrialPage(standalone=standalone)
    page = fixture.open(browser)
    if not standalone:
        profile(page)
        page.locator('.hp-promo-slide[data-promo-kind="pro"] .hp-promo-action').click()
    frame = trial_frame(page)
    close = frame.locator(".li-trial-close")
    assert close.evaluate("el=>el===document.activeElement")
    start = frame.locator("#footer .cta")
    start.focus()
    page.keyboard.press("Tab")
    assert close.evaluate("el=>el===document.activeElement")
    page.keyboard.press("Shift+Tab")
    assert start.evaluate("el=>el===document.activeElement")
    frame.locator("#footer .cta").first.click()
    assert frame.get_by_role("progressbar", name="HSK AI Pro").get_attribute("aria-valuetext") == "1 / 4"
    page.evaluate("window.mapBeforeKeyboardClose=MAP")
    page.keyboard.press("Escape")
    assert page.locator("#pwa-checkout-layer").count() == 0
    page.wait_for_function("MAP!==mapBeforeKeyboardClose")
    assert not page.locator(".wrap").evaluate("el=>el.inert")
    if not standalone:
        assert page.locator('.hp-promo-slide[data-promo-kind="pro"] .hp-promo-action').evaluate("el=>el===document.activeElement")
    assert fixture.starts == [] and fixture.onboarding_writes == []


def test_profile_trial_confirmation_restores_focus_after_verified_access_refresh(browser):
    fixture = TrialPage()
    page = fixture.open(browser)
    profile(page)
    page.locator('.hp-promo-slide[data-promo-kind="pro"] .hp-promo-action').click()
    frame = trial_frame(page)
    for _ in range(4):
        frame.locator("#footer .cta").first.click()
    frame.locator(".done-hero").wait_for()
    frame.locator("#footer .cta").first.click()
    page.wait_for_function("MAP.user.state==='TRIAL_ACTIVE'")
    page.wait_for_function("document.activeElement.matches('.hp-promo-action')")
    assert page.evaluate("SCREEN") == "profile"
    assert len(fixture.starts) == 1 and fixture.onboarding_writes == []


@pytest.mark.parametrize("language", ["uz", "ru", "tj"])
@pytest.mark.parametrize("goal,width,minutes,days", [
    ("hsk_exam", 320, 5, 7), ("travel", 390, 10, 14),
    ("work_china", 430, 15, 30), ("study_china", 320, 20, 50),
    ("daily_communication", 390, 30, 14),
])
def test_trial_has_one_free_action_persistent_brand_and_saved_personal_plan(browser, language, goal, width, minutes, days):
    from scripts.i18n_build_li_onboarding import read_sources
    copy = read_sources()[language]
    fixture = TrialPage(language, standalone=True, goals=[goal], daily_minutes=minutes, streak_target_days=days)
    page = fixture.open(browser, width)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    frame = trial_frame(page)
    assert frame.locator("#footer .cta").count() == 1
    assert frame.locator("#footer .cta").inner_text() == copy["trialOffer.start"]
    assert page.locator('meta[name="theme-color"]').get_attribute("content") == "#211D17"
    assert page.locator("#pwa-checkout-layer").evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(33, 29, 23)"
    for step in ("trialIntro", "trial1", "trial2", "trial3", "trialDone"):
        if step != "trialIntro":
            frame.locator("#footer .cta").first.click()
            page.wait_for_function("step => document.querySelector('#pwa-checkout-layer iframe').contentWindow.screen===step", arg=step)
        assert frame.get_by_role("heading", name="HSK AI PRO", exact=True).is_visible()
        assert frame.locator(".wrap").evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(33, 29, 23)"
        assert frame.locator("#stage").evaluate("el => el.scrollWidth<=el.clientWidth+1")
        if step in ("trial1", "trial2", "trial3"):
            assert frame.locator(".trial h2").inner_text() == copy[f"proGoal.{goal}.title"]
        if step == "trial2":
            assert copy["trialOffer.daily"].replace("{minutes}", str(minutes)) in frame.locator(".trial p").inner_text()
        if step == "trial3":
            assert copy["trialOffer.streak"].replace("{days}", str(days)) in frame.locator(".trial p").inner_text()
            assert not fixture.starts
        if step == "trialDone":
            assert frame.locator(".trial h2").inner_text() == copy["trialOffer.activated"]
            assert frame.locator(".trial p").count() == 0
            assert frame.locator("#footer .cta").inner_text() == copy["trialOffer.begin"]
            assert len(fixture.starts) == 1
    directory = os.getenv("HSK_TRIAL_REVIEW_DIR")
    if directory:
        Path(directory).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(directory) / f"{os.getenv('PWA_E2E_ENGINE', 'chromium')}-{width}-{language}-{goal}-done.png"))
    frame.locator("#footer .cta").click()
    page.wait_for_function("!document.querySelector('#pwa-checkout-layer')")
    assert page.locator('meta[name="theme-color"]').get_attribute("content") == "#FDF9F0"
    assert fixture.onboarding_writes == [] and errors == []


def test_trial_slow_runtime_does_not_flash_account_or_onboarding_screens(browser):
    fixture = TrialPage(standalone=True)
    fixture.hold_runtime = True
    page = fixture.open(browser, wait_until="domcontentloaded")
    page.wait_for_function("() => !!document.querySelector('#pwa-checkout-layer iframe')?.contentDocument?.documentElement?.classList.contains('li-trial-pending')")
    frame = page.frame_locator("#pwa-checkout-layer iframe")
    assert frame.locator(".wrap").evaluate("el => getComputedStyle(el).visibility") == "hidden"
    assert frame.locator("body").evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(33, 29, 23)"
    page.wait_for_function("() => !!document.querySelector('#pwa-checkout-layer iframe')?.contentDocument?.querySelector('script[src*=li-onboarding-runtime]')")
    assert len(fixture.runtime_held) == 1
    fixture.hold_runtime = False
    fixture.runtime_held.pop().fulfill(content_type="application/javascript", path=str(STATIC / "course_v3_data/li-onboarding-runtime.js"))
    trial_frame(page)
    assert frame.locator(".li-pro-welcome").is_visible()
    assert frame.locator("#footer .cta").count() == 1
    assert fixture.starts == [] and fixture.onboarding_writes == []


def test_cached_profile_trial_uses_existing_limit_panda_and_restores_status_bar(browser):
    """Cached owner-specific eligibility must avoid a second parent RTT.

    The child still performs its own verified session and status read; SVG is
    the same function that paints the existing Pro limit modal.
    """
    fixture = TrialPage("ru", standalone=False)
    page = fixture.open(browser, 390)
    profile(page)
    page.wait_for_function("TRIAL_LOADED && TRIAL_STATE?.eligible === true")
    before = len(fixture.status_reads)
    status_bar = page.locator('meta[name="apple-mobile-web-app-status-bar-style"]')
    old_style = status_bar.get_attribute("content")
    page.locator('.hp-promo-slide[data-promo-kind="pro"] .hp-promo-action').click()
    frame = trial_frame(page)
    assert len(fixture.status_reads) == before + 1  # child only, no redundant parent fetch
    assert frame.locator('.li-pro-welcome-panda svg.hip-pd-char').count() == 1
    assert frame.locator('.li-pro-welcome-panda svg text').text_content() == "PRO"
    assert frame.locator(".li-pro-welcome-panda").evaluate(
        "el => el.innerHTML === parent.HSKPwaInlinePro.trialPandaSvg()")
    assert status_bar.get_attribute("content") == "black-translucent"
    assert page.locator('meta[name="theme-color"]').get_attribute("content") == "#211D17"
    assert frame.locator("body").evaluate(
        "el => getComputedStyle(el).backgroundColor") == "rgb(33, 29, 23)"
    page.keyboard.press("Escape")
    page.locator("#pwa-checkout-layer").wait_for(state="detached")
    assert status_bar.get_attribute("content") == old_style
    assert page.locator('meta[name="theme-color"]').get_attribute("content") == "#FDF9F0"
    assert fixture.starts == [] and fixture.onboarding_writes == []
    page.context.close()


def test_cached_parent_trial_never_grants_or_displays_an_eligibility_reversal(browser):
    """A cached valid presentation hint cannot override the child's fresh status."""
    fixture = TrialPage("ru", standalone=False)
    page = fixture.open(browser)
    profile(page)
    page.wait_for_function("TRIAL_LOADED && TRIAL_STATE?.eligible === true")
    fixture.trial["eligible"] = False  # server state changed after the cached parent read
    before = len(fixture.status_reads)
    page.locator('.hp-promo-slide[data-promo-kind="pro"] .hp-promo-action').click()
    page.wait_for_function("() => !document.getElementById('pwa-checkout-layer') && TRIAL_PROMISE===null")
    assert len(fixture.status_reads) == before + 1  # child revalidated the real server
    assert fixture.starts == [] and fixture.onboarding_writes == []
    assert page.evaluate("MAP.user.state") == "FREE"
    page.context.close()
