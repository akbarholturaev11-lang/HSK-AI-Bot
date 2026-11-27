# Proposal

## Why

Test the owner's hypothesis that repetitive lessons, weakly perceived learning gains and incomplete connections between existing tools reduce return to HSK AI. A richer lesson is a hypothesis, not a proven improvement: compare the current product with one coherent treatment using canonical-account 50/50 randomization and identical learning assessments.

Baseline: fetched GitHub `origin/main` **45506d37d3b8dbfa09fc30607276ee61cad1fec3**, 2026-11-27. This is a **plan only**; runtime implementation, experiment activation and deployment are not performed by creating it. Existing adaptive-review, flashcard and value-first plans cover narrower delivered mechanisms, not universal composition, learning transfer or a global experiment. Their ownership remains intact; this change owns only the proposed additional behavior.

## What Changes

- Start with three reusable formats: a two-character audio scene with a pause/challenge, a bounded real-life role response, and finding/repairing an error. Translation, missing-turn selection, repetition and independent response are modes, not separate engines. Reuse existing picture-pronunciation cards; do not commission a new image system in V1. These are selected for current material reuse and measurable transfer, not asserted to be the most effective before testing.
- Extend the existing lesson plan to select eligible formats using goals, verified weakness, available time and recent **shown** formats, while preserving protected teaching, source order, objectives and exit checks. Avoid solving variety by adding unlimited tasks to short lessons.
- Connect confirmed results to existing adaptive review, Mistakes, word mastery/flashcards, Daily Plan and optional AI Voice. Show specific evidence of progress; reuse current feedback, XP/streak and accessibility settings without changing reward economics.
- Build the same versioned, capability-aware contract for all currently packaged HSK 2.0/3.0 levels, UZ/RU/TJ and learner platforms. Missing/unsafe material uses a recorded safe fallback. Future levels use the same compiler when their existing content/access QA admits them; this proposal does not unlock unpublished courses.
- Persist one experimental arm per canonical account, 50/50 for new and existing learners. Separate assignment, actual delivery and actual exposure. Retain arm across sign-in devices, locales, course switches, kill and restart.
- Add common server-scored transfer/recall checks to both arms, bounded attempt measurement, symmetric optional satisfaction and an aggregate experiment projection in the existing Admin Statistics surface. Preregister D7 qualified learning return, D1/D14, completion/abandonment, knowledge and satisfaction contracts; distinguish historical descriptive comparisons from randomized evidence.
- Keep a default-OFF server gate with a bounded online emergency stop and base-flow resume; no pilot-lesson rewriting or recruitment phase. Internal synthetic/content/device QA precedes one global 50/50 activation across supported surfaces.

## Capabilities

### New Capabilities

- `contextual-course-exercises`: source-grounded reusable scenes, role responses and error repair, including material eligibility and media fallback.
- `course-session-composition`: budgeted varied lesson composition with protected objectives and stable resume/compatibility.
- `learning-transfer-evidence`: common assessment, truthful progress feedback and connections to existing learning tools.
- `account-learning-experiment`: canonical stable allocation, exposure, measurement, analysis and emergency rollback.

### Modified Capabilities

None. The existing `admin-real-analytics` ownership, privacy, bounded-read and unavailable-data requirements apply unchanged; the new experiment is an additional typed projection under them. Adaptive review and flashcards remain governed by their existing active changes, not re-specified here.

## Impact

Affected areas: existing lesson-plan/adaptive services and course adapters; additive experiment/attempt snapshots and migration; authenticated Telegram/PWA/Android/Desktop transports; Mini App/PWA renderer, Android Direct/Play and paired macOS/Windows learning renderers; minimal legacy bot bridge; canonical local catalogs; analytics/monitoring registry and existing Admin experiment disclosure. Public website remains an entry surface, not a new lesson player.

**Scope reconciliation:** current `AGENTS.md` prioritizes PWA/Android and freezes Desktop. The owner's explicit request here for all platforms is recorded as a task-specific planning exception for paired Desktop learning support and legacy bot compatibility, not a general product unfreeze. Old installed clients remain functional through version negotiation and fallback; neither their existence nor a shared API proves treatment exposure.

Authoritative context (relative to this change): [root rules](../../../AGENTS.md), [AI rules](../../../AI_RULES.md), [memory](../../../PROJECT_MEMORY.md), [P3 active checkpoint](../../../localization/P3_ACTIVE_HANDOFF.md), [localization ownership](../../../localization/README.md), [content QA](../../../localization/AI_CONTENT_QA_POLICY.md), [adaptive review](../course-adaptive-lesson-engine/), [flashcards](../course-interactive-flashcards/), [value-first learning](../value-first-learning-pro/), [analytics](../../../docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md), [monitoring](../../../docs/monitoring/MONITORING_CONTEXT.md), [performance](../../../docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md), [Smart Reminder authority](../../../docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md). No parallel feature handoff or progress log is introduced.

Preserve canonical account/access/payment/referral authority, official course completion and +20-XP dedupe, source/P3 hashes, original graded keys and sequence, Telegram SDK, existing Daily Plan identities and SRS schedules. Excluded: subscription changes, account merging, rewriting every lesson, a new AI/voice/image provider, new currencies, notification campaigns and broad redesign. Principal risks are objective loss during trimming, invalid generated content, audio/ASR failure, cross-client drift, contaminated allocation and misleading analytics. Rollback stops treatment and resumes the saved base cursor while retaining progress, assignment and evidence; populated schema is never erased to roll back.
