# HSK 3.0 N1 — Learning Engine V2 groundwork

Status: **phase 1 / contract only**. No production lesson, answer key, access, XP, paywall, Android or Mini App flow is changed by this phase.

## Current architecture (checked against main)

- Source: `scripts/hsk30/seed_nhsk1_lesson_XX.py` + verified textbook extraction.
- Runtime: `app/static/course_v3_data/nhsk1/lesson_XX.json`, `nhsk1.json` and `nhsk1/manifest.json`.
- Mini App reads lesson JSON via `lessonDataUrl` / `loadLessonData` in `app/static/course-v3.html` and retains an in-memory cache.
- Android reads the **same server-side JSON** through `/api/v3/android/course/lesson/{lessonOrder}` and uses `LessonParser` with a separate offline cache. New card types require corresponding Android and Mini App renderer support.
- Server entitlements, lesson-completion dedupe, and mistake-record flow remain authoritative.

## Learning design contract (next phase)

For each original textbook lesson (possibly split into multiple runtime parts):

1. **Objective**: what the learner can independently understand or produce.
2. **Teach**: new word in Hanzi, tonal pinyin and UZ/RU/TJ translation with a contextual example.
3. **Understand**: real source-backed dialogue, listening and comprehension checks.
4. **Apply**: grammar in context, credible distractors, gap fill and sentence assembly without leaking the answer.
5. **Repair**: wrong answer -> *reason* -> distinct retry item, not only the correct answer.
6. **Exit check**: independently assess the lesson objectives without teaching hints.
7. **Retention**: use existing mistake/mastery mechanisms rather than a second competing progress database.

Keep the source textbook Chinese and pinyin traceable. Add localizations and new interactive practice as a separate editable layer. Do not copy textbook exercise pages verbatim.

## Compatibility and migration rules

- Preserve `schema_version: 2`, `level: nhsk1`, `lesson_id`, `source_lesson`, `part_no`, `part_count`, and map order.
- `material_ref` is position-based: `lesson:nhsk1:<lesson_id>:section:<section_no>:card:<card_index>`. Reordering or inserting a graded card may remap stored mistakes and resume indices. Before changing card positions, design a stable identity strategy and migration with test coverage.
- A future `learning_design_version` may identify the revised teaching edition, **but must not be deployed until server and both clients can handle version transitions and cache invalidation**.
- Mini App has in-memory lesson cache; Android stores previous server payloads on disk. Plan explicit content revision handling before changing existing cards or answer keys.
- Keep 2.0 / 3.0 track separation, 10 TJS unlock, Pro entitlement, trial and daily limits unchanged.
- Required translation languages are Uzbek, Russian and Tajik (Tajik uses Cyrillic).

## Phase 1 quality gate

Run `python scripts/hsk30/verify_nhsk1_learning_contract.py`.

The read-only checker examines all 103 N1 runtime parts and their 15-unit map. It validates structural consistency, checkpoint position, card formats, answer-index bounds, builder answer tokens, three-language translations and audio-text presence.

Repeated answer choices and missing pedagogical explanations are **warnings** during the existing-content baseline. Structural incompatibilities **fail** the check. A passing structural check does not mean a lesson has been pedagogically approved.

Unit tests: `python -m unittest discover -s tests -p test_nhsk1_learning_contract.py -v`. GitHub Actions checks the source textbook index and the N1 runtime contract for proposed N1 edits.

## First pilot: source lesson 1 (runtime parts 1–4)

1. Record the existing cards, translations, explanations, and learning outcome.
2. Define objective-level success criteria for greetings and the teacher/student exchange.
3. Add context-rich explanations, varied exercise types and an independent checkpoint *without changing existing material references silently*.
4. Implement any needed client/server improvements on both Mini App and Android; add parity tests.
5. Compare first-attempt accuracy, repair success and delayed retention against the original. Expand to the remaining 14 source lessons only after pilot evaluation.

Release discipline: work on an isolated branch, require CI and migration review, then promote to `main`. Do not claim the production lessons have changed merely because the quality gate exists.

## Pilot 1 delivered on draft PR #142 (2026-10-12)

- Original source lesson 1, **runtime parts 1–4** now includes **27 contextual, three-language explanations**. Uzbek explanations use Latin script; Russian and Tajik use Cyrillic.
- Authored source of truth: `scripts/hsk30/learning_overlays/nhsk1_lesson_01.json`.
- `scripts/hsk30/apply_learning_overlays.py` validates part/section/card position, type and the expected correct answer **before** attaching feedback. The Course V3 generator reapplies the editorial overlay during future regenerations.
- Mini App now shows the explanation after both right and wrong responses for **opted-in pilot cards** (`learning_feedback=n1_context_v1`); other levels and server-graded challenge behavior retain existing UX.
- Android's existing lesson feedback panel already shows `card.explanation` for both right and wrong answers, so these content changes need no new Android card type.
- Only card `explanation` and `learning_feedback` metadata changed in the four runtime JSON files. Verified against `main`: 7, 7, 6, 7 updated cards; all other lesson fields including section/card positions, options and answer keys remain identical.
- CI: Python tests, N1 source audit, all 103 N1 lesson parts, Mini App JavaScript syntax, and **generator round-trip diff** passed.

### Not yet delivered

- New assessment/card types, retry-loop and stable ref migration are not part of this pilot.
- Existing offline Android cache and an already-open Mini App may keep an older version until online reload/app reopen; explicit revision-aware invalidation is a separate project.
- CI validates technical consistency and script correctness, **not** the teaching accuracy of every translation or real-device behavior.
- Production `main` remains unchanged until PR approval/merge.
