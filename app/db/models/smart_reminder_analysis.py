"""Disposable analysis, separate from retained consent/day/issuance evidence."""
from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


DELIVERY_STAGES = ("reserved", "in_flight", "provider_accepted", "client_posted_unverified",
          "confirmed_not_displayed", "outcome_unknown", "cancelled", "expired", "definite_failure")
SHADOW_STAGES = ("shadow_candidate", "shadow_suppressed")
LEARNING_STAGES = ("verified_study_after_attempt", "verified_study_after_report")
ACTIVITY_STAGES = ("study_day_after_attempt", "study_day_after_report")
RETURN_STAGES = ("contact_study_24h", "study_unit_24h")
STAGES = DELIVERY_STAGES + SHADOW_STAGES + ("client_reported_open",) + LEARNING_STAGES + ACTIVITY_STAGES + RETURN_STAGES
STAGE_CHECK = "stage IN (" + ", ".join(repr(s) for s in STAGES) + ")"
RESERVATION_STAGES = ("shadow_reserved", "shadow_refused")
RESERVATION_CHECK = "stage IN (" + ", ".join(repr(s) for s in RESERVATION_STAGES) + ")"
MONTHLY_CHECK = "stage IN (" + ", ".join(repr(s) for s in STAGES + RESERVATION_STAGES) + ")"


class SmartReminderAnalysisEvent(Base):
    __tablename__ = "smart_reminder_analysis_events"
    __table_args__ = (
        CheckConstraint(STAGE_CHECK, name="stage"),
        CheckConstraint("channel IN ('none', 'telegram', 'android')", name="channel"),
        CheckConstraint("length(event_key) = 64", name="event_key"),
        CheckConstraint("expires_at > occurred_at", name="expiry"),
        Index("ix_smart_analysis_expiry", "expires_at", "user_id", "event_key"),
        Index("ix_smart_analysis_job", "job_id"),
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    event_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("smart_reminder_jobs.id", ondelete="CASCADE"))
    stage: Mapped[str] = mapped_column(String(32))
    channel: Mapped[str] = mapped_column(String(16))
    reason_code: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SmartReminderAnalysisMonthly(Base):
    __tablename__ = "smart_reminder_analysis_monthly"
    __table_args__ = (
        CheckConstraint(MONTHLY_CHECK, name="stage"),
        CheckConstraint("channel IN ('none', 'telegram', 'android')", name="channel"),
        CheckConstraint("fact_count >= 0", name="fact_count"),
    )
    month: Mapped[date] = mapped_column(Date, primary_key=True)
    stage: Mapped[str] = mapped_column(String(32), primary_key=True)
    channel: Mapped[str] = mapped_column(String(16), primary_key=True)
    fact_count: Mapped[int] = mapped_column(BigInteger)


class SmartReminderReservationObservation(Base):
    __tablename__ = "smart_reminder_reservation_observations"
    __table_args__ = (
        CheckConstraint(RESERVATION_CHECK, name="stage"),
        CheckConstraint("length(event_key) = 64", name="event_key"),
        CheckConstraint("expires_at > occurred_at", name="expiry"),
        Index("ix_smart_reservation_expiry", "expires_at", "user_id", "event_key"),
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    event_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    stage: Mapped[str] = mapped_column(String(32))
    reason_code: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
