"""Dars ichidagi shaxsiy takror (UIUX-007 / COURSE-ADAPTIVE-001).

Oddiy dars ochilganda server o'quvchining SERVERDA TEKSHIRILGAN xatolaridan
0-3 ta qo'shimcha savol tanlaydi. Klient ularni oddiy kartalar orasida
ko'rsatadi, javobni esa shu modul saqlangan snapshot bo'yicha baholaydi.

Asosiy qoidalar:
- Manba: `course_mistake_targets` (Xatolarim bilan bitta yozuv) + uning
  `course_mistakes` dalil qatorlari. Ikkinchi xato jadvali yoki SRS yo'q:
  interval qoidasi `course_word_mastery_service.schedule_box`.
- Ko'nikma alohida: ma'no, ieroglif, pinyin/ton, tinglash, grammatika.
- Natija FAQAT shaxsiy takror holatiga yoziladi: dars bali, XP, yurak,
  streak, unlock, progress, CourseAttempt, yakunlash o'zgarmaydi.
- Har qanday nosozlikda reja bo'sh qaytadi va dars odatdagidek davom etadi.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.db.models.course_adaptive_plan import CourseAdaptivePlan
from app.db.models.course_mistake import CourseMistake
from app.db.models.course_mistake_target import CourseMistakeTarget
from app.db.models.course_word_mastery import WORD_MASTERY_INTERVALS, WORD_MASTERY_MAX_BOX
from app.db.models.user import User
from app.services import mistake_drill_factory as drills
from app.services.account_identity import actual_telegram_id
from app.services.course_adaptive_schedule import FINAL_CHECK_DELAY_DAYS
from app.services.course_levels import is_hsk30_level
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_mistake_target_store import (
    CourseMistakeTargetStore,
    aware,
    drill_target,
    split_csv,
)
from app.services.course_v3_word_index import normalize_level
from app.services.course_word_mastery_service import (
    CourseWordMasteryService,
    local_today,
    schedule_box,
)


logger = logging.getLogger(__name__)

ADAPTIVE_PLAN_VERSION = 1
ADAPTIVE_STATE_VERSION = 1
MAX_ADAPTIVE_ITEMS = 3
NORMAL_REQUIRED_DAYS = 3
DIFFICULT_REQUIRED_DAYS = 4
PLAN_RETENTION_DAYS = 14
# Kecha tuzilgan reja yarim tunda ochiq qolgan dars uchun hali qabul qilinadi.
PLAN_ANSWER_MAX_AGE_DAYS = 1
ACTIVE_CANDIDATES = 40
DUE_CANDIDATES = 40
EVIDENCE_LIMIT = 400
RETIRED_MIN_BOX = 3

ADAPTIVE_SKILLS = ("meaning", "hanzi", "pinyin", "listening", "grammar")
# Server o'z kaliti bilan baholagan manbalar. `recognition`/`memorize` —
# klient baholaydi, `voice` — LLM, `pronunciation` — ASR bali: ular kirmaydi.
VERIFIED_SOURCES = frozenset({"lesson", "test", "training", "challenge", "adaptive"})
ADAPTIVE_SOURCE = "adaptive"

_FORMAT_SKILLS = {
    "meaning": {
        "meaning_guess", "translation_choice", "word_choice", "meaning_choice",
        "sentence_meaning", "quick_quiz", "match_pairs", "translation",
    },
    "hanzi": {"hanzi_choice", "character_choice", "hanzi_from_pinyin", "char_gap"},
    "pinyin": {"pinyin_choice", "listening_pinyin", "tone_choice", "tone"},
    "listening": {
        "listening_choice", "listen_choice", "audio_choice", "sentence_listening",
        "listen_builder", "listen_and_fill",
    },
    "grammar": {
        "sentence_builder", "reverse_builder", "gap_fill", "dialog_cloze",
        "dialog_context", "dialog_choice", "correct_choice", "grammar_correction",
        "word_order", "reorder", "sentence_reorder",
    },
}
_CATEGORY_SKILL = {
    "grammar": "grammar",
    "character": "hanzi",
    "pronunciation": "pinyin",
    "word": "meaning",
}
# Ko'nikmani aynan tekshiradigan mashq turlari (nishon turi bo'yicha).
SKILL_FORMATS = {
    "word": {
        "meaning": ("meaning_choice",),
        "hanzi": ("hanzi_choice", "hanzi_from_pinyin"),
        "pinyin": ("pinyin_choice", "listening_pinyin"),
        "listening": ("listening_choice", "listening_pinyin"),
        "grammar": ("gap_fill", "hanzi_choice", "meaning_choice"),
    },
    "sentence": {
        "meaning": ("sentence_meaning",),
        "hanzi": ("gap_fill", "correct_choice"),
        "pinyin": ("sentence_listening",),
        "listening": ("sentence_listening", "listen_builder"),
        "grammar": ("gap_fill", "dialog_choice", "correct_choice", "sentence_builder"),
    },
}


class AdaptiveRequestError(ValueError):
    def __init__(self, code: str, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


# ------------------------------------------------------------ pure helpers ---

def skill_for(material_format: str | None, category: str | None) -> str:
    fmt = str(material_format or "").strip().lower()
    for skill, formats in _FORMAT_SKILLS.items():
        if fmt in formats:
            return skill
    return _CATEGORY_SKILL.get(str(category or "").strip().lower(), "meaning")


def required_days(total_wrong: int) -> int:
    return DIFFICULT_REQUIRED_DAYS if int(total_wrong or 0) >= 2 else NORMAL_REQUIRED_DAYS


def track_for(level: str | None) -> str:
    return "hsk30" if is_hsk30_level(level) else "hsk20"


def load_state(raw) -> dict:
    try:
        state = json.loads(raw or "{}") if not isinstance(raw, dict) else raw
    except (TypeError, ValueError):
        state = {}
    if not isinstance(state, dict) or state.get("v") != ADAPTIVE_STATE_VERSION:
        state = {"v": ADAPTIVE_STATE_VERSION}
    skills = state.get("skills")
    state["skills"] = {
        name: dict(value)
        for name, value in (skills.items() if isinstance(skills, dict) else [])
        if name in ADAPTIVE_SKILLS and isinstance(value, dict)
    }
    if not isinstance(state.get("final"), dict):
        state.pop("final", None)
    return state


def dump_state(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _day(value, default: date) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return default


def _moment(value) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return aware(parsed)


def new_skill(today: date, *, need: int, evidence_at: str) -> dict:
    return {
        "phase": "active",
        "box": 0,
        "due": today.isoformat(),
        "ok_days": [],
        "need": int(need),
        "wrong": 0,
        "evidence_at": evidence_at,
        "last_day": None,
    }


def restart_skill(skill: dict, today: date, *, need: int) -> None:
    skill.update(
        phase="active",
        box=0,
        due=today.isoformat(),
        ok_days=[],
        need=max(int(need), int(skill.get("need") or NORMAL_REQUIRED_DAYS)),
    )
    skill.pop("retired_on", None)


def derive_skills(
    state: dict,
    evidence: dict[str, dict],
    *,
    category: str,
    fallback_seen_at: datetime | None,
    today: date,
) -> bool:
    """Tasdiqlangan dalildan ko'nikma holatini yaratadi yoki qayta boshlaydi.

    `evidence`: {skill: {"wrong": int, "seen_at": datetime}}. Dalil qatori yo'q
    (eski nishon) bo'lsa kategoriya bo'yicha bitta ko'nikma olinadi. Dalil
    holatdagi `evidence_at` dan YANGI bo'lsa — yangi tasdiqlangan xato: o'sha
    ko'nikma sikli qayta boshlanadi. Faqat FAOL nishonlar uchun chaqiriladi.
    """
    if not evidence:
        if fallback_seen_at is None:
            return False
        evidence = {_CATEGORY_SKILL.get(category, "meaning"): {"wrong": 1, "seen_at": fallback_seen_at}}
    changed = False
    skills = state.setdefault("skills", {})
    for name, item in evidence.items():
        seen_at = aware(item.get("seen_at"))
        if name not in ADAPTIVE_SKILLS or seen_at is None:
            continue
        wrong = int(item.get("wrong") or 0)
        current = skills.get(name)
        if current is None:
            skills[name] = new_skill(today, need=required_days(wrong), evidence_at=seen_at.isoformat())
            changed = True
            continue
        known = _moment(current.get("evidence_at"))
        if known is None or seen_at > known:
            restart_skill(current, today, need=required_days(wrong + int(current.get("wrong") or 0)))
            current["evidence_at"] = seen_at.isoformat()
            changed = True
    return changed


def due_on(state: dict) -> date | None:
    days = []
    for skill in state.get("skills", {}).values():
        try:
            days.append(date.fromisoformat(str(skill.get("due"))))
        except (TypeError, ValueError):
            continue
    return min(days) if days else None


def _retire(skill: dict, today: date) -> None:
    skill["phase"] = "retired"
    skill.setdefault("retired_on", today.isoformat())
    box = max(int(skill.get("box") or 0), RETIRED_MIN_BOX)
    box = min(box, WORD_MASTERY_MAX_BOX)
    skill["box"] = box
    due = _day(skill.get("due"), today)
    skill["due"] = max(due, today + timedelta(days=WORD_MASTERY_INTERVALS[box])).isoformat()


def apply_answer(
    state: dict,
    *,
    skill: str,
    kind: str,
    correct: bool,
    today: date,
    evidence_at: str,
    clear_at: str | None = None,
) -> dict:
    """Bitta tekshirilgan javobni holatga yozadi. Natija bayroqlari qaytadi.

    - To'g'ri javob mustaqil hisoblanadi faqat ko'nikma muddati kelgan va shu
      mahalliy kunda hali sanalmagan bo'lsa (bir kunda takror progress bermaydi).
    - `need` (3 yoki 4) ta mustaqil kun — faol takrordan chiqadi, lekin uzoq
      muddatli intervalda (7 -> 21 kun) qoladi.
    - Xato — o'sha ko'nikma qayta boshlanadi va endi 4 kun talab qiladi.
    """
    skills = state.setdefault("skills", {})
    current = skills.get(skill)
    if current is None:
        current = new_skill(today, need=NORMAL_REQUIRED_DAYS, evidence_at=evidence_at)
        skills[skill] = current
    today_key = today.isoformat()
    result = {"counted": False, "relearned": False, "retired": False}
    was_due = _day(current.get("due"), today) <= today
    if correct:
        ok_days = [str(value) for value in current.get("ok_days") or []]
        if was_due and current.get("last_day") != today_key and today_key not in ok_days:
            ok_days.append(today_key)
            result["counted"] = True
        current["ok_days"] = ok_days[-DIFFICULT_REQUIRED_DAYS:]
        box, due = schedule_box(
            int(current.get("box") or 0), _day(current.get("due"), today), correct=True, today=today
        )
        current["box"], current["due"] = box, due.isoformat()
        need = int(current.get("need") or NORMAL_REQUIRED_DAYS)
        if current.get("phase") != "retired" and len(current["ok_days"]) >= need:
            _retire(current, today)
            result["retired"] = True
        if kind == "final_check":
            for other in skills.values():
                if other.get("phase") != "retired":
                    _retire(other, today)
                    result["retired"] = True
    else:
        current["wrong"] = int(current.get("wrong") or 0) + 1
        restart_skill(current, today, need=DIFFICULT_REQUIRED_DAYS)
        current["evidence_at"] = evidence_at
        result["relearned"] = True
    current["last_day"] = today_key
    if kind == "final_check" and clear_at:
        state["final"] = {"clear_at": clear_at, "status": "passed" if correct else "failed"}
    return result


def rollout_bucket(user_id: int) -> int:
    digest = hashlib.sha256(f"course-adaptive:{int(user_id)}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def placement_slots(eligible: list[int], count: int) -> list[int]:
    """Mos chegaralar ichidan `count` tasini teng taqsimlab tanlaydi.

    Klientlar (PWA va Android) shu qoidaning nusxasini ishlatadi; bu yerdagi
    funksiya kontrakt testlari uchun manba.
    """
    if count <= 0 or not eligible:
        return []
    count = min(count, len(eligible))
    picked = []
    for index in range(count):
        position = (index + 1) * len(eligible) // (count + 1)
        position = min(max(position, 0), len(eligible) - 1)
        while eligible[position] in picked and position < len(eligible) - 1:
            position += 1
        if eligible[position] not in picked:
            picked.append(eligible[position])
    return picked


def _token(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:200]


def _grade(question: dict, answer) -> tuple[bool, dict] | None:
    """Snapshot bo'yicha baholash. Yaroqsiz javob — `None`."""
    tokens = question.get("tokens")
    if isinstance(tokens, list) and tokens:
        if not isinstance(answer, list):
            return None
        # Xatolarim baholash qoidasi bilan bir xil normallashtirish.
        selected = [_token(value) for value in answer[:30]]
        tokens = [_token(value) for value in tokens[:30]]
        expected = [_token(value) for value in (question.get("answer_tokens") or [])[:30]]
        if (
            not selected
            or any(not value for value in selected)
            or len(selected) != len(tokens)
            or sorted(selected) != sorted(tokens)
            or sorted(expected) != sorted(tokens)
        ):
            return None
        correct = selected == expected
        return correct, {
            "answer_type": "tokens",
            "selected_tokens": selected,
            "correct": correct,
            "correct_answer": str(question.get("correct_answer") or "".join(expected))[:700],
            "explanation": str(question.get("explanation") or "")[:600],
        }
    options = question.get("options")
    if isinstance(answer, bool) or not isinstance(options, list):
        return None
    try:
        selected_index = int(answer)
        correct_index = int(question.get("answer_index"))
    except (TypeError, ValueError):
        return None
    if not 0 <= selected_index < len(options) or not 0 <= correct_index < len(options):
        return None
    correct = selected_index == correct_index
    return correct, {
        "answer_type": "choice",
        "selected_index": selected_index,
        "correct_index": correct_index,
        "correct": correct,
        "correct_answer": str(options[correct_index])[:700],
        "explanation": str(question.get("explanation") or "")[:600],
    }


