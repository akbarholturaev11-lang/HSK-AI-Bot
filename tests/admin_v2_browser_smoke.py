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
    declared = set(re.findall(r'"key": "([a-z0-9_]+)"', block))
    assert len(declared) == 19, f"Admin backend module inventory changed: {declared}"

    mapping = html.split("function renderModules(){", 1)[1].split("for(const [id,keys]", 1)[0]
    mapped = set()
    for array_source in mapping.split("new Set([")[1:]:
        members = array_source.split("])", 1)[0]
        mapped.update(re.findall(r'"([a-z0-9_]+)"', members))
    direct = set(re.findall(r'data-module="([a-z0-9_]+)"', html))
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


def check_css_architecture():
    """Keep only one authoritative theme token definition and no orphan V1/demo styles."""
    html = Path("app/static/admin.html").read_text(encoding="utf-8")
    css = html.split("<style>", 1)[1].split("</style>", 1)[0]
    roots = re.findall(r":root\s*\{([^{}]*)\}", css)
    assert len(roots) >= 2, "Admin theme root not found"
    tokens = re.findall(r"(--[a-z0-9-]+)\s*:", "\n".join(roots))
    duplicate_tokens = sorted({name for name in tokens if tokens.count(name) > 1})
    assert not duplicate_tokens, f"Conflicting Admin theme tokens: {duplicate_tokens}"

    obsolete = ("topbar-inner", "drawer-head", "drawer-body", "drawer-footer",
                "demo-chip", "metric", "chart-svg", "chart-plot", "panel-header",
                "panel-body", "kpi-line", "kpi-list", "demo-strip",
                "preview-bubble", "filter-tabs", "option-tile", "pboard")
    for cls in ("tabs", *obsolete):
        selector = r"\." + re.escape(cls) + r"(?![a-zA-Z0-9_-])"
        assert not re.search(selector, css), f"Unused V1/demo CSS returned: .{cls}"
    assert "#drawer.open{transform:translateX(0)}" in css
    assert "#drawer.open{transform:translateY(0)}" in css
    print(f"Admin CSS architecture: {len(tokens)} unique theme tokens; orphan prototype components absent")




