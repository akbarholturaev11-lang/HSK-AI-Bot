import logging

from app.bot.utils.course_miniapp import course_miniapp_lesson_id
from app.bot.utils.i18n import t
from app.services.access_service import AccessService
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.conversion_funnel_service import ConversionFunnelService
from app.services.course_miniapp_result_service import CourseMiniAppResultService
from app.services.course_trial_service import CourseTrialService
from app.services.course_tutor_service import CourseTutorService


logger = logging.getLogger(__name__)


class CourseTrialValueService:
    def __init__(self, session):
        self.session = session

    async def generate_quiz_explanation(self, *, telegram_id: int, result: dict) -> str | None:
        user = result.get("user")
        lesson = result.get("lesson")
        if not user or not lesson:
            return None
        if result.get("block_no"):
            return None
        if course_miniapp_lesson_id(lesson) != 1:
            return None
        if CourseTrialService(self.session).is_paid_user(user):
            return None

        try:
            already_sent = await ConversionFunnelService(self.session).has_event(
                telegram_id=telegram_id,
                event_name="ai_explanation_seen",
                source="course_trial_auto_explanation",
                lesson_id=lesson.id,
            )
            if already_sent:
                return None
        except Exception:
            logger.exception("Failed to check trial auto explanation event for user %s", telegram_id)
            return None

        lang = user.language if getattr(user, "language", None) else "ru"
        miniapp_context = await CourseMiniAppResultService(self.session).build_ai_context(
            user_id=user.id,
            lesson_id=lesson.id,
        )
        user_message = t("course_trial_ai_explanation_prompt", lang)
        contextual_message = user_message
        if miniapp_context:
            contextual_message = f"{miniapp_context}\n\nFOYDALANUVCHI XABARI:\n{user_message}"

        tutor = CourseTutorService()
        try:
            reply = await tutor.generate_step_response(
                user_language=lang,
                user_level=user.level if getattr(user, "level", None) else "hsk1",
                lesson=lesson,
                step="review",
                user_message=contextual_message,
            )
            await AIUsageBudgetService(self.session).record_usage(
                telegram_id=telegram_id,
                result=tutor.last_ai_result,
                source="course_trial_auto_explanation",
            )
            await AccessService(self.session).downgrade_non_paid_active_if_budget_depleted(telegram_id)
            await self.session.commit()
            return reply
        except Exception:
            logger.exception("Trial auto explanation failed for user %s", telegram_id)
            return None
