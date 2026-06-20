import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from aiogram import Bot
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from starlette.middleware.gzip import GZipMiddleware

from app.config import settings
from app.bot.create_bot import create_bot
from app.db.session import async_session_maker, init_db
from app.db.models.course_lessons import CourseLesson
from app.services.course_seed_service import CourseSeedService
from app.services.access_service import AccessService
from app.services.daily_reset_service import DailyResetService
from app.services.expiry_reminder_service import ExpiryReminderService
from app.services.course_reminder_service import CourseReminderService
from app.services.bot_feedback_service import BotFeedbackService
from app.services.ad_campaign_service import AdCampaignService
from app.services.release_feedback_service import ReleaseFeedbackService
from app.services.discount_notification_service import DiscountNotificationService
from app.services.partner_service import PartnerService
from app.services.app_error_context_service import AppErrorContextService
from app.services.course_miniapp_result_service import CourseMiniAppResultService
from app.services.course_miniapp_lesson_service import CourseMiniAppLessonService
from app.services.onboarding_tip_service import OnboardingTipService
from app.services.study_miniapp_service import StudyMiniAppService
from app.services.subscription_miniapp_service import SubscriptionMiniAppService
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id
from app.repositories.user_repo import UserRepository
from app.repositories.course_pilot_event_repo import CoursePilotEventRepository
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.course import homework_retry_keyboard
from app.bot.keyboards.subscription import subscription_miniapp_keyboard
from app.bot.utils.i18n import t
from app.bot.keyboards.course_miniapp import (
    course_homework_done_keyboard,
    course_miniapp_quiz_result_keyboard,
)
from app.bot.utils.course_miniapp import (
    format_miniapp_homework_result,
    format_miniapp_quiz_result,
    normalize_miniapp_lang,
)

logger = logging.getLogger(__name__)

bot, dp = create_bot(settings)
_study_ai_tasks = set()


def _positive_int(value) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


async def _send_course_access_expired_offer(session, telegram_id: int) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    lang = user.language if user.language else "ru"
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=t("course_only_active_users", lang),
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
        )
        await bot.send_message(
            chat_id=telegram_id,
            text=t("subscription_miniapp_entry_text", lang),
            reply_markup=subscription_miniapp_keyboard(
                lang,
                source="course_expired",
                mode="subscription",
                include_free_mode=True,
            ),
            parse_mode="HTML",
        )
    except Exception as error:
        logger.warning("Failed to notify expired course user %s: %s", telegram_id, error)


def _track_study_ai_task(task) -> None:
    _study_ai_tasks.add(task)

    def _done(completed_task):
        _study_ai_tasks.discard(completed_task)
        if completed_task.cancelled():
            return
        error = completed_task.exception()
        if error:
            logger.error(
                "Study Mini App QA discussion failed: %s",
                error,
                exc_info=(type(error), error, error.__traceback__),
            )

    task.add_done_callback(_done)


async def _send_study_quiz_ai_discussion(telegram_id: int, payload: dict) -> None:
    async with async_session_maker() as session:
        await StudyMiniAppService(session).send_quiz_ai_discussion(bot, telegram_id, payload)


