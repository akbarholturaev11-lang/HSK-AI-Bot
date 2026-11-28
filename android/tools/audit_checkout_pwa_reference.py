#!/usr/bin/env python3
"""Read-only PWA reference screenshots for the native checkout audit.

Uses shipped frontend assets and the real HTML response renderer with synthetic
HTTP responses. No DB session, provider, real purchase or learner source write.
Run in the existing Playwright development environment with --help first.
"""
from pathlib import Path
from urllib.parse import urlsplit
import os,sys,json,mimetypes,argparse,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',default='/tmp/hsk-checkout-audit')
parser.add_argument('--engine',choices=('chromium','webkit'),default='chromium')
args=parser.parse_args()
# This isolated rendering process never inherits a production DB/provider target.
os.environ.update(DATABASE_URL='sqlite+aiosqlite:///:memory:',BOT_TOKEN='9123456:synthetic-test-only-unusable-token',REDIS_URL='redis://127.0.0.1:1/0')
os.chdir(ROOT)
from playwright.sync_api import sync_playwright
from fastapi import Request
from app.api.pwa_auth import _pwa_inline_html
STATIC=ROOT/'app/static'; OUT=Path(args.output);OUT.mkdir(parents=True,exist_ok=True)
PLANS=[{'plan_type':k,'amount':n,'currency':'USD','months':m,'days':d} for k,n,m,d in [('1_month','10.00',1,30),('3_months','27.00',3,90),('6_months','50.00',6,180),('12_months','90.00',12,365)]]
prices={'visa':{p:{'final_amount':n,'base_amount':n,'currency':'TJS'} for p,n in [('1_month',10),('10_days',10),('3_months',10)]},'alipay':{'1_month':{'final_amount':66,'base_amount':66,'currency':'CNY'}},'wechat':{'1_month':{'final_amount':66,'base_amount':66,'currency':'CNY'}}}
BASE={'ok':True,'mode':'subscription','language':'uz','preferred_currency':'TJS','checkout_allowed':True,'attempt_id':'fixture-manual','payment_details_configured':True,'prices':prices,'card_prices':{r:{p:{'final_amount':'10.00','base_amount':'10.00','currency':c} for p in prices['visa']} for r,c in [('uz','UZS'),('ru','RUB'),('other','USD')]},'support_url':'https://support.example.invalid','lava':{'mode':'both','email':'','plans':PLANS}}
scenario={'overview':BASE,'status':'pending','decision':'pending'};results=[]
def route(r):
 u=urlsplit(r.request.url);p=u.path
 if u.hostname!='reference.invalid':r.fulfill(status=200,content_type='text/plain',body='local fixture');return
 if p=='/iphone-pwa/course':
  r.fulfill(content_type='text/html',body='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/course_v3_data/design-tokens.css"><link rel="stylesheet" href="/course_v3_data/iphone-pwa-inline-pro.css"></head><body><script src="/course_v3_data/hsk-miniapp-i18n.js"></script><script src="/course_v3_data/hsk-course-i18n.js"></script><script src="/course_v3_data/hsk-subscription-presentation.js"></script><script src="/course_v3_data/iphone-pwa-inline-pro.js"></script></body></html>''')
 elif p=='/iphone-pwa/checkout':
  req=Request({'type':'http','headers':[]});res=_pwa_inline_html(req,'app/static/subscription.html',{},revalidate=False)
  r.fulfill(content_type='text/html',body=res.body)
 elif p=='/api/v3/pwa-auth/session':r.fulfill(json={'ok':True,'user_id':7,'csrf':'fixture'})
 elif p.endswith('/overview'):r.fulfill(json=scenario['overview'])
 elif p.endswith('/exit-offer'):r.fulfill(json={'ok':True,'available':True,'accepted':True,'percent':20})
 elif p.endswith('/lava/start'):r.fulfill(json={'ok':True,'checkout_id':7,'payment_url':'https://pay.lava.top/fixture','amount':'10.00','currency':'USD'})
 elif p.endswith('/lava/status'):r.fulfill(json={'ok':True,'checkout_id':7,'status':scenario['status'],'pro_until':'2026-12-31T00:00:00Z'})
 elif p.endswith('/payment-status'):r.fulfill(json={'ok':True,'payment_id':71,'status':scenario['decision'],'plan_type':'1_month'})
 elif p.endswith('/quote'):r.fulfill(json={'ok':True,'quote':{'pay_amount':'10','pay_currency':'TJS','payment_details':'TEST RECEIPT CHECKOUT','qr':{'available':False}}})
 elif p.startswith('/api/'):r.fulfill(json={'ok':True})
 else:
  f=STATIC/p.lstrip('/')
  if f.is_file():r.fulfill(path=str(f),content_type=mimetypes.guess_type(f)[0] or 'application/octet-stream')
  else:r.fulfill(status=404,body='')
