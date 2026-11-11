"""Native answers use the same canonical bot rows/rewards as current PWA."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import models  # noqa
from app.db.base import Base
from app.db.models.user import User
from app.db.models.bot_feedback import BotFeedback
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.api.android_features import create_android_features_router
from app.services.desktop_auth_service import DesktopAuthService, DesktopAuthError

class AndroidActivityFeedbackTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:', poolclass=StaticPool)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            for uid in (1,2):
                db.add(User(id=uid,telegram_id=None,full_name='Synthetic',level='hsk1',language='uz',
                    status='free',created_at=now-timedelta(days=3),last_active_at=now))
            await db.commit()
        self.owner = 1
        async def authenticate(token):
            if token != 'verified': raise DesktopAuthError('native_auth_required',status_code=401)
            async with self.sessions() as db:
                return SimpleNamespace(user=await db.get(User,self.owner))
        patcher=patch.object(DesktopAuthService,'authenticate',side_effect=authenticate)
        patcher.start(); self.addCleanup(patcher.stop)
        app=FastAPI(); app.include_router(create_android_features_router(session_factory=self.sessions, settings_obj=SimpleNamespace()))
        self.client=AsyncClient(transport=ASGITransport(app=app),base_url='https://android.test')
    async def asyncTearDown(self):
        await self.client.aclose(); await self.engine.dispose()
    async def post(self, action, body, token='verified'):
        return await self.client.post('/api/v3/android/feedback/'+action,json=body,headers={'Authorization':'Bearer '+token})
    async def prepare(self):
        async with self.sessions() as db:
            db.add(CourseMiniAppEvent(user_id=self.owner,event_name='training_completed',source='android',level='hsk1'))
            await db.commit()
        return await self.post('prepare',{'context':{'kind':'practice','level':'hsk1'}})
    async def test_actual_context_and_bearer_required_without_client_owner(self):
        body={'context':{'kind':'practice','level':'hsk1'}}
        self.assertEqual(401,(await self.post('prepare',body,token='bad')).status_code)
        self.assertEqual(409,(await self.post('prepare',body)).status_code)
        self.assertEqual(422,(await self.post('prepare',{**body,'user_id':2})).status_code)
        async with self.sessions() as db:
            self.assertIsNone(await db.scalar(select(BotFeedback.id)))
    async def test_real_native_voice_session_proves_use_without_fabricated_browser_telemetry(self):
        from app.db.models.voice_practice_session import VoicePracticeSession
        body={'context':{'kind':'voice','level':'hsk1'}}
        async with self.sessions() as db:
            db.add(VoicePracticeSession(id='synthetic-voice',user_id=1,role='friend',level='hsk1',language='uz',voice='female',turn_count=0))
            await db.commit()
        self.assertEqual(409,(await self.post('prepare',body)).status_code)
        async with self.sessions() as db:
            (await db.get(VoicePracticeSession,'synthetic-voice')).turn_count=1
            await db.commit()
        self.assertIsNotNone((await self.post('prepare',body)).json()['ordinary'])

    async def test_free_canonical_answers_single_reward_and_admin_storage(self):
        response=await self.prepare(); self.assertEqual(200,response.status_code,response.text)
        prompt=response.json()['ordinary']; self.assertFalse(prompt['paid'])
        self.assertEqual('bot',prompt['presentation']); self.assertIsNone(prompt['compact'])
        self.assertTrue(prompt['choices']['liked'])
        payload={'feedback_id':prompt['feedback_id'],'liked_code':'practice','liked_sub_code':'daily','disliked_code':'limits'}
        self.owner=2
        self.assertEqual(404,(await self.post('submit',payload)).status_code)
        self.owner=1
        self.assertEqual(422,(await self.post('submit',{**payload,'liked_sub_code':'invented'})).status_code)
        accepted=await self.post('submit',payload); self.assertEqual(200,accepted.status_code,accepted.text)
        self.assertTrue(accepted.json()['completed'])
        async with self.sessions() as db:
            row=await db.get(BotFeedback,prompt['feedback_id']); owner=await db.get(User,1)
            self.assertEqual(('completed','practice','limits'),(row.status,row.liked_code,row.disliked_code))
            self.assertIsNotNone(row.reward_granted_at); expiry=owner.end_date
        self.assertEqual(409,(await self.post('submit',payload)).status_code)
        async with self.sessions() as db:
            self.assertEqual(expiry,(await db.get(User,1)).end_date)
        self.assertIsNone((await self.prepare()).json()['ordinary'])
    async def test_paid_reward_does_not_rewrite_paid_term_and_partial_state_survives_mode_change(self):
        async with self.sessions() as db:
            user=await db.get(User,1); user.status='active'; user.payment_status='approved'
            user.end_date=datetime.now(timezone.utc)+timedelta(days=30)
            await db.commit(); expiry=user.end_date.replace(tzinfo=None)
        prompt=(await self.prepare()).json()['ordinary']; self.assertTrue(prompt['paid'])
        payload={'feedback_id':prompt['feedback_id'],'paid_code':'useful','paid_sub_code':'lessons'}
        saved=await self.post('submit',payload); self.assertEqual(200,saved.status_code,saved.text)
        async with self.sessions() as db:
            user=await db.get(User,1); row=await db.get(BotFeedback,prompt['feedback_id'])
            self.assertEqual(expiry,user.end_date); self.assertIsNone(row.reward_granted_at)
        self.owner=2
        prompt=(await self.prepare()).json()['ordinary']
        async with self.sessions() as db:
            row=await db.get(BotFeedback,prompt['feedback_id']); row.liked_code='practice'; row.prompted_at=None
            user=await db.get(User,2); user.status='active';user.payment_status='approved';user.end_date=datetime.now(timezone.utc)+timedelta(days=30)
            await db.commit()
        self.assertIsNone((await self.prepare()).json()['ordinary'])
        async with self.sessions() as db:
            self.assertEqual('practice',(await db.get(BotFeedback,prompt['feedback_id'])).liked_code)
