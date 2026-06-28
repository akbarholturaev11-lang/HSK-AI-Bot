import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")
expect = playwright_api.expect
sync_playwright = playwright_api.sync_playwright


APP_ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = APP_ROOT / "app/static"
STATIC_BASE_URL = "http://hsk-ai.local"
BASE_URL = os.getenv("MINIAPP_E2E_BASE_URL", STATIC_BASE_URL).rstrip("/")


def app_url(path):
    return f"{BASE_URL}/{path.lstrip('/')}"


def json_response(route, payload, *, status=200):
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload),
    )


def route_static_files(page):
    static_root = STATIC_ROOT.resolve()

    def handle_static(route):
        path = urlparse(route.request.url).path.lstrip("/") or "course-v3.html"
        file_path = (STATIC_ROOT / path).resolve()
        if not str(file_path).startswith(str(static_root)) or not file_path.exists():
            route.fulfill(status=404, content_type="text/plain", body="not found")
            return
        content_types = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".html": "text/html",
        }
        route.fulfill(
            status=200,
            content_type=content_types.get(file_path.suffix, "application/octet-stream"),
            body=file_path.read_text(encoding="utf-8"),
        )

    page.route(re.compile(r"^http://hsk-ai\.local/(?!api/).*"), handle_static)
    page.route(
        "https://telegram.org/js/telegram-web-app.js",
        lambda route: route.fulfill(
            status=200,
            content_type="application/javascript",
            body=(
                "window.Telegram=window.Telegram||{WebApp:{initData:'',"
                "ready(){},expand(){},close(){},setHeaderColor(){},setBackgroundColor(){},"
                "BackButton:{show(){},hide(){},onClick(){}}}};"
            ),
        ),
    )
    page.route(
        re.compile(r"^https://cdnjs\.cloudflare\.com/.*"),
        lambda route: route.fulfill(status=200, content_type="text/css", body=""),
    )


@pytest.fixture()
def page():
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")
        context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        page = context.new_page()
        if BASE_URL == STATIC_BASE_URL:
            route_static_files(page)
        yield page
        context.close()
        browser.close()


def mock_price_preview(page):
    page.route(
        "**/api/subscription-miniapp/overview",
        lambda route: json_response(route, {"ok": False, "error": "preview_unavailable"}),
    )


def test_course_v3_opens_static_map_and_query_lesson_sheet(page):
    mock_price_preview(page)
    page.add_init_script(
        """
        localStorage.setItem("hsk_v3_onb", "1");
        localStorage.setItem("hsk_v3_level", "hsk1");
        """
    )

    page.goto(app_url("/course-v3.html?lang=uz&level=hsk1&lesson=1&onboarded=1"), wait_until="networkidle")

    expect(page.locator("#s-course")).to_contain_text("HSK 1")
    expect(page.locator("#s-course")).to_contain_text("你好")
    expect(page.locator("#sheet")).to_have_class(re.compile(r"\bon\b"))
    expect(page.locator("#sheet")).to_contain_text("你好")
    expect(page.locator("#sheet")).to_contain_text("Yangi so'zlar")


def test_course_v3_support_pages_render_real_static_data(page):
    pages = [
        (
            "/hsk-lugat.html?lang=uz&char=%E4%BD%A0&theme=light&level=hsk1",
            ["TARKIBI", "Tez eslab qolish", "你好"],
        ),
        (
            "/course_v3_memorize.html?lang=uz&char=%E4%BD%A0&from=lugat&theme=light&level=hsk1",
            ["1/8", "你"],
        ),
        (
            "/course_v3_test.html?lang=uz&level=hsk1&theme=light",
            ["Test markazi", "HSK imtihonlari", "14 savol"],
        ),
    ]

    for path, expected_texts in pages:
        page.goto(app_url(path), wait_until="networkidle")
        for text in expected_texts:
            expect(page.locator("body")).to_contain_text(text)


