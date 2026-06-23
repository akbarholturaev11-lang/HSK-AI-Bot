import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from aiogram import Bot
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
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
from app.services.conversion_funnel_service import ConversionFunnelService
from app.services.onboarding_tip_service import OnboardingTipService
from app.services.study_miniapp_service import StudyMiniAppService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_lesson_flow_service import CourseMiniAppLessonFlowService
from app.services.course_miniapp_onboarding_service import CourseMiniAppOnboardingService
from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService
from app.services.course_mistake_service import CourseMistakeService
from app.services.course_gamification_service import CourseGamificationService
from app.services.subscription_miniapp_service import SubscriptionMiniAppService
from app.services.voice_practice_service import VoicePracticeError, VoicePracticeService
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id
from app.repositories.user_repo import UserRepository
from app.repositories.course_pilot_event_repo import CoursePilotEventRepository
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.course import homework_retry_keyboard
from app.bot.keyboards.subscription import subscription_miniapp_keyboard
from app.bot.utils.i18n import t
from app.bot.utils.trial_value_flow import send_trial_quiz_value_teaser
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


@app.get("/duo-lesson.html")
async def duo_lesson_miniapp():
    return miniapp_file_response("app/static/study.html")


@app.get("/study.html")
async def study_miniapp():
    return miniapp_file_response("app/static/study.html")


@app.get("/voice-practice.html")
async def voice_practice_miniapp():
    return miniapp_file_response("app/static/voice-practice.html")


@app.get("/study-v2.css")
async def study_v2_styles():
    return miniapp_file_response("app/static/study-v2.css")


@app.get("/study-v2.js")
async def study_v2_script():
    return miniapp_file_response("app/static/study-v2.js")


def _voice_practice_user_id(init_data: str) -> int | None:
    return extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN)


def _voice_practice_error(error: VoicePracticeError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"ok": False, "code": error.code, "message": error.message},
    )


@app.get("/api/voice-practice/me")
async def voice_practice_me(request: Request):
    telegram_id = _voice_practice_user_id(request.query_params.get("initData", ""))
    if not telegram_id:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "code": "INVALID_INIT_DATA", "message": "Invalid Telegram init data."},
        )
    try:
        async with async_session_maker() as session:
            return await VoicePracticeService(session).user_status(telegram_id)
    except VoicePracticeError as error:
        return _voice_practice_error(error)


@app.post("/api/voice-practice/session/start")
async def voice_practice_start(request: Request):
    payload = await request.json()
    telegram_id = _voice_practice_user_id(str(payload.get("initData") or ""))
    if not telegram_id:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "code": "INVALID_INIT_DATA", "message": "Invalid Telegram init data."},
        )
    try:
        async with async_session_maker() as session:
            result = await VoicePracticeService(session).start_session(
                telegram_id,
                role=str(payload.get("role") or ""),
                level=str(payload.get("level") or ""),
                language=str(payload.get("language") or ""),
                voice=str(payload.get("voice") or ""),
            )
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            await CourseMiniAppAnalyticsService(session).record_server_event(
                event_name="voice_started",
                telegram_id=telegram_id,
                user_id=getattr(user, "id", None),
                source="course_voice",
                level=str(payload.get("level") or "") or None,
                session_id=str(result.get("session_id") or "") or None,
                dedupe_key=str(result.get("session_id") or "") or None,
                payload={
                    "role": str(payload.get("role") or ""),
                    "course_context": result.get("course_context"),
                },
            )
            await session.commit()
            return result
    except VoicePracticeError as error:
        return _voice_practice_error(error)


@app.post("/api/voice-practice/message")
async def voice_practice_message(request: Request):
    form = await request.form()
    telegram_id = _voice_practice_user_id(str(form.get("initData") or ""))
    if not telegram_id:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "code": "INVALID_INIT_DATA", "message": "Invalid Telegram init data."},
        )
    audio = form.get("audio")
    if audio is None or not hasattr(audio, "read"):
        return JSONResponse(
            status_code=400,
            content={"ok": False, "code": "EMPTY_AUDIO", "message": "Audio is required."},
        )
    audio_bytes = await audio.read(5 * 1024 * 1024 + 1)
    try:
        async with async_session_maker() as session:
            return await VoicePracticeService(session).process_message(
                telegram_id,
                session_id=str(form.get("session_id") or ""),
                audio_bytes=audio_bytes,
                filename=str(getattr(audio, "filename", None) or "voice.webm"),
            )
    except VoicePracticeError as error:
        return _voice_practice_error(error)


