"""Reported placement counts, first-open strokes, and receipt-specific Pro return."""
import json
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect
from test_miniapp_smoke import STATIC_ROOT, app_url, json_response, mock_telegram_ready, page


@pytest.mark.parametrize('lang', ['uz', 'ru', 'tj'])
def test_placement_reports_answer_counts_without_claiming_level_mastery(page, lang, tmp_path):
    errors=[]
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(app_url('/course_v3_test.html?lang='+lang), wait_until='networkidle')
    page.evaluate('runPlacement();pans=[true,true,false,false,true,true];pResult()')
    rows=page.locator('#placement .mrow')
    assert rows.locator('.mv').all_text_contents()==['2 / 2','0 / 2','1 / 1','1 / 1']
    assert rows.filter(has=page.locator('.ml',has_text='HSK 1')).count()==1
    assert page.locator('#placement .rec .ml').inner_text()=='HSK 1'
    assert '100%' not in page.locator('#placement .meter').inner_text()
    page.screenshot(path=str(tmp_path / ('placement-'+lang+'.png')))
    page.evaluate('pans=PQ.map(()=>true);pResult()')
    assert page.locator('#placement .rec .ml').inner_text()=='HSK 4'
    page.evaluate('runPlacement()')
    assert page.evaluate('pans.length')==0
    assert not errors


@pytest.mark.parametrize('char', ['谢','你','好'])
def test_strokes_load_on_first_open_without_a_cdn(page,char,tmp_path):
    errors=[]
    requested=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    def strokes(route):
        requested.append(route.request.url)
        code=ord(parse_qs(urlparse(route.request.url).query)['char'][0])
        data=(STATIC_ROOT.parents[1]/'android/app/src/main/assets/strokes'/f'{code}.json').read_text()
        route.fulfill(status=200,content_type='application/json',body=data)
    page.route('**/api/v3/stroke?*',strokes)
    page.route('**/hanzi-writer-data*/**',lambda route:pytest.fail('Stroke CDN must not be requested'))
    page.goto(app_url('/hsk-lugat.html?theme=light&fast=1&char='+char+'&lang=ru'),wait_until='networkidle')
    expect(page.locator('#fast-strokes')).to_contain_text('черт')
    expect(page.locator('#fast-status')).to_be_empty()
    expect(page.locator('#fast-play')).to_be_enabled()
    assert page.locator('#fast-box svg path').count()>0
    page.locator('#fast-play').click()
    assert len(requested)==1
    page.screenshot(path=str(tmp_path / f'strokes-{ord(char)}.png'))
    assert not errors


@pytest.mark.parametrize('lang', ['uz','ru','tj'])
@pytest.mark.parametrize('granted', [True,False])
def test_pro_receipt_submission_reopen_and_origin_return_or_admin(page,lang,granted,tmp_path):
    errors=[]
    uploads=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    mock_telegram_ready(page)
    overview={'ok':True,'language':lang,'mode':'subscription','pending_payment':None,'support_url':'https://t.me/hsk_support_test','prices':{}}
    page.route('**/api/subscription-miniapp/overview',lambda route:json_response(route,overview))
    page.route('**/api/subscription-miniapp/submit',lambda route:uploads.append(route.request.post_data_json) or json_response(route,{'ok':True,'status':'pending','payment_id':81,'provisional_access':granted}))
    page.goto(app_url(f'/subscription.html?lang={lang}&return_to=course&return_tab=mashq&return_level=hsk2'),wait_until='networkidle')
    page.evaluate('''lang=>{
      state.lang=lang;var data=mockOverview();data.support_url='https://t.me/hsk_support_test';
      applyOverview(data);state.preview=false;state.quote={};state.screenshotDataUrl='data:image/png;base64,aGVsbG8=';
      Telegram.WebApp.openTelegramLink=url=>window.openedSupport=url;
    }''',lang)
    page.evaluate('submitPayment()')
    page.wait_for_function('state.pending===true && !state.busy')
    assert len(uploads)==1
    expected=page.evaluate('state.pendingPayment.provisional_access?tr().proReviewAccess:tr().proReviewWait')
    expect(page.locator('#doneText')).to_have_text(expected)
    assert page.locator('#botReturnBtn').inner_text()!=page.evaluate('tr().returnToBot')
    page.evaluate('Promise.all(document.getAnimations().filter(a=>a.effect.getTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{})))')
    page.screenshot(path=str(tmp_path / f'receipt-{lang}-{granted}.png'))
    # A reopened checkout must preserve this receipt's grant instead of spending another ticket.
    overview['pending_payment']={'id':81,'plan_type':'1_month','provisional_access':granted}
    page.reload(wait_until='networkidle')
    expect(page.locator('#doneText')).to_have_text(expected)
    page.evaluate('Telegram.WebApp.openTelegramLink=url=>window.openedSupport=url')
    if granted:
        page.route('**/course-v3.html?*',lambda route:route.fulfill(status=200,content_type='text/html',body='Course origin'))
        page.locator('#botReturnBtn').click()
        page.wait_for_url('**/course-v3.html?*')
        query=parse_qs(urlparse(page.url).query)
        assert query['tab']==['mashq']
        assert query['level']==['hsk2']
        assert query['lang']==[lang]
    else:
        page.locator('#botReturnBtn').click()
        assert page.evaluate('openedSupport')=='https://t.me/hsk_support_test'
        assert '/subscription.html' in page.url
    assert not errors


@pytest.mark.parametrize('origin', ['course_v3_voice.html','course_v3_recognition.html','course_v3_memorize.html','course_v3_pronunciation.html','course_v3_mistakes.html','course_v3_test.html','https://evil.example/steal'])
def test_pro_return_allows_only_the_original_known_practice_pages(page,origin):
    mock_telegram_ready(page)
    page.route('**/api/subscription-miniapp/overview',lambda route:json_response(route,{'ok':True,'language':'ru','mode':'subscription','prices':{}}))
    page.goto(app_url('/subscription.html?lang=ru&return_to=course&return_page='+origin+'&return_level=hsk3'),wait_until='networkidle')
    target=page.evaluate('courseReturnUrl()')
    if origin.startswith('https:'):
        assert target.startswith('/course-v3.html?')
    else:
        assert target.startswith('/'+origin+'?')
    assert parse_qs(urlparse(target).query)['level']==['hsk3']