def admin_payload():
    return {
        "ok": True,
        "generated_at": "28.06.2026 11:30",
        "report_text": "Real hisobot: 12 foydalanuvchi, 3 aktiv obuna.",
        "summary": [
            {"label": "Foydalanuvchilar", "value": 12, "note": "5 bugun aktiv", "tone": "info"},
            {"label": "Aktiv obuna", "value": 3, "note": "hozir to'lovli", "tone": "good"},
            {"label": "To'lov tekshiruvda", "value": 2, "note": "admin ko'rishi kerak", "tone": "warn"},
            {"label": "Issiq mijozlar", "value": 4, "note": "obunaga yaqin", "tone": "danger"},
        ],
        "counts": {
            "paid_users": 3,
            "pending_payments": 2,
            "active_week": 9,
            "active_24h": 5,
        },
        "segments": {
            "all": 12,
            "paid": 3,
            "pending": 2,
            "wants_pay": 4,
            "trial": 5,
            "expired": 1,
            "blocked": 0,
        },
        "payments": {
            "latest": [
                {
                    "id": 1,
                    "telegram_id": 111,
                    "name": "Ali",
                    "username": "ali",
                    "status": "pending",
                    "status_label": "Tekshiruvda",
                    "plan": "1 oy",
                    "method": "Alipay",
                    "amount": "99 TJS",
                    "submitted_at": "28.06.2026 11:00",
                    "reviewed_at": None,
                    "has_screenshot": True,
                    "comment": None,
                }
            ]
        },
        "course": {
            "opened_users": 10,
            "lesson_users": 7,
            "completed_users": 4,
            "completed_sections": 18,
            "completed_book_lessons": 3,
            "avg_sections": 4.5,
        },
        "channels": {"enabled": True, "active_count": 1, "items": []},
        "ads": {"total": 2, "active": 1, "delivered": 20, "failed": 1, "latest": []},
        "feedback": {"pending": 1, "completed": 6, "values": {}},
        "subscription_sources": [],
        "prices": [{"method": "Alipay", "plan": "1 oy", "amount": "99 TJS"}],
        "users": [
            {
                "id": 111,
                "name": "Ali",
                "username": "ali",
                "language": "O'zbekcha",
                "level": "HSK1",
                "mode": "Kurs",
                "status": "active",
                "status_label": "Faol",
                "payment_status": "approved",
                "payment_label": "Tasdiqlangan",
                "plan": "1 oy",
                "method": "Alipay",
                "end_date": "01.07.2026 12:00",
                "last_active": "hozir",
                "questions": "2/5",
                "bonus_left": 0,
                "streak": 4,
            }
        ],
        "queue": [
            {"title": "To'lov tekshiruvi", "note": "2 ta to'lov admin tasdig'ini kutyapti", "priority": "hozir", "section": "payments"}
        ],
        "modules": [
            {"key": "stats", "icon": "📊", "title": "Statistika", "note": "Umumiy hisobot", "section": "statistics", "callback": "adm:stats"}
        ],
        "monitor": {
            "ticker": [{"label": "24 soat aktiv", "value": 5, "tone": "up"}],
            "heat": [{"label": "dars tugadi", "value": 4, "tone": "hot"}],
            "bars": [
                {"label": "24 soat aktiv", "value": 5, "tone": "hot"},
                {"label": "Tekshiruvdagi to'lov", "value": 2, "tone": "warn"},
            ],
        },
    }


def test_admin_control_renders_real_api_payload_without_demo_data(page):
    page.add_init_script(
        """
        window.Telegram={WebApp:{initData:"admin-e2e",ready(){},expand(){},close(){},
        setHeaderColor(){},setBackgroundColor(){}}};
        """
    )
    page.route("**/api/admin-miniapp/overview", lambda route: json_response(route, admin_payload()))
    page.route("**/api/admin-miniapp/sub-entry-stats", lambda route: json_response(route, {"ok": True, "rows": []}))
    page.route(
        "**/api/admin-miniapp/notifications",
        lambda route: json_response(route, {"ok": True, "items": []}),
    )
    page.route("**/api/admin-miniapp/course-ads", lambda route: json_response(route, {"ok": True, "items": []}))

    page.goto(app_url("/admin-control.html"), wait_until="networkidle")

    expect(page.locator("#app")).to_be_visible()
    expect(page.locator("#statsGrid")).to_contain_text("Foydalanuvchilar")
    expect(page.locator("#statsGrid")).to_contain_text("12")
    expect(page.locator("#reportText")).to_contain_text("Real hisobot")
    expect(page.locator("#userList")).to_contain_text("Ali")
    expect(page.locator("#paymentBoard")).to_contain_text("99 TJS")
    expect(page.locator("#candleChart .candle")).to_have_count(2)


def test_subscription_page_smoke(page):
    page.route("**/api/subscription-miniapp/**", lambda route: route.abort())

    page.goto(app_url("/subscription.html?lang=uz&mode=subscription"), wait_until="networkidle")

    expect(page.locator("#plans .plan").first).to_be_visible()
    expect(page.locator("#methods .choice").first).to_be_visible()
    expect(page.locator("#paymentBox")).to_have_count(1)
