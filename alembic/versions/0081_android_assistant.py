"""Android assistant history and recoverable requests; no existing data removed."""
from alembic import op
import sqlalchemy as sa

revision = "0081_android_assistant"
down_revision = "0080_ai_usage_billing_tier"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())
    if "assistant_conversations" not in existing_tables:
        op.create_table(
            "assistant_conversations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_assistant_conversations_user_id", "assistant_conversations", ["user_id"])
    if "assistant_requests" not in existing_tables:
        op.create_table(
            "assistant_requests",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("conversation_id", sa.String(36), nullable=False),
            sa.Column("client_message_id", sa.String(36), nullable=False),
            sa.Column("fingerprint", sa.String(64), nullable=False),
            sa.Column("kind", sa.String(16), nullable=False),
            sa.Column("input_text", sa.Text(), nullable=False),
            sa.Column("status", sa.String(24), nullable=False),
            sa.Column("phase", sa.String(24), nullable=False),
            sa.Column("context_json", sa.Text(), nullable=False),
            sa.Column("response_json", sa.Text(), nullable=False),
            sa.Column("error", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["conversation_id"], ["assistant_conversations.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "client_message_id", name="uq_assistant_requests_user_client"),
        )
        op.create_index("ix_assistant_requests_user_id", "assistant_requests", ["user_id"])
        op.create_index("ix_assistant_requests_conversation_id", "assistant_requests", ["conversation_id"])
    if "assistant_assessments" not in existing_tables:
        op.create_table(
            "assistant_assessments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.String(160), nullable=False),
            sa.Column("kind", sa.String(16), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "session_id", name="uq_assistant_assessments_user_session"),
        )
        op.create_index("ix_assistant_assessments_user_id", "assistant_assessments", ["user_id"])
    columns = {c["name"] for c in sa.inspect(bind).get_columns("messages")}
    if "conversation_id" not in columns:
        with op.batch_alter_table("messages") as batch:
            batch.add_column(sa.Column("conversation_id", sa.String(36), nullable=True))
            batch.create_foreign_key("fk_messages_assistant_conversation", "assistant_conversations", ["conversation_id"], ["id"], ondelete="CASCADE")
            batch.create_index("ix_messages_conversation_id", ["conversation_id"])


def downgrade():
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("messages")}
    if "conversation_id" in columns:
        with op.batch_alter_table("messages") as batch:
            batch.drop_index("ix_messages_conversation_id")
            batch.drop_constraint("fk_messages_assistant_conversation", type_="foreignkey")
            batch.drop_column("conversation_id")
    existing_tables = set(sa.inspect(bind).get_table_names())
    for table in ("assistant_assessments", "assistant_requests", "assistant_conversations"):
        if table in existing_tables:
            op.drop_table(table)
