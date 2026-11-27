"""Plan-card presentation and region routing; all payment endpoints are synthetic."""
import os
from urllib.parse import urlsplit

import pytest
from test_miniapp_smoke import app_url, expect, mock_telegram_ready, route_static_files

pw = pytest.importorskip('playwright.sync_api')


def settle(page):
    page.evaluate('''()=>Promise.all(document.getAnimations().filter(a=>
        a.effect.getComputedTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{})))''')


def badges_share_the_term_row(page, selector):
    cards=page.locator(selector)
    for card in cards.all():
        name=card.locator('.plan-name').bounding_box()
        badge=card.locator('.badge').bounding_box()
        shape=card.bounding_box()
        assert name and badge and shape
        assert abs(name['y']+name['height']/2-badge['y']-badge['height']/2)<=1
        assert badge['x']>=name['x']+name['width']
        assert badge['x']+badge['width']<=shape['x']+shape['width']-10
        assert card.locator('.badge').evaluate('(e)=>e.scrollWidth<=e.clientWidth')


def overview(lang, count):
    terms = [('1_month', '10.00'), ('3_months', '27.00'), ('12_months', '90.00')][:count]
    def provider(currency):
        return [dict(plan_type=t, amount=a, currency=currency) for t,a in terms]
    def manual(currency):
        return {t: dict(base_amount=a,final_amount=a,currency=currency,discount_applied=False)
                for t,a in [('1_month',49),('10_days',19),('3_months',149)]}
    return dict(ok=True,language=lang,mode='subscription',checkout_allowed=True,
        analytics_user_id=7,attempt_id='layout-qa-attempt',pending_payment=None,
        access=dict(is_paid=False),payment_details='',payment_details_configured=True,
        prices=dict(visa=manual('TJS'),alipay=manual('CNY'),wechat=manual('CNY')),
        card_prices={c:manual('RUB' if c=='ru' else 'USD') for c in ['uz','ru','other']},
        lava=dict(mode='both',currency='USD',plans=provider('USD'),
                  plans_by_currency=dict(USD=provider('USD'),RUB=provider('RUB')),email='fixture@example.com'))


@pytest.mark.parametrize('lang',['uz','ru','tj'])
@pytest.mark.parametrize('count',[2,3])
def test_plan_cards_keep_all_terms_without_alternatives_and_route_region_changes(lang,count):
    with pw.sync_playwright() as driver:
        browser=getattr(driver,os.getenv('PWA_E2E_ENGINE','chromium')).launch()
        page=browser.new_context(viewport=dict(width=390,height=844),locale='en-US',timezone_id='UTC',color_scheme='light').new_page()
        page.set_default_timeout(8000)
        route_static_files(page);mock_telegram_ready(page)
        requests=[];errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        def api(route):
            path=urlsplit(route.request.url).path;requests.append(path)
            route.fulfill(json=overview(lang,count) if path.endswith('/overview') else dict(ok=True,recorded=True))
        page.route('**/api/subscription-miniapp/**',api)
        page.goto(app_url('/subscription.html?inline_manual=1&lang='+lang),wait_until='networkidle')
        expect(page.locator('#lavaPlans')).to_be_visible()
        expect(page.locator('#lavaPlans .plan')).to_have_count(count)
        settle(page)
        assert page.locator('#manualAlternative,#lavaAlternative,.reference-label,.plan-note').count()==0
        shapes=page.locator('#lavaPlans .plan').evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})')
        assert abs(shapes[0]['w']-page.locator('#lavaPlans').bounding_box()['width'])<=1
        if count==3:
            assert abs(shapes[1]['w']-shapes[2]['w'])<=1 and abs(shapes[1]['y']-shapes[2]['y'])<=1
            assert shapes[1]['y']>shapes[0]['y']
        else:
            assert abs(shapes[0]['w']-shapes[1]['w'])<=1 and shapes[1]['y']>shapes[0]['y']
        for width in [320,390,430]:
            page.set_viewport_size(dict(width=width,height=844))
            settle(page)
            badges_share_the_term_row(page,'#lavaPlans .plan')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.set_viewport_size(dict(width=390,height=844))
        if lang=='ru': page.screenshot(path=f'/tmp/hsk-plan-ui-lava-{count}-{os.getenv("PWA_E2E_ENGINE","chromium")}.png',full_page=True)
        page.locator('#lavaRegion').select_option('cn')
        expect(page.locator('#plans')).to_be_visible()
        expect(page.locator('#plans .plan')).to_have_count(3)
        expect(page.locator('#plans .old-price').first).to_be_visible()
        monthly=page.locator('#plans .plan[data-plan="1_month"]')
        settle(page)
        name=monthly.locator('.plan-name').bounding_box();badge=monthly.locator('.badge').bounding_box()
        assert abs(name['y']+name['height']/2-badge['y']-badge['height']/2)<=1
        color=monthly.locator('.badge').evaluate('(e)=>getComputedStyle(e).backgroundColor')
        rgb=[int(v) for v in color.removeprefix('rgb(').removesuffix(')').split(',')]
        assert rgb[1]>rgb[0] and rgb[1]>rgb[2],color
        if lang=='ru': page.screenshot(path=f'/tmp/hsk-plan-ui-manual-{count}-{os.getenv("PWA_E2E_ENGINE","chromium")}.png',full_page=True)
        for width in [320,430]:
            page.set_viewport_size(dict(width=width,height=844))
            settle(page)
            # The selected card animates its padding/size after a viewport
            # change. Assert the final geometry, not an intermediate frame.
            page.wait_for_function('''()=>{const card=document.querySelector('#plans .plan[data-plan="1_month"]');
                const a=card.querySelector('.plan-name').getBoundingClientRect();
                const b=card.querySelector('.badge').getBoundingClientRect();
                return Math.abs(a.y+a.height/2-b.y-b.height/2)<=1}''')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            name=monthly.locator('.plan-name').bounding_box();badge=monthly.locator('.badge').bounding_box()
            assert abs(name['y']+name['height']/2-badge['y']-badge['height']/2)<=1
            badges_share_the_term_row(page,'#plans .plan')
        page.locator('#planRegion').select_option('other')
        expect(page.locator('#lavaPlans')).to_be_visible()
        expect(page.locator('#lavaPlans .plan')).to_have_count(count)
        assert page.locator('#lavaPlans').inner_text().count('USD')>=count
        assert requests.count('/api/subscription-miniapp/overview')==1
        assert not any(path.endswith('/submit') or path.endswith('/lava/start') for path in requests)
        assert not errors,errors
        browser.close()
