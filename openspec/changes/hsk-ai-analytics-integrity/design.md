# Design

## Context

See `proposal.md` for the motivation and `specs/` for the requirements. These code facts were re-verified on `main` at `680761f1` (2026-11-12). The full writer → reader audit, with code and test citations, is the audit table in `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`, which is also the only place for session state and handoff. Row IDs (A1–A20, F1–F8) refer to that table.

- **Admin read path.** `app/admin_api/pwa_analytics_cache.py::section_projection` builds each section. `AdminPwaStatisticsReader` caches it for 24 hours per `cache_scope='analytics_<section>_v1'`. It has two early returns:
  - Any non-overall filter returns `attribution_not_audited` for every section except `platform/report/home/overview`.
  - For those four remaining sections, `iphone_pwa` returns `not_instrumented`.
- **Request filter.** `StatisticsRequest.platform` accepts `overall, telegram, android, macos, windows, iphone_pwa`.
- **Owner resolution.** `owner()` / `analytics_user_join` already resolve the canonical `users.id` first and fall back to a positive Telegram ID.
- **Detail bounds.** `bounded_rows()` returns `None` above 5,000 rows, and readers then expose `detail_limited`.
- **Trustworthy platform signals today.**
  - Android: `android_*` lifecycle events (A1); `lesson_completed` and foundation with source `android_course` (A8, A10); checkout source `android_*` and attempt prefix `android-` (F2); `payments.source` `android` (F4); Sources `android_*` (F6).
  - Telegram: `user_client_presence` surface `telegram_miniapp` (A2); `payments.source` `miniapp` / `telegram_bot` (F4).
  - PWA: `miniapp_opened` with source `pwa_course_v3` from `/api/v3/pwa/map` (A4); `/api/v3/pwa/event` rows with a server-set `transport: iphone_pwa` (A11); checkout payload transport (F1); `payments.source` `iphone_pwa` and Lava `pwa` (F4, F5).
- **Missing platform signals.**
  - Shared writers record no platform:
    - `lesson_started` (A6);
    - `lesson_completed` from the Mini App and the PWA, with hard-coded `course_v3` (A9);
    - practice, HSK exam and mistake review on all three platforms (A13–A15).
  - Android records no lesson start (A7).
  - The Telegram routes take `source` and payload from the client, so a Telegram client can write PWA-looking rows (A3, A12).
  - Voice sessions, AI usage, chat and PWA/Telegram subscription entries have no platform field (A16, A17, F7).
  - Android rows carry no Play/Direct channel (A19).
- **Reader names with no writer.** `android_lesson_started/completed` and `android_practice_started/completed` are read by `pwa_metrics.COURSE_EVENTS` and the learning features, but nothing writes them. Android learning is recorded under generic names with `android_*` sources.
- **Retention.** `retention()` covers D1/D7 only, counting `miniapp_opened`. Both the Mini App and the PWA write that event (A3, A4), so the series is a course-open series, not a Mini App-only series.
- **Existing handoff consumer.** `pwa_handoff_*` and `android_play_opened` are already read by the basic Statistics reader (`pwa_read.py`, `android_analytics_service.py`) (A18).
- **Event stores.**
  - `course_miniapp_events` has no DB check on `event_name`, and `payload_json` is free JSON.
  - `conversion_funnel_events` has a DB `CHECK`, so a new name needs a migration.
- **PWA Pro writers.**
  - The inline-event endpoint stores client `pwa_pro_*` rows, deduplicated by `event_id`.
  - `lava_checkout._start` records `pwa_pro_checkout_started` after a real invoice exists.
  - `lava/ledger.py` records `pwa_pro_checkout_paid` with `payment_id` inside the verified-grant transaction.
  - `lava_invoices` keeps `pwa_inline_attempt_id` and its status (`refunded`, `chargeback_*`).
  - No Admin reader consumes any of them (F8).
- **Scope rules on `main`.** macOS/Windows Desktop is under a development freeze. Monitoring (`docs/monitoring/REQUIREMENTS.md`) follows this work and must reuse its registry identifiers. The PWA performance contract applies to every new read and write.
- **Repo tooling.** PyYAML is not installed. Async tests use `unittest.IsolatedAsyncioTestCase`. `backend-ci.yml` runs a path-scoped test subset. Local agents often push straight to `main`, so the CI guard cannot rely on a PR body.

## Goals / Non-Goals

