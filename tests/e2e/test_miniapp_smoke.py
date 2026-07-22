import json
import os
import re
import base64
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


def mock_telegram_ready(page, init_data="query_id=smoke"):
    """Telegram WebApp stub'ni bo'sh bo'lmagan initData bilan qaytaradi, shunda
    Mini App auth-gate ko'rsatmasdan map'ni yuklaydi (static rejim)."""
    page.route(
        "https://telegram.org/js/telegram-web-app.js",
        lambda route: route.fulfill(
            status=200,
            content_type="application/javascript",
            body=(
                "window.Telegram={WebApp:{initData:'" + init_data + "',initDataUnsafe:{},"
                "ready(){},expand(){},close(){},setHeaderColor(){},setBackgroundColor(){},"
                "HapticFeedback:{impactOccurred(){},notificationOccurred(){},selectionChanged(){}},"
                "openTelegramLink(){},openLink(){},showConfirm(){},"
                "BackButton:{show(){},hide(){},onClick(){}}}};"
            ),
        ),
    )


def mock_course_map(page, *, level="hsk1"):
    """Static rejimda ``/api/v3/map`` ni haqiqiy statik map fayli asosida
    (auth qilingan, bepul user) mock qiladi — real backend'siz sahifa render'i
    uchun."""
    data = json.loads((STATIC_ROOT / f"course_v3_data/{level}.json").read_text(encoding="utf-8"))
    data["authenticated"] = True
    data["level"] = level
    progress = data.setdefault("progress", {})
    progress.setdefault("xp", 0)
    progress.setdefault("streak", 0)
    progress["completed"] = 0
    data["user"] = {
        "name": "Smoke Test",
        "avatar": "阿",
        "language": "uz",
        "is_paid": False,
        "referral_code": "",
    }
    data["notify"] = {"enabled": True}
    page.route(re.compile(r".*/api/v3/map(\?.*)?$"), lambda route: json_response(route, data))


def test_course_v3_opens_static_map_and_query_lesson_sheet(page):
    mock_price_preview(page)
    mock_telegram_ready(page)
    mock_course_map(page)
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


def test_course_v3_onboarding_autostart_opens_first_lesson_flow(page):
    mock_price_preview(page)
    mock_telegram_ready(page)
    mock_course_map(page)
    page.add_init_script(
        """
        localStorage.setItem("hsk_v3_onb", "1");
        localStorage.setItem("hsk_v3_level", "hsk1");
        """
    )

    page.goto(
        app_url("/course-v3.html?lang=uz&level=hsk1&lesson=1&autostart=1&onboarded=1"),
        wait_until="networkidle",
    )

    expect(page.locator("#flow")).to_have_class(re.compile(r"\bon\b"))
    expect(page.locator("#flow")).to_contain_text("Yangi so'z")
    expect(page.locator("#flow")).to_contain_text("你")


def test_course_v3_d1_recovery_resumes_saved_lesson_card_once(page):
    runtime_errors = []
    page.on("pageerror", lambda error: runtime_errors.append(str(error)))
    page.on(
        "console",
        lambda message: runtime_errors.append(message.text) if message.type == "error" else None,
    )
    mock_price_preview(page)
    mock_telegram_ready(page)
    mock_course_map(page)
    page.add_init_script(
        """
        localStorage.setItem("hsk_v3_onb", "1");
        localStorage.setItem("hsk_v3_level", "hsk1");
        localStorage.setItem(
          "hsk_v3_lesson_resume:hsk1:1",
          JSON.stringify({i: 3, at: Date.now()})
        );
        """
    )

    page.goto(
        app_url(
            "/course-v3.html?lang=uz&level=hsk1&lesson=1&autostart=1&source=d1_recovery_v1&onboarded=1"
        ),
        wait_until="networkidle",
    )

    expect(page.locator("#flow")).to_have_class(re.compile(r"\bon\b"))
    expect(page.locator("#f-stage")).to_contain_text("4 /")
    assert page.evaluate("Flow.i") == 3
    assert "autostart" not in page.url
    assert runtime_errors == []


