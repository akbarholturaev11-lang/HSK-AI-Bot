import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.db.models.course_miniapp_event import (
    CLIENT_COURSE_MINIAPP_EVENT_NAMES,
    COURSE_MINIAPP_EVENT_NAMES,
    CourseMiniAppEvent,
)
from app.db.models.user import User


MAX_EVENT_PAYLOAD_CHARS = 8000
logger = logging.getLogger(__name__)


class CourseMiniAppAnalyticsService:
    CLIENT_EVENT_NAMES = frozenset(CLIENT_COURSE_MINIAPP_EVENT_NAMES)

    def __init__(self, session):
        self.session = session

    @staticmethod
    def _payload_json(payload: dict[str, Any] | None) -> str | None:
        if not payload:
            return None
        encoded = json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":"))
        if len(encoded) <= MAX_EVENT_PAYLOAD_CHARS:
            return encoded
        return json.dumps(
            {"truncated": True, "preview": encoded[: MAX_EVENT_PAYLOAD_CHARS - 80]},
            ensure_ascii=False,
            separators=(",", ":"),
        )

    async def _record(
        self,
        *,
        event_name: str,
        telegram_id: int,
        user_id: int | None = None,
        source: str = "course_miniapp",
        level: str | None = None,
        lesson_id: int | None = None,
        lesson_order: int | None = None,
        session_id: str | None = None,
        dedupe_key: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict:
        event_name = str(event_name or "").strip()
        if event_name not in COURSE_MINIAPP_EVENT_NAMES:
            return {"ok": False, "error": "course_event_not_allowed"}
        if not telegram_id:
            return {"ok": False, "error": "course_event_user_required"}

        # Mini App'dagi har qanday haqiqiy faollik ham "aktiv" deb hisoblansin.
        # (Bot chat last_active_at'ni middleware yangilaydi; Mini App esa
        # FastAPI orqali kelgani uchun shu yerda yangilanadi.)
        await self._touch_user_active(telegram_id)

        source = str(source or "course_miniapp").strip()[:40] or "course_miniapp"
        level = (str(level).strip()[:32] if level else None) or None
        session_id = (str(session_id).strip()[:80] if session_id else None) or None
        dedupe_key = (str(dedupe_key).strip()[:120] if dedupe_key else None) or None

        if dedupe_key:
            existing_result = await self.session.execute(
                select(CourseMiniAppEvent.id).where(
                    CourseMiniAppEvent.telegram_id == int(telegram_id),
                    CourseMiniAppEvent.event_name == event_name,
                    CourseMiniAppEvent.dedupe_key == dedupe_key,
                )
            )
            if existing_result.scalar_one_or_none():
                return {"ok": True, "recorded": False, "duplicate": True}

        item = CourseMiniAppEvent(
            user_id=user_id,
            telegram_id=int(telegram_id),
            event_name=event_name,
            source=source,
            level=level,
            lesson_id=lesson_id,
            lesson_order=lesson_order,
            session_id=session_id,
            dedupe_key=dedupe_key,
            payload_json=self._payload_json(payload),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(item)
                await self.session.flush()
        except IntegrityError:
            if dedupe_key:
                duplicate_result = await self.session.execute(
                    select(CourseMiniAppEvent.id).where(
                        CourseMiniAppEvent.telegram_id == int(telegram_id),
                        CourseMiniAppEvent.event_name == event_name,
                        CourseMiniAppEvent.dedupe_key == dedupe_key,
                    )
                )
                if duplicate_result.scalar_one_or_none():
                    return {"ok": True, "recorded": False, "duplicate": True}
            raise
        return {"ok": True, "recorded": True, "duplicate": False}

    async def _touch_user_active(self, telegram_id: int) -> None:
        try:
            await self.session.execute(
                update(User)
                .where(User.telegram_id == int(telegram_id))
                .values(last_active_at=datetime.now(timezone.utc))
            )
        except Exception:
            logger.exception("Failed to update last_active_at for %s", telegram_id)

    async def record_client_event(self, **kwargs) -> dict:
        if kwargs.get("event_name") not in self.CLIENT_EVENT_NAMES:
            return {"ok": False, "error": "course_client_event_not_allowed"}
        return await self._record_safely(**kwargs)

    async def record_server_event(self, **kwargs) -> dict:
        return await self._record_safely(**kwargs)

    async def _record_safely(self, **kwargs) -> dict:
        try:
            return await self._record(**kwargs)
        except Exception:
            logger.exception("Failed to record Course Mini App event: %s", kwargs.get("event_name"))
            await self.session.rollback()
            return {"ok": False, "recorded": False, "error": "course_event_write_failed"}
