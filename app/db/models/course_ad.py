from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseAdCreative(Base):
    __tablename__ = "course_ad_creatives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    media_path: Mapped[str] = mapped_column(String(512), nullable=False)
    media_type: Mapped[str] = mapped_column(String(16), default="video", nullable=False)
    media_blob: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    media_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    media_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Reklama tili: "all" (barcha tillar), "uz", "ru", "tj".
    language: Mapped[str] = mapped_column(String(8), default="all", index=True, nullable=False)
    link_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_by_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CourseAdView(Base):
    __tablename__ = "course_ad_views"
    __table_args__ = (
        Index(
            "ix_course_ad_views_user_lesson_placement",
            "user_telegram_id",
            "level",
            "lesson_order",
            "placement",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ad_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("course_ad_creatives.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    level: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    lesson_order: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    placement: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    watched_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