def test_course_v3_support_pages_render_real_static_data(page):
    # Yodlash bo'limi usul tanlanmagan bo'lsa avval "Qaysi usul?" so'raydi va
    # o'sha qadamda belgi ko'rinmaydi. Tanlov saqlangan (qaytgan) user'ni taqlid
    # qilib, deck to'g'ridan belgini o'rgatishdan boshlaydi.
    page.add_init_script("localStorage.setItem('hsk_memo_pref', 'radical');")
    pages = [
        (
            "/hsk-lugat.html?lang=uz&char=%E4%BD%A0&theme=light&level=hsk1",
            # Ba'zi sarlavhalar (masalan "Tarkibi") CSS text-transform:uppercase
            # bilan KO'RINISHDA katta harfda, lekin DOM matni asl registrda —
            # shuning uchun harf registriga bog'liq bo'lmagan moslik ishlatamiz.
            ["Tarkibi", "Tez eslab qolish", "你好"],
        ),
        (
            # "1/8" — deck 8 kartadan qurilgani (statik belgi ma'lumoti yuklangani)
            # deterministik isbot. Belgining o'zi (你) birinchi qadamda ko'rinishi
            # buildSteps() tasodifiy tartibiga bog'liq (ba'zan HanziWriter SVG yoki
            # pinyin qadami) — shuning uchun unga tayanmaymiz (flaky bo'lardi).
            "/course_v3_memorize.html?lang=uz&char=%E4%BD%A0&from=lugat&theme=light&level=hsk1",
            ["1/8"],
        ),
        (
            "/course_v3_test.html?lang=uz&level=hsk1&theme=light",
            ["Test markazi", "HSK imtihonlari", "14 savol"],
        ),
    ]

    for path, expected_texts in pages:
        page.goto(app_url(path), wait_until="networkidle")
        for text in expected_texts:
            expect(page.locator("body")).to_contain_text(
                re.compile(re.escape(text), re.IGNORECASE)
            )


def test_hsk_exam_uses_public_questions_and_server_result(page):
    runtime_errors = []
    requests = []
    page.on("pageerror", lambda error: runtime_errors.append(str(error)))
    page.on(
        "console",
        lambda message: runtime_errors.append(message.text) if message.type == "error" else None,
    )
    page.on("request", lambda request: requests.append(request.url))
    mock_telegram_ready(page)
    page.route(
        "**/api/voice-practice/me*",
        lambda route: json_response(route, {"ok": True, "level": "hsk1"}),
    )
    page.route(
        "**/api/v3/practice/daily-gate",
        lambda route: json_response(route, {"ok": True, "allowed": True}),
    )
    page.route(
        "**/api/v3/exams/start",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "session": {
                    "id": "hsk-exam:1:hsk1:v2:smoke",
                    "level": "hsk1",
                    "duration_min": 25,
                    "pass_score": 60,
                    "questions": [
                        {
                            "id": "hsk1:q1",
                            "material_version": 2,
                            "format": "text_choice",
                            "section": "reading",
                            "prompt": "To'g'ri tarjimani tanlang",
                            "sentence": "你好",
                            "options": ["Salom", "Xayr"],
                        },
                        {
                            "id": "hsk1:q2",
                            "material_version": 2,
                            "format": "text_choice",
                            "section": "reading",
                            "prompt": "To'g'ri javobni tanlang",
                            "sentence": "谢谢",
                            "options": ["Rahmat", "Kechirasiz"],
                        },
                    ],
                },
            },
        ),
    )
    page.route(
        "**/api/v3/exams/complete",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "score": 1,
                "total": 2,
                "percent": 50,
                "passed": False,
                "pass_score": 60,
                "section_scores": {"reading": {"score": 1, "total": 2, "percent": 50}},
                "wrong_items": [{"question": "谢谢", "correct_answer": "Rahmat"}],
                "reward": {"awarded_xp": 10},
            },
        ),
    )

    page.goto(app_url("/course_v3_test.html?lang=uz&level=hsk1"), wait_until="networkidle")
    page.get_by_text("HSK 1", exact=True).click()
    expect(page.locator("#exam .opt")).to_have_count(2)
    page.locator("#exam .opt").nth(0).click()
    expect(page.locator("#exam")).to_contain_text("谢谢")
    expect(page.locator("#exam .opt")).to_have_count(2)
    page.locator("#exam .opt").nth(1).click()

    expect(page.locator("#exam")).to_contain_text("50%")
    expect(page.locator("#exam")).to_contain_text("Rahmat")
    assert not any("/course_v3_data/exams/" in url for url in requests)
    assert runtime_errors == []


