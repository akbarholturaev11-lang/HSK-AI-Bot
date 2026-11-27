# Proposal

## Why

UIUX-008 / COURSE-FLASHCARDS-001 (`HSK_AI_UI_UX_IMPROVEMENTS.md`, section
"UIUX-008") asks for card exercises **inside ordinary lessons**, with a real,
checkable answer instead of self-assessment. The owner's 2026-11-17 brief fixes
the first format: a stacked deck of **picture pronunciation cards** — the
learner looks at a picture of an already-learned word and says the Chinese
word; the existing pronunciation check grades it.

The same brief adds a second, coupled requirement: lessons must not grow long.
The lesson length follows the learner's onboarding answer
("Kuniga necha daqiqa vaqtingiz bor?", `course_miniapp_profiles.daily_minutes`).
When a lesson is shortened, the practice that matches the learner's goals
(`goal`, `goals_json`) and stated focus (`preferred_focus`) is kept, and the
goal also shifts the length itself.

A direct client-only task is insufficient: two clients (iPhone PWA / Telegram
Mini App `course-v3.html`, Android `feature/lesson`) must make the identical
selection, and both derive `material_ref` from card positions, so trimming must
be expressed as an explicit, server-computed plan that never renumbers cards.

Authoritative sources: `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`,
`HSK_AI_UI_UX_IMPROVEMENTS.md` (UIUX-008), `openspec/changes/course-adaptive-lesson-engine`
(UIUX-007, kept separate by owner decision 2026-11-17).

## What Changes

- New server `lesson_plan` object attached to the lesson payload of the signed
  Mini App/PWA content endpoint and the Android lesson endpoint, only when the
  rollout flag admits the learner. It contains:
  - `omit`: `(section_no, card_no)` pairs of optional practice cards dropped to
    fit the length budget (original positions; `material_ref` unchanged);
  - `picture_review`: 1–10 already-learned words with an exact picture, and
    the section anchor where the deck is placed.
- PWA and Android render the deck as **one lesson step**: stacked 3D cards,
  picture front, 🎙️ microphone, the existing Skip control, a 160° flip that
  reveals hanzi (always), pinyin (per the existing pinyin setting) and
  translation after the server verdict. Correct → bounce, green, slide out;
  wrong → bounce, amber, reveal, card returns to the end of the queue. Skip
  passes the current card without counting it correct.
- An unreliable recognition (empty transcript) gives no verdict and asks to
  repeat; the server no longer records a pronunciation mistake/mastery for an
  empty transcript.
- Feature flags `COURSE_LESSON_PLAN_ENABLED` (default off),
  `COURSE_LESSON_PLAN_ROLLOUT_PERCENT`, `COURSE_LESSON_PLAN_ALLOWLIST`.

Excluded: Desktop (macOS/Windows) lesson renderer, Practice/Daily Plan/AI Voice,
UIUX-007 adaptive review limits and logic, new analytics events, XP/streak/
completion API, self-assessment ✅/❌ cards, pinyin multiple choice.

## Capabilities

### New Capabilities
- `course-lesson-length-and-picture-review`: server-planned lesson length
  budget by onboarding minutes/goals/focus and the in-lesson picture
  pronunciation deck on PWA and Android.

### Modified Capabilities
<!-- none: existing course-progress/pronunciation specs are not tracked in openspec/specs -->

## Impact

- Backend: new `app/services/course_lesson_plan_service.py`, curated
  `app/services/data/lesson_picture_words.json`, flags in `app/config.py`,
  plan attachment in `app/api/miniapp_entitlements.py` and
  `app/services/android_course_service.py`, empty-transcript guard in
  `app/services/voice_practice_service.py`.
- PWA/Mini App: `app/static/course-v3.html` (queue build + deck renderer),
  canonical copy in `localization/ui/*/course.json` and generated bundles.
- Android: `data/lesson/LessonParser.kt`, `domain/model/Lesson.kt`,
  `feature/lesson/*`, new canonical XML bundle under `localization/android`.
- No migration, no access/payment/entitlement change, no change to lesson
  completion payloads, XP, streak, daily plan or UIUX-007.
- Rollback: turn `COURSE_LESSON_PLAN_ENABLED` off; both clients then run the
  unmodified lesson (no plan in payload).
- Cost: each picture card is one existing pronunciation STT call; free users
  stay under the existing `FREE_PRONOUNCE_DAILY` quota — when it is reached the
  deck ends and the lesson continues.
