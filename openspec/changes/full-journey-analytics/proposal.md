# Proposal — phased HSK AI analytics exports

## Why

HSK AI's Admin PWA already computes 9 analytics sections, with a separately cached feedback aggregate. The read-only R2 inventory on 2026-10-30 (GitHub Actions run 41031747420) **confirmed 22 aggregate objects**: 12 then-fresh and 10 expired. They include actual R2 objects for overview, home, course, funnel, money, sources, platform, experiments, report, basic statistics and feedback. Most of the desired aggregate data already reaches R2 on demand. Meanwhile the public `HSK-AI-Private-Analytics` mirror reads **only three overview objects**, exports exactly 16 allowlisted counters and splits them into apparent `overview/users/sales/payments/courses` sections. Those are slices of the same overview source, not independent section exports.

The owner has explicitly narrowed the immediate objective: **complete the safe R2 → GitHub → ChatGPT aggregate bridge now; postpone new user journey instrumentation and Smart Reminder integration until the latter is complete.**

Related GitHub Issue: [#251](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/issues/251). This is a **planning-only** change.

## Final Product Goal — weekly improvement decisions

**The R2 → GitHub → ChatGPT bridge is a means, not the outcome.** Its final purpose is to give the existing weekly **HSK AI product-improvement agent** sufficiently accurate, source-audited data to **proactively identify where learners get stuck, drop out of lessons, fail to reach a successful checkout, or do not return**, then read the matching **current real application code and tests** to distinguish a confirmed bug, a UX/product weakness, an instrumentation gap and an unproven hypothesis. The agent should present **1–3 prioritized improvements** with one **implementation-ready first action**, not a weekly list of changed numbers.

A successful weekly recommendation must connect: **observed metric or explicit missing evidence → cohort/window/denominator and reliability → current GitHub `main` code path and relevant tests → a concrete user-visible improvement → smallest safe implementation plan → regression tests, risk, rollback and a measurable success/guardrail KPI**. Recommendations are hypotheses unless implementation, testing and measurement establish actual benefit; correlation is not proof of causation.

**Phase 1's acceptance includes a read-only agent-consumer smoke test** using the verified published aggregate index and GitHub source code to produce at least one *grounded* prioritized improvement brief when source data supports it; when the evidence is insufficient, the correct output is an explicitly marked measurement gap and the minimal instrumentation/quality step, not a fabricated drop-off or bug. The weekly automation already exists and is separately configured; Phase 1 does not automatically rewrite it or authorize autonomous edits, PRs, notifications, deployments or Smart Reminder changes.

## What Changes — Phase 1 (NOW)

1. **Allowlist currently implemented, source-validated R2 aggregate sections**, respecting their different generated times, expiry, allowed variants, real calculation grain, source coverage and privacy constraints. Enumerate available keys from the current cache contract rather than guessing keys from the GitHub overview namespace. Missing/expired objects are NOT treated as zero or fresh.
2. **Extend the existing strict R2→GitHub mirror** (cross-repo `scripts/sync_from_r2.py`, `scripts/build_archive.py`, workflow staging paths, schema tests, indexes) to publish independently derived sanitized aggregate datasets for the eligible sections, not just 16 overview counters. Preserve original 16 counters and their compatibility paths.
3. **Provide a bounded, owner-authorized cache warming/refresh mechanism** only for the approved aggregate sections and periods, so the publication does not depend on the owner opening each Admin PWA tab. Reuse existing section projections, private R2 store and lease/advisory-lock policy; scheduled six-hour GitHub sync remains R2-only and must not launch SQL. Implement batching/timeouts and partial/unavailable statuses rather than pretending every section/period is instantly available.
4. **Test source-to-GitHub fidelity and privacy**, stale/missing/partial coverage, timing, forbidden fields, small-cell re-identification, index/archive immutability, and a staged end-to-end refresh. Do not alter business functions.

## Phase 2 (DEFERRED; separate explicit authorization)

- Per-user account journey history, new client telemetry for plan selection, screen active duration, notification open/display and detailed payment-attempt lineage.
- Smart Reminder event and outcome integration after its own implementation, deployment and source maturity; only future compatibility is noted now.
- Any new database models, migrations, entitlement/payment changes or autonomous AI analytics action.

Phase 2 is **not part of Phase 1 acceptance**; the existing full-journey capability specs remain future requirements, not authorization to implement them now.

## Current Source / Limitations

- Admin PWA source reader: `app/admin_api/pwa_analytics_cache.py` — `home/overview/course/platform/funnel/money/sources/report/experiments`, each with a `cache_scope`, R2 namespace and lazy 24h cache.
- Dedicated feedback aggregates: `app/admin_api/pwa_feedback_cache.py` (`kind=feedback`, source `all/bot/release/android`, only weekly/monthly); reads at most 500 recent records per source and reports truncation.
- Other analytics sections may be missing/expired, because their cache is generated only on demand; some detail calculations refuse incomplete streams above 5,000 rows; `all_time` can use recent 30d details; platform attribution may be unavailable.
- Private R2 key contract: `app/admin_api/pwa_r2_aggregate_store.py` — `admin-pwa/aggregates/v1/{namespace}/{statistics|feedback}/{variant}.json`; maximum 128 KiB per object. A source namespace MUST be verified, not inferred from the historical `overview` value.
- Public mirror today: `HSK-AI-Private-Analytics/scripts/sync_from_r2.py::sync_overview`, `OVERVIEW_PATHS` (16 counts); `scripts/build_archive.py` only slices the overview aggregate. GitHub workflow mirror runs every 6h and owner-only manual refresh explicitly refreshes overview only.
- Both GitHub repositories are currently public. No user identifiers, receipts, user-level journeys, raw feedback, device identifiers, private error details, tokens, PII or unsafe tiny slices may be exported.

## Impact and Safety

Phase 1 modifies only **aggregate publication and necessary bounded refresh integration**. It MUST reuse the existing projections and storage, and keep native clients, Smart Reminder, checkout decision logic, financial records, access rights, notifications and Admin PWA UX unchanged. The export must be fail-closed on unsafe/unknown source content.

Work must be staged in separate feature branches for the HSK AI server and analytics archive, tested independently, and merged/deployed only after review and actual test evidence. No runtime code or configuration was changed by writing this proposal.
