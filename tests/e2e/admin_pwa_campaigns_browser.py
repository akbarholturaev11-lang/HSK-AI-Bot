"""V10 campaign forms against real ASGI/SQL/native WebAuthn; synthetic delivery only."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import html
import json
from pathlib import Path
from io import BytesIO
from PIL import Image

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from playwright.async_api import async_playwright, expect
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.admin_api.pwa_bootstrap import create_admin_pwa_bootstrap_router
from app.admin_api.pwa_campaign_assets import create_admin_pwa_campaign_assets_router
from app.admin_api.pwa_campaigns import create_admin_pwa_campaigns_router
from app.admin_api.pwa_marketing import create_admin_pwa_marketing_router
from app.admin_api.pwa_outbound import create_admin_pwa_outbound_router, create_message_drainer
from app.admin_api.pwa_read import create_admin_pwa_read_router
from app.admin_api.pwa_step_up_transport import create_admin_pwa_step_up_router
from app.admin_api.pwa_webauthn_login_transport import create_admin_pwa_passkey_login_router
from app.db.base import Base
from app.db.models.ad_campaign import AdCampaign
from app.db.models.admin_pwa_campaign_asset import AdminPwaCampaignAsset
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.release_feedback import ReleaseFeedbackCampaign
from app.db.models.user import User
from app.repositories.ad_campaign_repo import AdCampaignRepository
from app.services.broadcast_translation_service import encode_localized_broadcast_text
from tests.e2e.admin_pwa_browser import setup_fresh_login, authenticate_fresh_launch
from tests.e2e.admin_pwa_step_up_gate import install_step_up_gate, wait_step_up, finish_step_up
from tests.test_admin_pwa_payment_review import PaymentFixtures

ORIGIN = 'https://hskai.app'
ROOT = Path(__file__).resolve().parents[2]


async def browser_checks(output):
    output.mkdir(parents=True, exist_ok=True)
    fixture = PaymentFixtures()
    fixture.engine = create_async_engine('sqlite+aiosqlite:///:memory:', poolclass=StaticPool)
    async with fixture.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    fixture.sessions = async_sessionmaker(fixture.engine, expire_on_commit=False)
    await fixture.seed_payment()
    async with fixture.sessions() as db:
        (await db.get(User, 2)).language = 'ru'
        now = datetime.now(timezone.utc)
        await AdCampaignRepository(db).create(title='QA ad <script>',
            message_text=encode_localized_broadcast_text({lang: html.escape('QA ad ' + lang + ' <中文>')
                                                        for lang in ('uz', 'ru', 'tj')}),
            content_type='text', media_file_id=None, starts_at=now,
            ends_at=now + timedelta(hours=24), send_count_total=1, target_languages=['ru'], is_active=False)
        await db.commit()
    common = dict(settings_obj=fixture.settings, session_factory=fixture.sessions)
    app, sent, calls, errors = FastAPI(), [], [], []
    async def emit(message):
        sent.append(message)
        return 555
    drainer = create_message_drainer(**common, emit=emit, drain_batches=1)
    for factory in (create_admin_pwa_bootstrap_router, create_admin_pwa_read_router,
                    create_admin_pwa_passkey_login_router, create_admin_pwa_step_up_router,
                    create_admin_pwa_marketing_router):
        app.include_router(factory(**common))
    upload_calls=[]
    async def upload(media):
        assert media.actor_telegram_id==9001 and Path(media.path).is_file()
        upload_calls.append(media.media_type)
        return 'PRIVATE_browser_media_'+str(len(upload_calls))
    app.include_router(create_admin_pwa_campaign_assets_router(**common,upload=upload))
    app.include_router(create_admin_pwa_campaigns_router(**common, drainer=drainer))
    app.include_router(create_admin_pwa_outbound_router(**common, emit=emit, drainer=drainer))
    async def serve(route):
        request = route.request
        assert request.url.startswith(ORIGIN + '/')
        path = request.url.removeprefix(ORIGIN)
        if path == '/admin/sw.js':
            await route.abort()
            return
        calls.append(path)
        if path == '/api/admin/v1/statistics':
            await route.fulfill(status=200, json={'ok': True, 'available': False})
            return
        async with AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN) as client:
            response = await client.request(request.method, path, headers=await request.all_headers(),
                                            content=request.post_data_buffer)
        headers = dict(response.headers)
        headers.pop('content-length', None)
        cookies = response.headers.get_list('set-cookie')
        if cookies:
            headers['set-cookie'] = '\n'.join(cookies)
        await route.fulfill(status=response.status_code, headers=headers, body=response.content)
    async def retire_test_quota():
        async with fixture.sessions() as db:
            await db.execute(update(AdminPwaStepUp).values(created_at=datetime.now(timezone.utc)-timedelta(minutes=11)))
            await db.commit()
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                context = await browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block')
                await context.route('**/*', serve)
                page = await context.new_page()
                await install_step_up_gate(page)
                page.on('pageerror', lambda error: errors.append(str(error)))
                await page.add_init_script("window.cspFailures=[];document.addEventListener('securitypolicyviolation',e=>cspFailures.push(e.violatedDirective))")
                await setup_fresh_login(context, page, fixture)
                await page.goto(ORIGIN + '/admin/')
                await page.wait_for_load_state('networkidle')
                await authenticate_fresh_launch(page)
                await expect(page.locator('.sidebar')).to_be_visible()
                async def marketing(language='uz'):
                    await page.set_viewport_size({'width': 1440, 'height': 1000})
                    await page.locator('#locale').select_option(language)
                    await page.locator('.nav [data-route=marketing]').click()
                async def create(kind, language='uz'):
                    await marketing(language)
                    await page.locator(f'[data-campaign-list="{kind}"]').click()
                    await page.locator(f'[data-campaign-create="{kind}"]').click()
                async def fill(kind):
                    if kind == 'release':
                        await page.locator('#releaseTitle').fill('QA release <script>')
                    for lang in ('uz', 'ru', 'tj'):
                        panel = page.locator('details.notice-languages').filter(has=page.locator(
                            ('#releaseText-' if kind == 'release' else '#discountTitle-') + lang))
                        if await panel.get_attribute('open') is None:
                            await panel.locator('summary').click()
                        if kind == 'release':
                            await page.locator('#releaseText-' + lang).fill('QA 中文 ' + lang + ' <b>plain</b>')
                        else:
                            await page.locator('#discountTitle-' + lang).fill('QA discount ' + lang)
                            await page.locator('#discountReason-' + lang).fill('QA reason <test> ' + lang)
                async def begin():
                    await retire_test_quota()
                    before = calls.count('/api/admin/v1/auth/step-up/options')
                    await page.locator('[data-action=managementPrepare]').click()
                    await wait_step_up(page)
                    assert calls.count('/api/admin/v1/auth/step-up/options') == before + 1
                for language in ('uz', 'ru', 'tj'):
                    for kind in ('release', 'discount'):
                        await create(kind, language)
                        await fill(kind)
                        await page.locator('details.notice-languages').evaluate_all("(panels,lang)=>panels.forEach(panel=>panel.open=panel.querySelector('summary').textContent===lang.toUpperCase())",language)
                        await page.locator('#drawerContent').evaluate('(el)=>el.scrollTop=0')
                        assert await page.locator('#drawerContent script').count() == 0
                        for width in (1440, 390):
                            await page.set_viewport_size({'width': width, 'height': 1000 if width == 1440 else 844})
                            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                            await page.screenshot(path=str(output / f'{kind}-{language}-{width}.png'))
                        await begin()
                        await page.evaluate('window.cancelStepUp()')
                        await expect(page.locator('.drawer')).not_to_have_attribute('aria-busy', 'true')
                        await expect(page.locator('#releaseTitle' if kind == 'release' else '#discountTitle-uz')).to_have_value(
                            'QA release <script>' if kind == 'release' else 'QA discount uz')
                        await page.locator('.drawer-close').click()
                async with fixture.sessions() as db:
                    assert await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)) == 0
                await create('discount')
                # Native validation opens the missing-language disclosure in the original form.
                await page.locator('#discountTitle-uz').fill('QA initial')
                await page.locator('[data-action=managementPrepare]').click()
                assert await page.locator('details.notice-languages').nth(1).get_attribute('open') is not None
                await fill('discount')
                await page.locator('#discountTarget').fill('1')
                await page.locator('#discountTarget').dispatch_event('change')
                await expect(page.locator('#discountSegment')).to_be_hidden()
                await page.locator('#discountQuota').fill('1')
                await page.locator('#campaignActive').select_option('true')
                await begin()
                await finish_step_up(page)
                saved_label=json.loads((ROOT/'localization/ui/uz/miniapp.json').read_text())['messages']['ui.admin_pwa.changesSaved']
                await expect(page.locator('#drawerTitle')).to_have_text(saved_label, timeout=15000)
                async with fixture.sessions() as db:
                    row = await db.scalar(select(DiscountCampaign))
                    assert row.target_user_id == 1 and row.target_telegram_id is None and row.is_active
                    assert not row.notify_enabled and row.quota_total == 1
                await page.locator('.drawer-close').click()
                await create('release')
                await fill('release')
                buffer=BytesIO();Image.new('RGB',(160,90),(26,108,116)).save(buffer,format='PNG')
                await page.locator('#campaignMediaSection summary').click()
                await page.locator('#campaignMediaFile').set_input_files({'name':'QA-release.png','mimeType':'image/png','buffer':buffer.getvalue()})
                await expect(page.locator('#campaignMediaPreview img')).to_be_visible(timeout=15000)
                await begin();await page.evaluate('window.cancelStepUp()')
                await expect(page.locator('.drawer')).not_to_have_attribute('aria-busy','true')
                await expect(page.locator('#campaignMediaPreview img')).to_be_visible()
                await page.locator('#releaseFeature').select_option('course')
                await page.set_viewport_size({'width': 390, 'height': 844})
                await begin()
                await finish_step_up(page)
                await expect(page.locator('[data-message-job]')).to_be_visible(timeout=15000)
                assert len(sent) == 1 and sent[0].reply_markup['inline_keyboard'][0][0]['callback_data'] == 'relfb:1:try'
                assert '&lt;b&gt;plain&lt;/b&gt;' in sent[0].text and sent[0].photo_file_id
                async with fixture.sessions() as db:
                    assert (await db.scalar(select(AdminPwaCampaignAsset))).status=='used'
                await page.screenshot(path=str(output / 'release-sent-uz-390.png'))
                await page.locator('.drawer-close').click()
                await marketing()
                await page.locator('[data-campaign-list=ad]').click()
                await page.locator('[data-campaign-detail="1"]').click()
                await begin()
                await finish_step_up(page)
                await expect(page.locator('[data-message-job]')).to_be_visible(timeout=15000)
                assert len(sent) == 2
                await page.locator('.drawer-close').click()
                await page.locator('[data-campaign-list=ad]').click()
                await page.locator('[data-campaign-detail="1"]').click()
                await expect(page.locator('[data-action=managementPrepare]')).to_have_count(0)
                async with fixture.sessions() as db:
                    assert (await db.get(ReleaseFeedbackCampaign, 1)).status == 'sent'
                    row = await db.get(AdCampaign, 1)
                    assert row.rounds_sent == 1 and not row.is_active and row.next_send_at is None
                    assert await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)) == 3
                await page.locator('.drawer-close').click()
                async def button_draft(language):
                    await marketing(language)
                    await page.locator('[data-campaign-list=ad]').click()
                    await page.locator('[data-marketing-kind=campaign_draft]').click()
                    await page.locator('#campaignTitle').fill('QA button campaign')
                    for lang in ('uz','ru','tj'):
                        panel=page.locator('.campaign-locale-copy').filter(has=page.locator('#campaignText-'+lang))
                        if await panel.get_attribute('open') is None:
                            await panel.locator('summary').click()
                        await page.locator('#campaignText-'+lang).fill('QA button copy '+lang)
                    await page.locator('[data-campaign-language=ru]').check()
                    await page.locator('#campaignButtonSection summary').click()
                    await page.locator('#campaignButtonAction').select_option('url')
                    await page.locator('#campaignButtonUrl').fill('https://example.invalid/course')
                    await page.locator('#campaignButtonCustom').check()
                    for lang in ('uz','ru','tj'):
                        await page.locator('#campaignButtonLabel-'+lang).fill('QA '+lang+' 中文 <test>')
                for language in ('uz','ru','tj'):
                    await button_draft(language)
                    for width in (1440,390):
                        await page.set_viewport_size({'width':width,'height':1000 if width==1440 else 844})
                        await page.locator('#campaignButtonSection').scroll_into_view_if_needed()
                        assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                        await page.screenshot(path=str(output/f'campaign-button-{language}-{width}.png'))
                    await begin()
                    await page.evaluate('window.cancelStepUp()')
                    await expect(page.locator('.drawer')).not_to_have_attribute('aria-busy','true')
                    await expect(page.locator('#campaignButtonAction')).to_have_value('url')
                    await expect(page.locator('#campaignButtonUrl')).to_have_value('https://example.invalid/course')
                    await expect(page.locator('#campaignButtonLabel-ru')).to_have_value('QA ru 中文 <test>')
                    await page.locator('.drawer-close').click()
                await button_draft('uz')
                await page.locator('#campaignButtonAction').select_option('course')
                await expect(page.locator('#campaignButtonUrl')).to_be_disabled()
                await begin()
                await finish_step_up(page)
                await expect(page.locator('#drawerTitle')).to_have_text(saved_label,timeout=15000)
                await page.locator('#drawerFoot [data-campaign-list=ad]').click()
                await page.locator('[data-campaign-detail="2"]').click()
                assert await page.locator('#drawerContent img').count()==0
                await expect(page.locator('#drawerContent')).to_contain_text('QA uz 中文 <test>')
                await begin()
                await finish_step_up(page)
                await expect(page.locator('[data-message-job]')).to_be_visible(timeout=15000)
                assert len(sent)==3
                assert sent[-1].reply_markup['inline_keyboard'][0][0]=={'text':'QA ru 中文 <test>','callback_data':'promo:action:course'}
                async with fixture.sessions() as db:
                    assert await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit))==5
                await page.locator('.drawer-close').click()
                buffer=BytesIO();Image.new('RGB',(160,90),(26,108,116)).save(buffer,format='PNG')
                photo=buffer.getvalue()
                for language in ('uz','ru','tj'):
                    await button_draft(language)
                    await page.locator('#campaignMediaSection summary').click()
                    await page.locator('#campaignMediaFile').set_input_files({'name':'QA-photo.png','mimeType':'image/png','buffer':photo})
                    await expect(page.locator('#campaignMediaPreview img')).to_be_visible(timeout=15000)
                    assert await page.locator('#campaignMediaPreview img').evaluate('(image)=>image.naturalWidth===160')
                    await page.set_viewport_size({'width':390,'height':844})
                    await page.locator('#campaignMediaSection').scroll_into_view_if_needed()
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    await page.screenshot(path=str(output/f'campaign-media-{language}-390.png'))
                    await begin();await page.evaluate('window.cancelStepUp()')
                    await expect(page.locator('.drawer')).not_to_have_attribute('aria-busy','true')
                    await expect(page.locator('#campaignMediaPreview img')).to_be_visible()
                    await expect(page.locator('[data-action=managementPrepare]')).to_be_enabled()
                    await page.locator('[data-action=campaignMediaClear]').click()
                    await expect(page.locator('#campaignMediaPreview img')).to_have_count(0)
                    await page.locator('.drawer-close').click()
                for media in ('photo','video'):
                    await button_draft('uz')
                    await page.locator('#campaignMediaSection summary').click()
                    payload=photo if media=='photo' else (ROOT/'tests/fixtures/admin_pwa_course_ad_test.mp4').read_bytes()
                    await page.locator('#campaignMediaFile').set_input_files({'name':'QA-media.'+('png' if media=='photo' else 'mp4'),'mimeType':'image/png' if media=='photo' else 'video/mp4','buffer':payload})
                    await expect(page.locator('#campaignMediaPreview '+('img' if media=='photo' else 'video'))).to_be_visible(timeout=150000)
                    if media=='video':await expect(page.locator('#campaignMediaPreview video')).to_have_js_property('videoWidth',64)
                    await begin();await finish_step_up(page)
                    await expect(page.locator('#drawerTitle')).to_have_text(saved_label,timeout=15000)
                    async with fixture.sessions() as db:
                        ad=await db.scalar(select(AdCampaign).order_by(AdCampaign.id.desc()).limit(1))
                        ad_id=ad.id
                        assert ad.content_type==media and ad.media_file_id.startswith('PRIVATE_browser_media_')
                        assert not ad.is_active
                        used=await db.scalar(select(AdminPwaCampaignAsset).where(AdminPwaCampaignAsset.command_id==
                            (await db.scalar(select(AdminPwaCommandAudit.id).order_by(AdminPwaCommandAudit.created_at.desc()).limit(1)))))
                        assert used and used.status=='used'
                    await page.locator('#drawerFoot [data-campaign-list=ad]').click()
                    await page.locator(f'[data-campaign-detail="{ad_id}"]').click()
                    await begin();await finish_step_up(page)
                    await expect(page.locator('[data-message-job]')).to_be_visible(timeout=15000)
                    assert (sent[-1].photo_file_id if media=='photo' else sent[-1].video_file_id).startswith('PRIVATE_browser_media_')
                    assert sent[-1].reply_markup['inline_keyboard'][0][0]['url']=='https://example.invalid/course'
                    await page.locator('.drawer-close').click()
                assert len(upload_calls)==6 and len(sent)==5
                assert not errors, errors
                assert not await page.evaluate('cspFailures')
            finally:
                await browser.close()
    finally:
        await fixture.engine.dispose()
    print('Campaigns: real ASGI/WebAuthn; UZ/RU/TJ 390/1440, one-window cancel, native personal discount, claimed release/ad delivery, localized buttons, owned photo/video staging and no duplicate sends passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    asyncio.run(browser_checks(parser.parse_args().output))
