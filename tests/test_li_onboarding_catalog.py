"""Exact user-demo Li Panda copy and local-first generated catalog contract."""
import hashlib
import unittest
from pathlib import Path

from scripts import i18n_build_li_onboarding as li


class LiOnboardingCanonicalCatalogTests(unittest.TestCase):
    def test_all_three_locales_have_exact_demo_copy_and_reactions(self):
        sources = li.read_sources()
        self.assertEqual(set(sources), {"uz", "ru", "tj"})
        self.assertEqual(len({k for k in sources["ru"] if k.startswith("copy.")}), 66)
        self.assertEqual(sources["uz"]["copy.firstTime"], "HSK AI'da birinchi marta")
        self.assertEqual(sources["ru"]["copy.loadCourse"], "Загружаем курс…")
        self.assertEqual(sources["tj"]["STREAKS.14.say"],
                         "Ду ҳафта — ин дигар тасодуф нест!")

    def test_generated_bundle_matches_reviewed_local_sources(self):
        output = li.output_files(li.read_sources())
        for relative, data in output.items():
            self.assertEqual((Path(relative)).read_text(encoding="utf-8"), data)

    def test_visual_demo_pinned_and_real_app_uses_catalog_not_copy_duplicates(self):
        demo = Path("docs/onboarding-li/DEMO_REFERENCE_ONLY.html").read_bytes()
        self.assertEqual(hashlib.sha256(demo).hexdigest(),
                         "767c2de59116229dab9304e3036ae589399379340013f1d137eae7df82644b30")
        html = Path("app/static/course_v3_li_onboarding.html").read_text(encoding="utf-8")
        self.assertIn("hsk-li-onboarding-i18n.js?v=", html)
        self.assertIn("var T=window.HSKAI_LI_I18N||{};", html)
        self.assertNotIn('accountTitle:"У вас есть аккаунт', html)
        self.assertIn("window.HSKAI_LI_OPTIONS", html)
