import logging

from app.bot.keyboards.subscription import subscription_miniapp_keyboard
from app.bot.utils.course_miniapp import course_miniapp_lesson_id
from app.bot.utils.i18n import t
from app.services.conversion_funnel_service import ConversionFunnelService
from app.services.course_trial_value_service import CourseTrialValueService


logger = logging.getLogger(__name__)


async def send_trial_quiz_value_teaser(
    *,
    session,
    telegram_id: int,
    result: dict,
    respond,
) -> bool:
    user = result.get("user")
    lesson = result.get("lesson")
    lang = user.language if user and getattr(user, "language", None) else "ru"

    explanation = await CourseTrialValueService(session).generate_quiz_explanation(
        telegram_id=telegram_id,
        result=result,
    )
    if not explanation:
        return False

    try:
        await respond(
            f"{t('course_trial_ai_explanation_title', lang)}\n\n{explanation}",
            parse_mode="HTML",
        )
        await ConversionFunnelService().record(
            event_name="ai_explanation_seen",
            user=user,
            source="course_trial_auto_explanation",
            lesson_id=getattr(lesson, "id", None),
            payload={"lesson_order": course_miniapp_lesson_id(lesson) if lesson else None},
        )
        await respond(
            t("course_trial_soft_paywall_teaser", lang),
            reply_markup=subscription_miniapp_keyboard(
                lang,
                source="trial_soft_paywall",
                mode="subscription",
                text=t("qa_limit_subscribe_button", lang),
            ),
            parse_mode="HTML",
        )
        await ConversionFunnelService().record(
            event_name="paywall_seen",
            user=user,
            source="trial_soft_paywall",
            lesson_id=getattr(lesson, "id", None),
            payload={"lesson_order": course_miniapp_lesson_id(lesson) if lesson else None},
        )
        return True
    except Exception:
        logger.exception("Failed to send trial quiz value teaser for user %s", telegram_id)
        return False
