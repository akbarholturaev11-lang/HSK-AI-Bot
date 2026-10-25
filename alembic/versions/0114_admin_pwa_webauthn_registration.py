"""Persist challenge-bound WebAuthn registration and verified public credentials."""
from alembic import op
import sqlalchemy as sa

revision = "0114_admin_pwa_webauthn_registration"
down_revision = "0113_admin_pwa_enrollment_grants"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_registration_challenges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("grant_id", sa.String(36), sa.ForeignKey("admin_pwa_enrollment_grants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("challenge", sa.LargeBinary(32), nullable=False),
        sa.Column("user_handle", sa.LargeBinary(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_admin_pwa_registration_challenges_expires_at", "admin_pwa_registration_challenges", ["expires_at"])
    op.create_table(
        "admin_pwa_credentials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(1024), nullable=False, unique=True),
        sa.Column("public_key", sa.LargeBinary(2048), nullable=False),
        sa.Column("user_handle", sa.LargeBinary(32), nullable=False),
        sa.Column("sign_count", sa.BigInteger(), nullable=False),
        sa.Column("device_type", sa.String(24), nullable=False),
        sa.Column("backed_up", sa.Boolean(), nullable=False),
        sa.Column("transports", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_admin_pwa_credentials_user_id", "admin_pwa_credentials", ["user_id"])


def downgrade():
    op.drop_index("ix_admin_pwa_credentials_user_id", table_name="admin_pwa_credentials")
    op.drop_table("admin_pwa_credentials")
    op.drop_index("ix_admin_pwa_registration_challenges_expires_at", table_name="admin_pwa_registration_challenges")
    op.drop_table("admin_pwa_registration_challenges")
