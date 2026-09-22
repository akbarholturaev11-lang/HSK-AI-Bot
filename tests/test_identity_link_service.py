"""The account-resolution rules that keep a provider login from taking over an account.

Most of these tests assert that something does NOT happen. That is the point:
the dangerous behaviours here are conveniences someone could add back in good
faith, so each one is pinned by a test that explains the attack.
"""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.identity_link_service import (
    IdentityLinkError,
    IdentityLinkService,
    mask_email,
)
from app.services.oidc_verifier import VerifiedIdentity


def _settings():
    return SimpleNamespace(
        DESKTOP_AUTH_SIGNING_SECRET="identity-link-test-secret-" + "x" * 40,
    )


def _user(user_id: int, telegram_id: int | None, name: str) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=name,
        language="uz",
        level="hsk1",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        daily_practice_streak=0,
        created_at=now,
        last_active_at=now,
    )


def _verified(
    provider="google",
    subject="sub-alice",
    email="alice@example.com",
    name="Alice",
) -> VerifiedIdentity:
    return VerifiedIdentity(
        provider=provider,
        subject=subject,
        email=email,
        email_verified=True,
        display_name=name,
        audience="client-web",
    )


class IdentityLinkServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all(
                [_user(1, 1001, "Alice"), _user(2, 1002, "Bob")]
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    def _service(self, session):
        return IdentityLinkService(session, _settings())

    async def _device(self, session, *, user_id, key_hash, device_id="d1"):
        now = datetime.now(timezone.utc)
        session.add(
            DesktopDevice(
                id=device_id,
                user_id=user_id,
                telegram_id=1000 + user_id,
                installation_key_hash=key_hash,
                platform="android",
                app_version="1.5.3",
                created_at=now,
            )
        )
        await session.commit()

    # --- sign-in resolution ----------------------------------------------
    async def test_unknown_identity_never_creates_or_guesses_an_account(self):
        async with self.sessions() as session:
            with self.assertRaises(IdentityLinkError) as blocked:
                await self._service(session).resolve_signin(
                    _verified(), installation_key_hash="k-unbound"
                )
            self.assertEqual(
                blocked.exception.code, "oauth_telegram_account_required"
            )
            self.assertEqual(blocked.exception.status_code, 409)
            count = await session.execute(select(UserIdentity))
            self.assertIsNone(count.scalars().first())

    async def test_matching_email_does_not_merge_into_an_existing_account(self):
        """The takeover this whole design exists to prevent."""

        async with self.sessions() as session:
            service = self._service(session)
            # Alice has already linked Google with this exact address.
            await service.link_to_user(_verified(), user_id=1)
            await session.commit()

            # An attacker controls a DIFFERENT provider account that reports
            # the same verified email (recycled Workspace address, relay, ...).
            with self.assertRaises(IdentityLinkError) as blocked:
                await service.resolve_signin(
                    _verified(subject="sub-attacker"),
                    installation_key_hash="k-attacker",
                )
            self.assertEqual(
                blocked.exception.code, "oauth_telegram_account_required"
            )

    async def test_known_identity_signs_in_and_records_the_login(self):
        async with self.sessions() as session:
            service = self._service(session)
            await service.link_to_user(_verified(), user_id=1)
            await session.commit()

            user_id = await service.resolve_signin(
                _verified(), installation_key_hash="k-alice"
            )
            await session.commit()
            self.assertEqual(user_id, 1)

            row = (
                await session.execute(select(UserIdentity))
            ).scalars().one()
            self.assertIsNotNone(row.last_login_at)

    async def test_device_bound_to_another_user_blocks_sign_in(self):
        async with self.sessions() as session:
            service = self._service(session)
            await service.link_to_user(_verified(), user_id=1)
            await session.commit()
            await self._device(session, user_id=2, key_hash="k-shared")

            with self.assertRaises(IdentityLinkError) as blocked:
                await service.resolve_signin(
                    _verified(), installation_key_hash="k-shared"
                )
            self.assertEqual(
                blocked.exception.code, "desktop_device_bound_to_other_user"
            )

    async def test_revoked_device_no_longer_blocks_sign_in(self):
        async with self.sessions() as session:
            service = self._service(session)
            await service.link_to_user(_verified(), user_id=1)
            await session.commit()
            await self._device(session, user_id=2, key_hash="k-shared")
            device = (
                await session.execute(select(DesktopDevice))
            ).scalars().one()
            device.revoked_at = datetime.now(timezone.utc)
            await session.commit()

            self.assertEqual(
                await service.resolve_signin(
                    _verified(), installation_key_hash="k-shared"
                ),
                1,
            )

    async def test_unknown_identity_on_a_bound_device_is_not_auto_linked(self):
        """A borrowed, signed-in device is not consent to attach an identity."""

        async with self.sessions() as session:
            service = self._service(session)
            await self._device(session, user_id=1, key_hash="k-alice-laptop")

            with self.assertRaises(IdentityLinkError) as blocked:
                await service.resolve_signin(
                    _verified(subject="sub-guest"),
                    installation_key_hash="k-alice-laptop",
                )
            self.assertEqual(
                blocked.exception.code, "oauth_telegram_account_required"
            )
            self.assertIsNone(
                (await session.execute(select(UserIdentity))).scalars().first()
            )

    async def test_a_blocked_account_cannot_sign_in_with_a_provider(self):
        """Parity with the bot flow, which a blocked user can never reach.

        BlockedUserMiddleware stops every bot handler, so a blocked user cannot
        approve a device link and cannot mint a new session. Without this guard
        a Google account linked before the block would still let them back in.
        """

        async with self.sessions() as session:
            service = self._service(session)
            await service.link_to_user(_verified(), user_id=1)
            user = await session.get(User, 1)
            user.status = "blocked"
            await session.commit()

            with self.assertRaises(IdentityLinkError) as blocked:
                await service.resolve_signin(
                    _verified(), installation_key_hash="k-alice"
                )
            self.assertEqual(blocked.exception.code, "user_blocked")
            self.assertEqual(blocked.exception.status_code, 403)

    async def test_a_blocked_account_cannot_add_new_sign_in_methods(self):
        async with self.sessions() as session:
            service = self._service(session)
            user = await session.get(User, 1)
            user.status = "blocked"
            await session.commit()

            with self.assertRaises(IdentityLinkError) as blocked:
                await service.link_to_user(_verified(), user_id=1)
            self.assertEqual(blocked.exception.code, "user_blocked")

    async def test_an_unblocked_account_signs_in_normally(self):
        """The guard must key off the canonical classifier, not any status."""

        async with self.sessions() as session:
            service = self._service(session)
            await service.link_to_user(_verified(), user_id=1)
            user = await session.get(User, 1)
            user.status = "active"
            user.payment_status = "approved"
            await session.commit()

            self.assertEqual(
                await service.resolve_signin(
                    _verified(), installation_key_hash="k-alice"
                ),
                1,
            )

    # --- linking ----------------------------------------------------------
    async def test_identity_bound_elsewhere_is_never_moved(self):
        async with self.sessions() as session:
            service = self._service(session)
            await service.link_to_user(_verified(), user_id=1)
            await session.commit()

            with self.assertRaises(IdentityLinkError) as blocked:
                await service.link_to_user(_verified(), user_id=2)
            self.assertEqual(
                blocked.exception.code, "oauth_identity_bound_to_other_user"
            )

            row = (await session.execute(select(UserIdentity))).scalars().one()
            self.assertEqual(row.user_id, 1)

    async def test_relinking_the_same_identity_is_idempotent(self):
        async with self.sessions() as session:
            service = self._service(session)
            first = await service.link_to_user(_verified(), user_id=1)
            await session.commit()
            again = await service.link_to_user(_verified(), user_id=1)
            await session.commit()
            self.assertEqual(first.id, again.id)

    async def test_second_google_account_on_one_user_is_refused(self):
        async with self.sessions() as session:
            service = self._service(session)
            await service.link_to_user(_verified(), user_id=1)
            await session.commit()

            with self.assertRaises(IdentityLinkError) as blocked:
                await service.link_to_user(
                    _verified(subject="sub-alice-work", email="alice@work.example"),
                    user_id=1,
                )
            self.assertEqual(
                blocked.exception.code, "oauth_identity_already_linked"
            )

    async def test_google_and_apple_can_coexist_on_one_user(self):
        async with self.sessions() as session:
            service = self._service(session)
            await service.link_to_user(_verified(), user_id=1)
            await service.link_to_user(
                _verified(provider="apple", subject="000123.abc.0001"), user_id=1
            )
            await session.commit()
            listed = await service.list_identities(1)
            self.assertEqual(
                sorted(item["provider"] for item in listed), ["apple", "google"]
            )

    async def test_the_raw_subject_is_never_stored(self):
        async with self.sessions() as session:
            service = self._service(session)
            await service.link_to_user(_verified(subject="108451234567890"), user_id=1)
            await session.commit()
            row = (await session.execute(select(UserIdentity))).scalars().one()
            self.assertNotIn("108451234567890", row.subject_hash)
            self.assertEqual(len(row.subject_hash), 64)

    async def test_listed_identities_mask_the_email(self):
        async with self.sessions() as session:
            service = self._service(session)
            await service.link_to_user(_verified(), user_id=1)
            await session.commit()
            listed = await service.list_identities(1)
            self.assertEqual(listed[0]["email_masked"], "a***e@example.com")
            self.assertNotIn("alice@example.com", str(listed))

    # --- unlinking --------------------------------------------------------
    async def test_unlinking_someone_elses_identity_reports_not_found(self):
        async with self.sessions() as session:
            service = self._service(session)
            identity = await service.link_to_user(_verified(), user_id=1)
            await session.commit()

            with self.assertRaises(IdentityLinkError) as blocked:
                await service.unlink(identity.id, user_id=2)
            # 404, not 403: never confirm the row exists on another account.
            self.assertEqual(blocked.exception.code, "oauth_identity_not_found")
            self.assertEqual(blocked.exception.status_code, 404)

    async def test_unlink_revokes_other_sessions_but_keeps_the_current_one(self):
        async with self.sessions() as session:
            service = self._service(session)
            identity = await service.link_to_user(_verified(), user_id=1)
            await self._device(session, user_id=1, key_hash="k-alice", device_id="dev-a")
            now = datetime.now(timezone.utc)
            session.add_all(
                [
                    DesktopSession(
                        id="s-current",
                        device_id="dev-a",
                        refresh_token_hash="r1",
                        expires_at=now,
                        created_at=now,
                    ),
                    DesktopSession(
                        id="s-other",
                        device_id="dev-a",
                        refresh_token_hash="r2",
                        expires_at=now,
                        created_at=now,
                    ),
                ]
            )
            await session.commit()

            outcome = await service.unlink(
                identity.id, user_id=1, keep_session_id="s-current"
            )
            await session.commit()
            self.assertEqual(outcome["sessions_revoked"], 1)

            rows = {
                row.id: row.revoked_at
                for row in (
                    await session.execute(select(DesktopSession))
                ).scalars().all()
            }
            self.assertIsNone(rows["s-current"])
            self.assertIsNotNone(rows["s-other"])

    async def test_telegram_user_can_always_unlink_their_last_provider(self):
        async with self.sessions() as session:
            service = self._service(session)
            identity = await service.link_to_user(_verified(), user_id=1)
            await session.commit()
            outcome = await service.unlink(identity.id, user_id=1)
            await session.commit()
            self.assertTrue(outcome["ok"])
            self.assertIsNone(
                (await session.execute(select(UserIdentity))).scalars().first()
            )



class IdentityUnlinkPhaseTwoTests(unittest.IsolatedAsyncioTestCase):
    """The "last identity" guard, exercised against the Phase 2 schema.

    ``users.telegram_id`` is still NOT NULL in Phase 1, so a Telegram-less user
    cannot exist yet. The guard ships now anyway — and is tested against the
    nullable shape migration 0083 will introduce — so Phase 2 cannot
    accidentally create an account nobody can sign in to.
    """

    async def asyncSetUp(self):
        self.column = User.__table__.c.telegram_id
        self.original_nullable = self.column.nullable
        self.column.nullable = True
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user(3, None, "No Telegram"))
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()
        self.column.nullable = self.original_nullable

    async def test_telegramless_user_cannot_unlink_their_only_identity(self):
        async with self.sessions() as session:
            service = IdentityLinkService(session, _settings())
            identity = await service.link_to_user(_verified(subject="sub-c"), user_id=3)
            await session.commit()

            with self.assertRaises(IdentityLinkError) as blocked:
                await service.unlink(identity.id, user_id=3)
            self.assertEqual(blocked.exception.code, "oauth_last_identity")
            self.assertEqual(blocked.exception.status_code, 409)

            await session.rollback()
            surviving = (
                await session.execute(select(UserIdentity))
            ).scalars().all()
            self.assertEqual(len(surviving), 1)

    async def test_telegramless_user_can_unlink_when_another_identity_remains(self):
        async with self.sessions() as session:
            service = IdentityLinkService(session, _settings())
            google = await service.link_to_user(_verified(subject="sub-c"), user_id=3)
            await service.link_to_user(
                _verified(provider="apple", subject="sub-c-apple"), user_id=3
            )
            await session.commit()

            outcome = await service.unlink(google.id, user_id=3)
            await session.commit()
            self.assertTrue(outcome["ok"])
            remaining = (
                await session.execute(select(UserIdentity))
            ).scalars().all()
            self.assertEqual([row.provider for row in remaining], ["apple"])


class MaskEmailTests(unittest.TestCase):
    def test_masking_keeps_the_domain_and_hides_the_local_part(self):
        for raw, expected in (
            ("learner@example.com", "l*****r@example.com"),
            ("ab@x.io", "a*@x.io"),
            ("a@x.io", "a*@x.io"),
            ("not-an-email", None),
            ("", None),
            (None, None),
        ):
            with self.subTest(email=raw):
                self.assertEqual(mask_email(raw), expected)


if __name__ == "__main__":
    unittest.main()
