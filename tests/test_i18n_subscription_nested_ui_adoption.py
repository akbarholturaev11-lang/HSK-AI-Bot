"""Exact source parity and nested subscription UI overlays without payment mutations."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOCALES=("uz","ru","tj")


def source_and_literal():
    source=(ROOT/"app/static/subscription.html").read_text(encoding="utf-8")
    block=source.split("const I18N=",1)[1].split("};var SUBSCRIPTION_UI=",1)[0]+"}"
    literal=json.loads(re.sub(
        r"([{,]\s*)([A-Za-z_$][A-Za-z0-9_$]*)(\s*:)",r'\1"\2"\3',block))
    return source,literal


def nested_labels(m):
    output={}
    normalize=lambda s: re.sub(r"_([a-z0-9])",lambda v:v.group(1).upper(),s)
    for group in ("modeTitles","modeTv","modePlans","planLabels","rows","cardHints"):
        for k,v in m[group].items():
            output[f"{group}.{normalize(k)}"]=v
    for section,labels in m["focus"].items():
        for key in ("t","d"):
            output[f"focus.{section}.{key}"]=labels[key]
    for index,pair in enumerate(m["benefits"]):
        output[f"benefit{index}.title"]=pair[0]
        output[f"benefit{index}.description"]=pair[1]
    for index,value in enumerate(m["perks"]):
        output[f"perk{index}"]=value
    for group in ("methods","countries"):
        for k,pair in m[group].items():
            output[f"{group}.{normalize(k)}.title"]=pair[0]
            output[f"{group}.{normalize(k)}.description"]=pair[1]
    return output


class SubscriptionNestedUIAdoptionTests(unittest.TestCase):
    def test_all_79_nested_display_labels_exact_for_3_locales(self):
        source,data=source_and_literal()
        self.assertEqual(set(data),set(LOCALES))
        for locale in LOCALES:
            with self.subTest(locale=locale):
                values=nested_labels(data[locale])
                self.assertEqual(len(values),79)
                catalog=json.loads(
                    (ROOT/f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
                )["messages"]
                self.assertEqual(len(catalog),895)
                for key,value in values.items():
                    self.assertEqual(catalog["subscriptionNested."+key],value)
        self.assertLess(source.index("hsk-course-i18n.js?v=20261020-57ce728d755d"),
                        source.index("const I18N={"))

    def test_nested_view_only_and_original_payment_id_paths(self):
        source,_=source_and_literal()
        self.assertIn('dict["subscriptionNested."+key]',source)
        self.assertIn('m[group][key]=subscriptionNestedLabel(locale,group+"."+n(key),m[group][key])',source)
        for marker in (
            "const HSK30_UNLOCK_MODE=",
            "const state={",
            "function tr(){return I18N[state.lang]||I18N.uz}",
            "const API=",
        ):
            self.assertIn(marker,source)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_node_nested_override_and_fallback_preserves_ids(self):
        source,data=source_and_literal()
        script="const I18N="+source.split("const I18N=",1)[1].split(
            "\n\nconst HSK30_UNLOCK_MODE=",1
        )[0]
        node=r"""
const fs=require("fs");
const arg=JSON.parse(fs.readFileSync(0,"utf8"));
const factory=new Function("window",arg.script+"\nreturn I18N;");
const fallback=factory({});
const hydrated=factory({HSKAI_COURSE_I18N:arg.overrides});
process.stdout.write(JSON.stringify({fallback,hydrated}));
"""
        overrides={
            locale:{
                "subscriptionNested.modeTitles.referralDiscount":"QA OFFER "+locale,
                "subscriptionNested.focus.qa.t":"QA FOCUS "+locale,
                "subscriptionNested.benefit0.title":"QA BENEFIT "+locale,
                "subscriptionNested.methods.dcCity.description":"QA DC "+locale,
                "subscriptionNested.perk0":""
            } for locale in LOCALES
        }
        result=json.loads(subprocess.run(
            ["node","-e",node],input=json.dumps({"script":script,"overrides":overrides}),
            text=True,capture_output=True,timeout=20,check=True,
        ).stdout)
        self.assertEqual(result["fallback"],data)
        expected=json.loads(json.dumps(data))
        for locale in LOCALES:
            m=expected[locale]
            m["modeTitles"]["referral_discount"]="QA OFFER "+locale
            m["focus"]["qa"]["t"]="QA FOCUS "+locale
            m["benefits"][0][0]="QA BENEFIT "+locale
            m["methods"]["dc_city"][1]="QA DC "+locale
        self.assertEqual(result["hydrated"],expected)


if __name__=="__main__":
    unittest.main()
