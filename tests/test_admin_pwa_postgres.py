"""Real PostgreSQL isolation and row-lock tests for Admin PWA passkey login.

Explicitly opt in with ADMIN_PWA_TEST_DATABASE_URL. Each test uses an ephemeral
random schema, never the live users or production/admin tables. One-time
challenges, session insert, and revocation share genuine PostgreSQL locks.
"""
import asyncio
import base64
import os
import unittest
from datetime import datetime, timedelta, timezone
import hashlib
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.admin_api.pwa_sessions import authenticate_admin_pwa_session, revoke_admin_pwa_session
from app.admin_api.pwa_step_up import consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_login import (
    PasskeyLoginRateLimited, begin_passkey_login, complete_passkey_login,
)
from app.db.base import Base
from tests.test_admin_pwa_payment_review import PaymentFixtures, COOKIE
from app.admin_api.pwa_payment_review import execute_payment_review
from app.admin_api.pwa_payment_outbox import dispatch_payment_review
from app.db.models.admin_pwa_payment_review import AdminPwaPaymentReview, AdminPwaPaymentOutbox
from app.db.models.payment import Payment
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.partner import PartnerCredit
from app.services.admin_payment_review_service import PaymentReviewError
from app.services.ai_usage_budget_service import AIUsageBudgetService
from unittest.mock import AsyncMock
from app.db.models.user import User
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.db.models.admin_pwa_authentication import AdminPwaAuthenticationChallenge
from app.db.models.admin_pwa_step_up import AdminPwaStepUp


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


