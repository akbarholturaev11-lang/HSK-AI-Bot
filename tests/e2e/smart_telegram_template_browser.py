"""Real PWA shell/catalogs, synthetic read-only API fixtures; no auth/send claims."""
import argparse
import asyncio
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from playwright.async_api import async_playwright, expect

from app.admin_api.pwa_bootstrap import create_admin_pwa_bootstrap_router
from app.admin_api.pwa_notifications import _preview
from app.services.notification_template_service import KEY_SMART_STUDY, TEMPLATE_KEYS

ORIGIN = "https://hskai.app"


async def browser_checks(output):
    output.mkdir(parents=True, exist_ok=True)
    app = FastAPI()
    app.include_router(create_admin_pwa_bootstrap_router(settings_obj=SimpleNamespace(
        ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN=ORIGIN)))
    errors = []

    async def serve(route):
        req = route.request
        assert req.url.startswith(ORIGIN + "/"), req.url
        path = req.url.removeprefix(ORIGIN)
        if path == "/admin/sw.js":
            await route.abort(); return
        if not path.startswith("/api/"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN) as client:
                response = await client.get(path)
            headers = dict(response.headers); headers.pop("content-length", None)
            await route.fulfill(status=response.status_code, headers=headers, body=response.content)
            return
        data = {"ok": True}
        if path.endswith("/me"):
            data.update(user_id=101, mcp_available=False, push_available=False)
        elif path.endswith("/unread-count"):
            data.update(unread_count=0, capped=False)
        elif path.endswith("/auth/logout"):
            data.update(status="logged_out")
        elif path.endswith("/analytics"):
            data.update(available=True, platform="overall", period="weekly",
                generated_at="2026-10-29T00:00:00+00:00", scope={"section":"home"},
                metrics={"users_total":0,"new_accounts":0,"active_accounts":0,
                         "payments_by_status":{},"levels":[],"languages":[]})
        elif path.endswith("/notifications/read"):
            if req.post_data_json.get("key"):
                assert req.post_data_json["key"] == KEY_SMART_STUDY
                data.update(template=_preview(KEY_SMART_STUDY, None))
            else:
                data.update(items=[{"key": key, "enabled": True} for key in TEMPLATE_KEYS])
        else:
            raise AssertionError("Unexpected UI request: " + path)
        await route.fulfill(status=200, json=data)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            context = await browser.new_context(viewport={"width":1440,"height":1000}, service_workers="block")
            await context.route("**/*", serve)
            page = await context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            for lang in ("uz", "ru", "tj"):
                await page.set_viewport_size({"width":1440,"height":1000})
                await page.goto(ORIGIN + "/admin/")
                await page.wait_for_load_state("networkidle")
                await page.locator("#locale").select_option(lang)
                await page.locator('.nav [data-route="system"]').click()
                await page.locator('[data-action="noticeList"]').click()
                await expect(page.locator('[data-notice-key]')).to_have_count(6)
                item = page.locator('[data-notice-key="smart_study"]')
                await expect(item).to_be_visible()
                assert "noticeSmartStudy" not in await item.inner_text()
                await item.click()
                await page.set_viewport_size({"width":390,"height":844})
                await expect(page.locator("#noticeText")).to_be_visible()
                save = page.locator('[data-action="managementPrepare"]')
                await expect(save).to_be_disabled()
                await page.locator("#noticeText").fill("QA {lesson}")
                await expect(save).to_be_enabled()
                await page.locator("#noticeText").fill("")
                await expect(save).to_be_disabled()
                for reader in ("uz", "ru", "tj"):
                    await page.locator("#noticeLanguage").select_option(reader)
                    assert "{lesson}" in await page.locator("#noticeText").get_attribute("placeholder")
                    await expect(save).to_be_disabled()
                assert await page.locator(".drawer-foot button").count() == 1
                assert await page.evaluate("document.documentElement.scrollWidth<=innerWidth")
                await page.screenshot(path=str(output / f"smart-template-{lang}-390.png"))
            assert not errors, errors
            await context.close()
        finally:
            await browser.close()
    print("Smart template PWA: UZ/RU/TJ, list/editor, mobile layout, Save/revert and console OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(browser_checks(parser.parse_args().output))
