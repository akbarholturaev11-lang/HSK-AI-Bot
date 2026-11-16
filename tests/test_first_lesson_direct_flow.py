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
    classList: {add(k){events.push('add:'+k)},remove(k){events.push('remove:'+k)}},
    setAttribute(k,v){this[k]=v},disabled:false,innerHTML:'',textContent:''
  };
}
const window = {};
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
  show:screen => events.push('show:'+screen)
};
App.showFirstLessonNext(2);
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
process.stdout.write(JSON.stringify({title,button,action,events}));
""";
        result = subprocess.run(
            ["node", "-e", script],
            text=True, capture_output=True, check=True,
        )
        values = json.loads(result.stdout)
        self.assertIn("NEXT TITLE", values["title"])
        self.assertEqual(values["button"], "START 🔥")
        self.assertEqual(values["action"], "App.startFirstLessonNext()")
        self.assertEqual(values["events"].count("lesson:1"), 1)
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
