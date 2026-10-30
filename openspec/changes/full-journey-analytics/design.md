# Design

## Context

See `proposal.md` and Issue #251. The current Admin PWA has separately cached analytics sections via `app/admin_api/pwa_analytics_cache.py` (`home`, `overview`, `course`, `platform`, `funnel`, `money`, `sources`, `report`, `experiments`), plus guarded feedback analytics. The GitHub archive's `sync_from_r2.py::OVERVIEW_PATHS` intentionally accepts 16 scalar overview counts and `build_archive.py` slices them into five categories. The source mirror is public and does not support private account-level reads. Real producer coverage and exact deployment state must be reconfirmed before implementation.

### Existing first-party sources to preserve

| Event family | Existing code/storage | Important constraint |
| --- | --- | --- |
| Subscription source | `subscription_entry_events`, `SubscriptionEntryAnalyticsService` | nearest pre-payment entry is descriptive; not causal |
| Checkout and payment | `conversion_funnel_events`, `_payment_attempt_funnel`, `payments` | attempt IDs and payment ID/server-approved status; no receipt body export |
| Courses and retention | `course_miniapp_events`, `pwa_analytics_learning.py` | unique canonical account vs event rows; matured D1/D7 eligibility |
| Notification lifecycle | `account_notice_deliveries`, Android/Telegram delivery services and targeted campaign/outbox records | accepted is not shown/read; distinguish observed vs unknown |
| Feedback and errors | `bot_feedbacks`, `release_feedback_responses`, `admin_pwa_native_reports`, private `app_error_context` | raw text, stack, attachments and student data are never GitHub-exportable |
| Source and finance | `pwa_analytics_finance.py`, site traffic daily table, approved payments | anonymous web visits differ from users; approximated USD not financial truth |

## Goals / Non-Goals

**Goals:** source-audited event contract, reliable account and attempt lineage, minimal private drill-down for authorized admins, privacy-safe cross-section aggregates, reproducible metadata, bounded cost and safe fallback. **Non-goals:** unlimited raw-event replication to R2, marketing causality claims, changing payment/notification behavior or forcibly inferring unseen historical timestamps.

## Decisions

### 1. Preserve authoritative DB and create a minimal canonical journey contract

Reuse existing event tables/producers where they already carry reliable evidence; add a narrow versioned server-validated event envelope only for missing data. Proposed fields: `schema_version`, `event_id` (dedupe), `event_name` (allowlist), `occurred_at` (UTC event time), `received_at` (server time), `surface`, `screen_key`, `source_key`, `session_ref`, `attempt_ref`, `payment_ref`, `notification_ref`, `offer_ref`, `plan_key`, `currency_key`, `app_version`, `outcome_code`, and `coverage`. Server resolves canonical user ID through authenticated ownership; client-supplied identity must not select another user. External refs are not trusted simply because numeric fields match. Typed screen/source/outcome enums prevent arbitrary strings reaching exports.

Prefer additive columns and composite indexes on existing event models to a giant unbounded 'track everything' table; introduce a dedicated event table only where required by migration safety and lifecycle semantics. Do not add foreign keys to legacy anonymized payment records without auditing deletion policy.

**Alternatives rejected:** copying all SQL rows to R2 (privacy and duplication), client-authoritative account IDs (spoofing), replacing current progress and payment systems with analytics events (business logic regression).

### 2. Correlate checkout attempts without claiming proof of intent

Join `paywall_seen`, `checkout_opened`, `plan_selected`, `instructions_viewed`, `receipt_selected`, `receipt_submitted`, `payment_approved/rejected` with one server-correlated attempt and canonical account; retain separate attempts after retries. Plan/method, last recorded entry surface, offer id and prices are attributed as observed facts with server-current purchase data. The payment state remains server-authoritative; a client 'success' event cannot cause or prove approval. `payment_ref` joins must honor owner and review outcome.

