import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.bot.keyboards.feedback import LIKE_SUB_OPTIONS, PAID_OPTIONS
from app.services.bot_feedback_service import (
    FEEDBACK_REWARD_DURATION,
    BotFeedbackService,
    feedback_prompt_for,
)
from app.services.discount_notification_service import DiscountNotificationService


NOW = datetime.now(timezone.utc)


def _user(**kwargs):
    base = dict(
        id=1,
        telegram_id=100,
        language="uz",
        status="trial",
        payment_status="none",
        start_date=None,
        end_date=None,
        questions_used=3,
        last_limit_reset_at=None,
        expiry_reminder_sent_at=NOW,
        selected_plan_type="1_month",
        pending_checkout_msg_id=55,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _paid_user(**kwargs):
    return _user(
        status="active",
        payment_status="approved",
        end_date=NOW + timedelta(days=10),
        **kwargs,
    )


def _feedback(**kwargs):
    base = dict(id=7, liked_code=None, disliked_code=None, reward_granted_at=None, price_offer_due_at=None)
    base.update(kwargs)
    return SimpleNamespace(**base)


class _Session:
    def __init__(self):
        self.flush_count = 0

    async def flush(self):
        self.flush_count += 1


class _FeedbackRepo:
    def __init__(self):
        self.completed = []
        self.scheduled_offers = []
        self.rewarded = []

    async def complete(self, feedback):
        self.completed.append(feedback)

    async def schedule_price_offer(self, feedback, due_at):
        self.scheduled_offers.append((feedback, due_at))

    async def mark_reward_granted(self, feedback):
        feedback.reward_granted_at = NOW
        self.rewarded.append(feedback)


def _service():
    service = BotFeedbackService.__new__(BotFeedbackService)
    service.session = _Session()
    service.feedback_repo = _FeedbackRepo()
    service.user_repo = None
    return service


class FeedbackPromptTest(unittest.TestCase):
    def test_paid_user_gets_subscription_question(self):
        text, keyboard = feedback_prompt_for(_paid_user(), _feedback(), "uz")

        self.assertIn("Obunani olganingizga", text)
        codes = [row[0].callback_data.split(":")[-1] for row in keyboard.inline_keyboard]
        self.assertEqual(codes, list(PAID_OPTIONS))

    def test_temporary_trial_user_keeps_classic_question(self):
        temp_user = _user(status="active", end_date=NOW + timedelta(minutes=30))
        _, keyboard = feedback_prompt_for(temp_user, _feedback(), "uz")

        self.assertTrue(keyboard.inline_keyboard[0][0].callback_data.startswith("fb:7:like:"))

    def test_free_user_resumes_at_dislike_step(self):
        text, keyboard = feedback_prompt_for(_user(), _feedback(liked_code="course"), "uz")

        self.assertIn("noqulay", text)
        self.assertTrue(keyboard.inline_keyboard[0][0].callback_data.startswith("fb:7:dislike:"))

    def test_every_like_option_with_substep_has_other_escape(self):
        for parent, codes in LIKE_SUB_OPTIONS.items():
            self.assertIn("other", codes, parent)


class FeedbackRewardTest(unittest.IsolatedAsyncioTestCase):
    async def test_paid_user_subscription_is_never_touched(self):
        service = _service()
        user = _paid_user()
        original_end = user.end_date
        feedback = _feedback()

        await service.grant_feedback_reward(user, feedback)

        self.assertEqual(user.end_date, original_end)
        self.assertEqual(user.selected_plan_type, "1_month")
        self.assertEqual(user.questions_used, 3)
        self.assertIsNone(feedback.reward_granted_at)

    async def test_free_user_still_gets_30_minute_access(self):
        service = _service()
        user = _user()
        feedback = _feedback()

        await service.grant_feedback_reward(user, feedback)

        self.assertEqual(user.status, "active")
        self.assertIsNotNone(user.end_date)
        self.assertLessEqual(user.end_date - user.start_date, FEEDBACK_REWARD_DURATION)
        self.assertIsNotNone(feedback.reward_granted_at)

    async def test_paid_user_gets_no_price_discount_offer(self):
        service = _service()
        feedback = _feedback(disliked_code="price")

        await service.finish_feedback(feedback, _paid_user())

        self.assertEqual(service.feedback_repo.scheduled_offers, [])

    async def test_free_user_still_gets_price_discount_offer(self):
        service = _service()
        feedback = _feedback(disliked_code="price")

        await service.finish_feedback(feedback, _user())

        self.assertEqual(len(service.feedback_repo.scheduled_offers), 1)


class _CampaignUserRepo:
    def __init__(self, users):
        self.users = users

    async def get_filtered_users(self, **_kwargs):
        return self.users

    async def get_by_telegram_id(self, telegram_id):
        return next((u for u in self.users if u.telegram_id == telegram_id), None)


class DiscountAudienceTest(unittest.IsolatedAsyncioTestCase):
    async def test_active_subscribers_are_excluded_from_broadcast(self):
        service = DiscountNotificationService.__new__(DiscountNotificationService)
        service.user_repo = _CampaignUserRepo(
            [
                _user(telegram_id=1),
                _paid_user(telegram_id=2),
                _user(telegram_id=3, status="expired"),
            ]
        )
        campaign = SimpleNamespace(
            target_telegram_id=None,
            audience_language=None,
            audience_status="active",
            audience_level=None,
        )

        users = await service._target_users(campaign)

        self.assertEqual([u.telegram_id for u in users], [1, 3])

    async def test_admin_can_still_target_one_subscriber_directly(self):
        service = DiscountNotificationService.__new__(DiscountNotificationService)
        service.user_repo = _CampaignUserRepo([_paid_user(telegram_id=2)])
        campaign = SimpleNamespace(
            target_telegram_id=2,
            audience_language=None,
            audience_status=None,
            audience_level=None,
        )

        users = await service._target_users(campaign)

        self.assertEqual([u.telegram_id for u in users], [2])


if __name__ == "__main__":
    unittest.main()
