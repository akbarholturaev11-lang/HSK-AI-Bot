# Onboarding → first lesson → second lesson (2026-11-16)

Branch: `feat/onboarding-first-two-lessons-20261116`. Base: `main@c1fccb45a47245f503d5f2449847f3404fa044fe`. **Never merge/push to main without explicit owner permission.**

## Scope/checklist

- [x] Inspect live main, root AGENTS.md/AI_RULES.md, PROJECT_MEMORY.md, frontend performance and localization rules.
- [x] Inspect canonical HSK-AI-Design-System AGENTS.md and existing PWA/Android navigation.
- [x] Inspect Analytics Integrity, Unified Error Monitoring architecture and existing lesson start/complete events.
- [x] Create isolated feature branch from verified main.
- [ ] PWA: verified onboarding → direct first available lesson, including Starter 0/HSK2.0/3.0, no bypass.
- [ ] Android: verified onboarding → direct first available lesson without notification/widget/map interruption, preserving gates.
- [ ] PWA: only confirmed first lesson completion → centered next-lesson CTA, no automatic rank screen or sheet.
- [ ] Android: only confirmed first lesson completion → centered next-lesson CTA, no automatic rank screen or sheet.
- [ ] Localize new text in canonical UZ/RU/TJ catalogs and generate frontend/Android output.
- [ ] Reuse existing Analytics and Monitoring flows; check necessary coverage, dedupe and nonblocking behavior.
- [ ] Add targeted tests, run feasible checks and inspect CI.
- [ ] Review changed files, access/XP/rank/streak/payment/daily-plan regressions, compare branch with main.
- [ ] Short final report: files, test results, risks, real-device limitations.

## Verified baseline

- PWA Li onboarding `li-onboarding-runtime.js::toCourse` sets `autostart=1` only for a narrow HSK2.0 saved lesson case; safe course boot already handles `resume=1`, `autostart=1` and Starter 0; server lesson start grant remains authoritative.
- PWA `course-v3.html::applyLessonDone` updates server-confirmed lesson completion, XP/streak/rank then renders celebration; `startLesson` preserves paid/access/grant checks. On subsequent lessons, existing completion UI stays unchanged.
- Android `MainActivity.kt` already has onboarding auto-start, but deliberately skips nhsk levels and gates launch behind notification/widget prompts. Lesson completion uses a verified `LessonOutcome.Completed` and existing rank/streak presentation.
- Existing Analytics V10 has PWA `lesson_started` events and server completion events. The Analytics Integrity plan describes Android native lesson-start instrumentation as a prior gap; confirm latest runtime before claiming it fixed. Unified Monitoring `diag.v1` and catalog should be reused.
- This document is a task-specific checklist, not a second Analytics Integrity/Monitoring progress log.

## Release gates

- Do not change entitlement, grading, purchases, XP awards or personal-account authority.
- No telemetry call may hold lesson navigation. Never treat a client event as a verified completed lesson.
- No main merge; physical iPhone Safari and Android device acceptance remain separate from CI.
