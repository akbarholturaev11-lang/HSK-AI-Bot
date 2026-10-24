import hashlib
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.bot_setting import BotSetting


class BotSettingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def lock_key(self, key: str) -> None:
        """Serialize a setting's writers even before its first row exists.

        The transaction owns this PostgreSQL advisory lock until commit or
        rollback. Readers do not acquire it. Multi-key commands should acquire
        all their keys in sorted order before writing; callers retain their
        transaction's lock/statement timeout policy. SQLite already serializes
        writes and does not support PostgreSQL advisory locks.
        """
        get_bind = getattr(self.session, "get_bind", None)
        bind = get_bind() if get_bind else None
        if bind is None or bind.dialect.name != "postgresql":
            return
        # A fixed namespace avoids collisions with unrelated advisory-lock
        # users. Unlike hash(), this ID is stable across workers/restarts.
        digest = hashlib.sha256(("hskai.bot-setting.v1:" + key).encode()).digest()
        lock_id = int.from_bytes(digest[:8], "big", signed=True)
        await self.session.execute(text(
            "SELECT pg_advisory_xact_lock(CAST(:setting_lock_id AS BIGINT))"
        ), {"setting_lock_id": lock_id})

    async def get(self, key: str) -> Optional[str]:
        result = await self.session.execute(
            select(BotSetting.value).where(BotSetting.key == key)
        )
        return result.scalar_one_or_none()

    async def get_record(self, key: str) -> BotSetting | None:
        result = await self.session.execute(
            select(BotSetting).where(BotSetting.key == key)
        )
        return result.scalar_one_or_none()

    async def set(self, key: str, value: str) -> BotSetting:
        await self.lock_key(key)
        result = await self.session.execute(
            select(BotSetting).where(BotSetting.key == key)
            .execution_options(populate_existing=True)
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            setting = BotSetting(key=key, value=value)
            self.session.add(setting)
        await self.session.flush()
        return setting

    async def get_bool(self, key: str, default: bool = False) -> bool:
        value = await self.get(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    async def set_bool(self, key: str, value: bool) -> BotSetting:
        return await self.set(key, "1" if value else "0")
