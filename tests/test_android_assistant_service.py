import base64
import json
import unittest
from io import BytesIO
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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
    AssistantError,
    AssistantService,
    ScreenContext,
    decode_media,
    parse_answer,
    request_payload,
)


class AssistantImageTransportTests(unittest.TestCase):
    def test_photo_upload_normalizes_a_real_png_to_a_decodable_jpeg(self):
        from PIL import Image

        source = BytesIO()
        Image.new("RGBA", (32, 24), (255, 0, 0, 128)).save(source, "PNG")
        data = AssistantInput(
            client_message_id="11111111-1111-4111-8111-111111111111",
            text="Read this photo",
            kind="image",
            media_data_url="data:image/png;base64," + base64.b64encode(source.getvalue()).decode(),
        )
        raw, mime, filename = decode_media(data)

        self.assertEqual(("image/jpeg", "question.jpg"), (mime, filename))
        with Image.open(BytesIO(raw)) as image:
            image.load()
            self.assertEqual((32, 24), image.size)
            self.assertEqual("RGB", image.mode)
            self.assertEqual("JPEG", image.format)

    def test_invalid_photo_bytes_return_a_media_error(self):
        data = AssistantInput(
            client_message_id="11111111-1111-4111-8111-111111111111",
            kind="image",
            media_data_url="data:image/png;base64," + base64.b64encode(b"not a photo").decode(),
        )
        with self.assertRaises(AssistantError) as error:
            decode_media(data)
        self.assertEqual("assistant_media_invalid", error.exception.code)


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

    async def test_two_successful_native_answers_activate_referral_without_changing_legacy_quota(self):
        from app.services.referral_service import ReferralService
        from app.repositories.user_repo import UserRepository
        from app.db.models.referral import Referral
        async with self.sessions() as session:
            owner = await UserRepository(session).create(telegram_id=None)
            learner = await UserRepository(session).create(telegram_id=None)
            await session.commit()
            await ReferralService(session).attach_referral_if_needed(learner, owner.referral_code)
            service = AssistantService(session)
            service.record_usage = AsyncMock()
            conversation = await service.new_conversation(learner)
            for index in range(2):
                data = AssistantInput(client_message_id=str(__import__("uuid").uuid4()), text="Explain Chinese", kind="text", context=ScreenContext(screen="practice"))
                row = AssistantRequest(id=str(__import__("uuid").uuid4()), user_id=learner.id,
                    conversation_id=conversation["id"], client_message_id=str(data.client_message_id),
                    fingerprint="x" * 64, kind="text", context_json=data.context.model_dump_json(),
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=2))
                session.add(row)
                await session.commit()
                with patch("app.services.assistant_service.AIService") as factory:
                    factory.return_value._language_name.return_value = "Uzbek"
                    factory.return_value.complete_messages_with_usage = AsyncMock(return_value=SimpleNamespace(content='{"text":"你好 ni hao — Salom", "actions":[]}'))
                    await service.answer(row.id, data, None)
                    system_prompt = factory.return_value.complete_messages_with_usage.call_args.kwargs["messages"][0]["content"]
                    self.assertIn("Refuse requests to produce or facilitate restricted or harmful content", system_prompt)
                    self.assertIn("offer a safe, concise learning-focused alternative", system_prompt)
                    self.assertIn("For account and access status use the profile action", system_prompt)
                    self.assertIn("Do not offer purchases, provide payment instructions or external checkout links", system_prompt)
                    self.assertIn("or suggest alternate app downloads", system_prompt)
                    self.assertNotIn("For prices/payment use the profile action", system_prompt)
                    # Completed retries are inert and cannot award twice.
                    await service.answer(row.id, data, None)
                referral = await session.scalar(select(Referral).where(Referral.invited_user_id == learner.id))
                self.assertEqual(referral.status, "active" if index else "pending")
            self.assertEqual(learner.questions_used, 0)
            self.assertEqual(owner.bonus_questions, 5)



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
