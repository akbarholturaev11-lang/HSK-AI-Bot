import asyncio
import json
import logging
import uuid
from datetime import datetime, time, timezone

from openai import AsyncOpenAI
from sqlalchemy import func, select

from app.config import settings
from app.db.models.voice_practice_session import VoicePracticeSession
from app.repositories.user_repo import UserRepository
from app.services.ai_service import AIService
from app.services.study_miniapp_service import StudyMiniAppService
from app.services.course_mistake_service import CourseMistakeService


logger = logging.getLogger(__name__)

FREE_TOTAL_SESSIONS = 1
PAID_DAILY_SESSIONS = 5
MAX_TURNS_PER_SESSION = 20
MAX_AUDIO_BYTES = 5 * 1024 * 1024

ROLE_PROMPTS = {
    "friend": "You are a warm Chinese friend. Be curious, informal, and encouraging.",
    "roommate": "You are the learner's Chinese roommate. Discuss realistic home and daily-life situations.",
    "seller": "You are a lively Chinese shop seller. Practice prices, quantities, choices, and bargaining.",
    "classmate": "You are a Chinese classmate. Discuss classes, plans, campus life, and homework naturally.",
    "social": "You are an engaging Chinese conversation partner. Adapt the topic to the learner's reply.",
}

LANGUAGE_NAMES = {"ru": "Russian", "tj": "Tajik", "uz": "Uzbek"}


