# Android practice overlays and covered actions

## Cause

The main scaffold hid navigation only for an active Voice call. Practice,
mistake review, exams and their completion scenes remained inside the floating
tab bar. The streak continuation used system insets and was covered by that
bar; the practice assistant button also floated over exercise controls.

The limit dialog capped its surface height and kept the purchase action in the
scrolling body. At a small viewport or larger font size the action could be
partially below the visible window.

Compose 1.7 additionally measures a non-default-width dialog from the display
height. On Android 15+ its floating window can still be fitted between the
system bars, clipping that larger content. A compact-layout test alone does
not cover this device-window mismatch.

## Fix

- `PracticeUiState.isImmersive` covers loading, active attempts and all result
  types. The main scaffold and practice assistant registration use that same
  state. Exiting restores normal section navigation and the assistant button.
- `SectionLimitOverlay` fills the safe viewport, registers `AssistantHidden`,
  and leaves its existing server-controlled purchase/recheck action outside
  the scrolling content. On API 30+ its own window disables platform inset
  fitting and allows the cutout area; Compose then owns the system padding.
  Close remains at the top.
- Native stroke previews retain length-based timing with a roughly 30% slower
  pace and a 380 ms pause between strokes.

## Risk

This changes presentation and navigation visibility. It does not change
grading, usage accounting, subscription decisions or checkout callbacks.
Keep the running attempt's exit guard and result completion callbacks intact.

## Prevention

- `PracticeImmersiveLayoutTest` renders practice inside the real tab scaffold,
  checks review visibility and assistant registration, advances a streak and
  verifies that navigation returns after completion.
- `SectionLimitOverlayTest` uses a compact viewport, 200% font size and a long
  limit explanation. It checks the whole action's bounds, the original unlock
  callback, assistant suppression and restoration after dismissal.
- The full-height test checks the layout's actual screen origin and height,
  so an oversized floating window cannot pass using only local node bounds.
- Inspect animation pacing with Android animation scales at 1. Automated test
  environments with scale 0 can make a correctly paced preview appear instant.

Run the relevant Direct device tests:

```sh
./gradlew connectedDirectDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=com.pomp.hskai.feature.practice.PracticeImmersiveLayoutTest,com.pomp.hskai.feature.limit.SectionLimitOverlayTest
```
