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

Existing auth/access/sequence/source ownership precedes receipt issuance/acceptance: Telegram initData, PWA cookie+CSRF+same-origin, native bearer/bridge. Common unaided-assessment prompts omit keys. Authorized formative tasks may use the opt-in local-grading projection planned by performance 2.11, with immediate feedback and background server regrade; do not reintroduce a round-trip wait for those tasks. Only accepted server evidence establishes verified results. Optional receipt failure cannot change official completion/hearts/score/XP/unlock.

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

### D11. Integrate with the active performance work

The owner explicitly selected `codex/perf-group2-20261123` as the compatibility target. Read-only comparison on 2026-11-28: local HEAD `550343d2750700a7202bafee982e2a9202cf02e3`, six unique committed packages and additional uncommitted session-Back changes; compared main `6bc754eaa64ce1599d725f6bc3f16ac7418da950`. This is not a merged release. [Evidence](evidence.md#6-performance-branch-compatibility-snapshot) pins the dirty files separately. Keep performance progress in [its current tasks](../perf-pwa-android-backend/tasks.md); the table below defines only what learning must consume.

| Boundary / status | Existing owner to reuse | Learning integration / verification |
| --- | --- | --- |
| Lesson entry, committed 2.8 | `HSKLessonPresentation.beginLessonEntry` → `reveal(build)` / `cancel()` | PWA uses `showAfterMs:300,minVisibleMs:300`; a fast start shows no panda. Preserve Telegram's own default/immediate 720 ms behavior. No new entry timer/loader per scene turn, reply, help or receipt. |
| Existing practice/layer continuation, committed 2.4/2.8/2.12 | `RESOURCE.PRACTICE_COVER`, `mountPracticeFrame`, `acceptPracticeActor`, `revealPracticeFrame`, `closePracticeFrame`; `HskPwaPracticeBoot` | Hub title/Back at once, matching bars after 150 ms, no hub panda; first-paint/actor readiness and 20 s local Retry remain. Follow existing close→cleanup/report→focus/progress/feedback chain rather than remove iframes directly. |
| Active-session Back, dirty portion of 2.6 | `NavBack` → `App.requestExitFlow` / `confirmExitFlow`, `saveLessonResume`, `Foundation.pause`; practice boot exit handlers | Scene/mission stays inside existing `#flow`, stationary during PWA swipe; one completed Back asks once, cancel keeps same turn/question/receipt, confirmed exit preserves the existing lesson/Foundation promise. Test/Mistakes no-save confirmation must not acquire a false resume promise. Add cleanup to existing exits, not another history controller. |
| Horizontal interaction | `NavBack.ownsHorizontalSwipe` / `[data-nb-ignore]` | Give real scene strips/token banks their own horizontal gesture ownership without swallowing system Back elsewhere. Preserve refresh suppression while flow/sheets are active. |
| Instant formative feedback, planned 2.11 / design 15 | Opt-in response-key projection, shared normalization/parity, bounded owner-scoped outbox and server regrade | Reuse when it lands; currently not implemented in committed or inspected dirty code. Telegram retains its existing server path. No global key serializer change; common probe purpose must refuse local-grading keys even if requested. |
| Lesson/result timing, planned 2.7 | Existing lesson start/complete/result owners | Extend pending-state/result regression rather than implement a parallel save/result pipeline. No optimistic rank/XP/streak. Existing first-audio race up to 1.8 s remains in this snapshot; do not claim it fixed. |
| Refresh, warm-up and optional assets | Existing refresh/worker readiness owners, including pending 2.15 | Do not reload an active scene, warm all media during launch or eagerly prefetch probes/keys. Bound upcoming-turn audio by speaker-aware identities while preserving legacy text-only word audio/cache. |

**Formative is not a secure measurement purpose.** For common unaided probes, use immediate neutral tap/pending feedback followed by the server verdict. Before an accepted first response or authenticated help reveal, answer keys/solutions cannot enter their public payload, DOM, bundle, prefetch, cache or outbox; later feedback follows D4's recorded reveal policy. An already key-exposed formative item cannot later be an unseen common probe. Keep serialized first-answer/help authority; local correctness and an enqueued request never establish mastery/reward/primary learning days. Preserve performance's formative feedback contract rather than imposing its accepted key-exposure trade-off on common measurement. Speech/AI keep their genuine server-processing/skip states.

Share outbox conventions and canonical identifiers, not endpoint/purpose authority. Freeze source/rubric/config/recording versions and server-accepted outcome time in both arms; delayed local writes remain pending/lost until accepted, never backdated by arbitrary device time. The existing anonymous `pwa_launch` beacon (one best-effort launch report) is separate from the QA profiler and authenticated receipts. It cannot supply arm/unique-user/audio evidence. Do not append account, answer or experiment data to that log channel.

Performance acceptance derives from [decision 12](../perf-pwa-android-backend/design.md) and its existing lab: interactions to next paint ≤200 ms; warm openings to first useful frame ≤1000 ms; cold shell ≤1500 ms; already-fast actions keep their measured baseline within 10%. Do not apply an interaction frame target to ASR/provider completion or call immediate pending UI a confirmed verdict. Extend the existing relevant entry/layer/session-back/refresh/result/parity fixtures on Chromium and WebKit; match native tests for changed Android and SQL/index evidence for backend writes. No second timing stack or unrelated full-lab rerun.

**Sequence:** reconcile reviewed performance packages and committed owner-accepted WIP with actual latest main before editing overlapping learning helpers. Never copy an entire old `course-v3.html`, checkout or practice page over newer main: this branch is behind current access/checkout/feedback fixes. Pin the resulting source/API versions, re-anchor changed i18n/cache tokens once on that candidate, rerun the three queue-audit programs and joint focused regressions, then freeze that same performance/recording policy across A/B. If relevant 2.11 or WIP has not landed, retain its negotiated old-compatible path and the dependency in its original owner; do not reimplement it here or wait for unrelated performance tasks. A later material common release is a versioned analysis/rollout event, not silently pooled data.

## Risks / Trade-offs

- Novelty without knowledge → common transfer/recall plus qualified regular return, not raw card/XP counts.
- No short-session optional space → core/retrieval priority and honest coverage/time; no hidden extra lesson.
- Valid free language outside rubric → unscored formative feedback, not fabricated wrong/mastery.
- Low traffic/old clients → feasible calibrated horizon and ITT uncertainty, not a promised small-lift result.
- Common probes alter both products → equal burden and explicit contrast/generalization limit.
- Private aggregate mistaken for raw sessions → controlled private memo, grain/freshness/overlap rules and no public small counts.

## Migration Plan

Re-fetch main before implementation and reconcile the touched performance packages under D11 before changing shared helpers; current source head `0160_smart_routing_pwa_state` does not reserve the next revision. Build source projection/receipt/instrumentation with flags OFF, then current renderers/results/report chain in bounded packages. Add only the neutral-receipt migration/purge/retention/bootstrap guards; preserve old store semantics. Complete all-source, auth/access/result, A/B equivalence, browser/native/provider and connected/offline kill evidence before activation.

Implementation/activation are later authorized work, not performed here. Internal QA uses synthetic cases and all-course coverage, with no recruited pilot. Freeze measured protocol, release negotiated adapters OFF, then enable one global revision and assess at the fixed mature horizon. A Git push is not installed-client/provider acceptance. Existing handoffs keep their ledgers; no automatic 100% B rollout or archive with unresolved gates.
