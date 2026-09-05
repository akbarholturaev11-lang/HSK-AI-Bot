"""Kunlik reja qoidalari.

`DailyPlanService` — sof funksiya, shuning uchun bazasiz test qilinadi.
Bu yerda arxitektura qarorlari qotiriladi: reja qanday quriladi, nima
ko'rsatilmaydi va nima o'zgarmaydi.
"""

import unittest

from app.services.daily_plan_service import (
    ACCESS_AD,
    ACCESS_LOCKED,
    ACCESS_OPEN,
    TASK_CONTINUE_LESSON,
    TASK_MISTAKE_REVIEW,
    TASK_MOCK_EXAM,
    TASK_SKILL_DRILL,
    TASK_VOICE_DIALOG,
    DailyPlanService,
    plan_key,
)
from app.services.learning_signals import LearningSignals


def signals(**kwargs) -> LearningSignals:
    base = dict(
        level="hsk1",
        goal="hsk_exam",
        daily_minutes=20,
        preferred_focus=None,
        plan_size=3,
        daily_goal_xp=40,
        completed_parts=12,
        current_part=13,
        total_parts=63,
        local_day="2026-09-05",
        today_xp=0,
        streak=3,
        mistakes_total=7,
        weakness={"word": 2, "grammar": 5, "character": 1, "pronunciation": 0, "listening": 8},
        evidence_count=20,
        active_days_7=4,
        done_refs_today=frozenset(),
        done_types_today=frozenset(),
    )
    base.update(kwargs)
    return LearningSignals(**base)


def types(tasks) -> list[str]:
    return [task["t"] for task in tasks]


class PlanShapeTests(unittest.TestCase):
    def test_course_always_comes_first(self):
        # Kurs — asosiy mahsulot; reja uni hech qachon ikkinchi o'ringa
        # tushirmaydi.
        for goal in ("hsk_exam", "daily_communication", "travel", "work_china", "study_china"):
            tasks = DailyPlanService.build(signals(goal=goal), seed="u1")
            self.assertEqual(tasks[0]["t"], TASK_CONTINUE_LESSON, goal)

    def test_plan_size_follows_daily_minutes(self):
        for size in (1, 2, 3, 4):
            tasks = DailyPlanService.build(signals(plan_size=size), seed="u1")
            self.assertEqual(len(tasks), size)

    def test_finished_band_drops_the_lesson_task(self):
        tasks = DailyPlanService.build(
            signals(completed_parts=63, current_part=63, total_parts=63), seed="u1"
        )
        # 63-qism hali tugatilmagan bo'lsa davom etish qoladi; band tugagach
        # (current_part > total) — yo'q.
        tasks_over = DailyPlanService.build(
            signals(completed_parts=63, current_part=64, total_parts=63), seed="u1"
        )
        self.assertIn(TASK_CONTINUE_LESSON, types(tasks))
        self.assertNotIn(TASK_CONTINUE_LESSON, types(tasks_over))

    def test_only_known_task_types_are_produced(self):
        allowed = {
            TASK_CONTINUE_LESSON,
            TASK_MISTAKE_REVIEW,
            TASK_SKILL_DRILL,
            TASK_MOCK_EXAM,
            TASK_VOICE_DIALOG,
        }
        tasks = DailyPlanService.build(signals(plan_size=4), seed="u1")
        self.assertTrue(set(types(tasks)) <= allowed)


class GoalWeightingTests(unittest.TestCase):
    def test_exam_goal_prefers_tests_and_mistake_review(self):
        tasks = DailyPlanService.build(signals(goal="hsk_exam", plan_size=4), seed="u1")
        self.assertIn(TASK_MISTAKE_REVIEW, types(tasks))
        self.assertIn(TASK_MOCK_EXAM, types(tasks))

    def test_speaking_goals_bring_in_the_voice_dialog(self):
        for goal in ("daily_communication", "travel", "work_china"):
            tasks = DailyPlanService.build(signals(goal=goal, plan_size=4), seed="u1")
            self.assertIn(TASK_VOICE_DIALOG, types(tasks), goal)

    def test_exam_goal_ranks_the_mock_exam_above_the_voice_dialog(self):
        # Imtihon maqsadida jonli suhbat rejaga faqat joy qolganda tushadi.
        tasks = DailyPlanService.build(signals(goal="hsk_exam", plan_size=4), seed="u1")
        self.assertIn(TASK_MOCK_EXAM, types(tasks))
        self.assertNotIn(TASK_VOICE_DIALOG, types(tasks))

    def test_evidence_outranks_the_goal_when_a_weakness_is_strong(self):
        # Ataylab: "gapirish" maqsadi ham real zaiflikni bosib o'tolmaydi.
        # Reja avval o'quvchi haqiqatan qoqilayotgan joyni beradi.
        tasks = DailyPlanService.build(
            signals(
                goal="daily_communication",
                plan_size=2,
                weakness={"word": 0, "grammar": 0, "character": 40, "pronunciation": 0, "listening": 0},
            ),
            seed="u1",
        )
        self.assertEqual(types(tasks), [TASK_CONTINUE_LESSON, TASK_SKILL_DRILL])

    def test_persona_follows_the_goal(self):
        # Mini App'da hozir faqat ikkita persona ochiq; qolganini ko'rsatish
        # UI o'zgarishi bo'lgani uchun alohida ruxsat talab qiladi.
        quiet = {"word": 0, "grammar": 0, "character": 0, "pronunciation": 0, "listening": 0}
        exam = DailyPlanService.build(
            signals(goal="hsk_exam", plan_size=4, mistakes_total=0, weakness=quiet), seed="u1"
        )
        travel = DailyPlanService.build(
            signals(goal="travel", plan_size=4, mistakes_total=0, weakness=quiet), seed="u1"
        )
        self.assertEqual(
            next(task for task in exam if task["t"] == TASK_VOICE_DIALOG)["role"],
            "teacher_li",
        )
        self.assertEqual(
            next(task for task in travel if task["t"] == TASK_VOICE_DIALOG)["role"],
            "friend",
        )