def _public_feedback(item_id: str, stored: dict) -> dict:
    feedback = {
        "item_id": item_id,
        "correct": bool(stored.get("correct")),
        "correct_answer": stored.get("correct_answer") or "",
        "explanation": stored.get("explanation") or "",
    }
    if stored.get("answer_type") == "tokens":
        feedback["selected_tokens"] = list(stored.get("selected_tokens") or [])
    else:
        feedback["selected_index"] = stored.get("selected_index")
        feedback["correct_index"] = stored.get("correct_index")
    return feedback


# ------------------------------------------------------------------ service ---

class CourseAdaptiveLessonService:
    def __init__(self, session, settings_obj):
        self.session = session
        self.settings = settings_obj
        self.targets = CourseMistakeTargetStore(session)

    # ---------- rollout ----------

    def _enabled_for(self, user_id: int) -> bool:
        if not bool(getattr(self.settings, "COURSE_ADAPTIVE_ENABLED", False)):
            return False
        allow = {
            part.strip()
            for part in str(getattr(self.settings, "COURSE_ADAPTIVE_ALLOWLIST", "") or "").split(",")
            if part.strip()
        }
        if str(int(user_id)) in allow:
            return True
        try:
            percent = int(getattr(self.settings, "COURSE_ADAPTIVE_ROLLOUT_PERCENT", 100))
        except (TypeError, ValueError):
            percent = 0
        return rollout_bucket(user_id) < max(0, min(100, percent))

    def _shadow(self) -> bool:
        return bool(getattr(self.settings, "COURSE_ADAPTIVE_SHADOW_ENABLED", False))

    # ---------- request validation ----------

    @staticmethod
    def _formats(formats) -> frozenset:
        if not isinstance(formats, list):
            return frozenset()
        declared = {str(value or "").strip()[:40] for value in formats[:40]}
        return frozenset(declared) & drills.ALL_FORMATS

    @staticmethod
    def _language(user, language: str | None) -> str:
        for value in (language, getattr(user, "language", None)):
            normalized = str(value or "").strip().lower()
            if normalized in {"tg", "tg-cyrl"}:
                normalized = "tj"
            if normalized in {"uz", "ru", "tj"}:
                return normalized
        return "uz"

    async def _lesson_context(self, user, level: str, lesson_order) -> tuple[str, int, int]:
        """O'quvchining joriy kursi va shu darsga yetib kelganini tekshiradi."""
        try:
            lesson_order = int(lesson_order)
        except (TypeError, ValueError) as exc:
            raise AdaptiveRequestError("adaptive_request_invalid") from exc
        requested = str(level or "").strip().lower()
        if lesson_order <= 0 or not requested:
            raise AdaptiveRequestError("adaptive_request_invalid")
        current_level, current_part, offset = await CourseWordMasteryService(self.session).context(user)
        if normalize_level(requested) != requested or requested != current_level:
            raise AdaptiveRequestError("adaptive_context_changed", status_code=409)
        if lesson_order > current_part:
            raise AdaptiveRequestError("adaptive_lesson_unavailable", status_code=403)
        return current_level, lesson_order, offset

    async def _lock_user(self, user_id: int) -> None:
        await self.session.execute(select(User.id).where(User.id == user_id).with_for_update())

    # ---------- candidate loading ----------

    async def _candidates(self, user_id: int, track: str, today: date) -> list[CourseMistakeTarget]:
        """Ikki chegaralangan so'rov: faol Xatolarim nishonlari va muddati kelganlar.

        Xatolarimda yopilgan nishon `adaptive_due_on = yopilgan kun + 3` oladi
        (qarang `course_adaptive_schedule`), shuning uchun yakuniy tekshiruv
        ham "muddati kelgan" so'rovidan keladi — alohida skan yo'q.
        """
        rows: dict[int, CourseMistakeTarget] = {}
        for row in await self.targets.active(user_id, limit=ACTIVE_CANDIDATES, track=track):
            rows[int(row.id)] = row
        due_query = CourseMistakeTargetStore._track_filter(
            select(CourseMistakeTarget).where(
                CourseMistakeTarget.user_id == user_id,
                CourseMistakeTarget.adaptive_due_on.is_not(None),
                CourseMistakeTarget.adaptive_due_on <= today,
            ),
            CourseMistakeTarget.level,
            track,
        ).order_by(CourseMistakeTarget.adaptive_due_on.asc(), CourseMistakeTarget.id.asc())
        for row in (await self.session.execute(due_query.limit(DUE_CANDIDATES))).scalars().all():
            rows.setdefault(int(row.id), row)
        return [row for row in rows.values() if row.kind in SKILL_FORMATS]

    async def _evidence(self, user_id: int, rows: list[CourseMistakeTarget]) -> dict[int, list[dict]]:
        """Nishonlarga bog'langan TASDIQLANGAN xato qatorlari (bitta so'rov)."""
        by_key = {(row.category, row.target_key): int(row.id) for row in rows}
        if not by_key:
            return {}
        result = await self.session.execute(
            select(
                CourseMistake.category,
                CourseMistake.target_key,
                CourseMistake.source,
                CourseMistake.material_json,
                CourseMistake.wrong_count,
                CourseMistake.last_seen_at,
                CourseMistake.level,
                CourseMistake.lesson_order,
            )
            .where(
                CourseMistake.user_id == user_id,
                CourseMistake.target_key.in_([key for _, key in by_key]),
            )
            .limit(EVIDENCE_LIMIT)
        )
        evidence: dict[int, list[dict]] = {}
        for category, key, source, material_json, wrong, seen_at, level, lesson_order in result.all():
            target_id = by_key.get((category, key))
            if target_id is None or str(source or "") not in VERIFIED_SOURCES:
                continue
            try:
                material = json.loads(material_json or "{}")
            except (TypeError, ValueError):
                material = {}
            fmt = material.get("format") if isinstance(material, dict) else None
            if (
                source == "test" and fmt == "text_choice"
                and len(re.findall(r"_{2,}", str(material.get("sentence") or ""))) == 1
            ):
                fmt = "gap_fill"  # The verified error was choosing a word in context.
            evidence.setdefault(target_id, []).append(
                {
                    "skill": skill_for(fmt, category),
                    "wrong": int(wrong or 1),
                    "seen_at": aware(seen_at),
                    "level": str(level or ""),
                    "lesson_order": int(lesson_order or 0),
                }
            )
        return evidence

    @staticmethod
    def _verified_target(row: CourseMistakeTarget, rows: list[dict]) -> bool:
        return bool(rows) or bool(set(split_csv(row.sources)) & VERIFIED_SOURCES)

    # ---------- selection ----------

    def _select(
        self,
        rows: list[CourseMistakeTarget],
        evidence: dict[int, list[dict]],
        *,
        level: str,
        lesson_order: int,
        today: date,
        now: datetime,
        language: str,
        formats: frozenset,
        seed: str,
    ) -> tuple[list[dict], dict[int, dict]]:
        """(reja elementlari, o'zgargan holatlar). Yozish chaqiruvchida."""
        states: dict[int, dict] = {}
        changed: dict[int, dict] = {}
        candidates = []
        today_key = today.isoformat()
        for row in rows:
            target_id = int(row.id)
            rows_evidence = evidence.get(target_id, [])
            if not self._verified_target(row, rows_evidence):
                continue
            state = load_state(row.adaptive_state_json)
            states[target_id] = state
            if row.status == "active":
                grouped: dict[str, dict] = {}
                for item in rows_evidence:
                    bucket = grouped.setdefault(item["skill"], {"wrong": 0, "seen_at": None})
                    bucket["wrong"] += item["wrong"]
                    if bucket["seen_at"] is None or item["seen_at"] > bucket["seen_at"]:
                        bucket["seen_at"] = item["seen_at"]
                fallback = aware(row.last_seen_at) if not rows_evidence else None
                if derive_skills(state, grouped, category=row.category, fallback_seen_at=fallback, today=today):
                    changed[target_id] = state
            # Faqat shu darsning o'zidagi xato — bu darsda allaqachon takrorlanadi.
            if rows_evidence and all(
                item["level"] == level and item["lesson_order"] == lesson_order for item in rows_evidence
            ):
                continue
            final = state.get("final") or {}
            cleared_at = aware(row.cleared_at)
            if (
                row.status == "cleared"
                and cleared_at is not None
                and final.get("clear_at") != cleared_at.isoformat()
            ):
                # Xatolarimda yopilgan: avval yakuniy tekshiruv, oraliqda
                # oddiy takror yo'q. 3 kun to'lmagan bo'lsa — kutadi.
                if cleared_at <= now - timedelta(days=FINAL_CHECK_DELAY_DAYS):
                    skill = self._final_skill(row, state, rows_evidence)
                    if (state["skills"].get(skill) or {}).get("last_day") != today_key:
                        candidates.append(((0, cleared_at.isoformat(), target_id), row, skill, "final_check"))
                continue
            for name, skill_state in state["skills"].items():
                if skill_state.get("last_day") == today_key:
                    continue
                if _day(skill_state.get("due"), today + timedelta(days=1)) > today:
                    continue
                if skill_state.get("phase") == "retired":
                    key = (2, skill_state.get("due") or "", int(skill_state.get("box") or 0), target_id)
                    candidates.append((key, row, name, "maintenance"))
                else:
                    key = (
                        1,
                        -int(skill_state.get("need") or NORMAL_REQUIRED_DAYS),
                        skill_state.get("due") or "",
                        int(skill_state.get("box") or 0),
                        -int(skill_state.get("wrong") or 0),
                        target_id,
                    )
                    candidates.append((key, row, name, "review"))
        candidates.sort(key=lambda entry: entry[0])

        items: list[dict] = []
        used: set[int] = set()
        for _, row, skill, kind in candidates:
            if len(items) >= MAX_ADAPTIVE_ITEMS:
                break
            target_id = int(row.id)
            if target_id in used:
                continue
            question = self._question(row, skill, states[target_id], language=language, formats=formats, seed=seed)
            if question is None:
                continue
            used.add(target_id)
            slot = len(items) + 1
            item_id = f"a{slot}:{target_id}:{question['format']}"[:120]
            question["id"] = item_id
            item = {
                "id": item_id,
                "slot": slot,
                "kind": kind,
                "skill": skill,
                "target_id": target_id,
                "question": question,
            }
            if kind == "final_check":
                item["clear_at"] = aware(row.cleared_at).isoformat()
            items.append(item)
        return items, changed

    @staticmethod
    def _final_skill(row: CourseMistakeTarget, state: dict, rows_evidence: list[dict]) -> str:
        weights: dict[str, int] = {}
        for item in rows_evidence:
            weights[item["skill"]] = weights.get(item["skill"], 0) + item["wrong"]
        for name, skill_state in state.get("skills", {}).items():
            weights[name] = weights.get(name, 0) + int(skill_state.get("wrong") or 0)
        if weights:
            return sorted(weights.items(), key=lambda entry: (-entry[1], entry[0]))[0][0]
        return _CATEGORY_SKILL.get(row.category, "meaning")

    @staticmethod
    def _question(
        row: CourseMistakeTarget,
        skill: str,
        state: dict,
        *,
        language: str,
        formats: frozenset,
        seed: str,
    ) -> dict | None:
        options = list(SKILL_FORMATS.get(row.kind, {}).get(skill, ()))
        if not options:
            return None
        skill_state = state.get("skills", {}).get(skill) or {}
        start = (len(skill_state.get("ok_days") or []) + int(skill_state.get("box") or 0)) % len(options)
        target = drill_target(row)
        for fmt in options[start:] + options[:start]:
            if fmt not in formats:
                continue
            question = drills.build_question(target, fmt, language=language, seed=seed)
            if question and question.get("format") == fmt and drills.client_supports(question, formats):
                return question
        return None

    # ---------- public API ----------

    @staticmethod
    def _plan_key(level: str, lesson_order: int, today: date, language: str, formats: frozenset) -> str:
        digest = hashlib.sha256(",".join(sorted(formats)).encode("utf-8")).hexdigest()[:10]
        return f"{level}:{int(lesson_order)}:{today.isoformat()}:{language}:{digest}"

    @staticmethod
    def _public_plan(plan: CourseAdaptivePlan) -> dict:
        items = json.loads(plan.items_json or "[]")
        answers = json.loads(plan.answers_json or "{}")
        public = []
        for item in items:
            stored = answers.get(item["id"])
            entry = {
                "id": item["id"],
                "slot": int(item["slot"]),
                "kind": "final_check" if item.get("kind") == "final_check" else "review",
                "skill": item["skill"],
                "question": drills.public_question(item["question"]),
                "answered": stored is not None,
            }
            if stored is not None:
                entry["feedback"] = _public_feedback(item["id"], stored)
            public.append(entry)
        return {
            "id": int(plan.id),
            "version": int(plan.contract_version),
            "level": plan.level,
            "lesson_order": int(plan.lesson_order),
            "items": public,
        }

    async def plan(
        self,
        user,
        *,
        level: str,
        lesson_order,
        formats=None,
        language: str | None = None,
        analytics_client: str | None = None,
    ) -> dict:
        disabled = {"ok": True, "enabled": False, "plan": None}
        if not user or not getattr(user, "id", None):
            raise AdaptiveRequestError("access_start_first", status_code=403)
        enabled = self._enabled_for(int(user.id))
        if not enabled and not self._shadow():
            return disabled
        level, lesson_order, offset = await self._lesson_context(user, level, lesson_order)
        client_formats = self._formats(formats)
        language = self._language(user, language)
        today = local_today(offset)
        now = datetime.now(timezone.utc)
        plan_key = self._plan_key(level, lesson_order, today, language, client_formats)
        if not enabled:
            await self._shadow_plan(user, level, lesson_order, today, now, language, client_formats, plan_key, analytics_client)
            return disabled
        if not client_formats:
            return disabled

        await self._lock_user(int(user.id))
        existing = await self._existing(int(user.id), plan_key)
        if existing is not None:
            return {"ok": True, "enabled": True, "plan": self._public_plan(existing)}

        track = track_for(level)
        rows = await self._candidates(int(user.id), track, today)
        evidence = await self._evidence(int(user.id), rows)
        items, changed = self._select(
            rows,
            evidence,
            level=level,
            lesson_order=lesson_order,
            today=today,
            now=now,
            language=language,
            formats=client_formats,
            seed=f"adaptive:{int(user.id)}:{plan_key}",
        )
        by_id = {int(row.id): row for row in rows}
        for target_id, state in changed.items():
            row = by_id[target_id]
            row.adaptive_state_json = dump_state(state)
            row.adaptive_due_on = due_on(state)

        await self.session.execute(
            delete(CourseAdaptivePlan).where(
                CourseAdaptivePlan.user_id == int(user.id),
                CourseAdaptivePlan.local_day < today - timedelta(days=PLAN_RETENTION_DAYS),
            )
        )
        plan = CourseAdaptivePlan(
            user_id=int(user.id),
            plan_key=plan_key,
            level=level,
            lesson_order=lesson_order,
            local_day=today,
            contract_version=ADAPTIVE_PLAN_VERSION,
            language=language,
            items_json=json.dumps(items, ensure_ascii=False, separators=(",", ":")),
            answers_json="{}",
        )
        try:
            async with self.session.begin_nested():
                self.session.add(plan)
                await self.session.flush()
        except IntegrityError:
            # Bir vaqtda ikkinchi so'rov — o'sha rejani qaytaramiz.
            existing = await self._existing(int(user.id), plan_key)
            if existing is None:
                raise
            await self.session.commit()
            return {"ok": True, "enabled": True, "plan": self._public_plan(existing)}
        if items:
            await CourseMiniAppAnalyticsService(self.session).record_server_event(
                event_name="adaptive_assigned",
                telegram_id=actual_telegram_id(user),
                user_id=int(user.id),
                source="course_adaptive",
                level=level,
                lesson_order=lesson_order,
                dedupe_key=f"adaptive:{int(plan.id)}:assigned",
                payload={
                    "plan_version": ADAPTIVE_PLAN_VERSION,
                    "count": len(items),
                    "skills": [item["skill"] for item in items],
                    "kinds": [item["kind"] for item in items],
                },
                analytics_client=analytics_client,
            )
        await self.session.commit()
        return {"ok": True, "enabled": True, "plan": self._public_plan(plan)}

    async def _existing(self, user_id: int, plan_key: str) -> CourseAdaptivePlan | None:
        result = await self.session.execute(
            select(CourseAdaptivePlan).where(
                CourseAdaptivePlan.user_id == user_id,
                CourseAdaptivePlan.plan_key == plan_key,
            )
        )
        return result.scalar_one_or_none()

    async def _shadow_plan(self, user, level, lesson_order, today, now, language, formats, plan_key, analytics_client) -> None:
        """Faqat hisob: holat yozilmaydi, klientga hech narsa bormaydi."""
        # Rollback ORM obyektlarini eskirtiradi — identifikatorlar oldindan olinadi.
        user_id, telegram_id = int(user.id), actual_telegram_id(user)
        try:
            rows = await self._candidates(user_id, track_for(level), today)
            evidence = await self._evidence(user_id, rows)
            items, _ = self._select(
                rows,
                evidence,
                level=level,
                lesson_order=lesson_order,
                today=today,
                now=now,
                language=language,
                formats=formats or drills.CHOICE_FORMATS,
                seed=f"adaptive:{user_id}:{plan_key}",
            )
            # Tanlov ORM obyektlarini o'zgartirmaydi, lekin ehtiyot uchun tashlaymiz.
            await self.session.rollback()
            await CourseMiniAppAnalyticsService(self.session).record_server_event(
                event_name="adaptive_shadow_planned",
                telegram_id=telegram_id,
                user_id=user_id,
                source="course_adaptive",
                level=level,
                lesson_order=lesson_order,
                dedupe_key=f"adaptive-shadow:{plan_key}"[:120],
                payload={
                    "count": len(items),
                    "skills": [item["skill"] for item in items],
                    "kinds": [item["kind"] for item in items],
                },
                analytics_client=analytics_client,
            )
            await self.session.commit()
        except Exception:  # noqa: BLE001 — shadow hech qachon darsga ta'sir qilmaydi
            logger.exception("Adaptive shadow plan failed for user %s", user_id)
            await self.session.rollback()

    async def answer(
        self,
        user,
        *,
        plan_id,
        item_id: str,
        answer,
        analytics_client: str | None = None,
    ) -> dict:
        if not user or not getattr(user, "id", None):
            raise AdaptiveRequestError("access_start_first", status_code=403)
        if not bool(getattr(self.settings, "COURSE_ADAPTIVE_ENABLED", False)):
            raise AdaptiveRequestError("adaptive_disabled", status_code=409)
        try:
            plan_id = int(plan_id)
        except (TypeError, ValueError) as exc:
            raise AdaptiveRequestError("adaptive_request_invalid") from exc
        item_id = str(item_id or "").strip()[:120]
        if plan_id <= 0 or not item_id:
            raise AdaptiveRequestError("adaptive_request_invalid")

        user_id = int(user.id)
        await self._lock_user(user_id)
        plan = (
            await self.session.execute(
                select(CourseAdaptivePlan)
                .where(CourseAdaptivePlan.id == plan_id, CourseAdaptivePlan.user_id == user_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if plan is None:
            raise AdaptiveRequestError("adaptive_plan_not_found", status_code=404)
        _, _, offset = await CourseWordMasteryService(self.session).context(user)
        today = local_today(offset)
        if track_for(plan.level) != track_for(getattr(user, "level", None)):
            raise AdaptiveRequestError("adaptive_context_changed", status_code=409)
        if plan.local_day < today - timedelta(days=PLAN_ANSWER_MAX_AGE_DAYS):
            raise AdaptiveRequestError("adaptive_plan_stale", status_code=409)

        items = {item["id"]: item for item in json.loads(plan.items_json or "[]")}
        item = items.get(item_id)
        if item is None:
            raise AdaptiveRequestError("adaptive_answer_invalid")
        answers = json.loads(plan.answers_json or "{}")
        if item_id in answers:
            await self.session.commit()
            return {"ok": True, **_public_feedback(item_id, answers[item_id]), "duplicate": True}

        graded = _grade(item["question"], answer)
        if graded is None:
            raise AdaptiveRequestError("adaptive_answer_invalid")
        correct, stored = graded
        now = datetime.now(timezone.utc)

        flags = {"counted": False, "relearned": False, "retired": False}
        row = (
            await self.targets.by_ids(user_id, [int(item["target_id"])], lock=True)
        ).get(int(item["target_id"]))
        if row is not None:
            state = load_state(row.adaptive_state_json)
            flags = apply_answer(
                state,
                skill=item["skill"],
                kind=item.get("kind") or "review",
                correct=correct,
                today=today,
                evidence_at=now.isoformat(),
                clear_at=item.get("clear_at"),
            )
            if not correct:
                # Yangi tasdiqlangan xato — Xatolarimdagi mavjud qoida bilan
                # bir xil: nishon qayta ochiladi va progressi nolga tushadi.
                await self.targets.upsert(
                    user_id,
                    category=row.category,
                    target={
                        "kind": row.kind,
                        "key": row.target_key,
                        "zh": row.zh,
                        "level": row.level,
                        "payload": {},
                    },
                    source=ADAPTIVE_SOURCE,
                    now=now,
                )
            row.adaptive_state_json = dump_state(state)
            row.adaptive_due_on = due_on(state)
            # Yakuniy tekshiruvda so'z Xatolarim yopganda allaqachon o'tkazilgan.
            if flags["retired"] and row.kind == "word" and item.get("kind") != "final_check":
                await self._hand_off(user, row)

        stored["at"] = now.isoformat()
        stored["counted"] = bool(flags["counted"])
        answers[item_id] = stored
        plan.answers_json = json.dumps(answers, ensure_ascii=False, separators=(",", ":"))
        await self.session.flush()
        await CourseMiniAppAnalyticsService(self.session).record_server_event(
            event_name="adaptive_answer_verified",
            telegram_id=actual_telegram_id(user),
            user_id=user_id,
            source="course_adaptive",
            level=plan.level,
            lesson_order=int(plan.lesson_order),
            dedupe_key=f"adaptive:{int(plan.id)}:{item_id}"[:120],
            payload={
                "skill": item["skill"],
                "kind": item.get("kind") or "review",
                "format": item["question"].get("format"),
                "correct": bool(correct),
                **flags,
            },
            analytics_client=analytics_client,
        )
        await self.session.commit()
        return {"ok": True, **_public_feedback(item_id, stored), "duplicate": False}

    async def _hand_off(self, user, row: CourseMistakeTarget) -> None:
        """Faol takrordan chiqqan so'z uzoq muddatli so'z mashqiga ham o'tadi."""
        from app.services.course_mistake_service import CourseMistakeService

        try:
            await CourseMistakeService(self.session)._hand_off_to_word_mastery(user, [row])
        except Exception:  # noqa: BLE001 — qo'shimcha yozuv javobni yiqitmasin
            logger.exception("Adaptive word mastery hand-off failed for user %s", getattr(user, "id", None))
