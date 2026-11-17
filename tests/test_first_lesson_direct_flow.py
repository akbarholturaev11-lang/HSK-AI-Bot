"""Onboarding autostart and next-part sheet regressions for web and Android hosts.

The Node check executes the actual course App handlers against a small DOM stub.
Android source checks are structural; emulator acceptance remains separate.
"""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FirstLessonDirectFlowTests(unittest.TestCase):
    def test_next_part_sheet_opens_only_for_current_open_part_and_defers_prompts(self):
        """Execute the actual openNextPartSheet helper against small stubs."""
        source = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        beginning = "function openNextPartSheet(idx,firstCheckpoint,afterClose){"
        ending = "function openLessonSheet(idx){"
        self.assertEqual(source.count(beginning), 1)
        body = beginning + source.split(beginning, 1)[1].split(ending, 1)[0]
        script = r"""
const vm = require('node:vm');
function run(lesson, opts) {
  const events = [];
  const ctx = {
    events, window:{}, MAP:{level:'hsk4'}, SCREEN:'course',
    allLessons:()=>[{n:1,status:'done'}, lesson],
    isPremiumLocked:l=>!!l.locked_premium,
    openLessonSheet:idx=>{events.push('sheet:'+idx);ctx.sheetOn=!opts.noSheet},
    $:()=>({classList:{contains:()=>ctx.sheetOn}}),
    setTimeout:fn=>{if(opts.switchLevel)ctx.MAP.level='nhsk1';fn()},
    sheetOn:false,
  };
  vm.runInNewContext(process.argv[1] + '\nopenNextPartSheet(1,' + !!opts.firstCheckpoint +
    ',function(){events.push("prompts")})', ctx);
  return {events, deferred:typeof ctx.window._afterLessonSheetClose === 'function'};
}
process.stdout.write(JSON.stringify({
  open:run({n:2,status:'current'},{}),
  pro:run({n:2,status:'current',locked_premium:true},{}),
  locked:run({n:2,status:'locked'},{}),
  otherLevel:run({n:2,status:'current'},{switchLevel:true}),
  firstCheckpoint:run({n:4,status:'locked'},{firstCheckpoint:true,noSheet:true}),
}));
""";
        values = json.loads(subprocess.run(
            ["node", "-e", script, body], text=True, capture_output=True, check=True,
        ).stdout)
        # The sheet opens and study setup/feedback wait for its close.
        self.assertEqual(values["open"], {"events": ["sheet:1"], "deferred": True})
        # Pro-locked, not-yet-open or stale-level parts keep the course map.
        for case in ("pro", "locked", "otherLevel"):
            self.assertEqual(values[case], {"events": ["prompts"], "deferred": False})
        # The first HSK1 checkpoint keeps its original sheet/skip-test/paywall path.
        self.assertEqual(values["firstCheckpoint"], {"events": ["sheet:1", "prompts"], "deferred": False})

    def test_last_celebration_screen_continues_to_next_part_sheet(self):
        course = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        # Every saved part whose next part is now current and open.
        self.assertIn('var nextPartSheet=!!(d&&d.ok&&next&&next.status==="current"&&!isPremiumLocked(next));', course)
        self.assertIn('window._pendingCheckpointNextIdx=(firstCheckpointNext||nextPartSheet)?al.indexOf(next):null;', course)
        # Lesson done -> streak -> (Telegram) rank-up -> next part sheet.
        self.assertIn("toNextPart?(showStreak?\"App.showStreakScreen('next')\":\"App.openCheckpointNext()\")", course)
        self.assertIn('var toNext=next==="checkpoint"||next==="next";', course)
        self.assertIn('if(pendingRankUp){App.showRankUp("checkpoint_next");return}', course)
        # The sales bridge stays limited to its original first-checkpoint trigger.
        self.assertIn('if(window._pendingCheckpointSalesBridge&&App.showSalesBridge())return;', course)
        self.assertIn('openNextPartSheet(checkpointNext,firstCheckpointNext,afterReturn)', course)
        # Starting the part drops the deferred map prompts; closing the sheet runs them.
        self.assertIn('window._afterLessonSheetClose=null; // starting a part is not a return to the map', course)
        self.assertIn('if(typeof afterLessonSheet==="function")setTimeout(afterLessonSheet,revealUnlock?260:0);', course)
        self.assertNotIn("showFirstLessonNext", course)
        self.assertNotIn("first-lesson-next", course)

    def test_lesson_sheet_header_is_label_then_one_line_hanzi_and_pinyin(self):
        course = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        head = course.split("function lessonSheetHead(l,chip){", 1)[1].split("\n}", 1)[0]
        self.assertIn("esc(chip)", head)
        self.assertIn('<div class="zh han fit1"', head)
        self.assertIn('<div class="py fit1">', head)
        self.assertNotIn("tr(l.tr)", head)
        self.assertEqual(course.count("App.openSheet(lessonSheetHead(l,chip)"), 2)
        self.assertNotIn("你好 · nǐ hǎo · ", course)
        self.assertIn(".shead .fit1{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;transition:none}", course)
        self.assertEqual(course.count("  fitSheetHeader();\n"), 2)

    def test_pwa_onboarding_autostart_is_pwa_only_and_access_checked(self):
        li = (ROOT / "app/static/course_v3_data/li-onboarding-runtime.js").read_text(encoding="utf-8")
        legacy = (ROOT / "app/static/course_v3_onboarding.html").read_text(encoding="utf-8")
        course = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertIn('if(hostPwa&& !launch.placement&&!launch.review_only)', li)
        self.assertIn('q.set("resume","1");q.set("autostart","1")', li)
        self.assertIn('!hostPwa&&!launch.reconciled&&global.track==="hsk20"', li)
        self.assertIn('query.set("resume","1");query.set("autostart","1")', legacy)
        self.assertIn('if(PWA_ONBOARDING_HOST&&!launch.placement&&!launch.review_only)', legacy)
        self.assertIn('else if(!PWA_ONBOARDING_HOST&&!isHsk30Level(sel)&&!launch.placement)', legacy)
        self.assertIn('opts.activationVariant||activationVariant()', course)
        self.assertIn("reserveLessonStart(l)", course)
        self.assertIn('if(sp.get("onboarded")==="1"&&sp.get("autostart")==="1"&&(idx<0||allLessons()[idx].status!=="current"))', course)

    def test_legacy_pwa_default_requires_hsk30_entitlement(self):
        """An advertised HSK 3.0 option is not a default unlocked lesson."""
        html=(ROOT / "app/static/course_v3_onboarding.html").read_text(encoding="utf-8")
        script=html.split("}else if(!hasSavedTrack&&!userSelectedTrack){",1)[1].split("}else if(track===\"hsk30\"&&!h30Enabled){",1)[0]
        node=r"""
const body=JSON.parse(process.argv[1]);
function choose(host,allowed){
  const f=new Function('PWA_ONBOARDING_HOST','h30Enabled','access',
    'var track,sel;'+body+';return {track,sel};');
  return f(host,true,{feature_enabled:true,allowed});
}
process.stdout.write(JSON.stringify({
  deniedPwa:choose(true,false),allowedPwa:choose(true,true),
  deniedMiniapp:choose(false,false)
}));
"""
        result=subprocess.run(["node","-e",node,json.dumps(script)],capture_output=True,text=True,check=True)
        data=json.loads(result.stdout)
        self.assertEqual(data["deniedPwa"],{"track":"hsk20","sel":"beginner"})
        self.assertEqual(data["allowedPwa"],{"track":"hsk30","sel":"nhsk1"})
        self.assertEqual(data["deniedMiniapp"],{"track":"hsk30","sel":"nhsk1"})

    def test_li_onboarding_handoff_never_fabricates_lesson_or_entitlement(self):
        """Run the actual Li onboarding handler with PWA/Telegram launch variants."""
        text = (ROOT / "app/static/course_v3_data/li-onboarding-runtime.js").read_text(encoding="utf-8")
        beginning, ending = "function toCourse(){", "function showLiveBooks(){"
        self.assertEqual(text.count(beginning), 1)
        function = beginning + text.split(beginning, 1)[1].split(ending, 1)[0]
        script = r"""
const vm = require('node:vm');
const fn = JSON.parse(process.argv[1]);
function open(host, track, launch) {
  const ctx = {
    launch, hostPwa:host, global:{LANG:'uz',track},
    location:{search:'?source=onboarding',href:'',assign(url){this.href=url;}},
    URLSearchParams, pageCourse:()=>host?'/iphone-pwa/course':'/course-v3.html',
    saveProfile(){}, renderError(){ctx.blocked=true}, blocked:false
  };
  vm.runInNewContext(fn+'\ntoCourse()',ctx);
  const link = new URL(ctx.location.href || '/unconfirmed','https://hskai.app');
  return {path:link.pathname,start:link.searchParams.get('autostart'),
    resume:link.searchParams.get('resume'),lesson:link.searchParams.get('lesson'),
    blocked:ctx.blocked};
}
const cases = {
 pwaHsk3:open(true,'hsk30',{ok:true,level:'nhsk1',lesson:1}),
 pwaReconciled:open(true,'hsk20',{ok:true,level:'hsk1',reconciled:true}),
 pwaPlacement:open(true,'hsk20',{ok:true,level:'hsk1',placement:true,lesson:1}),
 denied:open(true,'hsk30',{ok:false}),
 miniHsk2:open(false,'hsk20',{ok:true,level:'hsk1',lesson:1}),
 miniHsk3:open(false,'hsk30',{ok:true,level:'nhsk1',lesson:1})
};
process.stdout.write(JSON.stringify(cases));
"""
        run = subprocess.run(
            ["node", "-e", script, json.dumps(function)], capture_output=True,
            text=True, check=True,
        )
        cases = json.loads(run.stdout)
        self.assertEqual(cases["pwaHsk3"]["start"], "1")
        self.assertEqual(cases["pwaHsk3"]["lesson"], "1")
        self.assertEqual(cases["pwaReconciled"]["start"], "1")
        self.assertIsNone(cases["pwaReconciled"]["lesson"])
        self.assertEqual(cases["pwaReconciled"]["resume"], "1")
        self.assertIsNone(cases["pwaPlacement"]["start"])
        self.assertTrue(cases["denied"]["blocked"])
        self.assertEqual(cases["denied"]["path"], "/unconfirmed")
        self.assertEqual(cases["miniHsk2"]["start"], "1")
        self.assertIsNone(cases["miniHsk3"]["start"])

    def test_legacy_onboarding_keeps_telegram_track_handoff_unchanged(self):
        """Execute the actual existing go() handler for PWA and Telegram cases."""
        html = (ROOT / "app/static/course_v3_onboarding.html").read_text(encoding="utf-8")
        start = "  function go(result){"
        end = "  function fail(reason){"
        self.assertEqual(html.count(start), 1)
        block = start + html.split(start, 1)[1].split(end, 1)[0]
        script = r"""
const vm = require('node:vm');
const goSource = JSON.parse(process.argv[1]);
const base = (host, level, launch) => {
  const ctx = {
    input: launch, moved:false, saveNeedsVerification:false,
    PWA_ONBOARDING_HOST:host, LANG:'uz', sel:level,
    params:new URLSearchParams('campaign=default'),
    location:{href:'',hash:''}, URLSearchParams,
    localStorage:{setItem(){},removeItem(){}},
    isHsk30Level:s=>s.startsWith('nhsk'),
  };
  vm.runInNewContext(goSource + '\ngo(input)', ctx);
  return new URL(ctx.location.href,'https://hskai.app');
};
const eligible={ok:true,level:'nhsk1',lesson:1,tab:'course'};
const oldTrack=base(false,'nhsk1',eligible);
const oldHsk2=base(false,'hsk1',{ok:true,level:'hsk1',lesson:1});
const pwaHsk3=base(true,'nhsk1',eligible);
const pwaReconciled=base(true,'hsk1',{ok:true,level:'hsk1',reconciled:true});
process.stdout.write(JSON.stringify({
  oldTrack:{path:oldTrack.pathname,start:oldTrack.searchParams.get('autostart')},
  oldHsk2:{path:oldHsk2.pathname,start:oldHsk2.searchParams.get('autostart'),lesson:oldHsk2.searchParams.get('lesson')},
  pwaHsk3:{path:pwaHsk3.pathname,start:pwaHsk3.searchParams.get('autostart'),resume:pwaHsk3.searchParams.get('resume')},
  reconciled:{start:pwaReconciled.searchParams.get('autostart'),resume:pwaReconciled.searchParams.get('resume'),lesson:pwaReconciled.searchParams.get('lesson')}
}));
""";
        result = subprocess.run(
            ["node", "-e", script, json.dumps(block)], check=True,
            text=True, capture_output=True,
        )
        data = json.loads(result.stdout)
        self.assertEqual(data["oldTrack"], {"path": "/course-v3.html", "start": None})
        self.assertEqual(data["oldHsk2"], {"path": "/course-v3.html", "start": "1", "lesson": "1"})
        self.assertEqual(data["pwaHsk3"], {"path": "/iphone-pwa/course", "start": "1", "resume": "1"})
        self.assertEqual(data["reconciled"], {"start": "1", "resume": "1", "lesson": None})

    def test_android_onboarding_autostart_and_next_part_sheet(self):
        android = (ROOT / "android/app/src/main/java/com/pomp/hskai/MainActivity.kt").read_text(encoding="utf-8")
        screen = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonScreen.kt").read_text(encoding="utf-8")
        celebration = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonCompletionCelebration.kt").read_text(encoding="utf-8")
        sheet = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/course/NextPartSheet.kt").read_text(encoding="utf-8")
        # Onboarding still opens the verified first lesson; prompts wait for its exit.
        self.assertIn("onboardingFirstLessonFinished", android)
        self.assertIn('launchLevel.startsWith("nhsk") && map.hsk30?.access?.allowed != true', android)
        # The celebration scenes are unchanged: no direct first-lesson card.
        for text in (screen, celebration, android):
            self.assertNotIn("FirstLessonNextScreen", text)
            self.assertNotIn("onStartNext", text)
            self.assertNotIn("hsk_course_first_lesson_next", text)
        # A completed part waits for the ad and the refreshed map, then offers
        # the next part only when the server shows it current and open.
        self.assertIn("if (completed) pendingNextPart = NextPartOffer(currentLevel, finishedOrder)", android)
        self.assertIn("if (adRequest != null || courseState.isRefreshing) return@LaunchedEffect", android)
        self.assertIn("!courseState.isStale && it.level == pending.level", android)
        self.assertIn("it.order == pending.finishedOrder + 1", android)
        self.assertIn("next.status == com.pomp.hskai.domain.model.LessonStatus.CURRENT", android)
        self.assertIn("(next.access == LessonAccess.Open || next.access == LessonAccess.HalfPreview)", android)
        # Lesson feedback follows when the sheet is dismissed or not offered.
        self.assertEqual(android.count('activityFeedback.prepare("lesson", pending.level, pending.finishedOrder)'), 1)
        self.assertEqual(android.count('activityFeedback.prepare("lesson", offer.level, offer.finishedOrder)'), 1)
        self.assertIn("!checkoutVisible && nextPartSheet == null)", android)
        self.assertIn("launchLesson(next)", android.split("NextPartSheet(", 1)[1].split("onDismiss", 1)[0])
        # Same header as the web sheet: label, then one-line hanzi and pinyin.
        self.assertIn("R.string.hsk_course_lesson_flow_lesson_prefix", sheet)
        self.assertIn("R.string.hsk_course_lesson_flow_part_prefix", sheet)
        self.assertIn("maxLines = 1", sheet)
        self.assertIn("softWrap = false", sheet)
        self.assertIn("maxSize = 34.sp", sheet)
        self.assertIn("maxSize = 15.sp", sheet)
        self.assertNotIn("subtitle", sheet)

    def test_no_new_course_copy(self):
        for locale, suffix in (("uz", ""), ("ru", "-ru"), ("tj", "-tg")):
            messages = json.loads((ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8"))["messages"]
            self.assertEqual(len(messages), 1110)
            self.assertNotIn("firstLessonNext.title", messages)
            generated = (ROOT / f"android/app/src/main/res/values{suffix}/hsk_course_i18n.xml").read_text(encoding="utf-8")
            self.assertNotIn("hsk_course_first_lesson_next", generated)
            for name in ("hsk_course_lesson_flow_lesson_prefix", "hsk_course_lesson_flow_part_prefix",
                         "hsk_course_part_sections_w", "hsk_course_stage", "hsk_course_complete_of",
                         "hsk_course_cont"):
                self.assertIn(f'name="{name}"', generated)


if __name__ == "__main__":
    unittest.main()
