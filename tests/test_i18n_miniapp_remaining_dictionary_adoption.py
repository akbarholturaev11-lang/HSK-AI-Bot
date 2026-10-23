"""Primary catalog adoption for remaining fixed Mini App dictionaries.

Only UI snippets execute in Node; no app imports, auth, network or course data.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

from scripts.i18n_miniapp_catalog_audit import (
    TARGETS, extract_literal, key_value, split_top,
)

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("uz", "ru", "tj")


def static_value(value):
    value = value.strip()
    if value.startswith("{"):
        return {key: static_value(child)
                for key, child in map(key_value, split_top(value))}
    if value.startswith("["):
        return [static_value(child) for child in split_top(value)]
    if value.startswith("function"):
        return None  # Explicit dictionary plural functions are checked separately.
    return ast.literal_eval(value)


def catalog_sources():
    return {locale: json.loads((ROOT / f"localization/ui/{locale}/course.json")
                              .read_text(encoding="utf-8"))["messages"]
            for locale in LOCALES}


def memo_ui_literal():
    source = (ROOT / "app/static/course_v3_data/memo.js").read_text(encoding="utf-8")
    block = source.split("window.MEMO_UI = ", 1)[1].split("\n};", 1)[0] + "\n}"

    def parse(value):
        value = value.strip()
        if value.startswith("t(") and value.endswith(")"):
            cells = ast.literal_eval("[" + value[2:-1] + "]")
            if len(cells) != 3:
                raise ValueError("Three original locale values required")
            return dict(zip(LOCALES, cells))
        if value.startswith("{"):
            return {key: parse(child)
                    for key, child in map(key_value, split_top(value))}
        if value.startswith("["):
            return [parse(child) for child in split_top(value)]
        raise ValueError("Only static UI dictionaries allowed")

    return source, parse(block)


def memo_leaves(node, prefix="memorizeUi"):
    if isinstance(node, dict) and set(node) == set(LOCALES):
        return {prefix: node}
    output = {}
    items = ([("item" + str(index), child)
              for index, child in enumerate(node, 1)]
             if isinstance(node, list) else node.items())
    for key, child in items:
        output.update(memo_leaves(child, prefix + "." + key))
    return output


def node_json(script, payload):
    result = subprocess.run(["node", "-e", script], input=json.dumps(payload),
                            text=True, capture_output=True, timeout=20, check=True)
    return json.loads(result.stdout)


class RemainingMiniappDictionaryAdoptionTests(unittest.TestCase):
    def test_all_18_registered_maps_have_canonical_static_leaf_coverage(self):
        catalogs = catalog_sources()
        prefixes = {
            ("course-v3.html", "I18N"): "",
            ("course-v3.html", "TRACK_UI"): "track",
            ("course-v3.html", "HSK30_BOOK_COPY"): "hsk30Book",
            ("subscription.html", "I18N"): "subscriptionPage",
            ("course_v3_test.html", "L"): "testHub",
            ("course_v3_test.html", "EM"): "testExam",
            ("course_v3_test.html", "HSK30_SOON"): "testHsk30Soon",
            ("course_v3_test.html", "PT"): "testPlacement",
            ("course_v3_mistakes.html", "L"): "mistakesPage",
            ("course_v3_pronunciation.html", "L"): "pronunciation",
            ("course_v3_recognition.html", "L"): "recognition",
            ("course_v3_onboarding.html", "ONBOARDING_LEGACY"): "onboarding",
            ("course_v3_voice.html", "L"): "voicePage",
            ("hsk-lugat.html", "UI"): "dictionaryPage",
            ("hsk-lugat.html", "practiceLabels"): "dictionaryPractice",
            ("hsk-lugat.html", "memoLabels"): "dictionaryMemo",
            ("hsk-lugat.html", "messages"): "dictionaryWriterStatus",
            ("hsk-gaplar.html", "UI"): "readyPhrases",
        }
        self.assertEqual(len(prefixes), len(TARGETS))
        for filename, name in TARGETS:
            source = (ROOT / filename).read_text(encoding="utf-8")
            literal = static_value(extract_literal(source, name)[0])
            prefix = prefixes[(Path(filename).name, name)]
            for locale in LOCALES:
                def check(node, path):
                    if node is None:
                        self.assertEqual(prefix, "dictionaryPage")
                        self.assertIn(path, ("dictionaryPage.countAll",
                                             "dictionaryPage.countResults",
                                             "dictionaryPage.strokes"))
                    elif isinstance(node, dict):
                        for key, child in node.items():
                            child_path = (path + "." if path else "") + key
                            if path == "testExam" and key == "sec":
                                child_path = "testExamSection"
                            check(child, child_path)
                    elif isinstance(node, str):
                        with self.subTest(file=filename, name=name, key=path, locale=locale):
                            self.assertEqual(catalogs[locale][path], node)
                    else:
                        self.fail("Unexpected nonstatic registered UI leaf")
                if prefix == "subscriptionPage":
                    # All 79 nested leaves are independently covered by
                    # test_i18n_subscription_nested_ui_adoption, including IDs.
                    check({key: value for key, value in literal[locale].items()
                           if isinstance(value, str)}, prefix)
                else:
                    check(literal[locale], prefix)

    def test_40_memo_fixed_ui_values_and_untouched_learning_payload(self):
        source, literal = memo_ui_literal()
        leaves = memo_leaves(literal)
        self.assertEqual(len(leaves), 40)
        catalogs = catalog_sources()
        for key, cells in leaves.items():
            for locale in LOCALES:
                self.assertEqual(catalogs[locale][key], cells[locale])
        # Frozen original MEMO_BASE/MEMO_DATA includes Chinese, pinyin,
        # distractors, near flags and graded cloze/build answer identities.
        payload = source.split("// Pinyin + qisqa ma'no", 1)[1]
        self.assertEqual(hashlib.sha256(payload.encode()).hexdigest(),
                         "6a0e69455a0d774e91ed470ae97a5fcf39830031acecbf7fd48b399c822a425c")
        self.assertIn('adoptMemoUi(window.MEMO_UI,"memorizeUi")', source)
        self.assertNotIn("fetch(", source.split("window.MEMO_BASE", 1)[0])

    def test_three_practice_gates_keep_auth_flow_and_use_shared_ui(self):
        catalogs = catalog_sources()
        for page in ("memorize", "pronunciation", "recognition"):
            source = (ROOT / f"app/static/course_v3_{page}.html").read_text(encoding="utf-8")
            block = source.split("function practiceGateErrorCopy(){var copy=(", 1)[1]
            literal = static_value(block.split(")[LANG];", 1)[0])
            for locale in LOCALES:
                for key, value in literal[locale].items():
                    self.assertEqual(catalogs[locale]["practiceGate." + key], value)
            self.assertIn('dict["practiceGate."+key]', source)
            self.assertIn('if(typeof value==="string"&&value)copy[key]=value', source)
            self.assertIn('feature:"' + page + '",ref:ref', source)
            self.assertIn(".then(validatePracticeGate)", source)

    def test_main_hydrates_all_locales_and_has_corrected_uzbek_fallback(self):
        source = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        for name, prefix in (("I18N", ""), ("TRACK_UI", "track"),
                             ("HSK30_BOOK_COPY", "hsk30Book")):
            self.assertIn('adoptCourseLocaleDictionary(' + name + ',"' + prefix + '")', source)
        expected = ("Joriy kursdagi progressingiz saqlanadi. Istalgan payt "
                    "boshqa versiyaga qaytishingiz mumkin.")
        self.assertEqual(catalog_sources()["uz"]["track.switchConfirmBody"], expected)
        self.assertIn(expected, source)
        self.assertNotIn("qayтишингиз мумкин", source)
        for key in ("lessonPreview.helloGloss", "rating.leagueName", "rating.membersTotal"):
            self.assertIn('courseMessage("' + key + '",', source)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_memo_override_and_empty_missing_malformed_fallback(self):
        source, original = memo_ui_literal()
        snippet = source.split("// Pinyin + qisqa ma'no", 1)[0] + "})();return window.MEMO_UI;"
        changed = {locale: {key: "QA " + locale + " " + key
                            for key in memo_leaves(original)} for locale in LOCALES}
        output = node_json(r"""
