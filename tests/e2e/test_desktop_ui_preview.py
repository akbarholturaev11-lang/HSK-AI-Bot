from __future__ import annotations

import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest


playwright = pytest.importorskip("playwright.sync_api")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DESKTOP_UI_ROOT = PROJECT_ROOT / "desktop" / "ui"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args) -> None:
        return


def _install_native_fixture(
    page,
    lessons: dict[int, dict],
    delays=None,
    *,
    update=None,
    update_check_failures=0,
    update_install_delay=0,
    update_install_error=False,
    is_paid=True,
    pending_payment=None,
    local_ai_ready=False,
):
    lesson_rows = []
    for lesson_order in sorted(lessons):
        lesson_rows.append(
            {
                "n": lesson_order,
                "status": "current"
                if lesson_order == max(lessons)
                else "done",
                "zh": f"课{lesson_order}",
                "py": f"kè {lesson_order}",
                "tr": {
                    "uz": f"{lesson_order}-dars",
                    "ru": f"Урок {lesson_order}",
                    "tj": f"Дарси {lesson_order}",
                },
            }
        )
    fixture = {
        "lessons": {str(key): value for key, value in lessons.items()},
        "delays": {str(key): value for key, value in (delays or {}).items()},
        "update": update
        or {
            "available": False,
            "currentVersion": "test",
        },
        "updateCheckFailures": update_check_failures,
        "updateInstallDelay": update_install_delay,
        "updateInstallError": update_install_error,
        "map": {
            "ok": True,
            "authenticated": True,
            "level": "hsk1",
            "label": "HSK 1",
            "user": {
                "name": "Fixture User",
                "avatar": "FU",
                "language": "uz",
                "is_paid": is_paid,
            },
            "progress": {"completed": 0, "xp": 0, "streak": 0},
            "units": [
                {
                    "no": 1,
                    "title": {
                        "uz": "Fixture",
                        "ru": "Fixture",
                        "tj": "Fixture",
                    },
                    "lessons": lesson_rows,
                }
            ],
        },
        "subscription": {
            "pendingPayment": pending_payment,
            "submissions": 0,
        },
        "localAiReady": local_ai_ready,
    }
    encoded = json.dumps(fixture, ensure_ascii=False)
    page.add_init_script(
        script=f"""
          window.__DESKTOP_FIXTURE__ = {encoded};
          window.__COMPLETIONS = [];
          window.__UPDATE_CHECKS = 0;
          window.__UPDATE_INSTALLS = 0;
          window.__AI_CHATS = [];
          window.__DESKTOP_EVENT_HANDLERS = {{}};
          window.__TAURI__ = {{
            core: {{
              invoke: async (command, args = {{}}) => {{
                const fixture = window.__DESKTOP_FIXTURE__;
                if (command === "desktop_app_info") {{
                  return {{ productName: "HSK AI", version: "test", platform: "macos" }};
                }}
                if (command === "desktop_auth_status") {{
                  return {{
                    linked: true,
                    bootstrap: {{
                      ok: true,
                      authenticated: true,
                      user: {{ name: "Fixture User", language: "uz", level: "hsk1", is_paid: {str(is_paid).lower()} }}
                    }}
                  }};
                }}
                if (command === "desktop_course_map") return fixture.map;
                if (command === "desktop_subscription_overview") {{
                  const paid = Boolean(fixture.map.user.is_paid);
                  const pending = fixture.subscription.pendingPayment;
                  return {{
                    ok: true,
                    source: "desktop_subscription",
                    mode: "subscription",
                    access: {{
                      state: paid ? "paid" : "free",
                      is_paid: paid,
                      expires_at: paid ? "2026-12-31T00:00:00Z" : null
                    }},
                    checkout_allowed: !paid && !pending,
                    read_only_reason: paid
                      ? "desktop_subscription_active"
                      : pending ? "desktop_subscription_pending" : null,
                    attempt_id: !paid && !pending ? "desktop-e2e-attempt-1234" : null,
                    pending_payment: pending,
                    prices: !paid && !pending ? {{
                      visa: {{
                        "10_days": {{ final_amount: 45, currency: "TJS", discount_applied: false }},
                        "1_month": {{ final_amount: 95, currency: "TJS", discount_applied: false }},
                        "3_months": {{ final_amount: 245, currency: "TJS", discount_applied: false }}
                      }},
                      alipay: {{
                        "10_days": {{ final_amount: 28, currency: "¥", discount_applied: false }},
                        "1_month": {{ final_amount: 66, currency: "¥", discount_applied: false }},
                        "3_months": {{ final_amount: 168, currency: "¥", discount_applied: false }}
                      }},
                      wechat: {{
                        "10_days": {{ final_amount: 28, currency: "¥", discount_applied: false }},
                        "1_month": {{ final_amount: 66, currency: "¥", discount_applied: false }},
                        "3_months": {{ final_amount: 168, currency: "¥", discount_applied: false }}
                      }}
                    }} : {{}}
                  }};
                }}
                if (command === "desktop_subscription_quote") {{
                  return {{
                    ok: true,
                    source: "desktop_subscription",
                    mode: "subscription",
                    access: {{ state: "free", is_paid: false, expires_at: null }},
                    quote: {{
                      plan_type: args.plan,
                      payment_method: args.method,
                      card_country: args.country,
                      final_amount: 95,
                      final_currency: "TJS",
                      pay_amount: "95",
                      pay_currency: "TJS",
                      discount_applied: false,
                      discount_percent: 0,
                      payment_details: "Fixture Visa: 0000 0000 0000 0000"
                    }}
                  }};
                }}
                if (command === "desktop_subscription_submit") {{
                  fixture.subscription.submissions += 1;
                  fixture.subscription.pendingPayment = {{
                    id: 77,
                    plan_type: args.plan,
                    payment_method: args.method,
                    amount: 95,
                    currency: "TJS",
                    submitted_at: "2026-08-02T00:00:00Z"
                  }};
                  return {{
                    ok: true,
                    status: "pending",
                    source: "desktop_subscription",
                    mode: "subscription",
                    payment_id: 77,
                    already_pending: false,
                    access: {{ state: "free", is_paid: false, expires_at: null }}
                  }};
                }}
                if (command === "desktop_lesson_data") {{
                  const key = String(args.lessonOrder);
                  const delay = Number(fixture.delays[key] || 0);
                  if (delay) await new Promise(resolve => setTimeout(resolve, delay));
                  return fixture.lessons[key];
                }}
                if (command === "desktop_lesson_complete") {{
                  window.__COMPLETIONS.push(JSON.parse(JSON.stringify(args)));
                  return {{
                    ok: true,
                    completed_lesson: args.lessonOrder,
                    next_lesson: args.lessonOrder + 1,
                    completed_lessons_count: args.lessonOrder,
                    gamification: {{ awarded_xp: 20, xp: 20, streak: 1 }}
                  }};
                }}
                if (command === "desktop_set_language") {{
                  return {{ ok: true, language: args.language }};
                }}
                if (command === "desktop_tts_speak") {{
                  return {{ ok: false, available: false, error: "desktop_tts_unavailable" }};
                }}
                if (command === "local_ai_model_status") {{
                  return {{
                    modelId: "qwen3-4b-q4-k-m",
                    installed: Boolean(fixture.localAiReady),
                    sizeBytes: fixture.localAiReady ? 2497280256 : null,
                    expectedSizeBytes: 2497280256,
                    downloadedBytes: fixture.localAiReady ? 2497280256 : 0,
                    state: fixture.localAiReady ? "ready" : "missing",
                    runtimeAvailable: Boolean(fixture.localAiReady),
                    runtimeState: "stopped"
                  }};
                }}
                if (command === "local_ai_install_start") {{
                  return {{
                    modelId: "qwen3-4b-q4-k-m",
                    installed: false,
                    sizeBytes: null,
                    expectedSizeBytes: 2497280256,
                    downloadedBytes: 0,
                    state: "starting",
                    runtimeAvailable: Boolean(fixture.localAiReady),
                    runtimeState: "stopped"
                  }};
                }}
                if (command === "local_ai_install_cancel") {{
                  return {{
                    modelId: "qwen3-4b-q4-k-m",
                    installed: false,
                    sizeBytes: null,
                    expectedSizeBytes: 2497280256,
                    downloadedBytes: 0,
                    state: "paused",
                    runtimeAvailable: Boolean(fixture.localAiReady),
                    runtimeState: "stopped"
                  }};
                }}
                if (command === "local_ai_pack_remove") {{
                  fixture.localAiReady = false;
                  return {{
                    modelId: "qwen3-4b-q4-k-m",
                    installed: false,
                    sizeBytes: null,
                    expectedSizeBytes: 2497280256,
                    downloadedBytes: 0,
                    state: "missing",
                    runtimeAvailable: false,
                    runtimeState: "stopped"
                  }};
                }}
                if (command === "local_ai_chat") {{
                  window.__AI_CHATS.push(JSON.parse(JSON.stringify(args.request)));
                  return {{
                    requestId: args.request.requestId,
                    text: "你好 — nǐ hǎo — salom",
                    durationMs: 12
                  }};
                }}
                if (command === "local_ai_chat_cancel") {{
                  return null;
                }}
                if (command === "desktop_update_check") {{
                  window.__UPDATE_CHECKS += 1;
                  if (fixture.updateCheckFailures > 0) {{
                    fixture.updateCheckFailures -= 1;
                    throw new Error("desktop_update_check_failed");
                  }}
                  return fixture.update;
                }}
                if (command === "desktop_update_install") {{
                  window.__UPDATE_INSTALLS += 1;
                  const updateHandler = window.__DESKTOP_EVENT_HANDLERS["desktop-update://progress"];
                  updateHandler?.({{
                    payload: {{
                      downloadedBytes: 5 * 1024 * 1024,
                      totalBytes: 10 * 1024 * 1024,
                      percent: 50,
                      state: "downloading"
                    }}
                  }});
                  const delay = Number(fixture.updateInstallDelay || 0);
                  if (delay) await new Promise(resolve => setTimeout(resolve, delay));
                  if (fixture.updateInstallError) {{
                    throw new Error("desktop_update_install_failed");
                  }}
                  return null;
                }}
                if (command === "desktop_logout") return null;
                throw new Error("desktop_operation_not_allowed");
              }}
            }},
            event: {{
              listen: async (eventName, handler) => {{
                window.__DESKTOP_EVENT_HANDLERS[eventName] = handler;
                return () => {{ delete window.__DESKTOP_EVENT_HANDLERS[eventName]; }};
              }}
            }}
          }};
        """
    )


