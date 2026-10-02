import json
import re
import subprocess
from pathlib import Path


SUBSCRIPTION_HTML = Path("app/static/subscription.html")


def _html() -> str:
    return SUBSCRIPTION_HTML.read_text(encoding="utf-8")


def test_subscription_checkout_keeps_backend_contracts():
    html = _html()
    for marker in (
        "/api/subscription-miniapp/overview",
        "/api/subscription-miniapp/discount-start",
        "/api/subscription-miniapp/quote",
        "/api/subscription-miniapp/event",
        "/api/subscription-miniapp/submit",
        "X-Telegram-Init-Data",
    ):
        assert marker in html


def test_subscription_checkout_routes_banks_and_permanent_unlock_separately():
    html = _html()
    functions = []
    for name in ("hasMethodStep", "isHsk30Unlock", "flow"):
        match = re.search(r"function " + name + r"\([^)]*\)\{[\s\S]*?\}", html)
        assert match is not None
        functions.append(match.group(0))
    script = (
        'const state={mode:"subscription",plan:"1_month",done:false,pending:false};'
        + "\n".join(functions)
        + '\nconst results={}; for(const region of ["tj","uz","ru","cn","other"]){'
        + 'state.region=region;state.mode="subscription";results[region]=flow();'
        + 'state.mode="hsk30_unlock";results[region+"_unlock"]=flow();}'
        + '\nstate.pending=true;results.pending=flow();console.log(JSON.stringify(results));'
    )
    results = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    for region in ("tj", "cn"):
        assert results[region] == ["country", "plans", "method", "pay"]
        assert results[region + "_unlock"] == ["country", "method", "pay"]
    for region in ("uz", "ru", "other"):
        assert results[region] == ["country", "plans", "pay"]
        assert results[region + "_unlock"] == ["country", "pay"]
    assert results["pending"] == ["done"]
    assert "Dushanbe City" in html
    assert "«На карту»" in html
    assert 'id="qrPreview"' in html
    assert 'cn:"🇨🇳"' in html


def test_subscription_checkout_preserves_discount_modes():
    html = _html()
    for mode in ("subscription", "referral_discount", "admin_discount", "feedback_discount"):
        assert mode in html
