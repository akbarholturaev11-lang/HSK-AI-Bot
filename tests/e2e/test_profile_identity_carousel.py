"""Profile linking cards follow verified methods and retain real swipe motion."""

import re

import pytest

from test_miniapp_smoke import (
    app_url,
    expect,
    json_response,
    mock_course_map,
    mock_learning_audio,
    mock_price_preview,
    mock_telegram_ready,
    page,
)


ROOT = "#hsk-profile-promo-root"
SLIDES = ROOT + " .hp-promo-slide"
START = "**/api/v3/native-auth/identities/link/start"
STATUS = "**/api/v3/native-auth/identities/link/status"


def _open_profile(page, *, providers=None, identities=None, provider_payload=None,
                  identity_payload=None, language="uz"):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text)
            if message.type == "error" else None)
    # Optional profile services are outside this UI contract. Avoid real network
    # calls while preserving the real map, Telegram SDK stub and auth headers.
    page.route("**/api/**", lambda route: json_response(route, {"ok": True}))
    mock_price_preview(page)
    mock_telegram_ready(page, init_data="query_id=profile-link-regression")
    mock_course_map(page, language=language)
    mock_learning_audio(page)
    # Offline word bundles are generated/ignored assets in this checkout and
    # unrelated to profile linking. Keep their script requests deterministic.
    for name in ("index", "client"):
        page.route(f"**/audio/words/{name}.js*", lambda route: route.fulfill(
            status=200, content_type="application/javascript", body=""))
    page.route("**/api/v3/native-auth/providers*", lambda route: json_response(
        route, provider_payload if provider_payload is not None else {
            "ok": True, "providers": providers if providers is not None else ["google", "apple"],
        }))
    page.route("**/api/v3/native-auth/identities", lambda route: json_response(
        route, identity_payload if identity_payload is not None else {
            "ok": True, "telegram_linked": True,
            "identities": identities if identities is not None else [],
        }))
    page.add_init_script("""
      localStorage.setItem('hsk_v3_onb', '1');
      localStorage.setItem('hsk_v3_level', 'hsk1');
      localStorage.setItem('hsk_v3_tour', '1');
      localStorage.setItem('hsk_v3_launch_seen', '1');
    """)
    page.goto(app_url(f"/course-v3.html?lang={language}&level=hsk1&onboarded=1"),
              wait_until="networkidle")
    page.locator('#nav button[data-s="profile"]').click()
    page.wait_for_load_state("networkidle")
    expect(page.locator(ROOT)).to_be_visible()
    page.evaluate("HskProfileCarousel.pause()")
    return errors


def _select(page, kind):
    # A late profile-detail reply can replace the whole root between locator
    # resolution and Playwright's stability check. Query and scroll atomically.
    page.evaluate("""async kind => {
      document.getElementById('hsk-profile-promo-root').scrollIntoView({
        block:'center', inline:'nearest', behavior:'instant'
      });
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      HskProfileCarousel.select(kind); HskProfileCarousel.pause();
    }""", kind)
    slide = page.locator(f'{SLIDES}[data-promo-kind="{kind}"]')
    expect(slide).to_be_in_viewport(ratio=0.95)
    return slide


def _start_payload(*, provider="google", **changes):
    payload = {
        "ok": True,
        "authorize_url": ("https://appleid.apple.com/auth/authorize?state=fixture-state"
                          if provider == "apple" else
                          "https://accounts.google.com/o/oauth2/v2/auth?state=fixture-state"),
        "link_request_id": "d42b6aa3-52a4-4aa4-9a3b-8ed13d6dbbe3",
        "polling_secret": "fixture-polling-secret-for-profile-only",
        "expires_in": 600,
    }
    payload.update(changes)
    return payload


