"""UI contract for restored ranking title and compact profile identity (Mini App / Android)."""
from pathlib import Path

WEB = Path("app/static/course-v3.html").read_text(encoding="utf-8")
ANDROID = Path("android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileScreen.kt").read_text(encoding="utf-8")
RATING = Path("android/app/src/main/java/com/pomp/hskai/feature/rating/RatingScreen.kt").read_text(encoding="utf-8")
RINGS = Path("android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileAccuracyRings.kt").read_text(encoding="utf-8")


def test_ranking_has_header_in_both_apps():
    assert 'class="section-title rating-title"' in WEB
    assert "R.string.nav_rating" in RATING


def test_single_display_name_and_subscription_badge_after_avatar():
    profile = WEB.split("function renderProfile(){", 1)[1].split("/* ---------- sales_value_v1", 1)[0]
    assert '<strong class="profile-display-name">' in profile
    assert profile.count("profile-access-badge") == 1
    assert 'class="pun"' not in profile
    assert 'class="profile-title">\'+nickname' not in profile
    assert "text = stringResource(R.string.nav_profile)" in ANDROID
    hero = ANDROID.split("private fun ProfileHero(", 1)[1].split("private fun profileAvatarDrawable", 1)[0]
    assert hero.count("AccessPill(") == 1
    assert 'text = "@$username"' not in hero


def test_accuracy_compact_and_profile_surfaces_soft():
    web_rings = WEB.split("function profileAccuracyHtml(){", 1)[1].split("function renderProfile(){", 1)[0]
    assert "profile-accuracy-help" not in web_rings
    assert "accuracy-note" not in web_rings
    assert "profile_accuracy_note" not in RINGS
    assert "profile_accuracy_count" not in RINGS
    assert "PompColors.PaperRaised.copy(alpha = 0.72f)" in RINGS
    assert "profile-hero-content" in WEB
