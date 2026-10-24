"""ONE-TIME schema setup for a separate, empty Railway Universal QA project.

NEVER run this against production or the old staging project. This does not
import, clone, read or copy any learner data from anywhere. It first creates
an empty schema from the current ORM models, stamps the historical baseline
only on the NEW empty QA DB, then executes 0103..0121 and checks the head.

The historical Alembic base cannot create all course tables from scratch.
This explicitly isolated QA path is not a replacement for a production
migration. On any failure, quarantine DB for manual inspection; no retry
against partially initialized schema.
"""
from __future__ import annotations

import asyncio
import os

from sqlalchemy.engine import make_url

QA_PROJECT_ID = "7f737cb9-be6a-45cd-b6b3-8263b41d1cfd"
QA_ENVIRONMENT = "qa"
QA_HOST = "postgres.railway.internal"
QA_DATABASE = "railway"
EXPECTED_BASELINE = "0102_payment_review_preview"
EXPECTED_HEAD = "0124_admin_pwa_push_subscriptions"
# These reviewed migrations create tables unconditionally. Defer their DDL
# until after the empty ORM baseline is stamped; never precreate and then skip
# their migrations. This list is reviewed alongside EXPECTED_HEAD.
MIGRATION_CREATED_TABLES = frozenset({
    "public_site_traffic_daily", "admin_pwa_sessions", "admin_pwa_approvals",
    "admin_pwa_oauth_attempts", "admin_pwa_enrollment_grants",
    "admin_pwa_credentials", "admin_pwa_registration_challenges",
    "admin_pwa_authentication_challenges", "admin_pwa_step_ups",
    "admin_pwa_payment_reviews", "admin_pwa_payment_outbox",
    "admin_pwa_mcp_access_grants",
    "admin_pwa_mcp_authorizations",
    "admin_pwa_native_reports",
    "admin_pwa_inbox_triage", "admin_pwa_inbox_triage_audit",
    "admin_pwa_push_subscriptions",
    "admin_pwa_mcp_audit", "admin_pwa_mcp_quotas",
})


def _registered_model_metadata():
    from app.db import models  # noqa: F401
    from app.db.base import Base
    # Normal startup registers this through app.main. The isolated initializer
    # must also register it without importing the HTTP app or creating a bot.
    from app.db.models.notification_template import NotificationTemplate  # noqa: F401

    return Base.metadata


def validate_target(env: dict[str, str]) -> None:
    if env.get("RAILWAY_PROJECT_ID") != QA_PROJECT_ID:
        raise RuntimeError("standalone_qa_wrong_project")
    if env.get("RAILWAY_ENVIRONMENT_NAME") != QA_ENVIRONMENT:
        raise RuntimeError("standalone_qa_wrong_environment")
    if env.get("HSK_QA_EMPTY_DB_BOOTSTRAP") != "I_APPROVE_EMPTY_QA_DB":
        raise RuntimeError("standalone_qa_not_approved")
    try:
        parsed = make_url(env.get("DATABASE_URL", ""))
    except Exception as exc:
        raise RuntimeError("standalone_qa_invalid_database") from exc
    if (parsed.host or "").lower() != QA_HOST or parsed.database != QA_DATABASE:
        raise RuntimeError("standalone_qa_database_not_isolated")


async def ensure_database_empty() -> None:
    from sqlalchemy import inspect
    from app.db.session import engine
    async with engine.connect() as connection:
        existing = await connection.run_sync(
            lambda conn: inspect(conn).get_table_names(schema="public")
        )
    if existing:
        raise RuntimeError("standalone_qa_database_not_empty")


async def verify_qa_tables() -> None:
    from sqlalchemy import inspect, text
    from app.db.session import engine
    try:
        async with engine.connect() as con:
            tables = set(await con.run_sync(
                lambda conn: inspect(conn).get_table_names(schema="public")
            ))
            required = set(_registered_model_metadata().tables) | {"alembic_version"}
            if not required.issubset(tables):
                raise RuntimeError("standalone_qa_missing_schema_tables")
            version = (await con.execute(text("SELECT version_num FROM alembic_version"))).scalar()
            if version != EXPECTED_HEAD:
                raise RuntimeError("standalone_qa_bad_schema_revision")
            traffic_columns, traffic_primary_key = await con.run_sync(lambda conn: (
                inspect(conn).get_columns("public_site_traffic_daily", schema="public"),
                inspect(conn).get_pk_constraint("public_site_traffic_daily", schema="public"),
            ))
            if ({column["name"] for column in traffic_columns} != {"visit_day", "source", "visits"}
                    or any(column["nullable"] for column in traffic_columns)
                    or set(traffic_primary_key["constrained_columns"]) != {"visit_day", "source"}):
                raise RuntimeError("standalone_qa_bad_public_traffic_schema")
            for table in ("users", "payments", "referrals", "course_progress",
                          "user_identities", *sorted(MIGRATION_CREATED_TABLES)):
                n = (await con.execute(text(f"SELECT count(*) FROM {table}"))).scalar()
                if n != 0:
                    raise RuntimeError("standalone_qa_unexpected_user_rows")
    finally:
        await engine.dispose()


async def _create_empty_orm_schema() -> None:
    # The shared pool must be disposed before Alembic opens another event loop.
    from app.db.session import engine, _ensure_bootstrap_columns, _ensure_bootstrap_indexes
    try:
        await ensure_database_empty()
        metadata = _registered_model_metadata()
        async with engine.begin() as connection:
            await connection.run_sync(lambda conn: metadata.create_all(
                conn, tables=_initial_schema_tables(metadata),
            ))
            await _ensure_bootstrap_columns(connection)
            await _ensure_bootstrap_indexes(connection)
    finally:
        await engine.dispose()


def _initial_schema_tables(metadata):
    return [table for table in metadata.sorted_tables
            if table.name not in MIGRATION_CREATED_TABLES]


def _reviewed_alembic_config():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config("alembic.ini")
    if ScriptDirectory.from_config(config).get_heads() != [EXPECTED_HEAD]:
        raise RuntimeError("standalone_qa_unreviewed_schema_head")
    return config


def main() -> None:
    validate_target(dict(os.environ))
    from alembic import command
    cfg = _reviewed_alembic_config()
    asyncio.run(_create_empty_orm_schema())
    # QA ONLY. ORM-created tables model the latest empty schema; migration
    # 0103..0121 is then exercised to apply/refuse any missing constraints.
    command.stamp(cfg, EXPECTED_BASELINE)
    command.upgrade(cfg, "head")
    asyncio.run(verify_qa_tables())
    print("STANDALONE_QA_SCHEMA_PASS; NO_IMPORTED_ROWS; HEAD=" + EXPECTED_HEAD)


if __name__ == "__main__":
    main()
