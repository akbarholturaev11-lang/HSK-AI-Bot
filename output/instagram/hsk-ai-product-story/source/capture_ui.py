from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Route, sync_playwright


ROOT = Path(__file__).resolve().parents[4]
STATIC_ROOT = ROOT / "app" / "static"
OUTPUT_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = OUTPUT_ROOT / "assets"
BASE_URL = "http://hsk-ai.local"


SUBSCRIPTION_OVERVIEW = {
    "ok": True,
    "language": "tj",
    "mode": "subscription",
    "support_url": "",
    "pending_payment": None,
    "offer": None,
    "discount": None,
    "payment_details": "CARD: •••• •••• •••• 0000",
    "payment_details_configured": True,
    "card_countries": ["tj", "uz", "ru", "other"],
    "prices": {
        "visa": {
            "10_days": {
                "base_amount": 29,
                "final_amount": 29,
                "currency": "TJS",
                "discount_applied": False,
                "discount_percent": 0,
            },
            "1_month": {
                "base_amount": 89,
                "final_amount": 89,
                "currency": "TJS",
                "discount_applied": False,
                "discount_percent": 0,
            },
            "3_months": {
                "base_amount": 179,
                "final_amount": 179,
                "currency": "TJS",
                "discount_applied": False,
                "discount_percent": 0,
            },
        }
    },
}

SUBSCRIPTION_QUOTE = {
    "ok": True,
    "quote": {
        "plan_type": "1_month",
        "payment_method": "visa",
        "card_country": "tj",
        "base_amount": 89,
        "base_currency": "TJS",
        "final_amount": 89,
        "final_currency": "TJS",
        "pay_amount": 89,
        "pay_currency": "TJS",
        "pay_base_amount": 89,
        "pay_base_currency": "TJS",
        "exchange_rate": "1 TJS = 1 TJS",
        "discount_applied": False,
        "discount_percent": 0,
        "discount_source": "none",
        "payment_details": "CARD: •••• •••• •••• 0000",
    },
}


def json_response(route: Route, payload: dict, status: int = 200) -> None:
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload, ensure_ascii=False),
    )


def route_static_files(page, language: str) -> None:
    static_root = STATIC_ROOT.resolve()

    def handle_static(route: Route) -> None:
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
            ".mp3": "audio/mpeg",
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
                "window.Telegram={WebApp:{initData:'query_id=instagram-preview',"
                "initDataUnsafe:{user:{id:0}},platform:'ios',"
                "ready(){},expand(){},close(){},setHeaderColor(){},setBackgroundColor(){},"
                "HapticFeedback:{impactOccurred(){},notificationOccurred(){},selectionChanged(){}},"
                "openTelegramLink(){},openLink(){},showConfirm(){},"
                "BackButton:{show(){},hide(){},onClick(){}}}};"
            ),
        ),
    )

    # The real UI uses Tabler icon classes. Network access is intentionally not
    # required for this deterministic preview, so keep the request harmless.
    page.route(
        re.compile(r"^https://cdnjs\.cloudflare\.com/.*"),
        lambda route: route.fulfill(status=200, content_type="text/css", body=""),
    )

    data = json.loads(
        (STATIC_ROOT / "course_v3_data" / "hsk1.json").read_text(encoding="utf-8")
    )
    data["authenticated"] = True
    data["level"] = "hsk1"
    data["progress"] = {
        "xp": 0,
        "streak": 0,
        "longest_streak": 0,
        "weekly_xp": 0,
        "completed": 0,
        "daily_xp": 0,
        "league": "Bronze",
        "week_activity_dates": [],
    }
    data["user"] = {
        "name": {"uz": "O‘quvchi", "ru": "Ученик", "tj": "Донишҷӯ"}[language],
        "avatar": "学",
        "language": language,
        "is_paid": False,
        "referral_code": "",
    }
    data["notify"] = {"enabled": True}
    data["admin_contact"] = ""

    page.route(
        re.compile(r".*/api/v3/map(\?.*)?$"),
        lambda route: json_response(route, data),
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
        "**/api/subscription-miniapp/overview",
        lambda route: json_response(route, {"ok": False, "error": "preview_unavailable"}),
    )
    page.route(
        re.compile(r".*/api/miniapp/(event|gamification)(\?.*)?$"),
        lambda route: json_response(route, {"ok": True, "users": [], "meta": {}}),
    )
    page.route(
        re.compile(r".*/api/v3/(notify|clientlog)(\?.*)?$"),
        lambda route: json_response(route, {"ok": True}),
    )


def add_preview_state(page) -> None:
    page.add_init_script(
        """
        localStorage.setItem('hsk_v3_onb', '1');
        localStorage.setItem('hsk_v3_level', 'hsk1');
        localStorage.setItem('hsk_v3_pinyin', 'all');
        """
    )


