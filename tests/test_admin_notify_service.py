import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.admin_notify_service import AdminNotifyService


class AdminNotifyServiceTests(unittest.IsolatedAsyncioTestCase):
    def _service(self):
        service = AdminNotifyService()
        service.admin_ids = [111]
        service.feedback_notify_chat_ids = [-1004311413349]
        return service

    def _bot(self):
        return SimpleNamespace(
            send_message=AsyncMock(),
            send_photo=AsyncMock(),
            send_document=AsyncMock(),
        )

    def _user(self):
        return SimpleNamespace(
            telegram_id=222,
            full_name="Akbar",
            language="uz",
            level="hsk1",
            learning_mode="course",
            created_at=None,
        )

    async def test_bot_feedback_goes_to_admin_and_feedback_group(self):
        service = self._service()
        bot = self._bot()
        feedback = SimpleNamespace(
            id=7,
            liked_text="Kurs qulay",
            disliked_text="Narx qimmat",
            reward_granted_at=None,
            disliked_attachment_file_id=None,
            disliked_attachment_type=None,
        )

        await service.notify_bot_feedback(bot, feedback=feedback, user=self._user())

        self.assertEqual(bot.send_message.await_count, 2)
        admin_call, group_call = bot.send_message.await_args_list
        self.assertEqual(admin_call.kwargs["chat_id"], 111)
        self.assertIsNotNone(admin_call.kwargs["reply_markup"])
        self.assertEqual(group_call.kwargs["chat_id"], -1004311413349)
        self.assertIsNone(group_call.kwargs["reply_markup"])

    async def test_release_feedback_rating_goes_to_admin_and_feedback_group(self):
        service = self._service()
        bot = self._bot()
        campaign = SimpleNamespace(id=3, title="Course update", feature_key="course")
        response = SimpleNamespace(
            rating=5,
            comment_text="Yaxshi chiqibdi",
            attachment_file_id=None,
            attachment_type=None,
            discount_campaign_id=44,
        )

        await service.notify_release_feedback_response(
            bot,
            campaign=campaign,
            response=response,
            user=self._user(),
        )

        self.assertEqual(bot.send_message.await_count, 2)
        chat_ids = [call.kwargs["chat_id"] for call in bot.send_message.await_args_list]
        self.assertEqual(chat_ids, [111, -1004311413349])
        self.assertIn("5/5", bot.send_message.await_args_list[0].kwargs["text"])

