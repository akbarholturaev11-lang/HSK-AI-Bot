# Design

## Context

Product source: `HSK_AI_UI_UX_IMPROVEMENTS.md` → `UIUX-007 / COURSE-ADAPTIVE-001`.
Facts below were read from `main` `c1fccb45` on 2026-11-16.

| Building block | Current behaviour reused |
| --- | --- |
| `course_mistakes` | Per-question evidence rows with `material_json.format`, `source`, `level`, `lesson_order`, `last_seen_at`, `target_key`. |
| `course_mistake_targets` + `CourseMistakeTargetStore` | One row per learner/category/target; `upsert(new_mistake=True)` reopens a cleared target and resets Xatolarim progress. |
| `mistake_drill_factory` | `build_question`, `validate_question`, `public_question`, UZ/RU/TJ instructions, listening only with audio. |
| `CourseWordMasteryService` | Box rule 0/1/3/7/21 days; a correct answer advances only when due; a wrong answer resets to box 0. |
| `CourseWordMasteryService.context` | Learner level, current part and local-day offset. |
| `CourseMiniAppAnalyticsService.record_server_event` | Event registry, savepoint isolation, `(user, event, dedupe_key)` uniqueness. |

Verified mistake sources (server graded the answer against its own key):
`lesson` (canonical `material_ref` re-grade), `test`, `training`, `challenge`,
and new `adaptive`. Excluded: `recognition`, `memorize` (client graded),
`voice` (LLM judgement), `pronunciation` (ASR score).

## Goals / Non-Goals

**Goals:**
- At most three adaptive questions per ordinary lesson, from verified weak
  material only, shown between ordinary cards on PWA and Android.
- Server-only grading against a stored snapshot; per-skill spaced review;
  identical official lesson results with the feature ON or OFF.
- Instant rollback by flag; safe degradation on any failure.

**Non-Goals:**
- UIUX-008 flashcards, Desktop, Daily Plan/Practice/AI Voice consumers.
- Changing Xatolarim clearing, its XP, lesson JSON, grading or completion.
- A second SRS, mistake store or LLM-generated lessons.

## Decisions

### D1. State lives on the existing target row
`course_mistake_targets` gains `adaptive_state_json` (Text, default `{}`) and
`adaptive_due_on` (Date, nullable, indexed with `user_id`). One row stays the
single learning record for both Xatolarim and adaptive review; no parallel
mistake table. Alternative (new per-skill table) rejected: a second store of
the same weakness would drift from Xatolarim.

State shape (`v: 1`):

```json
{"v":1,
 "skills":{"pinyin":{"phase":"active","box":1,"due":"2026-11-17",
   "ok_days":["2026-11-16"],"need":3,"wrong":0,
   "evidence_at":"2026-11-15T10:00:00+00:00","last_day":"2026-11-16"}},
 "final":{"clear_at":"2026-11-10T08:00:00+00:00","status":"passed"}}
```

### D2. Skill detection
Each verified evidence row maps to one skill from its stored format, falling
back to category: meaning (`meaning_guess`, `translation_choice`,
`word_choice`, `meaning_choice`, `sentence_meaning`, `quick_quiz`), hanzi
(`hanzi_choice`, `character_choice`, `hanzi_from_pinyin`), pinyin
(`pinyin_choice`, `listening_pinyin`, tone formats), listening
(`listening_choice`, `audio_choice`, `sentence_listening`, `listen_builder`),
grammar (`sentence_builder`, `reverse_builder`, `gap_fill`, `dialog_cloze`,
`dialog_context`, `dialog_choice`, `correct_choice`, `grammar_correction`).
Category fallback: grammar → grammar, character → hanzi,
pronunciation → pinyin, word → meaning. A mistake on pinyin therefore never
schedules a meaning check for the same word.

### D3. Lazy derivation, no hot-path hooks
The planner derives state when it builds a plan: a skill appears when verified
evidence exists; if an evidence row's `last_seen_at` is newer than the skill's
`evidence_at`, the cycle restarts (box 0, due today, `ok_days` cleared).
Xatolarim clearance is detected from `status='cleared'` and `cleared_at`.
Lesson completion, `record_items` and Xatolarim completion are not modified.

### D4. Schedule and retirement
`schedule_box(box, due_on, correct, today)` is extracted from
`CourseWordMasteryService._schedule` and used by both services (one SRS rule).
A correct adaptive answer counts as *independent* only if the skill was due and
no correct answer was already counted that local day. `need` = 3, or 4 when the
skill has two or more verified wrong answers (history plus adaptive). When
`len(ok_days) >= need` the skill becomes `retired`; it keeps its box/due, so it
returns as low-priority maintenance (7 → 21 days). A word target is also
handed to `course_word_mastery` exactly like Xatolarim clearance. A verified
wrong adaptive answer restarts that skill, sets `need` to 4 and calls
`CourseMistakeTargetStore.upsert(new_mistake=True, source="adaptive")` — the
existing rule for any new verified mistake. Correct adaptive answers never
change Xatolarim `passed_formats`, `status` or XP.

