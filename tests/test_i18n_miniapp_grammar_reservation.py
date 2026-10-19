"""P3 Mini App: reservation-only display patch with no access/grade regression."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from app.services.course_p3_grammar_localization import (
    _source_pinned_drafts, miniapp_reserved_grammar_patch,
)

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "app/static/course-v3.html"
HELPER = ROOT / "app/static/course_v3_data/p3-grammar-reservation.js"
API = ROOT / "app/api/miniapp_entitlements.py"
SOURCE = ROOT / "app/static/course_v3_data/nhsk2/lesson_16.json"


class MiniAppP3ReservationTests(unittest.TestCase):
    def test_source_pinned_reservation_patch_is_display_only(self):
        before = SOURCE.read_bytes()
        _source_pinned_drafts.cache_clear()
        patch = miniapp_reserved_grammar_patch(
            level="nhsk2", lesson_order=16
        )
        self.assertIsNotNone(patch)
        self.assertEqual(patch["lesson_order"], 16)
        self.assertEqual(patch["level"], "nhsk2")
        self.assertEqual(len(patch["source_git_blob_sha1"]), 40)
        self.assertEqual(len(patch["display_translations"]), 12)
        self.assertEqual(SOURCE.read_bytes(), before)
        allowed = ("pointer", "zh", "pinyin", "values")
        paths = set()
        for row in patch["display_translations"]:
            self.assertEqual(set(row), set(allowed))
            self.assertEqual(set(row["values"]), {"uz", "ru", "tj"})
            self.assertTrue(all(row["values"].values()))
            self.assertNotIn(row["pointer"], paths)
            paths.add(row["pointer"])
            self.assertTrue(row["pointer"].startswith(("/grammar/", "/sections/")))
        serialized = json.dumps(patch, ensure_ascii=False)
        for token in ('"correct_index"', '"answer_tokens"', '"requires_pro"',
                      '"options"', '"bank"', '"scoring"', '"is_paid"'):
            self.assertNotIn(token, serialized)

    def test_all_48_miniapp_patches_match_native_display_only(self):
        """Exercise EVERY affected lesson, not just lesson 16.

        Catch runtime adapter drift across repeated contexts, mixed
        _grammar cards, and native/Mini App parity without API tokens.
        """
        from app.services.course_p3_grammar_localization import (
            apply_native_grammar_locales,
        )

        _source_pinned_drafts.cache_clear()
        drafts = _source_pinned_drafts()
        self.assertEqual(len(drafts), 48)
        total_display_maps = 0
        original_maps = 0
        for relative, draft in sorted(drafts.items()):
            number = int(Path(relative).stem.split("_")[-1])
            before = (ROOT / relative).read_bytes()
            original = json.loads(before)
            mini = miniapp_reserved_grammar_patch(
                level="nhsk2", lesson_order=number,
            )
            self.assertIsNotNone(mini, relative)
            self.assertEqual(mini["source_git_blob_sha1"],
                             draft["source_git_blob_sha1"])
            native = apply_native_grammar_locales(
                original, level="nhsk2", lesson_order=number,
            )
            self.assertIsNot(native, original, relative)
            self.assertEqual(mini["lesson_order"], number)
            locations = set()
            for patch in mini["display_translations"]:
                pointer = patch["pointer"]
                self.assertNotIn(pointer, locations)
                locations.add(pointer)
                keys = pointer.split("/")[1:-1]
                src_example, translated_example = original, native
                for segment in keys:
                    k = int(segment) if isinstance(src_example, list) else segment
                    src_example = src_example[k]
                    translated_example = translated_example[k]
                self.assertEqual(src_example["zh"], patch["zh"])
                self.assertEqual(src_example.get("pinyin", ""), patch["pinyin"])
                self.assertEqual(src_example["translation"],
                                 {"uz": "", "ru": "", "tj": ""})
                self.assertEqual(translated_example["translation"],
                                 patch["values"])
                self.assertEqual(set(patch["values"]), {"uz", "ru", "tj"})
                self.assertTrue(all(patch["values"].values()))
            original_maps += len(draft["translations"])
            total_display_maps += len(locations)
            self.assertEqual((ROOT / relative).read_bytes(), before)
        self.assertEqual(original_maps, 272)
        self.assertEqual(total_display_maps, 408)
        self.assertEqual(total_display_maps * 3, 1224)

    def test_wrong_level_source_revision_and_no_gap_return_none(self):
        self.assertIsNone(miniapp_reserved_grammar_patch(level="nhsk1", lesson_order=16))
        self.assertIsNone(miniapp_reserved_grammar_patch(level="nhsk2", lesson_order=1))
        self.assertIsNone(miniapp_reserved_grammar_patch(level="nhsk2", lesson_order=0))
        with __import__("tempfile").TemporaryDirectory() as tmp:
            self.assertIsNone(miniapp_reserved_grammar_patch(
                level="nhsk2", lesson_order=16, course_data_root=Path(tmp),
            ))

    def test_existing_verified_access_and_commit_precede_patch(self):
        api = API.read_text(encoding="utf-8")
        start = api.index('    @router.post("/api/v3/lesson/start")')
        stop = api.index('    @router.post("/api/v3/limits/status")', start)
        block = api[start:stop]
        self.assertLess(block.index("extract_verified_webapp_user_id"),
                        block.index("miniapp_reserved_grammar_patch("))
        review = block[block.index('if payload.get("review_only") is True:'):
                       block.index('if order < 1 or order > total_parts(level)', 
                                   block.index('if payload.get("review_only") is True:'))]
        self.assertLess(review.index("order > completed"),
                        review.index("miniapp_reserved_grammar_patch("))
        self.assertNotIn("consume=True", review)
        # The current lesson, by contrast, MUST consume its existing gate.
        reserved = block[block.index("result = await LessonAccessService(session).status("):]
        self.assertLess(reserved.index("consume=True"),
                        reserved.index("miniapp_reserved_grammar_patch("))
        self.assertLess(block.index("await session.commit()"),
                        block.index('if result["allowed"] and level == "nhsk2":'))
        self.assertIn('headers={"Cache-Control": "no-store"}', block)
        self.assertIn('status_code=200 if result["allowed"] else 403', block)
        self.assertNotIn("@router.get(", block)

    def test_miniapp_does_not_change_prefetch_or_cached_json_paths(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn("p3-grammar-reservation.js?v=20261019-p3-2", html)
        self.assertEqual(len(html.split("\n")), 8712)
        self.assertIn("fetch(lessonDataUrl(lv,n),", html)
        self.assertIn("LESSON_DATA_CACHE[key]=d;", html)
        self.assertIn(
            "reserveLessonStart(l).then(function(){return loadLessonData(lv,l.n)})",
            html,
        )
        start = html.index("function reserveLessonStart(l){")
        end = html.index("function handleLessonStartDenied(", start)
        fragment = html[start:end]
        self.assertIn('P3_RESERVED_GRAMMAR=null;', fragment)
        self.assertIn('return reserveCompletedP3Grammar(l);', fragment)
        self.assertIn('P3_RESERVED_GRAMMAR=d.p3_grammar||null;', fragment)
        self.assertIn('if(!r.ok||!d.ok||d.allowed===false)', fragment)
        self.assertLess(fragment.index('if(!r.ok||!d.ok||d.allowed===false)'),
                        fragment.index('P3_RESERVED_GRAMMAR=d.p3_grammar||null;'))
        self.assertIn("d=applyReservedP3Grammar(d,lv,l.n);", html)
        self.assertLess(html.index("d=applyReservedP3Grammar(d,lv,l.n);"),
                        html.index("Flow.queue=buildQueue(d);"))

    @unittest.skipUnless(shutil.which("node"), "Node is needed for JavaScript runtime smoke")
    def test_js_atomic_patch_applies_only_to_matching_zh_and_preserves_cache(self):
        helper = HELPER.read_text(encoding="utf-8")
        js = """
