from pathlib import Path

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.repositories.payment_repo import PaymentRepository
from app.repositories.bot_feedback_repo import BotFeedbackRepository
from app.repositories.user_repo import UserRepository
from app.services.discount_service import DiscountService
from app.services.payment_qr_code_service import PaymentQrCodeService
from app.services.payment_service import PaymentService
from app.services.subscription_currency_service import (
    format_subscription_price,
)
from app.services.subscription_price_service import SubscriptionPriceService
from app.bot.utils.i18n import t
from app.bot.keyboards.subscription import (
    subscription_miniapp_keyboard,
)


router = Router()
PAYMENT_METHODS = ("visa", "alipay", "wechat")
PLANS = ("10_days", "1_month")
_BOT_USERNAME_CACHE = None

# subscription.py → bot/handlers/ → bot/ → app/ → project root → app/static/payments/
_STATIC_PAYMENTS = Path(__file__).parent.parent.parent / "static" / "payments"

QR_PHOTO_PATHS = {
    "alipay_10_days":          str(_STATIC_PAYMENTS / "alipay_10_days.jpg"),
    "alipay_10_days_discount": str(_STATIC_PAYMENTS / "alipay_10_days_discount.jpg"),
    "alipay_1_month":          str(_STATIC_PAYMENTS / "alipay_1_month.jpg"),
    "alipay_1_month_discount": str(_STATIC_PAYMENTS / "alipay_1_month_discount.jpg"),
    "wechat_10_days":          str(_STATIC_PAYMENTS / "wechat_10_days.jpg"),
    "wechat_10_days_discount": str(_STATIC_PAYMENTS / "wechat_10_days_discount.jpg"),
    "wechat_1_month":          str(_STATIC_PAYMENTS / "wechat_1_month.jpg"),
    "wechat_1_month_discount": str(_STATIC_PAYMENTS / "wechat_1_month_discount.jpg"),
    "alipay_admin_discount":    str(_STATIC_PAYMENTS / "alipay_admin_discount.jpg"),
    "wechat_admin_discount":    str(_STATIC_PAYMENTS / "wechat_admin_discount.jpg"),
}




async def _uploaded_qr_file_id(session, user, plan: str, checkout_info: dict) -> str | None:
    payment_method = getattr(user, "payment_method", None)
    if not PaymentQrCodeService.is_qr_method(payment_method):
        return None

    scope = PaymentQrCodeService.checkout_scope(
        discount_source=checkout_info.get("discount_source") or "none",
        discount_percent=int(checkout_info.get("discount_percent") or 0),
        discount_campaign_id=checkout_info.get("discount_campaign_id"),
    )
    if not scope:
        return None

    return await PaymentQrCodeService(session).get_file_id(
        scope=scope,
        payment_method=payment_method,
        plan_type=plan,
        amount=int(checkout_info["final_amount"]),
        currency=checkout_info["currency"],
    )




def _parse_campaign_id(value: str | None) -> int | None:
    if not value:
        return None
    try:
        campaign_id = int(value)
    except (TypeError, ValueError):
        return None
    return campaign_id if campaign_id > 0 else None




async def _plan_price(session, plan_type: str, payment_method: str | None) -> tuple[int, str]:
    price = await SubscriptionPriceService(session).get_price(payment_method, plan_type)
    if price:
        return price.amount, price.currency
    if payment_method in ("alipay", "wechat"):
        return (66 if plan_type == "1_month" else 29), "¥"
    return (89 if plan_type == "1_month" else 29), "TJS"




def _is_card_currency(currency: str) -> bool:
    return (currency or "").strip().lower() in {"tjs", "somoni", "сомони"}




