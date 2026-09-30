#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NORMALIZED = HERE / "normalized" / "nhsk3"
TOC_PATH = HERE / "nhsk3_toc_map.json"

EXPECTED_LESSONS = 18
EXPECTED_TRACK = "hsk30"
EXPECTED_LEVEL = "nhsk3"
EXPECTED_SOURCE_REF = "main"
EXPECTED_SOURCE_PDF = "HSK 3.0 PDF/新HSK3教材.pdf"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path):
    if not path.is_file():
        fail(f"missing file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON: {path}: {exc}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> int:
    toc = load_json(TOC_PATH)
    toc_rows = toc.get("lesson_ranges", [])
    require(toc.get("track") == EXPECTED_TRACK, "TOC track mismatch")
    require(toc.get("level") == EXPECTED_LEVEL, "TOC level mismatch")
    require(toc.get("lesson_count") == EXPECTED_LESSONS, "TOC lesson_count != 18")
    require(toc.get("source_pdf") == EXPECTED_SOURCE_PDF, "TOC source_pdf mismatch")
    require(len(toc_rows) == EXPECTED_LESSONS, f"TOC has {len(toc_rows)} lessons, expected 18")

    toc_by_lesson = {row["lesson"]: row for row in toc_rows}
    expected_numbers = list(range(1, EXPECTED_LESSONS + 1))
    require(sorted(toc_by_lesson) == expected_numbers, "TOC lessons are not exactly 1..18")

    files = sorted(NORMALIZED.glob("lesson_*.json"))
    require(len(files) == EXPECTED_LESSONS, f"found {len(files)} normalized lesson files, expected 18")

    totals = {"objectives":0,"vocabulary":0,"grammar":0,"dialogues":0,"turns":0}
    seen = []

    for path in files:
        data = load_json(path)
        lesson = data.get("lesson")
        require(isinstance(lesson,int), f"{path.name}: invalid lesson")
        seen.append(lesson)
        prefix=f"L{lesson:02d}"
        row=toc_by_lesson.get(lesson)
        require(row is not None, f"{prefix}: TOC row missing")
        require(data.get("track")==EXPECTED_TRACK, f"{prefix}: track mismatch")
        require(data.get("level")==EXPECTED_LEVEL, f"{prefix}: level mismatch")

        source=data.get("source")
        require(isinstance(source,dict), f"{prefix}: source missing")
        require(source.get("ref")==EXPECTED_SOURCE_REF, f"{prefix}: source ref mismatch")
        require(source.get("pdf_path")==EXPECTED_SOURCE_PDF, f"{prefix}: source PDF mismatch")
        start,end=row["pdf_start"],row["pdf_end"]
        require(source.get("pages")==list(range(start,end+1)), f"{prefix}: source pages mismatch")

        title=data.get("title")
        require(isinstance(title,dict), f"{prefix}: title missing")
        require(title.get("hanzi")==row.get("title_hanzi"), f"{prefix}: title mismatch")
        require(bool(title.get("pinyin")), f"{prefix}: title pinyin missing")

        objectives=data.get("objectives")
        vocab=data.get("vocabulary")
        grammar=data.get("grammar")
        dialogues=data.get("dialogues")
        require(isinstance(objectives,list) and objectives, f"{prefix}: objectives empty")
        require(isinstance(vocab,list) and vocab, f"{prefix}: vocabulary empty")
        require(isinstance(grammar,list) and grammar, f"{prefix}: grammar empty")
        require(isinstance(dialogues,list) and dialogues, f"{prefix}: dialogues empty")

        for item in vocab:
            require(bool(item.get("hanzi")), f"{prefix}: vocab hanzi missing")
            require(bool(item.get("pinyin")), f"{prefix}: vocab pinyin missing")
            page=item.get("source_page")
            require(isinstance(page,int) and start<=page<=end, f"{prefix}: vocab page out of range")

        for point in grammar:
            require(bool(point.get("label")), f"{prefix}: grammar label missing")
            page=point.get("source_page")
            require(isinstance(page,int) and start<=page<=end, f"{prefix}: grammar page out of range")
            examples=point.get("examples")
            require(isinstance(examples,list) and examples, f"{prefix}: grammar examples empty")
            for ex in examples:
                require(bool(ex.get("hanzi")), f"{prefix}: grammar example hanzi missing")
                require(bool(ex.get("pinyin")), f"{prefix}: grammar example pinyin missing")

        for block in dialogues:
            page=block.get("source_page")
            require(isinstance(page,int) and start<=page<=end, f"{prefix}: dialogue page out of range")
            turns=block.get("turns")
            require(isinstance(turns,list) and turns, f"{prefix}: dialogue turns empty")
            for turn in turns:
                require(bool(turn.get("speaker")), f"{prefix}: speaker missing")
                require(bool(turn.get("hanzi")), f"{prefix}: dialogue hanzi missing")
                require(bool(turn.get("pinyin")), f"{prefix}: dialogue pinyin missing")

        totals["objectives"]+=len(objectives)
        totals["vocabulary"]+=len(vocab)
        totals["grammar"]+=len(grammar)
        totals["dialogues"]+=len(dialogues)
        totals["turns"]+=sum(len(x["turns"]) for x in dialogues)

    require(sorted(seen)==expected_numbers, "lesson numbers are not exactly 1..18")
    print("OK:", json.dumps({"lessons":18, **totals}, ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
