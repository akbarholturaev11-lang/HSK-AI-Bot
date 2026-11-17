"""lava.top connection preflight (read-only unless --test-invoice-email).

Uses LAVA_* settings from the environment / .env and the stored Admin PWA
config. Prints OK/FAIL per check; never prints secrets.

    python scripts/lava_preflight.py
    python scripts/lava_preflight.py --test-invoice-email owner@example.com
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--test-invoice-email", default=None,
                        help="also create one unpaid invoice to prove checkout rights")
    parser.add_argument("--no-db", action="store_true",
                        help="skip reading the stored Admin PWA config (catalog checks only)")
    args = parser.parse_args()

    from app.config import settings
    from app.services.lava.client import LavaClient
    from app.services.lava.config import LavaConfig, LavaConfigService
    from app.services.lava.preflight import run_preflight

    config = LavaConfig()
    if not args.no_db:
        from app.db.session import async_session_maker
        async with async_session_maker() as session:
            config = await LavaConfigService(session).load()
    client = (LavaClient(api_key=settings.LAVA_API_KEY, base_url=settings.LAVA_API_BASE)
              if settings.LAVA_API_KEY else None)
    report = await run_preflight(client, config, settings_obj=settings,
                                 test_invoice_email=args.test_invoice_email)
    for check in report.checks:
        print(("OK   " if check.ok else "FAIL ") + check.code + (f" · {check.detail}" if check.detail else ""))
    print(json.dumps({"offers": report.offers}, ensure_ascii=False, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
