# Proposal

## Why

Android, the Telegram Mini App and the iPhone PWA already record analytics, but Admin PWA Analytics V10 reads only part of it. As a result, some recorded behavior never reaches the right section or platform filter. Re-verified on `main` at `334368cc` (2026-11-11). The full audit is in the context file below.

- PWA Pro writes client `pwa_pro_*` stages, a server `pwa_pro_checkout_started` row and a ledger `pwa_pro_checkout_paid` row. No `app/admin_api` reader consumes any of them.
- The `iphone_pwa` filter returns `not_instrumented` for every section. Yet PWA course opens, flow telemetry, checkout and payments already carry a trustworthy PWA signal.
- Every non-overall filter returns `attribution_not_audited` for the Course, Funnel, Finance and Sources sections. Some families can be attributed today:
  - Android lesson completion;
  - Android and PWA checkout;
  - payment sources.

  Others cannot: the shared lesson, practice, exam and mistake-review writes record no platform.
- Retention measures only `miniapp_opened`, which both the Mini App and the PWA write.

Nothing yet stops a new feature from shipping without an Admin metric. This work touches several clients, payment-derived metrics and CI, so `AGENTS.md` ("Selective OpenSpec planning") calls for a spec'd delta.

Shared context, current state and handoff: `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`, the single context file for this work. Other authorities: `AGENTS.md` (permanent analytics rule), `AI_RULES.md`, `PROJECT_MEMORY.md`, `openspec/specs/admin-real-analytics` and `admin-control-center-ui`, and `openspec/changes/lava-top-pro-payments` for Lava payment authority. Where these disagree, code and tests win.

## What Changes

- **Connect existing analytics to V10:** compute each applicable metric per platform (Android Play/Direct, Mini App, PWA) in its existing V10 section, from writers whose platform attribution is verified in code.
  - Overall counts each canonical account once across platforms and devices.
  - Each metric reports `available`, `not_applicable`, unavailable with a reason, or a real zero.
- **PWA Pro funnel:** read the PWA Pro events already recorded into an attempt-based Conversion funnel, kept separate from the legacy funnel. Paid means only the server-verified Lava payment.
- **Platform signal on shared writes:** add one server-set `client` key to the existing shared lesson, practice, exam and mistake-review writes. Stop Telegram routes from storing client-supplied PWA metadata.
- **Retention:** keep the existing D1/D7 series under a course-open label (Mini App and PWA opens) and add a cross-platform D1/D7 return series from verified activity events.
- **Report:** show the latest event time per platform source, so a disconnected platform is visible.
- **Proof:** a metric counts as connected only when a chain test shows its event going through the API, PostgreSQL, the aggregation and the Admin PWA UI. A regression fixture keeps existing V10 values unchanged.
- **Future coverage:** add a JSON coverage registry (metric × platform), a stdlib checker and an `analytics-integrity` CI workflow, and update the `AGENTS.md` enforcement status. A justified `not_applicable` stays allowed.

## Capabilities

### New Capabilities
- `analytics-feature-coverage`: Keeps business-flow analytics declared and enforced. Covers the coverage registry with its platform × section matrix, chain-test evidence for `covered`, per-change Analytics Impact, the CI guard with reviewed exemptions, and the durable agent rule.

### Modified Capabilities
- `admin-real-analytics`: Adds platform-scoped section metrics, metric states, cross-platform deduplication, preservation of existing V10 metrics, the PWA Pro attempt funnel, cross-platform return and per-platform freshness.
- `admin-control-center-ui`: Adds rendering of per-platform states and distinct retention labels inside the existing seven tabs.

## Impact

- **Read side:** `app/admin_api/pwa_analytics*.py`, `pwa_metrics.py`, plus the existing readers they call. Read-only SQL over existing tables.
- **Admin UI:** `app/static/admin-pwa/app.js`, with labels from the canonical localization sources.
- **Writers:** two changes only, both to existing writes:
  - a server-set `client` payload key on the shared lesson, practice, exam and mistake-review writes;
  - the Telegram event/map routes stop storing client-supplied PWA metadata.

  No new event, no payment, entitlement or grading path change, and no extra work on the learner request path. The PWA foreground proof reuses the existing PWA course-open row.
- **Tooling:** `docs/analytics/FEATURE_ANALYTICS_COVERAGE.json`, `scripts/check_analytics_coverage.py`, `tests/test_analytics_coverage_contract.py` (names provisional), `.github/workflows/analytics-integrity.yml`.
- **Schema/infrastructure:** none. No new store, no PostHog, no new Redis use, no vendor. A migration needs separate evidence and review.
- **Out of scope:**
  - rebuilding V10;
  - any macOS/Windows Desktop work (development freeze; registry statuses only);
  - Monitoring itself, which follows this work and reuses its registry identifiers;
  - platform columns for voice, AI usage or subscription entries;
  - client telemetry retry, campaign attribution and error/performance analytics;
  - labeling unverified issues as defects.
- **Learner-visible change:** none.
- **Rollback:** each read-side step, the UI labels and the CI workflow can be reverted on their own. None of them touch payments or access.
