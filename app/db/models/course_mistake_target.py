from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Nishon — o'quvchi bilmagan NARSA, savol emas: lug'at so'zi (`word`),
# to'g'ri xitoycha gap (`sentence`) yoki nishon ajratib bo'lmagan eski
# savolning o'zi (`question`, faqat bitta format bilan qaytadi).
COURSE_MISTAKE_TARGET_KINDS = ("word", "sentence", "question")
COURSE_MISTAKE_TARGET_STATUSES = ("active", "cleared")


class CourseMistakeTarget(Base):
    """Xatolarim bo'limidagi takror birligi.

    Nega alohida jadval: `course_mistakes` qatorlari SAVOL bo'yicha — bitta
    你 so'zi ma'no, tinglash, ieroglif va juftlik savollarida 4 ta qator
    bo'lib yotishi mumkin. Takror esa so'zning o'zini 3 xil mashqda
    tekshiradi, shuning uchun progress (`passed_formats`) nishonda turadi.
    `course_mistakes` tarix/dalil sifatida qoladi va nishon yopilganda
    unga bog'langan qatorlar `resolved` qilinadi — shu bilan LearningSignals,
    kunlik reja va AI Voice konteksti o'zgarishsiz ishlaydi.
    """

    __tablename__ = "course_mistake_targets"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "category",
            "target_key",
            name="uq_course_mistake_targets_user_category_key",
        ),
        # Issiq yo'l: "shu o'quvchining faol nishonlari (kategoriya bo'yicha)".
        Index("ix_course_mistake_targets_user_status", "user_id", "status", "category"),
        CheckConstraint(
            "category IN ('word', 'grammar', 'character', 'pronunciation')",
            name="category",
        ),
        CheckConstraint("kind IN ('word', 'sentence', 'question')", name="kind"),
        CheckConstraint("status IN ('active', 'cleared')", name="status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    target_key: Mapped[str] = mapped_column(String(64), nullable=False)
    zh: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    # Mashq yasash uchun material: pinyin, ma'no/tarjima (3 tilda), gap
    # bo'laklari, o'quvchining xato varianti, muallif variantlari va h.k.
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # Qaysi manbalardan kelgani (vergul bilan): XP "ishonchli manba" qoidasi uchun.
    sources: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    # To'g'ri bajarilgan mashq turlari (vergul bilan). Xato javob nolga tushiradi.
    passed_formats: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleared_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cleared_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
