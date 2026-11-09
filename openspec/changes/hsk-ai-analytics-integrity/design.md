# Design

## Context

See `proposal.md` for the motivation and `specs/` for the requirements. These code facts were verified on `main` at `8ff505b3`. Re-check them at implementation start. Session state and handoff live only in `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`.

- **Admin read path.** `app/admin_api/pwa_analytics_cache.py::section_projection` builds each section. `AdminPwaStatisticsReader` caches it for 24 hours per `cache_scope='analytics_<section>_v1'`. It has two early returns:
  - `iphone_pwa` returns `not_instrumented` for every section.
  - Any other non-overall filter returns `attribution_not_audited` for every section except `platform/report/home/overview`.
- **Request filter.** `StatisticsRequest.platform` accepts `overall, telegram, android, macos, windows, iphone_pwa`.
- **Owner resolution.** `owner()` / `analytics_user_join` already resolve the canonical `users.id` first and fall back to a positive Telegram ID.
- **Detail bounds.** `bounded_rows()` returns `None` above 5,000 rows, and readers then expose `detail_limited`.
- **Platforms today.**
  - Android: `platform_metrics()` derives activity from `android_app_opened`.
  - Desktop: derived from `desktop_*` events.
  - Telegram: derived from `user_client_presence` with surface `telegram_miniapp`.
  - PWA: `iphone_pwa_available` is hard-coded `False`. PWA voice events carry payload `transport: iphone_pwa`. Other PWA activity writers are `to_verify`.
  - Android has a `play`/`direct` channel in its entitlement and request code (`app/services/entitlements/contract.py`). Whether it reaches the analytics rows is `to_verify`.
- **Event stores.**
  - `course_miniapp_events` has no DB check on `event_name`.
  - `conversion_funnel_events` has a DB `CHECK`, so a new name needs a migration.
- **PWA Pro writers.**
  - The inline-event endpoint stores client `pwa_pro_*` rows, deduplicated by `event_id`.
  - `lava_checkout._start` records `pwa_pro_checkout_started` after a real invoice exists.
  - `lava/ledger.py` records `pwa_pro_checkout_paid` with `payment_id` inside the verified-grant transaction.
  - `lava_invoices` keeps `pwa_inline_attempt_id` and its status (`refunded`, `chargeback_*`).
  - No Admin reader consumes any of them.
- **Retention.** `retention()` covers D1/D7 only, counting `miniapp_opened` in `[signup+n days, signup+n+1 days)`.
- **Repo tooling.** PyYAML is not installed. Async tests use `unittest.IsolatedAsyncioTestCase`. `backend-ci.yml` runs a path-scoped test subset. Local agents often push straight to `main`, so the CI guard cannot rely on a PR body.

## Goals / Non-Goals

**Goals:**
- Connect the existing Android, Mini App and PWA analytics to their V10 sections and filters, with honest states, canonical deduplication and chain-test proof.
- Keep future features covered through the registry, the CI check and the `AGENTS.md` rule.

**Non-Goals:**
- A new analytics system or store. PostHog, a new Redis use or new infrastructure.
- Client telemetry retry, campaign attribution or error/performance analytics.
- Payment, entitlement or grading changes.
- Calling an unverified issue a defect.

## Decisions

### D1. One JSON registry and one stdlib checker
`docs/analytics/FEATURE_ANALYTICS_COVERAGE.json` holds `metrics[]` (section, key, per-platform `{status, reason, chain_test}`), `flows[]` (critical flows and their events), `critical_paths[]` and `exemptions[]`.
- `scripts/check_analytics_coverage.py` uses only stdlib. It runs four checks:
  1. Schema validation.
  2. `ast` extraction of `CONVERSION_FUNNEL_EVENT_NAMES`, the course event tuples and `PwaProUiEvent.event`, to find unregistered and stale events.
  3. Diff detection for `push` (`before..sha`) and `pull_request` (`base...head`).
  4. Exemption validation.
- A pytest contract test projects every section × platform × period on the fixture DB and compares the returned metric keys and states with `metrics[]`. Static parsing cannot see projection output, which is why this test exists.
- Why JSON: YAML would add a new dependency, and the repo already keeps JSON registries such as `localization/surface_registry.json`.

### D2. Metric state per metric, applied in the existing projections
- Each metric gains `{state, reason}`. Existing value keys stay unchanged.
- The two section-wide early returns become a per-metric map driven by registry statuses, so a section can mix available and unavailable metrics.
- Changed sections move to `cache_scope` `_v2`, so `_v1` snapshots are never served with new semantics.
- Auth, revocation, no-store and deadlines are reused unchanged.

