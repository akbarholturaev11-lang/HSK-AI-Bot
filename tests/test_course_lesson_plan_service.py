"""UIUX-008: dars uzunligi rejasi va rasmli talaffuz kartochkalari.

Server darsni o'zgartirmaydi — faqat `lesson_plan` qo'shadi. Bu testlar
quyidagilarni qotiradi:

* uzunlik onboarding daqiqasi va maqsadga moslashadi;
* qisqartirishda yangi so'z, grammatika, dialog, N1 va exit-ticket qoladi;
* qolgan mashqlar maqsad/fokusga mos keladi;
* rasmli kartaga faqat O'RGANILGAN va aniq rasmi bor so'z kiradi;
* flag OFF bo'lsa javob baytma-bayt eski.
"""

import copy
import json
import unittest
from collections import Counter
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import course_lesson_plan_service as plan_service
from app.services.course_lesson_plan_service import (
    EXIT_PURPOSES,
    MAX_PICTURES,
    PICTURE_CAP_BY_MINUTES,
    TRIMMABLE_PURPOSES,
    budget_units,
    build_lesson_plan,
    enabled_for,
    learned_picture_words,
    lesson_plan_for,
    rollout_bucket,
    skill_weights,
    with_lesson_plan,
)
from app.services.course_v3_parts import total_parts


def _card(card_type, **extra):
    return {"type": card_type, **extra}


def _lesson():
    """Kichik, lekin real tuzilmali qism: 6 himoyalangan + 10 ixtiyoriy karta."""
    return {
        "source_lesson": 3,
        "sections": [
            {"section_no": 1, "section_purpose": "intro", "cards": [
                _card("word_intro"), _card("word_intro"),
            ]},
            {"section_no": 2, "section_purpose": "grammar", "cards": [
                _card("grammar_rule"), _card("sentence_builder"),
            ]},
            {"section_no": 3, "section_purpose": "practice", "cards": [
                _card("pronunciation"),
                _card("listening_choice"),
                _card("sentence_builder"),
                _card("translation_choice"),
                _card("pronunciation"),
                _card("gap_fill"),
                _card("meaning_guess", objective_id="obj-1"),  # N1: himoyalangan
            ]},
            {"section_no": 4, "section_purpose": "retention_review", "cards": [
                _card("listening_choice"),
                _card("hanzi_choice"),
                _card("reverse_builder"),
                _card("pronunciation"),
            ]},
            {"section_no": 5, "section_purpose": "learning_exit_check", "cards": [
                _card("meaning_guess"),
            ]},
        ],
        "exit_ticket": {"cards": [_card("quick_quiz")]},
    }


def _words(count):
    return [
        {"zh": f"字{i}", "pinyin": f"zi{i}", "meaning": {"uz": f"s{i}"}, "image": chr(0x1F400 + i)}
        for i in range(count)
    ]


def _cards_by_ref(lesson):
    out = {}
    for index, section in enumerate(lesson["sections"], start=1):
        number = int(section.get("section_no") or index)
        for card_no, card in enumerate(section.get("cards") or [], start=1):
            out[(number, card_no)] = (section.get("section_purpose"), card)
    return out


def _kept_types(lesson, plan):
    omitted = {(o["section_no"], o["card_no"]) for o in (plan or {}).get("omit", [])}
    return [
        card["type"]
        for ref, (purpose, card) in _cards_by_ref(lesson).items()
        if purpose in TRIMMABLE_PURPOSES and ref not in omitted
    ]


