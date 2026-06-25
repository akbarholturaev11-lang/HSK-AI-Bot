import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select

from app.db.models.conversion_funnel_event import (
    CONVERSION_FUNNEL_EVENT_NAMES,
    ConversionFunnelEvent,
)
from app.db.session import async_session_maker


logger = logging.getLogger(__name__)


class ConversionFunnelService:
    EVENT_NAMES = CONVERSION_FUNNEL_EVENT_NAMES
    EVENT_LABELS = {
        "course_cta_seen": "CTA",
        "course_started": "Kurs",
        "lesson_started": "Dars",
        "quiz_completed": "Test",
        "ai_explanation_seen": "AI",
        "homework_completed": "Uy vazifa",
        "paywall_seen": "To'lov oynasi",
        "checkout_opened": "To'lov ochildi",
        "payment_screenshot_submitted": "Skrinshot",
        "payment_approved": "Tasdiq",
        "payment_rejected": "Rad",
    }
    RATE_PAIRS = (
        ("CTA → Kurs", "course_started", "course_cta_seen"),
        ("Kurs → Dars", "lesson_started", "course_started"),
        ("Dars → Test", "quiz_completed", "lesson_started"),
        ("Test → AI", "ai_explanation_seen", "quiz_completed"),
        ("AI → Uy vazifa", "homework_completed", "ai_explanation_seen"),
        ("To'lov oynasi → To'lov", "checkout_opened", "paywall_seen"),
        ("To'lov → Skrinshot", "payment_screenshot_submitted", "checkout_opened"),
        ("Skrinshot → Tasdiq", "payment_approved", "payment_screenshot_submitted"),
        ("Skrinshot → Rad", "payment_rejected", "payment_screenshot_submitted"),
    )

    def __init__(self, session=None):
        self.session = session

    @staticmethod
    def _pct(part: int, total: int) -> float:
        return round(part / total * 100, 1) if total > 0 else 0.0

    @staticmethod
    def _payload_json(payload: dict[str, Any] | None) -> str | None:
        if not payload:
            return None
        return json.dumps(payload, ensure_ascii=False, default=str)

    async def record(
        self,
        *,
        event_name: str,
        user=None,
        user_id: int | None = None,
        telegram_id: int | None = None,
        source: str | None = None,
        lesson_id: int | None = None,
        payment_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        if event_name not in self.EVENT_NAMES:
            logger.warning("Unknown conversion funnel event ignored: %s", event_name)
            return False

        if user is not None:
            user_id = getattr(user, "id", None) if user_id is None else user_id
            telegram_id = getattr(user, "telegram_id", None) if telegram_id is None else telegram_id

        if not telegram_id:
            logger.warning("Conversion funnel event skipped without telegram_id: %s", event_name)
            return False

        event = ConversionFunnelEvent(
            user_id=user_id,
            telegram_id=int(telegram_id),
            event_name=event_name,
            source=(source or None),
            lesson_id=lesson_id,
            payment_id=payment_id,
            payload_json=self._payload_json(payload),
            created_at=datetime.now(timezone.utc),
        )

        try:
            async with async_session_maker() as write_session:
                write_session.add(event)
                await write_session.commit()
            return True
        except Exception:
            logger.exception("Failed to record conversion funnel event: %s", event_name)
            return False

    async def has_event(
        self,
        *,
        telegram_id: int,
        event_name: str,
        source: str | None = None,
        lesson_id: int | None = None,
        payment_id: int | None = None,
    ) -> bool:
        if self.session is None:
            raise RuntimeError("has_event requires a read session")

        stmt = (
            select(func.count())
            .select_from(ConversionFunnelEvent)
            .where(
                ConversionFunnelEvent.telegram_id == telegram_id,
                ConversionFunnelEvent.event_name == event_name,
            )
        )
        if source is not None:
            stmt = stmt.where(ConversionFunnelEvent.source == source)
        if lesson_id is not None:
            stmt = stmt.where(ConversionFunnelEvent.lesson_id == lesson_id)
        if payment_id is not None:
            stmt = stmt.where(ConversionFunnelEvent.payment_id == payment_id)

        return bool((await self.session.execute(stmt)).scalar() or 0)

    async def counts_by_event(self, since: datetime | None = None) -> dict[str, int]:
        if self.session is None:
            raise RuntimeError("counts_by_event requires a read session")

        stmt = (
            select(ConversionFunnelEvent.event_name, func.count().label("cnt"))
            .select_from(ConversionFunnelEvent)
            .group_by(ConversionFunnelEvent.event_name)
        )
        if since is not None:
            stmt = stmt.where(ConversionFunnelEvent.created_at >= since)

        rows = (await self.session.execute(stmt)).fetchall()
        values = {str(row.event_name): int(row.cnt or 0) for row in rows}
        return {name: values.get(name, 0) for name in self.EVENT_NAMES}

    async def unique_users_by_event(self, since: datetime | None = None) -> dict[str, int]:
        if self.session is None:
            raise RuntimeError("unique_users_by_event requires a read session")

        stmt = (
            select(
                ConversionFunnelEvent.event_name,
                func.count(func.distinct(ConversionFunnelEvent.telegram_id)).label("cnt"),
            )
            .select_from(ConversionFunnelEvent)
            .group_by(ConversionFunnelEvent.event_name)
        )
        if since is not None:
            stmt = stmt.where(ConversionFunnelEvent.created_at >= since)

        rows = (await self.session.execute(stmt)).fetchall()
        values = {str(row.event_name): int(row.cnt or 0) for row in rows}
        return {name: values.get(name, 0) for name in self.EVENT_NAMES}

    async def admin_funnel_text(self, *, week_ago: datetime) -> str:
        all_unique = await self.unique_users_by_event()
        week_unique = await self.unique_users_by_event(since=week_ago)

        compact_rows = [
            ("course_cta_seen", "course_started", "lesson_started"),
            ("quiz_completed", "ai_explanation_seen", "homework_completed"),
            ("paywall_seen", "checkout_opened", "payment_screenshot_submitted"),
            ("payment_approved", "payment_rejected"),
        ]
        lines = ["<b>🧭 FUNNEL unique (all/7 kun)</b>"]
        for row in compact_rows:
            lines.append(
                "  "
                + " · ".join(
                    f"{self.EVENT_LABELS[name]}: <b>{all_unique[name]}</b>/<b>+{week_unique[name]}</b>"
                    for name in row
                )
            )

        rate_parts = [
            f"{label}: <b>{self._pct(all_unique[numerator], all_unique[denominator])}%</b>"
            for label, numerator, denominator in self.RATE_PAIRS
        ]
        lines.append("  Ko'rsatkichlar: " + " · ".join(rate_parts[:3]))
        lines.append("  To'lov: " + " · ".join(rate_parts[5:]))
        lines.append("  Rad = admin rad qilgan to'lov, checkout tashlab ketish emas.")
        return "\n".join(lines)
