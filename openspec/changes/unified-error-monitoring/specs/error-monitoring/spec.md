# Spec Delta

## Purpose

Detects technical failures on Android, the learner PWA, the Telegram Mini App and the shared backend without waiting for a learner complaint, and groups them into privacy-safe incidents. It never blocks a learner flow.

## ADDED Requirements

### Requirement: Versioned privacy-safe failure event
A client failure event SHALL contain only versioned bounded fields: `event_id`, client time, client/platform, app/build version, `feature_code`, `failure_code`, `site_code`, outcome and a safe technical category. Codes MUST come from the server-owned catalog. The server MUST reject an event that carries a forbidden field and MUST NOT store, log, push or project any forbidden value.

#### Scenario: Forbidden field rejected
- **WHEN** an event carries a token, cookie, Telegram `initData`, password, chat or lesson answer text, payment data, screenshot, raw stack or error message, URL query, request/response body or device fingerprint
- **THEN** the whole request is rejected, and nothing from it reaches storage, logs, the Inbox, Push or analytics

#### Scenario: Unknown code rejected
- **WHEN** an event names a `feature_code`, `failure_code` or `site_code` that is not in the catalog
- **THEN** that event is rejected, and other valid events in the same batch are still accepted

#### Scenario: Oversized request rejected
- **WHEN** a request exceeds the maximum body size or the maximum events per batch
- **THEN** it is rejected without a partial write

### Requirement: Owner from the verified session only
The intake SHALL derive the account (`users.id`) only from the verified session of its transport: Android bearer, PWA cookie with CSRF and same origin, or verified Telegram `initData`. A client-supplied owner ID MUST NOT be trusted.

#### Scenario: Client sends an owner ID
- **WHEN** an event body contains `user_id` or `telegram_id`
- **THEN** the request is rejected, and no client value decides the owner

#### Scenario: Blocked or revoked account
- **WHEN** a blocked account or a revoked session sends events
- **THEN** the intake refuses them with the transport's existing auth error, and no receipt or incident is written

#### Scenario: Unauthenticated client failure
- **WHEN** a failure happens before any verified session exists
- **THEN** the client does not send it under any account. Backend-side signals of the same route still record the failure without an owner

### Requirement: Idempotent receipts and server-owned incidents
Each accepted `event_id` SHALL produce exactly one receipt, even on retry. The server SHALL compute the fingerprint from platform, `feature_code`, `failure_code` and `site_code`, and group equal fingerprints into one incident with occurrence count, first/last seen and first/last version. Severity SHALL come from the catalog and from server-observed scope only. A client-supplied fingerprint or severity MUST be rejected.

#### Scenario: Client sends a fingerprint or severity
- **WHEN** an event body contains a fingerprint or a severity
- **THEN** the request is rejected, and grouping and severity stay server-derived

#### Scenario: Retried event
- **WHEN** the same `event_id` from the same account arrives twice
- **THEN** one receipt exists and the incident's occurrence count grows by one

#### Scenario: Concurrent workers
- **WHEN** two API workers accept the first two events of a new fingerprint at the same time
- **THEN** exactly one incident exists, and its occurrence count is two

#### Scenario: Version is not part of the grouping
- **WHEN** the same failure arrives from two app versions
- **THEN** it is one incident, which records both the first and the last version seen

### Requirement: Expected outcomes are not incidents
Reporters SHALL NOT report expected outcomes as failures: a limit, a paywall, a user cancel, an ordinary 401/403/409, rate limiting or temporary offline. A recovery the client confirmed with server data MAY only lower severity, never raise it.

#### Scenario: Paywall response
- **WHEN** a lesson request returns the limit or paywall result
- **THEN** no failure event is created

#### Scenario: Offline then success
- **WHEN** a request fails because the device is offline, and a retry later succeeds
- **THEN** no incident is recorded for it

#### Scenario: Recovered save
- **WHEN** a save response is lost but the client confirms the saved state from the server
- **THEN** the event is marked recovered, and its incident is never ranked above the unrecovered variant

### Requirement: Backend failure capture
The backend SHALL record a server-side occurrence for an unhandled exception or a 5xx response on allowlisted critical routes, and for named integration failures in critical flows. It MUST NOT record a 4xx result or any request or response content.

