# HSK AI Li Panda onboarding — additional security/UX/data audit
**Date:** 2026-11-09. **Working branch:** `feature/li-onboarding-mainffbff9-20261108`. **PR:** #282 (draft). **Do not merge/deploy on this audit alone.**

## Uploaded video and deletion decision

- Latest user upload commit `65a6aafff5221391fe779d587f2a9dae83f01c2b` has **the exact same Git tree** (`412a7bf8226d13e8c404d8565e29508db444837c`) as its parent `e8a8ef71d2c491354e63cc0df580f7062e03d3f3`. **No additional video/blob/path exists to delete.** Avoid force-rewriting shared branch history just to remove an empty commit.
- Exact canonical video remains `app/static/assets/onboarding/iphone-home-screen.mp4`, **709,956 bytes**, Git blob SHA-1 `4c263a39cb0a6dba12a43379702ed3dd907d1d06`, local SHA-256 `727be15b30229aedffee780eab61ee781ef3727e9cd7bcf8af5aab6d99bacb8f`.
- Uploaded ZIP and temporary one-time import workflow are absent. Unrelated test fixture `tests/fixtures/admin_pwa_course_ad_test.mp4` is **not** a duplicate; keep it.
- The tutorial recording visually contains a truncated **`up.railway.app`** hostname in iPhone Safari Share UI. This might be a legacy or configured URL; **official production PWA hostname has not been proved**. Review before publishing as authoritative installation instruction.

## Confirmed issues and branch-only fixes

| Severity | Observed source-level defect | Applied change | Regression |
|---|---|---|---|
| HIGH | HSK 3.0 onboarding directly called `CourseTrackService.switch(...allow_locked_hsk30=True)` without checking per-user `access.allowed`. Content being live is not a payment entitlement. | `course_miniapp_onboarding_service.py` now checks `hsk30_access` before mutating the track; switches with bypass **off**. | `tests/test_course_miniapp_onboarding.py::test_locked_hsk30_onboarding_cannot_switch_or_persist` |
| HIGH | Trial expiration reminders could target an **already-paid** Pro account with an old unexpired `pro_trial_ends_at` column. | `trial_reminder_service.py` checks canonical `resolve_state(...)=TRIAL_ACTIVE` first. The PWA outbox already rechecks active trial before delivery. | `tests/test_trial_reminder_service.py::test_paid_pro_user_never_gets_a_stale_trial_expiry_notice` |
| HIGH | Query selected 200 accounts whose trial ends 48–72 hours later, starving a true T-48h notification. | SQL query now filters precise due 24h / 36–48h windows and orders by expiration. | `test_not_due_rows_cannot_starve_the_48_hour_batch` |
| HIGH | Even after due-window filtering, users beyond `MAX_BATCH=200` could be permanently starved by repeatedly scanning already-notified rows. | SQL uses correlated `NOT EXISTS` for the relevant one-time slot before applying LIMIT. Subsequent bounded runs reach next learners. | `test_large_due_cohort_drains_across_bounded_runs_without_duplicates` |
| MEDIUM | JS timeout raced only HTTP **headers**, so a server stalling on `response.json()` left the onboarding loader stuck. | `li-onboarding-runtime.js` races the entire fetched/validated JSON Promise against 12s GET / 20s POST deadline. | `tests/e2e/test_li_onboarding_runtime.py::test_partial_json_response_cannot_leave_loading_screen_stuck` |
| MEDIUM | A failed trial grant rendered a **Retry** action that actually skipped to the end. Repeated failures could append multiple error panels. | Real retry now calls `beginTrial`; separate free-course exit remains; prior error is removed before displaying a new one. | `test_trial_activation_denial_offers_real_retry_and_free_course` |
| LOW | Daily-time validation error claimed only 10/15/20/30 even though 5 minutes was already supported by DB and service. | Corrected error copy; no enum/DB change. | Existing course profile tests, backend CI |
| MEDIUM | Safari video route existed but had no real network-byte-range regression. | `tests/test_li_install_video_route.py` exercises the real FastAPI MP4 route at three byte ranges (206), and 200 full bytes. | New CI step |
| MEDIUM | Onboarding and install sheets had only Chromium synthetic coverage. | Added `PWA_E2E_ENGINE=webkit` execution for the same Li runtime and install tests **after** installing WebKit in CI. | New WebKit CI step |

