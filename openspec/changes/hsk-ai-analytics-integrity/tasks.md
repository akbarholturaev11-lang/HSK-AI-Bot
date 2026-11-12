# Tasks

This is the only checklist for this work. Context, audit results, decisions and the next step live only in `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`. Update that file at the end of every session. A checked box is not proof of passing tests, promotion or production acceptance. Audit row IDs (A1–A20, F1–F8) refer to the audit table in that file.

**Test conventions:**
- Run Python tests with `.venv/bin/python`, and write async tests as `unittest.IsolatedAsyncioTestCase`.
- Run PostgreSQL chain tests over local TCP Postgres, with a fresh database per module.
- Compare Playwright runs with a pre-change baseline worktree, and report skipped runs as skipped.

**Scope reminders:**
- macOS/Windows Desktop is frozen: registry statuses only, and no desktop code, tests or CI.
- Monitoring starts after group 2 and reuses the registry identifiers.

## 1. Audit and baseline

- [x] 1.1 Revalidated on `origin/main` `680761f1` (2026-11-12; delta from `334368cc`).
  - Traced writer → table → platform signal → reader → section for Android, the Mini App, the PWA and desktop: rows A1–A20 and F1–F8, marked `verified`, `to_verify` or `gap` with code and test citations.
  - Confirmed unchanged V10 keys and updated the audit for Android Li guest, Voice V8, feedback reservations and PWA push.
  - Decided D3: PWA foreground proof = existing `miniapp_opened` with source `pwa_course_v3`; Android shows combined values only, with no Play/Direct split.
  - Evidence: the audit section and the decisions log of the context file.
- [x] 1.2 Add the V10 regression fixture and `tests/test_admin_pwa_v10_regression.py`. Verified 162 section × filter × period outputs over fresh TCP PostgreSQL on unchanged `main` `680761f1` and on the merged planning branch (15 tests passed, no skips; see shared context).

## 2. Coverage guard (before any metric repair)

- [x] 2.1 Create `docs/analytics/FEATURE_ANALYTICS_COVERAGE.json` (design D1) from the 1.1 key list and audit rows.
  - Use honest statuses and reasons.
  - Reader names with no writer are `no_writer`.
  - Desktop entries reflect existing code only.
  - Platform keys and flow IDs are stable.

  Verified: `scripts/check_analytics_coverage.py --schema-only` passed and declared keys matched all 144 non-experiment baseline responses.
- [x] 2.2 Implement `scripts/check_analytics_coverage.py` (stdlib only) and `tests/test_analytics_coverage_contract.py`. Verified all cases below with 11 tests and 165 subtests over the baseline and real PostgreSQL projection contract:
  - an unmapped new event fails, naming the file and event
  - a stale entry fails
  - a copy/CSS/i18n-only change passes
  - an empty-reason exemption fails
  - a directory-wide exemption fails
  - a `covered` entry without an existing chain test fails
  - the projection-key-versus-registry contract catches a missing metric
- [x] 2.3 Add push and pull-request CI and link the registry/check from `AGENTS.md`. A cosmetic scratch push passed, and an unmapped event failed with the file and event named. Run links and the 65-test local PostgreSQL result are in the shared context.

## 3. Metric states and platform scoping

- [x] 3.1 Add per-metric `{state, reason}` and move the eight changed V10 sections to `_v2` cache scopes. Registry-driven states are available even when the legacy section payload is empty. Analytics, PostgreSQL and Redis/manual refresh tests verified that:
  - an unavailable metric is never zero;
  - `not_applicable` and unavailable stay distinct;
  - the `gap` rows report `not_instrumented`;
  - the 1.2 fixture is unchanged.
