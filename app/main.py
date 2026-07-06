import asyncio
import contextlib
import logging
import os
import shutil
import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from starlette.middleware.gzip import GZipMiddleware

from app.config import settings
from app.bot.create_bot import create_bot
from app.db.session import async_session_maker, init_db
from app.db.models.user import User
from app.db.models.course_lessons import CourseLesson
from app.db.models.notification_template import NotificationTemplate  # noqa: F401 (register table)
from app.db.models.course_ad import CourseAdCreative, CourseAdView  # noqa: F401 (register tables)
from app.services.course_seed_service import CourseSeedService
from app.services.notification_template_service import (
    MOTIVATION_KEYS,
    NotificationTemplateService,
)
from app.services.motivation_reminder_service import (
    MEDIA_ROOT as NOTIFICATION_MEDIA_ROOT,
    MotivationReminderService,
)
from app.services.access_service import AccessService
from app.services.bot_block_status_service import BotBlockStatusService
from app.services.daily_reset_service import DailyResetService
from app.services.expiry_reminder_service import ExpiryReminderService
from app.services.course_reminder_service import CourseReminderService
from app.services.bot_feedback_service import BotFeedbackService
from app.services.subscription_churn_service import SubscriptionChurnService
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
from app.services.course_challenge_service import CourseChallengeService
from app.services.course_miniapp_access_service import (
    COURSE_AI_PRACTICE_FEATURES,
    CourseMiniAppAccessService,
)
from app.services.course_ad_service import COURSE_AD_MEDIA_ROOT, CourseAdService
from app.services.referral_service import ReferralService, REFERRAL_TRIAL_REQUIRED_ACTIVE
from app.services.payment_notify_service import PaymentNotifyService
from app.services.portfolio_service import PortfolioService
from app.services.required_channel_service import RequiredChannelService
from app.services.subscription_service import SubscriptionService
from app.services.subscription_price_service import PAYMENT_METHODS, PLANS, SubscriptionPriceService
from app.services.subscription_currency_service import format_subscription_price
from app.services.subscription_miniapp_service import SubscriptionMiniAppService
from app.services.subscription_miniapp_service import PAYMENT_DETAILS_KEY
from app.services.subscription_entry_analytics_service import SubscriptionEntryAnalyticsService
from app.services.admin_miniapp_service import (
    HOT_LEAD_ACTIVITY_WINDOW,
    AdminMiniAppService,
    admin_miniapp_today_start,
    is_admin_active_today,
    is_admin_hot_lead,
)
from app.services.admin_finance_stats_service import AdminFinanceStatsService
from app.services.broadcast_translation_service import localized_broadcast_text_for_language
from app.services.admin_broadcast_service import (
    AdminBroadcastService,
    BROADCAST_FILTER_OPTIONS,
    parse_broadcast_filters,
    parse_button_config,
)
from app.services.payment_qr_code_service import (
    PaymentQrCodeService,
    SUBSCRIPTION_DISCOUNT_20_QR_SCOPE,
    SUBSCRIPTION_QR_SCOPE,
)
from app.bot.keyboards.promo_button import encode_promo_button_config
from app.services.help_settings_service import HELP_LANGS, HELP_VIDEO_FIELDS, normalize_help_url
from app.services.support_contact_service import ADMIN_CONTACT_KEY, admin_contact_url, normalize_admin_contact
from app.services.voice_practice_service import VoicePracticeError, VoicePracticeService
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id
from app.repositories.ad_campaign_repo import AdCampaignRepository, decode_languages as decode_ad_languages
from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.course_audio_repo import CourseAudioRepository
from app.repositories.user_repo import UserRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.release_feedback_repo import ReleaseFeedbackRepository, decode_languages as decode_feedback_languages
from app.repositories.discount_campaign_repo import DiscountCampaignRepository
from app.repositories.course_lesson_repo import CourseLessonRepository
from app.repositories.course_progress_repo import CourseProgressRepository
from app.repositories.course_pilot_event_repo import CoursePilotEventRepository
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.bot.keyboards.subscription_churn import subscription_expired_offer_keyboard
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
COURSE_AD_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
COURSE_AD_ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}


class CourseAdVideoError(Exception):
    pass


def _positive_int(value) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _prepare_course_ad_video_file(data: bytes, *, raw_ext: str, telegram_id: int) -> str:
    """Store course ad video as Telegram WebView-safe MP4.

    ffmpeg is expected in production (see nixpacks.toml). Without ffmpeg we
    reject uploads instead of saving a video that may render black in Telegram
    WebView.
    """
    os.makedirs(COURSE_AD_MEDIA_ROOT, exist_ok=True)
    token = uuid.uuid4().hex[:10]
    final_name = f"course_ad_{telegram_id}_{int(time.time())}_{token}.mp4"
    final_path = os.path.join(COURSE_AD_MEDIA_ROOT, final_name)
    source_ext = raw_ext if raw_ext in COURSE_AD_ALLOWED_VIDEO_EXTENSIONS else ".mp4"
    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        raise CourseAdVideoError("ffmpeg_not_available")

    source_path = os.path.join(COURSE_AD_MEDIA_ROOT, f".course_ad_upload_{token}{source_ext}")
    with open(source_path, "wb") as handle:
        handle.write(data)

    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                source_path,
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-vf",
                "scale='min(720,iw)':-2:force_original_aspect_ratio=decrease,format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-profile:v",
                "main",
                "-level",
                "3.1",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                "-shortest",
                final_path,
            ],
            check=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        with contextlib.suppress(OSError):
            os.remove(final_path)
        raise CourseAdVideoError("video_transcode_failed") from exc
    finally:
        with contextlib.suppress(OSError):
            os.remove(source_path)

    if not os.path.exists(final_path) or os.path.getsize(final_path) <= 0:
        raise CourseAdVideoError("video_transcode_failed")
    return final_name


async def _send_subscription_expired_offer(session, telegram_id: int) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return
    if getattr(user, "subscription_expired_offer_sent_at", None):
        return

    lang = user.language if user.language else "ru"
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=t("subscription_expired_soft_text", lang),
            reply_markup=subscription_expired_offer_keyboard(lang),
            parse_mode="HTML",
        )
        await SubscriptionChurnService(session).mark_expired_offer_sent(user)
        await session.commit()
    except Exception as error:
        logger.warning("Failed to notify expired subscription user %s: %s", telegram_id, error)


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
                _, expired_paid_user_ids = await AccessService(session).downgrade_expired_active_users()
                for telegram_id in expired_paid_user_ids:
                    await _send_subscription_expired_offer(session, telegram_id)
            async with async_session_maker() as session:
                await DailyResetService(session).send_daily_reset_notifications(bot)
            async with async_session_maker() as session:
                await ExpiryReminderService(session).send_expiry_reminders(bot)
            async with async_session_maker() as session:
                await CourseReminderService(session).send_due_reminders(bot)
            async with async_session_maker() as session:
                await CourseReminderService(session).send_weekly_progress_reports(bot)
            async with async_session_maker() as session:
                await MotivationReminderService(session).send_due_reminders(bot)
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
            async with async_session_maker() as session:
                await SubscriptionChurnService(session).send_due_followups(bot)
            async with async_session_maker() as session:
                await BotBlockStatusService(session).scan_due_users(bot, limit=100)
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
# Heavy, version-busted static assets (loaded as `file.js?v=YYYYMMDD`) can be cached
# long-term: a content change bumps the `?v=` query and busts the cache. Without this
# the 2.9 MB dictionary re-downloads on every page/iframe open, making the Mini App slow.
STATIC_ASSET_HEADERS = {
    "Cache-Control": "public, max-age=31536000, immutable",
}
COURSE_DATA_FILES = {
    "hsk1": "app/static/course_data/hsk1.json",
    "hsk2": "app/static/course_data/hsk2.json",
    "hsk3": "app/static/course_data/hsk3.json",
    "hsk4a": "app/static/course_data/hsk4a.json",
    "hsk4b": "app/static/course_data/hsk4b.json",
}
ADMIN_MINIAPP_SECTIONS = {
    "stats": ("📊 Statistika", "adm:stats"),
    "user_search": ("🔎 Foydalanuvchi qidirish", "adm:user_search_info"),
    "portfolio": ("💼 Portfel", "adm:portfolio"),
    "prices": ("💳 Obuna narxlari", "adm:prices"),
    "channels": ("📣 Majburiy kanal obunasi", "adm:channels"),
    "delete_user": ("🗑 Foydalanuvchini o'chirish", "adm:deleteuser_info"),
    "broadcast": ("📢 Ommaviy xabar", "adm:broadcast_info"),
    "ads": ("📣 Reklama kampaniyasi", "adm:ads_panel"),
    "release_feedback": ("🆕 Yangilik fikri", "adm:release_feedback"),
    "discount": ("🎁 Chegirma boshqaruv", "adm:discount_panel"),
    "partners": ("🤝 Hamkorlar", "adm:partners"),
    "help": ("🆘 Yordam sozlamalari", "adm:help_settings"),
    "give_access": ("✅ Obuna berish", "adm:giveaccess_info"),
    "audio": ("🎵 Audio boshqaruv", "adm:audio_panel"),
}


def miniapp_file_response(path: str) -> FileResponse:
    return FileResponse(path, headers=MINIAPP_HTML_HEADERS)


def static_asset_response(path: str, media_type: str | None = None) -> FileResponse:
    return FileResponse(path, media_type=media_type, headers=STATIC_ASSET_HEADERS)


def static_json_response(path: str) -> FileResponse:
    return FileResponse(path, media_type="application/json")


def _admin_miniapp_user_id(request: Request) -> int | None:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    return extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN)


def _is_admin_id(telegram_id: int | None) -> bool:
    return bool(telegram_id and telegram_id in settings.admin_id_list)


def _admin_auth_error(telegram_id: int | None) -> JSONResponse | None:
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})
    return None


def _mini_label(value: str | None, labels: dict[str, str]) -> str:
    return labels.get(str(value or "").lower(), value or "—")


def _mini_plan_label(value: str | None) -> str:
    return _mini_label(value, {"10_days": "10 kun", "1_month": "1 oy", "3_months": "3 oy"})


def _mini_method_label(value: str | None) -> str:
    return _mini_label(value, {"visa": "Visa/karta", "alipay": "Alipay", "wechat": "WeChat"})


def _mini_dt(value) -> str:
    if not value:
        return "—"
    try:
        return value.astimezone(timezone(timedelta(hours=8))).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(value)


def _mini_usd(value) -> str:
    try:
        return f"${float(value or 0):.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _admin_miniapp_section_keyboard(section: str) -> InlineKeyboardMarkup:
    title, callback_data = ADMIN_MINIAPP_SECTIONS.get(section, ADMIN_MINIAPP_SECTIONS["stats"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=title, callback_data=callback_data)],
            [InlineKeyboardButton(text="🛠 Admin panel", callback_data="adm:menu")],
        ]
    )


