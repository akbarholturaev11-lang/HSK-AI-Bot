"""One-time, per-account PWA Exit Offer entitlement.

Creating and accepting a 20% promotion is never proof of payment.
No financial records are changed here.
"""
from alembic import op
import sqlalchemy as sa

revision = "0152_pwa_exit_offer"
down_revision = "0151_lava_top_payments"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pwa_exit_offers",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_pwa_exit_offers")),
    )


def downgrade():
    op.drop_table("pwa_exit_offers")
