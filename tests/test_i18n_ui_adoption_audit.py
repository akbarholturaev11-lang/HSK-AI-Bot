"""New fixed locale maps cannot bypass central authoring unnoticed."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_ui_adoption_audit import ROOT, audit, locale_maps


class UIAdoptionCoverageTests(unittest.TestCase):
    def test_current_python_maps_are_explicitly_classified(self):
        report = audit()
        self.assertEqual(report["unclassified"], [])
        self.assertEqual(report["stale_classifications"], [])
        self.assertEqual(report["classified_maps"], 79)
        self.assertTrue(report["categories"]["learning_material"])

    def test_new_ui_map_requires_a_canonical_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "app/bot/handlers/example.py"
            source.parent.mkdir(parents=True)
            source.write_text('LABELS={"uz":"Davom","ru":"Продолжить","tj":"Идома"}')
            registry = root / "localization/review/ui_map_exceptions.json"
            registry.parent.mkdir(parents=True)
            data = {"schema_version": 1, "scope": "fixture", "exceptions": []}
            registry.write_text(json.dumps(data))
            self.assertEqual(len(audit(root)["unclassified"]), 1)
            row = next(locale_maps(root))
            data["exceptions"] = [{"source": row["source"], "sha256": row["sha256"],
                                   "category": "admin_only", "count": 1}]
            registry.write_text(json.dumps(data))
            self.assertEqual(audit(root)["unclassified"], [])
            source.write_text(source.read_text() + '\nMORE={"uz":"x","ru":"y","tj":"z"}')
            self.assertEqual(len(audit(root)["unclassified"]), 1)
            source.write_text("")
            self.assertEqual(len(audit(root)["stale_classifications"]), 1)


if __name__ == "__main__":
    unittest.main()
