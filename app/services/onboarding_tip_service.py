import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import select

from app.bot.utils.i18n import t
from app.db.models.onboarding_tip_event import OnboardingTipEvent
from app.db.models.user import User
from app.db.session import async_session_maker
from app.repositories.course_progress_repo import CourseProgressRepository
from app.repositories.user_repo import UserRepository


logger = logging.getLogger(__name__)

ONBOARDING_TIP_DELAY_SECONDS = 30
COURSE_VOCAB_TIP = "course_vocab_tip"
COURSE_DIALOGUE_TIP = "course_dialogue_tip"
COURSE_GRAMMAR_TIP = "course_grammar_tip"
QA_PHOTO_TIP = "qa_photo_tip"
QA_VOICE_TIP = "qa_voice_tip"

COURSE_TIP_KEYS = {
    COURSE_VOCAB_TIP,
    COURSE_DIALOGUE_TIP,
    COURSE_GRAMMAR_TIP,
}

TIP_TEXT_KEYS = {
    COURSE_VOCAB_TIP: "onboarding_tip_course_vocab",
    COURSE_DIALOGUE_TIP: "onboarding_tip_course_dialogue",
    COURSE_GRAMMAR_TIP: "onboarding_tip_course_grammar",
    QA_PHOTO_TIP: "onboarding_tip_qa_photo",
    QA_VOICE_TIP: "onboarding_tip_qa_voice",
}

_TIP_TASKS: set[asyncio.Task] = set()


def _track_tip_task(task: asyncio.Task) -> None:
    _TIP_TASKS.add(task)

    def _done(completed_task: asyncio.Task) -> None:
        _TIP_TASKS.discard(completed_task)
        if completed_task.cancelled():
            return
        error = completed_task.exception()
        if error:
            logger.warning("Onboarding tip task failed: %s", error, exc_info=True)

    task.add_done_callback(_done)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class OnboardingTipService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)

    async def _get_event(self, user_id: int, tip_key: str) -> OnboardingTipEvent | None:
        result = await self.session.execute(
            select(OnboardingTipEvent).where(
                OnboardingTipEvent.user_id == user_id,
                OnboardingTipEvent.tip_key == tip_key,
            )
        )
        return result.scalar_one_or_none()

    async def queue_once(
        self,
        user,
        tip_key: str,
        *,
        lesson_id: int | None = None,
        step: str | None = None,
        delay_seconds: int = ONBOARDING_TIP_DELAY_SECONDS,
    ) -> bool:
        if tip_key not in TIP_TEXT_KEYS or not user:
            return False

        now = datetime.now(timezone.utc)
        scheduled_at = now + timedelta(seconds=delay_seconds)
        event = await self._get_event(user.id, tip_key)
        if event and event.sent_at:
            return False

        if event:
            event.trigger_lesson_id = lesson_id
            event.trigger_step = step
            event.scheduled_at = scheduled_at
            event.updated_at = now
        else:
            self.session.add(
                OnboardingTipEvent(
                    user_id=user.id,
                    tip_key=tip_key,
                    trigger_lesson_id=lesson_id,
                    trigger_step=step,
                    scheduled_at=scheduled_at,
                    created_at=now,
                    updated_at=now,
                )
            )
        await self.session.flush()
        return True

    async def _is_course_tip_context_valid(self, user, event: OnboardingTipEvent) -> bool:
        if event.tip_key not in COURSE_TIP_KEYS:
            return True
        if getattr(user, "learning_mode", "qa") != "course":
            return False

        progress = await CourseProgressRepository(self.session).get_by_user_id(user.id)
        if not progress:
            return False
        if event.trigger_lesson_id and progress.current_lesson_id != event.trigger_lesson_id:
            return False
        if event.trigger_step and progress.current_step != event.trigger_step:
            return False
        if getattr(progress, "current_step", "") == "completed":
            return False
        return True

    async def send_due_tip(self, bot: Bot, telegram_id: int, tip_key: str) -> bool:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False

        event = await self._get_event(user.id, tip_key)
        if not event or event.sent_at:
            return False

        now = datetime.now(timezone.utc)
        scheduled_at = _as_utc(event.scheduled_at)
        if scheduled_at and scheduled_at > now:
            return False
        if not await self._is_course_tip_context_valid(user, event):
            return False

        text_key = TIP_TEXT_KEYS.get(tip_key)
        if not text_key:
            return False

        lang = getattr(user, "language", None) or "ru"
        await bot.send_message(
            chat_id=telegram_id,
            text=t(text_key, lang),
            parse_mode="HTML",
        )
        event.sent_at = now
        event.updated_at = now
        await self.session.commit()
        return True

    async def send_due_tips(self, bot: Bot, limit: int = 50) -> int:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(OnboardingTipEvent)
            .where(OnboardingTipEvent.sent_at.is_(None))
            .where(OnboardingTipEvent.scheduled_at <= now)
            .order_by(OnboardingTipEvent.scheduled_at.asc())
            .limit(limit)
        )
        events = list(result.scalars().all())
        sent = 0
        for event in events:
            user = await self.session.get(User, event.user_id)
            if not user:
                continue
            if await self.send_due_tip(bot, user.telegram_id, event.tip_key):
                sent += 1
        return sent


async def _deliver_tip_after_delay(
    bot: Bot,
    telegram_id: int,
    tip_key: str,
    delay_seconds: int,
) -> None:
    await asyncio.sleep(delay_seconds)
    async with async_session_maker() as session:
        await OnboardingTipService(session).send_due_tip(bot, telegram_id, tip_key)


def schedule_onboarding_tip(
    bot: Bot,
    telegram_id: int,
    tip_key: str,
    *,
    delay_seconds: int = ONBOARDING_TIP_DELAY_SECONDS,
) -> None:
    _track_tip_task(
        asyncio.create_task(
            _deliver_tip_after_delay(bot, telegram_id, tip_key, delay_seconds)
        )
    )
