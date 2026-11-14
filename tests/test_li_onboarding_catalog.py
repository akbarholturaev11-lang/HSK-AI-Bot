"""Exact user-demo Li Panda copy and local-first generated catalog contract."""
import hashlib
import json
import re
import unittest
from pathlib import Path

from scripts import i18n_build_li_onboarding as li


class LiOnboardingCanonicalCatalogTests(unittest.TestCase):
    def test_all_three_locales_have_exact_demo_copy_and_reactions(self):
        sources = li.read_sources()
        self.assertEqual(set(sources), {"uz", "ru", "tj"})
        self.assertEqual(len({k for k in sources["ru"] if k.startswith("copy.")}), 69)
        self.assertEqual(sources["uz"]["copy.firstTime"], "HSK AI'da birinchi marta")
        self.assertEqual(sources["ru"]["copy.loadCourse"], "Загружаем курс…")
        self.assertEqual(sources["tj"]["STREAKS.14.say"],
                         "Ду ҳафта — ин дигар тасодуф нест!")

    def test_final_profile_keeps_original_user_demo_speech_in_three_languages(self):
        source = li.read_sources()
        expected = {
            "uz": "Progressingizni yo'qotmang! Keling, sizga profil ochamiz.",
            "ru": "Не потеряйте свой прогресс! Давайте создадим вам профиль.",
            "tj": "Пешрафти худро гум накунед! Биёед, барои шумо профил созем.",
        }
        for lang, message in expected.items():
            with self.subTest(lang=lang):
                self.assertEqual(source[lang]["copy.profile"], message)

    def test_home_screen_guide_strings_are_canonical_in_three_languages(self):
        sources = li.read_sources()
        for lang in ("uz", "ru", "tj"):
            for key in li.INSTALL_KEYS:
                self.assertTrue(sources[lang][key].strip(), (lang, key))
        self.assertEqual(len(li.INSTALL_KEYS), 23)
        self.assertEqual(len(li.PRO_GOAL_KEYS), 10)
        for lang in ("uz", "ru", "tj"):
            for key in li.PRO_GOAL_KEYS:
                self.assertTrue(sources[lang][key].strip(), (lang, key))
        self.assertEqual(len({k for k in sources["uz"] if k.startswith("copy.")}), 69)

    def test_telegram_handoff_landing_strings_are_canonical_in_three_languages(self):
        sources = li.read_sources()
        self.assertEqual(len(li.HANDOFF_KEYS), 6)
        bundle = li.output_files(sources)[li.OUTPUT]
        script = Path("app/static/iphone-pwa-handoff.js").read_text(encoding="utf-8")
        used = set(re.findall(r'"(handoff\.[A-Za-z]+)"', script))
        # The landing page may only name strings the catalog really ships.
        self.assertEqual(used, set(li.HANDOFF_KEYS))
        for lang in ("uz", "ru", "tj"):
            for key in li.HANDOFF_KEYS:
                self.assertTrue(sources[lang][key].strip(), (lang, key))
                self.assertIn(json.dumps(sources[lang][key], ensure_ascii=False), bundle)
        for key in ("handoff.accountMismatch", "handoff.switchAccount"):
            for lang in ("uz", "ru", "tj"):
                self.assertIn("Telegram", sources[lang][key])

    def test_hsk30_access_gate_is_localized_without_changing_original_demo(self):
        sources = li.read_sources()
        keys = ("copy.hsk30AccessNeeded", "copy.hsk30OpenInCourse", "copy.hsk30Use20")
        for lang in ("uz", "ru", "tj"):
            with self.subTest(lang=lang):
                for key in keys:
                    self.assertIn("HSK", sources[lang][key])
                self.assertIn("3.0", sources[lang]["copy.hsk30AccessNeeded"])

    def test_generated_bundle_matches_reviewed_local_sources(self):
        output = li.output_files(li.read_sources())
        for relative, data in output.items():
            self.assertEqual((Path(relative)).read_text(encoding="utf-8"), data)

    def test_guest_li_install_assets_use_current_versioned_blobs(self):
        # The guest Li page is outside the shared cache-token generator.
        # Stale versions make Safari PWA Cache First serve old UI and copy.
        html = Path("app/static/course_v3_li_onboarding.html").read_text(encoding="utf-8")
        for asset in ("li-onboarding-install.js", "li-onboarding-install.css",
                      "hsk-li-onboarding-i18n.js"):
            raw = (Path("app/static/course_v3_data") / asset).read_bytes()
            digest = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii")
                                  + b"\0" + raw).hexdigest()[:12]
            pattern = rf'(?:href|src)="/course_v3_data/{re.escape(asset)}\?v=\d{{8}}-{digest}"'
            self.assertRegex(html, pattern, asset)

    def test_visual_demo_pinned_and_real_app_uses_catalog_not_copy_duplicates(self):
        demo = Path("docs/onboarding-li/DEMO_REFERENCE_ONLY.html").read_bytes()
        self.assertEqual(hashlib.sha256(demo).hexdigest(),
                         "767c2de59116229dab9304e3036ae589399379340013f1d137eae7df82644b30")
        html = Path("app/static/course_v3_li_onboarding.html").read_text(encoding="utf-8")
        self.assertIn("hsk-li-onboarding-i18n.js?v=", html)
        self.assertIn("var T=window.HSKAI_LI_I18N||{};", html)
        self.assertNotIn('accountTitle:"У вас есть аккаунт', html)
        self.assertIn("window.HSKAI_LI_OPTIONS", html)
