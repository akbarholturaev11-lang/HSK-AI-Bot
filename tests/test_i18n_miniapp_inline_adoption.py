"""Remaining inline/helper UI uses local data without changing legacy payloads."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from scripts.i18n_build_miniapp_catalogs import ROOT, TARGET, generate, read_sources
from scripts.i18n_miniapp_catalog_audit import extract_literal


def fixtures():
    proof = json.loads((ROOT / "localization/review/miniapp_inline_map_migration.json").read_text())
    rows = []
    for row in proof["maps"]:
        source = (ROOT / row["file"]).read_text(encoding="utf-8")
        marker = "(" + json.dumps(row["id"]) + ","
        start = source.index(marker) + len(marker)
        literal, _ = extract_literal("var HSK_TMP=" + source[start:], "HSK_TMP")
        rows.append({**row, "literal": literal})
    return rows


def run_node(bundle, rows, suffix=""):
    script = r'''
const vm=require("vm"),arg=JSON.parse(require("fs").readFileSync(0,"utf8"));
const window={},context={window};vm.runInNewContext(arg.bundle,context);
const rows=arg.rows.map(row=>{const base=vm.runInNewContext("("+row.literal+")",Object.create(null));
  return {id:row.id,base,rendered:window.HSKAILocaleMap(row.id,base)}});
const result={rows};
''' + suffix + r'''
process.stdout.write(JSON.stringify(result));
'''
    result = subprocess.run(["node", "-e", script],
                            input=json.dumps({"bundle": bundle, "rows": rows}),
                            capture_output=True, text=True, timeout=30, check=True)
    return json.loads(result.stdout)


class MiniappInlineCatalogTests(unittest.TestCase):
    def test_76_migrated_ui_maps_preserve_every_value_and_order(self):
        rows = fixtures()
        self.assertEqual(len(rows), 76)
        output = run_node((ROOT / TARGET).read_text(), rows)
        for row, result in zip(rows, output["rows"]):
            with self.subTest(key=row["id"]):
                self.assertEqual(result["base"], result["rendered"])
                for locale, expected in row["locale_value_sha256"].items():
                    actual = json.dumps(result["rendered"][locale], ensure_ascii=False, separators=(",", ":"))
                    self.assertEqual(hashlib.sha256(actual.encode()).hexdigest(), expected)

    def test_canonical_edit_reaches_ui_with_no_shared_bundle_or_network(self):
        catalogs = read_sources()
        key = next(key for key, text in catalogs["uz"]["messages"].items() if "{" not in text)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for locale in ("uz", "ru", "tj"):
                dest = root / f"localization/ui/{locale}"
                dest.mkdir(parents=True)
                for namespace in ("miniapp", "common", "course"):
                    shutil.copyfile(ROOT / f"localization/ui/{locale}/{namespace}.json", dest / f"{namespace}.json")
            source = root / "localization/ui/uz/miniapp.json"
            data = json.loads(source.read_text())
            data["messages"][key] = "QA canonical UI"
            source.write_text(json.dumps(data))
            generate(root, check=False)
            bundle = (root / TARGET).read_text()
            output = run_node(bundle, fixtures())
            self.assertIn("QA canonical UI", json.dumps(output, ensure_ascii=False))
            self.assertNotIn("fetch(", bundle)
            self.assertEqual(generate(root, check=True), [])

    def test_missing_unknown_or_malformed_values_keep_exact_fallback(self):
        rows = fixtures()[:1]
        suffix = r'''
const base=rows[0].base;
result.unknown=window.HSKAILocaleMap("missing",base);
Object.keys(window.HSKAI_MINIAPP_I18N.uz).forEach(key=>window.HSKAI_MINIAPP_I18N.uz[key]=42);
result.invalid=window.HSKAILocaleMap(rows[0].id,base);
result.absent=vm.runInNewContext('(window.HSKAILocaleMap||function(_,fallback){return fallback})("missing",'+JSON.stringify(base)+')',{window:{}});
'''
        output = run_node((ROOT / TARGET).read_text(), rows, suffix)
        for name in ("unknown", "invalid", "absent"):
            self.assertEqual(output[name], output["rows"][0]["base"])

    def test_new_local_bundle_is_current_and_loaded_before_helper_scripts(self):
        self.assertEqual(generate(check=True), [])
        for page in sorted({row["file"] for row in fixtures() if row["file"].endswith(".html")}):
            source = (ROOT / page).read_text()
            self.assertEqual(source.count("hsk-miniapp-i18n.js?v="), 1)
        source = (ROOT / "app/main.py").read_text()
        self.assertIn('"hsk-miniapp-i18n.js": "application/javascript"', source)
        self.assertEqual(len((ROOT / "app/static/course-v3.html").read_text().splitlines()), 9121)

    def test_graded_placement_blocks_remain_byte_identical(self):
        proof = json.loads((ROOT / "localization/review/miniapp_inline_map_migration.json").read_text())
        for guard in proof["protected_placement_blocks"]:
            source = (ROOT / guard["source"]).read_text()
            block = "var QP=[" + source.split("var QP=[", 1)[1].split("];", 1)[0] + "];"
            self.assertEqual(hashlib.sha256(block.encode()).hexdigest(), guard["sha256"])


    def test_dynamic_templates_keep_original_rendering_for_all_branches(self):
        source = (ROOT / "app/static/course-v3.html").read_text()
        originals = {'soon': '  var copy={\n    uz:{title:label+" · Tez orada",body:"Bu HSK 3.0 darajasi hali ochilmagan. Hozir mavjud darajani tugatgan progress saqlanadi."},\n    ru:{title:label+" · Скоро",body:"Этот уровень HSK 3.0 ещё не открыт. Прогресс на текущем доступном уровне сохранён."},\n    tj:{title:label+" · Ба зудӣ",body:"Ин сатҳи HSK 3.0 ҳоло кушода нашудааст. Пешрафти сатҳи дастраси ҳозира нигоҳ дошта мешавад."}\n  }[LANG];\n', 'level': '    var levelCopy={\n      ru:{h:curLabel+" пройден!",p:pendingLabel?pendingLabel+" — скоро.":(nextLabel?"Поздравляем! Открыт "+nextLabel+".":"Поздравляем! Этот уровень завершён."),soon:"скоро"},\n      uz:{h:curLabel+" tugadi!",p:pendingLabel?pendingLabel+" · tez orada.":(nextLabel?"Tabriklaymiz! "+nextLabel+" ochildi.":"Tabriklaymiz! Bu daraja tugadi."),soon:"tez orada"},\n      tj:{h:curLabel+" тамом!",p:pendingLabel?pendingLabel+" · ба зудӣ.":(nextLabel?"Табрик! "+nextLabel+" кушода шуд.":"Табрик! Ин сатҳ анҷом ёфт."),soon:"ба зудӣ"}\n    }[LANG]||{};\n', 'foundation': '  var m={\n    uz:{h:"0 dan asoslar",p:"你好 ni eshiting, tushuning va o\'zingiz tuzing",go:done?"Qaytarish":"Boshlash"},\n    ru:{h:"Основы с нуля",p:"Услышьте, поймите и соберите 你好",go:done?"Повторить":"Начать"},\n    tj:{h:"Асосҳо аз сифр",p:"你好-ро шунавед, фаҳмед ва худатон созед",go:done?"Такрор":"Оғоз"}\n  }[LANG];\n', 'rivalry': '\t    var rivNote={ru:ahead?"Вы впереди на "+diff.toLocaleString("ru")+" XP":"Отставание "+diff.toLocaleString("ru")+" XP",\n\t      uz:ahead?"Siz "+diff.toLocaleString("ru")+" XP oldinda":diff.toLocaleString("ru")+" XP orqadasiz",\n\t      tj:ahead?"Шумо "+diff.toLocaleString("ru")+" XP пеш":diff.toLocaleString("ru")+" XP қафо"}[LANG];\n'}
        fragments = {}
        for name, map_id, end in (
            ("soon", "ui.course_v3.levelSoon.templates", "  App.openSheet("),
            ("level", "ui.course_v3.levelCompletion.templates", "    var g=(data&&data.gamification)"),
            ("foundation", "ui.course_v3.foundationEntry.templates", "  return "),
            ("rivalry", "ui.course_v3.rivalry.templates", "    var rivTitle="),
        ):
            position = source.index(json.dumps(map_id))
            start = source.rfind("\n", 0, position) + 1
            fragments[name] = source[start:source.index(end, start)]
        script = r"""