async def _record_course_pilot_event(
    session,
    *,
    telegram_id: int,
    level: str,
    lesson_order: int,
    event_type: str,
    step_name: str,
    mode: str,
    block_no: int | None = None,
    payload: dict | None = None,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    result = await session.execute(
        select(CourseLesson)
        .where(CourseLesson.level == (level or "").strip().lower())
        .where(CourseLesson.lesson_order == lesson_order)
        .limit(1)
    )
    lesson = result.scalar_one_or_none()
    await CoursePilotEventRepository(session).record(
        telegram_id=telegram_id,
        user_id=getattr(user, "id", None),
        lesson_id=getattr(lesson, "id", None),
        level=level,
        lesson_order=lesson_order,
        block_no=block_no,
        event_type=event_type,
        step_name=step_name,
        mode=mode,
        payload=payload,
    )


async def _seed_lessons() -> None:
    """Run all lesson seed scripts in the background after startup."""
    logger.info("=== SEEDING START: loading all lesson scripts ===")
    try:
        async with async_session_maker() as session:
            count = await CourseSeedService(session).sync_all_lessons()
        logger.info(f"=== SEEDING COMPLETE: {count} lessons in DB ===")
    except Exception as e:
        logger.error(f"=== SEEDING ERROR: {e} ===", exc_info=True)


async def _background_scheduler(bot: Bot) -> None:
    while True:
        await asyncio.sleep(60)
        try:
            async with async_session_maker() as session:
                _, expired_course_user_ids = await AccessService(session).downgrade_expired_active_users()
                for telegram_id in expired_course_user_ids:
                    await _send_course_access_expired_offer(session, telegram_id)
            async with async_session_maker() as session:
                await DailyResetService(session).send_daily_reset_notifications(bot)
            async with async_session_maker() as session:
                await ExpiryReminderService(session).send_expiry_reminders(bot)
            async with async_session_maker() as session:
                await CourseReminderService(session).send_due_reminders(bot)
            async with async_session_maker() as session:
                await CourseReminderService(session).send_weekly_progress_reports(bot)
            async with async_session_maker() as session:
                await BotFeedbackService(session).send_due_price_discount_offers(bot)
            async with async_session_maker() as session:
                await DiscountNotificationService(session).send_due_notifications(bot)
            async with async_session_maker() as session:
                await PartnerService(session).send_due_payout_reminders(bot)
            async with async_session_maker() as session:
                await OnboardingTipService(session).send_due_tips(bot)
            async with async_session_maker() as session:
                await AdCampaignService(session).send_due_ads(bot)
            async with async_session_maker() as session:
                await ReleaseFeedbackService(session).send_due_campaigns(bot)
            async with async_session_maker() as session:
                await BotFeedbackService(session).send_due_feedback_requests(bot)
        except Exception as e:
            print("Scheduler error:", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()                                          # faqat jadval yaratish (tez)
    seed_task = asyncio.create_task(_seed_lessons())        # background seeding
    polling_task = asyncio.create_task(dp.start_polling(bot))
    scheduler_task = asyncio.create_task(_background_scheduler(bot))
    try:
        yield                                                # /health darhol ishlaydi
    finally:
        seed_task.cancel()
        polling_task.cancel()
        scheduler_task.cancel()
        study_ai_tasks = tuple(_study_ai_tasks)
        for task in study_ai_tasks:
            task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await seed_task
        with contextlib.suppress(asyncio.CancelledError):
            await polling_task
        with contextlib.suppress(asyncio.CancelledError):
            await scheduler_task
        for task in study_ai_tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await bot.session.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1024)

MINIAPP_HTML_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def miniapp_file_response(path: str) -> FileResponse:
    return FileResponse(path, headers=MINIAPP_HTML_HEADERS)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/hsk3.html")
async def hsk3_miniapp():
    return miniapp_file_response("app/static/hsk3.html")


@app.get("/hsk4.html")
async def hsk4_miniapp():
    return miniapp_file_response("app/static/hsk4.html")


@app.get("/hsk1.html")
async def hsk1_miniapp():
    return miniapp_file_response("app/static/hsk1.html")


@app.get("/hsk2.html")
async def hsk2_miniapp():
    return miniapp_file_response("app/static/hsk2.html")


@app.get("/study.html")
async def study_miniapp():
    return miniapp_file_response("app/static/study.html")


@app.get("/subscription.html")
async def subscription_miniapp():
    return miniapp_file_response("app/static/subscription.html")


@app.get("/subscription-preview.html")
async def subscription_preview_miniapp():
    return miniapp_file_response("app/static/subscription.html")


@app.get("/stroke-order.html")
async def stroke_order_miniapp():
    return miniapp_file_response("app/static/stroke-order.html")


@app.get("/course-miniapp-v2.js")
async def course_miniapp_v2_script():
    return miniapp_file_response("app/static/course-miniapp-v2.js")


@app.post("/api/miniapp/access")
async def miniapp_access(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return {"ok": False, "error": "invalid_telegram_init_data"}

    async with async_session_maker() as session:
        return await StudyMiniAppService(session).get_access_payload(telegram_id)


@app.get("/api/miniapp/lesson")
async def miniapp_lesson(
    request: Request,
    lesson: int,
    lang: str = "uz",
    level: str = "hsk3",
    block: int | None = None,
    mode: str = "course",
):
    resolved_lang = normalize_miniapp_lang(lang)

    async with async_session_maker() as session:
        payload = await CourseMiniAppLessonService(session).get_payload(lesson, resolved_lang, level=level, block_no=block)
        if not payload:
            return {"ok": False, "error": "lesson_not_found"}
        telegram_id = extract_verified_webapp_user_id(
            request.headers.get("X-Telegram-Init-Data", ""),
            settings.BOT_TOKEN,
        )
        if telegram_id:
            await _record_course_pilot_event(
                session,
                telegram_id=telegram_id,
                level=str(payload.get("level") or level),
                lesson_order=int(payload.get("lesson_id") or lesson),
                event_type="opened",
                step_name=f"{mode}_opened",
                mode=mode,
                block_no=payload.get("block_no"),
                payload={"has_experience": bool(payload.get("experience"))},
            )
            await session.commit()
        return {"ok": True, "lesson": payload}


@app.post("/api/subscription-miniapp/overview")
async def subscription_miniapp_overview(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return {"ok": False, "error": "invalid_telegram_init_data"}

    payload = await request.json()
    async with async_session_maker() as session:
        return await SubscriptionMiniAppService(session).overview(
            telegram_id,
            bot=bot,
            mode=str(payload.get("mode") or ""),
            campaign_id=_positive_int(payload.get("campaign_id")),
            feedback_id=_positive_int(payload.get("feedback_id")),
        )


@app.post("/api/subscription-miniapp/discount-start")
async def subscription_miniapp_discount_start(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return {"ok": False, "error": "invalid_telegram_init_data"}

    async with async_session_maker() as session:
        return await SubscriptionMiniAppService(session).start_discount(telegram_id, bot=bot)


@app.post("/api/subscription-miniapp/quote")
async def subscription_miniapp_quote(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return {"ok": False, "error": "invalid_telegram_init_data"}

    payload = await request.json()
    async with async_session_maker() as session:
        return await SubscriptionMiniAppService(session).quote(
            telegram_id=telegram_id,
            plan_type=str(payload.get("plan_type") or ""),
            payment_method=str(payload.get("payment_method") or ""),
            card_country=payload.get("card_country"),
            bot=bot,
            mode=str(payload.get("mode") or ""),
            campaign_id=_positive_int(payload.get("campaign_id")),
            feedback_id=_positive_int(payload.get("feedback_id")),
        )


@app.post("/api/subscription-miniapp/submit")
async def subscription_miniapp_submit(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return {"ok": False, "error": "invalid_telegram_init_data"}

    payload = await request.json()
    async with async_session_maker() as session:
        return await SubscriptionMiniAppService(session).submit(
            telegram_id=telegram_id,
            plan_type=str(payload.get("plan_type") or ""),
            payment_method=str(payload.get("payment_method") or ""),
            card_country=payload.get("card_country"),
            screenshot_data_url=str(payload.get("screenshot_data_url") or ""),
            bot=bot,
            mode=str(payload.get("mode") or ""),
            campaign_id=_positive_int(payload.get("campaign_id")),
            feedback_id=_positive_int(payload.get("feedback_id")),
        )


@app.post("/api/miniapp/event")
async def miniapp_event(request: Request):
    payload = await request.json()
    event = str(payload.get("event") or "").strip()

    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return {"ok": False, "error": "invalid_telegram_init_data"}

    async with async_session_maker() as session:
        if event == "bot_return_clicked":
            await _record_course_pilot_event(
                session,
                telegram_id=telegram_id,
                level=str(payload.get("level") or ""),
                lesson_order=_positive_int(payload.get("lesson_id")) or 0,
                event_type="returned",
                step_name=str(payload.get("mode") or "course"),
                mode=str(payload.get("mode") or "course"),
                block_no=_positive_int(payload.get("block_no") or payload.get("block")),
                payload=payload,
            )
            await session.commit()
            return {"ok": True}

        study_service = StudyMiniAppService(session)

        if event == "subscribe_clicked":
            sent = await study_service.send_subscription_menu(bot, telegram_id)
            return {"ok": bool(sent)}

        if event == "quiz_ai_discuss_clicked":
            _track_study_ai_task(
                asyncio.create_task(_send_study_quiz_ai_discussion(telegram_id, payload))
            )
            return {"ok": True}

        if event in {
            "study_quiz_completed",
            "starred_changed",
            "audio_played",
            "language_changed",
            "level_changed",
        }:
            return {"ok": True}

        if event == "app_error":
            saved = await AppErrorContextService(session).record_miniapp_error(
                telegram_id=telegram_id,
                payload=payload,
            )
            return {"ok": bool(saved)}

        service = CourseMiniAppResultService(session)

        if event == "quiz_completed":
            result = await service.save_quiz_result(telegram_id, payload)
            if result.get("error_key"):
                if result["error_key"] == "course_only_active_users":
                    await _send_course_access_expired_offer(session, telegram_id)
                return {"ok": False, "error": result["error_key"]}

            user = result["user"]
            lang = user.language if user and user.language else "ru"
            reply_markup = course_miniapp_quiz_result_keyboard(
                lang,
                block_no=bool(result.get("block_no")),
                low_score=int(result.get("percent") or 0) < 60,
            )
            await bot.send_message(
                chat_id=telegram_id,
                text=format_miniapp_quiz_result(lang, result),
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            return {"ok": True}

        if event == "homework_submitted":
            pre_user = await UserRepository(session).get_by_telegram_id(telegram_id)
            lang = pre_user.language if pre_user and pre_user.language else "ru"
            processing_message = None
            try:
                processing_message = await bot.send_message(
                    chat_id=telegram_id,
                    text=t("course_miniapp_homework_processing", lang),
                    parse_mode="HTML",
                )
            except Exception as error:
                logger.warning("Failed to send homework processing message to %s: %s", telegram_id, error)

            result = await service.save_homework_result(telegram_id, payload)
            if result.get("error_key"):
                if result["error_key"] == "course_only_active_users":
                    if processing_message:
                        try:
                            await processing_message.edit_text(
                                text=t(result["error_key"], lang),
                                parse_mode="HTML",
                            )
                        except Exception as error:
                            logger.warning("Failed to edit homework processing error for %s: %s", telegram_id, error)
                        await bot.send_message(
                            chat_id=telegram_id,
                            text=t("subscription_miniapp_entry_text", lang),
                            reply_markup=subscription_miniapp_keyboard(
                                lang,
                                source="course_expired",
                                mode="subscription",
                                include_free_mode=True,
                            ),
                            parse_mode="HTML",
                        )
                    else:
                        await _send_course_access_expired_offer(session, telegram_id)
                elif processing_message:
                    try:
                        await processing_message.edit_text(
                            text=t(result["error_key"], lang),
                            parse_mode="HTML",
                        )
                    except Exception as error:
                        logger.warning("Failed to edit homework processing error for %s: %s", telegram_id, error)
                        await bot.send_message(
                            chat_id=telegram_id,
                            text=t(result["error_key"], lang),
                            parse_mode="HTML",
                        )
                else:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=t(result["error_key"], lang),
                        parse_mode="HTML",
                    )
                return {"ok": False, "error": result["error_key"]}

            user = result["user"]
            lang = user.language if user and user.language else "ru"
            result_text = format_miniapp_homework_result(lang, result)
            result_markup = (
                course_homework_done_keyboard(lang)
                if result.get("passed")
                else homework_retry_keyboard(lang)
            )
            if processing_message:
                try:
                    await processing_message.edit_text(
                        text=result_text,
                        reply_markup=result_markup,
                        parse_mode="HTML",
                    )
                except Exception as error:
                    logger.warning("Failed to edit homework processing result for %s: %s", telegram_id, error)
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=result_text,
                        reply_markup=result_markup,
                        parse_mode="HTML",
                    )
            else:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=result_text,
                    reply_markup=result_markup,
                    parse_mode="HTML",
                )
            return {"ok": True}

    return {"ok": False, "error": "unknown_event"}
