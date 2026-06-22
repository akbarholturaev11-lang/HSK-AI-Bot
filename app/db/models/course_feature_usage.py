from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


COURSE_FEATURE_KEYS = ("lesson", "voice", "placement", "training_test")


class CourseFeatureUsage(Base):
    __tablename__ = "course_feature_usages"
    __table_args__ = (
        CheckConstraint(
            "feature_key IN ('lesson', 'voice', 'placement', 'training_test')",
            name="feature_key",
        ),
        UniqueConstraint(
            "user_id",
            "feature_key",
            "usage_ref",
            name="uq_course_feature_usages_user_feature_ref",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    feature_key: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    usage_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