def test_mistake_filters_show_real_category_material(page):
    runtime_errors = []
    page.on("pageerror", lambda error: runtime_errors.append(str(error)))
    page.on(
        "console",
        lambda message: runtime_errors.append(message.text) if message.type == "error" else None,
    )
    mock_telegram_ready(page)
    page.route(
        "**/api/miniapp/mistakes*",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "summary": {"total": 3, "categories": {"word": 2, "grammar": 1}},
                "items": [
                    {
                        "id": 1,
                        "category": "word",
                        "source": "test",
                        "question": "你好 nimani anglatadi?",
                        "user_answer": "Xayr",
                        "correct_answer": "Salom",
                        "count": 2,
                    },
                    {
                        "id": 2,
                        "category": "word",
                        "source": "challenge",
                        "question": "谢谢 nimani anglatadi?",
                        "user_answer": "Salom",
                        "correct_answer": "Rahmat",
                        "count": 1,
                    },
                    {
                        "id": 3,
                        "category": "grammar",
                        "source": "lesson",
                        "lesson": 4,
                        "question": "Gapni to'g'ri tartiblang",
                        "user_answer": "我去昨天",
                        "correct_answer": "我昨天去",
                        "count": 1,
                    },
                ],
            },
        ),
    )

    page.goto(app_url("/course_v3_mistakes.html?lang=uz&level=hsk1"), wait_until="networkidle")
    expect(page.locator("#content")).to_contain_text("HSK test")
    page.get_by_role("button", name="Grammatika · 1").click()
    expect(page.locator("#content")).to_contain_text("Gapni to'g'ri tartiblang")
    expect(page.locator("#content")).not_to_contain_text("你好 nimani anglatadi?")
    assert runtime_errors == []


def test_challenge_question_is_blind_until_server_submit(page):
    runtime_errors = []
    page.on("pageerror", lambda error: runtime_errors.append(str(error)))
    page.on(
        "console",
        lambda message: runtime_errors.append(message.text) if message.type == "error" else None,
    )
    mock_price_preview(page)
    mock_telegram_ready(page)
    mock_course_map(page)
    challenge = {
        "id": 7,
        "status": "accepted",
        "viewer_role": "challenger",
        "challenger": {"id": 1, "name": "Smoke Test"},
        "opponent": {"id": 2, "name": "Raqib"},
        "other_user": {"id": 2, "name": "Raqib"},
        "viewer_level": "hsk1",
        "other_level": "hsk2",
        "viewer_done": False,
        "opponent_done": False,
        "challenger_score": None,
        "challenger_total": None,
        "opponent_score": None,
        "opponent_total": None,
        "winner_user_id": None,
    }
    page.route(
        "**/api/miniapp/challenges",
        lambda route: json_response(route, {"ok": True, "items": [challenge]}),
    )
    page.route(
        "**/api/miniapp/challenges/7/start",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "session": {
                    "id": "challenge:7:1",
                    "questions": [
                        {
                            "id": "challenge:q1",
                            "type": "meaning_to_hanzi",
                            "prompt": "Salom so'zini tanlang",
                            "options": ["你好", "谢谢"],
                        }
                    ],
                },
            },
        ),
    )
    page.add_init_script(
        "localStorage.setItem('hsk_v3_onb','1'); localStorage.setItem('hsk_v3_level','hsk1');"
    )

    page.goto(
        app_url("/course-v3.html?lang=uz&level=hsk1&challenge_id=7&onboarded=1"),
        wait_until="networkidle",
    )
    page.get_by_role("button", name="Raundni boshlash").click()
    expect(page.locator("#flow")).to_have_class(re.compile(r"\bon\b"))
    page.locator("#f-body .opt").nth(0).click()

    expect(page.locator("#f-msg")).to_contain_text("Javob qabul qilindi")
    assert page.locator("#f-hp").inner_text() == "5"
    assert page.evaluate("Flow.challenge.answers") == [
        {"question_id": "challenge:q1", "selected_index": 0}
    ]
    assert runtime_errors == []


