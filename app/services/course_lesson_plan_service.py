"""Dars rejasi: onboarding uzunligi + rasmli talaffuz kartochkalari (UIUX-008).

Server darsning o'zini O'ZGARTIRMAYDI. U dars JSON'iga `lesson_plan`
qo'shadi, klientlar (PWA/Mini App `course-v3.html` va Android) esa:

* `omit` dagi `(section_no, card_no)` kartalarni ko'rsatmaydi — `material_ref`
  asl pozitsiyadan hisoblanadi, shuning uchun server qayta baholashi va P3
  overlay'lari buzilmaydi;
* `picture_review` so'zlarini bitta dars qadami sifatida, ustma-ust
  kartochkalar ko'rinishida chiqaradi.

Uzunlik o'quvchining onboardingdagi "Kuniga necha daqiqa?" javobiga
(`daily_minutes`) va maqsadiga bog'liq. Faqat `practice`/`retention_review`
dagi qo'shimcha mashqlar qisqartiriladi; yangi so'z o'rgatish, grammatika,
dialog, N1 tekshiruvlari va exit-ticket doim qoladi.

Rasmli kartaga faqat O'RGANILGAN so'zlar kiradi: avval joriy darsning oldingi
qismlari, keyin shu darajaning oldingi darslari. Aniq rasm (tasdiqlangan
`data/lesson_picture_words.json`) topilmagan so'z umuman ishlatilmaydi.

Bu funksiya hech qachon darsni yiqitmaydi: istalgan xato -> reja yo'q ->
klientlar asl darsni ko'rsatadi.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select

from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.services.course_v3_parts import total_parts
from app.services.onboarding_goal_selection import read_onboarding_goals


logger = logging.getLogger(__name__)

PLAN_VERSION = 1
COURSE_V3_DATA_ROOT = Path(__file__).resolve().parents[1] / "static" / "course_v3_data"
PICTURE_WORDS_PATH = Path(__file__).resolve().parent / "data" / "lesson_picture_words.json"

# Onboarding: "Kuniga necha daqiqa vaqtingiz bor?" -> dars qismining
# uzunligi (oddiy karta birliklarida). Bugungi qism 11-18 karta (mediana 18).
UNITS_BY_MINUTES = {5: 14, 10: 18, 15: 21, 20: 24, 30: 27}
PICTURE_CAP_BY_MINUTES = {5: 4, 10: 6, 15: 8, 20: 10, 30: 10}
DEFAULT_MINUTES = 10
MAX_PICTURES = 10

# Maqsad uzunlikni ham suradi: imtihonga tayyorlanuvchi to'liqroq mashq oladi,
# sayohatchi/so'zlashuv — qisqaroq va amaliyroq dars.
GOAL_UNIT_SHIFT = {
    "hsk_exam": 2.0,
    "study_china": 1.0,
    "work_china": 0.0,
    "daily_communication": -1.0,
    "travel": -2.0,
}
DEFAULT_GOAL = "hsk_exam"

# Maqsad -> ko'nikma vazni (0..3). Qiymatlar `DailyPlanService.GOAL_WEIGHTS`
# ruhida: so'zlashuv maqsadlari gapirish/tinglashni, imtihon esa tinglash,
# lug'at va grammatikani ko'taradi.
GOAL_SKILL_WEIGHTS = {
    "hsk_exam": {"listening": 2.6, "vocabulary": 2.4, "grammar": 2.4, "speaking": 0.8},
    "daily_communication": {"speaking": 3.0, "listening": 2.6, "vocabulary": 1.6, "grammar": 1.0},
    "travel": {"speaking": 2.8, "listening": 2.4, "vocabulary": 2.0, "grammar": 0.8},
    "work_china": {"speaking": 2.4, "listening": 2.2, "grammar": 1.8, "vocabulary": 1.6},
    "study_china": {"grammar": 2.4, "vocabulary": 2.2, "listening": 2.2, "speaking": 1.6},
}
FOCUS_TO_SKILL = {
    "speaking": "speaking",
    "listening": "listening",
    "vocabulary": "vocabulary",
    "grammar": "grammar",
}
FOCUS_BOOST = 1.5          # DailyPlanService.PRIOR_WEIGHT bilan bir xil
REVIEW_BONUS = 0.3         # oldingi darslarni takrorlash qiymati
REPEAT_DECAY = 0.6         # bir xil ko'nikmaning har keyingi kartasi
PICTURE_COST = 0.5         # rasmli karta oddiy kartaning yarmi vaqt oladi
PICTURE_VALUE = 0.4        # va oddiy mashqdan yengilroq
PICTURE_DECAY = 0.85

TRIMMABLE_PURPOSES = frozenset({"practice", "retention_review"})
EXIT_PURPOSES = frozenset({"learning_exit_check", "learning_repair_bank", "exit_ticket"})
CARD_SKILL = {
    "pronunciation": "speaking",
    "listening_choice": "listening",
    "meaning_guess": "vocabulary",
    "translation_choice": "vocabulary",
    "hanzi_choice": "vocabulary",
    "pinyin_choice": "vocabulary",
    "match_pairs": "vocabulary",
    "quick_quiz": "vocabulary",
    "sentence_builder": "grammar",
    "reverse_builder": "grammar",
    "gap_fill": "grammar",
    "dialog_cloze": "grammar",
}


# ------------------------------------------------------------------ data ---

@lru_cache(maxsize=1)
def _picture_index() -> dict[str, dict[str, str]]:
    """level -> {hanzi: emoji}. Faqat tasdiqlangan, bir ma'noli rasmlar."""
    raw = json.loads(PICTURE_WORDS_PATH.read_text(encoding="utf-8"))
    index: dict[str, dict[str, str]] = {}
    for entry in raw.get("words") or []:
        zh = str(entry.get("zh") or "").strip()
        emoji = str(entry.get("emoji") or "").strip()
        if not zh or not emoji:
            continue
        for level in entry.get("levels") or []:
            index.setdefault(str(level), {})[zh] = emoji
    return index