class LessonLengthBudgetTests(unittest.TestCase):
    def test_budget_follows_the_onboarding_minutes(self):
        values = [budget_units(m, "work_china", ()) for m in (5, 10, 15, 20, 30)]
        self.assertEqual(values, sorted(values))
        self.assertLess(values[0], values[-1])

    def test_goal_shifts_the_length_too(self):
        self.assertGreater(budget_units(10, "hsk_exam", ()), budget_units(10, "travel", ()))
        self.assertGreater(
            budget_units(10, "study_china", ()), budget_units(10, "daily_communication", ())
        )

    def test_unknown_minutes_fall_back_to_ten(self):
        self.assertEqual(budget_units(7, "work_china", ()), budget_units(10, "work_china", ()))
        self.assertEqual(budget_units(0, "work_china", ()), budget_units(10, "work_china", ()))

    def test_secondary_goals_mix_like_the_daily_plan(self):
        mixed = budget_units(10, "hsk_exam", ("hsk_exam", "travel"))
        self.assertLess(mixed, budget_units(10, "hsk_exam", ()))
        self.assertGreater(mixed, budget_units(10, "travel", ()))

    def test_focus_raises_its_skill(self):
        base = skill_weights("hsk_exam", (), None)
        focused = skill_weights("hsk_exam", (), "speaking")
        self.assertGreater(focused["speaking"], base["speaking"])
        self.assertEqual(focused["grammar"], base["grammar"])


class LessonPlanTrimTests(unittest.TestCase):
    def _plan(self, minutes, goal, **kwargs):
        return build_lesson_plan(
            _lesson(), level="hsk1", lesson_order=8, minutes=minutes, goal=goal,
            seed="42", **kwargs,
        )

    def test_short_day_trims_only_extra_practice(self):
        lesson = _lesson()
        plan = self._plan(5, "travel")
        self.assertIsNotNone(plan)
        self.assertTrue(plan["omit"])
        refs = _cards_by_ref(lesson)
        for item in plan["omit"]:
            purpose, card = refs[(item["section_no"], item["card_no"])]
            self.assertIn(purpose, TRIMMABLE_PURPOSES)
            self.assertNotIn("objective_id", card)

    def test_grammar_dialog_exit_and_n1_cards_are_never_omitted(self):
        plan = self._plan(5, "travel")
        omitted = {(o["section_no"], o["card_no"]) for o in plan["omit"]}
        self.assertNotIn((2, 2), omitted)  # grammar bo'limidagi builder
        self.assertNotIn((3, 7), omitted)  # objective_id
        self.assertNotIn((5, 1), omitted)  # exit check
        self.assertFalse({ref for ref in omitted if ref[0] in (1, 2, 5)})

    def test_longer_day_keeps_more_cards(self):
        short = self._plan(5, "work_china")
        long = self._plan(30, "work_china")
        self.assertGreater(len(short["omit"]), len((long or {}).get("omit", [])))

    def _omitted_types(self, plan):
        refs = _cards_by_ref(_lesson())
        return [refs[(o["section_no"], o["card_no"])][1]["type"] for o in (plan or {}).get("omit", [])]

    def test_kept_cards_match_the_learner_goal(self):
        grammar = {"sentence_builder", "gap_fill", "reverse_builder"}
        talk = self._omitted_types(self._plan(5, "daily_communication"))
        exam = self._omitted_types(self._plan(5, "hsk_exam"))
        # So'zlashuv maqsadi grammatika mashqlarini birinchi bo'lib qisqartiradi,
        # imtihon maqsadi esa gapirish takrorini.
        self.assertGreaterEqual(sum(t in grammar for t in talk), 2)
        self.assertEqual(sum(t in grammar for t in exam), 0)
        self.assertEqual(set(exam), {"pronunciation"})

    def test_focus_keeps_more_of_that_skill(self):
        plain = self._omitted_types(self._plan(5, "daily_communication"))
        focused = self._omitted_types(self._plan(5, "daily_communication", focus="speaking"))
        self.assertIn("pronunciation", plain)
        self.assertNotIn("pronunciation", focused)

    def test_kept_practice_fits_the_budget(self):
        lesson = _lesson()
        for minutes in (5, 10, 15, 20, 30):
            for goal in plan_service.GOAL_UNIT_SHIFT:
                plan = build_lesson_plan(
                    lesson, level="hsk1", lesson_order=8, minutes=minutes, goal=goal,
                    picture_words=_words(10),
                )
                total = len(_cards_by_ref(lesson)) + 1  # + exit ticket
                kept = total - len((plan or {}).get("omit", []))
                pictures = len(((plan or {}).get("picture_review") or {}).get("words", []))
                used = kept + 0.5 * pictures
                self.assertLessEqual(used, max(budget_units(minutes, goal, ()), 7) + 0.5)

    def test_long_day_with_nothing_to_trim_returns_no_plan(self):
        self.assertIsNone(self._plan(30, "hsk_exam"))

    def test_plan_is_deterministic(self):
        first = self._plan(15, "travel", picture_words=_words(10))
        second = self._plan(15, "travel", picture_words=_words(10))
        self.assertEqual(first, second)

    def test_source_lesson_is_not_mutated(self):
        lesson = _lesson()
        before = copy.deepcopy(lesson)
        build_lesson_plan(lesson, level="hsk1", lesson_order=8, minutes=5, goal="travel",
                          picture_words=_words(6))
        self.assertEqual(before, lesson)


