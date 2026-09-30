"""HSK 3.0 runtime integration guardrails.

Stdlib-only verifier used by GitHub Actions. It checks that the generated HSK
3.0 runtime is actually wired into Mini App/payment/practice/AI Voice paths,
not merely present as JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
DATA = STATIC / "course_v3_data"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"FAIL: {label}: missing {needle!r}")


def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"FAIL: {label}: forbidden {needle!r}")


def check_runtime() -> None:
    parts = json.loads((DATA / "parts_manifest.json").read_text(encoding="utf-8"))
    expected = {"nhsk1": 15, "nhsk2": 15, "nhsk3": 18}
    for level, source_lessons in expected.items():
        info = parts.get(level) or {}
        total = int(info.get("total_parts") or 0)
        if total <= 0:
            raise SystemExit(f"FAIL: {level}: missing total_parts")
        lesson_files = sorted((DATA / level).glob("lesson_*.json"))
        if len(lesson_files) != total:
            raise SystemExit(
                f"FAIL: {level}: runtime lessons {len(lesson_files)} != {total}"
            )
        manifest = json.loads(
            (DATA / level / "manifest.json").read_text(encoding="utf-8")
        )
        if manifest.get("content_status") != "runtime_ready":
            raise SystemExit(f"FAIL: {level}: runtime manifest is not ready")
        if int(manifest.get("lesson_count") or 0) != total:
            raise SystemExit(f"FAIL: {level}: flat lesson count mismatch")
        if int(manifest.get("source_lesson_count") or 0) != source_lessons:
            raise SystemExit(f"FAIL: {level}: source lesson count mismatch")


def check_course_ui() -> None:
    html = read("app/static/course-v3.html")
    for needle in (
        'HSK30_LEVELS=["nhsk1","nhsk2","nhsk3"]',
        '"/api/v3/course-tracks"',
        '"/api/v3/course-tracks/switch"',
        'mode","hsk30_unlock"',
        'plan","hsk30_unlock"',
        "showHsk30AccessGate()",
        "showHsk30TestSoon()",
        'if(isHsk30Level((MAP&&MAP.level)||getSelectedLevel()))',
        '"next_level_pending" in d',
    ):
        require(html, needle, "course-v3.html")
    forbid(html, '"nhsk3":"nhsk4"', "course-v3.html")


def check_checkout() -> None:
    html = read("app/static/subscription.html")
    service = read("app/services/subscription_miniapp_service.py")
    for needle in (
        '"hsk30_unlock"',
        "HSK30_UNLOCK_MODE",
        'state.mode==="hsk30_unlock"',
        'plan:state.plan',
    ):
        require(html, needle, "subscription.html")
    for needle in (
        '"hsk30_unlock"',
        "Hsk30UnlockService(self.session).payment_eligibility(user)",
        "HSK30_UNLOCK_PLAN_TYPE",
        '"discount_applied": False',
        '"discount_source": "none"',
    ):
        require(service, needle, "subscription_miniapp_service.py")


def check_access() -> None:
    main = read("app/main.py")
    lesson_start = read("app/api/miniapp_entitlements.py")
    access = read("app/services/entitlements/lesson_access.py")
    levels = read("app/services/course_levels.py")
    require(main, '"lesson_gate_hsk30.js": "application/javascript"', "main.py")
    require(main, '"hsk30-words.js": "application/javascript"', "main.py")
    require(lesson_start, "content_level(user.level)", "miniapp_entitlements.py")
    require(access, 'normalized_level.startswith("nhsk")', "lesson_access.py")
    require(access, "track_service = CourseTrackService(self.session)", "lesson_access.py")
    require(access, "await track_service.hsk30_access(user)", "lesson_access.py")
    require(access, "await track_service.hsk30_feature.is_level_live(normalized_level)", "lesson_access.py")
    require(levels, 'key="nhsk4"', "course_levels.py")
    require(levels, "if not candidate or not candidate.selectable:", "course_levels.py")


def check_practice() -> None:
    index = read("app/services/course_v3_word_index.py")
    vocab = read("app/services/course_v3_vocab.py")
    for needle in (
        "lesson_gate_hsk30.js",
        "HSK30_WORD_GATE",
        '"hsk30":',
        '"nhsk1", "nhsk2", "nhsk3"',
    ):
        require(index, needle, "course_v3_word_index.py")
    require(vocab, '("nhsk1", "nhsk2", "nhsk3")', "course_v3_vocab.py")

    for name in ("course_v3_recognition.html", "course_v3_pronunciation.html"):
        html = read(f"app/static/{name}")
        require(html, "/course_v3_data/hsk30-words.js", name)
        require(html, "/course_v3_data/lesson_gate_hsk30.js", name)
        require(html, "window.HSK30_WORDS", name)
        require(html, "window.HSK30_WORD_GATE", name)
        forbid(
            html,
            'function wordSource(){return isHsk30()?(window.HSK30_WORDS||[]):wordSource()}',
            name,
        )


    memorize = read("app/static/course_v3_memorize.html")
    require(memorize, "lesson_gate_hsk30.js", "course_v3_memorize.html")
    require(memorize, "window.HSK30_CHAR_GATE", "course_v3_memorize.html")

    test_center = read("app/static/course_v3_test.html")
    require(test_center, "HSK30_SOON", "course_v3_test.html")
    require(test_center, "showHsk30Soon()", "course_v3_test.html")


def check_voice() -> None:
    voice = read("app/services/voice_practice_service.py")
    for level in ("nhsk1", "nhsk2", "nhsk3"):
        require(voice, f'"{level}"', "voice_practice_service.py")
    require(voice, "New HSK 3.0 N1", "voice_practice_service.py")
    require(voice, "New HSK 3.0 N3", "voice_practice_service.py")


def main() -> int:
    check_runtime()
    check_course_ui()
    check_checkout()
    check_access()
    check_practice()
    check_voice()
    print("OK: HSK 3.0 runtime integration guardrails")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
