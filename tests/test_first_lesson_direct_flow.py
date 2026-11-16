"""First-lesson direct-flow regressions for the existing PWA and Android hosts.

The Node check executes the actual course App handlers against a small DOM stub.
Android source checks are structural; emulator acceptance remains separate.
"""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FirstLessonDirectFlowTests(unittest.TestCase):
    def test_pwa_next_button_invokes_existing_lesson_start_once(self):
        source = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        beginning = "  showFirstLessonNext:function(nextOrder){"
        ending = "  showLevelUp:function(type,data,extra){"
        self.assertEqual(source.count(beginning), 1)
        body = beginning + source.split(beginning, 1)[1].split(ending, 1)[0]
        script = r"""
const events = [];
const nodes = {};
function $(selector) {
  return nodes[selector] ||= {
    classList: {flags:new Set(),add(...ks){for(const k of ks){this.flags.add(k);events.push('add:'+k)}},remove(...ks){for(const k of ks){this.flags.delete(k);events.push('remove:'+k)}},contains(k){return this.flags.has(k)}}, 
    setAttribute(k,v){this[k]=v},disabled:false,innerHTML:'',textContent:''
  };
}
const window = {_pendingPwaLessonFeedback:{lessonId:1},_pendingLessonEndAd:1};
const MAP = {level:'hsk1'};
let scope = 'account-A';
const localUserScope = () => scope;
const document = {querySelector(){return {classList:{add(){}}}}};
const pandaChar = () => '<span>Panda</span>';
const courseMessage = (key, fallback) => ({'firstLessonNext.title':'NEXT TITLE',
  'firstLessonNext.start':'START 🔥'}[key] || fallback);
const esc = s => s;
const cancelLessonPron = () => {};
const stopTourAudio = () => {};
const edgeGlow = () => {};
const renderAll = () => {};
const allLessons = () => [{n:1},{n:2}];
const startLesson = idx => events.push('lesson:'+idx);
const setTimeout = fn => fn();
let pendingRankUp = null;
const App = {
""" + body + r"""
  show:screen => events.push('show:'+screen),
  closeLevelUp: () => events.push('dismiss:outside')
};
App.showFirstLessonNext(2);
const preserved = {feedback:window._pendingPwaLessonFeedback.lessonId,ad:window._pendingLessonEndAd};
const title = $('#lu-stage').innerHTML;
const button = $('#lu-cta').textContent;
const action = $('#lu-cta').onclick;
App.startFirstLessonNext();
App.startFirstLessonNext();
App.showFirstLessonNext(2);
MAP.level = 'nhsk1';
App.startFirstLessonNext(); // no stale cross-track auto launch
MAP.level = 'hsk1';
App.showFirstLessonNext(2);
scope = 'account-B';
App.startFirstLessonNext(); // no stale cross-account auto launch
scope = 'account-A'; MAP.level = 'hsk1';
App.showFirstLessonNext(2);
const overlay = $('#levelup');
overlay.onclick({target:{closest(){return {tag:'central-card'}}}}); // inside must stay
const insideDidNotClose = !events.includes('dismiss:outside');
overlay.onclick({target:{closest(){return null}}}); // outside closes
const outsideClosed = events.includes('dismiss:outside');
process.stdout.write(JSON.stringify({title,button,action,events,preserved,insideDidNotClose,outsideClosed}));
""";
        result = subprocess.run(
            ["node", "-e", script],
            text=True, capture_output=True, check=True,
        )
        values = json.loads(result.stdout)
        self.assertIn("NEXT TITLE", values["title"])
        self.assertEqual(values["preserved"], {"feedback": 1, "ad": 1})
        self.assertEqual(values["button"], "START 🔥")
        self.assertEqual(values["action"], "App.startFirstLessonNext()")
        self.assertEqual(values["events"].count("lesson:1"), 1)
        self.assertTrue(values["insideDidNotClose"])
        self.assertTrue(values["outsideClosed"])
        self.assertNotIn("show:rating", values["events"])

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
        self.assertIn('localUserScope()!==window._firstLessonNextScope', course)
        self.assertIn('Number(d.completed_lessons_count)===1', course)
        self.assertIn('if(PWA_COURSE_HOST&&firstVerifiedLesson&&next&&next.status==="current"&&!isPremiumLocked(next))', course)

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

    def test_android_first_lesson_gate_and_fresh_next_access(self):
        android = (ROOT / "android/app/src/main/java/com/pomp/hskai/MainActivity.kt").read_text(encoding="utf-8")
        screen = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonScreen.kt").read_text(encoding="utf-8")
        celebration = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonCompletionCelebration.kt").read_text(encoding="utf-8")
        self.assertIn("onboardingFirstLessonFinished", android)
        self.assertIn('launchLevel.startsWith("nhsk") && map.hsk30?.access?.allowed != true', android)
        self.assertIn("app.courseRepository.courseMap()", android)
        self.assertIn("openLesson?.attemptKey != expectedAttempt", android)
        self.assertIn("fresh?.level == expectedLevel", android)
        self.assertIn("it.order == launch.lesson.order + 1", android)
        self.assertIn("next.access == LessonAccess.Open", android)
        self.assertIn("!outcome.gamification.duplicate && onStartNext != null", screen)
        course = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertIn('!(d.gamification&&d.gamification.duplicate)', course)
        self.assertIn("next.status == com.pomp.hskai.domain.model.LessonStatus.CURRENT", android)
        self.assertIn("it.status == com.pomp.hskai.domain.model.LessonStatus.CURRENT", android)
        self.assertIn("FirstLessonNextScreen(onStartNext = onStartNext, onExit = onExit)", screen)
        self.assertIn("hsk_course_first_lesson_next_title", celebration)
        self.assertIn("hsk_course_first_lesson_next_start", celebration)
        first_screen = celebration.split("internal fun FirstLessonNextScreen(", 1)[1].split("private enum class CelebrationScene", 1)[0]
        self.assertNotIn("SecondaryAction(", first_screen)
        self.assertIn("clickable(", first_screen)
        self.assertIn("onClick = { if (!starting) onExit() }", first_screen)

    def test_translations_are_shared_and_generated(self):
        for locale, suffix in (("uz", ""), ("ru", "-ru"), ("tj", "-tg")):
            source = json.loads((ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8"))
            messages = source["messages"]
            self.assertEqual(len(messages), 1109)
            self.assertTrue(messages["firstLessonNext.title"].strip())
            self.assertTrue(messages["firstLessonNext.start"].endswith("🔥"))
            generated = (ROOT / f"android/app/src/main/res/values{suffix}/hsk_course_i18n.xml").read_text(encoding="utf-8")
            self.assertIn('name="hsk_course_first_lesson_next_title"', generated)
            self.assertIn('name="hsk_course_first_lesson_next_start"', generated)


if __name__ == "__main__":
    unittest.main()