### D5. Xatolarim final check
A target cleared by Xatolarim with `cleared_at <= now - 3 days` and
`final.clear_at != cleared_at` gets one `final_check` item. Correct → every
skill on the target retires and `final` records the clearance. Wrong → the
target reopens through `upsert`, the skill restarts. One check per clearance.

### D6. Plan selection
Bounded queries: (1) active targets, (2) `adaptive_due_on <= today`,
(3) cleared targets due for a final check, (4) evidence rows for those
targets. Same HSK track only (`nhsk*` vs legacy), kinds `word`/`sentence`
only, at least one verified source, not answered today, not solely from the
lesson being opened. Order: final checks, active due skills (difficult first,
oldest due, lowest box), retired maintenance. At most one item per target and
three per plan. Questions come from `mistake_drill_factory` restricted to the
skill's formats and the client's declared formats, seeded with
`adaptive:<user>:<plan_key>` so order varies by day but is stable on retry.

### D7. Plan persistence and contract
New table `course_adaptive_plans`: `user_id`, `plan_key`
(`level:lesson:day:lang:formats`), `level`, `lesson_order`, `local_day`,
`contract_version`, `language`, `items_json` (server snapshot with answer
keys), `answers_json`, timestamps; unique `(user_id, plan_key)`. Plans older
than 14 days are deleted per user when a new plan is created. Item IDs are
`a<n>:<target>:<format>` and never look like `lesson:<level>:...`.

`POST .../adaptive/plan` `{level, lesson_order, formats, language?}` →
`{ok, enabled, plan:{id, version, level, lesson_order, items:[{id, slot,
kind, skill, question, answered, feedback?}]}}`. `question` is
`public_question` (no key). Disabled/rollout-excluded/failed → `{ok:true,
enabled:false, plan:null}`.

`POST .../adaptive/answer` `{plan_id, item_id, selected_index |
selected_tokens}` → `{ok, item_id, correct, correct_index?, correct_answer,
explanation, duplicate}`.

Server checks: authenticated actor; requested level equals the learner's
current course level and `1 <= lesson_order <= completed+1` (lesson attempt);
answer plan belongs to the actor, same HSK track, `local_day` not older than
yesterday, item in snapshot, answer shape valid. The first answer per item is
final; repeats return the stored feedback with `duplicate: true` and no
state change. User row lock serializes plan creation and answers.

Transports: Telegram (`/api/v3/adaptive/*`, initData), PWA
(`/api/v3/pwa/adaptive/*`, cookie + CSRF + same-origin), Android
(`/api/v3/android/adaptive/*`, bearer). One router module, one service.

### D8. Client overlay
Both clients keep the base queue and cursor. Eligible slots are boundaries
after a graded base card, not in the first two cards, before any exit-ticket,
`learning_exit_check`/`learning_repair_bank` section, and not in preview,
test or challenge flows. Items are spread evenly over eligible boundaries; an
unanswered item whose slot is already behind the resume cursor moves to the
next eligible boundary. Plan loading never delays the first card (async,
timeout); failure → no overlay. The overlay card uses existing option styles
and its own feedback bar; it does not call the lesson's heart, streak,
objective, mistake, resume or interaction-analytics code. PWA keeps an
offline outbox (max 10, per user scope) and replays answers on the next plan
load; Android keeps an in-memory retry queue for the attempt.

### D9. Flags, analytics, monitoring
`COURSE_ADAPTIVE_ENABLED` (false), `COURSE_ADAPTIVE_ROLLOUT_PERCENT` (100,
stable hash of `user_id`), `COURSE_ADAPTIVE_ALLOWLIST` (user IDs),
`COURSE_ADAPTIVE_SHADOW_ENABLED` (false; selection computed and counted, no
state writes, nothing delivered). Server events: `adaptive_assigned`,
`adaptive_answer_verified` (payload `skill`, `kind`, `correct`, `counted`,
`relearned`, `retired`), `adaptive_shadow_planned`; PWA client event
`adaptive_shown`. None of them is a lesson event or a master state. Technical
failures log with `logger.exception` and degrade to no overlay; a learner's
wrong answer is not an incident.

## Risks / Trade-offs

- [Wrong adaptive answer reopens a Xatolarim target] → this is the existing
  rule for a new verified mistake; XP rules are untouched because `adaptive`
  is not a trusted reward source.
- [Retirement does not clear the Xatolarim target] → deliberate: Xatolarim
  clearing rules stay owner-defined; listed as an owner question.
- [Lesson mistakes are client-reported selections] → the server re-grades the
  selection against the canonical key; a forged report can only add review for
  oneself and grants nothing.
- [Same lesson opened on two clients the same day] → separate plans (format set
  in the key); state writes stay deduplicated per local day.
- [Android process death while offline] → the unsent adaptive answer is lost;
  no official result is affected.
- [JSON state on a shared row] → serialized by the user row lock used by all
  writers.
