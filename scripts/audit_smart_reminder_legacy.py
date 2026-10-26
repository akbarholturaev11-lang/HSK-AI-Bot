"""Read one synthetic/local QA account's legacy reminder evidence, never send.

Run from the project root with PYTHONPATH=.; supply the local QA URL through
SMART_REMINDER_AUDIT_DATABASE_URL, never a command argument. This command does
not read the application's settings/.env or initialize/migrate any database.
It refuses remote databases and uses a database-enforced read-only connection.
Production/staging observation still requires its own explicit authorization.
"""

import argparse
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.services.smart_reminder_legacy_evidence import (
    LegacyEvidenceUnavailable,
    SmartReminderLegacyEvidenceService,
)


class LocalAuditTargetError(ValueError):
    pass


def validate_local_target(value: str):
    try:
        url = make_url(value)
    except Exception:
        raise LocalAuditTargetError("audit_local_database_required") from None
    if url.drivername == "sqlite+aiosqlite":
        # No implicit creation of a missing/empty SQLite database. URI query
        # options are excluded so callers cannot override the reviewed mode.
        if url.query or not url.database or not Path(url.database).is_file():
            raise LocalAuditTargetError("audit_existing_local_sqlite_required")
    elif url.drivername == "postgresql+asyncpg":
        if url.host not in {"127.0.0.1", "localhost", "::1"} or url.query:
            raise LocalAuditTargetError("audit_local_database_required")
    else:
        raise LocalAuditTargetError("audit_local_database_required")
    return url


async def audit(url, user_id: int) -> dict:
    engine = create_async_engine(url, echo=False)
    try:
        async with engine.connect() as connection:
            if url.drivername == "sqlite+aiosqlite":
                await connection.execute(text("PRAGMA query_only = ON"))
            else:
                await connection.execute(text("SET TRANSACTION READ ONLY"))
            async with AsyncSession(bind=connection, autoflush=False) as session:
                evidence = await SmartReminderLegacyEvidenceService(session).snapshot(user_id)
                return asdict(evidence)
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True, type=int, help="Canonical users.id in a local QA database")
    args = parser.parse_args()
    try:
        url = validate_local_target(os.environ.get("SMART_REMINDER_AUDIT_DATABASE_URL", ""))
        report = asyncio.run(audit(url, args.user_id))
    except (LocalAuditTargetError, LegacyEvidenceUnavailable) as error:
        # Validation and service errors contain stable codes only. Never echo
        # the supplied URL, raw driver exception, provider token or private ID.
        print(str(error), file=sys.stderr)
        return 2
    except Exception:
        print("audit_database_unavailable", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
