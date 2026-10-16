"""Safety and preservation checks for the operator's read-only rehearsal helper."""
import copy
from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/rehearse_native_account_migration.py"
SPEC = importlib.util.spec_from_file_location("native_rehearsal", SCRIPT)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)
KEY = b"unit-test-key-32-bytes-no-real-data"
STAGING = "postgresql://user:secret@stage.example.test:1234/rehearsal"
PRODUCTION = "postgresql://user:secret@production.example.test:5678/live"
APPROVED = {"purpose": "staging", "host": "stage.example.test", "port": 1234, "database": "rehearsal"}


def table(table_name, *, migrated=False, mutate=None):
    row = {"id": 42, "value": "private learner evidence"}
    if table_name == "users":
        row.update(payment_preview_available=False, payment_preview_payment_id=73)
    if table_name in helper.OWNERS:
        row[helper.OWNERS[table_name]] = 1001
        if table_name in helper.FOUNDATION or migrated:
            row["user_id"] = 7 if migrated else None
        if table_name in helper.DEDUPE:
            row.update({helper.DEDUPE[table_name]: "opened", "dedupe_key": "dedupe"})
    if table_name == "desktop_link_requests":
        row.update(intent="link", status="expired" if migrated else "pending")
        if migrated:
            row.update(language=None, bind_session_id=None, approved_identity_id=None)
    baseline_columns = sorted(name for name in row if not (
        migrated and ((table_name in helper.AI_VOICE and name == "user_id") or
                      (table_name == "desktop_link_requests" and name in ("language", "bind_session_id", "approved_identity_id")))))
    if mutate:
        mutate(row)
    summary = helper.TableSummary(table_name, sorted(row), baseline_columns, {1001: 7}, KEY, not migrated)
    summary.add(row)
    return summary.finish()


def snapshots():
    names = set(helper.OWNERS) | {"desktop_link_requests", "desktop_devices"}
    names |= {table for group in helper.CRITICAL.values() for table in group}
    before_tables = {name: table(name) for name in names}
    after_tables = {name: table(name, migrated=True) for name in names}
    before_schema = {name + "." + column: {"type": "int4", "nullable": False}
                     for name, summary in before_tables.items() for column in summary["columns"]}
    for name, column in helper.NULLABLE:
        before_schema.setdefault(name + "." + column, {"type": "int8", "nullable": False})
    after_schema = copy.deepcopy(before_schema)
    for name, column in helper.NULLABLE:
        after_schema[name + "." + column]["nullable"] = True
    for name in ("language", "bind_session_id", "approved_identity_id"):
        after_schema["desktop_link_requests." + name] = {"type": "varchar", "nullable": True}
    for name in helper.AI_VOICE:
        after_schema[name + ".user_id"] = {"type": "int4", "nullable": True}
    def report(tables, schema, migrated):
        constraints = {"users.users_telegram_id_key": {"kind": "u", "columns": ["telegram_id"], "definition_digest": "unique-tg"},
                       "course_progress.course_progress_user_id_fkey": {"kind": "f", "columns": ["user_id"], "definition_digest": "progress-fk"}}
        if migrated:
            constraints |= {name: {"kind": "u", "columns": ["user_id"], "definition_digest": "known-new"} for name in helper.ADDED_CONSTRAINTS}
        else:
            constraints["users.users_telegram_id_not_null"] = {"kind": "n", "columns": ["telegram_id"], "definition_digest": "not-null"}
        indexes = {"users.ix_users_telegram_id": "real-tg-unique-index"}
        if migrated:
            indexes |= {name: "known-new" for name in helper.ADDED_INDEXES}
        return {"format": 2, "read_only": True, "server_major": 18, "sequence_digest": "sequence", "account_keys_digest": "accounts",
                "key_id": "test-key-id", "inventory_digest": "test-inventory",
                "migration_head": [helper.HEAD_REVISION if migrated else helper.BASE_REVISION],
                "migration_contract": migrated, "schema_digest": "after" if migrated else "before",
                "column_schema": schema, "tables": tables, "inventory_contract": not migrated,
                "column_metadata": {column: "preserved-default-and-modifiers" for column in schema},
                "constraint_metadata": constraints, "index_metadata": indexes,
                "critical": {group: helper.digest(KEY, {name: tables[name]["migration_legacy_digest"] for name in members})
                             for group, members in helper.CRITICAL.items()}}
    return report(before_tables, before_schema, False), report(after_tables, after_schema, True)