async def _admin_miniapp_management_payload(session) -> dict:
    setting_repo = BotSettingRepository(session)
    prices = await SubscriptionPriceService(session).all_prices()
    channels_service = RequiredChannelService(session)
    channel_rows = await channels_service.list_channels()
    portfolio = PortfolioService(session)
    portfolio_summary = await portfolio.get_summary()
    portfolio_history = await portfolio.list_history(limit=12)
    ad_repo = AdCampaignRepository(session)
    feedback_repo = ReleaseFeedbackRepository(session)
    discount_repo = DiscountCampaignRepository(session)
    partner_service = PartnerService(session)
    partner_stats = await partner_service.overall_stats()
    pending_partners = await partner_service.repo.list_by_status("pending", limit=12)
    active_partners = await partner_service.repo.list_by_status("active", limit=30)
    blocked_partners = await partner_service.repo.list_by_status("blocked", limit=20)
    open_payouts = await partner_service.repo.list_open_payouts(limit=12)

    active_partner_rows = []
    for item in active_partners:
        balance = await partner_service.get_balance(item)
        active_partner_rows.append({
            "id": item.id,
            "telegram_id": item.user_telegram_id,
            "contact_username": item.contact_username,
            "promotion_channel": item.promotion_channel,
            "audience_size": item.audience_size,
            "referrals": int(balance.referrals),
            "paid_referrals": int(balance.paid_referrals),
            "balance_usd": _mini_usd(balance.balance_usd),
            "in_progress_usd": _mini_usd(balance.in_progress_usd),
            "withdrawn_usd": _mini_usd(balance.withdrawn_usd),
            "approved_at": _mini_dt(item.approved_at),
        })
    blocked_partner_rows = [
        {
            "id": item.id,
            "telegram_id": item.user_telegram_id,
            "contact_username": item.contact_username,
            "promotion_channel": item.promotion_channel,
            "blocked_at": _mini_dt(item.blocked_at),
        }
        for item in blocked_partners
    ]
    audio_repo = CourseAudioRepository(session)

    help_links = []
    for field in HELP_VIDEO_FIELDS:
        for lang in HELP_LANGS:
            help_links.append({
                "key": field.key,
                "label": field.label,
                "icon": field.icon,
                "lang": lang,
                "value": normalize_help_url(await setting_repo.get(field.setting_key(lang))),
            })

    recent_ads = []
    for item in await ad_repo.list_recent(limit=8):
        recent_ads.append({
            "id": item.id,
            "title": item.title,
            "text": item.message_text or "",
            "active": bool(item.is_active),
            "rounds_sent": int(item.rounds_sent or 0),
            "send_count_total": int(item.send_count_total or 0),
            "languages": decode_ad_languages(item.target_languages),
            "starts_at": _mini_dt(item.starts_at),
            "ends_at": _mini_dt(item.ends_at),
        })

    recent_feedback = []
    for item in await feedback_repo.list_recent_campaigns(limit=8):
        recent_feedback.append({
            "id": item.id,
            "title": item.title,
            "text": item.message_text or "",
            "status": item.status,
            "sent": int(item.sent_count or 0),
            "failed": int(item.failed_count or 0),
            "languages": decode_feedback_languages(item.target_languages),
            "send_at": _mini_dt(item.send_at),
        })

    recent_discounts = []
    for item in await discount_repo.list_recent(limit=8):
        recent_discounts.append({
            "id": item.id,
            "title": item.title,
            "percent": int(item.percent or 0),
            "active": bool(item.is_active),
            "audience_status": item.audience_status or "barcha",
            "language": item.audience_language or "barcha",
            "payment_method": item.payment_method or "barcha",
            "plan_type": item.plan_type or "barcha",
            "starts_at": _mini_dt(item.starts_at),
            "ends_at": _mini_dt(item.ends_at),
            "used": await discount_repo.count_used(item.id),
        })

    audio_summary = []
    for level in ("hsk1", "hsk2", "hsk3", "hsk4"):
        audio_summary.append({
            "level": level.upper(),
            "lessons": int(await audio_repo.count_uploaded_lessons(level)),
        })

    qr_service = PaymentQrCodeService(session)
    price_items = []
    for price in prices:
        is_qr = PaymentQrCodeService.is_qr_method(price.payment_method)
        qr_set = False
        if is_qr:
            file_id = await qr_service.get_file_id(
                scope=SUBSCRIPTION_QR_SCOPE,
                payment_method=price.payment_method,
                plan_type=price.plan_type,
                amount=int(price.amount),
                currency=price.currency,
            )
            qr_set = bool(file_id)
        price_items.append({
            "method": price.payment_method,
            "method_label": _mini_method_label(price.payment_method),
            "plan": price.plan_type,
            "plan_label": _mini_plan_label(price.plan_type),
            "amount": int(price.amount),
            "currency": price.currency,
            "text": format_subscription_price(price.amount, price.currency),
            "qr_method": is_qr,
            "qr_set": qr_set,
        })

    return {
        "ok": True,
        "prices": price_items,
        "payment_details": (await setting_repo.get(PAYMENT_DETAILS_KEY) or settings.PAYMENT_DETAILS or "").strip(),
        "channels": {
            "enabled": await channels_service.is_enabled(),
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "chat_id": item.chat_id,
                    "invite_link": item.invite_link or "",
                    "active": bool(item.is_active),
                }
                for item in channel_rows
            ],
        },
        "help": {
            "admin_contact": admin_contact_url(await setting_repo.get(ADMIN_CONTACT_KEY)) or (await setting_repo.get(ADMIN_CONTACT_KEY) or ""),
            "links": help_links,
        },
        "portfolio": {
            "summary": {
                "approved_payments": portfolio_summary.approved_payments,
                "gross_revenue_usd": _mini_usd(portfolio_summary.gross_revenue_usd),
                "subscription_profit_usd": _mini_usd(portfolio_summary.subscription_profit_usd),
                "manual_profit_usd": _mini_usd(portfolio_summary.manual_profit_usd),
                "manual_expense_usd": _mini_usd(portfolio_summary.manual_expense_usd),
                "net_usd": _mini_usd(portfolio_summary.net_usd),
            },
            "history": [
                {
                    "id": item.id,
                    "type": item.transaction_type,
                    "source": item.source,
                    "amount_usd": _mini_usd(item.amount_usd),
                    "original": (
                        f"{item.original_amount:g} {item.original_currency}"
                        if item.original_amount is not None and item.original_currency
                        else ""
                    ),
                    "note": item.note or "",
                    "created_at": _mini_dt(item.created_at),
                }
                for item in portfolio_history
            ],
        },
        "campaigns": {
            "ads": recent_ads,
            "release_feedback": recent_feedback,
            "discounts": recent_discounts,
        },
        "partners": {
            "stats": {key: str(value) for key, value in partner_stats.items()},
            "active": active_partner_rows,
            "blocked": blocked_partner_rows,
            "pending": [
                {
                    "id": item.id,
                    "telegram_id": item.user_telegram_id,
                    "promotion_channel": item.promotion_channel,
                    "audience_size": item.audience_size,
                    "contact_username": item.contact_username,
                    "created_at": _mini_dt(item.created_at),
                }
                for item in pending_partners
            ],
            "payouts": [
                {
                    "id": item.id,
                    "partner_id": item.partner_id,
                    "amount_usd": _mini_usd(item.amount_usd),
                    "local_amount": f"{item.local_amount:.2f} {item.local_currency}",
                    "status": item.status,
                    "method": item.payment_method,
                    "account": item.account_details,
                    "created_at": _mini_dt(item.created_at),
                }
                for item in open_payouts
            ],
        },
        "audio": audio_summary,
    }


async def _admin_user_payload(session, user) -> dict:
    payments = await PaymentRepository(session).list_by_user(user.telegram_id, limit=10)
    now = datetime.now(timezone.utc)
    today_start = admin_miniapp_today_start(now)
    hot_since = now - HOT_LEAD_ACTIVITY_WINDOW
    return {
        "ok": True,
        "user": {
            "id": user.telegram_id,
            "name": user.full_name or "Nomsiz",
            "username": user.username,
            "language": user.language,
            "level": user.level,
            "learning_mode": user.learning_mode,
            "status": user.status,
            "status_label": user.status or "—",
            "bot_blocked": BotBlockStatusService.is_bot_blocked(user),
            "bot_blocked_at": _mini_dt(user.bot_blocked_at),
            "bot_unblocked_at": _mini_dt(user.bot_unblocked_at),
            "last_bot_block_check_at": _mini_dt(user.last_bot_block_check_at),
            "payment_status": user.payment_status,
            "payment_method": user.payment_method,
            "selected_plan_type": user.selected_plan_type,
            "start_date": _mini_dt(user.start_date),
            "end_date": _mini_dt(user.end_date),
            "questions": f"{user.questions_used}/{user.question_limit}",
            "bonus_left": max((user.bonus_questions or 0) - (user.bonus_questions_used or 0), 0),
            "streak": user.daily_practice_streak or 0,
            "created_at": _mini_dt(user.created_at),
            "last_active_at": _mini_dt(user.last_active_at),
            "active_today": is_admin_active_today(user, today_start),
            "hot_lead": is_admin_hot_lead(user, hot_since),
            "referral_code": user.referral_code or "",
            "referred_by_telegram_id": user.referred_by_telegram_id,
        },
        "payments": [
            {
                "id": payment.id,
                "status": payment.payment_status,
                "plan": _mini_plan_label(payment.plan_type),
                "method": _mini_method_label(payment.payment_method),
                "amount": format_subscription_price(payment.amount, payment.currency),
                "submitted_at": _mini_dt(payment.submitted_at),
                "reviewed_at": _mini_dt(payment.reviewed_at),
                "comment": payment.admin_comment or "",
            }
            for payment in payments
        ],
    }


