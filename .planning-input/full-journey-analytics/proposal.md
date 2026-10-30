# Proposal

## Why

HSK AI already records many user, course, checkout, notification, feedback and error events, and Admin PWA displays several independently computed funnels. However the R2→GitHub analytics mirror publishes only 16 overview counters; it cannot explain where learners reached checkout, which recorded entry preceded purchase, what proportion abandoned each stage, or which categories correlate with poor retention. The owner needs actionable, reproducible growth evidence without exposing individual students or weakening payment/access controls.

This plan concerns GitHub Issue [#251](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/issues/251). It is **planning only**, not a production release.

## What Changes

- Define a versioned, first-party, server-owned journey event contract that reuses existing recorded sources and instruments genuinely missing checkout/plan/screen/notification stages. Missing historical observations remain unavailable.
- Provide an authorized, privacy-restricted administrator journey drill-down with clear evidence and timestamp provenance, while keeping sensitive raw content in its existing protected system.
- Extend validated R2 aggregate snapshots and the GitHub analytics mirror beyond the legacy 16 counters with real source-derived metrics for checkout, attribution, learning, retention, notifications, feedback categories, error categories, product usage, finance and experiment diagnostics where coverage is sufficient.
- Enforce strict separation: internal identifiers/user journeys only in protected first-party infrastructure; GitHub contains safe aggregate statistics only. The analytics GitHub repository is **currently public**, despite its name.
- Preserve existing payment approval, subscription entitlement, learning grading, notification dispatch, cache semantics and manual refresh authorization. Add bounded correctness, privacy, security and failure-mode tests before rollout.

## Capabilities

### New Capabilities
- `journey-event-contract`: canonical, privacy-bounded recorded events and status/coverage semantics across existing clients and server.
- `checkout-journey-attribution`: account-scoped checkout attempts, plan/stage timing and carefully described descriptive entry-to-payment lineage.
- `engagement-and-feedback-observability`: notification lifecycle, product learning, retention, feedback and technical error category aggregates without exposing private bodies.
- `verified-analytics-export`: immutable, source-verified R2 and aggregate-only GitHub reports with freshness, lineage, coverage, safe small-cell handling and guarded refresh.

### Modified Capabilities
None; the existing feature behavior shall remain backward compatible. Work is additive and observational.

## Impact

- Backend: `app/admin_api/pwa_analytics_*.py`, `pwa_statistics_cache.py`, analytics identities and existing event models/producers; possible additive Alembic migration only after audit.
- Clients: telemetry-producing subscription/paywall paths for Telegram Mini App, Android and Desktop; public website traffic stays anonymous and is not silently equated with account visits.
- Operational/notification data: `subscription_entry_events`, `conversion_funnel_events`, `payments`, `account_notice_deliveries`, `bot_feedbacks`, `release_feedback_*`, `admin_pwa_native_reports`, course events, technical-error markers.
- Archive: `akbarholturaev11-lang/HSK-AI-Private-Analytics` `scripts/sync_from_r2.py`, `scripts/build_archive.py`, `index.json`, `data/status.json`, and owner-authorized refresh workflow, as a separate reviewed repository change.
- Risk: unauthorized personal-data disclosure, misleading attribution or denominators, duplicate/out-of-order events, time-spent mismeasurement, heavy DB scans, cache inconsistency and accidental payment side effects.

## Out of Scope

- Automatic AI-directed subscription, marketing, payments, message sending, notification scheduling or changes to current billing/entitlement decisions.
- Export of raw payment receipts, screenshots, user IDs, private feedback text, prompts, stack traces, tokens, message content or user-level timelines to public GitHub.
- Reconstructing historical events or attributing conversions where the source never recorded the relevant step.
- Switching existing R2, Redis, PostgreSQL or production deployment architecture as part of the planning task.

## Evidence and Handoff

Canonical repo rules: `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`; planning skill: `.agents/skills/hsk-ai-openspec-planning/SKILL.md`; issue: #251. Existing verified source files include `app/admin_api/pwa_analytics_cache.py`, `app/admin_api/pwa_analytics_finance.py`, `app/admin_api/pwa_analytics_learning.py`, `app/services/admin_miniapp_service.py` and the analytics mirror allowlist. Before implementation, recheck the then-current `main`, missing producer coverage, retention and current tests. No acceptance/test results are implied by this plan.
