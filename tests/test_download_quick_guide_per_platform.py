"""The post-download guide must belong to the device that downloaded.

The dialog keeps one step list per platform in the same markup and shows the
one the chosen platform points at. Android had no list and no copy, so a phone
that tapped "download" was shown whatever was in the DOM — the macOS DMG
steps — which is advice it cannot follow.

Pinned here: every platform whose steps the dialog can show has a list in the
HTML, copy in all three languages, and CSS that hides the other platforms'
lists.
"""

import re
import unittest
from pathlib import Path


STATIC = Path(__file__).resolve().parents[1] / "app" / "static"
HTML = (STATIC / "desktop-download.html").read_text(encoding="utf-8")
JS = (STATIC / "desktop-download-page.js").read_text(encoding="utf-8")
CSS = (STATIC / "desktop-download-page.css").read_text(encoding="utf-8")

LANGUAGES = ("uz", "ru", "tj")
# copy key -> (css class suffix, step slot prefix)
GUIDED = {"mac": ("macos", "m"), "windows": ("windows", "w"), "android": ("android", "a")}


def _step_lists(copy_key: str) -> list[list[str]]:
    """Every language's copy of one step list, as its step titles."""

    blocks = re.findall(rf"{copy_key}QuickSteps: \[\n(.*?)\n      \]", JS, re.S)
    return [re.findall(r'^\s*\["([^"]+)"', block, re.M) for block in blocks]


class QuickGuideCopyTests(unittest.TestCase):
    def test_every_guided_platform_has_steps_in_all_three_languages(self):
        for copy_key in GUIDED:
            with self.subTest(platform=copy_key):
                lists = _step_lists(copy_key)
                self.assertEqual(len(lists), len(LANGUAGES))
                self.assertTrue(all(lists[0]))
                # One language may not quietly carry fewer steps than another.
                self.assertEqual({len(steps) for steps in lists}, {len(lists[0])})

    def test_android_steps_talk_about_the_phone_not_the_desktop(self):
        for steps in _step_lists("android"):
            joined = " ".join(steps)
            with self.subTest(steps=joined):
                self.assertIn("APK", joined)
                for desktop_only in ("DMG", "EXE", "Applications", "SmartScreen"):
                    self.assertNotIn(desktop_only, joined)


class QuickGuideMarkupTests(unittest.TestCase):
    def test_each_platform_list_has_a_slot_for_every_step(self):
        for copy_key, (css_name, prefix) in GUIDED.items():
            with self.subTest(platform=copy_key):
                self.assertIn(f"quick-guide-steps quick-platform-{css_name}", HTML)
                slots = re.findall(rf'data-quick-step-title="{prefix}(\d+)"', HTML)
                self.assertEqual(
                    [int(slot) for slot in slots],
                    list(range(1, len(_step_lists(copy_key)[0]) + 1)),
                )

    def test_the_script_knows_the_prefix_and_badge_of_every_list(self):
        prefixes = dict(re.findall(r"(\w+): \"(\w)\"", re.search(r"QUICK_PREFIX = \{([^}]*)\}", JS).group(1)))
        badges = dict(re.findall(r"(\w+): \"([\w ]+)\"", re.search(r"QUICK_BADGE = \{([^}]*)\}", JS).group(1)))
        for css_name, prefix in GUIDED.values():
            with self.subTest(platform=css_name):
                self.assertEqual(prefixes.get(css_name), prefix)
                self.assertTrue(badges.get(css_name))


def _hidden_selectors() -> set[str]:
    hidden = set()
    for rule in re.finditer(r"([^{}]+)\{([^{}]*)\}", CSS):
        if "display: none" not in rule.group(2):
            continue
        hidden.update(part.strip() for part in rule.group(1).split(","))
    return hidden


class QuickGuideStyleTests(unittest.TestCase):
    def test_one_platform_hides_the_others(self):
        hidden = _hidden_selectors()
        for css_name, _ in GUIDED.values():
            for other, _ in GUIDED.values():
                if other == css_name:
                    continue
                with self.subTest(shown=css_name, hidden=other):
                    self.assertIn(
                        f'[data-quick-guide][data-platform="{css_name}"] '
                        f".quick-platform-{other}",
                        hidden,
                    )


if __name__ == "__main__":
    unittest.main()
