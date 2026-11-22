"""Knot Thread launch mark, Pro panda and the shared Pro/Trial colour set.

Owner request 2026-11-22: a minimalist launch effect and a Pro panda with its
own effects, delivered as isolated components; Pro and Trial windows share
one light paper + gold palette. Pins PWA/Android parity, the canonical panda
(no new character), reduced-motion handling and the "not wired yet" boundary.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"
ANDROID = ROOT / "android/app/src/main/java/com/pomp/hskai"

LAUNCH_JS = (STATIC / "assets/brand/hsk-launch-mark.js").read_text(encoding="utf-8")
LAUNCH_CSS = (STATIC / "assets/brand/hsk-launch-mark.css").read_text(encoding="utf-8")
THEME_CSS = (STATIC / "assets/brand/hsk-pro-theme.css").read_text(encoding="utf-8")
PANDA_JS = (STATIC / "assets/characters/hsk-pro-panda.js").read_text(encoding="utf-8")
PANDA_CSS = (STATIC / "assets/characters/hsk-pro-panda.css").read_text(encoding="utf-8")
INLINE_PRO = (STATIC / "course_v3_data/iphone-pwa-inline-pro.js").read_text(encoding="utf-8")
TOKENS = (STATIC / "course_v3_data/design-tokens.css").read_text(encoding="utf-8")
LI = (STATIC / "course_v3_li_onboarding.html").read_text(encoding="utf-8")
LAUNCH_KT = (ANDROID / "core/design/components/HskLaunchMark.kt").read_text(encoding="utf-8")
PRO_COLORS_KT = (ANDROID / "core/design/ProColors.kt").read_text(encoding="utf-8")
PRO_PANDA_KT = (ANDROID / "feature/limit/ProPanda.kt").read_text(encoding="utf-8")


def _js_timeline() -> dict[str, list[int] | int]:
    raw = re.search(r"var TIMELINE=(\{.*?\});", LAUNCH_JS).group(1)
    out: dict[str, list[int] | int] = {}
    for key, value in re.findall(r"(\w+):(\[[^\]]*\]|\d+)", raw):
        out[key] = [int(v) for v in value.strip("[]").split(",")] if value.startswith("[") else int(value)
    return out


def _kt_const(name: str) -> int:
    return int(float(re.search(rf"const val {name} = ([\d.]+)f", LAUNCH_KT).group(1)))


def _light_token(name: str) -> str:
    # First :root block of design-tokens.css is the light theme.
    return re.search(rf"--hsk-{name}:\s*(#[0-9A-Fa-f]{{6}})", TOKENS).group(1).upper()


class LaunchMarkContractTests(unittest.TestCase):
    def test_pwa_and_android_share_one_timeline(self):
        t = _js_timeline()
        self.assertEqual(t["seal"], [_kt_const("SEAL_START"), _kt_const("SEAL_MS")])
        self.assertEqual(t["strandA"], [_kt_const("STRAND_A_START"), _kt_const("STRAND_MS")])
        self.assertEqual(t["strandB"], [_kt_const("STRAND_B_START"), _kt_const("STRAND_MS")])
        self.assertEqual(t["weave"], [_kt_const("WEAVE_START"), _kt_const("WEAVE_MS")])
        self.assertEqual(t["glint"], [_kt_const("GLINT_START"), _kt_const("GLINT_MS")])
        self.assertEqual(t["word"], [_kt_const("WORD_START"), _kt_const("WORD_MS")])
        self.assertEqual(t["total"], _kt_const("TOTAL_MS"))
        self.assertLessEqual(t["total"], 1200)

    def test_css_keyframes_use_the_same_beats(self):
        t = _js_timeline()
        for selector, beat in ((".hlm-a path", "strandA"), (".hlm-b path", "strandB"),
                               (".hlm-x", "weave"), (".hlm-glint", "glint"), (".hlm-word", "word")):
            start, duration = t[beat]
            rule = re.search(rf"\.hlm\.is-playing {re.escape(selector)}\{{[^}}]*\}}", LAUNCH_CSS).group(0)
            self.assertIn(f"{duration}ms", rule, selector)
            if start:
                self.assertIn(f"{start}ms both", rule, selector)

    def test_reduced_motion_shows_the_finished_mark(self):
        self.assertIn("prefers-reduced-motion:reduce", LAUNCH_CSS)
        self.assertIn('el.classList.add("is-static")', LAUNCH_JS)
        self.assertIn("hskMotionOff(context)", LAUNCH_KT)
        self.assertIn("if (motionOff) LaunchMarkTimeline.TOTAL_MS else 0f", LAUNCH_KT)

    def test_draws_the_real_logo_geometry(self):
        logo = (ROOT / "branding/hsk-ai-logo.svg").read_text(encoding="utf-8")
        for path in re.findall(r'var [ABX]="([^"]+)"', LAUNCH_JS):
            self.assertIn(path, logo)
        self.assertIn("RoundRect(35f, 35f, 73f, 73f, CornerRadius(4.5f))", LAUNCH_KT)

    def test_is_not_wired_and_the_golden_logo_stays_shipped(self):
        for name in ("course-v3.html", "course_v3_li_onboarding.html", "iphone-pwa-login.html"):
            text = (STATIC / name).read_text(encoding="utf-8")
            self.assertNotIn("hsk-launch-mark", text, name)
            self.assertNotIn("hsk-pro-panda", text, name)
        self.assertIn('id="hsk-launch-splash"', (STATIC / "course-v3.html").read_text(encoding="utf-8"))
        main = "".join(p.read_text(encoding="utf-8") for p in ANDROID.rglob("*.kt")
                       if p.name not in {"HskLaunchMark.kt", "ProPanda.kt", "HskProGlint.kt"})
        self.assertNotIn("HskLaunchMark(", main)
        self.assertNotIn("ProPanda(", main)


class ProPandaContractTests(unittest.TestCase):
    def test_uses_the_canonical_inline_pro_panda_drawing(self):
        def drawing(src: str, prefix: str) -> str:
            start = src.index("var INK=")
            body = src[start:src.index('return "<svg', start)]
            body = re.sub(r"\s+", "", body).replace(prefix, "PD-").replace('hipCard"+pose+"', '"+uid+"')
            # The reusable panda deliberately drops the offer-only gift pose list.
            return re.sub(r'if\(.*?\)pose="pro";', "", body, count=1)
        self.assertEqual(drawing(PANDA_JS, "hpp-"), drawing(INLINE_PRO, "hip-pd-"))

    def test_poses_effects_and_reduced_motion(self):
        self.assertIn('var POSES=["pro","celebrate","read"]', PANDA_JS)
        self.assertNotIn("−20%\"", PANDA_JS.split("function render")[1])
        for cls in (".hpp-halo", ".hpp-sparks.is-on i", ".hpp-glint::after"):
            self.assertIn(cls, PANDA_CSS)
        self.assertIn("prefers-reduced-motion:reduce", PANDA_CSS)
        self.assertIn("aria-hidden", PANDA_JS)
        # A celebrating panda settles instead of bouncing forever.
        self.assertIn(".hpp-bounce{animation:hpp-bounce .8s ease-in-out 3}", PANDA_CSS)

    def test_android_reuses_the_course_panda(self):
        self.assertIn("CoursePandaMascot(", PRO_PANDA_KT)
        self.assertIn("clearAndSetSemantics", PRO_PANDA_KT)
        self.assertIn("hskMotionOff(context)", PRO_PANDA_KT)
        self.assertRegex(PANDA_JS, r"i<8;")
        self.assertIn("internal const val PRO_SPARK_COUNT = 8", PRO_PANDA_KT)


class ProTrialPaletteContractTests(unittest.TestCase):
    ROLES = {
        "paper": "paper", "surface": "paper-raised", "ink": "ink", "muted": "ink-secondary",
        "line": "divider", "gold": "gold", "gold-ink": "gold-ink", "gold-soft": "gold-soft",
        "cta": "cinnabar", "cta-deep": "cinnabar-ink",
    }
    KOTLIN = {
        "paper": "Paper", "surface": "PaperRaised", "ink": "Ink", "muted": "InkSecondary",
        "line": "Divider", "gold": "Gold", "gold-ink": "GoldInk", "gold-soft": "GoldSoft",
        "cta": "Cinnabar", "cta-deep": "CinnabarInk",
    }

    def test_pwa_roles_alias_the_light_design_tokens(self):
        for role, token in self.ROLES.items():
            match = re.search(rf"--hsk-pro-{role}:var\(--hsk-{token},(#[0-9A-Fa-f]{{6}})\)", THEME_CSS)
            self.assertIsNotNone(match, role)
            self.assertEqual(match.group(1).upper(), _light_token(token), role)

    def test_android_roles_read_the_same_tokens(self):
        for role, name in self.KOTLIN.items():
            self.assertRegex(PRO_COLORS_KT, rf"get\(\) = PompColors\.{name}\n", role)

    def test_trial_window_uses_the_light_pro_palette(self):
        theme = LI[LI.index("/* ---- Pro / Trial theme"):LI.index("/* Pro intro:")]
        self.assertNotIn("background:#211D17", theme)
        self.assertNotIn("color:#fff", theme)
        self.assertIn("html.li-trial-offer .wrap.dark{background:var(--li-pro-paper)}", LI)
        self.assertNotIn("color-scheme:dark", LI)
        for role, token in (("paper", "paper"), ("gold-ink", "gold-ink"), ("gold-soft", "gold-soft")):
            self.assertIn(f"--li-pro-{role}:var(--hsk-{token},{_light_token(token)})", LI)
        trial = LI[LI.index(".trial h2{"):LI.index(".trial-hero{")]
        self.assertNotIn("255,255,255", trial)
        course = (STATIC / "course-v3.html").read_text(encoding="utf-8")
        self.assertIn("html.hsk-pwa-browser:has(.pwa-checkout-trial) body{background:var(--paper)}", course)
        self.assertNotIn('theme.setAttribute("content","#211D17")', course)
        bridge = (STATIC / "course_v3_data/iphone-pwa-inline-pro-bridge.js").read_text(encoding="utf-8")
        self.assertNotIn("#211D17", bridge)


if __name__ == "__main__":
    unittest.main()
