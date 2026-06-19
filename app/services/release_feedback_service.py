import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from app.bot.keyboards.release_feedback import (
    release_feedback_discount_keyboard,
    release_feedback_rating_keyboard,
)
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackResponse
from app.repositories.discount_campaign_repo import DiscountCampaignRepository
from app.repositories.release_feedback_repo import ReleaseFeedbackRepository, decode_languages
from app.repositories.user_repo import UserRepository
from app.services.ai_usage_budget_service import AIUsageBudgetService, RELEASE_FEEDBACK_TRIAL_PLAN_TYPE
from app.services.broadcast_translation_service import localized_broadcast_text_for_language
from app.config import settings


_PROMPT_TEXTS = {
    "uz": (
        "\n\nYangilikni sinab ko'ring va 1-5 ball bering. "
        "Fikr qoldirsangiz, obunangiz bo'lmasa sizga 24 soatlik 20% chegirma beriladi."
    ),
    "ru": (
        "\n\nПопробуйте обновление и оцените от 1 до 5. "
        "Если оставите отзыв и у вас нет подписки, вам откроется скидка 20% на 24 часа."
    ),
    "tj": (
        "\n\nНавигариро санҷед ва аз 1 то 5 баҳо диҳед. "
        "Агар фикр гузоред ва обуна надошта бошед, барои шумо тахфифи 20% ба 24 соат кушода мешавад."
    ),
}

_LOW_RATING_COMMENT_TEXTS = {
    "uz": "Nima noqulay bo'ldi? Qisqa izoh yoki screenshot yuboring. Shundan keyin chegirma ochiladi.",
    "ru": "Что было неудобно? Отправьте короткий комментарий или скриншот. После этого скидка откроется.",
    "tj": "Чӣ ноқулай буд? Шарҳи кӯтоҳ ё скриншот фиристед. Баъд аз ин тахфиф кушода мешавад.",
}

_OPTIONAL_COMMENT_TEXTS = {
    "uz": "Rahmat. Xohlasangiz, qisqa izoh ham qoldiring.",
    "ru": "Спасибо. Если хотите, оставьте короткий комментарий.",
    "tj": "Ташаккур. Агар хоҳед, шарҳи кӯтоҳ ҳам гузоред.",
}

_THANKS_TEXTS = {
    "uz": "Rahmat, fikringiz qabul qilindi.",
    "ru": "Спасибо, ваш отзыв принят.",
    "tj": "Ташаккур, фикри шумо қабул шуд.",
}

_DISCOUNT_TEXTS = {
    "uz": "Rahmat. Aytganimizdek, sizga 24 soatlik 20% chegirma berildi.",
    "ru": "Спасибо. Как и обещали, для вас открыта скидка 20% на 24 часа.",
    "tj": "Ташаккур. Тавре гуфта будем, барои шумо тахфифи 20% ба 24 соат дода шуд.",
}

_TRY_GRANTED_TEXTS = {
    "uz": "Test access ochildi: 24 soat ichida yangilangan joyni 1-2 marta sinab ko'ring.",
    "ru": "Тестовый доступ открыт: в течение 24 часов попробуйте обновлённый раздел 1-2 раза.",
    "tj": "Дастрасии тестӣ кушода шуд: дар 24 соат қисми навшударо 1-2 маротиба санҷед.",
}

_TRY_ALREADY_TEXTS = {
    "uz": "Sizda bu funksiyani sinab ko'rish uchun access bor.",
    "ru": "У вас уже есть доступ, чтобы попробовать эту функцию.",
    "tj": "Шумо аллакай барои санҷидани ин функсия дастрасӣ доред.",
}

RELEASE_FEEDBACK_TRIAL_BUDGET_USD = 0.03


@dataclass(frozen=True)
class ReleaseFeedbackSendResult:
    campaign_id: int
    total: int
    sent: int
    failed: int


def release_feedback_prompt(lang: str | None) -> str:
    return _PROMPT_TEXTS.get(lang or "ru", _PROMPT_TEXTS["ru"])


def release_feedback_low_rating_comment_text(lang: str | None) -> str:
    return _LOW_RATING_COMMENT_TEXTS.get(lang or "ru", _LOW_RATING_COMMENT_TEXTS["ru"])


def release_feedback_optional_comment_text(lang: str | None) -> str:
    return _OPTIONAL_COMMENT_TEXTS.get(lang or "ru", _OPTIONAL_COMMENT_TEXTS["ru"])


def release_feedback_thanks_text(lang: str | None) -> str:
    return _THANKS_TEXTS.get(lang or "ru", _THANKS_TEXTS["ru"])


def release_feedback_discount_text(lang: str | None) -> str:
    return _DISCOUNT_TEXTS.get(lang or "ru", _DISCOUNT_TEXTS["ru"])


def release_feedback_try_granted_text(lang: str | None) -> str:
    return _TRY_GRANTED_TEXTS.get(lang or "ru", _TRY_GRANTED_TEXTS["ru"])


def release_feedback_try_already_text(lang: str | None) -> str:
    return _TRY_ALREADY_TEXTS.get(lang or "ru", _TRY_ALREADY_TEXTS["ru"])


def _lang(value: str | None) -> str:
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
            if user.status != "blocked"
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
                    rating_markup=release_feedback_rating_keyboard(campaign.id),
                )
                sent_count += 1
            except Exception as exc:
                status = "failed"
                error = str(exc)
                failed_count += 1

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
        until = now + timedelta(minutes=int(campaign.trial_access_minutes or 1440))
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

        await AIUsageBudgetService(self.session).create_fixed_budget(
            telegram_id=user.telegram_id,
            plan_type=RELEASE_FEEDBACK_TRIAL_PLAN_TYPE,
            amount=0,
            currency="USD",
            total_budget_usd=RELEASE_FEEDBACK_TRIAL_BUDGET_USD,
            starts_at=now,
            ends_at=until,
        )

        await self.repo.mark_try_clicked(
            campaign_id=campaign.id,
            user_telegram_id=user.telegram_id,
            trial_granted_until=until,
        )
        await self.session.flush()
        return True, until
