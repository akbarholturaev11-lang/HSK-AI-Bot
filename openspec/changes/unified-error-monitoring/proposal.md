# Proposal

## Why

HSK AI learns about technical failures mostly when a learner complains. Re-audited on `origin/main` `5ea7c22f` (2026-11-13), which contains Analytics Integrity and its R1–R4:

- **Android** has no crash handler and no automatic failure intake. Only the manual bug report exists (`/api/v3/android/bug-report` → `admin_pwa_native_reports`).
- **iPhone/browser PWA** has no `window.onerror` / `unhandledrejection` capture. `/api/v3/pwa/event` rejects `app_error`. Only the manual shake report exists (`/api/v3/pwa/bug-report`, same table).
- **Telegram Mini App** sends `app_error` from onboarding only. `AppErrorContextService` stores the raw message, stack and URL in `messages`, and every row enqueues its own Admin PWA `technical` push. Identical failures are not grouped.
- **Lava payments** alert admins by Telegram only. **Live voice** failures are shown to the learner only.
- **Backend** has no 5xx or integration-failure capture beyond process logs.
- `/api/v3/clientlog` writes unauthenticated user-agent and message text to logs.

Nothing makes a new feature report its failures. `docs/monitoring/REQUIREMENTS.md` (owner, 2026-11-10) makes this P0: every new important PWA, Android and Backend feature must connect to monitoring in its own task, and CI must block a merge when it does not.

Monitoring adds a schema, authenticated intake on three clients, Admin Inbox and Push changes, and CI. `AGENTS.md` ("Selective OpenSpec planning") therefore asks for a spec'd delta. A direct task would not settle the shared contracts with Analytics.

**Authoritative sources:**
- `docs/monitoring/REQUIREMENTS.md`: goals and mandatory requirements.
- Analytics Integrity on `main`, which Monitoring follows and reuses (REQUIREMENTS §8, §11):
  - its context file `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md` ("Monitoring handoff");
  - the OpenSpec changes `hsk-ai-analytics-integrity` and `analytics-*` (R1–R4);
  - the registry `docs/analytics/FEATURE_ANALYTICS_COVERAGE.json`, `scripts/check_analytics_coverage.py` and `analytics-integrity.yml`.
- `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`.
- `docs/admin-pwa/BROWSER_UI_CONTRACT.md` and `docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md`.

Where these disagree, code and tests win.

## What Changes

- **Failure catalog and incident store.** A server-owned catalog of `feature_code` / `failure_code` / `site_code`.
  - `feature_code` reuses the Analytics flow IDs. Monitoring adds an ID only where no Analytics flow exists.
  - One additive migration adds incidents and per-event receipts.
  - The server computes the fingerprint and severity. Receipts are idempotent by `event_id`.
  - Admission is atomic across workers. Retention, account deletion and auto-reopen rules apply.
- **Authenticated intake** on the existing transports:
  - Android bearer route;
  - PWA cookie + CSRF route;
  - Mini App `app_error` via verified Telegram `initData`;
  - an in-process backend reporter for 5xx and integration failures on critical routes.

  The owner comes only from the verified session. Forbidden fields are rejected.
- **Reporters**:
  - Android (Direct + Play): crash handler, process-exit reasons, critical API failures and live-voice failures.
  - PWA: JS errors, rejections, critical API, load, save and restore failures, and live-voice failures.

  Both use a bounded, owner-bound offline queue with backoff. Neither ever blocks the learner.
- **Admin PWA:**
  - a `diagnostic` source in the existing Inbox and triage (New → Investigating → Resolved), with no new filter control, the existing "Fixed" button and an audited reopen that shows a "fixed error came back" notice;
  - bounded Apple Push through the existing outbox for new or escalated critical incidents, plus one push whenever an incident marked fixed comes back, at any severity.
- **Mini App compatibility.** The Mini App `app_error` and `clog` signals feed the same intake. The adapter is additive (owner decision 2026-11-13). The `technical` item, its per-error push, bot AI context and the other existing consumers stay unchanged.
- **P0 coverage enforcement from the first group:**
  - a `Monitoring Impact` rule in `AGENTS.md`;
  - an optional `monitoring` block in the existing registry, keyed by Analytics flow IDs and platform keys;
  - checks added to the existing `check_analytics_coverage.py` (reusing its chain-test proof, plus a runtime proof that each chain test really ran) and `analytics-integrity.yml`.

  A new learner route, Android feature package or PWA page without monitoring coverage fails CI. Legacy gaps sit in a frozen baseline that can only shrink.
