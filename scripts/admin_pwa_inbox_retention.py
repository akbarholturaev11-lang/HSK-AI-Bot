"""Operator-only bounded orphan metadata sweep; defaults to a read-only dry run."""
import argparse
import asyncio
import json

from sqlalchemy import text
from app.services.admin_pwa_inbox_retention import SOURCE_MODELS,scan_orphaned_inbox_triage


async def run(session_factory,*,execute=False,limit=100,after=None):
    async with session_factory() as db:
        async with db.begin():
            if db.get_bind().dialect.name=='postgresql':
                await db.execute(text("SET LOCAL statement_timeout = '5000'"))
                await db.execute(text("SET LOCAL lock_timeout = '2000'"))
                if not execute:await db.execute(text('SET TRANSACTION READ ONLY'))
            return await scan_orphaned_inbox_triage(db,execute=execute,limit=limit,after=after)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--purge-orphans',action='store_true',help='Delete one bounded orphan metadata page')
    parser.add_argument('--limit',type=int,choices=range(1,1001),default=100,metavar='1..1000')
    parser.add_argument('--after-source',choices=tuple(SOURCE_MODELS))
    parser.add_argument('--after-id',type=int)
    args=parser.parse_args()
    if (args.after_source is None)!=(args.after_id is None) or (args.after_id is not None and not 0<args.after_id<=2_147_483_647):
        parser.error('--after-source and --after-id must be supplied together with a positive bounded ID')
    after=(args.after_source,args.after_id) if args.after_source else None
    from app.db.session import async_session_maker,engine
    async def work():
        try:print(json.dumps(await run(async_session_maker,execute=args.purge_orphans,limit=args.limit,after=after)))
        finally:await engine.dispose()
    asyncio.run(work())


if __name__=='__main__':main()
