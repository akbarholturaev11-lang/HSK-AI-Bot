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
        self.owner_id = 31
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
        self.lesson_completions = []
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
            route.fulfill(json={'ok': True, 'user_id': self.owner_id, 'csrf': 'test-csrf'})
        elif path == '/api/v3/pwa/map':
            route.fulfill(json=self.data, headers={'X-HSK-PWA-User-ID': str(self.owner_id)})
        elif path == '/api/v3/pwa/lesson/foundation':
            route.fulfill(json={'ok': True, 'foundation': self.foundation})
        elif path == '/api/v3/pwa/event':
            self.events.append(route.request.post_data_json)
            route.fulfill(json={'ok': True})
        elif path == '/api/v3/pwa/lesson/complete':
            assert route.request.headers.get('x-hsk-pwa-csrf') == 'test-csrf'
            self.lesson_completions.append(route)
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
            route.fulfill(headers={'X-HSK-PWA-User-ID': str(self.owner_id)}, json={'ok': True, 'ad': {
                'id': 1, 'title': 'HSK AI', 'media_type': 'photo',
                'media_url': '/assets/pwa/icon-192.png', 'media_available': True,
                'placement': placement, 'skip_after_seconds': 0,
            } if self.offer_ads else None})
        elif path == '/api/v3/pwa/ad/view':
            self.ad_views.append(route.request.post_data_json)
            assert route.request.headers.get('x-hsk-pwa-csrf') == 'test-csrf'
            route.fulfill(json={'ok': True})
        elif path == '/api/v3/pwa/voice/me':
            # The verified owner's own quota. An unowned reply is the
            # actor-changed logout path (location.replace), which races the
            # session re-check and fails WebKit runs at random.
            route.fulfill(headers={'X-HSK-PWA-User-ID': str(self.owner_id)},
                          json={'ok': True, 'remaining_voice_limit': -1 if self.paid else 3})
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
            question_key = 'pwaFeedback.paidQ' if paid else 'pwaFeedback.likedQ'
            expected_heading = page.evaluate('(key)=>courseMessage(key, "")', question_key)
            assert root.locator('#hsk-pwa-feedback-title').inner_text() == expected_heading
            assert root.locator('.hsk-pwa-feedback-question').count() == 0
            background = root.locator('[role="dialog"]').evaluate('(node)=>getComputedStyle(node).backgroundColor')
            assert background.startswith('rgb(') or background.endswith(', 1)'), 'background text must not show through the question'
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


@pytest.mark.parametrize('lang, chip', [('ru', 'Урок 1 · Часть 2'), ('uz', '1-dars · 2-qism'), ('tj', 'Дарси 1 · Қисми 2')])
def test_completed_part_continues_to_one_line_next_part_sheet(lang, chip):
    """Lesson done -> streak -> Continue opens the next part's sheet; feedback waits for its close."""
    fixture = LearningPage(lang=lang)
    # Exercise a genuinely short line before the explicitly long fitting case.
    fixture.data['units'][0]['lessons'][1].update(zh='你们 · 对不起', py='nǐmen · duìbuqǐ')
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv('PWA_E2E_ENGINE', 'chromium')).launch()
        try:
            page = fixture.open(browser)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.evaluate("""() => {
                refreshCourseProgress=()=>Promise.resolve(true);
                applyLessonDone(allLessons()[0], {ok:true,duplicate:false,completed_lessons_count:1,
                  gamification:{awarded_xp:25,xp:25,streak:1,previous_streak:0,streak_updated:true,
                    local_date:'2026-11-16',week_start:'2026-11-16',week_activity_dates:['2026-11-16'],daily_xp:25}});
            }""")
            page.wait_for_function('''document.querySelector("#levelup.on") &&
                document.querySelector("#lu-cta").getAttribute("onclick").endsWith("App.showStreakScreen('next')")''')
            page.locator('#lu-cta').click()
            page.wait_for_function('document.querySelector("#lu-cta").getAttribute("onclick") === "App.openCheckpointNext()"')
            page.locator('#lu-cta').click()
            head = page.locator('#sheet.on .shead')
            head.wait_for()
            assert head.locator('[role="heading"]').inner_text() == chip
            assert head.locator('.tr').count() == 0
            assert '你好 · nǐ hǎo' not in head.inner_text()
            assert page.locator('#sheet.on .scta').count() == 1
            page.wait_for_timeout(1200)
            assert fixture.prepares == [], 'lesson feedback must not cover the next part sheet'

            def lines():
                return page.evaluate("""() => [...document.querySelectorAll('#sheet.on .shead .fit1')].map(el => {
                  const fs=parseFloat(getComputedStyle(el).fontSize), text=document.createRange();
                  text.selectNodeContents(el);  // exact width: no clipped "…" at the end
                  return {fs, oneLine: el.getBoundingClientRect().height < fs*1.6,
                    fits: text.getBoundingClientRect().width <= el.getBoundingClientRect().width};
                })""")
            short = lines()
            # Short lines keep their normal size (never grow; WebKit may trim
            # half a pixel at the 1px safety margin).
            assert 33 <= short[0]['fs'] <= 34 and 14 <= short[1]['fs'] <= 15
            assert all(line['oneLine'] and line['fits'] for line in short)
            page.evaluate("""() => {const l=allLessons()[1]; l.zh='熟悉 · 不仅 · 性格 · 开玩笑 · 一直 · 互相';
                l.py='shúxī · bùjǐn · xìnggé · kāi wánxiào · yìzhí · hùxiāng · xíguàn'; openLessonSheet(1)}""")
            long = lines()
            assert 14 <= long[0]['fs'] < 34 and 10 <= long[1]['fs'] < 15
            assert all(line['oneLine'] and line['fits'] for line in long)

            page.evaluate('App.closeSheet()')
            page.wait_for_timeout(1500)
            assert [p['context'] for p in fixture.prepares] == [{'kind': 'lesson', 'level': 'hsk1', 'lesson_id': 1}], \
                'closing the sheet returns to the map with the usual feedback'
            assert errors == []
        finally:
            browser.close()


