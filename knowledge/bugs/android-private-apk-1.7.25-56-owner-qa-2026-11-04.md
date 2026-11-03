# Android 1.7.25 (56) — owner-only test APK: bug audit and phone findings

**Recorded:** 2026-11-04  
**Status:** CONFIRMED install-preview crash reproduced and fixed; bounded auth/locale fixes and private replacement **1.7.26/57** passed the automated/owned-emulator checks recorded below. Actual owner-device/provider acceptance remains open.
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

These observations are not interchangeable with a confirmed root cause. The initial audit lacked the widget stack; the follow-up below now records an independently reproduced install-preview crash, without claiming a collected physical-phone stack.

## Source-backed findings / bug candidates (against this build)

| ID | Class | Code location and factual finding | Status / impact |
| --- | --- | --- | --- |
| AUTH-01 | **Confirmed error-handling defect** | `android/app/src/main/java/com/pomp/hskai/feature/auth/LinkScreen.kt:104-119,575-586`: `openCustomTab` and `openTelegram` swallow `startActivity`/Custom Tab launch failures via `runCatching`; the screen *always* calls `onBrowserUrlOpened()` / `onTelegramUrlOpened()`, consuming the one-shot URL even when launch failed. | Definite broken failure path; not established as cause of the observed post-login browser behavior. |
| AUTH-02 | **Navigation hypothesis, needs device reproduction** | `LinkScreen.kt:575-580` adds `FLAG_ACTIVITY_NEW_TASK` to a Custom Tab. Backend `app/api/native_oauth.py:167-188,362-390` returns `pomp-hsk-ai://oauth-return`, while `MainActivity.kt:190-221` ignores auth-return as a destination and login success comes from polling. No explicit browser-tab dismissal is implemented. | Browser/task transition merits test; **not** proof that `NEW_TASK` causes a bug on the physical phone. |
| AUTH-03 | **Process-death resilience gap** | `feature/auth/LinkViewModel.kt:21-65,234-304`: active `PendingLink`/polling is held in ViewModel/StateFlow rather than persisted via SavedStateHandle or durable state. | If Android kills the app process while outside in Telegram/browser, the in-flight attempt cannot be restored by this ViewModel. Distinct from an ordinary Activity recreation. |
| AUTH-04 | **Expected lifecycle behavior, not automatically a defect** | `MainActivity.kt:327-333`, `core/i18n/AppLocale.kt:46-57`: after authenticated account language differs, `activity.recreate()` is deliberately invoked. | Can explain the apparent restart; **do not** label it crash without logs. Check whether it happens repeatedly / loses navigation. |
| WIDGET-01 | **Event-timing race candidate** | `widget/WidgetInstallPromptScreen.kt:152-158`: `HskAiWidgetReceiver.placements.drop(1)` skips the StateFlow's first observed value. If placement happens before subscription, that value can already contain the new placement, so the event is missed. An ON_RESUME installed check exists as backup. | Can miss immediate success UI; **not** demonstrated as cause of launcher crash. |
| WIDGET-02 | **Uncaught crash paths, root cause unconfirmed** | `widget/HskAiSmartWidget.kt:183-199`: `HskAiWidgetReceiver.onUpdate` calls WorkManager and WidgetScheduler without a local exception boundary. `widget/WidgetPandaArt.kt:78-103`: first render decodes/crops all 36 sprites without explicit decoder-null/memory fallback. | These are inspection targets, **not confirmed Xiaomi exceptions**. Obtain `AndroidRuntime/FATAL EXCEPTION` stack trace before choosing a fix. |
| NOTIF-01 | **Audit correction: intentional pending-OFF support** | The existing switch remains usable during a pending ON so the owner can immediately turn it OFF. D29 uses sequence-bound UI state and durable latest-intent / UUID-revision / epoch fences in `SmartPreferenceBridge`. | Do not disable it with `isSavingNotifications`: that would regress immediate OFF. Existing bridge race and `pendingStudyOnCanStillBeTurnedOffUsingTheExistingSwitch` checks cover the intended behavior. |

## Smart Reminder: confirmed distinction, not a source-code bug

- Profile → Settings → Notifications exposes the phone's **study notification** switch (`ProfileScreen.kt:883-893,945-958`); it writes *device-specific intent* through `MainActivity.kt:610-645` and `core/notify/SmartPreferenceBridge.kt`. It is **not** an independently named global Smart Reminder activation switch.
- Backend defaults `SMART_REMINDER_ENABLED=False`, `SMART_REMINDER_TELEGRAM_ENABLED=False`, `SMART_REMINDER_ANALYSIS_ENABLED=False` (`app/config.py:113-119`). `app/services/smart_reminder_runtime.py:176-188` will not construct an active runtime until explicitly enabled. These are **source defaults**; production variable values require independent verification.
- The private APK does not imply activation of server routing, delivery, cohorts or A/B.

## Required confirmation before marking any phone symptom fixed

