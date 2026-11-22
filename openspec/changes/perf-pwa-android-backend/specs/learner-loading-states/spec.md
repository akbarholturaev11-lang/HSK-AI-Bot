# Spec Delta

## Purpose

Defines what a learner sees while a learner screen, layer or section loads,
fails or retries on the PWA and the native Android app, so no surface shows a
blank, text-only or full-screen spinner state while its structure is known.

## ADDED Requirements

### Requirement: Known structure shows from the first useful frame
When a learner opens a screen, layer or section, it MUST show the content it
already knows from its first useful frame: header, back control, tabs, titles,
labels and navigation, as real localized text. Placeholders stand in only for
pending data. A blank page, a centred text-only status or a full-screen spinner
is not an acceptable loading state on either platform.

#### Scenario: Inbox opens while its feed is pending
- **WHEN** the learner opens the Inbox in the PWA and the feed request has not answered
- **THEN** the Inbox header and close control are real, and placeholder rows shaped like real notice rows fill the first viewport

#### Scenario: Android Ready Phrases opens on a slow network
- **WHEN** Ready Phrases opens on Android before its data has loaded
- **THEN** the screen shows its header and row-shaped placeholders instead of one centred spinner

#### Scenario: First-ever Android Course open
- **WHEN** the Android Course opens with no cached course map
- **THEN** it shows the Course header and a path-shaped placeholder instead of a full-screen loader, and later opens still use the cached map at once

### Requirement: Fast responses do not flash placeholders
A response that arrives before a placeholder would be noticeable MUST replace
its slot directly, without a visible placeholder flash. Reserved geometry is
still present from the first frame. Any anti-flash delay applies only to the
look of pending-data bars, never to the shell or reserved slots.

#### Scenario: Cached layer opens instantly
- **WHEN** an embedded layer's page and data are already cached and paint within the anti-flash window
- **THEN** no loading text or placeholder bar is visible before the real content

### Requirement: Loading, empty, error and retry are distinct and local
Each independently loaded region MUST have separate loading, empty, error and
retry states:
- an error keeps the region's reserved geometry and offers a localized retry;
- the retry re-requests only that region;
- other settled regions and navigation stay usable.

#### Scenario: Inbox feed fails
- **WHEN** the Inbox feed request fails or times out
- **THEN** the Inbox shows a localized error with a retry control in place, and choosing retry shows placeholders again and then the feed, without closing the layer

#### Scenario: One section fails while others are ready
- **WHEN** one section's request fails after other sections have settled
- **THEN** the settled sections, header and navigation do not move or disappear

### Requirement: Settling keeps stable anchors
When data replaces a placeholder, stable anchors MUST stay in place: header,
navigation, tabs and already-settled sections.
- PWA: anchors move by at most 8 px, and the screen's CLS is at most 0.1, at
  320, 390 and 430 px widths.
- Android: an equivalent check on the native layout bounds.

#### Scenario: PWA layer settles at 320 px
- **WHEN** a PWA layer settles from placeholders to data at 320 px width
- **THEN** its header and the first row's top edge move by at most 8 px, and its CLS is at most 0.1

### Requirement: Loading states use existing copy and design
Loading, error and retry states MUST:
- reuse the surface's existing localized labels for UZ, RU and TJ, and its
  existing design tokens;
- derive placeholder sizes from the real component styles, never randomized;
- never add a second skeleton-only dictionary or invented placeholder text.

#### Scenario: Retry label in three languages
- **WHEN** the Inbox error state is shown in Uzbek, Russian or Tajik
- **THEN** its retry label is an existing reviewed translation for that language
