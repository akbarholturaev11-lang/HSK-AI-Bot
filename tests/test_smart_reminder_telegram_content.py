"""Real SQL content/inbox checks; synthetic cohorts and fake Bot only."""
import unittest
import os
import tempfile
from datetime import time, timedelta
from functools import partial
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from unittest.mock import AsyncMock, patch
from pathlib import Path
from sqlalchemy import select, update

from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.notification_template import NotificationTemplate
from app.db.models.user import User
from app.db.models.smart_reminder import SmartReminderPreference
from app.services.course_notification_service import CourseNotificationService
from app.services.notification_template_service import KEY_SMART_STUDY, default_text
from app.services.smart_reminder_preferences import SmartReminderError, SmartReminderPreferencesService
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB
from app.services.smart_reminder_telegram_content import render_telegram_content, send_telegram_content
from tests.test_smart_reminder_telegram import TelegramChecks


class ContentChecks:
    postgres = False
    asyncSetUp = TelegramChecks.asyncSetUp
    asyncTearDown = TelegramChecks.asyncTearDown
    _progress = TelegramChecks._progress
    _deletion = TelegramChecks._deletion
    study = TelegramChecks.study
    review = TelegramChecks.review
    active = TelegramChecks.active
    prepare = TelegramChecks.prepare
    claim = TelegramChecks.claim
    rows = TelegramChecks.rows

    async def dispatch(self, lease, sender=None):
        return await self.service.dispatch(self.actor, lease,
            sender or partial(send_telegram_content, self.bot), history_since=self.since)

    async def planned(self):
        await self.active()
        planned = await self.prepare()
        self.tick = self.tick.replace(hour=14)
        lease = await self.claim(planned.job_id)
        self.assertEqual(lease.reason, "telegram_claimed")
        return lease

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

    async def test_current_language_after_claim_reaches_bot_and_job_deduplicated_inbox(self):
        lease = await self.planned()
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == 1).values(language="tj"))
        async def sender(envelope):
            async with self.sessions.begin() as s:
                await s.execute(select(User.id).where(User.id == 1).with_for_update())
                self.assertEqual(await s.scalar(select(ATTEMPT.c.state)), "in_flight")
            return await send_telegram_content(self.bot, envelope)
        result = await self.dispatch(lease, sender)
        self.assertEqual(result.state, "provider_accepted")
        sent = self.bot.send_message.call_args.kwargs
        self.assertEqual(sent["chat_id"], 3001)
        self.assertEqual(sent["text"], default_text(KEY_SMART_STUDY, "tj").format(lesson=5))
        query = parse_qs(urlsplit(sent["reply_markup"].inline_keyboard[0][0].web_app.url).query)
        self.assertEqual({k: query[k] for k in ("lesson", "level", "lang", "source")},
                         {"lesson": ["5"], "level": ["hsk1"], "lang": ["tj"], "source": [KEY_SMART_STUDY]})
        self.assertNotIn("autostart", query)
        for lang in ("uz", "ru", "tj"):
            async with self.sessions.begin() as s:
                user = await s.get(User, 1); user.language = lang; await s.flush()
                feed = await CourseNotificationService(s).list_for_user(user)
                self.assertEqual(len(feed), 1)
                self.assertEqual((feed[0]["action"], feed[0]["level"], feed[0]["lesson_order"]), ("course", "hsk1", 5))
                self.assertIn("5", feed[0]["body"])
                self.assertNotIn("<b>", feed[0]["body"])
        await self.dispatch(lease)
        self.assertEqual(self.bot.send_message.await_count, 1)
        async with self.sessions() as s:
            rows = (await s.scalars(select(CourseUserNotification))).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].dedupe_key, "job:"+lease.job_id)
            self.assertEqual(rows[0].params, {"template_service": KEY_SMART_STUDY, "lesson": 5})

    async def test_admin_custom_copy_and_all_canonical_languages_use_real_consumer(self):
        async with self.sessions.begin() as s:
            s.add(NotificationTemplate(key=KEY_SMART_STUDY, enabled=True, text_ru="<b>Админ {lesson}</b>"))
        for lang in ("uz", "ru", "tj"):
            async with self.sessions.begin() as s:
                await SmartReminderPreferencesService(s).read(self.actor)
                await s.execute(update(User).where(User.id == 1).values(language=lang))
                result = await render_telegram_content(s, self.actor, {"course_key": "hsk1", "lesson_order": 5})
                expected = "<b>Админ 5</b>" if lang == "ru" else default_text(KEY_SMART_STUDY, lang).format(lesson=5)
                self.assertEqual(result.text, expected)

    async def test_disabled_template_after_claim_cancels_prepared_without_transport(self):
        lease = await self.planned()
        async with self.sessions.begin() as s:
            s.add(NotificationTemplate(key=KEY_SMART_STUDY, enabled=False))
        self.assertEqual((await self.dispatch(lease)).reason, "telegram_template_disabled")
        self.bot.send_message.assert_not_called()
        self.assertEqual((await self.rows(ATTEMPT))[0]["state"], "cancelled")

    async def test_invalid_fields_utf16_and_unowned_media_refuse_before_io(self):
        for text, media_type, media_path in (("{lesson.__class__}", "none", None),
                ("{lesson!r}", "none", None), ("{unknown}", "none", None),
                ("😀"*2100, "none", None), ("😀"*520, "photo", "photo.png"),
                ("{lesson}", "photo", "../private.png")):
            with self.subTest(text=text[:24], media_type=media_type):
                async with self.sessions.begin() as s:
                    row = await s.scalar(select(NotificationTemplate).where(NotificationTemplate.key == KEY_SMART_STUDY))
                    if row is None:
                        row = NotificationTemplate(key=KEY_SMART_STUDY, enabled=True);s.add(row)
                    row.text_ru = text;row.media_type = media_type;row.media_path = media_path
                    await s.execute(update(User).where(User.id == 1).values(language="ru"));await s.flush()
                    with self.assertRaises(SmartReminderError) as error:
                        await render_telegram_content(s, self.actor, {"course_key": "hsk1", "lesson_order": 5})
                    self.assertEqual(error.exception.code, "telegram_template_invalid")
        self.bot.send_message.assert_not_called()

    async def test_bad_configured_destination_cannot_smuggle_query_or_fragment(self):
        from app.bot.utils import course_miniapp
        for url in ("http://qa.invalid/course-v3.html", "https://qa.invalid/course-v3.html?token=secret",
                    "https://qa.invalid/course-v3.html#fragment", "https://name:password@qa.invalid/course-v3.html"):
            with self.subTest(url=url), patch.object(course_miniapp.settings, "MINI_APP_BASE_URL", url):
                async with self.sessions.begin() as s:
                    with self.assertRaises(SmartReminderError) as error:
                        await render_telegram_content(s, self.actor, {"course_key": "hsk1", "lesson_order": 5})
                    self.assertEqual(error.exception.code, "telegram_content_target_invalid")

    async def test_expired_lease_during_render_never_starts_io(self):
        lease = await self.planned()
        async def late(*args):
            content = await render_telegram_content(*args)
            self.tick += timedelta(minutes=1)
            return content
        with patch("app.services.smart_reminder_telegram.render_telegram_content", side_effect=late):
            self.assertEqual((await self.dispatch(lease)).reason, "telegram_lease_lost")
        self.bot.send_message.assert_not_called()
        self.assertEqual((await self.rows(ATTEMPT))[0]["state"], "prepared")

    async def test_quiet_window_crossed_during_template_read_vetoes_still_valid_lease(self):
        async with self.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id == 1)
                .values(quiet_start=time(14,1), quiet_end=time(15)))
        await self.active()
        planned = await self.prepare()
        self.tick = self.tick.replace(hour=14)
        lease = await self.claim(planned.job_id, lease_for=timedelta(minutes=5))
        self.assertEqual(lease.reason, "telegram_claimed")
        async def late(*args):
            content = await render_telegram_content(*args)
            self.tick += timedelta(minutes=2)
            return content
        with patch("app.services.smart_reminder_telegram.render_telegram_content", side_effect=late):
            result = await self.dispatch(lease)
        self.assertEqual(result.state, "cancelled")
        self.bot.send_message.assert_not_called()

    async def test_track_change_after_claim_never_renders_or_sends_old_lesson(self):
        lease = await self.planned()
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == 1).values(level="hsk2"))
        with patch("app.services.smart_reminder_telegram.render_telegram_content") as renderer:
            self.assertEqual((await self.dispatch(lease)).state, "cancelled")
            renderer.assert_not_called()
        self.bot.send_message.assert_not_called()

    async def test_unknown_provider_and_feed_commit_rollback_never_replay_or_claim_inbox_success(self):
        lease = await self.planned()
        with patch.object(CourseNotificationService, "record_from_text", side_effect=RuntimeError("feed rollback")):
            with self.assertRaisesRegex(RuntimeError, "feed rollback"):
                await self.dispatch(lease)
        self.assertEqual((await self.rows(ATTEMPT))[0]["state"], "in_flight")
        await self.dispatch(lease)
        self.assertEqual(self.bot.send_message.await_count, 1)
        async with self.sessions() as s:
            self.assertIsNone(await s.scalar(select(CourseUserNotification)))

    async def test_provider_exception_creates_no_success_feed(self):
        lease = await self.planned()
        self.bot.send_message.side_effect = RuntimeError("uncertain provider")
        self.assertEqual((await self.dispatch(lease)).state, "unknown")
        await self.dispatch(lease)
        self.assertEqual(self.bot.send_message.await_count, 1)
        async with self.sessions() as s:
            self.assertIsNone(await s.scalar(select(CourseUserNotification)))

    async def test_inbox_owner_dedupe_legacy_fallback_and_reads_never_create_jobs(self):
        async with self.sessions.begin() as s:
            service = CourseNotificationService(s)
            for uid in (1, 2):
                user = await s.get(User, uid)
                values = dict(key=KEY_SMART_STUDY, lang="uz", text="Original "+str(uid),
                    dedupe_key="same-key", params={"template_service":KEY_SMART_STUDY,"lesson":5} if uid == 1 else None)
                self.assertTrue(await service.record_from_text(user, **values))
                self.assertFalse(await service.record_from_text(user, **values))
            s.add(NotificationTemplate(key=KEY_SMART_STUDY, enabled=True, text_tj="Broken {missing}"))
        async with self.sessions.begin() as s:
            for uid, count in ((1,1),(2,1),(3,0)):
                user = await s.get(User, uid); user.language="tj"; await s.flush()
                items = await CourseNotificationService(s).list_for_user(user)
                self.assertEqual(len(items),count)
                if items:self.assertEqual(items[0]["body"],"Original "+str(uid))
            self.assertIsNone(await s.scalar(select(JOB.c.id)))
            self.assertIsNone(await s.scalar(select(ATTEMPT.c.id)))


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_owned_media_has_one_provider_call_and_uncertain_media_never_falls_back(self):
        from app.services import smart_reminder_telegram_content as content
        for media_type in ("photo", "video"):
            with self.subTest(media_type=media_type), tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/"owned.bin";path.write_bytes(b"synthetic local fixture")
                envelope=SimpleNamespace(telegram_id=3001, content=SimpleNamespace(
                    text="Rendered", markup=None, media_type=media_type, media_path=path.name))
                bot=AsyncMock()
                with patch.object(content,"MEDIA_ROOT",Path(directory)):
                    sender=bot.send_photo if media_type=="photo" else bot.send_video
                    sender.return_value=SimpleNamespace(message_id=77)
                    self.assertEqual((await send_telegram_content(bot,envelope)).message_id,77)
                    sender.assert_awaited_once();bot.send_message.assert_not_called()
                    sender.side_effect=RuntimeError("uncertain media")
                    with self.assertRaisesRegex(RuntimeError,"uncertain media"):
                        await send_telegram_content(bot,envelope)
                    bot.send_message.assert_not_called()

    async def test_missing_owned_media_uses_text_and_symlink_escape_is_refused(self):
        from app.services import smart_reminder_telegram_content as content
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            bot=AsyncMock();envelope=SimpleNamespace(telegram_id=3001, content=SimpleNamespace(
                text="Rendered", markup=None, media_type="photo", media_path="missing.png"))
            with patch.object(content,"MEDIA_ROOT",Path(directory)):
                await send_telegram_content(bot,envelope)
                bot.send_message.assert_awaited_once();bot.send_photo.assert_not_called()
                (Path(directory)/"missing.png").symlink_to(Path(outside)/"private.png")
                with self.assertRaisesRegex(ValueError,"Unowned"):
                    await send_telegram_content(bot,envelope)
                self.assertEqual(bot.send_message.await_count,1)


class SQLiteContentTests(ContentChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(os.environ.get("SMART_REMINDER_TEST_DATABASE_URL"), "owned disposable PostgreSQL required")
class PostgreSQLContentTests(ContentChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True
