"""Read-only, aggregate AI ledger audit. No credentials or learner IDs in output.

Run: python -m scripts.audit_ai_costs --since 2026-07-21T00:00:00Z --until 2026-09-09T00:00:00Z
Works before and after the billing-tier migration. Never changes ledger/budgets.
"""

import argparse
import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine


def utc_date(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise argparse.ArgumentTypeError("Use an explicit timezone, e.g. 2026-07-21T00:00:00Z")
    return dt.astimezone(timezone.utc)


async def audit(connection, since, until):
    if connection.dialect.name == "postgresql":
        await connection.execute(text("SET TRANSACTION READ ONLY"))
    elif connection.dialect.name == "sqlite":
        await connection.execute(text("PRAGMA query_only = ON"))
    else:
        raise ValueError("Read-only audit supports PostgreSQL and SQLite")
    columns = await connection.run_sync(
        lambda conn: {c["name"] for c in inspect(conn).get_columns("ai_usage_events")}
    )
    tier = "billing_tier" if "billing_tier" in columns else "'legacy_estimate'"
    grouping = "model, source, billing_tier" if "billing_tier" in columns else "model, source"
    # Only the inspected column name/static literal is interpolated; dates are bound.
    rows = (await connection.execute(text(f"""
        SELECT model, source, {tier} AS tier, COUNT(*) AS requests,
               COALESCE(SUM(total_tokens), 0) AS tokens,
               COALESCE(SUM(cost_usd), 0) AS recorded_cost_usd,
               COUNT(DISTINCT budget_id) AS linked_budgets
        FROM ai_usage_events
        WHERE created_at >= :since AND created_at < :until
        GROUP BY {grouping}
        ORDER BY {grouping}
    """), {"since": since, "until": until})).mappings().all()
    return {
        "since": since.isoformat(), "until_exclusive": until.isoformat(),
        "rows": [dict(row) for row in rows],
        "notice": "Ledger estimates, not invoices. Confirm the historical free-tier dates before correcting Gemini costs or linked budgets. No writes performed.",
    }


async def run(args):
    from app.config import settings
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    try:
        async with engine.connect() as connection:
            async with connection.begin():
                result = await audit(connection, args.since, args.until)
        print(json.dumps(result, indent=2, default=str))
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", type=utc_date, required=True)
    parser.add_argument("--until", type=utc_date, required=True)
    args = parser.parse_args()
    if args.since >= args.until:
        parser.error("--since must be earlier than --until")
    try:
        asyncio.run(run(args))
    except Exception as exc:
        # DB exception strings can contain connection details; do not print them.
        parser.exit(1, f"Audit failed ({type(exc).__name__}); check DB access/schema locally. No credentials printed.\n")


if __name__ == "__main__":
    main()
