"""entitlement shadow comparison log

Markaziy limit dvigateli eski qarorlarni almashtirishdan OLDIN ular bilan
yonma-yon ishlaydi va har bir farq shu jadvalga yoziladi. Ko'chirish
"ishlayotgandir" degan taxmin bilan emas, o'lchov bilan yoqiladi.

Unique kalitda `agree` bor: bir kunda bir foydalanuvchi × harakat × klient
uchun ko'pi bilan bitta "mos keldi" va bitta "mos kelmadi" qatori yoziladi.
Busiz faol foydalanuvchi kuniga o'nlab bir xil qator yozib jadvalni
shishirardi; bu kalit bilan esa nomuvofiqliklar ham, halol namuna soni ham
saqlanadi.

Jadval vaqtinchalik: har bir harakat 30 kun barqaror ishlagach shadow
tarmoqlari o'chiriladi, jadval esa tarix uchun qoladi.

Revision ID: 0075_entitlement_shadow_events
Revises: 0074_voice_session_plan
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0075_entitlement_shadow_events"
down_revision: Union[str, None] = "0074_voice_session_plan"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entitlement_shadow_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("client", sa.String(length=16), nullable=False),
        sa.Column("agree", sa.Boolean(), nullable=False),
        sa.Column("legacy_allowed", sa.Boolean(), nullable=True),
        sa.Column("legacy_limit", sa.Integer(), nullable=True),
        sa.Column("legacy_used", sa.Integer(), nullable=True),
        sa.Column("legacy_remaining", sa.Integer(), nullable=True),
        sa.Column("engine_allowed", sa.Boolean(), nullable=True),
        sa.Column("engine_limit", sa.Integer(), nullable=True),
        sa.Column("engine_used", sa.Integer(), nullable=True),
        sa.Column("engine_remaining", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(length=24), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.Column("day_key", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "telegram_id",
            "action",
            "client",
            "day_key",
            "agree",
            name="uq_entitlement_shadow_events_daily",
        ),
    )
    op.create_index(
        "ix_entitlement_shadow_events_telegram_id",
        "entitlement_shadow_events",
        ["telegram_id"],
    )
    op.create_index(
        "ix_entitlement_shadow_events_action", "entitlement_shadow_events", ["action"]
    )
    op.create_index(
        "ix_entitlement_shadow_events_client", "entitlement_shadow_events", ["client"]
    )
    op.create_index(
        "ix_entitlement_shadow_events_agree", "entitlement_shadow_events", ["agree"]
    )
    op.create_index(
        "ix_entitlement_shadow_events_created_at",
        "entitlement_shadow_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_entitlement_shadow_events_created_at", table_name="entitlement_shadow_events"
    )
    op.drop_index(
        "ix_entitlement_shadow_events_agree", table_name="entitlement_shadow_events"
    )
    op.drop_index(
        "ix_entitlement_shadow_events_client", table_name="entitlement_shadow_events"
    )
    op.drop_index(
        "ix_entitlement_shadow_events_action", table_name="entitlement_shadow_events"
    )
    op.drop_index(
        "ix_entitlement_shadow_events_telegram_id",
        table_name="entitlement_shadow_events",
    )
    op.drop_table("entitlement_shadow_events")
