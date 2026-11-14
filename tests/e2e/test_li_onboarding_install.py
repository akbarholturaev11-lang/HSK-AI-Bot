"""iPhone PWA Home Screen guide: availability, platform, fallback and frequency.

Browser-mode iOS only, once per opening (one tab session) for a verified
account: after a new sign-up and on every new course opening. This is a
presentation-only view. It may never grant a PWA session, start a Pro trial
or request push permissions.
"""
from pathlib import Path
import os

import pytest

pw = pytest.importorskip("playwright.sync_api")
STATIC = Path("app/static")
JS = (STATIC / "course_v3_data/li-onboarding-install.js").read_text(encoding="utf-8")
CAT = (STATIC / "course_v3_data/hsk-li-onboarding-i18n.js").read_text(encoding="utf-8")
CSS = (STATIC / "course_v3_data/li-onboarding-install.css").read_text(encoding="utf-8")
IOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1"
ANDROID = "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
ORIGIN = "https://hsk.test"
SHOWN_KEY = "hskai.pwa.install.guide.shown"
# Mirrors the PWA-only tag app/api/pwa_auth.py adds to /iphone-pwa/course
# (its exact content-versioned form is pinned in tests/test_pwa_initial_shell.py).
COURSE_TAG = (
    "<script defer src='/course_v3_data/li-onboarding-install.js?v=t' "
    "data-hsk-install-launch='course' "
    "data-i18n='/course_v3_data/hsk-li-onboarding-i18n.js?v=t' "
    "data-css='/course_v3_data/li-onboarding-install.css?v=t'></script>"
)
COURSE_HTML = (
    "<!doctype html><html lang='ru'><head><meta name='viewport' content='width=device-width'></head>"
    "<body><main id='course'>Course map</main><script>"
    "var LANG='uz';var NavBack={BLOCK:['#paywall.on']};window.__actor=0;window.__flushed=0;"
    "function pwaCourseActor(){window.__actor++;"
    "return Promise.resolve({ok:true,user_id:77,language:'ru',csrf:'c'})}"
    "function flushPendingCenterAd(){window.__flushed++}"
    "</script>" + COURSE_TAG + "</body></html>"
)