class WeaknessTests(unittest.TestCase):
    def test_the_weakest_measure_picks_the_drill_skill(self):
        tasks = DailyPlanService.build(
            signals(weakness={"word": 0, "grammar": 0, "character": 9, "pronunciation": 0, "listening": 1}),
            seed="u1",
        )
        drill = next(task for task in tasks if task["t"] == TASK_SKILL_DRILL)
        self.assertEqual(drill["skill"], "characters")

    def test_grammar_weakness_never_becomes_a_drill(self):
        # Savol banki grammatikani qoplay olmaydi (o'lchandi: 30-qismda ham
        # 4/10). Uning o'rniga o'quvchining O'Z xatolari takrorlanadi.
        tasks = DailyPlanService.build(
            signals(
                weakness={"word": 0, "grammar": 40, "character": 0, "pronunciation": 0, "listening": 0},
                plan_size=4,
            ),
            seed="u1",
        )
        drills = [task for task in tasks if task["t"] == TASK_SKILL_DRILL]
        self.assertTrue(all(task["skill"] != "writing" for task in drills))
        self.assertIn(TASK_MISTAKE_REVIEW, types(tasks))

    def test_a_beginner_is_not_promised_a_skill_the_bank_cannot_fill(self):
        # 2-qismdagi o'quvchi uchun tinglash savollari deyarli yo'q.
        tasks = DailyPlanService.build(
            signals(completed_parts=1, current_part=2,
                    weakness={"word": 0, "grammar": 0, "character": 0, "pronunciation": 0, "listening": 9}),
            seed="u1",
        )
        drills = [task for task in tasks if task["t"] == TASK_SKILL_DRILL]
        self.assertEqual(drills, [])

    def test_no_mistakes_means_no_review_task(self):
        tasks = DailyPlanService.build(signals(mistakes_total=0, plan_size=4), seed="u1")
        self.assertNotIn(TASK_MISTAKE_REVIEW, types(tasks))


class PreferredFocusTests(unittest.TestCase):
    def test_stated_focus_wins_while_there_is_no_evidence(self):
        flat = {"word": 0, "grammar": 0, "character": 0, "pronunciation": 0, "listening": 0}
        tasks = DailyPlanService.build(
            signals(weakness=flat, evidence_count=0, preferred_focus="speaking"),
            seed="u1",
        )
        drill = next(task for task in tasks if task["t"] == TASK_SKILL_DRILL)
        self.assertEqual(drill["skill"], "pronunciation")

    def test_a_skill_without_a_screen_is_never_offered(self):
        # Server tinglash savollarini bera oladi, lekin Mini App'da uni
        # ochadigan ekran YO'Q. Ochib bo'lmaydigan vazifa rejaga tushmaydi.
        tasks = DailyPlanService.build(
            signals(
                preferred_focus="listening",
                evidence_count=0,
                current_part=30,
                weakness={"word": 0, "grammar": 0, "character": 0, "pronunciation": 0, "listening": 90},
                plan_size=4,
            ),
            seed="u1",
        )
        drills = [task for task in tasks if task["t"] == TASK_SKILL_DRILL]
        self.assertTrue(all(task["skill"] != "listening" for task in drills))

    def test_evidence_overrides_the_stated_focus_over_time(self):
        # O'quvchi "tinglash" degan, lekin real xatolar ieroglifda va u
        # allaqachon 20 ta mashg'ulot qilgan — tizim ko'rganiga ishonadi.
        tasks = DailyPlanService.build(
            signals(
                preferred_focus="listening",
                evidence_count=20,
                weakness={"word": 0, "grammar": 0, "character": 30, "pronunciation": 0, "listening": 1},
            ),
            seed="u1",
        )
        drill = next(task for task in tasks if task["t"] == TASK_SKILL_DRILL)
        self.assertEqual(drill["skill"], "characters")

    def test_no_preference_answer_adds_no_bias(self):
        flat = {"word": 0, "grammar": 0, "character": 0, "pronunciation": 0, "listening": 0}
        none_focus = DailyPlanService.build(
            signals(weakness=flat, evidence_count=0, preferred_focus="none"), seed="u1"
        )
        unset = DailyPlanService.build(
            signals(weakness=flat, evidence_count=0, preferred_focus=None), seed="u1"
        )
        self.assertEqual(types(none_focus), types(unset))


