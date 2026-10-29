# Android Smart Widget

Native Android home-screen widget for HSK AI. It is a Glance widget owned by the Android APK; it never opens Telegram or the Mini App.

## Change points

| Need | File | Edit |
| --- | --- | --- |
| Refresh/reminder/stale times | `android/app/src/main/java/com/pomp/hskai/widget/WidgetPolicy.kt` | Change the constant, then increment `SCHEDULE_VERSION` when the schedule changes. Shared semantic validity is defined by the server; the renderer adds no clock thresholds. |
| When the panda is calm, bored, worried or relieved | `android/app/src/main/java/com/pomp/hskai/widget/WidgetVisualState.kt` | `WidgetVisualResolver` is the only engine that produces a state. Nothing else decides art. |
| Which drawing and which line a state shows | `android/app/src/main/java/com/pomp/hskai/widget/WidgetArt.kt` | One table, 28 rows. Adding art is a row; the wording stays in resources. |
| Link/stale/foundation behaviour | `android/app/src/main/java/com/pomp/hskai/widget/WidgetState.kt` | `WidgetStateResolver.resolve` answers access and freshness only, never mood. |
| Reminder wording variants | `android/app/src/main/res/values*/strings.xml` (`notify_*_body*`) + `StudyNotifications.bodies` | Add the body in all three languages and to the list; `WidgetPolicy.REMINDER_VARIANTS` says how many are rotated. |
| Widget copy | `localization/android/main/values*/widget_personal.xml` | Author new personal labels in all three canonical bundles and regenerate. Frozen legacy resources stay byte-identical. |
| Panda artwork | `android/app/src/main/res/drawable-nodpi/widget_panda_*.webp` | Replace a drawing without changing state or layout code. |
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
The existing 28 art assets and deterministic FNV variants remain available; the
passive personal resolver does not produce the old urgent art families.

## 28 ta rasm va deterministik tanlov

Har holatning o‘z rasm oilasi bor: `M01–M03`, `D01–D03`, `W01–W04`,
`E01–E04`, `L01–L04`, `C01–C05`, `OK01–OK05` — jami 28 ta, `drawable-nodpi`
ichida 512px WebP (hammasi ~500 KB).

Yangi rasm qo‘yayotganda ikki narsaga qarang: **kayfiyat** holatga mos
keladimi, va **rasmdagi yorug‘lik** holatning soatiga mos keladimi. Tunggi
osmon `DAY` da turgani kayfiyat to‘g‘ri bo‘lsa ham xatodek ko‘rinadi.

Variant tasodifiy emas. Widget yangilanishi OS tomonidan kechiktirilishi mumkin; tasodifiy tanlov pandani
miltillatardi. Shuning uchun:

```
variant = FNV-1a(epoch + "|" + mahalliy sana + "|" + holat) % holat.variants
```

- bir kun + bir holat → **doim bir xil rasm**
- holat o‘zgarsa → rasm o‘zgarishi mumkin
- yangi mahalliy kun → rasm o‘zgarishi mumkin

`epoch` — `WidgetSession.epoch`, ya’ni qurilma ulanganda o‘zi uchun yaratgan
UUID. Widget xotirasiga **hech qanday foydalanuvchi ID qo‘shilmagan**. FNV-1a
qo‘lda yozilgan, chunki `String.hashCode` barqaror deb va’da qilinmagan va
process qayta ishga tushganda o‘zgargan rasm xatodek ko‘rinardi.

Matn rasm ichida emas: har variant o‘z string resursiga ulangan
(`widget_morning_01` … `widget_completed_05`, `widget_milestone`), uchchala
tilda ham to‘liq.

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

`WidgetVisualStateTest` consumes all 31 shared semantic goldens; `WidgetPersonalContextTest` covers strict envelope decoding, live bridge/store races and passive Retrofit fields. Regenerate complete JVM envelopes with `python -m scripts.export_smart_widget_goldens --write` and verify with `--check`. `WidgetPersonalLayoutTest` renders personal copy at all existing sizes in UZ/RU/TJ and both themes; it is not launcher/installed acceptance. `WidgetArtTest` covers all 28 drawing/line mappings. The instrumentation test `WidgetLayoutTest` covers 2x1, 2x2 and 4x2 sizes, UZ/RU/TJ, light/dark, every access state and all 28 variants. `launcherFixture` can be run with `-e widgetFixture true` on an emulator for a real launcher placement pass.
