from datetime import date

from sqlalchemy import CheckConstraint, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


PUBLIC_SITE_TRAFFIC_SOURCES = ("instagram", "tiktok", "youtube", "other")


class PublicSiteTrafficDaily(Base):
    """Anonymous daily counts for tagged visits to public-site entry pages."""

    __tablename__ = "public_site_traffic_daily"
    __table_args__ = (
        CheckConstraint(
            "source IN ('instagram', 'tiktok', 'youtube', 'other')",
            name="source",
        ),
    )

    visit_day: Mapped[date] = mapped_column(Date, primary_key=True)
    source: Mapped[str] = mapped_column(String(24), primary_key=True)
    visits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