def capture(
    page,
    name: str,
    url: str,
    ready_selector: str,
    *,
    hide_selectors: tuple[str, ...] = (),
    capture_selector: str | None = None,
) -> None:
    page.goto(f"{BASE_URL}{url}", wait_until="networkidle")
    page.locator(ready_selector).wait_for(state="visible")
    page.wait_for_timeout(500)
    for selector in hide_selectors:
        page.locator(selector).evaluate("element => element.remove()")
    output_path = str(ASSET_ROOT / f"ui-{name}.png")
    if capture_selector:
        page.locator(capture_selector).screenshot(path=output_path)
    else:
        page.screenshot(path=output_path, full_page=False)


def capture_panda_assets(page) -> None:
    for mood in ("happy", "talk", "celebrate"):
        page.evaluate(
            """
            mood => {
              const markup = pandaChar(mood, {anim: false});
              document.documentElement.style.background = "transparent";
              document.body.style.cssText = "margin:0;background:transparent;overflow:hidden";
              document.body.innerHTML = `<div id="story-panda" style="width:220px;height:234px">${markup}</div>`;
            }
            """,
            mood,
        )
        page.locator("#story-panda").screenshot(
            path=str(ASSET_ROOT / f"panda-{mood}.png"),
            omit_background=True,
        )


def add_subscription_routes(page) -> None:
    page.unroute("**/api/subscription-miniapp/overview")
    page.route(
        "**/api/subscription-miniapp/overview",
        lambda route: json_response(route, SUBSCRIPTION_OVERVIEW),
    )
    page.route(
        "**/api/subscription-miniapp/quote",
        lambda route: json_response(route, SUBSCRIPTION_QUOTE),
    )
    page.route(
        "**/api/subscription-miniapp/event",
        lambda route: json_response(route, {"ok": True}),
    )
    page.route(
        "**/api/subscription-miniapp/submit",
        lambda route: json_response(
            route,
            {"ok": True, "payment_id": 123, "status": "pending"},
        ),
    )


def capture_subscription(page, language: str) -> None:
    add_subscription_routes(page)
    page.goto(
        f"{BASE_URL}/subscription.html?lang={language}&mode=subscription&source=menu_subscription",
        wait_until="networkidle",
    )
    page.locator('section[data-screen="start"].active').wait_for(state="visible")
    page.locator('[data-plan="1_month"]').click()
    page.locator('[data-card-method="tj"]').click()
    page.add_style_tag(
        content="""
        .kicker, .steps, .tv, .value-copy, .top-actions { display: none !important; }
        .app { padding-top: 18px !important; }
        .top { margin-bottom: 8px !important; }
        """
    )
    page.wait_for_timeout(250)
    page.screenshot(
        path=str(ASSET_ROOT / f"ui-{language}-subscription-start.png"),
        full_page=False,
    )

    page.locator("#nextBtn").click()
    page.locator('section[data-screen="pay"].active').wait_for(state="visible")
    page.locator("#amountValue").wait_for(state="visible")
    page.add_style_tag(
        content="""
        .top, .meta, .detail-hint { display: none !important; }
        .hero { padding-top: 18px !important; }
        """
    )
    page.locator("#receiptInput").set_input_files(
        {
            "name": "payment.png",
            "mimeType": "image/png",
            "buffer": base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
        }
    )
    page.locator("#uploadBox.ready").wait_for(state="visible")
    page.wait_for_timeout(250)
    page.locator('section[data-screen="pay"] .hero').screenshot(
        path=str(ASSET_ROOT / f"ui-{language}-subscription-pay.png"),
    )

    page.locator("#nextBtn").click()
    page.locator('section[data-screen="done"].active').wait_for(state="visible")
    page.locator("#doneTitle").wait_for(state="visible")
    page.wait_for_timeout(250)
    page.screenshot(
        path=str(ASSET_ROOT / f"ui-{language}-subscription-done.png"),
        full_page=False,
    )


def main(language: str) -> None:
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            locale={"uz": "uz-UZ", "ru": "ru-RU", "tj": "tg-TJ"}[language],
        )
        page = context.new_page()
        route_static_files(page, language)
        add_preview_state(page)

        capture(
            page,
            f"{language}-course",
            f"/course-v3.html?lang={language}&level=hsk1&onboarded=1",
            "#s-course.on",
        )
        capture_panda_assets(page)
        capture(
            page,
            f"{language}-lesson",
            f"/course-v3.html?lang={language}&level=hsk1&lesson=1&autostart=1&onboarded=1",
            "#flow.on",
        )
        capture(
            page,
            f"{language}-voice",
            f"/course-v3.html?lang={language}&level=hsk1&tab=voice&onboarded=1",
            "#s-voice.on",
            capture_selector="#s-voice .voicebox",
        )
        capture(
            page,
            f"{language}-practice",
            f"/course-v3.html?lang={language}&level=hsk1&tab=mashq&onboarded=1",
            "#s-mashq.on",
        )
        capture(
            page,
            f"{language}-profile",
            f"/course-v3.html?lang={language}&level=hsk1&tab=profile&onboarded=1",
            "#s-profile.on",
            hide_selectors=("#pomp-desktop-profile-root",),
        )
        capture_subscription(page, language)

        context.close()
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=("uz", "ru", "tj"), default="tj")
    main(parser.parse_args().lang)
