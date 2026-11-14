"""Best-effort lava.top user notices and admin alerts (post-commit only).

Delivery never decides money or access; failures are logged and ignored.
User-facing copy is authored in ``localization/ui/*/bot.json`` (``lava.*``).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from html import escape

from app.bot.utils.i18n import t
from app.services.account_identity import actual_telegram_id
from app.services.bot_block_status_service import BotBlockStatusService

logger = logging.getLogger(__name__)

USER_NOTICE_KEYS = {
    "renewal_failed": "bot.lava.user_renewal_failed",
    "subscription_cancelled": "bot.lava.user_subscription_cancelled",
    "refund_revoked": "bot.lava.user_refund_revoked",
    "chargeback_revoked": "bot.lava.user_chargeback_revoked",
    "chargeback_restored": "bot.lava.user_chargeback_restored",
}

ADMIN_ALERT_TEXT = {
    "unmatched": "lava.top: noma'lum kontrakt to'landi — Admin PWA → lava.top'da foydalanuvchiga bog'lang.",
    "needs_review": "lava.top: to'lov qo'lda tekshiruv talab qiladi.",
    "amount_mismatch": "lava.top: to'langan summa kutilgandan farq qiladi (Pro berildi).",
    "activation_failed": "lava.top: to'lov tasdiqlandi, lekin Pro faollashmadi — tekshiring.",
    "refund_revoked": "lava.top: refund — Pro avtomatik qisqartirildi.",
    "chargeback_revoked": "lava.top: chargeback ochildi — Pro qisqartirildi, natijani Admin PWA'da yoping.",
    "refund_review": "lava.top: refund/chargeback avtomatik bog'lanmadi — qo'lda tekshiring.",
    "partner_credit": "lava.top: qaytarilgan to'lov uchun partner komissiyasi yozilgan — qo'lda hal qiling.",
    "renewal_overdue": "lava.top: kutilgan obuna yangilanishi kelmadi.",
    "retry_exhausted": "lava.top: webhook ko'p marta qayta ishlanmadi — tekshiring.",
    "webhook_auth_failed": "lava.top: webhook noto'g'ri kalit bilan keldi (401).",
    "promo_rejected": "lava.top: promokod bilan invoice yaratilmadi — kodni lava kabinetida tekshiring.",
}


# Admin alert codes that are processing failures, with their diagnostic site.
LAVA_FAILURE_SITES = {
    "retry_exhausted": "lava_webhook",
    "activation_failed": "lava_ledger",
    "amount_mismatch": "lava_ledger",
    "unmatched": "lava_ledger",
    "needs_review": "lava_ledger",
    "refund_review": "lava_ledger",
    "renewal_overdue": "lava_ledger",
    "promo_rejected": "lava_ledger",
}


def _date(value: datetime | None) -> str:
    return value.strftime("%d.%m.%Y") if isinstance(value, datetime) else ""


class LavaNotifier:
    """Telegram transport. Tests inject a recording fake with the same API."""

    def __init__(self, bot=None, session_factory=None, admin_ids=None):
        self.bot = bot
        self.session_factory = session_factory
        self.admin_ids = list(admin_ids or [])
        self._last_alert: dict[str, float] = {}

    async def admin_alert(self, code: str, *, invoice_id: int | None = None, detail: str | None = None,
                          throttle_seconds: int = 0) -> None:
        # Processing failures are also a diagnostic incident (unified-error-monitoring
        # D4), added next to the Telegram alert, never instead of it: same code,
        # throttle and recipients below. Rejected authentication and completed
        # refund/chargeback outcomes are not processing failures.
        if code in LAVA_FAILURE_SITES:
            from app.services.monitoring.backend import report_server_failure
            report_server_failure("checkout_payments", "provider_failed", LAVA_FAILURE_SITES[code])
        if self.bot is None or not self.admin_ids:
            return
        now = time.monotonic()
        if throttle_seconds and now - self._last_alert.get(code, -1e9) < throttle_seconds:
            return
        self._last_alert[code] = now
        text = ADMIN_ALERT_TEXT.get(code, f"lava.top: {code}")
        if invoice_id is not None:
            text += f"\n#lava_invoice_{int(invoice_id)}"
        if detail:
            text += f"\n{escape(detail[:200])}"
        for admin_id in self.admin_ids:
            try:
                await self.bot.send_message(chat_id=admin_id, text=text)
            except Exception:  # noqa: BLE001 - alert delivery is best effort
                logger.warning("lava.top admin alert delivery failed")

    async def user_notice(self, user, kind: str, *, end_date: datetime | None = None) -> None:
        key = USER_NOTICE_KEYS.get(kind)
        if self.bot is None or key is None or user is None or actual_telegram_id(user) is None:
            return
        if BotBlockStatusService.is_bot_blocked(user):
            return
        lang = getattr(user, "language", None) or "ru"
        try:
            await self.bot.send_message(chat_id=user.telegram_id, text=t(key, lang, date=_date(end_date)))
        except Exception:  # noqa: BLE001
            logger.warning("lava.top user notice delivery failed")
