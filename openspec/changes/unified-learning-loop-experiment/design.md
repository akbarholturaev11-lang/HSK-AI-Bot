# Design

## Context

See [proposal.md](proposal.md) for the hypothesis, authority and platform exception. Audit base: GitHub `origin/main` **45506d37d3b8dbfa09fc30607276ee61cad1fec3** (2026-11-27). Original checkout was `2a3215ed` with unrelated dirty graph/content/assets; this plan uses a separate worktree. Node `v26.13.1`, OpenSpec `1.15.0`; `openspec context --json` resolved the correct worktree. No learner data or production configuration was read. Static source findings do not prove effective production flags or retention effects.

### Verified source and reuse map

Paths/lines refer to the audited base, not graph inference. Graphify's report was built at `a448c5ce`; its `CourseMiniAppEvent` neighborhood helped locate owners, and current source was checked independently. It is not evidence of current completeness.

| Area | Verified current contract / implication |
| --- | --- |
| Courses | `app/services/course_levels.py:23–50`: packaged HSK 2.0 hsk1–4 and HSK 3.0 nhsk1–3; nhsk4 is registered but not selectable. No promise of nonexistent higher-level content. |
| Existing variety | `scripts/gen_course_v3_from_seed.py:1362–1419` already generates dialogue listening, character gaps, cloze, shuffled comprehension and a real-line pronunciation finale. The delta is a coherent voiced scene/role task and history-aware composition, not inventing these task types again. Learned-vocabulary gates exist at `:607–624,1731–1756`. |
| Time/goal plan | `app/services/course_lesson_plan_service.py:232–323` protects teaching/objectives/exit checks, trims optional practice and adds picture review. Selection uses skill and original position; its seed only shuffles pictures. No shown-format history or verified-weakness input. |
| Adaptive review | `course_adaptive_lesson_service.py:693–803,894–986`: account/day/formats plan snapshot, user lock, owned/stale guards and server answer grading. Existing ≤3 review questions use existing mistake targets/SRS. Keep that owner. |
| Pictures | `course_lesson_plan_service.py:147–179` and `app/services/data/lesson_picture_words.json`: previously learned words plus curated emoji; this is already a feature, not general scene-image understanding. |
| Audio | `app/services/tts_service.py:27–48`: one Mandarin Edge voice, Gemini fallback, voice/rate/text cache. Extend preset identity and reuse cache/concurrency gates; no new provider stack. |
| Browser | `app/static/course-v3.html:5030–5096` assigns original material refs before applying plan; `:6386–6400` adaptive overlay. `:5994–6020` dialogue playback is per line, not a sequenced two-speaker scene. Shared PWA/Mini App source requires transport-specific auth. |
| Native | `app/services/android_course_service.py:244–253` attaches plan; `LessonParser.kt:211–213,293–302` handles known types and unsupported fallback. Direct/Play share learning code, not payment permissions. |
| Desktop | `desktop/ui/js/lesson.js:16–23,286–299` consumes old schema/types; `DesktopCourseService.lesson` at `:494–584` lacks the new plan; Rust endpoint allowlist is `desktop/src-tauri/src/lib.rs:315–337`. Existing audio uses IPC (`app/api/desktop_voice.py:1–12`). A shared API alone cannot deliver parity. |
| Tool connections | `voice_practice_service.py:444–546,749–780` already reads SRS/goal/focus/weakness and freezes lesson words. `course_today_service.py:111–120` freezes daily task IDs. Improve contextual handoff; do not create another Daily Plan/SRS. |
| Completion/rewards | `app/main.py:3496–3565` and `desktop_course_service.py:674–699` authorize sequence/start then complete/+20 XP; they do not measure objective mastery. `course_gamification_service.py:81–119` dedupes canonical activity refs. `v3-part:{level}:{order}:complete` remains unchanged. |
| Identity | `account_identity.py:19–44`, `admin_analytics_identity.py:8–44`: canonical account ownership. `identity_link_service.py:124–129,162–170,203–215` does not merge separately owned accounts. |
| Analytics | `course_miniapp_event.py:173–203`: canonical unique event/dedupe keys. `course_miniapp_analytics_service.py:61–75,179–187`: trusted route attribution/savepoint isolation. `pwa_analytics_experiments.py:27–65` has an existing disclosure with a 5,000-detail-row/30-day limit, not a global experiment ledger. |
| Existing experiment | `course_sales_experiment_service.py:215–219,372–414` hashes Telegram ID and restricts eligibility to a sales-specific new HSK1 population. Reuse locking/settings ideas, not its allocation or outcome meanings. |

### Static content inventory

Read-only JSON traversal of `app/static/course_v3_data/<level>/lesson_*.json`, excluding maps/aliases and counting section cards once per packaged part:

