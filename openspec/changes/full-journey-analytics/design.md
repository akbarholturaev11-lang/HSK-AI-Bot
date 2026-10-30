# Design — existing R2 aggregate export first

## Architectural decision

**Phase 1 is an export/refresh adapter, not a new analytics product.** Keep PostgreSQL, the source-side Admin PWA aggregate projections, lazy 24-hour Redis/R2 caching and the validated GitHub archive. Do not introduce a new event collector, new database tables, direct user-level MCP, UI screens, new notifications or Smart Reminder behavior.

Source reality (2026-10-30 `main`, read-only R2 audit run 41031747420):
- 22 R2 aggregate objects discovered, 12 fresh and 10 expired at inspection.
- Real `statistics` scope objects: `home`, `overview`, `course`, `funnel`, `money`, `sources`, `platform`, `experiments`, `report`, plus older basic statistics.
- One `feedback` scope object: `all_weekly`, expired; not proof that a current weekly or monthly response exists.
- 9-section reader `app/admin_api/pwa_analytics_cache.py`; feedback lives in `pwa_feedback_cache.py`. Sections are lazily computed and have independent internal cache namespaces.
- The GitHub archive currently reads only `R2_OVERVIEW_NAMESPACE` `statistics/overall_{weekly,monthly,all_time}.json`, whitelists 16 integers, and presents five derived folder labels. Separate folders do not prove separate data sources.

## Authoritative source map and eligibility

| Source | Existing kind and keys | Current export eligibility / caveats |
| --- | --- | --- |
| overview | `statistics`, `overall_weekly`, `overall_monthly`, `overall_all_time` | Preserve existing verified 16-counter output; optionally add independently validated extra safe dimensions, without silently changing legacy metric definitions. |
| home | `statistics`, `overall_{weekly,monthly,all_time}` | Some stock counts and calendar daily learning series have mixed grains; allow only reviewed values. |
| course | `statistics`, `overall_{weekly,monthly,all_time}` on demand | Detail may be restricted to last 30 days even for all_time, 5,000 rows cap; emit `detail_limited` and provenance, never totalize partial history. |
| funnel | `statistics`, `overall_{weekly,monthly,all_time}` on demand | Attempt/account grain distinct; missing/out-of-window rows may make funnel unavailable. |
| money | `statistics`, `overall_{weekly,monthly,all_time}` on demand | Currencies and USD estimates are not invoices; approved `HSK30_UNLOCK` excluded from some payment definitions unlike overview. |
| sources | `statistics`, `overall_{weekly,monthly,all_time}` on demand | Nearest recorded source before payment is **descriptive** (no lookback cutoff in existing projection), not causal; anonymous web visits are not accounts. |
| platform | `statistics`, various `platform_period` variants | Some counters ignore selected period or are based on current device inventory; iPhone PWA not instrumented, Telegram attribution not proved. |
| experiments | `statistics`, `overall_{weekly,monthly,all_time}` on demand | `all_time` experiment detail actually rolling 30 days, and 5,000 row cap can invalidate output; no unverified lift claims. |
| report | `statistics`, `overall_{weekly,monthly,all_time}` on demand | Source quality metadata, generated times and record counts; never export identifying records. |
| feedback | `feedback`, `{all,bot,release,android}_{weekly,monthly}` on demand | Capped newest 500 records per source; `truncated` and incomplete historic Android data must be retained. |
| basic_statistics | `statistics`, older standalone basic reader | Keep compatibility only; do not merge into renamed overview with changed metric meanings. |
| Smart Reminder | Future, currently disabled dispatch | Explicitly deferred until verifiable production events exist. |

**Important:** the table shows recognized *possible variants*, not a claim that each R2 object currently exists. The 22-object read-only inventory is evidence of partial, demand-driven materialization, not exhaustive 24/7 coverage.

## Implementation boundary and affected paths

### Server repository: `akbarholturaev11-lang/HSK-AI-Bot`

Use existing `app/admin_api/pwa_analytics_cache.py::section_projection`, `pwa_statistics_cache.py::AdminPwaStatisticsReader`, `pwa_feedback_cache.py`, `pwa_r2_aggregate_store.py` and `pwa_manual_aggregate_refresh.py`. Do not change their original metric formulas without independently reviewed bug evidence.

- Introduce a **server-owned, explicit mapping** of approved section / kind / namespace / platform / period combinations; no exposure of R2 credentials, arbitrary namespace lookup or user-provided paths. Prefer a strict manifest/snapshot from R2 which includes only safe section identifiers and freshness metadata, or narrowly scoped CI secrets if existing deployment constraints make this safer. Do not derive arbitrary private R2 paths from public client input.
- When requested by authenticated owner, compute only missing, expired or explicitly forced approved section-period projections, using the existing SQL loaders. Enforce a read-only snapshot, upper bounds on request time and workload, single refresh authority/lease, cooldown, no indefinite retries. **Do not simply expand the existing ~80s overview bundle into a single unbounded 9-section x 3-period computation**. Batch with bounded execution and truthful per-section success/failure.
- Preserve old overview endpoint response and Redis/R2 fallback semantics; existing `overview` can be verified to refresh reliably even without Redis. Do not remove existing locking, manual token check, origin check or prevention of double recomputation.
- Capture safe `generated_at`, `expires_at`, `period`, `since`, source section, unit/denominator and indicators of partial/truncated/unknown. Avoid giving feedback any `all_time` period it does not support.

### Archive repository: `akbarholturaev11-lang/HSK-AI-Private-Analytics`

