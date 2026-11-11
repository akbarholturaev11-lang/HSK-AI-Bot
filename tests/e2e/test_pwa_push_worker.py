"""Run committed push/click handler logic in real Chromium and iPhone WebKit JS.

Provider delivery and OS notification chrome require an installed physical PWA;
these checks deliberately stub only those OS interfaces.
"""
import os
from pathlib import Path

import pytest

pw = pytest.importorskip('playwright.sync_api')
WORKER = Path('app/static/iphone-pwa-sw.js').read_text(encoding='utf-8')


@pytest.mark.parametrize('language', ['uz', 'ru', 'tj'])
def test_push_content_and_authenticated_click(language):
    from app.bot.utils.i18n import t
    from app.services.learner_pwa_push_copy import push_copy
    title, body = push_copy(t('trial_expiring_soon', language, days=2), title='', body='')
    with pw.sync_playwright() as playwright:
        browser = getattr(playwright, os.environ.get('PWA_E2E_ENGINE', 'chromium')).launch()
        page = browser.new_page(viewport={'width': 390, 'height': 844})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        result = page.evaluate('''async ({source, payload}) => {
          const handlers = {}, shown = [], opened = [], focused = [], badge = [];
          const store = new Map();
          const cache = {match:async key => store.get(key)?.clone(), put:async (key,value) => store.set(key,value)};
          const sw = {location:{origin:'https://hsk.test'},
            addEventListener:(key,handler) => {handlers[key]=handler;},
            registration:{showNotification:async (title,options) => {shown.push({title,...options});}},
            caches:{}, navigator:{setAppBadge:async n => badge.push(n)},
            clients:{matchAll:async () => [],openWindow:async url => opened.push(url)}};
          new Function('self','caches',source)(sw,{open:async () => cache});
          let pending;
          handlers.push({data:{json:() => payload},waitUntil:p => {pending=p;}});
          await pending;
          handlers.notificationclick({notification:{close:() => {}},waitUntil:p => {pending=p;}});
          await pending;
          sw.clients.matchAll=async () => [{url:'https://hsk.test/iphone-pwa/course',
            navigate:async url => {focused.push(url);return null;},focus:async () => {focused.push('focus');}}];
          handlers.notificationclick({notification:{close:() => {}},waitUntil:p => {pending=p;}});
          await pending;
          return {shown,opened,focused,badge};
        }''', dict(source=WORKER, payload=dict(title=title, body=body, lang=language,
                     tag='hsk-reviewed-event', url='https://evil.test/forged')))
        browser.close()
    assert errors == []
    assert result['shown'][0]['title'] == title
    assert result['shown'][0]['body'] == body
    assert result['shown'][0]['lang'] == ('tg' if language == 'tj' else language)
    assert result['shown'][0]['tag'] == 'hsk-reviewed-event'
    assert result['shown'][0]['data']['url'] == '/iphone-pwa/course?notice=1'
    assert result['opened'] == ['https://hsk.test/iphone-pwa/course?notice=1']
    assert result['focused'] == ['https://hsk.test/iphone-pwa/course?notice=1', 'focus']
    assert result['badge'] == [1]
