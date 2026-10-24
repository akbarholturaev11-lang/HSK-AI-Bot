"""Synthetic browser QA with real SQL + WebAuthn server verification.

No network/provider calls: https://hskai.app requests are served by ASGI in
memory. Chromium's virtual authenticator is NOT physical biometric evidence.
Run: python -m tests.e2e.admin_pwa_browser --output /tmp/admin-pwa-browser
"""
import argparse
import asyncio
import base64
import io
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import socket
import uvicorn
from types import SimpleNamespace
from fastapi.responses import JSONResponse
from unittest.mock import AsyncMock, patch
from PIL import Image, ImageDraw

from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from playwright.async_api import async_playwright, expect
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.ai_usage import AIUsageEvent
from app.db.models.bot_feedback import BotFeedback
from app.db.models.course_progress import CourseProgress
from app.db.models.payment import Payment
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackResponse
from app.db.models.user import User
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriageAudit
from app.db.models.admin_pwa_payment_review import AdminPwaPaymentReview
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.admin_api.pwa_approval import start_pwa_approval, approve_pwa_approval
from app.admin_api.pwa_enrollment_transport import create_admin_pwa_completion_router
from app.admin_api.pwa_webauthn_transport import create_admin_pwa_webauthn_router
from app.admin_api.pwa_bootstrap import create_admin_pwa_bootstrap_router
from app.admin_api.pwa_google_transport import create_admin_pwa_google_router
from app.admin_api.pwa_webauthn_login_transport import create_admin_pwa_passkey_login_router
from app.admin_api.pwa_step_up_transport import create_admin_pwa_step_up_router
from app.admin_api.pwa_payment_review_transport import create_admin_pwa_payment_review_router
from app.admin_api.pwa_payment_receipts import create_admin_pwa_receipt_router, download_receipt_image
from app.admin_api.pwa_mcp_management import create_admin_pwa_mcp_management_router
from app.admin_api.pwa_mcp_oauth import begin_mcp_authorization, decide_mcp_consent, exchange_mcp_code, pkce_s256
from app.admin_api.pwa_mcp_resource import verify_readonly_mcp_bearer
from app.admin_api.pwa_read import create_admin_pwa_read_router
from app.admin_api.pwa_access_grants import create_admin_pwa_access_grant_router
from app.admin_api.pwa_feedback_analytics import create_admin_pwa_feedback_analytics_router
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.admin_api.pwa_inbox_triage import create_admin_pwa_inbox_triage_router
from app.admin_api.pwa_inbox_attachments import create_admin_pwa_inbox_attachment_router
from tests.test_admin_pwa_payment_review import PaymentFixtures, COOKIE
from tests.test_admin_pwa_webauthn_crypto_vectors import CRED_ID, HANDLE
from tests.test_admin_pwa_receipts import png

ORIGIN='https://hskai.app'


async def wait_js(page, predicate):
    # Playwright 1.56 wait_for_function internally calls in-page eval, which
    # strict CSP correctly blocks on Linux. Direct debugger evaluation avoids
    # that helper path without changing/bypassing the app's CSP.
    async with asyncio.timeout(10):
        while not await page.evaluate(predicate):
            await asyncio.sleep(.025)


class Fixture(PaymentFixtures):
    pass


