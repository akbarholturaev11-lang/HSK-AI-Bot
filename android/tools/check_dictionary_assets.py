#!/usr/bin/env python3
"""The dictionary entry's bundled material must be complete and current.

The dictionary works with no connection because everything an entry shows
travels inside the APK: the word list, the writing order (checked by
`check_stroke_assets.py`), and what this checks —

  assets/hsk-examples.json    rebuilt from the course and must match it
  assets/hanzi-parts.json     rebuilt from dictionary_insights/parts and must
                              match it
  assets/audio/words/*.mp3    one per word, or the listen button is silent

A generated file nobody regenerated looks exactly like one that was never
meant to have more in it, so the stale case fails here rather than on a
phone.

Usage:  python3 tools/check_dictionary_assets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_dictionary_insights as insights  # noqa: E402
from build_word_audio import AUDIO_DIR, audio_name  # noqa: E402

REBUILD_INSIGHTS = "python3 android/tools/build_dictionary_insights.py"
REBUILD_AUDIO = "python3 android/tools/build_word_audio.py"


def main() -> int:
    problems: list[str] = []

    examples, parts, part_problems = insights.build()
    problems += [f"parts: {problem}" for problem in part_problems]
    for path, expected in ((insights.EXAMPLES_ASSET, examples), (insights.PARTS_ASSET, parts)):
        if not path.is_file():
            problems.append(f"{path.name} is missing — run: {REBUILD_INSIGHTS}")
        elif path.read_text(encoding="utf-8") != expected:
            problems.append(f"{path.name} is out of date — run: {REBUILD_INSIGHTS}")

    words = sorted({str(w.get("h") or "").strip() for w in insights.dictionary_words()} - {""})
    silent = [word for word in words if not (AUDIO_DIR / audio_name(word)).is_file()]
    if silent:
        problems.append(
            f"{len(silent)} word(s) have no bundled audio, e.g. {''.join(silent[:8])} — run: {REBUILD_AUDIO}"
        )

    # Every entry the dictionary can open shows a real sentence, and every
    # character in it is explained. A new word without either is a gap on a
    # phone that nothing else would report.
    covered = json.loads(examples)["words"]
    explained = json.loads(parts)["chars"]
    chars = {ch for word in words for ch in word if insights.HANZI.match(ch)}
    if unexampled := [word for word in words if word not in covered]:
        problems.append(
            f"{len(unexampled)} word(s) have no example sentence, e.g. {', '.join(unexampled[:5])} "
            "— add them to android/tools/dictionary_insights/examples*.json"
        )
    if unexplained := sorted(chars - set(explained)):
        problems.append(
            f"{len(unexplained)} character(s) have no breakdown, e.g. {''.join(unexplained[:10])} "
            "— add them to android/tools/dictionary_insights/parts/"
        )

    if problems:
        for problem in problems:
            print(f"dictionary assets: {problem}")
        return 1

    print(
        f"dictionary assets are current: {len(words)} words with audio, "
        f"examples for {len(covered)}, breakdowns for {len(explained)}/{len(chars)} characters"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