## Related areas source-reviewed

- **PWA auth:** public 23-state Li HTML is presentation-only; private status/course/trial APIs verify cookie and server-owned actor. POSTs require same-origin and CSRF. OAuth return may adopt guest draft only when browser-local handoff proof exists; real Google/Telegram callback must still be checked end-to-end.
- **Telegram Mini App:** server uses signed initData, not the untrusted `initDataUnsafe.user.id` for mutations. User-facing local key uses unsafe ID **only as a draft name**, never an authorization check.
- **HSK course:** HSK 2.0 progress remains owned by course engine; a locked HSK 3.0 level cannot become an entitlement merely through onboarding. No new client-trusted lesson flags added.
- **Trial/billing:** only `ProTrialService.start` grants the trial, with anti-abuse checks and single-use row locking; Li view uses this server endpoint. Android/Google Play payment restrictions are outside this change.
- **Push:** PWA opt-in subscription + configured VAPID sender required. Existing outbox/source record provides dedupe; accepted provider HTTP is **not** proof a device displayed the push. A delayed outbox notification is cancelled if the trial is no longer active.
- **Daily plan/streak:** new multi-goals are additive and old scalar profiles default to one goal. Streak target is aspirational only; Smart Reminder context read is not an opt-in switch.
- **Video UX:** fixed-path MP4, no user-controlled URL, controlled inline player, no autoplay, 3-language textual fallback, correct `preload=metadata` and `playsinline`. **Actual iPhone device playback still unverified.**
- **Database:** additive migration `0154` preserves old rows; original XP/streak and old course plan remain immutable from onboarding. Production migration not applied here.

## Residual release blockers (NOT yet verified)

1. **No real iPhone Safari/Web Push device run:** WebKit CI helps catch browser incompatibility but is not identical to physical iOS Safari or real push permission. Verify Home Screen setup, video seek/range on slow throttled data, audio and offline text fallback.
2. **Production flags not observed:** `PWA_AUTH_ENABLED`, `PWA_PUSH_ENABLED`, `PWA_PUSH_SEND_ENABLED`, VAPID material and scheduler cadence must be checked in the real environment before promising a T-48h notification.
3. **Official URL in video:** confirm the recording's `up.railway.app` address is the desired official PWA; if not, replace or review the recording before shipping. Do not instruct users to install from an obsolete domain.
4. **End-to-end OAuth providers:** real Google/Telegram redirect and cookie lifecycle on physical iPhone and Mini App signed initData are not proven by mock Playwright provider responses alone.
5. **23-state visual QA:** no complete screenshot/VoiceOver/keyboard/safe-area audit at all screen sizes. Old default onboarding is still in place; Li routes remain previews.
6. **CSP:** Li page currently needs inline JS/event handlers and allows `unsafe-inline` in `script-src`. No user-provided text is directly rendered by this script, but tightening CSP to nonces or external static handlers is a separate security hardening task before promotion to main.
7. **Partial delivery failures:** Telegram/Android trial notifications persist a dedupe record before transport to avoid duplicates; a transient send failure may not automatically retry. PWA outbox has explicit retries. Review desired semantics and telemetry before changing the shared notice service.
8. **Production DB and Cloudflare:** No applied production migration or measured CDN/network performance; route test/CI and 710 KB video size are not substitutes for deployment verification.
9. **CI:** Latest feature head triggered fresh Actions on every commit; treat statuses as **pending** until the final head's targeted, WebKit, i18n, Smart Reminder and native PostgreSQL checks complete successfully.

## Required before approving PR #282

No force push, merge, production deploy or real payment is authorized by this audit. Run the final head's targeted tests, test the optional MP4 route and Safari WebKit suite, inspect screenshots and run the first-login/new/returning, 3-language, locked HSK3, trial-used and revoked-trial matrix on real test accounts. Update `IMPLEMENTATION_CONTEXT.md` with exact CI run IDs and evidence before marking ready.
