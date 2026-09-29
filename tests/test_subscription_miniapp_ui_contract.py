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


def test_subscription_checkout_country_first_payment_copy():
    html = _html()
    assert '[\"country\",\"start\",\"method\",\"pay\"]' in html
    assert "DC (По номеру карты)" in html
    assert "«На карту»" in html
    assert "QR-кодни сканер қилиб тўланг" in html
    assert 'data-country="cn"' in html or 'cn:"🇨🇳"' in html


def test_subscription_checkout_preserves_discount_modes():
    html = _html()
    for mode in ("subscription", "referral_discount", "admin_discount", "feedback_discount"):
        assert mode in html