def _card_texts(lang: str) -> dict[str, str]:
    texts = {
        "tj": {
            "main_title": "💎 <b>Тарифҳои обуна</b>",
            "benefits": "Обуна гиред ва аз бот бе лимит истифода баред.",
            "card_note_short": "💳 Бо ҳар гуна корти бонкӣ метавонед пардохт кунед.",
            "card_note_full": (
                "Агар корти шумо корти Тоҷикистон набошад, маблағро бо қурби бонки худ "
                "дар TJS ҳисоб карда ба ҳамин корт фиристед."
            ),
            "referral_hint": "🎁 3 дӯсти нав даъват кунед ва 20% тахфиф гиред.",
            "choose": "👇 <b>Тарифро интихоб кунед:</b>",
            "checkout_title": "💳 Шумо обунаро интихоб кардед",
            "plan_label": "Тариф",
            "price_label": "Нарх",
            "bank_label": "Бонк",
            "bank_name": "DC city",
            "payment_details_label": "Реквизити пардохт",
            "send_screenshot": "Пас аз пардохт скриншотро фиристед.",
        },
        "ru": {
            "main_title": "💎 <b>Тарифы подписки</b>",
            "benefits": "Оформите подписку и пользуйтесь ботом без ограничений.",
            "card_note_short": "💳 Можно оплатить любой банковской картой.",
            "card_note_full": (
                "Если ваша карта не таджикская, рассчитайте сумму в TJS по курсу вашего банка "
                "и отправьте на эту карту."
            ),
            "referral_hint": "🎁 Пригласите 3 новых друзей и получите скидку 20%.",
            "choose": "👇 <b>Выберите тариф:</b>",
            "checkout_title": "💳 Вы выбрали подписку",
            "plan_label": "Тариф",
            "price_label": "Цена",
            "bank_label": "Банк",
            "bank_name": "DC city",
            "payment_details_label": "Реквизиты для оплаты",
            "send_screenshot": "После оплаты отправьте скриншот.",
        },
        "uz": {
            "main_title": "💎 <b>Obuna tariflari</b>",
            "benefits": "Obuna oling va botdan limitsiz foydalaning.",
            "card_note_short": "💳 Istalgan bank kartasi orqali to'lov qilishingiz mumkin.",
            "card_note_full": (
                "Agar kartangiz Tojikiston kartasi bo'lmasa, o'z bankingiz kursi bo'yicha "
                "TJS valyutasida hisoblab shu kartaga yuboring."
            ),
            "referral_hint": "🎁 3 ta yangi do'st taklif qiling va 20% chegirma oling.",
            "choose": "👇 <b>Tarifni tanlang:</b>",
            "checkout_title": "💳 Siz obunani tanladingiz",
            "plan_label": "Tarif",
            "price_label": "Narx",
            "bank_label": "Bank",
            "bank_name": "DC city",
            "payment_details_label": "To'lov rekviziti",
            "send_screenshot": "To'lovdan keyin skrinshot yuboring.",
        },
    }
    return texts.get(lang, texts["ru"])


def _card_plan_label(plan_type: str, lang: str) -> str:
    labels = {
        "tj": {"10_days": "10 рӯз", "1_month": "1 моҳ"},
        "ru": {"10_days": "10 дней", "1_month": "1 месяц"},
        "uz": {"10_days": "10 kunlik", "1_month": "1 oylik"},
    }
    return labels.get(lang, labels["ru"]).get(plan_type, plan_type)


def _card_main_price(amount: int) -> str:
    return f"💸 {amount} TJS 🇹🇯"




def _card_main_plan_line(plan_type: str, lang: str, amount: int) -> str:
    return f"🗓️ {_card_plan_label(plan_type, lang)} — {_card_main_price(amount)}"


def _card_main_text(
    lang: str,
    price_10: tuple[int, str],
    price_1m: tuple[int, str],
    *,
    show_discount_hint: bool,
) -> str:
    texts = _card_texts(lang)
    plan_lines = "\n".join([
        _card_main_plan_line("10_days", lang, price_10[0]),
        _card_main_plan_line("1_month", lang, price_1m[0]),
        "",
        texts["card_note_short"],
    ])
    base = (
        f"{texts['main_title']}\n\n"
        f"{texts['benefits']}\n\n"
        f"<blockquote>{plan_lines}</blockquote>"
    )
    if show_discount_hint:
        base += f"\n\n{texts['referral_hint']}"
    return f"{base}\n\n{texts['choose']}"




def _plan_label(plan_type: str, lang: str) -> str:
    labels = {
        "tj": {"10_days": "10 рӯз", "1_month": "1 моҳ"},
        "ru": {"10_days": "10 дней", "1_month": "1 месяц"},
        "uz": {"10_days": "10 kunlik", "1_month": "1 oylik"},
    }
    return labels.get(lang, labels["ru"]).get(plan_type, plan_type)




