"""Real course JS on mobile Chromium/WebKit, isolated authenticated API fixtures."""
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

from tests.e2e.test_pwa_progressive_sections import pwa_document, STATIC, ORIGIN
from tests.pwa_layout_geometry import capture_geometry, assert_reserved_layout


class LearningPage:
    def __init__(self, *, lang='uz', required=False, paid=False):
        self.data = json.loads((STATIC / 'course_v3_data/hsk1.json').read_text())
        self.foundation = json.loads((STATIC / 'course_v3_data/hsk1/lesson_01.json').read_text())['foundation']
        self.data.update(authenticated=True, level='hsk1', user={
            'name': 'Verified', 'avatar': '阿', 'language': lang, 'is_paid': paid,
            'state': 'PRO_ACTIVE' if paid else 'FREE', 'onboarding_completed': True,
        }, foundation={'id': 'starter0_hsk1', 'version': 1, 'required': required,
                       'completed': False, 'status': 'required' if required else 'optional'})
        self.data['progress']['completed'] = 0
        self.data['notify'] = {'enabled': True}
        self.events = []
        self.completions = []
        self.prepares = []
        self.submissions = []
        self.ad_views = []
        self.ad_reads = []
        self.available_reads = 0
        self.offer_ads = False
        self.hold_ads = False
        self.held_ads = []
        self.lang = lang
        self.paid = paid
        self.fail_feedback_once = False

    def feedback_choices(self):
        # Use the actual canonical bot labels in all three mobile locales.
        catalog = json.loads((STATIC.parent.parent / f'localization/ui/{self.lang}/bot.json').read_text())['messages']
        def options(prefix, codes):
            return [{'code': code, 'label': catalog[f'texts.feedback_{prefix}_{code}']} for code in codes]
        if self.paid:
            return {'paid': options('paid', ['worth', 'useful', 'unsure', 'regret']),
                    'paid_sub_positive': options('sub', ['lessons', 'voice', 'pronunciation', 'daily', 'other']),
                    'paid_sub_negative': options('sub', ['content', 'slow', 'tech', 'time', 'other'])}
        return {'liked': options('like', ['course', 'voice', 'pronunciation', 'dictionary', 'practice', 'other']),
                'liked_sub': {'course': options('sub', ['lessons', 'exercises', 'voice', 'other']),
                              'practice': options('sub', ['daily', 'memorize', 'quiz', 'other'])},
                'disliked': options('dislike', ['price', 'limits', 'unclear', 'pace', 'other']),
                'disliked_detail_required': ['unclear', 'pace', 'other']}

    def serve(self, route):
        path = urlsplit(route.request.url).path
        if path == '/iphone-pwa/course':
            route.fulfill(content_type='text/html', body=pwa_document())
        elif path == '/iphone-pwa/practice/recognition':
            route.fulfill(content_type='text/html', body='''<body><button id="practice-exit"
                onclick="parent.RESOURCE.closePracticeFrame(window)">Back</button><script>
                parent.RESOURCE.acceptPracticeActor(window,31);
                parent.RESOURCE.revealPracticeFrame(window);
                </script></body>''')
        elif path == '/api/v3/pwa-auth/session':
            route.fulfill(json={'ok': True, 'user_id': 31, 'csrf': 'test-csrf'})
        elif path == '/api/v3/pwa/map':
            route.fulfill(json=self.data, headers={'X-HSK-PWA-User-ID': '31'})
        elif path == '/api/v3/pwa/lesson/foundation':
            route.fulfill(json={'ok': True, 'foundation': self.foundation})
        elif path == '/api/v3/pwa/event':
            self.events.append(route.request.post_data_json)
            route.fulfill(json={'ok': True})
        elif path == '/api/v3/pwa/lesson/foundation/complete':
            assert route.request.headers.get('x-hsk-pwa-csrf') == 'test-csrf'
            self.completions.append(route)
        elif path == '/api/v3/pwa/feedback/ordinary/prepare':
            payload = route.request.post_data_json
            self.prepares.append(payload)
            route.fulfill(json={'ok': True, 'ordinary': {'feedback_id': 71, 'compact': None,
                'presentation': 'bot', 'paid': self.paid, 'choices': self.feedback_choices()}})
        elif path == '/api/v3/pwa/feedback/ordinary/submit':
            self.submissions.append(route.request.post_data_json)
            assert route.request.headers.get('x-hsk-pwa-csrf') == 'test-csrf'
            if self.fail_feedback_once:
                self.fail_feedback_once = False
                route.fulfill(status=503, json={'ok': False, 'error': 'temporary'})
                return
            route.fulfill(json={'ok': True, 'completed': True})
        elif path == '/api/v3/pwa/feedback/available':
            self.available_reads += 1
            route.fulfill(json={'ok': True, 'ordinary': None, 'release': []})
        elif path == '/api/v3/pwa/ad':
            self.ad_reads.append(route.request.url)
            if self.hold_ads:
                self.held_ads.append(route)
                return
            placement = 'lesson_end' if 'placement=lesson_end' in route.request.url else 'screen_center'
            route.fulfill(headers={'X-HSK-PWA-User-ID': '31'}, json={'ok': True, 'ad': {
                'id': 1, 'title': 'HSK AI', 'media_type': 'photo',
                'media_url': '/assets/pwa/icon-192.png', 'media_available': True,
                'placement': placement, 'skip_after_seconds': 0,
            } if self.offer_ads else None})
        elif path == '/api/v3/pwa/ad/view':
            self.ad_views.append(route.request.post_data_json)
            assert route.request.headers.get('x-hsk-pwa-csrf') == 'test-csrf'
            route.fulfill(json={'ok': True})
        elif path.startswith('/api/'):
            route.fulfill(json={'ok': False})
        else:
            file = (STATIC / path.lstrip('/')).resolve()
            if file.is_file() and file.is_relative_to(STATIC.resolve()):
                route.fulfill(path=str(file), content_type=mimetypes.guess_type(file)[0] or 'application/octet-stream')
            else:
                route.fulfill(status=204, body='')

    def open(self, browser, width=390):
        context = browser.new_context(viewport={'width': width, 'height': 844}, is_mobile=True,
                                      reduced_motion='reduce')
        page = context.new_page()
        page.set_default_timeout(15000)
        page.route('**/*', self.serve)
        page.goto(ORIGIN + '/iphone-pwa/course?lang=' + self.lang + '&onboarded=1', wait_until='networkidle')
        page.wait_for_function('window.MAP && MAP.authenticated && window.PWA_COURSE_USER_ID')
        page.locator('#hsk-launch-splash:not(.is-done)').wait_for(state='hidden')
        # Sound providers are unrelated to completion. Keep grading and every
        # real DOM action intact, suppress only narration in this offline fixture.
        page.evaluate('Foundation.stopAudio(); Foundation.scheduleAudio=function(){}; narrate=function(){}; foundationSpeak=function(){}')
        return page


