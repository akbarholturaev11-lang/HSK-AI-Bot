"""Editable in-app profile fields without mutating Telegram identity."""

from alembic import op
import sqlalchemy as sa

revision = "0083_course_profile_identity"
down_revision = "0082_user_identities"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "course_miniapp_profiles" not in set(inspector.get_table_names()):
        return
    columns = {c["name"] for c in inspector.get_columns("course_miniapp_profiles")}
    with op.batch_alter_table("course_miniapp_profiles") as batch:
        if "display_name" not in columns:
            batch.add_column(sa.Column("display_name", sa.String(80), nullable=True))
        if "avatar_key" not in columns:
            batch.add_column(
                sa.Column("avatar_key", sa.String(32), nullable=False, server_default="")
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "course_miniapp_profiles" not in set(inspector.get_table_names()):
        return
    columns = {c["name"] for c in inspector.get_columns("course_miniapp_profiles")}
    with op.batch_alter_table("course_miniapp_profiles") as batch:
        if "avatar_key" in columns:
            batch.drop_column("avatar_key")
        if "display_name" in columns:
            batch.drop_column("display_name")
