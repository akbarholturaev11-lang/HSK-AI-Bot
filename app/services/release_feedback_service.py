import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from app.bot.keyboards.release_feedback import (
    release_feedback_rating_keyboard,
)
from app.bot.utils.i18n import t
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackResponse
from app.repositories.discount_campaign_repo import DiscountCampaignRepository
from app.repositories.release_feedback_repo import ReleaseFeedbackRepository, decode_languages
from app.repositories.user_repo import UserRepository
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.account_identity import actual_telegram_id
from app.services.broadcast_translation_service import localized_broadcast_text_for_language
from app.services.bot_block_status_service import BotBlockStatusService
from app.config import settings


@dataclass(frozen=True)
class ReleaseFeedbackSendResult:
    campaign_id: int
    total: int
    sent: int
    failed: int


def _release_feedback_text(key: str, lang: str | None) -> str:
    return t(f"common.bot.releaseFeedback.{key}", lang or "ru")


def release_feedback_prompt(lang: str | None) -> str:
    return _release_feedback_text("prompt", lang)


def release_feedback_low_rating_comment_text(lang: str | None) -> str:
    return _release_feedback_text("lowRatingComment", lang)


def release_feedback_optional_comment_text(lang: str | None) -> str:
    return _release_feedback_text("optionalComment", lang)


def release_feedback_thanks_text(lang: str | None) -> str:
    return _release_feedback_text("thanks", lang)


def release_feedback_discount_text(lang: str | None) -> str:
    return _release_feedback_text("discount", lang)


def release_feedback_try_granted_text(lang: str | None) -> str:
    return _release_feedback_text("tryGranted", lang)


def release_feedback_try_already_text(lang: str | None) -> str:
    return _release_feedback_text("tryAlready", lang)


def _lang(value: str | None) -> str:
    if value in {"tg", "tg-TJ"}:
        return "tj"
    return value if value in {"uz", "ru", "tj"} else "ru"


async def send_release_feedback_payload(
    bot: Bot,
    *,
    chat_id: int,
    text: str | None,
    content_type: str,
    media_file_id: str | None,
    language: str | None,
    rating_markup: InlineKeyboardMarkup,
) -> int | None:
    lang = _lang(language)
    base_text = localized_broadcast_text_for_language(text, lang)
    prompt = release_feedback_prompt(lang)
    max_length = 1024 if content_type in {"photo", "video"} else 4096
    text_with_prompt = f"{base_text}{prompt}" if base_text else prompt.strip()

    if len(text_with_prompt) <= max_length:
        if content_type == "photo" and media_file_id:
            msg = await bot.send_photo(
                chat_id=chat_id,
                photo=media_file_id,
                caption=text_with_prompt,
                reply_markup=rating_markup,
            )
        elif content_type == "video" and media_file_id:
            msg = await bot.send_video(
                chat_id=chat_id,
                video=media_file_id,
                caption=text_with_prompt,
                reply_markup=rating_markup,
            )
        else:
            msg = await bot.send_message(chat_id=chat_id, text=text_with_prompt, reply_markup=rating_markup)
        return msg.message_id

    if content_type == "photo" and media_file_id:
        await bot.send_photo(chat_id=chat_id, photo=media_file_id, caption=base_text or None)
    elif content_type == "video" and media_file_id:
        await bot.send_video(chat_id=chat_id, video=media_file_id, caption=base_text or None)
    else:
        await bot.send_message(chat_id=chat_id, text=base_text or "")

    msg = await bot.send_message(
        chat_id=chat_id,
        text=prompt.strip(),
        reply_markup=rating_markup,
    )
    return msg.message_id