def admin_payload():
    advanced = {
        "explain": "Product health metrikalari tanlangan davr bo'yicha.",
        "cards": [
            {"label": "D1 retention", "value": "50%", "note": "5/10 user", "tone": "good"},
            {"label": "D7 retention", "value": "30%", "note": "3/10 user", "tone": "good"},
            {"label": "Avg session", "value": "12 min", "note": "8 Mini App session", "tone": "info"},
        ],
        "payment": {
            "funnel": {
                "steps": [
                    {"key": "paywall_seen", "label": "To'lov oynasi", "users": 10},
                    {"key": "checkout_opened", "label": "Checkout ochdi", "users": 6},
                    {"key": "payment_screenshot_submitted", "label": "Skrinshot yubordi", "users": 3},
                    {"key": "payment_approved", "label": "Tasdiqlandi", "users": 2},
                ],
                "abandon_step": "To'lov oynasi → Checkout ochdi",
                "abandon_count": 4,
                "abandon_rate": 40.0,
                "explain": "Payment abandon step izohi.",
            }
        },
        "feature_adoption": {
            "paid_denominator": 3,
            "free_denominator": 9,
            "rows": [
                {"label": "Darslar", "paid": 2, "free": 5, "paid_rate": 66.7, "free_rate": 55.6},
                {"label": "AI savol-javob", "paid": 1, "free": 4, "paid_rate": 33.3, "free_rate": 44.4},
            ],
            "explain": "Feature adoption izohi.",
        },
    }
    return {
        "ok": True,
        "generated_at": "28.06.2026 11:30",
        "report_text": "Real hisobot: 12 foydalanuvchi, 3 aktiv obuna.",
        "statistics_reports": [
            {"key": "weekly", "title": "Haftalik", "note": "Oxirgi 7 kun", "cards": [], "course": {}, "metrics": {}, "text": "Weekly hisobot", "advanced": advanced},
            {"key": "monthly", "title": "Oylik", "note": "Oxirgi 30 kun", "cards": [], "course": {}, "metrics": {}, "text": "Monthly hisobot", "advanced": advanced},
            {"key": "all_time", "title": "To'liq", "note": "Butun davr", "cards": [], "course": {}, "metrics": {}, "text": "Real hisobot: 12 foydalanuvchi, 3 aktiv obuna.", "advanced": advanced},
        ],
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
            "active_today": 5,
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
                "active_today": True,
                "hot_lead": False,
                "questions": "2/5",
                "bonus_left": 0,
                "streak": 4,
            }
        ],
        "queue": [
            {"title": "To'lov tekshiruvi", "note": "2 ta to'lov admin tasdig'ini kutyapti", "priority": "hozir", "section": "payments"}
        ],
        "modules": [
            {"key": "stats", "icon": "📊", "title": "Statistika", "note": "Umumiy hisobot", "section": "statistics", "callback": "adm:stats"},
            {"key": "give_access", "icon": "✅", "title": "Obuna berish", "note": "Istalgan muddatga paid active", "section": "settings", "callback": "adm:giveaccess_info"},
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


def admin_finance_payload():
    def period(key, title, note):
        return {
            "key": key, "title": title, "note": note, "range_label": "01.01.2026 — 28.06.2026",
            "finance": {
                "revenue_text": "$120.00", "ai_cost_text": "$10.00", "expense_text": "$5.00",
                "net_text": "$105.00", "net_positive": True, "ai_share_pct": 8.3, "margin_pct": 87.5,
                "explain": "Sof foyda = daromad - AI xarajat - portfel rasxod.",
            },
            "unit": {
                "arpu_text": "$1.00", "arppu_text": "$12.00", "avg_check_text": "$12.00",
                "paying_users": 10, "total_users": 12, "approved_count": 10,
                "explain": "ARPU va ARPPU izohi.",
            },
            "retention": {
                "new_paying": 8, "renewals": 2, "renewal_share_pct": 20.0, "renewal_rate_pct": 20.0,
                "churn_rate_pct": (15.0 if key == "all_time" else None),
                "active_paid_now": 9, "paid_ever": 12, "renewed_ever": 2,
                "explain": "Yangilash va churn izohi.",
            },
            "sources_paid": [
                {"source": "v3_paywall", "label": "Course v3 - Paywall", "paying_users": 6, "payments": 7, "revenue_text": "$80.00"}
            ],
            "cards": [
                {"label": "Daromad", "value": "$120.00", "note": "10 ta to'lov", "tone": "info"},
                {"label": "AI xarajat", "value": "$10.00", "note": "daromadning 8.3%", "tone": "warn"},
                {"label": "Portfel rasxod", "value": "$5.00", "note": "qo'lda", "tone": "warn"},
                {"label": "Sof foyda", "value": "$105.00", "note": "marja 87.5%", "tone": "good"},
                {"label": "ARPU", "value": "$1.00", "note": "har foydalanuvchi", "tone": "info"},
                {"label": "ARPPU", "value": "$12.00", "note": "har pullik", "tone": "good"},
                {"label": "Pullik foydalanuvchi", "value": 10, "note": "yangi 8 · yangilash 2", "tone": "good"},
                {"label": "Yangilash", "value": "20.0%", "note": "qayta to'lov ulushi", "tone": "good"},
            ],
        }
    return {
        "ok": True, "generated_at": "28.06.2026 11:30", "tz": "Asia/Shanghai",
        "periods": [
            period("weekly", "Haftalik", "Oxirgi 7 kun"),
            period("monthly", "Oylik", "Oxirgi 30 kun"),
            period("all_time", "To'liq", "Butun davr"),
        ],
    }


def test_admin_control_renders_real_api_payload_without_demo_data(page):
    grant_requests = []

    def grant_access(route):
        grant_requests.append(json.loads(route.request.post_data or "{}"))
        json_response(
            route,
            {
                "ok": True,
                "duration_days": 45,
                "extended": False,
                "status": "active",
                "payment_status": "approved",
                "start_date": "11.07.2026 12:00",
                "end_date": "25.08.2026 12:00",
            },
        )

    page.add_init_script(
        """
        window.Telegram={WebApp:{initData:"admin-e2e",ready(){},expand(){},close(){},
        setHeaderColor(){},setBackgroundColor(){}}};
        """
    )
    page.route("**/api/admin-miniapp/overview", lambda route: json_response(route, admin_payload()))
    page.route("**/api/admin-miniapp/finance-stats", lambda route: json_response(route, admin_finance_payload()))
    page.route("**/api/admin-miniapp/sub-entry-stats", lambda route: json_response(route, {"ok": True, "rows": []}))
    page.route("**/api/admin-miniapp/management", lambda route: json_response(route, {"ok": True}))
    page.route(
        "**/api/admin-miniapp/notifications",
        lambda route: json_response(route, {"ok": True, "items": []}),
    )
    page.route("**/api/admin-miniapp/course-ads", lambda route: json_response(route, {"ok": True, "items": []}))
    page.route("**/api/admin-miniapp/users/give-access", grant_access)

    page.goto(app_url("/admin.html"), wait_until="networkidle")

    expect(page.locator("#app")).to_be_visible()
    expect(page.locator("#summaryGrid")).to_contain_text("Foydalanuvchilar")
    expect(page.locator("#summaryGrid")).to_contain_text("12")
    expect(page.locator("#reportText")).to_contain_text("Real hisobot")
    expect(page.locator("#userList")).to_contain_text("Ali")
    expect(page.locator("#paymentBoard")).to_contain_text("99 TJS")
    expect(page.locator("#financeCards")).to_contain_text("Sof foyda")
    expect(page.locator("#advancedCards")).to_contain_text("D1 retention")
    expect(page.locator("#featureAdoption")).to_contain_text("Darslar")

    page.locator('[data-tab="settings"]').click()
    page.locator('[data-module="give_access"]').click()
    expect(page.locator("#gaDays")).to_be_visible()
    page.locator('[data-duration-target="gaDays"][data-duration-days="90"]').click()
    expect(page.locator("#gaDays")).to_have_value("90")

    page.locator("#gaId").fill("111")
    page.locator("#gaDays").fill("0")
    page.locator("[data-gasave]").click()
    expect(page.locator("#toast")).to_contain_text("1–36500")
    assert grant_requests == []

    page.locator("#gaDays").fill("45")
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator("[data-gasave]").click()
    expect(page.locator("#toast")).to_contain_text("25.08.2026 12:00")
    assert grant_requests == [{"telegram_id": 111, "duration_days": 45}]
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_subscription_page_smoke(page):
    page.route("**/api/subscription-miniapp/**", lambda route: route.abort())

    page.goto(app_url("/subscription.html?lang=uz&mode=subscription"), wait_until="networkidle")

    expect(page.locator("#plans .plan").first).to_be_visible()
    expect(page.locator("#plans .plan").first).to_contain_text("1 oy")
    expect(page.locator("#methods .choice").first).to_be_visible()
    expect(page.locator("#methods .choice").first).to_contain_text("🇹🇯")
    expect(page.locator("#methods .choice").first).to_contain_text("Tojikiston kartasi")
    expect(page.locator("[data-card-method=foreign]")).to_contain_text("💳")
    expect(page.locator("[data-china-group]")).to_contain_text("🇨🇳")
    expect(page.locator("#nextBtn")).to_contain_text("Tojikiston kartasi")
    page.locator("[data-card-method=foreign]").click()
    page.locator("#nextBtn").click()
    expect(page.locator("#countries")).not_to_contain_text("Tojikiston kartasi")
    expect(page.locator("#countries")).to_contain_text("🇺🇿")
    expect(page.locator("#countries")).to_contain_text("🇷🇺")
    expect(page.locator("#paymentBox")).to_have_count(1)


def test_subscription_checkout_tracks_one_attempt_through_real_stages(page):
    mock_telegram_ready(page)
    requests = []
    overview = {
        "ok": True,
        "language": "uz",
        "mode": "subscription",
        "pending_payment": None,
        "offer": None,
        "discount": None,
        "payment_details": "CARD: 0000 0000 0000 0000",
        "prices": {
            "visa": {
                "1_month": {
                    "base_amount": 89,
                    "final_amount": 89,
                    "currency": "TJS",
                    "discount_applied": False,
                    "discount_percent": 0,
                }
            }
        },
    }

    def capture_overview(route):
        requests.append(("overview", route.request.post_data_json))
        json_response(route, overview)

    def capture_quote(route):
        requests.append(("quote", route.request.post_data_json))
        json_response(
            route,
            {
                "ok": True,
                "quote": {
                    "plan_type": "1_month",
                    "payment_method": "visa",
                    "pay_amount": 89,
                    "pay_currency": "TJS",
                    "base_amount": 89,
                    "base_currency": "TJS",
                    "discount_applied": False,
                    "payment_details": overview["payment_details"],
                },
            },
        )

    def capture_event(route):
        requests.append(("event", route.request.post_data_json))
        json_response(route, {"ok": True})

    page.route("**/api/subscription-miniapp/overview", capture_overview)
    page.route("**/api/subscription-miniapp/quote", capture_quote)
    page.route("**/api/subscription-miniapp/event", capture_event)
    page.goto(
        app_url("/subscription.html?lang=uz&mode=subscription&source=v3_locked_lesson"),
        wait_until="networkidle",
    )

    expect(page.locator("#valueText")).to_contain_text("Boshlagan darsingizni davom ettiring")
    page.locator("#nextBtn").click()
    expect(page.locator("#paymentBox")).to_contain_text("0000 0000 0000 0000")
    page.locator("#receiptInput").set_input_files(
        {
            "name": "receipt.png",
            "mimeType": "image/png",
            "buffer": base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
        }
    )
    expect(page.locator("#uploadBox")).to_have_class(re.compile(r"\bready\b"))
    page.wait_for_timeout(100)

    attempt_ids = [body.get("attempt_id") for _, body in requests if body.get("attempt_id")]
    event_stages = [body.get("stage") for kind, body in requests if kind == "event"]
    assert attempt_ids and len(set(attempt_ids)) == 1
    assert "payment_instructions_viewed" in event_stages
    assert "payment_receipt_selected" in event_stages
