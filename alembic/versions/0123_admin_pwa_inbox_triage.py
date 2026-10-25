"""Durable, audited first-party inbox triage, separate from feedback sources."""
from alembic import op
import sqlalchemy as sa

revision = "0123_admin_pwa_inbox_triage"
down_revision = "0122_admin_pwa_native_reports"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_inbox_triage",
        sa.Column("source", sa.String(16), primary_key=True),
        sa.Column("source_id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.CheckConstraint("source IN ('bot', 'release', 'android', 'payment')", name="ck_admin_pwa_inbox_triage_source"),
        sa.CheckConstraint("status IN ('new', 'read', 'assigned', 'resolved')", name="ck_admin_pwa_inbox_triage_status"),
        sa.CheckConstraint("priority IN ('normal', 'important')", name="ck_admin_pwa_inbox_triage_priority"),
        sa.CheckConstraint("revision >= 1", name="ck_admin_pwa_inbox_triage_revision"),
    )
    op.create_index("ix_admin_pwa_inbox_triage_status", "admin_pwa_inbox_triage", ["status", "priority"])
    op.create_table(
        "admin_pwa_inbox_triage_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(24), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source IN ('bot', 'release', 'android', 'payment')", name="ck_admin_pwa_inbox_audit_source"),
        sa.CheckConstraint("operation IN ('mark_read','assign_self','resolve','reopen','mark_important','clear_important')",
                           name="ck_admin_pwa_inbox_audit_operation"),
    )
    op.create_index("ix_admin_pwa_inbox_audit_created", "admin_pwa_inbox_triage_audit", ["created_at"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT count(*) FROM admin_pwa_inbox_triage_audit")).scalar_one():
        raise RuntimeError("Archive inbox triage audit before destructive downgrade")
    if op.get_bind().execute(sa.text("SELECT count(*) FROM admin_pwa_inbox_triage")).scalar_one():
        raise RuntimeError("Archive inbox triage state before destructive downgrade")
    op.drop_index("ix_admin_pwa_inbox_audit_created", table_name="admin_pwa_inbox_triage_audit")
    op.drop_table("admin_pwa_inbox_triage_audit")
    op.drop_index("ix_admin_pwa_inbox_triage_status", table_name="admin_pwa_inbox_triage")
    op.drop_table("admin_pwa_inbox_triage")
