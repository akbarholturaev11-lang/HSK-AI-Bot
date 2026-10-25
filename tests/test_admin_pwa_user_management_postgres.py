"""Real account-row wait cannot outlive a signed account command's authority."""
import asyncio
from datetime import datetime, timedelta, timezone
import os
import unittest

from sqlalchemy import event, select

from app.admin_api import pwa_user_management as api
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.user import User
from tests import test_admin_pwa_settings_postgres as pg
from tests import test_admin_pwa_user_management as unit
from tests import test_admin_pwa_payment_review as fixtures


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'),'requires disposable test PostgreSQL')
class UserManagementPostgresTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp = pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown = pg.AdminPwaSettingsPostgresTests.asyncTearDown
    prepare = unit.UserManagementTests.prepare
    proof = unit.UserManagementTests.proof
    execute = unit.UserManagementTests.execute

    async def test_expiry_during_real_target_user_lock_wait_rolls_back(self):
        command=await self.prepare();proof=await self.proof(command)
        async with self.sessions() as db:
            (await db.get(AdminPwaStepUp,proof)).expires_at=datetime.now(timezone.utc)+timedelta(seconds=2)
            await db.commit()
        waiting=asyncio.Event()
        def observe(conn,cursor,statement,parameters,context,many):
            if 'FROM users' in statement and 'FOR UPDATE' in statement and tuple(parameters)==(1,):
                waiting.set()
        task=None
        async with self.sessions() as blocker:
            async with blocker.begin():
                await blocker.scalar(select(User.id).where(User.id==1).with_for_update())
                event.listen(self.engine.sync_engine,'before_cursor_execute',observe)
                try:
                    task=asyncio.create_task(self.execute(command,proof))
                    await asyncio.wait_for(waiting.wait(),5)
                    self.assertFalse(task.done())
                    await asyncio.sleep(2.1)
                finally:
                    event.remove(self.engine.sync_engine,'before_cursor_execute',observe)
        try:
            with self.assertRaises(api.CommandError) as denied:
                await asyncio.wait_for(task,5)
            self.assertEqual(denied.exception.status,403)
            async with self.sessions() as db:
                self.assertEqual((await db.get(User,1)).status,'free')
                self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')
        finally:
            if task is not None and not task.done():
                task.cancel();await asyncio.gather(task,return_exceptions=True)
