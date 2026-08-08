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
            ".webp": "image/webp",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        is_text = file_path.suffix in {".css", ".js", ".json", ".html"}
        route.fulfill(
            status=200,
            content_type=content_types.get(file_path.suffix, "application/octet-stream"),
            body=(
                file_path.read_text(encoding="utf-8")
                if is_text
                else file_path.read_bytes()
            ),
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
    page.route(
        "**/api/v3/desktop-download/status",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "enabled": False,
                "platforms": {"macos": False, "windows": False},
                "versions": {"macos": None, "windows": None},
                "promo": {"eligible": False, "placements": {}},
            },
        ),
    )
    page.route(
        "**/api/admin-miniapp/desktop-stats",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "period": "all_time",
                "desktop": {
                    "funnel": {},
                    "active": {"dau": 0, "wau": 0, "mau": 0},
                    "platforms": {"active_users_30d": {}},
                    "ai_pack": {},
                    "sync": {},
                    "versions": {},
                    "notes": {},
                },
            },
        ),
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


def mock_telegram_desktop_download(
    page,
    *,
    platform="tdesktop",
    native_download=True,
    native_accept=True,
    confirm=True,
):
    download_method = (
        "downloadFile(params,cb){window.__downloadFileParams=params;cb("
        + ("true" if native_accept else "false")
        + ");},"
        if native_download
        else ""
    )
    confirm_value = "true" if confirm else "false"
    page.route(
        "https://telegram.org/js/telegram-web-app.js",
        lambda route: route.fulfill(
            status=200,
            content_type="application/javascript",
            body=(
                "window.Telegram={WebApp:{initData:'query_id=desktop-smoke',"
                "initDataUnsafe:{user:{id:42}},platform:'"
                + platform
                + "',ready(){},expand(){},close(){window.__closed=true;},"
                "setHeaderColor(){},setBackgroundColor(){},"
                "HapticFeedback:{impactOccurred(){},notificationOccurred(){},selectionChanged(){}},"
                + download_method
                + "openLink(url){window.__openedLink=url;},"
                "showConfirm(message,cb){window.__confirmMessage=message;cb("
                + confirm_value
                + ");},BackButton:{show(){},hide(){},onClick(){}}}};"
            ),
        ),
    )


def mock_desktop_release_status(page, payload=None):
    if payload is None:
        payload = {
            "ok": True,
            "enabled": True,
            "platforms": {"macos": True, "windows": True},
            "versions": {"macos": "1.0.0", "windows": "1.0.0"},
            "downloads": {
                "macos": "https://downloads.example/downloads/macos",
                "windows": "https://downloads.example/downloads/windows",
            },
            "promo": {
                "eligible": True,
                "cooldown_days": 14,
                "placements": {
                    "profile": True,
                    "home_prompt": True,
                    "lesson_end_promo": True,
                    "ad_promo": True,
                },
            },
        }
    page.route(
        "**/api/v3/desktop-download/status",
        lambda route: json_response(route, payload),
    )


def mock_course_map(page, *, level="hsk1", language="uz"):
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
        "language": language,
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


def _open_course_profile_with_desktop_release(
    page,
    *,
    status_payload=None,
    status_handler=None,
    language="uz",
    path="/course-v3.html?lang=uz&level=hsk1&onboarded=1",
    select_profile=True,
):
    mock_price_preview(page)
    mock_course_map(page, language=language)
    if status_handler is None:
        mock_desktop_release_status(page, status_payload)
    else:
        page.route("**/api/v3/desktop-download/status", status_handler)
    page.route(
        "**/api/miniapp/event",
        lambda route: json_response(route, {"ok": True}),
    )
    page.add_init_script(
        """
        localStorage.setItem("hsk_v3_onb", "1");
        localStorage.setItem("hsk_v3_level", "hsk1");
        """
    )
    page.goto(app_url(path), wait_until="networkidle")
    if select_profile:
        page.locator('#nav button[data-s="profile"]').click()
    expect(page.locator("#pomp-desktop-profile-root .pdd-card")).to_be_visible()


