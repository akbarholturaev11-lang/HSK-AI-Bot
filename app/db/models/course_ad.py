from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text
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
    # Reklama turi: "odiy" (oddiy reklama), "hamkorlik" (hamkorlik uchun),
    # "bot" (boshqa botni reklama qilish), "dars_yakuni" (dars tugagach bepul
    # userga ko'rsatiladigan blok — ostida obuna knopkasi va ixtiyoriy tashqi CTA,
    # mashq bo'limlarida CHIQMAYDI), "app" (desktop ilova reklamasi — Mini App
    # ochilganda markazda chiqadi, mashq bo'limlarida CHIQMAYDI).
    # Turga qarab mini app'da knopka va slot farq qiladi.
    ad_type: Mapped[str] = mapped_column(String(16), default="odiy", nullable=False)
    # Universal knopka nomi (hamkorlik/bot/dars_yakuni tashqi CTA uchun).
    # Bo'sh bo'lsa — turga mos default nom.
    button_text: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    # Faqat "app" turi uchun: yopish (X) tugmasi necha soniyadan keyin chiqadi.
    # NULL/0 — X darrov chiqadi. Boshqa turlar bu maydonni ishlatmaydi.
    skip_after_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Faqat "app" turi uchun: bir foydalanuvchiga kuniga necha marta ko'rsatiladi.
    # NULL yoki 0 — cheklovsiz (har ochilganda).
    daily_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Faqat "app" turi uchun: platforma tugmalarining QO'LDA kiritilgan havolalari.
    # JSON: {"macos": "https://...", "windows": "https://..."}.
    # Bo'sh bo'lsa — havola reliz tizimidan avtomatik olinadi. Qiymat bo'lsa,
    # u avtomatik havolani bosib o'tadi (reliz buzilganda zaxira yo'l).
    platform_links: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
