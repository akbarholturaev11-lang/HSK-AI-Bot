"""Smart reminder situation, rotation and catalog-backed rendering (D33)."""
from datetime import date, datetime, timedelta, timezone
import unittest
from uuid import uuid4

from sqlalchemy import event, insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.notification_template import NotificationTemplate
from app.db.models.user import User
from app.services.notification_template_service import KEY_SMART_STUDY
from app.services.smart_reminder_messages import (
    ATTEMPT, JOB, POOLS, MessageFacts, choose, is_key, last_sent_days, library_text, load_facts,
    resolve_for_feed, situation, smart_study_content,
)

TODAY = date(2026, 11, 22)


class PureSelectionTests(unittest.TestCase):
    def facts(self, days_ago=None, streak=0):
        return MessageFacts(TODAY, None if days_ago is None else TODAY - timedelta(days=days_ago), streak)

    def test_situation_precedence_and_boundaries(self):
        cases = ((None, 0, "daily"), (0, 5, "daily"), (1, 1, "daily"), (1, 2, "streak"),
                 (2, 9, "comeback"), (7, 0, "comeback"), (8, 0, "long_break"), (40, 0, "long_break"))
        for days_ago, streak, expected in cases:
            with self.subTest(days_ago=days_ago, streak=streak):
                self.assertEqual(situation(self.facts(days_ago, streak)), expected)
        self.assertEqual(situation(MessageFacts()), "daily")

    def test_no_repeat_until_the_whole_pool_was_used_then_least_recent(self):
        for pool, size in POOLS.items():
            sent, picked = {}, []
            for n in range(size * 2):
                day = TODAY + timedelta(days=n)
                key = choose(pool, user_id=7, local_day=day, last_sent=sent)
                picked.append(key)
                sent[key] = day
            with self.subTest(pool=pool):
                self.assertEqual(len(set(picked[:size])), size)
                self.assertEqual(picked[size:], picked[:size])  # least recently sent first

    def test_choice_is_stable_per_account_day_and_differs_between_accounts(self):
        first = choose("daily", user_id=1, local_day=TODAY, last_sent={})
        self.assertEqual(first, choose("daily", user_id=1, local_day=TODAY, last_sent={}))
        starts = {choose("long_break", user_id=n, local_day=TODAY, last_sent={}) for n in range(1, 40)}
        self.assertGreater(len(starts), 3)

    def test_keys_are_bounded_to_known_pools(self):
        self.assertTrue(is_key("long_break.v10"))
        for bad in ("long_break.v11", "daily.v0", "streak.v7", "custom", None, 5, "daily.v1 "):
            self.assertFalse(is_key(bad), bad)

    def test_missing_catalog_variant_falls_back_without_sending_an_empty_title(self):
        from unittest.mock import patch
        from app.services.generated.notification_i18n import NOTIFICATION_MESSAGES
        with patch.dict(NOTIFICATION_MESSAGES["uz"], {"smart.msg.daily.v1.title": ""}), \
                self.assertLogs("app.services.smart_reminder_messages", "WARNING") as logs:
            self.assertIsNone(library_text("daily.v1", "uz", streak=0))
        self.assertIn("smart_catalog_missing", logs.output[0])

    def test_library_text_keeps_lesson_for_the_caller_and_fills_streak(self):
        text = library_text("streak.v3", "ru", streak=12)
        self.assertTrue(text.startswith("<b>"))
        self.assertIn("12", text)
        self.assertIn("{lesson}", text)
        self.assertNotIn("{streak}", text)


