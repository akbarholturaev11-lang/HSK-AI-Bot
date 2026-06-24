import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hsk4_lower_pdf_materials import HSK4_LOWER_PDF_MATERIALS


EXPECTED = {
    11: {"vocab": 30, "blocks": 5},
    12: {"vocab": 32, "blocks": 5},
    13: {"vocab": 34, "blocks": 5},
    14: {"vocab": 32, "blocks": 5},
    15: {"vocab": 31, "blocks": 5},
    16: {"vocab": 31, "blocks": 5},
    17: {"vocab": 28, "blocks": 5},
    18: {"vocab": 32, "blocks": 5},
    19: {"vocab": 32, "blocks": 5},
    20: {"vocab": 30, "blocks": 5},
}


def _fail(errors, lesson_order, message):
    errors.append(f"HSK4 lesson {lesson_order}: {message}")


def main():
    errors = []
    for lesson_order, expected in EXPECTED.items():
        lesson = HSK4_LOWER_PDF_MATERIALS.get(lesson_order)
        if not lesson:
            _fail(errors, lesson_order, "missing lesson data")
            continue

        vocab = lesson.get("vocabulary") or []
        grammar = lesson.get("grammar") or []
        blocks = lesson.get("dialogues") or []
        if len(vocab) != expected["vocab"]:
            _fail(errors, lesson_order, f"expected {expected['vocab']} vocab items, got {len(vocab)}")
        if len(grammar) != 5:
            _fail(errors, lesson_order, f"expected 5 grammar items, got {len(grammar)}")
        if len(blocks) != expected["blocks"]:
            _fail(errors, lesson_order, f"expected {expected['blocks']} blocks, got {len(blocks)}")

        word_nos = {int(item.get("no") or 0) for item in vocab if isinstance(item, dict)}
        grammar_nos = {int(item.get("no") or 0) for item in grammar if isinstance(item, dict)}
        seen_block_nos = set()
        for block in blocks:
            block_no = int(block.get("block_no") or 0)
            if block_no in seen_block_nos:
                _fail(errors, lesson_order, f"duplicate block_no {block_no}")
            seen_block_nos.add(block_no)
            if not block.get("word_nos"):
                _fail(errors, lesson_order, f"block {block_no} missing word_nos")
            if not block.get("grammar_nos"):
                _fail(errors, lesson_order, f"block {block_no} missing grammar_nos")
            missing_words = [no for no in block.get("word_nos", []) if int(no) not in word_nos]
            missing_grammar = [no for no in block.get("grammar_nos", []) if int(no) not in grammar_nos]
            if missing_words:
                _fail(errors, lesson_order, f"block {block_no} has missing word numbers {missing_words}")
            if missing_grammar:
                _fail(errors, lesson_order, f"block {block_no} has missing grammar numbers {missing_grammar}")

            lines = block.get("dialogue") or []
            if not lines:
                _fail(errors, lesson_order, f"block {block_no} missing dialogue lines")
            for index, line in enumerate(lines, 1):
                for key in ("zh", "pinyin", "uz", "ru", "tj"):
                    if not str(line.get(key) or "").strip():
                        _fail(errors, lesson_order, f"block {block_no} line {index} missing {key}")
                if "都有得懂" in str(line.get("zh") or ""):
                    _fail(errors, lesson_order, f"block {block_no} line {index} has typo 都有得懂")

    if errors:
        raise SystemExit("\n".join(errors))
    print("ok: HSK4 lower PDF lessons 11-20")


if __name__ == "__main__":
    main()
