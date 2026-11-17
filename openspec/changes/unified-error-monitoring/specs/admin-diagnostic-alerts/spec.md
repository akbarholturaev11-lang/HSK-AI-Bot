# Spec Delta

## Purpose

Lets administrators see, triage and mark diagnostic incidents fixed in the existing Admin PWA Inbox. They are alerted on iPhone and Mac for new or escalated critical incidents, and whenever an incident they marked fixed comes back.

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
An incident item SHALL show its platform, feature, a localized explanation of the failure code, first and last version, first and last seen time, occurrence count, affected accounts, priority and triage status. The Inbox API SHALL filter incidents by platform, status and priority; the minimal Inbox MUST NOT gain new filter controls or buttons. No forbidden telemetry field or account identifier SHALL be shown.

#### Scenario: Explanation in the admin's language
- **WHEN** an admin reads an incident in UZ, RU or TJ
- **THEN** the failure explanation comes from the canonical catalog in that language

#### Scenario: Unknown affected count
- **WHEN** the affected-account count is limited by retention or by refused events
- **THEN** the view shows "at least N" or "unknown" in the admin's language, never a confident number or zero

#### Scenario: No private data
- **WHEN** an incident and its detail are rendered
- **THEN** no stack, message, URL, payload, token or account ID appears in the response or the page

### Requirement: Last reported sample in the incident detail
The diagnostic detail SHALL show the debug evidence of one retained receipt, labelled as the last reported sample with its own time and version: exception name, category, a generic reason marked as a likely cause, and source locations. A missing value SHALL read "not captured". The read MUST be bounded per incident, and the drawer MUST NOT gain a new control.

#### Scenario: Sample attribution
- **WHEN** an incident has receipts of several versions, some with a location and newer ones without
- **THEN** the detail shows the newest retained receipt that has a location, with its own time, version, name and reason

#### Scenario: Evidence predates the feature
- **WHEN** an incident's receipts carry only a category
- **THEN** the detail shows the category and "not captured" for the rest, and no location is invented

#### Scenario: No sample at all
- **WHEN** no retained receipt of an incident carries a category
- **THEN** the detail shows the category as "unknown"

#### Scenario: Large incident
- **WHEN** an incident has tens of thousands of receipts
- **THEN** the sample is read from one indexed row per incident, without scanning its receipts

#### Scenario: Three languages
- **WHEN** an admin reads the sample in UZ, RU or TJ
- **THEN** the labels, category and reason come from the canonical catalog in that language

### Requirement: Source link only for a verified commit
A link to an exact source line SHALL be shown only when the reported script version equals the file the deployment serves and the deployment's immutable commit was known when the receipt was stored. A cache token MUST NOT be used as a commit. Otherwise the coordinates SHALL be shown without a link.

#### Scenario: Verified location
- **WHEN** the script version matches the deployed file and the deployment commit is known
- **THEN** the location links to that file and line at that exact commit

#### Scenario: Stale or unknown version
- **WHEN** the script version does not match, is missing, or no deployment commit is configured
- **THEN** the location shows its file, line and column as text only

### Requirement: Triage with audited automatic reopen
Incident triage SHALL use the existing audited triage store: New is `new`, Investigating is `read` (set when an admin opens it) or `assigned`, Resolved is `resolved`. The existing "Fixed" button SHALL resolve in one tap, with no prompt or learner notice. A resolved incident SHALL reopen automatically on an occurrence from a version not older than the newest at resolution (backend: any occurrence), with a localized "fixed error came back" notice. Every change SHALL be audited.

#### Scenario: Admin investigates and resolves
- **WHEN** an admin opens a new incident and later taps "Fixed"
- **THEN** its status moves from new to read to resolved, each step has an audit row, no confirmation prompt appears, and no learner is notified

#### Scenario: Failure returns on the fixed version
- **WHEN** a resolved Android incident gets a new occurrence from the same or a newer app version
- **THEN** it reopens with a system audit row, shows the "fixed error came back" notice with the time and version in UZ, RU or TJ, and counts as reopened for alerting

#### Scenario: Old version still in use
- **WHEN** a resolved incident gets a new occurrence only from a version older than the newest one at resolution
- **THEN** it stays resolved, and the occurrence is still counted

### Requirement: Bounded diagnostic Apple Push
Diagnostic Apple Push SHALL go through the existing Admin PWA push outbox and dispatcher, and only in three cases: an incident is new at critical severity, its server-observed scope raises it to critical, or an incident marked fixed reopens at any severity. New and escalation alerts SHALL have a per-incident cooldown and a global hourly cap. A reopen alert SHALL be sent once per reopen, exempt from both.

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

#### Scenario: Fixed error comes back
- **WHEN** a `normal`-severity incident marked fixed reopens, even during a flood or within the cooldown
- **THEN** exactly one push with the fixed "came back" label is queued per enrolled device

### Requirement: Safe push payload and destination
A diagnostic push payload SHALL carry only a fixed safe category. Opening it SHALL lead, after Admin PWA authentication, to the Inbox filtered to diagnostic incidents. Existing payment, Android-report, bot and release alerts SHALL keep their payload, priority and behavior. Existing Telegram admin messages, including Lava payment alerts, SHALL stay unchanged and MUST NOT be suppressed or deduplicated against diagnostic alerts.

#### Scenario: Admin taps the alert
- **WHEN** an admin taps a diagnostic notification
- **THEN** the Admin PWA opens the Inbox with the diagnostic filter once the session is valid, and the notification carried no incident details

#### Scenario: Push accepted but not displayed
- **WHEN** the push provider accepts a diagnostic push
- **THEN** it is recorded as accepted only, never as displayed on the device

#### Scenario: Lava failure in both channels
- **WHEN** a Lava payment activation fails, raising its Telegram admin alert, and is also reported as a diagnostic incident
- **THEN** the Telegram message is sent as today, the incident appears in the Inbox (with a push when critical), and neither channel suppresses the other

### Requirement: Additive Mini App adapter
When the Mini App adapter is enabled, Mini App technical errors admitted by the intake mode SHALL also be recorded as diagnostic incidents. The existing `technical` Inbox item, its per-error push and the bot's AI context MUST stay unchanged, whether the adapter is on or off. Disabling the adapter SHALL stop only the incident writes.

#### Scenario: Adapter enabled
- **WHEN** the Mini App onboarding sends `app_error` while the adapter is on
- **THEN** the `technical` item and its push appear as today, one diagnostic incident occurrence is also recorded, and the bot's AI context receives the error context as today

#### Scenario: Thirty identical errors
- **WHEN** 30 learners hit the same onboarding save error in one day
- **THEN** 30 `technical` pushes arrive as today, and one grouped diagnostic incident shows 30 occurrences

#### Scenario: Adapter disabled again
- **WHEN** the adapter is switched off
- **THEN** no new incident occurrence is written, and the `technical` items and pushes continue unchanged