async def browser_checks(output):
    fixture=Fixture()
    fixture.engine=create_async_engine('sqlite+aiosqlite:///:memory:',poolclass=StaticPool)
    async with fixture.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    fixture.sessions=async_sessionmaker(fixture.engine,expire_on_commit=False)
    await fixture.seed_payment()
    async with fixture.sessions() as db:
        (await db.get(User,1)).full_name='<img src=x onerror=alert(1)> QA account'
        db.add(CourseProgress(user_id=1,level='HSK1',completed_lessons_count=7))
        db.add(AIUsageEvent(user_id=1,source='qa',model='fixture',cost_usd=.025,total_tokens=123))
        db.add(BotFeedback(user_id=1,telegram_id=1001,status='completed',disliked_code='price',
                           disliked_text='<script>private QA feedback</script>',
                           completed_at=datetime.now(timezone.utc)))
        db.add(BotFeedback(user_id=2,telegram_id=2002,status='completed',disliked_text='other account QA feedback'))
        for index in range(11):
            db.add(Payment(user_id=1,amount=index+1,currency='TJS',plan_type='1_month',payment_status='approved'))
        await db.execute(update(AdminPwaSession).values(revoked_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc)))
        await db.commit()
    settings=fixture.settings
    settings.ADMIN_PWA_MCP_ENABLED=True
    settings.ADMIN_PWA_MCP_TRANSPORT_ENABLED=True
    settings.ADMIN_PWA_MCP_RESOURCE=ORIGIN+'/mcp'
    settings.ADMIN_PWA_MCP_CLIENT_ID='synthetic-browser-client'
    settings.ADMIN_PWA_MCP_REDIRECT_URI='https://registered-client.example/callback'
    settings.GOOGLE_DESKTOP_CLIENT_ID="synthetic-browser-client"
    settings.DESKTOP_AUTH_SIGNING_SECRET="H"*64
    app=FastAPI()
    common={'settings_obj':settings,'session_factory':fixture.sessions}
    for factory in (create_admin_pwa_bootstrap_router,create_admin_pwa_google_router,
                    create_admin_pwa_passkey_login_router,create_admin_pwa_step_up_router,
                    create_admin_pwa_payment_review_router,create_admin_pwa_read_router,
                    create_admin_pwa_feedback_analytics_router,create_admin_pwa_inbox_triage_router,
                    create_admin_pwa_completion_router,create_admin_pwa_webauthn_router,
                    create_admin_pwa_mcp_management_router):
        app.include_router(factory(**common))
    app.include_router(create_admin_pwa_receipt_router(**common,loader=AsyncMock(return_value=(png(),'image/png'))))
    calls=[];drop_review=False;fail_reads=False;fail_prepare=False;receipt_failure=False
    hold_boot_unread=False
    unread_paused,release_unread=asyncio.Event(),asyncio.Event()
    async def serve(route):
        nonlocal drop_review,hold_boot_unread
        request=route.request
        path=request.url.removeprefix(ORIGIN)
        if not request.url.startswith(ORIGIN+'/'):
            raise AssertionError('Unexpected external browser request')
        if path=='/admin/sw.js':
            await route.abort();return
        calls.append((path,request.method,request.post_data_json if request.method=='POST' else None))
        if fail_reads and path=='/api/admin/v1/statistics':
            await route.fulfill(status=503,json={'ok':False,'error':'synthetic_failure'});return
        if fail_prepare and path=='/api/admin/v1/payments/prepare-review':
            await route.fulfill(status=503,json={'ok':False,'error':'synthetic_failure'});return
        if receipt_failure and '/receipt?' in path:
            await route.fulfill(status=503,json={'ok':False});return
        async with AsyncClient(transport=ASGITransport(app=app),base_url=ORIGIN) as client:
            response=await client.request(request.method,path,headers=await request.all_headers(),content=request.post_data_buffer)
        if hold_boot_unread and path=='/api/admin/v1/inbox/unread-count':
            hold_boot_unread=False
            unread_paused.set()
            await release_unread.wait()
        headers=dict(response.headers)
        headers.pop('content-length',None)
        cookies=response.headers.get_list('set-cookie')
        if cookies:headers['set-cookie']='\n'.join(cookies)
        if drop_review and path=='/api/admin/v1/payments/review':
            drop_review=False
            await route.abort();return
        if response.status_code>=400 and '/auth/step-up/' in path:print('Step-up failure',response.status_code,response.text,flush=True)
        await route.fulfill(status=response.status_code,headers=headers,body=response.content)
    async with async_playwright() as pw:
        browser=await pw.chromium.launch()
        context=await browser.new_context(viewport={'width':1440,'height':1000},service_workers='block')
        await context.route('**/*',serve)
        page=await context.new_page()
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        await page.add_init_script("window.cspFailures=[];document.addEventListener('securitypolicyviolation',e=>window.cspFailures.push(e.violatedDirective));")
        cdp=await context.new_cdp_session(page)
        await cdp.send('WebAuthn.enable')
        auth=await cdp.send('WebAuthn.addVirtualAuthenticator',{'options':{
            'protocol':'ctap2','transport':'internal','hasResidentKey':True,
            'hasUserVerification':True,'isUserVerified':True,'automaticPresenceSimulation':True}})
        auth_id=auth['authenticatorId']
        b64=lambda value:base64.b64encode(value).decode()
        await cdp.send('WebAuthn.addCredential',{'authenticatorId':auth_id,'credential':{
            'credentialId':b64(CRED_ID),'isResidentCredential':True,'rpId':'hskai.app',
            'privateKey':b64(fixture.key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())),
            'userHandle':b64(HANDLE),'signCount':0,'userName':'synthetic-admin','userDisplayName':'Synthetic QA'}})
        await page.goto(ORIGIN+'/admin/')
        await expect(page.locator('[data-action=signin]')).to_be_visible()
        assert not any(path.endswith('step-up/options') for path,_,_ in calls)
        await page.locator('[data-action=signin]').click()
        await expect(page.locator('.sidebar')).to_be_visible(timeout=20000)
        # Push flag defaults OFF: no button and no subscription/permission flow.
        await expect(page.locator('[data-action=pushSettings]')).to_have_count(0)
        assert not any('/push/' in path for path,_,_ in calls)
        assert any(path.endswith('login/verify') for path,_,_ in calls)
        cookies=await context.cookies()
        assert any(row['name']=='__Host-hskai_admin' and row['httpOnly'] and row['secure'] for row in cookies)
        assert '__Host-hskai_admin=' not in await page.evaluate('document.cookie')
        await expect(page.locator('.metric')).to_have_count(4)
        await expect(page.locator('.stat-detail')).to_have_count(3)
        await expect(page.locator('.stat-detail').first).to_contain_text('0.025 USD')
        await page.screenshot(path=str(output/'desktop-statistics.png'),full_page=True)
        await page.locator('#locale').select_option('ru')
        await expect(page.locator('html')).to_have_attribute('lang','ru')
        await page.locator('#locale').select_option('tj')
        await expect(page.locator('html')).to_have_attribute('lang','tg')
        await page.locator('#locale').select_option('uz')
        await page.locator('[data-action=platform]').click()
        await page.locator('[data-platform=iphone_pwa]').click()
        await expect(page.locator('#content .state-panel')).to_be_visible()
        await expect(page.locator('.metric')).to_have_count(0)
        await page.locator('[data-action=platform]').click()
        await page.locator('[data-platform=overall]').click()
        await expect(page.locator('.metric')).to_have_count(4)
        await page.locator('[data-action=period]').click()
        await page.locator('[data-period=all_time]').click()
        await expect(page.locator('.metric')).to_have_count(4)
        label=await page.evaluate('window.HSKAI_ADMIN_I18N.uz.active30')
        await expect(page.locator('.metric').nth(2)).to_contain_text(label)
        fail_reads=True
        await page.locator('[data-route=stats]').first.click()
        await expect(page.locator('[data-action=reload]')).to_be_visible()
        fail_reads=False
        await page.locator('[data-action=reload]').click()
        await expect(page.locator('.metric')).to_have_count(4)
        await page.locator('[data-route=users]').first.click()
        await expect(page.locator('.data-table tbody tr')).to_have_count(3)
        await expect(page.locator('.data-table img')).to_have_count(0)
        await page.locator('#userQuery').fill('999999')
        await page.locator('#searchForm button').click()
        await expect(page.locator('.data-table')).to_have_count(0)
        await page.locator('#userQuery').fill('1')
        await page.locator('#searchForm button').click()
        await expect(page.locator('.data-table tbody tr')).to_have_count(1)
        await page.locator('.user-table [data-user-detail="1"]').click()
        await expect(page.locator('#drawerTitle')).to_have_text('Foydalanuvchi profili')
        await expect(page.locator('#drawerContent')).to_contain_text('<img src=x onerror=alert(1)> QA account')
        await expect(page.locator('#drawerContent img')).to_have_count(0)
        await expect(page.locator('#profilePayments article')).to_have_count(10)
        await page.locator('[data-profile-payments]').click()
        await expect(page.locator('#profilePayments article')).to_have_count(2)
        await expect(page.locator('[data-profile-payments]')).to_have_count(0)
        await page.screenshot(path=str(output/'desktop-user-profile.png'),full_page=True)
        await page.locator('[data-user-feedback]').click()
        await expect(page.locator('#drawerContent')).to_contain_text('<script>private QA feedback</script>')
        await expect(page.locator('#drawerContent')).not_to_contain_text('other account QA feedback')
        baseline_inbox_rows = await page.locator('.inbox-feedback-item').count()
        assert baseline_inbox_rows >= 1
        await page.locator('#inboxSearchQuery').fill('private')
        await page.locator('#inboxSearchForm button').click()
        await expect(page.locator('.inbox-feedback-item')).to_have_count(1)
        assert any(path.endswith('/inbox/list') and body.get('search')=='private'
                   and body.get('user_id')==1 for path,_,body in calls if isinstance(body,dict))
        await page.locator('#inboxSearchQuery').fill('doesnotexist')
        await page.locator('#inboxSearchForm button').click()
        await expect(page.locator('.inbox-feedback-item')).to_have_count(0)
        await page.locator('#inboxSearchQuery').fill('')
        await page.locator('#inboxSearchForm button').click()
        await expect(page.locator('.inbox-feedback-item')).to_have_count(baseline_inbox_rows)
        await page.locator('[data-source=release]').click()
        assert calls[-1][2]['user_id']==1
        await page.locator('.drawer-close').click()
        await page.set_viewport_size({'width':390,'height':844})
        await page.screenshot(path=str(output/'mobile-users.png'),full_page=True)
        for language in ('uz','ru','tj'):
            if language!='uz':
                await page.locator('[data-action=more]').click()
                await page.locator('#drawerLocale').select_option(language)
            await page.locator('.user-cards [data-user-detail="1"]').click()
            await expect(page.locator('#profilePayments article')).to_have_count(10)
            await page.screenshot(path=str(output/f'mobile-user-profile-{language}.png'),full_page=True)
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            await page.locator('.drawer-close').click()
        await page.locator('[data-action=more]').click()
        await page.locator('#drawerLocale').select_option('uz')
        await page.locator('[data-route=stats]').last.click()
        await expect(page.locator('.stat-detail')).to_have_count(4)
        await expect(page.locator('.feedback-analysis')).to_contain_text('Шикоятлар таҳлили')
        await expect(page.locator('.feedback-analysis')).to_contain_text('Нарх')
        await page.screenshot(path=str(output/'mobile-statistics-details.png'),full_page=True)
        assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        await page.locator('[data-route=payments]').last.click()
        await expect(page.locator('[data-review]')).to_have_count(1)
        receipt_failure=True
        await page.locator('[data-review]').click()
        await expect(page.locator('[data-action=approve]')).to_be_disabled()
        await page.locator('.drawer-close').click()
        receipt_failure=False
        await page.locator('[data-review]').click()
        await expect(page.locator('[data-action=approve]')).to_be_enabled()
        await page.locator('[data-action=reject]').click()
        await expect(page.locator('#rejectReason')).to_be_focused()
        assert not any(path.endswith('step-up/options') for path,_,_ in calls)
        fail_prepare=True
        await page.locator('[data-action=approve]').click()
        await expect(page.locator('[data-action=execute]')).to_have_count(0)
        await page.locator('.drawer-close').click()
        fail_prepare=False
        await page.locator('[data-review]').click()
        await expect(page.locator('[data-action=approve]')).to_be_enabled()
        await page.screenshot(path=str(output/'mobile-payment-receipt.png'),full_page=True)
        await page.locator('[data-action=approve]').click()
        await expect(page.locator('[data-action=execute]')).to_be_enabled()
        await expect(page.locator('.amount-value')).to_have_text('100 TJS')
        await page.screenshot(path=str(output/'mobile-payment-confirmation.png'),full_page=True)
        assert not any(path.endswith('step-up/options') for path,_,_ in calls)
        await page.locator('[data-action=execute]').click()
        try:await expect(page.locator('[data-review]')).to_have_count(0,timeout=20000)
        except AssertionError:
            print(await page.locator('#dialogs').inner_text(),[p for p,_,_ in calls],flush=True)
            await page.screenshot(path=str(output/'failure.png'),full_page=True)
            raise
        async with fixture.sessions() as db:
            assert (await db.get(Payment,fixture.payment_id)).payment_status=='approved'
            assert await db.scalar(select(func.count()).select_from(AdminPwaPaymentReview))==1
            assert (await db.get(User,1)).end_date is not None
        writes=[body for path,_,body in calls if path.endswith('/payments/review')]
        operations=[body for path,_,body in calls if path.endswith('step-up/options')]
        assert len(writes)==len(operations)==1
        assert {k:v for k,v in writes[0].items() if k!='step_up_id'}==operations[0]['payload']
        await page.locator('.drawer-close').click()
        # Rejected payment uses a new ceremony and the exact visible reason.
        async with fixture.sessions() as db:
            payment=Payment(user_id=2,amount=10,currency='USD',plan_type='10_days',payment_method='visa',payment_status='pending',screenshot_file_id='synthetic-receipt')
            db.add(payment);await db.flush();second_id=payment.id;await db.commit()
        await page.locator('[data-route=payments]').last.click()
        await expect(page.locator('[data-review]')).to_have_count(1)
        await page.locator('[data-review]').click()
        await expect(page.locator('[data-action=reject]')).to_be_enabled()
        await page.locator('#rejectReason').fill('Synthetic QA duplicate')
        await page.locator('[data-action=reject]').click()
        await expect(page.locator('.review-summary')).to_contain_text('Synthetic QA duplicate')
        # A lost HTTP response AFTER a real commit must not resend the write.
        drop_review=True
        await page.locator('[data-action=execute]').click()
        await expect(page.locator('[data-review]')).to_have_count(0,timeout=20000)
        assert len([p for p,_,_ in calls if p.endswith('/payments/review')])==2
        async with fixture.sessions() as db:
            assert (await db.get(Payment,second_id)).payment_status=='rejected'
            assert await db.scalar(select(func.count()).select_from(AdminPwaPaymentReview))==2
        await page.locator('.drawer-close').click()
        async with fixture.sessions() as db:
            db.add(Payment(user_id=2,amount=10,currency='USD',plan_type='10_days',payment_method='visa',payment_status='pending',screenshot_file_id='synthetic-receipt'))
            await db.commit()
        await page.locator('[data-route=payments]').last.click()
        await expect(page.locator('[data-review]')).to_have_count(1)
        await page.locator('[data-review]').click()
        await expect(page.locator('[data-action=approve]')).to_be_enabled()
        await page.locator('[data-action=approve]').click()
        # Delay an OLD rejected native promise across a NEW prompt. Closing
        # the new drawer must still abort its own controller (not lose it to
        # the old promise's finally). Native signatures are never fabricated.
        await page.evaluate("""()=>{
            window.qaNativeGet=navigator.credentials.get.bind(navigator.credentials);
            window.qaAbortCount=0;window.qaNativeCalls=0;window.qaDelayFirst=true;window.qaRelease=null;
            navigator.credentials.get=async options=>{
                window.qaNativeCalls++;const delayed=window.qaDelayFirst;window.qaDelayFirst=false;
                options.signal.addEventListener('abort',()=>window.qaAbortCount++);
                try{return await window.qaNativeGet(options);}
                catch(error){if(delayed)await new Promise(resolve=>window.qaRelease=resolve);throw error;}
            };
        }""")
        await cdp.send('WebAuthn.setAutomaticPresenceSimulation',{'authenticatorId':auth_id,'enabled':False})
        async with page.expect_response('**/auth/step-up/options'):
            await page.locator('[data-action=execute]').click()
        await wait_js(page,'() => window.qaNativeCalls===1')
        await page.locator('.drawer-close').click()
        await expect(page.locator('[data-review]')).to_have_count(1)
        await wait_js(page,'() => !!window.qaRelease')
        await page.locator('[data-review]').click()
        await expect(page.locator('[data-action=approve]')).to_be_enabled()
        await page.locator('[data-action=approve]').click()
        async with page.expect_response('**/auth/step-up/options'):
            await page.locator('[data-action=execute]').click()
        await wait_js(page,'() => window.qaNativeCalls===2')
        await page.evaluate('window.qaRelease()')
        await page.locator('.drawer-close').click()
        await wait_js(page,'() => window.qaAbortCount===2')
        await page.evaluate('()=>{navigator.credentials.get=window.qaNativeGet;}')
        assert len([p for p,_,_ in calls if p.endswith('/payments/review')])==2
        await cdp.send('WebAuthn.setAutomaticPresenceSimulation',{'authenticatorId':auth_id,'enabled':True})
        await page.locator('[data-action=feedback]').click()
        await expect(page.locator('.inbox-shell')).to_be_visible()
        for source in ('bot', 'release', 'android', 'payment', 'all'):
            await page.locator(f'[data-source={source}]').click()
            await expect(page.locator('.inbox-shell')).to_be_visible()
            assert 'primary' in (await page.locator(f'[data-source={source}]').get_attribute('class'))
        # Real count uses all eligible source records, not the visible 30-row page.
        await wait_js(page, "() => !!document.querySelector('[data-action=feedback] .top-icon-badge')")
        assert (await page.locator('[data-action=feedback] .top-icon-badge').inner_text())=='3'
        await page.locator('[data-inbox-priority=important]').click()
        await expect(page.locator('.inbox-shell')).to_be_visible()
        assert await page.locator('.inbox-shell .feedback-item').count()==1
        await expect(page.locator('.inbox-shell')).to_contain_text('Тўлов чеклари')
        await page.locator('[data-inbox-priority=all]').click()
        await expect(page.locator('.inbox-shell .feedback-item')).to_have_count(3)
        # The 390px viewport mirrors the installed iPhone PWA layout.
        assert page.viewport_size['width']==390
        assert await page.locator('[data-inbox-op=mark_read]').first.evaluate(
            '(element) => element.getBoundingClientRect().height >= 44')
        await page.screenshot(path=str(output/'mobile-inbox-triage.png'),full_page=True)
        async def wait_for_inbox_audit(expected):
            async with asyncio.timeout(12):
                while True:
                    async with fixture.sessions() as db:
                        actual=await db.scalar(select(func.count()).select_from(AdminPwaInboxTriageAudit))
                    if actual==expected:
                        return
                    await asyncio.sleep(.04)
        await page.locator('[data-inbox-op=mark_read]').first.click()
        await wait_for_inbox_audit(1)
        await wait_js(page, "() => !!document.querySelector('[data-action=feedback] .top-icon-badge') && document.querySelector('[data-action=feedback] .top-icon-badge').textContent === '2'")
        await wait_js(page, "() => !!document.querySelector('.inbox-drawer button[data-inbox-op=assign_self]:not(:disabled)')")
        await page.locator('[data-inbox-op=assign_self]').first.click()
        await wait_for_inbox_audit(2)
        await wait_js(page, "() => !!document.querySelector('.inbox-drawer button[data-inbox-op=resolve]:not(:disabled)')")
        assert len([path for path,_,_ in calls if path.endswith('/inbox/triage')]) == 2
        await page.keyboard.press('Escape')
        # Apple notificationclick always uses a fixed /admin/?inbox=1 link.
        # A valid passkey session must be verified before showing private inbox.
        await page.goto(ORIGIN+'/admin/?inbox=1')
        await expect(page.locator('.inbox-shell')).to_be_visible()
        assert page.url==ORIGIN+'/admin/'
        await page.keyboard.press('Escape')
        # Actual consent/code/token services seed one synthetic connection;
        # the V10 drawer calls real session-bound management and audit services.
        cookie=next(row['value'] for row in await context.cookies() if row['name']=='__Host-hskai_admin')
        async with fixture.sessions() as db:
            pending=await begin_mcp_authorization(db,session_cookie=cookie,
                client_id=settings.ADMIN_PWA_MCP_CLIENT_ID,
                redirect_uri=settings.ADMIN_PWA_MCP_REDIRECT_URI,
                resource=ORIGIN+'/mcp',scope='admin:analytics:read',state='state-'+'s'*44,
                code_challenge=pkce_s256('v'*64),code_challenge_method='S256',settings_obj=settings)
        assert pending
        async with fixture.sessions() as db:
            code=await decide_mcp_consent(db,request_id=pending.request_id,session_cookie=cookie,
                approved=True,csrf_proof=pending.csrf_proof,settings_obj=settings)
        async with fixture.sessions() as db:
            token=await exchange_mcp_code(db,code=code.code,code_verifier='v'*64,
                client_id=settings.ADMIN_PWA_MCP_CLIENT_ID,redirect_uri=settings.ADMIN_PWA_MCP_REDIRECT_URI,
                resource=ORIGIN+'/mcp',settings_obj=settings)
        async def open_connections(width):
            if width<760:
                await page.locator('[data-action=more]').click()
                await page.locator('#dialogs [data-action=mcpConnections]').click()
            else:
                await page.locator('.sidebar [data-action=mcpConnections]').click()
            await expect(page.locator('[data-mcp-revoke]')).to_be_visible()
        async def set_mcp_locale(locale,width):
            if width<760:
                await page.locator('[data-action=more]').click()
                await page.locator('#drawerLocale').select_option(locale)
            else:
                await page.locator('#locale').select_option(locale)
        for width in (1440,390):
            await page.set_viewport_size({'width':width,'height':900})
            for locale in ('uz','ru','tj'):
                await set_mcp_locale(locale,width)
                await open_connections(width)
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                await expect(page.locator('.mcp-client-name')).to_contain_text('synthetic-browser-client')
                await page.screenshot(path=str(output/f'mcp-history-{width}-{locale}.png'),full_page=True)
                await page.keyboard.press('Escape')
        await set_mcp_locale('uz',390)
        await open_connections(390)
        await page.locator('[data-mcp-revoke]').click()
        await expect(page.locator('[data-action=mcpRevokeConfirm]')).to_be_visible()
        await page.keyboard.press('Escape')
        async with fixture.sessions() as db:
            assert await verify_readonly_mcp_bearer(db,authorization='Bearer '+token.token,settings_obj=settings)
        await open_connections(390)
        await page.locator('[data-mcp-revoke]').click()
        await page.locator('[data-action=mcpRevokeConfirm]').click()
        await expect(page.locator('[data-mcp-revoke]')).to_have_count(0)
        await expect(page.locator('.mcp-history')).to_contain_text('Ruxsat bekor qilingan')
        async with fixture.sessions() as db:
            assert await verify_readonly_mcp_bearer(db,authorization='Bearer '+token.token,settings_obj=settings) is None
        await page.keyboard.press('Escape')
        await page.set_viewport_size({'width':390,'height':844})
        # Offline clears private DOM and return requires current session.
        await context.set_offline(True)
        await expect(page.locator('.sidebar')).to_have_count(0)
        await expect(page.locator('.auth-panel')).to_be_visible()
        await context.set_offline(False)
        await expect(page.locator('.sidebar')).to_have_count(1)
        async with fixture.sessions() as db:
            await db.execute(update(AdminPwaSession).values(revoked_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc)));await db.commit()
        await page.locator('[data-route=users]').last.click()
        await expect(page.locator('[data-action=signin]')).to_be_visible()
        assert 'QA account' not in await page.locator('body').inner_text()
        assert await page.evaluate('Object.keys(localStorage)')==['hsk-admin-locale']
        assert not await page.evaluate('window.cspFailures')
        assert not errors,errors
        # Synthetic approved OIDC/Bot proof is seeded by existing services;
        # Google and Telegram NETWORK/provider checks remain staging QA.
        async with fixture.sessions() as db:
            pending=await start_pwa_approval(db,verified_google_subject_hash='a'*64,
                verified_google_audience=settings.GOOGLE_DESKTOP_CLIENT_ID)
        async with fixture.sessions() as db:
            assert await approve_pwa_approval(db,request_id=pending.request_id,
                verified_bot_telegram_id=9001,settings_obj=settings)
        onboarding=await browser.new_context(viewport={'width':390,'height':844},service_workers='block')
        await onboarding.route('**/*',serve)
        await onboarding.add_cookies([{'name':name,'value':value,'url':ORIGIN,'httpOnly':True,'secure':True,'sameSite':'Lax'}
            for name,value in [('__Host-hskai_admin_request',pending.request_id),('__Host-hskai_admin_approval',pending.browser_proof)]])
        enrolled=await onboarding.new_page()
        enrolled.on('pageerror',lambda error:errors.append(str(error)))
        enroll_cdp=await onboarding.new_cdp_session(enrolled)
        await enroll_cdp.send('WebAuthn.enable')
        await enroll_cdp.send('WebAuthn.addVirtualAuthenticator',{'options':{
            'protocol':'ctap2','transport':'internal','hasResidentKey':True,
            'hasUserVerification':True,'isUserVerified':True,'automaticPresenceSimulation':True}})
        await enrolled.goto(ORIGIN+'/admin/')
        await expect(enrolled.locator('[data-action=enroll]')).to_be_visible()
        await enrolled.locator('[data-action=enroll]').click()
        await expect(enrolled.locator('[data-action=signin]')).to_be_visible(timeout=20000)
        async with fixture.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(AdminPwaCredential))==2
        # A visible authenticated shell precedes the end of boot's last read.
        # Hold that response so the More click cannot be lost to busy=true.
        hold_boot_unread=True
        await enrolled.locator('[data-action=signin]').click()
        try:
            await asyncio.wait_for(unread_paused.wait(),20)
            await expect(enrolled.locator('.mobile-tabs')).to_be_visible(timeout=20000)
            await expect(enrolled.locator('[data-action=more]')).to_be_disabled()
        finally:
            release_unread.set()
        await expect(enrolled.locator('[data-action=more]')).to_be_enabled(timeout=20000)
        await enrolled.locator('[data-action=more]').click()
        await enrolled.locator('#dialogs [data-action=logout]').click()
        await expect(enrolled.locator('[data-action=signin]')).to_be_visible()
        assert not errors,errors
        await browser.close()
    await fixture.engine.dispose()
    print('Browser: real virtual WebAuthn registration/login + approval/rejection/cancellation, lost-response no-retry, receipt gating, locales, mobile/desktop, XSS, offline/revocation passed')


