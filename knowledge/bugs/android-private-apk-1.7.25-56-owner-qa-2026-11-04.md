# Android 1.7.25 (56) — owner-only test APK: bug audit and phone findings

**Recorded:** 2026-11-04  
**Status:** OPEN — owner-device QA; no fix or new APK is asserted  
**Scope:** This note records issues against the exact *private Direct* test APK below; it does **not** authorize public R2/Play publication.

## Exact APK identity (do not confuse with Google Play or public Direct)

- File: `hsk-ai-1.7.25-56-direct-release.apk`
- Package: `com.pomp.hskai`; `versionName=1.7.25`, `versionCode=56`; signed, non-debuggable.
- Size: `11,382,752` bytes.
- **SHA-256:** `6ad6c0bb99cc0ac91c98d845173a2863273ae26c16e084cfab1f5fc2bcc30de8`
- Source acceptance: `870d479484c0c03fe56c1e44c17ba2d6eca4f5d0`; documented at `main@30b244c27fe294574143a6d2bd724ce2770f4ec0`, `docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md` §17.88.
- This APK was delivered for owner-only practical testing; the signed APK itself is outside Git and was **not** published through Actions/R2/Play. No production rollout/Smart routing was authorized.

## Owner-observed problems (physical phone, not reproduced by this source audit)

1. **AUTH:** After Google account sign-in, the browser comes back to foreground; Telegram login appears to close/reopen the app.
2. **WIDGET:** Attempting to place a home-screen widget closes/crashes the HSK AI app on the owner's Xiaomi/Redmi.
3. **REMINDER:** Owner cannot find a separate Smart Reminder activation control.

These observations are not interchangeable with a confirmed root cause. In particular, widget crash requires the crash stack trace from the exact signed APK.

## Source-backed findings / bug candidates (against this build)

| ID | Class | Code location and factual finding | Status / impact |
| --- | --- | --- | --- |
| AUTH-01 | **Confirmed error-handling defect** | `android/app/src/main/java/com/pomp/hskai/feature/auth/LinkScreen.kt:104-119,575-586`: `openCustomTab` and `openTelegram` swallow `startActivity`/Custom Tab launch failures via `runCatching`; the screen *always* calls `onBrowserUrlOpened()` / `onTelegramUrlOpened()`, consuming the one-shot URL even when launch failed. | Definite broken failure path; not established as cause of the observed post-login browser behavior. |
| AUTH-02 | **Navigation hypothesis, needs device reproduction** | `LinkScreen.kt:575-580` adds `FLAG_ACTIVITY_NEW_TASK` to a Custom Tab. Backend `app/api/native_oauth.py:167-188,362-390` returns `pomp-hsk-ai://oauth-return`, while `MainActivity.kt:190-221` ignores auth-return as a destination and login success comes from polling. No explicit browser-tab dismissal is implemented. | Browser/task transition merits test; **not** proof that `NEW_TASK` causes a bug on the physical phone. |
| AUTH-03 | **Process-death resilience gap** | `feature/auth/LinkViewModel.kt:21-65,234-304`: active `PendingLink`/polling is held in ViewModel/StateFlow rather than persisted via SavedStateHandle or durable state. | If Android kills the app process while outside in Telegram/browser, the in-flight attempt cannot be restored by this ViewModel. Distinct from an ordinary Activity recreation. |
| AUTH-04 | **Expected lifecycle behavior, not automatically a defect** | `MainActivity.kt:327-333`, `core/i18n/AppLocale.kt:46-57`: after authenticated account language differs, `activity.recreate()` is deliberately invoked. | Can explain the apparent restart; **do not** label it crash without logs. Check whether it happens repeatedly / loses navigation. |
| WIDGET-01 | **Event-timing race candidate** | `widget/WidgetInstallPromptScreen.kt:152-158`: `HskAiWidgetReceiver.placements.drop(1)` skips the StateFlow's first observed value. If placement happens before subscription, that value can already contain the new placement, so the event is missed. An ON_RESUME installed check exists as backup. | Can miss immediate success UI; **not** demonstrated as cause of launcher crash. |
| WIDGET-02 | **Uncaught crash paths, root cause unconfirmed** | `widget/HskAiSmartWidget.kt:183-199`: `HskAiWidgetReceiver.onUpdate` calls WorkManager and WidgetScheduler without a local exception boundary. `widget/WidgetPandaArt.kt:78-103`: first render decodes/crops all 36 sprites without explicit decoder-null/memory fallback. | These are inspection targets, **not confirmed Xiaomi exceptions**. Obtain `AndroidRuntime/FATAL EXCEPTION` stack trace before choosing a fix. |
| NOTIF-01 | **Confirmed UI state-guard defect** | `feature/profile/ProfileScreen.kt:945-955` notification toggle uses `enabled = !settings.isSavingLanguage` rather than `!settings.isSavingNotifications`; the latter is set during a pending study-notification write by `feature/profile/ProfileSettingsViewModel.kt:85-98`. | Repeated taps remain permitted while saving; potential overlapping writes and confusing switch state. |

## Smart Reminder: confirmed distinction, not a source-code bug

- Profile → Settings → Notifications exposes the phone's **study notification** switch (`ProfileScreen.kt:883-893,945-958`); it writes *device-specific intent* through `MainActivity.kt:610-645` and `core/notify/SmartPreferenceBridge.kt`. It is **not** an independently named global Smart Reminder activation switch.
- Backend defaults `SMART_REMINDER_ENABLED=False`, `SMART_REMINDER_TELEGRAM_ENABLED=False`, `SMART_REMINDER_ANALYSIS_ENABLED=False` (`app/config.py:113-119`). `app/services/smart_reminder_runtime.py:176-188` will not construct an active runtime until explicitly enabled. These are **source defaults**; production variable values require independent verification.
- The private APK does not imply activation of server routing, delivery, cohorts or A/B.

## Required confirmation before marking any phone symptom fixed

- [ ] **Google:** On owner phone, sign in successfully; check Custom Tab → callback → app foreground transition and back stack; inspect whether the browser returns unexpectedly.
- [ ] **Telegram:** Repeat sign-in; distinguish normal locale-driven `Activity.recreate()` from process death / crash. Verify account/session persistence and return path.
- [ ] **Widget:** Capture crash log from the exact `1.7.25/56` private APK (e.g. `adb logcat -b crash -d -v time` immediately after reproduction); inspect the exception's class, stack and process. Then reproduce pin request, host placement and render on the actual Xiaomi/HyperOS launcher.
- [ ] **Notifications:** Test rapid toggles, denied Android notification permission, server master-OFF, device ON/OFF persistence and offline retry independently.
- [ ] Re-run native unit/instrumentation and real-device regression checks after code changes. No public release until expressly approved by owner.

**Audit boundary:** This file documents real code observations and owner-reported symptoms; it is **not** a claim that all five previously discussed candidates explain the phone failures. Recording the audit changes no source behavior, APK, production flag, or user setting.
