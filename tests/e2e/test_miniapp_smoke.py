import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")
expect = playwright_api.expect
sync_playwright = playwright_api.sync_playwright


APP_ROOT = Path(__file__).resolve().parents[2]
STATIC_BASE_URL = "http://hsk-ai.local"
BASE_URL = os.getenv("MINIAPP_E2E_BASE_URL", STATIC_BASE_URL).rstrip("/")
PROD_ORIGIN = "https://telegram-chinese-bot-production.up.railway.app"

STATIC_FILES = {
    "study.html": APP_ROOT / "app/static/study.html",
    "study-v2.css": APP_ROOT / "app/static/study-v2.css",
    "study-v2.js": APP_ROOT / "app/static/study-v2.js",
    "voice-practice.html": APP_ROOT / "app/static/voice-practice.html",
    "hsk1.html": APP_ROOT / "app/static/hsk1.html",
    "subscription.html": APP_ROOT / "app/static/subscription.html",
    "course-miniapp-v2.js": APP_ROOT / "app/static/course-miniapp-v2.js",
}

ACTIVE_ACCESS = {
    "status": "active",
    "level": "hsk1",
    "language": "uz",
    "limits": {
        "quiz_per_lesson_24h": 999,
        "audio_daily": 999,
        "flashcard_translate_daily": 999,
        "starred_limit": 999,
        "wrong_analysis": True,
        "backend_progress": True,
    },
}

TRIAL_ACCESS = {
    "status": "trial",
    "level": "hsk1",
    "language": "uz",
    "limits": {
        "quiz_per_lesson_24h": 1,
        "audio_daily": 5,
        "flashcard_translate_daily": 20,
        "starred_limit": 3,
        "wrong_analysis": False,
        "backend_progress": False,
    },
}


@pytest.fixture()
def page():
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        if BASE_URL == STATIC_BASE_URL:
            route_static_files(page)
        yield page
        context.close()
        browser.close()


def app_url(path):
    return f"{BASE_URL}/{path.lstrip('/')}"


def json_response(route, payload):
    route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(payload),
    )


def route_static_files(page):
    def handle(route):
        path = urlparse(route.request.url).path.lstrip("/") or "study.html"
        file_path = STATIC_FILES.get(path)
        if not file_path:
            route.abort()
            return
        content_types = {".css": "text/css", ".js": "application/javascript"}
        content_type = content_types.get(file_path.suffix, "text/html")
        route.fulfill(
            status=200,
            content_type=content_type,
            body=file_path.read_text(encoding="utf-8"),
        )

    page.route(
        re.compile(
            r"^http://hsk-ai\.local/(study\.html|study-v2\.css|study-v2\.js|voice-practice\.html|hsk1\.html|subscription\.html|course-miniapp-v2\.js)(\?.*)?$"
        ),
        handle,
    )


def mock_study_access(page, access=ACTIVE_ACCESS, fail_events=True):
    page.route(
        f"{PROD_ORIGIN}/api/miniapp/access",
        lambda route: json_response(route, access),
    )
    if fail_events:
        page.route(f"{PROD_ORIGIN}/api/miniapp/event", lambda route: route.abort())
    else:
        page.route(
            f"{PROD_ORIGIN}/api/miniapp/event",
            lambda route: json_response(route, {"ok": True}),
        )


def mock_course_onboarding(page):
    page.route(
        f"{PROD_ORIGIN}/api/miniapp/onboarding",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "level": "hsk1",
                "lesson": 1,
                "tab": "course",
                "placement": False,
            },
        ),
    )


def mock_course_lesson(page):
    questions = [
        {
            "id": f"q{i}",
            "type": "multiple_choice",
            "q": f"Question {i}",
            "opts": [f"Answer {i}", f"Wrong {i}A", f"Wrong {i}B", f"Wrong {i}C"],
            "ans": 0,
            "expl": f"Answer {i} is correct.",
        }
        for i in range(1, 6)
    ]
    page.route(
        re.compile(r".*/api/miniapp/lesson\?.*"),
        lambda route: json_response(
            route,
            {
                "ok": True,
                "lesson": {
                    "id": 5,
                    "lesson_id": 5,
                    "lang": "uz",
                    "quiz_questions": questions,
                    "reinforcement_tasks": [],
                },
            },
        ),
    )
    page.route("**/api/miniapp/event", lambda route: route.abort())


