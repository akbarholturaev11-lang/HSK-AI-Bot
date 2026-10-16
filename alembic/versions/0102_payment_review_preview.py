"""One reusable provisional subscription receipt opportunity per learner.

Revision ID: 0102_payment_review_preview
Revises: 0101_account_deletion_requests
"""
from alembic import op
import sqlalchemy as sa

revision = "0102_payment_review_preview"
down_revision = "0101_account_deletion_requests"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    columns = {col["name"] for col in sa.inspect(conn).get_columns("users")}
    if "payment_preview_available" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "payment_preview_available",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )
    if "payment_preview_payment_id" not in columns:
        op.add_column(
            "users",
            sa.Column("payment_preview_payment_id", sa.Integer(), nullable=True),
        )


def downgrade():
    op.drop_column("users", "payment_preview_payment_id")
    op.drop_column("users", "payment_preview_available")