def _lesson_payload(lesson_order: int, cards: list[dict], *, preview_half=False):
    return {
        "ok": True,
        "level": "hsk1",
        "lesson_order": lesson_order,
        "preview_half": preview_half,
        "lesson": {
            "schema_version": 2,
            "level": "hsk1",
            "lesson_id": lesson_order,
            "title": f"Fixture {lesson_order}",
            "sections": [
                {
                    "section_no": 1,
                    "section_title": {
                        "uz": "Sinov",
                        "ru": "Тест",
                        "tj": "Санҷиш",
                    },
                    "cards": cards,
                }
            ],
        },
    }


@pytest.fixture(scope="module")
def desktop_ui_url():
    handler = partial(_QuietHandler, directory=str(DESKTOP_UI_ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.fixture()
def browser_page():
    with playwright.sync_playwright() as session:
        browser = session.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1180, "height": 780})
        errors: list[str] = []
        page.on(
            "console",
            lambda message: errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: errors.append(str(error)))
        yield page, errors
        browser.close()


def test_desktop_course_lesson_profile_and_ai_flow(
    desktop_ui_url,
    browser_page,
):
    page, errors = browser_page
    page.goto(f"{desktop_ui_url}/?mock=1", wait_until="networkidle")

    page.locator("#workspace").wait_for(state="visible")
    assert page.locator("#rail-user-name").inner_text() == "Akbar"
    assert page.locator("#content-title").inner_text() == "Bugun"
    assert "HSK 1" in page.locator(".view-tag").inner_text()

    page.locator(".resume-card .primary-button").click()
    page.locator("#lesson-layer").wait_for(state="visible")
    page.keyboard.press("Meta+K")
    assert page.locator("#ai-drawer").get_attribute("aria-hidden") == "true"
    page.keyboard.press("Shift+Tab")
    assert page.evaluate("document.activeElement?.id") == "lesson-next"
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement?.id") == "close-lesson"

    # active_word
    page.locator("#lesson-next").click()

    # meaning_guess
    page.locator(".lesson-option").nth(1).click()
    page.locator("#lesson-next").click()
    assert page.locator(".lesson-option.is-correct").count() == 1
    page.locator("#lesson-next").click()

    # pronunciation and grammar teaching cards
    page.locator("#lesson-next").click()
    page.locator("#lesson-next").click()

    # sentence_builder
    token_bank = page.locator(".token-bank")
    for token in ("你", "叫", "什么", "名字"):
        token_bank.get_by_role("button", name=token, exact=True).click()
    page.locator("#lesson-next").click()
    assert "is-correct" in page.locator("#lesson-feedback").get_attribute("class")
    page.locator("#lesson-next").click()

    # match_pairs
    pair_columns = page.locator(".pair-grid .lesson-options")
    left = pair_columns.nth(0)
    right = pair_columns.nth(1)
    left.get_by_role("button", name="你好", exact=True).click()
    right.get_by_role("button", name="salom", exact=True).click()
    left.get_by_role("button", name="名字", exact=True).click()
    right.get_by_role("button", name="ism", exact=True).click()
    page.locator("#lesson-next").click()

    page.get_by_role("heading", name="Dars saqlandi").wait_for()
    assert "+20 XP" in page.locator(".finish-stats").inner_text()
    page.locator("#lesson-next").click()
    page.locator("#lesson-layer").wait_for(state="hidden")

    page.locator("#ai-launcher").click()
    page.get_by_role("heading", name="AI Pack o‘rnatilmagan").wait_for()
    assert page.locator("#ai-input").is_disabled()
    page.locator("#close-ai").click()
    assert page.evaluate("document.activeElement?.id") == "ai-launcher"

    page.locator("#show-profile").click()
    page.locator("#content-inner").get_by_role(
        "heading", name="Profil va sozlamalar"
    ).wait_for()
    page.get_by_role("button", name="Русский", exact=True).click()
    page.locator("#content-inner").get_by_role(
        "heading", name="Профиль и настройки"
    ).wait_for()

    assert errors == []


