"""ONE-TIME schema setup for a separate, empty Railway Universal QA project.

NEVER run this against production or the old staging project. This does not
import, clone, read or copy any learner data from anywhere. It first creates
an empty schema from the current ORM models, stamps the historical baseline
only on the NEW empty QA DB, then executes 0103..0108 and checks the head.

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
EXPECTED_HEAD = "0108_native_audit_ownership"


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
    async with engine.connect() as con:
        tables = set(await con.run_sync(
            lambda conn: inspect(conn).get_table_names(schema="public")
        ))
        required = {"users", "payments", "referrals", "course_progress",
                    "user_identities", "alembic_version"}
        if not required.issubset(tables):
            raise RuntimeError("standalone_qa_missing_schema_tables")
        version = (await con.execute(text("SELECT version_num FROM alembic_version"))).scalar()
        if version != EXPECTED_HEAD:
            raise RuntimeError("standalone_qa_bad_schema_revision")
        for table in ("users", "payments", "referrals", "course_progress"):
            n = (await con.execute(text(f"SELECT count(*) FROM {table}"))).scalar()
            if n != 0:
                raise RuntimeError("standalone_qa_unexpected_user_rows")


def main() -> None:
    validate_target(dict(os.environ))
    asyncio.run(ensure_database_empty())
    from app.db.session import init_db
    from alembic import command
    from alembic.config import Config
    asyncio.run(init_db())
    cfg = Config("alembic.ini")
    # QA ONLY. ORM-created tables model the latest empty schema; migration
    # 0102..0108 is then exercised to apply/refuse any missing constraints.
    command.stamp(cfg, EXPECTED_BASELINE)
    command.upgrade(cfg, "head")
    asyncio.run(verify_qa_tables())
    print("STANDALONE_QA_SCHEMA_PASS; NO_IMPORTED_ROWS; HEAD=" + EXPECTED_HEAD)


if __name__ == "__main__":
    main()