def mock_course_lesson_flow(page):
    def handle_section_plan(route):
        json_response(
            route,
            {
                "ok": True,
                "level": "hsk1",
                "content_level": "hsk1",
                "completed_book_lessons_count": 0,
                "completed_sections_count": 0,
                "total_sections": 2,
                "current_section": {"section_key": "1.1", "section_no": 1, "book_lesson_order": 1},
                "lessons": [
                    {
                        "level": "hsk1",
                        "content_level": "hsk1",
                        "lesson_id": 1,
                        "book_lesson_order": 1,
                        "lesson_title": "你好",
                        "section_count": 2,
                        "is_completed": False,
                        "is_locked": False,
                        "sections": [
                            {
                                "level": "hsk1",
                                "book_lesson_order": 1,
                                "lesson_id": 1,
                                "lesson_title": "你好",
                                "section_key": "1.1",
                                "section_no": 1,
                                "section_count": 2,
                                "section_purpose": "intro",
                                "section_title": "Новые слова",
                                "section_group": {"key": "a", "label": "A", "no": 1, "section_start": 1, "section_end": 2},
                                "active_words": [{"zh": "你好", "pinyin": "nǐ hǎo", "meaning": "привет"}],
                                "node_status": "current",
                                "is_current": True,
                                "is_locked": False,
                                "is_completed": False,
                                "next_section": {"section_key": "1.2", "section_no": 2, "book_lesson_order": 1},
                            },
                            {
                                "level": "hsk1",
                                "book_lesson_order": 1,
                                "lesson_id": 1,
                                "lesson_title": "你好",
                                "section_key": "1.2",
                                "section_no": 2,
                                "section_count": 2,
                                "section_purpose": "review",
                                "section_title": "Review",
                                "section_group": {"key": "a", "label": "A", "no": 1, "section_start": 1, "section_end": 2},
                                "active_words": [{"zh": "谢谢", "pinyin": "xiè xie", "meaning": "спасибо"}],
                                "node_status": "locked",
                                "is_current": False,
                                "is_locked": True,
                                "is_completed": False,
                                "next_section": None,
                            },
                        ],
                    }
                ],
                "sections": [],
            },
        )

    def handle_lesson_flow(route):
        query = parse_qs(urlparse(route.request.url).query)
        section_key = query.get("section", ["1.1"])[0]
        section_no = int(section_key.split(".")[1])
        word = "谢谢" if section_key == "1.2" else "你好"
        json_response(
            route,
            {
                "ok": True,
                "flow": {
                    "id": f"lesson:1:{section_key}:v1",
                    "version": 1,
                    "level": "hsk1",
                    "lesson_id": 1,
                    "book_lesson_order": 1,
                    "section_key": section_key,
                    "section_no": section_no,
                    "section_count": 2,
                    "section_purpose": "intro" if section_key == "1.1" else "review",
                    "section_title": "Новые слова" if section_key == "1.1" else "Review",
                    "title": word,
                    "active_words": [{"zh": word, "pinyin": "nǐ hǎo", "meaning": "привет"}],
                    "cards": [
                        {
                            "id": "word:1",
                            "type": "active_word",
                            "title": "Новое активное слово",
                            "word": {"zh": word, "pinyin": "nǐ hǎo", "meaning": "привет"},
                            "required": True,
                        },
                        {
                            "id": "activity:meaning",
                            "type": "meaning_guess",
                            "title": "Выберите правильное значение",
                            "prompt": f"Что означает {word}?",
                            "options": ["привет", "спасибо"],
                            "correct_index": 0,
                            "required": True,
                        },
                        {
                            "id": "activity:match",
                            "type": "match_pairs",
                            "title": "Соедините пары",
                            "prompt": "Соедините пары",
                            "pairs": [["你好", "привет"], ["谢谢", "спасибо"]],
                            "required": True,
                        },
                    ],
                },
            },
        )

    page.route(re.compile(r".*/api/miniapp/course-section-plan\?.*"), handle_section_plan)
    page.route(
        re.compile(r".*/api/miniapp/course-lesson\?.*"),
        handle_lesson_flow,
    )
    page.route(
        f"{PROD_ORIGIN}/api/miniapp/course-lesson/complete",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "completed_lesson": 1,
                "next_lesson": 2,
                "percent": 100,
                "correct": 1,
                "total": 1,
                "section_key": "1.1",
                "section_no": 1,
                "section_count": 2,
                "book_lesson_completed": False,
                "next_section": {"section_key": "1.2", "section_no": 2, "book_lesson_order": 1},
                "reward": {"xp": 30, "awarded_xp": 30},
            },
        ),
    )