@pytest.mark.parametrize("providers,linked,expected", [
    (["google", "apple"], [], ["link-google", "link-apple"]),
    (["google", "apple"], ["google"], ["link-apple"]),
    (["google", "apple"], ["apple"], ["link-google"]),
    (["google", "apple"], ["google", "apple"], []),
    (["apple"], [], ["link-apple"]),
    ([], [], []),
    (["google", "google", "telegram", "unknown"], [], ["link-google"]),
])
def test_only_configured_unlinked_providers_get_separate_cards(page, providers, linked, expected):
    errors = _open_profile(page, providers=providers, identities=[
        {"id": f"identity-{provider}", "provider": provider, "email_masked": "a***@example.test"}
        for provider in linked
    ])
    kinds = page.locator(SLIDES).evaluate_all("nodes => nodes.map(node => node.dataset.promoKind)")
    assert kinds == ["apps", "hsk30", "pro"] + expected
    assert "link-telegram" not in kinds  # The Mini App already proves Telegram.
    expect(page.locator(ROOT + ' [data-promo-dot]')).to_have_count(len(kinds))
    expect(page.locator(ROOT + ' [data-promo-dot="1"]')).to_have_attribute("aria-current", "true")
    _select(page, "hsk30")
    for kind in expected:
        card = _select(page, kind)
        expect(card.locator(".hp-promo-action")).to_be_enabled()
        expect(card).to_contain_text("Google" if kind == "link-google" else "Apple")
    assert not errors


def test_link_cards_wait_until_both_provider_and_identity_replies_arrive(page):
    page.add_init_script("""(() => {
      const fetchOriginal = window.fetch;
      window.fetch = function(url, options) {
        if (String(url) === '/api/v3/native-auth/identities') {
          return new Promise(resolve => {
            window.__resumeIdentityReply = () => resolve(new Response(JSON.stringify({
              ok:true, telegram_linked:true, identities:[]
            }), {status:200, headers:{'Content-Type':'application/json'}}));
          });
        }
        return fetchOriginal.call(this, url, options);
      };
    })();""")
    errors = _open_profile(page)
    expect(page.locator(SLIDES)).to_have_count(3)
    expect(page.locator(SLIDES + '[data-promo-kind^="link-"]')).to_have_count(0)
    page.evaluate("window.__resumeIdentityReply()")
    expect(page.locator(SLIDES)).to_have_count(5)
    assert not errors


@pytest.mark.parametrize("which,payload", [
    ("identities", {"ok": False, "error": "temporarily_unavailable"}),
    ("identities", {"ok": True, "identities": None}),
    ("providers", {"ok": False, "providers": ["google", "apple"]}),
])
def test_incomplete_identity_discovery_does_not_offer_linking(page, which, payload):
    kwargs = {"identity_payload" if which == "identities" else "provider_payload": payload}
    errors = _open_profile(page, **kwargs)
    expect(page.locator(SLIDES + '[data-promo-kind^="link-"]')).to_have_count(0)
    expect(page.locator(SLIDES)).to_have_count(3)
    assert not errors


@pytest.mark.parametrize("language,title,action", [
    ("uz", "Google’ni ulash", "Ulash"),
    ("ru", "Подключить Google", "Подключить"),
    ("tj", "Пайваст кардани Google", "Пайваст кардан"),
])
def test_link_cards_are_localized_and_fit_narrow_mobile_viewports(page, language, title, action):
    page.set_viewport_size({"width": 320, "height": 600})
    errors = _open_profile(page, language=language)
    card = _select(page, "link-google")
    expect(card.locator("strong")).to_have_text(title)
    button = card.locator(".hp-promo-action")
    expect(button).to_have_text(action)
    assert card.evaluate("node => node.scrollWidth <= node.clientWidth + 1")
    assert card.locator("strong").evaluate("node => node.scrollWidth <= node.clientWidth + 1")
    button_box = button.bounding_box()
    dots_box = page.locator(ROOT + " > .hp-promo-dots").bounding_box()
    assert button_box and dots_box
    assert button_box["x"] + button_box["width"] <= dots_box["x"] - 4
    assert not errors


