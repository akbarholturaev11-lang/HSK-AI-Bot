from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseAdaptivePlan(Base):
    """Bitta darsga qo'shiladigan shaxsiy takror savollari (UIUX-007).

    Savollar va ularning javob kaliti serverda saqlanadi: klient faqat
    kalitsiz savolni oladi va javobini shu snapshot bo'yicha tekshirtiradi.
    Kalit — o'quvchi + dars + mahalliy kun + til + klient formatlari, shuning
    uchun qayta so'rov, tarmoq uzilishi yoki qayta ochilish o'sha rejani
    qaytaradi. Bu jadval dars natijasi, XP yoki progress EMAS.
    """

    __tablename__ = "course_adaptive_plans"
    __table_args__ = (
        UniqueConstraint("user_id", "plan_key", name="uq_course_adaptive_plans_user_key"),
        Index("ix_course_adaptive_plans_user_day", "user_id", "local_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_key: Mapped[str] = mapped_column(String(96), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    lesson_order: Mapped[int] = mapped_column(Integer, nullable=False)
    local_day: Mapped[date] = mapped_column(Date, nullable=False)
    contract_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    answers_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
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