def test_desktop_profile_card_is_discoverable_and_explains_transfer(page):
    mock_telegram_desktop_download(page, platform="android")
    _open_course_profile_with_desktop_release(page)

    card = page.locator("#pomp-desktop-profile-root .pdd-card")
    goal = page.locator("#s-profile .pgoal")
    calendar = page.locator("#pomp-desktop-profile-root + .sech")
    nav = page.locator("#nav")
    mac = card.locator('[data-pdd-platform="macos"]')
    windows = card.locator('[data-pdd-platform="windows"]')

    expect(card).to_be_visible()
    expect(mac).to_be_visible()
    expect(windows).to_be_visible()
    expect(card.locator(".pdd-product-preview")).to_be_visible()
    expect(card.locator(".pdd-preview-word")).to_contain_text("学习")
    expect(card.locator(".pdd-preview-word")).to_contain_text("xuéxí · o‘rganmoq")
    expect(card.locator(".pdd-benefit")).to_have_count(3)
    expect(card.locator(".pdd-mobile-hint")).to_contain_text(
        "AirDrop/ulashish"
    )

    goal_box = goal.bounding_box()
    card_box = card.bounding_box()
    calendar_box = calendar.bounding_box()
    nav_box = nav.bounding_box()
    mac_box = mac.bounding_box()
    windows_box = windows.bounding_box()

    assert all(
        box is not None
        for box in (goal_box, card_box, calendar_box, nav_box, mac_box, windows_box)
    )
    assert goal_box["y"] + goal_box["height"] <= card_box["y"] + 1
    assert card_box["y"] + card_box["height"] <= calendar_box["y"] + 1
    assert card_box["y"] < 844 * 0.5
    assert mac_box["y"] + mac_box["height"] <= nav_box["y"] + 1
    assert windows_box["y"] + windows_box["height"] <= nav_box["y"] + 1


def test_desktop_profile_unavailable_state_is_honest_and_sends_no_request(page):
    mock_telegram_desktop_download(page, platform="android")
    requests = []
    page.route(
        "**/api/v3/desktop-download/request",
        lambda route: (
            requests.append(route.request.post_data_json),
            json_response(route, {"ok": False}, status=500),
        )[-1],
    )
    unavailable = {
        "ok": True,
        "enabled": False,
        "platforms": {"macos": False, "windows": False},
        "versions": {"macos": None, "windows": None},
        "promo": {"eligible": False, "placements": {}},
    }
    _open_course_profile_with_desktop_release(page, status_payload=unavailable)

    card = page.locator("#pomp-desktop-profile-root .pdd-card")
    mac = card.locator('[data-pdd-platform="macos"]')
    windows = card.locator('[data-pdd-platform="windows"]')
    expect(card).to_be_visible()
    expect(mac).to_be_disabled()
    expect(windows).to_be_disabled()
    expect(mac).to_contain_text("Mac — tez orada")
    expect(windows).to_contain_text("Windows — tez orada")
    expect(card.locator(".pdd-availability-note")).to_contain_text(
        "Yuklash fayllari tayyorlanmoqda"
    )

    page.evaluate(
        """
        document.querySelector('[data-pdd-platform="macos"][data-pdd-source="profile"]').click();
        document.querySelector('[data-pdd-platform="windows"][data-pdd-source="profile"]').click();
        """
    )
    page.wait_for_timeout(100)
    assert requests == []
    assert page.locator("#pomp-desktop-destination-root").is_hidden()


