"""Orphan cleanup is opt-in, bounded, source-ID-only and preserves audit facts."""
from datetime import datetime, timezone
import os
import unittest
from uuid import uuid4

from sqlalchemy import event, func, select

from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage, AdminPwaInboxTriageAudit
from app.db.models.message import Message
from app.services.admin_pwa_inbox_retention import SOURCE_MODELS,scan_orphaned_inbox_triage
from scripts.admin_pwa_inbox_retention import run
from tests import test_admin_pwa_payment_review as fixtures
from tests import test_admin_pwa_inbox_triage as inbox
from tests import test_admin_pwa_settings_postgres as pg


class InboxRetentionTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown=fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def seed_metadata(self):
        ids=await inbox.AdminPwaInboxTriageTests.seed(self)
        async with self.sessions() as db:
            marker=Message(user_id=1,role='assistant',content='PRIVATE raw stack',content_type='app_error_context')
            db.add(marker);await db.flush();ids['technical']=marker.id;ids['payment']=self.payment_id
            now=datetime.now(timezone.utc)
            for source,key in ids.items():
                for source_id in (key,900001):
                    db.add(AdminPwaInboxTriage(source=source,source_id=source_id,status='read',priority='normal',
                        revision=1,updated_at=now))
                    db.add(AdminPwaInboxTriageAudit(id=str(uuid4()),source=source,source_id=source_id,
                        operation='mark_read',actor_user_id=101,created_at=now))
            await db.commit()
        return ids

    async def test_dry_run_never_writes_or_reads_content_and_reports_only_its_page(self):
        await self.seed_metadata();statements=[]
        def collect(conn,cursor,statement,params,context,many):statements.append(statement.lower())
        event.listen(self.engine.sync_engine,'before_cursor_execute',collect)
        try:result=await run(self.sessions,limit=100)
        finally:event.remove(self.engine.sync_engine,'before_cursor_execute',collect)
        self.assertEqual(result,dict(scanned=10,orphan_candidates=5,removed=0,next_cursor=None,mode='dry_run'))
        self.assertEqual(len(statements),6)
        self.assertTrue(all(q.lstrip().startswith('select ') for q in statements))
        self.assertFalse(any('for update' in q or 'count(' in q or 'attachment' in q or 'content' in q for q in statements))
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaInboxTriage)),10)

    async def test_keyset_sweep_deletes_only_missing_source_metadata_and_keeps_every_audit(self):
        ids=await self.seed_metadata();after=None;scanned=removed=0
        for _ in range(7):
            result=await run(self.sessions,execute=True,limit=2,after=after)
            scanned+=result['scanned'];removed+=result['removed'];after=result['next_cursor']
            if after is None:break
        self.assertEqual((scanned,removed),(10,5));self.assertIsNone(after)
        async with self.sessions() as db:
            rows=(await db.execute(select(AdminPwaInboxTriage.source,AdminPwaInboxTriage.source_id))).all()
            self.assertEqual({(r.source,r.source_id) for r in rows},set(ids.items()))
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaInboxTriageAudit)),10)
            for source,model in SOURCE_MODELS.items():
                self.assertIsNotNone(await db.get(model,ids[source]))

    async def test_failed_transaction_rolls_back_cleanup_and_repeated_sweep_is_idempotent(self):
        await self.seed_metadata()
        with self.assertRaises(RuntimeError):
            async with self.sessions() as db:
                async with db.begin():
                    self.assertEqual((await scan_orphaned_inbox_triage(db,execute=True))['removed'],5)
                    raise RuntimeError('synthetic caller failure')
        self.assertEqual((await run(self.sessions))['orphan_candidates'],5)
        self.assertEqual((await run(self.sessions,execute=True))['removed'],5)
        self.assertEqual((await run(self.sessions,execute=True))['removed'],0)

    async def test_invalid_limits_and_cursors_are_rejected_before_sql(self):
        async with self.sessions() as db:
            for value in (True,0,1001,-1,1.5,'100'):
                with self.assertRaises(ValueError):await scan_orphaned_inbox_triage(db,limit=value)
            for after in (('unknown',1),('bot',True),('bot',0),('bot',2_147_483_648),('bot',),['bot',1]):
                with self.assertRaises(ValueError):await scan_orphaned_inbox_triage(db,after=after)


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'),'requires disposable PostgreSQL')
class InboxRetentionPostgresTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown=pg.AdminPwaSettingsPostgresTests.asyncTearDown
    seed_metadata=InboxRetentionTests.seed_metadata

    async def test_active_metadata_lock_is_skipped_and_read_only_preview_works(self):
        await self.seed_metadata()
        self.assertEqual((await run(self.sessions))['orphan_candidates'],5)
        async with self.sessions() as holder:
            async with holder.begin():
                await holder.scalar(select(AdminPwaInboxTriage).where(
                    AdminPwaInboxTriage.source=='android',AdminPwaInboxTriage.source_id==900001).with_for_update())
                result=await run(self.sessions,execute=True)
                self.assertEqual((result['scanned'],result['removed']),(9,4))
        self.assertEqual((await run(self.sessions,execute=True))['removed'],1)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaInboxTriageAudit)),10)
