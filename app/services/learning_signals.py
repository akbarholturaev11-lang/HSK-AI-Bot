"""Kunlik reja uchun O'QUV SIGNALLARI — faqat o'qish, qaror yo'q.

Bu qatlam hech narsa hal qilmaydi va hech narsa yozmaydi. U mavjud
jadvallardan (`course_progress`, `course_mistakes`, `course_xp_events`,
`course_miniapp_profiles`) bitta ko'rinish yig'adi, `DailyPlanService` esa
shu ko'rinish ustida qaror qabul qiladi.

Ataylab BU YERDA YO'Q:
- kirish/limit tekshiruvi — u `CourseMiniAppAccessService` da qoladi. Ikkinchi
  gating implementatsiyasi paydo bo'lsa, "Known Problem 3" takrorlanardi;
- reja qurish qoidalari — ular `DailyPlanService` da.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import func, select

from app.db.models.course_mistake import CourseMistake
from app.db.models.course_xp_event import CourseXpEvent
from app.services.course_daily_window import local_day_key
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.course_v3_parts import current_part, total_parts


logger = logging.getLogger(__name__)

# Zaiflik o'lchovlari. `course_mistakes.category` da to'rttasi bor; TINGLASH
# alohida ustun EMAS — u `material_json.format` dan chiqariladi, shuning uchun
# migratsiya kerak emas (qarang ARCHITECTURE_DECISION.md).
WEAKNESS_KEYS = ("word", "grammar", "character", "pronunciation", "listening")
LISTENING_FORMATS = {"listening_choice", "listen_and_fill", "listening"}

# `course_xp_events` dagi O'RGANISH turlari. `reward_chest`, `challenge_win` va
# `challenge_tie` sovg'a/gamifikatsiya yozuvlari — sur'atni ular bo'yicha
# o'lchash "sovg'a ochgan kun" ni "o'qigan kun" deb ko'rsatardi.
LEARNING_ACTIVITY_TYPES = (
    "lesson",
    "section",
    "chapter",
    "book_lesson",
    "test",
    "training",
    "mistake_review",
    "voice",
    "challenge",
)

# Zaiflik reytingi uchun namuna hajmi. Reja ANIQ SON emas, TARTIB talab
# qiladi, shuning uchun eng og'ir N ta xato yetarli — butun tarixni o'qish
# `/api/v3/map` yo'lini qimmatlashtirardi.
WEAKNESS_SAMPLE_SIZE = 80

# Prior (o'quvchi aytgan fokus) shuncha o'quv faoliyatidan keyin so'nadi.
EVIDENCE_FULL_TRUST = 10


@dataclass(frozen=True)
class LearningSignals:
    level: str
    goal: str
    daily_minutes: int
    preferred_focus: str | None
    plan_size: int
    daily_goal_xp: int
    completed_parts: int
    current_part: int
    total_parts: int
    local_day: str
    today_xp: int
    streak: int
    mistakes_total: int
    weakness: dict[str, int] = field(default_factory=dict)
    evidence_count: int = 0
    active_days_7: int = 0
    done_refs_today: frozenset[str] = frozenset()
    done_types_today: frozenset[str] = frozenset()

    @property
    def has_next_part(self) -> bool:
        return bool(self.total_parts) and self.current_part <= self.total_parts

    @property
    def prior_weight(self) -> float:
        """Aytilgan fokusning ta'sir kuchi: dalil to'plangan sari so'nadi."""
        if not self.preferred_focus or self.preferred_focus == "none":
            return 0.0
        return max(0.0, 1.0 - (self.evidence_count / EVIDENCE_FULL_TRUST))