async def worker_checks(output):
    """Real loopback HTTP (secure-context localhost) SW; no auth bypass in app."""
    public=FastAPI()
    public.include_router(create_admin_pwa_bootstrap_router(settings_obj=SimpleNamespace(
        ADMIN_PWA_ENABLED=True,ADMIN_PWA_PUBLIC_ORIGIN=ORIGIN),session_factory=None))
    @public.api_route('/api/admin/v1/cache-probe',methods=['GET','POST'])
    async def probe():
        return JSONResponse({'synthetic_private':'must-never-cache'},headers={'Cache-Control':'no-store'})
    @public.get('/admin.html')
    async def legacy():return JSONResponse({'synthetic_legacy':True})
    revision=0
    async def local_fixture(scope,receive,send):
        # Test-only bridge: canonical gate still runs. This app is NEVER
        # imported by production; localhost is used only for public SW QA.
        scope={**scope,'scheme':'https','server':('hskai.app',443),
               'headers':[(k,v) for k,v in scope.get('headers',[]) if k!=b'host']+[(b'host',b'hskai.app')]}
        async def respond(message):
            if scope['path']=='/admin/sw.js' and revision:
                if message['type']=='http.response.start':
                    message={**message,'headers':[(k,v) for k,v in message['headers'] if k!=b'content-length']}
                if message['type']=='http.response.body':
                    message={**message,'body':message.get('body',b'').replace(b"const VERSION = '",b"const VERSION = 'qa-update-")}
            await send(message)
        await public(scope,receive,respond)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(local_fixture,log_level='error',lifespan='off'))
    task=asyncio.create_task(server.serve(sockets=[sock]))
    try:
        async with asyncio.timeout(10):
            while not server.started:await asyncio.sleep(.01)
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            context=await browser.new_context(viewport={'width':390,'height':844})
            page=await context.new_page()
            await page.goto(f'http://127.0.0.1:{port}/admin/')
            await page.evaluate('navigator.serviceWorker.ready')
            await page.reload()
            await wait_js(page,'() => !!navigator.serviceWorker.controller')
            assert (await page.evaluate('navigator.serviceWorker.getRegistration().then(r=>new URL(r.scope).pathname)'))=='/admin/'
            await page.evaluate("""async()=>{
                await fetch('/api/admin/v1/cache-probe');
                await fetch('/api/admin/v1/cache-probe',{method:'POST',body:'synthetic'});
                await fetch('/admin.html');
                await fetch('/admin/?sensitive=synthetic');
            }""")
            cached=await page.evaluate("""async()=>{const rows=[];for(const name of await caches.keys())for(const req of await (await caches.open(name)).keys())rows.push(new URL(req.url).pathname+new URL(req.url).search);return rows;}""")
            assert set(cached)=={'/admin/','/admin/assets/styles.css','/admin/assets/catalog.js',
                '/admin/assets/app.js','/admin/assets/icon.png','/admin/assets/icon-large.png'},cached
            cdp=await context.new_cdp_session(page)
            install=await cdp.send('Page.getInstallabilityErrors')
            assert not install['installabilityErrors'],install
            # Public shell works offline; no private response is available.
            await context.set_offline(True)
            await page.reload()
            await expect(page.locator('.auth-panel')).to_be_visible()
            assert await page.evaluate('navigator.onLine') is False
            assert await page.evaluate("fetch('/api/admin/v1/cache-probe').then(()=>false,()=>true)")
            await page.screenshot(path=str(output/'mobile-offline.png'),full_page=True)
            await context.set_offline(False)
            await wait_js(page,'() => navigator.onLine')
            revision=1
            await page.evaluate('navigator.serviceWorker.getRegistration().then(r=>r.update())')
            await expect(page.locator('[data-action=update]')).to_be_visible(timeout=10000)
            async with page.expect_navigation():
                await page.locator('[data-action=update]').click()
            names=await page.evaluate('caches.keys()')
            assert len(names)==1 and names[0].startswith('hsk-admin-public-qa-update-'),names
            await browser.close()
        print('Service worker: installable manifest, narrow scope, public-only cache, offline shell, explicit update passed')
    finally:
        server.should_exit=True
        await task
        sock.close()