def test_local_ai_ready_chat_uses_native_command_without_network(
    desktop_ui_url,
    browser_page,
):
    page, errors = browser_page
    _install_native_fixture(
        page,
        {
            1: _lesson_payload(
                1,
                [
                    {
                        "type": "active_word",
                        "word": {
                            "zh": "你",
                            "pinyin": "nǐ",
                            "meaning": {"uz": "sen"},
                        },
                    }
                ],
            )
        },
        local_ai_ready=True,
    )
    page.goto(desktop_ui_url, wait_until="networkidle")
    page.locator("#workspace").wait_for(state="visible")
    page.locator("#ai-launcher").click()
    page.get_by_role("heading", name="你好！Men lokal HSK ustozingizman.").wait_for()

    page.locator("#ai-input").fill("你好 nimani anglatadi?")
    page.get_by_role("button", name="Yuborish", exact=True).click()
    playwright.expect(page.locator(".ai-message.is-assistant")).to_contain_text(
        "你好 — nǐ hǎo — salom"
    )
    requests = page.evaluate("window.__AI_CHATS")
    assert len(requests) == 1
    assert "Current course: HSK 1" in requests[0]["prompt"]
    assert "Chinese: 课1" in requests[0]["prompt"]
    assert requests[0]["prompt"].endswith("你好 nimani anglatadi?")
    assert requests[0]["language"] == "uz"
    assert requests[0]["history"] == []
    assert page.locator("#ai-input").is_enabled()
    assert errors == []


