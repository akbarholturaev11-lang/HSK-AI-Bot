from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert

from app.db.models.public_site_traffic import (
    PUBLIC_SITE_TRAFFIC_SOURCES,
    PublicSiteTrafficDaily,
)


SOURCE_LABELS = {
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "youtube": "YouTube",
    "other": "Бошқа манба",
}


def normalize_public_site_source(source: str | None) -> str | None:
    value = str(source or "").strip().lower()
    if not value:
        return None
    if value in {"instagram", "ig", "insta"}:
        return "instagram"
    if value in {"tiktok", "tik_tok"}:
        return "tiktok"
    if value in {"youtube", "you_tube", "yt"}:
        return "youtube"
    return "other"


class PublicSiteAnalyticsService:
    def __init__(self, session):
        self.session = session

    async def record_source_visit(self, source: str, *, today: date | None = None) -> None:
        visit_day = today or datetime.now(timezone.utc).date()
        statement = insert(PublicSiteTrafficDaily).values(
            visit_day=visit_day,
            source=source,
            visits=1,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[PublicSiteTrafficDaily.visit_day, PublicSiteTrafficDaily.source],
            set_={"visits": PublicSiteTrafficDaily.visits + 1},
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def source_stats(self, *, today: date | None = None) -> list[dict]:
        current_day = today or datetime.now(timezone.utc).date()
        week_start = current_day - timedelta(days=6)
        month_start = current_day - timedelta(days=29)
        statement = (
            select(
                PublicSiteTrafficDaily.source,
                func.sum(
                    case(
                        (PublicSiteTrafficDaily.visit_day >= week_start, PublicSiteTrafficDaily.visits),
                        else_=0,
                    )
                ).label("visits_7_days"),
                func.sum(
                    case(
                        (PublicSiteTrafficDaily.visit_day >= month_start, PublicSiteTrafficDaily.visits),
                        else_=0,
                    )
                ).label("visits_30_days"),
                func.sum(PublicSiteTrafficDaily.visits).label("visits_all_time"),
            )
            .group_by(PublicSiteTrafficDaily.source)
        )
        rows = (await self.session.execute(statement)).all()
        totals = {
            row.source: {
                "visits_7_days": int(row.visits_7_days or 0),
                "visits_30_days": int(row.visits_30_days or 0),
                "visits_all_time": int(row.visits_all_time or 0),
            }
            for row in rows
        }
        return [
            {
                "source": source,
                "label": SOURCE_LABELS[source],
                **totals.get(source, {
                    "visits_7_days": 0,
                    "visits_30_days": 0,
                    "visits_all_time": 0,
                }),
            }
            for source in PUBLIC_SITE_TRAFFIC_SOURCES
        ]
