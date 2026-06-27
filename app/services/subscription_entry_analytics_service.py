from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from html import escape

from sqlalchemy import func, select

from app.db.models.subscription_entry_event import SubscriptionEntryEvent


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubscriptionSourceStats:
    source: str
    label: str
    total_all: int
    unique_all: int
    total_week: int
    unique_week: int


class SubscriptionEntryAnalyticsService:
    SOURCE_LABELS = {
        "command_subscription": "/subscription",
        "menu_subscription": "Menyu -> Obuna",
        "profile_subscription": "Profil -> Obuna",
        "subscription_open": "Obuna callback",
        "qa_limit": "QA limit",
        "qa_daily_limit": "QA kunlik limit",
        "voice_required": "Voice limit",
        "voice_translator": "Voice translator",
        "voice_transcribe": "Voice transcribe",
        "course_locked": "Kurs paywall",
        "course_expired": "Kurs obunasi tugagan",
        "course_trial_completed": "Kurs trial tugadi",
        "trial_soft_paywall": "Trial soft paywall",
        "study_miniapp": "Kurs Mini App",
        "v3_profile": "Course v3 — Profil",
        "v3_paywall": "Course v3 — Paywall",
        "v3_locked_lesson": "Course v3 — Qulflangan dars",
        "v3_level_up": "Course v3 — Daraja oshdi",
        "course_voice": "Kurs voice",
        "admin_discount": "Admin chegirma",
        "release_feedback_try": "Release feedback",
        "payment_rejected": "Rad to'lov qayta urinish",
        "photo_limit": "Foto limit",
        "daily_limit": "Daily limit",
        "required_channel_course": "Kanal checkpoint -> Kurs",
        "unknown": "Noma'lum",
    }

    def __init__(self, session):
        self.session = session

    @classmethod
    def normalize_source(cls, source: str | None) -> str:
        raw = str(source or "").strip().lower()
        if not raw:
            return "unknown"
        normalized = re.sub(r"[^a-z0-9_.:-]+", "_", raw).strip("_")
        return (normalized or "unknown")[:80]

    @classmethod
    def normalize_mode(cls, mode: str | None) -> str:
        raw = str(mode or "").strip().lower()
        normalized = re.sub(r"[^a-z0-9_.:-]+", "_", raw).strip("_")
        return (normalized or "subscription")[:40]

    @classmethod
    def source_label(cls, source: str) -> str:
        normalized = cls.normalize_source(source)
        if normalized in cls.SOURCE_LABELS:
            return cls.SOURCE_LABELS[normalized]
        return normalized.replace("_", " ").replace("miniapp", "Mini App").title()

    async def record_entry(
        self,
        *,
        telegram_id: int,
        user=None,
        source: str | None = None,
        mode: str | None = None,
        plan_type: str | None = None,
        payment_method: str | None = None,
        campaign_id: int | None = None,
        feedback_id: int | None = None,
    ) -> bool:
        if not telegram_id:
            return False

        event = SubscriptionEntryEvent(
            user_id=getattr(user, "id", None),
            telegram_id=int(telegram_id),
            source=self.normalize_source(source),
            mode=self.normalize_mode(mode),
            plan_type=(str(plan_type).strip()[:32] if plan_type else None),
            payment_method=(str(payment_method).strip()[:16] if payment_method else None),
            campaign_id=campaign_id,
            feedback_id=feedback_id,
        )

        try:
            self.session.add(event)
            await self.session.commit()
            return True
        except Exception:
            logger.exception("Failed to record subscription entry event")
            try:
                await self.session.rollback()
            except Exception:
                logger.exception("Failed to rollback subscription entry event")
            return False

    async def _counts_by_source(self, *, since: datetime | None = None) -> dict[str, tuple[int, int]]:
        stmt = (
            select(
                SubscriptionEntryEvent.source,
                func.count().label("total"),
                func.count(func.distinct(SubscriptionEntryEvent.telegram_id)).label("unique_users"),
            )
            .select_from(SubscriptionEntryEvent)
            .group_by(SubscriptionEntryEvent.source)
        )
        if since is not None:
            stmt = stmt.where(SubscriptionEntryEvent.created_at >= since)

        rows = (await self.session.execute(stmt)).fetchall()
        return {
            str(row.source or "unknown"): (
                int(row.total or 0),
                int(row.unique_users or 0),
            )
            for row in rows
        }

    async def source_stats(self, *, week_ago: datetime, limit: int = 8) -> list[SubscriptionSourceStats]:
        all_counts = await self._counts_by_source()
        week_counts = await self._counts_by_source(since=week_ago)
        sources = set(all_counts) | set(week_counts)

        rows = [
            SubscriptionSourceStats(
                source=source,
                label=self.source_label(source),
                total_all=all_counts.get(source, (0, 0))[0],
                unique_all=all_counts.get(source, (0, 0))[1],
                total_week=week_counts.get(source, (0, 0))[0],
                unique_week=week_counts.get(source, (0, 0))[1],
            )
            for source in sources
        ]
        rows.sort(
            key=lambda item: (
                item.unique_week,
                item.total_week,
                item.unique_all,
                item.total_all,
            ),
            reverse=True,
        )
        return rows[:limit]

    async def admin_text(self, *, week_ago: datetime, limit: int = 8) -> str:
        rows = await self.source_stats(week_ago=week_ago, limit=limit)
        lines = ["<b>💎 OBUNA MANBALARI</b>"]
        if not rows:
            lines.append("  hali yo'q")
            return "\n".join(lines)

        for row in rows:
            lines.append(
                f"  {escape(row.label)}: "
                f"user <b>{row.unique_all}</b>/<b>+{row.unique_week}</b> · "
                f"kirish <b>{row.total_all}</b>/<b>+{row.total_week}</b>"
            )
        return "\n".join(lines)
