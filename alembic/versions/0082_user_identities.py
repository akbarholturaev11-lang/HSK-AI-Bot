"""Provider identities linked to one internal user; no existing data removed.

Adds ``user_identities`` and the flow/intent columns on
``desktop_link_requests``. ``users.telegram_id`` is deliberately NOT touched:
Telegram stays the single source of truth for its own identity in Phase 1, and
existing rows keep the ``telegram``/``signin`` defaults so every current link
flow behaves exactly as before.
"""
from alembic import op
import sqlalchemy as sa

revision = "0082_user_identities"
down_revision = "0081_android_assistant"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "user_identities" not in existing_tables:
        op.create_table(
            "user_identities",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(16), nullable=False),
            sa.Column("subject_hash", sa.String(64), nullable=False),
            sa.Column("email_hash", sa.String(64), nullable=True),
            sa.Column("email_display", sa.String(255), nullable=True),
            sa.Column(
                "email_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("display_name", sa.String(120), nullable=True),
            sa.Column("audience", sa.String(190), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "provider", "subject_hash", name="uq_user_identities_provider_subject"
            ),
            sa.UniqueConstraint(
                "user_id", "provider", name="uq_user_identities_user_provider"
            ),
        )
        op.create_index("ix_user_identities_user_id", "user_identities", ["user_id"])
        op.create_index(
            "ix_user_identities_email_hash", "user_identities", ["email_hash"]
        )

    if "desktop_link_requests" in existing_tables:
        columns = {c["name"] for c in inspector.get_columns("desktop_link_requests")}
        with op.batch_alter_table("desktop_link_requests") as batch:
            if "flow" not in columns:
                batch.add_column(
                    sa.Column(
                        "flow",
                        sa.String(16),
                        nullable=False,
                        server_default="telegram",
                    )
                )
            if "intent" not in columns:
                batch.add_column(
                    sa.Column(
                        "intent",
                        sa.String(16),
                        nullable=False,
                        server_default="signin",
                    )
                )
            if "bind_user_id" not in columns:
                batch.add_column(sa.Column("bind_user_id", sa.Integer(), nullable=True))
            if "link_failure_code" not in columns:
                batch.add_column(
                    sa.Column("link_failure_code", sa.String(48), nullable=True)
                )
        if "bind_user_id" not in columns:
            op.create_index(
                "ix_desktop_link_requests_bind_user_id",
                "desktop_link_requests",
                ["bind_user_id"],
            )
            op.create_foreign_key(
                "fk_desktop_link_requests_bind_user",
                "desktop_link_requests",
                "users",
                ["bind_user_id"],
                ["id"],
                ondelete="CASCADE",
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "desktop_link_requests" in existing_tables:
        columns = {c["name"] for c in inspector.get_columns("desktop_link_requests")}
        if "bind_user_id" in columns:
            op.drop_constraint(
                "fk_desktop_link_requests_bind_user",
                "desktop_link_requests",
                type_="foreignkey",
            )
            op.drop_index(
                "ix_desktop_link_requests_bind_user_id",
                table_name="desktop_link_requests",
            )
        with op.batch_alter_table("desktop_link_requests") as batch:
            for name in ("link_failure_code", "bind_user_id", "intent", "flow"):
                if name in columns:
                    batch.drop_column(name)

    if "user_identities" in existing_tables:
        op.drop_index("ix_user_identities_email_hash", table_name="user_identities")
        op.drop_index("ix_user_identities_user_id", table_name="user_identities")
        op.drop_table("user_identities")
