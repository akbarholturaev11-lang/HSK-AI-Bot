# Design

## Context

[Proposal](proposal.md) defines scope; [evidence](evidence.md) records current source paths, actual findings, reproducible methods and private-data limits. Runtime baseline is `d7e91f42`, not a production rollout claim. The owner's boredom report is the accepted product need. Source type counts cannot invalidate perceived sameness; analytics tests the solution's effect.

The earlier plan committed three formats, three tables and synchronized course sessions before necessity was shown. This revision chooses two experiential families, existing durable assignment ownership, one neutral receipt store and unchanged course cursors. It also recognizes common probes as an intervention and removes illustrative effect/sample numbers that were not calibrated HSK AI facts.

## Goals / Non-Goals

**Goals:** purposeful participation, source-grounded independent application, visible honest progress and a valid account-level effectiveness test across admitted courses/locales/platforms.

**Non-goals:** re-proving boredom before design; isolating every component's causal effect in one bundle; treating XP/ASR similarity as mastery; rewriting lessons; changing access/rewards; general Desktop revival; a new provider/SRS/dashboard or synchronized course cursor.

## Decisions

### D1. Two experiences around existing material

| Family | Experience | Reuse / genuine change |
| --- | --- | --- |
| Scene with participation | Two characters exchange coherent short voiced turns; at one meaningful pause the learner interprets/supplies a reply or takes a character's role, then the scene continues. | Existing dialogue/listening/cloze/builders/pronunciation; new turn orchestration, pause/reveal and role state. An unrelated quiz between clips is not the target. |
| Practical mission | A clear real-life goal using taught vocabulary/grammar; learner constructs/supplies the needed utterance before a model. Find/repair/reapply can complete the same goal. | Existing grammar/mistake validators and response controls; new contextual goal/progression and application feedback. Open language uses formative uncertainty, not an LLM common score. |

Choice/translation/token/repetition are modes, not additional formats. Reuse curated picture recall rather than build scene-image generation. No new currency/game map. Use existing characters/feedback; create no decorative subsystem.

Compile public templates from real source word/grammar/dialogue and P3-resolved meanings; personalize privately. Pin track/level/part/source-ref/objective/format/version/digest. Keep original Chinese/JSON/graded keys/material refs immutable; supplements have separate snapshots/keys. Turns must be contiguous or agent-verified coherent after vocabulary gating. Never stitch unrelated fragments or invent purported original pinyin. Missing/ambiguous material selects a safe existing objective task with a reason.

Objective tags are sparse. Derive absent identities centrally from existing target keys, skill and source references in a digest-pinned sidecar; verify semantic equivalence once per unique objective instead of tagging 746 parts manually. Agent QA owns Chinese/UZ/RU/TJ templates, distractors and accepted variants; no human-review homework or unchecked live generation. Future levels use this compiler after their normal admission; nhsk4 remains unavailable.

### D2. One budgeted planner, objective before novelty

Extend `course_lesson_plan_service`, not another assembler. Keep mandatory teaching/grammar/dialogue/objectives/repair/exit checks and original order. Context replaces only legal optional opportunities: short sessions at most one, longer at most two, with current picture/adaptive costs plus audio/response burden accounted for. No legal slot → preserve core and report coverage, not a hidden second lesson.

Some audited profiles discard most existing retention. Preserve one relevant retrieval/application opportunity **where legal optional space exists** before filling that space with extra recognition/novelty. This does not make every old optional card mandatory. Card units are not measured minutes; protected overflow stays honest and cannot be truncated to satisfy a time promise.

Use current goal/focus weights, verified due weakness and prerequisites, then bounded recent **shown** family history (six sessions/30 days, max 24 facts). Assigned/hidden/failed tasks and replay do not count. Stable receipt-seeded ties avoid retry reshuffling; only one safe form can repeat. SRS/Mistakes/Word Mastery remain authoritative; no new profiling model or ASR-derived mastery.

### D3. Bounded media, first teaching stays usable

Extend `tts_service` with allowlisted speaker presets and voice/provider/rate/text cache identities, preserving old cache lookups. Prepare by unique source line using existing concurrency/circuit/fallback; no new provider, per-user scene synthesis or Live Voice session to hear a scene. Verify distinct speaker/codec/MIME; degraded transcript/single-voice delivery is labelled, not listening success.

