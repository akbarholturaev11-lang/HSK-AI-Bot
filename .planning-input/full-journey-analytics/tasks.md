# Tasks

> Planning-only change for Issue #251. All checkboxes remain unchecked until code, migration, security checks and actual tests exist. Relevant source must be reverified against current `main` before applying any task.

## 1. Verify source contracts and define metrics

- [ ] 1.1 Recheck current `main`, all relevant tests and event producers across Telegram, Mini App, Android, Desktop, website and Admin PWA, including legacy clients and feature flags.
- [ ] 1.2 Inventory each supported event with producing file, session/attempt/account identity, UTC timestamp, server trust boundary, accepted/rejected status, retention and real collection coverage; publish a measured/partial/uninstrumented matrix.
- [ ] 1.3 Reconcile V10 Admin PWA funnel, source, learning, finance and experiment definitions with existing DB/grain, including payment status, D1/D7 maturity, anomalous source entries, 30-day detail cap and present display values.
- [ ] 1.4 Audit `HSK-AI-Private-Analytics` allowlist, public visibility, source namespace, cache expiration, snapshot manifest and owner refresh; document existing 16-count limit without weakening it.
- [ ] 1.5 Define 1–3 outcome KPIs, diagnostic drivers and counter-metrics with SQL grain, denominator, source, observation maturity, timezone, coverage and reasons to withhold claims.

## 2. Privacy, authorization and migration gate

- [ ] 2.1 Document allowed / restricted / forbidden export fields per source and public small-cohort suppression/dimension allowlist; confirm current repository access and GDPR/consent/deletion requirements with owner.
- [ ] 2.2 Specify protected first-party account timeline access roles, existing session/passkey reuse, pagination, rate limits, per-access audit and raw attachment redaction. Explicitly prohibit account-level GitHub/MCP export.
- [ ] 2.3 Review existing account purge/anonymization for event and payment refs and choose retention period. If additions are unavoidable, create strictly additive, reversible Alembic migrations and indexes.
- [ ] 2.4 Test canonical owner resolution, forged client fields, cross-account payment references, orphan/legacy IDs, profile unlinking and actual deletion in isolated fixtures.

## 3. Instrument canonical journey and checkout

- [ ] 3.1 Introduce allowlisted versioned telemetry contract, idempotency keys, server resolved identity and bounded timestamp skew with safe off-by-default rollout.
- [ ] 3.2 Attach missing plan selection, instruction view, receipt selection, receipt submission and review transitions to correct checkout attempt and payment refs; retain existing billing and access state unchanged.
- [ ] 3.3 Add one platform's measured visibility/foreground/exit/heartbeat timing with cap, offline replay and background guards; leave unmeasured legacy duration unknown.
- [ ] 3.4 Extend producer adapters for remaining platforms only after platform-specific auth/version tests and duplicate/out-of-order regression.
- [ ] 3.5 Implement protected Admin PWA account timeline for available observed data with redaction, explicit lack-of-evidence states and audit logs; no user-level bulk export.

## 4. Verified aggregate projections

- [ ] 4.1 Implement controlled checkout funnel summaries by attempted/unique account grains, stage loss and approval, plus selected plan/method when verified.
- [ ] 4.2 Implement bounded descriptive source lineage and preserve anonymous public-site traffic grain; label attribution as observational.
- [ ] 4.3 Implement matured D1/D7 retention and learning activation/session evidence with source row completeness, denominator and 30-day detail limits.
- [ ] 4.4 Add notification accepted/shown/opened/actioned estimates only per instrumented channel, preserving fallback and no-send semantics.
- [ ] 4.5 Aggregate safe categorical feedback and technical errors (including known app version/screen and status) without copying free text, stack traces or receipt contents.
- [ ] 4.6 Add optional finance/product/experiment breakdowns only from reviewed first-party sources; retain unknown/unpriced/incomplete states.

## 5. R2 and GitHub archive integration

- [ ] 5.1 Define and test per-section R2 aggregate envelopes (source version, period, window, generated/expires, coverage, metric definition, strict input size, source origin) while preserving current 16-count output.
- [ ] 5.2 Extend GitHub-side `scripts/sync_from_r2.py` strict allowlists and `scripts/build_archive.py` immutable section histories/manifests without exporting private user/device/attempt IDs, raw content, rare cells or identity-linkable dimensions.
- [ ] 5.3 Expand owner-authorized manual refresh only to vetted sections; preserve token validation, serialization, idempotency, fail-closed semantics and scheduled mirror-only behavior.
- [ ] 5.4 Test expired, missing, partial, malformed, stale, out-of-order, unauthorized and duplicate snapshot handling; check no unsafe fields in commits, logs, summary or history.
- [ ] 5.5 Verify source refresh AND downstream sync separately; compare GitHub snapshots against protected aggregate queries with exact metadata and period boundaries.

## 6. Validation, rollout and handoff

- [ ] 6.1 Run focused unit/integration tests for telemetry, checkout, consent/deletion, payment approval, paid access, notification fallback and privacy boundaries; do not report unexecuted suites as passing.
- [ ] 6.2 Test realistic event volume, query costs, timeouts, 24h cache lifetime, 6h mirror and Redis/R2 partial-write behavior in staging.
- [ ] 6.3 Validate Admin PWA read-only drill-down and each client's telemetry flow with version-gated staged checks; prevent user-visible UI regressions.
- [ ] 6.4 Roll out section by section behind explicit feature flags with a documented rollback that preserves existing 16-count reports, financial records and production access decisions.
- [ ] 6.5 Run official `openspec validate` for this change, then follow `AGENTS.md` branch/CI/promotion rules; confirm any later `main` merge SHA and live data freshness separately from documentation validity.
