#!/usr/bin/env bash
# Run Codex CLI in read-only review mode against current repository changes.
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cd "$REPO_ROOT"

DIFF=$(git diff)
DIFF_CACHED=$(git diff --cached)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
BASE_BRANCH="${BASE_BRANCH:-main}"

FULL_DIFF=""
if [[ -n "$DIFF_CACHED" ]]; then
  FULL_DIFF="$DIFF_CACHED"
fi
if [[ -n "$DIFF" ]]; then
  FULL_DIFF="${FULL_DIFF}${DIFF}"
fi

if [[ -z "$FULL_DIFF" ]]; then
  FULL_DIFF=$(git diff "${BASE_BRANCH}...${BRANCH}" 2>/dev/null || true)
fi

if [[ -z "$FULL_DIFF" ]]; then
  echo "No changes detected against ${BASE_BRANCH}. Nothing to review."
  exit 0
fi

PROMPT="You are a senior software engineer performing a thorough code review. \
You must NOT modify any files — this is a READ-ONLY review.

Analyze the following git diff and report all issues grouped by severity:

SEVERITY LEVELS:
- CRITICAL: data loss, security vulnerabilities (SQLi, XSS, auth bypass, secrets exposed), crashes
- HIGH: logic bugs, regressions, broken error handling, missing input validation, race conditions
- MEDIUM: edge cases not handled, architectural concerns, performance issues, missing tests for critical paths
- LOW: code style, minor improvements, missing comments on non-obvious logic

For each issue use this format:
[SEVERITY] file.py:line — Short title
  Problem: what is wrong and why it matters
  Fix: concrete suggestion

Check specifically for:
1. Bugs and regressions introduced by the diff
2. Security issues (injection, auth, secrets, IDOR, open redirects)
3. Architecture violations (business logic in wrong layer, missing abstraction)
4. Edge cases (empty input, None/null, concurrent access, large payloads)
5. Error handling (silent failures, missing rollback, swallowed exceptions)
6. Missing tests for changed critical paths
7. Database query safety (N+1, missing transactions, unindexed filters)

After the issue list, add a short SUMMARY section with total counts per severity.

--- GIT DIFF START ---
${FULL_DIFF}
--- GIT DIFF END ---"

echo "=== Codex Review: branch '${BRANCH}' vs '${BASE_BRANCH}' ==="
echo ""

codex exec \
  --sandbox read-only \
  --ephemeral \
  --ignore-user-config \
  "$PROMPT"
