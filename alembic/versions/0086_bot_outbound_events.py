"""store Telegram outbound delivery evidence

Revision ID: 0086_bot_outbound_events
Revises: 0085_bot_reachability_events
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0086_bot_outbound_events"
down_revision = "0085_bot_reachability_events"
branch_labels = None
depends_on = None


_INDEXES = {
    "ix_bot_outbound_events_user_id": ["user_id"],
    "ix_bot_outbound_events_telegram_id": ["telegram_id"],
    "ix_bot_outbound_events_source": ["source"],
    "ix_bot_outbound_events_status": ["status"],
    "ix_bot_outbound_events_created_at": ["created_at"],
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "bot_outbound_events" not in set(inspector.get_table_names()):
        op.create_table(
            "bot_outbound_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("telegram_id", sa.BigInteger(), nullable=False),
            sa.Column("source", sa.String(length=120), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        inspector = sa.inspect(bind)

    existing_indexes = {
        item["name"] for item in inspector.get_indexes("bot_outbound_events") if item.get("name")
    }
    for name, columns in _INDEXES.items():
        if name not in existing_indexes:
            op.create_index(name, "bot_outbound_events", columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "bot_outbound_events" in set(inspector.get_table_names()):
        op.drop_table("bot_outbound_events")
