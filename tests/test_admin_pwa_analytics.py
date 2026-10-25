"""Real bounded analytics fixtures; no dashboard demo values or private rows."""
from datetime import datetime, timedelta, timezone
import json
import unittest

from sqlalchemy import event, select

from app.admin_api import pwa_analytics as api
from app.admin_api.pwa_read import read_transaction
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.payment import Payment
from app.db.models.user import User
from tests import test_admin_pwa_payment_review as fixtures

NOW=datetime(2026,10,26,12,tzinfo=timezone.utc)


class AnalyticsProjectionTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown=fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def seed_analytics(self):
        async with self.sessions() as db:
            admin=await db.get(User,101);admin.created_at=NOW-timedelta(days=100);admin.language='uz';admin.level='hsk1';admin.last_active_at=NOW-timedelta(days=100)
            first=await db.get(User,1);first.created_at=NOW-timedelta(days=1);first.status='active'
            first.payment_status='approved';first.end_date=NOW+timedelta(days=2);first.language='ru';first.level='nhsk2'
            first.last_active_at=NOW-timedelta(hours=1)
            second=await db.get(User,2);second.created_at=NOW-timedelta(days=10);second.status='free'
            second.language='tj';second.level='hsk1';second.last_active_at=NOW-timedelta(hours=2)
            second.bot_blocked_at=NOW-timedelta(hours=3)
            db.add(User(id=3,telegram_id=3003,status='free',created_at=NOW+timedelta(days=1),
                        language='PRIVATE',level='PRIVATE name'))
            pending=await db.scalar(select(Payment));pending.submitted_at=NOW-timedelta(hours=1)
            for user_id,tid,delta in ((1,2002,-1),(None,2002,-2),(None,999999,-3),(1,None,1)):
                db.add(Payment(user_id=user_id,user_telegram_id=tid,amount=100,currency='TJS',
                    plan_type='1_month',payment_method='visa',payment_status='approved',
                    submitted_at=NOW+timedelta(hours=delta),reviewed_at=NOW+timedelta(hours=delta)))
            for user_id,tid,name,when in (
                (1,None,'lesson_started',NOW-timedelta(minutes=3)),
                (1,2002,'android_lesson_completed',NOW-timedelta(minutes=2)),
                (None,2002,'training_started',NOW-timedelta(minutes=1)),
                (1,None,'lesson_started',NOW-timedelta(days=1)),
                (None,999999,'lesson_started',NOW-timedelta(minutes=1)),
                (1,None,'lesson_completed',NOW+timedelta(hours=1)),
            ):
                db.add(Event(user_id=user_id,telegram_id=tid,event_name=name,created_at=when,
                             source='course_miniapp',payload_json='{"PRIVATE":"must not escape"}'))
            await db.commit()

    async def projection(self, *, period='weekly', overview=False):
        async with self.sessions() as db:
            async with read_transaction(db):
                return await api.home_overview_metrics(db,period=period,now=NOW,overview=overview)

    async def test_home_counts_are_actual_canonical_snapshot_without_mixed_time_or_private_rows(self):
        await self.seed_analytics();result=await self.projection();m=result['metrics']
        self.assertEqual((m['users_total'],m['new_accounts'],m['active_accounts'],m['active_today']),(3,1,2,2))
        self.assertEqual((m['active_pro'],m['expiring_pro'],m['bot_blocked']),(1,1,1))
        self.assertEqual(m['pending_current'],1)
        self.assertEqual(m['payments_by_status'],{'pending':1,'approved':3,'rejected':0})
        self.assertEqual(m['paying_accounts'],2)
        self.assertEqual(result['generated_at'],NOW.isoformat())
        self.assertEqual(result['timezone'],'Asia/Shanghai')
        encoded=json.dumps(result)
        self.assertNotIn('PRIVATE',encoded)
        self.assertNotIn('telegram_id',encoded)
        self.assertNotIn('user_id',encoded)

    async def test_calendar_series_is_real_zero_filled_and_canonical_deduplicated(self):
        await self.seed_analytics();result=await self.projection();series=result['metrics']['activity']
        self.assertEqual(len(series['points']),7)
        self.assertEqual(series['points'][-1],{'date':'2026-10-26','accounts':2})
        self.assertEqual(series['points'][-2],{'date':'2026-10-25','accounts':1})
        self.assertEqual(series['points'][0]['accounts'],0)
        self.assertEqual(series['scope'],'calendar_7_days')
        self.assertEqual(series['since'],'2026-10-19T16:00:00+00:00')
        for period in ('monthly','all_time'):
            r=await self.projection(period=period)
            self.assertEqual(len(r['metrics']['activity']['points']),30)
            self.assertEqual(r['metrics']['activity']['scope'],'calendar_30_days')

    async def test_overview_engagement_and_distributions_keep_actual_grains(self):
        await self.seed_analytics();result=await self.projection(overview=True);m=result['metrics']
        self.assertEqual(m['course_engagement'],{'engaged_accounts':2,'started_accounts':1,'completed_accounts':1})
        self.assertEqual(m['levels'],[{'key':'hsk1','accounts':2},{'key':'nhsk2','accounts':1}])
        self.assertEqual(m['languages'],[{'key':'uz','accounts':1},{'key':'ru','accounts':1},{'key':'tj','accounts':1}])
        async with self.sessions() as db:
            u=await db.get(User,2);u.level='PRIVATE custom';u.language='PRIVATE';await db.commit()
        result=await self.projection(overview=True)
        self.assertIn({'key':'unknown','accounts':1},result['metrics']['levels'])
        self.assertNotIn('PRIVATE',json.dumps(result))

    async def test_projection_performs_only_bounded_aggregate_selects(self):
        await self.seed_analytics();statements=[]
        def record(conn,cursor,sql,*args):statements.append(sql.lower())
        event.listen(self.engine.sync_engine,'before_cursor_execute',record)
        try:
            await self.projection(overview=True)
        finally:event.remove(self.engine.sync_engine,'before_cursor_execute',record)
        self.assertEqual(len(statements),8)
        self.assertTrue(all(sql.lstrip().startswith('select ') for sql in statements))
        self.assertTrue(all('count(' in sql for sql in statements))
        self.assertFalse(any('payload_json' in sql or 'full_name' in sql for sql in statements))


class AnalyticsCacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import asyncio
        from tests import test_admin_pwa_statistics_cache as cache_fixtures
        from app.admin_api.pwa_analytics_cache import AdminPwaAnalyticsReader
        self.fixture=cache_fixtures.StatisticsCacheFixtures()
        self.fixture.setUp()
        self.calls={'home':0,'overview':0}
        self.active=0;self.max_active=0
        def projection(section):
            async def load(db,query):
                self.calls[section]+=1;self.active+=1;self.max_active=max(self.active,self.max_active)
                try:await asyncio.sleep(.01)
                finally:self.active-=1
                return {'platform':query.platform,'period':query.period,'available':True,
                    'generated_at':datetime.fromtimestamp(self.fixture.clock,timezone.utc).isoformat(),
                    'scope':{'section':section},'metrics':{'accounts':self.calls[section]}}
            return load
        self.reader=AdminPwaAnalyticsReader(settings_obj=self.fixture.settings,session_factory=self.fixture.sessions,
            projections={key:projection(key) for key in self.calls},
            reader_options={'clock':lambda:self.fixture.clock})

    async def asyncTearDown(self):
        await self.reader.aclose();await self.fixture.reader.aclose()

    async def test_unopened_sections_do_no_work_and_concurrent_sections_serialize(self):
        import asyncio
        from app.admin_api.pwa_analytics_cache import AnalyticsRequest
        await asyncio.gather(*(self.reader(AnalyticsRequest(section='home')) for _ in range(12)))
        self.assertEqual(self.calls,{'home':1,'overview':0})
        await self.reader(AnalyticsRequest(section='overview'))
        self.assertEqual(self.calls,{'home':1,'overview':1})
        self.fixture.clock+=86401
        await asyncio.gather(self.reader(AnalyticsRequest(section='home')),self.reader(AnalyticsRequest(section='overview')))
        self.assertEqual(self.calls,{'home':2,'overview':2})
        self.assertEqual(self.max_active,1)
        home,overview=(self.reader._readers[key] for key in ('home','overview'))
        self.assertNotEqual(home.prefix,overview.prefix)
        self.assertNotEqual(home._r2_namespace,overview._r2_namespace)
        self.assertEqual(home._lease_key,overview._lease_key)
        self.assertNotEqual(home._r2_namespace,self.fixture.reader._r2_namespace)

    async def test_original_generation_time_is_reused_then_refreshes_after_one_day(self):
        from app.admin_api.pwa_analytics_cache import AnalyticsRequest
        q=AnalyticsRequest(section='home');first=await self.reader(q)
        self.fixture.clock+=86399
        self.assertEqual((await self.reader(q))['generated_at'],first['generated_at'])
        self.fixture.clock+=2
        self.assertNotEqual((await self.reader(q))['generated_at'],first['generated_at'])
        self.assertEqual(self.calls,{'home':2,'overview':0})

    async def test_strict_scope_and_disabled_boundary_do_not_load_data(self):
        from app.admin_api.pwa_analytics_cache import AnalyticsRequest
        from app.admin_api.pwa_statistics_cache import StatisticsUnavailable
        from pydantic import ValidationError
        for values in ({'section':'private_users'},{'section':'home','user_id':1},{'platform':'arbitrary'}):
            with self.assertRaises(ValidationError):AnalyticsRequest(**values)
        self.fixture.settings.ADMIN_PWA_ENABLED=False
        with self.assertRaises(StatisticsUnavailable):await self.reader(AnalyticsRequest())
        self.assertEqual(sum(self.calls.values()),0)


class AnalyticsTransportTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown=fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def request(self, *, reader=None, cookie=fixtures.COOKIE, payload=None, origin='https://hskai.app'):
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from app.admin_api.pwa_analytics_transport import create_admin_pwa_analytics_router
        from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
        app=FastAPI();app.include_router(create_admin_pwa_analytics_router(settings_obj=self.settings,
            session_factory=self.sessions,analytics_reader=reader))
        async with AsyncClient(transport=ASGITransport(app=app),base_url='https://hskai.app') as client:
            return await client.post('/api/admin/v1/analytics',json=payload or {'section':'home'},headers={
                'Origin':origin,'Cookie':ADMIN_PWA_COOKIE_NAME+'='+cookie})

    async def test_actual_authenticated_projection_is_private_and_body_is_strict(self):
        from unittest.mock import AsyncMock
        response=await self.request()
        self.assertEqual(response.status_code,200,response.text)
        self.assertIn('no-store',response.headers['cache-control'])
        self.assertEqual(response.json()['scope']['section'],'home')
        self.assertIn('snapshot',response.json())
        reader=AsyncMock()
        for values in ({'section':'home','user_id':1},{'section':'private_users'},{'section':'home','url':'https://evil.invalid'}):
            denied=await self.request(payload=values,reader=reader)
            self.assertEqual(denied.status_code,400)
        self.assertEqual((await self.request(reader=reader,origin='https://evil.invalid')).status_code,403)
        self.assertEqual((await self.request(reader=reader,cookie='invalid')).status_code,401)
        reader.assert_not_awaited()

    async def test_cache_boundary_releases_connection_and_late_revocation_denies_result(self):
        from app.db.models.admin_pwa import AdminPwaSession
        active=0
        def checkout(*args):
            nonlocal active
            active+=1
        def checkin(*args):
            nonlocal active
            active-=1
        async def reader(query):
            self.assertEqual(active,0)
            async with self.sessions() as db:
                (await db.get(AdminPwaSession,self.session_id)).revoked_at=datetime.now(timezone.utc)
                await db.commit()
            return {'available':True,'metrics':{'PRIVATE':10}}
        event.listen(self.engine.sync_engine,'checkout',checkout);event.listen(self.engine.sync_engine,'checkin',checkin)
        try:response=await self.request(reader=reader)
        finally:
            event.remove(self.engine.sync_engine,'checkout',checkout);event.remove(self.engine.sync_engine,'checkin',checkin)
        self.assertEqual(response.status_code,401)
        self.assertNotIn('PRIVATE',response.text)
