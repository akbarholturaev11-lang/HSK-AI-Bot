# Mobile lesson question layout — 2026-10-09

## Symptom
Telegram Mini App lesson/review screenshots (Russian, iPhone) showed the long question in a narrow column beside the monkey mascot, causing a very tall card and placing answer options well below the fold.

## Root cause
`syncLessonCoachLine()` moved every direct `#f-body > .qcard` or `.dia` into `#f-coach-slot` inside the mascot row. That row does not scroll with the choices and leaves too little width for long localized text.

## Changes on `codex/cloud-ai`
- `app/static/course-v3.html`: On viewports <= 600 CSS px, keep question and choices together in scrollable `#f-body`. The same applies to long materials, dialogs, and gap prompts even on wider viewports.
- Compact mascot, question padding/type and option wrapping on smaller screens; preserve short desktop side-by-side cards.
- `tests/e2e/test_lesson_mobile_responsive.py`: regression for Russian question and four options at widths 320/375/390/430/768.

## Validation
- HTML inline JavaScript parsed successfully with a syntax-only check.
- Static invariants for breakpoint, layout guard and wrapping were verified.
- **Playwright browser E2E was not run in the connected tool environment**; no device screenshot comparison or main deploy has been performed.

## Required local checks before `main`
1. Run `pytest -q tests/e2e/test_lesson_mobile_responsive.py` on a checkout that includes the two change commits.
2. Open Telegram Mini App lesson/review flows at 320x568, 375x667, 390x844 and 430x932; check Russian/Tajik/Uzbek, long text, dialog, audio and gap-fill, and landscape rotation.
3. Confirm no horizontal overflow, mascot/card separation, option clickability, bottom action bar, progress preservation, and paywall/lesson completion.
4. After a clean E2E and visual result, promote the isolated commits to latest `main` without overwriting concurrent changes; then align collaboration branches.

## Risk
CSS is scoped to narrow screens; JS changes only card placement. Course data, answer checking, premium limits and payments are unchanged. Separate content QA: screenshot says “какое предложение” although options are single Chinese characters; this copy issue is outside the responsive-layout fix.
