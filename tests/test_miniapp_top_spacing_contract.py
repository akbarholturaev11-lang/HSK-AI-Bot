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