class VoicePracticeError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class VoicePracticeService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)

    @staticmethod
    def _day_start() -> datetime:
        now = datetime.now(timezone.utc)
        return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

    @staticmethod
    def _is_paid(user) -> bool:
        return StudyMiniAppService.is_paid_user(user)

    async def _session_count(self, telegram_id: int, *, today_only: bool) -> int:
        query = select(func.count(VoicePracticeSession.id)).where(
            VoicePracticeSession.user_telegram_id == telegram_id
        )
        if today_only:
            query = query.where(VoicePracticeSession.started_at >= self._day_start())
        result = await self.session.execute(query)
        return int(result.scalar_one() or 0)

    async def user_status(self, telegram_id: int) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise VoicePracticeError("USER_NOT_FOUND", "Start the bot before opening Voice Practice.", 404)

        paid = self._is_paid(user)
        used = await self._session_count(telegram_id, today_only=paid)
        limit = PAID_DAILY_SESSIONS if paid else FREE_TOTAL_SESSIONS
        return {
            "is_paid": paid,
            "plan": "premium" if paid else "free",
            "remaining_voice_limit": max(0, limit - used),
            "level": getattr(user, "level", None) or "hsk1",
            "language": getattr(user, "language", None) or "ru",
        }

    async def start_session(
        self,
        telegram_id: int,
        *,
        role: str,
        level: str,
        language: str,
        voice: str,
    ) -> dict:
        if role not in ROLE_PROMPTS:
            raise VoicePracticeError("INVALID_ROLE", "Unknown conversation role.")
        if level not in {"beginner", "hsk1_2", "hsk3_4", "hsk1", "hsk2", "hsk3", "hsk4"}:
            raise VoicePracticeError("INVALID_LEVEL", "Unknown HSK level.")
        if language not in LANGUAGE_NAMES:
            language = "ru"
        if voice not in {"female", "male"}:
            voice = "female"

        status = await self.user_status(telegram_id)
        if status["remaining_voice_limit"] <= 0:
            raise VoicePracticeError("LIMIT_EXCEEDED", "Voice Practice limit reached.", 403)

        item = VoicePracticeSession(
            id=str(uuid.uuid4()),
            user_telegram_id=telegram_id,
            role=role,
            level=level,
            language=language,
            voice=voice,
            history=[],
            corrections=[],
        )
        self.session.add(item)
        await self.session.commit()

        next_status = await self.user_status(telegram_id)
        return {
            "session_id": item.id,
            "user_status": {"is_paid": status["is_paid"], "plan": status["plan"]},
            "remaining_limit": next_status["remaining_voice_limit"],
        }

    async def _get_active_session(self, telegram_id: int, session_id: str) -> VoicePracticeSession:
        result = await self.session.execute(
            select(VoicePracticeSession)
            .where(VoicePracticeSession.id == session_id)
            .where(VoicePracticeSession.user_telegram_id == telegram_id)
            .limit(1)
        )
        item = result.scalar_one_or_none()
        if not item or item.status != "active":
            raise VoicePracticeError("SESSION_NOT_FOUND", "Voice session not found.", 404)
        return item

    @staticmethod
    def _clean_reply(raw: str) -> dict:
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            raise VoicePracticeError("AI_RESPONSE_INVALID", "AI returned an invalid response.", 502) from error

        chinese = str(data.get("chinese_reply") or "").strip()
        if not chinese:
            raise VoicePracticeError("AI_RESPONSE_INVALID", "AI returned an empty response.", 502)
        return {
            "chinese_reply": chinese[:500],
            "pinyin": str(data.get("pinyin") or "").strip()[:700],
            "translation": str(data.get("translation") or "").strip()[:700],
            "correction": str(data.get("correction") or "").strip()[:700] or None,
        }

    async def _generate_reply(self, item: VoicePracticeSession, transcription: str) -> dict:
        target_language = LANGUAGE_NAMES.get(item.language, "Russian")
        recent = list(item.history or [])[-8:]
        messages = [
            {
                "role": "system",
                "content": (
                    f"{ROLE_PROMPTS[item.role]} The learner level is {item.level}. "
                    "Continue a realistic spoken Chinese roleplay. Use short natural replies, usually one or two sentences. "
                    "Ask a useful follow-up question when natural. Do not switch out of character. "
                    f"Translate into {target_language}. Correct only meaningful learner errors, gently. "
                    "Return valid JSON only with keys chinese_reply, pinyin, translation, correction. "
                    "correction must be null when the learner's phrase is acceptable."
                ),
            }
        ]
        for entry in recent:
            if not isinstance(entry, dict):
                continue
            user_text = str(entry.get("user") or "").strip()
            assistant_text = str(entry.get("assistant") or "").strip()
            if user_text:
                messages.append({"role": "user", "content": user_text[:700]})
            if assistant_text:
                messages.append({"role": "assistant", "content": assistant_text[:700]})
        messages.append({"role": "user", "content": transcription[:1000]})

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"},
            max_completion_tokens=350,
            temperature=0.7,
        )
        return self._clean_reply(response.choices[0].message.content or "")

    async def process_message(
        self,
        telegram_id: int,
        *,
        session_id: str,
        audio_bytes: bytes,
        filename: str,
    ) -> dict:
        if not settings.OPENAI_API_KEY:
            raise VoicePracticeError("AI_UNAVAILABLE", "Voice AI is not configured.", 503)
        if not audio_bytes:
            raise VoicePracticeError("EMPTY_AUDIO", "Audio is empty.")
        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise VoicePracticeError("AUDIO_TOO_LARGE", "Audio is too large.", 413)

        item = await self._get_active_session(telegram_id, session_id)
        if item.turn_count >= MAX_TURNS_PER_SESSION:
            raise VoicePracticeError("TURN_LIMIT_EXCEEDED", "This voice session reached its turn limit.", 403)

        try:
            ai = AIService()
            transcription_result = await asyncio.wait_for(
                ai.transcribe_voice_with_usage(
                    audio_bytes=audio_bytes,
                    filename=filename,
                    user_language=item.language,
                    user_level=item.level,
                ),
                timeout=35,
            )
            transcription = transcription_result.content.strip()
            if not transcription:
                raise VoicePracticeError("TRANSCRIPTION_EMPTY", "No speech was detected.")
            reply = await asyncio.wait_for(self._generate_reply(item, transcription), timeout=30)
        except VoicePracticeError:
            raise
        except asyncio.TimeoutError as error:
            raise VoicePracticeError("AI_TIMEOUT", "Voice AI timed out. Try again.", 504) from error
        except Exception as error:
            logger.exception("Voice Practice AI failed for user %s", telegram_id)
            raise VoicePracticeError("AI_FAILED", "Voice AI failed. Try again.", 502) from error

        history = list(item.history or [])
        history.append({"user": transcription, "assistant": reply["chinese_reply"]})
        item.history = history[-20:]
        if reply["correction"]:
            item.corrections = [*list(item.corrections or []), reply["correction"]][-20:]
        item.turn_count += 1
        await self.session.commit()

        status = await self.user_status(telegram_id)
        return {
            "transcription": transcription,
            **reply,
            "audio_reply_url": None,
            "audio_reply_base64": None,
            "remaining_limit": status["remaining_voice_limit"],
        }

    async def end_session(self, telegram_id: int, session_id: str) -> dict:
        item = await self._get_active_session(telegram_id, session_id)
        ended_at = datetime.now(timezone.utc)
        started_at = item.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        item.status = "completed"
        item.ended_at = ended_at
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user:
            await CourseMistakeService(self.session).record_items(
                user,
                [
                    {
                        "question": str(correction),
                        "correction": str(correction),
                        "category": "pronunciation",
                    }
                    for correction in list(item.corrections or [])
                    if str(correction or "").strip()
                ],
                source="voice",
                level=item.level,
            )
        await self.session.commit()
        return {
            "ok": True,
            "duration_seconds": max(0, int((ended_at - started_at).total_seconds())),
            "message_count": item.turn_count,
            "corrections": list(item.corrections or []),
        }
