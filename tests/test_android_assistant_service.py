import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.assistant import AssistantAssessment, AssistantRequest
from app.db.models.message import Message
from app.db.models.user import User
from app.services.assistant_service import (
    AssistantInput,
    AssistantService,
    ScreenContext,
    parse_answer,
    request_payload,
)


def _user(user_id=1, telegram_id=4200) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name="Android assistant tester",
        language="uz",
        level="hsk2",
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
        created_at=now,
        last_active_at=now,
    )


class AndroidAssistantServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_active_assessment_gets_procedural_help_without_ai_provider(self):
        async with self.sessions() as session:
            user = _user()
            session.add(user)
            session.add(
                AssistantAssessment(
                    id="assessment-1",
                    user_id=user.id,
                    session_id="exam-1",
                    kind="exam",
                    status="active",
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
                )
            )
            await session.commit()

            service = AssistantService(session)
            conversation = await service.new_conversation(user)
            data = AssistantInput(
                client_message_id="11111111-1111-4111-8111-111111111111",
                text="mana buni ayt",
                kind="text",
                context=ScreenContext(
                    screen="exam",
                    title="HSK 2 imtihon",
                    details="Active exam question; solution must stay hidden.",
                    material_ref="exam-question-1",
                    attempt_id="exam-1",
                    answer_state="restricted",
                ),
            )
            row, created = await service.reserve(user, conversation["id"], data)

            with patch("app.services.assistant_service.AIService") as ai:
                await service.answer(row.id, data, None)

            ai.assert_not_called()
            request = await session.get(AssistantRequest, row.id)
            messages = (await session.scalars(select(Message).order_by(Message.id))).all()

        self.assertTrue(created)
        self.assertEqual("completed", request.status)
        payload = json.loads(request.response_json)
        self.assertEqual([], payload["actions"])
        self.assertIn("imtihon", payload["text"].lower())
        self.assertEqual(["assistant_help", "text"], [msg.content_type for msg in messages])


class AssistantAnswerParsingTests(unittest.TestCase):
    """A cut-off or fenced model reply must never reach the learner as raw JSON."""

    def test_clean_json_object(self):
        text, actions = parse_answer('{"text": "Salom", "actions": ["profile"]}')
        self.assertEqual("Salom", text)
        self.assertEqual(["profile"], actions)

    def test_code_fenced_json(self):
        text, actions = parse_answer('```json\n{"text": "Misol: 你好", "actions": []}\n```')
        self.assertEqual("Misol: 你好", text)
        self.assertEqual([], actions)

    def test_truncated_json_salvages_text(self):
        raw = '{\n  "text": "\\"Mashq\\" ekrani HSK2 uchun mashq qilishga yordam beradi. Bu yer'
        text, actions = parse_answer(raw)
        self.assertEqual('"Mashq" ekrani HSK2 uchun mashq qilishga yordam beradi. Bu yer', text)
        self.assertEqual([], actions)
        self.assertNotIn('"text"', text)

    def test_plain_text_passes_through(self):
        text, _ = parse_answer("Oddiy javob matni")
        self.assertEqual("Oddiy javob matni", text)

    def test_empty_stays_empty(self):
        self.assertEqual(("", []), parse_answer(""))
        self.assertEqual(("", []), parse_answer(None))

    def test_stored_history_wrapper_is_repaired(self):
        row = SimpleNamespace(
            client_message_id="c1", conversation_id="v1", status="completed",
            phase="done", error="", input_text="Soddaroq tushuntir", kind="text",
            context_json='{"screen": "practice"}',
            response_json=json.dumps({"text": '{\n  "text": "Mashq ekrani yordam beradi. Bu yer', "actions": []}),
        )
        payload = request_payload(row)
        self.assertEqual("Mashq ekrani yordam beradi. Bu yer", payload["text"])

    def test_stored_history_plain_text_untouched(self):
        row = SimpleNamespace(
            client_message_id="c2", conversation_id="v1", status="completed",
            phase="done", error="", input_text="salom", kind="text",
            context_json="{}", response_json=json.dumps({"text": "Oddiy javob", "actions": []}),
        )
        self.assertEqual("Oddiy javob", request_payload(row)["text"])
