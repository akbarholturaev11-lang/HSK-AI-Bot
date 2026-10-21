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

def test_liquid_glass_navigation_is_inline_and_keeps_existing_routes():
    """The Mini App glass effect must not depend on a new CSS HTTP route."""
    course = (STATIC / "course-v3.html").read_text(encoding="utf-8")
    api = (STATIC.parent / "main.py").read_text(encoding="utf-8")

    assert "liquid-glass-nav.css" not in course
    assert 'liquid-glass-nav.css": "text/css"' not in api
    assert "/* Inline nav skin: no extra static-asset endpoint or CSS request. */" in course
    assert "bottom: calc(10px + var(--safe-b))" in course
    assert "-webkit-backdrop-filter: blur(26px)" in course
    assert "backdrop-filter: blur(26px)" in course
    assert ':root[data-hsk-theme="dark"] .nav' in course
    assert "@media (prefers-reduced-transparency: reduce)" in course
    assert "@media (prefers-reduced-motion: reduce)" in course
    assert '<nav class="nav" id="nav">' in course
    assert course.count('data-s="') >= 5
    for tab in ("course", "mashq", "voice", "rating", "profile"):
        assert f'data-s="{tab}"' in course
    assert 'function navInit(){document.querySelectorAll("#nav button")' in course

def test_practice_tab_renders_without_waiting_for_background_preloads():
    course = (STATIC / "course-v3.html").read_text(encoding="utf-8")
    assert 'if(!$("#s-mashq").firstElementChild)renderMashq()' in course
    assert 'requestIdleCallback(warmInIdle,{timeout:1800})' in course
    assert 'prefetchPracticeAssets();' in course
    assert 'if(window.RESOURCE)RESOURCE.warm();' in course
    # All four existing asset warm-ups must remain active.
    assert 'loadJsOnce(practiceWordsUrl()).catch(function(){})' in course
    assert 'loadJsOnce(lessonGateUrl()).catch(function(){})' in course
    assert 'if(!STATE.phrases.frame)ensure("phrases")' in course
    assert 'if(!STATE.dict.frame)ensure("dict")' in course
    # No change to server authorization on paid HSK 3.0 levels.
    assert 'MASHQ_ACCESS_PENDING=courseTrackStatus(true)' in course


def test_glass_optical_layers_do_not_start_continuous_animations():
    course = (STATIC / "course-v3.html").read_text(encoding="utf-8")
    assert '.nav::after {' in course
    assert '--glass-light-x: 25%' in course
    assert '"--glass-light-x"' in course
    assert 'pointerdown' in course
    assert '@media (prefers-reduced-transparency: reduce)' in course
    assert '@media (prefers-reduced-motion: reduce)' in course
