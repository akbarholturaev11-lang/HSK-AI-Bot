# iPhone PWA functional audit — 2026-11-04

**Repository:** `akbarholturaev11-lang/HSK-AI-Bot`. **Baseline:** `main` on 2026-11-04. **Patch branch:** `codex/iphone-pwa-navigation-audit-20261104`.

**Scope and evidence boundary.** This is a source audit of the real learner PWA, not an iOS device test. There is no authenticated production browser/iPhone, user session, server logs, or measured network waterfall in this run. Therefore **no screen is marked runtime PASS**, and no fabricated timing or "fixed on iPhone" statement is valid. Execute the test matrix below on an installed iPhone PWA with a QA account, 4G and throttled network before approving the PR. Avoid modifying production user entitlements to test.

## Confirmed source issues and initial fixes

| ID | Severity | Finding / evidence | Action in branch | Proof still needed |
|---|---|---|---|---|
| PWA-01 | P1 | `GET /iphone-pwa` served `iphone-pwa-login.html` even for a verified session; the JS then checked `/api/v3/pwa-auth/session` and navigated. Returning users saw a welcome flash. | Server verifies HttpOnly PWA session cookie and redirects to `/iphone-pwa/course` **before login HTML** for valid accounts; anonymous/expired remain on login. | Auth integration test and device cold-launch comparison |
| PWA-02 | P1 | `refreshCourseProgress` excluded browser PWA when `INIT_DATA` was empty, despite browser-scoped `_fetchCourseMap` existing. | Permit verified PWA actor path in progress refresh; preserve in-flight guard and old Telegram path. | Finish lesson, purchase, switch HSK level and compare server progress after return |
| PWA-03 | P1 | iOS BFCache `pageshow` map refresh skipped browser PWA entirely; `CHECKOUT_NAVIGATING` remained true on restored Course page. | Reset checkout guard; allow CSRF-protected browser map refresh when BFCache restores, refuse failed responses. | Swipe Safari back after pending/rejected/approved purchase; simulate offline resume |
| PWA-04 | P2 | On entering Practice, background preloading eagerly instantiated two iframes (dictionary + phrasebook), competing for network and main thread. | Disable invisible warm-up **only for PWA**, keep on-demand `RESOURCE.open` and existing Telegram preloads. | Record peak requests, first-input latency, cold dictionary open |
| PWA-05 | P2 | Checkout HTML loads blocking Telegram SDK from `telegram.org`, independent of learner origin and slow-network cache. | Use same-origin version already served for Course V3. | Browser checkout/Telegram Mini App compatibility and offline CDN failure |
| PWA-06 | P1 | Checkout Return always replaced Course, forcing a fresh 700KB+ HTML and script navigation even when a safe BFCache history entry existed. | Use a verified short-lived same-tab return nonce (`Referrer-Policy:no-referrer` prevents trusting `document.referrer`) then `history.back()`; fallback reload for direct/Telegram checkout. | iPhone BFCache return and blocked/approved payment transitions |
| PWA-07 | P1 | PWA daily goal previously returned null without Telegram initData, so Settings could not persist the user's choice. | Reuse canonical preferences service behind `/api/v3/pwa/preferences`, with validated browser session + CSRF; revert goal in UI on server failure. | Integration test and persisted cross-device goal verification |
| PWA-08 | P2 | Inbox had course/account tab split in a small modal, and swipe-back did not understand it. | One chronological course/account/payment feed, full-screen safe-area view; support NavBack and restore focus. | Browser notice behavior and real iOS swipe QA |
| PWA-09 | P2 | PWA Settings opened as a bottom sheet; its original Telegram notification toggle had no browser save endpoint. | Full-screen PWA Settings, nested pickers remain sheets; hide nonfunctional Telegram-only toggle while retaining real iPhone push settings. | Mobile layout and push permission QA |
| PWA-10 | P2 | Course tab did expensive synchronous SVG geometry before the first paint. | For PWA only defer trail drawing through two animation frames; Telegram path unchanged. | Measure long tasks and animation correctness on slow device |

## Screen-by-screen source review and runtime test matrix

Status **NEEDS DEVICE QA** means code path identified but not exercised on a real authenticated iPhone. For each case record open, close, edge-swipe, browser back, keyboard, unexpected redirects, stale data, errors, main-thread long tasks, and response latency.

