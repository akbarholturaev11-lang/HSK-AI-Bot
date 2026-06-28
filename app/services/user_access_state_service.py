from datetime import datetime, timezone


class UserAccessState:
    PAID = "paid"
    TEMPORARY_TRIAL = "temporary_trial"
    TRIAL = "trial"
    FREE = "free"
    EXPIRED = "expired"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class UserAccessStateService:
    """Canonical user access classifier.

    This does not mutate the database. Feature services still own their own limits;
    this class only answers "what plan/lifecycle is this user in right now?"
    """

    FREE_TIER_STATES = {
        UserAccessState.TRIAL,
        UserAccessState.FREE,
        UserAccessState.EXPIRED,
    }

    COURSE_ELIGIBLE_STATES = {
        UserAccessState.TRIAL,
        UserAccessState.FREE,
        UserAccessState.EXPIRED,
        UserAccessState.TEMPORARY_TRIAL,
    }

    @staticmethod
    def as_utc(value):
        if not value:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def has_active_end_date(cls, user, *, now: datetime | None = None) -> bool:
        end_date = cls.as_utc(getattr(user, "end_date", None))
        return bool(end_date and end_date > (now or datetime.now(timezone.utc)))

    @classmethod
    def classify(cls, user, *, now: datetime | None = None) -> str:
        if not user:
            return UserAccessState.UNKNOWN

        now = now or datetime.now(timezone.utc)
        status = str(getattr(user, "status", "") or "").strip().lower()
        payment_status = str(getattr(user, "payment_status", "") or "").strip().lower()
        has_active_end = cls.has_active_end_date(user, now=now)

        if status == "blocked":
            return UserAccessState.BLOCKED
        if status == "active" and payment_status == "approved" and has_active_end:
            return UserAccessState.PAID
        if status == "active" and payment_status == "approved":
            return UserAccessState.EXPIRED
        if status == "active" and has_active_end:
            return UserAccessState.TEMPORARY_TRIAL
        if status == "expired":
            return UserAccessState.EXPIRED
        if status == "trial":
            return UserAccessState.TRIAL
        if status == "free":
            return UserAccessState.FREE
        return UserAccessState.FREE

    @classmethod
    def is_paid(cls, user, *, now: datetime | None = None) -> bool:
        return cls.classify(user, now=now) == UserAccessState.PAID

    @classmethod
    def is_temporary_trial(cls, user, *, now: datetime | None = None) -> bool:
        return cls.classify(user, now=now) == UserAccessState.TEMPORARY_TRIAL

    @classmethod
    def can_use_free_tier(cls, user, *, now: datetime | None = None) -> bool:
        return cls.classify(user, now=now) in cls.FREE_TIER_STATES

    @classmethod
    def can_use_course(cls, user, *, now: datetime | None = None) -> bool:
        return cls.classify(user, now=now) in cls.COURSE_ELIGIBLE_STATES or cls.is_paid(user, now=now)