class PictureDeckTests(unittest.TestCase):
    def test_deck_respects_the_minutes_cap_and_ten_card_limit(self):
        for minutes, cap in PICTURE_CAP_BY_MINUTES.items():
            plan = build_lesson_plan(
                _lesson(), level="hsk1", lesson_order=8, minutes=minutes,
                goal="daily_communication", picture_words=_words(12),
            )
            words = ((plan or {}).get("picture_review") or {}).get("words", [])
            self.assertLessEqual(len(words), min(cap, MAX_PICTURES))
            self.assertEqual(len({w["zh"] for w in words}), len(words))

    def test_speaking_learners_get_pictures(self):
        plan = build_lesson_plan(
            _lesson(), level="hsk1", lesson_order=8, minutes=20,
            goal="daily_communication", picture_words=_words(10),
        )
        self.assertGreaterEqual(len(plan["picture_review"]["words"]), 4)

    def test_deck_uses_only_given_words(self):
        given = _words(8)
        plan = build_lesson_plan(
            _lesson(), level="hsk1", lesson_order=8, minutes=30,
            goal="travel", picture_words=given,
        )
        self.assertTrue(set(w["zh"] for w in plan["picture_review"]["words"]) <= {w["zh"] for w in given})

    def test_anchor_is_before_retention_review(self):
        plan = build_lesson_plan(
            _lesson(), level="hsk1", lesson_order=8, minutes=20,
            goal="travel", picture_words=_words(6),
        )
        self.assertEqual(plan["picture_review"]["anchor"], {"section_no": 4, "position": "start"})

    def test_anchor_without_review_is_the_last_regular_section(self):
        lesson = _lesson()
        lesson["sections"] = [s for s in lesson["sections"] if s["section_purpose"] != "retention_review"]
        plan = build_lesson_plan(
            lesson, level="hsk1", lesson_order=8, minutes=20,
            goal="travel", picture_words=_words(6),
        )
        self.assertEqual(plan["picture_review"]["anchor"], {"section_no": 3, "position": "end"})

    def test_no_words_means_no_deck(self):
        plan = build_lesson_plan(
            _lesson(), level="hsk1", lesson_order=8, minutes=5, goal="travel", picture_words=[],
        )
        self.assertNotIn("picture_review", plan)