def test_explicit_telegram_link_flow(desktop_ui_url, browser_page):
    page, errors = browser_page
    page.set_viewport_size({"width": 720, "height": 560})
    page.goto(
        f"{desktop_ui_url}/?mock=1&unlinked=1",
        wait_until="networkidle",
    )

    page.locator("#auth-screen").wait_for(state="visible")
    page.locator("#start-link").click()
    page.locator("#auth-code-wrap").wait_for(state="visible")
    assert page.locator("#auth-code").inner_text() == "HSK4827X"
    assert page.locator("#auth-screen").evaluate(
        "node => getComputedStyle(node).overflowY === 'auto'"
    )
    page.locator("#open-telegram").scroll_into_view_if_needed()
    auth_bottom = page.locator("#auth-screen").bounding_box()
    action_bottom = page.locator("#open-telegram").bounding_box()
    assert auth_bottom is not None and action_bottom is not None
    assert action_bottom["y"] + action_bottom["height"] <= (
        auth_bottom["y"] + auth_bottom["height"] + 1
    )
    page.locator("#open-telegram").click()
    playwright.expect(page.locator("#open-telegram")).to_be_hidden()
    playwright.expect(page.locator("#auth-step-2")).to_contain_text("qo‘lda yuboring")
    playwright.expect(page.locator("#auth-status")).to_contain_text("qo‘lda yuboring")
    page.locator("#workspace").wait_for(state="visible", timeout=8_000)

    assert errors == []