@lru_cache(maxsize=16)
def _level_parts(level: str) -> tuple[tuple[int, int, tuple[dict, ...]], ...]:
    """Darajadagi har qism: (order, source_lesson, active_words). Deploy bilan o'zgaradi."""
    parts = []
    for order in range(1, total_parts(level) + 1):
        path = COURSE_V3_DATA_ROOT / level / f"lesson_{order:02d}.json"
        try:
            lesson = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        words = tuple(
            {
                "zh": str(w.get("zh") or "").strip(),
                "pinyin": str(w.get("pinyin") or "").strip(),
                "meaning": w.get("meaning") if isinstance(w.get("meaning"), dict) else {},
            }
            for w in (lesson.get("active_words") or [])
            if isinstance(w, dict) and str(w.get("zh") or "").strip()
        )
        parts.append((order, int(lesson.get("source_lesson") or 0), words))
    return tuple(parts)


def learned_picture_words(level: str, lesson_order: int, source_lesson: int) -> list[dict]:
    """Rasmi bor o'rganilgan so'zlar, ustuvorlik tartibida (ko'pi bilan 10).

    1) joriy darsning oldingi qismlari (eng yaqini birinchi);
    2) shu darajaning oldingi darslari (eng yaqini birinchi).
    Joriy qism va keyingi qismlar so'zlari — hali o'rganilmagan, kirmaydi.
    """
    pictures = _picture_index().get(level) or {}
    if not pictures:
        return []
    earlier = [p for p in _level_parts(level) if p[0] < int(lesson_order)]
    same = sorted((p for p in earlier if source_lesson and p[1] == source_lesson), key=lambda p: -p[0])
    other = sorted((p for p in earlier if not (source_lesson and p[1] == source_lesson)), key=lambda p: -p[0])
    out: list[dict] = []
    seen_words: set[str] = set()
    seen_images: set[str] = set()
    for _, _, words in [*same, *other]:
        for word in words:
            zh = word["zh"]
            image = pictures.get(zh)
            if not image or zh in seen_words or image in seen_images:
                continue
            seen_words.add(zh)
            seen_images.add(image)
            out.append({
                "zh": zh,
                "pinyin": word["pinyin"],
                "meaning": {k: str(v) for k, v in word["meaning"].items() if k in ("uz", "ru", "tj")},
                "image": image,
            })
            if len(out) >= MAX_PICTURES:
                return out
    return out


