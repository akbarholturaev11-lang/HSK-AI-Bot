"""Additive Smart storage; no row is itself consent, a claim, or send authority."""

from datetime import date, datetime, time
from uuid import uuid4

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer,
    String, Time, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _id() -> str:
    return str(uuid4())


class SmartReminderPreference(Base):
    __tablename__ = "smart_reminder_preferences"
    __table_args__ = (
        CheckConstraint("revision >= 0 AND grant_epoch >= 0 AND migration_version >= 0", name="versions"),
        CheckConstraint("time_mode IN ('auto', 'manual_locked')", name="time_mode"),
        CheckConstraint("channel_mode IN ('auto', 'manual_locked')", name="channel_mode"),
        CheckConstraint("preferred_channel IS NULL OR preferred_channel IN ('telegram', 'android')", name="channel"),
        CheckConstraint("time_mode != 'manual_locked' OR (manual_time_local IS NOT NULL AND timezone_name IS NOT NULL)", name="manual_time"),
        CheckConstraint("channel_mode != 'manual_locked' OR preferred_channel IS NOT NULL", name="manual_channel"),
        CheckConstraint("(quiet_start IS NULL AND quiet_end IS NULL) OR (quiet_start IS NOT NULL AND quiet_end IS NOT NULL)", name="quiet_pair"),
        CheckConstraint("legacy_offset_minutes IS NULL OR legacy_offset_minutes BETWEEN -720 AND 840", name="legacy_offset"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    master_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    grant_epoch: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    migration_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    time_mode: Mapped[str] = mapped_column(String(16), default="auto", server_default="auto")
    manual_time_local: Mapped[time | None] = mapped_column(Time)
    timezone_name: Mapped[str | None] = mapped_column(String(64))
    legacy_time_local: Mapped[time | None] = mapped_column(Time)
    legacy_offset_minutes: Mapped[int | None] = mapped_column(Integer)
    channel_mode: Mapped[str] = mapped_column(String(16), default="auto", server_default="auto")
    preferred_channel: Mapped[str | None] = mapped_column(String(16))
    quiet_start: Mapped[time | None] = mapped_column(Time)
    quiet_end: Mapped[time | None] = mapped_column(Time)
    pause_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    action_source: Mapped[str | None] = mapped_column(String(32))
    action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SmartReminderConsent(Base):
    __tablename__ = "smart_reminder_consents"
    __table_args__ = (
        UniqueConstraint("user_id", "channel", "source_key", name="uq_smart_consent_source"),
        CheckConstraint("channel IN ('telegram', 'android')", name="channel"),
        CheckConstraint("state IN ('unknown', 'on', 'off')", name="state"),
        CheckConstraint("revision >= 0 AND evidence_version >= 1", name="versions"),
        CheckConstraint("device_id IS NULL OR channel = 'android'", name="device_channel"),
        Index("ix_smart_consent_user_channel", "user_id", "channel"),
        Index("ix_smart_consent_device", "device_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(16))
    # Stable provenance key survives deletion of an obsolete device row.
    source_key: Mapped[str] = mapped_column(String(96))
    device_id: Mapped[str | None] = mapped_column(ForeignKey("desktop_devices.id", ondelete="SET NULL"))
    state: Mapped[str] = mapped_column(String(16), default="unknown", server_default="unknown")
    source: Mapped[str] = mapped_column(String(32))
    evidence_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SmartReminderCapability(Base):
    __tablename__ = "smart_reminder_capabilities"
    __table_args__ = (
        CheckConstraint("protocol_version >= 0 AND generation >= 0", name="versions"),
        CheckConstraint("(observed_at IS NULL AND expires_at IS NULL) OR (observed_at IS NOT NULL AND expires_at IS NOT NULL AND expires_at > observed_at)", name="observation_window"),
        Index("ix_smart_capability_user", "user_id"),
    )

    device_id: Mapped[str] = mapped_column(ForeignKey("desktop_devices.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    protocol_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    generation: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    autonomous_study_disabled: Mapped[bool | None] = mapped_column(Boolean)
    study_notifications_allowed: Mapped[bool | None] = mapped_column(Boolean)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SmartReminderJob(Base):
    __tablename__ = "smart_reminder_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "local_day", "category", name="uq_smart_job_account_day_category"),
        CheckConstraint("category = 'study'", name="category"),
        CheckConstraint("state IN ('shadow', 'pending', 'claimed', 'provider_accepted', 'unknown', 'cancelled', 'expired', 'completed')", name="state"),
        CheckConstraint("grant_epoch >= 0 AND preference_revision >= 0", name="versions"),
        CheckConstraint("day_start_utc <= scheduled_at AND scheduled_at < expires_at AND expires_at <= day_end_utc", name="day_window"),
        CheckConstraint("selected_channel IS NULL OR selected_channel IN ('telegram', 'android')", name="channel"),
        CheckConstraint("selected_device_id IS NULL OR (selected_channel IS NOT NULL AND selected_channel = 'android')", name="device_channel"),
        CheckConstraint("lesson_order IS NULL OR lesson_order >= 1", name="lesson_order"),
        CheckConstraint("(lease_token IS NULL AND lease_expires_at IS NULL) OR (lease_token IS NOT NULL AND lease_expires_at IS NOT NULL)", name="lease_pair"),
        Index("ix_smart_job_due", "state", "scheduled_at", "expires_at", "id"),
        Index("ix_smart_job_account_window", "user_id", "day_start_utc", "day_end_utc"),
        Index("ix_smart_job_device", "selected_device_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(16), default="study", server_default="study")
    local_day: Mapped[date] = mapped_column(Date)
    timezone_name: Mapped[str] = mapped_column(String(64))
    day_start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    day_end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(24), default="shadow", server_default="shadow")
    preference_revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    grant_epoch: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    policy_version: Mapped[str] = mapped_column(String(32))
    selected_channel: Mapped[str | None] = mapped_column(String(16))
    selected_device_id: Mapped[str | None] = mapped_column(ForeignKey("desktop_devices.id", ondelete="SET NULL"))
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason_code: Mapped[str | None] = mapped_column(String(64))
    course_key: Mapped[str | None] = mapped_column(String(32))
    lesson_order: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SmartReminderAttempt(Base):
    __tablename__ = "smart_reminder_attempts"
    __table_args__ = (
        UniqueConstraint("attempt_key", name="uq_smart_attempt_key"),
        CheckConstraint("channel IN ('telegram', 'android')", name="channel"),
        CheckConstraint("state IN ('prepared', 'in_flight', 'provider_accepted', 'client_posted_unverified', 'verified_shown', 'confirmed_not_displayed', 'definite_failure', 'unknown', 'cancelled')", name="state"),
        CheckConstraint("grant_epoch >= 0", name="epoch"),
        CheckConstraint("expires_at > prepared_at", name="expiry"),
        CheckConstraint("device_id IS NULL OR channel = 'android'", name="device_channel"),
        Index("ix_smart_attempt_job", "job_id"),
        Index("ix_smart_attempt_device", "device_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("smart_reminder_jobs.id", ondelete="CASCADE"))
    attempt_key: Mapped[str] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(16))
    device_id: Mapped[str | None] = mapped_column(ForeignKey("desktop_devices.id", ondelete="SET NULL"))
    grant_epoch: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    state: Mapped[str] = mapped_column(String(32), default="prepared", server_default="prepared")
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason_code: Mapped[str | None] = mapped_column(String(64))