const assert=require("node:assert/strict");
const vm=require("node:vm");
const env={normalizeLevel:x=>x,cloneJson:x=>JSON.parse(JSON.stringify(x))};
vm.runInNewContext(JSON.parse(process.argv[1]),env);
const blank={uz:"",ru:"",tj:""};
const example={zh:"她去过中国。",pinyin:"",translation:blank};
const original={level:"nhsk2",lesson_id:16,grammar:[{examples:[example]}],
  sections:[{cards:[{type:"_grammar",g:{examples:[example]}}]}]};
const untouched=JSON.stringify(original);
const vals={uz:"U Xitoyda bo‘lgan.",ru:"Она бывала в Китае.",
  tj:"Ӯ пештар ба Чин рафтааст."};
const patch={version:1,level:"nhsk2",lesson_order:16,
  source_git_blob_sha1:"a".repeat(40),display_translations:[
    {pointer:"/grammar/0/examples/0/translation",
     zh:"她去过中国。",pinyin:"",values:vals},
    {pointer:"/sections/0/cards/0/g/examples/0/translation",
     zh:"她去过中国。",pinyin:"",values:vals}
  ]};
env.P3_RESERVED_GRAMMAR=patch;
const result=env.applyReservedP3Grammar(original,"nhsk2",16);
assert.equal(result.grammar[0].examples[0].translation.ru,vals.ru);
assert.equal(result.sections[0].cards[0].g.examples[0].translation.tj,vals.tj);
assert.equal(JSON.stringify(original),untouched);
assert.equal(env.P3_RESERVED_GRAMMAR,null);
// Atomic fail-closed: a changed mirror Chinese prevents all mutations.
const invalid=JSON.parse(JSON.stringify(patch));
invalid.display_translations[1].zh="篡改";
env.P3_RESERVED_GRAMMAR=invalid;
const fallback=env.applyReservedP3Grammar(original,"nhsk2",16);
assert.equal(JSON.stringify(fallback),untouched);
assert.equal(env.P3_RESERVED_GRAMMAR,null);
// Never patch a different user/level/lesson after a race or retry.
env.P3_RESERVED_GRAMMAR=patch;
assert.equal(env.applyReservedP3Grammar(original,"nhsk2",17),original);
assert.equal(env.P3_RESERVED_GRAMMAR,null);
// A malformed path cannot touch arbitrary protected fields.
const forged=JSON.parse(JSON.stringify(patch));
forged.display_translations[0].pointer="/sections/0/cards/0/correct_index";
env.P3_RESERVED_GRAMMAR=forged;
assert.equal(env.applyReservedP3Grammar(original,"nhsk2",16),original);
assert.equal(JSON.stringify(original),untouched);
"""
        completed = subprocess.run(
            ["node", "-e", js, json.dumps(helper)],
            text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[-2500:])


    @unittest.skipUnless(shutil.which("node"), "Node is needed for JavaScript runtime smoke")
    def test_completed_review_fetches_once_with_safe_fallback(self):
        helper = HELPER.read_text(encoding="utf-8")
        js = """