# --------------------------------------------------------------- weights ---

def _mix(goal: str, goals: Iterable[str], table: dict[str, Any], default):
    """`DailyPlanService._goal_weights` qoidasi: asosiy 60%, qolganlari 40%."""
    primary = goal if goal in table else DEFAULT_GOAL
    others = [g for g in goals if g in table and g != primary]
    base = table[primary]
    if not others:
        return base
    share = 0.4 / len(others)
    if isinstance(base, dict):
        return {
            key: 0.6 * base.get(key, 0.0) + share * sum(table[g].get(key, 0.0) for g in others)
            for key in base
        }
    return 0.6 * base + share * sum(table[g] for g in others)


def skill_weights(goal: str, goals: Iterable[str], focus: str | None) -> dict[str, float]:
    weights = dict(_mix(goal, goals, GOAL_SKILL_WEIGHTS, None))
    skill = FOCUS_TO_SKILL.get(str(focus or ""))
    if skill:
        weights[skill] = weights.get(skill, 0.0) + FOCUS_BOOST
    return weights


def budget_units(minutes: int, goal: str, goals: Iterable[str]) -> float:
    base = UNITS_BY_MINUTES.get(int(minutes or 0), UNITS_BY_MINUTES[DEFAULT_MINUTES])
    return base + float(_mix(goal, goals, GOAL_UNIT_SHIFT, 0.0))


# ------------------------------------------------------------------ plan ---

def _protected(card: dict) -> bool:
    return bool(card.get("objective_id") or card.get("learning_objective") or card.get("learning_retry"))


def _anchor(sections: list[tuple[int, str]]) -> dict | None:
    """Rasmli deck joyi: retention_review oldidan, aks holda oxirgi oddiy bo'lim oxiri."""
    for number, purpose in sections:
        if purpose in EXIT_PURPOSES:
            break
        if purpose == "retention_review":
            return {"section_no": number, "position": "start"}
    regular = [number for number, purpose in sections if purpose not in EXIT_PURPOSES]
    if not regular:
        return None
    return {"section_no": regular[-1], "position": "end"}


def build_lesson_plan(
    lesson: dict,
    *,
    level: str,
    lesson_order: int,
    minutes: int,
    goal: str,
    goals: Iterable[str] = (),
    focus: str | None = None,
    seed: str = "",
    picture_words: list[dict] | None = None,
) -> dict | None:
    """Sof funksiya: dars + o'quvchi sozlamalari -> reja yoki None."""
    goals = tuple(goals or ())
    weights = skill_weights(goal, goals, focus)
    budget = budget_units(minutes, goal, goals)

    section_list: list[tuple[int, str]] = []
    protected = 0
    optional: list[dict] = []
    for index, section in enumerate(lesson.get("sections") or [], start=1):
        if not isinstance(section, dict):
            continue
        number = int(section.get("section_no") or index)
        purpose = str(section.get("section_purpose") or "")
        section_list.append((number, purpose))
        for card_no, card in enumerate(section.get("cards") or [], start=1):
            if not isinstance(card, dict):
                continue
            skill = CARD_SKILL.get(str(card.get("type") or ""))
            if purpose in TRIMMABLE_PURPOSES and skill and not _protected(card):
                optional.append({
                    "section_no": number, "card_no": card_no, "skill": skill,
                    "review": purpose == "retention_review",
                    "position": len(optional),
                })
            else:
                protected += 1
    protected += len(((lesson.get("exit_ticket") or {}).get("cards")) or [])

    cap = PICTURE_CAP_BY_MINUTES.get(int(minutes or 0), PICTURE_CAP_BY_MINUTES[DEFAULT_MINUTES])
    anchor = _anchor(section_list)
    candidates = list(picture_words or [])[:min(cap, MAX_PICTURES)] if anchor else []

    remaining = budget - protected
    chosen: set[int] = set()
    used_skill: dict[str, int] = {}
    pictures = 0
    speak = weights.get("speaking", 0.0)
    while True:
        best = None  # (value per unit, -position, kind, item)
        for item in optional:
            if item["position"] in chosen or remaining < 1:
                continue
            value = (weights.get(item["skill"], 0.0) + (REVIEW_BONUS if item["review"] else 0.0))
            value *= REPEAT_DECAY ** used_skill.get(item["skill"], 0)
            key = (value, -item["position"])
            if best is None or key > best[0]:
                best = (key, "card", item)
        if pictures < len(candidates) and remaining >= PICTURE_COST:
            value = PICTURE_VALUE * speak * (PICTURE_DECAY ** pictures) / PICTURE_COST
            key = (value, -10**6)  # teng bo'lsa dars kartasi ustun
            if best is None or key > best[0]:
                best = (key, "picture", None)
        if best is None:
            break
        if best[1] == "picture":
            pictures += 1
            remaining -= PICTURE_COST
        else:
            item = best[2]
            chosen.add(item["position"])
            used_skill[item["skill"]] = used_skill.get(item["skill"], 0) + 1
            remaining -= 1

    omit = [
        {"section_no": item["section_no"], "card_no": item["card_no"]}
        for item in optional if item["position"] not in chosen
    ]
    deck = candidates[:pictures]
    if deck:
        random.Random(f"{seed}|{level}|{lesson_order}").shuffle(deck)
    if not omit and not deck:
        return None
    plan: dict[str, Any] = {
        "version": PLAN_VERSION,
        "daily_minutes": int(minutes or DEFAULT_MINUTES),
        "omit": omit,
    }
    if deck:
        plan["picture_review"] = {"anchor": anchor, "words": deck}
    return plan