@unittest.skipUnless(
    os.environ.get("ADMIN_PWA_TEST_DATABASE_URL"),
    "requires isolated ADMIN_PWA_TEST_DATABASE_URL (never production)",
)
class AdminPwaPostgresConcurrencyTests(PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = "adminpwa_test_" + uuid4().hex
        url = os.environ["ADMIN_PWA_TEST_DATABASE_URL"]
        self.admin_engine = create_async_engine(url, pool_pre_ping=True)
        async with self.admin_engine.begin() as conn:
            # schema only ever contains strictly validated UUID hex characters
            await conn.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(
            url, pool_pre_ping=True,
            connect_args={
                "server_settings": {
                    "search_path": self.schema + ",public",
                    "statement_timeout": "15000",
                    "lock_timeout": "10000",
                },
            },
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
                # Complete financial models in this disposable schema; public
                # contains only the migration baseline and is never reused.
                sync_conn, checkfirst=False,
            ))
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True,
            ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app",
            admin_id_list=[9001],
        )

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin_engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin_engine.dispose()

    async def _new_login_challenge(self):
        async with self.sessions() as db:
            return await begin_passkey_login(db, settings_obj=self.settings)

    async def test_postgres_advisory_lock_makes_start_cap_atomic(self):
        async def attempt():
            try:
                return await self._new_login_challenge()
            except PasskeyLoginRateLimited:
                return "limited"
        with patch("app.admin_api.pwa_webauthn_login._MAX_STARTS", 1):
            first, second = await asyncio.wait_for(
                asyncio.gather(attempt(), attempt()), timeout=30,
            )
        self.assertEqual(sum(item == "limited" if isinstance(item, str) else False
                             for item in (first, second)), 1)
        self.assertEqual(sum(not isinstance(item, str)
                             for item in (first, second)), 1)
        async with self.sessions() as db:
            count = (await db.execute(
                select(func.count()).select_from(AdminPwaAuthenticationChallenge)
            )).scalar_one()
            self.assertEqual(count, 1)

    async def test_same_challenge_cannot_issue_two_sessions_under_contention(self):
        now = datetime.now(timezone.utc)
        cred_id = b"postgres-credential"
        handle = b"H" * 32
        async with self.sessions() as db:
            db.add(User(id=1, telegram_id=9001, status="active"))
            # Ensure FK target exists before persisting a credential. The
            # models have FKs but no ORM relationship to infer flush order.
            await db.flush()
            db.add(AdminPwaCredential(
                id=str(uuid4()), user_id=1,
                credential_id=cred_id, public_key=b"test-public-key",
                user_handle=handle, sign_count=0,
                device_type="multi_device", backed_up=True, created_at=now,
            ))
            await db.commit()
        started = await self._new_login_challenge()
        signed = {
            "id": _b64(cred_id), "rawId": _b64(cred_id), "type": "public-key",
            "response": {"userHandle": _b64(handle)},
        }
        response = SimpleNamespace(
            credential_id=cred_id, user_verified=True, new_sign_count=1,
            credential_device_type="multi_device", credential_backed_up=True,
        )

        async def finish():
            async with self.sessions() as db:
                return await complete_passkey_login(
                    db, browser_proof=started.browser_proof,
                    credential=signed, settings_obj=self.settings,
                )
        with patch("app.admin_api.pwa_webauthn_login.verify_authentication_response",
                   return_value=response):
            a, b = await asyncio.wait_for(asyncio.gather(finish(), finish()), timeout=30)
        self.assertEqual(sum(v is not None for v in (a, b)), 1)
        token = next(v.token for v in (a, b) if v is not None)
        async with self.sessions() as db:
            self.assertEqual((await db.execute(select(func.count()).select_from(
                AdminPwaSession))).scalar_one(), 1)
            self.assertEqual((await db.execute(select(
                AdminPwaAuthenticationChallenge.status
            ))).scalar_one(), "consumed")
            self.assertEqual((await db.execute(
                select(AdminPwaCredential.sign_count)
            )).scalar_one(), 1)
        async def revoke():
            async with self.sessions() as db:
                return await revoke_admin_pwa_session(db, token)
        results = await asyncio.wait_for(asyncio.gather(revoke(), revoke()), timeout=30)
        self.assertCountEqual(results, [True, False])
        async with self.sessions() as db:
            self.assertIsNone(await authenticate_admin_pwa_session(
                db, token, self.settings,
            ))


    async def test_action_receipt_consumed_once_with_real_pg_locks(self):
        now = datetime.now(timezone.utc)
        cookie = "S" * 64
        receipt_id = str(uuid4())
        session_id = str(uuid4())
        payload = {"user_id": 77, "reason": "duplicate"}
        action = "users.delete"
        target = "77"
        async with self.sessions() as db:
            db.add(User(id=11, telegram_id=9001, status="active"))
            await db.flush()
            db.add(AdminPwaSession(
                id=session_id, user_id=11,
                token_hash=hashlib.sha256(cookie.encode()).hexdigest(),
                auth_method="webauthn", created_at=now,
                expires_at=now + timedelta(hours=1),
            ))
            await db.flush()
            db.add(AdminPwaCredential(
                id=str(uuid4()), user_id=11, credential_id=b"stepup-pg-key",
                public_key=b"synthetic-public-key", user_handle=b"H" * 32,
                sign_count=1, device_type="multi_device", backed_up=True,
                created_at=now,
            ))
            await db.flush()
            db.add(AdminPwaStepUp(
                id=receipt_id, session_id=session_id, user_id=11,
                action=action, target=target,
                payload_hash=operation_digest(
                    action=action, target=target, payload=payload,
                ),
                challenge=b"C" * 32, status="verified",
                credential_id=b"stepup-pg-key",
                created_at=now, verified_at=now,
                expires_at=now + timedelta(seconds=50),
            ))
            await db.commit()

        async def consume(*, target_value=target):
            async with self.sessions() as db:
                async with db.begin():
                    return await consume_step_up_in_mutation(
                        db, session_cookie=cookie, step_up_id=receipt_id,
                        action=action, target=target_value, payload=payload,
                        settings_obj=self.settings,
                    )
        self.assertFalse(await consume(target_value="99"))
        a, b = await asyncio.wait_for(
            asyncio.gather(consume(), consume()), timeout=30,
        )
        self.assertCountEqual([a, b], [True, False])
        async with self.sessions() as db:
            row = (await db.execute(select(AdminPwaStepUp))).scalar_one()
            self.assertEqual(row.status, "consumed")
            self.assertIsNotNone(row.consumed_at)


    async def test_same_payment_two_distinct_step_ups_only_one_financial_commit(self):
        await self.seed_payment(partner=True)
        command = await self.command()
        receipt_a, receipt_b = await self.receipt(command), await self.receipt(command)
        async def finish(receipt):
            try:
                return await self.execute(command, receipt)
            except PaymentReviewError as exc:
                return str(exc)
        with patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                          new=AsyncMock(return_value={"tjs": 10, "cny": 7})):
            results = await asyncio.wait_for(asyncio.gather(finish(receipt_a), finish(receipt_b)), timeout=30)
        self.assertEqual(sum(isinstance(r, dict) for r in results), 1)
        self.assertIn("payment_already_reviewed", results)
        async with self.sessions() as db:
            self.assertCountEqual(list((await db.scalars(select(AdminPwaStepUp.status))).all()), ["consumed", "verified"])
            for model in (AdminPwaPaymentReview, AdminPwaPaymentOutbox, AIUsageBudget, PortfolioTransaction):
                self.assertEqual(await db.scalar(select(func.count()).select_from(model)), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(PartnerCredit)), 2)
            user = await db.get(User, 1)
            self.assertEqual(user.end_date-user.start_date, timedelta(days=30))

    async def test_same_receipt_parallel_approval_and_outbox_attempt_are_one_use(self):
        await self.seed_payment()
        command = await self.command()
        receipt = await self.receipt(command)
        async def finish():
            try:
                return await self.execute(command, receipt)
            except PaymentReviewError:
                return None
        with patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                          new=AsyncMock(return_value={"tjs": 10, "cny": 7})):
            results = await asyncio.wait_for(asyncio.gather(finish(), finish()), timeout=30)
        self.assertEqual(sum(r is not None for r in results), 1)
        result = next(r for r in results if r is not None)
        emitter = AsyncMock()
        async def dispatch():
            return await dispatch_payment_review(review_id=result["review_id"], session_factory=self.sessions,
                                                  settings_obj=self.settings, emit=emitter)
        attempts = await asyncio.wait_for(asyncio.gather(dispatch(), dispatch()), timeout=30)
        self.assertCountEqual(attempts, [True, False])
        emitter.assert_awaited_once()

    async def test_financial_failure_rolls_back_then_waiting_approval_can_succeed(self):
        await self.seed_payment()
        command = await self.command()
        receipt_a, receipt_b = await self.receipt(command), await self.receipt(command)
        from app.services.admin_payment_review_service import review_locked_payment
        first = True
        async def fail_first(*args, **kwargs):
            nonlocal first
            result = await review_locked_payment(*args, **kwargs)
            if first:
                first = False
                raise RuntimeError("injected failure after entitlement writes")
            return result
        async def finish(receipt):
            try:
                return await self.execute(command, receipt)
            except RuntimeError:
                return None
        with patch("app.admin_api.pwa_payment_review.review_locked_payment", side_effect=fail_first), \
             patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                          new=AsyncMock(return_value={"tjs": 10, "cny": 7})):
            results = await asyncio.wait_for(asyncio.gather(finish(receipt_a), finish(receipt_b)), timeout=30)
        self.assertEqual(sum(r is not None for r in results), 1)
        async with self.sessions() as db:
            self.assertCountEqual(list((await db.scalars(select(AdminPwaStepUp.status))).all()), ["consumed", "verified"])
            for model in (AdminPwaPaymentReview, AdminPwaPaymentOutbox, AIUsageBudget, PortfolioTransaction):
                self.assertEqual(await db.scalar(select(func.count()).select_from(model)), 1)

    async def test_receipt_expiring_during_lock_wait_is_denied_at_write_boundary(self):
        await self.seed_payment()
        command = await self.command()
        receipt = await self.receipt(command, expires_at=datetime.now(timezone.utc)+timedelta(milliseconds=500))
        async with self.sessions() as blocker:
            async with blocker.begin():
                await blocker.execute(select(AdminPwaStepUp).where(AdminPwaStepUp.id == receipt).with_for_update())
                task = asyncio.create_task(self.execute(command, receipt))
                await asyncio.sleep(0.7)
        with self.assertRaisesRegex(PaymentReviewError, "step_up_denied"):
            await asyncio.wait_for(task, timeout=30)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "pending")
            self.assertEqual((await db.get(AdminPwaStepUp, receipt)).status, "verified")

    async def test_empty_qa_table_selection_runs_real_0103_through_0117_ddl(self):
        # Rehearse only in this disposable UUID schema, not through the guarded
        # Railway CLI. The production allowlist/approval guards are untouched.
        import importlib.util
        from pathlib import Path
        from sqlalchemy import inspect
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        from scripts.qa_standalone_bootstrap import (
            _registered_model_metadata, _initial_schema_tables, MIGRATION_CREATED_TABLES,
        )
        metadata = _registered_model_metadata()
        schema = self.schema + "_bootstrap"
        versions = Path(__file__).resolve().parents[1] / "alembic/versions"
        paths = sorted(path for path in versions.glob("*.py")
                       if path.name[:4].isdigit() and 103 <= int(path.name[:4]) <= 117)
        self.assertEqual(len(paths), 15)
        async with self.engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA {schema}"))
            await conn.execute(text(f"SET LOCAL search_path TO {schema}"))
            await conn.run_sync(lambda sync: metadata.create_all(
                sync, tables=_initial_schema_tables(metadata), checkfirst=False,
            ))
            initial = set(await conn.run_sync(lambda sync: inspect(sync).get_table_names(schema=schema)))
            self.assertTrue(MIGRATION_CREATED_TABLES.isdisjoint(initial))
            for path in paths:
                spec = importlib.util.spec_from_file_location("qa_migration_"+path.stem, path)
                migration = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(migration)
                def upgrade(sync):
                    with Operations.context(MigrationContext.configure(sync)):
                        migration.upgrade()
                await conn.run_sync(upgrade)
            actual = set(await conn.run_sync(lambda sync: inspect(sync).get_table_names(schema=schema)))
            self.assertTrue(set(metadata.tables).issubset(actual))
            for name in sorted(MIGRATION_CREATED_TABLES):
                columns = await conn.run_sync(lambda sync: {
                    column["name"] for column in inspect(sync).get_columns(name, schema=schema)
                })
                self.assertEqual(columns, set(metadata.tables[name].columns.keys()), name)
                self.assertEqual((await conn.execute(text(f"SELECT count(*) FROM {name}"))).scalar_one(), 0)
            await conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))

    async def test_actual_0117_migration_preserves_nonempty_financial_audit(self):
        import importlib.util
        from pathlib import Path
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        path = Path(__file__).resolve().parents[1] / "alembic/versions/0117_admin_pwa_payment_reviews.py"
        spec = importlib.util.spec_from_file_location("pwa_payment_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        schema = self.schema + "_migration"
        async with self.engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA {schema}"))
            await conn.execute(text(f"SET LOCAL search_path TO {schema}"))
            def upgrade(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    migration.upgrade()
            def downgrade(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    migration.downgrade()
            await conn.run_sync(upgrade)
            await conn.execute(text("""INSERT INTO admin_pwa_payment_reviews
                (id, step_up_id, payment_id, actor_user_id, target_user_id, action,
                 decision, payload_hash, payload_json, status, created_at)
                VALUES ('synthetic-review', 'synthetic-step', 1, 101, 1, 'payments.review',
                        'approve', :digest, '{}', 'applied', CURRENT_TIMESTAMP)"""), {"digest": "a"*64})
            with self.assertRaisesRegex(RuntimeError, "audit_requires_retention"):
                await conn.run_sync(downgrade)
            self.assertEqual((await conn.execute(text("SELECT count(*) FROM admin_pwa_payment_reviews"))).scalar_one(), 1)
            # Only synthetic records in this random, disposable test schema.
            await conn.execute(text("DELETE FROM admin_pwa_payment_reviews WHERE id='synthetic-review'"))
            await conn.run_sync(downgrade)
            await conn.run_sync(upgrade)
            await conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))

    async def test_pending_signature_cannot_refresh_an_expired_lock_wait(self):
        from app.admin_api.pwa_step_up import verify_step_up
        from tests.test_admin_pwa_webauthn_crypto_vectors import make_assertion
        await self.seed_payment()
        command = await self.command()
        receipt = await self.receipt(command, status="pending", verified_at=None,
            expires_at=datetime.now(timezone.utc)+timedelta(milliseconds=500))
        async def verify():
            async with self.sessions() as db:
                return await verify_step_up(db, session_cookie=COOKIE, step_up_id=receipt,
                    credential=make_assertion(self.key), settings_obj=self.settings)
        async with self.sessions() as blocker:
            async with blocker.begin():
                await blocker.execute(select(AdminPwaStepUp).where(AdminPwaStepUp.id == receipt).with_for_update())
                task = asyncio.create_task(verify())
                await asyncio.sleep(0.7)
        self.assertFalse(await asyncio.wait_for(task, timeout=30))
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, receipt)).status, "pending")

    async def test_telegram_adapter_and_pwa_race_do_not_extend_subscription_twice(self):
        from tests.test_main_imports import MainModuleImportTests
        main = MainModuleImportTests._import_main()
        await self.seed_payment()
        command = await self.command()
        receipt = await self.receipt(command)
        async def telegram():
            async with self.sessions() as db:
                _, status = await main._review_admin_payment(db, payment_id=self.payment_id,
                                                            action="approve", reason=None)
                return status
        async def pwa():
            try:
                await self.execute(command, receipt)
                return 200
            except PaymentReviewError as exc:
                return exc.status
        with patch.object(main, "_emit_admin_payment_review_effects", new=AsyncMock()), \
             patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                          new=AsyncMock(return_value={"tjs": 10, "cny": 7})):
            statuses = await asyncio.wait_for(asyncio.gather(telegram(), pwa()), timeout=30)
        self.assertCountEqual(statuses, [200, 409])
        async with self.sessions() as db:
            user = await db.get(User, 1)
            self.assertEqual(user.end_date-user.start_date, timedelta(days=30))
            self.assertEqual(await db.scalar(select(func.count()).select_from(AIUsageBudget)), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(PortfolioTransaction)), 1)

    async def test_projection_transaction_is_read_only_and_repeatable_on_postgres(self):
        from app.admin_api.pwa_read import read_transaction, users, UsersRequest, statistics, StatisticsRequest
        from sqlalchemy import update
        from sqlalchemy.exc import DBAPIError
        await self.seed_payment()
        async with self.sessions() as db:
            async with read_transaction(db):
                self.assertEqual(await db.scalar(text("SHOW transaction_read_only")), "on")
                self.assertEqual(await db.scalar(text("SHOW transaction_isolation")), "repeatable read")
                self.assertEqual((await statistics(db, StatisticsRequest()))["metrics"]["users_total"], 3)
                self.assertEqual(len((await users(db, UsersRequest(limit=2)))["items"]), 2)
        with self.assertRaises(DBAPIError):
            async with self.sessions() as db:
                async with read_transaction(db):
                    await db.execute(update(User).where(User.id == 1).values(status="blocked"))
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(text("SHOW transaction_read_only")), "off")
            self.assertEqual((await db.get(User, 1)).status, "free")


if __name__ == "__main__":
    unittest.main()