const vm=require("vm"),arg=JSON.parse(require("fs").readFileSync(0,"utf8"));
const window={};vm.runInNewContext(arg.bundle,{window});
function run(code,lang,names,values,result,view){return new Function("window","LANG",...names,
  code+"\nreturn "+result)(view,lang,...values)}
const outputs=[];
for(const lang of ["uz","ru","tj"]){
  for(const next of ["","HSK 2"]){for(const pending of ["","HSK 3"]){
    const args=["HSK 1",next,pending],names=["curLabel","nextLabel","pendingLabel"];
    outputs.push({base:run(arg.originals.level,lang,names,args,"levelCopy",{}),
      actual:run(arg.fragments.level,lang,names,args,"levelCopy",window)});
  }}
  for(const done of [false,true])outputs.push({
    base:run(arg.originals.foundation,lang,["done"],[done],"m",{}),
    actual:run(arg.fragments.foundation,lang,["done"],[done],"({h:m.h,p:m.p,go:m.go})",window)});
  for(const ahead of [false,true])for(const diff of [0,1,12345])outputs.push({
    base:run(arg.originals.rivalry,lang,["ahead","diff"],[ahead,diff],"rivNote",{}),
    actual:run(arg.fragments.rivalry,lang,["ahead","diff"],[ahead,diff],"rivNote",window)});
  outputs.push({base:run(arg.originals.soon,lang,["label"],["HSK 3.0 · HSK 2"],"copy",{}),
    actual:run(arg.fragments.soon,lang,["label"],["HSK 3.0 · HSK 2"],"copy",window)});
}
window.HSKAI_MINIAPP_I18N.uz["ui.course_v3.levelCompletion.templates.h"]="QA {level}";
window.HSKAI_MINIAPP_I18N.uz["ui.course_v3.levelSoon.templates.body"]="QA SOON";
window.HSKAI_MINIAPP_I18N.uz["ui.course_v3.foundationEntry.templates.p"]="QA FOUNDATION";
window.HSKAI_MINIAPP_I18N.uz["ui.course_v3.rivalry.templates.ahead"]="QA {xp}";
const overrides={level:run(arg.fragments.level,"uz",["curLabel","nextLabel","pendingLabel"],
 ["HSK 1","",""],"levelCopy.h",window),soon:run(arg.fragments.soon,"uz",["label"],["HSK 2"],"copy.body",window),
 foundation:run(arg.fragments.foundation,"uz",["done"],[false],"m.p",window),
 rivalry:run(arg.fragments.rivalry,"uz",["ahead","diff"],[true,12345],"rivNote",window)};
