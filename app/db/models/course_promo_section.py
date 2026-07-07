from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CoursePromoSection(Base):
    """Reklama ko'rish oqimida (video ostida) ko'rsatiladigan admin boshqaradigan
    promo bo'lim: hamkorlik taklifi yoki boshqa botni reklama qilish.

    `title` va `body` — 3 tilga (uz/ru/tj) tarjima qilingan localized JSON
    (broadcast bilan bir xil format). `link_url` — hamkorlik uchun Instagram,
    bot-promo uchun bot havolasi (t.me/...).
    """

    __tablename__ = "course_promo_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # "cooperation" (hamkorlik) | "bot_promo" (boshqa bot reklamasi)
    kind: Mapped[str] = mapped_column(String(16), default="bot_promo", nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    link_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # Admin qaysi tilda yozganini eslab qolamiz (qayta tarjima uchun).
    source_language: Mapped[str] = mapped_column(String(8), default="uz", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)
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
