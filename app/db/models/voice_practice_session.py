from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VoicePracticeSession(Base):
    __tablename__ = "voice_practice_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    level: Mapped[str] = mapped_column(String(24), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    voice: Mapped[str] = mapped_column(String(16), nullable=False)
    # `turn` keeps the existing upload/STT flow; `live` is the native
    # bidirectional audio transport. Existing rows are backfilled to `turn`.
    mode: Mapped[str] = mapped_column(String(8), default="turn", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True, nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    history: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    corrections: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    lesson_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("course_lessons.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    target_words: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    review_words: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Sessiya boshida muzlatilgan moslashuv rejasi: maqsad, fokus, eng kuchli
    # zaiflik, qayta sinaladigan xato va SRS so'zlari. Bo'sh `{}` bo'lsa AI
    # prompt'i moslashuvsiz eski holatida ishlaydi (rollback yo'li).
    plan_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # One provider socket per live practice row. Expiry releases abandoned
    # sockets after the server-enforced maximum duration.
    live_connection_token: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    live_connection_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    live_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    live_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    live_resumption_handle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
