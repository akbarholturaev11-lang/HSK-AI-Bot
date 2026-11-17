# Proposal

## Why

The owner-approved `UIUX-007 / COURSE-ADAPTIVE-001` decision in
`HSK_AI_UI_UX_IMPROVEMENTS.md` (final owner decision 2026-11-13, implementation
order 2026-11-16) requires personal review questions, built from a learner's
own server-verified mistakes, to appear *inside* the next ordinary lessons on
the iPhone PWA and Android. No Course plan/OpenSpec existed for it, and the
feature touches the database, three client transports and the learning state
shared with «Мои ошибки» (Xatolarim), so a scoped proposal is needed before
code. That section of `HSK_AI_UI_UX_IMPROVEMENTS.md` stays the product source;
this change is the single technical Course OpenSpec for it.

Current evidence (static audit of `main` `c1fccb45`, 2026-11-16):

- Lesson mistakes reach the server only at completion, as `material_ref` plus
  the raw selection; `CourseLessonMistakeMaterialService.canonicalize_items`
  re-grades them against the checked-in lesson JSON. Test, training and
  challenge mistakes are graded from server snapshots. `recognition`/`memorize`
  drills are client-graded, `voice` is LLM-judged and `pronunciation` is ASR-scored.
- `course_mistake_targets` (Alembic 0091) already turns mistakes into word /
  sentence targets; `mistake_drill_factory` builds validated questions
  (`validate_question`) in UZ/RU/TJ; Xatolarim clears a target after three
  distinct formats in server-graded review sessions.
- `CourseWordMasteryService` owns the 1 → 3 → 7 → 21 day box rule
  (`WORD_MASTERY_INTERVALS`), advancing only when an item is due.
- PWA (`course-v3.html`: `buildQueue`, `Flow.next`, `saveLessonResume`,
  `restoreLessonMastery`) and Android (`LessonViewModel`, `LessonParser`)
  keep the lesson card index as the resume cursor and grade locally for instant
  feedback; the server only accepts completion and canonical mistakes.

## What Changes

- A server-built, versioned **Adaptive Lesson Plan** per learner, lesson and
  local day: at most three extra review questions chosen only from verified weak
  targets, stable on retry, persisted with its answer keys.
- A separate **server-graded adaptive answer** endpoint. It updates only the
  personal per-skill review state and never touches lesson score, XP, hearts,
  streak, unlock, `course_progress`, `CourseAttempt` or completion.
- **Per-skill review state** (meaning, hanzi, pinyin/tone, listening, grammar)
  stored on the existing `course_mistake_targets` row and scheduled with the
  existing 1/3/7/21-day rule; three (or four for repeated mistakes)
  independent correct days retire a skill into long-term review.
- **Xatolarim final check:** a target cleared in Xatolarim gets one adaptive
  check in an ordinary lesson at least three days later.
- PWA and Android show the questions **between ordinary cards** as an overlay;
  the canonical lesson JSON, `material_ref`, base queue and resume cursor are
  unchanged.
- Server feature flag `COURSE_ADAPTIVE_ENABLED` (default off), percentage and
  allowlist rollout, and a read-only shadow mode. Turning the flag off returns
  the original lesson instantly without a client release or migration back.

Excluded: UIUX-008 flashcards, Desktop, Practice/Daily Plan/AI Voice
integrations, any change to Xatolarim XP/clearing rules, lesson JSON or grading.

## Capabilities

### New Capabilities
- `course-adaptive-review`: personal server-verified review questions inside
  ordinary lessons, their per-skill spaced schedule and the Xatolarim final check.

### Modified Capabilities
- None. Existing lesson completion, Xatolarim and Word Mastery contracts are
  preserved; this change only reads them and adds a separate overlay.

## Impact

- Backend: `app/services/course_adaptive_lesson_service.py` (new),
  `app/api/course_adaptive.py` (new), `app/db/models/course_adaptive_plan.py`
  (new), `app/db/models/course_mistake_target.py`, migration
  `0158_course_adaptive_lessons`, `app/config.py`, analytics event registry.
- PWA: `app/static/course-v3.html` (overlay only), course UI catalog keys.
- Android: new `AndroidAdaptiveApi`, `AdaptiveLessonRepository`, overlay in
  `LessonViewModel`/`LessonScreen`; strings come from the generated course
  catalog (`hsk_course_adaptive_*`), no separate bundle.
- Risks: a client bug could change lesson counters (guarded by the ON/OFF
  equivalence tests); Xatolarim reopening on a wrong adaptive answer (same rule
  as any new verified mistake); extra DB rows (bounded, 14-day retention).
- Rollback: set `COURSE_ADAPTIVE_ENABLED=false`. Plans stop immediately, clients
  run the base queue. Added columns/table are additive and may stay.
