# HSK AI — Analytics Integrity & Future Feature Coverage Plan

Status: **PLANNED / NOT IMPLEMENTED**. Planning baseline: `main` commit `c80d72184b853ec4b83141403f7e2c77dcffb557` (2026-11-08 UTC). Revalidate `main` before coding. This document is a **canonical implementation checklist**, not proof that production analytics is correct or that CI enforcement already exists.

## Outcome

Keep the analytics HSK AI already collects. Repair disconnected, incomplete or misleading measurement paths so product questions can be answered from **verified user/account, journey, payment, learning and error evidence**. Every subsequent feature/flow change must either integrate with the existing analytics contract or demonstrate why its behavior does not require instrumentation. Prevent future features from silently falling outside dashboards, by combining **agent instructions + a source-to-consumer coverage registry + focused CI + end-to-end tests**.

**Do not** rebuild Analytics V10, add a new database/Redis/CDP/vendor by default, infer missing events, or create extra tracking for cosmetic-only changes. Honor canonical-account ownership and server-authoritative billing/progress; avoid personal data in telemetry.

## Verified source baseline (inspect again at task start)

- Existing course and native events: `app/db/models/course_miniapp_event.py`, `app/services/course_miniapp_analytics_service.py`.
- Checkout conversion events: `app/db/models/conversion_funnel_event.py`, `app/services/conversion_funnel_service.py`.
- PWA Pro event emit and authenticated persistence: `app/static/course_v3_data/iphone-pwa-inline-pro.js`, `app/api/pwa_auth.py`, `app/api/lava_checkout.py`, `app/services/lava/`.
- Admin aggregation: `app/admin_api/pwa_analytics*.py`, `app/admin_api/pwa_metrics.py`, `app/admin_api/pwa_statistics_cache.py`, `docs/admin-pwa/READ_PROJECTIONS.md`.
- Existing identity/source and traffic: `app/services/admin_analytics_identity.py`, `app/services/subscription_entry_analytics_service.py`, `app/services/public_site_analytics_service.py`, `app/db/models/public_site_traffic.py`.
- Current V10 specification: `openspec/specs/admin-real-analytics/spec.md`; archived plan is historical, not a current task list.

### Code-confirmed coverage gaps to investigate, not blindly patch

1. The `iphone_pwa` selection in `app/admin_api/pwa_analytics_cache.py` returns `not_instrumented`, and platform metrics declare `iphone_pwa_available=False`, even though selected PWA Pro events are being persisted elsewhere. Determine *which* PWA metrics are actually provable before enabling any.
2. `retention()` in `pwa_analytics_learning.py` counts `miniapp_opened` for D1/D7. It is **Mini App-open retention**, not all-platform learner/product retention. Preserve a clearly labeled legacy series if needed; add separately defined cross-platform learning/return cohorts only with verified activity proofs.
3. The Admin V10 `funnel_metrics()` reader uses legacy `checkout_opened/payment_screenshot_submitted/payment_approved` events. The new PWA Pro `pwa_pro_*` events and Lava provider lifecycle need a **separate linked attempt funnel**, not unsafe mixing of unlike steps.
4. PWA UI `emit()` swallows telemetry delivery errors (intentionally nonblocking for payments); assess missing/dropped-event risk with bounded health counters, safe retries and server reconciliation. Do not block checkout, alter payment authority, or claim exactly-once delivery without proof.
5. Public-site traffic is aggregated by day/source only; closest subscription entry before payment is **descriptive proximity**, not ad-to-payer attribution. Distinguish tagged visits, verified account linkage, and unsupported attribution.
6. Detailed learning/experiment reads intentionally cap at 5,000 rows and all-time detail uses a last-30-day scope. Preserve explicit `unavailable/detail_limited` where coverage is insufficient; use scalable indexed/grouped SQL for any newly required complete metric, with query-plan and performance evidence.
7. The Report section currently lists row counts and latest timestamps for selected tables; these do not validate event delivery, identity integrity, funnel stage reconciliation or metric freshness by platform.

## Phase 0 — permanent Codex/agent obligation (do first)