def mock_practice_flow(page):
    questions = [
        {
            "id": f"hsk1:1:{index}",
            "level": "hsk1",
            "lesson": 1,
            "type": "multiple_choice",
            "subtype": "hanzi_to_meaning",
            "prompt": f"Practice question {index}",
            "sentence": "",
            "audio_text": "",
            "options": ["Correct", "Wrong"],
            "answer_index": 0,
            "explanation": "Correct",
        }
        for index in range(1, 11)
    ]
    page.route(
        f"{PROD_ORIGIN}/api/miniapp/practice/start",
        lambda route: json_response(
            route,
            {
                "ok": True,
                "session": {
                    "id": "practice:1:placement:placement:hsk1:v1",
                    "mode": "placement",
                    "skill": "",
                    "level": "hsk1",
                    "questions": questions,
                },
            },
        ),
    )
def study_frame(page):
    page.locator("#level-frame").wait_for(state="attached")
    return page.frame_locator("#level-frame")


def wait_for_access_cache(page, status):
    page.wait_for_function(
        """expected => {
          const raw = localStorage.getItem('hsk_all_access_cache_v1');
          if (!raw) return false;
          try { return JSON.parse(raw).access?.status === expected; }
          catch (e) { return false; }
        }""",
        arg=status,
    )


def wait_for_pending_event(page, key, event, lesson_id=5):
    page.wait_for_function(
        """([storageKey, eventName, lessonId]) => {
          try {
            const events = JSON.parse(localStorage.getItem(storageKey) || '[]');
            return events.some(item => item.event === eventName && item.lesson_id === lessonId);
          } catch (e) {
            return false;
          }
        }""",
        arg=[key, event, lesson_id],
    )


def test_study_app_open_and_query_tab_routing(page):
    mock_study_access(page)

    cases = [
        ("quiz", "#page-quiz", "#quiz-filters .active"),
        ("words", "#page-flashcards", "#fc-filters .active"),
        ("grammar", "#page-grammar", "#grammar-filters .active"),
    ]
    for tab, page_selector, active_filter in cases:
        page.goto(app_url(f"/study.html?level=hsk1&lesson=5&tab={tab}&lang=uz"))
        frame = study_frame(page)
        expect(frame.locator(page_selector)).to_have_class(re.compile(r"\bactive\b"))
        expect(frame.locator(active_filter)).to_contain_text("Dars 5")


def test_v2_home_course_voice_and_placement_flow(page):
    mock_study_access(page)
    mock_practice_flow(page)

    page.goto(app_url("/study.html?level=hsk1&lang=ru&tab=home"))
    frame = study_frame(page)
    expect(frame.locator("#page-home.active")).to_be_visible()
    expect(frame.locator("#page-home")).to_contain_text("Продолжим китайский")

    frame.locator('.v2-nav [data-page="course"]').click()
    expect(frame.locator("#page-course.active")).to_be_visible()
    expect(frame.locator("#page-course")).to_contain_text("Учебный путь")

    frame.locator('.v2-nav [data-page="voice"]').click()
    voice = frame.frame_locator("#voice-frame")
    expect(voice.locator("#btn-welcome-start")).to_be_visible()
    voice.locator("#btn-welcome-start").click()
    expect(voice.locator("#btn-start-call")).to_be_visible()
    voice.locator("#btn-start-call").click()
    expect(voice.locator("#btn-end-call")).to_be_visible()
    voice.locator("#btn-end-call").click()
    expect(voice.locator("#btn-summary-close")).to_be_visible()
    voice.locator("#btn-summary-close").click()
    expect(frame.locator("#page-home.active")).to_be_visible()

    frame.locator("#page-home .v2-feature").filter(has_text=re.compile("Test Center|Центр тестов|Test markazi")).click()
    frame.locator("#page-tests .v2-row-card").first.click()
    expect(frame.locator("#page-quiz.active")).to_be_visible()
    expect(frame.locator("#page-quiz .page-title")).to_have_count(0)
    expect(frame.locator("#quiz-box .quiz-meta")).to_contain_text("1/10")


