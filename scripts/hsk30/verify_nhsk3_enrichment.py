from __future__ import annotations

from pathlib import Path

from nhsk3_adapter import (
    TRANSLATION_DIR,
    Nhsk3TranslationError,
    load_seed_lesson,
)


def main() -> int:
    files = sorted(TRANSLATION_DIR.glob("lesson_*.json"))
    if len(files) != 18:
        raise SystemExit(
            f"FAIL: expected exactly 18 N3 translation sidecars, found {len(files)}"
        )

    translated = 0
    for path in files:
        order = int(path.stem.split("_")[-1])
        try:
            seed = load_seed_lesson(order)
        except Nhsk3TranslationError as exc:
            raise SystemExit(f"FAIL: {path.name}: {exc}") from exc
        translated += 1
        print(
            f"OK lesson {order:02d}: "
            f"title={seed['title']} translation_layer=complete"
        )

    if translated != 18:
        raise SystemExit(f"FAIL: N3 enrichment coverage {translated}/18")
    print("OK: N3 enrichment coverage 18/18")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