class AccessTests(unittest.TestCase):
    def test_a_locked_task_is_never_issued(self):
        tasks = DailyPlanService.build(
            signals(plan_size=4),
            access={"voice": ACCESS_LOCKED, "training_test": ACCESS_LOCKED},
            seed="u1",
        )
        self.assertNotIn(TASK_VOICE_DIALOG, types(tasks))
        self.assertNotIn(TASK_MOCK_EXAM, types(tasks))
        self.assertNotIn(TASK_SKILL_DRILL, types(tasks))

    def test_an_ad_supported_task_is_issued(self):
        # Qaror B: reklamali vazifalar cheklanmaydi.
        tasks = DailyPlanService.build(
            signals(plan_size=4),
            access={"voice": ACCESS_AD, "training_test": ACCESS_AD, "mistake_review": ACCESS_AD},
            seed="u1",
        )
        self.assertGreater(len(tasks), 1)

    def test_a_locked_course_drops_the_lesson_task(self):
        tasks = DailyPlanService.build(
            signals(), access={"lesson": ACCESS_LOCKED}, seed="u1"
        )
        self.assertNotIn(TASK_CONTINUE_LESSON, types(tasks))


class StabilityTests(unittest.TestCase):
    def test_the_same_seed_gives_the_same_plan(self):
        first = DailyPlanService.build(signals(), seed="user-7|2026-09-05")
        second = DailyPlanService.build(signals(), seed="user-7|2026-09-05")
        self.assertEqual(first, second)

    def test_plan_key_carries_schema_version_band_and_local_day(self):
        key = plan_key(level="hsk2", local_day="2026-09-05")
        self.assertEqual(key, "v1:hsk2:2026-09-05")
        # Band o'zgarsa kalit mos kelmaydi -> reja qayta quriladi, ya'ni
        # mavjud bo'lmagan qism raqamlari qolib ketmaydi.
        self.assertNotEqual(key, plan_key(level="hsk3", local_day="2026-09-05"))


class HydrateTests(unittest.TestCase):
    def test_completed_part_marks_the_lesson_task_done(self):
        tasks = [{"t": TASK_CONTINUE_LESSON, "ref": "hsk1:13"}]
        view = DailyPlanService.hydrate(tasks, signals(completed_parts=13))
        self.assertTrue(view["tasks"][0]["done"])
        self.assertTrue(view["complete"])

    def test_todays_activity_marks_the_matching_task_done(self):
        tasks = [{"t": TASK_SKILL_DRILL, "skill": "listening"}, {"t": TASK_MOCK_EXAM}]
        view = DailyPlanService.hydrate(
            tasks, signals(done_types_today=frozenset({"training"}))
        )
        self.assertTrue(view["tasks"][0]["done"])
        self.assertFalse(view["tasks"][1]["done"])
        self.assertEqual(view["done"], 1)

    def test_a_task_locked_after_it_was_issued_stays_in_the_list(self):
        # Q-B qoidasi: almashtirish rejani beqaror qilardi.
        tasks = [{"t": TASK_VOICE_DIALOG, "role": "friend"}]
        view = DailyPlanService.hydrate(
            tasks, signals(), access={"voice": ACCESS_LOCKED}
        )
        self.assertEqual(len(view["tasks"]), 1)
        self.assertFalse(view["tasks"][0]["available"])
        self.assertEqual(view["tasks"][0]["access"], ACCESS_LOCKED)

    def test_unknown_task_types_are_dropped_instead_of_crashing(self):
        # Eski sxemadagi saqlangan reja deploydan keyin yiqitmasin.
        view = DailyPlanService.hydrate([{"t": "telepathy"}], signals())
        self.assertEqual(view["tasks"], [])

    def test_progress_numbers_come_from_the_signals(self):
        view = DailyPlanService.hydrate([], signals(today_xp=25, daily_goal_xp=40, streak=6))
        self.assertEqual(view["goal_xp"], 40)
        self.assertEqual(view["done_xp"], 25)
        self.assertEqual(view["streak"], 6)
        self.assertFalse(view["complete"])

    def test_default_access_is_open_so_a_missing_view_never_hides_work(self):
        tasks = [{"t": TASK_MISTAKE_REVIEW}]
        view = DailyPlanService.hydrate(tasks, signals())
        self.assertTrue(view["tasks"][0]["available"])
        self.assertEqual(view["tasks"][0]["access"], ACCESS_OPEN)


if __name__ == "__main__":
    unittest.main()
