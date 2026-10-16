"""Read-only evidence for a 0102 -> 0105 staging migration and backup restores.

This script never migrates, dumps, restores, or imports application settings.
Run ``snapshot`` on the isolated restored database before/after the operator's
migration, then ``compare --mode migration``. Compare each restored backup with
its own source snapshot using ``--mode restore``. Keep the same inventory and
random HMAC key for the whole rehearsal. All credentials are explicit env vars.

The approved-target env contains {"purpose":"staging","host":...,"port":...,
"database":...}; it must identify this exact destination. Production's URL is
required only to deny that endpoint. Reports contain counts/keyed digests, never
row values, account IDs, destination names, or connection URLs.
"""
import argparse
import asyncio
from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import parse_qsl, unquote, urlsplit


BASE_REVISION = "0102_payment_review_preview"
HEAD_REVISION = "0105_native_ai_voice_ownership"
FOUNDATION = {
    "account_notice_deliveries": "telegram_id",
    "conversion_funnel_events": "telegram_id",
    "course_ad_views": "user_telegram_id",
    "course_miniapp_events": "telegram_id",
    "course_user_notifications": "telegram_id",
    "trial_risk_events": "telegram_id",
}
AI_VOICE = {name: "user_telegram_id" for name in (
    "ai_usage_budgets", "ai_usage_events", "voice_practice_sessions")}
OWNERS = FOUNDATION | AI_VOICE
DEDUPE = {"course_miniapp_events": "event_name", "course_user_notifications": "key"}
NEW_UNIQUES = {table: ("uq_" + table + "_user_" + ("event" if field == "event_name" else "key") + "_dedupe",
                       ["user_id", field, "dedupe_key"]) for table, field in DEDUPE.items()}
ADDED_CONSTRAINTS = {table + "." + name for table, (name, fields) in NEW_UNIQUES.items()} | {
    table + ".fk_" + table + "_user_id" for table in AI_VOICE}
ADDED_INDEXES = {table + "." + name for table, (name, fields) in NEW_UNIQUES.items()} | {
    table + ".ix_" + table + "_user_id" for table in AI_VOICE}
NULLABLE = {("users", "telegram_id"), ("desktop_devices", "telegram_id")} | set(OWNERS.items())
CRITICAL = {
    "billing": ("users", "payments", "portfolio_transactions", "ai_usage_budgets"),
    "progress": ("course_progress", "course_attempts", "course_word_mastery"),
    "xp_rating": ("course_xp_events", "course_miniapp_profiles"),
}
IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


class RehearsalError(Exception):
    """A safe, static error code; never include database/row/exception text."""


def canonical(value):
    def encode(item):
        if isinstance(item, (datetime, date, time, Decimal)):
            return {"type": type(item).__name__, "value": str(item)}
        if isinstance(item, bytes):
            return {"type": "bytes", "value": item.hex()}
        raise RehearsalError("unsupported_database_type")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=encode).encode()


def digest(key, value):
    return hmac.new(key, canonical(value), hashlib.sha256).hexdigest()


def normalize_inventory_definition(definition):
    """Only PG18's proven distribution of a literal varchar[] -> text[] cast.

    pg_dump/reparse rewrites (ARRAY['a'::varchar])::text[] into
    ARRAY[('a'::varchar)::text]. Unbounded varchar/text literal conversion is
    lossless. Preserve every literal, operator and other cast, including widths.
    Quoted strings/identifiers/comments are consumed before any inner pattern.
    Live preservation digests deliberately do not use this normalizer.
    """
    literal = r"'(?:''|[^'])*'"
    item = literal + r"::character varying"
    distributed = r"\(" + item + r"\)::text"
    pattern = re.compile(
        r"(?:[Ee]'(?:\\.|''|[^'\\])*'|" + literal + r'|"(?:""|[^"])*"|'
        r"(?P<dollar>\$(?:[a-zA-Z_][a-zA-Z0-9_]*)?\$).*?(?P=dollar)|--[^\n]*|/\*.*?\*/)"
        r"|(?P<source>\(ARRAY\[" + item + r"(?:, " + item + r")*\]\)::text\[\])"
        r"|(?P<distributed>ARRAY\[" + distributed + r"(?:, " + distributed + r")*\])", re.S)
    def replace(match):
        if match.group("source") or match.group("distributed"):
            return "ARRAY[" + ", ".join(value + "::text" for value in re.findall(literal, match.group())) + "]"
        return match.group()
    return pattern.sub(replace, definition)


