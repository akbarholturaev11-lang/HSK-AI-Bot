"""Record where a subscription receipt was submitted.

Revision ID: 0087_payment_source
Revises: 0086_bot_outbound_events
"""

from alembic import op
import sqlalchemy as sa


revision = "0087_payment_source"
down_revision = "0086_bot_outbound_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column(
            "source", sa.String(length=32), nullable=False,
            server_default="telegram_bot",
        ),
    )


def downgrade() -> None:
    op.drop_column("payments", "source")