def test_desktop_subscription_checkout_becomes_pending(
    desktop_ui_url,
    browser_page,
):
    page, errors = browser_page
    _install_native_fixture(
        page,
        {
            1: _lesson_payload(
                1,
                [
                    {
                        "type": "active_word",
                        "word": {
                            "zh": "学",
                            "pinyin": "xué",
                            "meaning": {"uz": "o‘rganmoq"},
                        },
                    }
                ],
            )
        },
        is_paid=False,
    )
    page.goto(desktop_ui_url, wait_until="networkidle")
    page.locator("#workspace").wait_for(state="visible")

    page.locator("#show-subscription").click()
    page.get_by_role("heading", name="Obuna va to‘lov").wait_for()
    page.locator('[data-testid="subscription-plan"][data-plan="1_month"]').click()
    page.get_by_role("button", name="To‘lov ma’lumotlarini ko‘rish").click()
    page.get_by_text("Fixture Visa: 0000 0000 0000 0000").wait_for()

    page.locator("#payment-screenshot").set_input_files(
        {
            "name": "receipt.png",
            "mimeType": "image/png",
            "buffer": b"\x89PNG\r\n\x1a\nfixture",
        }
    )
    page.locator("#payment-submit").click()
    page.get_by_role("heading", name="To‘lov yuborildi").wait_for()
    assert page.evaluate("window.__DESKTOP_FIXTURE__.subscription.submissions") == 1
    assert errors == []


def test_desktop_content_scroll_owns_vertical_overflow(
    desktop_ui_url,
    browser_page,
):
    page, errors = browser_page
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(f"{desktop_ui_url}/?mock=1", wait_until="networkidle")
    page.locator("#workspace").wait_for(state="visible")

    header_box = page.locator(".content-header").bounding_box()
    refresh_box = page.locator("#refresh-map").bounding_box()
    avatar_box = page.locator("#header-profile").bounding_box()
    assert header_box is not None
    assert refresh_box is not None
    assert avatar_box is not None
    assert avatar_box["y"] == pytest.approx(refresh_box["y"], abs=1)
    assert avatar_box["y"] + avatar_box["height"] <= (
        header_box["y"] + header_box["height"] + 1
    )

    scroll_area = page.locator(".content-scroll")
    scroll_area.locator(".content-inner").evaluate(
        """
        (node) => {
          const spacer = document.createElement("div");
          spacer.dataset.testid = "desktop-scroll-spacer";
          spacer.style.height = "900px";
          spacer.style.pointerEvents = "none";
          node.appendChild(spacer);
        }
        """
    )
    before = scroll_area.evaluate(
        """
        (node) => ({
          clientHeight: node.clientHeight,
          scrollHeight: node.scrollHeight,
          scrollTop: node.scrollTop,
          overflowY: getComputedStyle(node).overflowY,
          bodyScrollTop: document.body.scrollTop,
          documentScrollTop: document.documentElement.scrollTop
        })
        """
    )

    assert before["overflowY"] in {"auto", "scroll"}
    assert before["scrollHeight"] > before["clientHeight"]
    assert before["scrollTop"] == 0
    assert before["bodyScrollTop"] == 0
    assert before["documentScrollTop"] == 0

    scroll_area.evaluate("node => { node.scrollTop = node.scrollHeight; }")
    after = scroll_area.evaluate(
        """
        (node) => ({
          scrollTop: node.scrollTop,
          bodyScrollTop: document.body.scrollTop,
          documentScrollTop: document.documentElement.scrollTop
        })
        """
    )

    assert after["scrollTop"] > 0
    assert after["bodyScrollTop"] == 0
    assert after["documentScrollTop"] == 0
    assert errors == []