- Extend `scripts/sync_from_r2.py` with **explicit per-section validators** for approved source signatures and fields. Only `source`, `scope.section`, safe enums, bounded numbers, predefined scalar/group keys and exact data windows are accepted; reject arbitrary DB JSON and new unreviewed fields. No raw R2 objects checked in or logged. R2 128 KiB input bound is retained.
- Extend `scripts/build_archive.py` to keep legacy `overview/users/sales/payments/courses` aliases while adding separate true-source datasets in **new distinct paths** (e.g., `analytics/course`, `analytics/funnel`, `analytics/money`, `analytics/sources`, etc.). Do not overwrite existing `courses` derived overview numbers as if they were independent course projections.
- Extend index/manifests and `.github/workflows/sync-r2.yml` allowed commit path set. Publish only filtered, schema-valid, privacy-safe aggregates; keep 6h mirror **read-only to R2** and avoid changing server SQL from a scheduled archive task.
- Fresh snapshots and historical immutable snapshots must be distinguishable. No claim of freshness for expired cache, no silent source mixing and no sum/difference presented as standalone daily change for overlapping rolling 7d/30d windows.

## Downstream consumer: weekly proactive improvement agent (final goal)

The existing weekly HSK AI agent is an **independent read-only consumer**, not a new analytics service and not an actuator. **The delivery is successful only if a real decision can be grounded in exported evidence and then checked against current code**.

The bridge's `index.json`, status and each individual source projection MUST make it possible to:
- Discover a real section and verified `latest`/historical path without hardcoded future sections; identify whether `courses` is a legacy overview-derived slice versus `analytics/course` from the actual course projection.
- Recover original `section`, `source`, `platform`, `period`, `since`, `generated_at`, `expires_at`, `window`, `observation_date_utc`, `coverage`, `detail_limited`/`truncated`, `unit`, `numerator/denominator` **where actually available**, and known metric definitions and missingness statuses.
- Compare like-for-like cohorts or nonoverlapping observations when present, without subtracting overlapping rolling windows as if they represented daily change or asserting causal attribution from nearest source.
- Tie potential learning drop-off, checkout abandonment, payment friction, feedback or platform usage to the *actual verified metric*; then use the GitHub connector to read the current HSK AI application `main` and the relevant real code/test paths. Aggregate files need not contain private user IDs, arbitrary source-code snippets or a redundant replica of the repo.
- Provide **1–3 concrete, ranked, minimal changes**, identify one highest-value implementation-ready brief (affected user flow, relevant files, test cases, risk, rollback, outcome KPI and guardrail), and note confirmed versus speculative diagnosis. The agent MUST NOT claim improvement just because a metric moved.

**Read-only consumer acceptance:** with synthetic fixtures and then an available real fresh snapshot, verify the agent can locate a genuine independent `funnel` / `course` / `sources` entry and trace a specific question to an actual code function/test in the separately read `HSK-AI-Bot` repository. Produce a grounded recommendation if evidence supports it, otherwise an explicit observability gap. Test the `missing`, `expired`, small-cohort and partially capped cases, so the agent never fabricates a plausible but unsupported flaw. This smoke test checks **data usability and traceability**, not proof of uplift or agent autonomy.

The agent's existing weekly automation, schedule, execution authority and actual implementation decisions are managed separately; Phase 1 does not require building a new agent or changing product behavior.

## Security and privacy invariants

Both repositories are publicly readable. The private R2 bucket stays private. Public GitHub accepts no Telegram/canonical IDs, PII, payment receipt image/media references, text feedback, stack traces, arbitrary errors, URLs or tokens, individual-level journeys, user-supplied freeform dimensions or rare identifiable cohorts. Use per-section fixed allowlists, bounded dimensions and suppression of low-count combinations where needed. Hashes are not a substitute for aggregation. Sensitive feedback and errors continue in their existing protected interfaces.

Only approved numerical/category feedback (already category-only and 500-row capped) may go to the public bridge. Do not imply sampling makes estimates population-complete.

## Truthful data and partial availability

- Each section has its own original generation timestamp and expiry. Cross-section 'all generated together' is false until a coherent batch actually proves it; per-source timestamps must remain.
- `weekly` = rolling 7d where coded, `monthly` = rolling 30d, `all_time` may contain rolling-stock/30d-detail metrics. Some platform cards are non-period-specific.
- `not_instrumented`, `missing`, `expired`, `partial`, `suppressed`, `invalid_source`, `fresh` must be handled distinctly without fabricating zeroes.
- The admin source may be refreshed while another GitHub sync is running. Mirror publishing must remain idempotent and immutable for already recorded observation timestamps.
- Report metrics sharing names can have different semantics: e.g. `overview.payments_approved` vs `money.payments` exclude different purchase categories. Keep source definitions.

## Four-step release with safe rollback

1. **Source/contract:** fix and test section mapping and privacy allowlists from the existing real cache, including 22-object audit evidence, supported periods, source status and schema limits.
2. **Refresh:** implement minimum safe owner-triggered cache warming of approved, existing projections with batching and per-section honest results. Existing overview refresh untouched by default.
3. **Bridge/archive:** implement independent validated section exports and immutable indexed history while keeping 16 legacy counters and 6-hour R2-only schedule intact.
4. **Verification/release:** run server and archive regression tests, synthetic oversized/poisoned R2 payloads, partial/stale/unknown/small-cell and source comparison cases, owner manual refresh in staging then controlled live verification, manual checks of public Git diff for leakage and CI, separate reviewed PRs and rollback.

Rollback disables new sections and reverts new mapping/warm-up while keeping the original 16-counter overview mirror, existing cached objects and payment/course functionality unchanged.

## Deferred — NOT authorized in Phase 1

Journey event instrumentation, person-level timelines, checkout active screen time, new push acknowledgement fields, additional error telemetry, Smart Reminder ML/dispatch/experiment changes, migrations and client releases. Any further work requires an explicit separate implementation decision. The pre-existing full-journey capability specs document later behavior, not current sprint scope.