class RowsDigest:
    """Order-independent multiset digest; duplicate rows remain significant."""
    def __init__(self, key):
        self.key, self.rows = key, []

    def add(self, value):
        self.rows.append(digest(self.key, value))

    def finish(self):
        return digest(self.key, sorted(self.rows))


def endpoint(url):
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ("postgresql", "postgresql+asyncpg", "postgres"):
            raise ValueError()
        host, port, database = parsed.hostname, parsed.port, unquote(parsed.path[1:])
        if not host or not port or not database or not parsed.username or not parsed.password or parsed.fragment:
            raise ValueError()
        # asyncpg unquotes hosts; accepting an encoded alias could bypass the
        # production deny comparison or turn an approved name into localhost.
        if not all(re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                   for label in host.split(".")):
            raise ValueError()
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", database):
            raise ValueError()
        return host.lower(), port, database
    except (ValueError, TypeError):
        raise RehearsalError("explicit_postgres_endpoint_required") from None


def validate_destination(url, approved, production_url):
    actual = endpoint(url)
    production = endpoint(production_url)
    host = actual[0]
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise RehearsalError("local_or_ip_destination_refused")
    if "." not in host or host.endswith((".localhost", ".local", ".")) or host in ("localhost", "host.docker.internal"):
        raise RehearsalError("local_or_ambiguous_destination_refused")
    if actual[:2] == production[:2]:
        raise RehearsalError("production_endpoint_refused")
    if not isinstance(approved, dict) or set(approved) != {"purpose", "host", "port", "database"}:
        raise RehearsalError("explicit_staging_target_required")
    if approved["purpose"] != "staging" or type(approved["port"]) is not int:
        raise RehearsalError("explicit_staging_target_required")
    if actual != (approved["host"], approved["port"], approved["database"]):
        raise RehearsalError("unapproved_staging_destination")
    # Disallow libpq multi-host and alternate destination query parameters.
    if any(name.lower() in {"host", "hostaddr", "port", "dbname", "database", "service"}
           for name, value in parse_qsl(urlsplit(url).query)):
        raise RehearsalError("alternate_destination_refused")
    return actual


def validate_inventory(inventory):
    if inventory.get("read_only") is not True or inventory.get("alembic_revisions") != [BASE_REVISION]:
        raise RehearsalError("expected_readonly_baseline_inventory")
    tables = {}
    for column in inventory["columns"]:
        table, name = column["table_name"], column["column_name"]
        if not IDENTIFIER.fullmatch(table) or not IDENTIFIER.fullmatch(name):
            raise RehearsalError("invalid_inventory_identifier")
        tables.setdefault(table, []).append(name)
    required = {"users": {"id", "telegram_id", "payment_preview_available", "payment_preview_payment_id"}, "desktop_devices": {"telegram_id"},
                "desktop_link_requests": {"intent", "status"}}
    required |= {table: {"id", column} | ({"user_id"} if table in FOUNDATION else set())
                 for table, column in OWNERS.items()}
    for group in CRITICAL.values():
        for table in group:
            required.setdefault(table, set()).add("id")
    for table, columns in required.items():
        if not columns.issubset(tables.get(table, [])):
            raise RehearsalError("inventory_missing_migration_columns")
    return {table: sorted(columns) for table, columns in tables.items() if table != "alembic_version"}


