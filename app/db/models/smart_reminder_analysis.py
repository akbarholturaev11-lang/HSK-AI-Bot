"""Disposable analysis, separate from retained consent/day/issuance evidence."""
from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String
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


class SmartReminderBaselineMember(Base):
    __tablename__ = "smart_reminder_baseline_members"
    __table_args__ = (
        CheckConstraint("length(protocol_version) > 0", name="protocol"),
        CheckConstraint("expires_at > entered_at", name="expiry"),
        CheckConstraint("observed_active_days BETWEEN 0 AND 7 AND observed_units >= 0 "
            "AND observed_d7 IN (0, 1) AND d1_overlap IN (0, 1) AND source_limited IN (0, 1)", name="outcomes"),
        CheckConstraint("observed_at IS NOT NULL OR (observed_active_days = 0 AND observed_units = 0 "
            "AND observed_d7 = 0 AND d1_overlap = 0 AND source_limited = 0)", name="observation"),
        Index("ix_smart_baseline_expiry", "expires_at", "user_id"),
        Index("ix_smart_baseline_entry", "protocol_version", "entered_at"),
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    protocol_version: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_job_id: Mapped[str] = mapped_column(String(36))
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone_name: Mapped[str] = mapped_column(String(64))
    course_key: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_active_days: Mapped[int] = mapped_column(Integer, server_default="0")
    observed_units: Mapped[int] = mapped_column(BigInteger, server_default="0")
    observed_d7: Mapped[int] = mapped_column(Integer, server_default="0")
    d1_overlap: Mapped[int] = mapped_column(Integer, server_default="0")
    source_limited: Mapped[int] = mapped_column(Integer, server_default="0")


class SmartReminderBaselineTotal(Base):
    __tablename__ = "smart_reminder_baseline_totals"
    __table_args__ = (CheckConstraint("enrolled_accounts >= 0", name="accounts"),
        CheckConstraint("observed_accounts BETWEEN 0 AND enrolled_accounts "
            "AND observed_active_days BETWEEN 0 AND observed_accounts * 7 AND observed_units >= 0 "
            "AND observed_d7_accounts BETWEEN 0 AND observed_accounts "
            "AND d1_overlap_accounts BETWEEN 0 AND observed_accounts "
            "AND source_limited_accounts BETWEEN 0 AND observed_accounts", name="outcomes"))
    protocol_version: Mapped[str] = mapped_column(String(32), primary_key=True)
    cohort_month: Mapped[date] = mapped_column(Date, primary_key=True)
    enrolled_accounts: Mapped[int] = mapped_column(BigInteger)
    matures_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observed_accounts: Mapped[int] = mapped_column(BigInteger, server_default="0")
    observed_active_days: Mapped[int] = mapped_column(BigInteger, server_default="0")
    observed_units: Mapped[int] = mapped_column(BigInteger, server_default="0")
    observed_d7_accounts: Mapped[int] = mapped_column(BigInteger, server_default="0")
    d1_overlap_accounts: Mapped[int] = mapped_column(BigInteger, server_default="0")
    source_limited_accounts: Mapped[int] = mapped_column(BigInteger, server_default="0")
