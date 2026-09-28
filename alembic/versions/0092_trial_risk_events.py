"""Store privacy-safe Pro-trial anti-abuse shadow snapshots.

Revision ID: 0092_trial_risk_events
Revises: 0091_course_mistake_targets
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0092_trial_risk_events"
down_revision: Union[str, None] = "0091_course_mistake_targets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "trial_risk_events"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("client", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("installation_key_hash", sa.String(length=64), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("account_age_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "prior_device_trial_users",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "prior_ip_trial_users_24h",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "prior_ip_trial_users_7d",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("signals_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="shadow"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_trial_risk_events_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trial_risk_events"),
    )
    op.create_index("ix_trial_risk_events_user_id", TABLE, ["user_id"], unique=False)
    op.create_index(
        "ix_trial_risk_events_telegram_id", TABLE, ["telegram_id"], unique=False
    )
    op.create_index("ix_trial_risk_events_client", TABLE, ["client"], unique=False)
    op.create_index("ix_trial_risk_events_created_at", TABLE, ["created_at"], unique=False)
    op.create_index(
        "ix_trial_risk_events_installation_created",
        TABLE,
        ["installation_key_hash", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_trial_risk_events_ip_created",
        TABLE,
        ["ip_hash", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_trial_risk_events_ip_created", table_name=TABLE)
    op.drop_index("ix_trial_risk_events_installation_created", table_name=TABLE)
    op.drop_index("ix_trial_risk_events_created_at", table_name=TABLE)
    op.drop_index("ix_trial_risk_events_client", table_name=TABLE)
    op.drop_index("ix_trial_risk_events_telegram_id", table_name=TABLE)
    op.drop_index("ix_trial_risk_events_user_id", table_name=TABLE)
    op.drop_table(TABLE)