async def attachment_browser_checks(output):
    """Actual image routes + Telegram image decoder + V10 lifecycle, offline QA."""
    fixture=Fixture()
    fixture.engine=create_async_engine('sqlite+aiosqlite:///:memory:',poolclass=StaticPool)
    async with fixture.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    fixture.sessions=async_sessionmaker(fixture.engine,expire_on_commit=False)
    await fixture.seed_payment()
    image=Image.new('RGB',(320,420),'#e9f1f3')
    ImageDraw.Draw(image).text((35,190),'SYNTHETIC QA IMAGE',fill='#1d2c36')
    raw=io.BytesIO();image.save(raw,format='JPEG')
    remote_images={}
    for reference,format,kind in (('private-file-never-returned','WEBP','image/webp'),
                                  ('private-release-image','PNG','image/png')):
        data=io.BytesIO();image.save(data,format=format)
        remote_images[reference]=(data.getvalue(),kind)
    async def get_file(reference):
        assert reference in remote_images
        return SimpleNamespace(file_path=reference,file_size=len(remote_images[reference][0]))
    async def download_file(path,*,destination,timeout):
        destination.write(remote_images[path][0])
    telegram=SimpleNamespace(get_file=AsyncMock(side_effect=get_file),download_file=download_file)
    now=datetime.now(timezone.utc)
    async with fixture.sessions() as db:
        (await db.get(User,1)).telegram_id=1001
        db.add(ReleaseFeedbackCampaign(id=777,title='Synthetic screenshot campaign',send_at=now))
        await db.flush()
        report=AdminPwaNativeReport(user_id=1,deduplication_key='c'*64,
            description='Synthetic Android screenshot report',app_version='qa',screen='course',
            attachment_bytes=raw.getvalue(),notification_state='sent',created_at=now,
            last_attempt_at=now,expires_at=now+timedelta(days=1))
        db.add(report)
        bot_report=BotFeedback(user_id=1,telegram_id=1001,status='completed',disliked_text='Synthetic Bot media',
            disliked_attachment_file_id='private-file-never-returned',disliked_attachment_type='photo')
        release_report=ReleaseFeedbackResponse(campaign_id=777,user_telegram_id=1001,rating=4,
            comment_text='Synthetic release image',attachment_file_id='private-release-image',attachment_type='document')
        db.add_all([bot_report,release_report,BotFeedback(user_id=2,telegram_id=2002,status='completed',
            disliked_text='Unsupported media',disliked_attachment_file_id='never-download-audio',disliked_attachment_type='voice')])
        await db.commit();report_id=report.id
    app=FastAPI()
    for factory in (create_admin_pwa_bootstrap_router,create_admin_pwa_read_router):
        app.include_router(factory(settings_obj=fixture.settings,session_factory=fixture.sessions))
    app.include_router(create_admin_pwa_inbox_attachment_router(settings_obj=fixture.settings,
        session_factory=fixture.sessions,loader=lambda reference:download_receipt_image(telegram,reference)))
    attachment_path=f'/api/admin/v1/inbox/android/{report_id}/attachment'
    calls=[];mode=None;started=asyncio.Event();release=asyncio.Event();finished=asyncio.Event()
    async def serve(route):
        request=route.request
        assert request.url.startswith(ORIGIN+'/'), 'Unexpected external request'
        path=request.url.removeprefix(ORIGIN)
        if path=='/admin/sw.js':
            await route.abort();return
        if path==attachment_path:
            calls.append(await request.all_headers())
            if mode=='unavailable':
                await route.fulfill(status=503,json={'ok':False});return
            if mode=='wrong_type':
                await route.fulfill(status=200,json={'ok':True});return
        async with AsyncClient(transport=ASGITransport(app=app),base_url=ORIGIN) as client:
            response=await client.request(request.method,path,headers=await request.all_headers(),
                                          content=request.post_data_buffer)
        delayed=path==attachment_path and mode=='delayed'
        if delayed:
            started.set();await release.wait()
        headers=dict(response.headers);headers.pop('content-length',None)
        await route.fulfill(status=response.status_code,headers=headers,body=response.content)
        if delayed:finished.set()
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            context=await browser.new_context(viewport={'width':1440,'height':1000},service_workers='block')
            await context.add_cookies([{'name':'__Host-hskai_admin','value':COOKIE,'url':ORIGIN,
                                       'secure':True,'httpOnly':True,'sameSite':'Strict'}])
            await context.route('**/*',serve)
            await context.add_init_script("""window.qaURLs=[];window.qaRevoked=[];
                const create=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL);
                URL.createObjectURL=blob=>{const url=create(blob);qaURLs.push(url);return url;};
                URL.revokeObjectURL=url=>{qaRevoked.push(url);return revoke(url);};
                window.cspFailures=[];document.addEventListener('securitypolicyviolation',e=>cspFailures.push(e.violatedDirective));""")
            page=await context.new_page();errors=[]
            native_button=page.locator('[data-inbox-attachment][data-attachment-source=android]')
            page.on('pageerror',lambda error:errors.append(str(error)))
            await page.goto(ORIGIN+'/admin/');await page.wait_for_load_state('networkidle')
            await expect(page.locator('.metrics')).to_be_visible()
            assert not calls, 'Private images must not preload'
            telegram.get_file.assert_not_awaited()
            async def open_inbox():
                await page.locator('[data-action=feedback]').click()
                await expect(page.locator('[data-inbox-attachment]')).to_have_count(3)
                assert await page.evaluate("() => {const ids=[...document.querySelectorAll('.inbox-attachment')].map(e=>e.id);return new Set(ids).size===3;}")
            async def loaded():
                await wait_js(page,"() => {const i=document.querySelector('.inbox-attachment-image');return i?.complete&&i.naturalWidth===320;}")
            for locale in ('uz','ru','tj'):
                await page.set_viewport_size({'width':1440,'height':1000})
                await page.locator('#locale').select_option(locale)
                await open_inbox()
                assert await page.locator('.inbox-attachment-image').count()==0
                for source in ('bot','release','android'):
                    await page.locator(f'[data-inbox-attachment][data-attachment-source={source}]').click()
                    await loaded()
                    await expect(page.locator('.inbox-attachment-image')).to_have_count(1)
                    if locale=='uz' and source in ('bot','release'):
                        await page.screenshot(path=str(output/f'desktop-feedback-{source}.png'),full_page=True)
                        await page.set_viewport_size({'width':390,'height':844})
                        await page.locator('.inbox-attachment-image').scroll_into_view_if_needed()
                        assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                        await page.screenshot(path=str(output/f'mobile-feedback-{source}.png'),full_page=True)
                        await page.set_viewport_size({'width':1440,'height':1000})
                # ASGI route interception omits Chromium's network-generated
                # Fetch Metadata. Explicit cross-site rejection is API-tested.
                assert calls[-1].get('accept')=='image/jpeg'
                await page.screenshot(path=str(output/f'desktop-inbox-image-{locale}.png'),full_page=True)
                await page.set_viewport_size({'width':390,'height':844})
                assert await native_button.evaluate('(e)=>e.getBoundingClientRect().height>=44')
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                await page.locator('.inbox-attachment-image').scroll_into_view_if_needed()
                await page.screenshot(path=str(output/f'mobile-inbox-image-{locale}.png'),full_page=True)
                document=await page.content()
                assert all(value not in document for value in ('private-file-never-returned','private-release-image','never-download-audio'))
                await native_button.click()
                await expect(page.locator('.inbox-attachment-image')).to_have_count(0)
                assert await page.evaluate('qaURLs.length===qaRevoked.length')
                await page.keyboard.press('Escape')
            assert [call.args[0] for call in telegram.get_file.await_args_list]==[
                'private-file-never-returned','private-release-image']*3
            # Server retention is rechecked after the list was loaded.
            await open_inbox()
            async with fixture.sessions() as db:
                await db.execute(update(AdminPwaNativeReport).values(expires_at=now-timedelta(seconds=1)))
                await db.commit()
            await native_button.click()
            await expect(page.locator('.inbox-attachment [role=status]')).to_have_text('Ин маълумот ҳоло дастрас нест')
            assert await page.locator('.inbox-attachment-image').count()==0
            async with fixture.sessions() as db:
                await db.execute(update(AdminPwaNativeReport).values(expires_at=now+timedelta(days=1)))
                await db.commit()
            # Network/media failures never render private fallback content.
            for failure in ('unavailable','wrong_type'):
                await native_button.click();mode=failure
                await native_button.click()
                await expect(page.locator('.inbox-attachment [role=status]')).to_have_text('Ин маълумот ҳоло дастрас нест')
                assert await page.locator('.inbox-attachment-image').count()==0
            await native_button.click();mode='delayed'
            await native_button.click();await asyncio.wait_for(started.wait(),10)
            await page.keyboard.press('Escape');mode=None
            await open_inbox();await page.locator('[data-inbox-attachment][data-attachment-source=bot]').click();await loaded()
            current_url=await page.locator('.inbox-attachment-image').get_attribute('src')
            release.set();await asyncio.wait_for(finished.wait(),10)
            assert await page.locator('.inbox-attachment-image').get_attribute('src')==current_url
            # Offline/pagehide clear object URLs, as well as the current drawer.
            for event in ('offline','pagehide'):
                await page.evaluate('(event)=>window.dispatchEvent(new Event(event))',event)
                assert await page.locator('.inbox-attachment-image').count()==0
                assert await page.evaluate('qaURLs.length===qaRevoked.length')
                await page.reload();await expect(page.locator('.metrics')).to_be_visible()
                await open_inbox()
                await native_button.click();await loaded()
            await page.keyboard.press('Escape');await open_inbox()
            async with fixture.sessions() as db:
                await db.execute(update(AdminPwaSession).values(revoked_at=now))
                await db.commit()
            await native_button.click()
            await expect(page.locator('.auth-panel')).to_be_visible()
            assert await page.locator('.inbox-attachment-image').count()==0
            assert await page.evaluate('qaURLs.length===qaRevoked.length')
            assert await page.evaluate('Object.keys(localStorage)')==['hsk-admin-locale']
            assert not errors,errors
            assert not await page.evaluate('cspFailures')
            await browser.close()
        print('Private Inbox images: Android JPEG + Bot WebP + Release PNG through actual decoder, UZ/RU/TJ 1440/390, failure/cancel/offline/pagehide cleanup passed')
    finally:
        release.set()
        await fixture.engine.dispose()