def test_minimum_window_uses_collapsible_rail_and_ai_sheet(
    desktop_ui_url,
    browser_page,
):
    page, errors = browser_page
    page.set_viewport_size({"width": 700, "height": 600})
    page.goto(f"{desktop_ui_url}/?mock=1", wait_until="networkidle")
    page.locator("#workspace").wait_for(state="visible")

    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    workspace_box = page.locator("#workspace").bounding_box()
    content_box_before = page.locator(".content-column").bounding_box()
    assert workspace_box is not None
    assert content_box_before is not None

    page.locator("#rail-toggle").click()
    playwright.expect(page.locator("#rail-scrim")).to_be_visible()
    page.wait_for_function(
        "Math.abs(document.querySelector('#course-rail').getBoundingClientRect().left) < 1"
    )
    assert "is-open" in page.locator("#course-rail").get_attribute("class")

    rail_box = page.locator("#course-rail").bounding_box()
    scrim_box = page.locator("#rail-scrim").bounding_box()
    content_box_open = page.locator(".content-column").bounding_box()
    assert rail_box is not None
    assert scrim_box is not None
    assert content_box_open is not None
    assert rail_box["x"] >= -1
    assert rail_box["width"] == pytest.approx(280, abs=1)
    assert rail_box["x"] + rail_box["width"] <= 700
    assert content_box_open["x"] == pytest.approx(content_box_before["x"], abs=1)
    assert content_box_open["width"] == pytest.approx(
        content_box_before["width"], abs=1
    )
    assert scrim_box["x"] == pytest.approx(workspace_box["x"], abs=1)
    assert scrim_box["y"] == pytest.approx(workspace_box["y"], abs=1)
    assert scrim_box["width"] == pytest.approx(workspace_box["width"], abs=1)
    assert scrim_box["height"] == pytest.approx(workspace_box["height"], abs=1)

    controlled_id = page.locator(".unit-button").first.get_attribute("aria-controls")
    assert controlled_id
    assert page.locator(f"#{controlled_id}").count() == 1
    page.locator("#rail-scrim").click()
    playwright.expect(page.locator("#rail-scrim")).to_be_hidden()
    assert "is-open" not in page.locator("#course-rail").get_attribute("class")
    assert page.locator("#rail-toggle").get_attribute("aria-expanded") == "false"

    launcher_box = page.locator("#ai-launcher").bounding_box()
    assert launcher_box is not None
    assert launcher_box["x"] + launcher_box["width"] <= 700
    assert launcher_box["y"] + launcher_box["height"] <= 600
    page.locator("#ai-launcher").click()
    assert page.locator("#ai-drawer").get_attribute("aria-hidden") == "false"

    assert errors == []


def test_dialog_blank_is_visible_and_future_card_cannot_award_xp(
    desktop_ui_url,
    browser_page,
):
    page, errors = browser_page
    dialog = {
        "type": "dialog_cloze",
        "title": {"uz": "Dialogni to‘ldiring"},
        "lines": [
            {"speaker": "A", "zh": "你好！", "blank": False},
            {"speaker": "B", "zh": "", "blank": True},
        ],
        "options": ["再见", "你好"],
        "correct_index": 1,
        "explanation": {"uz": "你好 — to‘g‘ri javob"},
    }
    future = {"type": "future_super_card", "payload": "must-not-skip"}
    _install_native_fixture(
        page,
        {1: _lesson_payload(1, [dialog, future])},
    )
    page.goto(desktop_ui_url, wait_until="networkidle")
    page.locator(".resume-card .primary-button").click()

    dialog_text = page.locator(".dialog-card").inner_text()
    assert "＿＿＿＿" in dialog_text
    assert "true" not in dialog_text.lower()
    page.locator(".lesson-option").nth(1).click()
    page.locator("#lesson-next").click()
    page.locator("#lesson-next").click()

    page.get_by_role(
        "heading",
        name="Bu mashq turi desktop ilovada hali qo‘llanmaydi.",
    ).wait_for()
    assert page.locator("#lesson-next").is_disabled()
    assert page.get_by_role("button", name="Qayta urinish").is_visible()
    assert page.evaluate("window.__COMPLETIONS.length") == 0
    assert errors == []