def shot(page,name):
 page.wait_for_timeout(150);page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),name
 results.append({'state':name,'screenshot':name+'.png','horizontal_overflow':False})
def inline(page,lang='uz'):
 page.goto('https://reference.invalid/iphone-pwa/course');page.evaluate("window.open=()=>({closed:false,focus(){}})")
 page.evaluate("lang=>HSKPwaInlinePro.open({source:'v3_locked_lesson',lang})",lang)
 page.locator('.hip-plan').first.wait_for();page.locator('select').select_option('other')
with sync_playwright() as pw:
 browser=getattr(pw,args.engine).launch(headless=True)
 page=browser.new_page(viewport={'width':411,'height':914},device_scale_factor=2.625)
 page.route('**/*',route); errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.emulate_media(reduced_motion='reduce')
 inline(page);shot(page,'pwa-limit-primary')
 page.get_by_role('button',name='Boshqa tariflar',exact=True).click();shot(page,'pwa-limit-more')
 page.locator('select').select_option('uz');shot(page,'pwa-country-other')
 page.locator('select').select_option('other');page.locator('.hip-primary').click();page.locator('input[type=email]').wait_for();shot(page,'pwa-email')
 page.locator('input[type=email]').fill('broken');page.locator('input[type=email]').press('Enter');shot(page,'pwa-email-error')
 page.locator('input[type=email]').fill('fixture@example.com');shot(page,'pwa-email-filled');page.locator('input[type=email]').press('Enter');page.wait_for_timeout(400);shot(page,'pwa-provider-pending')
 scenario['status']='paid';page.wait_for_timeout(5500);shot(page,'pwa-provider-paid')
 for lang in ('uz','ru','tj'):
  scenario['status']='pending';inline(page,lang)
  # first step uses one X; source action requests the real account-offer fixture.
  page.locator('.hip-close').click()
  source=(STATIC/'course_v3_data/iphone-pwa-inline-pro.js').read_text()
  words=re.search(r'\b'+lang+r': \{(.*?)\}\s*[,\n]',source,re.S).group(1)
  title=re.search(r'\bexitTitle:"([^"]*)"',words).group(1)
  page.get_by_text(title,exact=True).wait_for()
  shot(page,'pwa-exit-'+lang)
 # Shared real checkout shell, with the actual PWA bridge injected by the server renderer.
 scenario['overview']=BASE
 inline(page);page.locator('select').select_option('tj');page.locator('.hip-primary').click()
 manual=page.frame_locator('.hip-checkout')
 manual.locator('[data-bank]').first.wait_for();shot(page,'pwa-inline-manual-bank')
 manual.locator('#nextBtn').click();manual.get_by_text('TEST RECEIPT CHECKOUT',exact=True).wait_for();shot(page,'pwa-inline-manual-requisites')
 scenario['overview']={**BASE,'lava':None}
 page.goto('https://reference.invalid/iphone-pwa/checkout?lang=uz');page.locator('[data-plan="1_month"]').wait_for()
 page.locator('#planRegion').select_option('tj');shot(page,'pwa-manual-plans')
 page.locator('#nextBtn').click();shot(page,'pwa-manual-bank')
 page.locator('#nextBtn').click();page.wait_for_timeout(300);shot(page,'pwa-manual-requisites')
 scenario['overview']={**BASE,'lava':None,'checkout_allowed':False,'pending_payment':{'id':71,'plan_type':'1_month'}}
 page.goto('https://reference.invalid/iphone-pwa/checkout?lang=uz');page.wait_for_timeout(400);shot(page,'pwa-manual-pending')
 print(json.dumps({'screens':len(results),'errors':errors},ensure_ascii=False))
 (OUT/'pwa-results.json').write_text(json.dumps({'screens':results,'errors':errors},ensure_ascii=False,indent=2))
 browser.close()
 assert not errors, errors