| Level | Parts | Parts with two speakers and nonblank Chinese/pinyin/UZ/RU/TJ dialogue |
| --- | ---: | ---: |
| hsk1 | 63 | 63 |
| hsk2 | 72 | 72 |
| hsk3 | 109 | 109 |
| hsk4 | 181 | 181 |
| nhsk1 | 103 | 89 |
| nhsk2 | 73 | 72 |
| nhsk3 | 145 | 139 |
| Total | 746 | 725 |

There are 12,414 section cards and 743 parts with some root dialogue. Dialogue contexts repeat across split textbook parts; 725 is **structural eligibility**, not 725 unique scenes, semantic approval or verified audio coverage. Twenty-one parts need a different eligible exercise/fallback before scene coverage can be claimed. Curated pictures contain 170 distinct entries, with level memberships 30/34/43/30/41/34/52 in the order above.

Static execution of the pure planner against all 746 parts found identical optional selections across changed seeds when pictures were excluded; 5-minute HSK-exam settings omitted 891 cards in aggregate, travel 3,086. This identifies a structural repetition risk, not a measured learner problem. Runtime/provider/device validation remains outstanding. Agent audit attempted planner and card-contract tests in one combined system-Python command: 12 static card tests passed, but planner import lacked `sqlalchemy` and the aggregate command failed. This is not a passed planner suite or runtime acceptance.

Reconcile existing checkpoints instead of cloning them: adaptive tasks 3.6–3.7 and flashcard device/provider/rollout gates remain open. [P3 active handoff](../../../localization/P3_ACTIVE_HANDOFF.md) records main promotion in its top checkpoint, superseding old branch-only text still present in memory. Current source and that checkpoint take precedence over stale summary language.

## Goals / Non-Goals

**Goals:** one additive source-to-session contract, three reusable presentations, measurable independent transfer, reproducible allocation and complete measurement across eligible courses/locales/surfaces. Preserve ordinary lesson completion even if every new dependency fails. Bound content work, queries, audio preparation and paid AI consumption.

**Non-goals:** a second curriculum, mistake/SRS engine, voice backend, analytics stack or reward economy; general Desktop revival; automatic account merging; activating unpublished levels; changing lesson unlocks, official answer keys, payment/referral terms or notification policy. A plan does not activate an experiment. The test evaluates the bundled learning journey; it cannot identify which of its three components caused any lift without a later experiment.

## Decisions

### D1. Reusable exercise projection over immutable materials

Extend `course_lesson_plan_service` and the existing card/question factories. Add a small source-to-exercise compiler at that boundary only if it keeps adapters from duplicating logic. Compile shared public **content templates**, then apply learner context privately; never cache private plans as public templates. Identify every exercise by `track/level/part/source_ref/objective_id/format/version/source_digest` and each presentation by an attempt-owned instance ID.

Use existing P3 translation/grammar resolution before projection; leave original JSON, source SHA, `section_no/card_no`, graded keys and material refs untouched. New derived answers are stored separately from official lesson answers and graded through an owned snapshot. Candidate eligibility requires the taught lexicon/grammar, a single clear learning objective, safe distractors/accepted answers, all UZ/RU/TJ display fields and applicable asset rights. Structural validation and agent semantic QA are separate gates under `AI_CONTENT_QA_POLICY.md`.

No runtime LLM is required for V1 material or answer creation. Where source is insufficient, first select an equivalent existing supported exercise. A missing source-dependent detail is never filled with plausible fiction. Reusable authored templates/variants may be added centrally as a small reviewed overlay only when their semantics can be verified against existing taught content in all three languages; unresolved items stay excluded with a reason. Do not rewrite 746 lessons or silently enable nhsk4. Produce a machine-readable coverage summary and fail CI on unsafe sources or unknown available levels, not on the honest absence of a particular format.

Existing explicit section-card objective tags cover only 15 nhsk1 parts / 62 cards; universal objective IDs cannot be assumed. Derive missing objective identities centrally from existing canonical mistake/word target keys, skill and source word/grammar references, using a versioned source-digest sidecar and shared templates. Distinguish lexical recall from grammar/application objectives; do not collapse every sentence sharing a word into equivalent knowledge. Agent-review the derived mappings/probe templates once per unique source objective, not manual tagging of every repeated mini-part. Common-probe coverage is a separate launch gate: every admitted level/locale must have a reviewed measurable pool, each session declares eligible/unsupported objective coverage, and the frozen protocol must justify representative coverage before a global knowledge claim. A format fallback does not excuse an unmeasured entire course.

Scene turns must be contiguous in the original exchange or have agent-verified contextual continuity after learned-vocabulary gating; never stitch unrelated speakers, contexts or nonadjacent fragments just to satisfy a two-speaker check. Source grammar with missing pinyin stays immutable: exclude that new spoken candidate or admit a separately reviewed supplemental reading under P3 policy, never invent purported original phonetics.

Rejected: per-lesson manual scenes, live generated graded dialogue and a new content repository. These add cost and drift from source/locale/answer guards.

### D2. Three initial formats, explicit evidence limits

