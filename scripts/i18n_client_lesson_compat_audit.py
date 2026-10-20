#!/usr/bin/env python3
"""P0 client lesson delivery audit; read-only, source-level evidence only.

Checks the Mini App signed lesson-content APIs and the native bearer lesson
APIs. Does not make network requests, import server modules, load secrets or
touch application data. Staging and installed-client acceptance remain open.
"""
from __future__ import annotations

import argparse
import ast
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
    "android_app": "android/app/src/main/java/com/pomp/hskai/HskAiApplication.kt",
    "android_main_activity": "android/app/src/main/java/com/pomp/hskai/MainActivity.kt",
    "desktop_lesson": "desktop/ui/js/lesson.js",
    "desktop_bridge": "desktop/ui/js/bridge.js",
    "desktop_rust": "desktop/src-tauri/src/lib.rs",
    "backend_android_api": "app/api/android_course.py",
    "backend_desktop_api": "app/api/desktop_course.py",
    "backend_desktop_service": "app/services/desktop_course_service.py",
    "backend_android_service": "app/services/android_course_service.py",
    "backend_miniapp_content": "app/api/miniapp_entitlements.py",
    "backend_main": "app/main.py",
}
ANDROID_PRIVATE = "api/v3/android/course/lesson/{lessonOrder}"
DESKTOP_PRIVATE = "/api/v3/desktop/course/lesson/{lesson_order}"


def _has(src: str, pattern: str) -> bool:
    return bool(re.search(pattern, src, re.S))