@pytest.mark.parametrize("provider", ["google", "apple"])
def test_link_card_uses_existing_authenticated_link_flow_once_while_pending(page, provider):
    starts, status_calls, requests = [], [], []
    page.on("request", lambda request: requests.append(request.url))
    errors = _open_profile(page)
    page.evaluate("""() => {window.__openedLinks = [];
        tg.openLink = url => window.__openedLinks.push(url);}""")

    def start(route):
        starts.append({"body": route.request.post_data_json,
                       "headers": route.request.all_headers()})
        json_response(route, _start_payload(provider=provider))

    page.route(START, start)
    page.route(STATUS, lambda route: (status_calls.append(route.request.post_data_json),
                                     json_response(route, {"ok": True, "status": "pending"}))[-1])
    _select(page, "link-" + provider).locator(".hp-promo-action").click()
    page.evaluate("App.connectIdentity('google'); App.connectIdentity('apple')")
    page.wait_for_function("window.__openedLinks.length === 1")
    expect(page.locator(SLIDES + f'[data-promo-kind="link-{provider}"] .hp-promo-action')).to_be_disabled()
    assert len(starts) == 1
    assert starts[0]["body"] == {
        "platform": "miniapp", "app_version": "1.0.0",
        "provider": provider, "mode": "browser_redirect",
    }
    assert starts[0]["headers"]["x-telegram-init-data"] == "query_id=profile-link-regression"
    page.wait_for_function("provider => SIGNIN_STATE.busy === provider", arg=provider)
    page.wait_for_timeout(2100)
    assert status_calls and status_calls[0] == {
        "link_request_id": _start_payload()["link_request_id"],
        "polling_secret": _start_payload()["polling_secret"],
    }
    assert not any(re.search(r"/(oauth/start|oauth/assert|token|exchange)(?:\?|$)", url) for url in requests)
    assert not errors


def test_link_success_reloads_identities_and_removes_only_the_connected_card(page):
    errors = _open_profile(page)
    identity_reads = []
    page.route("**/api/v3/native-auth/identities", lambda route: (
        identity_reads.append(route.request.url), json_response(route, {
            "ok": True, "telegram_linked": True,
            "identities": [{"id": "google-linked", "provider": "google", "email_masked": "a***@example.test"}],
        }))[-1])
    page.route(START, lambda route: json_response(route, _start_payload()))
    page.route(STATUS, lambda route: json_response(route, {"ok": True, "status": "linked"}))
    _select(page, "link-google").locator(".hp-promo-action").click()
    expect(page.locator(SLIDES + '[data-promo-kind="link-google"]')).to_have_count(0, timeout=7000)
    expect(page.locator(SLIDES + '[data-promo-kind="link-apple"]')).to_have_count(1)
    assert len(identity_reads) == 1
    assert page.evaluate("SIGNIN_STATE.busy") == ""
    assert not errors


def test_pending_link_pauses_away_from_profile_and_resumes_the_same_proof(page):
    errors = _open_profile(page)
    starts, polls = [], []
    page.route(START, lambda route: (starts.append(route.request.post_data_json),
                                    json_response(route, _start_payload()))[-1])
    page.route(STATUS, lambda route: (polls.append(route.request.post_data_json),
                                     json_response(route, {"ok": True, "status": "failed"}))[-1])
    _select(page, "link-google").locator(".hp-promo-action").click()
    page.wait_for_function("() => SIGNIN_PENDING !== null")
    page.locator('#nav button[data-s="course"]').click()
    page.wait_for_timeout(2200)
    assert polls == []
    page.locator('#nav button[data-s="profile"]').click()
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => SIGNIN_STATE.busy === '' && !!SIGNIN_STATE.note", timeout=7000)
    assert len(starts) == 1
    assert polls == [{"link_request_id": _start_payload()["link_request_id"],
                      "polling_secret": _start_payload()["polling_secret"]}]
    expect(_select(page, "link-google").locator(".hp-promo-action")).to_be_enabled()
    assert not errors


def test_late_start_response_after_leaving_profile_is_ignored_and_retry_is_available(page):
    errors = _open_profile(page)
    page.evaluate("""() => {window.__openedLinks = [];
        tg.openLink = url => window.__openedLinks.push(url);}""")
    starts, polls = [], []
    page.route(START, lambda route: starts.append(route))
    page.route(STATUS, lambda route: (polls.append(route.request.post_data_json),
                                     json_response(route, {"ok": True, "status": "expired"}))[-1])
    _select(page, "link-google").locator(".hp-promo-action").click()
    page.locator('#nav button[data-s="course"]').click()
    assert len(starts) == 1
    json_response(starts[0], _start_payload())
    page.wait_for_timeout(2200)
    assert polls == []
    assert page.evaluate("SIGNIN_PENDING") is None
    assert page.evaluate("SIGNIN_STATE.busy") == ""
    assert page.evaluate("window.__openedLinks") == []
    page.locator('#nav button[data-s="profile"]').click()
    page.wait_for_load_state("networkidle")
    card = _select(page, "link-google")
    expect(card.locator(".hp-promo-action")).to_be_enabled()
    retry_id = "d42b6aa3-52a4-4aa4-9a3b-8ed13d6dbbe4"
    retries = []
    page.route(START, lambda route: (retries.append(route.request.post_data_json),
                                    json_response(route, _start_payload(link_request_id=retry_id)))[-1])
    card.locator(".hp-promo-action").click()
    page.wait_for_function("id => SIGNIN_PENDING && SIGNIN_PENDING.id === id", arg=retry_id)
    assert len(starts) == len(retries) == 1
    assert page.evaluate("window.__openedLinks.length") == 1
    assert polls == []
    assert not errors