| Format | Source and interaction | Answer/evidence policy | Safe alternative |
| --- | --- | --- | --- |
| Two-character scene | Two source speakers, sequential short audio turns; pause at a deterministic beginning/middle/end checkpoint. Challenge modes: heard meaning, missing turn, repeat or take a role. One checkpoint normally; replay/resume at turn boundary. | Reuse listening/cloze/choice/token validators. Optional repetition uses current pronunciation API, not a tone-mastery claim. Full transcript/translation is available as help/feedback; first unaided response precedes reveal and is marked helped afterwards. | Transcript with speaker labels and existing verified task if audio fails; another eligible format if no real dialogue. Never count transcript-only as listening success. |
| Situation response | Minimal localized context from a verified taught dialogue/grammar template; learner supplies the requested intent as short Chinese text or a token response. Optional voice is an equivalent input method, not required Live Voice. | Deterministic accepted variants for constrained tasks. For genuinely open language, show formative feedback; ambiguous valid alternatives are `unscored/needs_review`, not falsely wrong. LLM feedback remains optional under existing access/quota and cannot supply the common experimental score. | Existing builder/choice with the same objective; record that a supported response was used, not independent open production. |
| Find and repair | Agent-verified single corruption of an existing correct sentence; identify the error and repair it. Reuse grammar `correct_choice`/gap/builder validation rather than another grading engine. | Require exactly one intended error and accepted repair variants; expose explanation after response. Avoid corruptions allowing multiple correct meanings. | Existing correct sentence/comprehension when a unique repair cannot be verified. |

Picture-based speaking stays the existing curated picture deck in the mix. General image scenes/image recognition are deferred: no corpus or grader currently justifies that cost. Selection of these formats is an engineering/product hypothesis. Their effectiveness must be measured.

For scene audio reuse `tts_service` and bundled word/phrase audio first. Extend only allowlisted `speaker_a/speaker_b` presets with provider-supported distinct voices; preserve legacy single-voice cache filenames and version new voice/provider/rate/text cache keys. Prepare/cache by **unique source line**, not by learner or duplicated part, with existing bounded concurrency/retry and a finite preparation manifest. Test pronunciation and both preset outputs; if the provider cannot supply distinguishable voices, keep visual speaker identity and label the degraded exposure, never claim two-voice delivery. No provider call may hold a DB connection. Do not autoplay before a user gesture on Safari/Telegram; cancel playback on navigation/background/account switch. No Live Voice quota is consumed by hearing a scene.

### D3. Extend one budgeted planner, preserve the learning core

Control uses current supported lesson presentation plus the common measurement layer. Treatment replaces eligible **optional practice slots** with contextual variants and adds evidence-based handoff. Mandatory teaching/grammar/dialogue objectives, N1 learning checks/repair/exit tickets and original order remain protected. Contextual practice may follow a protected dialogue; it does not remove or silently replace that teaching block. Existing adaptive reviews keep their separate grading/SRS owner but share the displayed session time budget so ≤3 extra review items cannot silently dominate a five-minute lesson.

Inputs: existing goals/minutes/focus, taught/current objective coverage, verified skill weakness/due state from adaptive/Mistakes/Word Mastery, recent shown formats, client capability and asset readiness. No new learner-profiling model or unverified ASR-based knowledge estimate. Use the current skill weighting as the starting score; add bounded weakness/due and novelty terms, then deterministic attempt-seeded tie-breaking. Coverage/prerequisites outrank novelty. Do not vary between retries to appear fresh.

History is the last six completed/confirmed shown eligible sessions within 30 days, bounded to 24 distinct shown-format facts. Assigned/unseen cards and replayed audio do not count. Penalize recently dominant formats; when at least two objective-equivalent formats fit, prefer one absent from the last two sessions. No forced quota when only one safe form exists. For short lessons, start with at most one contextual slot; for longer lessons at most two, **inside** optional budget. Estimate audio/response durations, rather than calling a full scene half a card. Keep existing unit/minute settings as policy baseline; calibrate estimates with measured duration before launch.

If protected material alone exceeds the chosen budget, preserve it and honestly show estimated remaining work; never drop core content to meet a time promise. A server-authored manifest records retained/replaced optional source refs, objective coverage, expected cost and fallback reason. Exhaustive tests across all available parts and 5/10/15/20/30-minute profiles must prove original refs/mandatory cards remain. No expansion into a second course assembly system.

### D4. Stable session contract and minimal durable storage

Evolve optional `lesson_plan` additively as a negotiated version; old clients receive their current version. Do not mutate adaptive plan v1 into a course-completion authority. Proposed conceptual fields:

```text
session: id, contract_version, assignment_version, delivered_variant,
         config_revision, source_digest, base_resume_ref, lease_expires_at
plan:    existing omit/picture fields + ordered exercise instances,
         original source refs, objective refs, slot/cost, safe fallback refs
exercise: instance_id, format, mode, public prompt/turns/assets,
          response_schema, help_available (no private answer key)
```

Use three small additive storage boundaries (names provisional, ownership fixed):

