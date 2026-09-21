from pathlib import Path
import re
import unittest


CHARACTER_ASSETS = {
    "hsk-character-pack.css": "text/css",
    "hsk-character-motion.css": "text/css",
    "hsk-lesson-presentation.css": "text/css",
    "hsk-character-pack.js": "application/javascript",
    "hsk-character-motion.js": "application/javascript",
    "hsk-lesson-presentation.js": "application/javascript",
}

# The dock the standalone practice pages share. Serving these is allowlisted
# exactly like the lesson's, so a file added to the folder is not reachable
# until someone says so.
PRACTICE_COACH_ASSETS = {
    "hsk-practice-coach.css": "text/css",
    "hsk-practice-coach.js": "application/javascript",
}

# Which character each practice page hands the coach, by CAST role.
PRACTICE_PAGES = {
    "course_v3_mistakes.html": "rabbit",
    "course_v3_recognition.html": "crane",
    "course_v3_pronunciation.html": "monkey",
}


class CourseCharacterAssetWiringTests(unittest.TestCase):
    def test_course_references_only_existing_versioned_character_assets(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        root = Path("app/static/assets/characters")

        # `\\?` ortiqcha ekranlash edi: u "ixtiyoriy teskari chiziq" degani,
        # `?` belgisi emas — shuning uchun `?v=` hech qachon mos kelmasdi va
        # bu da'vo tug'ilganidan beri bo'sh to'plamni solishtirib yiqilardi.
        refs = set(
            re.findall(r"/assets/characters/([^?\"']+)\?v=[^\"']+", html)
        )
        self.assertEqual(refs, set(CHARACTER_ASSETS))

        for filename in CHARACTER_ASSETS:
            with self.subTest(filename=filename):
                self.assertTrue((root / filename).is_file())
                self.assertIn(f"/assets/characters/{filename}?v=", html)

    def test_fastapi_route_allowlists_every_character_asset(self):
        source = Path("app/main.py").read_text(encoding="utf-8")
        self.assertIn('@app.get("/assets/characters/{filename}")', source)
        self.assertIn("COURSE_CHARACTER_ASSETS", source)

        for filename, media_type in CHARACTER_ASSETS.items():
            with self.subTest(filename=filename):
                self.assertIn(f'"{filename}": "{media_type}"', source)

        self.assertIn(
            'f"app/static/assets/characters/{filename}"',
            source,
        )

    def test_lesson_cards_have_a_persistent_character_coach(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")

        self.assertIn('id="f-coach-dock"', html)
        self.assertIn('id="f-coach"', html)
        self.assertIn('renderLessonCoach(c,"idle")', html)
        self.assertIn("reactLessonCoach(card,ok,reaction)", html)

        # The coach speaks the card's own instruction rather than standing
        # alone beside a name tag. The line is MOVED, not copied: the source
        # `.qq` is hidden, or the same sentence would sit on screen twice.
        self.assertIn('id="f-coach-bubble"', html)
        self.assertIn("function syncLessonCoachLine()", html)
        self.assertIn('q.style.display="none"', html)
        self.assertIn("Promise.resolve().then(syncLessonCoachLine)", html)
        self.assertNotIn("f-coach-label", html)
        self.assertIn('t==="_dialogue"', html)
        self.assertIn('t==="sentence_builder"', html)
        self.assertIn('return"monkey"', html)

    def test_unlock_animation_only_follows_a_real_progress_transition(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")

        self.assertIn(
            'if(nextWasLocked&&next&&next.status!=="locked")'
            'window._pendingCourseUnlockOrder=Number(next.n)||0',
            html,
        )
        self.assertIn(
            'if(wasLocked&&target&&target.status!=="locked")'
            'window._pendingCourseUnlockOrder=Number(target.n)||0',
            html,
        )
        self.assertIn("applyLocalProgress(d.completed_lessons_count)", html)

    def test_practice_coach_assets_exist_and_are_allowlisted(self):
        root = Path("app/static/assets/characters")
        source = Path("app/main.py").read_text(encoding="utf-8")

        for filename, media_type in PRACTICE_COACH_ASSETS.items():
            with self.subTest(filename=filename):
                self.assertTrue((root / filename).is_file())
                # Without this line the file 404s and the coach silently
                # never appears — the pages guard on `window.PracticeCoach`.
                self.assertIn(f'"{filename}": "{media_type}"', source)

    def test_every_practice_page_loads_and_wires_the_coach(self):
        needed = set(PRACTICE_COACH_ASSETS) | {
            "hsk-character-pack.css",
            "hsk-character-motion.css",
            "hsk-character-pack.js",
            "hsk-character-motion.js",
        }

        for page, character in PRACTICE_PAGES.items():
            html = Path("app/static") / page
            source = html.read_text(encoding="utf-8")
            with self.subTest(page=page):
                refs = set(
                    re.findall(
                        r"/assets/characters/([^?\"']+)\?v=[^\"']+",
                        source,
                    )
                )
                self.assertEqual(needed, refs)

                # Mounted, reacted to, and closed out — a dock that is only
                # created is a character that never moves.
                self.assertIn("PracticeCoach.init(", source)
                self.assertIn("PracticeCoach.idle(", source)
                self.assertIn("PracticeCoach.answer(", source)
                self.assertIn("PracticeCoach.finish(", source)
                self.assertIn(character, source)

    def test_the_hsk_exam_never_gets_a_coach(self):
        """An exam withholds the verdict until the end.

        A coach that reacts to an answer would hand over the answer, so the
        test centre deliberately has no character at all. Android keeps the
        same rule in `PracticeCharacters.kt` (ExamRun has no coach row).
        """
        source = Path("app/static/course_v3_test.html").read_text(encoding="utf-8")

        self.assertNotIn("PracticeCoach", source)
        self.assertNotIn("/assets/characters/", source)

    def test_the_shared_coach_climbs_the_same_ladder_as_the_lesson(self):
        source = Path(
            "app/static/assets/characters/hsk-practice-coach.js"
        ).read_text(encoding="utf-8")

        # Four in a row turns a jump into a celebration, exactly like
        # `hskReactionFor` on Android and the lesson's own reaction ladder.
        self.assertIn('if (ok && run >= 4) return "celebrate";', source)
        self.assertIn('return ok ? "jump" : "wrong";', source)

        # A reaction with no text of its own must KEEP what the bubble was
        # saying. Forwarding the absent argument blanks the bubble and leaves
        # the character standing alone — the exact look this layout replaced.
        self.assertIn("if (arguments.length > 2) show(id, reaction, text);", source)
        self.assertIn("else show(id, reaction);", source)

        # The closing thresholds mirror PracticeCompletionOutcome.reaction.
        self.assertIn('if (percent >= 90) return { id: "dragon"', source)
        self.assertIn('if (percent >= 70) return { id: "panda"', source)
        self.assertIn('if (percent >= 50) return { id: "panda"', source)
        self.assertIn('return { id: "rabbit"', source)

    def test_character_route_does_not_use_a_generic_static_mount(self):
        source = Path("app/main.py").read_text(encoding="utf-8")
        route = source.split(
            '@app.get("/assets/characters/{filename}")',
            1,
        )[1].split('@app.get("/assets/install/{filename}")', 1)[0]

        self.assertIn("COURSE_CHARACTER_ASSETS.get(filename)", route)
        self.assertIn('status_code=404', route)


if __name__ == "__main__":
    unittest.main()
