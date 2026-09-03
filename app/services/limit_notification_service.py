"""Limitga yaqinlashgan va limitga urilgan o'quvchiga bot xabari.

Ikki xil limit bor va ular boshqacha ishlaydi:

* **Darslar limiti** — bepul qismlar tugab boradi va qaytib ochilmaydi.
  Shuning uchun oxiriga yaqinlashganda OGOHLANTIRISH mantiqiy: o'quvchi
  devorga urilishidan oldin biladi.
* **Kunlik limit** — ertaga o'zi ochiladi. Bu yerda ogohlantirishning
  ma'nosi yo'q (bo'lim limiti 1 ta), faqat tugagan payti xabar beriladi.

Xabar IKKI joyga tushadi: Telegram chatiga va ilova ichidagi bildirishnoma
lentasiga. Takror yubormaslik lentadagi `dedupe_key` bilan ta'minlanadi —
qator yozilmasa (ya'ni allaqachon bor) Telegram xabari ham yuborilmaydi.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.bot.keyboards.subscription import subscription_miniapp_keyboard
from app.bot.utils.i18n import t
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.services import course_daily_window
from app.services.course_notification_service import (
    CourseNotificationService,
    notification_copy,
)

logger = logging.getLogger(__name__)


KEY_LESSON_WARNING = "limit_lesson_warning"
KEY_LESSON_SPENT = "limit_lesson_spent"
KEY_DAILY_SPENT = "limit_daily_spent"

# Ogohlantirish bepul qismlarning shuncha qismi ishlatilganda chiqadi.
LESSON_WARNING_RATIO = 0.9


def lesson_warning_threshold(free_parts) -> int | None:
    """Ogohlantirish uchun nechta bepul qism tugagan bo'lishi kerak.

    Bepul qism 2 tadan kam bo'lsa None qaytadi: bitta qismda "tugayapti"
    degan payt umuman yo'q — faqat "tugadi" bor.

    90% kichik sonlarda 100% bilan bir joyga tushib qoladi (6 ning 90% i —
    6), shuning uchun chegara "oxirgi qismdan oldin" bilan cheklanadi.
    Ya'ni 6 ta qismda 5-qismdan keyin, 20 ta qismda 18-qismdan keyin.
    """
    try:
        free = int(free_parts or 0)
    except (TypeError, ValueError):
        return None
    if free < 2:
        return None
    return min(math.ceil(free * LESSON_WARNING_RATIO), free - 1)


def lesson_stage(completed_parts, free_parts) -> str | None:
    """Qaysi xabar tegishli: ``spent``, ``warning`` yoki hech qaysi."""
    try:
        completed = int(completed_parts or 0)
        free = int(free_parts or 0)
    except (TypeError, ValueError):
        return None
    if free <= 0:
        return None
    if completed >= free:
        return "spent"
    threshold = lesson_warning_threshold(free)
    if threshold is not None and completed >= threshold:
        return "warning"
    return None


class LimitNotificationService:
    def __init__(self, session):
        self.session = session

    async def _offset_minutes(self, user) -> int:
        user_id = getattr(user, "id", None)
        if user_id is None:
            return 0
        result = await self.session.execute(
            select(CourseMiniAppProfile.timezone_offset_minutes).where(
                CourseMiniAppProfile.user_id == int(user_id)
            )
        )
        return course_daily_window.normalize_offset_minutes(result.scalar_one_or_none() or 0)

    @staticmethod
    def _local_clock(reset_at: str | None, offset_minutes: int) -> str | None:
        """Server bergan instantni o'quvchining soatida ko'rsatadi.

        Soat hech qayerda qattiq yozilmagan. O'qib bo'lmasa None qaytadi va
        xabar vaqt va'da qilmaydi.
        """
        if not reset_at:
            return None
        try:
            moment = datetime.fromisoformat(str(reset_at))
        except (TypeError, ValueError):
            return None
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        local = moment.astimezone(timezone.utc) + timedelta(minutes=offset_minutes)
        return local.strftime("%H:%M")

    async def _deliver(
        self,
        user,
        *,
        key: str,
        lang: str,
        text: str,
        dedupe_key: str,
        level: str | None = None,
        bot=None,
    ) -> bool:
        """Lentaga yozadi va yangi bo'lsa Telegram'ga yuboradi.

        Lentaga yozish takrorni to'sadi: bir xil ``dedupe_key`` ikkinchi
        marta yozilmaydi, demak xabar ham ikkinchi marta ketmaydi.
        """
        title, body = notification_copy(key, lang, text)
        recorded = await CourseNotificationService(self.session).record(
            user,
            key=key,
            lang=lang,
            title=title,
            body=body,
            action="subscription",
            source="limit_notice",
            level=level,
            dedupe_key=dedupe_key,
        )
        if not recorded or bot is None:
            return recorded
        try:
            await bot.send_message(
                chat_id=int(user.telegram_id),
                text=text,
                reply_markup=subscription_miniapp_keyboard(
                    lang, source="limit_notice", mode="subscription"
                ),
                parse_mode="HTML",
            )
        except Exception:  # noqa: BLE001 — bloklagan user xabari oqimni buzmasin
            logger.info("Limit notice could not be delivered", exc_info=True)
        return recorded

    async def lesson_progress(
        self,
        user,
        *,
        level: str | None,
        completed_parts,
        free_parts,
        bot=None,
    ) -> str | None:
        """Bepul darslar tugayotganini yoki tugaganini bildiradi.

        Har daraja uchun har bosqich BIR marta yuboriladi.
        """
        stage = lesson_stage(completed_parts, free_parts)
        if stage is None:
            return None
        lang = getattr(user, "language", None) or "ru"
        normalized_level = str(level or "").strip().lower() or "hsk1"
        if stage == "spent":
            key = KEY_LESSON_SPENT
            text = t("limit_lesson_spent_notice", lang)
        else:
            key = KEY_LESSON_WARNING
            remaining = max(0, int(free_parts) - int(completed_parts))
            text = t("limit_lesson_warning_notice", lang, remaining=remaining)
        sent = await self._deliver(
            user,
            key=key,
            lang=lang,
            text=text,
            dedupe_key=f"limit:lesson:{normalized_level}:{stage}",
            level=normalized_level,
            bot=bot,
        )
        return stage if sent else None

    async def daily_limit_spent(
        self,
        user,
        *,
        feature_key: str,
        reset_at: str | None,
        lifetime: bool = False,
        bot=None,
    ) -> bool:
        """Kunlik bepul limit tugaganini bildiradi (kuniga bir marta).

        Umrbod limitda "ertaga ochiladi" degan narsa yo'q, shuning uchun
        matn boshqacha va vaqt ko'rsatilmaydi.
        """
        lang = getattr(user, "language", None) or "ru"
        offset = await self._offset_minutes(user)
        clock = None if lifetime else self._local_clock(reset_at, offset)
        if clock:
            text = t("limit_daily_spent_notice", lang, reset_time=clock)
        else:
            text = t("limit_daily_spent_notice_no_time", lang)
        day_key = "lifetime" if lifetime else course_daily_window.local_day_key(offset)
        return await self._deliver(
            user,
            key=KEY_DAILY_SPENT,
            lang=lang,
            text=text,
            dedupe_key=f"limit:daily:{str(feature_key or '').strip().lower()}:{day_key}",
            bot=bot,
        )
