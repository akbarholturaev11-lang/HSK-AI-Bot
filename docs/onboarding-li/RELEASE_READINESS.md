# Li Panda onboarding — staged release verification (2026-11-09)

**Repository:** `akbarholturaev11-lang/HSK-AI-Bot`  
**Draft PR:** [#282](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/282)  
**Safety rule:** This checklist is not permission to deploy, merge, grant Pro, or change production settings.

## Source and merge baseline

- Updated the feature branch with a **two-parent merge commit** `a53774fdb0637e71b41b0887e4a71cd0466108ab`, using `main@8ff505b352f88c0155e9d390f04d1205669fa0d5` as second parent.
- Feature branch is **0 commits behind main** at this synchronization checkpoint. Main had only modified `AGENTS.md` and newly added `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`; unrelated feature files were not overwritten.
- New permanent analytics-impact obligations in `AGENTS.md` now apply to this onboarding release.

## Reversible initial entry — deliberately OFF

- `PWA_LI_ONBOARDING_ENTRY_ENABLED: bool = False` in `app/config.py`. It is independent of `PWA_AUTH_ENABLED`.
- When **OFF**, `GET /iphone-pwa` uses the original login page. Authenticated returning users go to `/iphone-pwa/course`; OAuth resume cookie behavior is unchanged.
- When **ON**, only unauthenticated or invalid-cookie requests to `GET /iphone-pwa` receive 303 to public `/iphone-pwa/onboarding/li`; server-authenticated users still go to the canonical course, or to Li only once for a valid OAuth resume hint.
- The public Li route is **visual presentation only**. Any profile/session/trial/payment action remains protected by signed session, same-origin and CSRF validation. The release switch does not grant access or turn on push.
- If a problem is observed, set `PWA_LI_ONBOARDING_ENTRY_ENABLED=false`. Do not revert data migrations or delete saved user preferences as a "rollback".
- The guest-only switch prepares a PWA cutover; it does **not** yet replace Telegram Mini App's default onboarding. A separate signed-initData route-owner decision is required for a full two-platform launch.

## Analytics Impact — source-backed

| Behavior | Writer and persistence | Consumer and limitation | Release impact |
|---|---|---|---|
| Completed onboarding | Server-side `CourseMiniAppOnboardingService.complete()` invokes `CourseMiniAppAnalyticsService.record_server_event` with `onboarding_completed`, canonical `user_id`, `source=course_onboarding`, and profile-specific dedupe key; persists `CourseMiniAppEvent`. | `pwa_analytics_learning.py` references `onboarding_completed`, but the existing cross-platform attribution/denominator has not been audited. | Reuses existing event; no invented conversions. |
| Anonymous Li welcome / step views | No authenticated identity at guest entry; an event must not fabricate a user or link an unverified visit to a payer. | PWA platform analytics includes `not_instrumented` cases. No verified guest-to-Pro funnel currently. | **Partial / unavailable** until an explicitly reviewed, privacy-safe platform/attempt funnel exists. |
| Route switch default OFF | No live UI behavior change until an operator enables the flag. | No new KPI can be inferred from the existence of the flag. | **Not applicable while disabled.** Document real exposure before activation. |
| Trial / payment / Pro | Canonical server trial service and existing payment/webhook writers remain authoritative. | Do not combine PWA Pro `pwa_pro_*`, Lava purchase and onboarding events without a validated join/attempt contract. | **No billing instrumentation change in this patch.** |

Do **not** report measured Li signup rate, onboarding completion rate, 48h push delivery rate, or PWA conversion when the necessary identity/coverage/denominator has not been verified. A future enabled rollout must explicitly recheck the Analytics Integrity plan and complete a supported coverage record or documented exemption.

## Required acceptance gates (not all complete)

- [x] Source changes from current `main` merged into feature branch, without force pushing or modifying `main`.
- [x] Release entry routing is **default disabled** with a focused PWA auth regression (guest, forged cookie, valid session, global auth kill switch).
- [ ] Latest feature HEAD's entire required CI set completes successfully, especially Backend targeted, localization source guards, WebKit onboarding, PostgreSQL migration, Smart Reminder, PWA navigation.
- [ ] Run **staging** `alembic upgrade head` to revision `0154_li_onboarding_choices`; confirm the two additive columns and constraint without modifying existing XP/streak/course progress. No production migration was performed.
- [ ] Real iPhone Safari: new signup, returning account, real Google and Telegram callback, screen installation, Home Screen standalone, 23-state layout, fast/slow/offline network, cancelled/failed API, VoiceOver and safe areas.
- [ ] Confirm the 709,956-byte approved MP4's **recorded URL** is the intended official PWA host (the video appears to show an `up.railway.app` hostname), then test actual iPhone Range/seek, playback and text fallback.
- [ ] Verify real production PWA auth configuration, and separate VAPID, push consent, scheduler and provider delivery before promising a 48-hour Web Push notice. Never auto-opt users in.
- [ ] Verify signed Telegram Mini App owner and separate Mini App route cutover plan. PWA-only flag does not silently affect it.
- [ ] The same install guide (intro → video, once per learner) is also opened by the Telegram Mini App → iPhone PWA one-time sign-in landing `/iphone-pwa/handoff` (PR #300), behind the Admin iPhone PWA promo switch. Its real-device QA is tracked in `docs/TELEGRAM_PWA_ANDROID_HANDOFF_CONTEXT.md`; the hostname check above applies to it too.
- [ ] Verify platform attribution/analytics coverage and do not interpret missing data as zero.
- [ ] Review staged rollout, monitoring and rollback. Explicit release authorization required before enabling the entry flag or shipping to main.

**Status:** code-only release preparation, not a completed real-device or production signoff.
