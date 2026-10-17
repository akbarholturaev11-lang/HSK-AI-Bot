"""Regression tests for selected read-only Mini App locale dictionaries."""
import unittest
from scripts.i18n_miniapp_catalog_audit import compare_literal, extract_literal, inventory, split_top


class MiniappCatalogAuditTests(unittest.TestCase):
    def test_nested_maps_and_arrays(self):
        data = """{
            uz:{label:"Hello {name}",body:{title:"A"},benefits:[["B","C"]]},
            ru:{label:"Hello {name}",body:{title:"D"},benefits:[["E","F"]]},
            tj:{label:"Hello {name}",body:{title:"G"},benefits:[["H","I"]]}
        }"""
        report = compare_literal(data)
        self.assertEqual(report["leaf_counts"], {"uz":4,"ru":4,"tj":4})
        self.assertEqual(report["missing_leaves"], [])
        self.assertEqual(report["placeholder_drift"], [])

    def test_missing_and_placeholder_contract(self):
        report = compare_literal("""{
            uz:{title:"{name}",extra:"x"},
            ru:{title:"{user}"},
            tj:{title:"{name}"}
        }""")
        self.assertEqual(report["missing_leaves"], [{"path":"extra","missing":["ru","tj"]}])
        self.assertEqual([x["locale"] for x in report["placeholder_drift"]], ["ru"])
        self.assertNotIn("{user}", str(report["missing_leaves"]))

    def test_duplicate_key_and_dynamic_expression(self):
        report = compare_literal("""{
            uz:{title:"Hi",title:"Again",next:call()},
            ru:{title:"Hi",next:call()},
            tj:{title:"Hi",next:call()}
        }""")
        self.assertTrue(any(x["issue"] == "duplicate_property" for x in report["parse_review"]))
        self.assertTrue(any(x["issue"] == "dynamic_value" for x in report["parse_review"]))

    def test_legacy_function_copy_parameters_are_reviewed(self):
        source = """{
            uz:{count:function(n, level){return level+n;}},
            ru:{count:function(n, level){return level+n;}},
            tj:{count:function(n, amount){return amount+n;}}
        }"""
        result = compare_literal(source)
        self.assertEqual(len([row for row in result["parse_review"]
                              if row["issue"] == "legacy_function_copy"]), 3)
        self.assertEqual(result["legacy_function_parameter_drift"][0]["locale"], "tj")
        self.assertEqual(result["missing_leaves"], [])

    def test_rejects_bad_source(self):
        with self.assertRaises(ValueError):
            split_top('{uz:{k:"unterminated},')
        with self.assertRaises(ValueError):
            compare_literal('{uz:{title:"Missing other languages"}}')
        with self.assertRaises(ValueError):
            extract_literal("const I18N = dynamicCatalog;", "I18N")

    def test_live_selected_sources_are_parsable_without_runtime(self):
        report = inventory()
        self.assertEqual(len(report["catalogs"]), 18)
        for row in report["catalogs"]:
            self.assertEqual(set(row["leaf_counts"]), {"uz","ru","tj"})
            self.assertGreater(min(row["leaf_counts"].values()), 0)
            # Deviations are candidates, not automatically confirmed defects.
            self.assertGreaterEqual(row["leaf_union"], max(row["leaf_counts"].values()))
            self.assertIsInstance(row["placeholder_drift"], list)
            self.assertIsInstance(row["parse_review"], list)


if __name__ == "__main__":
    unittest.main()
