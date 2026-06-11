from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from app.bot.utils.course_miniapp import subscription_miniapp_url
from app.bot.utils.i18n import t


def subscription_miniapp_button(
    lang: str,
    source: str = "subscription_button",
    text: str | None = None,
    mode: str | None = None,
    campaign_id: int | None = None,
    feedback_id: int | None = None,
    plan: str | None = None,
    method: str | None = None,
) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text or t("subscription_miniapp_open_button", lang),
        web_app=WebAppInfo(
            url=subscription_miniapp_url(
                lang,
                source=source,
                mode=mode,
                campaign_id=campaign_id,
                feedback_id=feedback_id,
                plan=plan,
                method=method,
            )
        ),
    )


def subscription_miniapp_keyboard(
    lang: str,
    source: str = "subscription_button",
    text: str | None = None,
    mode: str | None = None,
    campaign_id: int | None = None,
    feedback_id: int | None = None,
    plan: str | None = None,
    method: str | None = None,
    include_free_mode: bool = False,
) -> InlineKeyboardMarkup:
    rows = [
        [
            subscription_miniapp_button(
                lang,
                source=source,
                text=text,
                mode=mode,
                campaign_id=campaign_id,
                feedback_id=feedback_id,
                plan=plan,
                method=method,
            )
        ]
    ]
    if include_free_mode:
        rows.append([
            InlineKeyboardButton(
                text=t("subscription_free_mode_button", lang),
                callback_data="mode:free_qa",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscription_main_keyboard(lang: str, show_discount: bool = True) -> InlineKeyboardMarkup:
    rows = []

    # Invite button shown FIRST — only if user hasn't used discount yet
    if show_discount:
        rows.append([
            subscription_miniapp_button(
                lang,
                source="legacy_referral_discount",
                mode="referral_discount",
                text=t("subscription_referral_discount_button", lang),
            )
        ])

    rows.append([
        subscription_miniapp_button(
            lang,
            source="legacy_plan",
            mode="subscription",
            text=t("subscription_button_10_days", lang),
            plan="10_days",
        ),
        subscription_miniapp_button(
            lang,
            source="legacy_plan",
            mode="subscription",
            text=t("subscription_button_1_month", lang),
            plan="1_month",
        ),
    ])
    rows.append([
        subscription_miniapp_button(
            lang,
            source="legacy_change_payment",
            mode="subscription",
            text=t("payment_back", lang),
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscription_discount_progress_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Shown while waiting for 3 referrals — only back button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                subscription_miniapp_button(
                    lang,
                    source="legacy_referral_progress",
                    mode="referral_discount",
                    text=t("subscription_back_to_main", lang),
                )
            ]
        ]
    )


def subscription_discount_ready_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Shown when 3/3 referrals reached — plan buttons + back."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                subscription_miniapp_button(
                    lang,
                    source="legacy_referral_ready",
                    mode="referral_discount",
                    text=t("subscription_button_10_days", lang),
                    plan="10_days",
                ),
                subscription_miniapp_button(
                    lang,
                    source="legacy_referral_ready",
                    mode="referral_discount",
                    text=t("subscription_button_1_month", lang),
                    plan="1_month",
                ),
            ],
            [
                subscription_miniapp_button(
                    lang,
                    source="legacy_referral_ready_back",
                    mode="referral_discount",
                    text=t("subscription_back_to_main", lang),
                ),
            ],
        ]
    )


def payment_method_keyboard(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            subscription_miniapp_button(
                lang,
                source="legacy_payment_method",
                text=t("payment_method_visa_button", lang),
                method="visa",
            ),
        ],
        [
            subscription_miniapp_button(lang, source="legacy_payment_method", text="🇨🇳 Alipay", method="alipay"),
        ],
        [
            subscription_miniapp_button(lang, source="legacy_payment_method", text="🇨🇳 WeChat Pay", method="wechat"),
        ],
        [
            InlineKeyboardButton(text=t("payment_back", lang), callback_data="payment:back"),
        ]
    ])


