"""UTC/session fences, bounded due polling and actual PostgreSQL migration."""
import asyncio
from datetime import datetime, timedelta, timezone
import importlib.util
import hashlib
from uuid import uuid4
from types import SimpleNamespace
import os
from pathlib import Path
import unittest
from unittest.mock import AsyncMock

from pydantic import ValidationError
from sqlalchemy import event, inspect, select

from app.admin_api import pwa_campaign_schedule as schedule, pwa_campaigns as api, pwa_outbound as outbound
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_outbound import AdminPwaOutboundJob as Job, AdminPwaOutboundRecipient as Recipient
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from tests import test_admin_pwa_campaigns as campaigns, test_admin_pwa_settings_postgres as pg


def future(minutes=5):
    return (datetime.now(timezone.utc)+timedelta(minutes=minutes)).isoformat().replace('+00:00','Z')


class ScheduleTests(campaigns.fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = campaigns.CampaignTests.asyncSetUp
    asyncTearDown = campaigns.CampaignTests.asyncTearDown
    prepare = campaigns.CampaignTests.prepare
    proof = campaigns.CampaignTests.proof
    execute = campaigns.CampaignTests.execute

    async def queued(self, **kw):
        command=await self.prepare(campaigns.RELEASE|{'send_at':future()}|kw)
        return await self.execute(command, await self.proof(command))

    async def due(self, job_id):
        async with self.sessions() as db:
            (await db.get(Job, job_id)).not_before=datetime.now(timezone.utc)-timedelta(seconds=1)
            await db.commit()

    async def test_explicit_utc_and_short_live_session_window(self):
        for stamp in ('2026-10-26T10:00', '2026-10-26T10:00:00+08:00', 'wrong', ''):
            with self.assertRaises(ValidationError):
                api.PrepareCampaign(change=campaigns.RELEASE|{'send_at':stamp})
        for stamp in (future(-1),future(31)):
            with self.assertRaises(api.CommandError):
                await self.prepare(campaigns.RELEASE|{'send_at':stamp})
        async with self.sessions() as db:
            (await db.get(AdminPwaSession,self.session_id)).expires_at=datetime.now(timezone.utc)+timedelta(minutes=2)
            await db.commit()
        with self.assertRaises(api.CommandError):
            await self.prepare(campaigns.RELEASE|{'send_at':future(3)})

    async def test_early_manual_and_background_drain_do_not_claim_or_send(self):
        result=await self.queued();job_id=result['job_id'];emitter=AsyncMock()
        self.assertFalse(await outbound.dispatch_message_batch(job_id=job_id,session_factory=self.sessions,
            settings_obj=self.settings,emit=emitter))
        async with self.sessions() as db:
            with self.assertRaises(api.CommandError):
                await outbound.authorize_message_run(db,session_cookie=campaigns.fixtures.COOKIE,
                    request=outbound.RunMessage(job_id=job_id),settings_obj=self.settings)
        drainer=outbound.create_message_drainer(session_factory=self.sessions,settings_obj=self.settings,emit=emitter)
        await drainer(job_id)
        poll=schedule.create_due_campaign_poller(session_factory=self.sessions,settings_obj=self.settings,drainer=drainer)
        try:
            self.assertEqual(await poll(),0)
            async with self.sessions() as db:
                job=await db.get(Job,job_id)
                expiry=job.expires_at
                self.assertEqual(job.status,'ready')
                self.assertIsNone(job.started_at)
                self.assertEqual((await db.get(Recipient,(job_id,2))).status,'pending')
                self.assertLessEqual((job.expires_at-job.created_at).total_seconds(),3600)
            await self.due(job_id)
            await asyncio.gather(drainer(job_id),drainer(job_id))
            emitter.assert_awaited_once()
            await drainer(job_id)
            emitter.assert_awaited_once()
            async with self.sessions() as db:
                self.assertEqual((await db.get(Job,job_id)).expires_at,expiry)
        finally:
            await poll.close()

    async def test_revoked_actor_is_filtered_and_disabled_poller_performs_zero_queries(self):
        result=await self.queued();await self.due(result['job_id'])
        drainer=AsyncMock();poll=schedule.create_due_campaign_poller(session_factory=self.sessions,settings_obj=self.settings,drainer=drainer)
        async with self.sessions() as db:
            (await db.get(AdminPwaSession,self.session_id)).revoked_at=datetime.now(timezone.utc)
            await db.commit()
        self.assertEqual(await poll(),0);drainer.assert_not_awaited()
        self.settings.ADMIN_PWA_ENABLED=False
        def forbidden(*args):
            raise AssertionError('disabled poller must not touch SQL')
        event.listen(self.engine.sync_engine,'before_cursor_execute',forbidden)
        try:
            self.assertEqual(await poll(),0)
        finally:
            event.remove(self.engine.sync_engine,'before_cursor_execute',forbidden)
            await poll.close()

    async def test_at_most_two_tracked_drains_and_no_wait_for_provider(self):
        # Seed separately signed jobs; the normal one-use proof is not reused.
        ids=[]
        for _ in range(4):
            result=await self.queued();ids.append(result['job_id']);await self.due(result['job_id'])
        started=[];release=asyncio.Event()
        async def drain(job_id):
            started.append(job_id);await release.wait()
        poll=schedule.create_due_campaign_poller(session_factory=self.sessions,settings_obj=self.settings,drainer=drain)
        try:
            results=await asyncio.gather(poll(),poll(),poll())
            self.assertEqual(sum(results),2)
            await asyncio.sleep(0)
            self.assertEqual(len(started),2)
            self.assertEqual(len(set(started)),2)
            self.assertEqual(await poll(),0)
        finally:
            release.set();await poll.close()

    async def test_fresh_signed_pending_only_resume_preserves_original_due_time_and_expiry(self):
        result=await self.queued();job_id=result['job_id'];cookie='R'*64
        async with self.sessions() as db:
            old=await db.get(Job,job_id);planned,expiry=old.not_before,old.expires_at
            (await db.get(AdminPwaSession,self.session_id)).revoked_at=datetime.now(timezone.utc)
            self.session_id=str(uuid4())
            db.add(AdminPwaSession(id=self.session_id,user_id=101,auth_method='webauthn',
                token_hash=hashlib.sha256(cookie.encode()).hexdigest(),expires_at=datetime.now(timezone.utc)+timedelta(hours=1)))
            await db.commit()
        async with self.sessions() as db:
            prepared=await outbound.prepare_message_control(db,session_cookie=cookie,
                request=outbound.PrepareMessageControl(job_id=job_id,operation='resume'),settings_obj=self.settings)
        control=outbound.MessageControlCommand(**prepared['operation']['payload'])
        proxy=SimpleNamespace(operation=control.operation_payload)
        # The common fixture signs using its session ID; only the cookie needs this override.
        from tests import test_admin_pwa_settings as proofs
        self.cookie=cookie
        proof=await proofs.AdminPwaSettingsTests.proof(self,proxy)
        async with self.sessions() as db:
            await outbound.execute_message_control(db,session_cookie=cookie,
                request=outbound.ExecuteMessageControl(**control.model_dump(),step_up_id=proof),settings_obj=self.settings)
        emitter=AsyncMock()
        self.assertFalse(await outbound.dispatch_message_batch(job_id=job_id,session_factory=self.sessions,
            settings_obj=self.settings,emit=emitter))
        emitter.assert_not_awaited()
        async with self.sessions() as db:
            job=await db.get(Job,job_id)
            self.assertEqual((job.not_before,job.expires_at),(planned,expiry))

    async def test_session_change_after_prepare_preserves_proof_and_creates_no_job(self):
        command=await self.prepare(campaigns.RELEASE|{'send_at':future(10)})
        proof=await self.proof(command)
        async with self.sessions() as db:
            (await db.get(AdminPwaSession,self.session_id)).expires_at=datetime.now(timezone.utc)+timedelta(minutes=2)
            await db.commit()
        with self.assertRaises(api.CommandError):
            await self.execute(command,proof)
        async with self.sessions() as db:
            self.assertIsNone(await db.scalar(select(Job.id)))
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'),'requires isolated PostgreSQL')
class SchedulePostgresTests(campaigns.fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown=pg.AdminPwaSettingsPostgresTests.asyncTearDown
    prepare=ScheduleTests.prepare
    proof=ScheduleTests.proof
    execute=ScheduleTests.execute
    queued=ScheduleTests.queued
    due=ScheduleTests.due
    test_early_manual_and_background_drain_do_not_claim_or_send=ScheduleTests.test_early_manual_and_background_drain_do_not_claim_or_send

    async def test_actual_migration_indexes_and_refuses_nonempty_schedule_downgrade(self):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        path=Path(__file__).resolve().parents[1]/'alembic/versions/0132_admin_pwa_campaign_schedule.py'
        spec=importlib.util.spec_from_file_location('pwa_schedule_migration',path)
        migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
        result=await self.queued()
        async with self.engine.begin() as connection:
            def refuses(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    with self.assertRaisesRegex(RuntimeError,'Archive scheduled'):
                        migration.downgrade()
            await connection.run_sync(refuses)
            await connection.execute(Job.__table__.update().values(not_before=None))
            def recreate(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    migration.downgrade();migration.upgrade()
            await connection.run_sync(recreate)
            columns=await connection.run_sync(lambda sync:{c['name'] for c in inspect(sync).get_columns(Job.__tablename__)})
            self.assertEqual(columns,set(Job.__table__.columns.keys()))
            indexes=await connection.run_sync(lambda sync:{i['name']:i['column_names'] for i in inspect(sync).get_indexes(Job.__tablename__)})
            self.assertEqual(indexes['ix_pwa_outbound_due'],['status','not_before','id'])
