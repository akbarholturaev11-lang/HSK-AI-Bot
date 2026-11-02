"""Read one anonymous baseline month; never aggregate, migrate or send.

Run as a module from the repository root. Supply an explicit database URL via
SMART_REMINDER_BASELINE_DATABASE_URL, never a command argument. Application
settings/.env are not a target fallback. Database access remains the operator's
authorization boundary; output is the existing partial baseline projection.
"""
import argparse
import asyncio
from datetime import date
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote

from sqlalchemy import event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

REPORT_TIMEOUT = 10
TARGET_ENV = "SMART_REMINDER_BASELINE_DATABASE_URL"


class BaselineReportError(ValueError):
    pass


def month_argument(value):
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value):
        raise argparse.ArgumentTypeError("baseline_month_required")
    try:
        return date.fromisoformat(value + "-01")
    except ValueError:
        raise argparse.ArgumentTypeError("baseline_month_required") from None


def validate_target(value):
    if not value:
        raise BaselineReportError("baseline_database_target_required")
    try:
        url = make_url(value)
        if url.drivername == "sqlite+aiosqlite":
            path = Path(url.database or "")
            if (url.query or url.host or url.username or url.password or url.port or
                    not path.is_absolute() or not path.is_file()):
                raise ValueError
            # Driver mode=ro also closes the validation/open creation race.
            return URL.create("sqlite+aiosqlite", database="file:" + quote(str(path), safe="/"),
                query={"mode": "ro", "uri": "true"})
        if url.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
            raise ValueError
        if (not url.host or not url.database or (url.port is not None and not 1 <= url.port <= 65535)
                or set(url.query) - {"ssl"}
                or (url.query and url.query["ssl"] not in {"require", "verify-ca", "verify-full"})):
            raise ValueError
        return url.set(drivername="postgresql+asyncpg")
    except Exception:
        raise BaselineReportError("baseline_database_target_invalid") from None


def readonly_engine(target):
    if target.drivername == "postgresql+asyncpg":
        ssl = target.query.get("ssl", False if target.host in {"localhost", "127.0.0.1", "::1"} else "require")
        engine = create_async_engine(target.set(query={}), poolclass=NullPool, echo=False, hide_parameters=True,
            connect_args={"timeout": 3, "command_timeout": 5, "ssl": ssl,
                "server_settings": {"default_transaction_read_only": "on", "statement_timeout": "5000",
                    "lock_timeout": "1000", "application_name": "hsk-smart-baseline-readonly-v1"}})
    else:
        engine = create_async_engine(target, poolclass=NullPool, echo=False, hide_parameters=True,
            connect_args={"timeout": 1})
        @event.listens_for(engine.sync_engine, "connect")
        def query_only(connection, _):
            cursor = connection.cursor()
            try:
                cursor.execute("PRAGMA query_only = ON")
            finally:
                cursor.close()
    return engine


async def read_report(database_url, month):
    if type(month) is not date or month.day != 1:
        raise BaselineReportError("baseline_month_required")
    target = validate_target(database_url)

    async def perform():
        engine = readonly_engine(target)
        try:
            # No application session/config import, initializer or worker.
            from app.services.smart_reminder_baseline import SmartReminderBaselineService
            sessions = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)
            return await SmartReminderBaselineService(sessions).report(month)
        finally:
            await engine.dispose()
    return await asyncio.wait_for(perform(), timeout=REPORT_TIMEOUT)


class ReportParser(argparse.ArgumentParser):
    def error(self, message):
        # Unknown arguments may contain a mistakenly supplied credential URL.
        self.exit(2, "baseline_arguments_invalid\n")


def main(argv=None):
    parser = ReportParser(description=__doc__)
    parser.add_argument("--month", required=True, type=month_argument, metavar="YYYY-MM")
    args = parser.parse_args(argv)
    try:
        report = asyncio.run(read_report(os.environ.get(TARGET_ENV, ""), args.month))
    except BaselineReportError as error:
        print(str(error), file=sys.stderr)
        return 2
    except TimeoutError:
        print("baseline_report_timeout", file=sys.stderr)
        return 2
    except Exception:
        print("baseline_database_unavailable", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
