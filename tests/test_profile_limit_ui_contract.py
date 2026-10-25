"""Lightweight source contracts for Mini App profile and restored original limit UI.

These checks do not replace Telegram WebView screenshots or end-to-end checkout
testing. They prevent regressions in screen hierarchy and trial/Pro CTA wiring.
"""
import re
import unittest
from pathlib import Path

PROFILE = Path("app/static/course-v3.html").read_text(encoding="utf-8")
ADS = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")
ANDROID_DIRECT_LIMIT = Path("android/app/src/direct/java/com/pomp/hskai/feature/limit/SectionLimitBlock.kt").read_text(encoding="utf-8")


class MiniAppProfilePagodaAssetTests(unittest.TestCase):
    def test_selected_profile_background_has_a_public_route(self):
        main = Path("app/main.py").read_text(encoding="utf-8")
        css = Path("app/static/course_v3_data/profile-carousel.css").read_text(encoding="utf-8")
        svg_path = Path("app/static/assets/hsk-profile-pagoda.svg")
        self.assertTrue(svg_path.exists(), "Profile artwork must ship with server")
        self.assertIn('@app.get("/assets/hsk-profile-pagoda.svg")', main)
        self.assertIn('"app/static/assets/hsk-profile-pagoda.svg",', main)
        self.assertIn('"image/svg+xml",', main)
        self.assertIn('url("/assets/hsk-profile-pagoda.svg?v=20261014-2")', css)
        self.assertIn('profile-carousel.css?v=20261017-link-cards-1', PROFILE)
        self.assertIn("viewBox", svg_path.read_text(encoding="utf-8"))


class MiniAppProfileCarouselArtworkTests(unittest.TestCase):
    def test_every_slide_has_its_own_locally_served_art(self):
        main = Path("app/main.py").read_text(encoding="utf-8")
        css = Path("app/static/course_v3_data/profile-carousel.css").read_text(encoding="utf-8")
        for slide, filename in (
            ("version", "hsk-profile-pagoda.svg"),
            ("apps", "hsk-profile-apps.svg"),
            ("pro", "hsk-profile-pro.svg"),
        ):
            with self.subTest(slide=slide):
                self.assertIn(f".hp-promo-{slide}", css)
                self.assertIn(f'url("/assets/{filename}?v=', css)
                self.assertIn(f'@app.get("/assets/{filename}")', main)
                self.assertIn(f'"app/static/assets/{filename}"', main)
                self.assertTrue((Path("app/static/assets") / filename).exists())

    def test_native_pro_uses_distinct_art_and_never_offers_apps_slide(self):
        native = Path(
            "android/app/src/main/java/com/pomp/hskai/feature/profile/ProfilePromoCarousel.kt"
        ).read_text(encoding="utf-8")
        self.assertIn("R.drawable.profile_promo_pro", native)
        self.assertIn("R.drawable.profile_promo_pagoda", native)
        # Card order is dynamic now. Keep the native no-download-ad invariant
        # while Kotlin model tests exercise linked methods and Play filtering.
        page_kinds = native.split("internal enum class ProfilePromoPage(", 1)[1].split("\n}", 1)[0]
        keys = re.findall(r'^\s+[A-Z0-9_]+\("([^\"]+)"', page_kinds, re.MULTILINE)
        self.assertIn("hsk30", keys)
        self.assertIn("pro", keys)
        self.assertNotIn("apps", keys)
        page_policy = native.split("internal fun profilePromoPages(", 1)[1].split("\n/**", 1)[0]
        self.assertIn("if (checkoutAvailable) add(ProfilePromoPage.PRO)", page_policy)
        self.assertTrue(Path("android/app/src/main/res/drawable/profile_promo_pro.xml").exists())
        self.assertIn("profile-carousel.css?v=20261017-link-cards-1", PROFILE)