def _prepare(browser, *, ios=True, installed=False, has_video=False, context=None,
             path="/iphone-pwa/onboarding/li", html=None, user_agent=None, query=""):
    owner = context or browser.new_context(
        viewport={"width": 390, "height": 844},
        user_agent=user_agent or (IOS if ios else
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"),
    )
    page = owner.new_page()
    page.requests = []
    page.on("request", lambda request: page.requests.append(request.url))
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    if installed:
        page.add_init_script(
            "Object.defineProperty(navigator,'standalone',{get:()=>true});"
        )
    page.route("**/course_v3_data/hsk-li-onboarding-i18n.js*", lambda route: route.fulfill(
        body=CAT, content_type="application/javascript"))
    page.route("**/course_v3_data/li-onboarding-install.js*", lambda route: route.fulfill(
        body=JS, content_type="application/javascript"))
    page.route("**/course_v3_data/li-onboarding-install.css*", lambda route: route.fulfill(
        body=CSS, content_type="text/css"))
    def video_response(route):
        if not has_video:
            route.fulfill(status=404, body="not available", content_type="text/plain")
            return
        # A fake 12-byte ftyp header is NOT a valid MP4. WebKit correctly
        # rejected that fixture. Test the committed optimized H.264 recording
        # and real Safari HTTP byte-range behaviour instead.
        video = (STATIC / "assets/onboarding/iphone-home-screen.mp4").read_bytes()
        header = route.request.headers.get("range", "")
        headers = {"Accept-Ranges": "bytes", "Content-Type": "video/mp4"}
        if header.startswith("bytes="):
            start_text, _, end_text = header[6:].partition("-")
            if start_text:
                start_byte = int(start_text)
                end_byte = min(len(video)-1, int(end_text) if end_text else len(video)-1)
            else:
                start_byte = max(0, len(video) - int(end_text))
                end_byte = len(video)-1
            if start_byte >= len(video) or end_byte < start_byte:
                route.fulfill(status=416, headers={
                    **headers, "Content-Range": f"bytes */{len(video)}"
                })
                return
            headers["Content-Range"] = f"bytes {start_byte}-{end_byte}/{len(video)}"
            route.fulfill(status=206, body=video[start_byte:end_byte + 1], headers=headers)
        else:
            route.fulfill(status=200, body=video, headers=headers)

    page.route("**/assets/onboarding/iphone-home-screen.mp4*", video_response)
    page.route("**/assets/onboarding/iphone-install-home-focus.jpg*", lambda route: route.fulfill(
        body=(STATIC / "assets/onboarding/iphone-install-home-focus.jpg").read_bytes(),
        content_type="image/jpeg"))
    if html is None:
        html = (
            "<!doctype html><html lang='uz'><head><meta name='viewport' content='width=device-width'>"
            "<style>" + CSS + "</style></head>"
            "<body><main>Authenticated onboarding complete</main>"
            "<script src='/course_v3_data/hsk-li-onboarding-i18n.js'></script>"
            "<script src='/course_v3_data/li-onboarding-install.js'></script>"
            "</body></html>"
        )
    page.route(ORIGIN + path + "*", lambda route: route.fulfill(
        body=html, content_type="text/html; charset=utf-8"))
    page.goto(ORIGIN + path + query)
    page.wait_for_function("window.HSKAILiInstallGuide")
    return page, errors


def test_iphone_install_starts_with_focus_photo_then_video_with_three_fallback_steps():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser)
        # Verified login may preload before the installation guide is shown.
        page.evaluate("() => HSKAILiInstallGuide.preload()")
        assert page.evaluate("() => document.querySelector('video') === null") is True
        opened = page.evaluate("""() => {
          window.__next=0;
          return HSKAILiInstallGuide.open({userId:37,lang:"uz"},()=>window.__next++);
        }""")
        assert opened is True
        assert page.locator(".li-install-hero").is_visible()
        page.wait_for_function("document.querySelector('.li-install-hero')?.naturalWidth > 0")
        assert page.locator(".li-install-title").is_visible()
        assert "telefoningiz" in page.locator(".li-install-title").inner_text()
        assert page.locator(".li-install-how").inner_text() == "Qanday?"
        # Keep the heading close to the owner's Home Screen illustration;
        # no stretching of blank space between the title and hero image.
        assert page.locator(".li-install-hero").evaluate("""(img) => {
          const h = document.querySelector('.li-install-title').getBoundingClientRect();
          const p = img.getBoundingClientRect();
          return p.top > h.bottom && p.top - h.bottom <= 45;
        }""")
        assert page.locator(".li-install-back").count() == 0
        assert page.locator(".li-install-close").evaluate(
            "(el) => getComputedStyle(el).backgroundColor === 'rgba(0, 0, 0, 0)'")
        assert page.locator(".li-install-video-page").is_hidden()
        assert page.locator(".li-install-continue, .li-install-note").count() == 0
        assert page.locator(".li-install-card").evaluate(
            "(node) => Math.abs(node.getBoundingClientRect().height - innerHeight) < 2")
        assert page.get_by_role("dialog").get_attribute("aria-modal") == "true"

        page.locator(".li-install-how").click()
        page.locator(".li-install-video-page").wait_for(state="visible")
        page.locator(".li-install-video-fallback").wait_for(state="visible")
        # The video page is headed "Qo‘llanma" (Guide), right above the media.
        assert page.locator(".li-install-video-title").inner_text() == "Qo‘llanma"
        assert page.locator(".li-install-video-title").evaluate("""(h) => {
          const m = document.querySelector('.li-install-media').getBoundingClientRect();
          const t = h.getBoundingClientRect();
          return t.bottom <= m.top && m.top - t.bottom <= 24 && t.top >= 0;
        }""")
        assert page.get_by_role("dialog").get_attribute("aria-labelledby") == "li-install-video-title"
        assert page.locator(".li-install-video").is_hidden()
        assert page.locator(".li-install-video-fallback .li-install-steps li").count() == 3
        assert page.locator(".li-install-scroll-steps").is_hidden()
        assert page.locator(".li-install-back").count() == 0
        assert page.locator(".li-install-close").is_visible()
        # One minimalist X dismisses either step; no secondary back arrow.
        assert page.locator(".li-install-close").evaluate(
            "(el) => getComputedStyle(el).backgroundColor === 'rgba(0, 0, 0, 0)'")
        assert page.locator(".li-install-close svg path").count() == 1
        page.locator(".li-install-close").click()
        assert page.evaluate("window.__next") == 1
        assert page.get_by_role("dialog").count() == 0
        # Once per opening: a per-tab marker, never a permanent per-account flag.
        assert page.evaluate(f"sessionStorage.getItem('{SHOWN_KEY}')") == "1"
        assert page.evaluate("localStorage.length") == 0
        assert page.evaluate("""() => HSKAILiInstallGuide.open(
            {userId:37,lang:"ru"},()=>window.__next++)""") is False
        assert not errors
        browser.close()


