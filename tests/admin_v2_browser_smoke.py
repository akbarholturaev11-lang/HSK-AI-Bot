"""Offline Admin V2 browser smoke; never performs production/admin mutations."""
import argparse
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/admin-v2-ui")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(Path(".").resolve()), **kw)

        def log_message(self, *a):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for width, height in [(1440, 900), (390, 844), (320, 700)]:
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.route("https://telegram.org/js/telegram-web-app.js", lambda route: route.fulfill(
                    status=200, content_type="application/javascript",
                    body="window.Telegram={WebApp:{initData:'invalid-demo-session',ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){},onEvent(){}}};"
                ))
                page.route("**/api/admin-miniapp/**", lambda route: route.fulfill(
                    status=403, content_type="application/json",
                    body='{"ok":false,"error":"admin_only"}'
                ))
                page.goto(f"http://127.0.0.1:{server.server_port}/app/static/admin.html", wait_until="domcontentloaded")
                page.wait_for_timeout(250)
                assert page.locator("#app").evaluate("(el) => el.hidden"), "Unauthenticated admin shell is not hidden"
                if width < 760:
                    assert not page.locator(".mobile-nav").is_visible(), "Unauthenticated mobile navigation is visible"

                # Explicit UI-only presentation fixture; no live account/data access.
                page.evaluate("""() => {
                    document.querySelector('#loading').hidden = true;
                    document.querySelector('#app').hidden = false;
                    const blocks = [['Foydalanuvchilar','1 480'],['Faol foydalanuvchilar','317'],['Pro obunalar','42'],['Tushum','825 TJS']];
                    document.querySelector('#summaryGrid').innerHTML = blocks.map(x=>`<article class="stat"><div class="lab">${x[0]}</div><div class="val">${x[1]}</div><div class="sub">Demo — real emas</div></article>`).join('');
                    document.querySelector('#queueList').innerHTML = '<div class="srow"><h3>To‘lovni tekshirish</h3></div><div class="srow"><h3>Pro statusini ko‘rish</h3></div>';
                    document.querySelector('#financeQuick').innerHTML = '<div class="stat"><div class="lab">Daromad</div><div class="val">—</div></div>';
                }""")
                assert page.locator("main .view").count() == 7, "7 views expected"
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Horizontal overflow"
                page.screenshot(path=str(output / f"admin-v2-dashboard-{width}.png"), full_page=True)
                if width >= 860:
                    assert page.locator("#tabs [data-tab]").count() == 7
                    assert page.evaluate("getComputedStyle(document.body).overflowY !== 'hidden'"), "Desktop scroll locked"
                    page.locator('#tabs [data-tab="marketing"]').click()
                else:
                    assert page.locator(".mobile-nav [data-tab]").count() == 5
                    page.locator('.mobile-nav [data-tab="menu"]').click()
                    page.locator('#drawer.open [data-tab="marketing"]').click()
                assert page.locator("#marketing").evaluate("(el) => el.classList.contains('active')")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Marketing overflow"
                page.screenshot(path=str(output / f"admin-v2-marketing-{width}.png"), full_page=True)
                assert not errors, "JS errors: " + str(errors)
                results.append({"viewport": width, "passed": True})
                context.close()
            # Approved standalone prototype as a persistent visual reference.
            baseline_context = browser.new_context(viewport={"width": 1440, "height": 900})
            baseline = baseline_context.new_page()
            baseline.goto(
                f"http://127.0.0.1:{server.server_port}/tests/fixtures/admin_v2_approved_prototype.html",
                wait_until="domcontentloaded"
            )
            baseline.wait_for_timeout(250)
            baseline.screenshot(path=str(output / "approved-prototype-1440.png"), full_page=True)
            baseline_context.close()

            # Compare the stable left-navigation region, not data-dependent KPI values.
            from PIL import Image, ImageChops, ImageStat
            current = Image.open(output / "admin-v2-dashboard-1440.png").convert("RGB").crop((0, 0, 258, 560))
            approved = Image.open(output / "approved-prototype-1440.png").convert("RGB").crop((0, 0, 258, 560))
            metric = sum(ImageStat.Stat(ImageChops.difference(current, approved)).mean) / 3
            print(f"Visual navigation mean pixel difference (0=identical): {metric:.2f}/255")
            # This metric is diagnostic until both live and demo content states are normalized.
            browser.close()
    finally:
        server.shutdown()
    print(json.dumps({"ok": True, "results": results}))


if __name__ == "__main__":
    main()
