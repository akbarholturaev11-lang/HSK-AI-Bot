"""Exact QA boot guards and real empty-schema/native-refresh/claim integration."""
from datetime import datetime, timedelta, timezone
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from scripts import smart_reminder_qa_guard as guard
from scripts import qa_standalone_bootstrap as bootstrap
from scripts.smart_reminder_qa_seed import seed

SAFE = {"RAILWAY_PROJECT_ID":guard.PROJECT_ID,"RAILWAY_ENVIRONMENT_ID":guard.ENVIRONMENT_ID,
        "RAILWAY_ENVIRONMENT_NAME":"qa","RAILWAY_SERVICE_ID":guard.SERVICE_ID,
        "RAILWAY_PUBLIC_DOMAIN":guard.DOMAIN,"HSK_SMART_QA_MODE":"1",
        "DATABASE_URL":"postgresql://synthetic:unusable@postgres.railway.internal:5432/railway",
        "DESKTOP_AUTH_SIGNING_SECRET":"synthetic-qa-native-"+"q"*64}
REFRESH = ["pomp_r1_synthetic_fixture_"+str(n)+"x"*64 for n in (1,2)]


class SmartQAGuardTests(unittest.TestCase):
    def test_only_exact_qa_binding_is_accepted(self):
        self.assertTrue(guard.validate(SAFE).startswith("postgresql+asyncpg://"))
        for key in ("RAILWAY_PROJECT_ID","RAILWAY_ENVIRONMENT_ID","RAILWAY_ENVIRONMENT_NAME",
                    "RAILWAY_SERVICE_ID","RAILWAY_PUBLIC_DOMAIN","HSK_SMART_QA_MODE","DESKTOP_AUTH_SIGNING_SECRET"):
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                guard.validate(SAFE|{key:"wrong"})

    def test_database_and_provider_inheritance_fail_closed(self):
        for url in ("broken",SAFE['DATABASE_URL']+'?x=1',SAFE['DATABASE_URL'].replace('/railway','/production'),
                    SAFE['DATABASE_URL'].replace('postgres.railway.internal','production.railway.internal'),
                    'postgresql://postgres.railway.internal/railway'):
            with self.subTest(url=url), self.assertRaises(RuntimeError): guard.validate(SAFE|{'DATABASE_URL':url})
        for key in ('BOT_TOKEN','OPENAI_API_KEY','GEMINI_API_KEY','ANDROID_FCM_SERVICE_ACCOUNT_JSON','GOOGLE_DESKTOP_CLIENT_SECRET'):
            with self.subTest(key=key), self.assertRaises(RuntimeError): guard.validate(SAFE|{key:'unusable-fixture'})

    def test_operator_seed_requires_private_proof_and_finite_window(self):
        env=SAFE|dict(HSK_SMART_QA_REFRESH_1=REFRESH[0],HSK_SMART_QA_REFRESH_2=REFRESH[1],
            HSK_SMART_QA_UNTIL=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat())
        guard.validate(env,seed=True)
        for key,value in (('HSK_SMART_QA_REFRESH_1',''),('HSK_SMART_QA_UNTIL','bad'),
                          ('HSK_SMART_QA_UNTIL','2000-01-01T00:00:00Z')):
            with self.subTest(key=key), self.assertRaises(RuntimeError): guard.validate(env|{key:value},seed=True)

    def test_factory_rejects_wrong_binding_and_dotenv_before_database_use(self):
        from app.smart_reminder_qa import create_app
        with patch.dict(os.environ,SAFE|{'RAILWAY_PROJECT_ID':'production'},clear=True):
            with self.assertRaisesRegex(RuntimeError,'deployment_binding'):
                create_app()
        with patch.dict(os.environ,SAFE,clear=True), patch('app.smart_reminder_qa.Path.exists',return_value=True):
            with self.assertRaisesRegex(RuntimeError,'dotenv_refused'):
                create_app()


class SmartQAIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        raw=os.environ.get('SMART_REMINDER_TEST_DATABASE_URL','')
        if not raw: self.skipTest('Owned loopback PostgreSQL required')
        url=make_url(raw)
        if (url.drivername!='postgresql+asyncpg' or url.host not in ('127.0.0.1','localhost') or
                not (url.database or '').startswith('smart_reminder_qa') or url.query):
            raise RuntimeError('Refuse non-owned/non-loopback QA database')
        self.name='smart_reminder_qa_boot_'+uuid4().hex[:12]
        self.assertRegex(self.name,r'^smart_reminder_qa_boot_[0-9a-f]+$')
        self.admin=create_async_engine(url,isolation_level='AUTOCOMMIT')
        async with self.admin.connect() as c: await c.execute(text('CREATE DATABASE '+self.name))
        self.engine=create_async_engine(url.set(database=self.name))
        self.sessions=async_sessionmaker(self.engine,expire_on_commit=False)
        from app.db.session import _ensure_bootstrap_columns,_ensure_bootstrap_indexes
        async with self.engine.begin() as c:
            await c.run_sync(lambda sync: bootstrap._registered_model_metadata().create_all(sync,
                tables=bootstrap._initial_schema_tables(bootstrap._registered_model_metadata())))
            await _ensure_bootstrap_columns(c)
            await _ensure_bootstrap_indexes(c)
            def migrations(sync):
                # Same actual baseline -> head DDL as the operator; this test owns a NEW database.
                scripts=ScriptDirectory.from_config(Config('alembic.ini'))
                sync.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(255) NOT NULL PRIMARY KEY)'))
                context=MigrationContext.configure(sync)
                context.stamp(scripts,bootstrap.EXPECTED_BASELINE)
                with Operations.context(context):
                    for revision in reversed(list(scripts.iterate_revisions(bootstrap.EXPECTED_HEAD,bootstrap.EXPECTED_BASELINE))):
                        revision.module.upgrade()
                        context.stamp(scripts,revision.revision)
            await c.run_sync(migrations)
        self.now=datetime.now(timezone.utc)
        from app.config import Settings
        self.settings=Settings(_env_file=None, DATABASE_URL=url.set(database=self.name).render_as_string(hide_password=False),
            DESKTOP_AUTH_SIGNING_SECRET=SAFE['DESKTOP_AUTH_SIGNING_SECRET'],BOT_TOKEN='')
        await seed(self.sessions,self.settings,now=self.now,until=self.now+timedelta(hours=2),refresh_tokens=REFRESH)

    async def asyncTearDown(self):
        if hasattr(self,'engine'):
            await self.engine.dispose()
        if hasattr(self,'admin'):
            async with self.admin.connect() as c: await c.execute(text('DROP DATABASE '+self.name))
            await self.admin.dispose()

    def app(self):
        from app.smart_reminder_qa import create_app
        with patch.dict(os.environ,SAFE,clear=True):
            return create_app(session_factory=self.sessions,engine_obj=self.engine,settings_obj=self.settings)

    async def test_actual_initializer_seed_refresh_and_selected_claim(self):
        from app.services.smart_reminder_android import GRANT
        app=self.app()
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=ASGITransport(app=app),base_url='https://'+guard.DOMAIN) as client:
                self.assertEqual((await client.get('/health')).status_code,200)
                for path in ('/docs','/api/v3/smart-reminder/preferences','/api/v3/android-auth/link/start'):
                    self.assertEqual((await client.get(path)).status_code,404)
                self.assertEqual((await client.get('/api/v3/android/smart-reminder/mode')).status_code,401)
                response=await client.post('/api/v3/android-auth/refresh',json={'refresh_token':REFRESH[0]})
                self.assertEqual(response.status_code,200)
                headers={'Authorization':'Bearer '+response.json()['access_token']}
                account=await client.get('/api/v3/android/bootstrap',headers=headers,params={'app_version':guard.APP_VERSION})
                self.assertEqual(account.status_code,200,account.text)
                self.assertTrue(account.json()['authenticated'])
                base='/api/v3/android/smart-reminder'
                self.assertTrue((await client.get(base+'/mode',headers=headers)).json()['server_claim_required'])
                due=(await client.get(base+'/due',headers=headers)).json()
                self.assertEqual(due.get('job_id'),guard.JOB_ID,due)
                body=dict(version=1,request_id=str(uuid4()),local_epoch=str(uuid4()),capability_generation=due['capability_generation'],
                    preference_revision=due['preference_revision'],grant_epoch=due['grant_epoch'])
                grant=(await client.post(base+'/jobs/'+guard.JOB_ID+'/claim',headers=headers,json=body)).json()
                self.assertTrue(grant['dispatch_allowed'],grant)
                self.assertFalse((await client.post(base+'/jobs/'+guard.JOB_ID+'/claim',headers=headers,json=body)).json()['dispatch_allowed'])
                async with self.sessions() as s: self.assertEqual(await s.scalar(select(func.count()).select_from(GRANT)),1)

    async def test_operator_reseed_and_unexpected_learner_are_refused(self):
        with self.assertRaisesRegex(RuntimeError,'existing_users'):
            await seed(self.sessions,self.settings,now=self.now,until=self.now+timedelta(hours=1),refresh_tokens=REFRESH)
        from app.db.models.user import User
        async with self.sessions.begin() as s: s.add(User(id=900000002,telegram_id=None,full_name='unexpected'))
        with self.assertRaisesRegex(RuntimeError,'fixture_or_schema'):
            async with self.app().router.lifespan_context(None): pass