async def export_browser_checks(output):
    """Actual aggregate file downloads, bounded errors and stale-response cleanup."""
    fixture=Fixture()
    fixture.engine=create_async_engine('sqlite+aiosqlite:///:memory:',poolclass=StaticPool)
    async with fixture.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    fixture.sessions=async_sessionmaker(fixture.engine,expire_on_commit=False)
    await fixture.seed_payment()
    async with fixture.sessions() as db:
        (await db.get(User,1)).full_name='private-export-canary@example.invalid'
        await db.commit()
    app=FastAPI()
    common={'settings_obj':fixture.settings,'session_factory':fixture.sessions}
    for factory in (create_admin_pwa_bootstrap_router,create_admin_pwa_read_router,
                    create_admin_pwa_feedback_analytics_router):
        app.include_router(factory(**common))
    mode='normal';calls=[];downloads=[]
    started,release,finished=asyncio.Event(),asyncio.Event(),asyncio.Event()
    async def serve(route):
        request=route.request;path=request.url.removeprefix(ORIGIN)
        if path=='/admin/sw.js':await route.abort();return
        is_export=path=='/api/admin/v1/statistics/export'
        if is_export:
            calls.append((request.post_data_json,await request.all_headers()))
            if mode=='failure':await route.fulfill(status=503,json={'ok':False});return
            if mode=='wrong_type':await route.fulfill(status=200,content_type='text/html',body='invalid');return
            if mode=='oversized':await route.fulfill(status=200,content_type='application/json',body='x'*(128*1024+1));return
        async with AsyncClient(transport=ASGITransport(app=app),base_url=ORIGIN) as client:
            response=await client.request(request.method,path,headers=await request.all_headers(),content=request.post_data_buffer)
        delayed=is_export and mode=='delayed'
        if delayed:started.set();await release.wait()
        headers=dict(response.headers);headers.pop('content-length',None)
        await route.fulfill(status=response.status_code,headers=headers,body=response.content)
        if delayed:finished.set()
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            context=await browser.new_context(viewport={'width':1440,'height':1000},service_workers='block')
            await context.add_cookies([{'name':'__Host-hskai_admin','value':COOKIE,'url':ORIGIN,'secure':True,'httpOnly':True,'sameSite':'Strict'}])
            await context.route('**/*',serve)
            await context.add_init_script("""window.qaURLs=[];window.qaRevoked=[];
                const create=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL);
                URL.createObjectURL=blob=>{const url=create(blob);qaURLs.push(url);return url;};
                URL.revokeObjectURL=url=>{qaRevoked.push(url);return revoke(url);};""")
            page=await context.new_page();errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('download',lambda download:downloads.append(download))
            await page.goto(ORIGIN+'/admin/');await page.wait_for_load_state('networkidle')
            await expect(page.locator('.metrics')).to_be_visible()
            assert not calls,'Exports must only run after an explicit tap'
            await page.locator('[data-route=stats]').first.click()
            await expect(page.locator('[data-export-format]')).to_have_count(2)
            await expect(page.locator('.feedback-analysis')).to_be_visible()
            await expect(page.locator('[data-feedback-export]')).to_have_count(2)
            original_time=None
            for width in (1440,390):
                await page.set_viewport_size({'width':width,'height':1000 if width==1440 else 844})
                for language in ('uz','ru','tj'):
                    if width==1440:await page.locator('#locale').select_option(language)
                    else:
                        await page.locator('[data-action=more]').click()
                        await page.locator('#drawerLocale').select_option(language)
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    assert await page.locator('[data-export-format=json]').evaluate('(el) => el.getBoundingClientRect().height>=44')
                    await page.screenshot(path=str(output/f'statistics-export-{width}-{language}.png'),full_page=True)
                    async with page.expect_download() as pending:
                        await page.locator('[data-export-format=json]').click()
                    download=await pending.value
                    assert download.suggested_filename=='hskai-statistics-overall-weekly.json'
                    text=Path(await download.path()).read_text()
                    data=json.loads(text)
                    assert 'private-export-canary' not in text and COOKIE not in text
                    assert data['dataset']=='hskai_statistics' and data['metrics'][0]['value']==3
                    original_time=original_time or data['generated_at']
                    assert data['generated_at']==original_time
                    await wait_js(page,'() => qaURLs.length===qaRevoked.length')
            async with page.expect_download() as pending:
                await page.locator('[data-export-format=csv]').click()
            download=await pending.value
            rows=list(csv.DictReader(io.StringIO(Path(await download.path()).read_text())))
            assert rows and all(row['generated_at']==original_time for row in rows)
            assert 'denominator' in next(row['definition'] for row in rows if row['metric']=='registration_conversion.percent')
            await wait_js(page,'() => qaURLs.length===qaRevoked.length')
            assert len(calls)==len(downloads)==7
            assert all(headers['origin']==ORIGIN and headers['content-type']=='application/json' for _,headers in calls)
            baseline=len(downloads)
            for mode in ('failure','wrong_type','oversized'):
                await page.locator('[data-export-format=json]').click()
                await expect(page.locator('[data-export-format=json]')).to_be_enabled()
                assert len(downloads)==baseline
            await page.set_viewport_size({'width':1440,'height':1000})
            for cancel in ('route','locale','offline','pagehide'):
                mode='normal'
                await page.reload();await page.wait_for_load_state('networkidle')
                await page.locator('[data-route=stats]').first.click()
                await expect(page.locator('[data-export-format=json]')).to_be_visible()
                mode='delayed';started.clear();release.clear();finished.clear()
                await page.locator('[data-export-format=json]').click()
                await asyncio.wait_for(started.wait(),5)
                await expect(page.locator('[data-export-format=json]')).to_be_disabled()
                if cancel=='route':await page.locator('[data-route=users]').first.click()
                elif cancel=='locale':await page.locator('#locale').select_option('uz' if await page.locator('#locale').input_value()!='uz' else 'ru')
                else:await page.evaluate('(name) => window.dispatchEvent(new Event(name))',cancel)
                release.set();await asyncio.wait_for(finished.wait(),5)
                assert len(downloads)==baseline
                assert await page.evaluate('qaURLs.length===qaRevoked.length')
            # Feedback export is an explicit first-party action, independent
            # of the longer cached statistics window.
            await page.reload();await page.wait_for_load_state('networkidle')
            await page.locator('[data-route=stats]').first.click()
            await expect(page.locator('[data-feedback-export=json]')).to_be_visible()
            await page.locator('[data-feedback-source=bot]').click()
            await expect(page.locator('.feedback-analysis-source')).to_have_count(1)
            await page.locator('[data-feedback-period=monthly]').click()
            await expect(page.locator('.feedback-analysis')).to_contain_text('30 kun')
            async with page.expect_download() as pending:
                await page.locator('[data-feedback-export=json]').click()
            fb=await pending.value
            assert fb.suggested_filename=='hskai-feedback-categories-bot-monthly.json'
            raw=Path(await fb.path()).read_text()
            parsed=json.loads(raw)
            assert parsed['schema']=='hskai_feedback_categories_v1'
            assert parsed['source']=='bot' and parsed['period']=='monthly'
            assert 'private-export-canary' not in raw
            await wait_js(page,'() => qaURLs.length===qaRevoked.length')
            assert not errors,errors
            await browser.close()
        print('Statistics and feedback downloads: ASGI, WebAuthn, locales, PII limits and cancellation passed')
    finally:
        release.set()
        await fixture.engine.dispose()


