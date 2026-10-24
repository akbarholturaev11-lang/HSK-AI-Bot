"""Synthetic desktop/mobile UX QA of the real MCP consent HTML + catalog.

Real FastAPI router and public asset allowlist, mocked OAuth service only.
No user records, production tokens, real Google/ChatGPT or biometric inputs.
Run: python -m tests.e2e.admin_pwa_mcp_consent_browser --output /tmp/admin-pwa-browser
"""
from tests.mcp_transport_fakes import admit, finish, statistics_admit

import argparse
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from playwright.async_api import async_playwright, expect

from app.admin_api.pwa_bootstrap import create_admin_pwa_bootstrap_router
from app.admin_api.pwa_mcp_consent_transport import create_admin_pwa_mcp_consent_router
from app.admin_api.pwa_mcp_oauth import PendingMcpConsent

ORIGIN="https://hskai.app"
REDIRECT="https://registered-client.example/oauth/callback"
COOKIE="c"*64
QUERY={
    "response_type":"code",
    "client_id":"registered-test-client",
    "redirect_uri":REDIRECT,
    "resource":ORIGIN+"/mcp",
    "scope":"admin:analytics:read",
    "state":"test-"+"s"*44,
    "code_challenge":"x"*43,
    "code_challenge_method":"S256",
}


@asynccontextmanager
async def db():
    yield object()


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="/tmp/admin-pwa-browser")
    args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    settings=SimpleNamespace(
        ADMIN_PWA_ENABLED=True,ADMIN_PWA_MCP_ENABLED=True,
        ADMIN_PWA_MCP_TRANSPORT_ENABLED=True,
        ADMIN_PWA_PUBLIC_ORIGIN=ORIGIN,ADMIN_PWA_MCP_RESOURCE=ORIGIN+"/mcp",
        ADMIN_PWA_MCP_CLIENT_ID=QUERY["client_id"],
        ADMIN_PWA_MCP_REDIRECT_URI=REDIRECT,
    )
    async def start(db,**kwargs):
        assert kwargs["session_cookie"]==COOKIE
        return PendingMcpConsent(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",QUERY["client_id"],
            REDIRECT,QUERY["resource"],QUERY["scope"],QUERY["state"],
            __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            "q"*64,
        )
    async def expired(db, **kwargs):
        return None
    app=FastAPI()
    app.include_router(create_admin_pwa_bootstrap_router(
        settings_obj=settings,session_factory=db,
    ))
    app.include_router(create_admin_pwa_mcp_consent_router(
        settings_obj=settings,session_factory=db,begin_service=start,decide_service=expired,
        admission_service=admit, completion_service=finish,
    ))

    async def serve(route):
        request=route.request
        if not request.url.startswith(ORIGIN+"/"):
            raise AssertionError("Unexpected third-party request in consent UI")
        path=request.url.removeprefix(ORIGIN)
        headers=await request.all_headers()
        if request.method=="POST":
            # Chromium routing omits network-generated Fetch Metadata here.
            # Assert the actual browser Origin and navigation before supplying
            # only that synthetic transport header to the in-process bridge.
            assert headers.get('origin')==ORIGIN, 'Native form lost its CSRF Origin'
            assert headers.get('referer')==ORIGIN+'/', 'OAuth query leaked into Referer'
            assert request.is_navigation_request()
            headers['sec-fetch-site']='same-origin'
        async with AsyncClient(transport=ASGITransport(app=app),base_url=ORIGIN) as client:
            response=await client.request(
                request.method,path,headers=headers,
                content=request.post_data_buffer,
            )
        headers=dict(response.headers);headers.pop("content-length",None)
        await route.fulfill(status=response.status_code,headers=headers,body=response.content)

    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        try:
            for width,height,filename in [
                (1440,900,"mcp-consent-desktop.png"),
                (390,844,"mcp-consent-iphone.png"),
            ]:
                context=await browser.new_context(
                    viewport={"width":width,"height":height},service_workers="block",
                )
                await context.add_cookies([{
                    "name":"__Host-hskai_admin","value":COOKIE,"domain":"hskai.app",
                    "path":"/","httpOnly":True,"secure":True,"sameSite":"Lax",
                }])
                await context.route("**/*",serve)
                page=await context.new_page()
                errors=[];page.on("pageerror",lambda err:errors.append(str(err)))
                await page.goto(ORIGIN+"/oauth/authorize?"+urlencode(QUERY))
                await page.wait_for_load_state("networkidle")
                await expect(page.get_by_role("heading",level=1)).to_contain_text(
                    "Statistikaga kirishga ruxsat berish",
                )
                await expect(page.locator('button[value="allow"]')).to_be_visible()
                await expect(page.locator('button[value="deny"]')).to_be_visible()
                assert await page.evaluate(
                    "() => document.documentElement.scrollWidth <= window.innerWidth"
                ),f"Horizontal overflow at width={width}"
                await page.locator("#mcp-locale").select_option("ru")
                await expect(page.locator("html")).to_have_attribute("lang","ru")
                await expect(page.get_by_role("heading",level=1)).to_contain_text(
                    "Разрешить доступ к статистике",
                )
                await page.locator("#mcp-locale").select_option("tj")
                await expect(page.locator("html")).to_have_attribute("lang","tg")
                await expect(page.get_by_role("heading",level=1)).to_contain_text(
                    "Иҷозати дастрасӣ ба омор",
                )
                await page.locator("#mcp-locale").select_option("uz")
                await expect(page.locator("html")).to_have_attribute("lang","uz")
                assert not errors,errors
                # Ensure only server-approved hidden form fields are present.
                assert await page.locator('input[name="csrf"]').count()==1
                assert await page.locator('input[name="request_id"]').count()==1
                assert await page.locator('form[action="/oauth/authorize"]').count()==1
                await page.screenshot(path=str(output/filename),full_page=True)
                await context.clear_cookies()
                await page.goto(ORIGIN+"/oauth/authorize?"+urlencode(QUERY))
                await page.wait_for_load_state("networkidle")
                await expect(page.locator('[data-i18n=mcpSignIn]')).to_be_visible()
                await expect(page.locator('a[href="/admin/"]')).to_have_attribute('target','_blank')
                assert await page.locator('input[name="csrf"]').count()==0
                await page.screenshot(path=str(output/("mcp-signin-"+str(width)+".png")),full_page=True)
                await context.add_cookies([{
                    "name":"__Host-hskai_admin","value":COOKIE,"domain":"hskai.app",
                    "path":"/","httpOnly":True,"secure":True,"sameSite":"Lax",
                }])
                await page.locator('#mcp-retry').click()
                await expect(page.locator('button[value="allow"]')).to_be_visible()
                await page.locator('button[value="allow"]').click()
                await expect(page.locator('[data-i18n=mcpRestart]')).to_be_visible()
                assert await page.locator('#mcp-retry').count()==0
                for locale in ('uz','ru','tj'):
                    await page.locator('#mcp-locale').select_option(locale)
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                await page.screenshot(path=str(output/("mcp-expired-"+str(width)+".png")),full_page=True)
                assert not errors,errors
                await context.close()
        finally:
            await browser.close()
    print("MCP consent UI: 1440px desktop and 390px iPhone, UZ/RU/TJ labels, accessibility and overflow checks passed")


if __name__=="__main__":
    asyncio.run(main())