def test_desktop_profile_status_error_can_be_retried(page):
    mock_telegram_desktop_download(page, platform="android")
    attempts = []

    def status_handler(route):
        attempts.append(route.request.url)
        if len(attempts) == 1:
            json_response(route, {"ok": False, "error": "temporary"}, status=503)
            return
        json_response(
            route,
            {
                "ok": True,
                "enabled": True,
                "platforms": {"macos": True, "windows": True},
                "versions": {"macos": "1.1.0", "windows": "1.1.0"},
                "downloads": {
                    "macos": "https://downloads.example/downloads/macos",
                    "windows": "https://downloads.example/downloads/windows",
                },
                "promo": {"eligible": False, "placements": {}},
            },
        )

    _open_course_profile_with_desktop_release(
        page,
        status_handler=status_handler,
    )

    card = page.locator("#pomp-desktop-profile-root .pdd-card")
    note = card.locator(".pdd-availability-note")
    retry = card.locator(".pdd-availability-retry")
    mac = card.locator('[data-pdd-platform="macos"]')
    windows = card.locator('[data-pdd-platform="windows"]')

    expect(note).to_have_class(re.compile(r"\bis-error\b"))
    expect(note).to_contain_text("Yuklash holatini tekshirib bo‘lmadi")
    expect(note).not_to_contain_text("Yuklash fayllari tayyorlanmoqda")
    expect(retry).to_have_text("Qayta tekshirish")
    expect(mac).to_be_disabled()
    expect(windows).to_be_disabled()

    retry.click()
    expect(mac).to_be_enabled()
    expect(windows).to_be_enabled()
    expect(card.locator(".pdd-availability-note")).to_have_count(0)
    assert len(attempts) == 2


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("ru", "xuéxí · учиться"),
        ("tj", "xuéxí · омӯхтан"),
    ],
)
def test_desktop_profile_preview_is_localized_and_fits(page, lang, expected):
    mock_telegram_desktop_download(page, platform="android")
    _open_course_profile_with_desktop_release(
        page,
        language=lang,
        path=f"/course-v3.html?lang={lang}&level=hsk1&onboarded=1",
    )

    card = page.locator("#pomp-desktop-profile-root .pdd-card")
    expect(card.locator(".pdd-product-preview")).to_contain_text(expected)
    expect(card.locator(".pdd-mobile-hint")).to_be_visible()
    assert card.evaluate("node => node.scrollWidth <= node.clientWidth + 1")


def test_desktop_download_deep_link_opens_profile_and_focuses_card(page):
    mock_telegram_desktop_download(page, platform="android")
    page.add_init_script(
        """
        (() => {
          const original = Element.prototype.scrollIntoView;
          Element.prototype.scrollIntoView = function(options) {
            if (this.matches && this.matches('.pdd-card')) {
              window.__pddFocusScroll = options || true;
            }
            return original.apply(this, arguments);
          };
        })();
        """
    )
    _open_course_profile_with_desktop_release(
        page,
        path=(
            "/course-v3.html?lang=uz&level=hsk1&onboarded=1"
            "&tab=profile&desktop_download=1"
        ),
        select_profile=False,
    )

    expect(page.locator("#s-profile")).to_have_class(re.compile(r"\bon\b"))
    expect(page.locator('#nav button[data-s="profile"]')).to_have_class(
        re.compile(r"\bon\b")
    )
    page.wait_for_function("Boolean(window.__pddFocusScroll)")
    assert page.evaluate("window.__pddFocusScroll.block") == "center"
    card = page.locator("#pomp-desktop-profile-root .pdd-card")
    expect(card).to_be_visible()
    expect(card).to_be_focused()


def test_desktop_download_opens_branded_site_without_closing_miniapp(page):
    mock_telegram_desktop_download(page, platform="tdesktop", native_download=True)
    requested = []
    started = []

    def request_download(route):
        requested.append(route.request.post_data_json)
        json_response(
            route,
            {
                "ok": True,
                "platform": "macos",
                "download_url": "https://downloads.example/desktop-download?platform=macos&request=abc123",
                "download_page_url": "https://downloads.example/desktop-download?platform=macos&request=abc123",
                "transfer_url": "https://downloads.example/downloads/macos",
                "file_name": "Pomp-HSK-AI-1.0.0.dmg",
                "duplicate": False,
            },
        )

    page.route("**/api/v3/desktop-download/request", request_download)
    page.route(
        "**/api/v3/desktop-download/started",
        lambda route: (
            started.append(route.request.post_data_json),
            json_response(route, {"ok": True, "recorded": True, "duplicate": False}),
        )[-1],
    )
    _open_course_profile_with_desktop_release(page)

    page.locator('[data-pdd-platform="macos"][data-pdd-source="profile"]').click()
    expect(page.locator("#pomp-desktop-destination-root")).to_be_visible()
    page.locator('[data-pdd-destination-action="direct"]').click()
    page.wait_for_function("Boolean(window.__openedLink)")
    page.wait_for_function("document.querySelector('.pdd-promo-shell[data-mode=\"success\"]')")
    page.wait_for_timeout(100)

    assert page.evaluate("window.__downloadFileParams") is None
    assert (
        page.evaluate("window.__openedLink")
        == "https://downloads.example/desktop-download?platform=macos&request=abc123"
    )
    assert requested and started
    assert started[0]["event_id"] == requested[0]["event_id"]
    assert started[0]["transport"] == "open_link"
    assert not page.evaluate("Boolean(window.__closed)")
    expect(page.locator(".pdd-promo-shell")).to_contain_text("Yuklash sayti ochildi")


