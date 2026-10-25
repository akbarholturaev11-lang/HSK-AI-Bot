"""Actual ASGI/passkey outbound commands; synthetic provider, no external IO."""
import argparse
import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport,AsyncClient
from playwright.async_api import async_playwright,expect
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine
from sqlalchemy.pool import StaticPool

from app.admin_api.pwa_bootstrap import create_admin_pwa_bootstrap_router
from app.admin_api.pwa_read import create_admin_pwa_read_router
from app.admin_api.pwa_outbound import create_admin_pwa_outbound_router
from app.admin_api.pwa_step_up_transport import create_admin_pwa_step_up_router
from app.admin_api.pwa_webauthn_login_transport import create_admin_pwa_passkey_login_router
from app.db.base import Base
from app.db.models.user import User
from tests.e2e.admin_pwa_browser import setup_fresh_login, authenticate_fresh_launch
from tests.test_admin_pwa_payment_review import PaymentFixtures

ORIGIN='https://hskai.app'
ROOT=Path(__file__).resolve().parents[2]


from tests.e2e.admin_pwa_step_up_gate import install_step_up_gate, wait_step_up, finish_step_up


async def browser_checks(output):
    output.mkdir(parents=True,exist_ok=True)
    fixture=PaymentFixtures();fixture.engine=create_async_engine('sqlite+aiosqlite:///:memory:',poolclass=StaticPool)
    async with fixture.engine.begin() as connection:await connection.run_sync(Base.metadata.create_all)
    fixture.sessions=async_sessionmaker(fixture.engine,expire_on_commit=False);await fixture.seed_payment()
    async with fixture.sessions() as db:
        user=await db.get(User,2);user.full_name='Outbound QA';user.language='ru'
        db.add_all([User(id=i,telegram_id=2000+i,status='free',language='ru') for i in range(3,14)])
        await db.commit()
    app=FastAPI();common=dict(settings_obj=fixture.settings,session_factory=fixture.sessions)
    sent=[]
    async def emit(message):sent.append((message.user_id,message.language,message.text))
    for factory in (create_admin_pwa_bootstrap_router,create_admin_pwa_read_router,
                    create_admin_pwa_passkey_login_router,create_admin_pwa_step_up_router):
        app.include_router(factory(**common))
    app.include_router(create_admin_pwa_outbound_router(**common,emit=emit,drain_batches=1))
    calls=[];errors=[]
    async def serve(route):
        request=route.request;assert request.url.startswith(ORIGIN+'/')
        path=request.url.removeprefix(ORIGIN)
        if path=='/admin/sw.js':await route.abort();return
        calls.append((path,request.post_data_json if request.method=='POST' else None))
        if path=='/api/admin/v1/statistics':
            await route.fulfill(status=200,json={'ok':True,'available':False});return
        async with AsyncClient(transport=ASGITransport(app=app),base_url=ORIGIN) as client:
            response=await client.request(request.method,path,headers=await request.all_headers(),content=request.post_data_buffer)
        headers=dict(response.headers);headers.pop('content-length',None)
        cookies=response.headers.get_list('set-cookie')
        if cookies:headers['set-cookie']='\n'.join(cookies)
        await route.fulfill(status=response.status_code,headers=headers,body=response.content)
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            try:
                context=await browser.new_context(viewport={'width':1440,'height':1000},service_workers='block')
                await context.route('**/*',serve);page=await context.new_page();await install_step_up_gate(page)
                page.on('pageerror',lambda error:errors.append(str(error)))
                await page.add_init_script("window.cspFailures=[];document.addEventListener('securitypolicyviolation',e=>cspFailures.push(e.violatedDirective))")
                await setup_fresh_login(context,page,fixture)
                async def login():
                    await authenticate_fresh_launch(page)
                    await expect(page.locator('.sidebar')).to_be_visible(timeout=15000)
                async def marketing():
                    await page.locator('.nav [data-route=marketing]').click()
                    await page.locator('[data-action=messageList]').click()
                async def fill_three():
                    for lang in ('uz','ru','tj'):
                        await page.locator('#messageLanguage').select_option(lang)
                        await page.locator('#messageText').fill('QA '+lang+' <b>你好</b>')
                async def confirm():
                    await page.locator('[data-action=managementPrepare]').click()
                    await wait_step_up(page)
                    await finish_step_up(page)
                    await expect(page.locator('[data-message-job]')).to_be_visible(timeout=15000)
                await page.goto(ORIGIN+'/admin/');await page.wait_for_load_state('networkidle');await login()
                for language in ('uz','ru','tj'):
                    await page.locator('#locale').select_option(language)
                    await page.locator('.nav [data-route=users]').click()
                    await page.locator('[data-user-detail="2"]:visible').click()
                    await page.locator('[data-menu-toggle=userManagementMenu]').click()
                    await page.locator('[data-message-user="2"]').click()
                    await page.locator('#messageText').fill('QA <img src=x onerror=alert(1)>')
                    await page.set_viewport_size({'width':390,'height':844})
                    before=len([p for p,_ in calls if p.endswith('step-up/options')])
                    await page.locator('[data-action=managementPrepare]').click()
                    await wait_step_up(page)
                    assert await page.locator('#drawerContent img').count()==0
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    assert len([p for p,_ in calls if p.endswith('step-up/options')])==before+1
                    await page.screenshot(path=str(output/f'direct-message-confirm-{language}-390.png'))
                    await page.locator('.drawer-close').click()
                    await page.set_viewport_size({'width':1440,'height':1000})
                await page.locator('#locale').select_option('uz');await marketing()
                await page.locator('[data-action=messageEditor]').click()
                await page.locator('#messageKind').select_option('test');await fill_three();await confirm()
                assert len(sent)==1 and sent[0][0]==101
                await page.locator('.drawer-close').click();await marketing()
                await page.locator('[data-action=messageEditor]').click();await fill_three()
                await page.locator('#messageFilters summary').click()
                await page.locator('[data-message-language=ru]').check()
                await page.locator('[data-action=managementPrepare]').click()
                await wait_step_up(page)
                await page.screenshot(path=str(output/'broadcast-confirm-uz.png'))
                baseline=len(sent)
                await finish_step_up(page)
                await expect(page.locator('[data-message-run]')).to_be_visible(timeout=15000)
                assert len(sent)-baseline==10
                job=await page.locator('[data-message-run]').get_attribute('data-message-run')
                # A normal reload must retain this verified session and
                # expose the next-batch action without another passkey.
                prior_verifications=len([p for p,_ in calls if p.endswith('login/verify')])
                await page.reload();await login();await marketing()
                await page.locator(f'[data-message-job="{job}"]').click()
                await expect(page.locator('[data-message-run]')).to_be_visible()
                assert len([p for p,_ in calls if p.endswith('login/verify')])==prior_verifications
                # Explicit logout deliberately ends the job's browser session.
                # Reauthentication uses a fresh WebAuthn session, so the
                # existing cross-session control must require a signed resume.
                await page.locator('.drawer-close').click()
                await page.locator('.side-foot [data-action=logout]').click()
                await expect(page.locator('[data-action=signin]')).to_be_visible()
                await page.reload();await login();await marketing()
                await page.locator(f'[data-message-job="{job}"]').click()
                await expect(page.locator('[data-message-run]')).to_have_count(0)
                await expect(page.locator('[data-message-control=resume]')).to_be_visible()
                await page.locator('[data-message-control=resume]').click();await confirm()
                assert len(sent)-baseline==12
                assert len({row[0] for row in sent[baseline:]})==12
                await expect(page.locator('[data-message-run]')).to_have_count(0)
                assert not errors,errors
                assert not await page.evaluate('cspFailures')
            finally:await browser.close()
    finally:await fixture.engine.dispose()
    print('Outbound: real ASGI + fresh WebAuthn; UZ/RU/TJ mobile review, self-test, bounded broadcast and signed cross-session resume passed')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    asyncio.run(browser_checks(parser.parse_args().output))
