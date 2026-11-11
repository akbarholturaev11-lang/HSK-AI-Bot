# Spec Delta

## ADDED Requirements

### Requirement: Platform-scoped section metrics
For the Android, Telegram Mini App and iPhone PWA filters, every V10 section SHALL compute each applicable metric only from that platform's recorded activity. Platform scoping SHALL apply only to event families whose platform attribution is verified in code. Android covers both Play and Direct builds. A metric MUST NOT be filled with overall values or with another platform's values.

#### Scenario: Android course metrics
- **WHEN** an administrator selects Android and opens Course
- **THEN** lesson and onboarding metrics come only from verified Android activity, with Android's own denominators

#### Scenario: Unaudited attribution
- **WHEN** a metric's event family has no verified platform attribution yet
- **THEN** that metric is unavailable for the platform with `attribution_not_audited`, and the rest of the section still renders

#### Scenario: Android channel not recorded
- **WHEN** Android records carry no Play/Direct channel
- **THEN** the combined Android value is shown and no Play/Direct split is invented

#### Scenario: Shared writer gains a platform key
- **WHEN** a shared lesson, practice, exam or mistake-review write starts storing a server-set client key
- **THEN** per-platform values for that family use only rows with the key, report the earliest attributed time, and Overall still counts every row

#### Scenario: Client-supplied platform metadata
- **WHEN** a Telegram client sends a PWA source or transport value in its event payload
- **THEN** the stored row is not attributed to the iPhone PWA

### Requirement: Metric states
Every metric SHALL report exactly one state:
- `available`, with its value (which may be a real zero);
- `not_applicable`, when the metric does not concern the platform;
- unavailable, with one reason: `not_instrumented`, `attribution_not_audited`, `detail_limited` or `no_data`.

`not_applicable` MUST NOT be used for missing data, and an unavailable metric MUST NOT be shown as zero.

#### Scenario: Not applicable versus not instrumented
- **WHEN** desktop device inventory is viewed under the Mini App filter, and AI cost, which records no platform, is viewed under the PWA filter
- **THEN** the first is `not_applicable`, the second is unavailable with `not_instrumented`, and neither is zero

#### Scenario: Detail row limit exceeded
- **WHEN** a detailed calculation exceeds its safe row limit
- **THEN** the metric is unavailable with `detail_limited` and is not calculated from truncated rows

### Requirement: Cross-platform canonical deduplication
Overall account metrics SHALL count each canonical account once, however many devices or platforms it used in the window. Each platform view SHALL count the account once for that platform. Responses SHALL mark platform counts as overlapping, and device inventory SHALL keep its separate device grain.

#### Scenario: One account on three platforms
- **WHEN** one canonical account is active on Android, in the Mini App and in the PWA on the same day
- **THEN** overall daily active accounts include it once, each platform view includes it once, and the platform counts are marked overlapping

#### Scenario: One account on two Android devices
- **WHEN** one account opens the Android app on two devices in a day
- **THEN** Android active accounts include it once, and device inventory counts two devices

### Requirement: Existing V10 metrics preserved
Existing V10 metric values, keys and definitions SHALL stay unchanged for identical stored data. A superseded definition SHALL stay readable under its own label until it is removed in a reviewed change.

#### Scenario: Regression fixture
- **WHEN** the fixture dataset is projected for every section, platform and period before and after this change
- **THEN** every pre-existing metric value is identical, and only new keys or labels differ

### Requirement: Attempt-based PWA Pro funnel
The Conversion section SHALL provide a PWA Pro funnel, separate from the legacy manual-receipt funnel. Attempts are keyed by canonical account and attempt ID, and every step's denominator is the same attempt cohort. Paid SHALL mean only a server-verified, approved payment for that attempt. A refund or lost chargeback SHALL be counted as a reversal.

#### Scenario: Verified Lava payment
- **WHEN** a verified Lava invoice becomes an approved Pro payment for a recorded attempt
- **THEN** only that owner's matching attempt moves to paid

#### Scenario: Unverified success signals
- **WHEN** a learner clicks checkout, returns from the provider URL, or a webhook fails verification
- **THEN** the attempt is not counted as paid

#### Scenario: Refund after payment
- **WHEN** a paid attempt's invoice is later refunded
- **THEN** the attempt stays paid at its original time, and is also counted as reversed

#### Scenario: Legacy funnel unaffected
- **WHEN** only legacy manual-receipt events exist in the window
- **THEN** the legacy funnel output is unchanged, and the PWA Pro funnel shows an empty cohort rather than borrowed steps

### Requirement: Cross-platform return retention
The existing D1/D7 series counts course-map opens, which both the Mini App and the PWA record. It SHALL keep its definition under a course-open label. A separate cross-platform D1/D7 return series SHALL count each mature-cohort account once when it has verified user activity on any covered platform. The series SHALL list the platforms it covers.

#### Scenario: One account in two apps
- **WHEN** one account is active in the Android app and the PWA during its D7 window
- **THEN** it counts once in cross-platform D7 return

#### Scenario: Passive activity
- **WHEN** an account's only activity is a delivered notification, an admin payment decision or a background job
- **THEN** it does not count as returned

### Requirement: Per-platform source freshness
The Report section SHALL show, for each platform source, the latest recorded event time and the number of events whose owner cannot be resolved. These are aggregates only, so that a disconnected or stale platform is visible.

#### Scenario: Platform stopped sending events
- **WHEN** a platform has recorded no events for longer than its expected window
- **THEN** Report shows that platform's latest event time as stale, without learner identifiers or raw payloads