- [ ] Add and maintain the permanent **Analytics impact rule** in root `AGENTS.md`; reference this plan there. Refer to the same canonical rule from `AI_RULES.md` only if helpful, without conflicting duplicate rules.
- [ ] **Before repairing feature metrics, ship the smallest CI guard**: any newly changed critical user/business flow must carry an Analytics Impact declaration (covered/reused/partial/unavailable/not-applicable), a valid registry mapping or reviewed exemption, and targeted test evidence. This prevents features added during this migration from bypassing analytics; phase 4 strengthens the checks with writer/reader/consumer static and functional coverage.
- [ ] Create `docs/analytics/FEATURE_ANALYTICS_COVERAGE.yaml` as a concise source-of-truth **feature → event → recorder → persisted table → aggregator → Admin consumer → tests** registry. Include owner, platform, supported flow, grain, event version, source/attempt IDs, authoritative result, status (`covered` / `partial` / `not_instrumented` / `not_applicable`), reason and last verified commit.
- [ ] Define a short **Analytics Impact** section in the repository PR template / change checklist: relevant feature? existing event reused? new/changed event? corresponding reader/UI? tests? safe fallback? If not applicable, give a concrete explanation. Do not require event creation for pure CSS/copy/refactor with unchanged behavior.
- [ ] Codex must inspect the current writer/transport/model/reader/consumer chain **before** implementing a behavior change; update the registry, instrumentation, projections, docs and focused tests **in the same task**. If a required dimension cannot be trusted, explicitly label its metric unavailable and record the limitation; never silently omit, guess or report zero.
- [ ] A feature task is not complete merely because API/UI works. It needs **analytics impact evidence**, or a verified no-impact justification, in the final implementation summary. This is an ongoing cross-session rule, including after this plan is archived.

## Phase 1 — baseline inventory, business questions and data contracts

- [ ] Inventory actual writers/consumers across Telegram bot, Mini App, PWA, Android, desktop, backend, public site and Admin PWA. For each critical journey trace: user action → authenticated endpoint → durable record → canonical owner → query → displayed metric.
- [ ] Catalog existing events and missing critical transitions. Avoid duplicate sources and do not create an event just because it is absent from one reader.
- [ ] Specify actionable questions and precise metric contracts: registered→first meaningful lesson; D1/D7/D30 product return vs learning return; lesson start→completion; limit/paywall→plan→invoice→verified Pro; first/renewal/refund; channel acquisition→verified buyer when supported; UX errors. Every metric defines unit/grain, denominator, eligibility, cohort start, timezone, late-data maturity, window, platform, source, attribution limits and availability semantics.
- [ ] Compare legacy Admin PWA, bot reports and Analytics V10 definitions. Establish source-of-truth precedence and known differences; do not force unequal metrics to have the same label.
- [ ] Establish a fixture-backed baseline and SQL queries for key numbers before changing them. Production datasets/access must be explicitly authorized; repository inspection alone cannot prove live counts.

## Phase 2 — repair the existing measurement chain (priority order)

- [ ] **P0 PWA Pro:** connect `pwa_pro_*` stages, `attempt_id`, canonical user ID and the real Lava invoice/payment lifecycle in a new attempt-based projection. Distinguish client impressions, successful server checkout creation, payment-authoritative success, manual receipt stages, failures, cancellations, retries and refunds. Denominators must use the same eligible attempt cohorts.
- [ ] **P0 PWA/platform:** verify PWA foreground/open and meaningful activity proof. Enable metrics only for actually observed cohorts, not generic Telegram events. Keep separate PWA/Mini App/native instrumentation coverage.
- [ ] **P0 retention:** retain labeled Mini App-open retention for historical continuity; separately derive cross-platform D1/D7/D30 return/learning activity from verified events across platforms. Exclude passive notifications, admin payment actions, background jobs and non-user opens; handle maturity/identity dedupe and partial coverage.
- [ ] **P1 onboarding/course:** reconcile onboarding → first lesson → finish → next lesson across existing lesson variants and native/PWA clients. Report incomplete/unknown stages explicitly.
- [ ] **P1 marketing/source:** preserve existing aggregate visit counts; where feasible, add consent-appropriate first-party campaign/landing attribution tied to a verified account, with bounded identifiers and a defined lookback. Otherwise report descriptive traffic and `attribution_unavailable`, never causal ROI.
- [ ] **P1 errors/performance:** link existing safe client/API failure signals to platform/version/flow and release. Use bounded aggregated rates, not raw content or invasive session capture.
- [ ] Keep business-critical writes outside telemetry failure paths. Do not introduce synchronous analytics queries into checkout, course progress or lesson rendering. Design replay/reconciliation where practical, without unbounded buffers or sensitive payloads.

## Phase 3 — trustworthy projections, availability and diagnostics

