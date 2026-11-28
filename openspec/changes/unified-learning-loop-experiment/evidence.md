# Evidence and decision basis

Audited runtime source: GitHub main `d7e91f42851d7823917f62ad04f2faa387a1691c`, 2026-11-28. This revises the earlier `45506d37` proposal, not a second feature plan. The private aggregate archive was also read at an immutable revision; its exact observations and paths remain in an owner-local private review, outside this public repository. No raw learner records, production SQL or provider/device session were accessed.

## 1. Product evidence and what the audit is for

The owner explicitly reports that learners, including the owner personally, are tired of the repeated learning format. **Accept this as the product problem to address.** Do not make a further investigation proving boredom a prerequisite for new-format planning. Code-level counts cannot invalidate this first-hand experience.

The distinction is between interaction type and experience: changing a word, ordering eight card types differently, or adding another multiple-choice card can still feel like the same predictable lesson. The audit below identifies safe reuse, hidden constraints and a fair effectiveness test; it does not vote on whether the owner's experience is real. A/B tests whether the proposed coherent experience improves learning and return, not whether the owner was right to feel bored.

| Claim | Evidence class | Permitted conclusion |
| --- | --- | --- |
| Repetitive experience is tiring | Direct owner/learner qualitative report, reaffirmed 2026-11-28 | The product needs a more varied, meaningful learning experience. Population prevalence and effect size are not quantified by this report. |
| Some short profiles lose practice variety and retrieval opportunities | Reproducible enabled-path source execution, below | Change selection without dropping teaching; do not simply append more tasks. Actual rollout state must be checked before attributing existing production behavior to this path. |
| Learners cannot see/feel enough independent progress | Product hypothesis plus narrow current result projection | Add truthful objective-specific evidence; measure independent application rather than relabel XP/completion as mastery. |
| Current tools are completely disconnected | Refuted by shared goals/weakness/SRS/Daily Plan code | Improve continuity and visibility of the same objective; reuse existing tools. |
| Current aggregate changes prove boredom is the cause | Unsupported by archived observations | Preserve competing access, acquisition and technical explanations in analysis; they do not cancel the requested product change. |

## 2. Reconstructed current learning path

| Stage | Current source and practical constraint |
| --- | --- |
| Enter | `course-v3.html:4969–5015`: access/reserve → content → up to 1.8 s first-audio wait. No observed production latency distribution was obtained. `entitlements/lesson_access.py:119–132` already dedupes allowance reservation. |
| Teach/check | Current ordinary parts interleave teaching, choices, pronunciation, listening and builders. `gen_course_v3_from_seed.py:1230–1291,1362–1419,1593–1595` already rotates types, retention questions and dialogue tasks. A scene therefore needs real turn orchestration/role participation, not renaming cloze. |
| Answer/help | `course-v3.html:4828–4856,6042–6072` grades locally and adds objective repair where tags exist; guided work can affect displayed accuracy. Browser `:4866–4908` records observed interactions, not a universal server-owned first-unaided answer. |
| Abandon/resume | Browser page sessions and Android's local material-reference-bound resume do not preserve a common complete earlier-answer/help trace (`LessonViewModel.kt:445–447,829–833,990–1007`; `LessonResumeStore.kt:14,23–25`). Android already restores stable material identity; no new cursor system is needed. Absence of saved mistakes before completion is not absence of struggle. |
| Complete | `main.py:3639–3677` validates reported mistakes and confirms progression/reward. It does not verify every positive answer or independent transfer. `course_lesson_mistake_material_service.py:419–506` verifies a correction from original material. |
| See result | `learning_result` is returned only for part order 1 (`main.py:3674–3677`, `desktop_course_service.py:801–808`); it can show a saved correction, not newly proven independent ability. Existing confirmed-result UI already has a safe single Continue action. |
| Continue | `course_today_service.py:111–120` freezes daily task identities; Voice `:444–546` already reads shared SRS/goal/weakness. The next-part/result/streak/ad/access transitions have separate purposes; do not label every exit boredom. |

## 3. Reproducible queue findings

Use [audit programs](audit/queue_audit.py), [sensitivity](audit/queue_sensitivity.py), [actual JS projection](audit/queue_parity.js) and [compact summary](audit/summary.json). They import the real planner/curated pictures and execute actual extracted `buildQueue`/reference helpers, with UI-label stubs and no network/database. Reproduce from project root with an existing configured Python environment:

```sh
PYTHONPATH=. python3 openspec/changes/unified-learning-loop-experiment/audit/queue_audit.py /tmp/hsk-learning-queue-audit
PYTHONPATH=. python3 openspec/changes/unified-learning-loop-experiment/audit/queue_sensitivity.py /tmp/hsk-learning-queue-audit
node openspec/changes/unified-learning-loop-experiment/audit/queue_parity.js /tmp/hsk-learning-queue-audit
```