1. `learning_experiment_assignments`: canonical `user_id`, experiment/protocol version, immutable arm/bucket/cohort, assigned/enrolled timestamps, frozen safe analysis strata; unique `(experiment_id,user_id)` and experiment/cohort/arm/time index. No Telegram-ID bucket or best-effort-only assignment.
2. `course_learning_sessions`: canonical user/assignment, idempotent start key, level/part/source/manifest digest, current original-card cursor, actual delivery/capability/fallback, config lease, started/completed/last-interaction times. Persist the compact plan/accepted-answer snapshot server-side. Unique user/start key and owner/time indexes. This is attempt measurement/resume, not another `course_progress` table.
3. `course_learning_responses`: session/item unique key, measurement stage/objective/format/rubric version, first valid answer/assistance state, deterministic verdict and timestamps. Store only bounded validator input/snapshot needed for idempotent feedback; no raw audio or free conversation transcript. Reuse an existing typed owned attempt store instead if it can supply these exact invariants without changing its current meaning. Decide this reuse from source in implementation task 1.1; do not create two stores.

Telemetry mirrors assignment/delivery/shown/answer facts in the existing event pipeline for reports, but cannot substitute for durable allocation/assessment state. Foreign keys and account deletion remove user-owned experimental state through the established purge; historical aggregate privacy policy remains unchanged. Proposed retention: detailed session/response snapshots 90 days, then anonymous aggregates; remove freeform submitted text after scoring/idempotent receipt whenever an index/verdict suffices. Assignment survives for experiment life until canonical account deletion. Record storage estimates before activation; use batched existing cleanup, no independent daemon. Do not copy an example credential or private data into artifacts.

Create/continue a session only after existing authenticated lesson access, start proof/grant, sequence, track, foundation and entitlement checks. Private snapshots use `no-store`; expose public prompts, not private answer keys. An authenticated `start_key` identifies retry of the same attempt. Resume of an open part on a different device adopts that owned session; explicit replay after terminal completion starts a new practice session without a second official reward. Serialize competing open-session/start/answer writes under the canonical user lock; stale revision returns conflict plus current owned cursor. Locale changes re-localize the same instances; content/contract changes keep the pinned snapshot or safely resume the original base cursor, never replay rewards.

Add the smallest shared session/answer handlers with existing Telegram initData, PWA cookie+CSRF+same-origin, Android bearer and Desktop bearer/IPC adapters. Do not expose Telegram IDs as native account keys. Per-answer server grading is authoritative; clients may reuse current immediate local feedback where already supported, but only the accepted server receipt advances verified evidence. Existing official completion endpoint/proofs, hearts, quiz/homework scores and progress remain unchanged. New formative tasks cannot block official completion during failure or microphone denial.

### D5. All-platform delivery with honest compatibility

| Surface | Proposed change and gate |
| --- | --- |
| PWA Safari/Home Screen and browsers | Existing shared queue/player, NavBack layer, owner-checked async requests, recorder and result handoff. No first-card wait for media/planner. WebKit/Chromium tests at 320/390/430 px. |
| Telegram Mini App | Same exercise player; preserve real Telegram SDK/initData/launch fragment/BackButton and non-Telegram fallback. Auth adapters retain separate authority. |
| Android Direct + Play | Existing Parser/ViewModel/Compose, capability advertisement, native audio/recorder and durable owned resume. Both flavors compile/test, keep Play checkout restrictions. |
| macOS + Windows | Task-specific paired shared JS renderer plus exact Rust IPC allowlist/audio transport; both OS native acceptance before claiming universal support. No unrelated Desktop work. |
| Bot chat | Preserve current lessons/homework/quiz. Treatment study uses the already available authenticated Mini App/PWA course entry, retaining account/arm/part; measure a redirect as handoff, not exposure or completion. Continued old bot-only lessons are explicit unsupported-format fallback under ITT. Do not build another bot exercise engine or force account creation. |
| Public website | Preserve acquisition locale/auth route; a page/download/link click is not study or treatment exposure. |

Capability negotiation covers contract/format versions, audio, mic and codecs; server allowlists supported versions, and client capability claims grant no access. Missing/unknown support → original supported flow with a typed reason. Same account keeps arm across devices, including a B learner using an old client. No silently claiming every installed binary receives new formats. New binary adapters for all requested supported platforms and content gates must be ready **before** global activation; do not postpone an entire platform as a pilot. Unsupported historic clients remain a reported dilution of assignment effect.

Device/network/audio failures use transcript or equivalent non-mic task. Offline/new session without a valid lease stays in base mode; existing offline course functionality remains. Account switch clears private plans/audio queues/outboxes; pending responses are scoped to original owner and never replayed to the next account. Resume cannot bypass entitlement revalidation.

### D6. One learning journey, evidence before celebration

Keep source teaching → short contextual attempt → unaided transfer check → confirmed result → one contextual next action. Use the current result view and value-first handoff, not a second results modal. Say what the learner demonstrated using objective-specific confirmed evidence (for example a new correctly repaired structure or successful due recall), with offered/assisted/unscored states represented honestly. A single exposure, similarity pronunciation score or XP total is not proof of lasting mastery. Baseline unknown means no invented before/after claim.

