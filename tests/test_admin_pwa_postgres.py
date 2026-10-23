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
class AdminPwaPostgresConcurrencyTests(unittest.IsolatedAsyncioTestCase):
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
                sync_conn, checkfirst=False, tables=[
                    # Public migration baseline already contains minimal
                    # users(id); DO NOT reuse it. Force complete ORM tables
                    # into our isolated test schema via search_path.
                    User.__table__, AdminPwaSession.__table__,
                    AdminPwaCredential.__table__,
                    AdminPwaAuthenticationChallenge.__table__,
                    AdminPwaStepUp.__table__,
                ],
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


if __name__ == "__main__":
    unittest.main()