- **Rollout:**
  - an intake mode `off` / `owners` / `all` that doubles as the kill switch;
  - a separate diagnostic-push switch (`MONITORING_PUSH_ENABLED`);
  - a separate Mini App adapter switch (`MONITORING_MINIAPP_ADAPTER_ENABLED`).

  All default off. Turning them off never touches payments, lessons or existing pushes. Before `all`, `/privacy` and the Play Data safety declaration disclose automatic error reports.

## Capabilities

### New Capabilities
- `error-monitoring`: Failure capture on Android, PWA, Mini App and Backend; the privacy-safe authenticated intake; deduplication into incidents; non-blocking reliability; retention; rollout and kill switch.
- `admin-diagnostic-alerts`: The diagnostic incident source in the Admin PWA Inbox, its triage, "Fixed" and reopen rules, and bounded Apple Push for critical and returning incidents.
- `monitoring-coverage`: The durable Monitoring Impact rule, the monitoring section of the shared coverage registry, and the CI merge-block for unmonitored important features.

### Modified Capabilities
None. `admin-real-analytics` keeps its requirements. Report freshness gains a `diagnostics` source, which the "Per-platform source freshness" requirement of `hsk-ai-analytics-integrity` already covers. The Analytics change `hsk-ai-analytics-integrity` is not yet archived, so its `analytics-feature-coverage` capability is not a base spec. Its identifiers are referenced, not modified.

## Impact

- **Platforms:**
  - Android Direct + Play, the iPhone/browser learner PWA and the shared FastAPI backend (V1, P0);
  - the Telegram Mini App (compatibility only);
  - the Admin PWA on iPhone and macOS (Inbox and Push).
  - **Desktop (macOS/Windows): no code, adapter, test or CI** (development freeze). The intake contract stays platform-neutral.
- **Server:**
  - one Alembic migration after head `0155`: two tables, plus `diagnostic` in three existing source CHECK constraints;
  - a monitoring service package, two intake routes, a backend reporter hook and the Mini App `app_error` adapter in `app/main.py`;
  - the Inbox projection in `app/admin_api/pwa_inbox.py` and its triage hook;
  - the push outbox and dispatcher, `app/static/admin-pwa/{app.js,sw.js}`;
  - the hourly housekeeping loop (`_desktop_auth_retention_scheduler`);
  - a `diagnostics` source in Report freshness;
  - the automatic-report sentence in `/privacy`.
- **Clients:**
  - an Android `core/diagnostics` reporter, with R8 keep rules for both flavours;
  - one shared learner JS reporter used by `course-v3.html` and the PWA pages (with the `?v=` asset version);
  - the Mini App transport through the same script.
- **Tooling:**
  - `docs/analytics/FEATURE_ANALYTICS_COVERAGE.json` gains a `monitoring` block;
  - `scripts/check_analytics_coverage.py` and `.github/workflows/analytics-integrity.yml` are extended (no new workflow);
  - `AGENTS.md` gains the Monitoring Impact rule.
- **Not changed:**
  - the manual bug reports (Android and PWA) and their Telegram delivery;
  - analytics event stores and KPI values;
  - payment, entitlement, auth, grading and lesson flows;
  - the existing payment, Android and Mini App `technical` pushes and their priority, and the Lava Telegram alerts;
  - Desktop.
- **No new infrastructure:** no Redis use, vendor SDK, Sentry/Crashlytics or new worker. PostgreSQL and the existing hourly loop and push dispatcher are reused.
- **Learner-visible change:** only the disclosure sentence in `/privacy`. Reporting is silent and best-effort.
- **Prerequisite (met):** the Analytics registry, checker, workflow and R1–R4 are on `main`. Monitoring extends them; it does not copy them.
- **Rollback:**
  - Intake mode `off` stops all writes.
  - The push switch stops diagnostic alerts only.
  - Disabling the Mini App adapter stops only incident writes. The `technical` source and its per-event push never change.
  - The migration downgrade refuses while diagnostic triage or outbox rows exist, as `0127` does.