Reuse current sounds/haptics/character reactions/`LessonCompletionCelebration`; keep existing sound toggles, reduced motion, screen-reader feedback and no mandatory sound. Do not add XP/streak per new card, retry, audio play, measurement or animation. Reward schedule and existing local-day streak/recovery remain identical A/B. Celebration follows confirmed success; local formative feedback may be immediate without calling a persisted achievement.

Existing verified mistakes feed the existing material validator/target store, never an invented `material_ref`. Contextual answers use a separate snapshot-to-target adapter with the same ownership/track constraints; only unambiguous server-verified errors enter that store. Repetition/ASR ambiguity and LLM opinion do not become trusted skill facts. Due review uses existing adaptive schedule; words use Word Mastery; no second mastery score. Offer one applicable existing next action (due mistake, current Daily Plan task, flashcard due deck, next part or optional contextual Voice), prioritized by current server state. Preserve frozen daily task IDs and no added automatic notifications. Voice receives an allowlisted lesson/objective context reference verified by the server; no hidden answers, transcript, arbitrary prompt injection or new entitlement. If quota/free session is exhausted, offer a free equivalent without interrupting the course.

### D7. Canonical 50/50 assignment and interference control

Use experiment ID `learning_loop_v1` with immutable randomization/protocol version and a fixed server-owned seed. Uniform cryptographic hash of experiment seed + canonical `users.id`, threshold 50%, gives repeatable random assignment in expectation; persist once under user lock/unique constraint. Do not alternate arrivals, promise exact 50/50 in small samples, use localStorage/device/Telegram IDs or re-bucket on restart. Persist assignment authoritatively; storage failure serves base and retries that same deterministic arm rather than issuing unrecorded treatment.

At global start `T0`, every eligible canonical account is mapped by this rule; materialize on first authenticated relevant foreground entry, with no full-table write/scan for dormant accounts. New registrations enter immediately. Freeze `cohort=new` if canonical `created_at >= T0`, else `existing`; returning dormant users stay existing. Enrollment anchor is the first authenticated eligible learning opportunity after T0, before arm-dependent rendering. The report denominator is enrolled accounts, not every dormant database row. Anonymous pre-auth Li preview is unassigned; bind only after existing sign-in, never fingerprint it. Two independently created accounts are not one identity; linking an identity cannot move an already-owned account into another arm or merge records.

Freeze baseline language, track/level, minutes bracket, initial platform and available prior-activity bracket. Missing knowledge/history stays unknown. Capability/platform changes affect delivery only. `assigned_arm`, server delivered manifest and client-confirmed shown exercise are distinct facts. B fallback remains B in **intent-to-treat** (ITT), with delivery/exposure/fallback rates shown; exposure-only comparisons are diagnostic, not the causal headline. Randomization and assignment facts are passive activity events.

Pin source content, existing adaptive/picture/value-first flags, reward rules, access/paywall and reminder/sales policies equally in A/B. Existing reminders/sales experiments are not reworked; record their frozen eligibility/arm when available and check balance/interactions. No new campaign during the measurement window. A global product/code/protocol change that alters the treatment requires a new recorded version; never silently pool incompatible windows or restart clocks to improve results.

### D8. Common learning measurement and metric dictionary

Both arms receive the **same measurement layer** (not literally an untouched old binary): equal opportunity, objective sampling, timing, help policy, rubric and feedback/reward. Measure this small common-layer overhead equally. Use existing source-grounded factories/snapshot graders to supply equivalent unseen probes: short precheck when baseline is needed, immediate unaided transfer, delayed recall windows at 24–48 h and 6–8 d after the learning objective. At most one short probe at a session stage; do not turn a five-minute course into repeated testing. First response is frozen; after it, normal help/feedback is available. Assisted, skipped, missing and unscored responses are separate states. Probes grant no extra XP and do not change official completion.

Select probes independently of arm and recent practice answers, from agent-reviewed objective pools at comparable difficulty. Same objective coverage and first-answer scoring across languages/platforms; no answer leakage via scene transcript, prefilled response, TTS of the answer or replay. Short constrained text/finite semantic variants can demonstrate application; open conversation/ASR similarity cannot be the primary common scorer. Ambiguous variants remain unscored with coverage shown, never forced wrong. Baseline helps describe change but identical unseen post probes avoid mere memorization of the precheck.

For an unaided checkpoint/probe, public payloads withhold answer-bearing transcript, target/model response, explanation and private rubric until the first answer or an explicit authenticated help request. Required question audio remains available for a listening item. A help/reveal endpoint atomically commits a monotonic `helped` state before returning withheld content; item-level ordering serializes reveal/answer races across devices. A response accepted before any reveal can retain first-unaided status, while a reveal accepted first makes every later response assisted. Reopening/retry cannot reset this fact. Ordinary teaching remains accessible; revealing help never penalizes official completion, only changes measurement classification.

