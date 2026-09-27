"""Universal mistake review: per-target drill progress.

Revision ID: 0091_course_mistake_targets
Revises: 0090_referral_discount_device

`course_mistakes` qatorlari savol bo'yicha saqlanadi; takror esa nishonni
(so'z yoki gap) 3 xil mashqda tekshiradi. Progress yangi jadvalda turadi,
`course_mistakes.target_key` qatorni nishonga bog'laydi. Eski qatorlar
ATAYLAB bu yerda to'ldirilmaydi: nishon lug'at/dars JSON'idan aniqlanadi,
bu ish servisda lazy bajariladi (`CourseMistakeService._sync_targets`).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0091_course_mistake_targets"
down_revision: Union[str, None] = "0090_referral_discount_device"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "course_mistake_targets"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("target_key", sa.String(length=64), nullable=False),
        sa.Column("zh", sa.Text(), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("sources", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("passed_formats", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("wrong_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cleared_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_course_mistake_targets_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_course_mistake_targets"),
        sa.UniqueConstraint(
            "user_id",
            "category",
            "target_key",
            name="uq_course_mistake_targets_user_category_key",
        ),
        # CHECK nomlari QISQA: konvensiya `ck_%(table_name)s_` prefiksini o'zi qo'shadi.
        sa.CheckConstraint(
            "category IN ('word', 'grammar', 'character', 'pronunciation')",
            name="category",
        ),
        sa.CheckConstraint("kind IN ('word', 'sentence', 'question')", name="kind"),
        sa.CheckConstraint("status IN ('active', 'cleared')", name="status"),
    )
    op.create_index("ix_course_mistake_targets_user_id", TABLE, ["user_id"], unique=False)
    op.create_index(
        "ix_course_mistake_targets_user_status",
        TABLE,
        ["user_id", "status", "category"],
        unique=False,
    )
    op.add_column(
        "course_mistakes",
        sa.Column("target_key", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_course_mistakes_user_target",
        "course_mistakes",
        ["user_id", "category", "target_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_course_mistakes_user_target", table_name="course_mistakes")
    op.drop_column("course_mistakes", "target_key")
    op.drop_index("ix_course_mistake_targets_user_status", table_name=TABLE)
    op.drop_index("ix_course_mistake_targets_user_id", table_name=TABLE)
    op.drop_table(TABLE)
