from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.bot.utils.i18n import t
from app.db.models.onboarding_tip_event import OnboardingTipEvent
from app.db.models.user import User
from app.repositories.course_progress_repo import CourseProgressRepository
from app.repositories.message_repo import MessageRepository


TIP_DELAY_SECONDS = 0
TIP_KEY_COURSE_VOCAB = "course_vocab"
TIP_KEY_COURSE_DIALOGUE = "course_dialogue"
TIP_KEY_COURSE_GRAMMAR = "course_grammar"
TIP_KEY_NORMAL_PHOTO = "normal_photo"
TIP_KEY_NORMAL_VOICE = "normal_voice"

_COURSE_TIP_KEYS = {
    TIP_KEY_COURSE_VOCAB,
    TIP_KEY_COURSE_DIALOGUE,
    TIP_KEY_COURSE_GRAMMAR,
}


class OnboardingTipService:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _tip_text_key(tip_key: str) -> str:
        return f"onboarding_tip_{tip_key}"

    @staticmethod
    def _parse_context(raw: str | None) -> dict:
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    async def queue_once(
        self,
        *,
        user: User,
        tip_key: str,
        lang: str,
        delay_seconds: int = TIP_DELAY_SECONDS,
        context: dict | None = None,
    ) -> bool:
        if not user:
            return False

        result = await self.session.execute(
            select(OnboardingTipEvent)
            .where(OnboardingTipEvent.user_id == user.id)
            .where(OnboardingTipEvent.tip_key == tip_key)
        )
        event = result.scalar_one_or_none()
        if event and event.status == "sent":
            return False

        now = self._now()
        due_at = now + timedelta(seconds=delay_seconds)
        payload = json.dumps(context or {}, ensure_ascii=False) if context else None
        normalized_lang = lang if lang in {"uz", "ru", "tj"} else "ru"

        if event:
            event.lang = normalized_lang
            event.status = "queued"
            event.context_json = payload
            event.due_at = due_at
            event.updated_at = now
        else:
            event = OnboardingTipEvent(
                user_id=user.id,
                tip_key=tip_key,
                lang=normalized_lang,
                status="queued",
                context_json=payload,
                due_at=due_at,
                created_at=now,
                updated_at=now,
            )
            self.session.add(event)

        await self.session.flush()
        return True

    async def queue_course_tip(
        self,
        *,
        user: User,
        lesson,
        step: str,
        tip_key: str,
        lang: str,
    ) -> bool:
        lesson_id = getattr(lesson, "id", None)
        if not lesson_id:
            return False
        return await self.queue_once(
            user=user,
            tip_key=tip_key,
            lang=lang,
            context={
                "type": "course",
                "lesson_id": int(lesson_id),
                "step": step,
            },
        )

    async def queue_voice_tip_if_near_limit(self, *, user: User, lang: str) -> bool:
        if not user or getattr(user, "payment_status", "none") == "approved":
            return False
        if getattr(user, "trial_voice_used_at", None) is not None:
            return False

        near_text_limit = False
        if getattr(user, "status", "") == "trial":
            question_limit = int(getattr(user, "question_limit", 0) or 0)
            questions_used = int(getattr(user, "questions_used", 0) or 0)
            near_text_limit = question_limit > 0 and question_limit - questions_used <= 1

        image_count = await MessageRepository(self.session).count_user_messages_today(
            user_id=user.id,
            content_type="image",
        )
        near_image_limit = image_count >= 1

        if not near_text_limit and not near_image_limit:
            return False

        return await self.queue_once(
            user=user,
            tip_key=TIP_KEY_NORMAL_VOICE,
            lang=lang,
            context={"type": "normal"},
        )

    async def _course_context_is_current(self, user: User, context: dict) -> bool:
        if getattr(user, "learning_mode", "qa") != "course":
            return False

        lesson_id = context.get("lesson_id")
        step = str(context.get("step") or "").strip()
        if not lesson_id or not step:
            return False

        progress = await CourseProgressRepository(self.session).get_by_user_id(user.id)
        if not progress:
            return False

        return (
            int(getattr(progress, "current_lesson_id", 0) or 0) == int(lesson_id)
            and (getattr(progress, "current_step", "") or "") == step
            and (getattr(progress, "waiting_for", "none") or "none") == "none"
        )

    async def _should_send(self, user: User, event: OnboardingTipEvent) -> bool:
        if not user or getattr(user, "status", "") == "blocked":
            return False
        if event.tip_key in _COURSE_TIP_KEYS:
            return await self._course_context_is_current(user, self._parse_context(event.context_json))
        return True

    async def send_due_tips(self, bot, limit: int = 50) -> int:
        now = self._now()
        result = await self.session.execute(
            select(OnboardingTipEvent)
            .where(OnboardingTipEvent.status == "queued")
            .where(OnboardingTipEvent.due_at <= now)
            .order_by(OnboardingTipEvent.due_at.asc())
            .limit(limit)
        )
        events = list(result.scalars().all())
        sent_count = 0

        for event in events:
            user = await self.session.get(User, event.user_id)
            event.updated_at = now
            if not await self._should_send(user, event):
                event.status = "skipped"
                continue

            lang = event.lang or getattr(user, "language", None) or "ru"
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=t(self._tip_text_key(event.tip_key), lang),
                    parse_mode="HTML",
                )
            except Exception:
                event.status = "skipped"
                continue

            event.status = "sent"
            event.sent_at = now
            sent_count += 1

        if events:
            await self.session.commit()

        return sent_count
