# Design

## Context

The source baseline is `5bbbf707`. The verified startup contract in `tests/test_first_lesson_direct_flow.py` already starts an authenticated first course part on PWA and Android. Li collects goals and preferred focus under its own [handoff](../../../docs/onboarding-li/RELEASE_READINESS.md). The public automatic PWA Li entry setting defaults off. Native guest onboarding and every live flag value have separate acceptance. [Open PR #322](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/322) also owns first-to-second navigation changes. This delta uses the main result boundary and keeps its proposed onboarding/next-part choreography out of scope.

| Existing capability | Source and observed gap |
| --- | --- |
| Lesson completion | `app/main.py:3375`, `app/services/desktop_course_service.py:585` and Android's service adapter already save progress, XP and canonical mistakes. The PWA `showLevelUp` and Android `LessonCompletionCelebration` show activity and accuracy but lack grounded review evidence. Web checkpoint copy currently overstates what completion demonstrates. |
| Planning and learning signals | `LearningSignalsService` reads persisted preferences, progress and mistakes. `CourseTodayService.payload` attaches one per-day plan to the existing map. `DailyPlanService` freezes task identities and rehydrates access and done state. Both clients already render the plan. |
| Review and mastery | Canonical lesson mistake resolution, the existing Mistakes UI, word mastery, adaptive reviews and goal-aware picture flashcards already exist. One graded response shows attempt performance. Delayed recall or independent use needs separate practice evidence. XP and completion remain activity signals. |
| Commercial baseline | `course_sales_experiment_service.py` evaluates a sticky Telegram-ID cohort at HSK1's first full checkpoint, flat part 3. The PWA adapter shares offer assignment but filters sales events at the course writer and intake. Android map lacks this offer. PWA inline checkout has its own authenticated attempt funnel and webhook-owned confirmation. Android Direct has existing checkout and Play is consumption-only. |
| Measurement and delivery | V10 Course activation and return, Funnel, Finance, and Experiments already exist. The existing diagnostic catalog covers lesson save, practice access and checkout. Follow the [current analytics](../../../docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md), [monitoring](../../../docs/monitoring/MONITORING_CONTEXT.md), and [progressive loading](../../../docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md) contracts for the changed paths. |

### Product and learning rationale

A beginner can start learning during the existing onboarding handoff. The useful feedback at the end is what was covered, one repairable mistake and a clear way to keep studying. Preserve the single primary action and give the learner a review cue at the point of evidence. Present Pro when a real constraint gives it meaning. Optional lesson projection and copy add zero model requests. Evidence of learning comes from later recall or use rather than the completion animation.

HelloChinese documents native-speaker immersion, pronunciation feedback and spaced repetition. SuperChinese combines a structured course with AI speaking practice in its CHAO tier and has a separate HSK exam product. Duolingo describes personalized review and has dedicated work on Chinese character and tone learning. HSK AI can test whether its Uzbek, Russian and Tajik HSK course with error-linked review makes the next step clearer. That is a local product hypothesis. [HelloChinese](https://www.hellochinese.cc/), [SuperChinese FAQ](https://www.superchinese.com/faq.html), [Duolingo teaching method](https://blog.duolingo.com/duolingo-teaching-method/), [Duolingo Chinese course](https://en.duolingo.com/course/zh/en/Learn-Ch)

## Decisions

1. **Extend the saved result.** Keep the existing course views and transaction boundaries. Use the already loaded authenticated lesson topic. After a new first-part save and existing canonical mistake persistence, PWA and Android can attach the same optional `learning_result` display projection. It carries at most one bounded example from canonical material. No additional SQL query, client fetch, schema, cache or answer validation path. Omit it from duplicates and unrelated results. Continue to report the existing `lesson_completed` event. Attach the optional display block outside event payloads. In particular, the Android replay snapshot contains no correction text. Android parses it with an optional default. Shared Telegram and Desktop callers keep their existing results.
2. **Give a clear next action in the existing hierarchy.** Use the existing course return or access-checked next-part action and visible links to the existing Today and Mistakes surfaces where appropriate. Avoid claiming that sequence advancement grants access. Use the existing map refresh and Daily Plan contract. Keep frozen task IDs, review-bank reconstruction and mastery ownership. With sparse evidence, use the usual course-return action.
3. **Use access context to explain Pro.** Add only channel-appropriate learning copy through the existing limit context for the lesson or review action. Use a confirmed gate and supported client action. Preserve every quota decision, disabled channel, Trial or pending status, existing payment method and existing price. Leave the HSK1 checkpoint bridge and its fixed preview alone.
4. **Use current reporting and pre-register any future A/B scope.** Read the following together before cohort selection. Pull no learner detail into release reports.

| Measure | Population and evidence |
| --- | --- |
| Activation | Earliest confirmed real course completion per new canonical account within 24 h of registration. Use existing owned events and platform tag. Audit prior completions and account deduplication before labelling a metric first-ever. Existing V10 course metrics remain the trend baseline. |
| D7 | V10 Overall uses activity in hours 168–192 after signup. Platform returns use the first verified platform-use anchor. Display each with its own denominator and maturity. Learning-only return is an additional measure only if the event-to-Admin chain and eligible cohort are proved. |
| Paid conversion | Within seven days of an eligible assigned exposure, count the first approved real subscription by canonical owner. Use existing verified funnel outcomes, without treating pending, trial, refund, one-time HSK unlock, or manual grant as a new Pro subscription. Cross-platform exposure is unavailable today. |
| Subscription retention | Paid subscribers eligible to renew whose next paid term is approved by the due date plus the defined reporting grace period. Use Finance's existing renewal-payment share only under its own label. Cohort retention is unavailable until expiry and renewal can be joined reliably. |
| AI cost | Report recorded, priced provider cost by the supported Finance scope, with unknown-price calls disclosed. Monitor total cost as a guardrail. This change makes zero provider calls and current Finance data cannot support platform cost attribution. |
| Errors and speed | Existing lesson completion, lesson dispatch and applicable access/checkout diagnostic path and Admin Inbox. Compare identical test profiles for request count, response bytes and save path SQL. Real-client reliability remains a release condition. |

Use `sales_value_v1` only for its existing policy, cohort and historical results. It excludes ineligible/legacy/campaign users, assigns by Telegram identity, and its existing decision criteria include 7-day matured observations, SRM, guardrails, at least 200 per arm, 20 approvals, minimum 14 days and maximum 42 days. The neutral learning result goes to all eligible branch-test clients. Before any future commercial A/B, show usable exposure and supported CTA through the existing event → canonical owner → Admin chain, define the smallest non-overlapping cohort in the existing experiment infrastructure, and pre-register effect size, duration and stop conditions from its baseline. Until then report commercial increment as unavailable. Never widen or relabel the historical experiment.

## Risks / Trade-offs

- An unverified or declined submission and incomplete material → show only available facts. A valid completion and review write use the existing transaction. Presentation failure falls back to the existing result.
- A stale map or a spent quota → use the existing guarded navigation and current server decision. Never derive grants from a result or cached plan.
- Private data and duplicate saves → authenticated adapters only, no review text in analytics/diagnostics, no new durable state, and no added progress mutations on retry.
- Startup and display stability → render the new block synchronously from the completion response. Keep the current local save and retry states and the established geometry. Test both browsers, reduced motion, short and long UZ/RU/TJ, and both Android build variants.

## Migration Plan

No migration. Land small local commits in the isolated feature branch. First run server and client tests, plus the off-path legacy and absent-data cases. A future authorized release requires verified private staging, physical Safari/Home Screen and Android Play/Direct smoke, analytics and incident chain checks, and agreed stop conditions. Keep the historical experiment untouched. Rollback reverts the presentation commit(s) or serves the existing response without the optional block, with persisted progress, mistakes and billing intact. Preregister confirmed-save failures, incidents, negative activation/return impact and change-path latency regressions as stop signals before any percentage rollout.

## Plan review

The implementation baseline uses one result projection across the two existing screens. It combines the daily plan, progress and mistake handoff in the same client task and reuses the map refresh. A new onboarding step, result screen, recommendation API, quota check, mastery score, migration and competing experiment add no required evidence. The active perf initiative owns wider loading remediation and device profiling. Its existing tests serve as regression checks here. Access copy remains a separate package for rollback and review. The consolidated plan is the implementation baseline for this branch.

Local baseline on `5bbbf707` includes 73 Python tests and 14 subtests covering map, Daily Plan, PWA parity, performance policy and layout helper. Initial shell smoke passed in Chromium and WebKit, and the existing native completion DTO test passed on Direct and Play. Existing head failures include the next-part short-headline fixture and Russian Practice geometry at 320 px on both browser engines. Keep these recorded separately from regressions of the displayed result.

## Open Questions

Staging cohort counts, physical-device timing, and actual historical or trial-inclusive exposure coverage need deployment-side evidence. These measurements govern release and business interpretation. Worktree implementation uses local fixtures and verified source contracts.