def test_old_local_seen_flag_never_suppresses_a_new_opening():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser)
        # Legacy v1 flag from the former "show once per account" behaviour.
        page.evaluate("localStorage.setItem('hskai_li_install_guide_v1:37','seen')")
        assert page.evaluate("""() => HSKAILiInstallGuide.open(
            {userId:37,lang:"uz"},()=>{})""") is True
        page.locator(".li-install-close").click()
        page.reload()
        page.wait_for_function("window.HSKAILiInstallGuide")
        assert page.evaluate("""() => HSKAILiInstallGuide.open(
            {userId:37,lang:"uz"},()=>{})""") is False  # same opening (tab)
        # A new opening (new Safari tab, same browser storage) shows it again.
        again, more = _prepare(browser, context=page.context)
        assert again.evaluate("localStorage.getItem('hskai_li_install_guide_v1:37')") == "seen"
        assert again.evaluate("""() => HSKAILiInstallGuide.open(
            {userId:37,lang:"uz"},()=>{})""") is True
        assert again.locator(".li-install-hero").is_visible()
        assert not errors and not more
        browser.close()


@pytest.mark.parametrize("ios,installed,expect", [
    (False, False, False),
    (True, True, False),
    (True, False, True),
])
def test_install_prompt_is_exclusive_to_not_yet_installed_ios_pwa(ios, installed, expect):
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser, ios=ios, installed=installed)
        opened = page.evaluate("""() => HSKAILiInstallGuide.open(
            {userId:41,lang:"ru"},()=>{})""")
        assert opened is expect
        assert page.get_by_role("dialog").count() == int(expect)
        assert not errors
        browser.close()


def test_media_stays_optional_but_real_metadata_can_swap_to_vertical_video():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser, ios=True, has_video=True)
        assert page.evaluate("""() => HSKAILiInstallGuide.open(
          {userId:53,lang:"tj"},()=>{})""") is True
        assert page.locator(".li-install-hero").is_visible()
        assert page.locator(".li-install-video-page").is_hidden()
        page.locator(".li-install-how").click()
        # Actual playable MP4, not a synthetic loadedmetadata event.
        page.locator(".li-install-video").wait_for(state="visible", timeout=15000)
        assert page.locator(".li-install-video").evaluate(
            "(video) => video.readyState >= HTMLMediaElement.HAVE_METADATA")
        assert page.locator(".li-install-video-fallback").is_hidden()
        assert page.locator(".li-install-scroll-steps .li-install-steps li").count() == 3
        # Instructions live below the initial viewport, revealed by swipe.
        assert page.locator(".li-install-scroll-steps").evaluate(
            "(node) => node.getBoundingClientRect().top >= innerHeight - 20")
        page.locator(".li-install-video-page").evaluate(
            "(node) => node.scrollTop = node.scrollHeight")
        assert page.locator(".li-install-scroll-steps").is_visible()
        page.locator(".li-install-close").click()
        assert page.get_by_role("dialog").count() == 0
        assert not errors
        browser.close()


def test_telegram_in_app_browser_shows_safari_link_not_video():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser, ios=True)
        assert page.evaluate("""() => {
          window.Telegram={WebApp:{initData:"real-verified-placeholder"}};
          return HSKAILiInstallGuide.open({userId:53,lang:"ru"},()=>{});
        }""") is True
        assert page.locator(".li-install-panda").is_visible()
        assert page.locator(".li-install-browser-title").inner_text() == "Откройте HSK AI в Safari"
        assert page.locator(".li-install-safari-icon svg").is_visible()
        assert page.locator(".li-install-browser-hint").text_content().startswith("Скопируйте ссылку и откройте её в Safari, чтобы установить приложение.")
        assert page.locator(".li-install-browser-link").get_attribute("href") == "https://hskai.app/iphone-pwa"
        assert page.locator(".li-install-video, .li-install-steps, .li-install-title").count() == 0
        assert page.locator(".li-install-copy").inner_text() == "Скопировать ссылку"
        assert not errors
        browser.close()


