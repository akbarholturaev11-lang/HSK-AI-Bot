"""Actual binary upload, private preview, native passkey and payout transaction."""
import argparse
import asyncio
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport,AsyncClient
from playwright.async_api import async_playwright,expect
from sqlalchemy import func,select

from app.admin_api.pwa_bootstrap import create_admin_pwa_bootstrap_router
from app.admin_api.pwa_outbound import create_admin_pwa_outbound_router,create_message_drainer
from app.admin_api.pwa_partner_payouts import create_admin_pwa_partner_payouts_router
from app.admin_api.pwa_payout_completion import create_admin_pwa_payout_completion_router
from app.admin_api.pwa_read import create_admin_pwa_read_router
from app.admin_api.pwa_step_up_transport import create_admin_pwa_step_up_router
from app.admin_api.pwa_webauthn_login_transport import create_admin_pwa_passkey_login_router
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.partner import PartnerPayout
from tests.e2e.admin_pwa_browser import setup_fresh_login,authenticate_fresh_launch,wait_js
from tests.test_admin_pwa_payout_completion import CompletionTests,image_bytes

ORIGIN='https://hskai.app'


async def browser_checks(output):
    output.mkdir(parents=True,exist_ok=True)
    fixture=CompletionTests();await fixture.asyncSetUp()
    try:
        payout=await fixture.setup_payout();app=FastAPI()
        common=dict(settings_obj=fixture.settings,session_factory=fixture.sessions)
        uploaded=[];sent=[];calls=[];errors=[];drop_complete=False;hold_options=False
        options_started,options_release=asyncio.Event(),asyncio.Event()
        async def upload(proof):
            assert proof.raw==image_bytes();assert proof.actor_telegram_id==9001
            uploaded.append(proof);return 'PRIVATE_PROVIDER_REFERENCE'
        async def load(file_id):assert file_id=='PRIVATE_PROVIDER_REFERENCE';return image_bytes()
        async def emit(message):sent.append(message)
        drainer=create_message_drainer(**common,emit=emit)
        for factory in (create_admin_pwa_bootstrap_router,create_admin_pwa_read_router,
                        create_admin_pwa_partner_payouts_router,create_admin_pwa_passkey_login_router,
                        create_admin_pwa_step_up_router):app.include_router(factory(**common))
        app.include_router(create_admin_pwa_payout_completion_router(**common,upload=upload,loader=load,drainer=drainer))
        app.include_router(create_admin_pwa_outbound_router(**common,emit=emit,drainer=drainer))
        async def audit_count():
            async with fixture.sessions() as db:return await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit))
        async def serve(route):
            nonlocal drop_complete
            request=route.request;assert request.url.startswith(ORIGIN+'/')
            path=request.url.removeprefix(ORIGIN);calls.append(path)
            if path=='/admin/sw.js':await route.abort();return
            if path=='/api/admin/v1/statistics':
                await route.fulfill(status=200,json={'ok':True,'available':False});return
            async with AsyncClient(transport=ASGITransport(app=app),base_url=ORIGIN) as client:
                response=await client.request(request.method,path,headers=await request.all_headers(),content=request.post_data_buffer)
            if hold_options and path.endswith('/step-up/options'):
                options_started.set();await asyncio.wait_for(options_release.wait(),10)
            if drop_complete and path.endswith('/complete'):
                assert response.status_code==200,response.text
                drop_complete=False;await route.abort();return
            headers=dict(response.headers);headers.pop('content-length',None)
            cookies=response.headers.get_list('set-cookie')
            if cookies:headers['set-cookie']='\n'.join(cookies)
            await route.fulfill(status=response.status_code,headers=headers,body=response.content)
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            try:
                context=await browser.new_context(viewport={'width':1440,'height':1000},service_workers='block')
                await context.route('**/*',serve);page=await context.new_page()
                page.on('pageerror',lambda error:errors.append(str(error)))
                await page.add_init_script("window.cspFailures=[];document.addEventListener('securitypolicyviolation',e=>cspFailures.push(e.violatedDirective))")
                await setup_fresh_login(context,page,fixture)
                await page.goto(ORIGIN+'/admin/');await page.wait_for_load_state('networkidle');await authenticate_fresh_launch(page)
                async def editor():
                    await page.locator('.nav [data-route=marketing]').click()
                    await page.locator('[data-marketing-tab=partners]').click()
                    await page.locator('[data-action=payoutList]').click()
                    await page.locator(f'[data-payout-id="{payout}"]').click()
                    await expect(page.locator('#payoutProofFile')).to_be_visible()
                    await page.locator('#payoutProofFile').set_input_files({'name':'proof.png','mimeType':'image/png','buffer':image_bytes()})
                    await expect(page.locator('#payoutProofPreview img')).to_be_visible()
                    await expect(page.locator('[data-action=managementPrepare]')).to_be_enabled()
                for lang in ('uz','ru','tj'):
                    await page.set_viewport_size({'width':1440,'height':1000})
                    await page.locator('#locale').select_option(lang);await editor()
                    before=calls.count('/api/admin/v1/auth/step-up/options')
                    await page.set_viewport_size({'width':390,'height':844})
                    await expect(page.locator('#managementForm')).to_be_visible()
                    await expect(page.locator('[data-action=managementExecute]')).to_have_count(0)
                    await wait_js(page,"() => {const image=document.querySelector('#payoutProofPreview img');return image?.complete&&image.naturalWidth===40;}")
                    assert calls.count('/api/admin/v1/auth/step-up/options')==before
                    assert await audit_count()==0 and not sent
                    assert 'PRIVATE_PROVIDER_REFERENCE' not in await page.content()
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    await page.screenshot(path=str(output/f'payout-proof-single-window-{lang}-390.png'))
                    await page.locator('[data-action=close]').last.click()
                await page.set_viewport_size({'width':1440,'height':1000})
                await page.locator('#locale').select_option('uz');await editor()
                # The single-click path must not silently sign a target that
                # changed after the first window was shown.
                before=calls.count('/api/admin/v1/auth/step-up/options')
                async with fixture.sessions() as db:
                    (await db.get(PartnerPayout,payout)).note='Concurrent operator note';await db.commit()
                await page.locator('[data-action=managementPrepare]').click()
                await expect(page.locator('[data-payout-id]')).to_be_visible()
                assert calls.count('/api/admin/v1/auth/step-up/options')==before
                assert await audit_count()==0
                await page.locator('.drawer-close').click();await editor()
                # Closing while the backend prepares the native ceremony
                # aborts this action without a second application window.
                hold_options=True
                await page.locator('[data-action=managementPrepare]').click()
                await asyncio.wait_for(options_started.wait(),10)
                await expect(page.locator('#managementForm')).to_be_visible()
                await expect(page.locator('#payoutOperation')).to_be_disabled()
                await expect(page.locator('.management-comparison')).to_have_count(0)
                await expect(page.locator('[data-action=managementExecute]')).to_have_count(0)
                await page.locator('.drawer-close').click();hold_options=False;options_release.set()
                await page.wait_for_load_state('networkidle')
                assert await audit_count()==0 and not sent
                await editor()
                drop_complete=True
                await page.locator('[data-action=managementPrepare]').click()
                # A lost HTTP response after the payment was committed is NOT
                # positive confirmation. Show the uncertain state and require
                # explicit authoritative re-read; never auto-resubmit or show ✓.
                await expect(page.locator('#drawerContent')).to_contain_text(
                    await page.evaluate('window.HSKAI_ADMIN_I18N.uz.configUncertain'),timeout=15000)
                await expect(page.locator('.saved-animation')).to_have_count(0)
                await page.locator('.drawer-close').click()
                await page.locator('[data-action=payoutList]').click()
                await expect(page.locator('[data-payout-id]')).to_be_visible(timeout=15000)
                assert await audit_count()==1
                async with fixture.sessions() as db:assert (await db.get(PartnerPayout,payout)).status=='paid'
                assert len(sent)==1 and sent[0].telegram_id==7001 and sent[0].photo_file_id=='PRIVATE_PROVIDER_REFERENCE'
                await page.locator('[data-payout-id]').click()
                await expect(page.locator('#payoutProofFile')).to_have_count(0)
                assert calls.count('/api/admin/v1/partner-payouts/complete')==1
                assert calls.count('/api/admin/v1/auth/step-up/verify')==1
                assert len(uploaded)==6
                assert not errors,errors
                assert not await page.evaluate('cspFailures')
            finally:await browser.close()
        print('Payout completion: real upload/preview/WebAuthn, UZ/RU/TJ 390, cancel, one durable notice, lost-response no-retry passed')
    finally:await fixture.asyncTearDown()


async def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('/tmp/admin-pwa-payout-browser'))
    await browser_checks(parser.parse_args().output)


if __name__=='__main__':asyncio.run(main())
