"""Private campaign media ownership and source commitments, no media BLOBs."""
from alembic import op
import sqlalchemy as sa

revision = '0131_admin_pwa_campaign_assets'
down_revision = '0130_admin_pwa_payout_proofs'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('admin_pwa_campaign_assets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('admin_pwa_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('media_type', sa.String(16), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('byte_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('provider_file_id', sa.String(512)),
        sa.Column('command_id', sa.String(36), sa.ForeignKey('admin_pwa_command_audit.id', ondelete='RESTRICT')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('uploading','ready','failed','used')", name='ck_pwa_campaign_asset_status'),
        sa.CheckConstraint("media_type IN ('photo','video')", name='ck_pwa_campaign_asset_type'),
        sa.CheckConstraint('byte_count BETWEEN 1 AND 26214400', name='ck_pwa_campaign_asset_bytes'))
    op.create_index('ix_admin_pwa_campaign_assets_session_id', 'admin_pwa_campaign_assets', ['session_id'])
    op.create_index('ix_pwa_campaign_asset_actor_created', 'admin_pwa_campaign_assets', ['actor_user_id', 'created_at'])
    op.create_index('ix_pwa_campaign_asset_expiry', 'admin_pwa_campaign_assets', ['expires_at', 'id'])


def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS (SELECT 1 FROM admin_pwa_campaign_assets)')).scalar_one():
        raise RuntimeError('Archive campaign asset metadata before destructive downgrade')
    op.drop_table('admin_pwa_campaign_assets')
