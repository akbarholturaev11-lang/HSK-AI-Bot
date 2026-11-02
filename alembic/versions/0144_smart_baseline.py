"""First-ready baseline membership and original anonymous cohort denominator."""
from alembic import op
import sqlalchemy as sa

revision = "0144_smart_baseline"
down_revision = "0143_smart_return_analysis"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("smart_reminder_baseline_members",
        sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),primary_key=True),
        sa.Column("protocol_version",sa.String(32),primary_key=True),
        sa.Column("source_job_id",sa.String(36),nullable=False),
        sa.Column("entered_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("timezone_name",sa.String(64),nullable=False),
        sa.Column("course_key",sa.String(32),nullable=False),
        sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("length(protocol_version) > 0",name=op.f("ck_smart_reminder_baseline_members_protocol")),
        sa.CheckConstraint("expires_at > entered_at",name=op.f("ck_smart_reminder_baseline_members_expiry")))
    op.create_index("ix_smart_baseline_expiry","smart_reminder_baseline_members",["expires_at","user_id"])
    op.create_index("ix_smart_baseline_entry","smart_reminder_baseline_members",["protocol_version","entered_at"])
    op.create_table("smart_reminder_baseline_totals",
        sa.Column("protocol_version",sa.String(32),primary_key=True),
        sa.Column("cohort_month",sa.Date(),primary_key=True),
        sa.Column("enrolled_accounts",sa.BigInteger(),nullable=False),
        sa.Column("matures_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("enrolled_accounts >= 0",name=op.f("ck_smart_reminder_baseline_totals_accounts")))


def downgrade():
    for table in ("smart_reminder_baseline_members","smart_reminder_baseline_totals"):
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError("Refusing populated baseline downgrade; preserve original cohorts")
    op.drop_table("smart_reminder_baseline_totals")
    op.drop_table("smart_reminder_baseline_members")
