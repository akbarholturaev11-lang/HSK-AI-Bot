# Smart Reminder Preferences — Spec Delta

## Purpose

Provide one authenticated account study-reminder preference across clients while preserving each channel's actual consent, OS restrictions and legacy choices. These are proposed requirements; the current independent settings do not yet implement this contract.

## ADDED Requirements

### Requirement: Canonical account settings
The system SHALL expose one study-reminder settings state per canonical account across Telegram/Mini App and compatible Android clients. It MUST derive ownership from verified platform authentication, including native accounts without Telegram, and reject blocked, revoked or pending-deletion eligibility.

#### Scenario: Native-only learner reads settings
- **WHEN** a valid Android learner without a Telegram identity reads Smart settings
- **THEN** the learner receives their canonical account state without a fabricated Telegram identifier or Telegram enrollment

#### Scenario: Unauthorized or ineligible reader
- **WHEN** a request has invalid Telegram proof, an expired/revoked native session, another account's device, a blocked account or a pending deletion
- **THEN** the operation is denied without exposing or modifying preferences, jobs or account access

#### Scenario: Two supported clients read after a change
- **WHEN** a confirmed preference change is subsequently read from Android and Telegram/Mini App
- **THEN** both expose the same account revision and effective master state with channel-specific eligibility clearly retained

### Requirement: Consent and capability remain distinct
The system MUST authorize study only for historically permitted or intentionally enabled channels and eligible owned endpoints. Account ON, OS grant, installation, Telegram linkage or motivation default ON MUST NOT grant new study consent. Channel OFF and OS denial MUST remain effective under account ON; all channels OFF MUST yield effective study OFF. Previously eligible study channels SHALL upgrade without a new Smart activation prompt (D01/D14).

#### Scenario: Mixed Telegram ON and Android OFF
- **WHEN** saved Telegram study consent is ON and an Android installation has explicit study OFF
- **THEN** only Telegram is eligible; seamless upgrade does not enable Android, repeat consent or infer a manual time lock

#### Scenario: Motivation-only evidence
- **WHEN** the only source is a Mini App motivation flag defaulting to True or a legacy Android motivation preference
- **THEN** no Smart study channel becomes permitted and motivation remains separately governed

#### Scenario: Study channel muted but account notices allowed
- **WHEN** Android reports account-notice permission but the study notification channel is muted or its permission is unknown
- **THEN** Smart Android study delivery is ineligible; existing account-notice behavior remains independent

#### Scenario: All channels OFF and newly requested OS permission
- **WHEN** every known study channel is OFF, or a new channel lacks OS permission
- **THEN** the effective master is OFF for all-OFF sources, no channel is silently enabled, and any required OS prompt occurs only through an intentional supported permission action

### Requirement: Revision-safe intentional mutations
Preference writes SHALL require explicit allowlisted typed values, an expected account revision and retry identity. Concurrent stale writes MUST be rejected without partial changes. Authentication MUST bind any selected device to its owner. Unsupported fields, missing or ambiguous booleans and invalid zones MUST NOT mutate Smart state.

#### Scenario: Stale Android ON races Telegram OFF
- **WHEN** both clients read revision r, Telegram persists global OFF at r+1 and Android submits ON with r
- **THEN** Android receives a conflict with fresh-state recovery; global OFF remains effective and no grant is restored

#### Scenario: Invalid payload or forged device
- **WHEN** a writer supplies a string boolean, missing required change value, invalid IANA zone, unknown field or another learner's device
- **THEN** the request fails validation or authorization without partial mutation or changed payment/course state

#### Scenario: Mutation retry after lost response
- **WHEN** the same authenticated mutation identity and body are retried after a successful write whose response was lost
- **THEN** the original outcome is returned without another revision change; reusing that identity with different content is rejected

### Requirement: Durable global OFF
Explicit account study OFF SHALL invalidate unattempted jobs and outstanding grants across all server-controlled study paths and compatible clients. Old APIs, stale callbacks, backfill, optimizer changes and rollback MUST NOT resurrect it. Re-enabling study SHALL require a current intentional action and SHALL NOT grant consent to a previously OFF channel.

#### Scenario: OFF while a job is pending
- **WHEN** global OFF commits before a job crosses its authorized dispatch boundary
- **THEN** no new study attempt or compatible client post is authorized; motivation and transactional preferences are not overwritten

#### Scenario: Already externalized attempt
- **WHEN** OFF occurs after provider IO has irreversibly begun or an OS post has already occurred
- **THEN** future grants and attempts stop, the in-flight outcome remains honestly classified, and the system does not claim it recalled a physical notification

