"""add mini app payment local fields

Revision ID: 0037_add_miniapp_payment_local_fields
Revises: 0036_add_payment_qr_codes
Create Date: 2026-06-09 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0037_add_miniapp_payment_local_fields"
down_revision: Union[str, None] = "0036_add_payment_qr_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _add_column_if_missing("payments", sa.Column("card_country", sa.String(length=16), nullable=True))
    _add_column_if_missing("payments", sa.Column("local_amount", sa.String(length=32), nullable=True))
    _add_column_if_missing("payments", sa.Column("local_currency", sa.String(length=16), nullable=True))
    _add_column_if_missing("payments", sa.Column("exchange_rate", sa.String(length=80), nullable=True))


def downgrade() -> None:
    _drop_column_if_exists("payments", "exchange_rate")
    _drop_column_if_exists("payments", "local_currency")
    _drop_column_if_exists("payments", "local_amount")
    _drop_column_if_exists("payments", "card_country")