- [ ] Reuse existing PostgreSQL, `pwa_analytics*.py`, Admin PWA and Redis/R2 bounded daily snapshots. Prefer indexed grouped SQL and small pre-aggregates only when measured need is demonstrated.
- [ ] Expose `supported/source/grain/window/coverage/generated_at/last_event_at/partial_reason` alongside critical metrics, with `null + reason` for untrustworthy measurements; missing rows are not automatically user drop-off.
- [ ] Add a private data-health view: accepted/rejected/duplicate event counts by platform and day, latest event and ingest timestamp, unresolved ownership, missing attempt matches, transition contradictions, and sentinel-limit cases. Avoid raw events, PII or cross-tenant exports in Admin PWA.
- [ ] Ensure server-confirmed payments reconcile to invoice ledger, never browser-return or UI-success claims; keep currencies and approximate USD/AI costs visibly distinct. Verify historic comparability before relabeling or backfilling.
- [ ] Preserve privacy, auth/revocation checks, disabled rollout defaults, no-store, bounded memory/query time, and data deletion/retention policy. Recheck existing read-only DB transaction and cache isolation tests.

## Phase 4 — ongoing automated prevention

- [ ] Add `scripts/check_analytics_coverage.py` and `tests/test_analytics_coverage_contract.py` (names provisional): verify registry schema, known event names, required writers/readers/consumers, supported platform mappings, nonempty acceptance test IDs and no undocumented additions to event enums or business-flow routes.
- [ ] Integrate as a focused `analytics-integrity` GitHub Actions check. For changed business behavior in API/services/course/checkout/auth/Android/desktop/PWA, fail if neither registry/metrics/tests nor a reviewable `analytics_not_applicable` justification is supplied. Use a scoped allowlist and risk-based change detection; pure text/CSS must not create false-positive work.
- [ ] Add SQL fixture and end-to-end regression checks proving recorded event → correct canonical account → durable table → correct Admin projection/visible label. Test every important new feature path, retries, failed analytics delivery, double events, mixed Telegram/native ownership, refunds, expired payment, absent instrumentation and partial/over-limit datasets.
- [ ] Add reconciliation checks for server payment outcomes vs funnel completions, canonical account dedupe and freshness. Alerts must use justified thresholds and a rollback/quiet mechanism; do not create false claims of zero loss.
- [ ] Automated static checks cannot prove that every user interaction was instrumented. Require code review + representative user-journey tests for critical changes; use a documented, reviewable exemption mechanism rather than bypassing CI.

## Phase 5 — validation and rollout

- [ ] Verify representative PostgreSQL fixture SQL, focused unit/integration tests, Admin PWA consumer checks and CI. Add targeted browser/Android/Telegram/device evidence for changed surfaces; do not call skipped physical/provider tests passed.
- [ ] Compare before/after metrics on identical mature cohorts and source windows. Explain discontinuities from new instrumentation, release-date changes, retries and historical limits; do not silently rewrite old results.
- [ ] Gate new views behind existing rollout boundaries if required; publish with a documented rollback for only the analytics reader/UI. Never disable actual Pro verification, user access, course grading or production payments.
- [ ] Final evidence must include: measured questions answerable, source code paths, event/consumer coverage, known unavailable metrics, test commands/results, CI status, migration/flag implications and `main` commit after validated promotion.

## Mandatory per-feature completion contract (use forever)

When Codex adds or modifies a **user-observable behavior** (onboarding, course, quiz, voice, AI, limit, payment, Pro, promotion, referral, account, notification, navigation affecting a funnel, error handling or platform delivery):

1. Inspect existing analytics event definitions and real code paths; avoid inventing data or redundant event names.
2. Explicitly choose: **reuse an existing verified event**, **implement new/versioned measurement**, **mark partially/unavailable with reason**, or **prove no analytics impact**.
3. For measured paths implement and verify the **entire chain**: event trigger + trusted identity/attempt IDs + safe persistence/dedupe + Admin aggregation/segment/filter + accurate labels/availability + regression tests + registry update.
4. Preserve the original authority for entitlement, payment, learning results and security. Telemetry must not block user flows or leak personal/payment content.
5. Update impacted dashboards/reports/docs in the same change; confirm actual selected platform and time-period behavior, not merely existence of an event enum.
6. Include an **Analytics Impact** subsection in the PR/final task result: questions answered, affected events/readers, test evidence, limitations/exemptions. Do not declare an integrated feature complete without this evidence.

**Done means**: critical journeys are source-to-dashboard traceable; newly supported metrics are reconciled against their authoritative records; unsupported metrics say why; regressions and registry drift are caught by scoped CI and functional tests; future coding agents automatically encounter the enduring instruction in root `AGENTS.md`. A plan checklist alone is not a safeguard.
