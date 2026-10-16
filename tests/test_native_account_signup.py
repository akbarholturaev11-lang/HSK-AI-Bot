"""Real persistence/session contracts for first-time native account creation."""
from unittest.mock import patch
from sqlalchemy import func, select

from app.db.models.desktop import DesktopDevice
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.identity_link_service import IdentityLinkError, IdentityLinkService
from tests.test_native_oauth_api import _Base, _verified


class NativeAccountSignupTests(_Base):
    async def test_google_signup_poll_refresh_and_repeated_signin_keep_one_account(self):
        users = []
        for index in range(2):
            started = (await self.client.post('/api/v3/native-auth/oauth/start', json=self._start_body(
                installation_key=str(index) * 48, language='uz' if index == 0 else 'ru'))).json()
            with patch('app.services.google_auth.verify_android_id_token', return_value=_verified(subject='new-google')):
                result = await self.client.post('/api/v3/native-auth/oauth/assert', json={
                    'link_request_id': started['link_request_id'], 'polling_secret': started['polling_secret'],
                    'provider': 'google', 'id_token': 't' * 64})
            self.assertEqual(result.status_code, 200, result.text)
            async with self.sessions() as session:
                auth = DesktopAuthService(session, self.settings)
                signed_in = await auth.poll_link(link_request_id=started['link_request_id'], polling_secret=started['polling_secret'])
                context = await auth.authenticate(signed_in['access_token'])
                users.append(context.user.id)
                self.assertIsNone(context.user.telegram_id)
                self.assertEqual(context.user.language, 'uz')
                self.assertEqual(context.user.status, 'trial')
                self.assertIsNone(context.user.pro_trial_started_at)
                self.assertIsNone(context.user.end_date)
                self.assertNotEqual(context.user.payment_status, 'approved')
                refreshed = await auth.refresh(signed_in['refresh_token'])
                self.assertIn('access_token', refreshed)
        self.assertEqual(users[0], users[1])
        async with self.sessions() as session:
            self.assertEqual((await session.execute(select(func.count(User.id)))).scalar_one(), 3)
            self.assertEqual((await session.execute(select(func.count(UserIdentity.id)))).scalar_one(), 1)

    async def test_provider_subjects_never_merge_by_email_even_across_providers(self):
        async with self.sessions() as session:
            service = IdentityLinkService(session, self.settings)
            original = await service.resolve_signin(_verified(subject='one'), installation_key_hash='a', allow_create=True)
            other = await service.resolve_signin(_verified(subject='two'), installation_key_hash='b', allow_create=True)
            apple = await service.resolve_signin(_verified(subject='one', provider='apple'), installation_key_hash='c', allow_create=True)
            self.assertEqual(len({original, other, apple, 1, 2}), 5)
            await session.commit()

    async def test_bound_installation_does_not_create_or_attach_unknown_identity(self):
        await self._bearer()
        async with self.sessions() as session:
            device = (await session.execute(select(DesktopDevice))).scalars().one()
            with self.assertRaises(IdentityLinkError) as rejected:
                await IdentityLinkService(session, self.settings).resolve_signin(
                    _verified(subject='borrowed-device'), installation_key_hash=device.installation_key_hash, allow_create=True)
            self.assertEqual(rejected.exception.code, 'desktop_device_bound_to_other_user')
            self.assertEqual((await session.execute(select(func.count(User.id)))).scalar_one(), 2)
            self.assertEqual((await session.execute(select(func.count(UserIdentity.id)))).scalar_one(), 0)

    async def test_provider_only_unlink_preserves_last_method(self):
        async with self.sessions() as session:
            service = IdentityLinkService(session, self.settings)
            uid = await service.resolve_signin(_verified(subject='standalone'), installation_key_hash='a', allow_create=True)
            first = (await session.execute(select(UserIdentity))).scalars().one()
            with self.assertRaises(IdentityLinkError) as rejected:
                await service.unlink(first.id, user_id=uid)
            self.assertEqual(rejected.exception.code, 'oauth_last_identity')
            second = await service.link_to_user(_verified(subject='apple', provider='apple'), user_id=uid)
            await service.unlink(first.id, user_id=uid)
            with self.assertRaises(IdentityLinkError) as rejected:
                await service.unlink(second.id, user_id=uid)
            self.assertEqual(rejected.exception.code, 'oauth_last_identity')

    async def test_first_telegram_desktop_confirmation_creates_real_identity_once(self):
        async with self.sessions() as session:
            auth = DesktopAuthService(session, self.settings)
            started = await auth.start_link(platform='macos', app_version='1.5.3', installation_key='T' * 48, language='uz')
            await auth.approve_link(display_code=started['display_code'], telegram_id=7001)
            duplicate = await auth.approve_link(display_code=started['display_code'], telegram_id=7001)
            self.assertTrue(duplicate['duplicate'])
            result = await auth.poll_link(link_request_id=started['link_request_id'], polling_secret=started['polling_secret'])
            context = await auth.authenticate(result['access_token'])
            self.assertEqual(context.user.telegram_id, 7001)
            self.assertEqual(context.user.language, 'uz')
            self.assertEqual(context.user.status, 'trial')

    async def test_removed_identity_cannot_exchange_previously_approved_signin(self):
        async with self.sessions() as session:
            await IdentityLinkService(session, self.settings).link_to_user(_verified(), user_id=1)
            await session.commit()
        started = (await self.client.post('/api/v3/native-auth/oauth/start', json=self._start_body())).json()
        with patch('app.services.google_auth.verify_android_id_token', return_value=_verified()):
            verified = await self.client.post('/api/v3/native-auth/oauth/assert', json={
                'link_request_id': started['link_request_id'], 'polling_secret': started['polling_secret'],
                'provider': 'google', 'id_token': 't' * 64})
        self.assertEqual(verified.status_code, 200)
        async with self.sessions() as session:
            identity = (await session.execute(select(UserIdentity))).scalars().one()
            await IdentityLinkService(session, self.settings).unlink(identity.id, user_id=1)
            await session.commit()
            with self.assertRaises(DesktopAuthError) as rejected:
                await DesktopAuthService(session, self.settings).poll_link(
                    link_request_id=started['link_request_id'], polling_secret=started['polling_secret'])
            self.assertEqual(rejected.exception.code, 'oauth_identity_not_found')

    async def test_pending_link_proof_from_revoked_session_cannot_attach_replacement(self):
        headers = await self._bearer()
        async with self.sessions() as session:
            identity = await IdentityLinkService(session, self.settings).link_to_user(_verified(), user_id=1)
            old_id = identity.id
            await session.commit()
        started_response = await self.client.post('/api/v3/native-auth/identities/link/start', headers=headers,
            json=self._start_body(installation_key='N' * 48))
        self.assertEqual(started_response.status_code, 200, started_response.text)
        started = started_response.json()
        async with self.sessions() as session:
            await IdentityLinkService(session, self.settings).unlink(old_id, user_id=1)
            await session.commit()
        with patch('app.services.google_auth.verify_android_id_token', return_value=_verified(subject='replacement')):
            result = await self.client.post('/api/v3/native-auth/oauth/assert', json={
                'link_request_id': started['link_request_id'], 'polling_secret': started['polling_secret'],
                'provider': 'google', 'id_token': 't' * 64})
        self.assertEqual(result.status_code, 401, result.text)
        self.assertEqual(result.json()['error'], 'desktop_session_revoked')
        async with self.sessions() as session:
            self.assertEqual((await session.execute(select(func.count(UserIdentity.id)))).scalar_one(), 0)

    async def test_blocked_account_cannot_refresh_but_keeps_raw_deletion_proof(self):
        async with self.sessions() as session:
            auth = DesktopAuthService(session, self.settings)
            started = await auth.start_link(platform='android', app_version='1.5.3', installation_key='B' * 48)
            await auth.approve_link(display_code=started['display_code'], telegram_id=1001)
            tokens = await auth.poll_link(link_request_id=started['link_request_id'], polling_secret=started['polling_secret'])
            user = await session.get(User, 1)
            user.status = 'blocked'
            await session.commit()
            with self.assertRaises(DesktopAuthError) as rejected:
                await auth.refresh(tokens['refresh_token'])
            self.assertEqual(rejected.exception.code, 'user_blocked')
            self.assertEqual((await auth.authenticate(tokens['access_token'])).user.status, 'blocked')
