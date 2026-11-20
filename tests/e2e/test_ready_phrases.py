"""Ready phrases remain a static, client-side study tool in the Mini App."""

import json
import mimetypes
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright_api.sync_playwright

STATIC_ROOT = Path(__file__).resolve().parents[2] / "app" / "static"
BASE_URL = "http://hsk-ai.local"


def _serve_static(route):
    request_path = urlparse(route.request.url).path
    # The legacy interaction test supplies its own Telegram BackButton fixture.
    if request_path == "/assets/telegram-web-app.js":
        route.fulfill(status=200, content_type="application/javascript", body="")
        return
    aliases = {"/iphone-pwa/phrases": "hsk-gaplar.html", "/audio/words/index.js": "audio/words-index.js", "/audio/words/client.js": "audio/words-client.js"}
    path = (STATIC_ROOT / aliases.get(request_path, request_path.lstrip("/"))).resolve()
    if not path.is_relative_to(STATIC_ROOT.resolve()) or not path.is_file():
        route.fulfill(status=404, content_type="text/plain", body="not found")
        return
    content_types = {
        ".css": "text/css",
        ".html": "text/html",
        ".js": "application/javascript",
        ".json": "application/json",
    }
    route.fulfill(
        status=200,
        content_type=content_types.get(path.suffix, mimetypes.guess_type(path)[0] or "application/octet-stream"),
        path=str(path),
    )