def _admin_user_card_payload(user, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    today_start = admin_miniapp_today_start(now)
    hot_since = now - HOT_LEAD_ACTIVITY_WINDOW
    bonus_left = max((user.bonus_questions or 0) - (user.bonus_questions_used or 0), 0)
    return {
        "id": user.telegram_id,
        "name": user.full_name or "Nomsiz",
        "username": user.username,
        "language": user.language or "—",
        "level": user.level or "—",
        "mode": "Kurs" if user.learning_mode == "course" else "Savol-javob",
        "status": user.status,
        "status_label": user.status or "—",
        "bot_blocked": BotBlockStatusService.is_bot_blocked(user),
        "bot_blocked_at": _mini_dt(user.bot_blocked_at),
        "bot_unblocked_at": _mini_dt(user.bot_unblocked_at),
        "last_bot_block_check_at": _mini_dt(user.last_bot_block_check_at),
        "payment_status": user.payment_status,
        "payment_label": user.payment_status or "—",
        "plan": _mini_plan_label(user.selected_plan_type),
        "method": _mini_method_label(user.payment_method),
        "end_date": _mini_dt(user.end_date) if user.end_date else "",
        "last_active": _mini_dt(user.last_active_at),
        "active_today": is_admin_active_today(user, today_start),
        "hot_lead": is_admin_hot_lead(user, hot_since),
        "questions": f"{user.questions_used}/{user.question_limit}",
        "bonus_left": bonus_left,
        "streak": user.daily_practice_streak or 0,
    }


async def _review_admin_payment(
    session,
    *,
    payment_id: int,
    action: str,
    reason: str | None,
) -> tuple[dict, int]:
    payment_repo = PaymentRepository(session)
    user_repo = UserRepository(session)
    payment = await payment_repo.get_by_id(payment_id)
    if not payment:
        return {"ok": False, "error": "payment_not_found"}, 404
    if payment.payment_status != "pending":
        return {"ok": False, "error": "payment_already_reviewed"}, 409

    if action == "approve":
        if not await payment_repo.approve(payment, admin_comment="approved by admin mini app"):
            return {"ok": False, "error": "payment_already_reviewed"}, 409
        activated = await SubscriptionService(session).activate_plan(
            telegram_id=payment.user_telegram_id,
            plan_type=payment.plan_type,
            discount_source=payment.discount_source,
            payment=payment,
        )
        if not activated:
            await session.rollback()
            return {"ok": False, "error": "subscription_activation_failed"}, 400
        partner, commission_usd, unlocked_bonus = await PartnerService(session).record_approved_payment(payment)
        user = await user_repo.get_by_telegram_id(payment.user_telegram_id)
        await session.commit()
        await ConversionFunnelService().record(
            event_name="payment_approved",
            user=user,
            telegram_id=payment.user_telegram_id,
            source="admin_miniapp_payment_approve",
            payment_id=payment.id,
            payload={"plan_type": payment.plan_type, "payment_method": payment.payment_method},
        )
        async with async_session_maker() as analytics_session:
            course_event = await CourseMiniAppAnalyticsService(analytics_session).record_server_event(
                event_name="subscription_approved",
                telegram_id=payment.user_telegram_id,
                user_id=getattr(user, "id", None),
                source="admin_miniapp_payment_approve",
                dedupe_key=f"payment:{payment.id}",
                payload={"plan_type": payment.plan_type, "payment_method": payment.payment_method},
            )
            if course_event.get("recorded"):
                await analytics_session.commit()
        with contextlib.suppress(Exception):
            await PaymentNotifyService().notify_payment_approved(bot=bot, user=user)
        if partner:
            with contextlib.suppress(Exception):
                await PartnerService(session).notify_partner(
                    bot,
                    partner,
                    "partner_commission_notification",
                    commission=f"${commission_usd:.2f}",
                    include_bonus_line=unlocked_bonus,
                )
        return {"ok": True, "status": "approved"}, 200

    if action == "reject":
        comment = (reason or "rejected by admin mini app").strip()[:300]
        if not await payment_repo.reject(payment, admin_comment=comment):
            return {"ok": False, "error": "payment_already_reviewed"}, 409
        user = await user_repo.get_by_telegram_id(payment.user_telegram_id)
        if user:
            await user_repo.set_selected_plan_type(user, None)
        await session.commit()
        await ConversionFunnelService().record(
            event_name="payment_rejected",
            user=user,
            telegram_id=payment.user_telegram_id,
            source="admin_miniapp_payment_reject",
            payment_id=payment.id,
            payload={"plan_type": payment.plan_type, "payment_method": payment.payment_method, "reason": comment},
        )
        with contextlib.suppress(Exception):
            await PaymentNotifyService().notify_payment_rejected(
                bot=bot,
                user=user,
                reason=None,
                plan_type=payment.plan_type,
                payment=payment,
            )
        return {"ok": True, "status": "rejected"}, 200

    return {"ok": False, "error": "invalid_action"}, 400


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/hsk-lugat.html")
async def hsk_lugat_miniapp():
    return miniapp_file_response("app/static/hsk-lugat.html")


@app.get("/hsk-data.js")
async def hsk_data_script():
    return static_asset_response("app/static/hsk-data.js", "application/javascript")


@app.get("/admin.html")
async def admin_control_miniapp():
    return miniapp_file_response("app/static/admin.html")


@app.get("/subscription.html")
async def subscription_miniapp():
    return miniapp_file_response("app/static/subscription.html")


@app.get("/course_data/{level}.json")
async def course_data_file(level: str):
    path = COURSE_DATA_FILES.get(str(level or "").strip().lower())
    if not path:
        return JSONResponse(status_code=404, content={"ok": False, "error": "course_data_not_found"})
    return static_json_response(path)


# ── Course v3 Mini App ──────────────────────────────────────────────────────

_COURSE_V3_PAGES = {"onboarding", "recognition", "pronunciation", "test", "mistakes", "voice", "memorize"}
_COURSE_V3_LEVELS = {"hsk1", "hsk2", "hsk3", "hsk4"}


def _course_v3_level(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in _COURSE_V3_LEVELS else "hsk1"


# Band tugaganda keyingi HSK bandiga avtomatik o'tish (user.level yangilanadi).
_COURSE_V3_NEXT_BAND = {"hsk1": "hsk2", "hsk2": "hsk3", "hsk3": "hsk4"}


def _course_v3_user_level(user) -> str:
    return _course_v3_level(getattr(user, "level", None))


def _course_v3_user_lang(user) -> str:
    return normalize_miniapp_lang(getattr(user, "language", None))


def _apply_course_v3_access_policy(data: dict, *, level: str, completed: int, is_paid: bool) -> None:
    for unit in data.get("units", []):
        unit_unlocked = False
        for lesson in unit.get("lessons", []):
            n = int(lesson.get("n", 0) or 0)
            if n <= completed:
                lesson["status"] = "done"
                lesson.setdefault("stars", 2)
            elif n == completed + 1:
                lesson["status"] = "current"
                lesson.pop("stars", None)
            else:
                lesson["status"] = "locked"
                lesson.pop("stars", None)

            requires_premium = CourseMiniAppAccessService.lesson_requires_premium(level, n)
            if not is_paid and requires_premium and n > completed:
                if n == completed + 1 and n == 2:
                    # 2-dars: yangi bepul user uni ochib, ~yarmigacha ko'radi;
                    # frontend kartalar o'rtasida obuna oynasini chiqaradi.
                    lesson["status"] = "current"
                    lesson["preview_half"] = True
                    lesson.pop("locked_premium", None)
                else:
                    lesson["status"] = "locked"
                    lesson["locked_premium"] = True
                    lesson.pop("preview_half", None)
            else:
                lesson.pop("locked_premium", None)
                lesson.pop("preview_half", None)

            if lesson.get("status") in {"done", "current"} and not lesson.get("locked_premium"):
                unit_unlocked = True

        if not unit_unlocked:
            unit["status"] = "locked"
        else:
            unit.pop("status", None)


@app.get("/course-v3.html")
@app.get("/course-v3")
async def course_v3_miniapp():
    return miniapp_file_response("app/static/course-v3.html")


@app.get("/course_v3_{page}.html")
async def course_v3_sub_page(page: str):
    if page not in _COURSE_V3_PAGES:
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return miniapp_file_response(f"app/static/course_v3_{page}.html")


@app.get("/course_v3_data/memo.js")
async def course_v3_memo_script():
    return static_asset_response("app/static/course_v3_data/memo.js", "application/javascript")


@app.get("/course_v3_data/ads.js")
async def course_v3_ads_script():
    return static_asset_response("app/static/course_v3_data/ads.js", "application/javascript")


@app.get("/course_v3_data/{filename}")
async def course_v3_data_file(filename: str):
    import re
    if not re.fullmatch(r"[a-z0-9_\-]+\.json", filename):
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return static_json_response(f"app/static/course_v3_data/{filename}")


@app.get("/course_v3_data/exams/{filename}")
async def course_v3_exam_file(filename: str):
    import re
    if not re.fullmatch(r"hsk[1-4]\.json", filename):
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return static_json_response(f"app/static/course_v3_data/exams/{filename}")


@app.get("/course_v3_data/{level}/{filename}")
async def course_v3_lesson_file(level: str, filename: str):
    import re
    if not re.fullmatch(r"hsk[1-4]", level):
        return JSONResponse(status_code=404, content={"error": "not_found"})
    if not re.fullmatch(r"lesson_\d+\.json", filename):
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return static_json_response(f"app/static/course_v3_data/{level}/{filename}")


@app.get("/audio/tour/{lang}/{key}.mp3")
async def course_v3_tour_audio(lang: str, key: str):
    import os
    import re
    if lang not in {"uz", "ru", "tj"} or not re.fullmatch(r"[A-Za-z0-9_\-]+", key):
        return JSONResponse(status_code=404, content={"error": "not_found"})
    path = f"app/static/audio/tour/{lang}/{key}.mp3"
    if not os.path.isfile(path):
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return FileResponse(path, media_type="audio/mpeg")


# --- Server-side Chinese TTS (edge-tts) with on-disk cache -------------------
# Android WebView (Telegram) ko'pincha xitoy (zh-CN) speechSynthesis ovoziga ega
# emas -> jimlik. Shuning uchun ovozni serverда generatsiya qilib, mp3 sifatida
# beramiz. Har bir ibora birinchi so'rovда yaratilib diskка cache bo'ladi.
TTS_VOICE = "zh-CN-XiaoxiaoNeural"
TTS_CACHE_DIR = "app/static/audio/tts_cache"
_tts_locks: dict[str, asyncio.Lock] = {}


@app.get("/api/v3/tts")
async def v3_tts(text: str, rate: str = "-10%"):
    import hashlib
    import re

    text = (text or "").strip()
    # Faqat xitoycha iboralar: kamida bitta CJK belgisi bo'lishi shart va
    # uzunlik cheklangan (abuse/disk to'lishining oldini olish uchun).
    if not text or len(text) > 240 or not re.search(r"[一-鿿]", text):
        return JSONResponse(status_code=400, content={"error": "bad_text"})
    if not re.fullmatch(r"[+-]\d{1,3}%", rate):
        rate = "-10%"

    key = hashlib.sha1(f"{TTS_VOICE}|{rate}|{text}".encode("utf-8")).hexdigest()
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    path = os.path.join(TTS_CACHE_DIR, key + ".mp3")

    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return FileResponse(path, media_type="audio/mpeg", headers=STATIC_ASSET_HEADERS)

    lock = _tts_locks.setdefault(key, asyncio.Lock())
    async with lock:
        if not (os.path.isfile(path) and os.path.getsize(path) > 0):
            tmp = path + ".tmp"
            try:
                import edge_tts

                comm = edge_tts.Communicate(text, TTS_VOICE, rate=rate)
                await comm.save(tmp)
                if not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:
                    raise RuntimeError("empty tts output")
                os.replace(tmp, path)
            except Exception as exc:  # noqa: BLE001
                logging.warning("v3_tts generation failed: %s", exc)
                with contextlib.suppress(Exception):
                    os.remove(tmp)
                return JSONResponse(status_code=502, content={"error": "tts_failed"})

    return FileResponse(path, media_type="audio/mpeg", headers=STATIC_ASSET_HEADERS)


# --- Yengil client-side diagnostika logi -----------------------------------
# Qurilma/OS/Telegram versiyasi va audio/mikrofon xatolarini serverга yozib
# boramiz, keyinchalik "kimда nima buzilyapti" ni taxmin emas, aniq ko'rish uchun.
@app.post("/api/v3/clientlog")
async def v3_clientlog(request: Request):
    try:
        data = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=400, content={"ok": False})
    if not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"ok": False})
    event = str(data.get("event") or "")[:64]
    msg = str(data.get("msg") or "")[:300]
    ctx = data.get("ctx")
    safe_ctx = {}
    if isinstance(ctx, dict):
        for k, v in list(ctx.items())[:14]:
            safe_ctx[str(k)[:32]] = str(v)[:220]
    logging.warning("CLIENTLOG event=%s msg=%s ctx=%s", event, msg, safe_ctx)
    return JSONResponse(content={"ok": True})


