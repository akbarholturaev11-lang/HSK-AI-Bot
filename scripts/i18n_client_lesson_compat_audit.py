#!/usr/bin/env python3
"""P0 client lesson delivery audit; read-only, source-level evidence only.

Protects the existing separation between Mini App's legacy unauthenticated
lesson GET and the two native bearer-authenticated lesson APIs. Does not make
network requests, import server modules, load secrets or touch application data.
A known Mini App gap remains a human review blocker, not a test failure.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "miniapp": "app/static/course-v3.html",
    "android_api": "android/app/src/main/java/com/pomp/hskai/data/api/AndroidCourseApi.kt",
    "android_repository": "android/app/src/main/java/com/pomp/hskai/data/repository/CourseRepository.kt",
    "android_cache": "android/app/src/main/java/com/pomp/hskai/data/local/LessonCache.kt",
    "desktop_lesson": "desktop/ui/js/lesson.js",
    "desktop_bridge": "desktop/ui/js/bridge.js",
    "desktop_rust": "desktop/src-tauri/src/lib.rs",
    "backend_android_api": "app/api/android_course.py",
    "backend_desktop_api": "app/api/desktop_course.py",
    "backend_desktop_service": "app/services/desktop_course_service.py",
    "backend_android_service": "app/services/android_course_service.py",
}
MINIAPP_PUBLIC = "/course_v3_data/"
ANDROID_PRIVATE = "api/v3/android/course/lesson/{lessonOrder}"
DESKTOP_PRIVATE = "/api/v3/desktop/course/lesson/{lesson_order}"


def _has(src: str, pattern: str) -> bool:
    return bool(re.search(pattern, src, re.S))


def contract(sources: dict[str, str]) -> dict:
    if set(sources) != set(FILES):
        raise ValueError("Client source list changed; review lesson call sites")
    miniapp = sources["miniapp"]
    android_api = sources["android_api"]
    android_repo = sources["android_repository"]
    android_cache = sources["android_cache"]
    desktop_js = sources["desktop_lesson"]
    bridge = sources["desktop_bridge"]
    rust = sources["desktop_rust"]
    backend_android = sources["backend_android_api"]
    backend_desktop = sources["backend_desktop_api"]
    backend_service = sources["backend_desktop_service"]
    android_service = sources["backend_android_service"]

    checks = {
        "miniapp": {
            "legacy_public_lesson_url": _has(
                miniapp,
                r'var url="/course_v3_data/"\+level\+"/lesson_"\+',
            ),
            "fetches_legacy_url_directly": _has(
                miniapp, r"fetch\(lessonDataUrl\(lv,n\)",
            ),
            "n1_revision_bound_to_url": _has(
                miniapp, r'return level==="nhsk1"\?url\+"\?content_rev="',
            ),
        },
        "android": {
            "native_bearer_lesson_endpoint": _has(
                android_api,
                r'@GET\("api/v3/android/course/lesson/\{lessonOrder\}"\)'
                r'\s*suspend fun lesson\(\s*@Header\("Authorization"\)',
            ),
            "repository_sends_bearer": 'api.lesson("Bearer $token", lessonOrder, accessRef)' in android_repo,
            "service_inherits_lesson_policy": _has(
                android_service,
                r'async def lesson\([\s\S]{0,460}await super\(\)\.lesson\(',
            ),
            "offline_cache_limited_to_transport_failures": _has(
                android_repo,
                r"private suspend fun cachedLesson\([\s\S]{0,500}"
                r"error !is ApiError\.Offline && error !is ApiError\.Timeout",
            ),
            "logout_clears_lesson_cache": 'DELETE FROM course_lesson_cache' in android_cache,
            "server_bearer_required": _has(
                backend_android,
                r'@router\.get\("/api/v3/android/course/lesson/\{lesson_order\}"\)'
                r'[\s\S]{0,650}bearer_access_token\(request\)',
            ),
            "server_response_no_store": _has(
                backend_android,
                r'async def android_course_lesson\([\s\S]{0,1150}'
                r'"Cache-Control": "no-store"',
            ),
        },
        "desktop": {
            "lesson_js_uses_bridge": "this.bridge.lessonData(this.lessonOrder)" in desktop_js,
            "bridge_dispatches_tauri_command": _has(
                bridge,
                r'lessonData\(lessonOrder\)[\s\S]{0,180}COMMANDS\.lessonData',
            ),
            "rust_private_lesson_endpoint": _has(
                rust,
                r'async fn desktop_lesson_data\([\s\S]{0,470}'
                r'authenticated_get_json\([\s\S]{0,230}'
                r'/api/v3/desktop/course/lesson/\{lesson_order\}',
            ),
            "rust_authenticated_get_bearer": _has(
                rust, r'async fn authenticated_get_json\([\s\S]{0,420}'
                r'\.bearer_auth\(&token\)',
            ),
            "server_rejects_missing_token": _has(
                backend_desktop,
                r'async def desktop_course_lesson\([\s\S]{0,540}_access_token\(request\)',
            ),
            "server_enforces_lesson_sequence": _has(
                backend_service,
                r'async def lesson\([\s\S]{0,1000}lesson_order > completed \+ 1',
            ),
            "server_consumes_entitlement_on_lesson": _has(
                backend_service,
                r'async def lesson\([\s\S]{0,1650}'
                r'LessonAccessService\(self\.session\)\.status\([\s\S]{0,200}'
                r'consume=True',
            ),
            "server_response_no_store": _has(
                backend_desktop,
                r'async def desktop_course_lesson\([\s\S]{0,760}'
                r'"Cache-Control": "no-store"',
            ),
        },
    }
    failures = []
    for platform, names in checks.items():
        for key, result in names.items():
            if not result:
                failures.append({"platform": platform, "check": key, "issue": "source_contract_missing"})
    # A pass confirms only a source contract. Do not equate this with HTTP
    # authentication tests or proving no other call site exists.
    return {
        "schema_version": 1,
        "status": "REGRESSION" if failures else "SOURCE_CONTRACT_OK_LEGACY_MINIAPP_REVIEW",
        "checks": checks,
        "failures": failures,
        "migration_priority": "miniapp_legacy_public_lesson_fetch",
        "limitations": [
            "Mini App current public lesson GET still has no request authentication and needs a separate design.",
            "Android and Desktop secure API source contracts do not prove live deployment or account-state behavior.",
            "Native Android offline cache reuses already-fetched lessons only on Offline/Timeout errors, per source.",
            "Play/direct share main-source Retrofit lesson transport; build/flavor E2E remains untested.",
            "Does not inspect every native WebView/network call site or old released APK/desktop binaries.",
        ],
    }


def audit(root: Path = ROOT) -> dict:
    return contract({
        name: (root / file).read_text(encoding="utf-8")
        for name, file in FILES.items()
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        print("P0 cross-client lesson compatibility audit:", exc, file=sys.stderr)
        return 1
    print("P0 cross-client lesson audit:", report["status"],
          "regressions:", len(report["failures"]))
    return int(bool(report["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
