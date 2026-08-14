from zoneinfo import ZoneInfo

from app.bot.utils.i18n import t


ADMIN_TZ = ZoneInfo("Asia/Shanghai")




def plan_label(plan_type: str, lang: str) -> str:
    if plan_type == "10_days":
        return t("subscription_button_10_days", lang)
    if plan_type == "1_month":
        return t("subscription_button_1_month", lang)
    if plan_type == "3_months":
        return t("subscription_button_3_months", lang)
    return plan_type



