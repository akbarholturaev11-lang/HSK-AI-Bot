from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1280,'height':1050});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8766',wait_until='networkidle')
    page.get_by_role('button',name='Namuna matn').click()
    page.get_by_role('button',name='Ovoz yaratish').click()
    page.get_by_text('Ovozingiz tayyor.',exact=True).wait_for(timeout=190000)
    assert page.locator('audio').evaluate('(a)=>a.src.includes("/audio/")')
    with page.expect_download() as info:page.get_by_role('link',name='WAV faylni saqlash').click()
    assert info.value.suggested_filename.endswith('.wav')
    page.screenshot(path=str(BASE/'outputs/desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(BASE/'outputs/mobile.png'),full_page=True)
    assert not errors,errors
    print('Browser generation, audio, download, mobile overflow and JS checks passed.')
    browser.close()