def test_foundation_all_steps_offline_retry_reload_and_acknowledged_completion():
    fixture = LearningPage(required=True)
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv('PWA_E2E_ENGINE', 'chromium')).launch()
        try:
            page = fixture.open(browser)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.wait_for_function('Foundation.active && Foundation.data')
            wrong_once = False
            for _ in range(20):
                card = page.evaluate('Foundation.queue[Foundation.i]')
                if card['type'] == 'result':
                    break
                if card.get('_guided'):
                    page.locator('[onclick="Foundation.guidedCorrect()"]').click()
                    page.locator('#f-barbtn').click()
                elif card['type'] in ('choice', 'listen_choice'):
                    answer = card['correct_index']
                    if not wrong_once:
                        answer = (answer + 1) % len(card['options'])
                        wrong_once = True
                    page.locator(f'#f-body .opt[data-k="{answer}"]').click()
                    page.locator('#f-barbtn').click()
                elif card['type'] == 'builder':
                    for token in card['answer_tokens']:
                        page.locator('#foundation-bank button').filter(has_text=token).first.click()
                    page.locator('#f-barbtn').click()
                elif card['type'] == 'speak':
                    page.locator('[onclick="Foundation.skipSpeak()"]').click()
                else:
                    page.locator('#f-cta').click()
            assert page.evaluate('Foundation.queue.length') == 11
            assert page.evaluate('foundationRequiredMastered()')
            assert not page.evaluate('foundationIsComplete()')
            anchors = {'stage': '#f-stage', 'body': '#f-body', 'action': '#f-cta'}
            before = capture_geometry(page, anchors)
            page.locator('#f-cta').click()
            page.wait_for_function('Foundation.finishing')
            page.evaluate('document.querySelector("#f-cta").click()')
            assert len(fixture.completions) == 1
            assert not page.evaluate('foundationIsComplete()')
            assert_reserved_layout(before, capture_geometry(page, anchors))
            first_payload = fixture.completions[0].request.post_data_json
            fixture.completions[0].abort('internetdisconnected')
            page.wait_for_function('!Foundation.finishing')
            assert page.locator('#flow.on').is_visible()
            assert page.locator('#f-cta').is_enabled()
            assert not page.evaluate('Foundation.completed')
            page.reload(wait_until='networkidle')
            page.locator('#hsk-launch-splash:not(.is-done)').wait_for(state='hidden')
            page.wait_for_function('Foundation.active && Foundation.queue[Foundation.i].type === "result"')
            assert page.evaluate('foundationRequiredMastered()')
            page.locator('#f-cta').click()
            page.wait_for_function('Foundation.finishing')
            assert len(fixture.completions) == 2
            assert fixture.completions[1].request.post_data_json['event_id'] == first_payload['event_id']
            fixture.data['foundation'].update(completed=True, status='completed')
            fixture.completions[1].fulfill(headers={'X-HSK-PWA-User-ID': '31'}, json={
                'ok': True, 'duplicate': True, 'foundation': fixture.data['foundation'],
            })
            page.wait_for_function('!Foundation.active && foundationIsComplete()')
            assert page.evaluate('foundationCachedState("starter0_hsk1",1).completed')
            assert any(e['event'] == 'foundation_started' for e in fixture.events)
            assert len([e for e in fixture.events if e['event'] == 'interaction_completed']) >= 4
            assert errors == []
        finally:
            browser.close()


