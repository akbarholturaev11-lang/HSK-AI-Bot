# Android Smart Widget

Native Android home-screen widget for HSK AI. It is a Glance widget owned by the Android APK; it never opens Telegram or the Mini App.

## Change points

| Need | File | Edit |
| --- | --- | --- |
| Refresh/reaction/reminder/stale times | `android/app/src/main/java/com/pomp/hskai/widget/WidgetPolicy.kt` | Change the constant, then increment `SCHEDULE_VERSION` when the schedule changes. Seven daytime panda reactions are mapped in `WidgetState.kt`; outside the active window the neutral art remains. |
| Widget copy | `android/app/src/main/res/values/widget_strings.xml`, `values-ru/widget_strings.xml`, `values-tg/widget_strings.xml` | Keep all three files in sync; the static translation check enforces this. |
| Panda artwork | `android/app/src/main/res/drawable/widget_panda_*.xml` | Replace a mood vector without changing state or layout code. |
| Responsive layout and mood mapping | `android/app/src/main/java/com/pomp/hskai/widget/HskAiSmartWidget.kt` | Layout only; server/course rules stay elsewhere. |
| Add-widget/reminder UI | `android/app/src/main/java/com/pomp/hskai/widget/WidgetSetupSheet.kt` | The reminder switch is local Android state and does not change Telegram notification preferences. |
| API event allowlist | `app/api/android_events.py` | Add an event to the Pydantic literal and the server model allowlist together. |

### Yetti reaksiya sloti

`WidgetPolicy.kt` dagi 90 daqiqalik slotlar `WidgetState.kt` orqali quyidagi
rasmlarga ulanadi: 09:00 `calm`, 10:30 `invite` (wave), 12:00 `thinking`,
13:30 `focus`, 15:00 `cheer`, 16:30 `streak`, 18:00 `celebrate`. 09:00 dan oldin
yoki 19:00 dan keyin `calm` qaytadi. Rasmni `drawable/widget_panda_*.xml` dan,
vaqtni `WidgetPolicy.kt` dan almashtiring; jadval o‘zgarsa
`SCHEDULE_VERSION`ni oshiring.

## Operational contract

- `WidgetSnapshot` contains only a small progress projection. Tokens, user IDs and lesson content never enter the widget store or launcher intent.
- Every widget/notification open gets an authenticated server access check in `MainActivity`; failures land on Course and do not auto-open a lesson later.
- `WidgetStore.epoch` changes on link/logout. A late network response from the previous account is ignored.
- Background refresh is hourly best effort. Android/WorkManager may delay it; exact minute changes are not promised.
- Local reminder is opt-in, checked from 20:00 onward, and `WidgetStore.remindOnce` caps delivery to one per local server day. It is separate from the seven daytime panda reactions; no morning/evening widget state is emitted.
- Existing widget work is unique. `SCHEDULE_VERSION` plus `UPDATE` replaces policy safely without parallel workers.

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

The instrumentation test `WidgetLayoutTest` covers 2x1, 2x2 and 4x2 sizes, UZ/RU/TJ, light/dark and all mood states. `launcherFixture` can be run with `-e widgetFixture true` on an emulator for a real launcher placement pass.