**Goals:**
- Connect the existing Android, Mini App and PWA analytics to their V10 sections and filters, with honest states, canonical deduplication and chain-test proof.
- Keep future features covered through the registry, the CI check and the `AGENTS.md` rule.

**Non-Goals:**
- A new analytics system or store. PostHog, a new Redis use or new infrastructure.
- Schema changes. In particular, no platform column for voice sessions, AI usage or subscription entries.
- Desktop work of any kind: no desktop code, tests or CI. Desktop gets registry statuses only.
- Monitoring itself, client telemetry retry, campaign attribution and error/performance analytics.
- Payment, entitlement or grading changes.
- Calling an unverified issue a defect.

## Decisions

### D1. One JSON registry and one stdlib checker
`docs/analytics/FEATURE_ANALYTICS_COVERAGE.json` holds four lists:
- `metrics[]`: section, key and the filters whose projection emits it. Metric entries have per-platform `{status, reason, chain_test}`; projection metadata has key coverage only. API key presence is separate from metric attribution;
- `flows[]`: the critical flows and their events. Event identities are (store, name); the registry distinguishes declarations, internal writes and known names with no writer;
- `critical_paths[]`;
- `exemptions[]`.

`scripts/check_analytics_coverage.py` uses only stdlib. It runs four checks:
1. Schema validation.
2. `ast` extraction of `CONVERSION_FUNNEL_EVENT_NAMES`, the course event tuples and `PwaProUiEvent.event`, to find unregistered and stale events. Reader-only names with no writer are recorded as `no_writer` and are not counted as covered.
3. Diff detection for `push` (`before..sha`) and `pull_request` (`base...head`).
4. Exemption validation.

A contract test projects every section × platform × period on the fixture DB and compares the returned metric keys and states with `metrics[]`. Static parsing cannot see projection output, which is why this test exists.

**Identifiers.** Platform keys (`android`, `telegram`, `iphone_pwa`, `macos`, `windows`) and flow IDs are stable. Monitoring will reference them from its own registry section instead of copying them.

**Why JSON.** YAML would add a new dependency, and the repo already keeps JSON registries such as `localization/surface_registry.json`.

### D2. Metric state per metric, applied in the existing projections
- Each metric gains `{state, reason}`. Existing value keys stay unchanged.
- The two section-wide early returns become a per-metric map driven by registry statuses, so a section can mix available and unavailable metrics.
- Reasons are used as follows:
  - `not_instrumented`: the audit found no platform signal (the `gap` rows).
  - `attribution_not_audited`: a family is not yet audited or not yet tested.
  - `not_applicable`: company-wide values such as the ledger, marketing and traffic, and desktop inventory outside desktop.
- Changed sections move to `cache_scope` `_v2`, so `_v1` snapshots are never served with new semantics.
- Auth, revocation, no-store and deadlines are reused unchanged.

### D3. Platform attribution: verified signals, plus one server-set key on existing writes
**Predicates.** They apply only to the audit's `verified` rows, and to the rows fixed below once each has its test:
- Android: an `android_*` source or event prefix, an `android-` attempt prefix, and `payments.source='android'`.
- PWA:
  - source `pwa_course_v3` or server-set `transport='iphone_pwa'`;
  - `payments.source` in `iphone_pwa` or `pwa`;
  - `lava_invoices.source='pwa'`.
- Telegram:
  - presence surface `telegram_miniapp`;
  - `payments.source` in `miniapp` or `telegram_bot`;
  - Lava `miniapp`;
  - `client='telegram'`.

**Shared writers.** The lesson start/complete, practice, exam and mistake-review writes (A6, A9, A13–A15) get one `client` payload key: `telegram`, `iphone_pwa` or `android`.
- The route sets it and passes it into the existing service call. No parallel event and no migration.
- Rows written before the key exists stay in Overall only. Their per-platform values report `attributed_since`, the earliest row with the key, so a partial window is never shown as complete.

