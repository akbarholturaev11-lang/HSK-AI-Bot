"""Operator-only expiry cleanup. Defaults to count-only; no app startup/import."""
import argparse
import asyncio
import json

from sqlalchemy import func, select, text

from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.services.admin_pwa_native_reports import purge_expired_native_reports
from datetime import datetime, timezone


async def run(session_factory, *, execute=False, limit=100):
    now = datetime.now(timezone.utc)
    async with session_factory() as db:
        async with db.begin():
            if db.get_bind().dialect.name == "postgresql":
                await db.execute(text("SET LOCAL statement_timeout = '5000'"))
            expired = int(await db.scalar(select(func.count()).select_from(AdminPwaNativeReport)
                .where(AdminPwaNativeReport.expires_at <= now)) or 0)
            removed = await purge_expired_native_reports(db, now=now, limit=limit) if execute else 0
    return {"expired_before": expired, "removed": removed, "remaining_expired": expired-removed,
            "mode": "purge" if execute else "count_only"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purge-expired", action="store_true", help="Physically delete one expired batch")
    parser.add_argument("--limit", type=int, default=100, choices=range(1, 1001), metavar="1..1000")
    args = parser.parse_args()
    from app.db.session import async_session_maker, engine
    async def work():
        try:
            print(json.dumps(await run(async_session_maker, execute=args.purge_expired, limit=args.limit)))
        finally:
            await engine.dispose()
    asyncio.run(work())


if __name__ == "__main__":
    main()
