"""Trusted operator queue; deletion requires the receipt AND expected account ID."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def run(args):
    from sqlalchemy import select
    from app.config import settings
    from app.db.models.account_deletion import AccountDeletionRequest
    from app.db.session import async_session_maker
    from app.services.account_deletion_service import AccountDeletionService, now, utc
    async with async_session_maker() as session:
        if args.command == "list":
            rows = (await session.scalars(select(AccountDeletionRequest).where(
                AccountDeletionRequest.status == "submitted",
                AccountDeletionRequest.active_user_id.is_not(None)
            ).order_by(AccountDeletionRequest.due_at))).all()
            print(json.dumps([{"request_id": r.id, "user_id": r.user_id,
                "provider": r.provider, "requested_at": utc(r.requested_at).isoformat(),
                "due_at": utc(r.due_at).isoformat(), "overdue": utc(r.due_at) < now()}
                for r in rows], indent=2))
        else:
            result = await AccountDeletionService(session, settings).process(
                request_id=args.request_id, expected_user_id=args.user_id)
            print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="Read pending queue; does not delete data")
    complete = sub.add_parser("complete", help="Process an explicitly confirmed request")
    complete.add_argument("--request-id", required=True)
    complete.add_argument("--user-id", type=int, required=True)
    complete.add_argument("--confirm", choices=["DELETE_ACCOUNT"], required=True)
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
