# Android Smart Widget

Native Android home-screen widget for HSK AI. It is a Glance widget owned by the Android APK; it never opens Telegram or the Mini App.

## Change points

| Need | File | Edit |
| --- | --- | --- |
| Refresh/reaction/reminder/stale times | `android/app/src/main/java/com/pomp/hskai/widget/WidgetPolicy.kt` | Change the constant, then increment `SCHEDULE_VERSION` when the schedule changes. The reaction rules live in `WidgetState.kt`. |
| Which face and which line the widget shows | `android/app/src/main/java/com/pomp/hskai/widget/WidgetState.kt` | `WidgetStateResolver.reaction` picks the art, `prompt` picks the line. Neither touches the layout, and the wording stays in resources. |
| Reminder wording variants | `android/app/src/main/res/values*/strings.xml` (`notify_*_body*`) + `StudyNotifications.bodies` | Add the body in all three languages and to the list; `WidgetPolicy.REMINDER_VARIANTS` says how many are rotated. |
| Widget copy | `android/app/src/main/res/values/widget_strings.xml`, `values-ru/widget_strings.xml`, `values-tg/widget_strings.xml` | Keep all three files in sync; the static translation check enforces this. |
| Panda artwork | `android/app/src/main/res/drawable/widget_panda_*.xml` | Replace a mood vector without changing state or layout code. |
| Responsive layout and mood mapping | `android/app/src/main/java/com/pomp/hskai/widget/HskAiSmartWidget.kt` | Layout only; server/course rules stay elsewhere. |
| Add-widget/reminder UI | `android/app/src/main/java/com/pomp/hskai/widget/WidgetSetupSheet.kt` | The reminder switch is local Android state and does not change Telegram notification preferences. |
| API event allowlist | `app/api/android_events.py` | Add an event to the Pydantic literal and the server model allowlist together. |

### Panda qachon nima deydi

Rasm ikki qatlamdan chiqadi. Avval **holat**, keyin **vaqt**:

1. `RISK_HOUR` (19:00) dan `NIGHT_HOUR` (22:00) gacha bugun hali bironta ham XP
   yo‘q bo‘lsa — `worried`. Streak bor bo‘lsa matn ham o‘zgaradi
   (`widget_streak_risk`).
2. 22:00 dan `DAWN_HOUR` (06:00) gacha — `sleepy`. Kechasi turtki bermaydi.
3. Bugungi maqsadning yarmi (`CHEER_PERCENT`) bajarilgan bo‘lsa — `cheer`.
4. Boshqa holatda: streak bor bo‘lsa `streak`, aks holda kunduzgi rotatsiya.

Kunduzgi rotatsiya avvalgidek: `WidgetReaction.DAYTIME_ROTATION` 09:00 dan
19:00 gacha 90 daqiqalik yettita slotga ulanadi — `calm`, `invite` (wave),
`thinking`, `focus`, `cheer`, `streak`, `celebrate`. Oynadan tashqarida `calm`.

Kirish holatlari (ulanmagan, eskirgan, asos, kun yopilgan) rasmni o‘zi
belgilaydi va progressga qaramaydi. Rasmni `drawable/widget_panda_*.xml` dan,
vaqtni `WidgetPolicy.kt` dan almashtiring; jadval o‘zgarsa
`SCHEDULE_VERSION`ni oshiring.

## Operational contract

- `WidgetSnapshot` contains only a small progress projection — including today's XP and the server's goal for today. Tokens, user IDs and lesson content never enter the widget store or launcher intent.
- New `WidgetSnapshot` fields must have a default. A cache written by an older build that no longer decodes is dropped, and a dropped cache tells a linked learner to link their account.
- A goal of `0` means "not known yet": the widget then shows the lifetime XP it used to show and claims nothing about today.
- Every widget/notification open gets an authenticated server access check in `MainActivity`; failures land on Course and do not auto-open a lesson later.
- `WidgetStore.epoch` changes on link/logout. A late network response from the previous account is ignored.
- Background refresh is hourly best effort. Android/WorkManager may delay it; exact minute changes are not promised.
- Local reminder is opt-in, checked from 20:00 onward, and `WidgetStore.remindOnce` caps delivery to one per local server day. It is separate from the widget's reactions; no morning/evening widget state is emitted.
- The reminder body rotates by local day (`ReminderDecision.variant`), so a retried worker cannot change the wording mid-evening, and it carries the matching panda face as the notification's large icon.
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