@pytest.mark.parametrize("clipboard_works", [True, False])
def test_other_ios_browser_copies_the_safari_link(clipboard_works):
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser, user_agent=IOS.replace("Version/18.6 ", "CriOS/130.0.0.0 "))
        page.evaluate("""(ok) => {
          Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{
            writeText:(t) => ok ? (window.__copied=t, Promise.resolve())
                                : Promise.reject(new Error('denied'))}});
          document.execCommand = () => false;
        }""", clipboard_works)
        assert page.evaluate("""() => HSKAILiInstallGuide.open(
            {userId:61,lang:"tj"},()=>{})""") is True
        copy = page.locator(".li-install-copy")
        assert copy.inner_text() == "Нусхаи пайванд"
        assert page.locator(".li-install-browser-title").inner_text() == "HSK AI-ро дар Safari кушоед"
        copy.click()
        if clipboard_works:
            page.wait_for_function("window.__copied === 'https://hskai.app/iphone-pwa'")
            page.wait_for_function(
                "document.querySelector('.li-install-copy').textContent === 'Нусха шуд'")
        else:
            # Copy denied: the visible link is selected for the native menu.
            page.wait_for_function(
                "String(getSelection()).includes('hskai.app/iphone-pwa')")
            assert copy.inner_text() == "Нусхаи пайванд"
        assert page.get_by_role("dialog").count() == 1
        assert not errors
        browser.close()


def test_chrome_on_ios_is_not_mistaken_for_safari():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(browser)
        page.add_init_script("""Object.defineProperty(navigator, 'userAgent', {
          get:()=> 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/130.0.0.0 Mobile/15E148 Safari/604.1'
        });""")
        page.reload()
        assert page.evaluate("""() => HSKAILiInstallGuide.open(
            {userId:54,lang:"uz"},()=>{})""") is True
        assert page.locator(".li-install-panda").is_visible()
        assert page.locator(".li-install-video").count() == 0
        assert page.locator(".li-install-browser-hint").inner_text().count("Safari") == 1
        assert page.locator(".li-install-browser-title").inner_text() == "HSK AI’ni Safari’da oching"
        assert not errors
        browser.close()


def test_install_guide_never_opens_without_verified_account_id():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, _ = _prepare(browser)
        for value in (None, -1, 0, "guest", 1.5):
            assert page.evaluate("""v => HSKAILiInstallGuide.open(
                {userId:v,lang:"tj"},()=>{})""", value) is False
        assert page.get_by_role("dialog").count() == 0
        browser.close()


def _course(browser, **options):
    return _prepare(browser, path="/iphone-pwa/course", html=COURSE_HTML, **options)


def test_existing_account_course_opening_shows_guide_once_per_tab():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _course(browser)
        page.locator(".li-install-card").wait_for(state="visible", timeout=8000)
        # Verified server language wins over the course's provisional LANG.
        assert page.locator(".li-install-how").inner_text() == "Как?"
        assert page.evaluate("window.__actor") == 1
        # Course prompts (feedback, ads) treat the open guide as a block.
        assert page.evaluate("NavBack.BLOCK.includes('.li-install-overlay')")
        assert page.evaluate(
            "NavBack.BLOCK.some(function(s){return document.querySelector(s)})")
        page.locator(".li-install-close").click()
        assert page.locator(".li-install-card").count() == 0
        assert page.locator("#course").is_visible()
        assert page.evaluate("window.__flushed") == 1
        assert page.evaluate(f"sessionStorage.getItem('{SHOWN_KEY}')") == "1"
        page.reload()  # same opening: not again
        page.wait_for_function("window.HSKAILiInstallGuide")
        page.wait_for_timeout(500)
        assert page.locator(".li-install-card").count() == 0
        again, more = _course(browser, context=page.context)  # a new opening
        again.locator(".li-install-card").wait_for(state="visible", timeout=8000)
        assert not errors and not more
        browser.close()


@pytest.mark.parametrize("variant", ["standalone", "android", "payment_return"])
def test_course_guide_is_absent_for_installed_android_and_payment_return(variant):
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        options = {"installed": variant == "standalone"}
        if variant == "android":
            options["user_agent"] = ANDROID
        if variant == "payment_return":
            options["query"] = "?lang=ru&pro_checkout=5&pro_return=success"
        page, errors = _course(browser, **options)
        page.wait_for_timeout(700)
        assert page.locator(".li-install-card").count() == 0
        # Nothing extra is downloaded where the guide cannot appear.
        assert not [u for u in page.requests
                    if "hsk-li-onboarding-i18n" in u or "li-onboarding-install.css" in u]
        assert page.evaluate("window.__actor") == 0
        assert page.evaluate(f"sessionStorage.getItem('{SHOWN_KEY}')") is None
        assert not errors
        browser.close()