| # | Section | Existing implementation / code path | Risk and required QA | Status |
|---|---|---|---|---|
| 1 | Installed PWA cold launch and effect | `GET /iphone-pwa` → `course-v3.html` and `finishHskLaunchSplash` | Returning account must skip login welcome but **preserve course splash**; first-time logged-out keeps login | NEEDS DEVICE QA |
| 2 | OAuth and Telegram sign-in | `iphone-pwa-login.js`, `/api/v3/pwa-auth/*` | Google/Apple/Telegram proof, app↔browser return, canceled OAuth, cookie ownership | NEEDS DEVICE QA |
| 3 | Main tabs and swipe back | `App.show`, `NavBack` in `course-v3.html` | repeated switches, nested overlays, swipe vs tap consistency, per-screen scroll restoration | NEEDS DEVICE QA |
| 4 | Checkout entry/exit | `App.goPay`, `subscription.html` and `returnToCourseFromCheckout` | history restores Course for verified referrer; direct checkout still full navigation | **SOURCE FIXES PWA-02/03/05/06**; DEVICE QA |
| 5 | Payment pending/rejected/approved | `/api/v3/pwa/subscription/*` | never grant Pro before server decision, rejected retry returns correct plan and notice | NEEDS DEVICE QA |
| 6 | Course map and progress | `renderCourse`, `drawTrails`, `refreshCourseProgress` | deferred geometry and map refresh; measure actual long-task improvement | **SOURCE FIXES PWA-02/10**, DEVICE QA |
| 7 | Start, pause, finish lesson | `openLessonSheet`, `startLesson`, `Flow`, `exitFlow` | no lost resume/proof, no double XP, correct accessibility/back confirmation | NEEDS DEVICE QA |
| 8 | HSK 2.0↔3.0, HSK 1–4 | `courseTrackStatus`, `requestCourseTrackSwitch`, `loadLevel` | access gate, level switch and plan refresh, stale maps while a request is in flight | NEEDS DEVICE QA |
| 9 | Practice hub | `App.show("mashq")`, `renderMashq` | first paint and hidden network preloads; preserves server access gate | **SOURCE FIX PWA-04**, DEVICE QA |
| 10 | Dictionary | `RESOURCE.open("dict")`, `hsk-lugat.html` iframe | on-demand load/close/back; stroke modal, horizontal filters, iframe gesture | NEEDS DEVICE QA |
| 11 | Phrasebook | `RESOURCE.open("phrases")`, `hsk-gaplar.html` iframe | independent HTML parser, memory, iframe swipe and no repeated data downloads | NEEDS DEVICE QA |
| 12 | Recognition | `/iphone-pwa/practice/recognition` | separate protected page, session, return to original tab, quota | NEEDS DEVICE QA |
| 13 | Pronunciation | `/iphone-pwa/practice/pronunciation` | iOS mic permission, recording/playback, repeat/exit, quota | NEEDS DEVICE QA |
| 14 | Memorize | `/iphone-pwa/practice/memorize` | large bundle, persisted cards, back, network absence and quota | NEEDS DEVICE QA |
| 15 | My mistakes | `/iphone-pwa/practice/mistakes` | secure account-owned errors, empty state, start/review/exit, scored completion | NEEDS DEVICE QA |
| 16 | HSK test | `/iphone-pwa/practice/test` | question reload, scoring, plan gate, return to course | NEEDS DEVICE QA |
| 17 | AI Voice text + turn audio | `VOICE` and `/api/v3/pwa/voice/session/*` | verify microphone and text, session begin/end; no Telegram-specific mic copy | NEEDS DEVICE QA |
| 18 | **AI Live voice** | `pwa_voice_start` explicitly returns `live_available=False` | **NOT IMPLEMENTED for PWA**; needs separately authenticated Live RTC design, not just UI enablement | BLOCKED — IMPLEMENTATION REQUIRED |
| 19 | Rating/leaderboard/users | `renderRating`, `loadLatestRating`, `loadReferrals`, `upov` | server fetched on visible tab, friends/users, profile overlays/back and slow network | NEEDS DEVICE QA |
| 20 | Profile and Settings | `renderProfile`, `settingsSheetHtml`, `App.openSettings` | full-screen Settings and secure daily-goal persistence added; Google/Apple linking and Telegram-derived avatar still need dedicated PWA UI | **PARTIALLY PATCHED PWA-07/09**, DEVICE QA |
| 21 | Inbox | `iphone-pwa-notices.js` + `iphone-pwa-glass.css` | combined notices/receipts, no tabs, full-screen and NavBack registration added | **SOURCE PATCH PWA-08**, DEVICE QA |
| 22 | Push permissions | `HskPwaInbox.openPushSettings`, `/api/v3/pwa/push/*` | installed iPhone only, user gesture, correct revoke; no automatic OS consent | NEEDS DEVICE QA |
| 23 | Receipt/account/lesson push | `PaymentNotifyService`, `CourseNotificationService`, `learner_pwa_push.py` | enqueues existing events; sending additionally needs VAPID/settings/worker; generic lock-screen text intentional for privacy | NEEDS SERVER + DEVICE QA |
| 24 | Discounts, bot block, account block | `NotificationDeliveryService`, user access state | clarify per-event routing; blocked accounts are deliberately excluded from delivery; don't bypass restrictions | POLICY / IMPLEMENTATION QA |

## Load/performance measurement protocol (not measured in this audit)