def test_course_onboarding_completes_four_steps_and_opens_lesson(page):
    access = {
        **ACTIVE_ACCESS,
        "course_profile": {
            "goal": "hsk_exam",
            "daily_minutes": 10,
            "start_mode": "continue",
            "timezone_offset_minutes": 0,
            "onboarding_completed": False,
            "has_progress": False,
        },
    }
    mock_study_access(page, access, fail_events=False)
    mock_course_onboarding(page)

    page.goto(app_url("/study.html?level=hsk1&lang=ru"))
    frame = study_frame(page)
    expect(frame.locator("#v2-onboarding")).to_be_visible()

    frame.locator("#v2-onboarding .v2-primary").click()
    expect(frame.locator("#v2-onboarding h1")).to_contain_text("Зачем")
    frame.locator("#v2-onboarding .v2-primary").click()
    expect(frame.locator("#v2-onboarding h1")).to_contain_text("Сколько минут")
    frame.locator("#v2-onboarding .v2-primary").click()
    expect(frame.locator("#v2-onboarding h1")).to_contain_text("Откуда")
    frame.locator("#v2-onboarding .v2-primary").click()

    expect(frame.locator("#v2-onboarding")).to_have_count(0)
    expect(frame.locator("#page-course.active")).to_be_visible()
    expect(frame.locator("#v2-sheet .v2-sheet")).to_be_visible()


def test_server_backed_lesson_cards_finish_with_reward(page):
    mock_study_access(page, ACTIVE_ACCESS, fail_events=False)
    mock_course_lesson_flow(page)

    page.goto(app_url("/study.html?level=hsk1&lesson=1&tab=course&lang=ru"))
    frame = study_frame(page)
    expect(frame.locator("#v2-sheet .v2-sheet")).to_be_visible()
    frame.locator("#v2-sheet .v2-primary").click()

    expect(frame.locator("#page-lesson.active")).to_be_visible()
    expect(frame.locator(".v2-word-hero")).to_contain_text("你好")
    frame.locator(".v2-card-next").click()
    frame.get_by_role("button", name="привет", exact=True).click()
    frame.locator(".v2-card-next").click()
    expect(frame.locator(".v2-dialog-card")).to_contain_text("你好")
    frame.locator(".v2-card-next").click()

    expect(frame.locator(".v2-reward-shell")).to_contain_text("100%")
    expect(frame.locator(".v2-reward-shell")).to_contain_text("+30")


