"""Private short-lived payout proof references, never image BLOBs."""
from alembic import op
import sqlalchemy as sa

revision = '0130_admin_pwa_payout_proofs'
down_revision = '0129_admin_pwa_outbound'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('admin_pwa_payout_proofs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('admin_pwa_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('payout_id', sa.Integer(), sa.ForeignKey('partner_payouts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('byte_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('provider_file_id', sa.String(512)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('uploading','ready','failed','used')", name='ck_pwa_payout_proof_status'))
    op.create_index('ix_pwa_payout_proof_actor_created', 'admin_pwa_payout_proofs', ['actor_user_id', 'created_at'])
    op.create_index('ix_pwa_payout_proof_expiry', 'admin_pwa_payout_proofs', ['expires_at', 'id'])
    op.create_index('ix_admin_pwa_payout_proofs_session_id', 'admin_pwa_payout_proofs', ['session_id'])
    op.create_index('ix_admin_pwa_payout_proofs_payout_id', 'admin_pwa_payout_proofs', ['payout_id'])


def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS (SELECT 1 FROM admin_pwa_payout_proofs)')).scalar_one():
        raise RuntimeError('Archive payout proof references before destructive downgrade')
    op.drop_table('admin_pwa_payout_proofs')
