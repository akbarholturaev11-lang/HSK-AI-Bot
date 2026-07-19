"""hsk-data.js ni ikkiga bo'ladi: hsk-words.js + hsk-extra.js.

Nega kerak: hsk-data.js ~2.8 MB. Mashq sahifalari (course_v3_recognition.html,
course_v3_pronunciation.html) undan faqat WORDS'ni (~140 KB) ishlatadi, lekin
ilgari to'liq faylni yuklab parse qilardi — telefonda har ochilishda sezilarli
kechikish. STROKES/EXAMPLES/HSK4_GRAMMAR faqat hsk-lugat.html'ga kerak.

Ishlatish (hsk-data.js yangilangandan keyin):

    python3 scripts/split_hsk_data.py

Keyin HTML'lardagi `?v=` raqamini yangilashni unutmang, aks holda brauzer eski
(immutable keshlangan) faylni ishlatib qoladi.
"""

from __future__ import annotations

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"
SOURCE = STATIC / "hsk-data.js"

WORDS_BLOCKS = ("WORDS",)
EXTRA_BLOCKS = ("STROKES", "EXAMPLES", "HSK4_GRAMMAR")

WORDS_HEADER = """/* WORDS lug'ati — hsk-data.js dan ajratildi (scripts/split_hsk_data.py).
   Mashq sahifalari (recognition/pronunciation/memorize) faqat shu faylga muhtoj:
   2.8 MB o'rniga ~140 KB parse qilinadi. STROKES/EXAMPLES/HSK4_GRAMMAR -> hsk-extra.js */
"""

EXTRA_HEADER = """/* STROKES + EXAMPLES + HSK4_GRAMMAR — hsk-data.js dan ajratildi
   (scripts/split_hsk_data.py). Faqat hsk-lugat.html ishlatadi.
   WORDS uchun hsk-words.js ga qarang. */
"""


def split_blocks(source: str) -> dict[str, str]:
    """Top-level `const NAME = ...` bloklarini nomi bo'yicha ajratadi."""
    names = WORDS_BLOCKS + EXTRA_BLOCKS
    pattern = r"^(?:const|var|let)\s+(" + "|".join(names) + r")\s*="
    starts = [(m.group(1), m.start()) for m in re.finditer(pattern, source, re.M)]
    starts.sort(key=lambda item: item[1])

    missing = set(names) - {name for name, _ in starts}
    if missing:
        raise SystemExit(f"hsk-data.js ichida topilmadi: {', '.join(sorted(missing))}")

    blocks = {}
    for i, (name, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(source)
        blocks[name] = source[start:end].rstrip()
    return blocks


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    blocks = split_blocks(source)

    words_path = STATIC / "hsk-words.js"
    extra_path = STATIC / "hsk-extra.js"

    words_path.write_text(
        WORDS_HEADER + "\n".join(blocks[name] for name in WORDS_BLOCKS) + "\n",
        encoding="utf-8",
    )
    extra_path.write_text(
        EXTRA_HEADER + "\n".join(blocks[name] for name in EXTRA_BLOCKS) + "\n",
        encoding="utf-8",
    )

    for path in (words_path, extra_path):
        print(f"{path.name}: {path.stat().st_size / 1024:.0f} KB")
    print("Eslatma: HTML'lardagi ?v= raqamini yangilang.")


if __name__ == "__main__":
    main()
