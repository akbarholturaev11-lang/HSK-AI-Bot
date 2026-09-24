"""store Telegram bot reachability transitions

Revision ID: 0085_bot_reachability_events
Revises: 0084_bot_feedback_prompt_attempts
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0085_bot_reachability_events"
down_revision = "0084_bot_feedback_prompt_attempts"
branch_labels = None
depends_on = None


_INDEXES = {
    "ix_bot_reachability_events_user_id": ["user_id"],
    "ix_bot_reachability_events_telegram_id": ["telegram_id"],
    "ix_bot_reachability_events_event_type": ["event_type"],
    "ix_bot_reachability_events_created_at": ["created_at"],
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "bot_reachability_events" not in tables:
        op.create_table(
            "bot_reachability_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("telegram_id", sa.BigInteger(), nullable=False),
            sa.Column("event_type", sa.String(length=16), nullable=False),
            sa.Column("source", sa.String(length=120), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        inspector = sa.inspect(bind)

    existing_indexes = {
        item["name"]
        for item in inspector.get_indexes("bot_reachability_events")
        if item.get("name")
    }
    for name, columns in _INDEXES.items():
        if name not in existing_indexes:
            op.create_index(name, "bot_reachability_events", columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "bot_reachability_events" not in set(inspector.get_table_names()):
        return
    op.drop_table("bot_reachability_events")
