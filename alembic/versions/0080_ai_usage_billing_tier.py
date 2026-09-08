"""Snapshot AI billing tier without rewriting historical estimates."""

from alembic import op
import sqlalchemy as sa

revision = "0080_ai_usage_billing_tier"
down_revision = "0079_course_ad_view_daily_index"
branch_labels = None
depends_on = None


def upgrade():
    # Bootstrap may have added this column before Alembic runs.
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("ai_usage_events")}
    if "billing_tier" not in columns:
        op.add_column("ai_usage_events", sa.Column(
            "billing_tier", sa.String(24), nullable=False, server_default="legacy_estimate"
        ))


def downgrade():
    op.drop_column("ai_usage_events", "billing_tier")
