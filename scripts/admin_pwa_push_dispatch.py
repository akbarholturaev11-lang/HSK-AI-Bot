"""Opt-in private Apple Web Push sender. Does not run on app startup.

Usage:
    python -m scripts.admin_pwa_push_dispatch --once --limit 10
    python -m scripts.admin_pwa_push_dispatch --loop --limit 10 --interval 60

Use a separate managed worker with ADMIN_PWA_PUSH_SEND_ENABLED=true.
No secret, endpoint, payload, user or student information is logged.
"""
import argparse
import asyncio
import json

from app.config import settings
from app.services.admin_pwa_push_dispatch import dispatch_batch, sender_config


async def run(*, session_factory, once=True, limit=10, interval=60, sleep=asyncio.sleep):
    if sender_config(settings) is None:
        return {"enabled": False, "claimed": 0}
    latest = None
    while True:
        latest = await dispatch_batch(session_factory, settings_obj=settings, limit=limit)
        if once or not latest["enabled"]:
            return latest
        await sleep(interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Process one bounded delivery batch (default)")
    mode.add_argument("--loop", action="store_true", help="Poll bounded batches until stopped")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    if not 1 <= args.limit <= 50 or not 30 <= args.interval <= 3600:
        parser.error("limit must be 1..50 and interval must be 30..3600")
    from app.db.session import async_session_maker, engine
    async def work():
        try:
            return await run(session_factory=async_session_maker, once=not args.loop,
                             limit=args.limit, interval=args.interval)
        finally:
            await engine.dispose()
    try:
        print(json.dumps(asyncio.run(work()), sort_keys=True))
    except Exception:
        # Intentionally no exception text: provider libraries can carry the
        # delivery endpoint, authorization header, user or HTTP response body.
        print(json.dumps({"ok": False, "error": "admin_pwa_push_worker_unavailable"}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
