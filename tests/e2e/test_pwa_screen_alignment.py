"""Real PWA mobile chrome and list geometry, with local owned API fixtures."""
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from tests.e2e.test_pwa_installed_trial import TrialPage, browser, profile
from tests.e2e.test_pwa_learning_parity import STATIC


class ScreenPage(TrialPage):
    def serve(self, route):
        path = urlsplit(route.request.url).path
        if path == '/iphone-pwa/practice/mistakes':
            route.fulfill(content_type='text/html', path=str(STATIC / 'course_v3_mistakes.html'))
        elif path == '/api/v3/pwa/mistakes':
            route.fulfill(json={'ok': True, 'targets': [
                {'id': i, 'kind': 'word', 'category': 'word', 'zh': '坚持',
                 'pinyin': 'jiānchí', 'meaning': 'Упорно продолжать', 'wrong': 'Сомневаться',
                 'sources': ['test'], 'passed': 0, 'required': 3} for i in range(30)],
                'summary': {'total': 30, 'categories': {'word': 30}},
                'pagination': {'has_more': False}})
        elif path == '/api/v3/native-auth/providers':
            route.fulfill(json={'ok': True, 'providers': []})
        else:
            super().serve(route)


@pytest.mark.parametrize('language', ['uz', 'ru', 'tj'])
@pytest.mark.parametrize('width', [320, 390, 430])
def test_course_voice_profile_headers_and_compact_carousel(browser, language, width):
    fixture = ScreenPage(language)
    page = fixture.open(browser, width)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    headers = {}
    for tab in ('mashq', 'profile', 'voice', 'course'):
        page.locator(f'#nav [data-s="{tab}"]').click()
        root = page.locator(f'#s-{tab} .htop').first
        root.wait_for(state="visible")
        headers[tab] = root.bounding_box()
        if tab == 'profile':
            page.evaluate('HskProfileCarousel.pause()')
            card = page.locator('#hsk-profile-promo-root')
            assert card.bounding_box()['height'] <= 170
            assert page.locator('[data-promo-kind="apps"]').count() == 0
            for kind in ('pro', 'hsk30'):
                page.evaluate('kind => {HskProfileCarousel.select(kind);HskProfileCarousel.pause()}', kind)
                action = page.locator(f'.hp-promo-slide[data-promo-kind="{kind}"] .hp-promo-action')
                assert action.bounding_box()['height'] >= 44
                for dot in card.locator('[data-promo-dot]').all():
                    d, a = dot.bounding_box(), action.bounding_box()
                    assert d['width'] >= 44 and d['height'] >= 44
                    assert a['x'] + a['width'] <= d['x'] + 1
            page.evaluate('scrollTo(0,0)')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    for tab, rect in headers.items():
        assert abs(rect['y'] - headers['mashq']['y']) <= 1, (tab, headers)
        assert abs(rect['height'] - headers['mashq']['height']) <= 1, (tab, headers)
    assert not errors


@pytest.mark.parametrize('language', ['uz', 'ru', 'tj'])
@pytest.mark.parametrize('width', [320, 390, 430])
def test_mistakes_list_reaches_bottom_without_footer_band(browser, language, width):
    fixture = ScreenPage(language)
    page = fixture.open(browser, width)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    # Exercise real non-zero parent insets; the child owns the scroll area.
    page.add_style_tag(content=':root{--safe-t:47px;--safe-b:34px}')
    page.evaluate('RESOURCE.openPractice("/course_v3_mistakes.html?lang="+LANG)')
    frame = page.frame_locator('#pwa-practice-layer iframe')
    frame.locator('#content .item').first.wait_for()
    iframe = page.locator('#pwa-practice-layer iframe')
    page.wait_for_function('!document.querySelector("#pwa-practice-layer iframe").hidden')
    assert iframe.bounding_box()['y'] == 47
    assert abs(iframe.bounding_box()['y'] + iframe.bounding_box()['height'] - page.viewport_size['height']) <= 1
    metrics = frame.locator('#content').evaluate('''el => {
        const sub=document.querySelector('#m-sub'), head=document.querySelector('.top');
        return {bottom:el.getBoundingClientRect().bottom, height:innerHeight,
                headHeight:head.getBoundingClientRect().height,
                subHeight:sub.getBoundingClientRect().height,
                lineHeight:getComputedStyle(sub).lineHeight,
                whiteSpace:getComputedStyle(sub).whiteSpace};
    }''')
    assert abs(metrics['bottom'] - metrics['height']) <= 1
    assert metrics['headHeight'] == 64
    assert metrics['whiteSpace'] == 'nowrap' and metrics['subHeight'] <= 18
    frame.locator('#content').evaluate('el => el.scrollTop=el.scrollHeight')
    last = frame.locator('#content .item').last
    assert last.is_visible()
    assert last.bounding_box()['y'] + last.bounding_box()['height'] <= page.viewport_size['height'] + 1
    directory = os.getenv('HSK_LAYOUT_REVIEW_DIR')
    if directory:
        Path(directory).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(directory) / f'{os.getenv("PWA_E2E_ENGINE", "chromium")}-{width}-{language}-mistakes.png'))
    frame.locator('.top .ix').click()
    assert page.locator('#pwa-practice-layer').count() == 0
    assert not errors