def test_locked_path_node_readiness_test_opens_selected_section(page):
    mock_study_access(page, ACTIVE_ACCESS, fail_events=False)
    jump_requests = []

    def handle_lesson_flow(route):
        query = parse_qs(urlparse(route.request.url).query)
        section_key = query.get("section", ["1.1"])[0]
        lesson_order = int(section_key.split(".")[0])
        section_no = int(section_key.split(".")[1])
        word = "再见" if section_key == "2.1" else "你好"
        json_response(
            route,
            {
                "ok": True,
                "flow": {
                    "id": f"lesson:{lesson_order}:{section_key}:v1",
                    "version": 1,
                    "level": "hsk1",
                    "lesson_id": lesson_order,
                    "book_lesson_order": lesson_order,
                    "section_key": section_key,
                    "section_no": section_no,
                    "section_count": 1,
                    "section_purpose": "intro",
                    "section_title": "Yangi so'zlar",
                    "title": word,
                    "active_words": [{"zh": word, "pinyin": "pinyin", "meaning": "meaning"}],
                    "cards": [
                        {
                            "id": f"word:{section_key}",
                            "type": "active_word",
                            "title": "Yangi faol so'z",
                            "word": {"zh": word, "pinyin": "pinyin", "meaning": "meaning"},
                            "required": True,
                        }
                    ],
                },
            },
        )

    def handle_jump(route):
        payload = route.request.post_data_json
        jump_requests.append(payload() if callable(payload) else payload)
        json_response(
            route,
            {
                "ok": True,
                "level": "hsk1",
                "lesson_id": 2,
                "book_lesson_order": 2,
                "section_key": "2.1",
                "completed_lessons_count": 1,
                "percent": 25,
                "passed": False,
            },
        )

    page.route(
        re.compile(r".*/api/miniapp/course-section-plan\?.*"),
        lambda route: json_response(
            route,
            {
                "ok": True,
                "level": "hsk1",
                "content_level": "hsk1",
                "completed_book_lessons_count": 0,
                "completed_sections_count": 0,
                "total_sections": 2,
                "current_section": {"section_key": "1.1", "section_no": 1, "book_lesson_order": 1},
                "lessons": [
                    {
                        "level": "hsk1",
                        "lesson_id": 1,
                        "book_lesson_order": 1,
                        "lesson_title": "Salom",
                        "section_count": 1,
                        "is_completed": False,
                        "is_locked": False,
                        "sections": [
                            {
                                "level": "hsk1",
                                "book_lesson_order": 1,
                                "lesson_id": 1,
                                "lesson_title": "Salom",
                                "section_key": "1.1",
                                "section_no": 1,
                                "section_count": 1,
                                "section_purpose": "intro",
                                "section_title": "Yangi so'zlar",
                                "section_group": {"key": "a", "label": "A", "no": 1, "section_start": 1, "section_end": 1},
                                "active_words": [{"zh": "你好", "pinyin": "pinyin", "meaning": "meaning"}],
                                "node_status": "current",
                                "is_current": True,
                                "is_locked": False,
                                "is_completed": False,
                                "next_section": {"section_key": "2.1", "section_no": 1, "book_lesson_order": 2},
                            }
                        ],
                    },
                    {
                        "level": "hsk1",
                        "lesson_id": 2,
                        "book_lesson_order": 2,
                        "lesson_title": "Xayr",
                        "section_count": 1,
                        "is_completed": False,
                        "is_locked": True,
                        "sections": [
                            {
                                "level": "hsk1",
                                "book_lesson_order": 2,
                                "lesson_id": 2,
                                "lesson_title": "Xayr",
                                "section_key": "2.1",
                                "section_no": 1,
                                "section_count": 1,
                                "section_purpose": "intro",
                                "section_title": "Yangi so'zlar",
                                "section_group": {"key": "a", "label": "A", "no": 1, "section_start": 1, "section_end": 1},
                                "active_words": [{"zh": "再见", "pinyin": "pinyin", "meaning": "meaning"}],
                                "node_status": "locked",
                                "is_current": False,
                                "is_locked": True,
                                "is_completed": False,
                                "next_section": None,
                            }
                        ],
                    },
                ],
                "sections": [],
            },
        ),
    )
    page.route(re.compile(r".*/api/miniapp/course-lesson\?.*"), handle_lesson_flow)
    page.route(f"{PROD_ORIGIN}/api/miniapp/course-lesson/jump", handle_jump)
    page.add_init_script(
        """window.Telegram={WebApp:{initData:"miniapp-e2e",ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){}}};"""
    )

    page.goto(app_url("/study.html?level=hsk1&tab=course&lang=uz"))
    frame = study_frame(page)
    page.evaluate("window.MiniAppBridge.hasAuth=()=>true")
    frame.get_by_role("button", name=re.compile(r"^Dars 2\.1$")).click()
    expect(frame.locator("#v2-sheet")).to_contain_text("Qisqa tekshiruv")
    frame.get_by_role("button", name="Testni boshlash").click()

    for _ in range(12):
        if frame.get_by_role("button", name="Shu darsdan davom etish").count():
            break
        expect(frame.locator("#quiz-box .option").first).to_be_visible()
        frame.locator("#quiz-box .option").first.click()
        frame.locator("#quiz-box .btn.primary").click()

    expect(frame.get_by_role("button", name="Shu darsdan davom etish")).to_be_visible()
    frame.get_by_role("button", name="Shu darsdan davom etish").click()

    expect(frame.locator("#page-lesson.active")).to_be_visible()
    expect(frame.locator(".v2-word-hero")).to_contain_text("再见")
    assert jump_requests
    assert jump_requests[0]["section_key"] == "2.1"


