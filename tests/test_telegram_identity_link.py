"""Explicit Telegram attachment requires both native proof and private consent."""
import asyncio
import os
import unittest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.native_oauth import create_native_oauth_router
from app.bot.handlers import desktop_auth as handler
from app.db.base import Base
from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.identity_link_service import IdentityLinkService
from tests.test_native_oauth_api import _settings, _verified, _user
from tests.native_postgres_deadlines import postgres_timeout


class TelegramIdentityLinkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.settings = _settings()
        await self._setup_engine()
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.installation = 'native-installation-proof'.ljust(48, 'x')
        async with self.sessions() as session:
            self.user_id = await IdentityLinkService(session, self.settings).resolve_signin(
                _verified(subject='native-target'), installation_key_hash='new', allow_create=True)
            self.bearer, self.session_id = await self._session(session, self.user_id, self.installation)
            session.add(_user(99, 9900, 'Existing Telegram owner'))
            await session.commit()
        app = FastAPI()
        app.include_router(create_native_oauth_router(session_factory=self.sessions, settings_obj=self.settings))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://identity.test')
        self.headers = {'Authorization': f'Bearer {self.bearer}'}

    async def _setup_engine(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:', poolclass=StaticPool)

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _session(self, session, user_id, installation, platform='android'):
        auth = DesktopAuthService(session, self.settings)
        started = await auth.start_link(platform=platform, app_version='1.7.17',
            installation_key=installation, flow='google')
        row = await session.get(DesktopLinkRequest, started['link_request_id'])
        row.status = 'approved'
        row.approved_user_id = user_id
        row.approved_identity_id = (await session.execute(select(UserIdentity.id)
            .where(UserIdentity.user_id == user_id))).scalar_one()
        await session.commit()
        linked = await auth.poll_link(link_request_id=row.id, polling_secret=started['polling_secret'])
        context = await auth.authenticate(linked['access_token'])
        return linked['access_token'], context.session.id

    async def _start(self, **overrides):
        body = {'platform': 'android', 'app_version': '1.7.17', 'installation_key': self.installation,
                'provider': 'telegram', 'mode': 'telegram_approval'} | overrides
        return await self.client.post('/api/v3/native-auth/identities/link/start', headers=self.headers, json=body)

    async def _pending(self):
        response = await self._start()
        self.assertEqual(response.status_code, 200, response.text)
        started = response.json()
        self.assertNotIn('access_token', started)
        self.assertNotIn('refresh_token', started)
        self.assertNotIn('display_code', started)
        self.assertEqual(started['authorize_url'],
            'https://t.me/pomp_test_bot?start=tg_identity_' + started['link_request_id'])
        return started

    async def _status(self, started, *, headers=None, endpoint='status'):
        return await self.client.post('/api/v3/native-auth/identities/link/' + endpoint,
            headers=headers or self.headers,
            json={key: started[key] for key in ('link_request_id', 'polling_secret')})

    async def test_native_and_private_telegram_proof_attach_without_new_user_or_tokens(self):
        started = await self._pending()
        async with self.sessions() as session:
            before_sessions = (await session.execute(select(func.count(DesktopSession.id)))).scalar_one()
            auth = DesktopAuthService(session, self.settings)
            details = await auth.telegram_identity_confirmation(link_request_id=started['link_request_id'], telegram_id=4400)
            self.assertEqual(details['user_id'], self.user_id)
            self.assertIsNone((await session.get(User, self.user_id)).telegram_id)
            approved = await auth.approve_telegram_identity(link_request_id=started['link_request_id'], telegram_id=4400)
            self.assertEqual(approved['status'], 'linked')
            duplicate = await auth.approve_telegram_identity(link_request_id=started['link_request_id'], telegram_id=4400)
            self.assertTrue(duplicate['duplicate'])
            self.assertEqual((await session.execute(select(func.count(User.id)))).scalar_one(), 2)
            self.assertEqual((await session.execute(select(func.count(DesktopSession.id)))).scalar_one(), before_sessions)
            devices = list((await session.execute(select(DesktopDevice).where(DesktopDevice.user_id == self.user_id))).scalars())
            self.assertTrue(all(device.telegram_id == 4400 for device in devices))
            context = await auth.authenticate(self.bearer)
            self.assertEqual(context.user.id, self.user_id)
        result = await self._status(started)
        self.assertEqual(result.json(), {'ok': True, 'status': 'linked', 'provider': 'telegram'})
        cancel = await self._status(started, endpoint='cancel')
        self.assertEqual(cancel.json()['status'], 'linked')

    async def test_existing_telegram_owner_including_blocked_cannot_be_stolen(self):
        for status in ('free', 'blocked'):
            with self.subTest(status=status):
                started = await self._pending()
                async with self.sessions() as session:
                    owner = await session.get(User, 99)
                    owner.status = status
                    await session.commit()
                    with self.assertRaises(DesktopAuthError) as refused:
                        await DesktopAuthService(session, self.settings).telegram_identity_confirmation(
                            link_request_id=started['link_request_id'], telegram_id=9900)
                    self.assertEqual(refused.exception.code, 'oauth_identity_bound_to_other_user')
                    self.assertIsNone((await session.get(User, self.user_id)).telegram_id)
                    self.assertEqual((await session.get(User, 99)).telegram_id, 9900)
                result = await self._status(started)
                self.assertEqual(result.json()['status'], 'denied')

    async def test_bot_approval_needs_reservation_and_exact_chat_identity(self):
        started = await self._pending()
        async with self.sessions() as session:
            auth = DesktopAuthService(session, self.settings)
            with self.assertRaises(DesktopAuthError):
                await auth.approve_telegram_identity(link_request_id=started['link_request_id'], telegram_id=4400)
            await auth.telegram_identity_confirmation(link_request_id=started['link_request_id'], telegram_id=4400)
            for action in (auth.telegram_identity_confirmation, auth.approve_telegram_identity, auth.deny_telegram_identity):
                with self.assertRaises(DesktopAuthError):
                    await action(link_request_id=started['link_request_id'], telegram_id=4401)
            await auth.deny_telegram_identity(link_request_id=started['link_request_id'], telegram_id=4400)
            with self.assertRaises(DesktopAuthError):
                await auth.approve_telegram_identity(link_request_id=started['link_request_id'], telegram_id=4400)
            self.assertIsNone((await session.get(User, self.user_id)).telegram_id)

    async def test_expired_revoked_or_blocked_proof_never_attaches(self):
        for failure in ('expired', 'revoked', 'session_expired', 'device_revoked', 'blocked'):
            with self.subTest(failure=failure):
                # Restore valid proof between cases; expiry row is unique per case.
                async with self.sessions() as session:
                    user = await session.get(User, self.user_id); user.status = 'free'
                    for old in (await session.execute(select(DesktopLinkRequest))).scalars():
                        old.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
                    origin = await session.get(DesktopSession, self.session_id)
                    origin.revoked_at = None; origin.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
                    device = await session.get(DesktopDevice, origin.device_id); device.revoked_at = None
                    await session.commit()
                started = await self._pending()
                async with self.sessions() as session:
                    auth = DesktopAuthService(session, self.settings)
                    await auth.telegram_identity_confirmation(link_request_id=started['link_request_id'], telegram_id=4400)
                    past = datetime.now(timezone.utc) - timedelta(seconds=1)
                    row = await session.get(DesktopLinkRequest, started['link_request_id'])
                    origin = await session.get(DesktopSession, self.session_id)
                    if failure == 'expired': row.expires_at = past
                    elif failure == 'revoked': origin.revoked_at = past
                    elif failure == 'session_expired': origin.expires_at = past
                    elif failure == 'device_revoked': (await session.get(DesktopDevice, origin.device_id)).revoked_at = past
                    else: (await session.get(User, self.user_id)).status = 'blocked'
                    await session.commit()
                    with self.assertRaises(DesktopAuthError):
                        await auth.approve_telegram_identity(link_request_id=row.id, telegram_id=4400)
                    self.assertIsNone((await session.get(User, self.user_id)).telegram_id)
                result = await self._status(started)
                self.assertEqual(result.json().get('status') if failure == 'expired' else result.status_code,
                    'expired' if failure == 'expired' else 403 if failure == 'blocked' else 401)

    async def test_linked_poll_rechecks_origin_and_blocked_state(self):
        started = await self._pending()
        async with self.sessions() as session:
            auth = DesktopAuthService(session, self.settings)
            await auth.telegram_identity_confirmation(link_request_id=started['link_request_id'], telegram_id=4400)
            await auth.approve_telegram_identity(link_request_id=started['link_request_id'], telegram_id=4400)
            origin = await session.get(DesktopSession, self.session_id)
            origin.revoked_at = datetime.now(timezone.utc)
            await session.commit()
        self.assertEqual((await self._status(started)).status_code, 401)

    async def test_foreign_actor_secret_installation_and_mode_fail_closed(self):
        self.assertEqual((await self._start(installation_key='wrong-install'.ljust(48, 'x'))).status_code, 401)
        self.assertEqual((await self._start(platform='macos')).status_code, 401)
        self.assertEqual((await self._start(mode='browser_redirect')).status_code, 422)
        self.assertEqual((await self._start(platform='miniapp')).status_code, 422)
        started = await self._pending()
        wrong = dict(started, polling_secret='z' * 48)
        self.assertEqual((await self._status(wrong)).status_code, 401)
        self.assertEqual((await self._status(wrong, endpoint='cancel')).status_code, 401)
        async with self.sessions() as session:
            other_id = await IdentityLinkService(session, self.settings).resolve_signin(
                _verified(subject='other-native'), installation_key_hash='another', allow_create=True)
            bearer, _ = await self._session(session, other_id, 'another-install'.ljust(48, 'x'))
        self.assertEqual((await self._status(started, headers={'Authorization': 'Bearer ' + bearer})).status_code, 401)
        self.assertEqual((await self._status(started, endpoint='cancel')).json()['status'], 'denied')
        async with self.sessions() as session:
            with self.assertRaises(DesktopAuthError):
                await DesktopAuthService(session, self.settings).telegram_identity_confirmation(
                    link_request_id=started['link_request_id'], telegram_id=4400)

    async def test_signin_consumers_cannot_confirm_cancel_or_mint_from_link_intent(self):
        started = await self._pending()
        async with self.sessions() as session:
            auth = DesktopAuthService(session, self.settings)
            for action in (auth.link_request_preview, auth.link_request_confirmation,
                           auth.approve_link_request, auth.cancel_link_request):
                kwargs = {'link_request_id': started['link_request_id'], 'platform': 'android'}
                if action != auth.link_request_preview: kwargs['telegram_id'] = 4400
                with self.assertRaises(DesktopAuthError): await action(**kwargs)
            with self.assertRaises(DesktopAuthError):
                await auth.poll_link(link_request_id=started['link_request_id'], polling_secret=started['polling_secret'])

    async def test_provider_approved_signin_stays_valid_when_telegram_is_attached_before_poll(self):
        async with self.sessions() as session:
            auth = DesktopAuthService(session, self.settings)
            signin = await auth.start_link(platform='windows', app_version='0.2.0',
                installation_key='pending-oauth-device'.ljust(48, 'x'), flow='google')
            row = await session.get(DesktopLinkRequest, signin['link_request_id'])
            row.status = 'approved'; row.approved_user_id = self.user_id
            row.approved_identity_id = (await session.execute(select(UserIdentity.id)
                .where(UserIdentity.user_id == self.user_id))).scalar_one()
            await session.commit()
        pending = await self._pending()
        async with self.sessions() as session:
            auth = DesktopAuthService(session, self.settings)
            await auth.telegram_identity_confirmation(link_request_id=pending['link_request_id'], telegram_id=4400)
            await auth.approve_telegram_identity(link_request_id=pending['link_request_id'], telegram_id=4400)
            linked = await auth.poll_link(link_request_id=signin['link_request_id'], polling_secret=signin['polling_secret'])
            context = await auth.authenticate(linked['access_token'])
            self.assertEqual(context.user.id, self.user_id)
            self.assertEqual(context.device.telegram_id, 4400)

    async def test_telegram_signin_still_rejects_changed_telegram_proof_snapshot(self):
        async with self.sessions() as session:
            auth = DesktopAuthService(session, self.settings)
            signin = await auth.start_link(platform='macos', app_version='0.2.0',
                installation_key='telegram-signin-snapshot'.ljust(48, 'x'))
            await auth.approve_link(display_code=signin['display_code'], telegram_id=9900)
            owner = await session.get(User, 99)
            owner.telegram_id = 9901
            await session.commit()
            with self.assertRaises(DesktopAuthError) as refused:
                await auth.poll_link(link_request_id=signin['link_request_id'], polling_secret=signin['polling_secret'])
            self.assertEqual(refused.exception.code, 'desktop_link_invalid')

    async def test_private_bot_path_skips_onboarding_and_names_target_account(self):
        started = await self._pending()
        message = SimpleNamespace(text='/start tg_identity_' + started['link_request_id'],
            chat=SimpleNamespace(type='private', id=4400), from_user=SimpleNamespace(id=4400), answer=AsyncMock())
        state = SimpleNamespace(clear=AsyncMock())
        async with self.sessions() as session:
            with patch.object(handler, 'settings', self.settings), patch.object(handler, 'OnboardingService') as onboarding:
                await handler.begin_telegram_identity_link(message, state, session)
                onboarding.assert_not_called()
            text = message.answer.await_args.args[0]
            self.assertIn(f'<code>{self.user_id}</code>', text)
            self.assertIn('Telegram', text)
            self.assertEqual((await session.execute(select(func.count(User.id)))).scalar_one(), 2)
        message.answer.reset_mock(); message.chat.type = 'group'
        async with self.sessions() as session:
            await handler.begin_telegram_identity_link(message, state, session)
        message.answer.assert_not_awaited()


@unittest.skipUnless(os.environ.get('NATIVE_ACCOUNT_TEST_DATABASE_URL'), 'requires isolated PostgreSQL test database')
class TelegramIdentityConcurrencyTests(TelegramIdentityLinkTests):
    async def _setup_engine(self):
        self.schema = 'telegram_identity_' + uuid4().hex
        self.admin = create_async_engine(os.environ['NATIVE_ACCOUNT_TEST_DATABASE_URL'])
        async with self.admin.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA {self.schema}'))
        self.engine = create_async_engine(os.environ['NATIVE_ACCOUNT_TEST_DATABASE_URL'],
            connect_args={'server_settings': {'search_path': self.schema + ',public'}})

    async def asyncTearDown(self):
        await super().asyncTearDown()
        async with self.admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA {self.schema} CASCADE'))
        await self.admin.dispose()

    async def test_same_telegram_race_has_one_canonical_owner_without_merge(self):
        first = await self._pending()
        async with self.sessions() as session:
            auth = DesktopAuthService(session, self.settings)
            second_id = await IdentityLinkService(session, self.settings).resolve_signin(
                _verified(subject='second-target'), installation_key_hash='second', allow_create=True)
            install = 'second-native-installation'.ljust(48, 'x')
            _, origin = await self._session(session, second_id, install)
            second = await auth.start_telegram_identity_link(user_id=second_id, session_id=origin,
                platform='android', app_version='1.7.17', installation_key=install)
            for pending in (first, second):
                await auth.telegram_identity_confirmation(link_request_id=pending['link_request_id'], telegram_id=5500)
        ready = asyncio.Event()
        async def approve(pending):
            async with self.sessions() as session:
                await ready.wait()
                return await DesktopAuthService(session, self.settings).approve_telegram_identity(
                    link_request_id=pending['link_request_id'], telegram_id=5500)
        tasks = [asyncio.create_task(approve(pending)) for pending in (first, second)]
        ready.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), postgres_timeout(15))
        self.assertEqual(sum(isinstance(value, dict) for value in results), 1, results)
        errors = [value for value in results if isinstance(value, DesktopAuthError)]
        self.assertEqual([error.code for error in errors], ['oauth_identity_bound_to_other_user'])
        async with self.sessions() as session:
            owners = list((await session.execute(select(User).where(User.telegram_id == 5500))).scalars())
            self.assertEqual(len(owners), 1)
            self.assertIn(owners[0].id, (self.user_id, second_id))
            self.assertEqual((await session.execute(select(func.count(User.id)))).scalar_one(), 3)

    async def test_ordinary_telegram_signup_race_cannot_move_existing_resources(self):
        first = await self._pending()
        async with self.sessions() as session:
            auth = DesktopAuthService(session, self.settings)
            await auth.telegram_identity_confirmation(link_request_id=first['link_request_id'], telegram_id=5501)
            signin = await auth.start_link(platform='macos', app_version='0.2.0', installation_key='legacy-signin'.ljust(48, 'x'))
        ready = asyncio.Event()
        async def approve_attachment():
            async with self.sessions() as session:
                await ready.wait()
                return await DesktopAuthService(session, self.settings).approve_telegram_identity(
                    link_request_id=first['link_request_id'], telegram_id=5501)
        async def approve_signin():
            async with self.sessions() as session:
                await ready.wait()
                return await DesktopAuthService(session, self.settings).approve_link(
                    display_code=signin['display_code'], telegram_id=5501)
        tasks = [asyncio.create_task(approve_attachment()), asyncio.create_task(approve_signin())]
        ready.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), postgres_timeout(15))
        self.assertIsInstance(results[1], dict, results)
        if isinstance(results[0], Exception):
            self.assertIsInstance(results[0], DesktopAuthError)
            self.assertEqual(results[0].code, 'oauth_identity_bound_to_other_user')
        async with self.sessions() as session:
            owners = list((await session.execute(select(User).where(User.telegram_id == 5501))).scalars())
            self.assertEqual(len(owners), 1)
            signin_row = await session.get(DesktopLinkRequest, signin['link_request_id'])
            self.assertEqual(signin_row.approved_user_id, owners[0].id)
            identity = (await session.execute(select(UserIdentity).where(UserIdentity.user_id == self.user_id))).scalar_one()
            self.assertEqual(identity.user_id, self.user_id)
            if isinstance(results[0], dict):
                self.assertEqual(owners[0].id, self.user_id)
            else:
                self.assertIsNone((await session.get(User, self.user_id)).telegram_id)

    async def test_approval_waits_for_origin_revocation_and_rejects_stale_snapshot(self):
        pending = await self._pending()
        async with self.sessions() as session:
            await DesktopAuthService(session, self.settings).telegram_identity_confirmation(
                link_request_id=pending['link_request_id'], telegram_id=5502)
        async def approve():
            async with self.sessions() as session:
                return await DesktopAuthService(session, self.settings).approve_telegram_identity(
                    link_request_id=pending['link_request_id'], telegram_id=5502)
        async with self.sessions() as blocker:
            origin = (await blocker.execute(select(DesktopSession).where(
                DesktopSession.id == self.session_id).with_for_update())).scalar_one()
            task = asyncio.create_task(approve())
            await asyncio.sleep(0.15)
            self.assertFalse(task.done(), 'approval must wait for current origin proof')
            origin.revoked_at = datetime.now(timezone.utc)
            await blocker.commit()
        result = (await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), postgres_timeout(15)))[0]
        self.assertIsInstance(result, DesktopAuthError)
        self.assertEqual(result.code, 'desktop_session_revoked')
        async with self.sessions() as session:
            self.assertIsNone((await session.get(User, self.user_id)).telegram_id)