| Metric | Frozen unit / denominator / window |
| --- | --- |
| Primary D7 qualified learning return | Canonical enrolled account with at least one authenticated, server-accepted scored study response or confirmed ordinary study completion in `[168,192)` UTC hours after enrollment / enrolled accounts whose entire window matured. Passive events, notifications, assignment, audio replay, app open and grading retries never qualify. Explicit accepted answers are observed symmetrically in existing formats; do not require B-only endpoints. |
| D1 / D14 | Same rule in `[24,48)` / `[336,360)` hours. This is experiment enrollment retention; existing account-creation D1/D7 chart keeps its current meaning. |
| App return | Separate authenticated foreground-return rate under equivalent trusted PWA/Android/Mini App/Desktop writers. Never mix it with qualified study return. Unsupported platform coverage is unavailable, not zero. |
| Completion | Original server-confirmed learner/part completion within 24 h of an owned session start, deduped across devices. Also report completed accounts/enrolled and time-to-complete; replay practice is separate from first progression. |
| Abandonment | Started eligible sessions with no confirmed completion after 24 h, reconciled by owner/session/part across transports. Show explicit exit/background, unresolved, auth/access block and technical fallback separately; before 24 h label in-progress/immature. It is an operational abandonment proxy, not certainty about intent. |
| Independent task | First unaided valid common transfer response correct / all eligible offers, plus respondent accuracy and shown/responded/assisted/unscored rates. New-format practice success stays a separate metric. |
| Recall | Same common objective rubric in delayed windows; all-assigned demonstrated recall plus responder accuracy. Show due/offered/shown/responded/missing. Missing is not a knowledge failure or success; nonresponse is visible, with sensitivity bounds. |
| Satisfaction | Same optional 1–5 prompt after the same confirmed session trigger in both arms, at most weekly/account. Show eligible/shown/responded, distribution/mean and response rate; no coercion or fabricated missing rating. Existing release-feedback campaigns are not a random satisfaction sample. |
| Safety/resource | Auth/access/score divergence, duplicate XP, protected-objective coverage, unsupported/fallback rate, mic/ASR unknown rate, crash/error and completion API error rate, audio/start latency, paid-AI cost/session and server SQL/API p95 by arm/platform. |

The common measurement store is an operational learning record, not unrestricted telemetry. Events contain only allowlisted IDs/enums/counts/durations, server-resolved arm/cohort/platform and rubric version. No answers/audio/transcripts/messages/tokens/URLs/raw exceptions or payment data in telemetry/diagnostics. First answer and duplicate response behavior are distinct; late ingestion records server acceptance and bounded client timestamps without moving arbitrary events into retention windows. Use a 48 h ingestion/reconciliation lag after each matured window; late/unknown facts are reported and versioned, not silently overwritten.

### D9. Analysis protocol before activation

Preregister one outcome: D7 qualified learning return, analyzed **separately** for new and existing cohorts. Two prespecified cohort claims form one family: Holm-adjusted two-sided alpha 0.05, risk difference/relative change and compatible 95% confidence intervals with their multiplicity status. Use canonical-account units, not independent per-card samples. Combined effect uses fixed prelaunch cohort weights and remains secondary; course/language/platform/minutes slices are exploratory unless separately powered, with interaction intervals and sparse cells hidden/unavailable. Do not call a small positive point estimate a win.

Proposed materiality target is +3 percentage points D7; design power for +5 points at 80% power (conservative alpha .025 per cohort). Before launch use verified same-definition baseline and eligible traffic for each cohort to calculate required arm size, enrollment duration, common-assessment non-inferiority sample size and maximum calendar horizon. Example only: 20%→25% with alpha .025/80% power needs approximately **1,325 accounts/arm/cohort**, before allowance for unavailable measurement. This is a reproducible normal approximation, not HSK AI's actual baseline or traffic. If traffic cannot support that MDE/horizon, freeze a revised feasible protocol **before seeing arm outcomes**; otherwise finish as inconclusive rather than claim proof. No promised fixed two-week result.

Minimum enrollment spans two full weekly cycles plus the final account's D14 window and 48 h ingestion lag; actual duration is the larger of that and the powered enrollment horizon. Do not peek for efficacy or stop when p first drops below .05. Safety stopping is continuous and independent of a win claim. Multiple interim efficacy looks require a prospectively revised sequential design; not V1.

Success per cohort requires adjusted evidence of D7 improvement, point gain at least the frozen meaningful target, no safety/performance breach and common unaided transfer/recall non-inferiority. Proposed knowledge and completion margin: −3 percentage points, with one-sided 95% lower bound above that margin; freeze exact populations and power before launch. If only one cohort meets criteria, report that limited finding; no blanket rollout claim. Retention gain with worse knowledge fails the product goal. If knowledge data are too incomplete for the bound, the learning conclusion is inconclusive.

