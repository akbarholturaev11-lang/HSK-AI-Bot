#!/usr/bin/env python3
"""Fail-closed resolution for the main(055de820)+P3(7d113214) staging merge.

Run ONLY after a real git merge --no-commit on the dedicated integration branch.
Preserve Git's nonconflicting hunks, main account/Android security changes,
and P3 generated local-first catalogs. Never rewrite production/main.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

CONFLICT = re.compile(r"^<<<<<<< HEAD\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]+\n", re.M | re.S)
CASES = {
    ".github/workflows/backend-ci.yml": 1,
    "AI_RULES.md": 1,
    "PROJECT_MEMORY.md": 2,
    "android/app/src/main/java/com/pomp/hskai/feature/foundation/FoundationScreen.kt": 1,
    "android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileScreen.kt": 1,
    "app/static/course-v3.html": 4,
    "app/static/course_v3_memorize.html": 1,
    "graphify-out/GRAPH_REPORT.md": 1,
    "graphify-out/graph.json": 1,
    "tests/test_subscription_service.py": 1,
}


def resolve(path: str, index: int, ours: str, theirs: str) -> str:
    if path == ".github/workflows/backend-ci.yml":
        assert "hsk-i18n-source-audit.json" in theirs
        assert "Guard QA schema-only bootstrap" in ours
        # The P3 side continues a preceding run: | block; attach main steps AFTER.
        return theirs + ours
    if path == "AI_RULES.md":
        assert "## Scope- and risk-based testing" in ours
        assert "## Existing course localization ownership" in theirs
        return theirs.replace("## E2E Smoke Test Rule", "## Scope- and risk-based testing")
    if path == "PROJECT_MEMORY.md":
        if index == 0:
            assert "payments.user_id" in ours and "feature branch only" in theirs
            return ours + (
                "- P3 local-first lesson translations remain a separately reviewed "
                "UZ/RU/TJ display-only catalog; keep all source Chinese, scoring, "
                "graded homework, Pro checks and canonical account ownership intact.\n"
            )
        assert "Mini App stroke order" in ours and "Localization expansion" in theirs
        return ours + theirs
    if path.endswith("/foundation/FoundationScreen.kt"):
        assert "R.string.lesson_check" in ours
        assert "R.string.hsk_course_check" in theirs
        # The generated central catalog is the source; never show the chosen
        # answer tokens as the button caption.
        return "                text = stringResource(R.string.hsk_course_check),\n"
    if path.endswith("/profile/ProfileScreen.kt"):
        assert not ours.strip()
        assert "private fun NotificationsCategoriesSheet" in theirs
        assert "private fun StudyReminderSettingsSheet" in theirs
        return theirs
    if path == "app/static/course-v3.html":
        if index == 0:
            assert "aria-label" in ours and "courseMessage" in theirs
            return ours.replace('setAttribute("aria-label",T().say)', 'setAttribute("aria-label",courseMessage("say",T().say))')
        if index == 1:
            assert "LESSON_PRON_CANCEL" in ours and "var RT=" in theirs
            # Main repaired microphone cleanup and presentation; P3's separate
            # hardcoded translations would regress both. Existing courseMessage
            # and generated catalog remain active in the rest of the file.
            return ours
        if index == 2:
            assert "if(st.cancelled)return" in ours
            return ours.replace("setBtn(T().say)", 'setBtn(courseMessage("say",T().say))')
        assert index == 3 and "if(st.cancelled)return" in ours
        return ours.replace("setBtn(T().say)", 'setBtn(courseMessage("say",T().say))')
    if path == "app/static/course_v3_memorize.html":
        assert "MEMORIZE_LIMIT_UI" in theirs and "return_page=course_v3_memorize.html" in ours
        # Preserve main's safe return to course page and local-first labels.
        translated = theirs.split("function initData()", 1)[0]
        return translated + ours
    if path.startswith("graphify-out/"):
        # Generated snapshots conflict because two branches built different code
        # revisions. Keep production snapshot and explicitly mark regeneration.
        return ours
    if path == "tests/test_subscription_service.py":
        assert "user_id=1" in ours
        return ours
    raise RuntimeError("Unrecognized conflict: " + path)


def main() -> None:
    found = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=U"], text=True
    ).splitlines()
    if set(found) != set(CASES):
        raise RuntimeError(
            f"Unexpected conflict set: missing={sorted(set(CASES)-set(found))};"
            f" extra={sorted(set(found)-set(CASES))}"
        )
    for path in found:
        file = Path(path)
        source = file.read_text(encoding="utf-8")
        actual = 0

        def replace(match: re.Match[str]) -> str:
            nonlocal actual
            index = actual
            actual += 1
            return resolve(path, index, match.group(1), match.group(2))

        merged = CONFLICT.sub(replace, source)
        if actual != CASES[path] or "<<<<<<< HEAD" in merged or ">>>>>>> " in merged:
            raise RuntimeError(f"Unresolved conflict: {path}; chunks={actual}")
        file.write_text(merged, encoding="utf-8")
        subprocess.check_call(["git", "add", "--", path])
        print(f"RESOLVED {path}: {actual} conflict chunk(s)", flush=True)
    unresolved = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=U"], text=True
    ).strip()
    if unresolved:
        raise RuntimeError("Unmerged files remain: " + unresolved)
    # Assert both main Android auth sources and new course locale resources
    # survived the automatic non-conflicting merge.
    required = [
        "android/app/src/main/java/com/pomp/hskai/core/auth/AuthRepository.kt",
        "android/app/src/main/java/com/pomp/hskai/feature/profile/IdentitiesSheet.kt",
        "app/static/course_v3_data/hsk-course-i18n.js",
        "app/static/course_v3_data/p3-grammar-reservation.js",
        "localization/ui/uz/course.json",
    ]
    absent = [path for path in required if not Path(path).exists()]
    if absent:
        raise RuntimeError(f"Lost required main/P3 assets: {absent}")
    html = Path("app/static/course-v3.html").read_text()
    if "applyReservedP3Grammar" not in html or 'setAttribute("aria-label",courseMessage("say",T().say))' not in html:
        raise RuntimeError("Lost P3 reservation hook or centralized mic label")
    print("All ten real git conflicts resolved; both main and P3 assets present.")


if __name__ == "__main__":
    main()