def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/admin-v2-ui")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    check_real_module_coverage()
    check_css_architecture()

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
            live.on("console", lambda msg: live_errors.append(msg.text) if msg.type == "error" and "Admin panel render xatosi" in msg.text else None)
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
                "statistics_reports": [
                    {
                        "key": period, "note": "UI demo period",
                        "metrics": {
                            "user_count": 100, "active_users": 37,
                            "approved_payment_users": 5, "pending_payments": 1,
                        },
                        "course": {
                            "opened_users": 30, "lesson_users": 20,
                            "completed_users": 11,
                        },
                    } for period in ("weekly", "monthly", "all_time")
                ], "data_quality": {},
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
            fake_finance = {
                "ok": True,
                "periods": [
                    {
                        "key": period, "note": "UI demo", "range_label": "Demo period",
                        "unit": {"approved_count": 9, "arppu_text": "$8.00"},
                        "finance": {
                            "revenue_text": "$73.00", "ai_cost_text": "$5.00",
                            "expense_text": "$7.00", "net_text": "$61.00",
                            "ai_share_pct": 6.8, "margin_pct": 83.6,
                            "net_positive": True,
                        },
                        "client_business": {"rows": [
                            {"key": "miniapp", "entry_users": 24, "paying_users": 4,
                             "payments": 5, "revenue_text": "$40.00"},
                            {"key": "android", "entry_users": 12, "paying_users": 2,
                             "payments": 2, "revenue_text": "$16.00"},
                            {"key": "desktop", "entry_users": 8, "paying_users": 1,
                             "payments": 1, "revenue_text": "$8.00"},
                            {"key": "unknown", "entry_users": 0, "paying_users": 0,
                             "payments": 1, "revenue_text": "$9.00"},
                        ]},
                    } for period in ("weekly", "monthly", "all_time")
                ]
            }
            # Previous Admin had twelve independently useful analytics reports.
            # Keep the executive four-tab summary short, but exercise every
            # detailed report against real renderers and mocked read-only APIs.
            for period in fake_overview["statistics_reports"]:
                period["cards"] = [
                    {"label":"Savollar", "value":34, "note":"So‘rovlar", "tone":"info"}
                ]
                period["text"] = "Batafsil server hisobot — test."
                period["advanced"] = {
                    "explain":"Darsga qaytish va to‘lovni tugatish",
                    "cards":[{"label":"Retention", "value":"31%", "note":"Test", "tone":"info"}],
                    "payment":{"funnel":{"steps":[
                        {"label":"Paywall ochildi", "users":9},
                        {"label":"To‘lov boshladi", "users":5}
                    ],"abandon_step":"To‘lov boshladi","abandon_count":4,"abandon_rate":44}},
                    "feature_adoption":{"rows":[{"label":"Voice","paid":3,"free":2,
                       "paid_rate":30,"free_rate":20}],"paid_denominator":10,"free_denominator":10}
                }
            fake_overview["client_devices"] = {"miniapp_users_total":21,"native_users_total":8}
            fake_overview["data_quality"] = {"rows":[{"label":"To‘lov","status":"ok","last_at":"2026-10-09"}]}
            for period in fake_finance["periods"]:
                period["unit"].update({"approved_count":9,"arpu_text":"$0.73",
                    "arpu_users":100,"avg_check_text":"$8.11","paying_users":7,
                    "explain":"To‘lovlar soni va payer farq qiladi"})
                period["finance"].update({"manual_profit_text":"$3.00",
                    "explain":"Taxminiy hisob","ai_usage":[{"model":"demo",
                    "label":"AI Test","requests":4,"tokens":120,"cost_text":"$0.01"}]})
                period["retention"] = {"new_paying":5,"renewals":2,
                    "ever_renewed_share_pct":15,"inactive_paid_share_pct":3,
                    "renewal_share_pct":22,"active_paid_now":7,"explain":"Qayta to‘lov"}
                period["sources_paid"] = [{"label":"Telegram","paying_users":3,
                    "payments":4,"revenue_text":"$32.00"}]
            fake_desktop = {"funnel":{"download_requested":{"users":8},
                "verified_first_open":{"users":3}},
                "active":{"dau":1,"wau":2,"mau":3},
                "notes":{"install_definition":"Faqat birinchi ochish isbotlangan."}}
            fake_android = {"funnel":{"apk_requested":{"users":6},
                "first_open":{"users":4}},
                "registry":{"installed_devices":4,"installed_users":4},
                "active":{"dau":1,"wau":2,"mau":3},"versions":{"rows":[]}}
            fake_entry = {"ok":True,"rows":[{"label":"Bot",
                "total_week":9,"unique_week":7,"total_all":20,"unique_all":12}]}
            legacy_stats_requests = []
            attempted_mutations = []
            fake_management = {
                "ok": True,
                "prices": [
                  {"method":"alipay","plan":"10_days","amount":19,"currency":"TJS",
                   "text":"19 TJS","method_label":"Alipay","plan_label":"10 кун",
                   "qr_method":"alipay","qr_set":True}
                ],
                "payment_details": "Dushanbe City demo", "payment_details_alif": "Alif demo",
                "hsk30": {"enabled": False, "unlock_price_tjs": 10, "live_levels": []},
                "limits_config": {"plans": {}, "trial": {}},
                "channels": {"enabled": False, "items": []},
                "help": {"links": []}, "gemini": {"configured": False, "options": []},
                "portfolio": {"summary": {
                  "approved_payments": 12, "gross_revenue_usd": "$50.70",
                  "manual_profit_usd": "$81.14", "manual_expense_usd": "$143.75",
                  "net_usd": "$-11.91"
                }, "history": [
                  {"type":"profit","amount_usd":"$1.08","source":"manual_profit",
                   "created_at":"2026-10-09", "original":"10 TJS", "note":"Demo activity"}
                ]}
            }
            def api_fixture(route):
                url = route.request.url
                if url.endswith("/api/admin-miniapp/overview"):
                    route.fulfill(status=200, content_type="application/json",
                                  body=json.dumps(fake_overview))
                elif url.endswith("/api/admin-miniapp/management"):
                    route.fulfill(status=200, content_type="application/json",
                                  body=json.dumps(fake_management))
                elif url.endswith("/api/admin-miniapp/finance-stats"):
                    route.fulfill(status=200, content_type="application/json",
                                  body=json.dumps(fake_finance))
                elif url.endswith(("/desktop-stats", "/android-stats", "/sub-entry-stats")):
                    legacy_stats_requests.append(url)
                    data = ({"ok":True,"desktop":fake_desktop} if url.endswith("/desktop-stats")
                            else {"ok":True,"android":fake_android} if url.endswith("/android-stats")
                            else fake_entry)
                    route.fulfill(status=200, content_type="application/json",
                                  body=json.dumps(data))
                else:
                    if url.endswith(("/desktop-stats", "/android-stats", "/sub-entry-stats")):
                        legacy_stats_requests.append(url)
                    if url.endswith("/payments/review"):
                        attempted_mutations.append("payment_review")
                    route.fulfill(status=403, content_type="application/json",
                                  body='{"ok":false,"error":"admin_only"}')
            live.route("**/api/admin-miniapp/**", api_fixture)
            live.goto(f"http://127.0.0.1:{server.server_port}/app/static/admin.html",
                      wait_until="domcontentloaded")
            live.wait_for_selector("#app:not([hidden])", timeout=8000)
            assert live.locator("#summaryGrid .stat").count() == 4, "Real dashboard render failed"
            assert live.locator("#overviewCards .stat").count() == 4, "Executive overview should show exactly four facts"
            assert live.locator("#v2LearningCards .stat").count() == 3, "Learning report should show exactly three facts"
            assert live.locator("#v2FinanceCards .stat").count() == 4, "Finance should show four key facts"
            assert live.locator("#v2UnifiedApps .v2-client-card").count() == 3, "Three app summaries expected"
            for channel, revenue in (("miniapp", "$40.00"), ("android", "$16.00"), ("desktop", "$8.00")):
                c = live.locator(f'#v2UnifiedApps [data-client="{channel}"]')
                assert c.locator(".v2-client-fact").count() == 3, f"Too many facts for {channel}"
                assert revenue in c.inner_text(), f"Canonical revenue missing for {channel}"
            assert "noma'lum" in live.locator("#v2SourceNote").inner_text(), "Unattributed payments must be disclosed"
            assert not legacy_stats_requests, "Detailed reports must not load before opening: " + str(legacy_stats_requests)
            assert live.locator("#moduleGrid [data-module]").count() == 1, "Course track module rendering failed; browser errors: " + str(live_errors)
            assert live.locator("#v2ProductAccess [data-module]").count() == 2, "Access module rendering failed"
            assert live.locator("#v2MarketingModules [data-module]").count() == 4, "Marketing module rendering failed"
            assert live.locator("#v2SystemModules [data-module]").count() == 2, "System module rendering failed"
            assert live.locator("#v2ProductContent [data-module]").count() == 2, "Product Content modules missing"
            assert live.locator("#v2MarketingPartners [data-module]").count() == 1, "Partner module missing"
            assert live.locator('#v2PricesView').count() == 1, "Finance pricing workspace missing"
            assert live.locator('#v2MethodsView').count() == 1, "Finance payment-methods workspace missing"
            assert live.locator('#v2PortfolioView').count() == 1, "Finance inline portfolio section missing"
            assert live.locator("#marketing #adHub").count() == 1, "Existing Mini App advertising control was lost"
            assert live.locator("#marketing #notifTemplates").count() == 1, "Existing notifications control was lost"

            # Critical module coverage: each module must be discoverable from some safe V2 path.
            mapped_keys = {"hsk30","course_access","limits","course_sales_experiment","audio",
                           "broadcast","ads","release_feedback","discount","partners","channels","help",
                           "prices","portfolio","stats","user_search","give_access","delete_user","ads_hub"}
            assert len(mapped_keys) == 19
            for area, keys in (
                ("statistics", ("overview", "platform", "funnel", "ai", "details")),
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
                    if area == "statistics" and key == "details":
                        assert live.locator("#statistics .v2-legacy-group").count() == 3
                        assert live.locator("#statistics .v2-details-pane .block").count() == 12
                        assert live.locator("#statistics #legacyOverviewCards .stat").count() == 1
                        assert live.locator("#statistics #advancedCards .stat").count() == 1
                        assert live.locator("#statistics #featureAdoption .tbl").count() == 1
                        assert live.locator("#statistics #financeCards .stat").count() == 5
                        assert live.locator("#statistics #unitCards .stat").count() == 4
                        assert live.locator("#statistics #retentionCards .stat").count() == 4
                        assert live.locator("#statistics #clientDeviceCards .stat").count() == 4
                        live.locator("#desktopCards .stat").first.wait_for(timeout=8000)
                        live.locator("#androidCards .stat").first.wait_for(timeout=8000)
                        live.locator("#subEntryStats .tbl").wait_for(timeout=8000)
                        assert live.locator("#desktopCards .stat").count() == 4
                        assert live.locator("#androidCards .stat").count() >= 4
                        assert live.locator("#desktopFunnel .bar").count() == 5
                        assert live.locator("#androidFunnel .bar").count() == 4
                        assert "Batafsil server hisobot" in live.locator("#reportText").inner_text()
                        assert live.locator("#overviewCards .stat").count() == 4, "Simple analytics were overwritten"
                        assert len(legacy_stats_requests) == 3, "Detailed endpoints not lazily loaded once each"
                        live.screenshot(path=str(output / "admin-v2-full-legacy-analytics.png"),
                                        full_page=True)
                        live.locator('#statistics [data-v2-sub="statistics:overview"]').click()
                        assert live.locator("#overviewCards .stat").count() == 4
                        live.locator('#statistics [data-v2-sub="statistics:details"]').click()
                        assert len(legacy_stats_requests) == 3, "Details repeated network calls"
                    if area == "payments" and key == "prices":
                        live.locator('#v2PricesView [data-prow]').first.wait_for(timeout=6000)
                        assert live.locator('#v2PricesView [data-psave]').count() == 1, "Live pricing controls missing"
                        assert live.locator('#drawer.open').count() == 0, "Old prices drawer still opens"
                        live.screenshot(path=str(output / "admin-v2-prices-inline-1440.png"), full_page=True)
                    if area == "payments" and key == "methods":
                        live.locator('#v2MethodsView #payDetails').wait_for(timeout=6000)
                        assert live.locator('#v2MethodsView [data-qrbtn]').count() == 2, "Live QR controls missing"
                        assert live.locator('#v2MethodsView [data-pdsave]').count() == 2, "Bank save actions missing"
                        assert live.locator('#drawer.open').count() == 0, "Old payment-methods drawer still opens"
                        live.screenshot(path=str(output / "admin-v2-methods-inline-1440.png"), full_page=True)
                    if area == "payments" and key == "portfolio":
                        live.locator('#v2PortfolioView .v2-ledger-balance').wait_for(timeout=6000)
                        assert live.locator('#v2PortfolioView .v2-ledger-metric').count() == 3, "Finance KPI cards missing"
                        assert live.locator('#v2PortfolioView .v2-ledger-record').count() == 1, "Real portfolio history not rendered"
                        assert live.locator('#v2PortfolioView [data-pfsave]').count() == 1, "Live portfolio editor lost"
                        assert live.locator('#drawer.open').count() == 0, "Legacy finance drawer unexpectedly opened"
                        assert "$-11.91" in live.locator('#v2PortfolioView').inner_text(), "Portfolio did not use server balance"
                        live.screenshot(path=str(output / "admin-v2-portfolio-inline-1440.png"), full_page=True)
                    if key == keys[0] or area == "marketing" and key == "ads":
                        live.screenshot(path=str(output / f"admin-v2-{area}-{key}-1440.png"), full_page=True)
                live.locator(f'#{area} [data-v2-sub="{area}:{keys[0]}"]').click()
            live.locator('#tabs [data-tab="dashboard"]').click()
            assert live.locator("#userList [data-user]").count() >= 1, "Real Users rows missing"
            live.locator('#tabs [data-tab="users"]').click()
            live.screenshot(path=str(output / "admin-v2-users-1440.png"), full_page=True)
            live.locator('#tabs [data-tab="payments"]').click()
            live.screenshot(path=str(output / "admin-v2-payments-1440.png"), full_page=True)
            assert live.locator('#paymentBoard .v2-pay-desktop [data-payment-preview="7001"]').count() == 1, "Real Payments row missing"
            live.locator('#paymentBoard .v2-pay-desktop [data-payment-preview="7001"]').click()
            assert live.locator("#drawer.open").count() == 1, "Payment preview did not open"
            live.screenshot(path=str(output / "admin-v2-payment-preview-1440.png"), full_page=False)
            assert "bank" in live.locator("#drawerBody").inner_text().lower(), "Bank verification warning missing"
            assert "Kvitansiya" in live.locator("#drawerBody").inner_text(), "Missing receipt status"
            live.once("dialog", lambda d: d.dismiss())
            live.locator('#drawer.open [data-pay][data-pact="approve"]').click()
            assert not attempted_mutations, "Payment approval was sent despite cancelled verification"
            live.locator('[data-act="close-drawer"]').first.click(force=True)

            # Product control modules must be full-width inline workspaces now,
            # not old narrow modal drawers. The original server-backed form IDs
            # and events must survive the redesign.
            for subpage, module_key, expected in [
                ("tracks", "hsk30", "#hsk30Enabled"),
                ("access", "course_access", "#courseAccessMode"),
                ("access", "limits", "#trialEnabled"),
                ("content", "course_sales_experiment", "#salesExperimentMode"),
                ("content", "audio", "#auLevel"),
            ]:
                live.locator('#tabs [data-tab="settings"]').click()
                live.locator(f'#settings [data-v2-sub="settings:{subpage}"]').click()
                live.locator(f'#settings [data-module="{module_key}"]').first.click()
                host = live.locator('#settings .v2-product-editor:not([hidden])')
                host.locator(expected).wait_for(timeout=7000)
                assert host.count() == 1, f"Duplicated Product editor: {module_key}"
                assert not live.locator('#drawer').evaluate("(el) => el.classList.contains('open')"), f"Old drawer opened: {module_key}"
                assert live.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"Product overflow: {module_key}"
                live.screenshot(path=str(output / f"admin-v2-product-{module_key}-1440.png"), full_page=False)
                host.locator('[data-product-back]').click()
                assert live.locator(f'#settings [data-module="{module_key}"]').first.is_visible(), f"Product navigation lost: {module_key}"
            # Broadcast is now an actual V2 campaign editor, not an old Drawer.
            live.locator('#tabs [data-tab="marketing"]').click()
            live.locator('#marketing [data-v2-sub="marketing:campaigns"]').click()
            live.locator('#v2MarketingModules [data-module="broadcast"]').first.click()
            live.locator('#v2MarketingCampaignEditor:not([hidden]) #bcText').wait_for(timeout=6000)
            assert live.locator("#drawer.open").count() == 0, "Legacy broadcast drawer still opens"
            assert live.locator("#v2MarketingCampaignEditor #bcSend").count() == 1, "Real broadcast send action lost"
            assert live.locator("#v2MarketingCampaignEditor #bcTest").count() == 1, "Real broadcast test action lost"
            assert live.locator('#v2MarketingCampaignEditor [data-bcfilter]').count() >= 5, "Broadcast targeting filters lost"
            assert live.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Broadcast editor overflow"
            live.screenshot(path=str(output / "admin-v2-broadcast-inline-1440.png"), full_page=True)
            live.locator('#v2MarketingCampaignEditor [data-bc-close]').click()
            assert live.locator('#v2MarketingCampaignEditor').is_hidden(), "Broadcast close did not hide editor"
            live.locator('#v2MarketingModules [data-module="broadcast"]').first.click()
            live.locator('#v2MarketingCampaignEditor:not([hidden]) #bcText').wait_for(timeout=6000)
            assert live.locator('#v2MarketingCampaignEditor #bcText').count() == 1, "Duplicate broadcast inputs"
            live.locator('#v2MarketingCampaignEditor [data-bc-close]').click()

            # Channels and Help are now a single native V2 inline workspace.
            live.locator('#tabs [data-tab="system"]').click()
            live.locator('#system [data-v2-sub="system:settings"]').click()
            live.locator('#system [data-module="channels"]').first.click()
            live.locator('#v2SystemEditor:not([hidden]) [data-chadd]').wait_for(timeout=6000)
            assert live.locator("#drawer.open").count() == 0, "Legacy channels drawer still opens"
            assert live.locator("#v2SystemEditor [data-chmode]").count() == 1, "Channel controls missing"
            assert live.locator("#v2SystemEditor #chTitle").count() == 1, "Channel add form duplicated"
            live.screenshot(path=str(output / "admin-v2-system-channels-inline-1440.png"), full_page=True)
            live.locator('#v2SystemEditor [data-system-close]').click()
            assert live.locator("#v2SystemEditor").is_hidden(), "Channels close button did not hide editor"
            live.locator('#system [data-module="help"]').first.click()
            live.locator('#v2SystemEditor:not([hidden]) #adminContact').wait_for(timeout=6000)
            assert live.locator("#drawer.open").count() == 0, "Legacy help drawer still opens"
            assert live.locator('#v2SystemEditor [data-hcontact]').count() == 1, "Help save action missing"
            assert live.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Inline system editor overflow"
            live.screenshot(path=str(output / "admin-v2-system-help-inline-1440.png"), full_page=True)
            live.locator('#v2SystemEditor [data-system-close]').click()
            assert not attempted_mutations, "The UI smoke performed a production mutation"
            live.locator('#tabs [data-tab="dashboard"]').click()
            assert not live_errors, "Real render JS errors: " + str(live_errors)
            live.screenshot(path=str(output / "admin-v2-mocked-api-render-1440.png"),
                            full_page=True)
            live_context.close()

            # Telegram iOS-style WebView contract: native inset must prevent
            # native Close/menu overlays from covering the title and drawer.
            # Request mobile fullscreen and keep native floating controls clear.
            iphone_context = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=True, has_touch=True, device_scale_factor=3,
            )
            iphone = iphone_context.new_page()
            iphone_errors = []
            iphone.on("pageerror", lambda error: iphone_errors.append(str(error)))
            iphone.route("https://telegram.org/js/telegram-web-app.js", lambda route: route.fulfill(
                status=200, content_type="application/javascript",
                body="""window.__fullscreenRequests=0;
                window.Telegram={WebApp:{
                    initData:'nonprod-mobile-demo', platform:'ios',isFullscreen:false,
                    safeAreaInset:{top:57,right:0,bottom:15,left:0},
                    contentSafeAreaInset:{top:75,right:0,bottom:26,left:0},
                    requestFullscreen(){window.__fullscreenRequests++;this.isFullscreen=true},
                    ready(){},expand(){},setHeaderColor(){},
                    setBackgroundColor(){},
                    onEvent(type,callback){(window.__telegramEvents||(window.__telegramEvents={}))[type]=callback}
                }};"""
            ))
            iphone.route("**/api/admin-miniapp/**", api_fixture)
            iphone.goto(
                f"http://127.0.0.1:{server.server_port}/app/static/admin.html",
                wait_until="domcontentloaded"
            )
            iphone.wait_for_selector("#app:not([hidden])", timeout=8000)
            assert iphone.evaluate("window.__fullscreenRequests === 1"), "Admin did not request Telegram fullscreen"
            assert iphone.evaluate("parseFloat(getComputedStyle(document.querySelector('.workspace')).paddingTop)>=112"), "Fullscreen iPhone close-controls clearance missing"
            assert iphone.evaluate("""() => {
                const bar=document.querySelector('.workspace .topbar').getBoundingClientRect();
                const nav=document.querySelector('.mobile-nav').getBoundingClientRect();
                return bar.top>=110 && nav.bottom<=innerHeight-25;
            }"""), "Telegram header or bottom navigation overlaps native inset"
            # Telegram can update content-safe-area after expansion/rotation.
            iphone.evaluate("""() => {
                window.Telegram.WebApp.contentSafeAreaInset = {top:138,right:0,bottom:35,left:0};
                window.__telegramEvents.contentSafeAreaChanged();
            }""")
            assert iphone.evaluate("parseFloat(getComputedStyle(document.querySelector('.workspace')).paddingTop)>=138"), "Telegram dynamic safe top not applied"
            assert iphone.evaluate("parseFloat(getComputedStyle(document.querySelector('.mobile-nav')).bottom)>=35"), "Telegram dynamic bottom inset missing"
            iphone.evaluate("window.scrollTo(0, 0)")
            print("Fullscreen geometry", iphone.evaluate("""() => {
                const b=document.querySelector('.workspace .topbar').getBoundingClientRect();
                const t=document.querySelector('#v2Eyebrow').getBoundingClientRect();
                return {barTop:b.top,barBottom:b.bottom,titleTop:t.top,scrollY:window.scrollY,
                  workspaceTop:getComputedStyle(document.querySelector('.workspace')).paddingTop,
                  stickyTop:getComputedStyle(document.querySelector('.workspace .topbar')).top,
                  full:document.documentElement.dataset.adminFullscreen};
            }"""))
            assert iphone.evaluate("""() => {
                const bar=document.querySelector('.workspace .topbar').getBoundingClientRect();
                const eyebrow=document.querySelector('#v2Eyebrow').getBoundingClientRect();
                return bar.top >= 137 && eyebrow.top >= bar.bottom - 1;
            }"""), "Page title hidden behind Telegram-safe sticky header"
            iphone.screenshot(path=str(output / "admin-v2-telegram-safe-dashboard-390.png"), full_page=False)
            iphone.locator('.mobile-nav [data-tab="statistics"]').click()
            iphone.locator('#statistics [data-v2-sub="statistics:platform"]').click()
            assert iphone.locator("#v2UnifiedApps .v2-client-card").count() == 3
            assert iphone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Unified apps mobile overflow"
            iphone.screenshot(path=str(output / "admin-v2-telegram-unified-apps-390.png"), full_page=False)
            # Every Product subtab must fit within the viewport (no cut-off label).
            iphone.locator('.mobile-nav [data-tab="menu"]').click()
            iphone.locator('#drawer.open [data-tab="settings"]').click()
            iphone.locator('#settings [data-v2-sub="settings:access"]').click()
            assert iphone.locator('#settings>.v2-intro').is_hidden(), "Duplicate product description"
            assert iphone.evaluate("""() => {
                const nav=document.querySelector('#settings .v2-subnav');
                const rect=nav.getBoundingClientRect();
                return getComputedStyle(nav).display==='grid' &&
                  nav.scrollWidth<=nav.clientWidth+1 &&
                  [...nav.querySelectorAll('[data-v2-sub]')].every(tab=>{
                    const t=tab.getBoundingClientRect();
                    return t.left>=rect.left-1 && t.right<=rect.right+1;
                  });
            }"""), "Mobile Product tabs overflow or get clipped"
            iphone.screenshot(path=str(output / "admin-v2-telegram-product-tabs-390.png"), full_page=False)
            iphone.locator('.mobile-nav [data-tab="payments"]').click()
            iphone.locator('#payments [data-v2-sub="payments:prices"]').click()
            iphone.locator('#v2PricesView [data-prow]').first.wait_for(timeout=6000)
            assert iphone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Pricing overflow on iPhone"
            iphone.screenshot(path=str(output / "admin-v2-prices-inline-390.png"), full_page=True)
            iphone.locator('#payments [data-v2-sub="payments:methods"]').click()
            iphone.locator('#v2MethodsView #payDetails').wait_for(timeout=6000)
            assert iphone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Bank editor overflow on iPhone"
            iphone.screenshot(path=str(output / "admin-v2-methods-inline-390.png"), full_page=True)
            iphone.locator('#payments [data-v2-sub="payments:portfolio"]').click()
            iphone.locator('#v2PortfolioView .v2-ledger-balance').wait_for(timeout=6000)
            assert iphone.locator('#drawer.open').count() == 0, "Mobile finance still uses legacy drawer"
            assert iphone.locator('#v2PortfolioView [data-pfsave]').count() == 1
            assert iphone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Portfolio overflow on iPhone"
            iphone.screenshot(path=str(output / "admin-v2-portfolio-inline-390.png"), full_page=True)
            iphone.locator('.mobile-nav [data-tab="menu"]').click()
            iphone.locator('#drawer.open [data-tab="marketing"]').click()
            iphone.locator('#marketing [data-v2-sub="marketing:campaigns"]').click()
            iphone.locator('#v2MarketingModules [data-module="broadcast"]').first.click()
            iphone.locator('#v2MarketingCampaignEditor:not([hidden]) #bcText').wait_for(timeout=7000)
            assert iphone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "iPhone broadcast editor overflow"
            iphone.screenshot(path=str(output / "admin-v2-broadcast-inline-390.png"), full_page=True)
            iphone.locator('#v2MarketingCampaignEditor [data-bc-close]').click()
            iphone.locator('.mobile-nav [data-tab="menu"]').click()
            iphone.locator('#drawer.open [data-tab="system"]').click()
            iphone.locator('#system [data-v2-sub="system:settings"]').click()
            iphone.locator('#system [data-module="channels"]').first.click()
            iphone.locator('#v2SystemEditor:not([hidden]) #chTitle').wait_for(timeout=6000)
            assert iphone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Mobile channels editor overflow"
            iphone.screenshot(path=str(output / "admin-v2-system-channels-inline-390.png"), full_page=True)
            iphone.locator('#v2SystemEditor [data-system-close]').click()
            iphone.locator('.mobile-nav [data-tab="payments"]').click()
            assert iphone.locator('#payments').is_visible(), "Did not return to finance after system test"
            iphone.locator('#payments [data-v2-sub="payments:payments"]').click()
            assert iphone.locator("#paymentBoard .v2-pay-mobile [data-payment-preview]").count()==1, "Mobile finance cards missing"
            assert iphone.locator("#paymentBoard .v2-pay-desktop").is_hidden(), "Desktop payments table visible on mobile"
            assert iphone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Mobile finance overflow"
            iphone.screenshot(path=str(output / "admin-v2-telegram-mobile-finance-390.png"), full_page=False)
            iphone.locator("#paymentBoard .v2-pay-mobile [data-payment-preview]").first.click()
            assert iphone.locator("#drawer.open").is_visible(), "Payment details sheet missing"
            assert iphone.evaluate("""() => {
                const panel=document.querySelector('#drawer').getBoundingClientRect();
                const header=document.querySelector('#drawer .dhead').getBoundingClientRect();
                return panel.top>=75 && header.top>=panel.top && panel.right<=innerWidth+1;
            }"""), "Native Telegram controls cover drawer header"
            assert iphone.evaluate("document.body.classList.contains('locked')"), "Drawer did not lock background"
            # Render a real HSK 3.0 report shape inside a visible drawer with
            # in-memory data; verify phone-only card view rather than wide tables.
            iphone.evaluate("""() => {
                document.querySelector('#drawerBody').innerHTML='<div id="hsk30Analytics"></div>';
                renderHsk30Stats({
                    course_funnel:[{label:'Таклиф кўрсатилди',users:12},
                                   {label:'HSK 3.0 даражаси танланди',users:4,previous_users:12,converted_from_previous:4,conversion_from_previous_pct:33.3}],
                    payment_funnel:[{label:'Тўловга ўтиш',attempts:7},
                                    {label:'Тасдиқланган',attempts:2,previous_attempts:7,converted_from_previous:2,conversion_from_previous_pct:28.6}],
                    payments:{pending:0,approved:2,rejected:0}
                });
            }""")
            assert iphone.locator("#hsk30Analytics .hsk30-funnel-mobile .hsk30-funnel-step").count()==4, "HSK 3.0 funnel cards missing"
            assert iphone.locator("#hsk30Analytics .hsk30-funnel-desktop").first.is_hidden(), "Wide HSK30 funnel table visible on phone"
            assert iphone.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), "HSK3 stats horizontal overflow"
            iphone.screenshot(path=str(output / "admin-v2-telegram-hsk3-funnel-sheet-390.png"), full_page=False)
            iphone.screenshot(path=str(output / "admin-v2-telegram-payment-sheet-390.png"), full_page=False)
            iphone.locator('#drawer [data-act="close-drawer"]').click()
            assert not iphone.evaluate("document.body.classList.contains('locked')"), "Drawer background remained locked"
            iphone.locator('.mobile-nav [data-tab="users"]').click()
            assert iphone.locator("#userList .v2-users-mobile [data-user]").count()>0, "Mobile user cards missing"

            # Regression: iOS automatically zooms the entire page when an input
            # whose computed font is <16px receives focus in Telegram WebView.
            # Chromium doesn't emulate that native zoom; enforce the computed
            # font-size contract and stable in-viewport bounds instead.
            search = iphone.locator("#users #search")
            assert search.is_visible(), "Users search field is not visible"
            assert float(search.evaluate("(el) => getComputedStyle(el).fontSize.replace('px','')")) >= 16, "iOS search font causes focus auto-zoom"
            assert iphone.evaluate("""() => {
                const r=document.querySelector('#users .toolbar').getBoundingClientRect();
                return r.left >= -1 && r.right <= innerWidth+1;
            }"""), "Search toolbar overflows viewport before focus"
            search.focus()
            assert iphone.evaluate("""() => {
                const r=document.querySelector('#users #search').getBoundingClientRect();
                return r.left>=-1 && r.right<=innerWidth+1 &&
                  getComputedStyle(document.querySelector('#users #search')).fontSize==='16px';
            }"""), "Search input enlarged or clipped after focus"
            iphone.screenshot(path=str(output / "admin-v2-telegram-search-focused-390.png"), full_page=False)
            search.blur()
            iphone.screenshot(path=str(output / "admin-v2-telegram-users-390.png"), full_page=False)
            iphone.locator("#userList .v2-users-mobile [data-user]").first.click()
            iphone.locator("#drawer.open .v2-profile-details").first.wait_for(timeout=6000)
            assert iphone.locator("#drawer .v2-profile-details").count()==4, "Optional profile diagnostics not grouped"
            assert not iphone.locator("#drawer .v2-profile-details").first.evaluate("(el) => el.open"), "Technical data should start collapsed"
            iphone.locator("#drawer .v2-profile-details").first.locator("summary").first.click()
            assert iphone.locator("#drawer .v2-profile-details").first.evaluate("(el) => el.open"), "User diagnostics accordion does not expand"
            assert iphone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "User profile overflow"
            iphone.screenshot(path=str(output / "admin-v2-telegram-user-sheet-390.png"), full_page=False)
            iphone.locator('#drawer [data-act="close-drawer"]').click()
            assert iphone.locator(".workspace .topbar [data-act='reload']").is_visible(), "Mobile refresh not reachable"
            assert iphone.locator(".page-head .page-actions [data-act='reload']").is_hidden(), "Duplicate refresh CTA visible"
            # iPhone Product: editable real controls inline, no fullscreen drawer.
            iphone.locator('.mobile-nav [data-tab="menu"]').click()
            iphone.locator('#drawer.open [data-tab="settings"]').click()
            iphone.locator('#settings [data-v2-sub="settings:access"]').click()
            iphone.locator('#v2ProductAccess [data-module="course_access"]').click()
            iphone.locator('#v2ProductEditorAccess:not([hidden]) #courseAccessMode').wait_for(timeout=7000)
            assert not iphone.locator('#drawer').evaluate("(el) => el.classList.contains('open')"), "Mobile Product opened old modal"
            assert iphone.evaluate("document.documentElement.scrollWidth <= innerWidth+1"), "Mobile Product overflow"
            iphone.screenshot(path=str(output / "admin-v2-telegram-product-course-390.png"), full_page=False)
            iphone.locator('#v2ProductEditorAccess [data-product-back]').click()
            assert iphone.locator('#v2ProductAccess [data-module="limits"]').is_visible(), "Mobile Product module was not restored"
            assert not iphone_errors, "Telegram iPhone JS errors: " + str(iphone_errors)
            iphone_context.close()

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
