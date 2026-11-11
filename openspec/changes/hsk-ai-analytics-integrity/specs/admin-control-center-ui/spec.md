# Spec Delta

## ADDED Requirements

### Requirement: Per-platform states in existing tabs
Selecting Overall, Android, Telegram Mini App or iPhone PWA SHALL render each existing Statistics tab's values for that scope. No new tab is added. Available, `not_applicable`, unavailable (with reason) and real-zero metrics SHALL look different. All labels SHALL come from canonical UZ/RU/TJ catalogs.

#### Scenario: Value in the right place
- **WHEN** a Mini App lesson completion is recorded and the snapshot is refreshed
- **THEN** it appears in the Course tab under the Mini App and Overall filters, and not under Android or PWA

#### Scenario: Mobile Tajik unavailable metric
- **WHEN** an administrator opens a tab at a 390-pixel viewport in Tajik and a PWA metric is unavailable
- **THEN** a localized unavailable state and reason are shown, with no zero value and no horizontal overflow

### Requirement: Distinct retention labels
The Course/activity tab SHALL label the course-open retention series (Mini App and PWA opens) and the cross-platform return series distinctly. Each SHALL show its own denominator, and the two series MUST NOT be merged.

#### Scenario: Both series shown
- **WHEN** an administrator views retention
- **THEN** both series appear with distinct localized labels and their own denominators
