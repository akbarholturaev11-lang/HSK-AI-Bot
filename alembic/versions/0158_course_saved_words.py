"""Account-owned dictionary saved words (UIUX-003).

Independent from SRS/recognition/pronunciation and course_mistakes.
"""
from alembic import op
import sqlalchemy as sa

revision = "0158_course_saved_words"
down_revision = "0157_diagnostic_precision"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "course_saved_words",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hanzi", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "hanzi", name="uq_course_saved_words_user_hanzi"),
    )
    op.create_index("ix_course_saved_words_user_id", "course_saved_words", ["user_id"])
    op.create_index("ix_course_saved_words_user_created", "course_saved_words", ["user_id", "created_at"])


def downgrade():
    # Deliberately protect learner-saved words from accidental data loss.
    bind = op.get_bind()
    has_data = bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM course_saved_words)")).scalar_one()
    if has_data:
        raise RuntimeError("Export user saved words before downgrade")
    op.drop_index("ix_course_saved_words_user_created", table_name="course_saved_words")
    op.drop_index("ix_course_saved_words_user_id", table_name="course_saved_words")
    op.drop_table("course_saved_words")