def test_preview_half_stops_without_completion(
    desktop_ui_url,
    browser_page,
):
    page, errors = browser_page
    cards = [
        {
            "type": "active_word",
            "word": {
                "zh": value,
                "pinyin": f"pinyin-{index}",
                "meaning": {"uz": f"ma’no-{index}"},
            },
        }
        for index, value in enumerate(("一", "二", "三", "四"), 1)
    ]
    _install_native_fixture(
        page,
        {1: _lesson_payload(1, cards, preview_half=True)},
    )
    page.goto(desktop_ui_url, wait_until="networkidle")
    page.locator(".resume-card .primary-button").click()
    page.locator("#lesson-next").click()
    page.locator("#lesson-next").click()

    page.get_by_role("heading", name="Bepul rejim").wait_for()
    assert "barcha darslarni shu ilovada" in page.locator("#lesson-content").inner_text()
    assert page.evaluate("window.__COMPLETIONS.length") == 0
    assert errors == []


def test_stale_lesson_response_cannot_replace_newer_lesson(
    desktop_ui_url,
    browser_page,
):
    page, errors = browser_page
    first = _lesson_payload(
        1,
        [
            {
                "type": "active_word",
                "word": {
                    "zh": "旧",
                    "pinyin": "jiù",
                    "meaning": {"uz": "eski"},
                },
            }
        ],
    )
    second = _lesson_payload(
        2,
        [
            {
                "type": "active_word",
                "word": {
                    "zh": "新",
                    "pinyin": "xīn",
                    "meaning": {"uz": "yangi"},
                },
            }
        ],
    )
    _install_native_fixture(page, {1: first, 2: second}, delays={1: 350, 2: 10})
    page.goto(desktop_ui_url, wait_until="networkidle")

    page.locator("#show-course").click()
    lesson_nodes = page.locator(".lesson-node")
    lesson_nodes.nth(0).click()
    page.locator("#close-lesson").click()
    lesson_nodes.nth(1).click()
    page.locator(".hanzi-hero strong").wait_for()
    page.wait_for_timeout(450)

    assert page.locator(".hanzi-hero strong").inner_text() == "新"
    page.locator("#lesson-next").click()
    page.get_by_role("heading", name="Dars saqlandi").wait_for()
    assert page.evaluate("window.__COMPLETIONS[0].lessonOrder") == 2
    assert errors == []


def test_update_banner_is_localized_and_install_is_explicit(
    desktop_ui_url,
    browser_page,
):
    page, errors = browser_page
    page.set_viewport_size({"width": 720, "height": 560})
    _install_native_fixture(
        page,
        {
            1: _lesson_payload(
                1,
                [
                    {
                        "type": "active_word",
                        "word": {
                            "zh": "新",
                            "pinyin": "xīn",
                            "meaning": {"uz": "yangi"},
                        },
                    }
                ],
            )
        },
        update={
            "available": True,
            "currentVersion": "0.1.0",
            "version": "0.2.0",
            "notes": "Kurs oqimi va barqarorlik yangilandi.",
        },
        update_install_delay=250,
    )
    page.goto(desktop_ui_url, wait_until="networkidle")
    page.locator("#workspace").wait_for(state="visible")
    page.locator("#update-banner").wait_for(state="visible")

    assert page.locator("#update-title").inner_text() == "Yangi versiya: 0.2.0"
    assert page.evaluate("window.__UPDATE_CHECKS") == 1
    assert page.evaluate("window.__UPDATE_INSTALLS") == 0
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

    banner_box = page.locator("#update-banner").bounding_box()
    action_box = page.locator("#update-action").bounding_box()
    assert banner_box is not None and action_box is not None
    assert action_box["x"] + action_box["width"] <= 720
    assert action_box["y"] + action_box["height"] <= 560

    page.locator("#rail-toggle").click()
    page.locator("#show-profile").click()
    page.get_by_role("button", name="Русский", exact=True).click()
    assert page.locator("#update-title").inner_text() == "Доступна версия 0.2.0"
    page.get_by_role("button", name="Тоҷикӣ", exact=True).click()
    assert page.locator("#update-title").inner_text() == "Версияи 0.2.0 дастрас аст"

    page.locator("#update-action").focus()
    page.keyboard.press("Enter")
    assert page.locator("#update-action").is_disabled()
    assert page.locator("#update-status").get_attribute("aria-busy") == "true"
    assert page.evaluate("window.__UPDATE_INSTALLS") == 1
    page.locator("#update-progress").wait_for(state="visible")
    assert "50%" in page.locator("#update-progress-detail").inner_text()
    page.locator("#update-title").wait_for()
    page.wait_for_function(
        "document.querySelector('#update-title')?.textContent === "
        "'Навсозӣ омода аст'"
    )
    assert errors == []


