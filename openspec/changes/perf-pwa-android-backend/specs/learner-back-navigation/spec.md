# Spec Delta

## Purpose

Defines how a learner returns to the previous screen in the learner PWA and the
native Android app, so that every back gesture is predictable, single-step and
free of blank or see-through frames, on every current and future screen.

## ADDED Requirements

### Requirement: One back gesture moves exactly one step
Every way back on a surface MUST close only the top layer or screen, exactly
once per user gesture:
- PWA: in-page edge swipe, browser or Home Screen history swipe, browser back,
  and Telegram BackButton when inside Telegram;
- Android: system back gesture and button.

This holds even when a gesture triggers both an in-page drag and the browser's
own history navigation.

#### Scenario: Edge swipe that also triggers the browser's history swipe
- **WHEN** the learner starts a swipe within the left 16 px of the installed PWA on a dictionary word page and the browser also delivers its own history navigation for that gesture, before or after the in-page drag settles
- **THEN** only the word page closes, the dictionary list stays open, and the history guard used by Android back is restored

#### Scenario: Consecutive edge swipes
- **WHEN** the learner performs three separate edge swipes from a dictionary word page
- **THEN** they go word → dictionary list → Practice → Course, one level per swipe

#### Scenario: Control at the screen edge
- **WHEN** the learner taps a button, link or input that sits inside the edge strip
- **THEN** the tap reaches the control and is not consumed by the back gesture

### Requirement: No blank or see-through frame while going back
A layer being dragged back MUST stay opaque, and the screen it reveals must
already be painted. A completed swipe closes the layer while it is still
off-screen; it never flashes back to its open position first.

#### Scenario: Dragging a dictionary word page
- **WHEN** the learner drags a dictionary word page to the right
- **THEN** the word page has an opaque background with its scene art, and the list underneath shows at the position the learner left it

#### Scenario: Completing the drag
- **WHEN** the drag passes the completion threshold and is released
- **THEN** the word page closes before its transform is reset, with no frame showing it at x=0

### Requirement: Returning keeps the previous position
Returning from a detail to its list MUST restore the list's scroll position, search
text and filters on PWA and Android. The course map's centring on the current
lesson when the Course tab is opened again is intended behaviour.

#### Scenario: Android dictionary round trip
- **WHEN** the learner scrolls the Android dictionary to row 120, opens a word and goes back
- **THEN** row 120 is visible again and the list has not jumped to the top

### Requirement: New layers inherit the navigation contract
Every new PWA layer or screen, and every new Android detail screen, MUST meet
these requirements from its first version. It registers with the existing back
mechanism, either the PWA navigation layer list or an Android back handler,
rather than adding its own back logic. It also extends the existing swipe-back
regression or adds an Android test.

#### Scenario: A new PWA overlay is added
- **WHEN** a change adds a new learner PWA overlay
- **THEN** the overlay closes by one edge swipe, one browser back and one Telegram BackButton press, and the browser swipe-back regression covers it
