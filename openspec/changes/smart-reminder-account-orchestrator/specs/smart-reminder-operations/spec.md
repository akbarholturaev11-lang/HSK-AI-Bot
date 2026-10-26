# Smart Reminder Operations — Spec Delta

## Purpose

Govern safe rollout, reversible delivery, privacy, source-backed learning outcomes and protected administration of Smart Reminders. These requirements describe proposed observable behavior, not a deployed service or a claim that real-client acceptance has passed.

## ADDED Requirements

### Requirement: Evidence-gated cutover
The system SHALL move eligible accounts from legacy study senders to Smart dispatch only after their consent sources, client capabilities and competing senders are reconciled. A shadow or disabled rollout MUST create no user-visible Smart notification. An account MUST NOT run both independent old and new study paths during cutover.

#### Scenario: Shadow evaluation
- **WHEN** a cohort is selected for policy comparison while Smart dispatch is disabled
- **THEN** decisions and suppression reasons can be compared without a Smart provider attempt or Android local post authorized by the new service

#### Scenario: Unsupported older installation
- **WHEN** an account may still have an offline old Android installation able to post locally without a server claim
- **THEN** that account stays out of cross-channel cutover until verified fencing or another safe migration condition is met; the system reports no physical-display guarantee for the old installation

#### Scenario: Two workers during canary
- **WHEN** two scheduler processes evaluate one eligible account and local day concurrently
- **THEN** at most one new study job gains delivery authority and the prior server study sender cannot independently dispatch for that migrated account

### Requirement: Fail-safe rollback
The system SHALL have a server-controlled Smart dispatch stop that prevents new attempts, expires pending jobs and invalidates outstanding new grants without deleting explicit OFF, consent provenance or revisions. Legacy senders MUST resume only after a fresh account/channel eligibility and day-budget check; uncertain attempts MUST NOT be replayed.

#### Scenario: Rollback after account opt-out
- **WHEN** a learner turns study OFF and an operator later disables Smart dispatch
- **THEN** no old or new study sender re-enables or sends to that learner; the OFF revision remains visible on all compatible clients

#### Scenario: Rollback with unconfirmed provider attempt
- **WHEN** an FCM provider accepted a job but client display is unknown before rollback
- **THEN** rollback records an ambiguous outcome and authorizes no replacement Telegram study send for that job

#### Scenario: Schema reversal would lose consent evidence
- **WHEN** a downgrade would drop nonempty Smart preference, job, attempt or opt-out history
- **THEN** the downgrade is refused until a separately reviewed, non-destructive preservation procedure exists

### Requirement: Data minimization and account deletion
Smart Reminder SHALL retain only necessary personal learning, consent, job and outcome data with finite class-specific retention. Expired detail MUST be removed or reduced to privacy-safe aggregates. Account deletion or device revocation MUST cancel applicable queued jobs and derived personal features; financial retention and transactional notices remain separately governed.

#### Scenario: Retention expiry
- **WHEN** the approved retention period for a raw attempt or learning-response class expires
- **THEN** identifiable detail is deleted or irreversibly minimized while only permitted summary data remains; no indefinite raw clickstream accumulates

#### Scenario: Deletion submitted before dispatch
- **WHEN** a learner has a pending account-deletion request or completed purge while a study job is queued
- **THEN** that account receives no later new Smart attempt, and purge removes personal jobs, attempts, capabilities, tokens and derived habit features under the account-deletion contract

#### Scenario: Device revoked during claim
- **WHEN** a device is revoked, logged out or transferred before it uses a study grant
- **THEN** its grant and receipt authority fail, no wrong-account post is authorized, and no personal capability remains eligible

### Requirement: Truthful delivery and learning attribution
Operations SHALL distinguish scheduled, suppressed, provider attempted/accepted, verified client action, OS display when independently evidenced, opened and server-confirmed learning. Missing evidence MUST remain unknown. A notification open or existing Mini App open proxy MUST NOT be counted as causal study return or lesson completion.

