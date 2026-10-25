"""V10 management QA with real SQL commands and native virtual WebAuthn proofs.

No providers/network: shell and settings/price/auth requests use the actual
ASGI routes. Only the unrelated initial statistics response is a UI fixture.
Run: python -m tests.e2e.admin_pwa_settings_browser --output /tmp/admin-settings
"""
import argparse
import asyncio
import base64
import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from playwright.async_api import async_playwright, expect
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.admin_api.pwa_bootstrap import create_admin_pwa_bootstrap_router
from app.admin_api.pwa_read import create_admin_pwa_read_router
from app.admin_api.pwa_settings import create_admin_pwa_settings_router
from app.admin_api.pwa_marketing import create_admin_pwa_marketing_router
from app.admin_api.pwa_user_management import create_admin_pwa_user_management_router
from app.admin_api.pwa_channels import create_admin_pwa_channels_router
from app.admin_api.pwa_partner_payouts import create_admin_pwa_partner_payouts_router
from app.admin_api.pwa_partners import create_admin_pwa_partners_router
from app.admin_api.pwa_notifications import create_admin_pwa_notifications_router
from app.admin_api.pwa_portfolio import create_admin_pwa_portfolio_router
from app.admin_api.pwa_step_up_transport import create_admin_pwa_step_up_router
from app.admin_api.pwa_webauthn_login_transport import create_admin_pwa_passkey_login_router
from app.admin_api.pwa_payment_reconciliation import create_admin_pwa_payment_reconciliation_router
from app.admin_api.pwa_subscription_prices import create_admin_pwa_subscription_prices_router
from app.db.base import Base
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.admin_pwa_payment_review import AdminPwaPaymentReview,AdminPwaPaymentOutbox
from app.db.models.partner import Partner, PartnerPayout
from app.db.models.course_ad import CourseAdCreative
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.subscription_miniapp_service import PAYMENT_DETAILS_KEY
from app.services.support_contact_service import ADMIN_CONTACT_KEY
from tests.test_admin_pwa_payment_review import COOKIE, PaymentFixtures
from tests.test_admin_pwa_webauthn_crypto_vectors import CRED_ID, HANDLE

ORIGIN = "https://hskai.app"
ROOT = Path(__file__).resolve().parents[2]


