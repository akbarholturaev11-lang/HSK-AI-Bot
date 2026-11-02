"""Explicit analysis-only cleanup; defaults to anonymous counts, never startup."""
import argparse
import asyncio
import json

from app.services.smart_reminder_analysis import SmartReminderAnalysisService


async def run(session_factory, *, execute=False, limit=128):
    return await SmartReminderAnalysisService(session_factory).retention(execute=execute, limit=limit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purge-expired", action="store_true", help="Remove one expired analysis-only page")
    parser.add_argument("--limit", type=int, default=128)
    args = parser.parse_args()

    async def perform():
        from app.db.session import async_session_maker, engine
        try:
            print(json.dumps(await run(async_session_maker, execute=args.purge_expired, limit=args.limit)))
        finally:
            await engine.dispose()
    asyncio.run(perform())


if __name__ == "__main__":
    main()