#### Scenario: Provider accepted without display proof
- **WHEN** FCM accepts a hint or Telegram accepts a send but no credible display/read signal exists
- **THEN** the result is accepted or unconfirmed, not shown, read or learned

#### Scenario: Open without studying
- **WHEN** a learner opens the Mini App from a reminder but makes no server-confirmed study progress
- **THEN** open is reported separately and learning-reactivation/completion counts do not increase

#### Scenario: Late or repeated learning event
- **WHEN** the same canonical lesson result is replayed or recorded after its attribution window
- **THEN** results remain deduplicated by canonical account and are attributed only within the documented cohort and window

### Requirement: Protected minimal administration
The existing Admin PWA SHALL offer one simple Smart control and statistics surface with an authorized kill switch, existing localized template edit/preview and real counts for sent, suppressed, opted out and verified learning return. It MUST follow the existing passkey, audit, minimal-action and private analytics contracts; absent or immature data MUST be shown as unavailable, not zero or invented success.

#### Scenario: Authorized operator stops dispatch
- **WHEN** an authorized operator executes the existing protected command for the Smart kill switch
- **THEN** the stop takes effect on live dispatch authority, is audited and does not depend on a 24-hour analytics cache refresh

#### Scenario: Uninstrumented metric
- **WHEN** there is no mature Smart learning-outcome cohort or reliable display signal
- **THEN** the UI shows an explicit unavailable/collecting state with population, time-window and snapshot age; it does not present a fabricated rate

#### Scenario: Unauthorized read or edit
- **WHEN** an admin session is missing, revoked or lacks the required role during a read, cache wait, template change or kill-switch action
- **THEN** private metrics and control are denied without revealing learner records or command authority

#### Scenario: Learner and administrator push separation
- **WHEN** the Admin PWA's own notification capability exists
- **THEN** it is not treated as learner Web Push consent, learner device eligibility or a Smart delivery adapter

### Requirement: Baseline-grounded experimentation
Before enabling a Smart experiment, operations MUST measure actual eligible traffic and learning baseline, define cohort origin, denominators, observation window, guardrails and a powered MDE/sample-size/duration plan. Account-level assignment MUST be stable; existing D1 recovery holdouts and controls MUST never receive a treatment study send through another channel. Underpowered results MUST NOT be called a win.

#### Scenario: Insufficient baseline or traffic
- **WHEN** eligible cohort volume or mature learning observations cannot support a target or duration
- **THEN** no invented uplift percentage, fixed trial length or positive experiment result is displayed or used to enable rollout

#### Scenario: Existing D1 holdout intersects pilot
- **WHEN** a canonical account is in the existing D1 recovery control or another registered study holdout
- **THEN** the Smart policy respects the applicable exclusion consistently across Telegram and Android without reassigning by device or Telegram ID

#### Scenario: Valid comparison
- **WHEN** a registered treatment/control experiment reaches its planned observation point
- **THEN** reporting uses all assigned eligible accounts, server-confirmed learning outcomes, real denominators and uncertainty; delivered-only responder selection is labeled diagnostic

### Requirement: Safe automatic optimizer progression
Eligible new and sparse-history learners SHALL receive useful deterministic rules immediately. ML decisions SHALL activate automatically for a user only after a globally validated model is safely enabled and that user's evidence satisfies a versioned quality gate. Stale evidence, model failure, regression or any conflict with consent, access, day budget or manual override MUST revert to rules without an extra notification.

#### Scenario: New learner without a model
- **WHEN** study consent and channel eligibility exist but no reliable model or sufficient personal evidence exists
- **THEN** the functioning rule policy decides the reminder without an AI activation prompt

#### Scenario: Quality gate crossed
- **WHEN** a validated model is released and a learner's verified data crosses the approved eligibility gate
- **THEN** optimization can switch to the model automatically, while existing consent and one-per-day limits still govern every decision

#### Scenario: Model degraded after activation
- **WHEN** model quality, freshness, availability or a safety guard fails
- **THEN** decisions fall back to rules for that user, preserving already reserved jobs and avoiding a second same-day attempt
