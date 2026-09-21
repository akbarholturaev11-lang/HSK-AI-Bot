# Android Smart Widget

Native Android home-screen widget for HSK AI. It is a Glance widget owned by the Android APK; it never opens Telegram or the Mini App.

## Change points

| Need | File | Edit |
| --- | --- | --- |
| Refresh/reminder/stale times | `android/app/src/main/java/com/pomp/hskai/widget/WidgetPolicy.kt` | Change the constant, then increment `SCHEDULE_VERSION` when the schedule changes. The visual-state boundaries live in `WidgetVisualState.kt`. |
| When the panda is calm, bored, worried or relieved | `android/app/src/main/java/com/pomp/hskai/widget/WidgetVisualState.kt` | `WidgetVisualResolver` is the only engine that produces a state. Nothing else decides art. |
| Which drawing and which line a state shows | `android/app/src/main/java/com/pomp/hskai/widget/WidgetArt.kt` | One table, 28 rows. Adding art is a row; the wording stays in resources. |
| Link/stale/foundation behaviour | `android/app/src/main/java/com/pomp/hskai/widget/WidgetState.kt` | `WidgetStateResolver.resolve` answers access and freshness only, never mood. |
| Reminder wording variants | `android/app/src/main/res/values*/strings.xml` (`notify_*_body*`) + `StudyNotifications.bodies` | Add the body in all three languages and to the list; `WidgetPolicy.REMINDER_VARIANTS` says how many are rotated. |
| Widget copy | `android/app/src/main/res/values/widget_strings.xml`, `values-ru/widget_strings.xml`, `values-tg/widget_strings.xml` | Keep all three files in sync; the static translation check enforces this. |
| Panda artwork | `android/app/src/main/res/drawable-nodpi/widget_panda_*.webp` | Replace a drawing without changing state or layout code. |
| Responsive layout | `android/app/src/main/java/com/pomp/hskai/widget/HskAiSmartWidget.kt` | Layout only; state, art and copy selection stay elsewhere. |
| Add-widget/reminder UI | `android/app/src/main/java/com/pomp/hskai/widget/WidgetSetupSheet.kt` | The reminder switch is local Android state and does not change Telegram notification preferences. |
| API event allowlist | `app/api/android_events.py` | Add an event to the Pydantic literal and the server model allowlist together. |

## Panda qachon nima deydi

Bitta dvigatel bor — `WidgetVisualResolver`. U ikki narsani o‘qiydi:
foydalanuvchining **mahalliy vaqti** va **bugungi dars bajarilganmi**.

### Mahalliy vaqt bo‘yicha holatlar

| Vaqt (mahalliy) | Holat | Kayfiyat | Urgency | Variant |
| --- | --- | --- | --- | --- |
| 05:00–09:59 | `MORNING` | ijobiy, yumshoq | 0 | 3 |
| 10:00–13:59 | `DAY` | do‘stona, tayyor | 1 | 3 |
| 14:00–17:59 | `WAITING` | zerikkan, kutmoqda | 2 | 4 |
| 18:00–19:59 | `EVENING` | xafa, xavotirli | 3 | 4 |
| 20:00–21:59 | `LATE` | tashvishli, jiddiy | 4 | 4 |
| 22:00–23:59 | `CRITICAL` | vahima, oxirgi imkon | 5 | 5 |
| 00:00–04:59 | yangi kun oynasi → `MORNING` | ijobiy | 0 | 3 |
| bugun bajarilgan | `COMPLETED` | xursand, yengil | 0 | 5 |

00:00 da mahalliy kun yangilanadi. Kechagi `CRITICAL` yangi kunga o‘tmaydi:
soat 00:00–04:59 oynasi `MORNING` sifatida chiziladi.

Vaqt **UTC emas**, foydalanuvchining o‘z zonasida hisoblanadi
(`ZonedDateTime.hour`). Zona yoki soat o‘zgarsa `WidgetClockReceiver` qayta
chizadi.

### Ustuvorlik

```
SPECIAL  >  COMPLETED  >  TIME STATE
```

- `COMPLETED` **har doim** vaqt eskalatsiyasini bekor qiladi. 23:30 da dars
  bajarilgan bo‘lsa — `COMPLETED`, `CRITICAL` emas.
- `SPECIAL` (`WidgetSpecialKind`) — `MILESTONE`, `STREAK_BROKEN`, `COMEBACK`,
  `NEW_USER`, `SEASONAL`. Bulardan faqat `MILESTONE` da haqiqiy signal bor:
  kun yopilgan va serverdagi streak `7/30/50/100/365` ga tushgan. Qolgan
  to‘rttasi arxitekturada nom sifatida turadi — ularni chiqaradigan server
  yoki lokal maydon yo‘q, yo‘qini o‘ylab topish esa bosh ekranga yolg‘on
  yozish bo‘lardi.
- `UNLINKED`, `STALE`, `FOUNDATION` — bular kayfiyat emas, **kirish holati**
  (`WidgetAccess`). Ular alohida turadi va tinch bir rasmni vaqtincha oladi,
  chunki ular foydalanuvchining kuni haqida hech narsa demaydi.

### 28 ta rasm va deterministik tanlov

Har holatning o‘z rasm oilasi bor: `M01–M03`, `D01–D03`, `W01–W04`,
`E01–E04`, `L01–L04`, `C01–C05`, `OK01–OK05` — jami 28 ta.

Variant tasodifiy emas. Widget har soatda, har soat o‘zgarganda va launcher
qayta ishga tushganda qayta chiziladi; tasodifiy tanlov pandani
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

- `WidgetSnapshot` contains only a small progress projection — including today's XP and the server's goal for today. Tokens, user IDs and lesson content never enter the widget store or launcher intent.
- New `WidgetSnapshot` fields must have a default. A cache written by an older build that no longer decodes is dropped, and a dropped cache tells a linked learner to link their account.
- A goal of `0` means "not known yet": the widget then shows the lifetime XP it used to show and claims nothing about today.
- Every widget/notification open gets an authenticated server access check in `MainActivity`; failures land on Course and do not auto-open a lesson later.
- `WidgetStore.epoch` changes on link/logout. A late network response from the previous account is ignored, and the panda's variant may change with it.
- The widget renders from the local cache only. Glance never performs a network call; background refresh is hourly best effort and Android/WorkManager may delay it. A finished lesson reaches the widget through the existing snapshot publish, which re-renders immediately.
- Local reminder is opt-in, checked from 20:00 onward, and `WidgetStore.remindOnce` caps delivery to one per local server day. It is separate from the widget's visual state.
- The reminder body rotates by local day (`ReminderDecision.variant`), so a retried worker cannot change the wording mid-evening.
- Existing widget work is unique. `SCHEDULE_VERSION` plus `UPDATE` replaces policy safely without parallel workers.
- Streak is a display layer, not a state controller. It decides the milestone line and the stats line; it never replaces `MORNING`/`DAY`/`WAITING`/`EVENING`/`LATE`/`CRITICAL`.

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

`WidgetVisualStateTest` covers every local-hour boundary with the day finished and unfinished, the `COMPLETED` override, and deterministic variants. `WidgetArtTest` covers all 28 drawing/line mappings. The instrumentation test `WidgetLayoutTest` covers 2x1, 2x2 and 4x2 sizes, UZ/RU/TJ, light/dark, every access state and all 28 variants. `launcherFixture` can be run with `-e widgetFixture true` on an emulator for a real launcher placement pass.
