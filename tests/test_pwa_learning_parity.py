"""Canonical PWA foundation, existing ad caps and compact feedback integration."""
import asyncio
import hashlib
import hmac
import json
import time
import unittest
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

import tests.test_pwa_browser_auth as fixture
from app.api.miniapp_ads import create_miniapp_ads_router
from app.db.models.bot_feedback import BotFeedback
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.course_progress import CourseProgress
from app.db.models.course_ad import CourseAdView
from app.db.models.user import User
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.course_miniapp_admin_analytics_service import build_foundation_metrics
from app.services.ad_placement_service import AdPlacementService
from app.services.course_ad_service import CourseAdService
from app.admin_api.pwa_feedback_analytics import feedback_analytics, FeedbackAnalyticsRequest
from tests.test_ad_placement_service import _creative


class PwaLearningParityTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixture.PwaBrowserAuthTests.asyncSetUp
    asyncTearDown = fixture.PwaBrowserAuthTests.asyncTearDown
    begin = fixture.PwaBrowserAuthTests.begin
    callback = fixture.PwaBrowserAuthTests.callback

    async def login(self):
        await self.callback(await self.begin())
        me = (await self.client.get('/api/v3/pwa-auth/session')).json()
        return {'Origin': fixture.ORIGIN, 'X-HSK-PWA-CSRF': me['csrf']}

    def telegram_headers(self):
        values = {'auth_date': str(int(time.time())), 'user': json.dumps({'id': 1001})}
        secret = hmac.new(b'WebAppData', self.settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        check = '\n'.join(f'{k}={v}' for k, v in sorted(values.items()))
        values['hash'] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        return {'X-Telegram-Init-Data': urlencode(values)}

    async def test_foundation_pwa_telegram_and_android_service_share_one_committed_result(self):
        headers = await self.login()
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.level = 'beginner'
            db.add(fixture.user(2, None))
            await db.commit()
        denied = await self.client.post('/api/v3/pwa/lesson/start', headers=headers,
            json={'lesson_id': 1, 'level': 'hsk1'})
        self.assertEqual(denied.status_code, 403, denied.text)
        self.assertEqual(denied.json()['error'], 'android_foundation_required')
        event_path = '/api/v3/pwa/event'
        for payload in [
            {'event': 'foundation_started', 'foundation_id': 'starter0_hsk1', 'foundation_version': 1, 'dedupe_key': 'f:start'},
            {'event': 'interaction_completed', 'foundation_version': 1, 'objective_id': 'meaning', 'card_id': 'meaning-choice', 'attempt': 1, 'guided': False, 'correct': True, 'dedupe_key': 'f:answer'},
        ]:
            for _ in range(2):
                response = await self.client.post(event_path, headers=headers, json=payload)
                self.assertTrue(response.json()['ok'], response.text)
        payload = {'foundation_id': 'starter0_hsk1', 'foundation_version': 1,
                   'speaking_bonus': False, 'event_id': 'pwa:finish'}
        path = '/api/v3/pwa/lesson/foundation/complete'
        response = await self.client.post(path, headers=headers, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers['x-hsk-pwa-user-id'], '1')
        self.assertTrue(response.json()['foundation']['completed'])
        started = await self.client.post('/api/v3/pwa/lesson/start', headers=headers,
            json={'lesson_id': 1, 'level': 'hsk1'})
        self.assertEqual(started.status_code, 200, started.text)
        allowed = await self.client.get('/api/v3/pwa/lesson/content/hsk1/1')
        self.assertEqual(allowed.status_code, 200, allowed.text)

        # Lost ACK and a new device's intent must both return the stored result.
        for event_id in ['pwa:finish', 'pwa:other-device']:
            retry = await self.client.post(path, headers=headers, json={**payload, 'event_id': event_id})
            self.assertTrue(retry.json()['duplicate'])
        telegram = await self.client.post('/api/v3/lesson/foundation/complete',
            headers=self.telegram_headers(), json={**payload, 'event_id': 'telegram:finish'})
        self.assertTrue(telegram.json()['duplicate'], telegram.text)
        async with self.sessions() as db:
            service = CourseMiniAppProfileService(db)
            native = await service.complete_foundation(await db.get(User, 1),
                **payload, source='android_course')
            self.assertTrue(native['duplicate'])
            self.assertFalse((await service.foundation_status(await db.get(User, 2)))['completed'])
            events = (await db.execute(select(Event).where(Event.user_id == 1, Event.event_name.in_(['foundation_started', 'interaction_completed', 'foundation_completed'])).order_by(Event.id))).scalars().all()
        self.assertEqual([e.event_name for e in events], ['foundation_started', 'interaction_completed', 'foundation_completed'])
        self.assertTrue(all(e.source == 'pwa_course_v3' for e in events))
        rows = [(e.event_name, 'user:1', e.source, e.level, e.lesson_order, e.payload_json, e.created_at) for e in events]
        metrics = build_foundation_metrics(rows, now=datetime.now(timezone.utc))
        self.assertEqual(metrics['started_users'], 1)
        self.assertEqual(metrics['completed_users'], 1)

    async def test_foundation_auth_version_and_failure_never_acknowledge_success(self):
        path = '/api/v3/pwa/lesson/foundation/complete'
        payload = {'foundation_id': 'starter0_hsk1', 'foundation_version': 1, 'event_id': 'finish'}
        self.assertEqual((await self.client.post(path, headers={'Origin': fixture.ORIGIN}, json=payload)).status_code, 401)
        headers = await self.login()
        for change, expected in [({'foundation_version': 2}, 409), ({'foundation_version': '1'}, 409), ({'user_id': 2}, 422)]:
            self.assertEqual((await self.client.post(path, headers=headers, json={**payload, **change})).status_code, expected)
        self.assertEqual((await self.client.post(path, headers={**headers, 'Origin': 'https://evil.test'}, json=payload)).status_code, 403)
        self.assertEqual((await self.client.post(path, headers={'Origin': fixture.ORIGIN}, json=payload)).status_code, 403)
        with patch('app.services.course_miniapp_analytics_service.CourseMiniAppAnalyticsService.record_server_event',
                   new=AsyncMock(return_value={'ok': False})):
            failed = await self.client.post(path, headers=headers, json=payload)
        self.assertEqual(failed.status_code, 503, failed.text)
        async with self.sessions() as db:
            self.assertFalse((await CourseMiniAppProfileService(db).foundation_status(await db.get(User, 1)))['completed'])
        for name in ['foundation_completed', 'subscription_approved', 'lesson_completed']:
            rejected = await self.client.post('/api/v3/pwa/event', headers=headers, json={'event': name})
            self.assertEqual(rejected.status_code, 422)

    async def test_google_only_completion_has_canonical_owner_and_malformed_events_are_rejected(self):
        headers = await self.login()
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.telegram_id = None
            await db.commit()
        payload = {'foundation_id': 'starter0_hsk1', 'foundation_version': 1, 'event_id': 'google:finish'}
        result = await self.client.post('/api/v3/pwa/lesson/foundation/complete', headers=headers, json=payload)
        self.assertEqual(result.status_code, 200, result.text)
        async with self.sessions() as db:
            row = (await db.execute(select(Event).where(Event.event_name == 'foundation_completed'))).scalar_one()
            self.assertEqual(row.user_id, 1)
            self.assertIsNone(row.telegram_id)
        for event in [[], {}, 4, None]:
            response = await self.client.post('/api/v3/pwa/event', headers=headers, json={'event': event})
            self.assertEqual(response.status_code, 422)
        telemetry = await self.client.post('/api/v3/pwa/event', headers=headers, json={
            'event': 'interaction_completed', 'lesson_id': '²', 'source': 'android',
            'entry_level': 'fake', 'transport': 'android', 'client': 'android', 'dedupe_key': 'f:bad-metadata',
        })
        self.assertEqual(telemetry.status_code, 200)
        async with self.sessions() as db:
            row = (await db.execute(select(Event).where(Event.event_name == 'interaction_completed'))).scalar_one()
            self.assertIsNone(row.lesson_order)
            self.assertEqual(row.source, 'pwa_course_v3')
            self.assertEqual(json.loads(row.payload_json)['transport'], 'iphone_pwa')
            self.assertNotIn('client', json.loads(row.payload_json))

    async def test_pwa_ads_use_existing_settings_and_cross_client_daily_cap(self):
        self.client._transport.app.include_router(create_miniapp_ads_router(session_factory=self.sessions, settings_obj=self.settings))
        headers = await self.login()
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.language = 'ru'
            db.add(_creative(1, placements='screen_center,lesson_end', language='uz'))
            await db.commit()
        with patch.object(CourseAdService, 'ensure_media_available', new=AsyncMock(return_value=(True, ''))):
            response = await self.client.get('/api/v3/pwa/ad?placement=screen_center&lang=uz')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['ad']['id'], 1)
            view = {'ad_id': 1, 'placement': 'screen_center', 'watched_seconds': 5, 'lesson_order': 0, 'lang': 'uz'}
            no_csrf = await self.client.post('/api/v3/pwa/ad/view', headers={'Origin': fixture.ORIGIN}, json=view)
            self.assertEqual(no_csrf.status_code, 403)
            saved = await self.client.post('/api/v3/pwa/ad/view', headers=headers, json=view)
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertIsNone((await self.client.get('/api/v3/pwa/ad?placement=screen_center')).json()['ad'])
            async with self.sessions() as db:
                owner = await db.get(User, 1)
                self.assertIsNone(await AdPlacementService(db).next_ad(owner, placement='screen_center', client='android', language='uz'))
                rows = (await db.execute(select(CourseAdView))).scalars().all()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].user_id, 1)

    async def test_compact_context_feedback_reuses_bot_record_reward_and_admin_categories(self):
        headers = await self.login()
        context = {'kind': 'lesson', 'level': 'hsk1', 'lesson_id': 1}
        path = '/api/v3/pwa/feedback/ordinary/prepare'
        self.assertEqual((await self.client.post(path, headers=headers, json={'context': context})).status_code, 409)
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.created_at = datetime.now(timezone.utc) - timedelta(days=3)
            db.add(CourseProgress(user_id=1, level='hsk1', completed_lessons_count=1))
            await db.commit()
        prepared = await self.client.post(path, headers=headers, json={'context': context})
        feedback = prepared.json()['ordinary']
        self.assertEqual(feedback['compact'], context)
        again = await self.client.post(path, headers=headers, json={'context': context})
        self.assertIsNone(again.json()['ordinary'], 'same prompt obeys the shared 24h cooldown')
        payload = {'feedback_id': feedback['feedback_id'], 'context': context, 'answer': 'technical', 'comment': 'Audio stopped'}
        with patch('app.services.admin_notify_service.AdminNotifyService.notify_bot_feedback', new=AsyncMock()):
            result = await self.client.post('/api/v3/pwa/feedback/ordinary/submit', headers=headers, json=payload)
            self.assertEqual(result.status_code, 200, result.text)
            repeat = await self.client.post('/api/v3/pwa/feedback/ordinary/submit', headers=headers, json=payload)
            self.assertEqual(repeat.status_code, 409)
        async with self.sessions() as db:
            stored = await db.get(BotFeedback, feedback['feedback_id'])
            self.assertEqual(stored.status, 'completed')
            self.assertEqual(stored.disliked_code, 'context_technical')
            self.assertIn('lesson · hsk1 · 1', stored.disliked_text)
            self.assertIsNotNone(stored.reward_granted_at)
            metrics = await feedback_analytics(db, FeedbackAnalyticsRequest(source='bot'))
            self.assertEqual(metrics['sources'][0]['categories'], [{'category': 'other', 'count': 1}])

    async def test_practice_and_voice_feedback_require_recent_owned_activity(self):
        headers = await self.login()
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.created_at = datetime.now(timezone.utc) - timedelta(days=3)
            db.add(fixture.user(2, None))
            db.add(Event(user_id=2, event_name='voice_started', source='course_voice'))
            await db.commit()
        for kind, event in [('practice', 'card_seen'), ('voice', 'voice_started')]:
            body = {'context': {'kind': kind, 'level': 'hsk1'}}
            path = '/api/v3/pwa/feedback/ordinary/prepare'
            self.assertEqual((await self.client.post(path, headers=headers, json=body)).status_code, 409)
            async with self.sessions() as db:
                db.add(Event(user_id=1, event_name=event, source='course_voice' if kind == 'voice' else 'pwa_course_v3',
                    payload_json=json.dumps({'card_type':'practice_entry'}, separators=(',', ':')) if kind == 'practice' else None))
                # Clean only this synthetic pending prompt to test each context independently.
                from sqlalchemy import delete
                await db.execute(delete(BotFeedback))
                await db.commit()
            result = await self.client.post(path, headers=headers, json=body)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()['ordinary']['compact']['kind'], kind)

    async def test_bot_questionnaire_free_answers_keep_canonical_codes_and_single_reward(self):
        headers = await self.login()
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.created_at = datetime.now(timezone.utc) - timedelta(days=3)
            owner.telegram_id = None
            db.add(fixture.user(2, None))
            db.add(CourseProgress(user_id=1, level='hsk1', completed_lessons_count=1))
            await db.commit()
        context = {'kind': 'lesson', 'level': 'hsk1', 'lesson_id': 1}
        path = '/api/v3/pwa/feedback/ordinary/prepare'
        response = await self.client.post(path, headers=headers, json={'context': context, 'presentation': 'bot'})
        self.assertEqual(response.status_code, 200, response.text)
        feedback = response.json()['ordinary']
        self.assertEqual(feedback['presentation'], 'bot')
        self.assertIsNone(feedback['compact'])
        self.assertFalse(feedback['paid'])
        self.assertIn('practice', [x['code'] for x in feedback['choices']['liked']])
        self.assertIn('limits', [x['code'] for x in feedback['choices']['disliked']])
        self.assertIsNone((await self.client.post(path, headers=headers,
            json={'context': context, 'presentation': 'bot'})).json()['ordinary'])
        payload = {'feedback_id': feedback['feedback_id'], 'liked_code': 'practice',
                   'liked_sub_code': 'daily', 'disliked_code': 'limits'}
        with patch('app.services.admin_notify_service.AdminNotifyService.notify_bot_feedback', new=AsyncMock()) as notice:
            accepted = await self.client.post('/api/v3/pwa/feedback/ordinary/submit', headers=headers, json=payload)
            self.assertEqual(accepted.status_code, 200, accepted.text)
            self.assertEqual(notice.await_count, 1)
            async with self.sessions() as db:
                end = (await db.get(User, 1)).end_date
            retry = await self.client.post('/api/v3/pwa/feedback/ordinary/submit', headers=headers, json=payload)
            self.assertEqual(retry.status_code, 409)
            self.assertEqual(notice.await_count, 1)
        async with self.sessions() as db:
            stored = await db.get(BotFeedback, feedback['feedback_id'])
            self.assertEqual((stored.user_id, stored.telegram_id, stored.liked_code, stored.disliked_code),
                             (1, None, 'practice', 'limits'))
            self.assertIsNotNone(stored.reward_granted_at)
            self.assertIsNotNone(stored.price_offer_due_at)
            self.assertEqual((await db.get(User, 1)).end_date, end)
            metrics = await feedback_analytics(db, FeedbackAnalyticsRequest(source='bot'))
            self.assertEqual(metrics['sources'][0]['categories'], [{'category': 'limits', 'count': 1}])
            self.assertEqual(len((await db.scalars(select(BotFeedback))).all()), 1)

    async def test_bot_questionnaire_paid_value_and_reason_preserve_subscription(self):
        headers = await self.login()
        expires = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=30)
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.created_at = datetime.now(timezone.utc) - timedelta(days=3)
            owner.status = 'active'
            owner.payment_status = 'approved'
            owner.selected_plan_type = '1_month'
            owner.start_date = expires - timedelta(days=30)
            owner.end_date = expires
            db.add(Event(user_id=1, event_name='voice_started', source='course_voice'))
            await db.commit()
        path = '/api/v3/pwa/feedback/ordinary/prepare'
        response = await self.client.post(path, headers=headers,
            json={'context': {'kind': 'voice', 'level': 'hsk1'}, 'presentation': 'bot'})
        feedback = response.json()['ordinary']
        self.assertTrue(feedback['paid'])
        self.assertIn('useful', [x['code'] for x in feedback['choices']['paid']])
        self.assertIn('lessons', [x['code'] for x in feedback['choices']['paid_sub_positive']])
        payload = {'feedback_id': feedback['feedback_id'], 'paid_code': 'useful', 'paid_sub_code': 'lessons'}
        with patch('app.services.admin_notify_service.AdminNotifyService.notify_bot_feedback', new=AsyncMock()) as notice:
            accepted = await self.client.post('/api/v3/pwa/feedback/ordinary/submit', headers=headers, json=payload)
            self.assertEqual(accepted.status_code, 200, accepted.text)
            self.assertEqual(notice.await_args.kwargs['feedback'].liked_code, 'paid_useful')
        async with self.sessions() as db:
            stored = await db.get(BotFeedback, feedback['feedback_id'])
            self.assertEqual((stored.status, stored.liked_code, stored.disliked_code),
                             ('completed', 'paid_useful', 'paid_lessons'))
            self.assertIsNone(stored.reward_granted_at)
            self.assertIsNone(stored.price_offer_due_at)
            owner = await db.get(User, 1)
            self.assertEqual(owner.end_date.replace(tzinfo=timezone.utc), expires)
            self.assertEqual(owner.selected_plan_type, '1_month')

    async def _check_telegram_feedback_continuation(self, *, clients, attempts=1):
        from app.api.android_features import create_android_features_router
        from app.repositories.bot_feedback_repo import BotFeedbackRepository
        from app.services.bot_feedback_service import BotFeedbackService
        from app.services.desktop_auth_service import DesktopAuthService

        pwa_headers = await self.login()
        self.client._transport.app.include_router(create_android_features_router(
            session_factory=self.sessions, settings_obj=self.settings,
        ))
        body = {'context': {'kind': 'voice', 'level': 'hsk1'}, 'presentation': 'bot'}
        async with self.sessions() as db:
            auth = DesktopAuthService(db, self.settings)
            link = await auth.start_link(platform='android', app_version='1.1.0', installation_key='i' * 48)
            await auth.approve_link(display_code=link['display_code'], telegram_id=1001)
            native = await auth.poll_link(
                link_request_id=link['link_request_id'], polling_secret=link['polling_secret'],
            )
            owner = await db.get(User, 1)
            owner.created_at = datetime.now(timezone.utc) - timedelta(days=3)
            db.add(Event(user_id=1, event_name='voice_started', source='course_voice'))
            repo = BotFeedbackRepository(db)
            pending = await repo.create_pending(owner)
            for index in range(attempts):
                await repo.mark_prompt_sent(pending, 100 + index)
            await db.commit()
            feedback_id = pending.id
            self.assertFalse(BotFeedbackService(db)._is_prompt_due(pending, datetime.now(timezone.utc)))

        routes = {
            'pwa': ('/api/v3/pwa/feedback/ordinary', pwa_headers),
            'android': ('/api/v3/android/feedback', {'Authorization': 'Bearer ' + native['access_token']}),
        }

        async def prepare(client):
            path, headers = routes[client]
            result = await self.client.post(path + '/prepare', headers=headers, json=body)
            self.assertEqual(result.status_code, 200, result.text)
            return client, result.json()['ordinary']

        # A legacy compact client must not take the Telegram continuation.
        legacy = await self.client.post(routes['pwa'][0] + '/prepare', headers=pwa_headers,
                                        json={'context': body['context']})
        self.assertIsNone(legacy.json()['ordinary'])
        responses = await asyncio.wait_for(asyncio.gather(*(prepare(client) for client in clients)), timeout=25)
        available = [(client, ordinary) for client, ordinary in responses if ordinary is not None]
        self.assertEqual(len(available), 1, 'one app can resume the same Telegram invite')
        client, ordinary = available[0]
        self.assertEqual(ordinary['feedback_id'], feedback_id)
        self.assertFalse(ordinary['paid'])
        for transport in routes:
            self.assertIsNone((await prepare(transport))[1])

        async with self.sessions() as db:
            row = await db.get(BotFeedback, feedback_id)
            self.assertEqual((row.prompt_attempts, row.prompt_message_id), (attempts, 99 + attempts))
            self.assertEqual(row.status, 'pending')
            self.assertIsNone(row.reward_granted_at)

        answer = {'feedback_id': feedback_id, 'liked_code': 'practice',
                  'liked_sub_code': 'daily', 'disliked_code': 'limits'}
        path, headers = routes[client]
        with patch('app.services.admin_notify_service.AdminNotifyService.notify_bot_feedback', new=AsyncMock()):
            saved = await self.client.post(path + '/submit', headers=headers, json=answer)
        self.assertEqual(saved.status_code, 200, saved.text)
        for transport in routes:
            self.assertIsNone((await prepare(transport))[1])
        async with self.sessions() as db:
            rows = (await db.scalars(select(BotFeedback))).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].status, 'completed')
            self.assertIsNotNone(rows[0].reward_granted_at)
            owner = await db.get(User, 1)
            self.assertIsNone(await BotFeedbackService(db)._get_or_create_due_feedback(
                owner, datetime.now(timezone.utc),
            ))

    async def test_pwa_resumes_the_unanswered_telegram_prompt_once(self):
        await self._check_telegram_feedback_continuation(clients=('pwa',))

    async def test_android_resumes_the_unanswered_telegram_prompt_once(self):
        await self._check_telegram_feedback_continuation(clients=('android',))

    async def test_bot_questionnaire_resumes_partial_bot_answer_without_replacing_it(self):
        from app.repositories.bot_feedback_repo import BotFeedbackRepository
        headers = await self.login()
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.created_at = datetime.now(timezone.utc) - timedelta(days=3)
            db.add(Event(user_id=1, event_name='voice_started', source='course_voice'))
            repo = BotFeedbackRepository(db)
            pending = await repo.create_pending(owner)
            await repo.save_liked(pending, 'practice', 'Daily practice')
            await db.commit()
            feedback_id = pending.id
        path = '/api/v3/pwa/feedback/ordinary/prepare'
        context = {'kind': 'voice', 'level': 'hsk1'}
        legacy = await self.client.post(path, headers=headers, json={'context': context})
        self.assertIsNone(legacy.json()['ordinary'])
        response = await self.client.post(path, headers=headers, json={'context': context, 'presentation': 'bot'})
        feedback = response.json()['ordinary']
        self.assertEqual(feedback['feedback_id'], feedback_id)
        self.assertEqual(feedback['liked_code'], 'practice')
        payload = {'feedback_id': feedback_id, 'liked_code': 'course',
                   'liked_sub_code': 'lessons', 'disliked_code': 'limits'}
        denied = await self.client.post('/api/v3/pwa/feedback/ordinary/submit', headers=headers, json=payload)
        self.assertEqual(denied.status_code, 409)
        invalid = await self.client.post(path, headers=headers, json={'context': context, 'presentation': 'unknown'})
        self.assertEqual(invalid.status_code, 422)

    async def test_bot_questionnaire_skips_partial_answers_after_paid_status_changes(self):
        from app.repositories.bot_feedback_repo import BotFeedbackRepository
        headers = await self.login()
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.created_at = datetime.now(timezone.utc) - timedelta(days=3)
            db.add(Event(user_id=1, event_name='voice_started', source='course_voice'))
            pending = await BotFeedbackRepository(db).create_pending(owner)
            await db.commit()
            feedback_id = pending.id
        for paid, original in [(True, 'practice'), (False, 'paid_useful')]:
            with self.subTest(paid=paid):
                async with self.sessions() as db:
                    owner = await db.get(User, 1)
                    owner.status = 'active' if paid else 'free'
                    owner.payment_status = 'approved' if paid else 'none'
                    owner.end_date = datetime.now(timezone.utc) + timedelta(days=30) if paid else None
                    pending = await db.get(BotFeedback, feedback_id)
                    pending.liked_code = original
                    await db.commit()
                response = await self.client.post('/api/v3/pwa/feedback/ordinary/prepare', headers=headers,
                    json={'context': {'kind': 'voice', 'level': 'hsk1'}, 'presentation': 'bot'})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIsNone(response.json()['ordinary'], 'do not open an unanswerable form after a subscription change')
                async with self.sessions() as db:
                    pending = await db.get(BotFeedback, feedback_id)
                    self.assertEqual(pending.liked_code, original)
                    self.assertEqual(pending.prompt_attempts, 0)
                    self.assertIsNone(pending.reward_granted_at)
