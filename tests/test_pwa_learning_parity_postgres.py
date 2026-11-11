"""Real PostgreSQL row-lock verification, in a disposable unique test schema."""
import asyncio
import os
import unittest
from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.user import User
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService

URL = os.environ.get('PWA_PARITY_TEST_DATABASE_URL', '')


@unittest.skipUnless(URL.startswith('postgresql+asyncpg://'), 'PWA_PARITY_TEST_DATABASE_URL not set')
class FoundationPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_pwa_android_telegram_completions_commit_once_for_canonical_owner(self):
        schema = 'pwa_parity_' + uuid4().hex
        engine = create_async_engine(URL, connect_args={'server_settings': {'search_path': schema}}, pool_size=12)
        try:
            async with engine.begin() as connection:
                await connection.execute(text('CREATE SCHEMA ' + schema))
                await connection.run_sync(Base.metadata.create_all)
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            async with sessions() as session:
                session.add(User(id=1, telegram_id=None, full_name='Native learner', language='uz', status='free', level='beginner'))
                session.add(User(id=2, telegram_id=1002, full_name='Other learner', language='uz', status='free', level='beginner'))
                await session.commit()

            async def complete(index):
                async with sessions() as session:
                    user = await session.get(User, 1)
                    result = await CourseMiniAppProfileService(session).complete_foundation(
                        user, foundation_id='starter0_hsk1', foundation_version=1,
                        event_id=f'device:{index}', source=['pwa_course_v3', 'android_course', 'course_v3'][index % 3],
                    )
                    await session.commit()
                    return result

            results = await asyncio.wait_for(asyncio.gather(*(complete(i) for i in range(12))), timeout=25)
            self.assertTrue(all(result['ok'] and result['foundation']['completed'] for result in results))
            self.assertEqual(sum(not result['duplicate'] for result in results), 1)
            async with sessions() as session:
                rows = (await session.execute(select(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name == 'foundation_completed'))).scalars().all()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].user_id, 1)
                self.assertIsNone(rows[0].telegram_id)
                self.assertFalse((await CourseMiniAppProfileService(session).foundation_status(await session.get(User, 2)))['completed'])
        finally:
            async with engine.begin() as connection:
                await connection.execute(text('DROP SCHEMA IF EXISTS ' + schema + ' CASCADE'))
            await engine.dispose()


@unittest.skipUnless(URL.startswith('postgresql+asyncpg://'), 'PWA_PARITY_TEST_DATABASE_URL not set')
class FeedbackPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def _exercise(self, name):
        from tests.test_pwa_learning_parity import PwaLearningParityTests, fixture
        schema = 'pwa_feedback_' + uuid4().hex
        engine = create_async_engine(URL, connect_args={'server_settings': {'search_path': schema}})
        case = PwaLearningParityTests(name)
        try:
            async with engine.begin() as connection:
                await connection.execute(text('CREATE SCHEMA ' + schema))
            # Reuse the real authenticated ASGI fixture and assertions on PG.
            with patch.object(fixture, 'create_async_engine', return_value=engine):
                await case.asyncSetUp()
            try:
                await getattr(case, name)()
            finally:
                await case.asyncTearDown()
        finally:
            async with engine.begin() as connection:
                await connection.execute(text('DROP SCHEMA IF EXISTS ' + schema + ' CASCADE'))
            await engine.dispose()

    async def test_free_bot_questionnaire_commits_one_reward(self):
        await self._exercise('test_bot_questionnaire_free_answers_keep_canonical_codes_and_single_reward')

    async def test_paid_bot_questionnaire_preserves_the_subscription(self):
        await self._exercise('test_bot_questionnaire_paid_value_and_reason_preserve_subscription')

    async def test_partial_bot_answer_preserves_its_original_choice(self):
        await self._exercise('test_bot_questionnaire_resumes_partial_bot_answer_without_replacing_it')