Audit: 746 parts × five minute options × five primary goals, plus 20 five-minute goal/focus profiles, three multi-goal profiles and explicit OFF baseline. **35,808 planner calls; 109,662 queue checks** over UZ/RU/TJ. Types and original retained references matched; no protected card was omitted. These are constructed initial queues, not visited screen paths, linguistic approval, measured duration or real-user sessions. Conditional N1 repair and up to three adaptive overlays are outside this initial-queue parity check.

Five-minute primary-only/no-focus profiles, using real curated picture candidates:

| Goal | Mean ordinary optional type diversity before → after | Parts with no ordinary optional task | Protected core already over budget |
| --- | ---: | ---: | ---: |
| HSK exam | 4.941 → 3.997 | 0 | 0 |
| Daily communication | 4.941 → 1.673 | 257 | 123 |
| Travel | 4.941 → 1.193 | 344 | 257 |
| Work | 4.941 → 2.168 | 123 | 0 |
| Study | 4.941 → 3.375 | 0 | 0 |

Of 1,255 existing `retention_review` cards, travel/communication/work keep only 82/84/106 in those specific profiles. Entire retention sections disappear in 546/544/523 parts. This is permitted by current trimming policy (`course_lesson_plan_service.py:89,262–305`), not evidence of a regression or measured forgetting. It makes **preserving a retrieval opportunity when a legal slot exists** more valuable than maximizing a raw type count.

Concrete source cases: five-minute work `hsk1/14` and `/15` both retain one optional pronunciation task at section 3/card 3; `/11` and `/12` both retain listening→pronunciation, although `/12` additionally gets two picture words. Five-minute travel `hsk1/1` loses both retention questions and retains one optional pronunciation task. Conversely, `/2→/3` has substantially different retained optional practice. Focus and multiple goals alter these outcomes and must remain analysis strata.

Counterevidence to a literal claim of identical queues: 0/739 adjacent pairs have identical complete raw-type sequences; baseline mean is 8.307 interactive types. Ten-minute HSK-exam and all tested 30-minute primary profiles keep all optional source cards. Picture insertion can increase whole-queue type count while ordinary retrieval disappears. **None of these facts disproves a monotonous experienced lesson structure.**

Both adaptive/lesson-plan source defaults are OFF (`config.py:141,150`), and existing rollout/device tasks remain open. No effective production switch was verified. Describe the measured trimming effect as conditional, not universal live behavior.

## 4. What the private aggregate archive changes

Read the canonical full aggregate archive, not its old compatibility slices. Source timestamps, selected periods, freshness, metric states and platform overlap were checked against the actual application readers. Exact business numbers stay in the private report.

- Nonoverlapping recent windows show changed acquisition alongside course engagement; they do not isolate a lesson-format effect.
- Current retention has small registration-cohort denominators and includes app-open evidence. It does not provide the proposed experiment's new/existing enrollment baseline or universal learning-day distribution.
- Started/completed distinct-account sets are not matched attempts. Their ratio cannot establish abandonment. Session detail is explicitly unavailable once the bounded reader exceeds its limit.
- Existing sales A/B is a restricted sales population with an early-signal/not-ready state. It is neither this learning experiment nor a reusable effect estimate.
- Feedback is older, selected completed responses without a shown/invited denominator. Access/price/technical signals are competing explanations; absent categories do not establish absence of boredom.
- Device/version inventory is not an active treatment-capable population. Some scoped snapshots are historical; Overall filter availability is not proof a platform has no learners.
- Rolling snapshots overlap; platform counts can overlap. No sums across them, no fabricated daily series, no public copying of unsuppressed private small cells.

The archive supports descriptive calibration and prioritization. It cannot reconstruct first answer→help→retry→exit, independent transfer, precise audio latency, or satisfaction for the full learning population. Final sample size/horizon still needs the new endpoint's baseline. Low observed enrollment also makes a promised short, small-lift proof unjustified; do not manufacture an MDE to produce an attractive timeline.

## 5. Minimal storage and independent verification

Reuse `CourseMiniAppEvent` canonical uniqueness for an **authoritative** immutable server-only assignment receipt, not best-effort analytics. Existing practice nonce/digest and adaptive first-answer snapshot mechanisms provide reusable patterns. Their existing stores are not interchangeable: practice accepts HSK 2.0 only and is Smart-analysis-gated; `CourseAttempt` requires a legacy lesson FK; adaptive is review-only with 14-day cleanup/one-day answer age. One bounded neutral exercise receipt store is justified for independent assessment/help and source snapshots. A synchronized cross-device course-session/cursor system is not required for stable experiment arms.

