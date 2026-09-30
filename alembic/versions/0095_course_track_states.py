"""HSK 3.0 track state and cross-client promo bookkeeping.

Revision ID: 0095_course_track_states
Revises: 0094_account_notice_deliveries
"""

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0095_course_track_states"
down_revision: Union[str, None] = "0094_account_notice_deliveries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_track_states",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("track", sa.String(length=16), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column(
            "completed_lessons_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "unlock_payment_id",
            sa.Integer(),
            sa.ForeignKey("payments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id",
            "track",
            name="uq_course_track_states_user_track",
        ),
    )
    op.create_index(
        "ix_course_track_states_user_id",
        "course_track_states",
        ["user_id"],
    )
    op.create_index(
        "ix_course_track_states_track",
        "course_track_states",
        ["track"],
    )
    op.create_index(
        "ix_course_track_states_unlock_payment_id",
        "course_track_states",
        ["unlock_payment_id"],
    )

    op.add_column(
        "course_miniapp_profiles",
        sa.Column(
            "hsk30_promo_shown_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "course_miniapp_profiles",
        sa.Column(
            "hsk30_promo_last_shown_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    bot_settings = sa.table(
        "bot_settings",
        sa.column("key", sa.String(length=120)),
        sa.column("value", sa.Text()),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    bind = op.get_bind()
    existing = bind.execute(
        sa.select(bot_settings.c.key).where(
            bot_settings.c.key == "hsk30_enabled"
        )
    ).scalar_one_or_none()
    if existing is None:
        bind.execute(
            bot_settings.insert().values(
                key="hsk30_enabled",
                value="0",
                updated_at=datetime.now(timezone.utc),
            )
        )


def downgrade() -> None:
    bot_settings = sa.table(
        "bot_settings",
        sa.column("key", sa.String(length=120)),
    )
    op.get_bind().execute(
        bot_settings.delete().where(bot_settings.c.key == "hsk30_enabled")
    )

    op.drop_column(
        "course_miniapp_profiles",
        "hsk30_promo_last_shown_at",
    )
    op.drop_column(
        "course_miniapp_profiles",
        "hsk30_promo_shown_count",
    )

    op.drop_index(
        "ix_course_track_states_unlock_payment_id",
        table_name="course_track_states",
    )
    op.drop_index(
        "ix_course_track_states_track",
        table_name="course_track_states",
    )
    op.drop_index(
        "ix_course_track_states_user_id",
        table_name="course_track_states",
    )
    op.drop_table("course_track_states")