### D3. Platform attribution: verified event families only, by extending existing writes
- The audit builds one table: event family → writer → distinguishing field → platform, with `verified` (code and test cited) or `to_verify` per row. It is stored in the context file.
- Predicates apply only to `verified` rows.
- A verified writer that lacks a platform field gets the field on its existing write. No parallel event is added.
- **Overall:** `count(distinct users.id)` over the union of qualifying rows, using the existing `owner()` resolution. Per-platform views apply the platform predicate before counting.
- **PWA foreground proof:** reuse an existing authenticated PWA record if the audit finds one. Only otherwise, add a once-per-account-per-day `pwa_active_day` course event, which needs no migration, mirroring `desktop_active_day`.
- **Android Play/Direct:** split only if the channel is already available at an existing write. Otherwise show the combined Android value only.

### D4. PWA Pro funnel over existing rows
A new reader (provisional `app/admin_api/pwa_analytics_pwa_pro.py`) returns `pwa_pro_attempt_funnel` in the `funnel` section, beside the unchanged legacy `attempt_funnel`.
- **Attempt key:** `(users.id, attempt_id)`.
- **Steps:** opened → plan selected → checkout started (server invoice) → paid (`pwa_pro_checkout_paid` joined to an approved `payments` row).
- **Reversal:** `lava_invoices.status` of `refunded` or `chargeback_lost`.
- **Cohort and outliers:** the cohort is attempts whose first stage falls in the window. Approved payments with no matching attempt are reported as `unlinked`.
- **Bounds:** uses the existing `bounded_rows` sentinel. Above the cap the result is `detail_limited`. An indexed column needs a separately reviewed migration backed by query-plan evidence.

### D5. Retention: one new cross-platform series
- `retention` keeps its values and gains the label `miniapp_open`.
- `return_retention` (D1/D7) applies the same window and cohort to an explicit allowlist of verified activity events:
  - opens: `miniapp_opened`, `android_app_opened`, `desktop_app_opened`, `desktop_active_day`, plus the PWA proof from D3;
  - learning events: lesson, test, practice, mistake review and voice starts and completions.
- Implemented as one grouped `EXISTS` per window, with no row cap. Passive and server-derived rows are excluded because they are not on the allowlist.

### D6. Chain tests prove "connected"
- **Backend part.** Runs on local or CI PostgreSQL, using the existing TCP pattern (`tests/test_lava_postgres.py`), as `IsolatedAsyncioTestCase`. It sends a fixture action through the real platform route:
  - Android: native bearer route.
  - Mini App: signed Telegram route.
  - PWA: cookie + CSRF route.
  - Lava: ledger with `tests/lava_fakes.py`.

  It then reads the metric through the authenticated Admin analytics API.
- **UI part.** Extends the existing Admin PWA Playwright suites and asserts the value in the expected tab and filter.
- **Baseline.** Browser runs are compared with a pre-change baseline worktree, because those suites have known flaky timeouts.

### D7. Report freshness from existing rows
- Extend the existing Report quality list with `latest_at` and an unresolved-owner count per platform source, using grouped SQL over current tables.
- No intake counters and no new store.

## Risks / Trade-offs

- [Guard false positives] → Narrow `critical_paths`, `ast`-based detection, a copy/CSS/i18n allowlist and actionable messages.
- [Blanket exemptions] → Exact paths or events plus a non-empty reason. Directory-wide exemptions fail.
- [Weak platform signals guessed as attribution] → Only `verified` rows enable scoping. Everything else stays `attribution_not_audited`.
- [Relabeling looks like a data change] → Legacy values and keys stay. New series use new keys.
- [Payload `LIKE` attempt scans grow with volume] → The `detail_limited` sentinel is preferred over a wrong number. Indexing needs evidence.
- [Chain tests are slow or flaky] → Seed once per suite, test one representative value per entry, and compare with the baseline.

## Migration Plan

1. **Order:**
   1. Audit and regression fixture.
   2. Registry, checker and CI, with the `AGENTS.md` status update.
   3. States and platform scoping.
   4. PWA Pro funnel.
   5. Retention and Report freshness.
   6. Integration validation.
2. **Schema:** none planned.
3. **Rollback:** each step reverts on its own. Projections fall back to the `_v1` scopes. The UI labels, a writer field addition and the CI workflow can each be reverted alone. None of them touch payments, access or grading.
4. **Promotion:** follow the `AGENTS.md` Git rules with owner approval. CI results are recorded separately from real-device acceptance.
