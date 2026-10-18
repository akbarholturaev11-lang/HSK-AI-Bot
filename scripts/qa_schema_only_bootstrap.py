"""Operator-only schema-only QA bootstrap from a VERIFIED staging 0102 copy.

Copies PostgreSQL schema, NOT learner rows, receipts, payment rows, token
records or sequence values. Not invoked on app startup or in CI.
Requires a separate *new* destination database and explicit confirmation.
"""
from __future__ import annotations
import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Mapping

EXPECTED_REVISION = "0102_payment_review_preview"
CONFIRM = "I_APPROVE_STAGING_SCHEMA_ONLY"
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{2,62}$")
HOST = re.compile(r"^[a-z0-9][a-z0-9-]*\.railway\.internal$")


class BootstrapError(Exception):
    """Never expose secrets or source personal information in errors."""


@dataclass(frozen=True)
class Settings:
    source_host: str
    source_db: str
    source_user: str
    source_password: str
    target_host: str
    target_db: str
    target_user: str
    target_password: str


def load_settings(env: Mapping[str, str]) -> Settings:
    if env.get("RAILWAY_ENVIRONMENT_NAME") != "staging":
        raise BootstrapError("not_staging")
    if env.get("QA_SCHEMA_ONLY_SOURCE_APPROVED") != EXPECTED_REVISION:
        raise BootstrapError("unapproved_baseline")
    names = ("QA_SOURCE_HOST", "QA_SOURCE_DB", "QA_SOURCE_USER", "QA_SOURCE_PASSWORD",
             "QA_TARGET_HOST", "QA_TARGET_DB", "QA_TARGET_USER", "QA_TARGET_PASSWORD")
    values = [env.get(k, "").strip() for k in names]
    if not all(values):
        raise BootstrapError("missing_credentials")
    c = Settings(*values)
    if not HOST.fullmatch(c.source_host.lower()) or not HOST.fullmatch(c.target_host.lower()):
        raise BootstrapError("host_not_private")
    if c.source_host.lower() == c.target_host.lower():
        raise BootstrapError("same_server")
    if any(not IDENTIFIER.fullmatch(v) for v in
           (c.source_db, c.target_db, c.source_user, c.target_user)):
        raise BootstrapError("unsafe_identifier")
    if c.target_db in {c.source_db, "postgres", "railway", "production"}:
        raise BootstrapError("unsafe_target")
    if not c.target_db.startswith("hsk_universal_qa_"):
        raise BootstrapError("not_qa_target")
    if any(word in h.lower() for h in (c.source_host, c.target_host)
           for word in ("production", "prod-", "live-", "primary-")):
        raise BootstrapError("unsafe_host")
    return c


def pg_env(c: Settings, source: bool) -> dict[str, str]:
    e = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    e.update(PGHOST=c.source_host if source else c.target_host,
             PGPORT="5432", PGUSER=c.source_user if source else c.target_user,
             PGPASSWORD=c.source_password if source else c.target_password,
             PGDATABASE=c.source_db if source else c.target_db, PGCONNECT_TIMEOUT="8")
    if source:
        e["PGOPTIONS"] = "-c default_transaction_read_only=on"
    return e


def scalar(command: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(command, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, timeout=30, check=False)
    if result.returncode:
        raise BootstrapError("query_failed")
    return result.stdout.strip()


def check(c: Settings) -> None:
    source = pg_env(c, True)
    if scalar(["psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1",
               "-c", "SELECT version_num FROM alembic_version"], source) != EXPECTED_REVISION:
        raise BootstrapError("revision_mismatch")
    if scalar(["psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1",
               "-c", "SELECT count(*) FROM alembic_version"], source) != "1":
        raise BootstrapError("revision_ambiguous")
    target_admin = pg_env(c, False) | {"PGDATABASE": "postgres"}
    exists = scalar(["psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-c",
                     "SELECT count(*) FROM pg_database WHERE datname='" + c.target_db + "'"],
                    target_admin)
    if exists != "0":
        raise BootstrapError("target_already_exists")


def copy_schema(c: Settings) -> None:
    check(c)
    dest = pg_env(c, False)
    subprocess.run(["createdb", "--template=template0", c.target_db],
                   env=dest | {"PGDATABASE": "postgres"},
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=60, check=True)
    # Custom archive schema-only mode cannot contain any table data.
    with subprocess.Popen(["pg_dump", "--format=custom", "--schema-only", "--no-owner",
                           "--no-acl"], env=pg_env(c, True),
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as dump:
        with subprocess.Popen(["pg_restore", "--no-owner", "--no-acl",
                               "--exit-on-error", "--dbname=" + c.target_db],
                              env=dest, stdin=dump.stdout, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL) as restore:
            assert dump.stdout is not None
            dump.stdout.close()
            if dump.wait(timeout=180) or restore.wait(timeout=180):
                raise BootstrapError("schema_copy_failed_target_quarantined")
    # This is the *only* inserted row: the verified schema's Alembic marker.
    scalar(["psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-c",
            "INSERT INTO alembic_version(version_num) VALUES ('" + EXPECTED_REVISION + "')"],
           dest)
    for table in ("users", "payments", "course_progress", "referrals"):
        if scalar(["psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1",
                   "-c", "SELECT count(*) FROM " + table], dest) != "0":
            raise BootstrapError("target_data_nonempty_quarantine")
    if scalar(["psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1",
               "-c", "SELECT version_num FROM alembic_version"], dest) != EXPECTED_REVISION:
        raise BootstrapError("target_revision_invalid")


def main(argv: list[str] | None = None, environ: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe staging QA schema-only bootstrap")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    env = os.environ if environ is None else environ
    try:
        config = load_settings(env)
        check(config)
        if not args.apply:
            print("QA_BASELINE_VALID; TARGET_ABSENT; NO_WRITES")
            return 0
        if env.get("QA_SCHEMA_ONLY_CONFIRM") != CONFIRM:
            raise BootstrapError("missing_operator_approval")
        copy_schema(config)
        print("QA_SCHEMA_ONLY_COPY_PASS; NO_LEARNER_ROWS; REVISION=" + EXPECTED_REVISION)
        return 0
    except (BootstrapError, subprocess.SubprocessError, OSError):
        print("QA_BOOTSTRAP_STOPPED; see private operator logs", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
