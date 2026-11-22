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
look of pending-data bars, never to the shell or reserved slots. A refresh the
learner asks for is exempt (pull-to-refresh).

#### Scenario: Cached layer opens instantly
- **WHEN** an embedded layer's page and data are already cached and paint within the anti-flash window
- **THEN** no loading text or placeholder bar is visible before the real content

### Requirement: An embedded layer shows a matching skeleton, never a loading text
Until a PWA layer embedded as its own page paints, the host MUST show that
layer's real title, a working Back control and bars shaped like the layer's
first viewport. It MUST NOT show a loading text. The layer becomes visible at
its own first paint, which is the same skeleton. This covers Dictionary,
Ready Phrases and the Test and Mistakes centres.

#### Scenario: Embedded layer is slow to paint
- **WHEN** the learner opens Dictionary in the PWA and its page has not painted yet
- **THEN** the title, Back and row-shaped bars are visible, no "Yuklanmoqda…" or other loading text appears, and Back closes the layer

#### Scenario: Handoff from host to layer
- **WHEN** the embedded page paints its own skeleton
- **THEN** it replaces the host's skeleton at once, and the header and first three rows move by at most 2 px at 320, 390 and 430 px

#### Scenario: Embedded layer never loads
- **WHEN** an embedded layer's page has not painted after its timeout
- **THEN** the host shows the existing localized connection error with Retry and Back, and Retry loads the page again

### Requirement: Launch shows the course skeleton from its first frame
On a PWA launch, the first page paint MUST be the layout-faithful course
shell: real navigation and the path skeleton. It stays until the course is
ready. A blank page, "…" or a spinner MUST NOT appear between them. A failed
course map shows the existing error with retry.

#### Scenario: Course map is slow at launch
- **WHEN** the learner launches the PWA and the course map request is held
- **THEN** every frame from the first paint until the course is ready shows the nav and the pulsing path skeleton

### Requirement: Pull-to-refresh arms at one exact distance
On the PWA Course, Rating and Profile tabs, a pull from the top MUST arm the
refresh at exactly one finger distance, shown by the ring closing and taking
the accent colour. A release short of it MUST NOT send a request. No pull
starts while a flow, sheet, paywall or layer is open.

#### Scenario: Release before the threshold
- **WHEN** the learner pulls down 139 px from the top of the Course tab and releases
- **THEN** the ring springs back and no request is sent

#### Scenario: Release at the threshold
- **WHEN** the learner pulls down 140 px and releases
- **THEN** the ring shows the armed state before release, and the refresh starts on release

### Requirement: Pull-to-refresh shows a spinning ring and skeleton regions
After an armed release, the ring MUST spin until every refreshed region has
settled, for at least 600 ms. Each refreshed region shows its existing
placeholders in place; header and nav stay real. Success shows the new data.
Failure restores the previous content with an existing localized notice.

#### Scenario: Refresh on the Rating tab
- **WHEN** the learner releases an armed pull on Rating and the request is held
- **THEN** the ring spins, the leaderboard shows its skeleton, and the header and nav stay real and usable

#### Scenario: Refresh fails
- **WHEN** the refresh request fails or times out
- **THEN** the previous content returns unchanged and one localized connection notice appears

#### Scenario: A new version was deployed
- **WHEN** the course HTML on the server is newer than the open page during a refresh
- **THEN** the page reloads once, keeping the ring spinning until it leaves

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

### Requirement: A session start shows the panda only when preparation is slow
In the PWA, a session start (a lesson, Recognition, Pronunciation, Memorize, a
Test exam or a Mistakes review) MUST open directly when ready within 300 ms.
Otherwise it MUST show the existing panda preparing screen until ready, for at
least 300 ms once shown. Back stays usable, and one loader shows at a time.

#### Scenario: Fast session start
- **WHEN** the learner starts a lesson or a practice session in the PWA and it is ready within 300 ms
- **THEN** the first usable card appears with no panda frame and no added wait

#### Scenario: Slow session start
- **WHEN** a session start in the PWA is still preparing after 300 ms
- **THEN** the panda preparing screen appears, stays until the session is ready, and the Back control works while it is shown

#### Scenario: Telegram lesson entry
- **WHEN** a lesson starts in the Telegram Mini App
- **THEN** its preparing screen timing is the same as before this change

### Requirement: Hubs use skeletons, not the panda
In the PWA, hub screens (Test centre, Mistakes centre, Dictionary and Ready
Phrases) MUST NOT show the panda preparing screen. They MUST show
layout-faithful skeletons, and a page that never becomes ready MUST offer a
localized retry.

#### Scenario: Opening the Test or Mistakes centre
- **WHEN** the learner opens the Test centre or the Mistakes centre in the PWA
- **THEN** the hub shows its header and placeholders shaped like its exam cards or mistake rows, never the panda, and they settle with anchors moving by at most 8 px

#### Scenario: Practice page never becomes ready
- **WHEN** a PWA practice page has not become ready after its fallback timeout
- **THEN** it shows the existing localized error with Retry and Back, and Retry loads the page again

### Requirement: Loading states use existing copy and design
Loading, error and retry states MUST:
- reuse the surface's existing localized labels for UZ, RU and TJ, and its
  existing design tokens;
- derive placeholder sizes from the real component styles, never randomized;
- never add a second skeleton-only dictionary or invented placeholder text.

#### Scenario: Retry label in three languages
- **WHEN** the Inbox error state is shown in Uzbek, Russian or Tajik
- **THEN** its retry label is an existing reviewed translation for that language
