"""Real Chromium dictionary list stress test (source-backed, no backend network)."""
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "app/static/hsk-lugat.html").read_text(encoding="utf-8")
BEGIN = SOURCE.index("  /* Render a bounded DOM window")
END = SOURCE.index("  /* ---------- stroke-order writer", BEGIN)
LIST_JS = SOURCE[BEGIN:END]
CSS = re.search(r"<style>([\s\S]*?)</style>", SOURCE).group(1)

def test_dictionary_virtual_scroll_large_word_list_iPhone():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height in ((320,568),(390,844),(430,932)):
            page = browser.new_page(viewport={"width":width,"height":height},
                                    device_scale_factor=2,is_mobile=True,has_touch=True)
            page.set_content(
                '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">'
                '<style>'+CSS+'</style></head><body>'
                '<div id="list" class="list" style="height:460px;flex:none"></div></body></html>'
            )
            script = r"""
              var listEl=document.getElementById('list'),searchEl={value:''},
                countEl={textContent:'',setAttribute(){}},searchClear={classList:{toggle(){}}},
                currentLang='uz',UI={uz:{
                  emptyTitle:'No words',emptySub:'Try again',
                  countResults:n=>n+' results',countAll:n=>n+' words'}};
              function text(m){return m.uz}
              function normPinyin(v){return v.toLowerCase()}
              function escapeHtml(v){return String(v).replaceAll('&','&amp;').replaceAll('<','&lt;')}
              function formatDictionaryLevel(lv){return lv}
              function filterCountLabel(){return 'All'}
              var activeWords=Array.from({length:2400},(_,i)=>({
                id:i,h:i===1377?'学习':'词'+i,p:i===1377?'xuéxí':'ci'+i,
                m:{uz:i===1377?"o'rganmoq":'soz'+i},lv:'HSK1',
                _p:i===1377?'xuexi':'ci'+i,_m:i===1377?"o'rganmoq":'soz'+i
              }));
            """
            page.add_script_tag(content=script+"\n"+LIST_JS+"\nrenderList('');")
            assert page.locator("#list .row").count() <= 90
            assert page.locator("#list .row").first.evaluate(
                "(e) => Math.round(e.getBoundingClientRect().height)"
            ) == 88
            page.locator("#list").evaluate("(e) => e.scrollTop=88*1100")
            page.wait_for_function("document.querySelector('#list [data-idx=\"1100\"]')!==null")
            assert page.locator("#list .row").count() <= 90
            page.locator("#list").evaluate("(e) => e.scrollTop=e.scrollHeight")
            page.wait_for_function("document.querySelector('#list [data-idx=\"2399\"]')!==null")
            assert page.locator("#list .row").count() <= 90
            page.evaluate("searchEl.value='学习';renderList(searchEl.value)")
            assert page.locator("#list .row").count()==1
            assert page.locator("#list [data-idx='1377']").count()==1
            page.evaluate("searchEl.value='xuexi';renderList(searchEl.value)")
            assert page.locator("#list .row").count()==1
            page.evaluate("searchEl.value=\"o'rganmoq\";renderList(searchEl.value)")
            assert page.locator("#list .row").count()==1
            page.evaluate("searchEl.value='zzzzzz';renderList(searchEl.value)")
            assert page.locator("#list .row").count()==0
            assert page.locator("#list .empty").is_visible()
            page.close()
        browser.close()
