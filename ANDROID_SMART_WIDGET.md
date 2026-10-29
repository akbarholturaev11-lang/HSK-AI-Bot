# Android Smart Widget

Native Android home-screen widget for HSK AI. It is a Glance widget owned by the Android APK; it never opens Telegram or the Mini App.

## Change points

| Need | File | Edit |
| --- | --- | --- |
| Refresh/reminder/stale times | `android/app/src/main/java/com/pomp/hskai/widget/WidgetPolicy.kt` | Change the constant, then increment `SCHEDULE_VERSION` when the schedule changes. Shared semantic validity is defined by the server; the renderer adds no clock thresholds. |
| When the panda is calm, bored, worried or relieved | `android/app/src/main/java/com/pomp/hskai/widget/WidgetVisualState.kt` | `WidgetVisualResolver` is the only engine that produces a state. Nothing else decides art. |
| Which drawing and which line a state shows | `android/app/src/main/java/com/pomp/hskai/widget/WidgetArt.kt` | The legacy 28-scene table retains wording/rollback references; active flat poses come from WidgetPandaArt. |
| Link/stale/foundation behaviour | `android/app/src/main/java/com/pomp/hskai/widget/WidgetState.kt` | `WidgetStateResolver.resolve` answers access and freshness only, never mood. |
| Reminder wording variants | `android/app/src/main/res/values*/strings.xml` (`notify_*_body*`) + `StudyNotifications.bodies` | Add the body in all three languages and to the list; `WidgetPolicy.REMINDER_VARIANTS` says how many are rotated. |
| Widget copy | `localization/android/main/values*/widget_personal.xml` | Author new personal labels in all three canonical bundles and regenerate. Frozen legacy resources stay byte-identical. |
| Panda artwork | `widget/WidgetPandaArt.kt` + `res/drawable-nodpi/widget_panda_flat_sheet.png` | Three owner-approved modern transparent poses. Update the approved atlas frame bounds with the image; trim/scale is a cached presentation step. Existing 28 scene assets remain unchanged for recovery. |
| Responsive layout | `android/app/src/main/java/com/pomp/hskai/widget/HskAiSmartWidget.kt` | Layout only; state, art and copy selection stay elsewhere. |
| Add-widget UI | `android/app/src/main/java/com/pomp/hskai/widget/WidgetInstallPromptScreen.kt` | One full-screen prompt for onboarding, the daily reminder and Profile. It previews the real widget (same art and `widgetCopy` as `WidgetContent`) at 2x2 cells on a blurred home screen, hides the AI button, closes itself the moment a widget lands (`HskAiWidgetReceiver.placements` or resume) and then `WidgetPlacedNotice` shows for 1.5 s. On Xiaomi a pin that shows no system UI within 2 s is treated as blocked by the home-screen-shortcuts permission (`WidgetInstallPromptPolicy.pinLooksBlocked`). |
| API event allowlist | `app/api/android_events.py` | Add an event to the Pydantic literal and the server model allowlist together. |

## Personal state and retained art

`WidgetVisualResolver` consumes only the current authenticated v1 projection
from [the shared contract](docs/smart-reminders/SMART_WIDGET_CONTEXT.md).
There are no universal morning/evening/22:00 urgency boundaries in this renderer.

| Shared phase | Existing art family | Copy |
| --- | --- | --- |
| `before_study` | `DAY` | Personal study time is ahead |
| `study_time_reached` | `WAITING` | Personal study time has arrived |
| `completed` | `COMPLETED` | Verified goal, plan or course completion |
| Neutral/unknown/quiet/paused/unavailable | `DAY` | Calm permitted progress, no invented urgency |

Expired/future, wrong owner/epoch/course/day/zone and malformed contexts cannot
personalize. Access/stale/foundation rendering remains separate. A milestone
requires verified current-day goal/plan completion plus the known server streak;
raw reward XP and `dayComplete` are not proof. Other special kinds remain dormant.
The existing 28 scene assets and deterministic variant/wording references remain
available for recovery. Active rendering uses three owner-approved modern flat
panda poses (calm/wave/celebrate); no old urgent clock family is produced.

