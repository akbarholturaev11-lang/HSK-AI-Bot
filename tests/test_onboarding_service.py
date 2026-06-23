import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.bot.fsm.onboarding import OnboardingStates
from app.bot.handlers.start import cmd_start
from app.services.onboarding_service import (
    ONBOARDING_LANGUAGE_MODE,
    ONBOARDING_MODE_CHOICE_MODE,
    OnboardingService,
    can_attach_start_referral,
    onboarding_stage,
)
from app.services.referral_service import ReferralService


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
    async def test_attach_referral_activates_immediately_when_user_already_eligible(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = ReferralService(session)
        invited = SimpleNamespace(
            telegram_id=123,
            referred_by_telegram_id=None,
            questions_used=2,
        )
        referrer = SimpleNamespace(telegram_id=777)
        service.user_repo = SimpleNamespace(
            get_by_telegram_id=AsyncMock(side_effect=[invited, referrer]),
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
            referral_code="abc123",
            bot=bot,
        )

        service.referral_repo.create.assert_awaited_once_with(
            referrer_telegram_id=777,
            invited_user_telegram_id=123,
        )
        service.activate_referral_if_eligible.assert_awaited_once_with(
            bot=bot,
            invited_user_telegram_id=123,
        )


class StartHandlerOnboardingTests(unittest.IsolatedAsyncioTestCase):
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
        self.assertIn("Qanday o‘rganishni xohlaysiz?", text)
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


if __name__ == "__main__":
    unittest.main()
