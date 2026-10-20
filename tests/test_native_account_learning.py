"""Provider-only learners share learning rules, never another NULL identity."""

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_lessons import CourseLesson
from app.db.models.course_mistake import CourseMistake
from app.db.models.user import User
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_miniapp_onboarding_service import CourseMiniAppOnboardingService
from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService
from app.services.course_notification_service import CourseNotificationService
from app.services.study_miniapp_service import StudyMiniAppService
from app.services.miniapp_hint_service import MiniAppHintService, SECTION_HINTS
from app.services.conversion_funnel_service import ConversionFunnelService
from app.repositories.user_repo import UserRepository


class NativeAccountLearningTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.funnel_patch = patch('app.services.conversion_funnel_service.async_session_maker', self.sessions)
        self.funnel_patch.start()
        async with self.sessions() as session:
            now = datetime.now(timezone.utc)
            session.add_all([
                User(id=uid, telegram_id=tid, full_name=name, language="uz", level="hsk1",
                     status="free", payment_status="none", created_at=now, last_active_at=now)
                for uid, tid, name in ((1, None, "Google learner"), (2, None, "Apple learner"), (3, 3003, "Telegram learner"))
            ])
            session.add(CourseLesson(level="hsk1", lesson_order=1, lesson_code="native-test-hsk1-1", title="你好"))
            await session.commit()

    async def asyncTearDown(self):
        self.funnel_patch.stop()
        await self.engine.dispose()

    async def test_hint_dismissal_and_funnel_dedupe_are_per_canonical_learner(self):
        async with self.sessions() as session:
            alice, bob, legacy = [await session.get(User, uid) for uid in (1, 2, 3)]
            hints = MiniAppHintService(session)
            key = SECTION_HINTS['profile']
            self.assertIn(key, {item['key'] for item in await hints.hints_for(alice)})
            self.assertTrue(await hints.dismiss(alice, key, client='android'))
            await session.commit()
            self.assertNotIn(key, {item['key'] for item in await hints.hints_for(alice)})
            self.assertIn(key, {item['key'] for item in await hints.hints_for(bob)})
            with patch('app.services.conversion_funnel_service.async_session_maker', self.sessions):
                funnel = ConversionFunnelService()
                self.assertTrue(await funnel.record_once(event_name='limit_hit', user=alice, source='native_test'))
                self.assertFalse(await funnel.record_once(event_name='limit_hit', user=alice, source='native_test'))
                self.assertTrue(await funnel.record_once(event_name='limit_hit', user=bob, source='native_test'))
                self.assertTrue(await funnel.record(event_name='limit_hit', user=legacy, source='native_test'))
                self.assertTrue(await funnel.record(event_name='limit_hit', telegram_id=3003, source='legacy_test'))
            counts = await ConversionFunnelService(session).unique_users_by_event()
            self.assertEqual(counts['limit_hit'], 3)

    async def test_native_onboarding_and_profile_use_internal_account(self):
        async with self.sessions() as session:
            alice = await session.get(User, 1)
            result = await CourseMiniAppOnboardingService(session).complete(
                alice, level="hsk1", goal="hsk_exam", daily_minutes=20,
                start_mode="lesson_1", language="uz", timezone_offset_minutes=300,
            )
            self.assertTrue(result["ok"], result)
            payload = await StudyMiniAppService(session).get_profile_payload(alice)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["user"]["name"], "Google learner")
            self.assertEqual(payload["user"]["telegram_username"], "")
            events = (await session.execute(select(CourseMiniAppEvent))).scalars().all()
            self.assertTrue(events)
            self.assertTrue(all(event.user_id == 1 and event.telegram_id is None for event in events))
            self.assertEqual((await session.get(User, 2)).full_name, "Apple learner")
            legacy = await StudyMiniAppService(session).get_profile_payload(3003)
            self.assertEqual(legacy["user"]["name"], "Telegram learner")

    async def test_fresh_provider_starter_can_onboard_and_practice_without_paid_access(self):
        async with self.sessions() as session:
            user = await UserRepository(session).create_provider_account(full_name='New Google learner', language='uz')
            self.assertEqual(user.status, 'trial')
            result = await CourseMiniAppOnboardingService(session).complete(
                user, level='hsk1', goal='hsk_exam', daily_minutes=20,
                start_mode='lesson_1', language='uz', timezone_offset_minutes=300,
            )
            self.assertTrue(result['ok'], result)
            allowance = await CourseMiniAppAccessService(session).consume_daily_use(
                user, feature_key='training_test', ref='first-native-practice')
            self.assertTrue(allowance['allowed'], allowance)
            self.assertEqual(user.payment_status, 'none')
            self.assertIsNone(user.pro_trial_started_at)
            self.assertIsNone(user.end_date)

    async def test_daily_usage_and_idempotency_are_per_internal_user(self):
        async with self.sessions() as session:
            alice, bob = await session.get(User, 1), await session.get(User, 2)
            access = CourseMiniAppAccessService(session)
            first = await access.consume_daily_use(alice, feature_key="training_test", ref="same-attempt")
            self.assertTrue(first["allowed"], first)
            repeated = await access.consume_daily_use(alice, feature_key="training_test", ref="same-attempt")
            self.assertTrue(repeated["allowed"], repeated)
            other = await access.consume_daily_use(bob, feature_key="training_test", ref="same-attempt")
            self.assertTrue(other["allowed"], other)
            self.assertEqual(await access._daily_used_today(alice, "training_test"), 1)
            self.assertEqual(await access._daily_used_today(bob, "training_test"), 1)
            denied = await access.consume_daily_use(alice, feature_key="training_test", ref="another-attempt")
            self.assertFalse(denied["allowed"], denied)

    async def test_native_practice_saves_score_and_rejects_other_accounts_session(self):
        questions = [{
            "id": "nihao", "level": "hsk1", "lesson": 1, "type": "multiple_choice",
            "subtype": "hanzi_to_meaning", "prompt": "你好", "sentence": "你好！",
            "audio_text": "", "pinyin": "nǐ hǎo", "format": "meaning_choice",
            "category": "word", "options": ["Salom", "Rahmat"], "answer_index": 0,
            "explanation": "你好 — salom.",
        }]
        async with self.sessions() as session:
            alice, bob = await session.get(User, 1), await session.get(User, 2)
            practice = CourseMiniAppPracticeService(session)
            practice._questions = AsyncMock(return_value=questions)
            started = await practice.start(alice, mode="mock", level="hsk1", lang="uz")
            self.assertTrue(started["ok"], started)
            args = dict(session_id=started["session"]["id"], mode="mock", level="hsk1",
                        lang="uz", skill="", answers=[{"question_id": "nihao", "selected_index": 1}])
            refused = await practice.complete(bob, **args)
            self.assertEqual(refused["error"], "invalid_practice_session")
            completed = await practice.complete(alice, **args)
            self.assertTrue(completed["ok"], completed)
            self.assertEqual((completed["score"], completed["total"]), (0, 1))
            mistakes = (await session.execute(select(CourseMistake))).scalars().all()
            self.assertEqual(len(mistakes), 1)
            self.assertEqual(mistakes[0].user_id, alice.id)
            finished = (await session.execute(select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.event_name == "test_completed"))).scalars().one()
            self.assertEqual(finished.user_id, alice.id)
            self.assertIsNone(finished.telegram_id)

    async def test_notification_feed_and_dedupe_do_not_mix_null_telegram_ids(self):
        async with self.sessions() as session:
            alice, bob = await session.get(User, 1), await session.get(User, 2)
            notices = CourseNotificationService(session)
            common = dict(key="lesson_time", lang="uz", title="Dars", dedupe_key="same-notice")
            self.assertTrue(await notices.record(alice, body="Google account notice", **common))
            self.assertTrue(await notices.record(bob, body="Apple account notice", **common))
            self.assertFalse(await notices.record(alice, body="Duplicate", **common))
            self.assertEqual([row["body"] for row in await notices.list_for_user(alice)], ["Google account notice"])
            self.assertEqual([row["body"] for row in await notices.list_for_user(bob)], ["Apple account notice"])