@pytest.mark.parametrize('lang', ['uz', 'ru', 'tj'])
@pytest.mark.parametrize('width', [320, 390, 430])
@pytest.mark.parametrize('paid', [False, True])
def test_existing_bot_questionnaires_on_practice_and_voice_exit(lang, width, paid):
    fixture = LearningPage(lang=lang, paid=paid)
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv('PWA_E2E_ENGINE', 'chromium')).launch()
        try:
            page = fixture.open(browser, width)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            kind = 'voice' if width == 430 else 'practice'
            if kind == 'practice':
                page.evaluate('App.show("mashq");App.openRecog()')
                page.frame_locator('#pwa-practice-layer iframe').locator('#practice-exit').click()
                assert any(event.get('card_type') == 'practice_entry' for event in fixture.events)
            else:
                page.evaluate('App.show("voice");SECTION=VOICE;closeSection()')
            root = page.locator('#hsk-pwa-feedback-root')
            root.wait_for(state='visible')
            assert len(fixture.prepares) == 1
            assert fixture.prepares[0]['context']['kind'] == kind
            assert fixture.prepares[0]['presentation'] == 'bot'
            assert root.locator('[role="radiogroup"]').count() == 1
            assert root.locator('[role="radio"]').count() == (4 if paid else 6)
            assert root.locator('textarea').count() == 0
            assert root.locator('#hsk-pwa-feedback-submit').is_hidden()
            box = root.locator('[role="dialog"]').bounding_box()
            assert box['x'] >= 0 and box['x'] + box['width'] <= width + 1
            assert abs(box['x'] + box['width']/2 - width/2) < 2
            if lang == 'uz' and width == 390:
                page.screenshot(path=f'/tmp/hsk-pwa-bot-feedback-{"paid" if paid else "free"}.png')
            root.locator('[data-code="useful"]' if paid else '[data-code="practice"]').click()
            assert root.locator('[role="radiogroup"]').count() == 1
            page.evaluate('NavBack.goBack()')
            assert root.locator('[data-code="useful"]' if paid else '[data-code="practice"]').is_visible()
            root.locator('[data-code="useful"]' if paid else '[data-code="practice"]').click()
            root.locator('[data-code="lessons"]' if paid else '[data-code="daily"]').click()
            if not paid:
                assert root.locator('[role="radiogroup"]').count() == 1
                root.locator('[data-code="limits"]').click()
            page.wait_for_function('document.querySelector("#hsk-pwa-feedback-submit").hidden')
            page.wait_for_function('!document.querySelector("#hsk-pwa-feedback-form").children.length')
            assert len(fixture.submissions) == 1
            assert fixture.submissions[0].get('paid_code') == ('useful' if paid else None)
            assert fixture.submissions[0].get('liked_sub_code') == (None if paid else 'daily')
            assert 'answer' not in fixture.submissions[0]
            root.wait_for(state='hidden')
            page.evaluate('queuePwaActivityFeedback({kind:"practice"})')
            page.wait_for_timeout(1100)
            assert len(fixture.prepares) == 1
            assert not root.is_visible()
            available_before = fixture.available_reads
            page.evaluate('HskPwaFeedback.openRelease({canOpen:function(){return true}})')
            page.wait_for_timeout(50)
            assert fixture.available_reads == available_before, 'one automatic feedback prompt per session'
            assert errors == []
        finally:
            browser.close()


