"""course_progress.completed_lessons_count: HSK darslari -> mini-qismlar

Course v3 darslari mini-qismlarga bo'lindi (har qism 3-4 yangi so'z + oxirida
checkpoint; flat raqamlash). completed_lessons_count endi QISMLARNI sanaydi.
Bu migratsiya eski qiymatni (tugatilgan HSK darslari soni N) yangi hisobga
o'tkazadi: yangi qiymat = N-darsning checkpoint (oxirgi qism) flat raqami,
ya'ni 1..N darslarning barcha qismlari.

Raqamlar scripts/gen_course_v3_from_seed.py chiqargan
app/static/course_v3_data/parts_manifest.json dan olib KONSTANTA sifatida
yozildi (deploy paytida fayl o'qishga bog'lanmaslik uchun). Kurs qayta
bo'linsa, bu jadval EMAS — faqat kelajak progresslar o'zgaradi.

Revision ID: 0065_course_progress_parts
Revises: 0064_course_ad_type_button
Create Date: 2026-07-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0065_course_progress_parts"
down_revision: Union[str, None] = "0064_course_ad_type_button"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Har daraja uchun: index+1 = tugatilgan HSK darslari soni (eski qiymat),
# element = o'sha darsgacha bo'lgan barcha qismlar soni (yangi qiymat).
CHECKPOINTS: dict[str, list[int]] = {
    "hsk1": [3, 5, 9, 13, 17, 21, 25, 30, 35, 40, 44, 49, 53, 59, 63],
    "hsk2": [5, 10, 15, 20, 25, 30, 35, 40, 44, 49, 53, 58, 62, 67, 72],
    "hsk3": [6, 12, 18, 24, 29, 34, 38, 44, 49, 54, 60, 65, 70, 76, 83, 88, 93, 99, 104, 109],
    "hsk4": [9, 18, 27, 36, 45, 54, 64, 73, 82, 91, 100, 109, 119, 128, 137, 146, 154, 163, 172, 181],
}


def upgrade() -> None:
    conn = op.get_bind()
    for level, checkpoints in CHECKPOINTS.items():
        max_old = len(checkpoints)
        # Eski semantikada bo'lishi mumkin bo'lmagan qiymatlarni (QA/buzuq)
        # avval maksimal darsga qisqartiramiz — CASE konvertatsiyasidan OLDIN,
        # aks holda konvertatsiyalangan katta qiymatlar qayta ushlanadi.
        conn.execute(
            sa.text(
                "UPDATE course_progress SET completed_lessons_count = :max_old "
                "WHERE lower(level) = :lv AND completed_lessons_count > :max_old"
            ),
            {"lv": level, "max_old": max_old},
        )
        # Bitta atomik CASE — kaskadsiz (1->3 dan keyin 3 qayta 3->9 bo'lmaydi).
        whens = " ".join(
            f"WHEN {old} THEN {new}" for old, new in enumerate(checkpoints, 1)
        )
        conn.execute(
            sa.text(
                "UPDATE course_progress SET completed_lessons_count = "
                f"CASE completed_lessons_count {whens} ELSE completed_lessons_count END "
                "WHERE lower(level) = :lv "
                "AND completed_lessons_count BETWEEN 1 AND :max_old"
            ),
            {"lv": level, "max_old": max_old},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for level, checkpoints in CHECKPOINTS.items():
        # Teskari: yangi qiymat -> to'liq tugatilgan HSK darslari soni
        # (checkpointga yetmagan qismlar bekor bo'ladi).
        whens = " ".join(
            f"WHEN completed_lessons_count >= {new} THEN {old}"
            for old, new in sorted(enumerate(checkpoints, 1), key=lambda x: -x[1])
        )
        conn.execute(
            sa.text(
                "UPDATE course_progress SET completed_lessons_count = "
                f"CASE {whens} ELSE 0 END "
                "WHERE lower(level) = :lv AND completed_lessons_count > 0"
            ),
            {"lv": level},
        )