def test_update_retry_and_lesson_restart_guard(
    desktop_ui_url,
    browser_page,
):
    page, errors = browser_page
    _install_native_fixture(
        page,
        {
            1: _lesson_payload(
                1,
                [
                    {
                        "type": "active_word",
                        "word": {
                            "zh": "安全",
                            "pinyin": "ānquán",
                            "meaning": {"uz": "xavfsiz"},
                        },
                    }
                ],
            )
        },
        update={
            "available": True,
            "currentVersion": "0.1.0",
            "version": "0.2.0",
        },
        update_check_failures=1,
        update_install_error=True,
    )
    page.goto(desktop_ui_url, wait_until="networkidle")
    page.locator("#workspace").wait_for(state="visible")
    page.locator("#update-banner").wait_for(state="visible")
    assert page.locator("#update-title").inner_text() == (
        "Yangilanishni tekshirib bo‘lmadi"
    )

    page.locator("#update-action").click()
    page.wait_for_function(
        "document.querySelector('#update-title')?.textContent === "
        "'Yangi versiya: 0.2.0'"
    )
    assert page.evaluate("window.__UPDATE_CHECKS") == 2

    page.locator(".resume-card .primary-button").click()
    page.locator("#lesson-layer").wait_for(state="visible")
    page.locator("#update-action").evaluate("node => node.click()")
    assert page.evaluate("window.__UPDATE_INSTALLS") == 0
    assert "Avval darsni" in page.locator("#toast").inner_text()

    page.locator("#close-lesson").click()
    page.locator("#update-action").click()
    page.wait_for_function(
        "document.querySelector('#update-title')?.textContent === "
        "'Yangilanish o‘rnatilmadi'"
    )
    assert page.evaluate("window.__UPDATE_INSTALLS") == 1

    page.evaluate("window.__DESKTOP_FIXTURE__.updateInstallError = false")
    page.locator("#update-action").click()
    page.wait_for_function(
        "document.querySelector('#update-title')?.textContent === "
        "'Yangilanish tayyor'"
    )
    assert page.evaluate("window.__UPDATE_INSTALLS") == 2
    assert errors == []


def test_update_auto_installs_when_workspace_is_idle(
    desktop_ui_url,
    browser_page,
):
    page, errors = browser_page
    _install_native_fixture(
        page,
        {
            1: _lesson_payload(
                1,
                [
                    {
                        "type": "active_word",
                        "word": {
                            "zh": "更新",
                            "pinyin": "gēngxīn",
                            "meaning": {"uz": "yangilash"},
                        },
                    }
                ],
            )
        },
        update={
            "available": True,
            "currentVersion": "0.1.0",
            "version": "0.2.0",
        },
    )
    page.goto(desktop_ui_url, wait_until="networkidle")
    page.locator("#workspace").wait_for(state="visible")
    page.wait_for_function("window.__UPDATE_INSTALLS === 1", timeout=8_500)
    page.wait_for_function(
        "document.querySelector('#update-title')?.textContent === "
        "'Yangilanish tayyor'"
    )
    assert errors == []