def test_older_pending_status_cannot_restart_a_proof_after_resumed_poll_links_it(page):
    errors = _open_profile(page)
    first_status = []
    polls = []
    page.route(START, lambda route: json_response(route, _start_payload()))

    def status(route):
        polls.append(route.request.post_data_json)
        if len(polls) == 1:
            first_status.append(route)
            return
        json_response(route, {"ok": True, "status": "linked" if len(polls) == 2 else "pending"})

    page.route(STATUS, status)
    with page.expect_request("**/api/v3/native-auth/identities/link/status"):
        _select(page, "link-google").locator(".hp-promo-action").click()
    page.wait_for_timeout(50)
    assert len(first_status) == 1
    page.route("**/api/v3/native-auth/identities", lambda route: json_response(route, {
        "ok": True, "telegram_linked": True,
        "identities": [{"id": "google-linked", "provider": "google"}],
    }))
    page.locator('#nav button[data-s="course"]').click()
    page.locator('#nav button[data-s="profile"]').click()
    # The first HTTP response stays in flight while the resumed poll completes.
    expect(page.locator(SLIDES + '[data-promo-kind="link-google"]')).to_have_count(0, timeout=7000)
    assert len(polls) == 2
    assert page.evaluate("SIGNIN_PENDING") is None
    json_response(first_status[0], {"ok": True, "status": "pending"})
    page.wait_for_timeout(2300)
    assert len(polls) == 2
    assert page.evaluate("SIGNIN_PENDING") is None
    assert page.evaluate("SIGNIN_STATE.busy") == ""
    expect(page.locator(SLIDES + '[data-promo-kind="link-google"]')).to_have_count(0)
    assert not errors


@pytest.mark.parametrize("state", ["failed", "expired"])
def test_terminal_link_failure_reenables_the_card_without_hiding_it(page, state):
    errors = _open_profile(page)
    page.route(START, lambda route: json_response(route, _start_payload()))
    page.route(STATUS, lambda route: json_response(route, {"ok": True, "status": state}))
    _select(page, "link-google").locator(".hp-promo-action").click()
    page.wait_for_function("() => SIGNIN_STATE.busy === '' && !!SIGNIN_STATE.note", timeout=7000)
    card = _select(page, "link-google")
    expect(card.locator(".hp-promo-action")).to_be_enabled()
    assert not errors


@pytest.mark.parametrize("payload", [
    _start_payload(ok=False),
    _start_payload(authorize_url="javascript:alert(1)"),
    _start_payload(authorize_url="https://attacker.example/authorize"),
    _start_payload(link_request_id=None),
])
def test_invalid_link_start_never_navigates_or_starts_polling(page, payload):
    errors = _open_profile(page)
    page.evaluate("""() => {window.__openedLinks = [];
        tg.openLink = url => window.__openedLinks.push(url);}""")
    polls = []
    page.route(START, lambda route: json_response(route, payload))
    page.route(STATUS, lambda route: (polls.append(route.request.url),
                                     json_response(route, {"ok": True, "status": "pending"}))[-1])
    _select(page, "link-google").locator(".hp-promo-action").click()
    page.wait_for_function("() => SIGNIN_STATE.busy === '' && !!SIGNIN_STATE.note")
    page.wait_for_timeout(2100)
    assert page.evaluate("window.__openedLinks") == []
    assert polls == []
    expect(_select(page, "link-google").locator(".hp-promo-action")).to_be_enabled()
    assert not errors


