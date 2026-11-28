#!/usr/bin/env python3
"""Export the existing PWA checkout panda poses into Android Direct resources.

Run with the repository's Playwright development environment. This is a local
browser render of original product artwork, not a new illustration. No PWA
source file is written; hidden blink overlays retain the initial open eyes.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]; source=(root/'app/static/course_v3_data/iphone-pwa-inline-pro.js').read_text()
a=source.index('  function pandaSvg('); b=source.index('  function setPanda(',a)
function=source[a:b]
out=root/'android/app/src/direct/res/drawable-nodpi'; out.mkdir(exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 page=browser.new_page(viewport={'width':118,'height':122},device_scale_factor=3)
 page.set_content('<style>html,body{margin:0;background:transparent}svg{display:block;width:118px;height:122px}.hip-pd-blink{transform:scaleY(0);transform-origin:center;transform-box:fill-box}</style><div id="art"></div>')
 for pose in ['pro','read','celebrate','gift']:
  svg=page.evaluate('pose=>{'+function+';return pandaSvg(pose)}',pose)
  page.locator('#art').evaluate('(el,svg)=>el.innerHTML=svg',svg)
  page.locator('#art').screenshot(path=str(out/f'checkout_panda_{pose}.png'),omit_background=True)
 browser.close()