async def browser_checks(output):
    output.mkdir(parents=True, exist_ok=True)
    fixture = PaymentFixtures()
    fixture.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with fixture.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    fixture.sessions = async_sessionmaker(fixture.engine, expire_on_commit=False)
    await fixture.seed_payment()
    async with fixture.sessions() as db:
        await BotSettingRepository(db).set(PAYMENT_DETAILS_KEY, 'QA bank <img src=x onerror=alert(1)>')
        db.add(CourseAdCreative(id=1, title='QA ad <img src=x onerror=alert(1)>',
                               media_path='synthetic/no-local-file.png', media_type='photo'))
        db.add_all([Partner(id=i,user_telegram_id=7100+i,status='pending',
            promotion_channel='QA promotion <img src=x onerror=alert(1)>',
            audience_size='1000',contact_username='@qa_partner') for i in (1,2)])
        await db.flush()
        db.add_all([PartnerPayout(id=i,partner_id=i,amount_usd=10,exchange_rate=10.9,local_amount=109,
            local_currency='TJS',status='pending',payment_method='bank',account_details='QA account <img src=x onerror=alert(1)>') for i in (1,2)])
        await db.flush()
        db.add(AdminPwaPaymentReview(id='00000000-0000-0000-0000-000000000001',step_up_id='00000000-0000-0000-0000-000000000002',payment_id=999,actor_user_id=101,target_user_id=1,action='payments.review',decision='approve',payload_hash='0'*64,payload_json='{}',status='applied'))
        await db.flush()
        db.add(AdminPwaPaymentOutbox(review_id='00000000-0000-0000-0000-000000000001',status='uncertain',effects_json='{}',attempted_at=datetime.now(timezone.utc)))
        await db.commit()
    app = FastAPI()
    common = dict(settings_obj=fixture.settings, session_factory=fixture.sessions)
    for factory in (create_admin_pwa_bootstrap_router, create_admin_pwa_read_router,
                    create_admin_pwa_passkey_login_router, create_admin_pwa_step_up_router, create_admin_pwa_settings_router,
                    create_admin_pwa_subscription_prices_router, create_admin_pwa_marketing_router,
                    create_admin_pwa_user_management_router,create_admin_pwa_channels_router,
                    create_admin_pwa_portfolio_router,create_admin_pwa_notifications_router,create_admin_pwa_partners_router,create_admin_pwa_partner_payouts_router,create_admin_pwa_payment_reconciliation_router):
        app.include_router(factory(**common))
    calls, errors = [], []
    drop_save = False

    async def audit_count():
        async with fixture.sessions() as db:
            return await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit))

    async def serve(route):
        nonlocal drop_save
        request = route.request
        assert request.url.startswith(ORIGIN + "/"), request.url
        path = request.url.removeprefix(ORIGIN)
        if path == "/admin/sw.js":
            await route.abort()
            return
        body = request.post_data_json if request.method == "POST" else None
        calls.append((path, body))
        if path == "/api/admin/v1/statistics":
            await route.fulfill(status=200, json={"ok": True, "available": False})
            return
        async with AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN) as client:
            response = await client.request(request.method, path, headers=await request.all_headers(),
                                            content=request.post_data_buffer)
        if drop_save and path.endswith("/save"):
            assert response.status_code == 200, response.text
            drop_save = False
            await route.abort()
            return
        headers = dict(response.headers)
        headers.pop("content-length", None)
        cookies=response.headers.get_list("set-cookie")
        if cookies:headers["set-cookie"]="\n".join(cookies)
        await route.fulfill(status=response.status_code, headers=headers, body=response.content)

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                context = await browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
                await context.route("**/*", serve)
                page = await context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                await page.add_init_script("window.cspFailures=[];document.addEventListener('securitypolicyviolation',e=>window.cspFailures.push(e.violatedDirective));")
                cdp = await context.new_cdp_session(page)
                await cdp.send("WebAuthn.enable")
                authenticator = await cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {
                    "protocol": "ctap2", "transport": "internal", "hasResidentKey": True,
                    "hasUserVerification": True, "isUserVerified": True, "automaticPresenceSimulation": True}})
                b64 = lambda data: base64.b64encode(data).decode()
                await cdp.send("WebAuthn.addCredential", {"authenticatorId": authenticator["authenticatorId"], "credential": {
                    "credentialId": b64(CRED_ID), "isResidentCredential": True, "rpId": "hskai.app",
                    "privateKey": b64(fixture.key.private_bytes(serialization.Encoding.DER,
                        serialization.PrivateFormat.PKCS8, serialization.NoEncryption())),
                    "userHandle": b64(HANDLE), "signCount": 0, "userName": "settings-qa"}})

                async def navigate(route_name, width):
                    if width == 390:
                        await page.locator('[data-action="more"]').click()
                        await page.locator(f'.panel-action-list [data-route="{route_name}"]').click()
                    else:
                        await page.locator(f'.nav [data-route="{route_name}"]').click()
                    await expect(page.locator(".management-page")).to_be_visible()

                async def prepare_and_save(language, label=None):
                    before = await audit_count()
                    ceremonies = len([path for path, _ in calls if path.endswith("step-up/options")])
                    await page.locator('[data-action="managementPrepare"]').click()
                    await expect(page.locator(".management-comparison")).to_be_visible()
                    assert await audit_count() == before
                    assert len([path for path, _ in calls if path.endswith("step-up/options")]) == ceremonies
                    if label:
                        await page.screenshot(path=str(output / label))
                    await page.locator('[data-action="managementExecute"]').click()
                    expected = json.loads((ROOT / f"localization/ui/{language}/miniapp.json").read_text())["messages"]["ui.admin_pwa.changesSaved"]
                    await expect(page.locator("#drawerTitle")).to_have_text(expected, timeout=15000)
                    assert await audit_count() == before + 1
                    await page.locator(".drawer-close").click()

                await page.goto(ORIGIN + "/admin/")
                await page.wait_for_load_state("networkidle")
                await expect(page.locator("[data-action=signin]")).to_be_visible(timeout=15000)
                await page.locator("[data-action=signin]").click()
                await expect(page.locator(".sidebar")).to_be_visible(timeout=20000)
                live_cookie=next(cookie['value'] for cookie in await context.cookies()
                    if cookie['name']=='__Host-hskai_admin')
                async with fixture.sessions() as db:
                    fixture.session_id=await db.scalar(select(AdminPwaSession.id).where(
                        AdminPwaSession.token_hash==hashlib.sha256(live_cookie.encode()).hexdigest()))

                # Landing pages are navigation, with no per-page configuration queries.
                configuration_reads = lambda: [path for path, _ in calls
                    if path in ('/api/admin/v1/settings/read', '/api/admin/v1/subscription-prices/read')]
                initial = list(configuration_reads())
                await navigate("course", 1440)
                await expect(page.locator('[data-action="hsk30Settings"]')).to_be_visible()
                await expect(page.locator('[data-action="courseSettings"]')).to_be_visible()
                await navigate("system", 1440)
                assert configuration_reads() == initial
                for width in (1440, 390):
                    await page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
                    for index, language in enumerate(("uz", "ru", "tj")):
                        if width == 390:
                            await page.locator('[data-action="more"]').click()
                            await page.locator("#drawerLocale").select_option(language)
                        else:
                            await page.locator("#locale").select_option(language)
                        await navigate("system", width)
                        await page.screenshot(path=str(output / f"system-{language}-{width}.png"))
                        await page.locator('[data-action="priceSettings"]').click()
                        await expect(page.locator("#priceAmount")).to_have_value("29")
                        await page.locator("#pricePlan").select_option("1_month")
                        await page.locator("#priceAmount").fill(str(300 + index + (10 if width == 390 else 0)))
                        await prepare_and_save(language, f"price-confirm-{language}-{width}.png")
                        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")

                await page.set_viewport_size({"width": 1440, "height": 1000})
                await page.locator("#locale").select_option("uz")
                # Start the next logical scenario outside the fixed ten-proof
                # window. Rate limits have their own regression suite; all
                # browser signatures above still used the real server quota.
                async with fixture.sessions() as db:
                    await db.execute(update(AdminPwaStepUp).where(AdminPwaStepUp.status == "consumed").values(
                        created_at=datetime.now(timezone.utc)-timedelta(minutes=11)))
                    await db.commit()
                # Cancel has no proof/command side effects and never persists an edit.
                before = await audit_count()
                await page.locator('[data-setting-kind="payment_details"][data-bank="dc_city"]').click()
                await page.locator("#settingValue").fill("QA cancellation")
                await page.locator('[data-action="managementPrepare"]').click()
                await expect(page.locator(".management-comparison")).to_be_visible()
                assert await page.locator(".management-comparison img").count() == 0
                await page.locator('[data-action="close"]').last.click()
                assert await audit_count() == before
                for bank in ("dc_city", "alif"):
                    await page.locator(f'[data-setting-kind="payment_details"][data-bank="{bank}"]').click()
                    await page.locator("#settingValue").fill(f"QA {bank} bank\nAccount 1234")
                    await prepare_and_save("uz")
                await page.locator('[data-setting-kind="ai_model"]').click()
                await expect(page.locator("#settingModel")).to_be_visible()
                models = await page.locator("#settingModel option").evaluate_all("rows=>rows.map(r=>r.value)")
                await page.locator("#settingModel").select_option(models[-1])
                await prepare_and_save("uz")
                await page.locator('[data-setting-kind="help_contact"]').click()
                await page.locator("#settingValue").fill("@synthetic_support")
                await prepare_and_save("uz")
                await page.locator('[data-setting-kind="help_video"]').click()
                await page.locator("#helpVideoKey").select_option("qa_mode")
                await page.locator("#helpVideoLanguage").select_option("tj")
                await page.locator("#settingValue").fill("https://example.invalid/qa.mp4")
                await prepare_and_save("uz", "help-video-confirm.png")
                # A real concurrent config change invalidates the server snapshot.
                before = await audit_count()
                await page.locator('[data-setting-kind="help_contact"]').click()
                await page.locator("#settingValue").fill("@next_support")
                await page.locator('[data-action="managementPrepare"]').click()
                await expect(page.locator(".management-comparison")).to_be_visible()
                async with fixture.sessions() as db:
                    await BotSettingRepository(db).set(ADMIN_CONTACT_KEY, "@changed_elsewhere")
                    await db.commit()
                await page.locator('[data-action="managementExecute"]').click()
                await expect(page.locator('[data-setting-kind="help_contact"]')).to_have_count(2)
                assert await audit_count() == before
                await expect(page.locator('[data-action="managementExecute"]')).to_have_count(0)
                await page.locator(".drawer-close").click()
                # A lost response AFTER the command commits exposes only a reread action.
                await page.locator('[data-action="priceSettings"]').click()
                await page.locator("#priceAmount").fill("101")
                await page.locator('[data-action="managementPrepare"]').click()
                await expect(page.locator(".management-comparison")).to_be_visible()
                saves = len([path for path, _ in calls if path.endswith("subscription-prices/save")])
                drop_save = True
                await page.locator('[data-action="managementExecute"]').click()
                await expect(page.locator('#drawerFoot [data-action="priceSettings"]')).to_be_visible()
                await expect(page.locator('[data-action="managementExecute"]')).to_have_count(0)
                assert await audit_count() == before + 1
                assert len([path for path, _ in calls if path.endswith("subscription-prices/save")]) == saves + 1
                await page.locator('#drawerFoot [data-action="priceSettings"]').click()
                await expect(page.locator("#priceAmount")).to_have_value("101")
                assert len([path for path, _ in calls if path.endswith("subscription-prices/save")]) == saves + 1
                await page.locator(".drawer-close").click()
                # Marketing is the same exact passkey flow over shared real
                # configuration services. Read each localized editor before
                # exercising saved changes and a single creative deletion.
                async with fixture.sessions() as db:
                    await db.execute(update(AdminPwaStepUp).where(AdminPwaStepUp.status == "consumed").values(
                        created_at=datetime.now(timezone.utc)-timedelta(minutes=11)))
                    await db.commit()
                for width in (1440, 390):
                    await page.set_viewport_size({'width':width, 'height':1000 if width==1440 else 844})
                    for language in ('uz','ru','tj'):
                        if width == 390:
                            await page.locator('[data-action="more"]').click()
                            await page.locator('#drawerLocale').select_option(language)
                        else:
                            await page.locator('#locale').select_option(language)
                        await navigate('marketing', width)
                        for kind in ('sales_experiment','desktop_promo','course_ad'):
                            await page.locator(f'[data-marketing-kind="{kind}"]').click()
                            await expect(page.locator('#salesMode' if kind=='sales_experiment' else '#promoEnabled' if kind=='desktop_promo' else '[data-course-ad="1"]')).to_be_visible()
                            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                            assert await page.locator('#drawerContent img').count() == 0
                            await page.screenshot(path=str(output / f'marketing-{kind}-{language}-{width}.png'))
                            await page.locator('.drawer-close').click()
                await page.set_viewport_size({'width':1440,'height':1000})
                await page.locator('#locale').select_option('uz')
                await page.locator('[data-marketing-kind="sales_experiment"]').click()
                await page.locator('#salesMode').select_option('ab')
                await page.locator('#salesPercent').select_option('50')
                await prepare_and_save('uz','sales-experiment-confirm.png')
                await page.locator('[data-marketing-kind="desktop_promo"]').click()
                await page.locator('#promoEnabled').select_option('true')
                await page.locator('#promoLimit').fill('2')
                await prepare_and_save('uz','desktop-promo-confirm.png')
                for operation in ('set_active','delete'):
                    await page.locator('[data-marketing-kind="course_ad"]').click()
                    await page.locator('[data-course-ad="1"]').click()
                    await page.locator('#adOperation').select_option(operation)
                    if operation == 'set_active':
                        await page.locator('#adActive').select_option('false')
                    else:
                        await expect(page.locator('#adDeleteHint')).to_be_visible()
                    await prepare_and_save('uz',f'course-ad-{operation}-confirm.png')
                async with fixture.sessions() as db:
                    self_ad = await db.get(CourseAdCreative,1)
                    assert self_ad is None
                # The account footer keeps its primary subscription action;
                # destructive/state actions use the same secondary menu.
                for language in ('uz','ru','tj'):
                    await page.locator('#locale').select_option(language)
                    await page.set_viewport_size({'width':390,'height':844})
                    await page.locator('.mobile-tabs [data-route="users"]').click()
                    await page.locator('[data-user-detail="2"]:visible').click()
                    await page.locator('[data-menu-toggle="userManagementMenu"]').click()
                    await page.locator('[data-user-management="2"][data-user-operation="block"]').click()
                    await page.locator('[data-action="managementPrepare"]').click()
                    await expect(page.locator('.management-comparison')).to_be_visible()
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    await page.screenshot(path=str(output/f'account-block-confirm-{language}-390.png'))
                    await page.locator('[data-action="close"]').last.click()
                    await page.set_viewport_size({'width':1440,'height':1000})
                await page.locator('#locale').select_option('uz')
                for operation,user_id in (('block',2),('unblock',2),('delete',1)):
                    await page.locator('[data-user-detail="'+str(user_id)+'"]:visible').click()
                    await page.locator('[data-menu-toggle="userManagementMenu"]').click()
                    await page.locator(f'[data-user-management="{user_id}"][data-user-operation="{operation}"]').click()
                    if operation=='delete':
                        before_prepare=len([p for p,_ in calls if p.endswith('prepare-management')])
                        await page.locator('#manageConfirm').fill('2')
                        await page.locator('[data-action="managementPrepare"]').click()
                        assert len([p for p,_ in calls if p.endswith('prepare-management')])==before_prepare
                        await page.locator('#manageConfirm').fill('1')
                    await prepare_and_save('uz',f'account-{operation}-confirm.png')
                await navigate('system',1440)
                # Fixed channel settings are read only on an explicit editor
                # tap; these are DB commands and never Telegram API requests.
                async with fixture.sessions() as db:
                    await db.execute(update(AdminPwaStepUp).where(AdminPwaStepUp.status == 'consumed').values(
                        created_at=datetime.now(timezone.utc)-timedelta(minutes=11)))
                    await db.commit()
                for language in ('uz','ru','tj'):
                    await page.locator('#locale').select_option(language)
                    await page.locator('[data-channels-kind="mode"]').click()
                    await expect(page.locator('#channelEnabled')).to_be_visible()
                    await page.set_viewport_size({'width':390,'height':844})
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    await page.screenshot(path=str(output/f'channel-mode-{language}-390.png'))
                    await page.locator('.drawer-close').click()
                    await page.set_viewport_size({'width':1440,'height':1000})
                await page.locator('#locale').select_option('uz')
                await page.locator('[data-channels-kind="list"]').click()
                await page.locator('[data-channels-kind="add"]').click()
                await page.locator('#channelChat').fill('@qa_channel')
                await page.locator('#channelTitle').fill('QA channel <img src=x onerror=alert(1)>')
                await prepare_and_save('uz','channel-add-confirm.png')
                await page.locator('[data-channels-kind="mode"]').click()
                await page.locator('#channelEnabled').select_option('true')
                await prepare_and_save('uz')
                for operation in ('state','delete'):
                    await page.locator('[data-channels-kind="list"]').click()
                    await page.locator('[data-channel-id]').click()
                    await page.locator('#channelOperation').select_option(operation)
                    if operation=='state':await page.locator('#channelActive').select_option('false')
                    await prepare_and_save('uz',f'channel-{operation}-confirm.png')
                for language in ('uz','ru','tj'):
                    await page.locator('#locale').select_option(language)
                    await page.locator('[data-action="portfolioHistory"]').click()
                    await page.locator('[data-action="portfolioEditor"]').click()
                    await page.locator('#portfolioCurrency').select_option('TJS')
                    await page.locator('#portfolioAmount').fill('12.99')
                    await page.locator('#portfolioNote').fill('QA expense <img src=x onerror=alert(1)>')
                    await page.set_viewport_size({'width':390,'height':844})
                    await page.locator('[data-action="managementPrepare"]').click()
                    await expect(page.locator('.management-comparison')).to_be_visible()
                    assert await page.locator('.management-comparison img').count()==0
                    await page.screenshot(path=str(output/f'ledger-confirm-{language}-390.png'))
                    await page.locator('[data-action="close"]').last.click()
                    await page.set_viewport_size({'width':1440,'height':1000})
                await page.locator('#locale').select_option('uz')
                await page.locator('[data-action="portfolioHistory"]').click()
                await page.locator('[data-action="portfolioEditor"]').click()
                await page.locator('#portfolioType').select_option('expense')
                await page.locator('#portfolioCurrency').select_option('TJS')
                await page.locator('#portfolioAmount').fill('12.99')
                await page.locator('#portfolioNote').fill('QA committed expense')
                await prepare_and_save('uz')
                await page.locator('[data-action="portfolioHistory"]').click()
                await expect(page.locator('#drawerContent')).to_contain_text('QA committed expense')
                await page.locator('.drawer-close').click()
                async with fixture.sessions() as db:
                    await db.execute(update(AdminPwaStepUp).where(AdminPwaStepUp.status == 'consumed').values(
                        created_at=datetime.now(timezone.utc)-timedelta(minutes=11)))
                    await db.commit()
                for language in ('uz','ru','tj'):
                    await page.locator('#locale').select_option(language)
                    await page.locator('[data-action="noticeList"]').click()
                    await expect(page.locator('[data-notice-key]')).to_have_count(5)
                    await page.locator('[data-notice-key="daily_goal"]').click()
                    await page.set_viewport_size({'width':390,'height':844})
                    await expect(page.locator('#noticeText')).to_be_visible()
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    await page.screenshot(path=str(output/f'notice-editor-{language}-390.png'))
                    # Drafts survive language switches and invalid placeholders.
                    await page.locator('#noticeLanguage').select_option('uz')
                    await page.locator('#noticeText').fill('QA {unsafe}')
                    await page.locator('[data-action="managementPrepare"]').click()
                    await expect(page.locator('#noticeValidation')).to_be_visible()
                    await expect(page.locator('#noticeText')).to_have_value('QA {unsafe}')
                    await page.locator('#noticeText').fill('QA <b>{minutes}</b> <img src=x onerror=alert(1)>')
                    await page.locator('#noticeLanguage').select_option('ru')
                    await page.locator('#noticeText').fill('Минуты: {minutes}')
                    await page.locator('#noticeLanguage').select_option('tj')
                    await page.locator('#noticeText').fill('Дақиқа: {minutes}')
                    await page.locator('#noticeLanguage').select_option('uz')
                    await expect(page.locator('#noticeText')).to_have_value('QA <b>{minutes}</b> <img src=x onerror=alert(1)>')
                    await page.locator('[data-action="managementPrepare"]').click()
                    await expect(page.locator('.management-comparison')).to_be_visible()
                    assert await page.locator('.management-comparison img').count()==0
                    await page.screenshot(path=str(output/f'notice-confirm-{language}-390.png'))
                    await page.locator('[data-action="close"]').last.click()
                    await page.set_viewport_size({'width':1440,'height':1000})
                await page.locator('#locale').select_option('uz')
                await page.locator('[data-action="noticeList"]').click()
                await page.locator('[data-notice-key="daily_goal"]').click()
                await page.locator('#noticeEnabled').select_option('false')
                await page.locator('#noticeText').fill('Saved {minutes}')
                await prepare_and_save('uz')
                await page.locator('[data-action="noticeList"]').click()
                await page.locator('[data-notice-key="daily_goal"]').click()
                await expect(page.locator('#noticeText')).to_have_value('Saved {minutes}')
                await expect(page.locator('#noticeEnabled')).to_have_value('false')
                await page.locator('.drawer-close').click()
                await navigate('marketing',1440)
                async with fixture.sessions() as db:
                    await db.execute(update(AdminPwaStepUp).where(AdminPwaStepUp.status == 'consumed').values(
                        created_at=datetime.now(timezone.utc)-timedelta(minutes=11)))
                    await db.commit()
                for language in ('uz','ru','tj'):
                    await page.locator('#locale').select_option(language)
                    await page.locator('[data-action="partnerList"]').click()
                    await page.locator('[data-partner-id="1"]').click()
                    await page.set_viewport_size({'width':390,'height':844})
                    await expect(page.locator('#partnerOperation')).to_have_value('approve')
                    await page.locator('[data-action="managementPrepare"]').click()
                    await expect(page.locator('.management-comparison')).to_be_visible()
                    assert await page.locator('.management-comparison img').count()==0
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    await page.screenshot(path=str(output/f'partner-confirm-{language}-390.png'))
                    await page.locator('[data-action="close"]').last.click()
                    await page.set_viewport_size({'width':1440,'height':1000})
                await page.locator('#locale').select_option('uz')
                for partner_id,operation in ((1,'approve'),(1,'block'),(1,'unblock'),(2,'reject')):
                    await page.locator('[data-action="partnerList"]').click()
                    await page.locator(f'[data-partner-id="{partner_id}"]').click()
                    await page.locator('#partnerOperation').select_option(operation)
                    await prepare_and_save('uz')
                async with fixture.sessions() as db:
                    await db.execute(update(AdminPwaStepUp).where(AdminPwaStepUp.status == 'consumed').values(
                        created_at=datetime.now(timezone.utc)-timedelta(minutes=11)))
                    await db.commit()
                for language in ('uz','ru','tj'):
                    await page.locator('#locale').select_option(language)
                    await page.locator('[data-action="payoutList"]').click()
                    await page.locator('[data-payout-id="1"]').click()
                    await page.locator('#payoutDays').select_option('3')
                    await page.set_viewport_size({'width':390,'height':844})
                    await page.locator('[data-action="managementPrepare"]').click()
                    await expect(page.locator('.management-comparison')).to_be_visible()
                    assert await page.locator('.management-comparison img').count()==0
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    await page.screenshot(path=str(output/f'payout-confirm-{language}-390.png'))
                    await page.locator('[data-action="close"]').last.click()
                    await page.set_viewport_size({'width':1440,'height':1000})
                await page.locator('#locale').select_option('uz')
                for payout_id,operation in ((1,'deadline'),(1,'claim'),(1,'release'),(2,'reject')):
                    await page.locator('[data-action="payoutList"]').click()
                    await page.locator(f'[data-payout-id="{payout_id}"]').click()
                    await page.locator('#payoutOperation').select_option(operation)
                    await prepare_and_save('uz')
                await navigate('system',1440)
                for language in ('uz','ru','tj'):
                    await page.locator('#locale').select_option(language)
                    await page.locator('[data-action="deliveryList"]').click()
                    await page.locator('[data-delivery-id]').click()
                    await page.locator('#deliveryResolution').select_option('no_retry')
                    await page.locator('#deliveryReason').fill('QA reviewed <img src=x onerror=alert(1)>')
                    await page.set_viewport_size({'width':390,'height':844})
                    await page.locator('[data-action="managementPrepare"]').click()
                    await expect(page.locator('.management-comparison')).to_be_visible()
                    assert await page.locator('.management-comparison img').count()==0
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    await page.screenshot(path=str(output/f'reconciliation-confirm-{language}-390.png'))
                    await page.locator('[data-action="close"]').last.click()
                    await page.set_viewport_size({'width':1440,'height':1000})
                await page.locator('#locale').select_option('uz')
                await page.locator('[data-action="deliveryList"]').click()
                await page.locator('[data-delivery-id]').click()
                await page.locator('#deliveryResolution').select_option('no_retry')
                await page.locator('#deliveryReason').fill('Synthetic operator check')
                await prepare_and_save('uz')
                await page.locator('[data-action="deliveryList"]').click()
                await expect(page.locator('[data-delivery-id]')).to_have_count(0)
                await page.locator('.drawer-close').click()
                # Revocation between confirmation and proof fails before any write.
                before = await audit_count()
                await page.locator('[data-setting-kind="help_contact"]').click()
                await page.locator("#settingValue").fill("@revoked_session")
                await page.locator('[data-action="managementPrepare"]').click()
                await expect(page.locator(".management-comparison")).to_be_visible()
                async with fixture.sessions() as db:
                    (await db.get(AdminPwaSession, fixture.session_id)).revoked_at = datetime.now(timezone.utc)
                    await db.commit()
                await page.locator('[data-action="managementExecute"]').click()
                # Step-up deliberately returns 403 without disclosing session
                # status. A read-current tap revalidates the session with401.
                await page.locator('#drawerFoot [data-setting-kind="help_contact"]').click()
                await expect(page.locator('[data-action="signin"]')).to_be_visible()
                assert await audit_count() == before
                assert not errors, errors
                assert not await page.evaluate("window.cspFailures"), await page.evaluate("window.cspFailures")
            finally:
                await browser.close()
    finally:
        await fixture.engine.dispose()
    print("Management: real SQL + WebAuthn; UZ/RU/TJ 390/1440; settings/prices/marketing/account state+delete; cancel/CAS/lost-response/revoke passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/tmp/hsk-admin-pwa-settings"))
    asyncio.run(browser_checks(parser.parse_args().output))
