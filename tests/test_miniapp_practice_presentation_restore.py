"""Presentation-only regression checks for Mini App practice loading and limit overlays.

Limit enforcement, payment and trial eligibility must remain server-driven.
"""

import json
from pathlib import Path
import subprocess
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / "app" / "static"
SCENE = (ROOT / "assets/characters/hsk-scene-background.css").read_text(encoding="utf-8")
PREPARING = (ROOT / "assets/characters/hsk-study-preparing.js").read_text(encoding="utf-8")
ADS = (ROOT / "course_v3_data/ads.js").read_text(encoding="utf-8")

PAGES = (
    "course-v3.html",
    "course_v3_memorize.html",
    "course_v3_mistakes.html",
    "course_v3_onboarding.html",
    "course_v3_pronunciation.html",
    "course_v3_recognition.html",
    "course_v3_test.html",
    "course_v3_voice.html",
)


class MiniAppPracticePresentationTests(unittest.TestCase):
    def test_restore_original_dark_limit_promo_not_flat_white_paywall(self):
        self.assertIn(".caa-ov{position:fixed;inset:0;z-index:9000;background:#15120f", ADS)
        self.assertIn(".caa-ov.limit .caa-promo{height:auto;min-height:210px}", ADS)
        self.assertIn(".caa-ov.caa-done .caa-promo{display:flex}", ADS)
        self.assertIn("startLimitSlides(feature);", ADS)
        self.assertNotIn(".caa-ov.limit{background:var(--hsk-paper)", ADS)
        self.assertNotIn(".caa-ov.limit .caa-promo{display:none!important}", ADS)

    def test_limit_sheet_keeps_server_authority_and_pro_only_controls(self):
        self.assertIn('fetch("/api/v3/limits/status"', ADS)
        self.assertIn("function showLimitPromo(opts)", ADS)
        body = ADS.split("function showLimitPromo(opts){", 1)[1].split(
            "/* ============================================================", 1)[0]
        self.assertIn("els.limitPay.onclick=function()", body)
        self.assertIn("els.limitClose.onclick=function()", body)
        self.assertNotIn("trialStatus(", body)
        self.assertNotIn("trialStart(", body)
        self.assertNotIn("opts.onTrial", body)

    def test_actual_ad_module_limit_sheet_callbacks_and_signed_server_copy(self):
        """Execute the real module with local DOM/fetch doubles, no network."""
        script = r'''
const vm=require("vm"),input=JSON.parse(require("fs").readFileSync(0,"utf8"));
(async()=>{
 const results=[];
 for(const locale of ["uz","ru","tj"]){
  const nodes=new Map(),requests=[],timers=[];let subscribed=0,back=0;
  const document={activeElement:null,addEventListener(){}};
  class Element{
   constructor(){this.attributes={};this.style={};this.isConnected=true;this.hidden=false;
    const classes=new Set();this.classList={add:(...v)=>v.forEach(x=>classes.add(x)),
     remove:(...v)=>v.forEach(x=>classes.delete(x)),contains:x=>classes.has(x)};}
   appendChild(){} addEventListener(){} pause(){} load(){}
   setAttribute(k,v){this.attributes[k]=v;} removeAttribute(k){delete this.attributes[k];}
   querySelector(selector){if(!nodes.has(selector))nodes.set(selector,new Element());return nodes.get(selector);}
   focus(){document.activeElement=this;} getClientRects(){return [{}];}
  }
  document.createElement=()=>new Element();document.head=new Element();document.body=new Element();
  const window={},context={window,document,console,
   setInterval:(callback,delay)=>{timers.push({callback,delay});return timers.length;},clearInterval(){},clearTimeout(){},
   fetch:(url,options)=>{requests.push({url,...options});return Promise.resolve({ok:true,
    json:()=>Promise.resolve({ok:true,limit_text:"Server verified "+locale})});}};
  vm.runInNewContext(input.bundle,context);vm.runInNewContext(input.ads,context);
  const ads=window.CourseAds;
  ads.config({lang:locale,initData:"synthetic-test-signature",onSubscribe(){
   if(nodes.get(".caa-ls-pay").onclick!==null)throw new Error("subscribe before closing");subscribed++;}});
  ads.showLimitPromo({feature:"recognition",onTrial(){throw new Error("unexpected trial");}});
  await new Promise(resolve=>setImmediate(resolve));
  const pay=nodes.get(".caa-ls-pay"),close=nodes.get(".caa-ls-close");
  const reason=nodes.get(".caa-ls-why-text").textContent;
  const focused=document.activeElement===pay;
  pay.onclick();
  ads.showLimitPromo({feature:"recognition",reason:"Explicit denied reason",onBack(){back++;}});
  const explicit=nodes.get(".caa-ls-why-text").textContent;
  close.onclick();
  results.push({locale,requests,reason,explicit,focused,subscribed,back,
   slideTimers:timers.map(timer=>timer.delay),primaryLabel:nodes.get(".caa-ls-pay-text").textContent});
 }
 process.stdout.write(JSON.stringify(results));
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
        completed = subprocess.run(
            ["node", "-e", script], input=json.dumps({
                "ads": ADS,
                "bundle": (ROOT / "course_v3_data/hsk-miniapp-i18n.js").read_text(encoding="utf-8"),
            }), capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for result in json.loads(completed.stdout):
            with self.subTest(locale=result["locale"]):
                self.assertEqual(result["reason"], "Server verified " + result["locale"])
                self.assertEqual(result["explicit"], "Explicit denied reason")
                self.assertTrue(result["focused"])
                self.assertEqual((result["subscribed"], result["back"]), (1, 1))
                self.assertEqual(result["slideTimers"], [4500, 4500])
                course_catalog = json.loads((REPO_ROOT / "localization" / "ui" /
                                             result["locale"] / "course.json").read_text(encoding="utf-8"))
                self.assertEqual(result["primaryLabel"], course_catalog["messages"]["subscribe"])
                self.assertEqual(len(result["requests"]), 1)
                request = result["requests"][0]
                self.assertEqual(request["url"], "/api/v3/limits/status")
                self.assertEqual(request["method"], "POST")
                self.assertEqual(request["headers"]["X-Telegram-Init-Data"], "synthetic-test-signature")
                self.assertEqual(json.loads(request["body"]), {"feature": "recognition"})

    def test_preparing_panda_stays_compact_with_separate_copy(self):
        self.assertIn("width:110px;", SCENE)
        self.assertIn("height:121px;", SCENE)
        self.assertIn("max-width:30vw;", SCENE)
        self.assertIn(".hsk-study-preparing b{", SCENE)
        self.assertIn(".hsk-study-preparing small{", SCENE)
        self.assertIn('width:110px;height:121px;max-width:30vw', PREPARING)
        self.assertIn('<b style="display:block;', PREPARING)
        self.assertIn('<small style="display:block;', PREPARING)
        self.assertIn("HSKStudyPreparing={render:render}", PREPARING)

    def test_all_miniapp_pages_refresh_scene_asset(self):
        for page in PAGES:
            with self.subTest(page=page):
                html = (ROOT / page).read_text(encoding="utf-8")
                self.assertIn("hsk-scene-background.css?v=20261009-preparing-compact-1", html)
                self.assertNotIn("hsk-scene-background.css?v=20261008-scene-1", html)

    def test_practice_pages_refresh_loading_and_limit_assets(self):
        for page in PAGES:
            html = (ROOT / page).read_text(encoding="utf-8")
            if "hsk-study-preparing.js?" in html:
                with self.subTest(page=page, resource="preparing"):
                    self.assertIn("hsk-study-preparing.js?v=20261009-compact-1", html)
            if "course_v3_data/ads.js?" in html:
                with self.subTest(page=page, resource="ads"):
                    from scripts.i18n_baseline_guard import git_blob_sha1
                    digest = git_blob_sha1((ROOT / 'course_v3_data/ads.js').read_bytes())[:12]
                    self.assertRegex(html, r'course_v3_data/ads\.js\?v=\d{8}-' + digest)


if __name__ == "__main__":
    unittest.main()
