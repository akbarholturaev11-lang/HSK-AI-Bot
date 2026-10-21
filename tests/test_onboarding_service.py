import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.bot.fsm.onboarding import OnboardingStates
from app.bot.handlers.start import _send_android_referral_apk, cmd_start, process_language, router as start_router
from app.bot.handlers.commands import command_language_callback_handler
from app.services.onboarding_service import (
    ONBOARDING_LANGUAGE_MODE,
    ONBOARDING_MODE_CHOICE_MODE,
    OnboardingService,
    can_attach_start_referral,
    onboarding_stage,
)
from app.services.referral_service import (
    REFERRAL_TRIAL_REQUIRED_ACTIVE,
    ReferralService,
    normalize_referral_code,
    discount_platform_from_payload,
)


class OnboardingServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_user_is_persisted_as_incomplete_onboarding(self):
        session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
        service = OnboardingService(session)
        user = SimpleNamespace(telegram_id=123, learning_mode=ONBOARDING_LANGUAGE_MODE)
        service.user_repo = SimpleNamespace(
            get_by_telegram_id=AsyncMock(side_effect=[None, user]),
            create=AsyncMock(return_value=user),
        )
        service.referral_service = SimpleNamespace(
            attach_referral_if_needed=AsyncMock(),
        )

        result, created = await service.get_or_create_user(
            telegram_id=123,
            full_name="Ali",
            username="ali",
        )

        self.assertIs(result, user)
        self.assertTrue(created)
        service.user_repo.create.assert_awaited_once_with(
            telegram_id=123,
            full_name="Ali",
            username="ali",
            language="tj",
            level="beginner",
            learning_mode=ONBOARDING_LANGUAGE_MODE,
        )
        service.referral_service.attach_referral_if_needed.assert_awaited_once_with(
            invited_user_telegram_id=123,
            referral_code=None,
            bot=None,
        )
        session.commit.assert_awaited_once()

    async def test_existing_incomplete_user_can_still_attach_referral(self):
        session = SimpleNamespace(flush=AsyncMock(), commit=AsyncMock())
        service = OnboardingService(session)
        user = SimpleNamespace(
            telegram_id=123,
            full_name="Ali",
            username="ali",
            learning_mode=ONBOARDING_LANGUAGE_MODE,
        )
        service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        service.referral_service = SimpleNamespace(
            attach_referral_if_needed=AsyncMock(),
        )
        bot = SimpleNamespace()

        result, created = await service.get_or_create_user(
            telegram_id=123,
            full_name="Ali",
            username="ali",
            referral_code="abc123",
            bot=bot,
        )

        self.assertIs(result, user)
        self.assertFalse(created)
        service.referral_service.attach_referral_if_needed.assert_awaited_once_with(
            invited_user_telegram_id=123,
            referral_code="abc123",
            bot=bot,
        )
        session.commit.assert_awaited_once()

    async def test_existing_unreferred_free_user_can_attach_start_referral(self):
        session = SimpleNamespace(flush=AsyncMock(), commit=AsyncMock())
        service = OnboardingService(session)
        user = SimpleNamespace(
            telegram_id=123,
            full_name="Ali",
            username="ali",
            learning_mode="qa",
            referred_by_telegram_id=None,
            payment_status="none",
        )
        service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        service.referral_service = SimpleNamespace(
            attach_referral_if_needed=AsyncMock(),
        )
        bot = SimpleNamespace()

        result, created = await service.get_or_create_user(
            telegram_id=123,
            full_name="Ali",
            username="ali",
            referral_code="abc123",
            bot=bot,
        )

        self.assertIs(result, user)
        self.assertFalse(created)
        service.referral_service.attach_referral_if_needed.assert_awaited_once_with(
            invited_user_telegram_id=123,
            referral_code="abc123",
            bot=bot,
        )
        session.commit.assert_awaited_once()

    def test_onboarding_stage_uses_learning_mode_marker(self):
        self.assertEqual(
            onboarding_stage(SimpleNamespace(learning_mode=ONBOARDING_LANGUAGE_MODE)),
            "language",
        )
        self.assertEqual(
            onboarding_stage(SimpleNamespace(learning_mode=ONBOARDING_MODE_CHOICE_MODE)),
            "mode",
        )
        self.assertIsNone(onboarding_stage(SimpleNamespace(learning_mode="qa")))

    def test_onboarding_markers_fit_user_learning_mode_column(self):
        self.assertLessEqual(len(ONBOARDING_LANGUAGE_MODE), 16)
        self.assertLessEqual(len(ONBOARDING_MODE_CHOICE_MODE), 16)

    def test_start_referral_attach_guard_blocks_paid_or_referred_users(self):
        self.assertTrue(can_attach_start_referral(
            SimpleNamespace(
                learning_mode="qa",
                referred_by_telegram_id=None,
                payment_status="none",
            )
        ))
        self.assertFalse(can_attach_start_referral(
            SimpleNamespace(
                learning_mode="qa",
                referred_by_telegram_id=777,
                payment_status="none",
            )
        ))
        self.assertFalse(can_attach_start_referral(
            SimpleNamespace(
                learning_mode="qa",
                referred_by_telegram_id=None,
                payment_status="approved",
            )
        ))


class ReferralServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_referral_trial_access_threshold_is_viral_enough(self):
        self.assertEqual(REFERRAL_TRIAL_REQUIRED_ACTIVE, 5)

    async def test_existing_pending_referral_activates_when_user_is_eligible(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = ReferralService(session)
        invited = SimpleNamespace(
            id=1, status="free", referrer_id=None,
            telegram_id=123,
            referred_by_telegram_id=777,
            questions_used=2,
        )
        referrer = SimpleNamespace(id=2, status="free", telegram_id=777)
        referral = SimpleNamespace(referrer_telegram_id=777, status="pending")
        service.user_repo = SimpleNamespace(
            get_by_actor=AsyncMock(return_value=invited),
            get_by_referral_code=AsyncMock(return_value=referrer),
            set_referred_by=AsyncMock(),
        )
        service.referral_repo = SimpleNamespace(
            get_by_invited_user_telegram_id=AsyncMock(return_value=referral),
            create=AsyncMock(),
        )
        service.activate_referral_if_eligible = AsyncMock()
        bot = SimpleNamespace()

        await service.attach_referral_if_needed(
            invited_user_telegram_id=123,
            referral_code="abc12345",
            bot=bot,
        )

        service.referral_repo.create.assert_not_awaited()
        service.activate_referral_if_eligible.assert_awaited_once_with(bot, invited)

    async def test_attach_referral_activates_immediately_when_user_already_eligible(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = ReferralService(session)
        invited = SimpleNamespace(
            id=1, status="free", referrer_id=None,
            telegram_id=123,
            referred_by_telegram_id=None,
            questions_used=2,
        )
        referrer = SimpleNamespace(id=2, status="free", telegram_id=777)
        service.user_repo = SimpleNamespace(
            get_by_actor=AsyncMock(return_value=invited),
            get_by_referral_code=AsyncMock(return_value=referrer),
            set_referred_by=AsyncMock(),
        )
        service.referral_repo = SimpleNamespace(
            get_by_invited_user_telegram_id=AsyncMock(return_value=None),
            create=AsyncMock(),
        )
        service.activate_referral_if_eligible = AsyncMock()
        bot = SimpleNamespace()

        await service.attach_referral_if_needed(
            invited_user_telegram_id=123,
            referral_code="abc12345",
            bot=bot,
        )

        service.referral_repo.create.assert_awaited_once_with(
            referrer_telegram_id=referrer,
            invited_user_telegram_id=invited,
            discount_platform="unknown",
        )
        service.activate_referral_if_eligible.assert_awaited_once_with(bot, invited)


class ReferralStartPayloadTests(unittest.IsolatedAsyncioTestCase):
    def test_download_site_payload_preserves_platform_and_code(self):
        self.assertEqual("android", discount_platform_from_payload("ra_a1b2c3d4"))
        self.assertEqual("ios", discount_platform_from_payload("ri_a1b2c3d4"))
        self.assertEqual("a1b2c3d4", normalize_referral_code("ra_a1b2c3d4"))
        self.assertEqual("a1b2c3d4", normalize_referral_code("ri_a1b2c3d4"))
        self.assertEqual("unknown", discount_platform_from_payload("ref_a1b2c3d4"))
        self.assertEqual("unknown", discount_platform_from_payload("ra_bad"))

    def test_legacy_prefixed_payload_resolves_to_the_stored_code(self):
        self.assertEqual("abc123", normalize_referral_code("ref_abc123"))
        self.assertEqual("abc123", normalize_referral_code(" abc123 "))
        self.assertEqual("", normalize_referral_code("ref_"))
        self.assertEqual("", normalize_referral_code(None))

    async def test_link_shared_from_the_apps_still_attributes_the_invite(self):
        # The desktop and Android clients handed out `?start=ref_<code>` links
        # for a while. Those links are already in circulation, so the invites
        # they bring in must still reach the referrer.
        session = SimpleNamespace(commit=AsyncMock())
        service = ReferralService(session)
        invited = SimpleNamespace(
            id=1, status="free", referrer_id=None,
            telegram_id=123,
            referred_by_telegram_id=None,
            questions_used=0,
        )
        referrer = SimpleNamespace(id=2, status="free", telegram_id=777)
        service.user_repo = SimpleNamespace(
            get_by_actor=AsyncMock(return_value=invited),
            get_by_referral_code=AsyncMock(return_value=referrer),
            set_referred_by=AsyncMock(),
        )
        service.referral_repo = SimpleNamespace(
            get_by_invited_user_telegram_id=AsyncMock(return_value=None),
            create=AsyncMock(),
        )
        service.activate_referral_if_eligible = AsyncMock()

        await service.attach_referral_if_needed(
            invited_user_telegram_id=123,
            referral_code="ref_abc12345",
            bot=SimpleNamespace(),
        )

        service.user_repo.get_by_referral_code.assert_awaited_once_with("abc12345")
        service.referral_repo.create.assert_awaited_once_with(
            referrer_telegram_id=referrer,
            invited_user_telegram_id=invited,
            discount_platform="unknown",
        )


class StartHandlerOnboardingTests(unittest.IsolatedAsyncioTestCase):
    async def test_android_referral_start_registers_owner_before_offering_apk(self):
        user = SimpleNamespace(telegram_id=123, learning_mode=ONBOARDING_LANGUAGE_MODE)
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=123, first_name="Ali", full_name="Ali", username="ali", language_code="uz"),
            chat=SimpleNamespace(id=123),
            answer=AsyncMock(),
            bot=SimpleNamespace(),
        )
        state = SimpleNamespace(clear=AsyncMock(), update_data=AsyncMock(), set_state=AsyncMock())
        with patch("app.bot.handlers.start.OnboardingService") as onboarding, patch(
            "app.bot.handlers.start.UserRepository"
        ) as users, patch("app.bot.handlers.start.ReferralRepository") as referrals, patch(
            "app.bot.handlers.start.send_android_app", new_callable=AsyncMock
        ) as send_apk:
            onboarding.return_value.get_or_create_user = AsyncMock(return_value=(user, True))
            users.return_value.get_by_referral_code = AsyncMock(return_value=SimpleNamespace(telegram_id=777))
            referrals.return_value.get_by_invited_user_telegram_id = AsyncMock(
                return_value=SimpleNamespace(referrer_user_id=None, referrer_telegram_id=777, discount_platform="android")
            )
            send_apk.return_value = True
            await cmd_start(message, state, SimpleNamespace(), SimpleNamespace(args="ra_a1b2c3d4"))

        onboarding.return_value.get_or_create_user.assert_awaited_once()
        message.answer.assert_awaited_once()
        body = message.answer.await_args.args[0]
        self.assertIn("Taklif hisobingizga biriktirildi", body)
        send_apk.assert_awaited_once()
        self.assertEqual((message.bot, 123, 123), send_apk.await_args.args[:3])
        self.assertEqual("android_referral_start", send_apk.await_args.kwargs["source"])
        self.assertEqual("uz", send_apk.await_args.kwargs["language"])
        state.clear.assert_awaited_once()
        state.update_data.assert_not_awaited()

    async def test_android_referral_download_is_not_offered_for_different_owner(self):
        message = SimpleNamespace(
            from_user=SimpleNamespace(language_code="uz"),
            answer=AsyncMock(),
        )
        user = SimpleNamespace(telegram_id=123)
        with patch("app.bot.handlers.start.UserRepository") as users, patch(
            "app.bot.handlers.start.ReferralRepository"
        ) as referrals:
            users.return_value.get_by_referral_code = AsyncMock(return_value=SimpleNamespace(telegram_id=777))
            referrals.return_value.get_by_invited_user_telegram_id = AsyncMock(
                return_value=SimpleNamespace(referrer_user_id=None, referrer_telegram_id=888, discount_platform="android")
            )
            sent = await _send_android_referral_apk(
                message, SimpleNamespace(), user, "ra_a1b2c3d4"
            )

        self.assertFalse(sent)
        message.answer.assert_not_awaited()

    async def test_start_resumes_mode_choice_for_incomplete_user(self):
        user = SimpleNamespace(
            language="uz",
            level="beginner",
            learning_mode=ONBOARDING_MODE_CHOICE_MODE,
        )
        message = SimpleNamespace(
            from_user=SimpleNamespace(
                id=123,
                first_name="Ali",
                full_name="Ali Vali",
                username="ali",
            ),
            answer=AsyncMock(),
            bot=SimpleNamespace(),
        )
        state = SimpleNamespace(
            clear=AsyncMock(),
            update_data=AsyncMock(),
            set_state=AsyncMock(),
        )

        with patch("app.bot.handlers.start.OnboardingService") as service_class:
            service_class.return_value.get_or_create_user = AsyncMock(
                return_value=(user, False)
            )
            await cmd_start(
                message,
                state,
                session=SimpleNamespace(),
                command=SimpleNamespace(args=None),
            )

        message.answer.assert_awaited_once()
        text = message.answer.await_args.args[0]
        self.assertIn("Kurs rejimi ochildi", text)
        state.clear.assert_awaited_once()
        state.set_state.assert_not_awaited()

    async def test_start_resumes_language_choice_for_incomplete_user(self):
        user = SimpleNamespace(
            language="tj",
            level="beginner",
            learning_mode=ONBOARDING_LANGUAGE_MODE,
        )
        onboarding_message = SimpleNamespace(message_id=77)
        message = SimpleNamespace(
            from_user=SimpleNamespace(
                id=123,
                first_name="Ali",
                full_name="Ali Vali",
                username="ali",
            ),
            answer=AsyncMock(return_value=onboarding_message),
            bot=SimpleNamespace(),
        )
        state = SimpleNamespace(
            clear=AsyncMock(),
            update_data=AsyncMock(),
            set_state=AsyncMock(),
        )

        with patch("app.bot.handlers.start.OnboardingService") as service_class:
            service_class.return_value.get_or_create_user = AsyncMock(
                return_value=(user, False)
            )
            await cmd_start(
                message,
                state,
                session=SimpleNamespace(),
                command=SimpleNamespace(args="abc123"),
            )

        self.assertIn("Забонро интихоб кунед", message.answer.await_args.args[0])
        state.update_data.assert_awaited_once_with(onboarding_message_id=77)
        state.set_state.assert_awaited_once_with(OnboardingStates.choosing_language)