@pytest.mark.parametrize("height,reduced_motion", [(844, False), (600, True)])
def test_mobile_swipe_tracks_finger_and_snaps_both_directions(page, height, reduced_motion, tmp_path):
    page.set_viewport_size({"width": 390, "height": height})
    page.emulate_media(reduced_motion="reduce" if reduced_motion else "no-preference")
    errors = _open_profile(page)
    _select(page, "hsk30")
    track = page.locator(ROOT + " .hp-promo-track")
    track.scroll_into_view_if_needed()
    box = track.bounding_box()
    assert box and box["width"] <= 390
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    cdp = page.context.new_cdp_session(page)

    def touch(event, x=None):
        cdp.send("Input.dispatchTouchEvent", {
            "type": event,
            "touchPoints": [] if x is None else [{"x": x, "y": box["y"] + 55}],
        })

    start = track.evaluate("node => node.scrollLeft")
    touch("touchStart", box["x"] + box["width"] - 35)
    touch("touchMove", box["x"] + box["width"] - 75)
    page.wait_for_timeout(60)
    touch("touchMove", box["x"] + box["width"] - 155)
    page.wait_for_timeout(60)
    middle = track.evaluate("node => node.scrollLeft")
    assert start + 20 < middle < start + box["width"] - 20
    touch("touchMove", box["x"] + 35)
    touch("touchEnd")
    pro = page.locator(SLIDES + '[data-promo-kind="pro"]')
    expect(pro).to_be_in_viewport(ratio=0.95)
    expect(page.locator(ROOT + ' [data-promo-dot="2"]')).to_have_attribute("aria-current", "true")
    page.screenshot(path=str(tmp_path / f"profile-carousel-{height}.png"))

    # A rightward swipe returns to the preceding HSK 3.0 card.
    touch("touchStart", box["x"] + 35)
    touch("touchMove", box["x"] + 85)
    page.wait_for_timeout(60)
    touch("touchMove", box["x"] + box["width"] - 35)
    touch("touchEnd")
    expect(page.locator(SLIDES + '[data-promo-kind="hsk30"]')).to_be_in_viewport(ratio=0.95)
    expect(page.locator(ROOT + ' [data-promo-dot="1"]')).to_have_attribute("aria-current", "true")
    assert not errors


def test_selecting_a_card_immediately_after_mount_is_not_cancelled_by_initial_resize(page):
    errors = _open_profile(page)
    page.evaluate("""() => {
      document.getElementById('hsk-profile-promo-root').scrollIntoView({
        block:'center', inline:'nearest', behavior:'instant'
      });
      HskProfileCarousel.mount();
      HskProfileCarousel.select('apps');
      HskProfileCarousel.pause();
    }""")
    expect(page.locator(SLIDES + '[data-promo-kind="apps"]')).to_be_in_viewport(ratio=0.95)
    expect(page.locator(ROOT)).to_have_attribute("data-promo-kind", "apps")
    assert not errors


def test_existing_apps_hsk30_and_pro_actions_still_use_the_original_flows(page):
    errors = _open_profile(page)
    page.evaluate("""() => {
      window.__actions = [];
      PompDesktopDownload.openProfileApps = () => window.__actions.push('apps');
      openProfileCourseVersionBook = () => window.__actions.push('hsk30');
      App.goPay = source => window.__actions.push(source);
      TRIAL_LOADED = true; TRIAL_STATE = {eligible:false, active:false};
    }""")
    _select(page, "apps").locator(".hp-promo-action").click()
    _select(page, "hsk30").locator(".hp-promo-action").click()
    _select(page, "pro").locator(".hp-promo-action").click()
    assert page.evaluate("window.__actions") == ["apps", "hsk30", "profile_subscription"]
    assert not errors


@pytest.mark.parametrize("paid", [False, True])
def test_pro_trial_requires_explicit_cta_and_paid_card_keeps_renewal(page, paid):
    errors = _open_profile(page)
    page.evaluate("""paid => {
      window.__actions = [];
      MAP.user.plan = paid ? 'pro' : 'free';
      MAP.user.is_paid = paid;
      MAP.user.access_ends_at = paid ? '2030-01-01T00:00:00Z' : null;
      TRIAL_LOADED = true; TRIAL_STATE = {eligible:!paid, active:false};
      App.goPay = source => window.__actions.push(source);
      App.startTrial = source => window.__actions.push('trial:' + source);
      renderProfile();
    }""", paid)
    card = _select(page, "pro")
    card.locator(".hp-promo-copy").click()
    assert page.evaluate("window.__actions") == ["profile_renewal" if paid else "profile_subscription"]
    card.locator(".hp-promo-action").click()
    assert page.evaluate("window.__actions") == [
        "profile_renewal" if paid else "profile_subscription",
        "profile_renewal" if paid else "trial:profile",
    ]
    assert not errors