def test_desktop_download_falls_back_to_open_link(page):
    mock_telegram_desktop_download(page, platform="tdesktop", native_download=False)
    started = []
    page.route(
        "**/api/v3/desktop-download/request",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "platform": "windows",
                "download_url": "https://downloads.example/desktop-download?platform=windows&request=def456",
                "download_page_url": "https://downloads.example/desktop-download?platform=windows&request=def456",
                "transfer_url": "https://downloads.example/downloads/windows",
                "file_name": "Pomp-HSK-AI-1.0.0-setup.exe",
                "duplicate": False,
            },
        ),
    )
    page.route(
        "**/api/v3/desktop-download/started",
        lambda route: (
            started.append(route.request.post_data_json),
            json_response(route, {"ok": True, "recorded": True, "duplicate": False}),
        )[-1],
    )
    _open_course_profile_with_desktop_release(page)

    page.locator('[data-pdd-platform="windows"][data-pdd-source="profile"]').click()
    page.locator('[data-pdd-destination-action="direct"]').click()
    page.wait_for_function("Boolean(window.__openedLink)")
    page.wait_for_timeout(100)

    assert (
        page.evaluate("window.__openedLink")
        == "https://downloads.example/desktop-download?platform=windows&request=def456"
    )
    assert started and started[0]["transport"] == "open_link"
    assert not page.evaluate("Boolean(window.__closed)")


def test_download_site_does_not_use_native_download_dialog(page):
    mock_telegram_desktop_download(
        page,
        platform="tdesktop",
        native_download=True,
        native_accept=False,
    )
    started = []
    page.route(
        "**/api/v3/desktop-download/request",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "platform": "macos",
                "download_url": "https://downloads.example/desktop-download?platform=macos&request=cancel123",
                "download_page_url": "https://downloads.example/desktop-download?platform=macos&request=cancel123",
                "transfer_url": "https://downloads.example/downloads/macos",
                "file_name": "Pomp-HSK-AI-1.0.0.dmg",
                "duplicate": False,
            },
        ),
    )
    page.route(
        "**/api/v3/desktop-download/started",
        lambda route: (
            started.append(route.request.post_data_json),
            json_response(route, {"ok": True, "recorded": True, "duplicate": False}),
        )[-1],
    )
    _open_course_profile_with_desktop_release(page)

    page.locator('[data-pdd-platform="macos"][data-pdd-source="profile"]').click()
    page.locator('[data-pdd-destination-action="direct"]').click()
    page.wait_for_function("Boolean(window.__openedLink)")
    page.wait_for_timeout(200)

    assert page.evaluate("window.__downloadFileParams") is None
    assert started and started[0]["transport"] == "open_link"
    assert page.locator(".pdd-promo-shell[data-mode='success']").count() == 1
    assert not page.evaluate("Boolean(window.__closed)")