def test_study_quiz_score_and_event_localstorage_fallback(page):
    mock_study_access(page, ACTIVE_ACCESS, fail_events=True)

    page.goto(app_url("/study.html?level=hsk1&lesson=5&tab=quiz&lang=uz"))
    frame = study_frame(page)
    frame.locator("#quiz-box .btn.primary").click()

    for _ in range(5):
        expect(frame.locator("#quiz-box .option").first).to_be_visible()
        frame.locator("#quiz-box .option").first.click()
        frame.locator("#quiz-box .btn.primary").click()

    expect(frame.locator("#score-box")).to_be_visible()
    expect(frame.locator("#score-box")).to_contain_text("%")
    wait_for_pending_event(page, "hsk_pending_events", "study_quiz_completed")


def test_trial_paywall_routes_to_subscription(page):
    mock_study_access(page, TRIAL_ACCESS, fail_events=False)

    page.goto(app_url("/study.html?level=hsk1&lesson=5&tab=words&lang=uz"))
    wait_for_access_cache(page, "trial")
    frame = study_frame(page)
    stars = frame.locator(".fc-action.star")
    expect(stars.nth(3)).to_be_visible()

    for index in range(4):
        stars.nth(index).click()

    expect(frame.locator("#limit-modal")).to_be_visible()
    frame.locator("#limit-sub").click()
    expect(page).to_have_url(re.compile(r"subscription\.html"))


def test_active_access_keeps_paid_features_open(page):
    mock_study_access(page, ACTIVE_ACCESS, fail_events=False)

    page.goto(app_url("/study.html?level=hsk1&lesson=5&tab=words&lang=uz"))
    wait_for_access_cache(page, "active")
    frame = study_frame(page)
    stars = frame.locator(".fc-action.star")
    expect(stars.nth(3)).to_be_visible()

    for index in range(4):
        stars.nth(index).click()

    expect(frame.locator("#limit-modal")).not_to_be_visible(timeout=1000)


def test_subscription_page_smoke(page):
    page.route("**/api/subscription-miniapp/**", lambda route: route.abort())

    page.goto(app_url("/subscription.html?lang=uz&mode=subscription"))

    expect(page.locator("#plans .plan").first).to_be_visible()
    expect(page.locator("#methods .choice").first).to_be_visible()
    expect(page.locator("#paymentBox")).to_have_count(1)


def test_course_miniapp_v2_quiz_fallback_and_return_button(page):
    mock_course_lesson(page)

    page.goto(app_url("/hsk1.html?lesson=5&mode=quiz&lang=uz"))
    expect(page.locator(".cmv2")).to_be_visible()

    for _ in range(5):
        expect(page.locator(".cmv2-option").first).to_be_visible()
        page.locator(".cmv2-option").first.click()
        expect(page.locator("#cmv2-primary")).to_be_enabled()
        page.locator("#cmv2-primary").click()
        expect(page.locator("#cmv2-primary")).to_be_enabled()
        page.locator("#cmv2-primary").click()

    expect(page.locator(".cmv2-result")).to_be_visible()
    wait_for_pending_event(page, "hsk1_pending_events", "quiz_completed")

    page.locator("#cmv2-primary").click()
    wait_for_pending_event(page, "hsk1_pending_events", "bot_return_clicked")