class MiniAppCourseVersionNavigationTests(unittest.TestCase):
    def test_settings_uses_original_hsk30_book_dialog(self):
        carousel = Path("app/static/course_v3_data/profile-carousel.js").read_text(encoding="utf-8")
        self.assertIn('onclick="App.profileCourseVersionBook()"', PROFILE)
        self.assertIn("function openProfileCourseVersionBook(){", PROFILE)
        body = PROFILE.split("function openProfileCourseVersionBook(){", 1)[1].split(
            "function maybeShowHsk30Promo(){", 1
        )[0]
        self.assertIn("SETTINGS_SHEET=false;", body)
        self.assertIn("hsk30BookHeader(status,false)", body)
        self.assertIn("openHsk30BookSheet(", body)
        self.assertIn("renderHsk30AccessGate(status)", body)
        self.assertIn("openHsk30PromoLevelPicker()", body)
        self.assertIn("switchCourseTrack('hsk20',null)", body)
        self.assertIn("openProfileCourseVersionBook();", carousel)
        self.assertNotIn("HskProfileCarousel.confirmHsk30()", carousel)
        from scripts.i18n_baseline_guard import git_blob_sha1
        digest = git_blob_sha1(Path("app/static/course_v3_data/profile-carousel.js").read_bytes())[:12]
        self.assertIn("profile-carousel.js?v=20261021-" + digest, PROFILE)

    def test_course_path_header_still_uses_compact_version_and_level_picker(self):
        course = PROFILE.split("function renderCourse(){", 1)[1].split(
            "function render", 1
        )[0]
        self.assertIn('onclick="App.courseTrackPicker()"', course)
        self.assertIn("courseTrackPicker:function(){openCourseTrackPicker()}", PROFILE)
        self.assertIn('class="course-choice-grid"', PROFILE)
        self.assertIn('class="course-choice-levels', PROFILE)
        self.assertIn("coursePickerSavedLevel(track)", PROFILE)


class MiniAppProfileHierarchyTests(unittest.TestCase):
    def test_profile_reduced_hierarchy_and_real_achievement_progress(self):
        body = PROFILE.split("function renderProfile(){", 1)[1].split(
            "/* ---------- sales_value_v1", 1
        )[0]
        self.assertIn('var nickname=esc(PROF.name||courseMessage("you",t.you))', body)
        self.assertIn("var showProLink=!paid&&!trialActive", body)
        self.assertIn("profile_after_streak", body)
        self.assertIn("profileAccuracyHtml()", body)
        self.assertIn("profile-access-badge", body)
        self.assertNotIn("profile_crown", body)
        self.assertIn("profile-friends-link", body)
        self.assertIn("completedLessons=Number(MAP&&MAP.progress&&MAP.progress.completed||0)", body)
        self.assertIn("streak=Number(MAP&&MAP.progress&&MAP.progress.streak||0)", body)
        self.assertIn("profile-compact-ach", body)
        self.assertLess(body.index("profile-friends-link"), body.index("streakCalHtml()"))
        self.assertLess(body.index("profile-compact-ach"), body.index("hsk-profile-promo-root"))
        for removed in ('class="pgoal"', 'class="stats profile-stats"', "t.mistakesSub",
                        "p.a1", "socialLinksHtml()"):
            self.assertNotIn(removed, body)

    def test_social_links_are_in_settings_instead_of_profile(self):
        settings = PROFILE.split("function settingsSheetHtml(){", 1)[1].split(
            "function refreshSettingsRows()", 1
        )[0]
        self.assertIn("socialLinksHtml()", settings)

    def test_android_profile_has_matching_header_and_compact_friends(self):
        native = Path("android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileScreen.kt").read_text(encoding="utf-8")
        self.assertIn("private fun ProfileFriendsLink(", native)
        self.assertNotIn("showProCrown =", native)
        self.assertIn("ProfileProCta", native)
        self.assertIn("ProfileAccuracyRings", native)
        self.assertIn("state.profile?.subscription?.isPaid != true", native)
        self.assertIn("state.trial?.active != true", native)
        self.assertIn("SocialLinksRow(onOpen = onOpenSupport)", native)
        self.assertNotIn("item { StatsGrid(state) }", native)
        self.assertNotIn("DailyGoalCard(\n", native.split("LazyColumn(", 1)[1].split("if (settingsOpen)", 1)[0])

    def test_localized_stat_labels_exist(self):
        for label in (
            "Статистика обучения",
            "O‘qish statistikasi",
            "Омори омӯзиш",
            "Пройдено уроков",
            "Tugatilgan darslar",
            "Дарсҳои анҷомшуда",
        ):
            with self.subTest(label=label):
                self.assertIn(label, PROFILE)


