"""Bounded cleanup of expired PWA staging metadata, never retained payout proofs."""
import argparse
import asyncio
import json
from datetime import datetime,timezone
from sqlalchemy import select,text
from app.admin_api.pwa_payout_completion import purge_expired_proofs
from app.db.models.admin_pwa_payout_proof import AdminPwaPayoutProof


async def run(session_factory, *, execute=False, limit=100):
    if type(limit) is not int or not 1<=limit<=1000:raise ValueError('Invalid bounded proof expiry page')
    now=datetime.now(timezone.utc)
    async with session_factory() as db:
        async with db.begin():
            if db.get_bind().dialect.name=='postgresql':
                await db.execute(text("SET LOCAL statement_timeout = '5000'"))
                if not execute:await db.execute(text('SET TRANSACTION READ ONLY'))
            if execute:return {'removed':await purge_expired_proofs(db,limit=limit,now=now),'mode':'purge'}
            keys=(await db.scalars(select(AdminPwaPayoutProof.id).where(AdminPwaPayoutProof.expires_at<=now)
                .order_by(AdminPwaPayoutProof.expires_at,AdminPwaPayoutProof.id).limit(limit))).all()
    return {'candidates_in_page':len(keys),'page_full':len(keys)==limit,'removed':0,'mode':'dry_run'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--purge-expired',action='store_true')
    parser.add_argument('--limit',type=int,choices=range(1,1001),default=100,metavar='1..1000')
    args=parser.parse_args()
    from app.db.session import async_session_maker,engine
    async def work():
        try:print(json.dumps(await run(async_session_maker,execute=args.purge_expired,limit=args.limit)))
        finally:await engine.dispose()
    asyncio.run(work())


if __name__=='__main__':main()
