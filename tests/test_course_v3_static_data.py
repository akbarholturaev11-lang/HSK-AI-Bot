import json
import unittest
from pathlib import Path


BASE = Path("app/static/course_v3_data")
# Har HSK darsi 3-4 so'zlik mini-darslarga (qismlarga) bo'lingan; sonlar —
# flat qismlar soni (parts_manifest.json bilan mos bo'lishi ham tekshiriladi).
EXPECTED_LESSON_COUNTS = {
    "hsk1": 63,
    "hsk2": 72,
    "hsk3": 109,
    "hsk4": 181,
}
EXPECTED_SOURCE_LESSONS = {
    "hsk1": 15,
    "hsk2": 15,
    "hsk3": 20,
    "hsk4": 20,
}


class CourseV3StaticMapTests(unittest.TestCase):
    def test_level_maps_cover_all_lessons_without_demo_progress(self):
        for level, expected_count in EXPECTED_LESSON_COUNTS.items():
            with self.subTest(level=level):
                data = json.loads((BASE / f"{level}.json").read_text(encoding="utf-8"))
                lessons = [
                    lesson
                    for unit in data.get("units", [])
                    for lesson in unit.get("lessons", [])
                ]

                self.assertEqual(data["schema_version"], 2)
                self.assertEqual(data["level"], level)
                self.assertEqual(data["progress"]["xp"], 0)
                self.assertEqual(data["progress"]["completed"], 0)
                self.assertEqual(len(lessons), expected_count)
                # Unit = bitta HSK darsligi darsi; oxirgi tugun — checkpoint.
                self.assertEqual(len(data["units"]), EXPECTED_SOURCE_LESSONS[level])
                for unit in data["units"]:
                    self.assertTrue(unit["lessons"], unit.get("no"))
                    self.assertTrue(unit["lessons"][-1].get("checkpoint"), unit.get("no"))

                manifest = json.loads(
                    (BASE / "parts_manifest.json").read_text(encoding="utf-8")
                )[level]
                self.assertEqual(manifest["total_parts"], expected_count)
                self.assertEqual(
                    [l["n"] for l in lessons], list(range(1, expected_count + 1))
                )

                self.assertEqual(lessons[0]["status"], "current")
                for lesson in lessons[:3]:
                    self.assertFalse(lesson.get("locked_premium", False))
                    self.assertTrue((BASE / level / f"lesson_{lesson['n']:02d}.json").exists())
                for lesson in lessons[3:]:
                    self.assertEqual(lesson["status"], "locked")
                    self.assertTrue(lesson.get("locked_premium", False))
                    self.assertTrue((BASE / level / f"lesson_{lesson['n']:02d}.json").exists())

    def test_course_v3_respects_selected_level_and_real_invite_format(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        onboarding = Path("app/static/course_v3_onboarding.html").read_text(encoding="utf-8")

        self.assertIn("getSelectedLevel()", html)
        self.assertIn("localStorage.getItem(\"hsk_v3_level\")", html)
        self.assertIn('"/api/v3/map?lang="+LANG+"&level="+lv', html)
        self.assertIn("if(!INIT_DATA){showAuthGate();return;}", html)
        self.assertIn("function lessonDataUrl(lv,n)", html)
        self.assertIn('"/course_v3_data/"+normalizeLevel(lv)+"/lesson_"+String(Number(n)||0).padStart(2,"0")+".json"', html)
        self.assertIn("levelPicker:function", html)
        self.assertIn("/api/v3/invite?lang=", html)
        self.assertNotIn("start=ref_", html)
        self.assertIn("PRONOUNCE_LIMIT_EXCEEDED", html)
        self.assertIn("v3_pronunciation_limit", html)
        self.assertIn("Reklama bilan davom etish", html)
        self.assertIn("/api/v3/ad?placement=", html)
        self.assertIn("/api/v3/ad/view", html)
        self.assertIn("/api/v3/lesson/unlock", html)
        self.assertIn("section_completed", html)
        self.assertIn("ratingCountdownText()", html)
        self.assertIn("pendingRankUp", html)
        self.assertIn("loadLatestRating()", html)
        self.assertIn("rank:Number(u.rank||0)", html)
        self.assertIn("referralUsers=[]", html)
        self.assertIn("openRatingUser('+i+',\\'referrals\\')", html)
        self.assertIn("invitePayloadUrl()", html)
        self.assertNotIn("u.weeklyXp||u.xp||0", html)
        self.assertNotIn("meU.weeklyXp||MAP&&MAP.progress&&MAP.progress.xp", html)
        self.assertIn("awarded_xp", html)
        self.assertNotIn('["+60","XP"]', html)
        self.assertNotIn('["+200","XP"]', html)
        self.assertNotIn('["+50",lu.bonusXp]', html)
        self.assertNotIn("64 / 100", html)
        self.assertNotIn("2'+(LANG", html)
        self.assertIn("AdFlow", html)
        self.assertIn('event:"checkout_opened"', html)
        self.assertIn("CHECKOUT_NAVIGATING", html)
        self.assertIn('"&sid="+encodeURIComponent(COURSE_SESSION_ID)', html)
        self.assertIn('["course-v3",COURSE_SESSION_ID,event', html)
        self.assertNotIn('sessionStorage.getItem("hsk_v3_session_id")', html)
        subscription = (Path(__file__).parent.parent / "app" / "static" / "subscription.html").read_text(encoding="utf-8")
        self.assertIn('event:"/api/subscription-miniapp/event"', subscription)
        self.assertIn("CHECKOUT_ATTEMPT_ID", subscription)
        self.assertIn("attempt_id:state.attemptId", subscription)
        self.assertIn('trackSubscriptionStage("payment_instructions_viewed")', subscription)
        self.assertIn('trackSubscriptionStage("payment_receipt_selected")', subscription)
        self.assertIn("lockedValueText", subscription)
        self.assertIn("/api/miniapp/onboarding", onboarding)
        self.assertIn("onboarding_started", onboarding)
        self.assertIn('query.set("autostart","1")', onboarding)
        self.assertIn('activation_variant:"direct_start_v1"', onboarding)
        self.assertIn('if(sp.get("autostart")==="1")', html)
        self.assertIn('sp.delete("autostart")', html)
        self.assertIn("hsk_v3_lesson_resume:", html)
        self.assertIn("loadLessonResume(lv,l.n,Flow.queue.length)", html)
        self.assertIn("clearLessonResume((MAP&&MAP.level)||\"hsk1\",cur&&cur.n)", html)
        self.assertIn('lang:LANG,session_id:COURSE_SESSION_ID', html)

    def test_interactive_cards_present_and_level_gated(self):
        """New Duolingo-style cards (sentence_builder, listening_choice,
        dialog_cloze) appear and only use already-learned vocabulary.

        Qismlarga bo'lingandan keyin: har QISM 2-4 yangi so'z o'rgatadi (yoki
        checkpoint — 0 yangi so'z, dialog bilan yakunlaydi); tinglash va dialog
        to'ldirish har HSK darsining qismlar guruhida albatta bor."""
        manifest = json.loads((BASE / "parts_manifest.json").read_text(encoding="utf-8"))
        known_words: set[str] = set()
        known_lines: set[str] = set()
        for level in ("hsk1", "hsk2", "hsk3", "hsk4"):
            for src_lesson in manifest[level]["lessons"]:
                group_types = set()
                for n in src_lesson["parts"]:
                    data = json.loads(
                        (BASE / level / f"lesson_{n:02d}.json").read_text(encoding="utf-8")
                    )
                    where = f"{level}/lesson_{n:02d}"
                    is_checkpoint = n == src_lesson["checkpoint"]
                    self.assertEqual(data["checkpoint"], is_checkpoint, where)
                    self.assertEqual(data["source_lesson"], src_lesson["src"], where)
                    # dialoglar har qismda to'liq ma'lumotnoma sifatida turadi
                    lesson_lines = {
                        ln["zh"]
                        for b in data["dialogues"]
                        for ln in b["dialogue"]
                        if ln.get("zh")
                    }
                    cards = [c for sec in data["sections"] for c in sec["cards"]]
                    new_words = [c["word"]["zh"] for c in cards if c["type"] == "active_word"]
                    if is_checkpoint:
                        self.assertEqual(new_words, [], where)
                    else:
                        self.assertTrue(2 <= len(new_words) <= 4, f"{where}: {len(new_words)} new words")
                    part_words = {w["zh"] for w in data["active_words"]}
                    gate_words = known_words | part_words
                    gate_lines = known_lines | lesson_lines

                    for c in cards:
                        group_types.add(c["type"])
                        if c["type"] == "sentence_builder":
                            ans = c["answer_tokens"]
                            self.assertTrue(2 <= len(ans) <= 8, where)
                            for tok in ans:
                                self.assertIn(tok, c["tokens"], where)
                                self.assertIn(tok, gate_words, f"ungated builder token in {where}")
                            for lang in ("uz", "ru", "tj"):
                                self.assertTrue(c["sentence"].get(lang), where)
                        elif c["type"] == "listening_choice":
                            self.assertEqual(
                                c["options"][c["correct_index"]], c["audio_text"], where
                            )
                            # Listening cards come in two gated flavors: dialogue
                            # LINES or single WORDS (both only already-learned).
                            gate_listen = gate_lines | gate_words
                            for op in c["options"]:
                                self.assertIn(op, gate_listen, f"ungated listen option in {where}")
                        elif c["type"] == "dialog_cloze":
                            blanks = [ln for ln in c["lines"] if ln["blank"]]
                            self.assertEqual(len(blanks), 1, where)
                            self.assertIn(
                                c["options"][c["correct_index"]], gate_lines, where
                            )

                    known_words |= part_words
                    known_lines |= lesson_lines

                # Har HSK darsi (qismlar guruhi) interaktiv bo'lib qoladi:
                # tinglash + dialog to'ldirish.
                where = f"{level}/src_{src_lesson['src']}"
                self.assertIn("listening_choice", group_types, where)
                self.assertIn("dialog_cloze", group_types, where)

    def test_hsk_exam_options_hide_pinyin_and_hint_labels(self):
        html = Path("app/static/course_v3_test.html").read_text(encoding="utf-8")

        self.assertIn("function examOptionText(q,o)", html)
        self.assertIn('if(q.type==="audio_choice"||isMeaningQuestion(q))return lab||zh;', html)
        self.assertNotIn("var py=o.py?", html)
        self.assertNotIn("'<small>'+lab+'</small>'", html)


if __name__ == "__main__":
    unittest.main()
