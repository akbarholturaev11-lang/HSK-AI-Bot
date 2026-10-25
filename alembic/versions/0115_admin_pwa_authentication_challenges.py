"""Store one-use passkey sign-in challenges without credential/user claims."""
from alembic import op
import sqlalchemy as sa

revision = "0115_admin_pwa_authentication_challenges"
down_revision = "0114_admin_pwa_webauthn_registration"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_authentication_challenges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("challenge", sa.LargeBinary(32), nullable=False),
        sa.Column("browser_proof_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_admin_pwa_authentication_challenges_created_at",
        "admin_pwa_authentication_challenges", ["created_at"],
    )
    op.create_index(
        "ix_admin_pwa_authentication_challenges_expires_at",
        "admin_pwa_authentication_challenges", ["expires_at"],
    )


def downgrade():
    op.drop_index("ix_admin_pwa_authentication_challenges_expires_at",
                  table_name="admin_pwa_authentication_challenges")
    op.drop_index("ix_admin_pwa_authentication_challenges_created_at",
                  table_name="admin_pwa_authentication_challenges")
    op.drop_table("admin_pwa_authentication_challenges")
