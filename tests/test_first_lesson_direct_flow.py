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
""" + BODY + r"""
  show:screen => events.push('show:'+screen)
};
App.showFirstLessonNext(2);
const title = $('#lu-stage').innerHTML;
const button = $('#lu-cta').textContent;
const action = $('#lu-cta').onclick;
App.startFirstLessonNext();
App.startFirstLessonNext();
process.stdout.write(JSON.stringify({title,button,action,events}));
""";
        result = subprocess.run(
            ["node", "-e", script.replace("BODY", body)],
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
        self.assertIn('opts.activationVariant||activationVariant()', course)
        self.assertIn("reserveLessonStart(l)", course)
        self.assertIn('if(firstVerifiedLesson&&next&&next.status==="current"&&!isPremiumLocked(next))', course)

    def test_android_first_lesson_gate_and_fresh_next_access(self):
        android = (ROOT / "android/app/src/main/java/com/pomp/hskai/MainActivity.kt").read_text(encoding="utf-8")
        screen = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonScreen.kt").read_text(encoding="utf-8")
        celebration = (ROOT / "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonCompletionCelebration.kt").read_text(encoding="utf-8")
        self.assertIn("onboardingFirstLessonFinished", android)
        self.assertIn('launchLevel.startsWith("nhsk") && map.hsk30?.access?.allowed != true', android)
        self.assertIn("app.courseRepository.courseMap()", android)
        self.assertIn("it.order == launch.lesson.order + 1", android)
        self.assertIn("next.access == LessonAccess.Open", android)
        self.assertIn("!outcome.gamification.duplicate && onStartNext != null", screen)
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
