"""Real SQL content/inbox checks; synthetic cohorts and fake Bot only."""
import unittest
from sqlalchemy import select

from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.notification_template import NotificationTemplate
from app.db.models.user import User
from app.services.course_notification_service import CourseNotificationService
from tests.test_smart_reminder_telegram import TelegramChecks


class ContentChecks:
    postgres = False
    asyncSetUp = TelegramChecks.asyncSetUp
    asyncTearDown = TelegramChecks.asyncTearDown
    _progress = TelegramChecks._progress
    _deletion = TelegramChecks._deletion
    study = TelegramChecks.study

    async def test_template_service_roundtrip_and_reader_never_persist_rendered_copy(self):
        params = {"template_service": "streak_risk", "streak": 5}
        async with self.sessions.begin() as s:
            user = await s.get(User, 1)
            s.add(NotificationTemplate(key="streak_risk", enabled=True,
                text_ru="<b>Админ: серия {streak}</b>", text_tj="<b>Админ: силсилаи {streak}</b>"))
            self.assertTrue(await CourseNotificationService(s).record_from_text(user,
                key="streak_risk", lang="uz", text="Sent original", dedupe_key="roundtrip",
                params=params))
        for lang, text in (("ru", "Админ: серия 5"), ("tj", "Админ: силсилаи 5")):
            async with self.sessions.begin() as s:
                row = await s.scalar(select(CourseUserNotification))
                self.assertEqual(row.params, params)
                user = await s.get(User, 1)
                user.language = lang
                await s.flush()
                feed = await CourseNotificationService(s).list_for_user(user)
                self.assertEqual(feed[0]["body"], text)
                self.assertNotIn(row, s.dirty)
            async with self.sessions() as s:
                row = await s.scalar(select(CourseUserNotification))
                self.assertEqual(row.params, params)
                self.assertEqual(row.body, "Sent original")


class SQLiteContentTests(ContentChecks, unittest.IsolatedAsyncioTestCase):
    pass