class ReleaseFeedbackService:
    def __init__(self, session):
        self.session = session
        self.repo = ReleaseFeedbackRepository(session)
        self.user_repo = UserRepository(session)
        self.discount_repo = DiscountCampaignRepository(session)

    async def target_users(self, campaign: ReleaseFeedbackCampaign) -> list:
        users = await self.user_repo.get_filtered_users(
            languages=decode_languages(campaign.target_languages),
            status=campaign.status_filter,
            level=campaign.level_filter,
            learning_mode=campaign.mode_filter,
            payment_status=campaign.payment_status_filter,
            payment_method=campaign.payment_method_filter,
            selected_plan_type=campaign.plan_filter,
            discount_filter=campaign.discount_filter,
            course_promo_filter=campaign.course_promo_filter,
            activity_filter=campaign.activity_filter,
        )
        admin_ids = set(settings.admin_id_list)
        already_done = await self.repo.list_delivery_user_ids(campaign.id)
        return [
            user for user in users
            if actual_telegram_id(user) is not None
            and user.status != "blocked"
            and not BotBlockStatusService.is_bot_blocked(user)
            and user.telegram_id not in admin_ids
            and user.telegram_id not in already_done
        ]

    async def send_due_campaigns(self, bot: Bot) -> list[ReleaseFeedbackSendResult]:
        campaigns = await self.repo.list_due_campaigns()
        results = []
        for campaign in campaigns:
            results.append(await self._send_campaign(bot, campaign))
        if campaigns:
            await self.session.commit()
        return results

    async def _send_campaign(
        self,
        bot: Bot,
        campaign: ReleaseFeedbackCampaign,
    ) -> ReleaseFeedbackSendResult:
        await self.repo.mark_sending(campaign)
        await self.session.commit()

        users = await self.target_users(campaign)
        sent_count = 0
        failed_count = 0
        delivery_count = 0
        blocks = BotBlockStatusService(self.session)

        for user in users:
            status = "sent"
            error = None
            message_id = None
            try:
                message_id = await send_release_feedback_payload(
                    bot,
                    chat_id=user.telegram_id,
                    text=campaign.message_text,
                    content_type=campaign.content_type,
                    media_file_id=campaign.media_file_id,
                    language=user.language,
                    rating_markup=release_feedback_rating_keyboard(campaign.id, user.language or "ru"),
                )
                await blocks.handle_send_success(user, reason="release_feedback")
                sent_count += 1
            except Exception as exc:
                status = "failed"
                error = str(exc)
                failed_count += 1
                await blocks.handle_send_exception(
                    user.telegram_id,
                    exc,
                    reason="release_feedback",
                )

            await self.repo.create_delivery(
                campaign_id=campaign.id,
                user_telegram_id=user.telegram_id,
                status=status,
                message_id=message_id,
                error=error,
            )
            delivery_count += 1
            if delivery_count % 20 == 0:
                await self.session.commit()
            await asyncio.sleep(0.05)

        await self.repo.mark_sent(campaign, sent_count=sent_count, failed_count=failed_count)
        return ReleaseFeedbackSendResult(
            campaign_id=campaign.id,
            total=len(users),
            sent=sent_count,
            failed=failed_count,
        )

    async def create_discount_for_response(
        self,
        *,
        campaign: ReleaseFeedbackCampaign,
        response: ReleaseFeedbackResponse,
        user,
    ) -> int | None:
        if response.discount_campaign_id:
            return response.discount_campaign_id
        if not user or user.status == "blocked" or user.payment_status == "approved":
            return None

        now = datetime.now(timezone.utc)
        percent = int(campaign.discount_percent or 20)
        hours = int(campaign.discount_hours or 24)
        discount = await self.discount_repo.create(
            title=f"Release feedback #{campaign.id}",
            title_tj="Release feedback 20%",
            title_ru="Release feedback 20%",
            title_uz="Release feedback 20%",
            reason=f"Release feedback rating: {response.rating}/5",
            reason_tj="Баҳо барои навигарии бот",
            reason_ru="Оценка обновления бота",
            reason_uz="Bot yangiligi uchun baho",
            percent=percent,
            starts_at=now,
            ends_at=now + timedelta(hours=hours),
            target_telegram_id=user.telegram_id,
            quota_total=1,
            repeat_interval_days=None,
            notify_enabled=False,
            created_by_telegram_id=campaign.created_by_telegram_id,
        )
        await self.repo.attach_discount_campaign(response, discount.id)
        return discount.id

    async def grant_trial_access(
        self,
        *,
        campaign: ReleaseFeedbackCampaign,
        user,
    ) -> tuple[bool, datetime | None]:
        if not user or user.status == "blocked":
            await self.repo.mark_try_clicked(
                campaign_id=campaign.id,
                user_telegram_id=getattr(user, "telegram_id", 0) or 0,
            )
            return False, None

        if user.payment_status == "approved":
            await self.repo.mark_try_clicked(
                campaign_id=campaign.id,
                user_telegram_id=user.telegram_id,
            )
            return False, getattr(user, "end_date", None)

        now = datetime.now(timezone.utc)
        until = now + timedelta(minutes=int(campaign.trial_access_minutes or 30))
        current_end = getattr(user, "end_date", None)
        if current_end and current_end.tzinfo is None:
            current_end = current_end.replace(tzinfo=timezone.utc)
        if user.status == "active" and current_end and current_end > until:
            await self.repo.mark_try_clicked(
                campaign_id=campaign.id,
                user_telegram_id=user.telegram_id,
                trial_granted_until=current_end,
            )
            return False, current_end

        if user.status != "active":
            user.start_date = now
        user.status = "active"
        user.end_date = until
        user.questions_used = 0
        user.last_limit_reset_at = now
        user.expiry_reminder_sent_at = None
        user.selected_plan_type = None
        user.pending_checkout_msg_id = None

        await AIUsageBudgetService(self.session).expire_active_budgets(user.telegram_id)

        await self.repo.mark_try_clicked(
            campaign_id=campaign.id,
            user_telegram_id=user.telegram_id,
            trial_granted_until=until,
        )
        await self.session.flush()
        return True, until
