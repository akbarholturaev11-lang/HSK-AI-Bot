# Spec Delta

## Purpose

Defines the measurable acceptance that learner-facing PWA, native Android and
shared Backend changes must meet before they count as done. It also defines the
automated gate that refuses unverified changes, so performance holds for future
features as well as today's.

## ADDED Requirements

### Requirement: Every learner-facing change carries a matching regression test
A pull request or main integration that changes implementation MUST also change
a regression test for that surface. The gate refuses the change otherwise. The
three surfaces are:
- Backend: API, services, repositories, DB or migrations;
- learner PWA: static HTML, JS or CSS;
- native Android: Kotlin under the app's main source set.

A test for another surface does not count.

#### Scenario: Android screen changed without an Android test
- **WHEN** a pull request changes an Android screen's Kotlin source and only changes web or backend tests
- **THEN** the performance contract check fails and names the missing Android test

#### Scenario: Android build or resource change
- **WHEN** a pull request changes only Android build scripts, resources or documentation
- **THEN** the gate does not demand an Android test

### Requirement: Navigation regressions run on both browser engines
The swipe-back regression is a required part of the permanent policy and MUST run
on Chromium and WebKit whenever learner web code changes.

#### Scenario: The swipe-back regression is removed
- **WHEN** a change deletes the swipe-back regression file
- **THEN** the performance contract check fails

### Requirement: Performance claims are measured, not inferred
A change MUST NOT claim to make the product faster without comparable
before/after evidence:
- PWA: filmstrip, LCP, CLS and INP at mobile widths;
- Android: cold and warm start, frame jank and ANR data;
- Backend: route p50/p95/p99 and SQL statement counts.

A passing CI run, or the presence of skeleton code, is not such evidence. Paths
measured as already fast are left unchanged.

#### Scenario: Optimising an already fast route
- **WHEN** production data shows a route's p95 under 100 ms, for example session or course HTML
- **THEN** no optimisation work is scheduled for it beyond keeping its existing regression tests

#### Scenario: Optimising a measured slow route
- **WHEN** a change targets lesson completion, whose production p95 is about 490–670 ms
- **THEN** it records SQL statement counts and timings before and after, preserves atomic progress and XP updates, and reports production p50/p95 after deploy

### Requirement: Contracts and data stay intact
Performance and navigation work MUST NOT change any of the following:
- account ownership and session checks;
- CSRF;
- Trial, Free and Pro decisions;
- payments and refunds;
- lesson progress, grading, localization (UZ/RU/TJ) or Telegram SDK behaviour.

Nor may it cache private data across accounts.

#### Scenario: Back gesture over an access gate
- **WHEN** the paywall, level-up or an ad overlay is open
- **THEN** a back gesture does not dismiss it
