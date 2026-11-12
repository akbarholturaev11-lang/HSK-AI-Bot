# Spec Delta

## ADDED Requirements

### Requirement: Android lesson start
The authenticated Android lesson route SHALL record one server-built `android_lesson_started` per account, level, lesson and UTC day after the lesson is allowed, tagged with the route-set client `android`. The record MUST NOT use an event name that a reminder or other product flow reads, and its failure MUST NOT change the lesson response.

#### Scenario: Allowed lesson
- **WHEN** an Android learner opens an allowed lesson
- **THEN** one tagged `android_lesson_started` row exists for that account, level, lesson and day, and no `lesson_started` row is written

#### Scenario: Refetch on the same day
- **WHEN** the same lesson is fetched again on the same UTC day
- **THEN** no second row is written

#### Scenario: Refused lesson
- **WHEN** the lesson is locked, over the free limit or blocked by the foundation gate
- **THEN** no start row is written

#### Scenario: Course > Android lessons
- **WHEN** an administrator selects Android and opens Course
- **THEN** `features.lessons` counts accounts with a tagged Android start from `attributed_since.features_lessons` on, and the entry is omitted before the first tagged row