const arg=JSON.parse(require("fs").readFileSync(0,"utf8"));
const render=new Function("window",arg.snippet);
process.stdout.write(JSON.stringify({base:render({}),changed:render({HSKAI_COURSE_I18N:arg.changed}),
  invalid:render({HSKAI_COURSE_I18N:{uz:{"memorizeUi.cont":"","memorizeUi.idk":42}}})}));
""", {"snippet": snippet, "changed": changed})
        self.assertEqual(output["base"], original)
        self.assertEqual(output["invalid"], original)
        for key, cells in memo_leaves(output["changed"]).items():
            self.assertEqual(cells, {locale: changed[locale][key] for locale in LOCALES})

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_main_primary_generated_values_and_fallback_for_every_locale(self):
        source = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        helper = source.split("function adoptCourseLocaleDictionary(", 1)[1].split(
            'adoptCourseLocaleDictionary(I18N,"");', 1)[0]
        helper = "function adoptCourseLocaleDictionary(" + helper
        dictionaries = {name: static_value(extract_literal(source, name)[0])
                        for name in ("I18N", "TRACK_UI", "HSK30_BOOK_COPY")}
        changed = {locale: {"cont": "QA CONT " + locale,
                            "nav.course": "QA COURSE " + locale,
                            "track.courseVersion": "QA TRACK " + locale,
                            "hsk30Book.body": "QA BOOK " + locale,
                            "track.cancel": "", "track.close": None}
                   for locale in LOCALES}
        output = node_json(r"""
const arg=JSON.parse(require("fs").readFileSync(0,"utf8"));
const render=new Function("window","dicts",arg.helper+
  ';adoptCourseLocaleDictionary(dicts.I18N,"");adoptCourseLocaleDictionary(dicts.TRACK_UI,"track");'+
  'adoptCourseLocaleDictionary(dicts.HSK30_BOOK_COPY,"hsk30Book");return dicts;');
process.stdout.write(JSON.stringify({base:render({},structuredClone(arg.dictionaries)),
  changed:render({HSKAI_COURSE_I18N:arg.changed},structuredClone(arg.dictionaries))}));
""", {"helper": helper, "dictionaries": dictionaries, "changed": changed})
        self.assertEqual(output["base"], dictionaries)
        expected = copy.deepcopy(dictionaries)
        for locale in LOCALES:
            expected["I18N"][locale]["cont"] = changed[locale]["cont"]
            expected["I18N"][locale]["nav"]["course"] = changed[locale]["nav.course"]
            expected["TRACK_UI"][locale]["courseVersion"] = changed[locale]["track.courseVersion"]
            expected["HSK30_BOOK_COPY"][locale]["body"] = changed[locale]["hsk30Book.body"]
        self.assertEqual(output["changed"], expected)


if __name__ == "__main__":
    unittest.main()
