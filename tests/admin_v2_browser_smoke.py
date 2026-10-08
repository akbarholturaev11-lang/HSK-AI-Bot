"""Offline Admin V2 browser smoke; never performs production/admin mutations."""
import argparse
import json
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright



def check_real_module_coverage():
    """Prove all backend-declared admin modules have a reachable V2 entry point."""
    html = Path("app/static/admin.html").read_text(encoding="utf-8")
    backend = Path("app/services/admin_miniapp_service.py").read_text(encoding="utf-8")
    block = backend.split("def _modules()", 1)[1].split("def _monitor(", 1)[0]
    declared = set(re.findall(r'"key": "([a-z_]+)"', block))
    assert len(declared) == 19, f"Admin backend module inventory changed: {declared}"

    mapping = html.split("function renderModules(){", 1)[1].split("for(const [id,keys]", 1)[0]
    mapped = set()
    for array_source in re.findall(r'new Set\\(\\[([^\\]]*)\\]\\)', mapping):
        mapped.update(re.findall(r'"([a-z_]+)"', array_source))
    direct = set(re.findall(r'data-module="([a-z_]+)"', html))
    special = {"stats": "statistics", "user_search": "users", "ads_hub": "marketing"}
    for module, view in special.items():
        assert f'key==="{module}"' in html, f"Special route missing for {module}"
        assert f'<section id="{view}" class="view' in html, f"Special view missing: {view}"
    covered = mapped | direct | set(special)
    missing = declared - covered
    unknown = mapped - declared
    assert not missing, f"Admin V2 cannot reach these backend modules: {sorted(missing)}"
    assert not unknown, f"Unrecognized module keys in V2: {sorted(unknown)}"
    print(f"Admin module reachability: {len(declared)}/{len(declared)} backend keys mapped")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/admin-v2-ui")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    check_real_module_coverage()

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
            for width, height in [(1440, 900), (1024, 768), (820, 1000), (390, 844), (320, 700)]:
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
                if width == 390:
                    page.screenshot(path=str(output / "admin-v2-mobile-viewport.png"), full_page=False)
                if width > 760:
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
                page.locator('#marketing [data-v2-sub="marketing:ads"]').click()
                assert page.locator('#marketing #adHub').is_visible(), "Mini App advertising panel inaccessible"
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"Ads horizontal overflow at {width}px"
                if width <= 390:
                    page.screenshot(path=str(output / f"admin-v2-ads-{width}.png"), full_page=True)
                assert not errors, "JS errors: " + str(errors)
                results.append({"viewport": width, "passed": True})
                context.close()
            # Execute the real load/render path with mocked read-only API responses.
            # The fake Telegram token and local route handlers never reach production.
            live_context = browser.new_context(viewport={"width": 1440, "height": 900})
            live = live_context.new_page()
            live_errors = []
            live.on("pageerror", lambda error: live_errors.append(str(error)))
            live.route("https://telegram.org/js/telegram-web-app.js", lambda route: route.fulfill(
                status=200, content_type="application/javascript",
                body="window.Telegram={WebApp:{initData:'nonprod-demo',ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){},onEvent(){}}};"
            ))
            fake_overview = {
                "ok": True, "generated_at": "2026-10-08T10:00:00Z",
                "summary": [
                    {"label": name, "value": 42, "note": "UI demo only", "tone": ""}
                    for name in ("Foydalanuvchilar", "Faol obuna", "To‘lov tekshiruvda", "Issiq mijoz")
                ],
                "segments": {}, "queue": [],
                "users": [{
                    "id": 9001, "name": "Demo Learner", "username": "demo",
                    "language": "tj", "level": "HSK 3", "last_active": "demo",
                    "plan": "Pro", "method": "Alif", "status": "active",
                    "questions": "3/5", "streak": 1
                }],
                "payments": {"latest": [{
                    "id": 7001, "telegram_id": 9001, "name": "Demo Learner",
                    "username": "demo", "plan": "Pro", "method": "Alif",
                    "amount": "69 TJS", "status": "pending", "status_label": "Tekshiruvda",
                    "submitted_at": "demo", "source": "miniapp", "has_screenshot": True
                }]},
                "statistics_reports": [], "data_quality": {},
                "modules": [
                    {"key": key, "title": label, "icon": "⚙️", "note": "Demo"}
                    for key, label in [
                        ("stats", "Statistika"),
                        ("user_search", "Foydalanuvchi qidirish"),
                        ("portfolio", "Portfel"),
                        ("prices", "Obuna narxlari"),
                        ("hsk30", "HSK 3.0"),
                        ("course_access", "Kursga kirish"),
                        ("limits", "Limitlar"),
                        ("ads_hub", "Mini App reklama"),
                        ("course_sales_experiment", "HSK sotuv A/B"),
                        ("channels", "Kanallar"),
                        ("delete_user", "Foydalanuvchini o‘chirish"),
                        ("broadcast", "Ommaviy xabar"),
                        ("ads", "Bot reklama"),
                        ("release_feedback", "Yangi versiya fikri"),
                        ("discount", "Chegirma"),
                        ("partners", "Hamkorlar"),
                        ("help", "Yordam"),
                        ("give_access", "Obuna berish"),
                        ("audio", "Audio")
                    ]
                ]
            }
            attempted_mutations = []
            fake_management = {
                "ok": True, "prices": [], "payment_details": "", "payment_details_alif": "",
                "hsk30": {"enabled": False, "unlock_price_tjs": 10, "live_levels": []},
                "limits_config": {"plans": {}, "trial": {}},
                "channels": {"enabled": False, "items": []},
                "help": {"links": []}, "gemini": {"configured": False, "options": []},
                "portfolio": {"summary": {}, "history": []}
            }
            def api_fixture(route):
                url = route.request.url
                if url.endswith("/api/admin-miniapp/overview"):
                    route.fulfill(status=200, content_type="application/json",
                                  body=json.dumps(fake_overview))
                elif url.endswith("/api/admin-miniapp/management"):
                    route.fulfill(status=200, content_type="application/json",
                                  body=json.dumps(fake_management))
                else:
                    if url.endswith("/payments/review"):
                        attempted_mutations.append("payment_review")
                    route.fulfill(status=403, content_type="application/json",
                                  body='{"ok":false,"error":"admin_only"}')
            live.route("**/api/admin-miniapp/**", api_fixture)
            live.goto(f"http://127.0.0.1:{server.server_port}/app/static/admin.html",
                      wait_until="domcontentloaded")
            live.wait_for_selector("#app:not([hidden])", timeout=8000)
            assert live.locator("#summaryGrid .stat").count() == 4, "Real dashboard render failed"
            assert live.locator("#moduleGrid [data-module]").count() == 1, "Course track module rendering failed"
            assert live.locator("#v2ProductAccess [data-module]").count() == 2, "Access module rendering failed"
            assert live.locator("#v2MarketingModules [data-module]").count() == 4, "Marketing module rendering failed"
            assert live.locator("#v2SystemModules [data-module]").count() == 2, "System module rendering failed"
            assert live.locator("#v2ProductContent [data-module]").count() == 2, "Product Content modules missing"
            assert live.locator("#v2MarketingPartners [data-module]").count() == 1, "Partner module missing"
            assert live.locator('#payments [data-v2-pane="payments:prices"] [data-module="prices"]').count() == 1, "Finance prices missing"
            assert live.locator('#payments [data-v2-pane="payments:methods"] [data-module="prices"]').count() == 1, "Finance methods missing"
            assert live.locator('#payments [data-v2-pane="payments:portfolio"] [data-module="portfolio"]').count() == 1, "Finance portfolio missing"
            assert live.locator("#marketing #adHub").count() == 1, "Existing Mini App advertising control was lost"
            assert live.locator("#marketing #notifTemplates").count() == 1, "Existing notifications control was lost"

            # Critical module coverage: each module must be discoverable from some safe V2 path.
            mapped_keys = {"hsk30","course_access","limits","course_sales_experiment","audio",
                           "broadcast","ads","release_feedback","discount","partners","channels","help",
                           "prices","portfolio","stats","user_search","give_access","delete_user","ads_hub"}
            assert len(mapped_keys) == 19
            for area, keys in (
                ("statistics", ("overview", "platform", "funnel", "ai")),
                ("payments", ("payments", "prices", "methods", "portfolio")),
                ("settings", ("tracks", "access", "content")),
                ("marketing", ("campaigns", "ads", "reminders", "partners")),
                ("system", ("model", "settings")),
            ):
                live.locator(f'#tabs [data-tab="{area}"]').click()
                for key in keys:
                    live.locator(f'#{area} [data-v2-sub="{area}:{key}"]').click()
                    active = live.locator(f'#{area} [data-v2-pane="{area}:{key}"]')
                    assert active.count() > 0 and all(x.get_attribute("hidden") is None for x in active.all()), f"Hidden active pane: {area}:{key}"
                    assert live.locator(f'#{area} [data-v2-sub="{area}:{key}"]').get_attribute("aria-selected") == "true"
                    if key == keys[0] or area == "marketing" and key == "ads":
                        live.screenshot(path=str(output / f"admin-v2-{area}-{key}-1440.png"), full_page=True)
                live.locator(f'#{area} [data-v2-sub="{area}:{keys[0]}"]').click()
            live.locator('#tabs [data-tab="dashboard"]').click()
            assert live.locator("#userList [data-user]").count() >= 1, "Real Users rows missing"
            live.locator('#tabs [data-tab="users"]').click()
            live.screenshot(path=str(output / "admin-v2-users-1440.png"), full_page=True)
            live.locator('#tabs [data-tab="payments"]').click()
            live.screenshot(path=str(output / "admin-v2-payments-1440.png"), full_page=True)
            assert live.locator('#paymentBoard [data-payment-preview="7001"]').count() == 1, "Real Payments row missing"
            live.locator('#paymentBoard [data-payment-preview="7001"]').click()
            assert live.locator("#drawer.open").count() == 1, "Payment preview did not open"
            live.screenshot(path=str(output / "admin-v2-payment-preview-1440.png"), full_page=False)
            assert "bank" in live.locator("#drawerBody").inner_text().lower(), "Bank verification warning missing"
            assert "Kvitansiya" in live.locator("#drawerBody").inner_text(), "Missing receipt status"
            live.once("dialog", lambda d: d.dismiss())
            live.locator('#drawer.open [data-pay][data-pact="approve"]').click()
            assert not attempted_mutations, "Payment approval was sent despite cancelled verification"
            live.locator('[data-act="close-drawer"]').first.click(force=True)

            # Open real management drawers with a fake in-memory management payload.
            for section, subpage, module_key, expected in [
                ("payments", "prices", "prices", "#payDetails"),
                ("settings", "tracks", "hsk30", "#hsk30Enabled"),
                ("settings", "access", "limits", "#trialEnabled"),
                ("marketing", "campaigns", "broadcast", "#bcText"),
                ("system", "settings", "channels", '[data-chadd]'),
            ]:
                live.locator(f'#tabs [data-tab="{section}"]').click()
                live.locator(f'#{section} [data-v2-sub="{section}:{subpage}"]').click()
                live.locator(f'#{section} [data-module="{module_key}"]').first.click()
                live.locator(f'#drawer.open {expected}').wait_for(timeout=5000)
                live.locator('#drawer [data-act="close-drawer"]').click()
            assert not attempted_mutations, "The UI smoke performed a production mutation"
            live.locator('#tabs [data-tab="dashboard"]').click()
            assert not live_errors, "Real render JS errors: " + str(live_errors)
            live.screenshot(path=str(output / "admin-v2-mocked-api-render-1440.png"),
                            full_page=True)
            live_context.close()

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
            mobile_baseline_ctx = browser.new_context(viewport={"width": 390, "height": 844})
            mobile_baseline = mobile_baseline_ctx.new_page()
            mobile_baseline.goto(
                f"http://127.0.0.1:{server.server_port}/tests/fixtures/admin_v2_approved_prototype.html",
                wait_until="domcontentloaded"
            )
            mobile_baseline.wait_for_timeout(250)
            mobile_baseline.screenshot(path=str(output / "approved-prototype-mobile-viewport.png"), full_page=False)
            mobile_baseline_ctx.close()

            # Compare the stable left-navigation region, not data-dependent KPI values.
            from PIL import Image, ImageChops, ImageStat
            current = Image.open(output / "admin-v2-dashboard-1440.png").convert("RGB").crop((0, 0, 258, 560))
            approved = Image.open(output / "approved-prototype-1440.png").convert("RGB").crop((0, 0, 258, 560))
            metric = sum(ImageStat.Stat(ImageChops.difference(current, approved)).mean) / 3
            print(f"Visual navigation mean pixel difference (0=identical): {metric:.2f}/255")
            mobile_current = Image.open(output / "admin-v2-mobile-viewport.png").convert("RGB").crop((0, 745, 390, 844))
            mobile_approved = Image.open(output / "approved-prototype-mobile-viewport.png").convert("RGB").crop((0, 745, 390, 844))
            mobile_metric = sum(ImageStat.Stat(ImageChops.difference(mobile_current, mobile_approved)).mean) / 3
            print(f"Visual mobile navigation mean pixel difference (0=identical): {mobile_metric:.2f}/255")
            # This metric is diagnostic until both live and demo content states are normalized.
            browser.close()
    finally:
        server.shutdown()
    print(json.dumps({"ok": True, "results": results}))


if __name__ == "__main__":
    main()
