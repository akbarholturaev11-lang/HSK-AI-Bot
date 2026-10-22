"""Static regression checks for the opt-in Mini App glass renderer."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "app/static/course-v3.html"
ROUTES = ROOT / "app/main.py"
ASSETS = ROOT / "app/static/assets/liquid-glass"


def test_glass_is_explicitly_opt_in():
    html = HTML.read_text(encoding="utf-8")
    assert "get('liquid_glass')!=='1'" in html
    assert "window.addEventListener('load',start,{once:true})" in html
    assert html.count('navInit();') == 1
    for section in ("course", "mashq", "voice", "rating", "profile"):
        assert f'data-s="{section}"' in html
    assert "App.show(b.dataset.s)" in html


def test_liquid_glass_assets_are_same_origin_and_allowlisted():
    html = HTML.read_text(encoding="utf-8")
    routes = ROUTES.read_text(encoding="utf-8")
    assert "var prefix='/assets/liquid-glass/'" in html
    assert '@app.get("/assets/liquid-glass/{filename}")' in routes
    assert "_LIQUID_GLASS_PILOT_ASSETS.get(filename)" in routes
    for asset in ("html2canvas.min.js", "container.js", "nav-glass.js", "nav-glass.css"):
        assert asset in routes
        assert (ASSETS / asset).is_file()
    assert (ASSETS / "LICENSE").is_file()
    assert (ASSETS / "html2canvas.LICENSE").is_file()


def test_original_navigation_has_safe_fallback():
    src = (ASSETS / "nav-glass.js").read_text(encoding="utf-8")
    assert "nav.classList.add('hsk-lg-active')" in src
    assert "nav.classList.remove('hsk-lg-active')" in src
    assert "webgl-context-lost" in src
    assert "prefers-reduced-transparency: reduce" in src
    assert "html2canvas(document.body" in src
    assert "allowTaint:false" in src
    assert "status.enabled=false" in src
