"""Admin settings are the live policy, including client transitions and copy."""
import hashlib
import hmac
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlencode
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.user import User
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.message import Message
from app.db.models.voice_practice_session import VoicePracticeSession
from app.api.miniapp_entitlements import create_miniapp_entitlements_router
from app.services.entitlements.engine import EntitlementEngine
from app.services.entitlements.lesson_access import LessonAccessService
from app.services.entitlements.limits_config import LimitConfigService, default_config
from app.services.entitlements.state import EntitlementState
from app.services.entitlements import actions as A
from app.services.course_access_policy_service import CourseAccessPolicyService
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.access_service import AccessService
from app.services.voice_practice_service import VoicePracticeService

TOKEN = 'test-token-only'


def signed(telegram_id=99001):
    fields = {'auth_date': str(int(datetime.now(timezone.utc).timestamp())), 'user': '{"id":%d}' % telegram_id}
    key = hmac.new(b'WebAppData', TOKEN.encode(), hashlib.sha256).digest()
    fields['hash'] = hmac.new(key, '\n'.join(f'{k}={v}' for k, v in sorted(fields.items())).encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


class AdminLimitAuthorityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine('sqlite+aiosqlite:///:memory:', poolclass=StaticPool)
        async with self.db.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)
        self.bot = SimpleNamespace(send_message=AsyncMock())
        self.funnel = patch('app.services.entitlements.engine.EntitlementEngine._record_limit_hit', AsyncMock())
        self.funnel.start()
        self.addCleanup(self.funnel.stop)
        self.shadow = patch('app.api.miniapp_entitlements.shadow_compare_gate', AsyncMock())
        self.shadow.start()
        self.addCleanup(self.shadow.stop)
        async with self.sessions() as session:
            session.add(User(id=1, telegram_id=99001, full_name='Limit test', language='uz',
                             level='hsk4', status='free', payment_status='none'))
            await session.commit()
        app = FastAPI()
        app.include_router(create_miniapp_entitlements_router(session_factory=self.sessions,
                            settings_obj=SimpleNamespace(BOT_TOKEN=TOKEN), bot=self.bot))
        self.http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        await self.http.aclose()
        await self.db.dispose()

    async def rule(self, action, limit, window='daily', state='FREE'):
        async with self.sessions() as session:
            config = (await LimitConfigService(session).get_config()).public_payload()
            config['plans'][state][action] = {'limit': limit, 'window': window}
            await LimitConfigService(session).save_config(config)
            await session.commit()

    async def user(self, session):
        return await session.get(User, 1)

    async def test_five_lessons_then_sixth_blocked_with_exact_copy_and_review(self):
        await self.rule(A.LESSON_START, 5)
        async with self.sessions() as session:
            user = await self.user(session)
            for number in range(1, 6):
                result = await LessonAccessService(session).status(user, level='hsk4', lesson_order=number, consume=True)
                self.assertTrue(result['allowed'])
            denied = await LessonAccessService(session).status(user, level='hsk4', lesson_order=6, consume=True)
            self.assertFalse(denied['allowed'])
            self.assertEqual(5, denied['limit'])
            self.assertIn('kuniga 5 ta dars', denied['limit_text'])
            self.assertEqual(0, denied['remaining'])
            self.assertIsNotNone(denied['reset_at'])
            repeated = await LessonAccessService(session).status(user, level='hsk4', lesson_order=5, consume=True)
            self.assertTrue(repeated['allowed'])
            self.assertTrue(repeated['idempotent'])
            self.assertEqual(5, (await EntitlementEngine(session).check(user, A.LESSON_START)).used)
            review = await LessonAccessService(session).status(user, level='hsk4', lesson_order=4, completed=5)
            self.assertTrue(review['allowed'])

    async def test_daily_rule_resets_but_lifetime_rule_does_not(self):
        await self.rule(A.PRACTICE_RECOGNITION, 1)
        async with self.sessions() as session:
            user = await self.user(session)
            await CourseMiniAppAccessService(session).consume_daily_use(user, feature_key='recognition', ref='old', lifetime=True)
            await session.execute(update(CourseMiniAppEvent).values(created_at=datetime.now(timezone.utc)-timedelta(days=2)))
            await session.commit()
            self.assertTrue((await CourseMiniAppAccessService(session).daily_status(user, 'recognition', lifetime=True))['allowed'])
        await self.rule(A.PRACTICE_RECOGNITION, 1, 'lifetime')
        async with self.sessions() as session:
            status = await CourseMiniAppAccessService(session).daily_status(await self.user(session), 'recognition')
            self.assertFalse(status['allowed'])
            self.assertIsNone(status['reset_at'])

    async def test_admin_change_is_live_without_restart(self):
        await self.rule(A.PRACTICE_PLACEMENT, 1, 'lifetime')
        async with self.sessions() as session:
            await CourseMiniAppAccessService(session).consume_daily_use(await self.user(session), feature_key='placement', ref='one')
            await session.commit()
        await self.rule(A.PRACTICE_PLACEMENT, 5, 'lifetime')
        async with self.sessions() as session:
            status = await CourseMiniAppAccessService(session).daily_status(await self.user(session), 'placement')
            self.assertTrue(status['allowed'])
            self.assertEqual(4, status['remaining'])
        await self.rule(A.PRACTICE_PLACEMENT, None)
        async with self.sessions() as session:
            status = await CourseMiniAppAccessService(session).daily_status(await self.user(session), 'placement')
            self.assertTrue(status['unlimited'])
        await self.rule(A.PRACTICE_PLACEMENT, 0)
        async with self.sessions() as session:
            status = await CourseMiniAppAccessService(session).daily_status(await self.user(session), 'placement')
            self.assertFalse(status['allowed'])

    async def test_trial_uses_trial_settings_and_expiry_falls_back_to_free(self):
        await self.rule(A.LESSON_START, 1)
        await self.rule(A.LESSON_START, 3, state='TRIAL_ACTIVE')
        async with self.sessions() as session:
            user = await self.user(session)
            user.pro_trial_ends_at = datetime.now(timezone.utc)+timedelta(days=2)
            for number in range(1, 4):
                result = await LessonAccessService(session).status(user, level='hsk4', lesson_order=number, consume=True)
                self.assertTrue(result['allowed'])
            denied = await LessonAccessService(session).status(user, level='hsk4', lesson_order=4, consume=True)
            self.assertFalse(denied['allowed'])
            self.assertIn('Trial rejimida kuniga 3', denied['limit_text'])
            user.pro_trial_ends_at = datetime.now(timezone.utc)-timedelta(seconds=1)
            free = await EntitlementEngine(session).check(user, A.LESSON_START)
            self.assertEqual('FREE', free.state)
            self.assertEqual(1, free.limit)
            self.assertFalse(free.allowed)

    async def test_paid_unlimited_and_blocked_wins_over_admin_free_mode(self):
        async with self.sessions() as session:
            user = await self.user(session)
            user.status='active';user.payment_status='approved';user.end_date=datetime.now(timezone.utc)+timedelta(days=5)
            self.assertTrue((await EntitlementEngine(session).check(user, A.LESSON_START)).unlimited)
            user.status='blocked'
            await CourseAccessPolicyService(session).save_policy(mode='free_until', duration_days=3)
            self.assertFalse((await LessonAccessService(session).status(user, level='hsk4', lesson_order=1))['allowed'])
            self.assertFalse((await CourseMiniAppAccessService(session).daily_status(user, 'recognition'))['allowed'])

    async def test_http_miniapp_silent_android_uses_same_counter_and_sends_once(self):
        await self.rule(A.PRACTICE_RECOGNITION, 1)
        headers={'X-Telegram-Init-Data': signed()}
        first=await self.http.post('/api/v3/practice/daily-gate', headers=headers, json={'feature':'recognition','ref':'shared'})
        self.assertEqual(200, first.status_code)
        duplicate=await self.http.post('/api/v3/practice/daily-gate', headers=headers, json={'feature':'recognition','ref':'shared'})
        self.assertEqual(200, duplicate.status_code)
        refused=await self.http.post('/api/v3/practice/daily-gate', headers=headers, json={'feature':'recognition','ref':'other'})
        self.assertEqual(403, refused.status_code)
        self.assertEqual(1, refused.json()['limit'])
        self.bot.send_message.assert_not_awaited()
        async with self.sessions() as session:
            user=await self.user(session)
            for _ in range(2):
                result=await CourseMiniAppAccessService(session).consume_daily_use(user,feature_key='recognition',ref='android',notify_bot=self.bot)
                self.assertFalse(result['allowed'])
            self.assertEqual(1,self.bot.send_message.await_count)

    async def test_other_feature_ref_cannot_grant_a_lesson(self):
        await self.rule(A.LESSON_START, 0)
        async with self.sessions() as session:
            user=await self.user(session)
            await CourseMiniAppAccessService(session).consume_daily_use(user, feature_key='recognition', ref='lesson:hsk4:1')
            result=await LessonAccessService(session).status(user,level='hsk4',lesson_order=1,consume=True)
            self.assertFalse(result['allowed'])

    async def test_lesson_start_http_validates_auth_and_sequence(self):
        await self.rule(A.LESSON_START, 5)
        headers={'X-Telegram-Init-Data':signed()}
        self.assertEqual(401,(await self.http.post('/api/v3/lesson/start',json={'lesson_id':1})).status_code)
        self.assertEqual(403,(await self.http.post('/api/v3/lesson/start',headers=headers,json={'lesson_id':2})).status_code)
        result=await self.http.post('/api/v3/lesson/start',headers=headers,json={'lesson_id':1})
        self.assertEqual(200,result.status_code)
        self.assertEqual(4,result.json()['remaining'])
        self.bot.send_message.assert_not_awaited()

    async def test_ai_settings_are_provider_independent_and_use_own_counters(self):
        await self.rule(A.AI_TEXT,2)
        await self.rule(A.AI_PHOTO,1,'lifetime')
        async with self.sessions() as session:
            user=await self.user(session)
            session.add_all([Message(user_id=1,role='user',content='hello',content_type='text') for _ in range(2)])
            session.add(Message(user_id=1,role='user',content='photo',content_type='image',created_at=datetime.now(timezone.utc)-timedelta(days=2)))
            await session.flush()
            for provider in (True,False):
                with patch('app.services.access_service.gemini_active',return_value=provider):
                    self.assertFalse((await AccessService(session)._can_use_daily_text_limit(user))[0])
                    self.assertFalse((await AccessService(session)._can_use_daily_image_limit(user))[0])
            self.assertTrue((await AccessService(session).can_use_free_daily_voice(user))[0])

    async def test_speaking_uses_configured_window_and_only_spoken_sessions(self):
        await self.rule(A.SPEAKING_SESSION,3,'lifetime')
        async with self.sessions() as session:
            user=await self.user(session)
            session.add(VoicePracticeSession(id='spoken',user_telegram_id=user.telegram_id,role='waiter',level='hsk4',language='uz',voice='female',turn_count=1,started_at=datetime.now(timezone.utc)-timedelta(days=2)))
            session.add(VoicePracticeSession(id='empty',user_telegram_id=user.telegram_id,role='waiter',level='hsk4',language='uz',voice='female',turn_count=0))
            await session.flush()
            status=await VoicePracticeService(session).user_status(user.telegram_id)
            self.assertEqual(2,status['remaining_voice_limit'])
            self.assertIsNone(status['reset_at'])
            self.assertIn('jami 3',status['limit_status']['limit_text'])

    async def test_copy_for_all_languages_is_bound_to_saved_limit(self):
        await self.rule(A.LESSON_START,5,'lifetime')
        async with self.sessions() as session:
            user=await self.user(session)
            decision=await EntitlementEngine(session).check(user,A.LESSON_START)
            for lang in ('uz','ru','tj'):
                data=decision.as_dict(language=lang)
                self.assertIn('5',data['limit_text'])
                self.assertIsNone(data['reset_at'])
