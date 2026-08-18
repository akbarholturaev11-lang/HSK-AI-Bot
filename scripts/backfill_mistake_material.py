"""Eski (material'siz) xatolarga dars JSON'idan materialni qaytaradi.

Nima uchun kerak
----------------
`course_mistakes` jadvalida `sentence` / `audio_text` / `pinyin` ustunlari
YO'Q — ular faqat `material_json` ichida saqlanadi. `material_version < 2`
bo'lgan eski yozuvlarda material umuman yo'q, shuning uchun xatolar
bo'limida "Tinglang — qaysi so'z?" audiosiz, "Bo'sh joyga mos ieroglifni
tanlang" gapsiz chiqardi (endi bunday savol review'ga umuman chiqmaydi).

Bu skript yozuvni dars JSON'idagi kartaga qaytadan bog'lab, materialni
tiklaydi. Bog'lash `(prompt, correct_answer)` juftligi bo'yicha, uchala
tilda (uz/ru/tj) sinab ko'riladi.

Xavfsizlik
----------
* Standart rejim — DRY RUN. Yozish uchun `--apply` kerak.
* Faqat materiali YO'Q yoki eski (v<2) yozuvlarga tegadi; yaxshi material
  hech qachon ustidan yozilmaydi. Shuning uchun qayta-qayta ishlatsa bo'ladi.
* `mistake_key` TEGILMAYDI — u dedup uchun ishlatiladi, o'zgartirilsa
  mavjud yozuvlar ikkilanib ketishi mumkin.
* Bir dars ichida bir xil (prompt, javob) bir nechta kartada uchrasa,
  ularning turi/gapi/audiosi bir xil ekani tekshiriladi; farq qilsa
  yozuvga tegilmaydi.

Ishlatish
---------
    python scripts/backfill_mistake_material.py               # ko'rish
    python scripts/backfill_mistake_material.py --apply       # yozish
    python scripts/backfill_mistake_material.py --user 12345  # bitta user
"""

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.db.session import engine
from app.services.course_lesson_mistake_material_service import (
    CourseLessonMistakeMaterialError,
    CourseLessonMistakeMaterialService as Lessons,
)

MATERIAL_VERSION = 2
LANGS = ("uz", "ru", "tj")

# Faqat variantli kartalar qayta bog'lanadi: builder/match_pairs xatolarining
# javobi tokenlardan yig'iladi, ularni (prompt, javob) bo'yicha ishonchli
# topib bo'lmaydi.
CHOICE_TYPES = {
    "meaning_guess", "hanzi_choice", "pinyin_choice", "translation_choice",
    "quick_quiz", "listening_choice", "gap_fill", "dialog_cloze", "dialog_context",
}

_INDEX_CACHE: dict = {}


def _lesson_index(level: str, lesson_order: int, lang: str) -> dict:
    """(prompt, correct_answer) -> material dict. Faqat bir xil kontentlilar."""
    key = (level, lesson_order, lang)
    if key in _INDEX_CACHE:
        return _INDEX_CACHE[key]
    try:
        data = Lessons._load_lesson(level, lesson_order)
    except CourseLessonMistakeMaterialError:
        _INDEX_CACHE[key] = {}
        return {}

    schema_version = int(data.get("schema_version") or 1)
    buckets = defaultdict(list)
    for section_no, section in enumerate(data.get("sections", []), 1):
        for card_no, card in enumerate(section.get("cards", []), 1):
            card_type = Lessons._text(card.get("type"), 64).lower()
            if card_type not in CHOICE_TYPES:
                continue
            options = Lessons._localized_list(card.get("options"), lang)
            try:
                answer_index = int(card.get("correct_index"))
            except (TypeError, ValueError):
                continue
            if not 0 <= answer_index < len(options) or len(options) < 2:
                continue
            prompt = Lessons._localized(card.get("prompt"), lang) or Lessons._localized(
                card.get("title"), lang
            )
            material_ref = Lessons.material_ref(level, lesson_order, section_no, card_no)
            material = Lessons._base_material(
                card=card, section=section, level=level, lesson_order=lesson_order,
                lang=lang, section_no=section_no, card_no=card_no,
                material_ref=material_ref, source_schema_version=schema_version,
            )
            material.update({
                "options": options,
                "correct_answer": options[answer_index],
                "answer_index": answer_index,
            })
            buckets[(prompt, options[answer_index])].append(material)

    index = {}
    for bucket_key, materials in buckets.items():
        # Bir nechta karta bo'lsa — MUHIM maydonlari bir xil bo'lishi shart.
        signature = {
            (m["format"], m["sentence"], m["audio_text"], m["pinyin"])
            for m in materials
        }
        if len(signature) == 1:
            index[bucket_key] = materials[0]
    _INDEX_CACHE[key] = index
    return index


