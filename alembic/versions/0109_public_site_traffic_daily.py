"""Add anonymous daily counts for public-site UTM sources."""

from alembic import op
import sqlalchemy as sa


revision = "0109_public_site_traffic_daily"
down_revision = "0108_native_audit_ownership"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "public_site_traffic_daily",
        sa.Column("visit_day", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("visits", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "source IN ('instagram', 'tiktok', 'youtube', 'other')",
            name="source",
        ),
        sa.PrimaryKeyConstraint(
            "visit_day",
            "source",
            name="pk_public_site_traffic_daily",
        ),
    )


def downgrade():
    op.drop_table("public_site_traffic_daily")