@app.get("/api/v3/map")
async def v3_course_map(request: Request, lang: str = "uz", level: str | None = None):
    import json as _json
    from pathlib import Path

    init_data = request.headers.get("X-Telegram-Init-Data", "")
    telegram_id = extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN) if init_data else None

    async with async_session_maker() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id) if telegram_id else None

        if not user:
            # Botka real ulanmaganda (initData yo'q / token mos kelmadi / user topilmadi)
            # default darajadagi "preview" KO'RSATILMAYDI. Mini app bot bilan bir xil
            # daraja va tilda ochilishi shart, shuning uchun foydalanuvchidan botga
            # qaytib /start bosib qaytadan kirishni so'raymiz.
            return JSONResponse(
                status_code=401,
                content={"ok": False, "authenticated": False, "error": "auth_required"},
            )

        # Yagona manba: foydalanuvchi botda (QA / onboarding) tanlagan daraja va til.
        # Course Mini App doim user.level bandida va user.language tilida ochiladi —
        # shunday qilib QA rejim va Kurs rejim hech qachon bir-biridan farq qilmaydi.
        resolved_lang = _course_v3_user_lang(user)
        target_band = _course_v3_user_level(user)

        progress_repo = CourseProgressRepository(session)
        progress = await progress_repo.get_by_user_id(user.id, for_update=True)
        if not progress:
            progress = await progress_repo.create(
                user_id=user.id,
                level=target_band,
                current_lesson_id=None,
                current_step="intro",
                waiting_for="none",
            )
        elif _course_v3_level(progress.level) != target_band:
            # Foydalanuvchi HSK bandini o'zgartirdi (botda darajani almashtirdi yoki
            # avvalgi bandni tugatdi). Progress har bir band uchun alohida, shuning
            # uchun yangi bandni noldan boshlaymiz.
            progress.level = target_band
            progress.completed_lessons_count = 0
            progress.current_lesson_id = None
            progress.current_step = "intro"
            progress.waiting_for = "none"
            progress.homework_status = "none"
        elif progress.level != target_band:
            # Band bir xil, lekin kanonik bo'lmagan nom bilan saqlangan
            # (masalan "beginner") — kanonik bandga normallashtiramiz.
            progress.level = target_band

        profile_svc = CourseMiniAppProfileService(session)
        profile = await profile_svc.get_or_create(user.id)
        tz_raw = request.query_params.get("tz")
        if tz_raw is not None:
            try:
                profile.timezone_offset_minutes = max(-720, min(840, int(tz_raw)))
            except (TypeError, ValueError):
                pass
        gamification = await CourseGamificationService(session).snapshot(user, profile=profile)
        is_paid = StudyMiniAppService.is_paid_user(user)

        resolved_level = target_band

        map_path = Path(f"app/static/course_v3_data/{resolved_level}.json")
        if not map_path.exists():
            map_path = Path("app/static/course_v3_data/hsk1.json")
        try:
            data = _json.loads(map_path.read_text())
        except Exception:
            return JSONResponse(status_code=500, content={"ok": False, "error": "map_load_failed"})

        completed = int(getattr(progress, "completed_lessons_count", 0) or 0)
        display_name = str(
            getattr(user, "full_name", None) or getattr(user, "username", None) or "HSK Student"
        ).strip()[:60]
        initials = "".join(p[:1].upper() for p in display_name.split()[:2]) or "阿"

        data["authenticated"] = True
        data["level"] = resolved_level
        data["progress"] = {
            "xp": gamification["xp"],
            "streak": gamification["streak"],
            "weekly_xp": gamification["weekly_xp"],
            "league": gamification["league"],
            "completed": completed,
        }
        data["user"] = {
            "name": display_name,
            "avatar": initials[:2],
            "language": resolved_lang,
            "is_paid": is_paid,
            "referral_code": getattr(user, "referral_code", None) or "",
        }
        # Motivational reminders are ON by default until the user turns them off.
        data["notify"] = {
            "enabled": bool(getattr(profile, "notifications_enabled", True)),
        }
        data["admin_contact"] = admin_contact_url(await BotSettingRepository(session).get(ADMIN_CONTACT_KEY))

        _apply_course_v3_access_policy(data, level=resolved_level, completed=completed, is_paid=is_paid)

        # Darslarda endi reklama YO'Q — bepul trial (1-dars to'liq + 2-dars
        # yarmi) va obuna paywall. Reklama oqimi mashq bo'limlariga ko'chirildi
        # (har bo'limning o'z kunlik reklama-ruxsati bor, sub-sahifalar boshqaradi).

        await CourseMiniAppAnalyticsService(session).record_server_event(
            event_name="miniapp_opened",
            telegram_id=telegram_id,
            user_id=getattr(user, "id", None),
            source="course_v3",
            level=resolved_level,
            dedupe_key=f"course-v3:miniapp-opened:{resolved_level}:{datetime.now(timezone.utc).date().isoformat()}",
        )
        await session.commit()
        return JSONResponse(content=data)


@app.get("/api/v3/invite")
async def v3_invite_payload(request: Request, lang: str = "uz"):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    telegram_id = extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN) if init_data else None
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})

    resolved_lang = normalize_miniapp_lang(lang)
    tz_raw = request.query_params.get("tz")
    tz_offset = None
    if tz_raw is not None:
        try:
            tz_offset = int(tz_raw)
        except (TypeError, ValueError):
            tz_offset = None
    async with async_session_maker() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return JSONResponse(status_code=404, content={"ok": False, "error": "user_not_found"})

        service = ReferralService(session)
        await user_repo.ensure_referral_code(user)
        active_count = await service.get_trial_activation_progress(user)
        joined_count = await service.referral_repo.count_by_referrer(user.telegram_id)
        referrals = await service.list_miniapp_referrals(user, timezone_offset_minutes=tz_offset)
        bot_username = (settings.BOT_USERNAME or "hsk_ai_bot").strip().lstrip("@") or "hsk_ai_bot"
        link = f"https://t.me/{bot_username}?start={user.referral_code}"
        full_lang, full_text = await service.build_trial_progress_text(user)

        share = {
            "ru": "Привет! Я учу китайский в HSK AI. Заходи, тебе тоже будет полезно:",
            "uz": "Salom! Men HSK AI bilan xitoy tilini o'rganyapman. Kirib ko'r, senga ham foydali bo'ladi:",
            "tj": "Салом! Ман бо HSK AI чинӣ меомӯзам. Дароед, барои шумо ҳам муфид мешавад:",
        }.get(resolved_lang, "Salom! Men HSK AI bilan xitoy tilini o'rganyapman. Kirib ko'r:")

        await session.commit()
        return JSONResponse(content={
            "ok": True,
            "link": link,
            "share_text": share,
            "full_text": full_text,
            "language": full_lang,
            "joined_count": int(joined_count),
            "active_count": int(active_count),
            "required": REFERRAL_TRIAL_REQUIRED_ACTIVE,
            "referrals": referrals,
        })


@app.post("/api/v3/notify")
async def v3_notify_toggle(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    telegram_id = extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN) if init_data else None
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False})
    payload = await request.json()
    enabled = bool(payload.get("enabled", True))

    async with async_session_maker() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            return JSONResponse(status_code=404, content={"ok": False})

        # The toggle is the master switch for the motivational reminders
        # (overtaken / daily goal / streak) sent by MotivationReminderService.
        profile = await CourseMiniAppProfileService(session).get_or_create(user.id)
        profile.notifications_enabled = enabled
        await session.commit()

        return JSONResponse(content={"ok": True, "notifications": enabled})


@app.post("/api/v3/language")
async def v3_set_language(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    telegram_id = extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN) if init_data else None
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    resolved_lang = normalize_miniapp_lang(str(payload.get("language") or ""))

    async with async_session_maker() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            return JSONResponse(status_code=403, content={"ok": False, "error": "access_start_first"})
        # Til ham yagona manba: Mini Appda tanlangan til botga (user.language) yoziladi,
        # shunda QA rejim va Kurs rejim bir xil tilda ochiladi.
        user.language = resolved_lang
        await session.commit()
        return JSONResponse(content={"ok": True, "language": resolved_lang})


@app.get("/api/v3/ad")
async def v3_course_ad(
    request: Request,
    placement: str = "start",
    level: str = "hsk1",
    lesson: int = 0,
    lang: str = "",
    feature: str = "",
):
    resolved_level = _course_v3_level(level)
    lesson_order = _positive_int(lesson) or 0
    section = str(feature or "").strip().lower()
    # Mashq bo'limlarida reklama darsga bog'lanmagan (lesson=0) — `feature`
    # (masalan "recognition") kontekst sifatida keladi. Faqat dars ham,
    # bo'lim ham bo'lmasa xato.
    if lesson_order <= 0 and section not in _COURSE_DAILY_GATE_FEATURES:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_lesson_payload"})

    # Foydalanuvchining tiliga mos reklamalarni (shu til + "all") qaytaramiz.
    # initData bo'lsa — kanonik user.language; bo'lmasa — query `lang`.
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    telegram_id = extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN) if init_data else None

    async with async_session_maker() as session:
        ad_language = None
        if telegram_id:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if user and getattr(user, "language", None):
                ad_language = user.language
        if not ad_language and lang:
            ad_language = lang
        ad_language = CourseAdService.normalize_language(ad_language)

        service = CourseAdService(session)
        ads = await service.list_active_payloads(language=ad_language)
        if service.media_backup_changed:
            await session.commit()
        if not ads:
            return JSONResponse(status_code=404, content={"ok": False, "error": "course_ad_not_found"})
        return JSONResponse(
            content={
                "ok": True,
                # Eski klientlar uchun moslik: birinchi reklama "ad" sifatida ham qoladi.
                "ad": ads[0],
                "ads": ads,
                "placement": service.normalize_placement(placement),
                "level": resolved_level,
                "lesson_order": lesson_order,
            }
        )


@app.post("/api/v3/ad/view")
async def v3_course_ad_view(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    telegram_id = extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN) if init_data else None
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})

    try:
        payload = await request.json()
        ad_id = int(payload.get("ad_id") or 0)
        lesson_order = int(payload.get("lesson_order") or payload.get("lesson_id") or 0)
        watched_seconds = int(payload.get("watched_seconds") or 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_ad_view_payload"})
    section = str(payload.get("feature") or "").strip().lower()
    # Mashq bo'limi reklamasi darsga bog'lanmagan (lesson_order=0) — bunda
    # `feature` bo'lishi shart.
    if ad_id <= 0 or (lesson_order <= 0 and section not in _COURSE_DAILY_GATE_FEATURES):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_ad_view_payload"})

    placement = CourseAdService.normalize_placement(str(payload.get("placement") or "start"))
    async with async_session_maker() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            return JSONResponse(status_code=404, content={"ok": False, "error": "user_not_found"})

        resolved_level = _course_v3_user_level(user)
        service = CourseAdService(session)
        result = await service.record_view(
            user=user,
            ad_id=ad_id,
            level=resolved_level,
            lesson_order=lesson_order,
            placement=placement,
            watched_seconds=watched_seconds,
        )
        if result.get("ok"):
            await CourseMiniAppAnalyticsService(session).record_server_event(
                event_name="course_ad_viewed",
                telegram_id=telegram_id,
                user_id=getattr(user, "id", None),
                source="course_v3_ad",
                level=resolved_level,
                lesson_order=lesson_order,
                payload={
                    "ad_id": ad_id,
                    "placement": placement,
                    "watched_seconds": watched_seconds,
                },
            )
        await session.commit()
        status = 200 if result.get("ok") else 400
        return JSONResponse(status_code=status, content=result)


_COURSE_DAILY_GATE_FEATURES = {
    "recognition",
    "memorize",
    "pronunciation",
    "placement",
    "training_test",
}


@app.post("/api/v3/practice/daily-gate")
async def v3_practice_daily_gate(request: Request):
    """Mashq bo'limining BEPUL foydalanishi (bepul userga UMRDA 1 marta,
    reklamasiz). Sessiya boshlanishida chaqiriladi; bepul tugagan bo'lsa 403 +
    reklama/obuna holati. Hisob server tomonda — user aylanib o'tolmaydi."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not init_data:
        init_data = str(payload.get("initData") or "")
    telegram_id = extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN) if init_data else None
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})

    feature = str(payload.get("feature") or "").strip().lower()
    if feature not in _COURSE_DAILY_GATE_FEATURES:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_feature"})
    ref_raw = payload.get("ref")
    ref = str(ref_raw).strip()[:48] if ref_raw else None

    async with async_session_maker() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            return JSONResponse(status_code=403, content={"ok": False, "error": "access_start_first"})
        access = CourseMiniAppAccessService(session)
        # Bepul: UMRDA 1 marta (lifetime=True — kunlik yangilanmaydi).
        result = await access.consume_daily_use(user, feature_key=feature, ref=ref, lifetime=True)
        if not result.get("allowed"):
            # Bepul tugadi. Endi reklama yoki obuna. AI token sarflaydigan
            # bo'limda (masalan talaffuz) reklama ham kuniga 2 marta cheklangan;
            # boshqa bo'limlarda reklama cheksiz.
            is_ai = feature in COURSE_AI_PRACTICE_FEATURES
            if is_ai:
                ad_status = await access.daily_status(user, f"{feature}_ad")
                ad_info = {
                    "available": bool(ad_status.get("allowed")),
                    "limited": True,
                    "used": int(ad_status.get("used") or 0),
                    "limit": int(ad_status.get("limit") or 0),
                    "remaining": ad_status.get("remaining"),
                }
            else:
                ad_info = {"available": True, "limited": False}
            await session.commit()
            return JSONResponse(
                status_code=403,
                content={
                    "ok": False,
                    "error": result.get("error") or "free_feature_limit_reached",
                    "is_paid": bool(result.get("is_paid", False)),
                    "ad": ad_info,
                },
            )
        await session.commit()
        return JSONResponse(
            content={
                "ok": True,
                "allowed": True,
                "is_paid": bool(result.get("is_paid", False)),
                "remaining": result.get("remaining"),
            }
        )


@app.post("/api/v3/practice/ad-gate")
async def v3_practice_ad_gate(request: Request):
    """Bepul tugagach, user reklama ko'rib yana kirmoqchi bo'lsa chaqiriladi.
    Odatda CHEKSIZ; faqat AI token sarflaydigan bo'limda (masalan talaffuz)
    reklama ham KUNIGA 2 marta cheklanadi. Server tomonda hisoblanadi."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not init_data:
        init_data = str(payload.get("initData") or "")
    telegram_id = extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN) if init_data else None
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})

    feature = str(payload.get("feature") or "").strip().lower()
    if feature not in _COURSE_DAILY_GATE_FEATURES:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_feature"})
    ref_raw = payload.get("ref")
    ref = str(ref_raw).strip()[:48] if ref_raw else None

    async with async_session_maker() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            return JSONResponse(status_code=403, content={"ok": False, "error": "access_start_first"})
        access = CourseMiniAppAccessService(session)
        # AI bo'lim emas — reklama cheksiz, slot band qilinmaydi.
        if feature not in COURSE_AI_PRACTICE_FEATURES:
            is_paid = access.is_paid_user(user)
            return JSONResponse(content={"ok": True, "allowed": True, "is_paid": is_paid, "remaining": None})
        # AI bo'lim — reklama ham kuniga 2 marta.
        result = await access.consume_daily_use(user, feature_key=f"{feature}_ad", ref=ref)
        await session.commit()
        if not result.get("allowed"):
            # Reklama-ruxsati ham tugadi — endi faqat obuna (ertaga yana ochiladi).
            return JSONResponse(
                status_code=403,
                content={
                    "ok": False,
                    "error": result.get("error") or "free_feature_limit_reached",
                    "is_paid": bool(result.get("is_paid", False)),
                },
            )
        return JSONResponse(
            content={
                "ok": True,
                "allowed": True,
                "is_paid": bool(result.get("is_paid", False)),
                "remaining": result.get("remaining"),
            }
        )