## Text, mascot and typography

Square widgets reserve a header above the panda. Compact/wide widgets use
adjacent text and art cells. Native rounded text, count, flat flame and a brief
localized caption never overlay the character. The full canvas has a semantic
color, with no dark scrim/panel. Completed state uses a white number with orange
contour and orange flame; unfinished states use coordinated light foregrounds.
The reference is the official [Duolingo widget article](https://blog.duolingo.com/widget-feature/).
HSK's selected panda is original generated art, not Duo's character.

`widget_streak_header.xml` and `widgetHeaderViews` are shared by the real widget
and Compose install preview. Bundled Nunito variable font uses explicit heavy
number/body weights; it is an open rounded alternative, not the proprietary
Duolingo font. Its OFL is bundled under `assets/licenses/`. Outline copies are
decorative and hidden from accessibility; the real counter has a localized
streak description. The transparent PNG atlas is framed/trimmed/scaled once into
three small cached bitmaps, retaining original aspect ratio and no background.

## Operational contract

- `WidgetRefreshBridge` requests the optional v1 context through a live Android bearer session; Room/ordinary maps cannot establish personal ownership. The store holds only a minimal progress projection and strict allowlisted context, never tokens, raw user/device IDs or lesson content.
- Installed snapshot fields retain defaults. Personal data is stored as a raw optional JSON element so an unsupported/malformed envelope cannot discard the older linked session. It renders neutral until a valid refresh.
- Request generation, link epoch, separately established opaque binding, preference revision and generated-time floors fence late/replayed frames. Acceptance holds the auth generation lock through the store write and rechecks expiry at durable acceptance. Foreground progress/course changes invalidate pending personal context before a live refresh.
- Logout clears the projection and rotates the epoch. Replacement sign-in clears old widget state **before** persisting new credentials, including the interrupted-write window. Token refresh does not relink the widget.
- Only verified daily learning XP is shown against a verified goal. Otherwise permitted lifetime XP/streak remain ordinary stats; reward counters cannot claim goal completion.
- Every tap uses the existing authenticated `CurrentLesson`/Course route and its fresh foundation/order/access checks. A cached suggestion never grants access, quota or identity.
- Glance renders cache only. Existing hourly WorkManager and clock invalidations are best effort; already drawn launcher pixels cannot be revoked at an exact deadline. No new scheduling interval or notification permission is introduced.
- Legacy opt-in study reminders remain separate pending the P4 server-claim protocol; passive projection does not enqueue/authorize another study send or change consent.
- Rollback can omit the optional server field or render neutral while preserving epoch/revision floors and OFF settings. Do not restore old fixed-hour urgency as personalization.

## QA commands

From `android/`:

```text
python3 tools/check_interface_fakes.py
python3 tools/check_named_arguments.py
python3 tools/check_flavor_parity.py
python3 tools/check_strings_translated.py
python3 tools/check_palette_matches_miniapp.py
./gradlew testPlayDebugUnitTest testDirectDebugUnitTest lintPlayDebug lintDirectDebug assemblePlayDebug assembleDirectDebug
```

`WidgetVisualStateTest` consumes all 36 shared semantic goldens; `WidgetPersonalContextTest` covers strict envelope decoding, live bridge/store races and passive Retrofit fields. Regenerate complete JVM envelopes with `python -m scripts.export_smart_widget_goldens --write` and verify with `--check`. `WidgetPersonalLayoutTest` renders personal copy at all existing sizes in UZ/RU/TJ and both themes; it is not launcher/installed acceptance. `WidgetArtTest` covers all 28 drawing/line mappings. The instrumentation tests cover 2x1, 2x2 and 4x2, UZ/RU/TJ, both themes, access/personal phases and retained legacy wording. They check actual visible text bounds and non-overlapping panda bounds. Screenshot output can use `-e widgetQaOutput UNIQUE_DIRECTORY` so a failed run cannot be mistaken for old successful pictures. `launcherFixture` can be run with `-e widgetFixture true` on an emulator for a real launcher placement pass.
