"""P0 Mini App lesson loader: prefetch cannot become entitlement consumption."""
import json
from pathlib import Path
import shutil
import unittest

from scripts.i18n_miniapp_lesson_fetch_audit import (
    PAGE, REGISTRY, ROOT, audit, audit_source, extract_calls,
)


class MiniAppLessonFetchIntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / PAGE).read_text(encoding="utf-8")
        cls.registry = json.loads((ROOT / REGISTRY).read_text(encoding="utf-8"))

    def test_remaining_direct_reads_are_classified_and_special_intents_use_their_apis(self):
        report = audit(ROOT)
        self.assertEqual(report["status"], "PURPOSE_SPECIFIC_API_CALLS_CLASSIFIED_REVIEW_REQUIRED")
        self.assertEqual(report["classified_direct_calls"], 3)
        self.assertEqual(report["regression_failures"], [])
        expected = [
            "audio_preload_before_continue",
            "background_nearby_prefetch",
            "interactive_lesson_after_reservation",
        ]
        self.assertEqual([row["intent"] for row in report["calls"]], expected)
        self.assertTrue(all(row["cost_sensitive"] for row in report["calls"]))
        self.assertEqual(
            [row["line"] for row in report["calls"]],
            [2203, 3008, 4091],
        )
        self.assertIn('fetch("/api/v3/lesson/sales-preview"', self.source)
        self.assertIn('fetch("/api/v3/lesson/foundation"', self.source)
        self.assertIn('_apiPost("/api/v3/lesson/skip-test"', self.source)

    def test_speculative_reads_are_not_the_reservation_flow(self):
        report = audit(ROOT)
        self.assertEqual(report["calls"][-1]["intent"],
                         "interactive_lesson_after_reservation")
        self.assertTrue(all(row["intent"] != "interactive_lesson_after_reservation"
                            for row in report["calls"][:-1]))
        self.assertIn("reserveLessonStart(l).then(function(){return loadLessonData(lv,l.n)}",
                      self.source)
        self.assertEqual(len(extract_calls(self.source)), 3)

    def test_added_background_fetch_requires_human_review(self):
        altered = self.source + '\nfunction unsafePrefetch(){loadLessonData("hsk3",50)}\n'
        report = audit_source(altered, self.registry)
        self.assertEqual(report["status"], "SOURCE_CONTRACT_REGRESSION")
        self.assertIn("unreviewed_or_missing_direct_read",
                      {row["issue"] for row in report["regression_failures"]})

    def test_interactive_access_order_change_blocks_migration(self):
        old = "reserveLessonStart(l).then(function(){return loadLessonData(lv,l.n)}"
        self.assertIn(old, self.source)
        changed = self.source.replace(old, "loadLessonData(lv,l.n)", 1)
        report = audit_source(changed, self.registry)
        self.assertIn("interactive_lesson_reservation_order_changed",
                      {row["issue"] for row in report["regression_failures"]})

    def test_shifted_source_line_requires_registry_review(self):
        shifted = "// New first line\n" + self.source
        report = audit_source(shifted, self.registry)
        self.assertIn("stale_or_unclassified_read",
                      {row["issue"] for row in report["regression_failures"]})

    def test_memory_resume_keys_need_manual_account_switch_qa(self):
        report = audit(ROOT)
        self.assertEqual(report["cache_scope"], {
            "memory_lesson_key_contains_identity": True,
            "resume_key_contains_identity": True,
            "mastery_key_contains_identity": True,
        })
        self.assertTrue(any(row["issue"] ==
                            "identity_scoped_lesson_cache_requires_runtime_QA"
                            for row in report["review_findings"]))
        self.assertNotIn("correct_index", json.dumps(report))

    @unittest.skipUnless(shutil.which("node"), "Node is needed for JavaScript runtime smoke")
    def test_lesson_data_cache_isolated_when_identity_changes_mid_fetch(self):
        import subprocess

        start = self.source.index("var LESSON_DATA_CACHE={},LESSON_DATA_PROMISES={}")
        end = self.source.index("function idleRun(fn){", start)
        loader = self.source[start:end]
        js = r"""
const vm=require("node:vm");
const assert=require("node:assert/strict");
let scope="account-a", fetchCount=0, finishFirst;
const env={
  localUserScope:()=>scope,
  normalizeLevel:x=>String(x||"hsk1"),
  cloneJson:x=>JSON.parse(JSON.stringify(x)),
  INIT_DATA:"signed-test-initdata",
  lessonDataUrl:(level,n)=>"/api/v3/lesson/content/"+level+"/"+n,
  fetch:(url,options)=>{
    if(url!=="/api/v3/lesson/content/nhsk2/16")throw new Error("unexpected lesson URL: "+url);
    if(!options||options.cache!=="no-store"||options.headers["X-Telegram-Init-Data"]!=="signed-test-initdata")throw new Error("missing private request contract");
    fetchCount++;
    if(fetchCount===1)return new Promise(resolve=>{finishFirst=resolve});
    return Promise.resolve({ok:true,json:()=>Promise.resolve({owner:scope})});
  }
};
vm.runInNewContext(JSON.parse(process.argv[1]),env);
(async()=>{
  const first=env.loadLessonData("nhsk2",16);
  scope="account-b";
  finishFirst({ok:true,json:()=>Promise.resolve({owner:"account-a"})});
  await assert.rejects(first,/lesson_identity_changed/);
  const second=await env.loadLessonData("nhsk2",16);
  assert.equal(second.owner,"account-b");
  assert.equal(fetchCount,2);
  scope="account-a";
  const third=await env.loadLessonData("nhsk2",16);
  assert.equal(third.owner,"account-a");
  assert.equal(fetchCount,3);
})().catch(err=>{console.error(err);process.exitCode=1});
"""
        completed = subprocess.run(
            ["node", "-e", js, json.dumps(loader)],
            text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[-2500:])


if __name__ == "__main__":
    unittest.main()