@app.post("/api/v3/lesson/unlock")
async def v3_course_lesson_unlock(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    telegram_id = extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN) if init_data else None
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})

    try:
        payload = await request.json()
        lesson_order = int(payload.get("lesson_id") or payload.get("lesson_order") or 0)
        score = int(payload.get("score") or 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_lesson_payload"})
    if lesson_order <= 0:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_lesson_payload"})

    async with async_session_maker() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            return JSONResponse(status_code=403, content={"ok": False, "error": "access_start_first"})

        resolved_level = _course_v3_user_level(user)
        lesson_repo = CourseLessonRepository(session)
        lesson = await lesson_repo.get_by_level_and_order(resolved_level, lesson_order)
        if not lesson:
            return JSONResponse(status_code=404, content={"ok": False, "error": "course_no_lesson_found"})

        access = CourseMiniAppAccessService(session)
        is_paid = access.is_paid_user(user)
        if not is_paid and CourseMiniAppAccessService.lesson_requires_premium(resolved_level, lesson_order):
            return JSONResponse(status_code=403, content={"ok": False, "error": "free_feature_limit_reached"})

        progress_repo = CourseProgressRepository(session)
        progress = await progress_repo.get_by_user_id(user.id, for_update=True)
        if not progress:
            progress = await progress_repo.create(
                user_id=user.id,
                level=resolved_level,
                current_lesson_id=lesson.id,
                current_step="intro",
                waiting_for="none",
            )
        progress.level = resolved_level
        progress.completed_lessons_count = max(
            int(getattr(progress, "completed_lessons_count", 0) or 0),
            lesson_order - 1,
        )
        await progress_repo.set_current_lesson_and_step(
            progress=progress,
            lesson_id=lesson.id,
            step="intro",
            waiting_for="none",
        )
        await progress_repo.set_homework_status(progress, "none")
        await CourseMiniAppAnalyticsService(session).record_server_event(
            event_name="test_completed",
            telegram_id=telegram_id,
            user_id=getattr(user, "id", None),
            source="course_v3_skip_test",
            level=resolved_level,
            lesson_id=getattr(lesson, "id", None),
            lesson_order=lesson_order,
            dedupe_key=f"course-v3:skip-test:{lesson.id}",
            payload={
                "score": max(0, min(100, score)),
                "unlock_completed_lessons_count": int(progress.completed_lessons_count or 0),
            },
        )
        await session.commit()
        return JSONResponse(
            content={
                "ok": True,
                "lesson_order": lesson_order,
                "completed_lessons_count": int(progress.completed_lessons_count or 0),
            }
        )


@app.post("/api/v3/lesson/complete")
async def v3_course_lesson_complete(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    telegram_id = extract_verified_webapp_user_id(init_data, settings.BOT_TOKEN) if init_data else None
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})

    try:
        payload = await request.json()
        lesson_order = int(payload.get("lesson_id") or payload.get("lesson_order") or 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_lesson_payload"})
    if lesson_order <= 0:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_lesson_payload"})

    async with async_session_maker() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return JSONResponse(status_code=403, content={"ok": False, "error": "access_start_first"})

        # Band yagona manbadan — user.level. Klient yuborgan level emas, server
        # foydalanuvchining haqiqiy bandiga ishonadi (QA rejim bilan bir xil).
        resolved_level = _course_v3_user_level(user)

        lesson_repo = CourseLessonRepository(session)
        lesson = await lesson_repo.get_by_level_and_order(resolved_level, lesson_order)
        if not lesson:
            return JSONResponse(status_code=404, content={"ok": False, "error": "course_no_lesson_found"})

        access = CourseMiniAppAccessService(session)
        is_paid = access.is_paid_user(user)
        # Darslarda reklama YO'Q. Bepul user faqat bepul trial doirasidagi
        # darsni (1-dars) yakunlay oladi; premium dars (2+) — obuna majburiy.
        # Bu serverdagi asosiy chegara: klient buzilgan bo'lsa ham aylanib
        # o'tib bo'lmaydi (frontend 2-darsni yarmida paywall bilan to'xtatadi).
        if not is_paid and CourseMiniAppAccessService.lesson_requires_premium(
            resolved_level, lesson_order
        ):
            return JSONResponse(status_code=403, content={"ok": False, "error": "free_feature_limit_reached"})

        progress_repo = CourseProgressRepository(session)
        progress = await progress_repo.get_by_user_id(user.id, for_update=True)
        if not progress:
            progress = await progress_repo.create(
                user_id=user.id,
                level=resolved_level,
                current_lesson_id=lesson.id,
                current_step="intro",
                waiting_for="none",
            )
        progress.level = resolved_level

        completed = int(getattr(progress, "completed_lessons_count", 0) or 0)
        gamification = CourseGamificationService(session)
        if lesson_order <= completed:
            snapshot = await gamification.snapshot(user)
            await session.commit()
            return JSONResponse(
                content={
                    "ok": True,
                    "duplicate": True,
                    "completed_lesson": lesson_order,
                    "completed_lessons_count": completed,
                    "gamification": snapshot,
                }
            )
        if lesson_order != completed + 1:
            return JSONResponse(status_code=403, content={"ok": False, "error": "course_lesson_not_unlocked"})

        await progress_repo.set_current_lesson_and_step(
            progress=progress,
            lesson_id=lesson.id,
            step="intro",
            waiting_for="none",
        )
        await progress_repo.mark_lesson_completed(progress)
        snapshot = await gamification.award(
            user,
            activity_type="lesson",
            activity_ref=f"v3-lesson:{lesson.id}:complete",
            base_xp=20,
            level=resolved_level,
        )

        next_lesson = await lesson_repo.get_next_lesson(resolved_level, lesson_order)
        if next_lesson is None:
            # Joriy band to'liq tugadi: keyingi HSK bandiga o'tamiz va user.level ni
            # yangilaymiz, shunda QA rejim ham yangi bandda bo'ladi (sinxron qoladi).
            # Progress keyingi map ochilganda yangi banddan noldan boshlanadi.
            next_band = _COURSE_V3_NEXT_BAND.get(resolved_level)
            if next_band:
                user.level = next_band
        next_requires_premium = CourseMiniAppAccessService.lesson_requires_premium(
            resolved_level,
            int(getattr(next_lesson, "lesson_order", 0) or 0) if next_lesson else None,
        )
        if next_lesson and (is_paid or not next_requires_premium):
            await progress_repo.set_current_lesson_and_step(
                progress=progress,
                lesson_id=next_lesson.id,
                step="intro",
                waiting_for="none",
            )
            await progress_repo.set_homework_status(progress, "none")
        else:
            await progress_repo.set_current_lesson_and_step(
                progress=progress,
                lesson_id=lesson.id,
                step="completed",
                waiting_for="none",
            )

        await CourseMiniAppAnalyticsService(session).record_server_event(
            event_name="lesson_completed",
            telegram_id=telegram_id,
            user_id=getattr(user, "id", None),
            source="course_v3",
            level=resolved_level,
            lesson_id=getattr(lesson, "id", None),
            lesson_order=lesson_order,
            dedupe_key=f"v3-lesson:{lesson.id}:completed",
            payload={
                "lesson_order": lesson_order,
                "is_paid": is_paid,
                "next_lesson": getattr(next_lesson, "lesson_order", None),
            },
        )
        await session.commit()
        return JSONResponse(
            content={
                "ok": True,
                "completed_lesson": lesson_order,
                "next_lesson": getattr(next_lesson, "lesson_order", None),
                "completed_lessons_count": int(getattr(progress, "completed_lessons_count", 0) or 0),
                "gamification": snapshot,
            }
        )


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


@app.post("/api/voice-practice/pronounce")
async def voice_practice_pronounce(request: Request):
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
            return await VoicePracticeService(session).score_pronunciation(
                telegram_id,
                target=str(form.get("target") or ""),
                target_pinyin=str(form.get("target_pinyin") or ""),
                audio_bytes=audio_bytes,
                filename=str(getattr(audio, "filename", None) or "voice.webm"),
                language=str(form.get("language") or ""),
                level=str(form.get("level") or ""),
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


@app.post("/api/admin-miniapp/overview")
async def admin_miniapp_overview(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    if not telegram_id:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "error": "invalid_telegram_init_data"},
        )
    if not _is_admin_id(telegram_id):
        return JSONResponse(
            status_code=403,
            content={"ok": False, "error": "admin_only"},
        )

    async with async_session_maker() as session:
        payload = await AdminMiniAppService(session).overview()
    return JSONResponse(content=payload)


@app.post("/api/admin-miniapp/finance-stats")
async def admin_miniapp_finance_stats(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    async with async_session_maker() as session:
        payload = await AdminFinanceStatsService(session).build()
    return JSONResponse(content=payload)


@app.post("/api/admin-miniapp/sub-entry-stats")
async def admin_miniapp_sub_entry_stats(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    async with async_session_maker() as session:
        rows = await SubscriptionEntryAnalyticsService(session).source_stats(week_ago=week_ago, limit=12)
    return JSONResponse(content={
        "ok": True,
        "rows": [
            {
                "source": r.source,
                "label": r.label,
                "total_all": r.total_all,
                "unique_all": r.unique_all,
                "total_week": r.total_week,
                "unique_week": r.unique_week,
            }
            for r in rows
        ],
    })


@app.post("/api/admin-miniapp/management")
async def admin_miniapp_management(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    async with async_session_maker() as session:
        payload = await _admin_miniapp_management_payload(session)
        await session.commit()
    return JSONResponse(content=payload)


@app.post("/api/admin-miniapp/users/search")
async def admin_miniapp_users_search(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    query = str(payload.get("query") or "").strip()
    async with async_session_maker() as session:
        repo = UserRepository(session)
        if query:
            users = await repo.search_by_identifier(query, limit=30)
        else:
            users = (await session.execute(
                select(User).order_by(User.last_active_at.desc()).limit(30)
            )).scalars().all()
    now = datetime.now(timezone.utc)
    return JSONResponse(content={"ok": True, "users": [_admin_user_card_payload(user, now=now) for user in users]})


@app.post("/api/admin-miniapp/users/detail")
async def admin_miniapp_user_detail(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
        target_id = int(payload.get("telegram_id") or 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_user_payload"})
    async with async_session_maker() as session:
        user = await UserRepository(session).get_by_telegram_id(target_id)
        if not user:
            return JSONResponse(status_code=404, content={"ok": False, "error": "user_not_found"})
        data = await _admin_user_payload(session, user)
    return JSONResponse(content=data)


@app.post("/api/admin-miniapp/payments/review")
async def admin_miniapp_payment_review(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
        payment_id = int(payload.get("payment_id") or 0)
        action = str(payload.get("action") or "").strip().lower()
        reason = str(payload.get("reason") or "").strip()
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_payment_payload"})
    if payment_id <= 0:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_payment_payload"})
    async with async_session_maker() as session:
        content, status = await _review_admin_payment(
            session,
            payment_id=payment_id,
            action=action,
            reason=reason,
        )
    return JSONResponse(status_code=status, content=content)


@app.post("/api/admin-miniapp/users/give-access")
async def admin_miniapp_user_give_access(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
        target_id = int(payload.get("telegram_id") or 0)
        plan = str(payload.get("plan") or "").strip()
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_access_payload"})
    if target_id <= 0 or plan not in PLANS:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_access_payload"})
    async with async_session_maker() as session:
        activated = await SubscriptionService(session).activate_plan(target_id, plan)
        if not activated:
            await session.rollback()
            return JSONResponse(status_code=404, content={"ok": False, "error": "user_or_plan_not_found"})
        await session.commit()
    return JSONResponse(content={"ok": True})


@app.post("/api/admin-miniapp/users/delete")
async def admin_miniapp_user_delete(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
        target_id = int(payload.get("telegram_id") or 0)
        confirm = str(payload.get("confirm") or "").strip()
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_delete_payload"})
    if target_id <= 0 or confirm != str(target_id):
        return JSONResponse(status_code=400, content={"ok": False, "error": "delete_confirmation_required"})
    async with async_session_maker() as session:
        deleted = await UserRepository(session).delete_by_telegram_id(target_id)
        await session.commit()
    if not deleted:
        return JSONResponse(status_code=404, content={"ok": False, "error": "user_not_found"})
    return JSONResponse(content={"ok": True})


@app.post("/api/admin-miniapp/users/block")
async def admin_miniapp_user_block(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
        target_id = int(payload.get("telegram_id") or 0)
        blocked = bool(payload.get("blocked"))
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_block_payload"})
    if target_id <= 0:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_block_payload"})
    if _is_admin_id(target_id):
        return JSONResponse(status_code=400, content={"ok": False, "error": "cannot_block_admin"})
    async with async_session_maker() as session:
        user = await UserRepository(session).set_blocked(target_id, blocked)
        if not user:
            await session.rollback()
            return JSONResponse(status_code=404, content={"ok": False, "error": "user_not_found"})
        await session.commit()
        status = user.status
    return JSONResponse(content={"ok": True, "status": status, "blocked": status == "blocked"})


@app.post("/api/admin-miniapp/prices/save")
async def admin_miniapp_prices_save(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
        method = str(payload.get("method") or "").strip()
        plan = str(payload.get("plan") or "").strip()
        amount = int(payload.get("amount") or 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_price_payload"})
    if method not in PAYMENT_METHODS or plan not in PLANS or amount <= 0 or amount > 1_000_000:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_price_payload"})
    async with async_session_maker() as session:
        price = await SubscriptionPriceService(session).set_price(
            payment_method=method,
            plan_type=plan,
            amount=amount,
            updated_by_telegram_id=telegram_id,
        )
        await session.commit()
    return JSONResponse(content={
        "ok": True,
        "price": {
            "method": price.payment_method,
            "plan": price.plan_type,
            "amount": price.amount,
            "currency": price.currency,
            "text": format_subscription_price(price.amount, price.currency),
        },
    })


@app.post("/api/admin-miniapp/prices/qr-upload")
async def admin_miniapp_prices_qr_upload(request: Request):
    form = await request.form()
    telegram_id = extract_verified_webapp_user_id(
        str(form.get("initData") or ""), settings.BOT_TOKEN
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})
    method = str(form.get("method") or "").strip()
    plan = str(form.get("plan") or "").strip()
    scope_kind = str(form.get("scope") or "main").strip()
    if not PaymentQrCodeService.is_qr_method(method) or plan not in PLANS:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_qr_target"})
    media = form.get("media")
    if media is None or not hasattr(media, "read"):
        return JSONResponse(status_code=400, content={"ok": False, "error": "empty_media"})
    content_type = str(getattr(media, "content_type", "") or "").lower()
    raw_name = str(getattr(media, "filename", "") or "").lower()
    if not (content_type.startswith("image") or raw_name.endswith((".jpg", ".jpeg", ".png", ".webp"))):
        return JSONResponse(status_code=400, content={"ok": False, "error": "unsupported_media"})
    data = await media.read(25 * 1024 * 1024 + 1)
    if len(data) > 25 * 1024 * 1024:
        return JSONResponse(status_code=400, content={"ok": False, "error": "media_too_large"})
    async with async_session_maker() as session:
        price = await SubscriptionPriceService(session).get_price(payment_method=method, plan_type=plan)
        amount = int(price.amount) if price else 0
        currency = price.currency if price else "¥"
        if amount <= 0:
            return JSONResponse(status_code=400, content={"ok": False, "error": "price_not_set"})
        if scope_kind == "discount20":
            scope = SUBSCRIPTION_DISCOUNT_20_QR_SCOPE
            amount = int(round(amount * 0.8))
        else:
            scope = SUBSCRIPTION_QR_SCOPE
        try:
            sent = await bot.send_photo(
                telegram_id,
                BufferedInputFile(data, "qr.jpg"),
                caption=f"📱 QR yuklandi · {PaymentQrCodeService.method_label(method)} · {plan} · {scope_kind}",
            )
            file_id = sent.photo[-1].file_id
        except Exception:
            return JSONResponse(status_code=400, content={"ok": False, "error": "qr_upload_failed"})
        await PaymentQrCodeService(session).save_qr_codes(
            [{
                "scope": scope,
                "payment_method": method,
                "plan_type": plan,
                "amount": amount,
                "currency": currency,
                "file_id": file_id,
            }],
            created_by_telegram_id=telegram_id,
        )
        await session.commit()
    return JSONResponse(content={"ok": True})


@app.post("/api/admin-miniapp/payment-details/save")
async def admin_miniapp_payment_details_save(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    text_value = str(payload.get("payment_details") or "").strip()
    if not text_value or len(text_value) > 1500:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_payment_details"})
    async with async_session_maker() as session:
        await BotSettingRepository(session).set(PAYMENT_DETAILS_KEY, text_value)
        await session.commit()
    return JSONResponse(content={"ok": True})


@app.post("/api/admin-miniapp/channels/save")
async def admin_miniapp_channels_save(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    action = str(payload.get("action") or "").strip()
    async with async_session_maker() as session:
        service = RequiredChannelService(session)
        if action == "mode":
            await service.set_enabled(bool(payload.get("enabled")))
        elif action == "add":
            raw_chat = str(payload.get("chat_id") or "").strip()
            title = str(payload.get("title") or "").strip()[:180]
            invite_link = str(payload.get("invite_link") or "").strip() or None
            if not raw_chat or not title:
                return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_channel_payload"})
            if raw_chat.startswith("-"):
                chat_id = raw_chat
            else:
                clean_chat = raw_chat.lstrip("@").strip("/")
                for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
                    if clean_chat.startswith(prefix):
                        clean_chat = clean_chat[len(prefix):]
                        break
                clean_chat = clean_chat.strip("/").split("/")[0]
                if not clean_chat:
                    return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_channel_payload"})
                chat_id = f"@{clean_chat}"
            await service.add_channel(
                chat_id=chat_id,
                title=title,
                invite_link=invite_link,
                created_by_telegram_id=telegram_id,
            )
        elif action == "toggle":
            channel_id = int(payload.get("channel_id") or 0)
            if channel_id <= 0 or not await service.set_channel_active(channel_id, bool(payload.get("active"))):
                return JSONResponse(status_code=404, content={"ok": False, "error": "channel_not_found"})
        elif action == "delete":
            channel_id = int(payload.get("channel_id") or 0)
            if channel_id <= 0 or not await service.delete_channel(channel_id):
                return JSONResponse(status_code=404, content={"ok": False, "error": "channel_not_found"})
        else:
            return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_channel_action"})
        await session.commit()
    return JSONResponse(content={"ok": True})


@app.post("/api/admin-miniapp/help/save")
async def admin_miniapp_help_save(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    target = str(payload.get("target") or "").strip()
    value = str(payload.get("value") or "").strip()
    async with async_session_maker() as session:
        if target == "admin_contact":
            normalized = normalize_admin_contact(value)
            if normalized and not admin_contact_url(normalized):
                return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_contact"})
            await BotSettingRepository(session).set(ADMIN_CONTACT_KEY, normalized)
        else:
            field_key = str(payload.get("key") or "").strip()
            lang = str(payload.get("lang") or "").strip()
            field = next((item for item in HELP_VIDEO_FIELDS if item.key == field_key), None)
            normalized = normalize_help_url(value)
            if not field or lang not in HELP_LANGS:
                return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_help_payload"})
            if value and not normalized:
                return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_help_url"})
            await BotSettingRepository(session).set(field.setting_key(lang), normalized)
        await session.commit()
    return JSONResponse(content={"ok": True})


@app.post("/api/admin-miniapp/portfolio/transaction")
async def admin_miniapp_portfolio_transaction(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
        transaction_type = str(payload.get("type") or "").strip()
        amount = float(payload.get("amount") or 0)
        currency = str(payload.get("currency") or "usd").strip()
        note = str(payload.get("note") or "").strip()
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_portfolio_payload"})
    if transaction_type not in {"profit", "expense"} or amount <= 0 or len(note) < 2:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_portfolio_payload"})
    async with async_session_maker() as session:
        transaction = await PortfolioService(session).add_manual_transaction(
            transaction_type=transaction_type,
            admin_telegram_id=telegram_id,
            amount=amount,
            currency=currency,
            note=note,
        )
        if not transaction:
            return JSONResponse(status_code=400, content={"ok": False, "error": "portfolio_save_failed"})
        await session.commit()
    return JSONResponse(content={"ok": True})


def _broadcast_validate_message(payload: dict) -> tuple[str, str, str | None] | JSONResponse:
    """(text, content_type, media_file_id) ni tekshiradi yoki xato qaytaradi."""
    text = str(payload.get("text") or "").strip()
    content_type = str(payload.get("content_type") or "text").strip()
    if content_type not in {"text", "photo", "video"}:
        content_type = "text"
    media_file_id = str(payload.get("media_file_id") or "").strip() or None
    if content_type in {"photo", "video"} and not media_file_id:
        content_type, media_file_id = "text", None
    has_media = bool(media_file_id)
    if not has_media and len(text) < 2:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_broadcast_text"})
    max_len = 1024 if has_media else 3500
    if len(text) > max_len:
        return JSONResponse(status_code=400, content={"ok": False, "error": "broadcast_text_too_long"})
    return text, content_type, media_file_id


@app.post("/api/admin-miniapp/broadcast/upload-media")
async def admin_miniapp_broadcast_upload_media(request: Request):
    form = await request.form()
    telegram_id = extract_verified_webapp_user_id(
        str(form.get("initData") or ""), settings.BOT_TOKEN
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})
    media = form.get("media")
    if media is None or not hasattr(media, "read"):
        return JSONResponse(status_code=400, content={"ok": False, "error": "empty_media"})
    raw_name = str(getattr(media, "filename", "") or "").lower()
    content_type = str(getattr(media, "content_type", "") or "").lower()
    if content_type.startswith("video") or raw_name.endswith((".mp4", ".mov", ".webm")):
        kind, fname = "video", "broadcast.mp4"
    elif content_type.startswith("image") or raw_name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        kind, fname = "photo", "broadcast.jpg"
    else:
        return JSONResponse(status_code=400, content={"ok": False, "error": "unsupported_media"})
    data = await media.read(25 * 1024 * 1024 + 1)
    if len(data) > 25 * 1024 * 1024:
        return JSONResponse(status_code=400, content={"ok": False, "error": "media_too_large"})
    try:
        sent = (
            await bot.send_video(telegram_id, BufferedInputFile(data, fname), caption="📤 Broadcast media tayyor (preview)")
            if kind == "video"
            else await bot.send_photo(telegram_id, BufferedInputFile(data, fname), caption="📤 Broadcast media tayyor (preview)")
        )
        file_id = sent.video.file_id if kind == "video" else sent.photo[-1].file_id
    except Exception:
        return JSONResponse(status_code=400, content={"ok": False, "error": "media_upload_failed"})
    return JSONResponse(content={"ok": True, "content_type": kind, "media_file_id": file_id})


@app.post("/api/admin-miniapp/broadcast/count")
async def admin_miniapp_broadcast_count(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    filters = parse_broadcast_filters(payload)
    admin_ids = set(settings.admin_id_list)
    async with async_session_maker() as session:
        service = AdminBroadcastService(bot, session)
        users = await service.target_users(filters)
        count = service.deliverable_count(users, admin_ids)
    return JSONResponse(content={"ok": True, "count": count, "total": len(users)})


@app.post("/api/admin-miniapp/broadcast/test")
async def admin_miniapp_broadcast_test(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    checked = _broadcast_validate_message(payload)
    if isinstance(checked, JSONResponse):
        return checked
    text, content_type, media_file_id = checked
    filters = parse_broadcast_filters(payload)
    button_config = parse_button_config(payload.get("button"))
    translate = bool(payload.get("translate"))
    async with async_session_maker() as session:
        service = AdminBroadcastService(bot, session)
        try:
            await service.send_test(
                telegram_id,
                text=text,
                content_type=content_type,
                media_file_id=media_file_id,
                button_config=button_config,
                translate=translate,
                languages=filters.get("languages"),
            )
        except Exception as exc:
            return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)[:120]})
    return JSONResponse(content={"ok": True})


@app.post("/api/admin-miniapp/broadcast/send")
async def admin_miniapp_broadcast_send(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    checked = _broadcast_validate_message(payload)
    if isinstance(checked, JSONResponse):
        return checked
    text, content_type, media_file_id = checked
    filters = parse_broadcast_filters(payload)
    button_config = parse_button_config(payload.get("button"))
    translate = bool(payload.get("translate"))
    admin_ids = set(settings.admin_id_list)
    async with async_session_maker() as session:
        service = AdminBroadcastService(bot, session)
        users = await service.target_users(filters)
        sent, failed, blocked = await service.deliver(
            users,
            admin_ids=admin_ids,
            text=text,
            content_type=content_type,
            media_file_id=media_file_id,
            button_config=button_config,
            translate=translate,
        )
    return JSONResponse(content={"ok": True, "sent": sent, "failed": failed, "blocked": blocked})


@app.post("/api/admin-miniapp/campaigns/create")
async def admin_miniapp_campaign_create(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    kind = str(payload.get("kind") or "").strip()
    title = str(payload.get("title") or "").strip()[:120]
    text = str(payload.get("text") or "").strip()
    hours = max(1, min(int(payload.get("hours") or 24), 24 * 30))
    filters = parse_broadcast_filters(payload)
    content_type = str(payload.get("content_type") or "text").strip()
    if content_type not in {"text", "photo", "video"}:
        content_type = "text"
    media_file_id = str(payload.get("media_file_id") or "").strip() or None
    if content_type in {"photo", "video"} and not media_file_id:
        content_type, media_file_id = "text", None
    has_media = bool(media_file_id)
    max_text = 1024 if has_media else 3500
    if not title or len(text) > max_text or (len(text) < 2 and not has_media):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_campaign_payload"})
    now = datetime.now(timezone.utc)
    async with async_session_maker() as session:
        if kind == "ad":
            button_config = encode_promo_button_config(parse_button_config(payload.get("button")))
            rounds = max(1, min(int(payload.get("rounds") or 1), 10))
            await AdCampaignRepository(session).create(
                title=title,
                message_text=text or None,
                content_type=content_type,
                media_file_id=media_file_id,
                starts_at=now,
                ends_at=now + timedelta(hours=hours),
                send_count_total=rounds,
                target_languages=filters.get("languages"),
                include_active_subscribers=bool(payload.get("include_active_subscribers")),
                button_config=button_config,
                created_by_telegram_id=telegram_id,
            )
        elif kind == "release_feedback":
            await ReleaseFeedbackRepository(session).create_campaign(
                title=title,
                message_text=text,
                content_type=content_type,
                media_file_id=media_file_id,
                send_at=now,
                feature_key=str(payload.get("feature_key") or "general").strip()[:32] or "general",
                created_by_telegram_id=telegram_id,
            )
        elif kind == "discount":
            percent = max(1, min(int(payload.get("percent") or 20), 90))
            languages = filters.get("languages") or []
            quota_raw = int(payload.get("quota_total") or 0)
            await DiscountCampaignRepository(session).create(
                title=title,
                reason=text[:500],
                percent=percent,
                starts_at=now,
                ends_at=now + timedelta(hours=hours),
                audience_status=filters.get("status"),
                audience_language=languages[0] if languages else None,
                audience_level=filters.get("level"),
                payment_method=filters.get("payment_method"),
                plan_type=filters.get("plan"),
                quota_total=quota_raw if quota_raw > 0 else None,
                created_by_telegram_id=telegram_id,
            )
        else:
            return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_campaign_kind"})
        await session.commit()
    return JSONResponse(content={"ok": True})


@app.post("/api/admin-miniapp/partners/action")
async def admin_miniapp_partners_action(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
        partner_id = int(payload.get("partner_id") or 0)
        action = str(payload.get("action") or "").strip()
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_partner_payload"})
    async with async_session_maker() as session:
        service = PartnerService(session)
        partner = await service.repo.get_by_id(partner_id)
        if not partner:
            return JSONResponse(status_code=404, content={"ok": False, "error": "partner_not_found"})
        if action == "approve":
            await service.approve(partner, telegram_id)
            with contextlib.suppress(Exception):
                await service.notify_partner(bot, partner, "partner_approved_notification")
        elif action == "reject":
            await service.repo.set_status(partner, "rejected", telegram_id)
        elif action == "block":
            await service.block(partner, telegram_id)
        elif action == "unblock":
            await service.unblock(partner, telegram_id)
        else:
            return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_partner_action"})
        await session.commit()
    return JSONResponse(content={"ok": True})


@app.post("/api/admin-miniapp/audio/list")
async def admin_miniapp_audio_list(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    auth_error = _admin_auth_error(telegram_id)
    if auth_error:
        return auth_error
    try:
        payload = await request.json()
        level = str(payload.get("level") or "hsk1").strip().lower()
        lesson_order = int(payload.get("lesson_order") or 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_audio_payload"})
    if level not in {"hsk1", "hsk2", "hsk3", "hsk4"} or lesson_order <= 0:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_audio_payload"})
    async with async_session_maker() as session:
        rows = await CourseAudioRepository(session).list_for_lesson(level, lesson_order)
    return JSONResponse(content={
        "ok": True,
        "items": [
            {"audio_type": item.audio_type, "file_id": item.file_id}
            for item in rows
        ],
    })


@app.post("/api/admin-miniapp/open-section")
async def admin_miniapp_open_section(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    if not telegram_id:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "error": "invalid_telegram_init_data"},
        )
    if not _is_admin_id(telegram_id):
        return JSONResponse(
            status_code=403,
            content={"ok": False, "error": "admin_only"},
        )

    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    section = str(payload.get("section") or "stats").strip()
    title, _ = ADMIN_MINIAPP_SECTIONS.get(section, ADMIN_MINIAPP_SECTIONS["stats"])
    return {"ok": True, "section": section, "title": title, "deprecated": True}


@app.post("/api/admin-miniapp/notifications")
async def admin_miniapp_notifications(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})
    async with async_session_maker() as session:
        items = await NotificationTemplateService(session).list_for_admin()
    return JSONResponse(content={"ok": True, "items": items})


@app.post("/api/admin-miniapp/notifications/save")
async def admin_miniapp_notifications_save(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    key = str(payload.get("key") or "").strip()
    if key not in MOTIVATION_KEYS:
        return JSONResponse(status_code=400, content={"ok": False, "error": "unknown_key"})
    async with async_session_maker() as session:
        await NotificationTemplateService(session).update_text(
            key,
            text_uz=str(payload.get("text_uz") or ""),
            text_ru=str(payload.get("text_ru") or ""),
            text_tj=str(payload.get("text_tj") or ""),
            enabled=bool(payload.get("enabled", True)),
            updated_by=telegram_id,
        )
        await session.commit()
    return JSONResponse(content={"ok": True})


@app.post("/api/admin-miniapp/notifications/media")
async def admin_miniapp_notifications_media(request: Request):
    form = await request.form()
    telegram_id = extract_verified_webapp_user_id(
        str(form.get("initData") or ""), settings.BOT_TOKEN
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})
    key = str(form.get("key") or "").strip()
    if key not in MOTIVATION_KEYS:
        return JSONResponse(status_code=400, content={"ok": False, "error": "unknown_key"})
    media = form.get("media")
    if media is None or not hasattr(media, "read"):
        return JSONResponse(status_code=400, content={"ok": False, "error": "empty_media"})
    raw_name = str(getattr(media, "filename", "") or "").lower()
    content_type = str(getattr(media, "content_type", "") or "").lower()
    if content_type.startswith("video") or raw_name.endswith((".mp4", ".mov", ".webm")):
        media_type, ext = "video", ".mp4"
    elif content_type.startswith("image") or raw_name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        media_type, ext = "photo", ".jpg"
    else:
        return JSONResponse(status_code=400, content={"ok": False, "error": "unsupported_media"})
    data = await media.read(25 * 1024 * 1024 + 1)
    if len(data) > 25 * 1024 * 1024:
        return JSONResponse(status_code=400, content={"ok": False, "error": "media_too_large"})
    os.makedirs(NOTIFICATION_MEDIA_ROOT, exist_ok=True)
    filename = f"{key}_{int(time.time())}{ext}"
    with open(os.path.join(NOTIFICATION_MEDIA_ROOT, filename), "wb") as handle:
        handle.write(data)
    async with async_session_maker() as session:
        service = NotificationTemplateService(session)
        old = await service._get_row(key)
        old_path = old.media_path if old else None
        await service.set_media(key, media_type=media_type, media_path=filename)
        await session.commit()
    if old_path and old_path != filename:
        with contextlib.suppress(OSError):
            os.remove(os.path.join(NOTIFICATION_MEDIA_ROOT, old_path))
    return JSONResponse(content={"ok": True, "media_type": media_type, "media_url": f"/uploads/notifications/{filename}"})


@app.post("/api/admin-miniapp/notifications/media/clear")
async def admin_miniapp_notifications_media_clear(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    key = str(payload.get("key") or "").strip()
    if key not in MOTIVATION_KEYS:
        return JSONResponse(status_code=400, content={"ok": False, "error": "unknown_key"})
    async with async_session_maker() as session:
        service = NotificationTemplateService(session)
        old = await service._get_row(key)
        old_path = old.media_path if old else None
        await service.clear_media(key)
        await session.commit()
    if old_path:
        with contextlib.suppress(OSError):
            os.remove(os.path.join(NOTIFICATION_MEDIA_ROOT, old_path))
    return JSONResponse(content={"ok": True})


@app.get("/uploads/notifications/{filename}")
async def serve_notification_media(filename: str):
    safe = os.path.basename(filename)
    path = os.path.join(NOTIFICATION_MEDIA_ROOT, safe)
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"ok": False, "error": "not_found"})
    return FileResponse(path)


@app.post("/api/admin-miniapp/course-ads")
async def admin_miniapp_course_ads(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})
    async with async_session_maker() as session:
        service = CourseAdService(session)
        items = await service.list_for_admin()
        if service.media_backup_changed:
            await session.commit()
    return JSONResponse(content={"ok": True, "items": items})


@app.post("/api/admin-miniapp/course-ads/upload")
async def admin_miniapp_course_ads_upload(request: Request):
    form = await request.form()
    telegram_id = extract_verified_webapp_user_id(
        str(form.get("initData") or ""), settings.BOT_TOKEN
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})

    media = form.get("media")
    if media is None or not hasattr(media, "read"):
        return JSONResponse(status_code=400, content={"ok": False, "error": "empty_media"})

    raw_name = str(getattr(media, "filename", "") or "").lower()
    content_type = str(getattr(media, "content_type", "") or "").lower()
    _, raw_ext = os.path.splitext(raw_name)
    if raw_ext not in COURSE_AD_ALLOWED_VIDEO_EXTENSIONS:
        raw_ext = ".mp4"
    if not (content_type.startswith("video") or raw_name.endswith(tuple(COURSE_AD_ALLOWED_VIDEO_EXTENSIONS))):
        return JSONResponse(status_code=400, content={"ok": False, "error": "unsupported_media"})

    data = await media.read(COURSE_AD_MAX_UPLOAD_BYTES + 1)
    if len(data) > COURSE_AD_MAX_UPLOAD_BYTES:
        return JSONResponse(status_code=400, content={"ok": False, "error": "media_too_large"})

    try:
        filename = await asyncio.to_thread(
            _prepare_course_ad_video_file,
            data,
            raw_ext=raw_ext,
            telegram_id=telegram_id,
        )
        media_backup = await asyncio.to_thread(CourseAdService.read_media_file, filename)
    except CourseAdVideoError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except OSError:
        return JSONResponse(status_code=400, content={"ok": False, "error": "media_upload_failed"})

    title = str(form.get("title") or "Course ad").strip()[:120] or "Course ad"
    duration_seconds = CourseAdService.normalize_duration(form.get("duration_seconds"))
    link_url = CourseAdService.normalize_link(form.get("link_url"))
    language = CourseAdService.normalize_language(form.get("language"))
    async with async_session_maker() as session:
        ad = await CourseAdService(session).create_video(
            title=title,
            media_path=filename,
            duration_seconds=duration_seconds,
            link_url=link_url,
            language=language,
            media_blob=media_backup,
            created_by_telegram_id=telegram_id,
        )
        await session.commit()
        payload = CourseAdService.payload(ad)
    return JSONResponse(content={"ok": True, "ad": payload})


@app.post("/api/admin-miniapp/course-ads/toggle")
async def admin_miniapp_course_ads_toggle(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})
    try:
        payload = await request.json()
        ad_id = int(payload.get("ad_id") or 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_course_ad_payload"})
    if ad_id <= 0:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_course_ad_payload"})

    async with async_session_maker() as session:
        ad = await CourseAdService(session).set_active(ad_id, bool(payload.get("is_active", True)))
        if not ad:
            return JSONResponse(status_code=404, content={"ok": False, "error": "course_ad_not_found"})
        await session.commit()
        item = CourseAdService.payload(ad)
    return JSONResponse(content={"ok": True, "ad": item})


@app.post("/api/admin-miniapp/course-ads/delete")
async def admin_miniapp_course_ads_delete(request: Request):
    telegram_id = _admin_miniapp_user_id(request)
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    if not _is_admin_id(telegram_id):
        return JSONResponse(status_code=403, content={"ok": False, "error": "admin_only"})
    try:
        payload = await request.json()
        ad_id = int(payload.get("ad_id") or 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_course_ad_payload"})
    if ad_id <= 0:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_course_ad_payload"})

    async with async_session_maker() as session:
        media_path = await CourseAdService(session).delete(ad_id)
        if media_path is None:
            return JSONResponse(status_code=404, content={"ok": False, "error": "course_ad_not_found"})
        await session.commit()

    # Diskdan media faylni ham o'chiramiz (DB o'chgandan keyin, xatoga chidamli).
    try:
        safe = os.path.basename(media_path)
        file_path = os.path.join(COURSE_AD_MEDIA_ROOT, safe)
        if safe and os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass

    return JSONResponse(content={"ok": True, "deleted_id": ad_id})


@app.get("/uploads/course_ads/{filename}")
async def serve_course_ad_media(filename: str):
    safe = os.path.basename(filename)
    path = os.path.join(COURSE_AD_MEDIA_ROOT, safe)
    if not os.path.exists(path):
        async with async_session_maker() as session:
            result = await session.execute(
                select(CourseAdCreative).where(CourseAdCreative.media_path == safe)
            )
            ad = result.scalar_one_or_none()
            if not ad or not CourseAdService.media_available(ad):
                return JSONResponse(status_code=404, content={"ok": False, "error": "not_found"})
    ext = os.path.splitext(safe.lower())[1]
    media_type = {
        ".mp4": "video/mp4",
        ".m4v": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
    }.get(ext, "application/octet-stream")
    return FileResponse(path, media_type=media_type, headers={"Accept-Ranges": "bytes"})


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
    section: str | None = None,
    completed_sections: str | None = None,
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
            section_key=section,
            client_completed_sections=completed_sections,
        )
    status_code = 200 if result.get("ok") else 403
    return JSONResponse(status_code=status_code, content=result)


@app.get("/api/miniapp/course-section-plan")
async def miniapp_course_section_plan(
    request: Request,
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
        result = await CourseMiniAppLessonFlowService(session).get_section_plan(
            telegram_id,
            level=level,
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
            section_key=payload.get("section_key") or payload.get("section"),
            client_completed_sections=payload.get("client_completed_sections") or payload.get("completed_sections"),
        )
    status_code = 200 if result.get("ok") else 400
    return JSONResponse(status_code=status_code, content=result)


@app.post("/api/miniapp/course-lesson/jump")
async def miniapp_course_lesson_jump(request: Request):
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
        lesson_order = int(payload.get("lesson_id") or payload.get("lesson") or 0)
        percent = int(payload.get("percent") or 0)
        score = int(payload.get("score") or 0)
        total = int(payload.get("total") or 0)
    except (TypeError, ValueError):
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "invalid_lesson_jump_payload"},
        )
    async with async_session_maker() as session:
        result = await CourseMiniAppLessonFlowService(session).jump_to_lesson(
            telegram_id,
            level=str(payload.get("level") or ""),
            lesson_order=lesson_order,
            section_key=payload.get("section_key") or payload.get("section"),
            percent=percent,
            score=score,
            total=total,
            passed=bool(payload.get("passed")),
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
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(status_code=403, content={"ok": False, "error": "access_start_first"})
            result = await CourseMiniAppPracticeService(session).start(
                telegram_id,
                mode=str(payload.get("mode") or ""),
                level=_course_v3_user_level(user),
                lang=_course_v3_user_lang(user),
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
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(status_code=403, content={"ok": False, "error": "access_start_first"})
            result = await CourseMiniAppPracticeService(session).complete(
                telegram_id,
                session_id=str(payload.get("session_id") or ""),
                mode=str(payload.get("mode") or ""),
                level=_course_v3_user_level(user),
                lang=_course_v3_user_lang(user),
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
        tz_raw = request.query_params.get("tz")
        tz_offset = None
        if tz_raw is not None:
            try:
                tz_offset = int(tz_raw)
            except (TypeError, ValueError):
                tz_offset = None
        result = await CourseGamificationService(session).leaderboard(
            user, timezone_offset_minutes=tz_offset
        )
        await session.commit()
    return {"ok": True, **result}


@app.post("/api/miniapp/reward-chest/open")
async def miniapp_reward_chest_open(request: Request):
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
        result = await CourseGamificationService(session).open_reward_chest(user)
        await session.commit()
    return JSONResponse(status_code=200 if result.get("ok") else 400, content=result)


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


@app.get("/api/miniapp/challenges")
async def miniapp_challenges(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    async with async_session_maker() as session:
        result = await CourseChallengeService(session).list_for_user(telegram_id)
    return JSONResponse(status_code=200 if result.get("ok") else 404, content=result)


@app.post("/api/miniapp/challenges")
async def miniapp_challenge_create(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_challenge_payload"})
    opponent_telegram_id = _positive_int(payload.get("opponent_telegram_id"))
    if not opponent_telegram_id:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_challenge_opponent"})
    async with async_session_maker() as session:
        result = await CourseChallengeService(session).create(
            telegram_id,
            opponent_telegram_id=opponent_telegram_id,
            level=str(payload.get("level") or ""),
            lang=str(payload.get("lang") or ""),
            bot=bot,
        )
        await session.commit()
    return JSONResponse(status_code=200 if result.get("ok") else 400, content=result)


@app.post("/api/miniapp/challenges/{challenge_id}/respond")
async def miniapp_challenge_respond(challenge_id: int, request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    async with async_session_maker() as session:
        result = await CourseChallengeService(session).respond(
            telegram_id,
            int(challenge_id),
            str(payload.get("action") or ""),
            bot=bot,
        )
        await session.commit()
    return JSONResponse(status_code=200 if result.get("ok") else 400, content=result)


@app.post("/api/miniapp/challenges/{challenge_id}/start")
async def miniapp_challenge_start(challenge_id: int, request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    async with async_session_maker() as session:
        result = await CourseChallengeService(session).start(telegram_id, int(challenge_id))
        await session.commit()
    return JSONResponse(status_code=200 if result.get("ok") else 400, content=result)


@app.post("/api/miniapp/challenges/{challenge_id}/submit")
async def miniapp_challenge_submit(challenge_id: int, request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_challenge_payload"})
    async with async_session_maker() as session:
        result = await CourseChallengeService(session).submit(
            telegram_id,
            int(challenge_id),
            payload.get("answers") if isinstance(payload.get("answers"), list) else [],
            duration_seconds=_positive_int(payload.get("duration_seconds")) or 0,
            bot=bot,
        )
        await session.commit()
    return JSONResponse(status_code=200 if result.get("ok") else 400, content=result)


@app.post("/api/miniapp/mistakes/review/start")
async def miniapp_mistake_review_start(request: Request):
    telegram_id = extract_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        settings.BOT_TOKEN,
    )
    if not telegram_id:
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    ad_supported = bool(payload.get("ad_supported")) if isinstance(payload, dict) else False
    async with async_session_maker() as session:
        result = await CourseMistakeService(session).start_review(telegram_id, ad_supported=ad_supported)
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
            source = str(payload.get("source") or payload.get("mode") or "subscription_miniapp")
            await SubscriptionEntryAnalyticsService(session).record_entry(
                telegram_id=telegram_id,
                user=user,
                source=source,
                mode=str(payload.get("mode") or ""),
                plan_type=str(payload.get("plan") or "") or None,
                payment_method=str(payload.get("method") or "") or None,
                campaign_id=_positive_int(payload.get("campaign_id")),
                feedback_id=_positive_int(payload.get("feedback_id")),
            )
            await SubscriptionChurnService(session).mark_subscription_miniapp_opened(telegram_id, source)
            await ConversionFunnelService().record(
                event_name="checkout_opened",
                user=user,
                telegram_id=telegram_id,
                source=source,
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
                source=str(payload.get("source") or "course_miniapp"),
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
                    await _send_subscription_expired_offer(session, telegram_id)
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
                        await _send_subscription_expired_offer(session, telegram_id)
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
