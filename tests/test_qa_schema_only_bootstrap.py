"""Offline safety regression suite for the QA-only schema bootstrap."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/qa_schema_only_bootstrap.py"
spec = importlib.util.spec_from_file_location("qa_schema_only_bootstrap", SCRIPT)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

EXAMPLE = {
    "RAILWAY_ENVIRONMENT_NAME": "staging",
    "QA_SCHEMA_ONLY_SOURCE_APPROVED": module.EXPECTED_REVISION,
    "QA_SOURCE_HOST": "test-source.railway.internal",
    "QA_SOURCE_DB": "native_audit_restore_before",
    "QA_SOURCE_USER": "qa_src", "QA_SOURCE_PASSWORD": "dummy-password",
    "QA_TARGET_HOST": "test-target.railway.internal",
    "QA_TARGET_DB": "hsk_universal_qa_schema",
    "QA_TARGET_USER": "qa_dst", "QA_TARGET_PASSWORD": "dummy-password",
}


class QaSchemaOnlyBootstrapTests(unittest.TestCase):
    def test_rejects_nonstaging_and_unsafe_destination(self):
        changes = (
            {"RAILWAY_ENVIRONMENT_NAME": "production"},
            {"QA_SCHEMA_ONLY_SOURCE_APPROVED": "0101_account_deletion_requests"},
            {"QA_SOURCE_HOST": "prod-db.railway.internal"},
            {"QA_TARGET_HOST": EXAMPLE["QA_SOURCE_HOST"]},
            {"QA_TARGET_DB": "production"},
            {"QA_TARGET_DB": "railway"},
            {"QA_TARGET_DB": "some_other_database"},
            {"QA_TARGET_HOST": "localhost"},
        )
        for delta in changes:
            with self.subTest(delta=delta), self.assertRaises(module.BootstrapError):
                module.load_settings(EXAMPLE | delta)

    def test_dry_run_never_creates_or_imports(self):
        with patch.object(module, "check") as check, patch.object(module, "copy_schema") as copy:
            self.assertEqual(module.main([], EXAMPLE), 0)
            check.assert_called_once()
            copy.assert_not_called()

    def test_apply_requires_explicit_confirmation(self):
        with patch.object(module, "check"), patch.object(module, "copy_schema") as copy:
            self.assertEqual(module.main(["--apply"], EXAMPLE), 2)
            copy.assert_not_called()
            self.assertEqual(module.main(["--apply"], EXAMPLE | {
                "QA_SCHEMA_ONLY_CONFIRM": module.CONFIRM,
            }), 0)
            copy.assert_called_once()

    def test_source_is_readonly_and_target_not(self):
        config = module.load_settings(EXAMPLE)
        src = module.pg_env(config, True)
        dst = module.pg_env(config, False)
        self.assertEqual(src["PGOPTIONS"], "-c default_transaction_read_only=on")
        self.assertNotIn("PGOPTIONS", dst)
        self.assertNotEqual(src["PGHOST"], dst["PGHOST"])
        self.assertNotEqual(src["PGPASSWORD"], dst.get("QA_SOURCE_PASSWORD"))

    def test_dump_is_always_schema_only(self):
        # This is a source-contract regression: no data export is authorized.
        code = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"--schema-only"', code)
        self.assertNotIn('"--data-only"', code)
        self.assertIn("target_already_exists", code)


if __name__ == "__main__":
    unittest.main()