def test_practice_menu_phrasebook_search_and_favorites_are_local():
    with sync_playwright() as playwright:
        try:
            browser = getattr(playwright, os.getenv("PWA_E2E_ENGINE", "chromium")).launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")

        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        page.add_init_script("""
            Date.now = () => Date.parse('2026-10-14T12:00:00+08:00');
            const back = {
                visible: false,
                handler: null,
                show() { this.visible = true; },
                hide() { this.visible = false; },
                onClick(handler) { this.handler = handler; },
                offClick(handler) { if (this.handler === handler) this.handler = null; }
            };
            window.__hskBackButton = back;
            window.Telegram = { WebApp: { BackButton: back, initData: "test" } };
        """)
        page.set_default_timeout(8000)
        api_requests = []
        page_errors = []
        page.on("request", lambda request: api_requests.append(request.url) if "/api/" in request.url and request.frame.url.startswith(f"{BASE_URL}/hsk-gaplar.html") else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.route(f"{BASE_URL}/**", _serve_static)
        page.route("https://**/*", lambda route: route.fulfill(status=200, body=""))

        try:
            page.goto(f"{BASE_URL}/course-v3.html", wait_until="domcontentloaded")
            assert page.evaluate("typeof renderMashq") == "function"
            page.evaluate("LANG='uz'; renderMashq()")
            row = page.locator("#m-ready-phrases")
            assert row.count() == 1
            assert row.locator(".new-section-badge").inner_text() == json.loads((STATIC_ROOT.parents[1] / "localization/ui/uz/course.json").read_text())["messages"]["newSectionBadge"]
            # The Mashq tab is hidden until selected; exercise the rendered row
            # handler, which opens the cached resource overlay without reloading.
            row.evaluate("element => element.click()")

            phrasebook = page.frame_locator("#resource-phrases iframe.resource-frame")
            phrasebook.locator(".phrase").first.wait_for()
            assert page.locator("#resourceov.on").count() == 1
            assert phrasebook.locator(".phrase").count() == 300
            # The phrasebook uses the same cinnabar accent as the main practice tab.
            assert phrasebook.locator(".pinyin").first.evaluate("el => getComputedStyle(el).color") == "rgb(178, 53, 48)"
            # The standalone phrasebook intentionally has no visible title/intro block.
            assert phrasebook.locator(".top, .eyebrow, .hero, #title, #intro").count() == 0
            assert phrasebook.locator(".page > .search").count() == 1
            assert phrasebook.locator("#query").evaluate("el => el.getBoundingClientRect().top") <= 24
            assert phrasebook.locator(".chip[aria-pressed='true']").first.evaluate("el => getComputedStyle(el).borderTopColor") == "rgb(224, 74, 64)"

            phrasebook.locator("#query").fill("ni hao")
            assert "你好" in " ".join(phrasebook.locator(".hanzi").all_text_contents())
            assert phrasebook.locator("#back").count() == 0
            phrasebook.locator("#query").fill("")
            phrasebook.locator(".phrase").first.locator("button.save").click()
            phrasebook.get_by_role("button", name="Saqlanganlar").click()
            assert phrasebook.locator(".phrase").count() == 1
            assert page.evaluate("window.__hskBackButton.visible") is True
            assert page.evaluate("typeof window.__hskBackButton.handler") == "function"
            page.evaluate("window.__hskBackButton.handler()")
            page.wait_for_function("!document.getElementById('resourceov').classList.contains('on')")
            assert page.url.startswith(f"{BASE_URL}/course-v3.html")
            assert api_requests == []
            assert page_errors == []
        finally:
            browser.close()


def test_new_section_release_windows_match_on_android_and_mini_app():
    miniapp = (STATIC_ROOT / "course-v3.html").read_text(encoding="utf-8")
    android = (
        Path(__file__).resolve().parents[2]
        / "android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeScreen.kt"
    ).read_text(encoding="utf-8")
    mini_registry = re.search(r"var NEW_SECTION_RELEASES=(\{[^;]+\});", miniapp)
    assert mini_registry is not None
    mini_releases = json.loads(mini_registry.group(1))

    android_ids = dict(re.findall(r'private const val ([A-Z0-9_]+_SECTION_ID) = "([^"]+)"', android))
    android_pairs = re.findall(r"([A-Z0-9_]+_SECTION_ID) to ([\d_]+)L", android)
    android_releases = {android_ids[key]: int(value.replace("_", "")) for key, value in android_pairs}
    assert mini_releases == android_releases


def test_practice_new_badge_expires_after_72_hours():
    with sync_playwright() as playwright:
        try:
            browser = getattr(playwright, os.getenv("PWA_E2E_ENGINE", "chromium")).launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")

        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        page.add_init_script("Date.now = () => Date.parse('2026-10-16T00:08:05+08:00')")
        page.route(f"{BASE_URL}/**", _serve_static)
        page.route("https://**/*", lambda route: route.fulfill(status=200, body=""))
        try:
            page.goto(f"{BASE_URL}/course-v3.html", wait_until="domcontentloaded")
            page.evaluate("LANG='uz'; renderMashq()")
            assert page.locator("#m-ready-phrases .new-section-badge").count() == 0
        finally:
            browser.close()


def test_phrasebook_loads_outside_telegram_with_shared_theme_tokens():
    with sync_playwright() as playwright:
        try:
            browser = getattr(playwright, os.getenv("PWA_E2E_ENGINE", "chromium")).launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")

        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.route(f"{BASE_URL}/**", _serve_static)
        try:
            page.goto(f"{BASE_URL}/hsk-gaplar.html?lang=uz&theme=dark", wait_until="domcontentloaded")
            page.locator(".phrase").first.wait_for()
            assert page.locator(".phrase").count() == 300
            assert page.locator("#back").count() == 0
            assert page.locator(".page > .search").count() == 1
            assert page.title() == "Tayyor gaplar · HSK AI"
            assert page.locator("body").evaluate("element => getComputedStyle(element).backgroundColor") == "rgb(0, 47, 73)"
            # Dark mode must use the dark-theme cinnabar tokens (cyan), not hardcoded red.
            assert page.locator(".pinyin").first.evaluate("el => getComputedStyle(el).color") == "rgb(126, 221, 246)"
            assert page.locator(".chip[aria-pressed='true']").first.evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(11, 76, 102)"
            assert page_errors == []
        finally:
            browser.close()


def test_android_ready_phrases_search_follows_compact_back_control():
    screen = (
        Path(__file__).resolve().parents[2]
        / "android/app/src/main/java/com/pomp/hskai/feature/practice/ReadyPhrasesScreen.kt"
    ).read_text(encoding="utf-8")
    layout = screen.split("fun ReadyPhrasesScreen(", 1)[1].split("private fun ReadyPhraseCard(", 1)[0]
    assert "R.string.ready_phrases_title" not in layout
    assert "R.string.ready_phrases_intro" not in layout
    assert "R.string.hsk_common_action_back" in layout
    assert layout.index("IconButton(") < layout.index("OutlinedTextField(") < layout.index("LazyRow(")

AUDIO_FIXTURE = """
window.__phraseAudio = [];
window.__copied = [];
Object.defineProperty(navigator, 'clipboard', {value:{writeText: value => {window.__copied.push(value); return Promise.resolve()}}});
window.Audio = class {
  constructor(src) { this.src=src; this.paused=false; window.__phraseAudio.push(this); }
  play() {
    if (window.__audioMode === 'hold') return new Promise((resolve,reject) => {this.resolve=resolve; this.reject=reject});
    if (window.__audioMode === 'reject') return Promise.reject(new Error('fixture'));
    return Promise.resolve();
  }
  pause() { this.paused=true; }
};
window.SpeechSynthesisUtterance = class {constructor(text) {this.text=text}};
Object.defineProperty(window, 'speechSynthesis', {value:{
  speak: utterance => {window.__spoken=utterance; if (!window.__holdSpeech && utterance.onstart) utterance.onstart()},
  cancel: () => {window.__speechCancelled=true}
}});
"""


def _phrase_audio_source(page):
    page.evaluate("""() => {
        window.__remembered=[];
        window.HSKOfflineAudio={cachedUrl:()=>null,url:()=>'/audio/words/fixture.mp3',rememberPlayed:(text,src)=>window.__remembered.push({text,src})};
    }""")


@pytest.mark.parametrize("width", [320, 390, 430])
@pytest.mark.parametrize("language", ["uz", "ru", "tj"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_recovered_pwa_phrases_preserve_search_save_and_independent_actions(width, language, theme):
    """Recover UIUX-004 from pro45; existing catalog/persistence stay authoritative."""
    from tests.pwa_layout_geometry import capture_geometry, assert_reserved_layout
    catalog = json.loads((STATIC_ROOT / 'course_v3_data/ready-phrases-v1.json').read_text())
    copy = json.loads((STATIC_ROOT.parents[1] / f'localization/ui/{language}/course.json').read_text())["messages"]
    with sync_playwright() as playwright:
        browser = getattr(playwright, os.getenv('PWA_E2E_ENGINE', 'chromium')).launch()
        try:
            page = browser.new_page(viewport={'width':width,'height':844},is_mobile=True,reduced_motion='reduce')
            page.set_default_timeout(10000)
            page.add_init_script(AUDIO_FIXTURE)
            errors, requests, pending_catalog = [], [], []
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('request',lambda request:requests.append(request.url) if '/api/' in request.url else None)
            page.route(BASE_URL+'/**',_serve_static)
            page.route('**/ready-phrases-v1.json',lambda route:pending_catalog.append(route))
            page.goto(BASE_URL+f'/iphone-pwa/phrases?lang={language}&theme={theme}',wait_until='domcontentloaded')
            page.locator('.phrase-skeleton').first.wait_for()
            anchors={'query':'#query','filters':'#filters','count':'#count'}
            anchors.update({f'row-{i}':f'#list>.phrase:nth-child({i})' for i in range(1,5)})
            loading=capture_geometry(page,anchors)
            assert len(pending_catalog)==1
            pending_catalog.pop().fulfill(path=str(STATIC_ROOT/'course_v3_data/ready-phrases-v1.json'),content_type='application/json')
            page.locator('.phrase-play').first.wait_for()
            cards=page.locator('.phrase')
            assert cards.count()==300
            assert_reserved_layout(loading,capture_geometry(page,anchors))
            page.unroute('**/ready-phrases-v1.json')
            assert page.locator('.phrase-details:not([hidden])').count()==0
            assert cards.first.locator('.hanzi').inner_text()==catalog['phrases'][0]['zh']
            _phrase_audio_source(page)
            for selector in ('.phrase-toggle','.phrase-play','.save','.chip'):
                box=page.locator(selector).first.bounding_box()
                assert box['width']>=44 and box['height']>=44
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert cards.first.locator('.phrase-toggle').get_attribute('aria-label').startswith(copy['readyPhrases.expand'])
            assert cards.first.locator('.phrase-play').get_attribute('aria-label').startswith(copy['readyPhrases.listen'])
            cards.first.locator('.phrase-toggle').focus()
            page.keyboard.press('Enter')
            assert cards.first.locator('.phrase-toggle').get_attribute('aria-expanded')=='true'
            assert cards.first.locator('.translation').inner_text()==catalog['phrases'][0]['translations'][language]
            assert cards.first.locator('.pinyin').inner_text()==catalog['phrases'][0]['pinyin']
            assert cards.first.locator('.translation').evaluate('el=>parseFloat(getComputedStyle(el).fontSize)')>=16
            cards.first.locator('.copy').click()
            assert page.evaluate('window.__copied[0]')==catalog['phrases'][0]['zh']
            cards.first.locator('.phrase-play').click()
            page.wait_for_function("document.querySelector('.phrase-play').getAttribute('aria-pressed')==='true'")
            assert cards.first.locator('.phrase-toggle').get_attribute('aria-expanded')=='true'
            cards.first.locator('.save').click()
            assert cards.first.locator('.save').get_attribute('aria-pressed')=='true'
            assert cards.first.locator('.phrase-play').get_attribute('aria-pressed')=='true'
            assert cards.first.locator('.phrase-toggle').get_attribute('aria-expanded')=='true'
            assert page.evaluate("document.activeElement.classList.contains('save')")
            assert page.evaluate('window.__phraseAudio[0].paused') is False
            assert cards.first.locator('.phrase-play').evaluate("""el=>{const probe=document.createElement('span');probe.style.color='var(--hsk-cinnabar-ink)';document.body.append(probe);const expected=getComputedStyle(probe).color;probe.remove();return getComputedStyle(el).color===expected}""")
            cards.nth(1).locator('.phrase-toggle').click()
            assert page.locator('.phrase-details:not([hidden])').count()==1
            assert cards.first.locator('.phrase-toggle').get_attribute('aria-expanded')=='false'
            page.get_by_role('button',name=copy['readyPhrases.saved'],exact=True).click()
            assert cards.count()==1
            assert page.evaluate("JSON.parse(localStorage.getItem('hsk_ai_ready_phrases:v1'))")==[catalog['phrases'][0]['id']]
            page.reload(wait_until='domcontentloaded')
            page.locator('.phrase').first.wait_for()
            page.get_by_role('button',name=copy['readyPhrases.saved'],exact=True).click()
            assert cards.count()==1
            page.get_by_role('button',name=copy['readyPhrases.all'],exact=True).click()
            page.locator('#query').fill('ni hao')
            assert '你好' in ' '.join(page.locator('.hanzi').all_text_contents())
            page.locator('#query').fill('zzzz_no_phrase_8675309')
            assert page.locator('#empty').is_visible()
            page.locator('#query').fill('')
            # Long actual catalog Hanzi can wrap without stealing the action targets.
            cards.first.locator('.hanzi').evaluate("el=>{el.textContent=el.textContent.repeat(12);el.style.fontSize='40px'}")
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert cards.first.locator('.hanzi').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
            folder=os.getenv('HSK_PHRASE_REVIEW_DIR')
            if folder:
                cards.first.locator('.hanzi').evaluate("(el,text)=>{el.textContent=text;el.style.fontSize=''}",catalog['phrases'][0]['zh'])
                if cards.first.locator('.phrase-toggle').get_attribute('aria-expanded')=='false':
                    cards.first.locator('.phrase-toggle').click()
                Path(folder).mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(Path(folder)/f'{os.getenv("PWA_E2E_ENGINE","chromium")}-{width}-{language}-{theme}.png'))
            assert not requests, 'Browsing and static fixture playback must not make grading/account/AI requests'
            assert not errors
        finally:
            browser.close()


def test_recovered_phrase_audio_rejects_stale_events_and_stops_on_parent_close():
    with sync_playwright() as playwright:
        browser=getattr(playwright,os.getenv('PWA_E2E_ENGINE','chromium')).launch()
        try:
            page=browser.new_page(viewport={'width':320,'height':568},is_mobile=True)
            page.set_default_timeout(10000)
            page.add_init_script(AUDIO_FIXTURE)
            page.route(BASE_URL+'/**',_serve_static)
            page.goto(BASE_URL+'/iphone-pwa/phrases?lang=uz',wait_until='domcontentloaded')
            page.locator('.phrase-play').first.wait_for()
            _phrase_audio_source(page)
            page.evaluate("window.__audioMode='hold'")
            page.locator('.phrase-play').nth(0).click()
            assert page.locator('.phrase-play').nth(0).is_disabled()
            assert page.locator('.save').nth(0).is_enabled()
            page.evaluate('() => {window.__staleError=window.__phraseAudio[0].onerror}')
            page.locator('.phrase-play').nth(1).click()
            page.evaluate('window.__staleError();window.__phraseAudio[0].resolve()')
            assert page.evaluate('window.__spoken===undefined')
            assert page.evaluate('window.__phraseAudio[0].paused')
            page.evaluate('window.__phraseAudio[1].resolve()')
            page.wait_for_function("document.querySelectorAll('.phrase-play')[1].getAttribute('aria-pressed')==='true'")
            page.evaluate('window.HSKResourcePause()')
            assert page.evaluate('window.__phraseAudio[1].paused')
            assert page.locator('.phrase-play[aria-pressed=true]').count()==0
            # Recovered fallback is bounded, and duplicate media failures speak only once.
            page.evaluate("() => {window.__audioMode='hold';window.__holdSpeech=true;window.__speakCount=0;window.speechSynthesis.speak=u=>{window.__spoken=u;window.__speakCount++}}")
            page.clock.install()
            page.locator('.phrase-play').nth(0).click()
            page.evaluate("() => {const audio=window.__phraseAudio[2];audio.onerror();audio.reject(new Error('fixture'))}")
            page.wait_for_function('!!window.__spoken')
            assert page.evaluate('window.__speakCount')==1
            assert page.evaluate('window.__spoken.lang')=='zh-CN'
            page.clock.fast_forward(10001)
            assert page.locator('.toast.on').inner_text()=='Ovoz ijro etilmadi. Qayta urinib ko‘ring.'
            assert page.locator('.phrase-play[disabled]').count()==0
            assert page.evaluate('window.__speechCancelled')
        finally:
            browser.close()


def test_recovered_phrase_catalog_failure_retry_and_missing_bundle_fallback():
    with sync_playwright() as playwright:
        browser=getattr(playwright,os.getenv('PWA_E2E_ENGINE','chromium')).launch()
        try:
            page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,reduced_motion='reduce')
            pending=[]
            page.route(BASE_URL+'/**',_serve_static)
            page.route('**/ready-phrases-v1.json',lambda route:pending.append(route))
            page.goto(BASE_URL+'/iphone-pwa/phrases?lang=ru',wait_until='domcontentloaded')
            page.locator('.phrase-skeleton').first.wait_for()
            before=page.locator('#query').bounding_box()
            assert page.locator('.phrase-skeleton').count()==4
            assert page.locator('.filters button[disabled]').count()==2
            pending.pop().fulfill(status=503,json={})
            page.locator('#retry').wait_for()
            assert page.locator('#list').get_attribute('aria-busy') is None
            assert page.locator('#query').bounding_box()==before
            page.locator('#retry').click()
            page.locator('.phrase-skeleton').first.wait_for()
            pending.pop().fulfill(path=str(STATIC_ROOT/'course_v3_data/ready-phrases-v1.json'),content_type='application/json')
            page.locator('.phrase-play').first.wait_for()
            assert page.locator('.phrase').count()==300
            assert page.locator('#query').bounding_box()==before
            page.evaluate("() => {Storage.prototype.setItem=function(){throw new DOMException('fixture','QuotaExceededError')}}")
            page.locator('.phrase .save').first.click()
            assert page.locator('.phrase .save').first.get_attribute('aria-pressed')=='false'
            assert page.locator('.toast.on').is_visible()
            # An unavailable new catalog retains the fully readable legacy fallback.
            page.route('**/hsk-course-i18n.js*',lambda route:route.fulfill(status=503,body=''))
            page.reload(wait_until='domcontentloaded')
            pending.pop().fulfill(path=str(STATIC_ROOT/'course_v3_data/ready-phrases-v1.json'),content_type='application/json')
            page.locator('.pinyin').first.wait_for()
            assert page.locator('.phrase-play,.phrase-toggle').count()==0
            assert page.locator('.translation').first.is_visible()
        finally:
            browser.close()


def test_recovered_phrase_audio_uses_existing_parent_pause_and_retains_cached_browse_state():
    from tests.e2e.test_pwa_progressive_sections import pwa_document
    data=json.loads((STATIC_ROOT/'course_v3_data/hsk1.json').read_text())
    data.update(authenticated=True,level='hsk1')
    data['user']={'name':'Fixture','avatar':'阿','language':'uz','is_paid':True,'state':'PRO_ACTIVE','onboarding_completed':True}
    def serve(route):
        path=urlparse(route.request.url).path
        if path=='/iphone-pwa/course':route.fulfill(content_type='text/html',body=pwa_document())
        elif path=='/api/v3/pwa-auth/session':route.fulfill(json={'ok':True,'user_id':31,'csrf':'test-csrf'})
        elif path=='/api/v3/pwa/map':route.fulfill(json=data,headers={'X-HSK-PWA-User-ID':'31'})
        elif path.startswith('/api/'):route.fulfill(status=404,json={'ok':False})
        else:_serve_static(route)
    with sync_playwright() as playwright:
        browser=getattr(playwright,os.getenv('PWA_E2E_ENGINE','chromium')).launch()
        try:
            page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,reduced_motion='reduce')
            page.add_init_script(AUDIO_FIXTURE)
            page.route(BASE_URL+'/**',serve)
            page.goto(BASE_URL+'/iphone-pwa/course?lang=uz&onboarded=1',wait_until='domcontentloaded')
            page.locator('#s-course .uban').first.wait_for()
            page.locator('#nav button[data-s=mashq]').click()
            page.locator('#m-ready-phrases').click()
            frame=page.locator('#resource-phrases iframe').element_handle().content_frame()
            frame.locator('.phrase-play').first.wait_for()
            assert frame.locator('#back').is_visible()
            _phrase_audio_source(frame)
            frame.locator('#query').fill('ni hao')
            frame.locator('.phrase-toggle').first.click()
            frame.locator('.phrase-play').first.click()
            frame.wait_for_function("document.querySelector('.phrase-play').getAttribute('aria-pressed')==='true'")
            frame.evaluate("document.body.dataset.retained='yes'")
            page.evaluate('RESOURCE.close()')
            assert frame.evaluate('window.__phraseAudio[0].paused')
            assert frame.locator('.phrase-play[aria-pressed=true]').count()==0
            page.locator('#m-ready-phrases').click()
            assert frame.evaluate('document.body.dataset.retained')=='yes'
            assert frame.locator('#query').input_value()=='ni hao'
            assert frame.locator('.phrase-toggle').first.get_attribute('aria-expanded')=='true'
            frame.locator('#back').click()
            assert page.locator('#resourceov.on').count()==0
        finally:
            browser.close()