def test_branded_download_page_exposes_direct_tracked_installers(page):
    request_token = "a" * 32
    page.set_viewport_size({"width": 1280, "height": 900})
    page.route(
        "**/api/v3/desktop-download/public-status",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "enabled": True,
                "platforms": {"macos": True, "windows": True},
                "versions": {"macos": "1.0.0", "windows": "1.0.0"},
                "downloads": {
                    "macos": "/downloads/macos",
                    "windows": "/downloads/windows",
                },
                "files": {
                    "macos": "Pomp-HSK-AI_1.0.0_universal.dmg",
                    "windows": "Pomp-HSK-AI_1.0.0_x64-setup.exe",
                },
            },
        ),
    )

    page.goto(
        app_url(
            f"/desktop-download.html?platform=macos&lang=uz&request={request_token}"
        ),
        wait_until="networkidle",
    )

    expect(page.locator("#page-title")).to_contain_text(
        "Xitoy tilini katta ekranda"
    )
    expect(page.locator(".brand-seal")).to_have_attribute(
        "src",
        "/assets/hsk-ai-avatar.webp",
    )
    expect(page.locator(".mini-seal")).to_have_attribute(
        "src",
        "/assets/hsk-ai-avatar.webp",
    )
    expect(page.locator("[data-download-button]")).to_have_attribute(
        "href",
        f"http://hsk-ai.local/downloads/macos?request={request_token}",
    )
    expect(page.locator("[data-transfer-link]")).to_have_value(
        "http://hsk-ai.local/downloads/macos"
    )
    expect(page.locator("[data-version]")).to_have_text("Versiya 1.0.0")
    expect(page.locator("[data-installer-stage]")).to_have_attribute(
        "data-installer-stage",
        "macos",
    )

    page.locator('[data-platform="windows"]').click()
    expect(page.locator("[data-download-button]")).to_have_attribute(
        "href",
        f"http://hsk-ai.local/downloads/windows?request={request_token}",
    )
    expect(page.locator("[data-transfer-link]")).to_have_value(
        "http://hsk-ai.local/downloads/windows"
    )
    expect(page.locator("[data-installer-stage]")).to_have_attribute(
        "data-installer-stage",
        "windows",
    )
    expect(page.locator("[data-security-copy]")).to_contain_text("SmartScreen")

    page.locator('[data-language="ru"]').click()
    expect(page.locator("#page-title")).to_contain_text(
        "Продолжайте китайский"
    )


def test_branded_download_page_manual_copy_fallback_keeps_url_token_free(page):
    request_token = "b" * 32
    page.add_init_script(
        """
        Object.defineProperty(Navigator.prototype, "userAgent", {
          configurable: true,
          get: function() { return "Mozilla/5.0 Android"; }
        });
        Object.defineProperty(Navigator.prototype, "clipboard", {
          configurable: true,
          get: function() { return undefined; }
        });
        Document.prototype.execCommand = function() { return false; };
        """
    )
    page.route(
        "**/api/v3/desktop-download/public-status",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "enabled": True,
                "platforms": {"macos": True, "windows": True},
                "versions": {"macos": "1.0.0", "windows": "1.0.0"},
                "downloads": {
                    "macos": "/downloads/macos",
                    "windows": "/downloads/windows",
                },
                "files": {
                    "macos": "Pomp-HSK-AI_1.0.0_universal.dmg",
                    "windows": "Pomp-HSK-AI_1.0.0_x64-setup.exe",
                },
            },
        ),
    )
    page.goto(
        app_url(
            f"/desktop-download.html?platform=macos&lang=uz&request={request_token}"
        ),
        wait_until="networkidle",
    )

    expect(page.locator("[data-mobile-transfer]")).to_be_visible()
    page.locator("[data-copy-link]").click()
    expect(page.locator("[data-transfer-manual]")).to_be_visible()
    expect(page.locator("[data-transfer-link]")).to_have_value(
        "http://hsk-ai.local/downloads/macos"
    )
    expect(page.locator("[data-transfer-status]")).to_contain_text(
        "Avtomatik nusxalanmadi"
    )
    assert request_token not in page.locator("[data-transfer-link]").input_value()