- [x] 3.2 Platform attribution (design D3), in this order:
  1. **Spoofing guard (verified):** the Telegram `/api/miniapp/event` and map routes stop storing a client-supplied `transport`, `client` or `pwa_course_v3` source (A3, A12); PWA telemetry drops client claims and keeps its server-set transport.
  2. **Client key (verified):** add the server-set `client` key to the existing shared writes, passed from each route:
     - lesson start (A6) and lesson complete (A9);
     - practice (A13), HSK exam (A14) and mistake review (A15).
  3. **Predicates:** apply them across Overview, Course, Platforms (PWA card from A4), Funnel, Finance and Sources for the `verified` rows and the rows fixed by steps 1–2. Report `attributed_since` for families that have the `client` key.
     - [x] Finance (F4, F5): payment keys and Lava lifecycle per server-set source; `tests/test_admin_pwa_platform_scope.py`.
     - [x] Funnel (F1–F3): route-set `transport` on base openings (added to Telegram and Android manual writes), `attributed_since`; `tests/test_checkout_transport_marker.py`.
     - [x] Sources: stays Overall-only; F6 Android prefix is caller-forgeable on the Telegram route (registry `not_instrumented`).
     - [x] Platforms PWA card (A4): DAU/WAU/MAU from the route-owned `pwa-course-v3:` map dedupe prefix, under the PWA filter.
     - [x] Course `features` and `completed_user_lessons` (A6, A8, A9, A13–A15): final-key `client` rule and a post-guard `attributed_since` boundary.
     - [x] Course `foundation` (A10): Telegram/PWA cohort by the tagged start; Android `not_instrumented`. PWA `activation` / `direct_activation` / `sessions` (A11) `not_instrumented`. Closing checks in `CrossPlatformDedupTests`.

  Verify with mixed-platform tests (`to_verify` rows A4, F3, F4, F5 become `verified`):
  - each view counts only its own rows
  - one account on three platforms counts once overall
  - two Android devices give one account and two devices
  - pre-key rows appear only in Overall
  - a spoofed Telegram row is not PWA, including historical source/transport lookalikes
  - learner responses and latency are unchanged
- [x] 3.3 Render the states, `attributed_since` and per-platform values in `app/static/admin-pwa/app.js`. Author UZ/RU/TJ keys in the canonical localization sources and run `scripts/i18n_build_all_catalogs.py --write` and `--check`. Verify the i18n tests and a Playwright run at 390 px in each language.
- [x] 3.4 Add chain tests for one representative metric per platform: Android bearer, Mini App signed and PWA cookie + CSRF routes, through PostgreSQL and the Admin analytics API to Playwright (right tab and filter). Flip those registry entries to `covered`, and update the definitions in `docs/admin-pwa/READ_PROJECTIONS.md`. Verify that the chain tests and the checker pass.

## 4. PWA Pro funnel

- [x] 4.1 Implement `pwa_pro_attempt_funnel` (design D4) beside the unchanged legacy funnel. Verify tests for each case:
  - a verified Lava payment moves only the matching attempt to paid
  - a click, a return URL or a failed webhook is not paid
  - two invoices in one attempt give one attempt
  - a refund or lost chargeback is reversed
  - an approved payment with no matching attempt is `unlinked`
  - legacy funnel values are unchanged
  - no attempt, invoice or provider IDs appear in the output
- [x] 4.2 Render the funnel card in the Conversion tab (UZ/RU/TJ). Add a chain test: PWA inline event → Lava start → ledger paid (`tests/lava_fakes.py`) → Admin API → Playwright under the Overall and PWA filters. Flip the registry entry (F8) to `covered` and update `READ_PROJECTIONS.md`. Verify that the chain test and the checker pass.

## 5. Retention and Report freshness

- [x] 5.1 Label `retention` as `course_open` (Mini App + PWA opens) and add `return_retention` D1/D7 (design D5), with distinct UI labels. Check the query plan with `EXPLAIN ANALYZE` on local Postgres. Verify with tests and a Playwright label check:
  - one account in two apps counts once;
  - passive activity, feedback reservations and Voice auto-start/end without a confirmed turn are excluded;
  - legacy values are unchanged.
- [x] 5.2 Add per-platform `latest_at` and unresolved-owner counts to the Report section (design D7). Verify tests showing that a stale platform is visible and that no identifiers or payloads appear in the response or the page.

## 6. Integration validation

- [ ] 6.1 Run these, comparing with the baseline:
  - `openspec validate hsk-ai-analytics-integrity --strict`;
  - the analytics, Lava, PWA and coverage suites;
  - the PostgreSQL chain tests;
  - the Admin PWA Playwright suites;
  - the `backend-pwa-performance-contract` checks.

  Verify by recording commands and results in the context file.
- [ ] 6.2 Real-client acceptance, recorded separately from CI. Perform one action each on installed Android Play and Direct builds, the Telegram Mini App and an iPhone PWA home-screen install. Confirm that each appears in the right tab and filter after a refresh, and that the shared account counts once overall. Verify by recording the evidence or the reason it was not done.
- [ ] 6.3 Promote under the `AGENTS.md` Git rules after owner approval. Write the final Analytics Impact summary: covered, `not_instrumented` and `not_applicable` metrics per platform, tests, CI and known gaps. Hand the registry identifiers to the Monitoring work for the joint integration audit. Verify the `main` commit via the remote ref.

## Workflow follow-up

- Archive with `openspec archive hsk-ai-analytics-integrity` only after verified completion.