class LearnedPictureWordsTests(unittest.TestCase):
    """Real kurs ma'lumotlari: faqat o'rganilgan, rasmi aniq so'zlar."""

    @staticmethod
    def _active(level, order):
        lesson = json.loads(
            (plan_service.COURSE_V3_DATA_ROOT / level / f"lesson_{order:02d}.json").read_text("utf-8")
        )
        return lesson, {w["zh"] for w in lesson.get("active_words") or []}

    def test_first_part_has_no_deck(self):
        for level in ("hsk1", "nhsk1"):
            self.assertEqual(learned_picture_words(level, 1, 1), [])

    def test_words_come_only_from_earlier_parts(self):
        index = plan_service._picture_index()
        for level in ("hsk1", "hsk2", "hsk3", "nhsk1", "nhsk2"):
            total = total_parts(level)
            for order in range(2, total + 1, max(1, total // 12)):
                lesson, _ = self._active(level, order)
                words = learned_picture_words(level, order, int(lesson.get("source_lesson") or 0))
                earlier = set()
                for prior in range(1, order):
                    earlier |= self._active(level, prior)[1]
                self.assertLessEqual(len(words), MAX_PICTURES)
                self.assertEqual(len({w["zh"] for w in words}), len(words))
                self.assertEqual(len({w["image"] for w in words}), len(words))
                for word in words:
                    self.assertIn(word["zh"], earlier, f"{level}/{order}: {word['zh']}")
                    self.assertEqual(index[level][word["zh"]], word["image"])
                    self.assertTrue(word["pinyin"])
                    self.assertTrue(set(word["meaning"]) <= {"uz", "ru", "tj"})

    def test_current_lesson_parts_come_first(self):
        level = "hsk2"
        for order in range(3, total_parts(level) + 1):
            lesson, _ = self._active(level, order)
            source = int(lesson.get("source_lesson") or 0)
            same = set()
            for prior in range(1, order):
                prior_lesson, active = self._active(level, prior)
                if int(prior_lesson.get("source_lesson") or 0) == source:
                    same |= active
            pictured = same & set(plan_service._picture_index()[level])
            if len(pictured) < 2:
                continue
            words = learned_picture_words(level, order, source)
            self.assertIn(words[0]["zh"], same)
            return
        self.skipTest("hsk2 da bir darsning ikki rasmli qismi topilmadi")


class PictureCatalogGuardTests(unittest.TestCase):
    """`lesson_picture_words.json` qo'lda tasdiqlangan: har rasm aniq bitta so'z."""

    def setUp(self):
        self.raw = json.loads(plan_service.PICTURE_WORDS_PATH.read_text("utf-8"))

    def test_every_word_exists_in_its_course_level(self):
        for entry in self.raw["words"]:
            for level in entry["levels"]:
                course_words = set()
                for order in range(1, total_parts(level) + 1):
                    lesson = json.loads(
                        (plan_service.COURSE_V3_DATA_ROOT / level / f"lesson_{order:02d}.json")
                        .read_text("utf-8")
                    )
                    course_words |= {w["zh"] for w in lesson.get("active_words") or []}
                self.assertIn(entry["zh"], course_words, f"{entry['zh']} not in {level}")

    def test_one_image_means_one_word_per_level(self):
        seen = {}
        for entry in self.raw["words"]:
            self.assertTrue(entry["emoji"].strip())
            for level in entry["levels"]:
                key = (level, entry["emoji"])
                self.assertNotIn(key, seen, f"{entry['zh']} and {seen.get(key)} share {entry['emoji']}")
                seen[key] = entry["zh"]

    def test_no_duplicate_words(self):
        counts = Counter(entry["zh"] for entry in self.raw["words"])
        self.assertEqual([zh for zh, n in counts.items() if n > 1], [])


class RolloutTests(unittest.TestCase):
    def _settings(self, **values):
        base = {
            "COURSE_LESSON_PLAN_ENABLED": True,
            "COURSE_LESSON_PLAN_ROLLOUT_PERCENT": 100,
            "COURSE_LESSON_PLAN_ALLOWLIST": "",
        }
        base.update(values)
        return SimpleNamespace(**base)

    def test_flag_off_disables_everyone(self):
        settings = self._settings(COURSE_LESSON_PLAN_ENABLED=False, COURSE_LESSON_PLAN_ALLOWLIST="7")
        self.assertFalse(enabled_for(settings, 7))
        self.assertFalse(enabled_for(SimpleNamespace(), 7))

    def test_allowlist_wins_over_zero_percent(self):
        settings = self._settings(COURSE_LESSON_PLAN_ROLLOUT_PERCENT=0, COURSE_LESSON_PLAN_ALLOWLIST="7, 9")
        self.assertTrue(enabled_for(settings, 7))
        self.assertFalse(enabled_for(settings, 8))

    def test_percent_uses_a_stable_bucket(self):
        settings = self._settings(COURSE_LESSON_PLAN_ROLLOUT_PERCENT=50)
        for user_id in range(1, 50):
            self.assertEqual(enabled_for(settings, user_id), rollout_bucket(user_id) < 50)


class LessonPlanForTests(unittest.IsolatedAsyncioTestCase):
    def _settings(self, enabled=True):
        return SimpleNamespace(
            COURSE_LESSON_PLAN_ENABLED=enabled,
            COURSE_LESSON_PLAN_ROLLOUT_PERCENT=100,
            COURSE_LESSON_PLAN_ALLOWLIST="",
        )

    def _session(self, profile):
        return SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: profile))
        )

    async def test_flag_off_never_touches_the_database(self):
        session = self._session(None)
        plan = await lesson_plan_for(
            session, self._settings(False), user_id=5, level="hsk1", lesson_order=8, lesson=_lesson(),
        )
        self.assertIsNone(plan)
        session.execute.assert_not_awaited()

    async def test_profile_minutes_and_goal_drive_the_plan(self):
        profile = SimpleNamespace(daily_minutes=5, goal="travel", goals_json=None, preferred_focus=None)
        with patch.object(plan_service, "learned_picture_words", return_value=_words(4)):
            plan = await lesson_plan_for(
                self._session(profile), self._settings(), user_id=5, level="hsk1",
                lesson_order=8, lesson=_lesson(),
            )
        self.assertEqual(plan["daily_minutes"], 5)
        self.assertTrue(plan["omit"])

    async def test_missing_profile_uses_defaults(self):
        with patch.object(plan_service, "learned_picture_words", return_value=[]):
            plan = await lesson_plan_for(
                self._session(None), self._settings(), user_id=5, level="hsk1",
                lesson_order=8, lesson=_lesson(),
            )
        self.assertIsNone(plan)  # 10 daqiqa + hsk_exam: kichik qism to'liq qoladi

    async def test_any_error_returns_the_original_lesson(self):
        session = SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError("db down")))
        with self.assertLogs("app.services.course_lesson_plan_service", level="ERROR"):
            plan = await lesson_plan_for(
                session, self._settings(), user_id=5, level="hsk1", lesson_order=8, lesson=_lesson(),
            )
        self.assertIsNone(plan)

    def test_with_lesson_plan_copies(self):
        lesson = _lesson()
        self.assertIs(with_lesson_plan(lesson, None), lesson)
        merged = with_lesson_plan(lesson, {"version": 1, "omit": []})
        self.assertNotIn("lesson_plan", lesson)
        self.assertEqual(merged["lesson_plan"]["version"], 1)


class RealCourseDataPlanTests(unittest.TestCase):
    """Butun kurs bo'ylab: reja hech qachon himoyalangan kartaga tegmaydi."""

    def test_every_part_trims_only_extra_practice(self):
        for level in ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3"):
            for order in range(1, total_parts(level) + 1):
                path = plan_service.COURSE_V3_DATA_ROOT / level / f"lesson_{order:02d}.json"
                if not path.exists():
                    continue
                lesson = json.loads(path.read_text("utf-8"))
                refs = _cards_by_ref(lesson)
                plan = build_lesson_plan(
                    lesson, level=level, lesson_order=order, minutes=5,
                    goal="daily_communication", seed="1",
                    picture_words=learned_picture_words(level, order, int(lesson.get("source_lesson") or 0)),
                )
                for item in (plan or {}).get("omit", []):
                    purpose, card = refs[(item["section_no"], item["card_no"])]
                    self.assertIn(purpose, TRIMMABLE_PURPOSES, f"{level}/{order}")
                    self.assertNotIn(purpose, EXIT_PURPOSES)
                    self.assertFalse(card.get("objective_id") or card.get("learning_objective"))
                    self.assertFalse(card.get("learning_retry"))


if __name__ == "__main__":
    unittest.main()