def test_branded_download_page_unknown_mobile_requires_platform_choice(page):
    page.add_init_script(
        """
        Object.defineProperty(Navigator.prototype, "userAgent", {
          configurable: true,
          get: function() { return "Mozilla/5.0 Android"; }
        });
        """
    )
    page.route(
        "**/api/v3/desktop-download/public-status",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "enabled": True,
                "platforms": {"macos": True, "windows": True},
                "versions": {"macos": "1.0.0", "windows": "1.0.0"},
                "downloads": {
                    "macos": "/downloads/macos",
                    "windows": "/downloads/windows",
                },
            },
        ),
    )
    page.goto(
        app_url("/desktop-download.html?lang=uz"),
        wait_until="networkidle",
    )

    expect(page.locator('[data-platform="macos"]')).to_have_attribute(
        "aria-pressed", "false"
    )
    expect(page.locator('[data-platform="windows"]')).to_have_attribute(
        "aria-pressed", "false"
    )
    expect(page.locator("[data-platform-prompt]")).to_be_visible()
    expect(page.locator("[data-download-title]")).to_have_text(
        "Mac yoki Windowsni tanlang"
    )
    expect(page.locator("[data-download-button]")).to_have_attribute(
        "aria-disabled", "true"
    )
    expect(page.locator("[data-mobile-transfer]")).to_contain_text(
        "Downloads yoki Fayllarga tushadi"
    )

    page.locator('[data-platform="windows"]').click()
    expect(page.locator("[data-platform-prompt]")).to_be_hidden()
    expect(page.locator("[data-download-button]")).to_have_attribute(
        "href", "http://hsk-ai.local/downloads/windows"
    )
    expect(page.locator("[data-platform-guide]")).to_be_visible()


def test_desktop_download_destination_can_cancel_before_request(page):
    mock_telegram_desktop_download(
        page,
        platform="android",
        native_download=True,
        confirm=False,
    )
    request_count = []
    page.route(
        "**/api/v3/desktop-download/request",
        lambda route: (
            request_count.append(1),
            json_response(route, {"ok": False}, status=500),
        )[-1],
    )
    _open_course_profile_with_desktop_release(page)

    page.locator('[data-pdd-platform="macos"][data-pdd-source="profile"]').click()
    expect(page.locator("#pomp-desktop-destination-root")).to_be_visible()
    page.locator(".pdd-destination-cancel").click()
    page.wait_for_timeout(100)

    assert request_count == []
    assert page.locator("#pomp-desktop-destination-root").is_hidden()
    assert page.evaluate("window.__downloadFileParams") is None
    assert page.evaluate("window.__openedLink") is None


def test_desktop_download_share_uses_clean_public_url_and_tracks_transport(page):
    page.add_init_script(
        """
        Object.defineProperty(Navigator.prototype, "share", {
          configurable: true,
          value: async function(payload) { window.__sharedTransfer = payload; }
        });
        Object.defineProperty(Navigator.prototype, "canShare", {
          configurable: true,
          value: function() { return true; }
        });
        """
    )
    mock_telegram_desktop_download(page, platform="android")
    requested = []
    started = []

    def request_download(route):
        requested.append(route.request.post_data_json)
        json_response(
            route,
            {
                "ok": True,
                "platform": "macos",
                "download_url": "https://downloads.example/desktop-download?platform=macos&request=tracked-secret",
                "download_page_url": "https://downloads.example/desktop-download?platform=macos&request=tracked-secret",
                "transfer_url": "https://downloads.example/downloads/macos",
                "file_name": "Pomp-HSK-AI-1.0.0.dmg",
                "duplicate": False,
            },
        )

    page.route("**/api/v3/desktop-download/request", request_download)
    page.route(
        "**/api/v3/desktop-download/started",
        lambda route: (
            started.append(route.request.post_data_json),
            json_response(route, {"ok": True, "recorded": True, "duplicate": False}),
        )[-1],
    )
    _open_course_profile_with_desktop_release(page)

    page.locator('[data-pdd-platform="macos"][data-pdd-source="profile"]').click()
    page.locator('[data-pdd-destination-action="share"]').click()
    page.wait_for_function("Boolean(window.__sharedTransfer)")
    page.wait_for_function("document.querySelector('.pdd-promo-shell[data-mode=\"success\"]')")
    page.wait_for_timeout(100)

    shared_url = page.evaluate("window.__sharedTransfer.url")
    assert shared_url == "https://downloads.example/downloads/macos"
    assert "request=" not in shared_url
    assert requested and started
    assert started[0]["event_id"] == requested[0]["event_id"]
    assert started[0]["transport"] == "web_share"
    assert page.evaluate("window.__openedLink") is None


