"""Use the real Telegram SDK, not a stub that invents initData on every page."""
import json
import re
from urllib.parse import urlencode, urlparse

import pytest
from playwright.sync_api import expect
from test_miniapp_smoke import STATIC_ROOT, TELEGRAM_SDK_ROUTE, app_url, json_response, page


@pytest.mark.parametrize('entry',['course','onboarding'])
@pytest.mark.parametrize('storage_blocked',[False,True])
@pytest.mark.parametrize('paid',[False,True])
def test_real_sdk_survives_hsk30_onboarding_documents(page,entry,storage_blocked,paid):
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    if storage_blocked:
        page.add_init_script("Object.defineProperty(window,'sessionStorage',{configurable:true,get(){throw new DOMException('disabled','SecurityError')}})")
    proof=urlencode({'query_id':'handoff-test','user':json.dumps({'id':42,'first_name':'QA'}),'auth_date':'1792341600','hash':'0'*64})
    fragment='#'+urlencode({'tgWebAppData':proof,'tgWebAppVersion':'8.0','tgWebAppPlatform':'ios'})
    page.route(TELEGRAM_SDK_ROUTE,lambda route:route.fulfill(status=200,content_type='application/javascript',body=(STATIC_ROOT/'assets/telegram-web-app.js').read_text()))
    page.route('https://telegram.org/**',lambda route:pytest.fail('Course/onboarding must not fetch a third-party SDK'))
    page.route('**/api/**',lambda route:json_response(route,{'ok':True}))
    state={'saved':False,'maps':0}
    headers=[]
    access={'feature_enabled':True,'payment_enabled':True,'allowed':paid,'paid_access':paid}
    tracks={'ok':True,'active_track':'hsk30','active_level':'nhsk1','tracks':{'hsk30':{'level':'nhsk1','live_levels':['nhsk1'],'access':access}},'hsk30_unlock':{'payment_enabled':True,'price_tjs':10,'price_display':'10 TJS'},'hsk30_promo':{'eligible':False}}
    def checked(route,data,status=200):
        actual=route.request.headers.get('x-telegram-init-data')
        headers.append(actual)
        if actual!=proof:
            json_response(route,{'ok':False,'error':'auth_required'},status=401)
        else:json_response(route,data,status=status)
    page.route('**/api/v3/course-tracks',lambda route:checked(route,tracks))
    def course_map(route):
        state['maps']+=1
        if state['saved'] and not paid:
            checked(route,{'ok':False,'error':'hsk30_unlock_required','level':'nhsk1','hsk30_access':access},status=403)
            return
        level='nhsk1' if state['saved'] else 'hsk1'
        data=json.loads((STATIC_ROOT/f'course_v3_data/{level}.json').read_text())
        data.update({'ok':True,'authenticated':True,'level':level,'user':{'name':'QA','language':'ru','is_paid':paid,'onboarding_completed':state['saved']},'lesson_limit':{'allowed':True,'hsk30_access':access},'notify':{'enabled':True}})
        checked(route,data)
    page.route(re.compile(r'.*/api/v3/map(?:\?.*)?$'),course_map)
    def save(route):
        assert route.request.post_data_json['level']=='nhsk1'
        state['saved']=True
        checked(route,{'ok':True,'level':'nhsk1','lesson':1,'tab':'course'})
    page.route('**/api/miniapp/onboarding',save)
    path='/course-v3.html?lang=ru&level=hsk1' if entry=='course' else '/course_v3_onboarding.html?lang=ru'
    page.goto(app_url(path)+fragment,wait_until='networkidle')
    page.wait_for_url(re.compile(r'course_v3_onboarding\.html'),wait_until='networkidle')
    page.locator('#cta').click()
    page.locator('button[data-track=hsk30]').click()
    page.locator('#cta').click()
    page.locator('#cta').click()
    page.locator('#cta').click()
    page.wait_for_url(re.compile(r'course-v3\.html'),wait_until='networkidle')
    expect(page.locator('#s-course')).not_to_contain_text('Откройте курс из бота')
    assert page.evaluate('INIT_DATA')==proof
    assert 'tgWebAppData=' in page.url.split('#',1)[1]
    assert state['saved']
    assert headers and all(h==proof for h in headers)
    assert state['maps'] >= (2 if entry=='course' else 1)
    # Credentials stay in the Telegram fragment/header, not HTTP query strings.
    assert 'tgWebAppData' not in urlparse(page.url).query
    if paid:
        expect(page.locator('#s-course .node')).not_to_have_count(0)
    else:
        expect(page.locator('#sheet.on')).to_be_visible()
        expect(page.locator('#s-course .node')).to_have_count(0)
    assert not errors


@pytest.mark.parametrize('with_proof',[False,True])
def test_real_sdk_never_bypasses_missing_or_rejected_auth(page,with_proof):
    page.route(TELEGRAM_SDK_ROUTE,lambda route:route.fulfill(status=200,content_type='application/javascript',body=(STATIC_ROOT/'assets/telegram-web-app.js').read_text()))
    calls=[]
    def denied(route):
        calls.append(route.request.headers.get('x-telegram-init-data'))
        json_response(route,{'ok':False,'error':'auth_required'},status=401)
    page.route('**/api/v3/course-tracks',denied)
    page.route(re.compile(r'.*/api/v3/map(?:\?.*)?$'),denied)
    fragment='#'+urlencode({'tgWebAppData':'query_id=forged&hash=invalid','tgWebAppVersion':'8.0'}) if with_proof else ''
    page.goto(app_url('/course-v3.html?lang=ru')+fragment,wait_until='networkidle')
    expect(page.locator('#s-course')).to_contain_text('Откройте курс из бота')
    expect(page.locator('#s-course .node')).to_have_count(0)
    assert bool(calls)==with_proof
