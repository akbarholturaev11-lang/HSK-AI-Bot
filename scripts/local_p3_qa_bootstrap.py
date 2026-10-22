"""Fail-closed bootstrap for a disposable, Docker-network-only P3 QA database.

This is NOT the normal production migration entrypoint. Existing databases
must already be at the reviewed current Alembic head; unknown/partial schema
is never stamped, reset, upgraded or repaired by this script.
"""
from __future__ import annotations

import asyncio
import os

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from scripts.qa_standalone_bootstrap import (
    EXPECTED_BASELINE,
    EXPECTED_HEAD,
    _create_empty_orm_schema,
    _reviewed_alembic_config,
    verify_qa_tables,
)

QA_HOST = "postgres"
QA_DB = "hsk_p3_local_qa"
QA_USER = "hsk_p3_local_qa"
APPROVAL = "I_APPROVE_EMPTY_LOCAL_P3_QA"


def _validate() -> None:
    if os.environ.get("HSK_P3_LOCAL_QA_BOOTSTRAP") != APPROVAL:
        raise RuntimeError("local_p3_qa_explicit_approval_required")
    if any(os.environ.get(key) for key in (
        "RAILWAY_PROJECT_ID", "RAILWAY_ENVIRONMENT_NAME", "RAILWAY_VOLUME_MOUNT_PATH"
    )):
        raise RuntimeError("local_p3_qa_refuses_railway_environment")

    try:
        db = make_url(os.environ.get("DATABASE_URL", ""))
    except Exception as exc:
        raise RuntimeError("local_p3_qa_invalid_database_url") from exc
    if (
        db.drivername != "postgresql+asyncpg"
        or db.host != QA_HOST
        or db.port != 5432
        or db.database != QA_DB
        or db.username != QA_USER
        or not db.password
    ):
        raise RuntimeError("local_p3_qa_database_must_match_dedicated_docker_service")


async def _existing_tables() -> set[str]:
    from app.db.session import engine
    try:
        async with engine.connect() as conn:
            return set(await conn.run_sync(
                lambda sql_conn: inspect(sql_conn).get_table_names(schema="public")
            ))
    finally:
        await engine.dispose()


async def _verify_existing_head() -> None:
    from app.db.session import engine
    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(text("SELECT version_num FROM alembic_version"))
            ).scalars().all()
            if rows != [EXPECTED_HEAD]:
                raise RuntimeError("local_p3_qa_existing_schema_is_not_reviewed_head")
            required = {"users", "payments", "referrals", "course_progress", "user_identities"}
            tables = set(await conn.run_sync(
                lambda sql_conn: inspect(sql_conn).get_table_names(schema="public")
            ))
            if not required.issubset(tables):
                raise RuntimeError("local_p3_qa_missing_required_tables")
    finally:
        await engine.dispose()


def main() -> None:
    _validate()
    cfg = _reviewed_alembic_config()
    tables = asyncio.run(_existing_tables())
    if tables:
        if "alembic_version" not in tables:
            raise RuntimeError("local_p3_qa_existing_unversioned_db_refused")
        asyncio.run(_verify_existing_head())
        print("P3_LOCAL_QA_EXISTING_SCHEMA_PASS; HEAD=" + EXPECTED_HEAD)
        return

    from alembic import command
    # The target is a newly created, empty, private Docker postgres database.
    # Reuse the reviewed clean-ORM + historical-baseline approach, then run
    # formal migrations. On failure, quarantine rather than auto-retrying.
    asyncio.run(_create_empty_orm_schema())
    command.stamp(cfg, EXPECTED_BASELINE)
    command.upgrade(cfg, "head")
    asyncio.run(verify_qa_tables())
    print("P3_LOCAL_QA_NEW_SCHEMA_PASS; EMPTY_USERS; HEAD=" + EXPECTED_HEAD)


if __name__ == "__main__":
    main()