def test_desktop_download_copy_uses_clean_public_url_and_tracks_transport(page):
    page.add_init_script(
        """
        Object.defineProperty(Navigator.prototype, "clipboard", {
          configurable: true,
          get: function() {
            return {writeText: async function(value) { window.__copiedTransfer = value; }};
          }
        });
        """
    )
    mock_telegram_desktop_download(page, platform="android")
    requested = []
    started = []

    def request_download(route):
        requested.append(route.request.post_data_json)
        json_response(
            route,
            {
                "ok": True,
                "platform": "windows",
                "download_url": "https://downloads.example/desktop-download?platform=windows&request=tracked-secret",
                "download_page_url": "https://downloads.example/desktop-download?platform=windows&request=tracked-secret",
                "transfer_url": "https://downloads.example/downloads/windows",
                "file_name": "Pomp-HSK-AI-1.0.0-setup.exe",
                "duplicate": False,
            },
        )

    page.route("**/api/v3/desktop-download/request", request_download)
    page.route(
        "**/api/v3/desktop-download/started",
        lambda route: (
            started.append(route.request.post_data_json),
            json_response(route, {"ok": True, "recorded": True, "duplicate": False}),
        )[-1],
    )
    _open_course_profile_with_desktop_release(page)

    page.locator('[data-pdd-platform="windows"][data-pdd-source="profile"]').click()
    page.locator('[data-pdd-destination-action="copy"]').click()
    page.wait_for_function("Boolean(window.__copiedTransfer)")
    page.wait_for_function("document.querySelector('.pdd-promo-shell[data-mode=\"success\"]')")
    page.wait_for_timeout(100)

    copied_url = page.evaluate("window.__copiedTransfer")
    assert copied_url == "https://downloads.example/downloads/windows"
    assert "request=" not in copied_url
    assert requested and started
    assert started[0]["event_id"] == requested[0]["event_id"]
    assert started[0]["transport"] == "copy_link"
    assert page.evaluate("window.__openedLink") is None


def test_desktop_download_destination_fits_short_safe_area_viewport(page):
    page.set_viewport_size({"width": 360, "height": 640})
    mock_telegram_desktop_download(page, platform="android")
    _open_course_profile_with_desktop_release(page)

    page.locator('[data-pdd-platform="macos"][data-pdd-source="profile"]').click()
    dialog = page.locator(".pdd-destination-shell")
    expect(dialog).to_be_visible()
    expect(dialog).to_have_attribute("role", "dialog")
    page.wait_for_timeout(220)
    box = dialog.bounding_box()

    assert box is not None
    assert box["x"] >= 0 and box["y"] >= 0
    assert box["x"] + box["width"] <= 360.5
    assert box["y"] + box["height"] <= 640.5
    for destination in ("direct", "share", "copy"):
        expect(
            page.locator(f'[data-pdd-destination-action="{destination}"]')
        ).to_be_visible()


def test_desktop_promo_fits_short_360x640_viewport(page):
    page.set_viewport_size({"width": 360, "height": 640})
    mock_telegram_desktop_download(page, platform="tdesktop", native_download=True)
    _open_course_profile_with_desktop_release(page)
    page.locator('#nav button[data-s="course"]').click()

    assert page.evaluate(
        "PompDesktopDownload.queuePromo('lesson_end_promo',{lesson_id:1})"
    )
    expect(page.locator(".pdd-promo-shell")).to_be_visible()
    page.wait_for_timeout(300)  # wait for the 220 ms entrance transform
    box = page.locator(".pdd-promo-shell").bounding_box()
    assert box is not None
    assert box["x"] >= 0 and box["y"] >= 0
    assert box["x"] + box["width"] <= 360.5
    assert box["y"] + box["height"] <= 640.5
    expect(page.locator('.pdd-promo-shell [data-pdd-platform="macos"]')).to_be_visible()
    expect(page.locator('.pdd-promo-shell [data-pdd-platform="windows"]')).to_be_visible()
