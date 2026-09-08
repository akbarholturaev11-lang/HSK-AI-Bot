"""Mini App ichidagi mayda tushuntirish blokchalari.

Ikki xil maslahat bor va ikkalasi ham bir xil qoidalarga bo'ysunadi:

* **Yangilik** — nimadir o'zgargan bo'lsa, foydalanuvchi O'SHA o'zgarishga
  duch kelganda chiqadi. Umumiy "yangiliklar oynasi" emas: odam paywallni
  ko'rmasa, paywall haqidagi maslahat ham chiqmaydi.
* **Bo'lim tanishtiruvi** — yangi odam bo'limga birinchi marta kirganda.

Qat'iy qoidalar (foydalanuvchi talabi):

1. **Majburiy emas.** Blokcha oqimni to'xtatmaydi, X bilan yopiladi.
2. **Mayda.** Bitta sarlavha + bitta jumla. Modal emas, ekran egallamaydi.
3. **Bir marta.** Yopilgach qaytmaydi.
4. **Istisno:** odam o'sha bo'limni UZOQ vaqt ishlatmagan bo'lsa, tanishtiruv
   qayta chiqadi — u allaqachon unutgan bo'lishi mumkin.

Saqlash uchun YANGI jadval yaratilmaydi: `course_miniapp_events` da
`hint_dismissed` nomi bilan yoziladi va o'sha jadvalning
`(telegram_id, event_name, dedupe_key)` unique kaliti "bir marta" ni bepul
ta'minlaydi.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.bot.utils.i18n import t
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.services.entitlements.state import has_full_access, resolve_state


logger = logging.getLogger(__name__)


HINT_EVENT_NAME = "hint_dismissed"
HINT_DEDUPE_PREFIX = "hint:"

#: Bo'limni shuncha vaqt ishlatmagan odamga tanishtiruv QAYTA chiqadi.
#: 60 kun — bir oy dam olgan odam hali eslaydi, ikki oy esa unutadi.
REINTRODUCE_AFTER = timedelta(days=60)

#: Bo'lim tanishtiruvlari. Kalit — Mini App'dagi bo'lim nomi.
SECTION_HINTS = {
    "course": "hint_section_course",
    "mashq": "hint_section_practice",
    "voice": "hint_section_voice",
    "rating": "hint_section_rating",
    "profile": "hint_section_profile",
}

#: Yangilik maslahatlari — faqat o'sha o'zgarishga duch kelganda.
CHANGE_HINT_PAYWALL = "hint_change_paywall"
CHANGE_HINT_TRIAL = "hint_change_trial"
CHANGE_HINT_ADS = "hint_change_ads"

#: Yangiliklar faqat SHU sanadan OLDIN ro'yxatdan o'tgan odamlarga.
#: Keyin kelgan odam uchun bu "yangilik" emas — u boshqacha holatni ko'rmagan.
CHANGE_CUTOFF = datetime(2026, 9, 8, tzinfo=timezone.utc)


#: Serverga yozilishi mumkin bo'lgan kalitlar. Klient o'zi o'ylab topgan
#: kalitni yozib, jadvalni to'ldira olmasligi kerak.
KNOWN_HINT_KEYS = frozenset(SECTION_HINTS.values()) | {
    CHANGE_HINT_PAYWALL,
    CHANGE_HINT_TRIAL,
    CHANGE_HINT_ADS,
}

_DAY_SUFFIX = re.compile(r":\d{4}-\d{2}-\d{2}$")


def _hint_name(dedupe_key: str) -> str:
    """`hint:<kalit>:<kun>` dan kalitni ajratadi.

    Kunsiz eski qatorlar ham bor (kun keyinchalik qo'shilgan), shuning uchun
    oxiri sanaga o'xshamasa butun qoldiq kalit deb olinadi.
    """
    raw = dedupe_key[len(HINT_DEDUPE_PREFIX) :]
    return _DAY_SUFFIX.sub("", raw)


def _as_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class MiniAppHintService:
    def __init__(self, session):
        self.session = session

    # --- yopilganlar ------------------------------------------------------

    async def _dismissed(self, telegram_id: int) -> dict[str, datetime]:
        """Yopilgan maslahatlar va qachon yopilgani."""
        result = await self.session.execute(
            select(
                CourseMiniAppEvent.dedupe_key,
                func.max(CourseMiniAppEvent.created_at),
            )
            .where(
                CourseMiniAppEvent.telegram_id == int(telegram_id),
                CourseMiniAppEvent.event_name == HINT_EVENT_NAME,
            )
            .group_by(CourseMiniAppEvent.dedupe_key)
        )
        out: dict[str, datetime] = {}
        for key, seen_at in result.all():
            if not key or not str(key).startswith(HINT_DEDUPE_PREFIX):
                continue
            name = _hint_name(str(key))
            seen = _as_utc(seen_at)
            # Bir kalitda bir nechta qator bo'lishi mumkin (har yopilish o'z
            # kunida). Eng OXIRGISI hisoblanadi — qayta chiqarish o'lchovi shu.
            if seen and (out.get(name) is None or seen > out[name]):
                out[name] = seen
        return out

    # --- qaror ------------------------------------------------------------

    def _is_existing_user(self, user, *, now: datetime) -> bool:
        created = _as_utc(getattr(user, "created_at", None))
        return bool(created and created < CHANGE_CUTOFF)

    async def hints_for(
        self,
        user,
        *,
        section: str | None = None,
        now: datetime | None = None,
    ) -> list[dict]:
        """Shu foydalanuvchi hozir ko'rishi kerak bo'lgan maslahatlar.

        Ro'yxat bo'sh bo'lishi — normal holat. Hech qachon exception
        tashlamaydi: maslahat oqimni buzmasligi kerak.
        """
        try:
            return await self._hints_for(user, section=section, now=now)
        except Exception:  # noqa: BLE001 — maslahat hech qachon oqimni buzmasin
            logger.exception("Maslahatlarni hisoblab bo'lmadi")
            return []

    async def _hints_for(self, user, *, section, now) -> list[dict]:
        if user is None:
            return []
        now = now or datetime.now(timezone.utc)
        lang = getattr(user, "language", None) or "ru"
        dismissed = await self._dismissed(int(user.telegram_id))
        state = resolve_state(user)
        full_access = has_full_access(state)
        existing = self._is_existing_user(user, now=now)

        hints: list[dict] = []

        def add(key: str, *, section_name: str | None = None, reintroduce=False):
            seen_at = dismissed.get(key)
            if seen_at is not None:
                # Bir marta yopilgan. Istisno: bo'lim tanishtiruvi uzoq
                # tanaffusdan keyin qayta chiqadi.
                if not reintroduce or (now - seen_at) < REINTRODUCE_AFTER:
                    return
            title = t(f"{key}_title", lang)
            body = t(f"{key}_body", lang)
            if title == f"{key}_title" or body == f"{key}_body":
                # Matn yo'q — maslahat ham yo'q. Kalitni ko'rsatib qo'ymaymiz.
                return
            hints.append(
                {"key": key, "title": title, "body": body, "section": section_name}
            )

        # --- yangiliklar: faqat ESKI foydalanuvchilarga -------------------
        if existing and not full_access:
            # Reklama ko'rib davom etish olib tashlandi — bu ular sezadigan
            # eng katta o'zgarish, shuning uchun paywall bilan birga chiqadi.
            add(CHANGE_HINT_PAYWALL, section_name="mashq")
            add(CHANGE_HINT_TRIAL, section_name="profile")
        if existing:
            add(CHANGE_HINT_ADS, section_name="mashq")

        # --- bo'lim tanishtiruvi ------------------------------------------
        for name, key in SECTION_HINTS.items():
            if section and name != section:
                continue
            add(key, section_name=name, reintroduce=True)

        if section:
            hints = [h for h in hints if h["section"] in (None, section)]
        return hints

    # --- yopish -----------------------------------------------------------

    @staticmethod
    def dedupe_key(hint_key: str, *, on: datetime | None = None) -> str:
        """`hint:<kalit>:<kun>`.

        Kun ATAYLAB kalit ichida. Sababi: yopilish `course_miniapp_events`
        ning `(telegram_id, event_name, dedupe_key)` unique kaliti orqali
        yoziladi, ya'ni bir xil kalit ikkinchi marta YOZILMAYDI. Kunsiz kalit
        bilan uzoq tanaffusdan keyin qayta chiqqan tanishtiruv yopilganda
        yangi qator yozilmasdi — `created_at` eskiligicha qolib, blokcha har
        ochilishda qaytaverardi.

        Kun bilan: bitta kun ichida necha marta bosilsa ham bitta qator, lekin
        boshqa kunda yopilsa yangi qator — ya'ni "bir marta" ham, "60 kundan
        keyin qayta" ham ishlaydi.
        """
        day = (on or datetime.now(timezone.utc)).date().isoformat()
        return f"{HINT_DEDUPE_PREFIX}{str(hint_key or '').strip()[:48]}:{day}"

    async def dismiss(self, user, hint_key: str, *, client: str = "course_v3") -> bool:
        """Blokchani yopilgan deb belgilaydi.

        Kalitni SERVER quradi, klient emas: kun kalit ichida va uni klient
        soatiga qoldirish qayta chiqarish o'lchovini buzadi.

        Hech qachon exception tashlamaydi — blokchani yopish oqimni
        to'xtatmasligi kerak.
        """
        key = str(hint_key or "").strip()[:48]
        if user is None or not key:
            return False
        if key not in KNOWN_HINT_KEYS:
            return False
        from app.services.course_miniapp_analytics_service import (
            CourseMiniAppAnalyticsService,
        )

        result = await CourseMiniAppAnalyticsService(self.session).record_server_event(
            event_name=HINT_EVENT_NAME,
            telegram_id=int(getattr(user, "telegram_id", 0) or 0),
            user_id=getattr(user, "id", None),
            source=str(client or "course_v3")[:40],
            dedupe_key=self.dedupe_key(key),
            payload={"hint": key},
        )
        return bool(result.get("ok"))