process.stdout.write(JSON.stringify({outputs,overrides}));
"""
        completed = subprocess.run(["node", "-e", script],
            input=json.dumps({"bundle": (ROOT / TARGET).read_text(),
                              "originals": originals, "fragments": fragments}),
            capture_output=True, text=True, timeout=30, check=True)
        result = json.loads(completed.stdout)
        self.assertEqual(len(result["outputs"]), 39)
        for row in result["outputs"]:
            self.assertEqual(row["actual"], row["base"])
        self.assertEqual(result["overrides"], {
            "level": "QA HSK 1", "soon": "QA SOON",
            "foundation": "QA FOUNDATION", "rivalry": "QA 12\u00a0345",
        })

    def test_answer_prefix_and_embedded_level_label_reuse_course_catalog(self):
        source = (ROOT / "app/static/course-v3.html").read_text()
        choice = "function _choiceFromWord(" + source.split(
            "function _choiceFromWord(", 1)[1].split("\nfunction cardWordFlash", 1)[0]
        literal, _ = extract_literal(source, "I18N")
        self.assertIn('mine_t=courseMessage("testHub.mineLevel",MINE_T[LANG]||MINE_T.uz)', source)
        script = r"""
const vm=require("vm"),arg=JSON.parse(require("fs").readFileSync(0,"utf8"));
const legacy=vm.runInNewContext("("+arg.literal+")",Object.create(null));
const render=new Function("window","I18N","$","esc",arg.choice+
 ';var opts=["我","你","学"],c={};_choiceFromWord(c,opts,1,"Question",{},"head");'+
 'return {c,sameOptions:c.options===opts};');