Store `first_known_entry`, `last_known_entry_before_checkout`, `last_known_entry_before_submission` as derived links, labeled `descriptive`, including `unattributed`/missing and explicit lookup windows. The existing nearest-entry-with-no-cutoff metric must retain its historical definition unless separately versioned; also provide bounded-window results to avoid interpreting ancient source entries as current cause.

**Alternatives rejected:** silently associating an anonymous Instagram visit with a later authenticated user; assigning one payment to every preceding entry; treating correlation as A/B-tested causality.

### 3. Measure elapsed active time, not wall time guessed from one click

Instrumentation uses screen enter/foreground, visibility/background, explicit exit and bounded heartbeat/duration with server time checks, one active session per surface where evidence permits, and an inactivity cutoff. Report `measured_active_seconds`, `observed_sessions`, `capped_sessions`, `missing_duration_sessions`, `coverage`; do not invent times for old clients or partial events. Correct for device clock skew and inconsistent offline uploads. Reopen or back-navigation yields a separate interval; never count background time by default.

**Alternatives rejected:** `payment.submitted_at - checkout_opened` as full active screen time; unlimited heartbeat and DB writes.

### 4. Keep delivery and engagement stages semantically distinct

For Telegram/Android/PWA notifications, preserve the provider's existing accepted/shown/fallback semantics. Emit aggregate counts for `eligible`, `queued`, `provider_accepted`, `client_shown`, `opened`, `action_clicked`, `failed`, and `unknown` only where source evidence exists. Never count FCM acceptance as display; never count reminder open as a proven causal recovery. Instrumentation must not alter fanout, retries, user consent or scheduling.

Categorize feedback by stored, known disliked/liked codes, status and channel; for errors aggregate stable machine-readable error code, component, version, screen and coarse severity when recorded. Raw feedback, freeform text, traces and URLs remain protected and outside generic AI/MCP/GitHub, even if in logs or a private diagnostic message.

### 5. Two explicit security/retention boundaries

**Protected first party:** authenticated Admin PWA session with strict role and optional step-up appropriate to existing authorization policy, server-side account lookups, fixed time ranges, pagination, redacted/summarized timeline, per-access audit and rate limiting. Keep private attachments on existing guarded retrieval routes only. Do not expose a bulk person-level MCP/export endpoint or permit arbitrary user lists. Reuse existing account purge/anonymization invariants and define retention/expiry before enabling new event writing; never make deletion irreversible due to a history mirror. User disclosures and consent/legal review are a production gate.

**Public mirror:** only versioned, allowlisted numeric dimensions and counts, with strict enums, safe small-cell suppression (threshold chosen during privacy review), no stable per-user/device/attempt tokens, no raw text/IDs/images/stack, and no creative 'hashing' that permits linkage. Any breakdown below the minimum safe cohort is suppressed rather than zeroed. All-time totals and current-stock figures remain distinguished from rolling flows; unknown is null plus reason/coverage, not zero.

**Alternatives rejected:** turning the currently public archive private as a substitute for enforcing least privilege, putting individual journeys in namespaced R2 objects readable by the mirror, or exporting arbitrary Admin PWA response JSON.

### 6. Source-derived projections and controlled R2 mirror

Extend first-party section projection only after each data source passes source/identity/field allowlist review. New candidate section groups: `checkout`, `attribution`, `retention`, `notifications`, `feedback`, `errors`, `product_usage`, `finance` and `experiments`; no made-up data for uninstrumented surfaces. Start with the high-value checkout/source/retention groups, then notification, feedback and errors.

Each projected document specifies `dataset`, `schema_version`, `source_version`, `section`, `platform`, `period`, `window`, `since`, `generated_at`, `expires_at`, `observation_date_utc`, `source`, `coverage`, `unit`, `grain`, `denominator` and safe metrics. Preserve R2's private, namespace-scoped 24h aggregate envelope. GitHub sync must validate each strict section-specific schema and provenance, reject unapproved fields and reject inconsistent/expired source snapshots without publishing partial unsafe content. Archives are immutable per observation timestamp and period; R2 is not a transactional replacement for DB. The manifest distinguishes `fresh`, `expired`, `not_instrumented`, `partial`, `history_only`, `no_data`.