def test_other_ios_browser_on_course_gets_safari_link_with_copy():
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _course(browser, user_agent=IOS.replace("Version/18.6 ", "CriOS/130.0.0.0 "))
        page.locator(".li-install-panda").wait_for(state="visible", timeout=8000)
        assert page.locator(".li-install-copy").inner_text() == "Скопировать ссылку"
        assert page.locator(".li-install-video").count() == 0
        page.locator(".li-install-close").click()
        assert page.locator("#course").is_visible()
        assert not errors
        browser.close()


def test_real_course_document_shows_guide_then_resumes_the_course():
    """Actual shared course HTML plus the PWA-only tag: real globals, no errors."""
    import json
    import mimetypes
    from urllib.parse import urlsplit

    source = (STATIC / "course-v3.html").read_text(encoding="utf-8")
    sdk = '<script src="/assets/telegram-web-app.js?v=20261019-1"></script>'
    assert source.count(sdk) == 1 and source.count("</body>") == 1
    document = source.replace(sdk, "", 1).replace("</body>", COURSE_TAG + "</body>", 1)
    data = json.loads((STATIC / "course_v3_data/hsk1.json").read_text(encoding="utf-8"))
    data.update(authenticated=True, level="hsk1")
    data["user"] = {"name": "Verified", "avatar": "阿", "language": "uz",
                    "is_paid": False, "state": "FREE", "onboarding_completed": True}

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/course":
            route.fulfill(status=200, content_type="text/html", body=document)
        elif path == "/api/v3/pwa-auth/session":
            route.fulfill(status=200, json={"ok": True, "user_id": 31, "csrf": "t",
                                            "language": "uz"})
        elif path == "/api/v3/pwa/map":
            route.fulfill(status=200, json=data, headers={"X-HSK-PWA-User-ID": "31"})
        elif path.startswith("/api/"):
            route.fulfill(status=404, json={"ok": False, "error": "not_mocked"})
        else:
            file = (STATIC / path.lstrip("/")).resolve()
            if file.is_file() and file.is_relative_to(STATIC.resolve()):
                mime, _ = mimetypes.guess_type(file)
                route.fulfill(path=str(file), content_type=mime or "application/octet-stream")
            else:
                route.fulfill(status=404, body="")

    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, user_agent=IOS)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.set_default_timeout(15000)
        page.route("**/*", serve)
        page.goto(ORIGIN + "/iphone-pwa/course?lang=ru", wait_until="domcontentloaded")
        page.locator(".li-install-card").wait_for(state="visible")
        assert page.locator(".li-install-hero").is_visible()
        assert page.locator(".li-install-how").inner_text() == "Qanday?"
        assert page.evaluate("NavBack.blocked()") is True
        page.locator("#s-course .uban").first.wait_for(state="attached")
        page.locator(".li-install-close").click()
        assert page.locator(".li-install-card").count() == 0
        assert page.evaluate("NavBack.blocked()") is False
        page.locator("#s-course .uban").first.wait_for(state="visible")
        assert page.evaluate(f"sessionStorage.getItem('{SHOWN_KEY}')") == "1"
        assert not errors, errors
        browser.close()

def test_other_ios_browser_short_viewport_can_scroll_to_copy_button():
    # The localized heading must not push Copy outside an unscrollable card.
    with pw.sync_playwright() as p:
        browser = getattr(p, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page, errors = _prepare(
            browser, user_agent=IOS.replace("Version/18.6 ", "CriOS/130.0.0.0 "))
        page.set_viewport_size({"width": 320, "height": 568})
        assert page.evaluate("""() => HSKAILiInstallGuide.open(
          {userId:53,lang:"ru"},()=>{})""") is True
        assert page.locator(".li-install-card.li-install-browser-mode").count() == 1
        copy = page.locator(".li-install-copy")
        copy.scroll_into_view_if_needed()
        assert copy.evaluate("""(node) => {
          const rect=node.getBoundingClientRect();
          return rect.top >= 0 && rect.bottom <= innerHeight;
        }""")
        assert not errors
        browser.close()
