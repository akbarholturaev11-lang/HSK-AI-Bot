import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.db.session import async_session_maker
from app.repositories.user_repo import UserRepository


async def delete_user(telegram_id: int):
    if telegram_id in settings.admin_id_list:
        print(f"Refusing to delete admin user {telegram_id}.")
        return

    async with async_session_maker() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(telegram_id)
        if not user:
            print(f"User {telegram_id} not found.")
            return

        print(f"Found: id={user.id}, name={user.full_name}")

        deleted = await repo.delete_by_telegram_id(telegram_id)
        if not deleted:
            await session.rollback()
            print(f"User {telegram_id} disappeared before deletion.")
            return

        await session.commit()
        print(
            f"Deleted user {telegram_id}: account data purged; "
            "system financial ledger preserved without user linkage."
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/delete_user.py TELEGRAM_ID")
    asyncio.run(delete_user(int(sys.argv[1])))
