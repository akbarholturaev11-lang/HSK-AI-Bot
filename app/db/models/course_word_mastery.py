from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Interval takrori: `box` bo'yicha necha kundan keyin so'z qaytadi.
# 0 — bugun (yangi yoki xato qilingan), keyin 1 -> 3 -> 7 -> 21 kun.
# Oxirgi qadamdan nariga chiqmaydi: so'z siyraklashadi, lekin HECH QACHON
# butunlay yo'qolmaydi.
WORD_MASTERY_INTERVALS = (0, 1, 3, 7, 21)
WORD_MASTERY_MAX_BOX = len(WORD_MASTERY_INTERVALS) - 1

# Bir so'zni tanish va talaffuz qilish — BOSHQA-BOSHQA ko'nikmalar. O'quvchi
# 谢谢 ni ko'rib tanishi mumkin, lekin ayta olmasligi mumkin, shuning uchun
# jadval kaliti ko'nikmani ham o'z ichiga oladi. Keyin voice/memorize shu
# ustunga yangi qiymat sifatida qo'shiladi — migratsiya kerak bo'lmaydi.
WORD_MASTERY_SKILLS = ("recognition", "pronunciation")


class CourseWordMastery(Base):
    """O'quvchining bitta so'zni bitta ko'nikma bo'yicha o'zlashtirishi.

    Nega alohida jadval: `course_mistakes` da faqat XATOLAR bor, interval
    takrori esa TO'G'RI javoblarni rejalashtiradi. To'g'ri javoblarni
    `course_mistakes` ga yozish "Xatolarim" ekranini, `LearningSignals` ni
    va kunlik rejani buzardi. Bundan tashqari u qatorlari SAVOL bo'yicha
    (bitta ieroglif 4+ qatorga ega bo'lishi mumkin), bu yerda esa kalit
    so'zning o'zi.

    `level` ustuni ATAYLAB yo'q: band almashganda (hsk1 -> hsk2)
    `completed_lessons_count` nolga tushadi, lekin o'quvchi hsk1 so'zlarini
    unutmaydi — o'zlashtirish saqlanib qolishi kerak.
    """

    __tablename__ = "course_word_mastery"
    __table_args__ = (
        # UniqueConstraint uchun konvensiya faqat BIRINCHI ustun nomini
        # ishlatadi, shuning uchun to'liq nom qo'lda yoziladi —
        # `course_mistakes` va `course_xp_events` da ham shunday.
        UniqueConstraint(
            "user_id", "skill", "zh", name="uq_course_word_mastery_user_skill_zh"
        ),
        Index("ix_course_word_mastery_due", "user_id", "skill", "due_on"),
        CheckConstraint("box >= 0 AND box <= 4", name="box"),
        CheckConstraint(
            "skill IN ('recognition', 'pronunciation')",
            name="skill",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    skill: Mapped[str] = mapped_column(String(24), nullable=False)
    zh: Mapped[str] = mapped_column(String(16), nullable=False)

    box: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    # O'quvchining MAHALLIY kuni (`course_daily_window.local_day_key`), UTC emas.
    due_on: Mapped[date] = mapped_column(Date, nullable=False)

    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    last_result_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
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
