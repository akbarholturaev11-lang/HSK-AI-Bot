"""Focused Smart editor QA: real ASGI SQL and browser WebAuthn signatures."""
import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from playwright.async_api import async_playwright, expect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.admin_api.pwa_notifications import create_admin_pwa_notifications_router
from app.db.base import Base
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.notification_template import NotificationTemplate
from app.db.models.smart_reminder_analysis import SmartReminderAnalysisMonthly
from tests.e2e.admin_pwa_browser import (
    Fixture, ORIGIN, authenticate_fresh_launch, setup_fresh_login, wait_js,
    create_admin_pwa_bootstrap_router, create_admin_pwa_read_router,
    create_admin_pwa_passkey_login_router, create_admin_pwa_step_up_router,
)
from tests.e2e.admin_pwa_step_up_gate import install_step_up_gate, finish_step_up


async def check(output):
    fixture=Fixture()
    fixture.engine=create_async_engine('sqlite+aiosqlite:///:memory:',poolclass=StaticPool)
    async with fixture.engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    fixture.sessions=async_sessionmaker(fixture.engine,expire_on_commit=False)
    await fixture.seed_payment()
    async with fixture.sessions.begin() as db:
        db.add(SmartReminderAnalysisMonthly(month=datetime.now(timezone.utc).date().replace(day=1),
            stage='contact_study_24h',channel='android',fact_count=7))
    fixture.settings.SMART_REMINDER_ANALYSIS_ENABLED=False
    app=FastAPI()
    for factory in (create_admin_pwa_bootstrap_router,create_admin_pwa_read_router,
                    create_admin_pwa_passkey_login_router,create_admin_pwa_step_up_router,
                    create_admin_pwa_notifications_router):
        app.include_router(factory(settings_obj=fixture.settings,session_factory=fixture.sessions))
    calls=[];failures=[]
    async def serve(route):
        request=route.request
        assert request.url.startswith(ORIGIN+'/'), request.url
        path=request.url.removeprefix(ORIGIN)
        if path=='/admin/sw.js': await route.abort();return
        calls.append(path)
        async with AsyncClient(transport=ASGITransport(app=app),base_url=ORIGIN) as client:
            response=await client.request(request.method,path,headers=await request.all_headers(),content=request.post_data_buffer)
        if response.status_code>=400: failures.append((path,response.status_code))
        headers=dict(response.headers);headers.pop('content-length',None)
        cookies=response.headers.get_list('set-cookie')
        if cookies: headers['set-cookie']='\n'.join(cookies)
        await route.fulfill(status=response.status_code,headers=headers,body=response.content)
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            context=await browser.new_context(viewport={'width':1440,'height':1000},service_workers='block')
            await context.route('**/*',serve)
            page=await context.new_page();errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('console',lambda message:errors.append(message.text) if message.type=='error' else None)
            await install_step_up_gate(page)
            await setup_fresh_login(context,page,fixture)
            await page.goto(ORIGIN+'/admin/');await authenticate_fresh_launch(page)
            errors.clear();failures.clear()  # Initial /me refusal triggers the genuine passkey login.
            await page.locator('[data-route=system]').first.click()
            for width in (1440,390):
                await page.set_viewport_size({'width':width,'height':1000})
                for lang in ('uz','ru','tj'):
                    if width==1440: await page.locator('#locale').select_option(lang)
                    else:
                        await page.locator('[data-action=more]').click()
                        await page.locator('#drawerLocale').select_option(lang)
                    await page.locator('[data-notice-key=smart_study]').click()
                    save=page.locator('[data-action=managementPrepare]')
                    await expect(save).to_be_disabled()
                    await expect(page.locator('#drawerFoot button')).to_have_count(1)
                    await expect(page.locator('.drawer-close')).to_have_count(1)
                    await expect(page.locator('.review-summary dd')).to_have_text([
                        await page.evaluate('(lang)=>HSKAI_ADMIN_I18N[lang].hsk30Off',lang),
                        datetime.now(timezone.utc).strftime('%Y-%m')+' · UTC','—','7','—'])
                    await page.locator('#noticeEnabled').select_option('false')
                    await expect(save).to_be_enabled()
                    await page.locator('#noticeEnabled').select_option('true')
                    await expect(save).to_be_disabled()
                    await page.locator('#noticeLanguage').select_option('ru' if lang!='ru' else 'tj')
                    await expect(save).to_be_disabled()
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    await page.screenshot(path=str(output/f'smart-{width}-{lang}.png'),full_page=True)
                    await page.locator('.drawer-close').click()
            # One real native ceremony; cancellation preserves the entire draft.
            await page.locator('[data-notice-key=smart_study]').click()
            await page.locator('#noticeEnabled').select_option('false')
            await page.locator('#noticeText').fill('<b>QA {lesson}</b>')
            await page.locator('[data-action=managementPrepare]').click()
            await wait_js(page,'() => window.stepUpWaiting===true')
            await page.evaluate('window.cancelStepUp()')
            await expect(page.locator('#noticeText')).to_have_value('<b>QA {lesson}</b>')
            await expect(page.locator('#noticeEnabled')).to_have_value('false')
            await page.locator('[data-action=managementPrepare]').click()
            await wait_js(page,'() => window.stepUpWaiting===true')
            await expect(page.locator('[data-action=managementExecute],.management-comparison')).to_have_count(0)
            await finish_step_up(page)
            await expect(page.locator('.save-success-drawer .saved-animation')).to_be_visible(timeout=15000)
            await expect(page.locator('#overlay')).to_have_count(0,timeout=6500)
            async with fixture.sessions() as db:
                row=await db.scalar(select(NotificationTemplate).where(NotificationTemplate.key=='smart_study'))
                assert row.enabled is False and row.text_tj=='<b>QA {lesson}</b>'
                assert await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit))==1
            await page.locator('[data-action=noticeList]').click()
            await expect(page.locator('#drawerContent [data-notice-key=smart_study]')).to_have_count(0)
            assert calls.count('/api/admin/v1/notifications/save')==1
            assert not errors, (errors,failures)
            await context.unroute_all(behavior='wait')
            await browser.close()
        print('Smart editor: real signed save, cancellation, 2.5s dismissal, single control, null/counts and UZ/RU/TJ at 1440/390 passed')
    finally: await fixture.engine.dispose()


async def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    output=Path(parser.parse_args().output);output.mkdir(parents=True,exist_ok=True)
    await check(output)


if __name__=='__main__': asyncio.run(main())