def backup_fingerprint(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as backup:
        info = os.fstat(backup.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size == 0 or info.st_mode & 0o077:
            raise RehearsalError("backup_must_be_nonempty_private_regular_file")
        checksum = hashlib.sha256()
        for block in iter(lambda: backup.read(1024 * 1024), b""):
            checksum.update(block)
    return {"bytes": info.st_size, "sha256": checksum.hexdigest()}


class TableSummary:
    def __init__(self, table, columns, legacy_columns, users, key, expire_old_links):
        self.table, self.columns, self.legacy, self.users = table, columns, legacy_columns, users
        self.expire_old_links = expire_old_links
        self.full, self.raw, self.normal = (RowsDigest(key) for _ in range(3))
        self.actual_owner, self.expected_owner = RowsDigest(key), RowsDigest(key)
        self.count = self.backfillable = self.unresolved = self.owner_conflicts = 0
        self.dedupe = Counter()

    def add(self, row):
        self.count += 1
        self.full.add([row[name] for name in self.columns])
        original = {name: row[name] for name in self.legacy}
        self.raw.add(original)
        normalized = dict(original)
        if self.table in OWNERS:
            tid = row[OWNERS[self.table]]
            actual = row.get("user_id")
            matched = self.users.get(tid) if tid is not None else None
            expected = actual if actual is not None else matched
            self.backfillable += int(actual is None and matched is not None)
            self.unresolved += int(actual is None and tid is not None and matched is None)
            self.owner_conflicts += int(actual is not None and matched is not None and actual != matched)
            self.actual_owner.add([row["id"], actual])
            self.expected_owner.add([row["id"], expected])
            if "user_id" in normalized:
                normalized["user_id"] = expected
            if self.table in DEDUPE:
                values = (expected, row[DEDUPE[self.table]], row["dedupe_key"])
                if all(value is not None for value in values):
                    self.dedupe[values] += 1
        if self.table == "desktop_link_requests" and self.expire_old_links:
            if row["intent"] == "link" and row["status"] == "pending":
                normalized["status"] = "expired"
        self.normal.add(normalized)

    def finish(self):
        result = {"rows": self.count, "columns": self.columns, "full_digest": self.full.finish(),
                  "raw_legacy_digest": self.raw.finish(), "migration_legacy_digest": self.normal.finish()}
        if self.table in OWNERS:
            result["owners"] = {"actual_digest": self.actual_owner.finish(), "expected_digest": self.expected_owner.finish(),
                                "backfillable_rows": self.backfillable, "unresolved_legacy_rows": self.unresolved,
                                "existing_owner_conflicts": self.owner_conflicts,
                                "canonical_duplicate_groups": sum(count > 1 for count in self.dedupe.values())}
        return result


async def collect_snapshot(connection, inventory, key):
    legacy = validate_inventory(inventory)
    server_major = int(await connection.fetchval("SHOW server_version_num")) // 10000
    if server_major != int(inventory["server_version"].split(".")[0]):
        raise RehearsalError("production_server_major_mismatch")
    columns = [dict(row) for row in await connection.fetch("""
        SELECT table_name, column_name, data_type, udt_name, is_nullable, column_default,
               character_maximum_length, numeric_precision, numeric_scale,
               datetime_precision, interval_type, interval_precision,
               collation_name, domain_name, is_identity, identity_generation,
               identity_start, identity_increment, identity_maximum, identity_minimum,
               identity_cycle, is_generated, generation_expression
        FROM information_schema.columns WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position"""
    )]
    actual = {}
    for row in columns:
        if not IDENTIFIER.fullmatch(row["table_name"]) or not IDENTIFIER.fullmatch(row["column_name"]):
            raise RehearsalError("invalid_database_identifier")
        actual.setdefault(row["table_name"], []).append(row["column_name"])
    for table, names in legacy.items():
        if not set(names).issubset(actual.get(table, [])):
            raise RehearsalError("legacy_columns_missing")
    revisions = sorted(row[0] for row in await connection.fetch("SELECT version_num FROM public.alembic_version"))
    if revisions not in ([BASE_REVISION], [HEAD_REVISION]):
        raise RehearsalError("unexpected_migration_head")
    account_keys = await connection.fetch("SELECT id, telegram_id FROM public.users ORDER BY id")
    users = {row["telegram_id"]: row["id"] for row in account_keys if row["telegram_id"] is not None}
    tables = {}
    for table, names in actual.items():
        if table == "alembic_version":
            continue
        names = sorted(names)
        summary = TableSummary(table, names, legacy.get(table, []), users, key,
                               "bind_session_id" not in actual.get("desktop_link_requests", []))
        fields = ", ".join(f'"{name}"' for name in names)
        async for row in connection.cursor(f'SELECT {fields} FROM public."{table}"', prefetch=5000):
            summary.add(dict(row))
        tables[table] = summary.finish()
    constraints = [dict(row) for row in await connection.fetch("""
        SELECT c.relname AS table_name, con.conname AS name, con.contype::text AS type,
               pg_get_constraintdef(con.oid) AS definition,
               ARRAY(SELECT a.attname::text FROM unnest(con.conkey) WITH ORDINALITY AS k(attnum, position)
                     JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
                     ORDER BY k.position) AS columns
        FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public'
        ORDER BY c.relname, con.conname"""
    )]
    indexes = [dict(row) for row in await connection.fetch("SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname")]
    sequences = RowsDigest(key)
    for row in await connection.fetch("SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' ORDER BY sequencename"):
        name = row["sequencename"]
        if not IDENTIFIER.fullmatch(name):
            raise RehearsalError("invalid_sequence_identifier")
        state = await connection.fetchrow(f'SELECT last_value, is_called FROM public."{name}"')
        sequences.add([name, state["last_value"], state["is_called"]])
    schema = {row["table_name"] + "." + row["column_name"]:
              {"type": row["udt_name"], "nullable": row["is_nullable"] == "YES"} for row in columns}
    column_metadata = {row["table_name"] + "." + row["column_name"]:
                       digest(key, {name: value for name, value in row.items()
                                    if name not in ("table_name", "column_name", "is_nullable")}) for row in columns}
    constraint_metadata = {row["table_name"] + "." + row["name"]:
                           {"kind": row["type"], "columns": row["columns"],
                            "definition_digest": digest(key, row["definition"])} for row in constraints}
    index_metadata = {row["tablename"] + "." + row["indexname"]: digest(key, row["indexdef"]) for row in indexes}
    column_lookup = {(row["table_name"], row["column_name"]): row for row in columns}
    constraint_lookup = {(row["table_name"], row["name"]): row for row in constraints}
    index_lookup = {(row["tablename"], row["indexname"]): row["indexdef"] for row in indexes}
    migration_contract = all(schema.get(table + "." + name, {}).get("nullable") for table, name in NULLABLE)
    for name, length in (("language", 8), ("bind_session_id", 36), ("approved_identity_id", 36)):
        field = column_lookup.get(("desktop_link_requests", name), {})
        migration_contract &= field.get("udt_name") == "varchar" and field.get("is_nullable") == "YES"
        migration_contract &= field.get("character_maximum_length") == length and field.get("column_default") is None
    for table, (name, fields) in NEW_UNIQUES.items():
        constraint = constraint_lookup.get((table, name), {})
        migration_contract &= constraint.get("type") == "u" and constraint.get("columns") == fields
        migration_contract &= constraint.get("definition") == "UNIQUE (" + ", ".join(fields) + ")"
        migration_contract &= index_lookup.get((table, name)) == f'CREATE UNIQUE INDEX {name} ON public.{table} USING btree ({", ".join(fields)})'
    for table in AI_VOICE:
        migration_contract &= schema.get(table + ".user_id") == {"type": "int4", "nullable": True}
        migration_contract &= any(row["table_name"] == table and row["type"] == "f" and
                                  row["definition"] == "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE" for row in constraints)
        migration_contract &= column_lookup.get((table, "user_id"), {}).get("column_default") is None
        migration_contract &= index_lookup.get((table, "ix_" + table + "_user_id")) == f"CREATE INDEX ix_{table}_user_id ON public.{table} USING btree (user_id)"
    critical = {group: digest(key, {table: tables[table]["migration_legacy_digest"] for table in names})
                for group, names in CRITICAL.items()}
    preflight = [reason + ":" + table for table, summary in tables.items() if table in OWNERS
                 for reason in ("existing_owner_conflicts", "canonical_duplicate_groups") if summary["owners"][reason]]
    inventory_columns = {row["table_name"] + "." + row["column_name"]: row for row in inventory["columns"]}
    live_inventory_columns = {row["table_name"] + "." + row["column_name"]:
                              {name: row[name] for name in next(iter(inventory_columns.values()))} for row in columns}
    inventory_constraints = {row["table_name"] + "." + row["name"]: row for row in inventory["constraints"]}
    live_inventory_constraints = {row["table_name"] + "." + row["name"]:
                                 {name: row[name] for name in ("table_name", "name", "type", "definition")} for row in constraints}
    inventory_indexes = {row["tablename"] + "." + row["indexname"]: row for row in inventory["indexes"]}
    live_inventory_indexes = {row["tablename"] + "." + row["indexname"]: row for row in indexes}
    def normalized(objects, definition):
        return {name: row | {definition: normalize_inventory_definition(row[definition])} for name, row in objects.items()}
    inventory_constraints = normalized(inventory_constraints, "definition")
    live_inventory_constraints = normalized(live_inventory_constraints, "definition")
    inventory_indexes = normalized(inventory_indexes, "indexdef")
    live_inventory_indexes = normalized(live_inventory_indexes, "indexdef")
    inventory_mismatches = [category + ":" + name for category, expected, current in (
        ("column", inventory_columns, live_inventory_columns),
        ("constraint", inventory_constraints, live_inventory_constraints),
        ("index", inventory_indexes, live_inventory_indexes))
        for name in expected.keys() | current.keys() if expected.get(name) != current.get(name)]
    inventory_contract = not inventory_mismatches
    if revisions == [BASE_REVISION] and not inventory_contract:
        preflight.append("baseline_schema_inventory_mismatch")
    return {"format": 2, "read_only": True, "server_major": server_major,
            "key_id": digest(key, "rehearsal-key-id"), "sequence_digest": sequences.finish(),
            "account_keys_digest": digest(key, [list(row) for row in account_keys]),
            "inventory_digest": digest(key, inventory), "migration_head": revisions,
            "schema_digest": digest(key, [columns, constraints, indexes]), "column_schema": schema,
            "column_metadata": column_metadata, "constraint_metadata": constraint_metadata,
            "index_metadata": index_metadata, "inventory_contract": inventory_contract,
            "inventory_mismatches": sorted(inventory_mismatches),
            "migration_contract": bool(migration_contract), "tables": tables, "critical": critical,
            "preflight_blockers": preflight}


def compare_snapshots(before, after, mode):
    failures = []
    for name in ("format", "key_id", "inventory_digest", "server_major", "sequence_digest", "account_keys_digest"):
        if before[name] != after[name]:
            failures.append(name + "_mismatch")
    if mode == "migration":
        if before["migration_head"] != [BASE_REVISION] or after["migration_head"] != [HEAD_REVISION]:
            failures.append("migration_head")
        if not before["inventory_contract"]:
            failures.append("baseline_schema_inventory_mismatch")
        if not after["migration_contract"]:
            failures.append("migration_schema_contract")
        for column, schema in before["column_schema"].items():
            expected = dict(schema)
            if tuple(column.split(".")) in NULLABLE:
                expected["nullable"] = True
            if after["column_schema"].get(column) != expected:
                failures.append("legacy_schema_changed:" + column)
            if after["column_metadata"].get(column) != before["column_metadata"].get(column):
                failures.append("legacy_column_modifiers_changed:" + column)
        added = {"desktop_link_requests." + name for name in ("language", "bind_session_id", "approved_identity_id")}
        added |= {table + ".user_id" for table in AI_VOICE}
        if set(after["column_schema"]) != set(before["column_schema"]) | added:
            failures.append("unexpected_schema_columns")
        for name, definition in before["constraint_metadata"].items():
            table = name.split(".")[0]
            allowed_drop = definition["kind"] == "n" and len(definition["columns"]) == 1 and (table, definition["columns"][0]) in NULLABLE
            if not allowed_drop and after["constraint_metadata"].get(name) != definition:
                failures.append("legacy_constraint_changed:" + name)
        allowed_drops = {name for name, definition in before["constraint_metadata"].items()
                         if definition["kind"] == "n" and len(definition["columns"]) == 1
                         and (name.split(".")[0], definition["columns"][0]) in NULLABLE}
        if set(after["constraint_metadata"]) != (set(before["constraint_metadata"]) - allowed_drops) | ADDED_CONSTRAINTS:
            failures.append("unexpected_schema_constraints")
        for name, definition in before["index_metadata"].items():
            if after["index_metadata"].get(name) != definition:
                failures.append("legacy_index_changed:" + name)
        if set(after["index_metadata"]) != set(before["index_metadata"]) | ADDED_INDEXES:
            failures.append("unexpected_schema_indexes")
    else:
        for name in ("migration_head", "schema_digest"):
            if before[name] != after[name]:
                failures.append(name + "_mismatch")
    if before["tables"].keys() != after["tables"].keys():
        failures.append("table_set_changed")
    for table, original in before["tables"].items():
        current = after["tables"].get(table, {})
        field = "migration_legacy_digest" if mode == "migration" else "full_digest"
        if original["rows"] != current.get("rows") or original[field] != current.get(field):
            failures.append("rows_changed:" + table)
        if mode == "migration" and table in OWNERS:
            if original["owners"]["expected_digest"] != current.get("owners", {}).get("actual_digest"):
                failures.append("owner_backfill:" + table)
            if original["owners"]["canonical_duplicate_groups"]:
                failures.append("canonical_duplicates:" + table)
            if original["owners"]["existing_owner_conflicts"]:
                failures.append("existing_owner_conflicts:" + table)
    critical = {name: before["critical"][name] == after["critical"][name] for name in CRITICAL}
    if not all(critical.values()):
        failures.append("critical_values_changed")
    return {"ok": not failures, "mode": mode, "migration_head": after["migration_head"],
            "critical_values_preserved": critical, "failures": failures,
            "owner_backfill_verified": mode == "migration" and not any("owner_backfill:" in item for item in failures)}


def env_value(name):
    value = os.environ.get(name)
    if not value:
        raise RehearsalError("required_secure_environment_missing")
    return value


def write_report(path, report):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(report, output, indent=2, sort_keys=True)
        output.write("\n")


async def snapshot(args):
    import asyncpg
    url = env_value(args.database_url_env)
    approved = json.loads(env_value(args.approved_target_env))
    target = validate_destination(url, approved, env_value(args.production_url_env))
    key = env_value(args.digest_key_env).encode()
    if len(key) < 32:
        raise RehearsalError("digest_key_requires_32_random_bytes")
    inventory = json.loads(Path(args.schema_inventory).read_text())
    validate_inventory(inventory)
    backup = backup_fingerprint(args.backup)
    connection = await asyncpg.connect(url.replace("postgresql+asyncpg://", "postgresql://", 1), ssl="require",
                                      timeout=30, server_settings={"application_name": "hsk-staging-rehearsal", "statement_timeout": "120000"})
    try:
        async with connection.transaction(isolation="repeatable_read", readonly=True):
            await connection.execute("SET LOCAL TIME ZONE 'UTC'")
            await connection.execute("SET LOCAL DateStyle = 'ISO, YMD'")
            if await connection.fetchval("SELECT current_database()") != target[2]:
                raise RehearsalError("connected_database_mismatch")
            if await connection.fetchval("SHOW transaction_read_only") != "on":
                raise RehearsalError("readonly_transaction_required")
            report = await collect_snapshot(connection, inventory, key)
    finally:
        await connection.close()
    report["backup"] = backup
    write_report(args.output, report)
    return {"ok": not report["preflight_blockers"], "read_only": True,
            "migration_head": report["migration_head"], "table_count": len(report["tables"]),
            "preflight_blockers": report["preflight_blockers"]}


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise RehearsalError("invalid_arguments")


def main(argv=None):
    parser = SafeParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("snapshot")
    for name in ("database-url-env", "approved-target-env", "production-url-env", "digest-key-env", "schema-inventory", "backup", "output"):
        capture.add_argument("--" + name, required=True)
    compare = commands.add_parser("compare")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    compare.add_argument("--mode", choices=("migration", "restore"), required=True)
    compare.add_argument("--output", required=True)
    try:
        args = parser.parse_args(argv)
        if args.command == "snapshot":
            report = asyncio.run(snapshot(args))
        else:
            report = compare_snapshots(json.loads(Path(args.before).read_text()), json.loads(Path(args.after).read_text()), args.mode)
            write_report(args.output, report)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["ok"] else 1
    except RehearsalError as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        return 2
    except Exception:
        # Driver/file/parser exceptions can contain credentials or learner data.
        print(json.dumps({"ok": False, "error": "rehearsal_failed_details_suppressed"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