Require an appropriate playback gesture; cancel obsolete playback on navigation/background/account switch. Optional plan/media never blocks first teaching. Mic/silence/provider/network/quota failure yields an unscored/non-mic/base alternative without trapping completion. Existing Free/Pro/receipt-preview limits apply. No provider IO with a held DB connection. Existing start/audio waits are separate performance findings, not a reason to add another wait.

### D4. Existing assignment store plus one neutral receipt

**Assignment:** existing `CourseMiniAppEvent` unique `(user_id,event_name,dedupe_key)`, exact server-only experiment/version key, verified nonnull canonical owner and closed compact payload. Write authoritatively in the owning transaction, not best-effort analytics/savepoint; commit before treatment. Lock first creation, reread unique-conflict winner. Arm/cohort/seed/cutoff/version are immutable. Invalid/truncated/conflicting evidence disables treatment and reports an incident, never recomputes. Exclude assignment from client allowlists/activity. Existing purge explicitly deletes owned event rows; test it because FK alone is SET NULL. Add only a narrow index justified by EXPLAIN.

**One neutral exercise receipt table:** owner, opaque UUID/purpose, immutable source/question/rubric/composition snapshot, language/context/capability, first-response/help state, timestamps/expiry. Bound private questions/keys/feedback and retain minimal grading input; no raw audio/conversation. Reuse adaptive snapshot/first-answer and practice nonce/digest patterns. Existing stores cannot simply take this role: legacy `CourseAttempt` has a lesson FK; practice is HSK1–4/Smart-analysis-gated; adaptive is review-only with 14-day cleanup/one-day answers. New neutral purpose supports all admitted tracks without enabling Smart.

Receipt is not progress, allowance reservation or course-session lock. Existing local original-material cursor remains. Cross-device **arm** stability is required; synchronized course position is not. An owned receipt can be adopted/retried by ID with original first feedback. Old client falls back. Do not claim an exact whole-course attempt funnel where starts/resume cannot be matched.

Existing auth/access/sequence/source ownership precedes receipt issuance/acceptance: Telegram initData, PWA cookie+CSRF+same-origin, native bearer/bridge. Public prompts omit keys. Instant local formative feedback may remain; only accepted server evidence establishes verified results. Optional receipt failure cannot change official completion/hearts/score/XP/unlock.

Before an unaided check, withhold answer-bearing transcript/model/explanation; required question audio remains. Authenticated reveal atomically records monotonic help before returning content. Serialize reveal/answer races across devices; only first accepted answer preceding reveal is unaided. Reload cannot reset this. Unhandled valid language is unscored, not falsely wrong. Remove the affected recorder's current `heard` transcript in `clog`/clientlog reuse and test captured requests.

Detailed receipts expire after 90 days via bounded existing cleanup; delayed checks receive their own valid receipt/window, not an adaptive one-day expiry. Assignment lasts for experiment life until account purge. Preserve approved anonymous aggregate policy and populated-downgrade refusal; no permanent answer archive for analytics.

### D5. Same objective, visible achievement, one next action

Extend the current result projection beyond part-order-1 correction: demonstrated objective → specific confirmed evidence → one relevant existing action. A new unaided success is visible now; improvement requires comparable prior evidence; one answer is not permanent mastery. Showing a correction alone is not proof the learner can apply it.

Verified errors feed existing canonical targets; ambiguous speech/open responses do not. Due review uses existing adaptive/Word Mastery schedules; Daily Plan task IDs remain frozen. Voice gets a verified context reference under current access/quota, not an automatic session or arbitrary prompt. Unavailable Voice retains useful free review/course continuation. Reuse characters/sounds/haptics/confirmed success, mute/reduced motion and accessibility; no extra XP/streak per new card/probe/replay.

Use `hsk-ai-ui` for actual interaction/feedback, appropriate Chinese/pinyin/meaning reveal, one primary action, mobile safe areas and stable partial/error/retry states. No unrelated redesign. Existing end ads/access/setup/feedback stay equal A/B and get distinct transition reasons rather than being called boredom exits.

### D6. All-platform source contract and actual delivery

PWA/Mini App extend current queue/player/recorder, preserving SDK/initData/launch fragment/BackButton and NavBack. Android Direct/Play extend Parser/Repository/ViewModel/Compose/native audio with unknown-type fallback and unchanged Play payment restrictions. Paired macOS/Windows require real shared JS and exact Rust IPC/audio adapter work under this task's explicit exception to freeze. Bot retains teaching/homework/quiz and uses existing authenticated course entry; chat-only learning is unsupported-format fallback, not another scene engine. Public site is entry, not exposure.