- Test on installed iOS standalone PWA with **cold cache and warm cache**, fast Wi-Fi and throttled 400 kbps / 400 ms RTT (or equivalent); record device/iOS version, build SHA, clock time and region.
- Measure `navigationStart → first visible interaction`, tab-switch tap → first paint, lesson/practice open/close, checkout back → first responsive tap, map/API duration, amount of JS/CSS/iframe loaded; record 5 trials, report **median and p95**.
- Suggested initial **acceptance targets, not observed results**: cached tab first response within 250 ms, modal back first response within 250 ms, returning from checkout first usable paint within 2.5 s on decent 4G, no unresponsive long task ≥500 ms during swipe/back. Under throttled connectivity measure and report outliers separately, don't mask with spinner or fabricate success.
- For each request record resource URL, start/end, duration, response code, transfer bytes, cache state, retry count; distinguish server latency from main-thread layout and redundant request load.
- Confirm first-run opt-in notifications **never** request system permission without a button press and that notification clicks open only authenticated user-scoped notices.

## Release gate

1. **Before merge:** run `python -m unittest tests.test_iphone_pwa_navigation_contract`, targeted `tests.test_pwa_browser_auth`, existing `tests.test_miniapp_request_load`, `node tests/test_pwa_notices_ui.js`, iOS viewport/browser E2E, localization guard. Review failed tests; never change tests merely to hide regressions.
2. **Security invariants:** PWA cookie and CSRF remain server-verified; no Telegram initData forgery, no premium access bypass, no misleading notification proof, no cross-user cache visibility, no new duplicated user XP.
3. **After merge only:** staging/release QA on real installed iPhone and actual production-like push service; compare the measured timings against the baseline.

**Priority next:** P1 real iPhone checkout back perf and freeze; P1 all-screen navigation/back regression; P1 verify Settings API on staging; P2 verify unified full-screen Inbox and push delivery; P2 Live voice independent design; P2 provider identity/avatar UI and Telegram-only text cleanup; P2 event-specific push classification with privacy and blocked-account policy.

**Syntax review:** V8 parsed the modified Inbox JS and inline Course/Checkout scripts with no syntax errors. This is not execution, correctness or iOS performance proof.


## Follow-up findings, 2026-11-05

**CI correction:** Prior PR #262 runs found a return-path assertion still expecting HTTP 200 for authenticated `/iphone-pwa`, and review-source hashes/anchors made stale by added HTML lines. The verified redirect test is now explicitly HTTP 303, all 9454 original source line positions preserved, and the exact reviewed SHA plus new storage-key inventory are maintained. CI status must be checked on the newest commit, not older canceled runs.

**PWA Web Push 422 root-cause candidate strongly supported by source:** Web standard `PushSubscription.toJSON()` may include `expirationTime:null`, while the server's `SubscribeRequest` sets Pydantic `extra="forbid"` and only allows `endpoint`/`keys`. The original client posted `subscription.toJSON()` unmodified. Production Railway HTTP logs contained one `/api/v3/pwa/push/subscribe` HTTP 422; its request body was not available, so the precise cause of that historical request cannot be proven. Client now sends only `endpoint` and `keys.{p256dh,auth}`, retaining strict server validation. The JS smoke harness now simulates Safari's extra `expirationTime` and rejects forwarding it. iOS user opt-in, VAPID settings, Apple's 201/202 provider acceptance and lock-screen delivery must still be verified end-to-end.

**Browser-only Telegram copy:** AI Voice now reuses the already-authored UZ/RU/TJ `pronunciation.micDeny` localized message (neutral microphone permission), not its Telegram-specific settings text. Unsupported PWA avatar editing is hidden rather than directing learners to their Telegram profile. The linked canonical user account and real avatar are never deleted or rewritten by this UI-only change. Linked identity management and other Telegram-specific flows require separate account-level design.

**QA-only client profiler:** `/iphone-pwa/course?pwa_perf=1` loads `iphone-pwa-perf.js` and makes `window.HskPwaPerf.snapshot()` available locally. It captures bounded tab handler/paint, long tasks and coarse same-origin resource timings, dropping URL query strings, all IDs and auth state; it never sends telemetry. It is disabled on normal navigation. No iOS measurements have been performed with it yet.

**Observed baseline from Railway HTTP proxy (sample, 2026-11-04, up to 500 recent records):**

| Endpoint | n | Proxy median (approximately ms, transport only) |
|---|---:|---:|
| `/api/v3/pwa/map` | 6 | 92 |
| `/iphone-pwa/course` | 6 | 46 |
| `/api/v3/pwa/notifications` | 10 | 20 |
| `/api/v3/pwa/account-notices` | 10 | 21 |
| `/api/v3/pwa/subscription/overview` | 1 | 221 |

These are not iPhone first-paint, RTT, JS parse, media, layout, page freeze or true user-visible load times. Do not infer frontend speed from them, particularly with n=1 for checkout. The observed rejected push subscribe was one request, not a confirmed universal failure.