class MiniAppUnifiedLimitSheetTests(unittest.TestCase):
    """One photo-inspired sheet, contextual copy, one primary CTA."""

    def test_sheet_has_reason_promo_and_single_primary_cta(self):
        self.assertIn('class="caa-limit-sheet"', ADS)
        self.assertIn('class="caa-ls-mark han"', ADS)
        self.assertIn('class="caa-ls-why-text"', ADS)
        self.assertIn('class="caa-ls-promo"', ADS)
        self.assertIn('class="caa-ls-pay"', ADS)
        self.assertIn(".caa-ov.limit .caa-limit-sheet{", ADS)

    def test_limit_only_shows_pro_not_trial_or_footer(self):
        body = ADS.split("function showLimitPromo(opts){", 1)[1].split(
            "/* ============================================================", 1
        )[0]
        self.assertIn("els.limitPay.onclick", body)
        self.assertIn("els.limitClose.onclick", body)
        self.assertIn("startLimitSlides(feature);", body)
        self.assertNotIn("trialStatus(", body)
        self.assertNotIn("opts.onTrial", body)
        self.assertNotIn("opts.trialEligible", body)
        self.assertNotIn("els.limFoot.hidden=false", body)
        self.assertIn("var controls=[els.limitClose,els.limitPay]", ADS)

    def test_limit_copy_is_contextual_for_all_languages(self):
        for key in ("recognition", "pronunciation", "memorize",
                    "training_test", "placement", "mistake_review",
                    "voice", "lesson"):
            self.assertIn(key + ":", ADS)
        self.assertIn("LIMIT_REASONS", ADS)
        self.assertIn("LIMIT_HEADINGS", ADS)


class AndroidLimitParityTests(unittest.TestCase):
    def test_android_uses_a_bottom_sheet_with_one_cta(self):
        overlay = Path(
            "android/app/src/main/java/com/pomp/hskai/feature/limit/SectionLimitOverlay.kt"
        ).read_text(encoding="utf-8")
        self.assertIn("RoundedCornerShape(topStart = 28.dp", overlay)
        self.assertIn('Text("会"', overlay)
        self.assertIn("limit_sheet_heading", overlay)
        self.assertIn("limitOfferCopy(sourceKey)", overlay)
        self.assertIn("onClick = onClose", overlay)
        self.assertNotIn("onStartTrial", overlay)
        self.assertNotIn("secondaryLabel =", overlay)

    def test_channel_fallbacks_exclude_trial_and_keep_play_status_guidance(self):
        direct = ANDROID_DIRECT_LIMIT
        play = Path(
            "android/app/src/play/java/com/pomp/hskai/feature/limit/SectionLimitBlock.kt"
        ).read_text(encoding="utf-8")
        for code in (direct, play):
            self.assertNotIn("limit.actions.onStartTrial", code)
            self.assertNotIn("limit_try_trial", code)
        self.assertNotIn("secondaryLabel =", direct)
        self.assertNotIn("hint =", direct)
        self.assertIn("secondaryLabel = stringResource(R.string.action_close)", play)
        self.assertIn("onSecondary = onClose", play)
        self.assertIn("R.string.play_limit_description", play)
        self.assertIn("R.string.play_limit_renewal", play)
        self.assertNotIn("openSubscription", play)
        self.assertIn("onPrimary = openSubscription", direct)
        self.assertIn("onPrimary = limit.actions.onRecheck", play)


if __name__ == "__main__":
    unittest.main()