def discount_payment_method_keyboard(
    lang: str,
    methods: list[str] | tuple[str, ...] | None = None,
    campaign_id: int | None = None,
):
    labels = {
        "visa": t("payment_method_visa_button", lang),
        "alipay": "🇨🇳 Alipay",
        "wechat": "🇨🇳 WeChat Pay",
    }
    methods = list(methods or ("visa", "alipay", "wechat"))
    rows = []
    for method in methods:
        if method not in labels:
            continue
        rows.append([
            subscription_miniapp_button(
                lang,
                source="legacy_admin_discount_method",
                mode="admin_discount",
                text=labels[method],
                campaign_id=campaign_id,
                method=method,
            )
        ])

    back_callback = f"discount_offer:back_entry:{campaign_id}" if campaign_id else "discount_offer:back_entry"
    rows.append([InlineKeyboardButton(text=t("payment_back", lang), callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_discount_entry_keyboard(lang: str, campaign_id: int | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                subscription_miniapp_button(
                    lang,
                    source="admin_discount",
                    mode="admin_discount",
                    campaign_id=campaign_id,
                    text=t("subscription_admin_discount_button", lang),
                )
            ]
        ]
    )


def admin_discount_plan_keyboard(
    lang: str,
    plans: list[str] | tuple[str, ...] | None = None,
    payment_method: str | None = None,
    campaign_id: int | None = None,
    back_callback: str = "discount_offer:back_entry",
) -> InlineKeyboardMarkup:
    plans = list(plans or ("10_days", "1_month"))
    plan_buttons = []
    for plan in plans:
        if campaign_id and payment_method:
            button = subscription_miniapp_button(
                lang,
                source="legacy_admin_discount_plan",
                mode="admin_discount",
                campaign_id=campaign_id,
                method=payment_method,
                plan=plan,
                text=t("subscription_button_10_days" if plan == "10_days" else "subscription_button_1_month", lang),
            )
        elif payment_method:
            button = subscription_miniapp_button(
                lang,
                source="legacy_admin_discount_plan",
                mode="admin_discount",
                method=payment_method,
                plan=plan,
                text=t("subscription_button_10_days" if plan == "10_days" else "subscription_button_1_month", lang),
            )
        else:
            button = subscription_miniapp_button(
                lang,
                source="legacy_admin_discount_plan",
                mode="admin_discount",
                campaign_id=campaign_id,
                plan=plan,
                text=t("subscription_button_10_days" if plan == "10_days" else "subscription_button_1_month", lang),
            )
        plan_buttons.append(button)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            plan_buttons,
            [
                InlineKeyboardButton(
                    text=t("payment_back", lang),
                    callback_data=back_callback,
                )
            ],
        ]
    )


def feedback_discount_payment_method_keyboard(feedback_id: int, lang: str):
    labels = {
        "visa": t("payment_method_visa_button", lang),
        "alipay": "🇨🇳 Alipay",
        "wechat": "🇨🇳 WeChat Pay",
    }
    return InlineKeyboardMarkup(inline_keyboard=[
        [
                subscription_miniapp_button(
                    lang,
                    source="legacy_feedback_discount_method",
                    mode="feedback_discount",
                    feedback_id=feedback_id,
                    text=label,
                    method=method,
                )
        ]
        for method, label in labels.items()
    ] + [
        [
            InlineKeyboardButton(text=t("payment_back", lang), callback_data="payment:back"),
        ],
    ])


def feedback_discount_plan_keyboard(
    feedback_id: int,
    lang: str,
    payment_method: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                subscription_miniapp_button(
                    lang,
                    source="legacy_feedback_discount_plan",
                    mode="feedback_discount",
                    feedback_id=feedback_id,
                    method=payment_method,
                    plan="10_days",
                    text=t("subscription_button_10_days", lang),
                ),
                subscription_miniapp_button(
                    lang,
                    source="legacy_feedback_discount_plan",
                    mode="feedback_discount",
                    feedback_id=feedback_id,
                    method=payment_method,
                    plan="1_month",
                    text=t("subscription_button_1_month", lang),
                ),
            ],
            [
                subscription_miniapp_button(
                    lang,
                    source="legacy_feedback_discount_back",
                    mode="feedback_discount",
                    feedback_id=feedback_id,
                    text=t("payment_back", lang),
                )
            ],
        ]
    )