Verification performed against audited runtime source:

- Planner/card/retention/adaptive focused suite: 87 tests run, two PostgreSQL concurrency checks skipped; remaining checks passed. Separate 46 planner/material tests passed and overlap this evidence; do not add totals.
- Existing adaptive JavaScript module passed using synthetic DOM/network.
- Seven selected Chromium learning-result tests passed, 26 deselected, with mocked authenticated network and real DOM. No claim of WebKit/physical-device/provider acceptance.
- Reproduced source-queue checks above preserve type/ref contracts, not educational effectiveness.

Focused suite command (use the existing configured environment, not a dependency install): `python3 -m unittest tests.test_course_lesson_plan_service tests.test_course_card_contract tests.test_course_retention_review tests.test_course_adaptive_lesson_service -q`. The two skips are real-PostgreSQL row-lock concurrency cases in `test_course_adaptive_lesson_service.py:590–603`; they remain unverified here. JavaScript command: `node tests/test_course_adaptive_pwa.js`.

Primary external evidence for the eventual product decision is the real randomized account outcome plus source-grounded independently scored application/recall. CI/source counts establish engineering correctness only. [Retrieval research](https://doi.org/10.1126/science.1152408) motivates measuring application/recall and reminds us that added tests can themselves change learning; it does not prove these HSK formats work. [Experiment data-quality research](https://www.microsoft.com/en-us/research/publication/diagnosing-sample-ratio-mismatch-in-online-controlled-experiments-a-taxonomy-and-rules-of-thumb-for-practitioners/) motivates allocation/loss checks before interpreting effects.

## 6. Performance branch compatibility snapshot

Owner-requested read-only comparison, 2026-11-28: local `codex/perf-group2-20261123` HEAD `550343d2750700a7202bafee982e2a9202cf02e3`, compared with main `6bc754eaa64ce1599d725f6bc3f16ac7418da950`. The local branch has six unique commits and is 64 commits behind that fetched main. Its extra dirty files were inspected, not modified, staged, tested or merged by this audit. The graph covers committed HEAD only; dirty source was read directly.

| Source status | Evidence / meaning |
| --- | --- |
| Committed | Six packages: Dictionary/Phrases cover, slow-start panda/hub skeletons, Rating warm reuse, Pro sheet, checkout/trial first paint and in-place refresh. `550343d2` does not prove eventual merged/device acceptance. |
| Uncommitted WIP | Active-session Back/exit confirmations and related catalogs/CI/test, including untracked `tests/e2e/test_pwa_session_back.py`. Documentation records local work, but this audit did not independently run it. |
| Planned | 2.11 opt-in formative local grading; 2.7 remaining lesson/result latency; other open root-tab/startup/Android/backend tasks. No local-grading API/native patch exists in this inspected WIP; current serializers still omit keys. |

Scoped dirty-source identities (Git blob hashes, not a release):

- `app/static/course-v3.html`: `8a4d8e890f800ce628d067d658c9e4d10028e6c2`.
- `app/static/course_v3_data/iphone-pwa-practice-boot.js`: `4410c08912deea886bc250f0c71dcc323933fd10`.
- Performance `design.md`: `7fdb2a273d647f2a3f0c9a656b7ff0cd4d20606d`; working `tasks.md`: `5f680be542f2d96a2be7c7b6bdcb4f2513748e29`.
- Untracked session-Back test: `525cdfa43382d066291b0de3443df115d74615d9`.

Queue/material-ref, plan/picture and resume/mastery extraction blocks were byte-identical across the original `d7e91f42` audit, current main, performance commit and its dirty snapshot (SHA-256 prefixes `7f1e76a1c8b5d3eb`, `adb73d9649cc79aa`, `5104677c38fe506b`). Planner, TTS service, Android LessonPlan, manifest and lesson JSON were unchanged in scope. The 746/109,662 audit therefore remains relevant historical evidence with matching inputs; it is **not** a test of a future merged tree. Re-run the existing programs on the reconciled candidate and pin commit/content/function/audit-program digests before implementation acceptance.

Timing evidence distinction: a committed `pwa_launch` clientlog beacon already exists on main/perf, separate from QA-only `iphone-pwa-perf.js`. It is anonymous/best-effort, skips launches hidden before ready and cannot join account/arm/receipt or establish complete failures/audio latency. No such raw production timing series was read from the private aggregate archive. The existing first-audio wait up to 1.8 s remains in the inspected branch.

The integration map and shared tests are in [design D11](design.md#d11-integrate-with-the-active-performance-work). No new product-runtime tests were run for this documentation-only compatibility update, and no performance improvement or completed merge is claimed.