#### Scenario: Legacy write after opt-out
- **WHEN** an old time callback, device-preference sync or migration replay arrives after global OFF
- **THEN** it cannot clear the OFF tombstone, advance Smart consent or enable another channel; supported legacy response shapes stay compatible

### Requirement: Time and channel overrides
Smart time and endpoint selection SHALL be automatic by default, using reliable actual learning and delivery signals. Cold start SHALL preserve a genuine legacy time. Only intentional manual lock SHALL fix time or channel. User quiet/pause settings and OS restrictions MUST prevail; there SHALL be no predefined global night blackout (D02/D04/D06).

#### Scenario: Habit becomes reliable
- **WHEN** an unlocked learner's verified study history becomes sufficiently reliable to adapt time
- **THEN** time can change automatically without a feature modal, while an explicitly locked time remains unchanged

#### Scenario: Learner habit is at night
- **WHEN** reliable study history favors 02:00 and there is no personal quiet/pause restriction or OS denial
- **THEN** the policy does not suppress solely because of a global nighttime rule; daily account limits still apply

#### Scenario: Locked channel unavailable
- **WHEN** the learner's manually selected channel is denied, unreachable or unsupported
- **THEN** no silent automatic channel substitution occurs outside the verified-failure fallback contract

### Requirement: Evidence-preserving legacy migration
Migration SHALL preserve source category, scope, known ON/OFF, permission, time and genuine provenance. Unknown or contradictory evidence MUST NOT create new study permission or invented action timestamps. Setup cancellation MUST NOT be interpreted as persisted OFF. Migration SHALL be idempotent and SHALL NOT treat a saved time as explicit manual lock.

#### Scenario: Telegram saved time then setup Cancel
- **WHEN** an existing saved study time is followed only by cancellation of the setup workflow
- **THEN** migration retains the actual saved ON/time evidence and does not fabricate a historical OFF action

#### Scenario: Conflicting Android snapshots
- **WHEN** local device consent and a stale server mirror conflict without authoritative action ordering
- **THEN** migration marks the source unresolved and grants no additional delivery permission until current evidence resolves it

#### Scenario: Backfill rerun after new opt-out
- **WHEN** the same migration source is replayed after a current explicit Smart OFF
- **THEN** the current OFF and revision survive and no duplicate source/grant is created

### Requirement: Mixed-version cutover safety
An account MUST NOT enter new cross-channel study dispatch while an uncontrolled old Android autonomous sender remains possible. Version strings, inactivity and missing receipts MUST NOT prove fencing. Compatible Android clients SHALL disable autonomous study posting and consult server jobs from both FCM and WorkManager; offline new clients MUST fail closed.

#### Scenario: Old offline APK and a new installation
- **WHEN** an account has a verified new installation plus an unknown or prior APK with potentially active local reminders
- **THEN** new central dispatch remains excluded for that account until cutover evidence is adequate; no global physical-display guarantee is reported for the old APK

#### Scenario: FCM and WorkManager on a compatible build
- **WHEN** both triggers run for the same account/day on a migrated compatible installation
- **THEN** both use the same selected server job and durable local guard; neither creates an independent reminder

#### Scenario: Old client remains outside cutover
- **WHEN** an old client uses its supported legacy API before safe migration
- **THEN** its existing response contract is preserved and it receives no new Smart job authority; the UI does not falsely claim that old offline local posting can be remotely stopped
### Requirement: Authenticated own-device capability observation
An Android capability observation SHALL derive canonical owner, device and session from verified native bearer authentication and recheck them under the User-first lock. The server SHALL bound observation validity by current verified auth deadlines and use observation-generation CAS. Capability SHALL remain separate from consent, cohort admission, old-client fencing and posting authority.

#### Scenario: Late allow arrives after denial
- **WHEN** an older observation generation reports permission allowed after a newer denied observation
- **THEN** CAS refuses it and the stored denial remains effective; an unknown report cannot erase that denial either

#### Scenario: All reported capability facts are positive
- **WHEN** an authenticated device reports a supported protocol, autonomous posting disabled and study permission allowed
- **THEN** it receives observation metadata only; no channel consent, cohort enrollment, job, attempt or posting grant is created

#### Scenario: Study capability is lost
- **WHEN** an authenticated observation loses a study prerequisite
- **THEN** existing pending authority is invalidated while explicit intent, externalized outcomes and account-notice permission remain independent
