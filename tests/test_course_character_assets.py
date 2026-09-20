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


class CourseCharacterAssetWiringTests(unittest.TestCase):
    def test_course_references_only_existing_versioned_character_assets(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        root = Path("app/static/assets/characters")

        refs = set(
            re.findall(r"/assets/characters/([^?\\\"']+)\\?v=[^\\\"']+", html)
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