class DestinationSafetyTests(unittest.TestCase):
    def test_only_explicit_exact_staging_destination_is_allowed(self):
        self.assertEqual(helper.validate_destination(STAGING, APPROVED, PRODUCTION), ("stage.example.test", 1234, "rehearsal"))
        for change in ({"host": "other.example.test"}, {"port": 5432}, {"database": "other"}, {"purpose": "production"}):
            with self.subTest(change=change), self.assertRaises(helper.RehearsalError):
                helper.validate_destination(STAGING, APPROVED | change, PRODUCTION)

    def test_production_endpoint_is_denied_even_with_another_database(self):
        with self.assertRaisesRegex(helper.RehearsalError, "production_endpoint_refused"):
            helper.validate_destination(STAGING, APPROVED, STAGING.replace("/rehearsal", "/production"))

    def test_local_ambiguous_and_overridden_destinations_are_refused(self):
        for host in ("localhost", "127.0.0.1", "::1", "postgres", "host.docker.internal", "stage.local", "stage.localhost."):
            safe_host = "[::1]" if host == "::1" else host
            url = STAGING.replace("stage.example.test", safe_host)
            with self.subTest(host=host), self.assertRaises(helper.RehearsalError):
                helper.validate_destination(url, APPROVED | {"host": host}, PRODUCTION)
        for query in ("host=production.example.test", "%68ost=production.example.test", "port=5678", "dbname=live", "service=prod"):
            with self.subTest(query=query), self.assertRaisesRegex(helper.RehearsalError, "alternate_destination_refused"):
                helper.validate_destination(STAGING + "?" + query, APPROVED, PRODUCTION)
        for url in ("sqlite:///test.db", "postgresql://user:secret@stage.example.test/rehearsal", "postgresql:///rehearsal"):
            with self.subTest(url=url), self.assertRaises(helper.RehearsalError):
                helper.validate_destination(url, APPROVED, PRODUCTION)

    def test_driver_decoded_production_and_local_aliases_are_refused(self):
        for host in ("%70roduction.example.test", "%6cocalhost", "%31%32%37.0.0.1", "stage.example.test,production.example.test"):
            url = STAGING.replace("stage.example.test", host)
            with self.subTest(host=host), self.assertRaises(helper.RehearsalError):
                helper.validate_destination(url, APPROVED | {"host": host}, PRODUCTION)

    def test_private_backup_and_exclusive_private_report(self):
        with tempfile.TemporaryDirectory() as directory:
            backup = Path(directory) / "backup.dump"
            backup.write_bytes(b"synthetic dump")
            backup.chmod(0o600)
            fingerprint = helper.backup_fingerprint(backup)
            self.assertEqual(fingerprint["bytes"], 14)
            self.assertNotIn(str(backup), json.dumps(fingerprint))
            backup.chmod(0o644)
            with self.assertRaises(helper.RehearsalError):
                helper.backup_fingerprint(backup)
            report = Path(directory) / "report.json"
            helper.write_report(report, {"ok": True})
            self.assertEqual(report.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                helper.write_report(report, {"ok": False})
            symlink = Path(directory) / "link.dump"
            symlink.symlink_to(backup)
            with self.assertRaises(OSError):
                helper.backup_fingerprint(symlink)

    def test_cli_errors_never_echo_database_driver_details(self):
        with patch.object(helper, "snapshot", side_effect=RuntimeError(STAGING)), patch("builtins.print") as output:
            code = helper.main(["snapshot", "--database-url-env", "STAGE", "--approved-target-env", "TARGET",
                                "--production-url-env", "PROD", "--digest-key-env", "KEY", "--schema-inventory", "inventory",
                                "--backup", "backup", "--output", "report"])
        self.assertEqual(code, 2)
        self.assertNotIn(STAGING, str(output.call_args_list))
        self.assertIn("details_suppressed", str(output.call_args_list))


class PreservationTests(unittest.TestCase):
    def test_current_preview_inventory_is_required_and_stale_inventory_is_refused(self):
        self.assertEqual(helper.BASE_REVISION, "0102_payment_review_preview")
        self.assertEqual(helper.HEAD_REVISION, "0105_native_ai_voice_ownership")
        before, _ = snapshots()
        inventory = {"read_only": True, "alembic_revisions": [helper.BASE_REVISION], "columns": [
            {"table_name": name.split(".")[0], "column_name": name.split(".")[1]}
            for name in before["column_schema"]]}
        self.assertIn("payment_preview_available", helper.validate_inventory(inventory)["users"])
        for revision in ("0101_account_deletion_requests", "0102_native_identity_accounts", "0104_native_ai_voice_ownership"):
            with self.subTest(revision=revision), self.assertRaisesRegex(helper.RehearsalError, "expected_readonly_baseline_inventory"):
                helper.validate_inventory(inventory | {"alembic_revisions": [revision]})
        for table_name, column_name in (("users", "payment_preview_payment_id"), ("users", "telegram_id"), ("ai_usage_budgets", "user_telegram_id")):
            missing = inventory | {"columns": [column for column in inventory["columns"]
                                               if (column["table_name"], column["column_name"]) != (table_name, column_name)]}
            with self.subTest(missing=column_name), self.assertRaisesRegex(helper.RehearsalError, "inventory_missing_migration_columns"):
                helper.validate_inventory(missing)

    def test_receipt_preview_state_must_survive_native_migration_and_backup_restore(self):
        before, after = snapshots()
        self.assertTrue(helper.compare_snapshots(before, after, "migration")["ok"])
        self.assertTrue(helper.compare_snapshots(after, copy.deepcopy(after), "restore")["ok"])
        for field, value in (("payment_preview_available", True), ("payment_preview_payment_id", None)):
            with self.subTest(field=field):
                changed = copy.deepcopy(after)
                changed["tables"]["users"] = table("users", migrated=True, mutate=lambda row: row.update({field: value}))
                changed["critical"]["billing"] = helper.digest(KEY, {
                    name: changed["tables"][name]["migration_legacy_digest"] for name in helper.CRITICAL["billing"]})
                for mode, source in (("migration", before), ("restore", after)):
                    result = helper.compare_snapshots(source, changed, mode)
                    self.assertFalse(result["ok"])
                    self.assertIn("rows_changed:users", result["failures"])
                    self.assertFalse(result["critical_values_preserved"]["billing"])

    def test_only_lossless_pg18_literal_array_cast_distribution_is_normalized(self):
        source = "CHECK ((status)::text = ANY ((ARRAY['pending'::character varying, 'approved'::character varying])::text[]))"
        restored = "CHECK ((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('approved'::character varying)::text]))"
        normalize = helper.normalize_inventory_definition
        self.assertEqual(normalize(source), normalize(restored))
        source_index = "CREATE UNIQUE INDEX test ON public.payments USING btree (user_id) WHERE " + source[7:-1]
        restored_index = "CREATE UNIQUE INDEX test ON public.payments USING btree (user_id) WHERE " + restored[7:-1]
        self.assertEqual(normalize(source_index), normalize(restored_index))
        for changed in (restored.replace("approved", "rejected"), restored.replace(" = ANY", " <> ANY"),
                        restored.replace("ANY", "ALL"), restored.replace("character varying", "character varying(3)"),
                        restored_index.replace("user_id", "other_user_id")):
            self.assertNotIn(normalize(changed), (normalize(source), normalize(source_index)))

    def test_inventory_normalizer_preserves_sql_looking_quoted_text(self):
        sql_text = "(ARRAY['a'::character varying])::text[]"
        for quoted in ("'" + sql_text.replace("'", "''") + "'", '"' + sql_text + '"',
                       "$quoted$" + sql_text + "$quoted$", "/* " + sql_text + " */", "-- " + sql_text):
            self.assertEqual(helper.normalize_inventory_definition(quoted), quoted)

    def test_expected_backfills_and_old_proof_expiration_pass(self):
        before, after = snapshots()
        result = helper.compare_snapshots(before, after, "migration")
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["owner_backfill_verified"])
        self.assertTrue(all(result["critical_values_preserved"].values()))

    def test_missing_owner_backfill_is_detected_even_when_legacy_digest_matches(self):
        before, after = snapshots()
        after["tables"]["ai_usage_budgets"] = table("ai_usage_budgets", migrated=True, mutate=lambda row: row.update(user_id=None))
        self.assertEqual(before["tables"]["ai_usage_budgets"]["migration_legacy_digest"], after["tables"]["ai_usage_budgets"]["migration_legacy_digest"])
        result = helper.compare_snapshots(before, after, "migration")
        self.assertIn("owner_backfill:ai_usage_budgets", result["failures"])

    def test_critical_value_or_user_id_changes_fail_without_exposing_values(self):
        before, after = snapshots()
        after["tables"]["payments"] = table("payments", migrated=True, mutate=lambda row: row.update(value="changed financial amount"))
        after["critical"]["billing"] = "different-digest"
        result = helper.compare_snapshots(before, after, "migration")
        self.assertFalse(result["ok"])
        self.assertIn("rows_changed:payments", result["failures"])
        self.assertFalse(result["critical_values_preserved"]["billing"])
        self.assertNotIn("private learner", json.dumps(before))
        self.assertNotIn("changed financial", json.dumps(result))

    def test_restore_requires_exact_rows_schema_heads_and_sequences(self):
        before, after = snapshots()
        for original in (before, after):
            self.assertTrue(helper.compare_snapshots(original, copy.deepcopy(original), "restore")["ok"])
            for field in ("sequence_digest", "schema_digest", "key_id", "account_keys_digest"):
                changed = copy.deepcopy(original)
                changed[field] = "changed"
                self.assertFalse(helper.compare_snapshots(original, changed, "restore")["ok"])
            changed = copy.deepcopy(original)
            changed["tables"]["users"]["full_digest"] = "changed"
            self.assertIn("rows_changed:users", helper.compare_snapshots(original, changed, "restore")["failures"])

    def test_unexpected_schema_change_and_owner_conflict_block(self):
        before, after = snapshots()
        after["column_schema"]["payments.user_telegram_id"] = {"type": "int8", "nullable": True}
        before["tables"]["trial_risk_events"]["owners"]["existing_owner_conflicts"] = 1
        failures = helper.compare_snapshots(before, after, "migration")["failures"]
        self.assertIn("unexpected_schema_columns", failures)
        self.assertIn("existing_owner_conflicts:trial_risk_events", failures)

    def test_removed_telegram_unique_index_dropped_progress_fk_and_changed_payment_default_fail(self):
        for kind, name in (("index_metadata", "users.ix_users_telegram_id"),
                           ("constraint_metadata", "course_progress.course_progress_user_id_fkey"),
                           ("column_metadata", "payments.value")):
            before, after = snapshots()
            if kind == "column_metadata":
                after[kind][name] = "changed-payment-default-or-width"
            else:
                del after[kind][name]
            with self.subTest(kind=kind):
                result = helper.compare_snapshots(before, after, "migration")
                self.assertFalse(result["ok"])
                self.assertTrue(any(name in failure for failure in result["failures"]), result)

    def test_only_targeted_not_null_constraints_may_disappear(self):
        before, after = snapshots()
        before["constraint_metadata"]["payments.payments_amount_not_null"] = {
            "kind": "n", "columns": ["amount"], "definition_digest": "must-remain"}
        result = helper.compare_snapshots(before, after, "migration")
        self.assertIn("legacy_constraint_changed:payments.payments_amount_not_null", result["failures"])

    def test_baseline_must_match_actual_production_inventory(self):
        before, after = snapshots()
        before["inventory_contract"] = False
        self.assertIn("baseline_schema_inventory_mismatch", helper.compare_snapshots(before, after, "migration")["failures"])

    def test_prospective_unique_constraint_duplicates_are_detected(self):
        summary = helper.TableSummary("course_miniapp_events", ["id", "user_id", "telegram_id", "event_name", "dedupe_key"],
                                      ["id", "user_id", "telegram_id", "event_name", "dedupe_key"], {1001: 7}, KEY, True)
        for row_id in (1, 2):
            summary.add({"id": row_id, "user_id": None, "telegram_id": 1001, "event_name": "opened", "dedupe_key": "same"})
        self.assertEqual(summary.finish()["owners"]["canonical_duplicate_groups"], 1)

    def test_multiset_digest_is_deterministic_and_duplicate_sensitive(self):
        values = [datetime(2026, 10, 16, tzinfo=timezone.utc), Decimal("12.00"), b"private"]
        one, reordered, duplicated = (helper.RowsDigest(KEY) for _ in range(3))
        for row in (values, [3]):
            one.add(row)
        for row in ([3], values):
            reordered.add(row)
        for row in (values, [3], [3]):
            duplicated.add(row)
        self.assertEqual(one.finish(), reordered.finish())
        self.assertNotEqual(one.finish(), duplicated.finish())
        self.assertNotEqual(helper.digest(KEY, values), helper.digest(b"different-key", values))


if __name__ == "__main__":
    unittest.main()
