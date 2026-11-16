"""QA Professional45 is source-backed but separate from production account services."""
import importlib
import os
import unittest
from unittest.mock import patch

import httpx

PROJECT = "06a405a4-9ec7-4d1f-87b6-b2f745d8fc76"
ENVIRONMENT = "aa22456f-c3f7-47d8-ad90-904856fc10bd"
QA_ENV = {"HSK_PROFESSIONAL45_QA": "1", "RAILWAY_PROJECT_ID": PROJECT,
          "RAILWAY_ENVIRONMENT_ID": ENVIRONMENT}


class QaPreviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_static_routes_and_fixture_api_take_priority(self):
        # Import-time guard must not accidentally inherit CI's synthetic BOT_TOKEN.
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict(os.environ, QA_ENV):
                from app import qa_professional45_preview as preview
        transport = httpx.ASGITransport(app=preview.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://qa.local") as client:
            main = await client.get("/iphone-pwa/course")
            self.assertEqual(main.status_code, 200)
            self.assertIn("text/html", main.headers["content-type"])
            self.assertIn("<html", main.text.lower())
            self.assertIn("pwa-professional45", main.text)
            canonical = await client.get("/api/v3/pwa/lesson/content/hsk3/29")
            self.assertEqual(canonical.status_code, 200)
            self.assertIn("sections", canonical.json())
            self.assertEqual((await client.get("/api/v3/pwa/lesson/content/hsk3/999")).status_code, 404)
            reserve = await client.post("/api/v3/pwa/lesson/start", json={"level":"hsk3","lesson_id":29})
            self.assertEqual(reserve.status_code, 200)
            self.assertEqual(reserve.json()["allowed"], True)
            self.assertEqual((await client.post("/api/v3/pwa/lesson/start",json={"level":"hsk3","lesson_id":99})).status_code, 422)
            dictionary = await client.get("/iphone-pwa/dictionary")
            self.assertEqual(dictionary.status_code, 200)
            self.assertIn("text/html", dictionary.headers["content-type"])
            profile = await client.get("/api/v3/pwa/profile")
            self.assertEqual(profile.status_code, 200)
            self.assertEqual(profile.json()["ok"], True)
            self.assertEqual(profile.headers["X-HSK-QA-Preview"], "visual-only")
            fmap = await client.post("/api/v3/pwa/map")
            self.assertEqual(fmap.status_code, 200)
            self.assertEqual(fmap.json()["progress"]["streak"], 7)
            self.assertEqual(fmap.headers["X-HSK-PWA-User-ID"], "900001")
            lessons = [lesson for unit in fmap.json()["units"] for lesson in unit["lessons"]]
            self.assertEqual(sum(lesson["status"] == "done" for lesson in lessons), 28)
            self.assertEqual(sum(lesson["status"] == "current" for lesson in lessons), 1)
            auth = await client.get("/api/v3/pwa-auth/session")
            self.assertEqual(auth.status_code, 200)
            self.assertEqual(auth.json()["csrf"], "isolated-visual-qa")
            self.assertEqual((await client.get("/api/v3/pwa/unrecognized")).status_code, 503)
            self.assertEqual((await client.post("/api/v3/pwa/subscription/lava/start", json={})).status_code, 503)
            self.assertEqual((await client.post("/course_v3_data/hsk3.json", json={})).status_code, 405)
            self.assertEqual((await client.get("/../secrets")).status_code, 404)

    async def test_visual_fixture_bookmarks_and_goal_without_database(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict(os.environ, QA_ENV):
                from app import qa_professional45_preview as preview
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=preview.app), base_url="http://qa.local") as client:
            q = await client.post("/api/v3/pwa/preferences", json={"streak_target_days":30})
            self.assertEqual(q.status_code, 200)
            self.assertEqual(q.json()["profile"]["streak_target_days"], 30)
            self.assertEqual((await client.post("/api/v3/pwa/preferences",json={"streak_target_days":31})).status_code, 422)
            self.assertEqual((await client.post("/api/v3/pwa/dictionary/saved/set",json={"hanzi":"坚持","saved":True})).status_code, 200)
            saved = (await client.post("/api/v3/pwa/dictionary/saved/list",json={})).json()
            self.assertIn("坚持", saved["words"])
            self.assertEqual((await client.post("/api/v3/pwa/dictionary/saved/set",json={"hanzi":"abc","saved":True})).status_code, 422)
            # Restore predictable test-state for later tests; never touches a real account.
            await client.post("/api/v3/pwa/preferences",json={"streak_target_days":14})
            await client.post("/api/v3/pwa/dictionary/saved/set",json={"hanzi":"坚持","saved":False})

    def test_server_must_not_run_in_production_or_with_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            from app import qa_professional45_preview as preview
            with self.assertRaises(RuntimeError):
                preview.qa_guard()
            with patch.dict(os.environ, QA_ENV):
                preview.qa_guard()
                with patch.dict(os.environ, {"DATABASE_URL":"postgresql://secret-invalid"}):
                    with self.assertRaises(RuntimeError):
                        preview.qa_guard()
                with patch.dict(os.environ, {"RAILWAY_PROJECT_ID":"another-project"}):
                    with self.assertRaises(RuntimeError):
                        preview.qa_guard()


if __name__ == "__main__":
    unittest.main()