**Spoofing guard.** The Telegram routes (`/api/miniapp/event`, map `source`) stop storing a client-supplied `transport`, `client` or `pwa_course_v3` source. This must land before PWA predicates rely on A4 or A11. The fix cannot retroactively authenticate old rows. Require route-owned evidence (such as the PWA map's fixed dedupe prefix) or a proven post-guard boundary, and test historical lookalikes; do not trust source or transport alone.

**Overall.** `count(distinct users.id)` over the union of qualifying rows, using the existing `owner()` resolution. Per-platform views apply the platform predicate before counting.

**PWA foreground proof.** Decided: reuse A4 (`miniapp_opened`, source `pwa_course_v3`). No `pwa_active_day` event. The PWA sign-in device (A5) is not used as activity.

**Android Play/Direct.** Decided: the channel is not recorded (A19), so only the combined Android value is shown.

**Android lesson start.** It is `not_instrumented` (A7). Adding a writer is out of scope unless the owner asks.

**No platform field.** AI usage, chat, voice minutes (A16, A17) and PWA/Telegram Sources entries (F7) stay `not_instrumented` per platform.

### D4. PWA Pro funnel over existing rows
A new reader (provisional `app/admin_api/pwa_analytics_pwa_pro.py`) returns `pwa_pro_attempt_funnel` in the `funnel` section, beside the unchanged legacy `attempt_funnel`.
- **Attempt key:** `(users.id, attempt_id)`.
- **Steps:** opened → plan selected → checkout started (server invoice) → paid (`pwa_pro_checkout_paid` joined to an approved `payments` row).
- **Reversal:** `lava_invoices.status` of `refunded` or `chargeback_lost`.
- **Cohort and outliers:** the cohort is attempts whose first stage falls in the window. Approved payments with no matching attempt are reported as `unlinked`.
- **Bounds:** uses the existing `bounded_rows` sentinel. Above the cap the result is `detail_limited`. An indexed column needs a separately reviewed migration backed by query-plan evidence.

### D5. Retention: relabel the existing series, add one cross-platform series
- `retention` keeps its values and gains the label `course_open`. Its basis is `miniapp_opened` from the Mini App and the PWA.
- `return_retention` (D1/D7) applies the same window and cohort to an explicit allowlist of verified activity events:
  - opens: `miniapp_opened` (Mini App and PWA), `android_app_opened`, `desktop_app_opened`, `desktop_active_day`;
  - learning: verified lesson, test, practice and mistake-review activity. Voice V8 auto-starts and can end with zero turns. Include Voice only with server-confirmed positive turns; bare Voice start/end rows and feedback delivery reservations are not return evidence.
- Implemented as one grouped `EXISTS` per window, with no row cap. Passive and server-derived rows are excluded because they are not on the allowlist.
- `return_retention` is an Overall series. Per-platform views take only the open events that carry a verified platform signal.

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
- Extend the existing Report quality list with `latest_at` and an unresolved-owner count per platform source. It uses the D3 predicates in grouped SQL over current tables. Legacy raw learning totals still include internal feedback reservations; the new per-platform freshness excludes them.
- No intake counters and no new store.

## Risks / Trade-offs

- [Guard false positives] → Narrow `critical_paths`, `ast`-based detection, a copy/CSS/i18n allowlist and actionable messages.
- [Blanket exemptions] → Exact paths or events plus a non-empty reason. Directory-wide exemptions fail.
- [Weak platform signals guessed as attribution] → Only `verified` rows enable scoping. Everything else stays unavailable with its reason.
- [Pre-rollout rows have no `client` key] → `attributed_since` on per-platform values. Overall is unaffected.
- [Telegram client writes PWA-looking rows] → The spoofing guard lands before any PWA predicate depends on A4 or A11.
- [Relabeling looks like a data change] → Legacy values and keys stay. New series use new keys.
- [Payload `LIKE` scans grow with volume] → The `detail_limited` sentinel is preferred over a wrong number. Indexing needs evidence.
- [Chain tests are slow or flaky] → Seed once per suite, test one representative value per entry, and compare with the baseline.
- [Learner-path latency] → Writers only add a key to an existing best-effort write. Readers stay in the 24-hour snapshot.

## Migration Plan

1. **Order:**
   1. Regression fixture. The audit is already done.
   2. Registry, checker and CI, with the `AGENTS.md` status update. Monitoring may start after this step.
   3. States and platform scoping: the spoofing guard first, then the `client` key, then the predicates.
   4. PWA Pro funnel.
   5. Retention and Report freshness.
   6. Integration validation, then the joint Analytics/Monitoring audit as `docs/monitoring/REQUIREMENTS.md` §11 requires.
2. **Schema:** none planned.
3. **Rollback:** each step reverts on its own.
   - Projections fall back to the `_v1` scopes.
   - The `client` key is additive, and readers ignore its absence.
   - The UI labels and the CI workflow can each be reverted alone.
   - None of them touch payments, access or grading.
4. **Promotion:** follow the `AGENTS.md` Git rules with owner approval. CI results are recorded separately from real-device acceptance.