def _compact_plan_line(plan_type: str, lang: str, amount: int, currency: str) -> str:
    return f"🗓️ {_plan_label(plan_type, lang)} - {format_subscription_price(amount, currency)}"


async def build_subscription_main_text_for_user(session, user, lang: str) -> str:
    price_10 = await _plan_price(session, "10_days", getattr(user, "payment_method", None))
    price_1m = await _plan_price(session, "1_month", getattr(user, "payment_method", None))

    is_card_payment = all(
        _is_card_currency(currency)
        for _, currency in (price_10, price_1m)
    )
    if is_card_payment:
        return _card_main_text(lang, price_10, price_1m, show_discount_hint=not user.discount_used)
    else:
        plan_lines = "\n".join([
            _compact_plan_line("10_days", lang, price_10[0], price_10[1]),
            _compact_plan_line("1_month", lang, price_1m[0], price_1m[1]),
        ])
        base = (
            f"{t('subscription_main_title', lang)}\n\n"
            f"🚀 {t('subscription_main_visa_benefits', lang)}\n\n"
            f"{plan_lines}"
        )
        if not user.discount_used:
            base += f"\n\n{t('subscription_referral_hint', lang)}"
        return f"{base}\n\n{t('subscription_main_choose', lang)}"


async def _bot_username(bot) -> str:
    global _BOT_USERNAME_CACHE
    if _BOT_USERNAME_CACHE:
        return _BOT_USERNAME_CACHE
    try:
        me = await bot.get_me()
        username = (getattr(me, "username", None) or "").strip().lstrip("@")
        if username:
            _BOT_USERNAME_CACHE = username
            return username
    except Exception:
        pass
    username = (settings.BOT_USERNAME or "").strip().lstrip("@")
    _BOT_USERNAME_CACHE = username
    return username




async def _replace_with_text(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    parse_mode: str | None = "HTML",
    disable_web_page_preview: bool = True,
) -> None:
    try:
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
        )
        return
    except Exception:
        pass

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )


async def _replace_with_expired_offer(callback: CallbackQuery, lang: str, key: str) -> None:
    try:
        await callback.answer()
    except Exception:
        pass
    await _replace_with_text(
        callback,
        t(key, lang),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


def _miniapp_button_text(lang: str, mode: str) -> str:
    if mode == "admin_discount":
        return t("subscription_admin_discount_button", lang)
    if mode == "feedback_discount":
        return t("feedback_price_offer_button", lang)
    if mode == "referral_discount":
        return t("subscription_referral_discount_button", lang)
    return t("subscription_miniapp_open_button", lang)


async def _replace_with_miniapp_entry(
    callback: CallbackQuery,
    lang: str,
    *,
    source: str,
    mode: str = "subscription",
    campaign_id: int | None = None,
    feedback_id: int | None = None,
    plan: str | None = None,
    method: str | None = None,
) -> None:
    await _replace_with_text(
        callback,
        t("subscription_miniapp_entry_text", lang),
        reply_markup=subscription_miniapp_keyboard(
            lang,
            source=source,
            mode=mode,
            campaign_id=campaign_id,
            feedback_id=feedback_id,
            plan=plan,
            method=method,
            text=_miniapp_button_text(lang, mode),
        ),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )




@router.callback_query(F.data == "subscription:open")
async def subscription_open_handler(callback: CallbackQuery, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"

    await callback.answer()
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="subscription_open",
        mode="subscription",
    )


@router.callback_query(F.data.startswith("discount_offer:open"))
async def discount_offer_open_handler(callback: CallbackQuery, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer()
        return

    lang = user.language or "ru"
    parts = callback.data.split(":")
    campaign_id = _parse_campaign_id(parts[2] if len(parts) > 2 else None)
    await callback.answer()
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_admin_discount_open",
        mode="admin_discount",
        campaign_id=campaign_id,
    )


@router.callback_query(F.data.startswith("feedback_discount:open:"))
async def feedback_discount_open_handler(callback: CallbackQuery, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = user.language or "ru"
    feedback_id = int(callback.data.split(":")[2])
    await callback.answer()
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_feedback_discount_open",
        mode="feedback_discount",
        feedback_id=feedback_id,
    )


@router.callback_query(F.data.startswith("feedback_discount:method:"))
async def feedback_discount_method_handler(callback: CallbackQuery, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    parts = callback.data.split(":")
    feedback_id = int(parts[2])
    payment_method = parts[3]
    lang = user.language or "ru"

    if payment_method not in PAYMENT_METHODS:
        await callback.answer()
        await _replace_with_expired_offer(callback, lang, "feedback_price_offer_expired")
        return

    await callback.answer()
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_feedback_discount_method",
        mode="feedback_discount",
        feedback_id=feedback_id,
        method=payment_method,
    )


@router.callback_query(F.data.startswith("feedback_discount:plan:"))
async def feedback_discount_plan_handler(callback: CallbackQuery, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    parts = callback.data.split(":")
    feedback_id = int(parts[2])
    payment_method = parts[3]
    plan = parts[4]
    lang = user.language or "ru"

    if payment_method not in PAYMENT_METHODS or plan not in PLANS:
        await callback.answer()
        await _replace_with_expired_offer(callback, lang, "feedback_price_offer_expired")
        return

    await callback.answer()
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_feedback_discount_plan",
        mode="feedback_discount",
        feedback_id=feedback_id,
        method=payment_method,
        plan=plan,
    )


@router.callback_query(F.data.startswith("discount_offer:method:"))
async def discount_offer_method_handler(callback: CallbackQuery, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    parts = callback.data.split(":")
    campaign_id = None
    payment_method = None
    if len(parts) >= 4:
        campaign_id = _parse_campaign_id(parts[2])
        payment_method = parts[3] if campaign_id else parts[2]
    elif len(parts) >= 3:
        payment_method = parts[2]

    if payment_method not in PAYMENT_METHODS:
        await callback.answer()
        await _replace_with_expired_offer(callback, user.language or "ru", "subscription_admin_discount_expired")
        return

    lang = user.language or "ru"
    await callback.answer()
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_admin_discount_method",
        mode="admin_discount",
        campaign_id=campaign_id,
        method=payment_method,
    )


@router.callback_query(F.data.startswith("discount_offer:change_payment"))
async def discount_offer_change_payment_handler(callback: CallbackQuery, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return
    lang = user.language or "ru"
    parts = callback.data.split(":")
    campaign_id = _parse_campaign_id(parts[2] if len(parts) > 2 else None)
    await callback.answer()
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_admin_discount_change_payment",
        mode="admin_discount",
        campaign_id=campaign_id,
    )


@router.callback_query(F.data.startswith("discount_offer:back_entry"))
async def discount_offer_back_entry_handler(callback: CallbackQuery, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return
    lang = user.language or "ru"
    parts = callback.data.split(":")
    campaign_id = _parse_campaign_id(parts[2] if len(parts) > 2 else None)
    await callback.answer()
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_admin_discount_back_entry",
        mode="admin_discount",
        campaign_id=campaign_id,
    )


@router.callback_query(F.data.startswith("discount_offer:back_payment"))
async def discount_offer_back_payment_handler(callback: CallbackQuery, session):
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return
    lang = user.language or "ru"
    parts = callback.data.split(":")
    campaign_id = _parse_campaign_id(parts[2] if len(parts) > 2 else None)
    await callback.answer()
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_admin_discount_back_payment",
        mode="admin_discount",
        campaign_id=campaign_id,
    )


@router.callback_query(F.data == "subscription:referral_discount")
async def subscription_referral_discount_handler(callback: CallbackQuery, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer()
        return

    # Guard: if user already used discount — ignore silently
    if user.discount_used:
        await callback.answer()
        return

    await user_repo.ensure_referral_code(user)

    # Only start the offer once — do NOT reset count on repeated clicks
    if not user.discount_offer_started_at:
        await user_repo.start_discount_offer(user)

    await session.flush()
    await DiscountService(session).sync_referral_discount_progress(user)

    lang = user.language if user.language else "ru"
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_referral_discount",
        mode="referral_discount",
    )
    await session.commit()
    await callback.answer()