def _needs_backfill(material_json):
    if not material_json:
        return True
    try:
        material = json.loads(material_json)
    except (TypeError, ValueError):
        return True
    if not isinstance(material, dict):
        return True
    try:
        return int(material.get("material_version") or 0) < MATERIAL_VERSION
    except (TypeError, ValueError):
        return True


def _match(row):
    level = Lessons.normalize_level(row.level or "")
    if not level or row.lesson_order is None:
        return None
    try:
        lesson_order = int(row.lesson_order)
    except (TypeError, ValueError):
        return None
    if lesson_order <= 0:
        return None
    prompt = Lessons._text(row.prompt)
    correct = Lessons._text(row.correct_answer)
    if not prompt or not correct:
        return None
    for lang in LANGS:
        found = _lesson_index(level, lesson_order, lang).get((prompt, correct))
        if found:
            return found
    return None


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="bazaga yozish (standart: faqat ko'rsatish)")
    parser.add_argument("--user", type=int, default=None, help="faqat shu telegram_id uchun")
    parser.add_argument("--limit", type=int, default=0, help="ko'riladigan yozuvlar soni chegarasi")
    args = parser.parse_args()

    where = ["(m.material_json IS NULL OR m.material_json NOT LIKE '%\"material_version\":2%')"]
    params = {}
    if args.user:
        where.append("u.telegram_id = :tid")
        params["tid"] = args.user
    sql = (
        "SELECT m.id, m.level, m.lesson_order, m.prompt, m.correct_answer, "
        "m.category, m.source, m.material_json "
        "FROM course_mistakes m JOIN users u ON u.id = m.user_id "
        "WHERE " + " AND ".join(where) + " ORDER BY m.id"
    )
    if args.limit:
        sql += " LIMIT %d" % int(args.limit)

    stats = defaultdict(int)
    updates = []
    async with engine.begin() as conn:
        rows = (await conn.execute(text(sql), params)).fetchall()
        for row in rows:
            stats["ko'rildi"] += 1
            if not _needs_backfill(row.material_json):
                stats["material allaqachon yaxshi"] += 1
                continue
            if (row.source or "") != "lesson":
                stats["dars emas (%s)" % (row.source or "?")] += 1
                continue
            material = _match(row)
            if not material:
                stats["mos karta topilmadi"] += 1
                continue
            stats["TIKLANADI"] += 1
            updates.append((row.id, json.dumps(material, ensure_ascii=False, separators=(",", ":"))))

        if args.apply and updates:
            for mistake_id, payload in updates:
                await conn.execute(
                    text("UPDATE course_mistakes SET material_json = :m WHERE id = :i"),
                    {"m": payload, "i": mistake_id},
                )

    print("=== Natija ===")
    for key in sorted(stats):
        print("  %s: %d" % (key, stats[key]))
    if updates and not args.apply:
        print("\nDRY RUN — hech narsa yozilmadi. Yozish uchun: --apply")
        for mistake_id, payload in updates[:3]:
            preview = json.loads(payload)
            print("  namuna id=%s: format=%s sentence=%r audio=%r" % (
                mistake_id, preview["format"], preview["sentence"][:40], preview["audio_text"][:20]))
    elif args.apply:
        print("\n%d ta yozuv yangilandi." % len(updates))


if __name__ == "__main__":
    asyncio.run(main())
