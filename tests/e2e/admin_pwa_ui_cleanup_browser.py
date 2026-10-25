"""Focused V10 interaction QA against the real public shell and fixture APIs.

This complements the SQL/WebAuthn suite: API responses are deliberate synthetic
UI fixtures, while the shipped JS, CSS, catalogs and strict shell CSP are real.
Run: python -m tests.e2e.admin_pwa_ui_cleanup_browser --output /tmp/admin-pwa-ui
"""
import argparse
import asyncio
import copy
import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image
from playwright.async_api import async_playwright, expect

from app.admin_api.pwa_bootstrap import create_admin_pwa_bootstrap_router

ORIGIN = "https://hskai.app"
STAMP = "2026-10-25T01:00:00+00:00"
UUID = "12345678-1234-1234-1234-123456789abc"


async def browser_checks(output):
    output.mkdir(parents=True, exist_ok=True)
    app = FastAPI()
    app.include_router(create_admin_pwa_bootstrap_router(settings_obj=SimpleNamespace(
        ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN=ORIGIN)))
    original = []
    for source, status, priority in (("bot", "new", "normal"),
                                      ("release", "read", "important"),
                                      ("technical", "new", "normal"),
                                      ("payment", "new", "important")):
        original.append(dict(source=source, source_id=1, user_id=7,
                             triage_status=status, triage_priority=priority,
                             triage_revision=0, triage_assigned_to=None,
                             created_at="2026-09-01T01:00:00+00:00" if source == "release" else STAMP, message="Synthetic " + source + " message",
                             has_attachment=source == "bot", image_preview_available=source == "bot",
                             feedback_parts={"liked": "Synthetic bot message", "disliked": "Synthetic issue", "paid": True} if source == "bot" else None))
    rows = copy.deepcopy(original)
    requests, triage, errors = [], [], []
    paginated = [False]
    stream = io.BytesIO()
    Image.new("RGB", (320, 150), "#e7f0f2").save(stream, "PNG")

    async def serve(route):
        request = route.request
        assert request.url.startswith(ORIGIN + "/"), request.url
        path = request.url.removeprefix(ORIGIN)
        if path == "/admin/sw.js":
            await route.abort()
            return
        if not path.startswith("/api/"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN) as client:
                response = await client.get(path)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            await route.fulfill(status=response.status_code, headers=headers, body=response.content)
            return
        payload = request.post_data_json if request.method == "POST" else None
        requests.append((path, payload))
        data = {"ok": True}
        if path.endswith("/me"):
            data.update(user_id=101, mcp_available=True, push_available=True)
        elif path.endswith("/auth/logout"):
            data.update(status="logged_out")
        elif path == "/api/admin/v1/analytics":
            metrics={"users_total":3,"new_accounts":1,"active_accounts":2,"active_pro":1,
                "active_today":2,"pending_current":1,"expiring_pro":1,"paying_accounts":1,"bot_blocked":0,"blocked_current":0,
                "payments_by_status":{"pending":1,"approved":1,"rejected":0},
                "activity":{"points":[]},"levels":[],"languages":[],
                "course_engagement":{"engaged_accounts":2,"started_accounts":1,"completed_accounts":1}}
            if payload['section']=='report':
                metrics={"quality":[],"detail_row_limit":5000}
            data.update(available=True,platform="overall",period=payload['period'],generated_at=STAMP,
                scope={"section":payload['section']},metrics=metrics)
        elif path.endswith("/statistics"):
            data.update(available=True, platform="overall", generated_at=STAMP, metrics={
                "users_total": 3, "new_accounts": 1, "active_accounts": 2,
                "payments_by_status": {"pending": 1}, "approved_amounts_by_currency": [],
                "ai_usage": {"estimated_cost_usd": 0, "recorded_requests": 0, "tokens": 0},
                "course_engagement": {"engaged_accounts": 2, "started_accounts": 1, "completed_accounts": 1},
                "registration_conversion": {"percent": 0, "registered_accounts": 1, "converted_accounts": 0}})
        elif path.endswith("/unread-count"):
            data.update(unread_count=sum(row["triage_status"] == "new" for row in rows), capped=False)
        elif path.endswith("/inbox/list"):
            selected = [row for row in rows if (payload["source"] == "all" or row["source"] == payload["source"])
                        and (payload["priority"] == "all" or row["triage_priority"] == payload["priority"])
                        and (payload["status"] == "all" or row["triage_status"] == payload["status"])
                        and (payload["period"] == "all_time" or datetime.fromisoformat(row["created_at"]) >=
                             datetime.fromisoformat(STAMP) - timedelta(days=7 if payload["period"] == "weekly" else 30))]
            if paginated[0]:
                if payload.get("before") is None:
                    data.update(items=[dict(copy.deepcopy(original[0]), source_id=i) for i in range(200, 230)],
                                next_before={"created_at": STAMP, "source": "bot", "source_id": 229,
                                             "unread": True, "important": False})
                else:
                    data.update(items=[dict(copy.deepcopy(original[0]), source_id=i) for i in range(230, 235)],
                                next_before=None)
            else:
                data.update(items=copy.deepcopy(selected), next_before=None)
        elif path.endswith("/inbox/triage"):
            triage.append(payload)
            row = next(row for row in rows if row["source"] == payload["source"])
            assert payload["source_id"] == 1 and payload["expected_revision"] == row["triage_revision"]
            operation = payload["operation"]
            if operation in ("resolve", "reopen", "mark_read"):
                row["triage_status"] = {"resolve": "resolved", "reopen": "new", "mark_read": "read"}[operation]
            elif operation == "assign_self":
                row["triage_assigned_to"] = 101
            elif operation in ("mark_important", "clear_important"):
                row["triage_priority"] = "important" if operation == "mark_important" else "normal"
            else:
                raise AssertionError(operation)
            row["triage_revision"] += 1
        elif path.endswith("/attachment"):
            await route.fulfill(status=200, content_type="image/png", body=stream.getvalue())
            return
        elif path.endswith("/categories"):
            data.update(schema="hskai_feedback_categories_v1", generated_at=STAMP, sources=[
                {"source": source, "records_scanned": 2, "truncated": False,
                 "categories": [{"category": "price" if source == "bot" else "reported_issue", "count": 2}]}
                for source in ("bot", "release", "android")
                if payload["source"] in ("all", source)])
        elif path.endswith("/export"):
            mime = "application/json" if payload["format"] == "json" else "text/csv"
            body = json.dumps({"generated_at": STAMP}) if payload["format"] == "json" else "generated_at\n" + STAMP
            await route.fulfill(status=200, content_type=mime, body=body)
            return
        elif path.endswith("/mcp/authorizations"):
            data.update(authorizations=[dict(id=UUID, client_id="Synthetic analytics client", status="redeemed",
                                             active_access=True, created_at=STAMP, access_expires_at=STAMP)])
        elif path.endswith("/mcp/authorizations/revoke"):
            data.update(revoked=True)
        elif path.endswith("/push/list"):
            data.update(sending_enabled=False, subscriptions=[dict(id=UUID, platform="iphone", created_at=STAMP)])
        elif path.endswith("/payments/list"):
            data.update(items=[], next_before_id=None)
        elif path.endswith("/hsk30/analytics"):
            data.update(analytics=dict(period_days=payload["days"],track_activated_users=2,
                 selected_level_users=3,payments={"approved":1},
                 course_funnel=[{"key":"promo_shown","label":"Таклиф кўрсатилди","users":4},
                                {"key":"track_activated","label":"HSK 3.0 курси очилди","users":2}],
                 coverage_note="Synthetic HSK 3.0 funnel"))
        elif path.endswith("/hsk30/read"):
            data.update(hsk30=dict(enabled=True,unlock_payment_enabled=True,unlock_price_tjs=99,
                                   live_levels=["nhsk1","nhsk2"],available_levels=["nhsk1","nhsk2","nhsk3"]))
        elif path.endswith("/course-access/read"):
            data.update(course_access=dict(mode="subscription",free_until=None,saved_at=STAMP))
        elif path.endswith("/limits/read"):
            rules={"lesson.start":{"limit":2,"window":"daily"},
                   "ai.text":{"limit":5,"window":"daily"},
                   "practice.placement":{"limit":1,"window":"lifetime"}}
            data.update(limits=dict(plans={"FREE":rules,"TRIAL_ACTIVE":copy.deepcopy(rules)},
                                    trial={"enabled":True,"days":7,"disabled_reason":"",
                                           "ai_budget_usd":1.5,"min_account_age_hours":0}),
                        revision_hash="0"*64)
        else:
            raise AssertionError("Unexpected UI request: " + path)
        await route.fulfill(status=200, json=data)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            context = await browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
            await context.route("**/*", serve)
            page = await context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.add_init_script("window.cspFailures=[];document.addEventListener('securitypolicyviolation',e=>window.cspFailures.push(e.violatedDirective));")
            for width in (390, 1440):
                await page.set_viewport_size({"width": width, "height": 844 if width == 390 else 1000})
                for language in ("uz", "ru", "tj"):
                    await page.goto(ORIGIN + "/admin/")
                    await page.wait_for_load_state("networkidle")
                    if width == 390:
                        await page.locator('[data-action="more"]').click()
                        await page.locator("#drawerLocale").select_option(language)
                    else:
                        await page.locator("#locale").select_option(language)
                    await page.locator('[data-action="feedback"]').click()
                    await expect(page.locator(".inbox-minimal-row")).to_have_count(4)
                    assert not await page.locator("#inboxSource,#inboxPriority,#inboxStatus,#inboxPeriod,#inboxSearchQuery").count()
                    assert not await page.locator('.inbox-drawer .drawer-foot:visible').count()
                    assert not await page.locator('[data-inbox-op],.inbox-primary-action').count()
                    await expect(page.locator(".inbox-minimal-row.is-important.is-unread")).to_have_count(2)
                    bot = page.locator('[data-inbox-open="bot:1"]')
                    await expect(bot).to_have_count(1)
                    assert await bot.evaluate("e=>e.getBoundingClientRect().height>=44")
                    await expect(bot.locator(".inbox-row-preview")).to_contain_text("Synthetic bot message")
                    await expect(bot.locator(".inbox-row-meta")).to_contain_text("Telegram Bot")
                    assert not await page.locator("[data-feedback-next]").count()
                    await page.screenshot(path=str(output / f"inbox-minimal-{language}-{width}.png"))
                    await bot.click()
                    await expect(page.locator(".inbox-details-text")).to_have_count(2)
                    await expect(page.locator(".inbox-details-text").first).to_contain_text("Synthetic bot message")
                    await expect(page.locator(".inbox-details-text").last).to_contain_text("Synthetic issue")
                    assert "👎" not in await page.locator(".inbox-detail-messages").inner_text()
                    await expect(page.locator(".inbox-detail-meta")).to_contain_text("Telegram Bot")
                    assert triage[-1]["source"]=="bot" and triage[-1]["operation"]=="mark_read"
                    await expect(page.locator('[data-inbox-attachment]')).to_have_count(1)
                    before = len(requests)
                    await page.locator('[data-inbox-attachment]').click()
                    await expect(page.locator('.inbox-attachment-image')).to_be_visible()
                    assert len([path for path, _ in requests[before:] if path.endswith("/attachment")])==1
                    await page.screenshot(path=str(output / f"inbox-detail-{language}-{width}.png"))
                    await page.locator(".inbox-back").click()
                    await expect(page.locator('[data-inbox-open="bot:1"]')).to_have_class(__import__("re").compile("is-read"))
                    await expect(page.locator(".inbox-minimal-row.is-important.is-unread")).to_have_count(2)
                    await page.locator(".drawer-close").click()
                    await page.locator('[data-route="stats"]:visible').first.click()
                    # V10 analytics keeps feedback controls in the Report tab.
                    await page.locator('[data-stats-tab="report"]').click()
                    await expect(page.locator("#feedbackSource")).to_be_visible()
                    for header_menu in ("period", "platform"):
                        header_trigger = page.locator(f'[data-action="{header_menu}"]')
                        await header_trigger.focus()
                        await header_trigger.press("ArrowDown")
                        await expect(page.locator(f'#{header_menu}Menu [role="menuitem"]').first).to_be_focused()
                        await page.keyboard.press("Escape")
                        await expect(page.locator(f'#{header_menu}Menu')).to_be_hidden()
                        await expect(header_trigger).to_be_focused()
                    await page.locator("#feedbackSource").select_option("bot")
                    await expect(page.locator(".feedback-analysis-source")).to_have_count(1)
                    await page.locator("#feedbackPeriod").select_option("monthly")
                    await expect(page.locator("#feedbackPeriod")).to_have_value("monthly")
                    for dataset in ("statistics", "feedback"):
                        menu_trigger = page.locator(f'[data-menu-toggle="{dataset}ExportMenu"]')
                        await menu_trigger.click()
                        attribute = "data-export-format" if dataset == "statistics" else "data-feedback-export"
                        async with page.expect_download() as pending:
                            await page.locator(f'[{attribute}="json"]').click()
                        downloaded = await pending.value
                        assert downloaded.suggested_filename.endswith(".json")
                        assert json.loads(Path(await downloaded.path()).read_text())["generated_at"] == STAMP
                        await expect(menu_trigger).to_be_enabled()
                        await expect(menu_trigger).to_be_focused()
                    await page.locator('.feedback-analysis').scroll_into_view_if_needed()
                    await page.screenshot(path=str(output / f"feedback-stats-{language}-{width}.png"))
                    assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth"), language
                    requests.clear()
            # The simplified UI has no manual triage, menus or importance flags.
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.locator('[data-action="feedback"]').click()
            await expect(page.locator(".inbox-minimal-row")).to_have_count(4)
            await page.locator('[data-inbox-open="technical:1"]').click()
            await expect(page.locator(".inbox-details")).to_be_visible()
            assert triage[-1]["source"]=="technical" and triage[-1]["operation"]=="mark_read"
            await page.locator(".inbox-back").click()
            await expect(page.locator('[data-inbox-open="technical:1"]')).to_have_class(__import__("re").compile("is-read"))
            assert not await page.locator('[data-inbox-op]').count()
            await page.locator(".drawer-close").click()
            # Paged Inbox appends, never replaces rows or exposes a "Next" button.
            paginated[0] = True
            await page.locator('[data-action="feedback"]').click()
            await expect(page.locator(".inbox-minimal-row")).to_have_count(30)
            assert not await page.locator('[data-feedback-next]').count()
            await page.locator("#drawerContent").evaluate("(el) => { el.scrollTop=el.scrollHeight; }")
            await expect(page.locator(".inbox-minimal-row")).to_have_count(35)
            assert any(path.endswith("/inbox/list") and payload.get("before")
                       for path, payload in requests if payload)
            await page.locator(".drawer-close").click()
            paginated[0] = False
            for action, target in (("pushSettings", "[data-push-revoke]"),
                                   ("mcpConnections", "[data-mcp-revoke]")):
                await page.locator('[data-action="more"]').click()
                # Mobile More now opens a compact bottom sheet; account tools
                # are grouped in .more-sheet-extras instead of the old action list.
                await expect(page.locator(".more-drawer .more-sheet-list")).to_be_visible()
                await page.locator(f'.more-drawer .more-sheet-extras [data-action="{action}"]').click()
                await expect(page.locator(target)).to_be_visible()
                box = await page.locator(target).bounding_box()
                assert box["height"] >= 44 and box["x"] + box["width"] <= 390, box
                await page.screenshot(path=str(output / f"{action}-mobile.png"))
                if action == "mcpConnections":
                    await page.locator(target).click()
                    await expect(page.locator('[data-action="mcpRevokeConfirm"]')).to_have_count(0)
                await page.locator(".drawer-close").click()

            # Mac-sized Safari/Chromium windows retain the full sidebar and Kurs view.
            for width, height in ((820, 600), (1024, 650), (1280, 800)):
                await page.set_viewport_size({"width": width, "height": height})
                await page.locator('.sidebar [data-route="course"]').click()
                await expect(page.locator(".course-subtabs [role=tab]")).to_have_count(4)
                await expect(page.locator('[data-action="hsk30Settings"]')).to_have_count(2)
                await page.locator('[data-course-tab="access"]').click()
                await expect(page.locator('[data-course-window]')).to_have_count(3)
                for field in await page.locator('[data-course-window]').all():
                    assert await field.locator("option").all_text_contents() == [
                        "Кунлик" if await page.evaluate("document.documentElement.lang")=="uz" else
                        "В день" if await page.evaluate("document.documentElement.lang")=="ru" else "Ҳар рӯз",
                        "Бир умр" if await page.evaluate("document.documentElement.lang")=="uz" else
                        "За всё время" if await page.evaluate("document.documentElement.lang")=="ru" else "Барои тамоми умр"]
                await page.locator('[data-course-tab="tracks"]').click()
                geometry = await page.evaluate("""() => {
                    const sidebar = document.querySelector('.sidebar').getBoundingClientRect();
                    const main = document.querySelector('main.main').getBoundingClientRect();
                    return {scrollWidth: document.documentElement.scrollWidth,
                            sidebarLeft: sidebar.left, sidebarRight: sidebar.right,
                            mainLeft: main.left, mainRight: main.right};
                }""")
                assert geometry["scrollWidth"] <= width + 1, geometry
                assert geometry["sidebarLeft"] >= -1, geometry
                assert geometry["sidebarRight"] <= width * 0.29, geometry
                assert geometry["mainLeft"] >= geometry["sidebarRight"] - 1, geometry
                assert geometry["mainRight"] <= width + 1, geometry
                if height < 780:
                    await page.locator(".sidebar").evaluate("(el) => { el.scrollTop = el.scrollHeight; }")
                    assert await page.locator(".sidebar .side-foot").evaluate(
                        "(el) => el.getBoundingClientRect().bottom <= innerHeight + 2")
                await page.screenshot(path=str(output / f"course-compact-mac-{width}.png"))
            assert not errors, errors
            assert not await page.evaluate("window.cspFailures"), await page.evaluate("window.cspFailures")
        finally:
            await browser.close()
    print("Minimal Inbox: mobile/desktop UZ/RU/TJ, automatic urgency, read-on-open, private images and settings passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/tmp/hsk-admin-pwa-ui-cleanup"))
    asyncio.run(browser_checks(parser.parse_args().output))