# ----------------------------------------------------------------- rollout ---

def rollout_bucket(user_id: int) -> int:
    digest = hashlib.sha256(f"course-lesson-plan:{int(user_id)}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def enabled_for(settings_obj, user_id: int) -> bool:
    if not bool(getattr(settings_obj, "COURSE_LESSON_PLAN_ENABLED", False)):
        return False
    allow = {
        part.strip()
        for part in str(getattr(settings_obj, "COURSE_LESSON_PLAN_ALLOWLIST", "") or "").split(",")
        if part.strip()
    }
    if str(int(user_id)) in allow:
        return True
    try:
        percent = int(getattr(settings_obj, "COURSE_LESSON_PLAN_ROLLOUT_PERCENT", 100))
    except (TypeError, ValueError):
        percent = 0
    return rollout_bucket(user_id) < max(0, min(100, percent))


async def lesson_plan_for(session, settings_obj, *, user_id: int, level: str,
                          lesson_order: int, lesson: dict) -> dict | None:
    """O'quvchi uchun reja. Har qanday xato -> None (asl dars)."""
    try:
        if not user_id or not enabled_for(settings_obj, int(user_id)):
            return None
        profile = (await session.execute(
            select(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id == int(user_id))
        )).scalar_one_or_none()
        goal = str(getattr(profile, "goal", "") or DEFAULT_GOAL)
        goals = read_onboarding_goals(getattr(profile, "goals_json", None), primary_goal=goal)
        minutes = int(getattr(profile, "daily_minutes", None) or DEFAULT_MINUTES)
        focus = getattr(profile, "preferred_focus", None)
        words = learned_picture_words(level, lesson_order, int(lesson.get("source_lesson") or 0))
        return build_lesson_plan(
            lesson, level=level, lesson_order=lesson_order, minutes=minutes,
            goal=goal, goals=goals, focus=focus, seed=str(int(user_id)),
            picture_words=words,
        )
    except Exception:  # noqa: BLE001 — reja hech qachon darsni yiqitmaydi
        logger.exception("Lesson plan failed for user %s %s/%s", user_id, level, lesson_order)
        return None


def with_lesson_plan(lesson: dict, plan: dict | None) -> dict:
    """Reja bo'lsa darsning NUSXASIga qo'shadi; manba dict o'zgarmaydi."""
    if not plan:
        return lesson
    copy = dict(lesson)
    copy["lesson_plan"] = plan
    return copy