#### Scenario: Critical route returns 5xx
- **WHEN** an allowlisted lesson, practice, progress, auth or payment route returns 5xx
- **THEN** an incident with platform `server` (or the route's client, when the route fixes it) and that route's feature code gains one occurrence, and the learner's response is unchanged

#### Scenario: Ordinary client error
- **WHEN** a route returns 401, 403, 404, 409 or 422
- **THEN** no occurrence is recorded

### Requirement: Android and PWA failure capture
Android SHALL capture uncaught exceptions, supported process-exit reasons (crash, native crash, ANR) and unexpected failures of critical API calls. The learner PWA SHALL capture uncaught errors, unhandled rejections and failures to load, save or restore in critical flows. Each report is mapped to catalog codes on the device.

#### Scenario: Android crash
- **WHEN** the Android app crashes on a lesson screen
- **THEN** a bounded local record is written without network IO, the system crash behavior is unchanged, and the record is sent on a later start

#### Scenario: Process killed for ANR
- **WHEN** Android reports an earlier ANR exit on the next start
- **THEN** it is reported once, never again on later starts

#### Scenario: PWA unhandled rejection
- **WHEN** an unhandled promise rejection happens on the PWA course page
- **THEN** one event with the page's feature code and a safe category is queued, without the error message or stack

### Requirement: Bounded owner-bound offline queue
Android and PWA reporters SHALL keep unsent events in a bounded queue with a short TTL and capped retry with backoff. Every queued event SHALL be bound to the account that produced it. Logout or an account switch MUST discard the previous owner's events.

#### Scenario: Offline then online
- **WHEN** events are queued offline and the device reconnects within the TTL
- **THEN** they are sent once, with their original `event_id`

#### Scenario: Account switch
- **WHEN** account A has queued events and the device signs in as account B
- **THEN** A's events are discarded and never sent with B's session

#### Scenario: Queue full or expired
- **WHEN** the queue is full or an event is older than the TTL
- **THEN** the oldest or expired events are dropped, and one content-free queue-dropped event is reported later in their place

### Requirement: Non-blocking reporting
Reporting SHALL never block or change login, the course, progress, payment or any learner response. A reporter MUST NOT report its own failures in a loop. A crash handler MUST NOT make a blocking network request.

#### Scenario: Intake unavailable
- **WHEN** the intake returns 5xx or times out
- **THEN** the learner flow continues unchanged, and the client retries later within its limits

#### Scenario: Reporter throws
- **WHEN** the reporter itself throws while building or sending an event
- **THEN** the error is swallowed, no new event is created for it, and the page or app keeps running

#### Scenario: Performance budget
- **WHEN** reporting is enabled
- **THEN** PWA first paint, section loading, backend learner-route latency and Android main-thread responsiveness stay within the existing performance contract

### Requirement: Atomic admission and abuse limits
The intake SHALL enforce a per-account hourly cap atomically across workers, plus maximum body size, batch size, clock-skew bounds and version-format checks. Events refused by a limit SHALL be counted, not stored, and SHALL be visible as data loss.

#### Scenario: Flood from one account
- **WHEN** one account sends more events in an hour than the cap, through several workers at once
- **THEN** no more than the cap is stored, and the refused count is recorded

#### Scenario: Skewed client clock
- **WHEN** an event's client time is outside the allowed skew window
- **THEN** the server keeps its own receive time for ordering and flags the client time as untrusted

### Requirement: Retention and account deletion
Receipts SHALL be deleted after a bounded retention period by the existing hourly housekeeping. Deleting an account SHALL delete its receipts in the same deletion. Incidents keep only aggregate, owner-free counts. An affected-account count that cannot be computed reliably SHALL be shown as partial or unknown, never as zero.

#### Scenario: Account deleted
- **WHEN** an account with receipts is deleted
- **THEN** its receipts are gone, its incidents remain without any owner reference, and their affected-account count no longer includes it

#### Scenario: Receipts expired
- **WHEN** receipts are older than the retention period
- **THEN** the housekeeping deletes them in bounded batches, and the incident shows its affected-account count as limited to the retention window

### Requirement: Rollout and kill switch
Monitoring SHALL default off and roll out in stages: off, then owner accounts, then all. One switch SHALL stop all intake writes. Diagnostic push and the Mini App adapter SHALL each have their own switch. Turning any of them off MUST NOT disable payments, lessons, manual bug reports or existing Admin pushes.

#### Scenario: Kill switch on
- **WHEN** the intake mode is set to off
- **THEN** the intake writes nothing and tells clients to pause, clients stop sending, and every learner flow works unchanged

#### Scenario: Owners-only stage
- **WHEN** the intake mode is owners
- **THEN** only the existing admin allowlist's accounts have their events stored; the others are acknowledged and dropped

### Requirement: Separation from analytics and manual reports
Diagnostic events SHALL NOT be written to analytics event stores, and analytics events SHALL NOT create incidents. Monitoring SHALL reuse the Analytics platform keys and flow IDs. Manual bug reports SHALL remain a separate source, and their intake, delivery and retention SHALL stay unchanged.

#### Scenario: Failure during a lesson
- **WHEN** a lesson save fails and is reported
- **THEN** one incident occurrence is recorded, and no analytics event or KPI value changes because of the report

#### Scenario: Manual report sent
- **WHEN** a learner sends a manual bug report on Android or the PWA
- **THEN** it follows the existing report path, and no diagnostic incident is created from it