Allowlisted contract/format/media capability grants no access. Current requested adapters must be ready before claiming universal launch; old installed clients keep arm/base path. Coverage includes all 746 admitted parts, seven keys and UZ/RU/TJ with honest fallback, not every format in every part or nonexistent levels. No pilot-lesson rewrite/recruitment or whole-platform deferral disguised as global readiness.

### D7. Global 50/50 and the causal contrast

`learning_loop_v1`: immutable server seed + canonical `users.id` cryptographic bucket, 50% threshold and committed persisted winner. Equal probability is not exact finite halves. Map all eligible accounts, materializing at first authenticated eligible foreground learning opportunity; no dormant-user bulk denominator. New = canonical created_at ≥T0, existing = earlier; enrollment precedes arm-dependent render. Anonymous previews remain unassigned; no fingerprinting/account merging.

Freeze baseline course/language/minutes/focus/platform/prior-activity strata and unknowns. Assignment, delivery and actual shown exposure are distinct. B fallback stays B in ITT; no selection by completion/exposure/response for headline estimates. The causal question is offering the coherent journey, not isolating each component or measuring dopamine chemistry. Source/rewards/access/prices/supporting flags and reminder/sales policies stay equal; material concurrent changes require explicit protocol/version handling.

### D8. Primary regularity and common knowledge evidence

Primary = mean **qualified-learning days**, zero to seven in elapsed 24 h buckets `[24,192)` after enrollment. This matches regular return, without assuming better power than D7. One account/bucket across clients. Qualifying sources are pinned existing symmetrically verified outcomes: ordinary lesson completion, existing server-scored practice/review/exam result, confirmed learner Voice turn where coverage is equivalent. App opens, passive events, XP alone, common measurement probes **and treatment-only formative receipt endpoints** do not qualify. Otherwise B's additional endpoints could mechanically inflate the primary. This coarse activity is not mastery; early unsaved work is a stated coverage limit.

| Measure | Fixed unit and limit |
| --- | --- |
| D1/D7/D14 | Same qualified source set, mature `[24,48)`, `[168,192)`, `[336,360)` windows; app-open return separate. Existing creation/first-platform-use charts retain their meanings. |
| Completion/exit | Original confirmed progression; receipt task completion separate. Matched start→terminal at 24 h only where identity exists; unmatched/background/access/technical/immature remain distinct. No distinct-account ratio as abandonment. |
| Application | First unaided common objective/rubric; eligible/offered/shown/responded/helped/unscored and response mode. Recognition/token/text/speech are not interchangeable production scores. |
| Recall | Equivalent unseen probes at 24–48 h and 6–8 d after objective; all-eligible demonstrated success, responder accuracy and missingness bounds. Nonreturn is not verified forgetting. |
| Satisfaction | Same optional server-owned post-activity scale/trigger/frequency cap in existing feedback surfaces; show eligible/shown/responded/distribution, not selected historic complaints as population satisfaction. |
| Guardrails | Protected objective/score/access/reward equivalence; save/error/latency/fallback/burden/provider cost. Wrong response or denied mic is not automatically an incident. |

Reuse comparable permitted checks first; where transfer/recall needs new probes, replace one legal optional practice opportunity with the **same** short reviewed assessment in A/B. No appended test battery. Objective/difficulty/timing/help/rubric and source-safe unseen variants must match across locales/platforms. Sparse tags and client-reported correctness do not provide this authority.

**Measurement changes learning.** Added retrieval can help or burden learners: contrast becomes existing format + common measurement versus new journey + common measurement. State this honestly rather than claim untouched A; cap equal burden, exclude measurement-only returns from primary and report generalization limits. No extra public measurement arm/pilot. Product application feedback remains part of B; official rewards stay equal.

### D9. Real calibration, bounded decision, no convenient invented proof

Private aggregates provide descriptive traffic/retention, not this enrollment endpoint's account-level day mean/variance, new/existing eligible split or universal help/recall evidence. Small registration cohorts, inventory and source-default flags cannot fix power or effective rollout. Read the private evidence memo, not a public copy of its unsuppressed figures.

Before activation, freeze a versioned protocol using minimal passive canonical evidence under the pinned source definition: cohort mean/variance, eligible arrivals, actual delivery fraction, meaningful effect, cost ceiling, knowledge/completion harm margins and feasible maximum horizon. Account-level empirical resampling/simulation estimates power for bounded days; calibrate cohorts separately. Keep values `UNCALIBRATED` until measured. This is a valid-test readiness gate, not a demand to prove boredom or recruit pilots. Remove arbitrary uplift/example sample counts from the earlier proposal.