@app.post("/api/voice-practice/session/end")
async def voice_practice_end(request: Request):
    payload = await request.json()
    telegram_id = _voice_practice_user_id(str(payload.get("initData") or ""))
    if not telegram_id:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "code": "INVALID_INIT_DATA", "message": "Invalid Telegram init data."},
        )
    try:
        async with async_session_maker() as session:
            session_id = str(payload.get("session_id") or "")
            result = await VoicePracticeService(session).end_session(
                telegram_id,
                session_id,
            )
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            await CourseMiniAppAnalyticsService(session).record_server_event(
                event_name="voice_completed",
                telegram_id=telegram_id,
                user_id=getattr(user, "id", None),
                source="course_voice",
                session_id=session_id or None,
                dedupe_key=session_id or None,
                payload={
                    "duration_seconds": result.get("duration_seconds", 0),
                    "message_count": result.get("message_count", 0),
                    "correction_count": len(result.get("corrections") or []),
                },
            )
            await session.commit()
            return result
    except VoicePracticeError as error:
        return _voice_practice_error(error)


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

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    async with async_session_maker() as session:
        access_payload = await StudyMiniAppService(session).get_access_payload(telegram_id)
        if access_payload.get("error"):
            return access_payload

        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        opened_at = str(payload.get("opened_at") or "").strip()[:80]
        await CourseMiniAppAnalyticsService(session).record_server_event(
            event_name="miniapp_opened",
            telegram_id=telegram_id,
            user_id=getattr(user, "id", None),
            source="course_miniapp",
            level=str(access_payload.get("level") or "") or None,
            dedupe_key=f"open:{opened_at}" if opened_at else None,
        )
        await session.commit()
        return access_payload


@app.post("/api/miniapp/onboarding")
async def miniapp_onboarding(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "error": "invalid_telegram_init_data"},
        )

    payload = await request.json()
    try:
        timezone_offset = int(payload.get("timezone_offset_minutes") or 0)
        async with async_session_maker() as session:
            result = await CourseMiniAppOnboardingService(session).complete(
                telegram_id,
                level=str(payload.get("level") or ""),
                goal=str(payload.get("goal") or ""),
                daily_minutes=int(payload.get("daily_minutes") or 0),
                start_mode=str(payload.get("start_mode") or ""),
                timezone_offset_minutes=timezone_offset,
            )
    except (TypeError, ValueError) as error:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "invalid_onboarding_payload", "message": str(error)},
        )

    if result.get("ok"):
        return result
    status_code = 409 if result.get("error") == "course_level_change_requires_placement" else 400
    return JSONResponse(status_code=status_code, content=result)


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


@app.get("/api/miniapp/course-lesson")
async def miniapp_course_lesson(
    request: Request,
    lesson: int,
    level: str,
    lang: str = "ru",
):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "error": "invalid_telegram_init_data"},
        )
    async with async_session_maker() as session:
        result = await CourseMiniAppLessonFlowService(session).get_flow(
            telegram_id,
            level=level,
            lesson_order=lesson,
            lang=normalize_miniapp_lang(lang),
        )
    status_code = 200 if result.get("ok") else 403
    return JSONResponse(status_code=status_code, content=result)


@app.post("/api/miniapp/course-lesson/complete")
async def miniapp_course_lesson_complete(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "error": "invalid_telegram_init_data"},
        )
    try:
        payload = await request.json()
        lesson_order = int(payload.get("lesson_id") or 0)
    except (TypeError, ValueError):
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "invalid_lesson_payload"},
        )
    async with async_session_maker() as session:
        result = await CourseMiniAppLessonFlowService(session).complete_flow(
            telegram_id,
            level=str(payload.get("level") or ""),
            lesson_order=lesson_order,
            lang=normalize_miniapp_lang(str(payload.get("lang") or "ru")),
            responses=payload.get("responses") if isinstance(payload.get("responses"), list) else [],
        )
    status_code = 200 if result.get("ok") else 400
    return JSONResponse(status_code=status_code, content=result)


