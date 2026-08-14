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