Check sample-ratio mismatch on enrollment allocation (and by prespecified strata/time/client), not an assumed 50/50 among completions. Predeclare alert at SRM p<.001; investigate before reporting any effect. Report assignment persistence failures, unsupported exposure, missing/invalid events and probe-response differences by arm. A/A verification uses internal synthetic traffic through both writer chains before launch; it is not an external pilot cohort. No real-user pilot lessons or recruitment. Causal estimate remains concurrent ITT; no removal of fallback/low performers after seeing outcomes.

Historical context: last 28 **fully covered comparable** pre-T0 days, same weekdays/available platforms/course/activity strata. Coverage dates come from the analytics registry/current writers. No fabricated historical D14/common knowledge/satisfaction/precise attempt data. Where unavailable, show `not_instrumented` and collect baseline symmetrically during preparation without withholding global eligibility. Existing `pwa_analytics_learning.py:104–151` creation-cohort D1/D7 cannot be relabeled enrollment D14. History is descriptive and subject to acquisition/seasonality, not the causal control.

Method references checked for this plan: [Microsoft Research on SRM/data quality](https://www.microsoft.com/en-us/research/articles/data-quality-fundamental-building-blocks-for-trustworthy-a-b-testing-analysis/?lang=ko-kr), [Microsoft's metric interpretation pitfalls](https://www.microsoft.com/en-us/research/wp-content/uploads/2020/08/2017-08-KDDMetricInterpretationPitfalls.pdf), [two-proportion power formula](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/power-and-sample-size/how-to/hypothesis-tests/power-and-sample-size-for-2-proportions/methods-and-formulas/methods-and-formulas/). Thresholds above are proposed product protocol, not claims made by those sources.

### D10. Existing analytics/Admin/monitoring chain

Extend existing event allowlists, passive-event classifications and server client attribution; do not trust caller arm/cohort/platform. Assignment/delivery/measurement preparation/report reads never refresh learner activity. Keep telemetry savepoint isolation so observability cannot roll back study. Durable session/response writes that fail return a clear unconfirmed status and safe base flow; never fabricate confirmed mastery.

Extend `pwa_analytics_experiments.py` and the existing Statistics disclosure with a versioned `learning_loop_v1` aggregate: protocol/T0/source coverage/config versions, four cells (new A/B, existing A/B), sample size/maturity, denominators, ITT effects/intervals, delivery/fallback/quality/guardrails and honest historical context. Use bounded SQL group-bys/indexed time ranges and anonymous daily sufficient aggregates for long experiments, not the sales report's 5,000-event scan or truncated 30-day denominator. Never silently sample/cap a global denominator. Preserve existing private daily snapshot/refresh lease and post-cache session checks. Safety switch status/operational incidents are live separately; a 24-hour statistics cache cannot own kill authority.

**Analytics Impact:** full authenticated source → canonical assignment/session → deduped PostgreSQL facts → metric reader → existing Admin disclosure/export → coverage registry/runtime chain tests. Register actual supported platform pairs and `not_applicable` reasons, no enum-only completion.

**Monitoring Impact:** extend existing `lessons`/practice flow IDs, allowlisted failure codes and `ROUTE_MAP`, plus exact shared critical-path mappings. Report compiler-invalid/source-drift, session conflict/lease, media failures, scoring and report unavailability as appropriate through existing intake → diagnostic incident → Admin Inbox. A wrong learner answer, denied mic or intentional unsupported fallback is not automatically an incident. No raw content. Existing analytics-integrity and performance CI guards remain enabled.

Recorder reuse needs one narrow privacy correction: current `course-v3.html:6165` passes a `heard` transcript excerpt to `clog`, whose `:2690` clientlog POST can transmit it. Remove transcript content from the affected shared recording log path and replace it only with allowlisted outcome codes; add a request-capture regression. Do not copy this existing behavior into new exercises or expand this into an unrelated logging refactor.

### D11. Emergency stop, performance and data safety

Use one existing signed settings-command path for experiment mode `off|shadow|ab`, revision and independent emergency veto; default OFF. Normal trial activation is exactly 50/50 AB after QA, not 10%/90% ladder. Shadow compiles/validates internally without exposure, SRS mutations, assignment outcome claims or external delivery. Any Admin control follows `docs/admin-pwa/BROWSER_UI_CONTRACT.md`: one contextual action, existing one-use passkey/CAS/audit, no redundant confirm/cancel buttons.

Target: an acknowledged kill veto stops new online treatment issuance and unshown tasks within **60 seconds**, tested across workers. Config cache max 15 s; active foreground session refresh at most every 30 s; treatment lease ≤60 s checked locally at task boundaries. One already displayed task may finish or be skipped; never block a base result on a rejected new-task answer. No per-card DB/config request, no background polling when feature OFF. In-flight grading may return its immutable receipt without issuing new tasks; new-task state writes honor kill revision. Existing adaptive flag-off answer rejection remains understood by clients.

Offline clients cannot receive an instantaneous remote signal. They cannot start new treatment after lease expiry; a displayed task exits safely to base at the next boundary. Persist original base resume ref, not an index into the temporary mixed queue. Disable treatment, clear unshown projections and continue ordinary completion without restarting taught material, losing results or awarding XP twice. Preserve assignment/evidence/config history; do not delete/downgrade populated tables or serve an old binary that cannot read retained contracts.

Lease validity uses elapsed monotonic time anchored to the last verified server grant, not an editable device wall clock or a scheduled timer alone. Recheck immediately on foreground and every task transition. A restored process/page cannot reuse a persisted lease without server revalidation; if suspend-safe elapsed time cannot be proven, expire it and use base flow. Server issuance/grading also checks its own expiry/config revision, so clock rollback cannot extend authority.

Performance budget: first card/safe shell never waits for experiment/audio/assessment planning; optional plan timeout ≤1 s with base fallback, validated against existing lab; existing 10 s bounded network UI controls remain section-specific. No synchronous paid AI in course-plan path. At most one owned session/config fetch per start and bounded foreground renewal; batch context queries, avoid per-card/line SQL, measure relevant EXPLAIN/index/pool behavior with real-size QA fixtures. Public template/audio caches keyed by content digest; private data scoped to account/session. Target no >10% p95 start/API regression and no >1 percentage-point completion-error regression versus A, subject to prelaunch lab baseline; security/access/incorrect scoring/duplicate reward/protected-content loss are zero-tolerance stops. Record cost budget from current provider usage before enabling optional AI; new deterministic/text formats and audio reuse need no per-turn LLM bill.

## Risks / Trade-offs

- [More variety without better learning] → common unaided transfer/delayed recall and D7 ITT, no causal claim from XP/completion alone.
- [Too much work in short lessons] → replace optional slots, account for adaptive/picture costs, mandatory core stays and honest duration overflow.
- [Invalid language/answers] → fail-closed agent semantic QA across UZ/RU/TJ; central reviewed variants, no live generated answer keys or human review homework.
- [Old clients and bot chat dilute B] → stable arm plus capability fallback/exposure rates; deliver all current adapters before launch, never exclude after outcomes.
- [Scene audio/speech cost/latency] → unique-line cache, bounded preparation, explicit gesture, non-mic path, current quota and uncertainty behavior.
- [Cross-device overlap or account swap] → user-first locks, stable original refs, one open attempt and owned responses/outboxes.
- [Learning bias from response-only samples] → common offered/eligible denominators, missingness bounds and no proof when knowledge coverage is insufficient.
- [Experiment interferes with other changes] → freeze/equalize existing flags/policies and version any material concurrent release; retain other experiments' identities.
- [Extra rows exhaust storage] → measure row volume, indexed bounded reads, 90-day detailed retention; existing DB capacity caveat is not a verified current production reading.

## Migration Plan

1. Re-fetch main and re-audit touched owners immediately before implementation; this planning SHA is a reproducible baseline, not a permanent head. Current source Alembic head is `0160_smart_routing_pwa_state`; select a new revision only after rechecking head. Update standalone QA bootstrap model/deferred-list/head guards when schema changes require it. No production startup initializer.
2. Implement additive schema/contract and full all-level/all-locale compiler QA with flags OFF. Add ownership/purge/idempotency/backward-reader tests; no default assignment bulk scan or provider calls in migration. A populated downgrade refuses destructive loss.
3. Deliver PWA/Mini App, Android Direct/Play, paired Desktop and bot handoff compatibility in one initiative using bounded reviewable commits. Common measurement/report/registry/monitoring must land with behavior; no half-connected metrics. Keep existing narrower handoff checklists authoritative.
4. Internal QA only: synthetic account A/A/50-50 determinism/concurrency, entire available content matrix, auth/access/result regressions, real browsers/devices/providers and kill rehearsals. All newly supported platform adapters must pass before calling the launch global. Failed material uses proven fallback; unresolved safety failures block activation.
5. Freeze protocol/baseline/traffic/sample size/horizon/guardrail budget and precise measurement coverage. Normal Git/CI/main policy applies to separately authorized implementation. Release installed binaries while OFF; verify actual release versions and effective server settings rather than infer from Git. Retain rollback-compatible server readers.
6. Activate global `ab` once internal gates pass; all eligible authenticated accounts get the same 50/50 rule, with old-client fallback recorded. No selected pilot lessons/users. Monitor safety/quality immediately, efficacy only at the preregistered mature horizon.
7. Final report for new and existing separately, source/quality/maturity limitations, historical context and justified keep/revise/stop/inconclusive recommendation. Promotion is a later explicit decision, not automatic 100% treatment from a checked task. Emergency OFF uses D11 and preserves the experiment ledger.

## Open Questions

Only operational calibration remains: actual covered baseline/eligible traffic, p95/cost limits from measured fixtures, exact provider-supported second voice and installed version availability. These are implementation verification inputs with fixed safe defaults (OFF/non-mic/base fallback), not permission to change allocation, curriculum, scoring or scope. Record them in this change's tasks/evidence, not a competing progress file.