@app.post("/api/miniapp/practice/start")
async def miniapp_practice_start(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    try:
        payload = await request.json()
        async with async_session_maker() as session:
            result = await CourseMiniAppPracticeService(session).start(
                telegram_id,
                mode=str(payload.get("mode") or ""),
                level=str(payload.get("level") or "hsk1"),
                lang=normalize_miniapp_lang(str(payload.get("lang") or "ru")),
                skill=str(payload.get("skill") or ""),
            )
    except ValueError as error:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_practice_payload", "message": str(error)})
    return JSONResponse(status_code=200 if result.get("ok") else 403, content=result)


@app.post("/api/miniapp/practice/complete")
async def miniapp_practice_complete(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    try:
        payload = await request.json()
        async with async_session_maker() as session:
            result = await CourseMiniAppPracticeService(session).complete(
                telegram_id,
                session_id=str(payload.get("session_id") or ""),
                mode=str(payload.get("mode") or ""),
                level=str(payload.get("level") or "hsk1"),
                lang=normalize_miniapp_lang(str(payload.get("lang") or "ru")),
                skill=str(payload.get("skill") or ""),
                answers=payload.get("answers") if isinstance(payload.get("answers"), list) else [],
            )
    except ValueError as error:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_practice_payload", "message": str(error)})
    return JSONResponse(status_code=200 if result.get("ok") else 400, content=result)


@app.get("/api/miniapp/mistakes")
async def miniapp_mistakes(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    async with async_session_maker() as session:
        result = await CourseMistakeService(session).overview(telegram_id)
    return JSONResponse(status_code=200 if result.get("ok") else 404, content=result)


@app.get("/api/miniapp/gamification")
async def miniapp_gamification(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    async with async_session_maker() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            return JSONResponse(status_code=404, content={"ok": False, "error": "access_start_first"})
        result = await CourseGamificationService(session).leaderboard(user)
        await session.commit()
    return {"ok": True, **result}


@app.get("/api/miniapp/profile")
async def miniapp_profile(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    async with async_session_maker() as session:
        result = await StudyMiniAppService(session).get_profile_payload(telegram_id)
        await session.commit()
    return JSONResponse(status_code=200 if result.get("ok") else 404, content=result)


@app.post("/api/miniapp/mistakes/review/start")
async def miniapp_mistake_review_start(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    async with async_session_maker() as session:
        result = await CourseMistakeService(session).start_review(telegram_id)
    status_code = 200 if result.get("ok") else 403 if result.get("error") == "free_feature_limit_reached" else 400
    return JSONResponse(status_code=status_code, content=result)


@app.post("/api/miniapp/mistakes/review/complete")
async def miniapp_mistake_review_complete(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_mistake_review_payload"})
    async with async_session_maker() as session:
        result = await CourseMistakeService(session).complete_review(
            telegram_id,
            session_id=str(payload.get("session_id") or ""),
            answers=payload.get("answers") if isinstance(payload.get("answers"), list) else [],
        )
    return JSONResponse(status_code=200 if result.get("ok") else 400, content=result)


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
        result = await SubscriptionMiniAppService(session).overview(
            telegram_id,
            bot=bot,
            mode=str(payload.get("mode") or ""),
            campaign_id=_positive_int(payload.get("campaign_id")),
            feedback_id=_positive_int(payload.get("feedback_id")),
        )
        if result.get("ok"):
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            await ConversionFunnelService().record(
                event_name="checkout_opened",
                user=user,
                telegram_id=telegram_id,
                source=str(payload.get("source") or payload.get("mode") or "subscription_miniapp"),
                payload={
                    "mode": str(payload.get("mode") or ""),
                    "campaign_id": _positive_int(payload.get("campaign_id")),
                    "feedback_id": _positive_int(payload.get("feedback_id")),
                },
            )
        return result


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
        result = await SubscriptionMiniAppService(session).submit(
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
        if result.get("ok") and result.get("payment_id") and not result.get("already_pending"):
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            await ConversionFunnelService().record(
                event_name="payment_screenshot_submitted",
                user=user,
                telegram_id=telegram_id,
                source=str(payload.get("source") or payload.get("mode") or "subscription_miniapp"),
                payment_id=_positive_int(result.get("payment_id")),
                payload={
                    "plan_type": str(payload.get("plan_type") or ""),
                    "payment_method": str(payload.get("payment_method") or ""),
                    "mode": str(payload.get("mode") or ""),
                },
            )
        return result


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
        analytics_service = CourseMiniAppAnalyticsService(session)

        if event == "subscribe_clicked":
            sent = await study_service.send_subscription_menu(bot, telegram_id)
            return {"ok": bool(sent)}

        if event == "quiz_ai_discuss_clicked":
            _track_study_ai_task(
                asyncio.create_task(_send_study_quiz_ai_discussion(telegram_id, payload))
            )
            return {"ok": True}

        if event == "v2_lesson_completed":
            return {"ok": False, "error": "course_lesson_flow_required"}

        if event in analytics_service.CLIENT_EVENT_NAMES:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            result = await analytics_service.record_client_event(
                event_name=event,
                telegram_id=telegram_id,
                user_id=getattr(user, "id", None),
                level=str(payload.get("level") or "") or None,
                lesson_order=_positive_int(payload.get("lesson_order") or payload.get("lesson_id")),
                session_id=str(payload.get("session_id") or "") or None,
                dedupe_key=str(payload.get("event_id") or payload.get("dedupe_key") or "") or None,
                payload=payload,
            )
            if result.get("ok"):
                await session.commit()
            return result

        if event in {
            "study_quiz_completed",
            "starred_changed",
            "audio_played",
            "language_changed",
            "level_changed",
            "v2_screen_opened",
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
            async def respond(text, **kwargs):
                await bot.send_message(chat_id=telegram_id, text=text, **kwargs)

            await send_trial_quiz_value_teaser(
                session=session,
                telegram_id=telegram_id,
                result=result,
                respond=respond,
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