def _submit_first_part_result(page):
    # Start from the final lesson card and exercise the actual save/render path.
    with page.expect_request('**/api/v3/pwa/lesson/complete'):
        page.evaluate("""() => {
            document.querySelector('#flow').classList.add('on');
            Object.assign(Flow, {lessonIdx: 0, exitRequired: [], graded: 2, correct: 1,
                                 startedAt: Date.now() - 21000});
            flowDone();
        }""")


@pytest.mark.parametrize('lang,width', [('uz', 320), ('ru', 390), ('tj', 430)])
def test_confirmed_learning_result_renders_verified_topic_and_review(lang, width):
    fixture = LearningPage(lang=lang)
    course_copy = json.loads((STATIC.parent.parent / f'localization/ui/{lang}/course.json')
                             .read_text())['messages']
    topic = fixture.data['units'][0]['lessons'][0]
    # An oversized word plus quoted markup tests scrolling and text escaping.
    prompt = '你好 <img onerror="throw Error(1)"> & nǐ hǎo'
    correction = '你' * 175 + ' & nǐ'
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv('PWA_E2E_ENGINE', 'chromium')).launch()
        try:
            page = fixture.open(browser, width)
            if width == 320:
                page.set_viewport_size({'width': width, 'height': 480})
            requests = []
            errors = []
            page.on('request', lambda request: requests.append(urlsplit(request.url).path))
            page.on('pageerror', lambda error: errors.append(str(error)))
            _submit_first_part_result(page)
            assert not page.locator('#levelup.on').count()
            assert len(fixture.lesson_completions) == 1
            assert fixture.lesson_completions[0].request.post_data_json['lesson_id'] == 1
            assert not page.locator('.lu-learning-topic').count()
            fixture.data['progress']['completed'] = 1
            fixture.lesson_completions[0].fulfill(json={
                'ok': True, 'completed_lessons_count': 1, 'gamification': {'awarded_xp': 20},
                'learning_result': {'review': {'prompt': prompt, 'correction': correction}},
            })
            result = page.locator('#levelup.on')
            result.locator('.lu-review-correction').wait_for()
            page.wait_for_function('PROGRESS_REFRESH === null')
            assert result.locator('h2').inner_text() == course_copy['levelUp.lessonH']
            assert result.locator('.lu-learning-topic span').all_inner_texts() == [
                topic['tr'][lang], topic['zh'], topic['py'],
            ]
            assert '50%' in result.locator('.lu-rewards').inner_text()
            assert result.locator('.lu-learning-review strong').inner_text() == course_copy['learningResult.review']
            assert result.locator('.lu-review-prompt').inner_text() == prompt
            assert result.locator('.lu-review-correction').inner_text() == correction
            assert result.locator('.lu-learning-review img').count() == 0
            assert result.locator('.lu-result-note').inner_text() == course_copy['learningResult.reviewHint']
            assert result.get_by_role('button').count() == 1
            action = result.locator('#lu-cta')
            assert action.inner_text().strip() == course_copy['learningResult.continue']
            stage = result.locator('#lu-stage')
            geometry = stage.evaluate("""el => ({
                  width: el.clientWidth, scrollWidth: el.scrollWidth,
                  height: el.clientHeight, scrollHeight: el.scrollHeight,
            })""")
            assert geometry['scrollWidth'] == geometry['width']
            if width == 320:
                assert geometry['scrollHeight'] > geometry['height']
                before = capture_geometry(page, {'continue': '#lu-cta'})
                stage.evaluate('el => { el.scrollTop = el.scrollHeight; }')
                assert stage.evaluate('el => el.scrollTop') > 0
                assert_reserved_layout(before, capture_geometry(page, {'continue': '#lu-cta'}))
            assert action.bounding_box()['height'] >= 44
            assert requests.count('/api/v3/pwa/map') == 1
            assert not any('sales-preview' in request for request in requests)
            action.click()
            result.wait_for(state='hidden')
            assert page.locator('.lu-learning-review').count() == 0
            page.locator('#sheet.on .scta').wait_for()
            assert page.locator('#paywall.on').count() == 0
            assert errors == []
        finally:
            browser.close()