- [ ] **Google:** On owner phone, sign in successfully; check Custom Tab → callback → app foreground transition and back stack; inspect whether the browser returns unexpectedly.
- [ ] **Telegram:** Repeat sign-in; distinguish normal locale-driven `Activity.recreate()` from process death / crash. Verify account/session persistence and return path.
- [x] **Widget source defect:** Independently reproduce the full install-prompt failure and add a regression; exact exception and consumer are recorded below.
- [ ] **Widget phone acceptance:** With the replacement APK, verify prompt → pin request → placement/render on the actual Xiaomi/HyperOS launcher. If a different failure remains, collect its stack when the owner is available; do not keep requesting currently unavailable crash text.
- [ ] **Notifications:** Test rapid toggles, denied Android notification permission, server master-OFF, device ON/OFF persistence and offline retry independently.
- [ ] Re-run native unit/instrumentation and real-device regression checks after code changes. No public release until expressly approved by owner.

**Audit boundary:** This file documents real code observations and owner-reported symptoms; it is **not** a claim that all five previously discussed candidates explain the phone failures. Recording the audit changes no source behavior, APK, production flag, or user setting.


## Follow-up from actual reproduction (2026-11-04)

### WIDGET-03 — confirmed install-screen crash

- **Sabab:** `PromptWidget` in `WidgetInstallPromptScreen.kt` passes shared Android `<shape>` gradient XML backgrounds to Compose `painterResource`. That loader supports vector/raster assets only. Opening the full install prompt—not merely rendering the Glance provider—throws `IllegalArgumentException: Only VectorDrawables and rasterized asset types are supported ex. PNG, JPG, WEBP` and crashes the main process.
- **Evidence:** the new actual `WidgetInstallPromptSmokeTest` reproduced `FATAL EXCEPTION: main` / `Process crashed` at `PromptWidget` on the owned API-36 fixture before the fix. Independently hosting the original normal signed 56 provider passed, showing why previous Glance/layout acceptance missed this separate Compose consumer. The owner's Xiaomi image confirms a real app crash; its exact device stack was not available, so do not claim that a physical stack was collected.
- **Fix:** draw the same Android gradient drawable into Compose's native canvas, preserving resource ownership/colors/corners and the original artwork. Consume the placements flow's first value too, checking actual provider IDs so a placement before subscription cannot be missed. Do not mask the failure with a broad receiver catch or claim the unproven OOM/WorkManager hypotheses were established.
- **Risk:** regression at another resource, locale, pin/return or installed host remains subject to the affected smoke/host checks and final signed APK verification.
- **Prevention:** CI includes the full install-prompt regression in both distributions. Keep the normal signed-provider host check distinct from this in-app preview. Private owner assets/frames remain outside Git.

### AUTH-01 / AUTH-02 — bounded handoff fix

The existing Activity is reused for browser/Telegram handoff; `NEW_TASK` is added only for a non-Activity context. Launch helpers report failure instead of consuming an unopened URL as success. A current-URL-bound VM callback stops that attempt, exposes the existing localized provider-unavailable error and permits retry; a stale failure cannot cancel another provider. Polling secrets remain in memory and existing late-token/account fences remain. Launcher failure/task-flag/real-screen callbacks have passed initial instrumentation; full flavor/signed and owner acceptance are recorded in the Master Plan when completed.

AUTH-03 remains a process-death resilience gap, not a confirmed explanation of this video; no new persisted polling secret is introduced. AUTH-04 retains recreation when the account language differs or the activity locale is unsupported. First login now skips the unnecessary rebuild when the Activity already uses the same supported account language; three instrumentation regressions cover matching RU, real language change and unknown-locale fallback. The owner currently cannot retrieve additional Redmi crash text; do not repeat that request while the confirmed preview defect can be fixed and verified locally.

### Current operations correction

D30 later explicitly authorized production server activation. The two startup/send variables were set true and successfully deployed; the existing Admin PWA Smart-study control stops new issuance/sends. This supersedes the earlier source-default/permission observation above, not individual OFF/consent. Current runtime admission is still restricted to reviewed accounts: a global startup switch does not prove all-user enrollment or real delivery. Private APK distribution remains separate.


## Verified private replacement and prevention

- Source: `dd8f9bc7acff4fdc602cac5869254402c8953b3a`; Master Plan §17.90 holds the execution evidence and remaining acceptance scope.
- Private replacement: `hsk-ai-1.7.26-57-direct-release.apk`, 11,382,752 bytes, SHA-256 `ee09cd8444813043c4f1cc6628d6bbfff5798323f6e0958bc111a9b15738d84a`; existing certificate, production package, non-debuggable and Firebase/resource checks passed. It supersedes 56 for testing; neither artifact was publicly published by this work.
- Automated acceptance: Direct/Play unit 657/606, both lints, affected instrumentation 34 per flavor; final-57 focused auth/locale/install-prompt/normal-signed-provider host 8 per flavor. Signed 57 offline cold start stays alive; crash buffers empty. The preview regression is explicitly included in both-flavor CI.
- Physical Google/Telegram return, Xiaomi pin/render and real notification delivery remain to be checked with the owner when available. Do not equate source/fixture acceptance with the absent phone trace or actual successful delivery. Process-death polling-secret persistence was not added.
