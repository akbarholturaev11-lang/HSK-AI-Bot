"""Canonical ordinary learner feedback shared by PWA and native Android.

Transport authentication stays in adapters; locks, eligibility, codes, cooldown
and rewards retain the bot contract. Historical helper names are kept for PWA compatibility.
"""
from datetime import datetime, timezone
from sqlalchemy import select
from app.bot.keyboards.feedback import (
    ACCEPTED_LIKED_OPTIONS, ACCEPTED_PAID_SUB_POSITIVE, DISLIKED_OPTIONS, LIKE_SUB_OPTIONS,
    PAID_OPTIONS, PAID_SUB_NEGATIVE, feedback_like_label, feedback_dislike_label,
    feedback_sub_label, feedback_paid_label,
)
from app.bot.handlers.feedback import DISLIKE_DETAIL_REQUIRED_CODES
from app.db.models.user import User
from app.db.models.bot_feedback import BotFeedback
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.repositories.bot_feedback_repo import BotFeedbackRepository
from app.services.bot_feedback_service import BotFeedbackService
from app.services.user_access_state_service import UserAccessStateService

class ActivityFeedbackError(Exception):
    def __init__(self, code, *, status_code):
        self.code, self.status_code = code, status_code
        super().__init__(code)

def _pwa_feedback_choices(language: str, *, paid: bool, current: str | None = None) -> dict:
    """Expose Telegram's existing localized choice contract, not a second UI catalog.

    Read-only metadata; no callback payload, Telegram auth or reward authority.
    The server still validates all submitted codes against the same dictionaries.
    """
    from app.bot.keyboards.feedback import (
        APP_LIKED_OPTIONS, APP_PAID_SUB_POSITIVE, ACCEPTED_LIKED_OPTIONS,
        DISLIKED_OPTIONS, LIKE_SUB_OPTIONS, PAID_OPTIONS, PAID_SUB_NEGATIVE,
        feedback_like_label, feedback_dislike_label,
        feedback_sub_label, feedback_paid_label,
    )
    from app.bot.handlers.feedback import DISLIKE_DETAIL_REQUIRED_CODES

    lang = language if language in {"uz", "ru", "tj"} else "ru"

    def choices(codes, label):
        return [{"code":code, "label":label(code, lang)} for code in codes]

    if paid:
        return {
            "paid": choices(PAID_OPTIONS, feedback_paid_label),
            "paid_sub_positive": choices(APP_PAID_SUB_POSITIVE, feedback_sub_label),
            "paid_sub_negative": choices(PAID_SUB_NEGATIVE, feedback_sub_label),
        }
    liked = list(APP_LIKED_OPTIONS)
    # A first answer already recorded in the bot stays selectable in the app.
    if current in ACCEPTED_LIKED_OPTIONS and current not in liked:
        liked.insert(-1, current)
    return {
        "liked": choices(liked, feedback_like_label),
        "liked_sub": {
            code: choices(codes, feedback_sub_label)
            for code, codes in LIKE_SUB_OPTIONS.items()
        },
        "disliked": choices(DISLIKED_OPTIONS, feedback_dislike_label),
        "disliked_detail_required": sorted(DISLIKE_DETAIL_REQUIRED_CODES | {"other"}),
    }


