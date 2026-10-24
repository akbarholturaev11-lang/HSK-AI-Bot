"""Encrypted, per-install Apple push subscriptions behind a disabled flag."""
from alembic import op
import sqlalchemy as sa

revision = "0124_admin_pwa_push_subscriptions"
down_revision = "0123_admin_pwa_inbox_triage"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "admin_pwa_push_subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint_hash", sa.String(64), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("endpoint_hash", name="uq_admin_pwa_push_endpoint"),
        sa.CheckConstraint("platform IN ('iphone', 'mac')", name="ck_admin_pwa_push_platform"),
    )
    op.create_index("ix_admin_pwa_push_user", "admin_pwa_push_subscriptions", ["user_id","revoked_at"])

def downgrade():
    if op.get_bind().execute(sa.text("SELECT count(*) FROM admin_pwa_push_subscriptions")).scalar_one():
        raise RuntimeError("Export/retire all private Web Push subscriptions before schema rollback")
    op.drop_index("ix_admin_pwa_push_user", table_name="admin_pwa_push_subscriptions")
    op.drop_table("admin_pwa_push_subscriptions")