const vm=require("node:vm");
const assert=require("node:assert/strict");
const calls=[];
const env={_apiPost:(url,data)=>{
  calls.push({url,data});
  return Promise.resolve({ok:true,json:()=>Promise.resolve({
    ok:true,allowed:true,p3_grammar:{version:1,level:"nhsk2",lesson_order:16}
  })});
}};
vm.runInNewContext(JSON.parse(process.argv[1]),env);
(async()=>{
  const granted=await env.reserveCompletedP3Grammar({n:16});
  assert.equal(granted.allowed,true);
  assert.equal(calls.length,1);
  assert.equal(calls[0].url,"/api/v3/lesson/start");
  assert.equal(calls[0].data.review_only,true);
  assert.equal(calls[0].data.lesson_id,16);
  assert.equal(env.P3_RESERVED_GRAMMAR.version,1);
  env.P3_RESERVED_GRAMMAR=null;
  env._apiPost=(url,data)=>Promise.resolve({
    ok:false,json:()=>Promise.resolve({ok:false,error:"course_lesson_not_unlocked"})
  });
  env._apiPost=()=>Promise.resolve({
    ok:false,status:403,json:()=>Promise.resolve({
      ok:false,allowed:false,error:"course_lesson_not_unlocked"
    })
  });
  await assert.rejects(env.reserveCompletedP3Grammar({n:17}),err=>
    err.lessonAccessDenied===true&&err.status===403&&
    err.data.error==="course_lesson_not_unlocked");
  assert.equal(env.P3_RESERVED_GRAMMAR,null);
  env._apiPost=()=>Promise.resolve({
    ok:false,status:401,json:()=>Promise.resolve({ok:false,error:"unauthorized"})
  });
  await assert.rejects(env.reserveCompletedP3Grammar({n:16}),err=>
    err.lessonAccessDenied===true&&err.status===401);
  assert.equal(env.P3_RESERVED_GRAMMAR,null);
  env._apiPost=()=>Promise.resolve({
    ok:true,status:200,json:()=>Promise.resolve({ok:true,allowed:false})
  });
  await assert.rejects(env.reserveCompletedP3Grammar({n:16}),err=>
    err.lessonAccessDenied===true);
  assert.equal(env.P3_RESERVED_GRAMMAR,null);
  env._apiPost=()=>Promise.reject(new Error("offline"));
  const offline=await env.reserveCompletedP3Grammar({n:16});
  assert.equal(offline.allowed,true);
  assert.equal(env.P3_RESERVED_GRAMMAR,null);
})().catch(err=>{console.error(err);process.exitCode=1});
"""
        result = subprocess.run(
            ["node", "-e", js, json.dumps(helper)],
            text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2500:])


if __name__ == "__main__":
    unittest.main()