@router.callback_query(F.data == "subscription:back_to_main")
async def subscription_back_to_main_handler(callback: CallbackQuery, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_subscription_back",
        mode="subscription",
    )

    await user_repo.clear_discount_progress_message(user)
    await session.commit()
    await callback.answer()


@router.callback_query(F.data == "payment:visa")
async def payment_visa_handler(callback: CallbackQuery, session):

    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    lang = user.language if user.language else "ru"
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_payment_visa",
        mode="subscription",
        method="visa",
    )


@router.callback_query(F.data == "payment:alipay")
async def payment_alipay_handler(callback: CallbackQuery, session):

    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    lang = user.language if user.language else "ru"
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_payment_alipay",
        mode="subscription",
        method="alipay",
    )


@router.callback_query(F.data == "payment:wechat")
async def payment_wechat_handler(callback: CallbackQuery, session):

    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    lang = user.language if user.language else "ru"
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_payment_wechat",
        mode="subscription",
        method="wechat",
    )


@router.callback_query(F.data == "checkout:change_plan")
async def checkout_change_plan_handler(callback: CallbackQuery, session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"

    draft = await PaymentRepository(session).get_latest_draft_by_user(callback.from_user.id)
    await user_repo.set_selected_plan_type(user, None)
    await session.commit()

    mode = "subscription"
    campaign_id = None
    feedback_id = None
    if draft and draft.discount_source == "admin_campaign":
        mode = "admin_discount"
        campaign_id = draft.discount_campaign_id
    elif draft and draft.discount_source == "feedback_price_offer":
        mode = "feedback_discount"
        feedback = await BotFeedbackRepository(session).get_latest_available_price_offer(callback.from_user.id)
        feedback_id = feedback.id if feedback else None
    elif draft and draft.discount_source == "referral":
        mode = "referral_discount"

    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_checkout_change_plan",
        mode=mode,
        campaign_id=campaign_id,
        feedback_id=feedback_id,
        method=(draft.payment_method if draft else None) or user.payment_method,
    )
    await callback.answer()
    return




@router.callback_query(F.data.startswith("discount_offer:plan:"))
async def discount_offer_plan_handler(callback: CallbackQuery, session):
    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    lang = user.language or "ru"
    parts = callback.data.split(":")
    campaign_id = None
    if len(parts) >= 5:
        campaign_id = _parse_campaign_id(parts[2])
        if campaign_id:
            payment_method = parts[3]
            plan = parts[4]
        else:
            payment_method = parts[2]
            plan = parts[3]
    elif len(parts) >= 4:
        payment_method = parts[2]
        plan = parts[3]
    else:
        payment_method = user.payment_method
        plan = parts[-1]

    if payment_method not in PAYMENT_METHODS:
        payment_method = None

    if plan not in PLANS:
        await _replace_with_expired_offer(callback, lang, "subscription_admin_discount_expired")
        return

    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_admin_discount_plan",
        mode="admin_discount",
        campaign_id=campaign_id,
        method=payment_method,
        plan=plan,
    )


@router.callback_query(F.data.startswith("subscription:plan:"))
async def subscription_plan_handler(callback: CallbackQuery, session):
    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        return

    lang = user.language or "ru"

    plan = callback.data.split(":")[-1]
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_subscription_plan",
        mode="subscription",
        plan=plan,
        method=user.payment_method,
    )


@router.callback_query(F.data == "payment:back")
async def payment_back_handler(callback: CallbackQuery, session):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.callback_query(F.data == "payment:retry")
async def payment_retry_handler(callback: CallbackQuery, session):
    from app.repositories.user_repo import UserRepository

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    lang = user.language if user.language else "ru"
    await callback.answer()
    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_payment_retry",
        mode="subscription",
    )


@router.callback_query(F.data == "subscription:change_payment_method")
async def subscription_change_payment_method_handler(callback: CallbackQuery, session):
    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        return

    lang = user.language if user.language else "ru"

    await _replace_with_miniapp_entry(
        callback,
        lang,
        source="legacy_change_payment_method",
        mode="subscription",
    )