def _function_source(source: str, name: str) -> str:
    nodes = [
        node for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if len(nodes) != 1:
        raise ValueError(f"Mini App function identity changed: {name}")
    return ast.unparse(nodes[0])


def contract(sources: dict[str, str]) -> dict:
    if set(sources) != set(FILES):
        raise ValueError("Client source list changed; review lesson call sites")
    miniapp = sources["miniapp"]
    android_api = sources["android_api"]
    android_repo = sources["android_repository"]
    android_cache = sources["android_cache"]
    android_app = sources["android_app"]
    android_activity = sources["android_main_activity"]
    desktop_js = sources["desktop_lesson"]
    bridge = sources["desktop_bridge"]
    rust = sources["desktop_rust"]
    backend_android = sources["backend_android_api"]
    backend_desktop = sources["backend_desktop_api"]
    backend_service = sources["backend_desktop_service"]
    android_service = sources["backend_android_service"]
    backend_miniapp = sources["backend_miniapp_content"]
    backend_main = sources["backend_main"]
    skip_test = _function_source(backend_miniapp, "v3_course_lesson_skip_test")
    skip_questions = _function_source(backend_miniapp, "_skip_test_questions")

    checks = {
        "miniapp": {
            "authenticated_lesson_url": _has(
                miniapp,
                r'var url="/api/v3/lesson/content/"\+level\+"/"',
            ),
            "fetches_with_signed_identity_and_no_store": _has(
                miniapp,
                r'fetch\(lessonDataUrl\(lv,n\),\{headers:\{"X-Telegram-Init-Data":INIT_DATA\},cache:"no-store"\}\)',
            ),
            "n1_revision_bound_to_url": _has(
                miniapp, r'return level==="nhsk1"\?url\+"\?content_rev="',
            ),
            "sales_preview_has_dedicated_projection": _has(
                miniapp, r'fetch\("/api/v3/lesson/sales-preview"',
            ),
            "foundation_has_dedicated_authenticated_read": _has(
                miniapp, r'fetch\("/api/v3/lesson/foundation"',
            ),
            "skip_test_uses_dedicated_bounded_read": _has(
                miniapp, r'_apiPost\("/api/v3/lesson/skip-test"',
            ),
        },
        "miniapp_server": {
            "signed_telegram_identity": _has(
                backend_miniapp,
                r'def _authenticated\([\s\S]{0,500}extract_verified_webapp_user_id',
            ),
            "lesson_access_is_non_consuming": _has(
                backend_miniapp,
                r'v3_course_lesson_content\([\s\S]{0,2200}LessonAccessService\(session\)\.status\([\s\S]{0,250}consume=False',
            ),
            "lesson_sequence_is_checked": _has(
                backend_miniapp,
                r'v3_course_lesson_content\([\s\S]{0,2000}lesson_order > completed \+ 1',
            ),
            "skip_test_uses_signed_canonical_account": _has(
                skip_test,
                r'await _authenticated\(request\).*?if not telegram_id:.*?status_code=401'
                r'.*?get_by_telegram_id\(telegram_id\).*?if not user:.*?status_code=403',
            ),
            "skip_test_checks_selected_level_and_bounds": (
                "level not in COURSE_LEVELS or lesson_order < 1" in skip_test
                and "user_level = content_level(getattr(user, 'level', None))" in skip_test
                and "level != user_level" in skip_test
                and "course_level_not_allowed" in skip_test
                and "total = total_parts(level)" in skip_test
                and _has(skip_test, r'if not total or lesson_order > total:\n')
            ),
            "skip_test_checks_foundation_and_shared_access_before_read": _has(
                skip_test,
                r'await _foundation_is_blocked\(session, user, level\).*?android_foundation_required'
                r'.*?LessonAccessService\(session\)\.status\(user, level=level, '
                r'lesson_order=lesson_order, completed=completed, consume=False\)'
                r".*?if not access\.get\('allowed'\):"
                r'\s*return _private_content_response\(access, status_code=403\)'
                r'\s*lesson = _read_course_lesson\(level, lesson_order\)',
            ),
            "skip_test_allows_locked_projection_without_progress_changes": (
                not _has(skip_test, r'if [^\n]*lesson_order[^\n]*completed')
                and not _has(skip_test, r'\.(?:commit|unlock_lesson|set_current_lesson_and_step)\(')
                and not _has(skip_test, r'progress\.[a-z_]+\s*=')
            ),
            "skip_test_returns_question_projection_only": _has(
                skip_test,
                r'questions = _skip_test_questions\(lesson\) if lesson else \[\]'
                r".*?return _private_content_response\(\{'ok': True, 'level': level, "
                r"'lesson_order': lesson_order, 'questions': questions\}\)",
            ),
            "skip_test_is_bounded": _has(
                skip_questions,
                r'secrets\.SystemRandom\(\)\.sample\(candidates, min\(6, len\(candidates\)\)\)',
            ),
            "all_private_content_responses_are_no_store": (
                _has(backend_miniapp, r'PRIVATE_CONTENT_HEADERS\s*=\s*\{[^}]*"Cache-Control":\s*"no-store"')
                and "headers=PRIVATE_CONTENT_HEADERS" in _function_source(
                    backend_miniapp, "_private_content_response",
                )
            ),
        },
        "legacy_public_route": {
            "old_lesson_json_route_returns_404": _has(
                backend_main,
                r'status_code=404,\s*content=\{"ok": False, "error": "lesson_content_not_found"\}',
            ),
            "root_json_route_allows_fixed_maps_only": _has(
                backend_main,
                r'COURSE_V3_PUBLIC_MAP_FILES = frozenset\([\s\S]{0,200}nhsk3\.json',
            ) and _has(
                backend_main,
                r'async def course_v3_data_file\([\s\S]{0,1800}filename not in COURSE_V3_PUBLIC_MAP_FILES',
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
            "dao_supports_lesson_cache_clear": 'DELETE FROM course_lesson_cache' in android_cache,
            "repository_clear_wipes_both_account_caches": _has(
                android_repo, r'suspend fun clearCache\(\)\s*\{\s*'
                r'dao\.clear\(\)\s*lessonDao\?\.clear\(\)',
            ),
            "app_session_cleanup_calls_repository_clear": _has(
                android_app, r'suspend fun clearLocalData\(\)\s*\{\s*'
                r'courseRepository\.clearCache\(\)',
            ),
            "sign_out_invokes_cache_cleanup": _has(
                android_activity, r'authRepository\.logout\([^)]*\)\s*'
                r'app\.clearLocalData\(\)',
            ),
            "unauthenticated_ui_clears_cache": _has(
                android_activity, r'AuthState\.Unauthenticated\s*->[\s\S]{0,850}'
                r'app\.clearLocalData\(\)',
            ),
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
        "status": "REGRESSION" if failures else "SOURCE_CONTRACT_OK_AUTHENTICATED_MINIAPP_REVIEW",
        "checks": checks,
        "failures": failures,
        "migration_priority": "miniapp_authenticated_lesson_api_runtime_verification",
        "limitations": [
            "Mini App source now uses signed per-request lesson APIs; source contracts do not prove deployed authorization or cache behavior.",
            "Locked-lesson skip-test reads are bounded question projections; lesson content and starts still enforce sequence.",
            "Android and Desktop secure API source contracts do not prove live deployment or account-state behavior.",
            "Native Android offline cache reuses already-fetched lessons only on Offline/Timeout errors, per source.",
            "Account session cache clearing is evidenced by source call chains; an actual device/session switch still needs E2E QA.",
            "Play/direct share main-source Retrofit lesson transport; build/flavor E2E remains untested.",
            "Old cached Mini App pages and previously released clients may still call the retired public URL; verify refresh and migration behavior in staging.",
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
    except (OSError, SyntaxError, UnicodeError, ValueError) as exc:
        print("P0 cross-client lesson compatibility audit:", exc, file=sys.stderr)
        return 1
    print("P0 cross-client lesson audit:", report["status"],
          "regressions:", len(report["failures"]))
    return int(bool(report["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