ITT account-level differences/intervals; new/existing primary claims are a Holm alpha .05 family. Repeated cards are not independent learners. Combined fixed-weight estimate is secondary; subgroup slices exploratory unless powered. One cohort's benefit cannot mask another's harm. D1/D7/D14 cannot be selected after seeing which wins.

Enrollment includes at least two weekly cycles; total horizon also satisfies power, last D14 maturation and 48 h reconciliation. Freeze a maximum duration before outcomes. No efficacy peeking; safety is continuous. If traffic cannot support the desired effect in that duration, show the detectable-effect curve and report inconclusive/large-effect-only evidence, not invented users or extension until significance.

Per-cohort benefit requires a meaningful primary gain with corrected uncertainty, adequate common knowledge coverage/non-inferiority and no completion/safety/cost breach. Knowledge/access/score/reward harm stops treatment. Missing/biased/underpowered data is inconclusive. SRM p<.001 triggers investigation/no-win, not proof of pedagogy harm. Check assignment/event loss and delivery/probe response by arm. History uses compatible nonoverlapping windows descriptively, never causal before/after proof.

### D10. Existing reporting, privacy and safe stop

Complete the authenticated fact→canonical receipt→deduped storage→typed full aggregate→existing Admin disclosure/export→registry/runtime-chain-test path. Extend event/passive/diagnostic/route/critical-path owners together, not just enums. No private answers/audio/transcripts/tokens/URLs in telemetry or public docs. Best-effort observations cannot roll back learning; authoritative allocation/assessment failure returns unconfirmed/base state rather than fake success.

Use bounded indexed SQL/daily sufficient aggregates for complete denominators, not 5,000-row/30-day detail truncation. Preserve existing private 24 h snapshot/auth/freshness/unavailable behavior. Live kill/incident state is independent of cached statistics; no new dashboard or forced production refresh.

Modes `off|shadow|ab`, immutable revision and independent emergency veto use the existing exact signed Admin settings action, with one contextual action/no redundant confirmation. Shadow has no learner exposure/reward/SRS writes. Global launch is 50/50 after internal gates, not a public percentage ladder.

Test acknowledged online stop ≤60 s across workers: config cache ≤15 s, foreground renewal ≤30 s, lease ≤60 s. No per-card config SQL or disabled polling. Use monotonic elapsed validity, immediate foreground/task checks and revalidation after process restore; uncertain suspended/offline leases expire to base. Instant remote stop for a disconnected device is impossible and must not be claimed. One displayed task can settle/skip; no new task after veto/expiry. Preserve original resume, official result, immutable feedback/assignment and schema readers without duplicate XP or destructive populated downgrade.

Optional planning has a bounded timeout/base fallback and no first-card dependency. Measure affected p95/query/pool/provider budgets through existing infrastructure; zero tolerance for protected source/access/grade/reward regressions. No DB connection across provider IO or private cross-account cache.

## Risks / Trade-offs

- Novelty without knowledge → common transfer/recall plus qualified regular return, not raw card/XP counts.
- No short-session optional space → core/retrieval priority and honest coverage/time; no hidden extra lesson.
- Valid free language outside rubric → unscored formative feedback, not fabricated wrong/mastery.
- Low traffic/old clients → feasible calibrated horizon and ITT uncertainty, not a promised small-lift result.
- Common probes alter both products → equal burden and explicit contrast/generalization limit.
- Private aggregate mistaken for raw sessions → controlled private memo, grain/freshness/overlap rules and no public small counts.

## Migration Plan

Re-fetch main before implementation; current source head `0160_smart_routing_pwa_state` does not reserve the next revision. Build source projection/receipt/instrumentation with flags OFF, then current renderers/results/report chain in bounded packages. Add only the neutral-receipt migration/purge/retention/bootstrap guards; preserve old store semantics. Complete all-source, auth/access/result, A/B equivalence, browser/native/provider and connected/offline kill evidence before activation.

Implementation/activation are later authorized work, not performed here. Internal QA uses synthetic cases and all-course coverage, with no recruited pilot. Freeze measured protocol, release negotiated adapters OFF, then enable one global revision and assess at the fixed mature horizon. A Git push is not installed-client/provider acceptance. Existing handoffs keep their ledgers; no automatic 100% B rollout or archive with unresolved gates.
