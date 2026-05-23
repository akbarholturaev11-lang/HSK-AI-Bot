import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.course_engine_service import get_step_order


LEVELS = {
    "hsk1": 15,
    "hsk2": 15,
    "hsk3": 20,
}


def _lesson(level: str, order: int) -> dict:
    return importlib.import_module(f"scripts.seed_{level}_lesson_{order:02d}").LESSON


def verify() -> None:
    errors = []
    for level, max_lesson in LEVELS.items():
        for order in range(1, max_lesson + 1):
            lesson = _lesson(level, order)
            blocks = json.loads(lesson.get("dialogue_json") or "[]")
            steps = get_step_order(SimpleNamespace(**lesson))
            seen_grammar_nos = set()

            for block in blocks:
                if not isinstance(block, dict):
                    continue
                block_no = int(block.get("block_no") or 0)
                if not block_no:
                    continue

                if f"block_grammar_{block_no}" not in steps:
                    errors.append(f"{level.upper()} lesson {order} block {block_no}: missing block_grammar step")

                grammar_notes = block.get("grammar_notes") or []
                grammar_nos = block.get("grammar_nos") or []
                if not grammar_notes and not grammar_nos:
                    errors.append(f"{level.upper()} lesson {order} block {block_no}: no grammar material")

                note_patterns = [
                    note.get("pattern")
                    for note in grammar_notes
                    if isinstance(note, dict) and note.get("pattern")
                ]
                if len(note_patterns) != len(set(note_patterns)):
                    errors.append(
                        f"{level.upper()} lesson {order} block {block_no}: duplicate grammar notes {note_patterns}"
                    )

                for grammar_no in grammar_nos:
                    if grammar_no in seen_grammar_nos:
                        errors.append(
                            f"{level.upper()} lesson {order} block {block_no}: duplicate grammar_no {grammar_no}"
                        )
                    seen_grammar_nos.add(grammar_no)

    if errors:
        raise SystemExit("\n".join(errors))

    print("HSK1/HSK2/HSK3 block grammar has no duplicate grammar_nos and every block has grammar material.")


if __name__ == "__main__":
    verify()