def test_bot_questionnaire_other_text_and_failed_write_can_retry():
    fixture = LearningPage()
    fixture.fail_feedback_once = True
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv('PWA_E2E_ENGINE', 'chromium')).launch()
        try:
            page = fixture.open(browser)
            page.evaluate('App.show("voice");SECTION=VOICE;closeSection()')
            root = page.locator('#hsk-pwa-feedback-root')
            root.wait_for(state='visible')
            root.locator('[data-code="other"]').click()
            assert root.locator('textarea').count() == 1
            assert root.locator('#hsk-pwa-feedback-submit').is_disabled()
            root.locator('textarea').fill('Vocabulary')
            root.locator('#hsk-pwa-feedback-submit').click()
            root.locator('[data-code="unclear"]').click()
            root.locator('textarea').fill('Audio stopped')
            root.locator('#hsk-pwa-feedback-submit').click()
            page.wait_for_function('!document.querySelector("#hsk-pwa-feedback-submit").disabled')
            assert len(fixture.submissions) == 1
            assert root.locator('textarea').input_value() == 'Audio stopped'
            root.locator('#hsk-pwa-feedback-submit').click()
            root.wait_for(state='hidden')
            assert fixture.submissions == [fixture.submissions[0], fixture.submissions[0]]
        finally:
            browser.close()


def test_existing_ads_two_placements_use_pwa_transport_and_resume_after_close():
    fixture = LearningPage()
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv('PWA_E2E_ENGINE', 'chromium')).launch()
        try:
            page = fixture.open(browser)
            fixture.offer_ads = True
            page.evaluate('maybeShowAppOpenAd({})')
            ad = page.locator('.caa-app.on')
            ad.wait_for(state='visible')
            ad.locator('.caa-app-x').click()
            page.wait_for_function('!document.querySelector(".caa-app").classList.contains("on")')
            page.evaluate("""() => {
                const celebrate=App.showLevelUp, refresh=refreshCourseProgress;
                App.showLevelUp=function(){}; refreshCourseProgress=()=>Promise.resolve(true);
                try {applyLessonDone(allLessons()[0], {ok:true,duplicate:false,completed_lessons_count:1});}
                finally {App.showLevelUp=celebrate;refreshCourseProgress=refresh;}
                if(window._pendingLessonEndAd!==1)throw Error('PWA saved lesson did not queue its existing ad');
                window.adReturned=0;playLessonEndAd(function(){window.adReturned++});
            }""")
            ad.wait_for(state='visible')
            assert 'lesson-end' in ad.get_attribute('class')
            ad.locator('.caa-app-x').click()
            page.wait_for_function('window.adReturned === 1')
            page.evaluate('CourseAds.closeCenterAd()')
            page.wait_for_timeout(100)
            assert page.evaluate('window.adReturned') == 1
            assert [v['placement'] for v in fixture.ad_views] == ['screen_center', 'lesson_end']
            assert len(page.locator('.caa-app').all()) == 1
        finally:
            browser.close()


def test_foundation_timeout_and_invalid_ack_leave_results_retryable():
    fixture = LearningPage(required=True)
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv('PWA_E2E_ENGINE', 'chromium')).launch()
        try:
            page = fixture.open(browser)
            page.wait_for_function('Foundation.active && Foundation.data')
            page.evaluate('''() => {Foundation.data.required_objectives.forEach(id => Foundation.mastery[id]=true);
                Foundation.i=Foundation.queue.length-1;Foundation.save();Foundation.render();}''')
            page.clock.install()
            page.locator('#f-cta').click()
            page.wait_for_function('Foundation.finishing')
            page.clock.fast_forward(12001)
            page.wait_for_function('!Foundation.finishing')
            assert not page.evaluate('foundationIsComplete()')
            assert page.locator('#f-cta').is_enabled()
            page.locator('#f-cta').click()
            page.wait_for_function('Foundation.finishing')
            fixture.completions[-1].fulfill(headers={'X-HSK-PWA-User-ID': '31'}, json={'ok': True})
            page.wait_for_function('!Foundation.finishing')
            assert not page.evaluate('Foundation.completed')
            assert page.locator('#flow.on').is_visible()
            page.locator('#f-cta').click()
            page.wait_for_function('Foundation.finishing')
            fixture.completions[-1].fulfill(headers={'X-HSK-PWA-User-ID': '99'}, json={
                'ok': True, 'foundation': {**fixture.data['foundation'], 'completed': True},
            })
            page.wait_for_function('!Foundation.finishing')
            assert not page.evaluate('foundationIsComplete()')
            assert page.locator('#f-cta').is_enabled()
            assert len({r.request.post_data_json['event_id'] for r in fixture.completions}) == 1
        finally:
            browser.close()


def test_stalled_lesson_ad_does_not_block_returning_to_course():
    fixture = LearningPage()
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv('PWA_E2E_ENGINE', 'chromium')).launch()
        try:
            page = fixture.open(browser)
            fixture.hold_ads = True
            page.clock.install()
            page.evaluate('window.adReturned=0;window._pendingLessonEndAd=1;playLessonEndAd(function(){window.adReturned++})')
            page.wait_for_function('window._pendingLessonEndAd === 0')
            page.clock.fast_forward(8001)
            page.wait_for_function('window.adReturned === 1')
            assert not page.locator('.caa-app.on').count()
            assert page.locator('#nav').is_visible()
        finally:
            browser.close()