class StorageChecks:
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        @event.listens_for(self.engine.sync_engine, "connect")
        def foreign_keys(dbapi, _):
            dbapi.execute("PRAGMA foreign_keys=ON")
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime(2026, 11, 22, 14, tzinfo=timezone.utc)
        async with self.sessions.begin() as s:
            s.add_all([User(id=1, telegram_id=3001, status="free"),
                       User(id=2, telegram_id=3002, status="free")])

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def job(self, s, user_id, day, *, key=None, started=True):
        start = datetime.combine(day, datetime.min.time(), timezone.utc)
        job_id = str(uuid4())
        await s.execute(insert(JOB).values(
            id=job_id, user_id=user_id, local_day=day, timezone_name="Etc/UTC", day_start_utc=start,
            day_end_utc=start + timedelta(days=1), scheduled_at=start + timedelta(hours=12),
            expires_at=start + timedelta(hours=14), policy_version="qa-v1", state="pending",
            course_key="hsk1", lesson_order=5, content_key=key))
        if started:
            await s.execute(insert(ATTEMPT).values(
                id=str(uuid4()), job_id=job_id, attempt_key=str(uuid4()), channel="telegram",
                state="provider_accepted", prepared_at=start, started_at=start + timedelta(hours=12),
                expires_at=start + timedelta(hours=14)))
        return job_id

    async def row(self, s, job_id):
        return (await s.execute(select(JOB).where(JOB.c.id == job_id))).mappings().one()

    async def test_last_sent_is_owner_scoped_and_ignores_unsent_or_current_jobs(self):
        async with self.sessions.begin() as s:
            await self.job(s, 1, TODAY - timedelta(days=3), key="daily.v2")
            await self.job(s, 1, TODAY - timedelta(days=1), key="daily.v2")
            await self.job(s, 1, TODAY - timedelta(days=2), key="daily.v5", started=False)
            await self.job(s, 2, TODAY - timedelta(days=1), key="daily.v3")
            current = await self.job(s, 1, TODAY, key="daily.v4")
            self.assertEqual(await last_sent_days(s, 1, exclude_job_id=current),
                             {"daily.v2": TODAY - timedelta(days=1)})

    async def test_profile_streak_and_last_day_match_the_app(self):
        async with self.sessions.begin() as s:
            self.assertEqual(await load_facts(s, 1, now=self.now), MessageFacts())
            s.add(CourseMiniAppProfile(user_id=1, current_streak=9, timezone_offset_minutes=0,
                                       last_activity_date=TODAY - timedelta(days=1)))
            await s.flush()
            self.assertEqual(await load_facts(s, 1, now=self.now), MessageFacts(TODAY, TODAY - timedelta(days=1), 9))
            profile = await s.scalar(select(CourseMiniAppProfile))
            profile.last_activity_date = TODAY - timedelta(days=4)
            await s.flush()
            self.assertEqual((await load_facts(s, 1, now=self.now)).streak, 0)  # expired streak

    async def test_key_is_chosen_once_and_reused_in_every_language(self):
        async with self.sessions.begin() as s:
            s.add(CourseMiniAppProfile(user_id=1, current_streak=4, timezone_offset_minutes=0,
                                       last_activity_date=TODAY - timedelta(days=1)))
            job_id = await self.job(s, 1, TODAY, started=False)
            first = await smart_study_content(s, 1, await self.row(s, job_id), "uz", now=self.now)
            self.assertTrue(first.content_key.startswith("streak."))
            self.assertEqual((await self.row(s, job_id))["content_key"], first.content_key)
            again = await smart_study_content(s, 1, await self.row(s, job_id), "tj", now=self.now)
            self.assertEqual(again.content_key, first.content_key)
            self.assertEqual(again.params(5), {"template_service": KEY_SMART_STUDY, "lesson": 5,
                                               "content_key": first.content_key, "streak": 4})
            feed = await resolve_for_feed(s, again.params(5), "ru")
            self.assertEqual(feed["text"], library_text(first.content_key, "ru", streak=4))

    async def test_admin_custom_text_wins_per_language_and_disabled_stops(self):
        async with self.sessions.begin() as s:
            s.add(NotificationTemplate(key=KEY_SMART_STUDY, enabled=True, text_ru="Свой текст {lesson}"))
            job_id = await self.job(s, 1, TODAY, started=False)
            custom = await smart_study_content(s, 1, await self.row(s, job_id), "ru", now=self.now)
            self.assertEqual((custom.text, custom.content_key), ("Свой текст {lesson}", None))
            self.assertIsNone((await self.row(s, job_id))["content_key"])
            library = await smart_study_content(s, 1, await self.row(s, job_id), "uz", now=self.now)
            self.assertTrue(is_key(library.content_key))
            template = await s.scalar(select(NotificationTemplate))
            template.enabled = False
            await s.flush()
            self.assertIsNone(await smart_study_content(s, 1, await self.row(s, job_id), "uz", now=self.now))


class SQLiteMessageStorageTests(StorageChecks, unittest.IsolatedAsyncioTestCase):
    pass


if __name__ == "__main__":
    unittest.main()
