"""Real PostgreSQL locks; opt in using an isolated test database URL."""
import asyncio
import os
import unittest
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.desktop_auth_service import DesktopAuthService
from app.services.identity_link_service import IdentityLinkError, IdentityLinkService
from tests.test_native_oauth_api import _settings, _verified


@unittest.skipUnless(os.environ.get('NATIVE_ACCOUNT_TEST_DATABASE_URL'), 'requires isolated PostgreSQL test database')
class NativeAccountConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = 'native_test_' + uuid4().hex
        self.admin = create_async_engine(os.environ['NATIVE_ACCOUNT_TEST_DATABASE_URL'])
        async with self.admin.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA {self.schema}'))
        self.engine = create_async_engine(os.environ['NATIVE_ACCOUNT_TEST_DATABASE_URL'],
            connect_args={'server_settings': {'search_path': self.schema + ',public'}})
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA {self.schema} CASCADE'))
        await self.admin.dispose()

    async def test_parallel_first_provider_signups_create_one_account(self):
        async def signup(index):
            async with self.sessions() as session:
                uid = await IdentityLinkService(session, _settings()).resolve_signin(
                    _verified(subject='concurrent-signup'), installation_key_hash=f'install-{index}', allow_create=True)
                await session.commit()
                return uid
        ids = await asyncio.wait_for(asyncio.gather(*(signup(i) for i in range(4))), timeout=15)
        self.assertEqual(len(set(ids)), 1)
        async with self.sessions() as session:
            self.assertEqual((await session.execute(select(func.count(User.id)))).scalar_one(), 1)
            self.assertEqual((await session.execute(select(func.count(UserIdentity.id)))).scalar_one(), 1)

    async def test_parallel_unlinks_wait_for_account_lock_and_keep_one_method(self):
        async with self.sessions() as session:
            service = IdentityLinkService(session, _settings())
            uid = await service.resolve_signin(_verified(subject='one'), installation_key_hash='x', allow_create=True)
            await service.link_to_user(_verified(subject='two', provider='apple'), user_id=uid)
            ids = list((await session.execute(select(UserIdentity.id))).scalars())
            await session.commit()
        async def unlink(identity_id):
            async with self.sessions() as session:
                result = await IdentityLinkService(session, _settings()).unlink(identity_id, user_id=uid)
                await session.commit()
                return result
        async with self.sessions() as blocker:
            await blocker.execute(select(User).where(User.id == uid).with_for_update())
            tasks = [asyncio.create_task(unlink(identity_id)) for identity_id in ids]
            try:
                await asyncio.sleep(0.15)
                self.assertTrue(all(not task.done() for task in tasks), 'identity changes must wait for the account lock')
            finally:
                await blocker.commit()
            outcomes = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=15)
        self.assertEqual(sum(isinstance(result, dict) for result in outcomes), 1)
        errors = [result for result in outcomes if isinstance(result, IdentityLinkError)]
        self.assertEqual([error.code for error in errors], ['oauth_last_identity'])
        async with self.sessions() as session:
            self.assertEqual((await session.execute(select(func.count(UserIdentity.id)))).scalar_one(), 1)

    async def test_first_telegram_confirmations_share_one_real_account(self):
        requests = []
        for index in range(3):
            async with self.sessions() as session:
                requests.append(await DesktopAuthService(session, _settings()).start_link(
                    platform='macos', app_version='1.5.3', installation_key=str(index) * 48, language='uz'))
        async def approve(started):
            async with self.sessions() as session:
                await DesktopAuthService(session, _settings()).approve_link(display_code=started['display_code'], telegram_id=7777)
        await asyncio.wait_for(asyncio.gather(*(approve(started) for started in requests)), timeout=15)
        async with self.sessions() as session:
            users = list((await session.execute(select(User))).scalars())
            self.assertEqual([(user.telegram_id, user.language) for user in users], [(7777, 'uz')])
