"""Add cross-client presence and platform promo cooldown state.

Revision ID: 0088_client_presence_promo
Revises: 0087_payment_source
"""

from alembic import op
import sqlalchemy as sa


revision = "0088_client_presence_promo"
down_revision = "0087_payment_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_client_presences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("surface", sa.String(length=32), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("app_version", sa.String(length=40), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_foreground_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "surface",
            "platform",
            name="uq_user_client_presence_user_surface_platform",
        ),
    )
    op.create_index(
        "ix_user_client_presences_user_id",
        "user_client_presences",
        ["user_id"],
    )
    op.create_index(
        "ix_user_client_presences_telegram_id",
        "user_client_presences",
        ["telegram_id"],
    )
    op.create_index(
        "ix_user_client_presences_surface",
        "user_client_presences",
        ["surface"],
    )
    op.create_index(
        "ix_user_client_presences_platform",
        "user_client_presences",
        ["platform"],
    )
    op.create_index(
        "ix_user_client_presences_last_seen_at",
        "user_client_presences",
        ["last_seen_at"],
    )
    op.create_index(
        "ix_user_client_presences_last_foreground_at",
        "user_client_presences",
        ["last_foreground_at"],
    )

    op.create_table(
        "app_promo_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("target_platform", sa.String(length=16), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_download_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "target_platform",
            name="uq_app_promo_state_user_platform",
        ),
    )
    op.create_index("ix_app_promo_states_user_id", "app_promo_states", ["user_id"])
    op.create_index(
        "ix_app_promo_states_telegram_id",
        "app_promo_states",
        ["telegram_id"],
    )
    op.create_index(
        "ix_app_promo_states_target_platform",
        "app_promo_states",
        ["target_platform"],
    )


def downgrade() -> None:
    op.drop_index("ix_app_promo_states_target_platform", table_name="app_promo_states")
    op.drop_index("ix_app_promo_states_telegram_id", table_name="app_promo_states")
    op.drop_index("ix_app_promo_states_user_id", table_name="app_promo_states")
    op.drop_table("app_promo_states")

    op.drop_index(
        "ix_user_client_presences_last_foreground_at",
        table_name="user_client_presences",
    )
    op.drop_index(
        "ix_user_client_presences_last_seen_at",
        table_name="user_client_presences",
    )
    op.drop_index("ix_user_client_presences_platform", table_name="user_client_presences")
    op.drop_index("ix_user_client_presences_surface", table_name="user_client_presences")
    op.drop_index(
        "ix_user_client_presences_telegram_id",
        table_name="user_client_presences",
    )
    op.drop_index("ix_user_client_presences_user_id", table_name="user_client_presences")
    op.drop_table("user_client_presences")
