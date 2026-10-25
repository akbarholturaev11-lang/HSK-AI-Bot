"""Account commands preserve shared finance rules and exact one-use authority."""
from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select

from app.admin_api import pwa_user_management as api
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_step_up import begin_step_up, verify_step_up, operation_digest
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.payment import Payment
from app.db.models.user import User
from tests import test_admin_pwa_payment_review as fixtures
from tests.test_admin_pwa_webauthn_crypto_vectors import CRED_ID, make_assertion


class UserManagementTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def prepare(self, operation='block', user_id=1):
        request=api.PrepareUserManagement(user_id=user_id,operation=operation,
            confirm_user_id=user_id if operation=='delete' else None)
        async with self.sessions() as db:
            result=await api.prepare_user_management(db,session_cookie=fixtures.COOKIE,
                                                    request=request,settings_obj=self.settings)
        return api.UserManagementCommand.model_validate(result['operation']['payload'])

    async def proof(self, command, *, signed=False):
        operation=command.signed_operation()
        if signed:
            async with self.sessions() as db:
                start=await begin_step_up(db,session_cookie=fixtures.COOKIE,settings_obj=self.settings,**operation)
            async with self.sessions() as db:
                challenge=bytes((await db.get(AdminPwaStepUp,start.step_up_id)).challenge)
            async with self.sessions() as db:
                self.assertTrue(await verify_step_up(db,session_cookie=fixtures.COOKIE,step_up_id=start.step_up_id,
                    settings_obj=self.settings,credential=make_assertion(self.key,challenge=challenge)))
            return start.step_up_id
        now=datetime.now(timezone.utc);step_id=str(uuid4())
        async with self.sessions() as db:
            db.add(AdminPwaStepUp(id=step_id,session_id=self.session_id,user_id=101,
                action=operation['action'],target=operation['target'],payload_hash=operation_digest(**operation),
                challenge=b'U'*32,status='verified',credential_id=CRED_ID,created_at=now,verified_at=now,
                expires_at=now+timedelta(seconds=50)))
            await db.commit()
        return step_id

    async def execute(self, command, proof):
        async with self.sessions() as db:
            return await api.execute_user_management(db,session_cookie=fixtures.COOKIE,
                request=api.ExecuteUserManagement(**command.model_dump(),step_up_id=proof),settings_obj=self.settings)

    async def test_real_signed_block_and_unblock_restore_paid_state_without_new_payment(self):
        async with self.sessions() as db:
            user=await db.get(User,1);user.payment_status='approved'
            user.end_date=datetime.now(timezone.utc)+timedelta(days=2)
            await db.commit()
        command=await self.prepare();proof=await self.proof(command,signed=True)
        with patch.object(api,'invalidate_block_cache') as invalidate:
            result,notice=await self.execute(command,proof)
        self.assertTrue(result['blocked']);self.assertIsNone(notice)
        invalidate.assert_not_called()  # Canonical native-only account.
        with self.assertRaises(api.CommandError):
            await self.execute(command,proof)
        command=await self.prepare('unblock');proof=await self.proof(command)
        result,notice=await self.execute(command,proof)
        self.assertEqual(result['status'],'active');self.assertIsNone(notice)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(Payment)),1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)),2)

    async def test_delete_reuses_shared_anonymization_and_keeps_financial_and_command_facts(self):
        async with self.sessions() as db:
            payment=Payment(user_id=1,amount=97,currency='TJS',plan_type='1_month',
                payment_method='visa',payment_status='approved',screenshot_file_id='PRIVATE-receipt')
            db.add(payment);await db.flush();approved_id=payment.id
            await db.commit()
        command=await self.prepare('delete');proof=await self.proof(command,signed=True)
        result,notice=await self.execute(command,proof)
        self.assertTrue(result['deleted']);self.assertIsNone(notice)
        async with self.sessions() as db:
            self.assertIsNone(await db.get(User,1));self.assertIsNotNone(await db.get(User,2))
            self.assertIsNone(await db.get(Payment,self.payment_id))
            payment=await db.get(Payment,approved_id)
            self.assertEqual((payment.amount,payment.payment_status,payment.user_id),(97,'approved',None))
            self.assertEqual(payment.user_telegram_id,-1);self.assertIsNone(payment.screenshot_file_id)
            audit=await db.get(AdminPwaCommandAudit,result['command_id'])
            self.assertEqual((audit.action,audit.target_user_id),('users.delete',1))
            self.assertNotIn('PRIVATE',audit.result_json)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'consumed')

    async def test_audit_failure_rolls_back_delete_and_proof_and_leaves_cache_alone(self):
        command=await self.prepare('delete');proof=await self.proof(command)
        with patch.object(api,'AdminPwaCommandAudit',side_effect=RuntimeError('synthetic audit failure')), \
             patch.object(api,'invalidate_block_cache') as invalidate:
            with self.assertRaises(RuntimeError):
                await self.execute(command,proof)
        invalidate.assert_not_called()
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(User,1));self.assertIsNotNone(await db.get(Payment,self.payment_id))
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')

    async def test_stale_identity_expired_proof_and_cross_operation_tampering_do_not_write(self):
        command=await self.prepare();proof=await self.proof(command)
        tampered=command.model_copy(update={'operation':'delete','confirm_user_id':1})
        with self.assertRaises(api.CommandError) as denied:
            await self.execute(tampered,proof)
        self.assertEqual(denied.exception.status,403)
        async with self.sessions() as db:
            (await db.get(User,1)).username='changed_elsewhere';await db.commit()
        with self.assertRaises(api.CommandError) as stale:
            await self.execute(command,proof)
        self.assertEqual(stale.exception.status,409)
        command=await self.prepare();proof=await self.proof(command)
        async with self.sessions() as db:
            (await db.get(AdminPwaStepUp,proof)).expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
            await db.commit()
        with self.assertRaises(api.CommandError):
            await self.execute(command,proof)
        async with self.sessions() as db:
            self.assertEqual((await db.get(User,1)).status,'free')
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)),0)

    async def test_protected_accounts_bad_confirmation_and_revoked_authority_fail_closed(self):
        self.settings.admin_id_list.append(2002)
        for user_id in (101,2):
            for operation in ('block','delete'):
                with self.assertRaises(api.CommandError) as protected:
                    await self.prepare(operation,user_id)
                self.assertEqual(protected.exception.status,403)
        for payload in ({'user_id':1,'operation':'delete'}, {'user_id':1,'operation':'delete','confirm_user_id':2},
                        {'user_id':True,'operation':'block'}, {'user_id':1,'operation':'grant'},
                        {'user_id':1,'operation':'block','sql':'anything'}):
            with self.assertRaises(ValidationError):
                api.PrepareUserManagement.model_validate(payload)
        command=await self.prepare();proof=await self.proof(command)
        self.settings.admin_id_list=[]
        with self.assertRaises(api.CommandError):
            await self.execute(command,proof)

    async def test_unblock_notification_runs_after_commit_once_and_does_not_claim_device_delivery(self):
        async with self.sessions() as db:
            user=await db.get(User,2);user.status='blocked';await db.commit()
        command=await self.prepare('unblock',2);proof=await self.proof(command)
        calls=[]
        async def emit(notice):
            async with self.sessions() as db:
                self.assertEqual((await db.get(User,2)).status,'free')
                self.assertIsNotNone(await db.get(AdminPwaCommandAudit,notice.command_id))
            calls.append(notice);return True
        app=FastAPI();app.include_router(api.create_admin_pwa_user_management_router(
            settings_obj=self.settings,session_factory=self.sessions,emit_unblocked=emit))
        async with AsyncClient(transport=ASGITransport(app=app),base_url='https://hskai.app',
                headers={'origin':'https://hskai.app'},cookies={ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE}) as client:
            payload={**command.model_dump(),'step_up_id':proof}
            response=await client.post('/api/admin/v1/users/manage',json=payload)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['notification_delivery'],'attempted')
            self.assertEqual(response.headers['cache-control'],'no-store')
            self.assertEqual((await client.post('/api/admin/v1/users/manage',json=payload)).status_code,403)
            self.assertEqual((await client.post('/api/admin/v1/users/prepare-management',json={},
                headers={'origin':'https://evil.invalid'})).status_code,403)
        self.assertEqual(len(calls),1)