async def access_grant_browser_checks(output):
    fixture=Fixture();fixture.engine=create_async_engine('sqlite+aiosqlite:///:memory:',poolclass=StaticPool)
    async with fixture.engine.begin() as conn:await conn.run_sync(Base.metadata.create_all)
    fixture.sessions=async_sessionmaker(fixture.engine,expire_on_commit=False)
    await fixture.seed_payment()
    app=FastAPI();common={'settings_obj':fixture.settings,'session_factory':fixture.sessions}
    for factory in (create_admin_pwa_bootstrap_router,create_admin_pwa_read_router,
                    create_admin_pwa_step_up_router,create_admin_pwa_access_grant_router):
        app.include_router(factory(**common))
    drop=False;calls=[]
    async def serve(route):
        nonlocal drop
        request=route.request;path=request.url.removeprefix(ORIGIN)
        if path=='/admin/sw.js':await route.abort();return
        calls.append((path,request.post_data_json if request.method=='POST' else None))
        async with AsyncClient(transport=ASGITransport(app=app),base_url=ORIGIN) as client:
            response=await client.request(request.method,path,headers=await request.all_headers(),content=request.post_data_buffer)
        if drop and path=='/api/admin/v1/users/grant-access':drop=False;await route.abort();return
        headers=dict(response.headers);headers.pop('content-length',None)
        await route.fulfill(status=response.status_code,headers=headers,body=response.content)
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch();context=await browser.new_context(viewport={'width':1440,'height':1000},service_workers='block')
            await context.add_cookies([{'name':'__Host-hskai_admin','value':COOKIE,'url':ORIGIN,'secure':True,'httpOnly':True,'sameSite':'Strict'}])
            await context.route('**/*',serve)
            page=await context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            cdp=await context.new_cdp_session(page);await cdp.send('WebAuthn.enable')
            auth=await cdp.send('WebAuthn.addVirtualAuthenticator',{'options':{'protocol':'ctap2','transport':'internal','hasResidentKey':True,'hasUserVerification':True,'isUserVerified':True,'automaticPresenceSimulation':True}})
            auth_id=auth['authenticatorId'];b64=lambda value:base64.b64encode(value).decode()
            await cdp.send('WebAuthn.addCredential',{'authenticatorId':auth_id,'credential':{'credentialId':b64(CRED_ID),'isResidentCredential':True,'rpId':'hskai.app','privateKey':b64(fixture.key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())),'userHandle':b64(HANDLE),'signCount':0}})
            await page.goto(ORIGIN+'/admin/');await page.wait_for_load_state('networkidle')
            await page.locator('[data-route=users]').first.click()
            async def prepare():
                await page.locator('[data-user-detail="1"]:visible').first.click()
                await page.locator('[data-access-user="1"]').click()
                await page.locator('#accessDays').fill('10')
                await page.locator('[data-prepare-access="1"]').click()
                await expect(page.locator('[data-action=executeAccess]')).to_be_visible()
            for width in (1440,390):
                await page.set_viewport_size({'width':width,'height':1000 if width==1440 else 844})
                for language in ('uz','ru','tj'):
                    if width==1440:await page.locator('#locale').select_option(language)
                    else:
                        await page.locator('[data-action=more]').click();await page.locator('#drawerLocale').select_option(language)
                    await prepare()
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    await page.screenshot(path=str(output/f'access-confirm-{width}-{language}.png'),full_page=True)
                    await page.locator('.drawer-close').click()
            assert not any(path.endswith('/users/grant-access') for path,_ in calls)
            await prepare();await page.locator('[data-action=executeAccess]').click()
            await expect(page.locator('#drawerContent')).to_contain_text('10')
            await expect(page.locator('[data-action=executeAccess]')).to_have_count(0)
            async with fixture.sessions() as db:
                assert await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit))==1
                assert (await db.get(User,1)).payment_status=='approved'
            await page.locator('.drawer-close').click()
            await prepare()
            async with fixture.sessions() as db:
                (await db.get(User,1)).end_date=datetime.now(timezone.utc)+timedelta(days=40);await db.commit()
            await page.locator('[data-action=executeAccess]').click()
            await expect(page.locator('#drawerFoot [data-user-detail="1"]')).to_be_visible()
            await expect(page.locator('[data-action=executeAccess]')).to_have_count(0)
            async with fixture.sessions() as db:assert await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit))==1
            await page.locator('.drawer-close').click()
            await prepare();drop=True
            await page.locator('[data-action=executeAccess]').click()
            await expect(page.locator('#drawerFoot [data-user-detail="1"]')).to_be_visible()
            assert len([path for path,_ in calls if path.endswith('/users/grant-access')])==3
            async with fixture.sessions() as db:assert await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit))==2
            assert not errors,errors
            await browser.close()
        print('Manual access: real WebAuthn signatures, canonical native target, UZ/RU/TJ 1440/390 confirmations/cancel, stale snapshot and lost-response no-retry passed')
    finally:await fixture.engine.dispose()


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='/tmp/admin-pwa-browser')
    args=parser.parse_args();output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    with patch('app.services.ai_usage_budget_service.AIUsageBudgetService._live_or_manual_usd_rates',new=AsyncMock(return_value={'tjs':10,'cny':7})):
        await browser_checks(output)
        await export_browser_checks(output)
        await access_grant_browser_checks(output)
        await attachment_browser_checks(output)
        await worker_checks(output)

if __name__=='__main__':asyncio.run(main())
