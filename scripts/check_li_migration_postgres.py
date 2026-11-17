"""Rehearse the real Alembic 0153 -> 0154 DDL on an isolated CI PostgreSQL DB.

This script refuses production/non-local connections and never uses
DATABASE_URL for its test data. It creates a disposable database, seeds a
minimal genuine pre-0154 profile table, runs the project's actual Alembic
CLI revision, verifies preservation/constraints, and removes the database.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import asyncpg
from sqlalchemy.engine import make_url


async def _run() -> None:
    source = os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL", "")
    if not source or os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Migration rehearsal is CI-only and needs a disposable PostgreSQL service.")
    url = make_url(source)
    if (
        url.drivername != "postgresql+asyncpg"
        or url.host not in {"localhost", "127.0.0.1"}
        or url.database != "hsk_critical_test"
        or not url.port
        or url.port <= 1
        or os.environ.get("DATABASE_URL") != "postgresql+asyncpg://qa:qa@127.0.0.1:1/qa"
    ):
        raise SystemExit("Refusing to run migration rehearsal against an unapproved database.")

    name = f"hsk_li_migration_rehearsal_{os.getpid()}"
    params = dict(
        user=url.username, password=url.password,
        host=url.host, port=url.port,
    )
    admin = await asyncpg.connect(database=url.database, **params)
    created = False
    try:
        # The PG service is ephemeral; CREATE DATABASE requires the runner's
        # own service user, not the application's production credentials.
        await admin.execute(f'CREATE DATABASE "{name}"')
        created = True
        rehearsal = await asyncpg.connect(database=name, **params)
        try:
            await rehearsal.execute(
                """
                CREATE TABLE course_miniapp_profiles (
                    id INTEGER PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    goal VARCHAR(32) NOT NULL,
                    current_streak INTEGER NOT NULL,
                    xp INTEGER NOT NULL
                )
                """
            )
            await rehearsal.execute(
                "INSERT INTO course_miniapp_profiles "
                "(id, user_id, goal, current_streak, xp) "
                "VALUES (1, 42, 'hsk_exam', 6, 240)"
            )
        finally:
            await rehearsal.close()

        # New processes are intentional: app.config.settings imports the
        # exact isolated DATABASE_URL before the real env.py runs.
        new_url = url.set(database=name)
        env = os.environ.copy()
        env["DATABASE_URL"] = new_url.render_as_string(hide_password=False)
        for command in (
            ("stamp", "0153_pwa_inline_funnel"),
            ("upgrade", "0154_li_onboarding_choices"),
        ):
            subprocess.run(
                ["alembic", *command],
                env=env, check=True, timeout=120,
                stdout=sys.stdout, stderr=sys.stderr,
            )

        rehearsal = await asyncpg.connect(database=name, **params)
        try:
            revision = await rehearsal.fetchval(
                "SELECT version_num FROM alembic_version"
            )
            assert revision == "0154_li_onboarding_choices", revision
            cols = {
                row["column_name"]: (row["data_type"], row["is_nullable"])
                for row in await rehearsal.fetch(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'course_miniapp_profiles'"
                )
            }
            assert cols["goals_json"] == ("text", "YES"), cols
            assert cols["streak_target_days"] == ("integer", "YES"), cols
            row = await rehearsal.fetchrow(
                "SELECT user_id,goal,current_streak,xp,goals_json,streak_target_days "
                "FROM course_miniapp_profiles WHERE id=1"
            )
            assert tuple(row.values()) == (42, "hsk_exam", 6, 240, None, None), row
            assert await rehearsal.fetchval(
                "SELECT count(*) FROM pg_constraint WHERE conrelid = "
                "'course_miniapp_profiles'::regclass "
                "AND conname = 'ck_course_miniapp_profiles_streak_target_days'"
            ) == 1
            try:
                await rehearsal.execute(
                    "UPDATE course_miniapp_profiles SET streak_target_days=99 WHERE id=1"
                )
            except asyncpg.CheckViolationError:
                pass
            else:
                raise AssertionError("Streak target CHECK constraint did not reject 99")
            await rehearsal.execute(
                "UPDATE course_miniapp_profiles SET streak_target_days=14 WHERE id=1"
            )
            assert await rehearsal.fetchval(
                "SELECT streak_target_days FROM course_miniapp_profiles WHERE id=1"
            ) == 14
            assert await rehearsal.fetchval(
                "SELECT xp FROM course_miniapp_profiles WHERE id=1"
            ) == 240
            print("PASS: real PostgreSQL 0153->0154 upgrade; existing user data intact.")
        finally:
            await rehearsal.close()
    finally:
        try:
            if created:
                await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
        finally:
            await admin.close()


if __name__ == "__main__":
    asyncio.run(_run())