Weekly rolling 7d, monthly rolling 30d and `all_time` are separate grains; no summing overlapping snapshots. Source coverage and retention windows are explicit; some historical detail is naturally 30-day limited. `marketing` remains `not_instrumented` until authenticated, verified campaign source and lawful attribution are separately wired.

**Alternatives rejected:** loosening existing 16-count validator to pass through arbitrary JSON; treating latest historical alias as live after expiry; making every six-hour mirror job run a fresh SQL aggregate.

### 7. Guarded refresh and cost limits

Preserve the current owner-only manual refresh token/actor, serialization and safety. After source approval, extend the protected recomputation to bounded new sections with clear partial success and fail-closed publication. Keep six-hour mirror as R2-read only. Aggregate queries require indexes, query limits/timeouts, materialization where justified and measured production-like scale tests; no `SELECT *` or infinite ID joins. Where source completeness is capped, expose `partial` and actual sample/coverage rather than falsely claiming population metrics.

### 8. Smallest actionable KPI contract

Top outcomes: (1) paid conversion of a defined registration or checkout cohort, with explicit denominator and observation maturity; (2) D7 qualified learner retention; (3) verified paid revenue in native currencies plus a clearly labeled derived USD estimate. Drivers: checkout completion by step and source/offer; activation within 2 minutes and Starter/course completion; notifications opened vs delivered. Guardrails: payment/access consistency, opt-out and bug-report rates, duplicate notification rate, AI cost per verified engaged account. No targets without credible baseline and attribution audit.

## Risks / Trade-offs

- **Public leak through rare cohort combinations** → strict dimension allowlist, minimum cell suppression, privacy attack/re-identification tests, no user-level logs.
- **False completion or source attribution** → server-owned payment outcome, attempt join checks, explicit descriptive vs experimental labels.
- **Notification delivery ambiguity** → distinguish accepted/shown/opened; `unknown` states and source-specific coverage.
- **High query/cache cost** → measured bounded ranges, indexes, periods and failure-to-unavailable rather than stale guessed data.
- **Breaking legacy clients/payment** → additive instrumentation, versioned adapters, feature flags and dual-read reconciliation.
- **Privacy/retention and legal obligations** → guarded admin scope, TTL/delete paths, approval gate before enabling individual timelines.
- **Partial R2/Redis publication** → existing failure semantics, idempotent mirror and separately verified GitHub history.

## Migration Plan

1. Complete producer/consumer audit, privacy and security inventory, definitions and baseline reconciliation. No runtime edits.
2. Add server-side allowlisted contracts, deduplication and additive migration (if needed), all disabled by default. Test synthetic fixtures and deletion.
3. Instrument missed checkout stages and active-time events in one platform at a time; reconcile observable Admin PWA figures without changing business decisions.
4. Enable protected aggregate readers for checkout, sources and retention; ship internal-only account drill-down after authorization review.
5. Extend isolated R2 writer and GitHub strict validators/archives; inspect manifests and private-public separation using test aggregates, plus guarded owner refresh.
6. Add notifications, feedback, errors, product usage and finance cohorts only after source acceptance; stage, test, canary, rollback per section.
7. Promote through existing repo branch/CI policy only after necessary unit/integration/security/device acceptance. Rollback disables new emissions/projections, leaves paid access and old 16-count reports functioning, retains legally required financial records while deleting/expiring optional analytics safely.

## Open Questions

- Confirm the retention/consent policy and access roles for per-account admin timelines before production.
- Determine which client versions currently emit every proposed plan/checkout/notification stage; do not equate a planned event with a measured one.
- Confirm native device install/session ownership and late-arriving offline client event semantics by platform.
- Choose suppression threshold and permitted aggregate dimension combinations after data volume and re-identification assessment.
- Confirm whether full historical user-linked incident review is operationally necessary; prefer minimum protected metadata and links to existing inbox records.
