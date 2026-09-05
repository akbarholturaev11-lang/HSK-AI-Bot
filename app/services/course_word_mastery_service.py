"""So'z darajasidagi interval takrori: mashq nimani berishini hal qiladi.

Ilgari mashq bo'limlari so'zni TASODIFIY tanlardi. Bu modul o'sha tanlovni
o'quvchining haqiqiy natijalariga bog'laydi: xato qilingan so'z ertaga
qaytadi, to'g'ri qilingani 1 -> 3 -> 7 -> 21 kun oralig'ida siyraklashadi.

Uchta metod:
- `select()`      — bugungi mashq uchun so'zlar (takror + yangi aralashmasi)
- `apply_results()` — mashq natijasini yozish va keyingi muddatni belgilash
- `weak_seed()`   — mastery yozuvi yo'q, lekin xato tarixi bor o'quvchi uchun

Serverda TASODIFIYLIK YO'Q: bir xil holatda ikki marta chaqirilsa bir xil
ro'yxat qaytadi. Mashqni tugatish mastery yozadi, shuning uchun keyingi
ochilish o'z-o'zidan oldinga siljiydi. Tashlab ketilgan mashq hech narsa
yozmaydi — u yangi so'zlarni "yoqib" yubormasligi kerak.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select as sa_select

from app.db.models.course_mistake import CourseMistake
from app.db.models.course_word_mastery import (
    WORD_MASTERY_INTERVALS,
    WORD_MASTERY_MAX_BOX,
    WORD_MASTERY_SKILLS,
    CourseWordMastery,
)
from app.services.course_daily_window import local_day_key
from app.services.course_v3_word_index import taught_words, word_position


logger = logging.getLogger(__name__)

# Har mashqda nechta takror so'z bo'lsin (qolgani yangi).
REVIEW_SLOTS = 4
# Har nechanchi o'rinda takror so'z tursin — takrorlar boshiga to'planib
# qolmasin, mashq bo'ylab yoyilsin.
REVIEW_EVERY = 3

# Savol banki bo'sh chiqmasligi uchun eng kam pool hajmi. Klientdagi
# chegaralar bilan bir xil, aks holda server klient ko'rsatadigan so'zdan
# torroq to'plam berardi.
MIN_POOL = {"recognition": 8, "pronunciation": 10}

# Muddati kelgan so'zlardan nechtasini o'qib ko'ramiz. Reja `REVIEW_SLOTS`
# tasini oladi, lekin ba'zilari endi o'rganilgan qismlardan tashqarida
# bo'lishi mumkin (band almashuvi), shuning uchun zaxira bilan.
DUE_FETCH_LIMIT = 60

# `weak_seed` faqat SHU manbalardan o'qiydi: ularda `correct_answer` server
# tomonidan tasdiqlangan ieroglif. `lesson`/`test`/`training` da u variant
# matni (tarjima, pinyin yoki butun gap) bo'lishi mumkin — ulardan ieroglif
# ajratib olish alohida ish va boshqa bo'limlar ulanganda kerak bo'ladi.
SEED_SOURCES = ("recognition", "pronunciation", "memorize")
SEED_LIMIT = 40


def normalize_skill(value: str | None) -> str:
    skill = str(value or "").strip().lower()
    if skill not in WORD_MASTERY_SKILLS:
        raise ValueError("Unknown mastery skill")
    return skill


def local_today(timezone_offset_minutes: int = 0) -> date:
    """O'quvchining mahalliy sanasi. UTC EMAS — aks holda UTC+5 dagi
    o'quvchiga so'z ertalab 05:00 da qaytardi."""
    return date.fromisoformat(local_day_key(timezone_offset_minutes))


class CourseWordMasteryService:
    def __init__(self, session):
        self.session = session

    # ---------- o'qish ----------

    async def _due_rows(self, user_id: int, skill: str, today: date) -> list[CourseWordMastery]:
        result = await self.session.execute(
            sa_select(CourseWordMastery)
            .where(
                CourseWordMastery.user_id == user_id,
                CourseWordMastery.skill == skill,
                CourseWordMastery.due_on <= today,
            )
            .order_by(
                CourseWordMastery.due_on.asc(),
                CourseWordMastery.box.asc(),
                CourseWordMastery.last_result_at.asc(),
                CourseWordMastery.zh.asc(),
            )
            .limit(DUE_FETCH_LIMIT)
        )
        return list(result.scalars().all())

    async def _all_rows(self, user_id: int, skill: str) -> dict[str, CourseWordMastery]:
        """Shu ko'nikma bo'yicha barcha yozuvlar. Lug'at hajmi bilan
        chegaralangan (~1200), shuning uchun to'liq o'qish xavfsiz — va bu
        SQL `NOT IN` ga mingta ieroglif uzatishdan ancha arzon."""
        result = await self.session.execute(
            sa_select(CourseWordMastery).where(
                CourseWordMastery.user_id == user_id,
                CourseWordMastery.skill == skill,
            )
        )
        return {row.zh: row for row in result.scalars().all()}

    async def weak_seed(self, user_id: int, *, limit: int = SEED_LIMIT) -> list[str]:
        """Mastery yozuvi paydo bo'lishidan OLDINGI xato tarixi.

        Shu uchta manbada `correct_answer` — server tomonidan tasdiqlangan
        ieroglif (`CourseDrillSignalService` uni o'z lug'atidan quradi,
        `_record_pronunciation_mistake` esa baholangan nishondan), shuning
        uchun hech qanday matn tahlili kerak emas.
        """
        weakness = CourseMistake.wrong_count - CourseMistake.resolved_count
        result = await self.session.execute(
            sa_select(CourseMistake.correct_answer, func.sum(weakness).label("weight"))
            .where(
                CourseMistake.user_id == user_id,
                CourseMistake.source.in_(SEED_SOURCES),
                CourseMistake.wrong_count > CourseMistake.resolved_count,
            )
            .group_by(CourseMistake.correct_answer)
            .order_by(func.sum(weakness).desc(), CourseMistake.correct_answer.asc())
            .limit(max(1, int(limit)))
        )
        words = []
        for zh, _weight in result.all():
            zh = str(zh or "").strip()
            if zh and word_position(zh):
                words.append(zh)
        return words

    async def select(
        self,
        user,
        *,
        skill: str,
        level: str,
        current_part: int,
        limit: int = 10,
        timezone_offset_minutes: int = 0,
    ) -> list[dict]:
        """Bugungi mashq so'zlari. Takrorlar mashq bo'ylab yoyiladi."""
        skill = normalize_skill(skill)
        limit = max(1, min(50, int(limit or 10)))
        user_id = int(getattr(user, "id", 0) or 0)
        today = local_today(timezone_offset_minutes)

        taught = taught_words(
            level,
            current_part,
            single_char=(skill == "recognition"),
            min_pool=MIN_POOL.get(skill, limit),
        )
        taught_order = [zh for zh, _ in taught]
        taught_set = set(taught_order)
        if not taught_order:
            return []

        rows = await self._all_rows(user_id, skill) if user_id else {}

        # 1. Muddati kelgan takrorlar — faqat o'quvchi ko'rgan so'zlar ichidan.
        reviews: list[tuple[str, int]] = []
        for row in await self._due_rows(user_id, skill, today) if user_id else []:
            if row.zh in taught_set:
                reviews.append((row.zh, int(row.box or 0)))
            if len(reviews) >= REVIEW_SLOTS:
                break

        # 2. Yozuv yo'q, lekin xato tarixi bor — eski xatolardan urug'lantiramiz.
        if not reviews and user_id:
            for zh in await self.weak_seed(user_id):
                if zh in taught_set and zh not in rows:
                    reviews.append((zh, 0))
                if len(reviews) >= REVIEW_SLOTS:
                    break

        chosen = {zh for zh, _ in reviews}

        # 3. Yangi so'zlar: o'rgatilgan, lekin bu ko'nikmada hech qachon
        #    ishlatilmagan. Eng yangi o'rgatilgani birinchi.
        fresh = [zh for zh in taught_order if zh not in rows and zh not in chosen]

        # 4. Yetmasa — eng uzoq vaqt ishlatilmagan tanish so'zlar.
        if len(reviews) + len(fresh) < limit:
            stale = sorted(
                (row for zh, row in rows.items() if zh in taught_set and zh not in chosen),
                key=lambda row: (row.last_result_at, row.zh),
            )
            fresh += [row.zh for row in stale if row.zh not in fresh]

        # 5. Aralashtirish: har `REVIEW_EVERY` o'rinda takror.
        return self._interleave(reviews, fresh, limit)

    @staticmethod
    def _interleave(reviews: list[tuple[str, int]], fresh: list[str], limit: int) -> list[dict]:
        out: list[dict] = []
        review_i = fresh_i = 0
        for slot in range(limit):
            take_review = (
                review_i < len(reviews)
                and (slot % REVIEW_EVERY == 0 or fresh_i >= len(fresh))
            )
            if take_review:
                zh, box = reviews[review_i]
                review_i += 1
                out.append({"zh": zh, "kind": "review", "box": box})
            elif fresh_i < len(fresh):
                out.append({"zh": fresh[fresh_i], "kind": "new", "box": 0})
                fresh_i += 1
            else:
                break
        return out

    # ---------- yozish ----------

    def _schedule(self, row: CourseWordMastery, *, correct: bool, today: date) -> None:
        """Interval takrori qoidasi.

        To'g'ri javob so'zni faqat MUDDATI KELGAN bo'lsa ko'taradi. Aks holda
        bir kunda to'rt marta mashq qilib so'zni +21 kunga surib yuborish
        mumkin bo'lardi — bu interval takrori emas, aylanib o'tish.
        """
        if correct:
            row.correct_count = int(row.correct_count or 0) + 1
            if row.due_on <= today:
                row.box = min(int(row.box or 0) + 1, WORD_MASTERY_MAX_BOX)
                row.due_on = today + timedelta(days=WORD_MASTERY_INTERVALS[row.box])
        else:
            row.wrong_count = int(row.wrong_count or 0) + 1
            row.box = 0
            row.due_on = today
        row.last_result_at = datetime.now(timezone.utc)

    async def apply_results(
        self,
        user,
        *,
        skill: str,
        results: list,
        timezone_offset_minutes: int = 0,
    ) -> int:
        """Mashq natijasini yozadi. Yozilgan so'zlar sonini qaytaradi.

        Bu HECH QACHON mashqni yiqitmaydi: xato bo'lsa jimgina 0 qaytadi va
        o'quvchi baribir o'z natijasini ko'radi.
        """
        skill = normalize_skill(skill)
        user_id = int(getattr(user, "id", 0) or 0)
        if not user_id or not results:
            return 0
        today = local_today(timezone_offset_minutes)

        # Bitta so'z bir necha marta kelsa — XATO ustun turadi. O'quvchi bir
        # sessiyada urinib, oxirida chiqargan bo'lsa ham so'z zaif hisoblanadi.
        merged: dict[str, bool] = {}
        for item in results[:100]:
            if not isinstance(item, dict):
                continue
            zh = str(item.get("hanzi") or "").strip()
            if not zh or not word_position(zh):
                # Server lug'atida yo'q — mijoz o'ylab topgan bo'lishi mumkin.
                continue
            correct = bool(item.get("correct"))
            merged[zh] = correct if zh not in merged else (merged[zh] and correct)
        if not merged:
            return 0

        try:
            rows = await self._all_rows(user_id, skill)
            for zh, correct in merged.items():
                row = rows.get(zh)
                if row is None:
                    row = CourseWordMastery(
                        user_id=user_id,
                        skill=skill,
                        zh=zh,
                        box=0,
                        due_on=today,
                        correct_count=0,
                        wrong_count=0,
                        last_result_at=datetime.now(timezone.utc),
                    )
                    # Yangi yozuv har doim "muddati kelgan" holatda boshlanadi,
                    # shuning uchun birinchi to'g'ri javob uni 1-boxga ko'taradi.
                    self.session.add(row)
                self._schedule(row, correct=correct, today=today)
            await self.session.flush()
        except Exception:  # noqa: BLE001 — natija yozuvi mashqni yiqitmasin
            logger.exception("Word mastery write failed for user %s", user_id)
            return 0
        return len(merged)