@pytest.mark.parametrize('variant', ['no_review', 'legacy', 'retried_duplicate', 'changed_owner'])
def test_learning_result_falls_back_without_current_confirmed_review(variant):
    fixture = LearningPage()
    fixture.data['today'] = {'complete': False, 'goal_xp': 40, 'tasks': [
        {'type': 'mistake_review', 'done': False, 'available': True, 'access': 'open'},
    ]}
    # The first part remains complete even if access to the next part is spent.
    fixture.data['units'][0]['lessons'][1].update(locked_premium=True, completion_allowed=False)
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv('PWA_E2E_ENGINE', 'chromium')).launch()
        try:
            page = fixture.open(browser)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            _submit_first_part_result(page)
            assert not page.locator('#levelup.on').count()
            assert len(fixture.lesson_completions) == 1
            response = {'ok': True, 'completed_lessons_count': 1}
            if variant == 'retried_duplicate':
                original_payload = fixture.lesson_completions[0].request.post_data_json
                fixture.lesson_completions[0].fulfill(status=503, json={
                    'ok': False, 'error': 'temporary', 'learning_result': {'review': None},
                })
                retry = page.locator('#flow.on #f-cta')
                retry.wait_for()
                assert not page.locator('#levelup.on').count()
                assert page.evaluate('MAP.progress.completed') == 0
                with page.expect_request('**/api/v3/pwa/lesson/complete'):
                    retry.click()
                assert not page.locator('#levelup.on').count()
                assert len(fixture.lesson_completions) == 2
                assert fixture.lesson_completions[1].request.post_data_json == original_payload
                response.update(duplicate=True, learning_result={'review': {'prompt': '例子', 'correction': '示例'}})
            elif variant == 'no_review':
                response['learning_result'] = {'review': None}
            elif variant == 'changed_owner':
                response['learning_result'] = {'review': {'prompt': '例子', 'correction': '示例'}}
                # The saved request belonged to the first actor, but the refreshed
                # session/map must describe the replacement already active in this tab.
                fixture.owner_id = 99
                page.evaluate('(owner) => { PWA_COURSE_USER_ID=owner; PWA_COURSE_ACTOR_PROMISE=null; }',
                              fixture.owner_id)
            fixture.data['progress']['completed'] = 1
            fixture.lesson_completions[-1].fulfill(json=response)
            result = page.locator('#levelup.on')
            result.wait_for()
            assert result.locator('.lu-learning-review').count() == 0
            if variant == 'no_review':
                assert result.locator('.lu-learning-topic').count() == 1
                assert result.locator('.lu-result-note').inner_text() == page.evaluate(
                    'courseMessage("learningResult.nextHint", "")',
                )
                result.locator('#lu-cta').click()
                result.wait_for(state='hidden')
                assert page.locator('#s-course .tplan').is_visible()
                assert page.locator('#sheet.on, #paywall.on').count() == 0
            else:
                assert result.locator('.lu-learning-topic, .lu-result-note').count() == 0
            assert errors == []
        finally:
            browser.close()