const catalog={};for(const lang of ["uz","ru","tj"])catalog[lang]={rightAns:"QA "+lang};
const fake=()=>({style:{},innerHTML:""}),esc=value=>String(value);
process.stdout.write(JSON.stringify({base:render({},legacy,fake,esc),
 actual:render({HSKAI_COURSE_I18N:catalog},legacy,fake,esc),legacy}));
"""
        completed = subprocess.run(["node", "-e", script],
            input=json.dumps({"choice": choice, "literal": literal}),
            capture_output=True, text=True, timeout=30, check=True)
        result = json.loads(completed.stdout)
        for variant in ("base", "actual"):
            self.assertTrue(result[variant]["sameOptions"])
            self.assertEqual(result[variant]["c"]["correct_index"], 1)
            self.assertEqual(result[variant]["c"]["options"], ["我", "你", "学"])
        for lang in ("uz", "ru", "tj"):
            self.assertEqual(result["base"]["c"]["explanation"][lang],
                             result["legacy"][lang]["rightAns"] + " 你")
            self.assertEqual(result["actual"]["c"]["explanation"][lang], "QA " + lang + " 你")

    def test_intl_and_android_icon_identifiers_are_not_translated(self):
        catalogs = read_sources()
        self.assertNotIn("ui.subscription.renewalDates.copy1", catalogs["uz"]["maps"])
        source = (ROOT / "app/static/subscription.html").read_text()
        self.assertIn('const locale=({uz:"uz-UZ",ru:"ru-RU",tj:"tg-TJ"})[state.lang]', source)
        self.assertNotIn('HSKAILocaleMap||function(_,fallback){return fallback})("ui.subscription.renewalDates', source)
        contexts = catalogs["uz"]["maps"]["ui.desktop_download.ANDROID_PROMO_COPY.copy1"]["object"]
        icons = [benefit["list"][0] for context in contexts.values()
                 for benefit in context["object"]["benefits"]["list"]]
        self.assertEqual(len(icons), 15)
        self.assertTrue(all(set(icon) == {"literal"} for icon in icons))
        for locale in ("uz", "ru", "tj"):
            self.assertFalse(any(key.endswith("benefits.item1.item1")
                                 for key in catalogs[locale]["messages"]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for locale in ("uz", "ru", "tj"):
                dest = root / f"localization/ui/{locale}"
                dest.mkdir(parents=True)
                for namespace in ("miniapp", "common", "course"):
                    shutil.copyfile(ROOT / f"localization/ui/{locale}/{namespace}.json", dest / f"{namespace}.json")
            dest = root / "localization/ui/uz/miniapp.json"
            original = json.loads(dest.read_text())
            metadata = json.loads(json.dumps(original))
            metadata["maps"]["ui.subscription.renewalDates.copy1"] = {"literal": "uz-UZ"}
            dest.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, "locale identifiers"):
                read_sources(root)
            bad_icons = json.loads(json.dumps(original))
            benefits = bad_icons["maps"]["ui.desktop_download.ANDROID_PROMO_COPY.copy1"]["object"]["course"]["object"]["benefits"]["list"]
            benefits[0]["list"][0] = {"message": next(iter(original["messages"]))}
            dest.write_text(json.dumps(bad_icons))
            with self.assertRaisesRegex(ValueError, "icon identifiers"):
                read_sources(root)

    def test_phrase_learning_sources_remain_byte_identical(self):
        proof = json.loads((ROOT / "localization/review/miniapp_inline_map_migration.json").read_text())
        self.assertEqual(len(proof["protected_phrase_blocks"]), 2)
        for guard in proof["protected_phrase_blocks"]:
            source = (ROOT / guard["source"]).read_text()
            block = "var SAFE=[" + source.split("var SAFE=[", 1)[1].split("];", 1)[0] + "];"
            self.assertNotIn("HSKAILocaleMap", block)
            self.assertEqual(hashlib.sha256(block.encode()).hexdigest(), guard["sha256"])


if __name__ == "__main__":
    unittest.main()
