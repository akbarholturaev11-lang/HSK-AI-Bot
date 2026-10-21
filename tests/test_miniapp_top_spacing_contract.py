"""Prevent repeated top safe-area padding in cached Telegram Mini App tabs."""
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"


def test_secondary_tab_titles_use_compact_spacing_without_losing_safe_area():
    course = (STATIC / "course-v3.html").read_text(encoding="utf-8")
    assert ".wrap{max-width:var(--shell);margin:0 auto;min-height:100vh;position:relative;padding-top:var(--safe-t)}" in course
    assert ".scr:not(#s-course)>.htop{padding-top:6px}" in course
    assert ".ctop{position:sticky;top:var(--safe-t)" in course


def test_embedded_resources_do_not_duplicate_telegram_top_inset():
    course = (STATIC / "course-v3.html").read_text(encoding="utf-8")
    phrases = (STATIC / "hsk-gaplar.html").read_text(encoding="utf-8")
    dictionary = (STATIC / "hsk-lugat.html").read_text(encoding="utf-8")
    assert 'embedded:"1"' in course
    assert "html.hsk-embedded body { padding-top: 0; }" in phrases
    assert "html.hsk-embedded .page { padding-top: 8px; }" in phrases
    assert "html.hsk-embedded .view{top:0}" in dictionary
    assert "html.hsk-embedded .hsk-native-back-duplicate" in dictionary

def test_liquid_glass_bottom_navigation_stylesheet_is_public_and_safe_area_aware():
    """A missing FastAPI asset allowlist entry silently shows the old navigation."""
    api = (STATIC.parent / "main.py").read_text(encoding="utf-8")
    course = (STATIC / "course-v3.html").read_text(encoding="utf-8")
    glass = (STATIC / "course_v3_data" / "liquid-glass-nav.css").read_text(encoding="utf-8")

    assert '"liquid-glass-nav.css": "text/css"' in api
    assert 'href="/course_v3_data/liquid-glass-nav.css?v=20261021-1"' in course
    assert "bottom: calc(10px + var(--safe-b))" in glass
    assert "backdrop-filter: blur(26px)" in glass
    assert ':root[data-hsk-theme="dark"] .nav' in glass
    assert "prefers-reduced-transparency" in glass
    assert '<nav class="nav" id="nav">' in course
    assert 'data-s="voice"' in course

