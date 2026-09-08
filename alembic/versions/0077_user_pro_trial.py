"""add the 7-day Pro trial columns

Trial O'ZINING ustunlarini oladi va `users.status`, `payment_status`,
`start_date`, `end_date` ga UMUMAN tegmaydi.

Nega bu shunchalik muhim: `AccessService._is_same_active_window` referral
mukofotining $2 lik AI byudjetini foydalanuvchining `start_date`/`end_date`
iga ±5 soniya aniqlik bilan bog'laydi. Trial o'sha ustunlarga yozsa, jonli
referral trialining byudjeti jimgina uzilib qolardi — foydalanuvchi hech
qanday xatosiz AI kirishini yo'qotardi va buni hech kim sezmasdi.

Eski foydalanuvchilar uchun `trial_used` `false` bo'lib qoladi, ya'ni
hammaga bir marta trial ochiladi. Pullik va referral foydalanuvchilar
ta'sirlanmaydi: holat aniqlagichi PRO_ACTIVE va TEMP_ACCESS ni trialdan
OLDIN tekshiradi.

Revision ID: 0077_user_pro_trial
Revises: 0076_conversion_funnel_events_v2
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0077_user_pro_trial"
down_revision: Union[str, None] = "0076_conversion_funnel_events_v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "trial_used",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "users", sa.Column("pro_trial_started_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "users", sa.Column("pro_trial_ends_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "users", sa.Column("pro_trial_source", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "users", sa.Column("pro_trial_revoked_at", sa.DateTime(timezone=True), nullable=True)
    )
    # Rejalashtirilgan vazifa muddati o'tgan triallarni shu indeks bo'yicha topadi.
    op.create_index("ix_users_pro_trial_ends_at", "users", ["pro_trial_ends_at"])


def downgrade() -> None:
    op.drop_index("ix_users_pro_trial_ends_at", table_name="users")
    op.drop_column("users", "pro_trial_revoked_at")
    op.drop_column("users", "pro_trial_source")
    op.drop_column("users", "pro_trial_ends_at")
    op.drop_column("users", "pro_trial_started_at")
    op.drop_column("users", "trial_used")
