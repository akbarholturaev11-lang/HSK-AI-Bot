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

## Pilot 2: independent exit and conditional transfer checks (draft PR #142)

- N1 source lesson 1 ends with **three independent checks**: respectful teacher greeting, listening comprehension for a thank-you expression, and building a student farewell.
- Each objective has a **different follow-up example** in an appended retry bank:
  1. Respond respectfully to a teacher's `大家好！` after missing a polite greeting.
  2. Recognize `不客气！` after confusing `谢谢！` in audio.
  3. Build `老师，再见！` after missing `同学们，再见！`.
- Mini App and the updated Android ViewModel both skip an alternate question if the corresponding independent check was correct; otherwise only that question appears. Incorrect answers still follow existing heart/mistake reporting and the UI shows the teacher-written explanation.
- Sections `learning_exit_check` (3) and `learning_repair_bank` (4) are **appended** after the unchanged existing N1 checkpoint sections (1–2). Total cards 12 → 18, preserving all 12 original section/card `material_ref` values.
- The new sections use existing `quick_quiz`, `listening_choice`, and `sentence_builder` types; server card count and Android parse count must match 18. Source content is authored in `scripts/hsk30/learning_overlays/nhsk1_lesson_01_exit.json`, reapplied during regeneration.
- Resume: Mini App retains a lightweight pilot failure map in its existing per-lesson mastery cache. Android's older resume store records only an index; if interrupted **after** the first exit question, the native client conservatively offers all alternate questions rather than incorrectly skipping missed skills. A future release should persist the exact per-objective result on Android.
- Existing Android APK builds **do not have conditional skip code**: while they can render every extra standard card, old builds would offer all three retry cards unconditionally after a server release. **Release gate:** do not merge/deploy these content changes until the new native build and backend are tested together and an old-APK compatibility approach is approved.
- This checks immediate transfer within the lesson; it does **not** establish 1-day or 7-day retention. No subscription, paywall, TJS unlock, trial or free-limit logic was changed.

## Pilot 3: connect the N1 learner's daily plan to errors (draft PR #142)

Existing architecture retained: `CourseTodayService` reads `LearningSignalsService`, calls the pure `DailyPlanService` and freezes task identity per level/day. Both Mini App and Android consume the same `today` payload. New rules do **not** bypass the authoritative access checker.

**Important server bug fixed:** `CourseLessonMistakeMaterialService` previously rejected all `nhsk1..3` material refs. They are now accepted through the same checked-in-JSON, reference/answer verification used for HSK 2.0. HSK 3.0 N1 exit and retry errors can therefore enter `CourseMistakeService` and the existing target-based review bank.

- `LearningSignalsService` isolates HSK 3.0 mistake weights from HSK 2.0 rows; the 2.0 view keeps legacy null-level rows.
- Listening recognition errors use `material.format`, even when canonical mistake category is `pronunciation`. Actual spoken pronunciation errors still rank separately.
- Both `mistakes_total` and weakness evidence ignore unresolvable `target_key="-"` rows.
- For `nhsk1`, available mistake review is promoted above optional activities when the learner has outstanding mistakes. `continue_lesson` remains first; access-locked review is never issued; HSK 3.0 mock exam is still absent.
- The daily plan is **frozen by local day**: same-day task identities are intentionally not rewritten mid-session. Fresh weakness evidence guides the next generated day plan.
- Integration tests: real SQLite track isolation, listening classification, missing targets; original-json N1 mistake canonicalization and forgery rejection; N1 priority and feature-lock regressions.

**Still not implemented:** accurate per-objective persistence for *correct* answers, explicit mastery-driven deferred planning, word-SRS-due task selection, and 1-/7-day retention analytics. These need their own schema/event tracking and careful migration, rather than conflating them with mistake counts.

## N1-wide checkpoint implementation (2026-10-12)

**15/15 textbook lesson checkpoints have independent assessment and alternate example banks.**

- Source lesson 1 remains manually authored: **3 objective checks + 3 different retries**, with 27 additional contextual explanations across its first four runtime parts.
- Source lessons 2–15: **2 independent checks + 2 different conditional retries each** (56 added cards), derived deterministically from **the original unit's own verified vocabulary, tonal pinyin, three-language translations and source grammar example translations**. Exactly **62 new checkpoint/repair cards** across the 15 lessons (6 + 56); the 27 contextual explanations are separate edits. Each unit uses four newly generated cards; no new card type.
- Total 103 N1 runtime parts remain in their original order; only the 15 final parts receive extra **appended** section 3 (exit) and section 4 (alternate bank). Existing question keys and material references are unchanged.
- Source-backed builder: `scripts/hsk30/build_nhsk1_source_assessment.py`. It fails if there are insufficient distinct authenticated source words or grammar translations. Neither AI-generated Chinese, new unverified translation nor fabricated answer key is required.
- **Mini App** and **new Android app** dynamically skip a retry objective if its independent check was correct. Mistake capture is canonicalized against the server's checked-in JSON.
- **Old Android APK protection:** the new Android client advertises `X-HSK-N1-Transfer: v1`. Without this capability header the server projects the same N1 payload **minus section 4** and recomputes total card/preview count. Older clients thus still receive the ordinary learning material and section 3 checks, but not conditional-only cards. No access policy or entitlement is changed. Desktop keeps its existing server course adapter and renders standard cards; it has no conditional-skip client in this pilot.
- **Daily plan** keeps frozen same-day task identity and tracks errors by HSK 2.0/3.0 separately, promoting available N1 mistake review. Correct per-objective history and delayed retention metrics are future additions.
- **CI gate:** regenerates **all 103 N1 runtime parts** and fails on any checked-in diff. Checks structure, translations, answer-index correctness and 15 authored/source-generated checkpoint contracts. Backend separately checks the old/new-APK projection and trial/limit regressions. Native unit tests exercise real checkpoint JSON parsing across all 15 source lessons.

### Release review and outstanding limitations

The automated gates prove deterministic generation, source provenance and cross-client schema compatibility; they do **not** prove the educational value of distractors or naturalness of each translation. Review the bilingual wording and audio on physical devices before declaring pedagogical sign-off. Android offline lesson cache may initially contain an earlier payload; old APKs receive the server's version-safe projection when online. Ship the new APK alongside the server update, but never claim that a deployed Android build updates itself via JSON alone.

Do not merge this draft while required CI is failing. Controlled rollout: (1) full CI green, (2) manual Mini App and Android UZ/RU/TJ + old APK regression, (3) merge/deploy, (4) audit completion rate and mistake review conversion without claiming causal improvement from mere CI success.
