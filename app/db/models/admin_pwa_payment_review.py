"""Financial audit facts survive session/credential/account removal.

No cascading identity FK: canonical IDs are retained like payments.user_id.
The outbox is separate so delivery never edits the financial audit record.
"""
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdminPwaPaymentReview(Base):
    __tablename__ = "admin_pwa_payment_reviews"
    __table_args__ = (
        CheckConstraint("decision IN ('approve', 'reject')", name="ck_pwa_review_decision"),
        CheckConstraint("status = 'applied'", name="ck_pwa_review_status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    step_up_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    payment_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    actor_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="applied")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
    )


class AdminPwaPaymentOutbox(Base):
    __tablename__ = "admin_pwa_payment_outbox"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'attempting', 'attempted', 'uncertain')",
                        name="ck_pwa_payment_outbox_status"),
    )
    review_id: Mapped[str] = mapped_column(
        ForeignKey("admin_pwa_payment_reviews.id", ondelete="RESTRICT"), primary_key=True,
    )
    effects_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