class LearningSignalsService:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def _weakness_key(item: CourseMistake) -> str:
        """Xato qaysi zaiflik o'lchoviga tegishli.

        `category` yagona manba, faqat TINGLASH undan chiqmaydi: tinglash
        savollari `word` ga tushadi (CourseMistakeService._category), shuning
        uchun saqlangan material formati bo'yicha ajratamiz.
        """
        category = str(getattr(item, "category", "") or "").strip().lower()
        if category in ("word", "character"):
            raw = getattr(item, "material_json", None)
            if raw:
                try:
                    material = json.loads(raw)
                except (TypeError, ValueError):
                    material = {}
                if isinstance(material, dict):
                    fmt = str(material.get("format") or "").strip().lower()
                    if fmt in LISTENING_FORMATS or material.get("audio_text"):
                        return "listening"
        return category if category in WEAKNESS_KEYS else "word"

    async def _weakness(self, user_id: int) -> dict[str, int]:
        weight = CourseMistake.wrong_count - CourseMistake.resolved_count
        result = await self.session.execute(
            select(
                CourseMistake.category,
                CourseMistake.material_json,
                weight.label("weight"),
            )
            .where(CourseMistake.user_id == user_id, weight > 0)
            .order_by(weight.desc(), CourseMistake.last_seen_at.desc())
            .limit(WEAKNESS_SAMPLE_SIZE)
        )
        scores = {key: 0 for key in WEAKNESS_KEYS}
        for category, material_json, item_weight in result.all():
            item = CourseMistake(category=category, material_json=material_json)
            scores[self._weakness_key(item)] += int(item_weight or 0)
        return scores

    async def _mistakes_total(self, user_id: int) -> int:
        weight = CourseMistake.wrong_count - CourseMistake.resolved_count
        result = await self.session.execute(
            select(func.coalesce(func.sum(weight), 0)).where(
                CourseMistake.user_id == user_id,
                CourseMistake.wrong_count > CourseMistake.resolved_count,
            )
        )
        return int(result.scalar_one() or 0)

    async def _today(self, user_id: int, local_day) -> tuple[int, set[str], set[str]]:
        """Bugun (MAHALLIY kun) bajarilgan ishlar: XP, ref'lar va turlar."""
        result = await self.session.execute(
            select(
                CourseXpEvent.activity_type,
                CourseXpEvent.activity_ref,
                CourseXpEvent.xp,
            ).where(
                CourseXpEvent.user_id == user_id,
                CourseXpEvent.activity_date == local_day,
            )
        )
        today_xp = 0
        refs: set[str] = set()
        types: set[str] = set()
        for activity_type, activity_ref, xp in result.all():
            today_xp += int(xp or 0)
            if activity_ref:
                refs.add(str(activity_ref))
            if activity_type:
                types.add(str(activity_type))
        return today_xp, refs, types

    async def _evidence_and_pace(self, user_id: int, local_day) -> tuple[int, int]:
        """Dalil hajmi (o'quv faoliyatlari soni) va oxirgi 7 kundagi faol kunlar."""
        result = await self.session.execute(
            select(CourseXpEvent.activity_date, CourseXpEvent.activity_type).where(
                CourseXpEvent.user_id == user_id,
                CourseXpEvent.activity_type.in_(LEARNING_ACTIVITY_TYPES),
            )
        )
        rows = result.all()
        evidence = len(rows)
        window_start = local_day - timedelta(days=6)
        active_days = {
            activity_date
            for activity_date, _ in rows
            if activity_date and window_start <= activity_date <= local_day
        }
        return evidence, len(active_days)

    async def load(self, user, *, profile, progress, level: str) -> LearningSignals:
        level = str(level or "hsk1").strip().lower()
        completed = int(getattr(progress, "completed_lessons_count", 0) or 0)
        offset = int(getattr(profile, "timezone_offset_minutes", 0) or 0)
        day_key = local_day_key(offset)
        gamification_day = None
        try:
            from datetime import date as _date

            gamification_day = _date.fromisoformat(day_key)
        except ValueError:  # noqa: PERF203 — kalit har doim ISO, bu himoya
            logger.warning("Bad local day key: %s", day_key)

        weakness = {key: 0 for key in WEAKNESS_KEYS}
        mistakes_total = 0
        today_xp, done_refs, done_types = 0, set(), set()
        evidence, active_days = 0, 0
        user_id = int(getattr(user, "id", 0) or 0)
        if user_id:
            weakness = await self._weakness(user_id)
            mistakes_total = await self._mistakes_total(user_id)
            if gamification_day is not None:
                today_xp, done_refs, done_types = await self._today(user_id, gamification_day)
                evidence, active_days = await self._evidence_and_pace(user_id, gamification_day)

        setup = CourseMiniAppProfileService.study_setup(profile, completed_parts=completed)
        return LearningSignals(
            level=level,
            goal=str(getattr(profile, "goal", "") or "hsk_exam"),
            daily_minutes=int(setup["daily_minutes"]),
            preferred_focus=setup["preferred_focus"],
            plan_size=int(setup["plan_size"]),
            daily_goal_xp=int(setup["daily_goal_xp"]),
            completed_parts=completed,
            current_part=current_part(level, completed),
            total_parts=total_parts(level),
            local_day=day_key,
            today_xp=today_xp,
            streak=int(getattr(profile, "current_streak", 0) or 0),
            mistakes_total=mistakes_total,
            weakness=weakness,
            evidence_count=evidence,
            active_days_7=active_days,
            done_refs_today=frozenset(done_refs),
            done_types_today=frozenset(done_types),
        )
