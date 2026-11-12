# Spec Delta

## Purpose

Lets administrators see, triage and resolve diagnostic incidents in the existing Admin PWA Inbox, and be alerted on iPhone and Mac only for new, escalated or reopened critical incidents.

## ADDED Requirements

### Requirement: Diagnostic source in the existing Inbox
The existing Admin PWA Inbox SHALL list incidents as one `diagnostic` source beside its current sources, with the same authentication, bounded keyset paging and ordering. No second Admin panel, triage store or notification worker SHALL be created.

#### Scenario: Incident listed
- **WHEN** an authorized admin opens the Inbox with source `all` or `diagnostic`
- **THEN** each incident appears once, regardless of how many events it grouped

#### Scenario: Unauthorized read
- **WHEN** a request without a valid Admin PWA session lists the Inbox
- **THEN** it is refused as today, and no incident data is returned

### Requirement: Safe incident view
An incident item SHALL show its platform, feature, a localized explanation of the failure code, first and last version, first and last seen time, occurrence count, affected accounts (or partial/unknown), priority and triage status. It SHALL offer filters by platform, status and priority. It MUST NOT show any forbidden telemetry field or account identifier.

#### Scenario: Explanation in the admin's language
- **WHEN** an admin reads an incident in UZ, RU or TJ
- **THEN** the failure explanation comes from the canonical catalog in that language

#### Scenario: Unknown affected count
- **WHEN** the affected-account count is limited by retention or by refused events
- **THEN** the view shows it as partial or unknown, never as a confident number or zero

#### Scenario: No private data
- **WHEN** an incident and its detail are rendered
- **THEN** no stack, message, URL, payload, token or account ID appears in the response or the page

### Requirement: Triage with audited automatic reopen
Incident triage SHALL use the existing audited triage store and operations: New is `new`, Investigating is `assigned`, Resolved is `resolved`. A resolved incident SHALL reopen automatically on a new occurrence from a version not older than the newest version at resolution; backend incidents reopen on any new occurrence. Every change, including a system reopen, SHALL be written to the triage audit.

#### Scenario: Admin investigates and resolves
- **WHEN** an admin assigns an incident to themselves and later resolves it
- **THEN** its status moves from new to assigned to resolved, and each step has an audit row

#### Scenario: Failure returns on the fixed version
- **WHEN** a resolved Android incident gets a new occurrence from the same or a newer app version
- **THEN** it reopens with a system audit row and counts as reopened for alerting

#### Scenario: Old version still in use
- **WHEN** a resolved incident gets a new occurrence only from a version older than the newest one at resolution
- **THEN** it stays resolved, and the occurrence is still counted

### Requirement: Bounded critical Apple Push
Diagnostic Apple Push SHALL go through the existing Admin PWA push outbox and dispatcher, and only in three cases: an incident is new at critical severity, its server-observed scope raises it to critical, or a critical incident reopens. Each incident SHALL have a cooldown, and diagnostic alerts SHALL have a global hourly cap.

#### Scenario: Many identical events
- **WHEN** 100 events of one critical fingerprint arrive within a minute
- **THEN** at most one diagnostic push per enrolled device is queued for that incident

#### Scenario: Non-critical incident
- **WHEN** a new incident is below critical severity and its scope stays below the escalation threshold
- **THEN** it appears in the Inbox without any push

#### Scenario: Scope escalation
- **WHEN** a high-severity incident reaches the distinct-account threshold within one hour
- **THEN** it becomes critical, and one diagnostic push is queued per enrolled device

#### Scenario: Diagnostic flood
- **WHEN** many different critical incidents open within one hour
- **THEN** diagnostic pushes stop at the global cap, and payment and Android report alerts are queued and sent as before

### Requirement: Safe push payload and destination
A diagnostic push payload SHALL carry only a fixed safe category. Opening it SHALL lead, after Admin PWA authentication, to the Inbox filtered to diagnostic incidents. Existing payment, Android-report, bot and release alerts SHALL keep their payload, priority and behavior.

#### Scenario: Admin taps the alert
- **WHEN** an admin taps a diagnostic notification
- **THEN** the Admin PWA opens the Inbox with the diagnostic filter once the session is valid, and the notification carried no incident details

#### Scenario: Push accepted but not displayed
- **WHEN** the push provider accepts a diagnostic push
- **THEN** it is recorded as accepted only, never as displayed on the device

### Requirement: Mini App technical source cutover
When the Mini App adapter is enabled, new Mini App technical errors admitted by the intake mode SHALL appear only as diagnostic incidents, and their per-error `technical` push SHALL stop. Errors the mode does not admit keep today's behavior. `technical` items recorded before the cutover stay visible for their existing 30 days. Disabling the adapter SHALL restore the current behavior.

#### Scenario: Adapter enabled
- **WHEN** the Mini App onboarding sends `app_error` after the cutover
- **THEN** one diagnostic incident occurrence is recorded, no new `technical` Inbox item or push appears, and the bot's AI context still receives the error context as today

#### Scenario: Intake off while the adapter is on
- **WHEN** the intake mode is off, or the account is outside the owners stage
- **THEN** the Mini App error is shown and pushed as a `technical` item as today, so no alert is lost

#### Scenario: Adapter disabled again
- **WHEN** the adapter is switched off
- **THEN** new Mini App errors appear as `technical` items with their per-error push, as before