class LanguageSelectionCallbackTests(unittest.IsolatedAsyncioTestCase):
    def callback(self, data):
        return SimpleNamespace(
            data=data, from_user=SimpleNamespace(id=123, full_name="Synthetic QA", username="qa"),
            answer=AsyncMock(), bot=SimpleNamespace(edit_message_text=AsyncMock()),
            message=SimpleNamespace(chat=SimpleNamespace(id=123), delete=AsyncMock(), answer=AsyncMock()),
        )

    async def test_onboarding_rejects_other_buttons_and_unknown_language_without_writes(self):
        for data in (None, "", "lang", "lang:en", "lang:", "lang:uz:extra", "level:hsk2", "cmdlang:ru"):
            with self.subTest(data=data):
                callback = self.callback(data)
                session = SimpleNamespace(commit=AsyncMock())
                state = SimpleNamespace(get_data=AsyncMock(return_value={}), clear=AsyncMock())
                with patch("app.bot.handlers.start.OnboardingService") as service:
                    await process_language(callback, state, session)
                    service.assert_not_called()
                callback.answer.assert_awaited_once()
                session.commit.assert_not_awaited()
                state.clear.assert_not_awaited()

    async def test_onboarding_router_only_matches_its_three_language_buttons(self):
        handler = next(row for row in start_router.callback_query.handlers if row.callback is process_language)
        for data in ("lang:uz", "lang:ru", "lang:tj", "level:hsk2", "cmdlang:ru", "lang:en", None):
            with self.subTest(data=data):
                matches, _ = await handler.check(self.callback(data), raw_state=OnboardingStates.choosing_language.state)
                self.assertEqual(matches, data in {"lang:uz", "lang:ru", "lang:tj"})

    async def test_onboarding_valid_languages_retain_mode_transition_and_local_copy(self):
        for language in ("uz", "ru", "tj"):
            with self.subTest(language=language):
                callback = self.callback("lang:" + language)
                session = SimpleNamespace(commit=AsyncMock())
                state = SimpleNamespace(get_data=AsyncMock(return_value={"onboarding_message_id": 77}),
                                        clear=AsyncMock())
                user = SimpleNamespace(language="ru", learning_mode=ONBOARDING_LANGUAGE_MODE)
                with patch("app.bot.handlers.start.OnboardingService") as service:
                    service.return_value.get_or_create_user = AsyncMock(return_value=(user, False))
                    await process_language(callback, state, session)
                self.assertEqual(user.language, language)
                self.assertEqual(user.learning_mode, ONBOARDING_MODE_CHOICE_MODE)
                session.commit.assert_awaited_once()
                state.clear.assert_awaited_once()
                callback.bot.edit_message_text.assert_awaited_once()

    async def test_command_language_rejects_unknown_or_malformed_buttons_before_lookup(self):
        for data in (None, "", "cmdlang", "cmdlang:", "cmdlang:en", "cmdlang:ru:extra", "lang:tj"):
            with self.subTest(data=data):
                callback = self.callback(data)
                session = SimpleNamespace(commit=AsyncMock())
                with patch("app.bot.handlers.commands.UserRepository") as repository:
                    await command_language_callback_handler(callback, session)
                    repository.assert_not_called()
                callback.answer.assert_awaited_once()
                session.commit.assert_not_awaited()
                callback.message.delete.assert_not_awaited()

    async def test_command_language_persists_each_supported_code(self):
        for language in ("uz", "ru", "tj"):
            with self.subTest(language=language):
                callback = self.callback("cmdlang:" + language)
                session = SimpleNamespace(commit=AsyncMock())
                user = SimpleNamespace(language="ru")
                with patch("app.bot.handlers.commands.UserRepository") as repository:
                    repository.return_value.get_by_telegram_id = AsyncMock(return_value=user)
                    await command_language_callback_handler(callback, session)
                self.assertEqual(user.language, language)
                session.commit.assert_awaited_once()
                callback.message.answer.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
