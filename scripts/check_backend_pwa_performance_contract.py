#!/usr/bin/env python3
"""CI gate for persistent Backend / PWA performance acceptance.

This guard checks policy links and whether changed implementation is accompanied
by regression tests. It does NOT claim static checks prove latency, CLS or
correct caching; browser and production-like measurements remain necessary.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

POLICY = "docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md"
AGENTS = ("AGENTS.md", "AI_RULES.md")
REQUIRED_HEADINGS = (
    "## Required: Initial Render & Progressive Loading (PWA)",
    "## Backend performance master checklist",
    "## PWA performance master checklist",
    "## Future feature invariant",
    "## Performance acceptance for every future change",
    "## Release gate",
)


def is_backend_source(path: str) -> bool:
    return (
        path == "app/main.py"
        or path == "requirements.txt"
        or path.startswith(("app/api/", "app/services/", "app/repositories/", "app/db/", "alembic/"))
    ) and path.endswith((".py", ".txt"))


def is_pwa_source(path: str) -> bool:
    # Shared assets count too: changes to a Mini App asset can affect the PWA.
    return path.startswith("app/static/") and path.endswith(
        (".html", ".js", ".mjs", ".css", ".ts", ".tsx", ".jsx")
    )


def is_regression_test(path: str) -> bool:
    return path.startswith("tests/") and Path(path).name.startswith("test_") and path.endswith(
        (".py", ".js", ".ts")
    )


def is_web_regression_test(path: str) -> bool:
    return is_regression_test(path) and (
        path.startswith("tests/e2e/")
        or any(keyword in path.lower() for keyword in (
            "pwa", "iphone", "course_v3", "dictionary", "miniapp", "frontend",
            "browser", "shell", "web", "ui", "static",
        ))
    )


def change_issues(paths: list[str]) -> list[str]:
    paths = [p for p in paths if p]
    backend = [p for p in paths if is_backend_source(p)]
    web = [p for p in paths if is_pwa_source(p)]
    tests = [p for p in paths if is_regression_test(p)]
    issues = []
    if backend and not tests:
        issues.append(
            "Backend implementation changed without any changed tests/test_* "
            "regression test. Add a focused test for the affected API/DB/cache path."
        )
    if web and not any(is_web_regression_test(p) for p in paths):
        issues.append(
            "PWA/shared frontend implementation changed without a changed "
            "browser/PWA/course/UI regression test. Cover first paint, loading, "
            "error/retry or the relevant user flow."
        )
    return issues


def policy_issues(root: Path) -> list[str]:
    issues = []
    policy = root / POLICY
    if not policy.is_file():
        return [f"Missing mandatory contract: {POLICY}"]
    body = policy.read_text(encoding="utf-8")
    for heading in REQUIRED_HEADINGS:
        if heading not in body:
            issues.append(f"{POLICY}: missing section {heading}")
    for path in AGENTS:
        agent_file = root / path
        if not agent_file.is_file() or POLICY not in agent_file.read_text(encoding="utf-8"):
            issues.append(f"{path}: must explicitly link to {POLICY}")
    for test in (
        "tests/e2e/test_pwa_initial_shell.py",
        "tests/e2e/test_pwa_progressive_sections.py",
    ):
        if not (root / test).is_file():
            issues.append(f"Missing behavioral PWA regression: {test}")
    return issues


def changed_files(base: str) -> list[str]:
    if not base:
        return []
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", f"{base}^{{commit}}"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        return subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"],
            text=True,
        ).splitlines()
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Cannot compare to base {base!r}; checkout with fetch-depth: 0."
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="", help="base commit for PR/push diff")
    parser.add_argument("--enforce-change-tests", action="store_true", help="require regression-test cochanges (PR or main integration)")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    issues = policy_issues(args.root)
    try:
        changed = changed_files(args.base)
        if args.enforce_change_tests:
            issues.extend(change_issues(changed))
    except RuntimeError as exc:
        issues.append(str(exc))
    if issues:
        for message in issues:
            print(f"::error::{message}")
        return 1
    print(f"Backend/PWA policy contract OK; examined {len(changed)} changed files.")
    print("NOTE: CI still requires behavioral tests and real-world performance evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
