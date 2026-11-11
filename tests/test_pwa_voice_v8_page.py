"""AI Voice V8 PWA page: catalog-driven copy, served topic photos, contracts.

Run: python -m unittest tests.test_pwa_voice_v8_page
"""
import json
import re
import unittest
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.main import app

PAGE = Path("app/static/iphone-pwa-voice.html")
TOPICS = ("free", "daily", "shopping", "food", "travel", "school", "friends", "work", "hsk")


def catalog(locale):
    path = Path("localization/ui") / locale / "course.json"
    return json.loads(path.read_text(encoding="utf-8"))["messages"]


class PwaVoiceV8PageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.html = PAGE.read_text(encoding="utf-8")

    def test_every_visible_label_exists_in_all_three_languages(self):
        keys = set(re.findall(r'data-i18n(?:-aria|-title|-placeholder|-example)?="([^"]+)"', self.html))
        keys |= set(re.findall(r"msg\('((?:voiceV8|courseVoiceInline)\.[A-Za-z0-9]+)'\)", self.html))
        keys |= {"voiceV8." + name for name in re.findall(r":'(status[A-Za-z]+)'", self.html)}
        keys |= set(re.findall(r"key:'(voiceV8\.topic[A-Za-z]+)'", self.html))
        self.assertGreater(len(keys), 55)
        for locale in ("uz", "ru", "tj"):
            messages = catalog(locale)
            for key in sorted(keys):
                with self.subTest(locale=locale, key=key):
                    self.assertTrue(messages.get(key), key)

    def test_page_uses_only_the_authenticated_pwa_voice_contract(self):
        for endpoint in ("/api/v3/pwa-auth/session", "/api/v3/pwa/voice/me",
                         "/api/v3/pwa/voice/session/start", "/api/v3/pwa/voice/session/mode",
                         "/api/v3/pwa/voice/message", "/api/v3/pwa/voice/session/end"):
            self.assertIn(endpoint, self.html)
        self.assertIn("'X-HSK-PWA-CSRF':csrf", self.html)
        self.assertIn("r.headers.get('X-HSK-PWA-User-ID')!==String(a.user_id)", self.html)
        self.assertIn("liveCandidate.connect(sessionId,'',actor.csrf)", self.html)
        self.assertIn("resource.acceptPracticeActor(window,a.user_id)", self.html)
        for forbidden in ("initData", "telegram-web-app.js", "/api/voice-practice/", "unsplash.com",
                          "maximum-scale", "user-scalable", "base64,"):
            self.assertNotIn(forbidden, self.html)
        self.assertIn('<script defer src="/voice-live.js?v=', self.html)
        self.assertEqual(self.html.count("</body>"), 1)
        roles = dict(re.findall(r"(\w+):'(friend|roommate|seller|classmate|manager_wang|teacher_li)'", self.html))
        self.assertEqual(set(roles), set(TOPICS))

    async def test_topic_photos_are_fixed_public_jpegs(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hsk.test") as client:
            for topic in TOPICS:
                with self.subTest(topic=topic):
                    data = Path(f"app/static/assets/voice-v8/{topic}.jpg").read_bytes()
                    self.assertTrue(data.startswith(b"\xff\xd8"))
                    response = await client.get(f"/assets/voice-v8/{topic}.jpg?v=20261111-1")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers["content-type"], "image/jpeg")
                    self.assertEqual(response.content, data)
            for name in ("other.jpg", "free.png", "..%2Fmain.py", "free.jpg.bak"):
                with self.subTest(name=name):
                    self.assertEqual((await client.get(f"/assets/voice-v8/{name}")).status_code, 404)


if __name__ == "__main__":
    unittest.main()