async def _pwa_feedback_context_exists(db, user, context) -> bool:
    """Only current, actually used learning contexts can request compact feedback."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import and_, or_, select
    from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
    from app.repositories.course_progress_repo import CourseProgressRepository
    from app.services.course_levels import content_level
    from app.services.course_miniapp_profile_service import CourseMiniAppProfileService

    if content_level(user.level) != context.level:
        return False
    if context.kind == "lesson":
        progress = await CourseProgressRepository(db).get_by_user_id(user.id)
        return bool(context.lesson_id and progress and progress.level == context.level
                    and progress.completed_lessons_count >= context.lesson_id)
    if context.lesson_id is not None:
        return False
    if context.kind == "foundation":
        return bool((await CourseMiniAppProfileService(db).foundation_status(user))["completed"])
    names = (("voice_started", "voice_completed") if context.kind == "voice" else
             ("training_started", "training_completed", "test_started", "test_completed",
              "practice_attempt_scored", "section_attempt_scored", "mistake_review_started", "mistake_review_completed"))
    activity = Event.event_name.in_(names)
    if context.kind == "practice":
        activity = or_(activity, and_(
            Event.event_name == "card_seen", Event.source == "pwa_course_v3",
            Event.payload_json.contains('"card_type":"practice_entry"'),
        ))
    recorded = (await db.execute(select(Event.id).where(
        Event.user_id == user.id, activity,
        Event.created_at >= datetime.now(timezone.utc) - timedelta(minutes=30),
    ).limit(1))).scalar_one_or_none() is not None
    if recorded or context.kind != "voice":
        return recorded
    # Native Voice persists real sessions instead of browser telemetry. A used
    # owned turn is evidence; opening a tab or client-supplied counters are not.
    from app.db.models.voice_practice_session import VoicePracticeSession
    from app.services.account_identity import owner_clause
    levels = (context.level, "beginner") if context.level == "hsk1" else (context.level,)
    return (await db.execute(select(VoicePracticeSession.id).where(
        owner_clause(VoicePracticeSession, user), VoicePracticeSession.level.in_(levels),
        VoicePracticeSession.turn_count > 0,
        VoicePracticeSession.started_at >= datetime.now(timezone.utc) - timedelta(minutes=30),
    ).limit(1))).scalar_one_or_none() is not None



def _pwa_feedback_prompt_eligible(user, service, now) -> bool:
    """Share the original bot's join/activity gates across PWA read and prepare.

    PWA deliberately does not require an active Telegram transport: a verified
    Google/Apple-only learner has the same canonical eligibility.
    """
    from app.services.bot_feedback_service import (
        FEEDBACK_ACTIVE_WINDOW, FEEDBACK_JOIN_DELAY,
    )

    joined = service._aware(user.created_at)
    active = service._aware(user.last_active_at)
    return bool(
        user.status != "blocked"
        and joined is not None and joined <= now - FEEDBACK_JOIN_DELAY
        and active is not None and active >= now - FEEDBACK_ACTIVE_WINDOW
    )


# Server-only delivery reservation, not client telemetry or a counted impression.
APP_TELEGRAM_FEEDBACK_RESERVATION = "app_telegram_feedback_reserved"


class ActivityFeedbackService:
    def __init__(self, db):
        self.db = db

    async def _reserve_telegram_continuation(self, feedback, now):
        """Allow one app to continue an already-delivered pending invite."""
        if (feedback.prompt_message_id or 0) <= 0:
            return False
        key = f"feedback:{feedback.id}"
        # The caller holds the canonical user lock; the existing event unique
        # key also protects the reservation across PWA and Android devices.
        reserved = await self.db.scalar(select(CourseMiniAppEvent.id).where(
            CourseMiniAppEvent.user_id == feedback.user_id,
            CourseMiniAppEvent.event_name == APP_TELEGRAM_FEEDBACK_RESERVATION,
            CourseMiniAppEvent.dedupe_key == key,
        ).limit(1))
        if reserved is not None:
            return False
        self.db.add(CourseMiniAppEvent(
            user_id=feedback.user_id,
            event_name=APP_TELEGRAM_FEEDBACK_RESERVATION,
            source="activity_feedback_server",
            dedupe_key=key,
            created_at=now,
        ))
        # Same attempt; the next real reminder still waits 24 hours.
        feedback.prompted_at = now
        feedback.updated_at = now
        return True

    async def prepare(self, user_id, data):
        db = self.db
        # Serialize prompt creation per canonical learner, including
        # concurrent browser tabs or simultaneous provider sessions.
        learner = (await db.execute(
            select(User).where(User.id == user_id).with_for_update()
            .execution_options(populate_existing=True)
        )).scalar_one()
        if data.context and not await _pwa_feedback_context_exists(db, learner, data.context):
            raise ActivityFeedbackError("feedback_context_unavailable", status_code=409)
        now = datetime.now(timezone.utc)
        service = BotFeedbackService(db)
        feedback = None
        if _pwa_feedback_prompt_eligible(learner, service, now):
            feedback = await service._get_or_create_due_feedback(learner, now)
        if data.context and feedback:
            # Legacy compact clients cannot replace a partial bot answer.
            # The bot presentation resumes the same canonical choices.
            # A paid/free change can make the old answer incompatible.
            mode_changed = feedback.liked_code and (
                feedback.liked_code.startswith("paid_") != UserAccessStateService.is_paid(learner)
            )
            if (data.presentation == "compact" and (feedback.liked_code or feedback.disliked_code)) or mode_changed:
                feedback = None
            else:
                continued = (
                    data.presentation == "bot"
                    and await self._reserve_telegram_continuation(feedback, now)
                )
                if not continued:
                    if service._is_prompt_due(feedback, now):
                        await service.feedback_repo.mark_prompt_sent(feedback, feedback.prompt_message_id)
                    else:
                        feedback = None
        elif feedback and not service._is_prompt_due(feedback, now):
            feedback = None
        await db.commit()
        payload = ({
            "feedback_id": feedback.id,
            "compact": data.context.model_dump() if data.context and data.presentation == "compact" else None,
            "presentation": data.presentation,
            "paid": UserAccessStateService.is_paid(learner),
            "liked_code": feedback.liked_code,
            "disliked_code": feedback.disliked_code,
            "choices": _pwa_feedback_choices(
                learner.language,
                paid=UserAccessStateService.is_paid(learner),
                current=feedback.liked_code,
            ),
        } if feedback else None)
        return payload

    async def submit(self, user_id, data):
        db = self.db
        if not 1 <= data.feedback_id <= 2147483647:
            raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
        # A verified account row serializes browser tabs and repeated
        # submissions; existing bot records use the same users.id.
        learner = (await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )).scalar_one()
        feedback = (await db.execute(
            select(BotFeedback).where(
                BotFeedback.id == data.feedback_id,
                BotFeedback.user_id == learner.id,
            ).with_for_update()
        )).scalar_one_or_none()
        if feedback is None:
            raise ActivityFeedbackError("feedback_not_available", status_code=404)
        if feedback.status != "pending":
            raise ActivityFeedbackError("feedback_already_completed", status_code=409)
        repo = BotFeedbackRepository(db)
        lang = learner.language if learner.language in {"uz", "ru", "tj"} else "ru"
        if data.context:
            if (not data.answer or feedback.liked_code or feedback.disliked_code
                    or any((data.liked_code, data.liked_sub_code, data.liked_other_text,
                            data.disliked_code, data.disliked_detail_text,
                            data.paid_code, data.paid_sub_code, data.paid_other_text))
                    or not await _pwa_feedback_context_exists(db, learner, data.context)):
                raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
            context_text = f"{data.context.kind} · {data.context.level}"
            if data.context.lesson_id:
                context_text += f" · {data.context.lesson_id}"
            await repo.save_liked(feedback, "context_" + data.context.kind, context_text)
            await repo.save_disliked(
                feedback, "context_" + data.answer,
                context_text + " · " + data.answer + ("\n" + data.comment.strip() if data.comment else ""),
            )
        elif data.answer is not None or data.comment is not None:
            raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
        elif UserAccessStateService.is_paid(learner):
            if (
                data.paid_code not in PAID_OPTIONS
                or any((
                    data.liked_code, data.liked_sub_code, data.liked_other_text,
                    data.disliked_code, data.disliked_detail_text,
                ))
            ):
                raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
            subs = (ACCEPTED_PAID_SUB_POSITIVE if data.paid_code in ("worth", "useful")
                    else PAID_SUB_NEGATIVE)
            if data.paid_sub_code not in subs:
                raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
            detail = (data.paid_other_text or "").strip()
            if (data.paid_sub_code == "other" and not detail) or len(detail) > 1000:
                raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
            if feedback.liked_code and feedback.liked_code != "paid_" + data.paid_code:
                raise ActivityFeedbackError("feedback_state_changed", status_code=409)
            await repo.save_liked(
                feedback, "paid_" + data.paid_code,
                feedback_paid_label(data.paid_code, lang),
            )
            await repo.save_disliked(
                feedback, "paid_" + data.paid_sub_code,
                detail if data.paid_sub_code == "other"
                else feedback_sub_label(data.paid_sub_code, lang),
            )
        else:
            if (
                data.liked_code not in ACCEPTED_LIKED_OPTIONS
                or data.disliked_code not in DISLIKED_OPTIONS
                or data.paid_code is not None or data.paid_sub_code is not None
                or data.paid_other_text is not None
            ):
                raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
            like_detail = (data.liked_other_text or "").strip()
            dislike_detail = (data.disliked_detail_text or "").strip()
            if len(like_detail) > 1000 or len(dislike_detail) > 1000:
                raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
            if data.liked_code in LIKE_SUB_OPTIONS:
                if data.liked_sub_code not in LIKE_SUB_OPTIONS[data.liked_code]:
                    raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
                if data.liked_sub_code == "other" and not like_detail:
                    raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
            elif data.liked_sub_code is not None:
                raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
            if data.liked_code == "other" and not like_detail:
                raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
            if data.disliked_code in DISLIKE_DETAIL_REQUIRED_CODES | {"other"}:
                if not dislike_detail:
                    raise ActivityFeedbackError("pwa_request_invalid", status_code=422)
            if feedback.liked_code and feedback.liked_code != data.liked_code:
                raise ActivityFeedbackError("feedback_state_changed", status_code=409)
            liked_text = (
                like_detail if data.liked_code == "other"
                else feedback_like_label(data.liked_code, lang)
            )
            if data.liked_sub_code:
                liked_text = (
                    liked_text + " → " + (
                        like_detail if data.liked_sub_code == "other"
                        else feedback_sub_label(data.liked_sub_code, lang)
                    )
                )[:1000]
            await repo.save_liked(feedback, data.liked_code, liked_text)
            await repo.save_disliked(
                feedback, data.disliked_code,
                dislike_detail if data.disliked_code in
                DISLIKE_DETAIL_REQUIRED_CODES | {"other"}
                else feedback_dislike_label(data.disliked_code, lang),
            )
        await BotFeedbackService(db).finish_feedback(feedback, learner)
        await db.commit()
        return learner, feedback
