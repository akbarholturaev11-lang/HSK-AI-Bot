# PROJECT_MEMORY.md

## 1. Project Identity

Project name: Unknown / needs inspection  
Project type: Telegram Bot / Mini App / Website / Backend / Other  
Main purpose: Unknown / needs inspection  
Target users: Unknown / needs inspection  
Current status: Unknown / needs inspection  

Short description:
- This project is built to: Unknown / needs inspection
- Main user problem: Unknown / needs inspection
- Main business goal: Unknown / needs inspection

---

## 2. Core Architecture

Frontend:
- Unknown / needs inspection

Backend:
- Unknown / needs inspection

Database:
- Unknown / needs inspection

Hosting:
- Unknown / needs inspection

Bot framework:
- Unknown / needs inspection

AI provider/model:
- Unknown / needs inspection

Payment system:
- Unknown / needs inspection

External services:
- Unknown / needs inspection

---

## 3. Important Project Rules

- Do not redesign the whole architecture without explicit request.
- Do not remove working logic unless there is a clear reason.
- Make minimal safe changes.
- Keep user/payment/subscription logic stable.
- If database schema changes, document the migration.
- If environment variables change, update `.env.example`.
- Never write secrets, API keys, tokens, passwords, or private URLs in this file.
- Before changing payment, subscription, or access logic, check the current flow first.
- If something is unclear, inspect the code first instead of guessing.

---

## 4. Memory Update Policy

This file is NOT a daily diary and must NOT become a dump of every small change.

Only update this file when the change is important for future AI assistants to understand, debug, or safely continue the project.

Update this file only for:
- Architecture changes
- Database schema changes
- Payment logic changes
- Subscription logic changes
- User access logic changes
- Important user flow changes
- Deployment or environment changes
- AI prompt behavior changes
- Course or lesson logic changes
- Important business logic decisions
- Major bug fixes
- Security-sensitive changes

Do NOT update this file for:
- Small text edits
- Emoji changes
- Typo fixes
- Minor UI/CSS changes
- Console log cleanup
- Small refactoring with no logic change
- Temporary experiments
- Changes already obvious from the code

Before updating memory, ask internally:

> Will this help another AI assistant understand, debug, or safely continue this project later?

If the answer is no, do not update this file.

When updating memory, keep it short and useful:
- What changed
- Why it changed
- Files touched
- Risk / follow-up if needed

Never turn this file into a long changelog.

---

## 5. Key Files and Folders

Main files:
- `main.py` — Unknown / needs inspection
- `bot.py` — Unknown / needs inspection
- `database.py` — Unknown / needs inspection
- `config.py` — Unknown / needs inspection
- `handlers/` — Unknown / needs inspection
- `keyboards/` — Unknown / needs inspection
- `services/` — Unknown / needs inspection
- `miniapp/` — Unknown / needs inspection
- `.env.example` — Unknown / needs inspection

Important note:
- Do not rename or delete important files unless necessary.

---

## 6. Database Schema Summary

### users
Purpose: stores Telegram users and access status.

Important fields:
- `telegram_id`
- `language`
- `status`
- `payment_status`
- `subscription_until`
- `question_limit`
- `questions_used`

### payments
Purpose: stores payment requests and confirmations.

Important fields:
- `payment_id`
- `telegram_id`
- `amount`
- `payment_code`
- `status`
- `created_at`
- `confirmed_at`

### logs / history
Purpose: stores important user actions or AI interactions.

Important fields:
- Unknown / needs inspection

---

## 7. Current Business Logic

### User onboarding
Current flow:
1. Unknown / needs inspection

### Subscription logic
Current logic:
- Free trial: Unknown / needs inspection
- Paid plans: Unknown / needs inspection
- Question limits: Unknown / needs inspection
- Expiration logic: Unknown / needs inspection
- Access blocked when: Unknown / needs inspection

### Payment logic
Current logic:
- Payment method: Unknown / needs inspection
- Manual approval: Unknown / needs inspection
- Auto approval: Unknown / needs inspection
- Admin notification: Unknown / needs inspection

### AI logic
Current logic:
- Unknown / needs inspection

---

## 8. Current Features

Working:
- Unknown / needs inspection

Partially working:
- Unknown / needs inspection

Not built yet:
- Unknown / needs inspection

---

## 9. Important Decisions

### Decision 1
Date: Unknown  
Decision: Unknown / needs inspection  
Reason: Unknown / needs inspection  
Risk: Unknown / needs inspection  

---

## 10. Recent Important Changes

### 2026-06-29 — Admin Mini App weekly/monthly/all-time statistics

Changed:
- Admin Mini App overview payload now includes `statistics_reports` split into weekly (last 7 days), monthly (last 30 days), and all-time reports.
- Each period report includes users, active users, approved payment users/revenue, pending/rejected payments, current/new bot blocks, and Course Mini App activity for the same period.
- `miniapp_course_stats(session, since=None)` can now filter Course Mini App event analytics by `created_at`.
- `admin-control.html` Statistics tab has period buttons, quick metric cards, period-specific conversion bars, and copies the selected report text.

Why:
- Admin needed weekly, monthly, and full statistics visible inside the admin panel instead of one mixed report.

Files touched:
- `app/services/admin_miniapp_service.py`, `app/services/admin_stats_service.py`, `app/static/admin-control.html`, `tests/test_admin_stats_service.py`

Risk:
- Read-only analytics/UI change. Payment, subscription, access, referral, lesson, quiz, and homework logic are not changed.

Follow-up:
- Real Telegram admin Mini App smoke-test after deploy; local Chromium smoke test is blocked by macOS sandbox permission in this Codex environment.

### 2026-06-29 — Course Mini App referral list + weekly rating reset behavior

Changed:
- `/api/v3/invite` now also returns the current user's referred users for the Course Mini App friends tab: name, Telegram username/id, referral status, weekly XP, total XP, course level, completed lessons, and paid flag.
- Course v3 friends tab now shows invited referrals, opens the same full profile overlay used by rating users, and lets the user open Telegram chat or send a Course challenge from that profile.
- Course leaderboard is now one weekly pool instead of filtering users by lifetime XP league. Weekly rating display uses weekly XP only, so after the weekly reset users show `0` instead of falling back to lifetime XP.

Why:
- Users need to see and re-engage people they invited. The old rating logic made weekly reset look broken because lifetime XP still separated users into league buckets and appeared as the visible score when weekly XP was zero.

Files touched:
- `app/services/referral_service.py`, `app/main.py`
- `app/services/course_gamification_service.py`
- `app/static/course-v3.html`
- `tests/test_course_v3_static_data.py`

Risk:
- Medium: user-facing Mini App referral/rating flow changed. No payment/subscription/access entitlement logic changed. Real Telegram WebView smoke-test with two accounts is still recommended.

Follow-up:
- In Telegram, verify invited-user list, profile overlay, direct Telegram chat behavior for username/no-username users, challenge send/receive, and Monday reset display.

### 2026-06-29 — Access state classifier + Telegram bot block tracking

Changed:
- Added canonical access classification for `paid`, `temporary_trial`, `trial`, `free`,
  `expired`, `blocked` without rewriting the whole subscription system.
- Free/expired users no longer fall into `access_start_first` in QA/image access; they
  use free-tier limits. Expired paid users become `status="expired"`; expired temporary
  trial users become `status="free"`.
- Course trial completion moves a `status="trial"` user to `status="free"` while keeping
  course trial fields as the source of trial entitlement history.
- Added Telegram bot-block tracking fields on `users` and a silent daily `getChat` scan.
  Admin block (`status="blocked"`) remains separate from Telegram bot block.
- Admin Mini App now shows separate `free` and `bot_blocked` segments.

Why:
- Trial/free/paid/expired were mixed across bot, Course Mini App, and admin stats, which
  could make old `free` users look like they had not started the bot.

Files touched:
- `app/services/user_access_state_service.py`, `app/services/access_service.py`
- `app/services/course_trial_service.py`, `app/services/course_miniapp_access_service.py`
- `app/services/bot_block_status_service.py`, `app/db/models/user.py`, `app/db/session.py`
- `app/main.py`, `app/services/admin_miniapp_service.py`, `app/static/admin-control.html`
- `alembic/versions/0059_user_bot_block_tracking.py`

Risk:
- Medium: access/payment-adjacent logic changed. The patch is backward-compatible and
  does not bulk-migrate existing users. Deploy must run migration `0059_user_bot_block_tracking`.

Follow-up:
- Smoke-test real Telegram: free user asks QA, expired paid user asks QA, trial lesson
  completion, admin Mini App free/bot-blocked segments, and bot-block status after a user
  blocks/unblocks the bot.

### 2026-06-29 — Course v3 and QA level/language canonical sync

Changed:
- Course v3 map no longer serves unauthenticated/local preview data when Telegram `initData` is missing, invalid, or the user is not found; the Mini App shows a "return to bot and press /start" gate instead.
- Course v3 uses `users.level` and `users.language` as the canonical source for map loading, ad view recording, skip-test unlock, lesson completion, practice start/complete, and challenge creation. Client URL/query/payload level/lang are ignored for these write paths.
- Finishing the last lesson in a band promotes `users.level` to the next HSK band, so QA and Course stay aligned.

Why:
- QA mode and Course mode must not open at different HSK levels or languages. A failed Mini App API/bot connection must not silently fall back to HSK1 or cached/local preview.

Files touched:
- `app/main.py`, `app/static/course-v3.html`, `app/services/course_challenge_service.py`

Risk:
- Medium: affects course progress, practice/challenge level selection, and unauthenticated Mini App behavior. Smoke-test inside real Telegram WebView after deploy.

Follow-up:
- Verify a user with non-HSK1 level/language in bot opens Course v3 at the same level/language, then completes a lesson and starts practice/challenge without drift.

### 2026-06-29 — Mini App slowness + lesson writer/dictionary deep-link fixes

Changed:
- `hsk-data.js` (2.9 MB) and `course_v3_data/memo.js` (440 KB) were served with
  `no-store` headers, so every Mini App page open and every in-lesson writer iframe
  re-downloaded ~3.4 MB. They are loaded as `file.js?v=YYYYMMDD` (version-busted), so
  they are now served with `Cache-Control: public, max-age=31536000, immutable` via a
  new `static_asset_response()` / `STATIC_ASSET_HEADERS` in `app/main.py`. HTML pages
  stay `no-store`. Bump the `?v=` query when the data content changes.
- `hsk-lugat.html` deep-link `?char=` (used by the lesson pencil ✏️ writer) previously
  only opened a detail on an exact `WORDS[].h` match and otherwise silently fell back to
  the full dictionary list ("opens old dictionary, doesn't open the requested char").
  New `openDeepChar()` tries: exact word → word containing the text → word containing the
  first character → synthesized `{h:deep}` so the stroke writer always shows the requested
  character.
- "Keyingi so'z" (next-word) button in the dictionary detail used to appear only after the
  stroke animation finished. It is now shown at the end of `loadChar()` (self-hides when no
  next word), so it works without waiting for the animation and across multi-char nav.

Why:
- User reported: in-lesson pencil sometimes opens the old dictionary and not the needed
  character; the next-character button sometimes does nothing; HTML sections open slowly.

Files:
- `app/main.py`, `app/static/hsk-lugat.html`

Risk:
- Caching is keyed by the full URL incl. `?v=`; if `hsk-data.js`/`memo.js` content changes
  without bumping `?v=`, clients keep the old cached file. No payment/subscription/access
  logic changed. Real Telegram WebView smoke test still recommended.

### 2026-06-29 — Course ad: admin-controlled duration, end-of-ad subscribe block, advertiser link, no mid-lesson force

Changed:
- Course ad watch duration is now admin-controlled in the 5–120s range (was hard-clamped to 6–7s). `COURSE_AD_MIN_SECONDS=5`, `COURSE_AD_MAX_SECONDS=120` in `app/services/course_ad_service.py`; frontend `adDuration()` in `course-v3.html` uses the same clamp so client watched-seconds match the server gate.
- Each ad now ends with a subscribe block ("Obuna bo'ling — reklamasiz, limitsiz") offering "Obuna olish" (→ paywall) and "Reklama bilan davom etish" (continue). Shown after the countdown for start/middle/end placements.
- `CourseAdCreative.link_url` added (advertiser link). Admin upload form has an optional link field; tapping the ad video in the Mini App asks (Telegram showConfirm) before opening the link via `tg.openLink`.
- Ad-supported lessons no longer force the subscribe sheet mid-lesson: start/middle/end ad errors now just continue the lesson, and a `free_feature_limit_reached` at completion of an ad-supported lesson shows a toast instead of the locked-lesson paywall.
- Admin Mini App can now fully DELETE a course ad (not just toggle): `POST /api/admin-miniapp/course-ads/delete` removes the row and the media file from disk. `CourseAdService.delete()` returns the media path for file cleanup. Toggle button relabeled to Фаолсизлантириш/Фаоллаштириш; a separate red "Бутунлай ўчириш" button does the full delete.

Why:
- Duration was stuck at 7s; advertisers/admin need control. The subscribe block gives a clean upsell at each ad without hard-blocking. Advertiser links monetize the placement. Forcing a paywall mid-lesson after the user chose the ad path was a bad UX bug.

Files:
- `app/db/models/course_ad.py`, `app/services/course_ad_service.py`, `app/main.py` (upload endpoint), `app/db/session.py` (bootstrap column), `alembic/versions/0058_course_ad_link_url.py`, `app/static/admin-control.html`, `app/static/course-v3.html`, `tests/test_course_miniapp_foundation.py`.

Risk:
- Migration `0058_course_ad_link_url` adds nullable `link_url`; runtime bootstrap also patches legacy DBs. Server-side ad gate (`has_completed_required_views`, all 3 placements) is unchanged.

### 2026-06-28 — Challenge invite deep-link and XP rewards

Changed:
- Course challenge invites now use clearer Uzbek/Russian/Tajik duel copy, edit the original invite message after accept/reject, and open Course v3 directly with `tab=rating&challenge_id=...`.
- Course v3 can deep-link into a challenge, accept/reject pending invites, start the shared 10-question round, submit answers, and show result/XP feedback.
- Challenge completion grants XP, and completed rounds grant bonus XP to the winner; exact ties reward both players.
- Practice/challenge question selection now samples across the level more evenly by lesson/type/subtype instead of stopping at the earliest lessons.

Why:
- Telegram challenge messages were mixed-language and the Mini App button opened a generic profile instead of the actual duel.
- Challenge rounds needed a stronger reward loop and fair, same-question gameplay for both users.

Files touched:
- `app/services/course_challenge_service.py`
- `app/services/course_miniapp_practice_service.py`
- `app/bot/handlers/challenge.py`
- `app/bot/utils/course_miniapp.py`
- `app/static/course-v3.html`
- `tests/test_course_challenge_service.py`
- `tests/test_course_miniapp_foundation.py`

Risk:
- Touches user-facing challenge flow, Mini App routing, question selection, and XP award events. Payment/subscription logic is not changed.

Follow-up:
- Smoke test in real Telegram WebApp with two accounts: send challenge, accept/reject, open direct duel, complete both sides, and verify XP/rating updates.

### 2026-06-28 — HSK exam answer hint cleanup

Changed:
- Test Center HSK 1-4 exam renderer no longer shows pinyin or secondary hint labels inside answer options.
- Meaning/listening questions show localized answer choices only; grammar, fill-blank, and writing/order questions show Chinese choices only.

Why:
- Answer options previously exposed pinyin, translations, or labels like `(noto'g'ri tartib)`, making some exam questions answerable without real understanding.

Files touched:
- `app/static/course_v3_test.html`
- `tests/test_course_v3_static_data.py`

Risk:
- Low. Exam data, scoring, result flow, payment, subscription, and access rules are unchanged.

Follow-up:
- Re-test in Telegram WebView after deploy on HSK 1-4 exams, especially meaning and writing/order questions.

### 2026-06-28 — Course v3 reward message correctness

Changed:
- Course v3 lesson-completion rank-up popup now refreshes real leaderboard data before showing and only appears when the user's rank actually improved.
- Mini App rating rows now preserve server-provided rank order, including stable tie handling.
- Motivation reminder ranking uses the same stable tie-breaker and no longer sends `0 XP` as the overtaken gap.
- Course v3 lesson-completion reward overlay now displays the backend `awarded_xp` value instead of hardcoded fake rewards such as `+60 XP`.

Why:
- The old lesson-completion popup could claim the user rose in ranking after every lesson and could name the wrong user because it used stale client leaderboard data.
- The old reward overlay showed fixed XP values that did not match real XP awarded by `CourseGamificationService`.

Files touched:
- `app/static/course-v3.html`
- `app/services/course_gamification_service.py`
- `app/services/motivation_reminder_service.py`

Risk:
- Low. Lesson completion, XP awarding, payment, subscription, and access rules are unchanged.

Follow-up:
- Re-test in real Telegram WebView after deploy because local Playwright Chromium is blocked by sandbox permissions.

### 2026-06-28 — Course v3 analytics, skip-test unlock, and real fallback cleanup

Changed:
- Course v3 now records `miniapp_opened` from `/api/v3/map` and client events for `lesson_started`, `section_started`, `section_completed`, `card_seen`, `interaction_completed`, `test_started`, and `paywall_seen` with source/session/dedupe data.
- Skip-ahead tests in Course v3 now call `/api/v3/lesson/unlock`; backend validates Telegram WebApp auth, lesson existence, and premium/free access before updating `course_progress`.
- Gamification snapshots include real weekly reset time/seconds for the rating countdown.
- Admin course stats count Course v3 `lesson_completed` together with legacy `book_lesson_completed`.
- Subscription Mini App API-error fallback no longer displays preview/mock prices; preview prices remain available only in explicit preview mode.

Why:
- Course v3 traffic was undercounted in admin stats because v3 did not emit the old Mini App analytics events.
- Skip-test unlock was frontend-only, so reload/backend progress could disagree with the UI.
- Rating/profile/subscription UI had fake fallback or hardcoded values that could look like real business data.

Risk:
- This touches course analytics and Course v3 skip-test access/progress. Payment approval and subscription pricing logic are not changed.

Files touched:
- `app/main.py`
- `app/static/course-v3.html`
- `app/static/subscription.html`
- `app/services/course_gamification_service.py`
- `app/services/admin_stats_service.py`
- `app/services/admin_miniapp_service.py`
- `app/db/models/course_miniapp_event.py`
- `tests/test_course_gamification_service.py`
- `tests/test_course_v3_static_data.py`

Follow-up:
- Browser smoke test should be repeated in a normal local/dev environment or Telegram WebApp, because this Codex sandbox blocked localhost port binding and `file://` browser navigation.

### 2026-06-28 — Course v3 tour narration fixed for Uzbek/Tajik

Changed:
- Course v3 onboarding tour now plays pre-generated MP3 narration from
  `app/static/audio/tour/{uz,ru,tj}/{key}.mp3` through `/audio/tour/{lang}/{key}.mp3`.
- Tour UI text and TTS text are separated in `scripts/gen_tour_audio.py`: screen text stays
  clean, while Uzbek/Tajik audio uses TTS-friendly wording.
- Browser speechSynthesis fallback no longer forces Uzbek/Tajik into Turkish/Russian voices;
  fallback runs only when a native matching browser voice exists. Cache version bumped to
  `TOUR_AUDIO_VER="20260628b"`.

Why:
- Device/browser TTS was producing bad Uzbek/Tajik pronunciation in the first Course v3 tour.
  Tajik has no native Edge voice, so the Tajik MP3s use Russian neural voice with phonetic
  Cyrillic text prepared for that voice.

Files touched:
- `app/static/course-v3.html`
- `app/main.py`
- `scripts/gen_tour_audio.py`
- `app/static/audio/tour/`

Risk:
- Frontend/static-audio only. Lesson order, quiz, homework, payment/subscription/access logic
  unchanged.

Follow-up:
- Real Telegram WebView listening check is still useful because autoplay policy can vary by
  client, but local Playwright verified UZ/TJ tour visibility and 2xx `audio/mpeg` requests.

### 2026-06-28 — Course v3 UX fixes: subscription nav, no-ad free fallback, league chat

Changed:
- Subscribe button no longer kicks users to the external browser: `App.goPay()` now
  navigates the same-origin `subscription.html` inside the Telegram Mini App webview
  via `location.href` instead of `tg.openLink`. Paywall/locked-lesson sheets got a clear
  trilingual hint: "Subscribe → after payment confirmed, lessons open right here".
- Ad-supported path when NO admin ad is uploaded: free users now continue the next
  premium lesson for free instead of being blocked. `/api/v3/lesson/complete` checks
  `CourseAdService.get_active_ad()`; if none active, the ad-gate is skipped (ad_supported
  =True). Frontend `_isNoAd()` lets start/middle/end ad failures (course_ad_not_found)
  fall through to the lesson. When admin enables an ad later, the 3-placement gate
  applies again automatically.
- Removed redundant "Keyinroq/Позже/Дертар" ghost close buttons from sheets (paywall,
  locked lesson, skip-test offer, skip-test result) since each sheet already has an X +
  backdrop-tap close.
- Profile streak calendar now reflects real data (current weekday + `progress.streak`)
  instead of a hardcoded week; header shows real streak count, not "Rekord: 23".
- Profile cups/trophies are now derived from real progress (completed lessons / streak)
  and the whole cups section is hidden when the user has earned none.
- League/rating "message" button opens the ranked user's direct Telegram chat
  (`openUserChat` via username/`tg://user?id=`), and "Challenge" now actually POSTs
  `/api/miniapp/challenges` (delivers a real bot notification to the opponent) instead
  of only showing a toast. `ratingUsers` now carries `username`/`tgId` from the
  leaderboard payload.

Files touched:
- `app/static/course-v3.html`
- `app/main.py` (v3 lesson complete ad gate)

Risk / follow-up:
- Access change: free users can now progress through premium lessons one-by-one while NO
  course ad is active. Once admin enables an ad, the watch-required gate returns. Paid
  approval logic unchanged.
- "Do'st qo'sh" (friendAdd) button was REMOVED from the rating profile: there was no
  friend-relationship backend, so it only faked "request sent". Rating profile now shows
  Challenge + direct-chat message, both of which DO reach the other user.
- Real Telegram WebView smoke-test needed: subscribe stays in-app, no-ad free lesson
  completes, challenge notification arrives for opponent, direct chat opens for a ranked
  user with/without username.

### 2026-06-28 — Course free preview gate + ad-supported Premium lesson path

Changed:
- Course v3 free access is now lesson-number based, not level based: every HSK level
  allows lessons 1-3 as free preview; lesson 4+ requires Premium unless the user is
  paid or completes the ad-supported flow for that lesson.
- `FREE_COURSE_LESSONS_PER_LEVEL = 3` lives in `course_miniapp_access_service.py`
  and is used by both `/api/v3/map` and `/api/v3/lesson/complete`.
- Added `course_ad_creatives` and `course_ad_views` tables. Admins can upload and
  enable/disable course ad media from the admin Mini App; free users may unlock a
  next premium lesson after watching required start/middle/end placements for 6-7s.
- Premium users keep full course access and do not need course ads.

Why:
- HSK1 users are the largest segment, so making all HSK1 free blocks monetization.
  The preview should show value without opening the full paid course.

Files touched:
- `app/services/course_miniapp_access_service.py`
- `app/main.py`
- `app/services/course_ad_service.py`
- `app/db/models/course_ad.py`
- `app/static/course-v3.html`
- `app/static/admin-control.html`
- `alembic/versions/0056_course_ad_supported_lessons.py`

Risk / follow-up:
- Run the Alembic migration before using admin ad uploads in production.
- Telegram Mini App ad policy should be checked before connecting external ad networks;
  the current implementation supports in-house/admin-uploaded media first.

### 2026-06-28 — Free-tier monetization limits

Changed:
- New users default to 5 free QA text answers per day (`User.question_limit = 5`).
- Migration `0055_free_tier_monetization_policy` updates existing non-paid trial/free
  users that still had the old 10-question default.
- Free pronunciation assessment is capped at 3 STT attempts per day before calling AI.
- Referral active-friend threshold changed from 10 to 5.
- Subscription analytics labels now include `v3_ad`, `v3_qa_limit`,
  `v3_voice_trial_used`, and `v3_pronunciation_limit`.

Why:
- Static course/language learning surfaces can stay generous, but real-cost AI paths
  need tighter metering so free users do not create unlimited token/STT cost.

Files touched:
- `app/db/models/user.py`
- `app/services/voice_practice_service.py`
- `app/services/referral_service.py`
- `app/services/subscription_entry_analytics_service.py`
- `app/bot/utils/i18n.py`
- `app/static/course_v3_pronunciation.html`
- `alembic/versions/0055_free_tier_monetization_policy.py`

Risk / follow-up:
- Existing paid-user AI budget logic is unchanged.
- After deploy, smoke-test QA daily limit, pronunciation limit, referral milestone,
  and subscription entry analytics.

### 2026-06-28 — Admin Mini App real action center

Changed:
- Admin Mini App now opens internal management panels instead of sending admin section bounce messages to Telegram chat.
- Added admin Mini App APIs for management payload, user search/detail, payment approve/reject, manual access, user delete, subscription prices, payment details, required channels, help links, portfolio transactions, text broadcast, text-first ad/release/discount campaign creation, partner actions, and audio listing.
- Payment approval from Mini App follows the same core flow as Telegram admin approval: marks payment approved, activates subscription, records analytics/portfolio/partner commission, and notifies the user.

Why:
- Admin work should be doable inside the Mini App while keeping old Telegram chat admin sections available as fallback.

Files touched:
- `app/main.py`
- `app/services/admin_miniapp_service.py`
- `app/static/admin-control.html`

Risk:
- Payment/access/user delete/broadcast/campaign actions are real admin mutations; they require Telegram WebApp admin auth and should be smoke-tested inside Telegram after deploy.
- Alipay/WeChat custom QR upload and audio upload still depend on Telegram `file_id` chat flows; Mini App can manage prices and list audio but not replace those file_id upload flows yet.

Follow-up:
- Browser localhost smoke was blocked by environment localhost/usage limits; Python compile, JS syntax check, focused pytest, and dummy-token import passed.

### 2026-06-28 — Legacy Course Mini App URLs now route to Course v3

Changed:
- Bot Mini App URL helpers no longer point to removed V2/static pages (`study.html`, `duo-lesson.html`, `stroke-order.html`, old `hsk*.html` base fallback).
- Course study/quiz/training links now open `course-v3.html`; legacy tabs such as `training`, `quiz`, `words`, `grammar`, and `tests` map to Course v3 `tab=mashq`.
- Stroke/vocab links now open `hsk-lugat.html` with `from=course`.
- `course-v3.html?lesson=N` opens the matching lesson sheet after boot, so bot deep links still land on the intended lesson.
- Default `MINI_APP_BASE_URL` in config/example is now the Course v3 page.

Why:
- The old V2 files were removed, but bot helpers/tests/config still referenced them. That created broken Mini App buttons and failing smoke coverage.

Files touched:
- `app/bot/utils/course_miniapp.py`, `app/static/course-v3.html`, `app/static/hsk-lugat.html`
- `app/config.py`, `.env.example`
- `tests/test_course_miniapp_foundation.py`, `tests/e2e/test_miniapp_smoke.py`

Risk:
- Old separate V2 quiz/homework pages are not restored; legacy entry points intentionally land inside Course v3.
- Real Telegram WebView smoke-test is still needed after deploy for initData/payment/microphone flows.

### 2026-06-28 — Course ad-supported Premium lesson path

Changed:
- Added Course Mini App ad tables: `course_ad_creatives` for admin-uploaded video creatives and `course_ad_views` for per-user lesson placement watch tracking.
- Added migration `0056_course_ad_supported_lessons.py`.
- Admin Mini App Settings can upload/toggle Course ad videos stored under `app/static/uploads/course_ads`.
- Course v3 locked Premium lessons now offer two paths when the lesson is the user's next lesson: subscribe to Premium or continue with ads.
- Ad-supported premium lessons require 6-7s video ads at lesson start, middle, and end. Server completion for unpaid users validates all three placements before allowing the Premium lesson to complete.
- Paid users remain ad-free. Lessons 1-3 free preview stays clean; ads are only for the ad-supported premium path.

Why:
- Most users are in HSK1, so hard-blocking lesson 4+ leaves money on the table. This creates a second monetization route for non-paying users without changing paid subscription approval logic.

Files touched:
- `app/db/models/course_ad.py`, `app/services/course_ad_service.py`, `app/main.py`
- `app/static/course-v3.html`, `app/static/admin-control.html`
- `alembic/versions/0056_course_ad_supported_lessons.py`

Risk:
- Deploy must run migration `0056_course_ad_supported_lessons`.
- Real Telegram smoke-test should verify admin video upload, free user lesson 4 ad flow start/middle/end, server completion after ads, no completion without ads, and paid user sees no ads.
- If no active Course ad exists, the ad path falls back to the Premium sheet.

Follow-up:
- Browser Playwright smoke-test was blocked by environment usage limits; Python compile, JS syntax extraction, and focused pytest passed.

### 2026-06-28 — HSK2-HSK4 memorize data coverage

Changed:
- `course_v3_data/memo.js` now keeps the hand-written HSK1 memo entries and adds a compact HSK2-HSK4 offline generator (`EXTRA_MEMO_ITEMS` + `makeExtraMemo`) built from existing `hsk-data.js` WORDS.
- Generated entries cover every Han character appearing in HSK2, HSK3, and HSK4 word data, so `course_v3_memorize.html?char=...` no longer falls back to HSK1-only decks for higher levels.
- `hsk-lugat.html` and `course_v3_memorize.html` bumped the `memo.js` cache query to `v=20260628`.

Why:
- The HSK character dictionary already exposed HSK2-HSK4 words, but the fast memorize module only had 87 HSK1 character entries.

Files touched:
- `app/static/course_v3_data/memo.js`
- `app/static/course_v3_memorize.html`
- `app/static/hsk-lugat.html`

Risk:
- Data/frontend-only; no payment, subscription, lesson completion, quiz, homework, or backend result logic changed.
- HSK2-HSK4 generated entries are honest word-based hooks, not historical etymology explanations.

Follow-up:
- Browser Playwright smoke test was blocked by local Chromium sandbox/permission limits; JS runtime validation and static data pytest passed.

### 2026-06-28 — Free-tier monetization limits and Course v3 3-lesson preview gate

Changed:
- Free QA text default is 5 questions/day (`User.question_limit`, new-user repo path, and migration/default aligned).
- Free pronunciation scoring is capped at 3 STT attempts/day before OpenAI is called; paid users still use the AI budget gate.
- Referral trial unlock threshold is 5 active friends; per-active-friend +5 bonus question behavior stays.
- Course v3 free course access is no longer level-based. Every HSK level gives lessons 1-3 as free preview and marks lesson 4+ as Premium in both static maps and server access policy.
- Course v3 pronunciation-limit paywall source is tracked as `v3_pronunciation_limit`; new analytics labels include v3 ad/QA/voice/pronunciation sources.

Why:
- Most users are expected to be in HSK1, so making all HSK1 free would block monetization. The new policy gives enough static course preview for learning habit while keeping deeper HSK1+ content behind Premium.

Files touched:
- `app/db/models/user.py`, `app/services/voice_practice_service.py`, `app/services/referral_service.py`, `app/services/course_miniapp_access_service.py`, `app/main.py`
- `app/static/course-v3.html`, `app/static/course_v3_pronunciation.html`, `app/static/course_v3_data/hsk1.json`..`hsk4.json`
- `alembic/versions/0055_free_tier_monetization_policy.py`

Risk:
- Access behavior changed for unpaid users: HSK1 lesson 4+ now requires Premium. Payment approval and paid-user AI budget logic were not changed.
- Deploy should run migration `0055_free_tier_monetization_policy`; Telegram smoke-test should verify free HSK1 lesson 3 completes, HSK1 lesson 4 opens Premium sheet, and paid user can open 4+.

### 2026-06-27 — Course v3 paywall to'siq oynasi tiriltirildi (locked dars → Premium sheet)

Changed:
- Avval Course v3'da qulflangan darsni (HSK 4+, `locked_premium`) bosganda foydalanuvchi
  hech qanday tushuntiruvchi oyna ko'rmay, to'g'ridan-to'g'ri `subscription.html`'ga
  uchib o'tardi. `paywallHtml()` funksiyasi va `#paywall` bottom-sheet HTML'i kodda
  bor edi, lekin hech qayerdan chaqirilmasdi (dead code).
- `App.openPaywall(ctx)` endi `#paywall-body`'ga `paywallHtml(ctx)` quyadi va sheet'ni
  ochadi (会 logo, "Bu dars Premium'da" sarlavha, b1/b2/b3 afzalliklar, narx, "Obuna
  bo'lish" + "Keyinroq" tugmalari). Avvalgidek darrov `goPay` chaqirmaydi.
- Yangi global `PAY_SOURCE` qo'shildi: `openPaywall` kontekstdan manbani saqlaydi
  (`v3_locked_lesson` / `v3_paywall` / `v3_profile`), `goPay` argument berilmasa
  `PAY_SOURCE`'dan oladi. Shu bois sheet'dagi "Obuna bo'lish" tugmasi to'g'ri
  `source=` bilan `/subscription.html?...&mode=subscription` ochadi.
- 3 ta trigger o'zgarmadi: qulflangan dars tap, skip-test, va server
  `free_feature_limit_reached` xatosi — barchasi endi avval sheet'ni ko'rsatadi.

Why:
- Foydalanuvchi qulfni bosganda nima uchun to'lov sahifasi ochilganini bilmasdi;
  endi avval qisqa Premium afzalliklari/narx oynasi chiqib, tushunib obunaga o'tadi.
  Mavjud dead code qayta ishlatildi.

Files touched:
- `app/static/course-v3.html`

Risk:
- Faqat frontend (paywall UX); to'lov/obuna/ruxsat backend mantig'i o'zgarmadi.
  Lock qoidasi (bepul HSK1-3, 4+ Premium) va `subscription.html` o'zi tegilmadi.
- Narx sheet'da faqat server narx datasi yuklangach ko'rinadi (`_priceStr` guard
  bilan); statik preview'da backend yo'qligi sabab narx ko'rinmaydi, real Telegram'da
  chiqadi.
- Real Telegram WebView smoke-test kerak: HSK 4-darsni bosib sheet → "Obuna bo'lish"
  → subscription oqimini tekshirish.

### 2026-06-27 — Motivatsion eslatmalar (reyting / kunlik maqsad / streak) + admin tahriri

Changed:
- Yangi `MotivationReminderService` 3 ta push eslatma yuboradi, har biri real Mini App
  ma'lumotidan: (1) reytingda kimdir ortda qoldirsa, (2) kun oxirida kunlik maqsad
  bajarilmasa, (3) streak uzilish xavfi bo'lsa. Har biri foydalanuvchiga mahalliy
  kun bo'yicha max 1 marta; goal/streak faqat 20:00–21:30 oynasida va bugun
  shug'ullanmagan bo'lsa. `_background_scheduler` (har 60s) ichiga ulandi.
- Reyting o'tib ketishini aniqlash uchun `course_miniapp_profiles` ga `last_known_rank`
  va 3 ta dedupe sanasi (`motivation_overtaken_date/goal_date/streak_date`) qo'shildi.
- Eslatma matnlari endi bazada (`notification_templates`) — admin Mini App'dan UZ/RU/TJ
  alohida tahrirlanadi, yoq/o'chir qilinadi, bitta umumiy surat/video biriktiriladi.
  Matn bo'sh bo'lsa koddagi standart matnga (DEFAULT_TEXTS) qaytadi, shuning uchun
  noto'g'ri sozlash eslatmani jimitib qo'ymaydi.
- Media admin Mini App'dan to'g'ridan-to'g'ri yuklanadi (`/api/admin-miniapp/notifications/media`),
  serverda `app/static/uploads/notifications/` ga saqlanadi, scheduler `FSInputFile`
  bilan yuboradi, preview `/uploads/notifications/{file}` orqali ko'rsatiladi.
  Caption (media bilan) max 1024, mediasiz matn max 4096 belgi.
- Admin Mini App "Sozlash" tabiga "🔔 Motivatsion eslatmalar" bo'limi qo'shildi
  (yangi tab/navigatsiya qo'shilmadi, 5 tab o'zgarmadi).

Why:
- Avval streak/liga/reyting faqat Mini App UI'da bor edi; foydalanuvchi botni ochmasa
  hech qanday motivatsion push kelmasdi (eski `CourseReminderService` faqat oddiy
  kunlik/haftalik eslatma yuborardi).

Files touched:
- `app/db/models/notification_template.py` (new)
- `app/db/models/course_miniapp_profile.py`
- `app/services/notification_template_service.py` (new)
- `app/services/motivation_reminder_service.py` (new)
- `app/main.py` (endpoints + scheduler + media route)
- `app/db/session.py` (bootstrap columns)
- `app/static/admin-control.html`
- `alembic/versions/0054_add_notification_motivation.py` (new head)

Risk:
- Migration `0054_add_notification_motivation` yangi head. `notification_templates`
  jadvali `create_all` bilan startda yaratiladi; profil ustunlari `_BOOTSTRAP_COLUMNS`
  orqali eski Railway DB'ga ham qo'shiladi.
- To'lov/obuna/ruxsat mantig'i o'zgarmadi.
- Eslatmalar `User.status == "active"` va Mini App profili bor foydalanuvchilarga
  yuboriladi; per-user opt-out yo'q (faqat admin template'ni o'chira oladi).
- Deploydan keyin real Telegram'da smoke-test kerak: admin Mini App'da matn tahriri,
  media yuklash/o'chirish, va kechqurun goal/streak push'i.

### 2026-06-27 — HSK lug'at kartasiga strukturali "eslab qolish" bo'limlari

Changed:
- `hsk-lugat.html` belgi detali endi `memo.js` (`window.MEMO_DATA`) dan
  data-driven 5 bo'lim ko'rsatadi: Tarkibi (breakdown), Ma'no/tovush belgisi
  (radikal rollari + signal), Eslab qolish (hooks), O'xshash iyerogliflar
  (confusables), Misol (words). Har bo'lim faqat shu belgi uchun data bo'lsa
  chiqadi, bo'lmasa toza yashiriladi (`.memo-wrap:empty{display:none}`).
- Stroke-order animatsiya va 1-3 bo'lim (hanzi/pinyin/ma'no), mavjud
  misol/grammatika/mashqlar bloklari tegilmadi.
- `etymology_honest:false` belgilarda `MEMO_UI.disclaimer` (3 til) ko'rsatiladi.
- `main.py` ga `GET /course_v3_data/memo.js` route qo'shildi (avval `.json`-only
  route uni 404 qilardi).
- `main.py` `_COURSE_V3_PAGES` ga `"memorize"` qo'shildi → lug'atdagi ⚡ "Tez
  eslab qolish" tugmasi (`/course_v3_memorize.html?char=…`) endi 404 emas, real
  interaktiv yodlash moduli ochiladi.
- Lug'at ⚡/mashq tugmalari endi `from=lugat` (+ `theme`/`level`) uzatadi
  (`goPractice`), va `course_v3_memorize.html` `goBack()` `from=lugat` bo'lsa
  `/hsk-lugat.html?char=FOCUS` ga qaytaradi → mashq tugagach foydalanuvchi
  boshlagan belgisiga (lug'atga) qaytadi, kurs mashq tabiga emas.

Why:
- Lug'at kartasi faqat hanzi/pinyin/ma'no ko'rsatardi; mavjud offline yozilgan
  memo data (HSK1, 87 belgi) shu kartada qayta ishlatildi. Runtime AI yo'q.

Files touched:
- `app/static/hsk-lugat.html`
- `app/main.py`

Risk:
- Faqat frontend + 1 statik route; lesson/quiz/homework/initData/backend/payment
  tegilmadi.
- Memo data hozir faqat HSK1 (87 belgi) uchun bor; qolgan belgilarda 4-8 bo'limlar
  yashirin (lug'at kartasida) va ⚡ modulida deck shu pul ichidan quriladi.

### 2026-06-27 — Legacy V2 Mini App removed, bot opens Course v3, subscription paywall rewritten

Changed:
- Removed the legacy V2 course Mini App surface and its assets: `study.html`,
  `study-v2.js`, `study-v2.css`, `course-miniapp-v2.js`, `voice-practice.html`,
  `stroke-order.html`, `hsk1.html`..`hsk4.html`, `subscription-preview.html`.
  The active course experience is now Course v3 (`course-v3.html` + `course_v3_*`).
- Bot Course entry points now open Course v3: `send_course_miniapp_entry()` and
  `run_course_entry_flow()` use the new `course_v3_miniapp_keyboard(lang)` /
  `course_v3_miniapp_url()` (opens `course-v3.html`) instead of `study.html`.
- `subscription.html` rebuilt as a compact Course v3-styled paywall (~1422 -> ~341
  lines): plan picker (1_month / 10_days), payment method, discount block.
- Subscription entry analytics gained Course v3 sources: `v3_paywall`,
  `v3_locked_lesson`, `v3_level_up` (and `v3_profile` relabeled). Admin control
  Mini App (`admin-control.html`) now shows an "Obuna manbalari" table via the
  existing `/api/admin-miniapp/sub-entry-stats` endpoint.
- `course_v3_voice.html` AI Voice character moods/visuals updated (UI only).

Why:
- Course fully moved to V3; the old V2 Mini App and its duplicate paywall/voice
  pages were dead weight and confused the entry flow.

Files touched:
- `app/bot/handlers/course.py`, `app/bot/keyboards/course_miniapp.py`,
  `app/bot/utils/course_miniapp.py`
- `app/services/subscription_entry_analytics_service.py`, `app/static/admin-control.html`
- `app/static/subscription.html`, `app/static/course_v3_voice.html`
- Deleted: `app/static/{study.html,study-v2.js,study-v2.css,course-miniapp-v2.js,voice-practice.html,stroke-order.html,hsk1.html,hsk2.html,hsk3.html,hsk4.html,subscription-preview.html}`

Risk:
- No payment/subscription/access backend rules changed; only the entry keyboard
  target and the paywall frontend.
- Bug fixed during review: `subscription.html` plan render had a stray `)` that
  broke the entire inline script (paywall would not render); corrected so the
  popular-plan `pop` class concatenates cleanly.
- Legacy bot code still references the deleted `study.html` (course challenge
  notifications, `course_study_miniapp_keyboard`) and `stroke-order.html`
  (`course_vocab_stroke_order_keyboard`), but these paths are only reachable from
  the removed V2 frontend / old in-chat course steps, so there is no live 404 in
  the V3 flow. Follow-up: repoint or remove those legacy references.
- `hsk-lugat.html` `goBackToStudy()` has a dead `study.html` branch; the dictionary
  is only opened from `course-v3.html` with `?theme=light`, so the live path always
  returns to `course-v3.html`.

### 2026-06-27 — Course v3 real pronunciation (microphone) scoring

Changed:
- Replaced the mocked random-score pronunciation checks with real microphone + server speech-to-text scoring in all course v3 sections that need a mic.
- Added `VoicePracticeService.score_pronunciation()` and `POST /api/voice-practice/pronounce`: verifies Telegram initData, gates paid users through the existing AI usage budget, transcribes audio via `transcribe_voice_with_usage`, and scores by CJK character match against the target word (`score>=60` passes). Usage recorded with source `voice_practice_pronounce`.
- `course_v3_pronunciation.html` (standalone Talaffuz mashqi) and the in-lesson `pronunciation` card in `course-v3.html` now record with `MediaRecorder`/`getUserMedia` and call the new endpoint instead of `Math.random()`. UZ/RU/TJ status/error strings added.
- AI Voice (`course_v3_voice.html`) already used a real mic and was left unchanged.

Why:
- The two pronunciation exercises only had the mic UI; they never opened the microphone and returned a fake random score.

Files touched:
- `app/services/voice_practice_service.py`
- `app/main.py`
- `app/static/course_v3_pronunciation.html`
- `app/static/course-v3.html`

Risk:
- No payment/subscription/access rules changed. Pronunciation scoring shares the existing AI budget gate for paid users.
- Scoring is character-match from STT, not per-syllable tone analysis. In-lesson failed attempts do NOT cost a heart and always allow continue (no soft-lock).
- Needs real Telegram WebView smoke test (mic permission + initData + OpenAI key) after deploy; browser preview returns 401 without initData.

### 2026-06-27 — Course v3 HSK exams functional (Test markazi)

Changed:
- Course v3 Test markazi (`course_v3_test.html`) HSK 1-4 imtihonlari endi real
  ishlaydi. Avval kartochkalar har doim "Material tayyorlanmoqda" bo'sh holatini
  ko'rsatardi (savol fayllari yo'q edi).
- Added per-level exam material files `app/static/course_v3_data/exams/hsk{1..4}.json`
  (schema_version 1; `sections` → listening/reading/writing; question types
  `audio_truefalse`, `audio_choice`, `text_choice`; multilingual uz/ru/tj).
- `course_v3_test.html` now loads that JSON and runs a real exam: section-grouped
  questions, TTS playback (`speak()`, `lang=zh-CN`) for listening, client-side
  grading, and a per-section result screen (reuses placement `.pl`/`.opt`/`.res` UI).
- Added route `/course_v3_data/exams/{filename}` in `app/main.py` (filename
  whitelisted to `hsk[1-4].json`).
- Hub exam cards now show real question/duration counts (14/12/12/12) instead of
  placeholder 40/60/80/100.

Why:
- HSK exam cards were dead (always empty state); the interface existed but the
  question material/runner did not.

Files touched:
- `app/static/course_v3_data/exams/hsk1.json` .. `hsk4.json` (new)
- `app/static/course_v3_test.html`
- `app/main.py`

Risk:
- Frontend + static data only; payment/subscription/progress logic unchanged.
- Exam result is client-side and NOT persisted to the server (like placement);
  add an endpoint if admin stats need it.
- Listening uses browser TTS; if device has no zh-CN voice, audio may be silent
  but option text still shows.
- Current scope is a simplified practice exam (~12-14 questions/level), not the
  full 40-100 question real HSK.

### 2026-06-26 — Course v3 static lesson data files

Changed:
- Added schema v2 static lesson JSON files under `app/static/course_v3_data/{hsk1,hsk2,hsk3,hsk4}/`.
- Coverage now includes HSK1 lessons 1-15, HSK2 lessons 1-15, HSK3 lessons 1-20, and HSK4 lessons 1-20.
- Each lesson includes multilingual UZ/RU/TJ subtitles, active words, grammar, dialogue, intro/practice/dialog sections, and frontend-supported card types.

Why:
- `course-v3.html` loads lesson flow content from `/course_v3_data/{level}/lesson_XX.json` and needs complete standalone lesson files for HSK1-HSK4.

Files touched:
- `app/static/course_v3_data/hsk1/lesson_01.json` through `lesson_15.json`
- `app/static/course_v3_data/hsk2/lesson_01.json` through `lesson_15.json`
- `app/static/course_v3_data/hsk3/lesson_01.json` through `lesson_20.json`
- `app/static/course_v3_data/hsk4/lesson_01.json` through `lesson_20.json`

Risk:
- Data-only change; no subscription, payment, backend result, or progress logic changed.

Follow-up:
- After deploy, test HSK level switching once v3 maps expose HSK2-HSK4 paths in the UI.

### 2026-06-26 — Course v3 access and progress hardening

Changed:
- Course v3 map files now expose real HSK1-HSK4 lesson counts with zeroed preview progress, not fake/demo XP.
- `/api/v3/map` keeps unpaid users limited to lessons 1-3 and marks lesson 4+ as premium-locked even when lesson progression would otherwise make the next node current.
- Added `/api/v3/lesson/complete` so Telegram users complete v3 lessons through the backend, with initData auth, sequential progress checks, gamification award, and the same free lesson limit.
- `course-v3.html` now waits for server completion before locally unlocking the next lesson for authenticated Telegram users.
- Fixed static lesson fallback ordering in `CourseMiniAppLessonFlowService` so DB/test payload content is not overwritten by static fallback files.
- Course v3 now respects `?level=` and `localStorage.hsk_v3_level`; onboarding passes the selected level into the main course URL so HSK4 opens HSK4 map and lesson JSON.
- Added Course v3 level picker from the HSK pill.
- Course v3 invite share now uses `/api/v3/invite`, which reuses `ReferralService` and the same referral link format as `/invite`; frontend opens Telegram share with ready text instead of making copy the main flow.
- Lesson intro cards were reshaped into a more Duolingo-like flow: word flash, listening pick, meaning pick, hanzi pick, then grammar.

Why:
- Prevent unpaid users from bypassing the Course v3 paywall by completing lessons locally.
- Remove demo progress data from the user-facing course map.
- Make v3 lesson progress server-authoritative for real Telegram users.
- Preserve selected HSK level across onboarding, reload, and lesson fetches.
- Avoid broken hardcoded referral links and reduce invite friction.

Files touched:
- `app/main.py`
- `app/static/course-v3.html`
- `app/static/course_v3_onboarding.html`
- `app/static/course_v3_data/{hsk1,hsk2,hsk3,hsk4}.json`
- `app/services/course_miniapp_lesson_flow_service.py`
- `tests/test_course_v3_static_data.py`

Risk:
- The v3 completion endpoint assumes course lessons are seeded in the database with level and order matching the static maps.
- Voice/rating/pronunciation demo text is outside this patch and still needs a separate real-backend audit.
- `/api/v3/invite` requires valid Telegram initData; local browser preview falls back to a plain bot link without referral attribution.

### 2026-06-26 — Mode selection required-channel edit resume

Changed:
- Start mode selection forced-channel gate now edits the existing mode message into the channel list instead of sending a separate block.
- After channel subscription is confirmed, the same message is edited into the selected path: Course shows the Course Mini App entry button; QA shows level selection first.
- QA level selection from this path marks the user as QA mode, then sends the normal first-message prompt with the main reply keyboard.

Why:
- New users should not get duplicate stacked bot blocks during mode selection and required-channel verification.

Files touched:
- `app/bot/handlers/course.py`
- `app/bot/handlers/required_channel.py`
- `app/bot/handlers/start.py`
- `app/bot/fsm/onboarding.py`
- `tests/test_course_miniapp_onboarding.py`

Risk:
- Required-channel/payment rules were not changed; this only changes message edit/resume behavior in the mode-selection path.

### 2026-06-25 — Subscription entry source analytics

Changed:
- Added `subscription_entry_events` to track which source brought a user into the Subscription Mini App.
- `/api/subscription-miniapp/overview` records the source from the Mini App URL payload only after the user actually opens the subscription Mini App.
- Admin `Statistika` now shows `OBUNA MANBALARI` with all-time and 7-day unique users/open counts by source.

Why:
- Admin needs to see which bot/Mini App branches drive the most interest toward subscription.

Files touched:
- `app/db/models/subscription_entry_event.py`
- `alembic/versions/0053_add_subscription_entry_events.py`
- `app/services/subscription_entry_analytics_service.py`
- `app/main.py`
- `app/bot/handlers/admin.py`

Risk:
- Requires Alembic migration `0053_add_subscription_entry_events`; payment and access rules were not changed.

### 2026-06-25 — Admin stats legacy blocks removed

Changed:
- Admin `Statistika` panel no longer shows legacy `DAILY 3-MIN`, `COURSE PILOT 1-3`, `TRIAL FUNNEL`, `TRIAL -> PAYMENT`, old `FUNNEL unique`, `O'QISH REJIMI`, or `course_progress` reminder counts.
- Current course analytics are limited to `course_miniapp_events` based `KURS` and `KURS MINI APP` sections plus general real user/payment/referral stats.

Why:
- Legacy course/trial/daily/pilot tables mixed old-version users with current Mini App activity and made admin stats misleading.

Files touched:
- `app/bot/handlers/admin.py`

Risk:
- Historical legacy funnel data is still stored in the database and other services, but it is intentionally hidden from the main admin stats report.

### 2026-06-25 — Admin course statistics Mini App source fix and Uzbek label cleanup

Changed:
- Admin `Statistika` panel keeps the detailed report, but the `KURS` block no longer counts legacy `course_progress` users as current course signups.
- `KURS` block now uses `course_miniapp_events` distinct `telegram_id` counts for Mini App opened, lesson started, and lesson completed users.
- Remaining visible admin/user labels found in bot handlers, admin keyboards, release feedback, help settings, Mini App pilot skeleton, funnel analytics, rich quiz message, and Voice Practice errors were aligned to Uzbek/current wording.

Why:
- Course stats were showing old-version course users together with users who moved to the Mini App; the current report must reflect post-Mini App activity.

Files touched:
- `app/services/admin_stats_service.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/commands.py`
- `app/bot/keyboards/admin_broadcast.py`
- `app/bot/keyboards/release_feedback.py`
- `app/services/conversion_funnel_service.py`
- `app/services/course_miniapp_admin_analytics_service.py`
- `app/services/course_miniapp_lesson_service.py`
- `app/services/help_settings_service.py`
- `app/services/rich_message_service.py`
- `app/services/voice_practice_service.py`
- `tests/test_admin_stats_service.py`

Risk:
- Users who used legacy course only and never opened the Mini App are intentionally excluded from the `KURS` Mini App counts.

### 2026-06-26 — Admin control Mini App

Changed:
- Added an admin-only Telegram Mini App at `/admin-control.html`.
- Added `/api/admin-miniapp/overview` for read-only admin dashboard data and `/api/admin-miniapp/open-section` to send existing Telegram admin section buttons back to the admin chat.
- `/admin` and admin `Statistika` now include a WebApp button for the admin Mini App.

Why:
- Admin needs a Mac/iPhone friendly control center without replacing existing Telegram admin FSM flows for payments, QR upload, channels, ads, discounts, and access actions.

Files touched:
- `app/static/admin-control.html`
- `app/services/admin_miniapp_service.py`
- `app/main.py`
- `app/bot/handlers/admin.py`
- `app/bot/utils/course_miniapp.py`

Risk:
- Read-only dashboard data plus Telegram admin section shortcuts; no payment, subscription, access, or course write logic was changed.

### 2026-06-25 — Course Mini App static data split and HSK1 static lesson pilot

Changed:
- `study.html` no longer embeds the full HSK1-4 course data blob; it lazy-loads whitelisted `/course_data/{level}.json` files.
- `CourseMiniAppLessonFlowService` checks `app/static/course_content/{level}/lesson_XX.json` first and falls back to the existing generated/server payload when no static lesson exists.
- HSK1 lessons 1-3 now have static 6-section JSON pilots; HSK2-HSK4 still use the legacy backend flow.

Why:
- Keep Mini App UI files lightweight and separate render/navigation code from course material and lesson card content.

Files touched:
- `app/main.py`
- `app/static/study.html`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/course_data/*.json`
- `app/static/course_content/hsk1/lesson_01.json` through `lesson_03.json`

Risk:
- Legacy generated lesson/card fallback remains active for non-static lessons.
- Graphify AST update was attempted but refused to overwrite because the rebuilt graph had fewer nodes than the existing graph.

### 2026-06-25 — Mini App HSK character dictionary data split

Changed:
- `Training -> Ierogliflar` dictionary flow now has the lightweight `hsk-lugat.html` shell backed by separate `/hsk-data.js`.
- HSK dictionary data includes HSK1-4 words/strokes, 157 HSK4 example sentences from the provided generator, and 100 HSK4 grammar explanations sourced from `hsk4.html`.
- The dictionary supports `?level=` filtering for HSK1/2/3/HSK4 上/下 and `?lang=` for UZ/RU/TJ, with a visible language switch and return to Training.

Why:
- The previous route existed but the static dictionary file/data needed to be connected and HSK4 entries needed examples plus understandable grammar context.

Files touched:
- `app/main.py`
- `app/static/hsk-lugat.html`
- `app/static/hsk-data.js`

Risk:
- Payment/subscription/access rules were not changed.
- HSK4 examples are available for 157 entries; remaining HSK4 entries still show word meaning and may show grammar only when matching an HSK4 grammar rule.

Follow-up:
- After deploy, smoke-test Telegram Mini App `Training -> Ierogliflar` in UZ/RU/TJ and check HSK4 上/下 filtering.

### 2026-06-25 — Mini App rating profile Telegram chat

Changed:
- Mini App leaderboard API now includes safe `username` and `telegram_id` fields for ranked users, so the rating profile sheet can open the user's existing Telegram chat instead of creating an in-app chat.
- Rating UI now shows paid users with a custom premium mark before the nickname and uses CSS-drawn medals for the top ranking positions instead of emoji badges.
- Leaderboard is no longer capped to 25 by default; `CourseGamificationService.leaderboard()` returns all same-league users unless an explicit limit is passed, and `league_size` reflects the real row count.
- Leaderboard rows also include safe course progress summary fields (`course_level`, `completed_lessons`, `total_xp`) for the rating profile sheet.
- Telegram Mini App viewport height is synced from `Telegram.WebApp.viewportHeight/stableHeight` through `study.html` into `study-v2.js`, so the fixed bottom nav stays inside the visible Mini App viewport.

Why:
- User-to-user contact from rating profiles should stay inside Telegram chat UX, and subscription status should be visible without using plain emoji/checkmark text.

Files touched:
- `app/services/course_gamification_service.py`
- `app/static/study-v2.js`
- `app/static/study-v2.css`

Risk:
- No subscription/payment/access rules changed.
- Direct Telegram chat opens only when Telegram username or user deep-link id is available.

Follow-up:
- After deploy, test a real Telegram Mini App rating profile for a user with username and one without username.
- Also test on Telegram iOS after opening the Mini App fresh: bottom nav should be visible without scrolling.

### 2026-06-25 — Mini App user challenge flow

Changed:
- Added `course_challenges` for Mini App user-to-user belashuv/challenge state. A challenge stores a frozen JSON question payload so both users get identical questions even if they complete at different times.
- Challenge lifecycle: `pending` invite, opponent `accept`/`reject`, each user completes once, then winner is calculated by score and tie-broken by faster duration.
- Mini App endpoints: list/create/respond/start/submit under `/api/miniapp/challenges`.
- Bot sends opponent an inline accept/reject notification and also exposes the same incoming challenges in the Mini App profile notification block.
- Rating profile can start a challenge from a ranked user; profile notifications show pending/active/completed challenges.

Risk:
- `Base.metadata.create_all()` creates the new table on startup, but existing DBs should still be tested after deploy for table creation.
- Challenge submit is one-shot per user; there is no rematch button yet.

Follow-up:
- Test with two real Telegram users: start from rating profile, accept from bot and Mini App profile, complete both sides, verify result/winner.

### 2026-06-25 — Mini App lesson material journey

Changed:
- Mini App lesson card generation now builds deterministic section-purpose material from the selected section `active_words` instead of accepting unscoped payload quiz fallbacks.
- Generated cards use indexed source-backed activities such as `activity:meaning:1`, `activity:listening:2`, `activity:gap:1`, so review/listening/usage sections do not all collapse into the same generic question.
- Listening cards keep `audio_text` only for playback; the frontend no longer displays the answer text inside the listening prompt and shows an audio waveform-style button instead.
- Generic fill-blank questions such as “Men bugun ____ so'zini o'rgandim” were removed from Mini App quiz generation; gap-fill cards now require a real lesson/example sentence containing the target word.
- Completing the final book lesson of a level in the Mini App now advances course progress to the next level and returns a server `next_book_lesson` ref plus concrete localized praise text.

Why:
- The previous generated cards could feel random/quiz-like, could produce fake blank prompts where every option fit, and the listening UI could reveal the heard word visually, which made the lesson flow poor despite correct section routing.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/study.html`
- `tests/test_course_miniapp_lesson_flow.py`
- `tests/test_course_miniapp_lesson_service.py`

Risk:
- Payment/subscription/QA/voice access logic was not changed.
- Graphify code graph was updated after the Mini App lesson logic changes.

Follow-up:
- After deploy, test a real Telegram Mini App lesson `1.3 Tinglash` and confirm the listening card plays audio while hiding the answer text.

### 2026-06-24 — Mini App server section plan source-of-truth

Changed:
- Mini App course path now loads a server-backed `course-section-plan` instead of building visible path nodes from static `COURSE_DATA.VOCAB`.
- Section plan and lesson flow share `CourseMiniAppLessonFlowService._section_plan()`, so path nodes and lesson cards use the same `section_key`, `section_no`, `active_words`, lock/completion status, and next section refs.
- Every book lesson now has six fixed learning-stage sections regardless of vocabulary count: intro, reinforcement, listening/pronunciation CTA, usage, short dialog, and review. Short lessons reuse the same lesson words across stages instead of jumping from `1.2` to `2.1`.

Why:
- Path node labels and opened lesson content previously came from different runtime sources, which could show one section in the path but open different material in the lesson.

Files touched:
- `app/main.py`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/study.html`
- `app/static/study-v2.js`
- `tests/test_course_miniapp_lesson_flow.py`
- `tests/e2e/test_miniapp_smoke.py`

Risk:
- Payment/subscription/QA logic was not changed.
- Graphify update refused to overwrite because the rebuilt graph had fewer nodes than the existing graph; do not force update without checking graph inputs.

Follow-up:
- After deploy, verify a real Telegram Mini App user opens path node `1.2` and lesson header/cards show the same `section_key` and `active_words` from server logs.

### 2026-06-24 — Mini App locked lesson readiness jump

Changed:
- Locked/future course path nodes are no longer ignored in the Mini App; explicit node taps open a short readiness test built from lessons up to the selected lesson.
- After the test, users can continue from the selected section even with a low score, with a short warning that the chosen lesson may be difficult.
- Confirming the jump calls a server endpoint that moves `course_progress.current_lesson_id` to the selected book lesson and records the test result in Mini App analytics.

Why:
- Users who intentionally choose a later lesson need a guided override instead of a dead locked tap, while server progress must still become the source of truth before lesson content opens.

Files touched:
- `app/main.py`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/study.html`
- `app/static/study-v2.js`
- `tests/test_course_miniapp_lesson_flow.py`

Risk:
- Payment/subscription logic was not changed.
- The readiness test uses existing Mini App course quiz material; lesson content itself is still loaded from the server after confirmation.

Follow-up:
- After deploy, test a locked path node such as `1.4`: complete the readiness test, continue despite low score, and verify the opened section header/content match the selected node.

### 2026-06-24 — Mini App lesson section source-of-truth fix

Changed:
- Course lesson flow no longer falls back from an unknown requested `section_key` to section `1`; server now returns `course_section_not_found`.
- Lesson flow response includes server `active_words`; frontend logs `level`, `lesson_order`, `section_key`, `section_no`, `book_lesson_order`, and `active_words` at lesson start.
- Broken lesson-flow microphone and fake stroke-order cards were removed from generated flows; activity generation now validates card count, source words, broken types, and diversity.

Why:
- Path nodes could show one section while the opened lesson used another section's content because local frontend section guesses and server fallback hid section mismatches.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/study-v2.js`
- `tests/test_course_miniapp_lesson_flow.py`
- `tests/e2e/test_miniapp_smoke.py`

Risk:
- Payment/subscription/QA logic was not changed.
- Real stroke order remains available in character dictionary/stroke pages, not inside lesson flow.

Follow-up:
- After deploy, test Telegram WebView path node `1.2`, next `1.2 -> 1.3`, and verify console debug active words match the opened section.

### 2026-06-24 — Mini App tests and character dictionary cleanup

Changed:
- Test Center HSK 1-4 mock exams are visually grouped into one bordered HSK tests block.
- The Pinyin test entry was removed from Test Center; Training no longer shows Writing, Pinyin, or separate Speaking entries.
- Training → Characters now opens `/hsk-lugat.html`, a standalone HSK 1-4 character dictionary with stroke animation, back routing to `study.html?tab=training`, and UZ/RU/TJ meanings sourced from existing course data.

Why:
- The training/test menu needed to be simplified and the user-provided character dictionary needed to be connected to the Mini App flow.

Files touched:
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/hsk-lugat.html`
- `app/main.py`

Risk:
- Payment/subscription logic was not changed; the Characters dictionary entry still uses the existing `training_test` feature lock.

Follow-up:
- After deploy, smoke-test in Telegram WebView: Tests tab, Training → Characters dictionary, RU/TJ language switch, and back button to Training.

### 2026-06-24 — AI Voice dialog-count session flow

Changed:
- AI Voice paid call UX no longer auto-closes by a 25-second frontend timer.
- Voice sessions now use a 7-dialog backend limit, where one user voice message plus one bot answer counts as one dialog.
- Session start returns a localized Chinese opening message (`你好`/`嗨`) that the frontend speaks before the user starts.
- The final AI reply is instructed to make a natural excuse and say goodbye; the backend returns `session_should_end` so the frontend ends after playing that reply.
- Voice reply latency was reduced by shortening the transcription prompt, limiting recent chat history, lowering AI reply token budget, and recording audio in smaller lower-bitrate chunks.

Why:
- Users need a longer-feeling practice than 25 seconds, but the product still needs a clear cost/session cap and faster turn response.

Files touched:
- `app/services/voice_practice_service.py`
- `app/services/ai_service.py`
- `app/static/voice-practice.html`
- `tests/test_voice_practice_course_context.py`

Risk:
- Payment/subscription/access logic was not changed.
- Real Telegram WebView should still be smoke-tested for microphone latency, opening speech playback, and automatic final summary after the 7th dialog.

Follow-up:
- If latency remains high in production, the next real improvement is streaming/realtime voice instead of the current transcribe-then-chat pipeline.

### 2026-06-24 — Course section sequence and next-section routing fix

Changed:
- Course Mini App book lesson sections now unlock only when all previous sections in the same book lesson are completed.
- Book lesson access now follows `course_progress.completed_lessons_count`, so manual requests cannot jump to later book lessons before prior book lessons are complete.
- Section completion response now returns structured `next_section` and `next_book_lesson` refs; the frontend next button uses those server refs and only falls back within the current book lesson.

Why:
- Users could finish `1.1` and jump to `1.3`/another section because frontend next/current logic relied too much on local calculation and backend section unlock only checked the immediate previous key.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/study-v2.js`
- `tests/test_course_miniapp_lesson_flow.py`
- `tests/e2e/test_miniapp_smoke.py`

Risk:
- Payment/subscription approval logic was not changed.
- Existing corrupted local section completion can still be rejected server-side with `course_section_not_unlocked`; users may need to reopen the first incomplete section.

Follow-up:
- After deploy, smoke-test in Telegram WebView: complete `1.1`, press next to `1.2`, then verify locked manual taps show the previous-section message/paywall.

### 2026-06-24 — AI Voice paid budget integration

Changed:
- Mini App AI Voice now uses the existing AI usage budget gate for paid users before starting a session and before processing each voice turn.
- Voice transcription and AI reply costs are recorded into `ai_usage_events` with sources `voice_practice_transcribe` and `voice_practice_reply`.
- Frontend handles existing budget cooldown/depleted codes with user-facing RU/TJ/UZ messages instead of treating every 403 as a generic paywall.

Why:
- Paid Voice Practice must share the same payment-derived AI budget rule as text/photo AI: roughly 50% of payment revenue is available for AI costs, with cooldown/depletion handling managed by `AIUsageBudgetService`.

Files touched:
- `app/services/voice_practice_service.py`
- `app/static/voice-practice.html`
- `tests/test_voice_practice_course_context.py`

Risk:
- Payment approval and subscription creation were not changed.
- Existing paid users without an active budget remain allowed because `AIUsageBudgetService.can_use_ai()` already allows no-budget users; users with active budgets now have Voice Practice counted against that budget.

Follow-up:
- Smoke-test one paid Voice Practice call after deploy and verify `ai_usage_events.source` contains `voice_practice_transcribe` and `voice_practice_reply`.

### 2026-06-23 — Course lesson quality, AI Voice access, and duplicate UX cleanup

Changed:
- Course Mini App lesson generation no longer creates sentence-build tasks from single Hanzi fragments like `以` + `前`; fallback sentence tasks now use short natural Chinese phrases.
- Character-writing cards became passive writing-order practice: users see the stroke/order hint and confirm completion instead of being forced to draw.
- Fixed a lesson generation crash caused by an undefined `zh` variable in grammar fallback cards.
- AI Voice paid users now receive subscription-based access (`remaining_voice_limit = -1`) instead of a hard daily session count; free users still keep the existing one-time trial gate.
- AI Voice frontend now exposes only two roles: Chinese friend and Li Laoshi. Unsupported level/settings controls are hidden.
- Profile removed duplicate subscription/league shortcuts and added local avatar upload. League rows are clickable and the League tab owns the main leaderboard/podium entry point.

Why:
- Users reported many lessons failing to open, unnatural dialogs, overly hard word-building tasks, and cluttered AI Voice/Profile/League UX.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/services/voice_practice_service.py`
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/voice-practice.html`
- `tests/test_course_miniapp_lesson_flow.py`

Risk:
- Payment backend and subscription approval flow were not changed.
- Real Telegram WebView should still be smoke-tested after deploy for voice paywall routing, avatar upload, and lesson card rendering.

### 2026-06-23 — Mode selection required-channel gate

Changed:
- Language selection now shows Course/Oddiy mode first, then required-channel subscription is checked when the user chooses either mode.
- If the user is missing required channel subscription, the selected mode is stored in FSM data and resumed after `force_sub:check`: Course sends the Course Mini App entry, Oddiy mode activates QA mode.

Why:
- Forced channel subscription should start after the user chooses Course or Oddiy mode, not before the mode selection screen.

Files touched:
- `app/bot/keyboards/onboarding.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/required_channel.py`
- `app/bot/middlewares/required_channel.py`
- `tests/test_course_miniapp_onboarding.py`

Risk:
- Telegram bots cannot truly auto-open a WebApp from a subscription check callback; the bot resumes the flow and sends the Course Mini App WebApp button automatically.

Follow-up:
- Smoke-test new `/start` users in Telegram for both Course and Oddiy mode with subscribed and unsubscribed channel states.

### 2026-06-23 — Course Mini App lesson variety and section unlock recovery

Changed:
- Course Mini App section lessons now include varied activity units inside the same path node: word intro, listening/audio choice, character trace, short dialog, sentence build, pronunciation, and review cards.
- Long word-order tasks are filtered out and replaced with short Chinese character/word builds so users are not asked to assemble long RU/TJ translations.
- Short dialog generation now uses natural templates by word type and special handling for awkward verbs like `赚`.
- Lesson open/complete APIs accept same-lesson client-completed section keys as recovery input when server analytics events lag behind local progress.

Why:
- Users were seeing repetitive multiple-choice sections, overly hard word assembly, unnatural dialogs, and locked sections after local completion.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/main.py`
- `app/static/study.html`
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `tests/test_course_miniapp_lesson_flow.py`

Risk:
- Client-completed recovery only counts valid previous sections in the same book lesson; payment/subscription/referral logic is unchanged.

Follow-up:
- Replace the current tap-to-confirm character trace MVP with real canvas stroke detection if higher accuracy is needed.

### 2026-06-23 — Mini App reward, league, and AI Voice paywall UX

Changed:
- Course Mini App lesson completion now shows a sequential reward experience: result, streak progress, and league movement using an HSK AI-owned `汉` mascot instead of copied Duolingo-style characters.
- League tab now renders a trophy track and ranked rows with special top-3 medals, while still using existing gamification data/fallback rows.
- AI Voice tab opens even when voice access is exhausted; the paywall appears at call/session start instead of blocking the tab. Voice paywall/subscription buttons route back to the existing Mini App subscription flow through the parent shell.
- AI Voice settings removed the unsupported help/support block and no longer claims limits refresh daily.

Why:
- Course rewards and league movement need Duolingo-like dopamine UX while keeping HSK AI visual identity and preserving existing subscription/payment logic.

Files touched:
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/voice-practice.html`

Risk:
- Changes are frontend UX only; payment/subscription backend logic was not changed.
- Real Telegram WebView should be smoke-tested for AI Voice paywall routing and reward screen layout.

Follow-up:
- Add browser/E2E screenshot coverage once local Playwright/Chrome runtime is available.

### 2026-06-23 — Course Mini App migration deploy fix

Changed:
- `0052_course_miniapp_v3_preferences` now drops existing `daily_minutes` check constraints from the Postgres catalog before recreating the canonical constraint with raw SQL.
- `CourseMiniAppProfile` uses naming-convention source names (`goal`, `daily_minutes`, `start_mode`) so SQLAlchemy does not double-prefix generated constraint names.
- Bot help and Mini App profile support now use the configured admin contact URL.

Why:
- Railway deploy failed when production had a naming-convention generated `daily_minutes` constraint name that did not match the migration's static drop list.

Files touched:
- `alembic/versions/0052_course_miniapp_v3_preferences.py`
- `app/db/models/course_miniapp_profile.py`
- `app/services/help_settings_service.py`
- `app/services/study_miniapp_service.py`
- `app/static/study.html`
- `app/static/study-v2.js`

Risk:
- Low. Migration is Postgres-focused and only changes the Course Mini App profile check constraint; payment/subscription logic is untouched.

### 2026-06-23 — Course Mini App section/chapter/book lesson progression

Changed:
- Course Mini App lessons now have three progress levels: section, chapter, and book lesson.
- HSK book material remains in `course_lessons`; Mini App splits each book lesson into deterministic section nodes by vocabulary count, grouped visually into A/B/C chapters.
- Darslar/Course page keeps the Duolingo-style road/path and renders sections as path nodes inside chapter groups instead of converting to a list/table.
- Every section includes a short context dialog card; long textbook dialogue screens are not restored.
- Completion now records `section_completed`, `chapter_completed`, and `book_lesson_completed`; legacy `lesson_completed` is still recorded only when the whole book lesson is complete for admin compatibility.
- XP is server-side at all three levels: section small XP, chapter bonus XP, book lesson bonus XP. Payment/subscription/referral logic was not changed.

Why:
- Large HSK book lessons must feel like small learning steps while preserving HSK material order and the existing Course path UX.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/db/models/course_miniapp_event.py`
- `app/services/course_miniapp_admin_analytics_service.py`
- `app/main.py`
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/study.html`
- `tests/test_course_miniapp_lesson_flow.py`

Risk:
- Completed section state is stored server-side through analytics/dedupe events, while the current frontend also mirrors section completion in local storage for immediate path rendering.
- Browser E2E still depends on Playwright/pytest availability in the local runtime.

### 2026-06-23 — Mini App AI Voice embedded UX fix

Changed:
- Course Mini App V3 AI Voice iframe now uses parent page height instead of subtracting the top/nav chrome twice, so start/call controls stay visible inside Telegram.
- Embedded AI Voice mode uses compact sizing, reduced background motion, direct end-call behavior, and posts `hsk_voice_close` back to the V3 shell instead of trying to close the whole Telegram Mini App from inside the iframe.
- The V3 quiz page no longer shows the visible `Quiz/Квиз` title header; lesson/test quiz routes and filters remain available.

Why:
- On iPhone Telegram WebView, AI Voice entry/call/summary controls could fall below the visible area or sit under the bottom nav, and the summary close action did not reliably return users to the Mini App shell.

Files touched:
- `app/static/study.html`
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/voice-practice.html`
- `tests/e2e/test_miniapp_smoke.py`

Risk:
- Browser E2E could not run locally because Playwright/pytest/Chrome are not installed in the available environments; JS syntax and Python compile checks passed.

### 2026-06-23 — Course Mini App V3 navigation, rewards, and training

Changed:
- Course Mini App V3 uses exactly five bottom tabs: Home, Lessons, League, AI Voice, Profile. Test is available from Home as a Test Center, not as a sixth nav tab.
- Free users see one-time access locks for lesson, AI Voice, placement, and training/test features through existing subscription checks; payment backend and entitlement logic were not changed.
- Server gamification now returns non-blocking energy, weekly same-league leaderboard metadata, and reward chest state. Reward chest opens through `/api/miniapp/reward-chest/open` and awards XP only.
- XP rules now match V3 product rules: lesson 20 XP, test 10 XP, training 8 XP, AI Voice 10 XP, mistake review 5 XP, with existing streak bonus.
- Training/Test Center now includes HSK1-HSK4 tests, placement, listening, pronunciation, writing, characters, pinyin, speaking, and mistake review.
- Onboarding daily time supports 10, 15, 20, and 30 minutes. Alembic head is `0052_course_miniapp_v3_preferences`.
- AI Voice Mini App call UI auto-closes paid calls around 25 seconds with a short Chinese goodbye; voice payment/access backend remains unchanged.

Why:
- V3 product decision keeps Course Mode inside the Mini App with Duolingo-style navigation, rewards, and practice while preserving Telegram QA and payments.

Key files:
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/study.html`
- `app/static/voice-practice.html`
- `app/services/course_gamification_service.py`
- `app/services/course_miniapp_practice_service.py`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/services/course_mistake_service.py`
- `app/services/voice_practice_service.py`
- `app/main.py`
- `alembic/versions/0052_course_miniapp_v3_preferences.py`

Risk:
- Migration `0052` must be applied before users select 30-minute onboarding goals.
- Browser E2E depends on Playwright/pytest availability in the runtime; local unit/syntax checks cover backend and script validity.

### 2026-06-23 — Course Mini App entry stays in QA mode

Changed:
- Bot-side Course entry points now send a short Course Mini App message with a WebApp button and keep `users.learning_mode = "qa"`.
- QA daily-limit messaging now shows exactly one block: first-lesson Mini App offer only before course trial usage; text/referral limit block after `trial_course_started_at`, `trial_course_completed_at`, `trial_quiz_explanation_used_at`, or a `quiz_completed` funnel event.
- Automatic post-QA course promo image/text was disabled.
- Course Mini App lesson flow no longer depends on `learning_mode = "course"`; it initializes `course_progress` and trial lesson access from the Mini App request.

Why:
- Course moved fully into Mini App, while Telegram chat should remain normal QA mode.

Files touched:
- `app/bot/handlers/messages.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/start.py`
- `app/bot/handlers/menu.py`
- `app/bot/handlers/commands.py`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/services/course_miniapp_onboarding_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/repositories/course_lesson_repo.py`

Risk:
- Existing old Course callback messages may still reach legacy handlers, but all main visible entry points now route to Mini App.

Follow-up:
- In Telegram, smoke-test QA daily limit for users with and without course trial history, plus Course Mini App lesson open/complete from QA mode.

### 2026-06-23 — Course Mini App AI Voice, profile locks, and admin analytics

Changed:
- AI Voice characters now use the current Course Mini App lesson context. `voice_practice_sessions` stores `lesson_id` and `target_words`, and voice prompts receive lesson vocabulary for Lily, Chen, Xiao Mei, Teacher Li, and Manager Wang.
- Course Mini App Profile is server-backed via `/api/miniapp/profile`, including user info, level, subscription status, XP/streak/league, completed lessons, mistakes count, and feature lock state.
- Mini App lock UI now follows server `course_features` for lesson, voice, placement, and training/test access. Payment/subscription entitlement remains in the existing access services.
- Admin stats now include Course Mini App funnel, lesson drop-off, test/training completion, AI Voice usage, mistake review, XP/streak activity, and Mini App paid conversion.
- Payment approval records an idempotent `subscription_approved` Course Mini App analytics event after the existing subscription activation succeeds; payment backend behavior was not changed.
- Alembic head is `0051_connect_voice_to_course`.

Key files:
- `app/services/voice_practice_service.py`
- `app/services/study_miniapp_service.py`
- `app/services/course_miniapp_admin_analytics_service.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/commands.py`
- `app/bot/handlers/admin_payments.py`
- `app/static/study-v2.js`
- `app/static/voice-practice.html`
- `alembic/versions/0051_connect_voice_to_course.py`

Risk:
- Migration `0051` must run before course-connected AI Voice traffic reaches production.
- Admin stats depend on `course_miniapp_events` being populated; missing historic events will show as zero rather than inferred.

### 2026-06-23 — Server XP, streak, and weekly league

Changed:
- Added idempotent `course_xp_events` and server-owned XP/streak fields on `course_miniapp_profiles`.
- Server-confirmed lesson, test, training, AI Voice, and mistake review completions now award XP; the first meaningful activity of a local day also awards a streak bonus.
- Added weekly leaderboard data for users in the same XP league and exposed gamification through access and Mini App APIs.
- Alembic head is `0050_add_course_gamification`.

Why:
- XP, streak, and league progression must not be granted by editable browser state.

Risk:
- Migration `0050` must run before the new gamification code receives production traffic.
- Existing payment and subscription approval logic was not changed.

Follow-up:
- Phase 8 connects AI Voice characters to the current course lesson vocabulary.

### 2026-06-23 — Server-backed Course Mistake Engine

Changed:
- Added `course_mistakes`, which aggregates lesson, test/training, and AI Voice corrections by word, grammar, character, and pronunciation weakness.
- Added authenticated mistake overview and idempotent personalized review APIs; review questions are server-graded and tied to server-issued session events.
- Mistake review uses the existing shared `training_test` one-time free entitlement. Paid access still follows the existing subscription check.
- Added `mistake_review_started` and `mistake_review_completed` analytics. Alembic head is `0049_add_course_mistakes`.

Why:
- Personalized mistake review needs persistent cross-feature data instead of browser-only `localStorage`.

Files touched:
- `app/db/models/course_mistake.py`
- `app/services/course_mistake_service.py`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/services/course_miniapp_practice_service.py`
- `app/services/voice_practice_service.py`
- `app/main.py`
- `app/static/study.html`
- `app/static/study-v2.js`
- `alembic/versions/0049_add_course_mistakes.py`

Risk:
- Migration `0049` must run before mistake collection receives production traffic.
- Payment handlers, payment tables, and subscription approval logic were intentionally not changed.

Follow-up:
- Phase 7 should move XP, streak, and league state from browser storage to the server.

### 2026-06-23 — Course Mini App backend foundation

Changed:
- Added server-side Course Mini App profile preferences, one-time feature usage records, and a dedicated analytics event store.
- Course access payload now exposes lesson, voice, placement, and training/test entitlements without changing payment approval or subscription rules.
- Existing completed lesson trials and voice sessions are treated as already used, so migration cannot reopen free features.
- Trusted completion events are server-only; client analytics events cannot grant progress or access.
- Alembic head is `0048_add_course_miniapp_foundation`.

Why:
- Course onboarding, interactive lessons, tests, gamification, and analytics need one server-side foundation before replacing the prototype's local-only state.

Files touched:
- `app/db/models/course_miniapp_profile.py`
- `app/db/models/course_feature_usage.py`
- `app/db/models/course_miniapp_event.py`
- `app/services/course_miniapp_access_service.py`
- `app/services/course_miniapp_profile_service.py`
- `app/services/course_miniapp_analytics_service.py`
- `app/main.py`
- `app/services/study_miniapp_service.py`
- `alembic/versions/0048_add_course_miniapp_foundation.py`

Risk:
- Migration `0048` must run before the new entitlement and analytics paths receive production traffic.
- Payment handlers and payment tables were intentionally not changed.

Follow-up:
- Phase 2 must persist Mini App onboarding through this profile service and emit the approved onboarding events.

### 2026-06-23 — Course-first HSK AI V2 Mini App and AI Voice

Changed:
- `study.html` now loads the course-first V2 Mini App shell with Home, Course, Tests, Training, AI Voice, Profile, XP, streak, missions, rewards, league, and mistake review while preserving existing lesson query routes.
- AI Voice now has verified Telegram Mini App APIs, capped session/turn/audio usage, OpenAI transcription and structured corrections, RU/TJ/UZ UI localization, and a persistent `voice_practice_sessions` table.
- Passing the exact current V2 lesson now idempotently advances legacy course progress through `CourseEngineService`; free access is limited to the first trial lesson.
- Alembic head is `0047_add_voice_practice_sessions`.

Why:
- The old study surface did not provide the requested unified course-first product experience, and the supplied voice prototype had mock endpoints only.

Files touched:
- `app/static/study.html`
- `app/static/study-v2.css`
- `app/static/study-v2.js`
- `app/static/voice-practice.html`
- `app/main.py`
- `app/services/voice_practice_service.py`
- `app/services/study_miniapp_service.py`
- `app/db/models/voice_practice_session.py`
- `alembic/versions/0047_add_voice_practice_sessions.py`

Risk:
- The V2 lesson score is currently calculated in the client; the server verifies Telegram identity, current lesson, access, pass threshold, and idempotence, but canonical server-side grading is still preferable.
- Production AI Voice requires migration `0047` before traffic and a real Telegram microphone/initData smoke test after deploy.

Follow-up:
- Run Alembic upgrade during deploy, test AI Voice in Telegram, monitor session limits/OpenAI cost, and move canonical V2 quiz grading server-side before expanding high-value rewards.

### 2026-06-21 — Course-first onboarding and Duo Mini App adapter

Changed:
- `/start` no longer sends new users into DailyPractice after language + level; it starts the first available course lesson directly so users see course value immediately.
- Course quiz/homework buttons now open `duo-lesson.html`, which loads real course payload from `/api/miniapp/lesson` and submits quiz/homework results to `/api/miniapp/event`.
- Course/QA onboarding tips are queued with zero delay and sent immediately when possible instead of waiting ~30 seconds.
- Stroke-order Mini App now sends Telegram WebApp init data when loading lesson vocabulary.

Why:
- Conversion issue was users not seeing course value early and getting split between QA/DailyPractice/Course choices.

Files touched:
- `app/bot/handlers/start.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/messages.py`
- `app/bot/utils/course_miniapp.py`
- `app/main.py`
- `app/static/duo-lesson.html`
- `app/static/stroke-order.html`
- `app/services/course_miniapp_result_service.py`
- `app/services/onboarding_tip_service.py`

Risk:
- Mini App result submission still depends on valid Telegram WebApp `initData`; local browser preview can only test fallback/static behavior.

Follow-up:
- Smoke test in Telegram after deploy: new `/start` onboarding, Duo quiz result, Duo homework result, stroke-order vocabulary open event.

### 2026-06-20 — Course pilot compact first 3 lessons

Changed:
- HSK1-HSK4 lessons 1-3 now return a compact pilot experience payload for Course Mini App quiz/reinforcement: consistent skeleton, shorter task count, and varied activities by lesson order.
- Lessons 4+ keep the existing payload shape and course flow.
- Added `course_pilot_events` for opened/completed/returned telemetry, with admin stats showing pilot open, quiz completion, reinforcement completion, drop signal, and lesson breakdown.

Why:
- Trial course completion was a weak signal; the pilot keeps structure familiar while making the first three lessons lighter and measurable before expanding changes.

Files touched:
- `app/services/course_miniapp_lesson_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/static/course-miniapp-v2.js`
- `app/main.py`
- `app/bot/handlers/admin.py`
- `app/db/models/course_pilot_event.py`
- `alembic/versions/0043_add_course_pilot_events.py`

Risk:
- Pilot telemetry is append-only and should not affect access/payment logic, but Mini App smoke testing is needed with real Telegram `initData`.

Follow-up:
- Watch Course pilot 1-3 stats before applying the compact format to later lessons.

### 2026-06-19 — Daily 3-min onboarding loop

Changed:
- New/free onboarding now starts with `DailyPractice`: 3 words, 2 quick quiz prompts, and 1 simple sentence after language and level selection.
- Course mode remains available from the menu and from DailyPractice, but it is no longer the primary onboarding path.
- Added `users.daily_practice_started_at`, `daily_practice_completed_at`, `daily_practice_streak`, and `daily_practice_last_day`.
- Required-channel subscription is no longer enforced globally or inside course `block_vocab_2`; it is checked only when a free QA user reaches the daily text limit.
- Trial course paywalls include a free QA fallback button, and admin stats show DailyPractice start/completion, D1→D2 return, Daily→Course, Daily→Paid, and QA-limit channel metrics.

Why:
- Trial course-first funnel showed low completion and no payment conversion. The new loop optimizes for quick daily completion and return before pushing full course depth.

Files touched:
- `app/bot/handlers/start.py`
- `app/bot/handlers/messages.py`
- `app/bot/middlewares/required_channel.py`
- `app/bot/handlers/required_channel.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/commands.py`
- `app/bot/keyboards/onboarding.py`
- `app/services/daily_practice_service.py`
- `app/services/course_trial_service.py`
- `app/db/models/user.py`
- `app/db/session.py`
- `alembic/versions/0042_add_daily_practice_fields.py`

Risk:
- `force_sub_required_at` now represents QA-limit channel checkpoint going forward, but old rows may still include historical course checkpoint data.

Follow-up:
- Watch D1 completion, D2 return, and Daily→Course before judging payment conversion.

### 2026-06-19 — Course Mini App release announcement template

Changed:
- Release feedback admin panel now includes a ready Course Mini App update template with localized UZ/RU/TJ text.
- The template preserves selected target filters, defaults to `mode_filter=course`, and reuses the existing release send/test/schedule flow.

Why:
- Course Mini App UI changes need a fast way to show the update to users without manually rewriting the announcement each time.

Files touched:
- `app/bot/handlers/release_feedback.py`
- `app/bot/keyboards/release_feedback.py`

Risk:
- Admin must still confirm/send the campaign; this does not auto-broadcast on deploy.

Follow-up:
- Use admin panel → Release feedback → Course Mini App update → Admin test → Hozir/Schedule.

### 2026-06-19 — Course Mini App quiz and reinforcement UI

Changed:
- Course Mini App quiz payload now serves 5 server-graded questions with backward-compatible `opts/ans/id` plus UI metadata for `multiple_choice`, `listening_choice`, and `fill_blank`.
- Homework user-facing flow was renamed to Mustahkamlash / Закрепление / Мустаҳкамкунӣ while backend `homework` endpoint/state names stay compatible.
- Mini App homework can now complete as interactive reinforcement (`word_order`, `match_pairs`, `listening_choice`, `stroke_preview`) without mandatory written answers or AI grading.
- HSK1-HSK4 static course pages load a shared Mini App v2 renderer only for `mode=quiz/homework`; normal study pages keep their existing code path.

Why:
- Course flow should feel lighter and more interactive after lessons while preserving Lesson → Quiz → Result → Mustahkamlash → Result → Next Lesson.

Files touched:
- `app/services/course_miniapp_lesson_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/static/course-miniapp-v2.js`
- `app/static/hsk1.html`
- `app/static/hsk2.html`
- `app/static/hsk3.html`
- `app/static/hsk4.html`
- `app/bot/utils/i18n.py`
- `app/bot/utils/course_miniapp.py`
- `app/main.py`

Risk:
- Full end-to-end Telegram smoke test still needs real `initData`, active course state, and production DB.

Follow-up:
- Smoke test HSK1-HSK4 quiz and Mustahkamlash from Telegram Mini App, including bot result messages and next lesson unlock.

### 2026-06-14 — Release feedback dashboard

Changed:
- Admin panel now has a Telegram-based Release feedback module for sending localized release announcements, collecting 1-5 ratings, required low-rating comments/screenshots, optional comments, and per-campaign stats.
- Release messages include a "Sinab ko'rish" CTA; non-paid users get temporary 30-minute active test access without changing `payment_status`.
- Completed release feedback from non-paid users creates a per-user 20% / 24-hour `admin_discount` campaign, so checkout reuses the existing Subscription Mini App admin discount flow.
- Added `release_feedback_campaigns`, `release_feedback_deliveries`, and `release_feedback_responses`.
- Admin statistics now includes overall bot feedback and release feedback metrics.

Why:
- Admin needs to announce new bot features, let users test them, collect actionable feedback, and track response/try/discount results.

Files touched:
- `app/bot/handlers/release_feedback.py`
- `app/services/release_feedback_service.py`
- `app/repositories/release_feedback_repo.py`
- `app/db/models/release_feedback.py`
- `app/bot/keyboards/release_feedback.py`
- `app/bot/fsm/release_feedback.py`
- `app/bot/handlers/admin.py`
- `app/main.py`
- `app/bot/create_bot.py`
- `alembic/versions/0041_add_release_feedback.py`

Risk:
- Temporary test access sets non-paid users to `status="active"` for 30 minutes but does not make them paid; paid logic must continue to rely on `payment_status="approved"`.
- Release feedback discounts are stored as normal admin discount campaigns targeted to one Telegram ID.

Follow-up:
- Run migration/deploy, then smoke test release create/test/send, user try access, 1-5 rating, low-rating comment, discount checkout, and admin stats.

### 2026-06-14 — Feedback prompt delay removed

Changed:
- Bot feedback requests are now eligible immediately after the daily limit offer is sent, without the previous 5-minute delay.

Why:
- User requested faster otziv collection after the daily limit is reached.

Files touched:
- `app/services/bot_feedback_service.py`

Risk:
- Feedback prompt may appear sooner after the limit message; retry and 30-day completion throttles still apply.

Follow-up:
- Smoke test a daily-limit user and confirm the otziv prompt is sent on the next scheduler cycle.

### 2026-06-13 — Broadcast and ad campaign CTA buttons

Changed:
- Admin broadcast and ad campaign creation now ask whether to add one inline button under the outgoing message.
- Ready button actions include subscription Mini App, partner, course mode, reminder setup, help, admin contact, profile, plus a custom external URL with optional custom button text.
- Ad campaigns store the optional button as `ad_campaigns.button_config` JSON text, with migration/bootstrap support for existing databases.

Why:
- Marketing messages need direct CTA buttons without manually building separate bot flows for each campaign.

Files touched:
- `app/bot/keyboards/promo_button.py`
- `app/bot/handlers/admin_broadcast.py`
- `app/bot/handlers/admin_ads.py`
- `app/bot/handlers/menu.py`
- `app/db/models/ad_campaign.py`
- `app/repositories/ad_campaign_repo.py`
- `app/services/ad_campaign_service.py`
- `app/db/session.py`
- `alembic/versions/0040_add_ad_campaign_button_config.py`

Risk:
- Button action callbacks send a new message and leave the original broadcast/ad message intact; Telegram smoke testing is needed for each CTA type.

Follow-up:
- Run migration/deploy, then test broadcast and ad campaign with no button, subscription, profile, reminder, admin contact, and external URL buttons.

### 2026-06-13 — AI level ceiling hardened

Changed:
- General QA system prompt now explicitly forbids examples, vocabulary, grammar, sentence patterns, and explanations above the user's current level.
- Course tutor prompts now append the same level-ceiling rule to every step response and homework evaluation.
- Image explainer prompt now requires image explanations/examples to stay at or below the user's level.

Why:
- AI tutor behavior must not teach above the user's HSK level unless the user explicitly asks about higher-level content.

Files touched:
- `app/prompts/qa_system.txt`
- `app/services/course_tutor_service.py`
- `app/services/image_explainer_service.py`

Risk:
- Responses may become simpler and avoid advanced examples even when they would be interesting, which is intentional for level safety.

Follow-up:
- Smoke test HSK1/HSK2 QA, image explanation, and course lesson AI feedback with prompts asking for advanced examples.

### 2026-06-13 — Help links moved to admin-managed bot settings

Changed:
- `/help` and menu Help now build 3-language HTML help text from `bot_settings` video-link keys instead of hardcoded help content/contact.
- Admin panel now has one `Help sozlamalari` section containing 4 help video link types per language (`tj`, `ru`, `uz`) plus one global admin contact link.
- Empty help video links are skipped in user help text; admin contact is shown as an inline button below the help message when configured.

Why:
- Help video URLs and support contact must be editable from the admin panel without code changes.

Files touched:
- `app/services/help_settings_service.py`
- `app/services/support_contact_service.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/commands.py`
- `app/bot/handlers/menu.py`
- `app/bot/handlers/messages.py`
- `app/bot/fsm/admin_management.py`
- `app/bot/utils/i18n.py`
- `app/static/subscription.html`

Risk:
- Existing deployments without `admin_contact` in `bot_settings` will show the help text without the contact button until admin sets a contact link.

Follow-up:
- In Telegram, test Admin panel → Help sozlamalari, set one video link for each language, then test `/help` and Help menu in TJ/RU/UZ.

### 2026-06-13 — Admin user deletion flow simplified and hardened

Changed:
- Admin panel delete-user button now starts an FSM flow: admin taps delete, bot waits for Telegram ID, admin sends only the numeric ID, and the bot deletes the user.
- Duplicate `/deleteuser` handler was removed from the broadcast router; the legacy `/deleteuser TELEGRAM_ID` fallback now uses the same repository delete path.
- User deletion now explicitly clears direct internal user-linked rows (`messages`, course progress/attempts, onboarding tip events, bot feedback) before deleting the `users` row.

Why:
- `/deleteuser` was duplicated across routers and admin panel forced command usage instead of a simple ID prompt.
- Delete could fail or behave inconsistently when related user rows existed and DB cascade was not enough.

Files touched:
- `app/bot/fsm/admin_management.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/admin_broadcast.py`
- `app/bot/handlers/messages.py`
- `app/repositories/user_repo.py`

Risk:
- Payment/portfolio/partner audit rows are intentionally not deleted; they may still reference the Telegram ID for business history.

Follow-up:
- Deploy and smoke test in Telegram: Admin panel → Foydalanuvchini o'chirish → send numeric Telegram ID → confirm user disappears/restarts cleanly.

### 2026-06-13 — Subscription Mini App card payment display cleanup

Changed:
- Card checkout payment summary no longer shows the card-country row or duplicate bot-price row.
- Card checkout now shows `Dushanbe City` as the TJK bank name and keeps the exchange-rate row only for non-TJ cards.
- Discounted card quotes now include the original local payable amount so the Mini App can show it as a small crossed-out amount above/beside the discounted payable amount.
- Card payment instructions are collapsed by default and expand on tap; Tajik wording was simplified and the `Intiqol` mention was removed.

Why:
- Users saw duplicate pricing and overly long payment instructions on the final card payment screen.

Files touched:
- `app/static/subscription.html`
- `app/services/subscription_miniapp_service.py`

Risk:
- Payment creation still uses the existing final amount; this change mainly affects display and quote payload shape.

Follow-up:
- Smoke test real Telegram Mini App card checkout with TJ and non-TJ cards, including a discount mode.

### 2026-06-13 — HSK1/HSK2 Mini App quiz and homework flow aligned with HSK4

Changed:
- HSK1 and HSK2 Mini App quiz pages now open directly into the lesson quiz, matching the HSK4 flow instead of showing a separate start card.
- HSK1 and HSK2 homework pages now use the same purpose text style as HSK4 and submit homework answers as `vocab_sentences`, `grammar_sentences`, and `translations`.
- Homework submit keeps the return-to-bot button visible after submission, with local/offline fallback and Telegram `sendData` fallback aligned to HSK4-style event handling.
- Mini App asset version was bumped so Telegram opens the updated static files.

Why:
- Quiz and homework Mini Apps needed consistent UI and behavior across all HSK levels.

Files touched:
- `app/static/hsk1.html`
- `app/static/hsk2.html`
- `app/bot/utils/course_miniapp.py`

Risk:
- HSK1/HSK2 direct quiz start removes the previous pre-quiz start screen; course result saving still uses the existing `/api/miniapp/event` path.

Follow-up:
- Smoke test Telegram Mini App links for HSK1 and HSK2: quiz result returns to bot, homework submission shows return button, and bot receives AI homework result.

### 2026-06-12 — Course text AI separated from QA daily text limit

Changed:
- Trial/free course-mode text AI checks now bypass the QA daily text limit and course text AI usage no longer increments `users.questions_used`.
- Normal QA text messages still use `questions_used/question_limit` exactly as before.

Why:
- Course-mode text help should not consume or block the user's QA-mode daily text allowance.

Files touched:
- `app/services/access_service.py`
- `app/bot/handlers/messages.py`

Risk:
- This affects only text AI access accounting; photo and voice limits are unchanged.

Follow-up:
- Smoke test with a trial user: ask course tutor/homework/mistake discussion, then switch to QA and confirm daily text remaining was not reduced.

### 2026-06-12 — Subscription Mini App referral, QR, and help contact fixes

Changed:
- Limit-offer referral buttons use clearer bonus-question wording and update the existing limit block into referral invite/progress text.
- Subscription Mini App referral sheet shows the referral link visibly, improves copy status, and uses a stronger QR download/open fallback.
- Help text is shorter and uses an admin contact inline button backed by configurable `bot_settings.admin_contact`.

Why:
- Users needed clearer referral actions, visible invite links, more reliable QR handling in Telegram WebView, and simpler help/contact access.

Files touched:
- `app/static/subscription.html`
- `app/services/subscription_miniapp_service.py`
- `app/services/support_contact_service.py`
- `app/bot/handlers/referral.py`
- `app/bot/keyboards/help.py`
- `app/bot/utils/i18n.py`

Risk:
- QR download still depends on Telegram WebView/browser behavior; fallback opens the image if direct download is blocked.

Follow-up:
- Smoke test Mini App referral copy/share, QR display/download, and `/help` admin contact button.

### 2026-06-12 — Course grammar and all-level quiz quality tuning

Changed:
- HSK4 grammar blocks render as concise useful blocks: pattern, usage, one lesson example, and one attention note.
- HSK1-HSK4 Mini App quiz selection prioritizes distinct new words before repeating alternate question types, limits grammar repetition, and deduplicates exact questions.
- Backend Mini App quiz questions include word metadata so frontend selection can avoid several early questions from the same word.
- Course quiz intro text was simplified into a direct challenge-style prompt.

Why:
- Quiz users should be tested on more newly learned words, not duplicate-style questions from the first few words.
- HSK4 grammar needed to be useful without becoming a long theory block.

Files touched:
- `app/bot/utils/course_formatter.py`
- `app/bot/utils/course_miniapp.py`
- `app/bot/utils/i18n.py`
- `app/services/course_miniapp_lesson_service.py`
- `app/services/course_tutor_service.py`
- `app/static/hsk1.html`
- `app/static/hsk2.html`
- `app/static/hsk3.html`
- `app/static/hsk4.html`

Risk:
- Small blocks can return fewer than the target count if there are not enough unique valid questions, but this avoids low-quality duplicates.

Follow-up:
- Smoke test HSK1-HSK4 block quiz in Telegram/Mini App and confirm the first questions cover different new words.

### 2026-06-12 — Course trial fallback and homework processing feedback

Changed:
- Course subscription offers shown after course/trial lock now include an "Oddiy rejim" fallback button that switches the user back to `learning_mode="qa"` with existing daily limits and sends a short explanation that no automatic lessons are sent in this mode.
- Mini App homework submission now sends an immediate "AI is checking" chat message and edits that same message into the final AI homework result.
- Text/photo/course/voice AI replies now use a safer send path: empty AI content returns a localized fallback, AI exceptions send a visible retry message, malformed HTML retries without parse mode, and long replies are split into Telegram-safe chunks.
- The temporary "bot is working" edit effect now chooses different emoji sequences by mode (`qa`, `course`, `image`) and a seed based on user question count/text.

Why:
- Trial users who finish the free course lesson need a clear non-paid path back to daily-limited QA instead of only seeing the subscription button.
- Homework AI checks can take time, so the bot should visibly work instead of staying silent.
- AI or Telegram formatting failures should not make the bot appear to ignore a user message when an app-level fallback can still be sent.

Files touched:
- `app/bot/keyboards/subscription.py`
- `app/bot/handlers/course.py`
- `app/main.py`
- `app/bot/handlers/messages.py`
- `app/bot/utils/i18n.py`

Risk:
- Free mode does not grant new access; it only sets `learning_mode="qa"` and existing daily limits still control usage.
- Telegram message edit failures fall back to sending the final result as a new message.
- The fallback cannot fix upstream outages or Telegram delivery failures, but it prevents silent app-level failures for empty AI output, exceptions, bad HTML, and overlong text.

Follow-up:
- Smoke test in Telegram: finish a trial lesson, tap "Oddiy rejim", ask text/photo/course questions, then submit homework from the Mini App and confirm the processing message edits into the final result.

### 2026-06-12 — AI usage budget live-rate calculation

Changed:
- Paid subscription AI usage budgets now try live USD exchange rates when a payment is approved, including TJS and CNY, with admin-set subscription rates as fallback.
- The admin subscription price panel now includes a CNY fallback rate for Alipay/WeChat AI budget conversion.
- AI usage budget profit reserve changed from 40% to 50%.
- The fixed $1 Railway/server deduction was removed from per-payment AI budget calculation.

Why:
- Subscription limits should follow real exchange rates and updated business margin rules, but live-rate failures must fall back to admin-controlled rates instead of hardcoded TJS/CNY values.

Files touched:
- `app/bot/handlers/admin.py`
- `app/services/ai_usage_budget_service.py`
- `app/services/subscription_currency_service.py`

Risk:
- New approved payments will receive smaller AI budgets than before because profit reserve increased to 50%, but no extra $1 deduction is taken.
- Existing active AI budgets are not recalculated automatically.

Follow-up:
- After deploy, approve a small test payment and verify the created `ai_usage_budgets.total_budget_usd` against live/fallback rates.

### 2026-06-11 — Mini App subscription payment/referral repair

Changed:
- Subscription Mini App no longer shows demo/fallback payment data to real Telegram users when quote/overview APIs fail.
- VISA/card checkout now fails with a clear error if admin payment details are not configured.
- Mini App submit creates a pending payment only if at least one admin payment-review notification is delivered; otherwise it rolls back and returns an error.
- Referral 20% discount progress is recalculated from active referral records instead of trusting only `users.discount_referral_count`.
- Referral links for the 3-friend discount use the live bot username when possible, and the Mini App invite flow now supports localized share text plus copy-link-only.
- Legacy chat checkout reads admin-updated card payment details from `bot_settings.subscription_payment_details`.
- Reopening the Subscription Mini App while a payment is still pending shows a localized waiting screen instead of allowing duplicate payment submissions.
- The first Subscription Mini App screen now removes the extra explanatory hero block and keeps only concrete subscription benefits plus plan/payment choices.
- Profile and text/photo limit subscription buttons now open the Subscription Mini App directly with WebApp buttons instead of routing through the legacy `subscription:open` entry block.
- Subscription, referral discount, feedback discount, and admin campaign discount checkout now run through the Subscription Mini App modes (`subscription`, `referral_discount`, `feedback_discount`, `admin_discount`). Chat checkout plan/payment callbacks are legacy fallbacks that redirect to Mini App, and admin campaign notifications use a short Mini App entry instead of chat checkout blocks.
- Users who already used the referral discount no longer receive discount UI or discounted pricing from the Mini App.
- VISA/card payment details are rendered as readable rows with copy buttons for card-like numbers; Tajikistan card payments hide the exchange-rate row.
- The main reply-keyboard subscription button is now a Web App button that opens the Subscription Mini App directly; command/profile flows still send the explanatory Mini App entry block.
- QR payment screens let the user tap the QR to reveal a download button for saving the QR image.
- Card exchange-rate rows shown to users use direct TJS rates, for example `1 TJS = ... RUB`, instead of displaying USD/USDT-style cross-rate chains.
- Subscription Mini App has a top Help button with the public admin contact for payment-confirmation problems and visible errors; it remains available on pending-payment screens.

Why:
- Users were seeing wrong/fallback QR, card details, referral links, and discount state in the subscription Mini App, and payment submits could appear successful even if admin review did not receive the request.

Files touched:
- `app/static/subscription.html`
- `app/services/subscription_miniapp_service.py`
- `app/services/admin_notify_service.py`
- `app/services/discount_service.py`
- `app/services/subscription_progress_service.py`
- `app/bot/handlers/subscription.py`
- `app/bot/utils/course_miniapp.py`
- `app/main.py`

Risk:
- If admin IDs are wrong or blocked, Mini App payment submit now returns an error instead of silently accepting the request.
- Graphify update was attempted but refused to overwrite the existing graph because the rebuilt graph had fewer nodes.

Follow-up:
- After deploy, test inside Telegram with real `initData`: VISA/card quote, Alipay/WeChat QR quote, screenshot submit, admin approval, and referral share/copy in UZ/RU/TJ.

### 2026-06-09 — Subscription flow moved to Mini App

Changed:
- Normal subscription entrypoints now open `subscription.html` as a Telegram Mini App instead of continuing the chat checkout flow.
- Mini App APIs `/api/subscription-miniapp/overview`, `/quote`, and `/submit` calculate prices server-side, apply only the normal referral 20% discount path, and send submitted screenshots to the existing admin payment review queue without AI screenshot verification.
- Admin price panel now includes manual bank-card rates for TJS/UZS/RUB and an AUTO live-rate toggle; Mini App card quotes use admin rates unless AUTO live rates are enabled and available.
- `payments` now stores optional `card_country`, `local_amount`, `local_currency`, and `exchange_rate` for Mini App card payments.

Why:
- Subscription checkout should stay inside the Mini App, avoid chat-return steps for the normal Obuna button, and prevent frontend-side price/rate mistakes.

Files touched:
- `app/static/subscription.html`, `app/main.py`, `app/services/subscription_miniapp_service.py`, `app/services/subscription_currency_service.py`, `app/bot/handlers/*`, `app/bot/keyboards/subscription.py`, `app/db/models/payment.py`, `app/repositories/payment_repo.py`, `alembic/versions/0037_add_miniapp_payment_local_fields.py`

Risk:
- Live exchange rates depend on the external rate provider; if unavailable, backend falls back to admin manual rates.

Follow-up:
- Verify the Mini App inside Telegram with real `initData`, uploaded QR codes for non-default Alipay/WeChat prices, and a real admin approval.

### 2026-06-07 — Price-specific Alipay/WeChat QR codes

Changed:
- Added `payment_qr_codes` storage for uploaded Telegram QR `file_id`s by scope, payment method, plan, amount, and currency.
- Alipay/WeChat custom subscription prices now require admin to upload the matching regular QR and the matching 20% discount QR before the price is saved.
- Admin discount campaigns that target or include Alipay/WeChat now require campaign QR codes per affected method/plan discounted amount.
- Checkout uses old static QR files only for default Alipay/WeChat prices and default 20% referral/feedback discounts; non-default missing QR no longer falls back to an old fixed-price QR.

Why:
- Alipay/WeChat QR codes are amount-specific, so users must never receive a QR for a different price after admin changes prices or creates a discount.

Files touched:
- `app/db/models/payment_qr_code.py`
- `app/repositories/payment_qr_code_repo.py`
- `app/services/payment_qr_code_service.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/admin_discount.py`
- `app/bot/handlers/subscription.py`
- `alembic/versions/0036_add_payment_qr_codes.py`

Risk:
- Existing active admin discount campaigns created before this change do not have campaign-scoped QR records; for Alipay/WeChat checkout they may show "QR not ready" instead of the old generic admin discount QR.

Follow-up:
- Run migration/init DB, then smoke test: custom Alipay/WeChat price, 20% referral/feedback checkout, and admin discount campaign checkout.

### 2026-06-06 — Feedback prompt and reward timing

Changed:
- Feedback reward access is now 30 minutes instead of 1 day.
- Feedback requests are sent only after the user is at least 1 day old and has hit the daily text limit; the prompt becomes due 5 minutes after that limit event.

Why:
- Feedback should be requested after real limit friction, not just because the account is old.
- Feedback reward should not give a full day by default.

Files touched:
- `app/services/access_service.py`
- `app/services/bot_feedback_service.py`
- `app/main.py`
- `app/bot/handlers/messages.py`
- `app/bot/utils/i18n.py`

Risk:
- Existing `users.daily_limit_offer_sent_at` is reused as the limit-hit timestamp; no migration.
- Scheduler now checks feedback requests every 60 seconds, relying on pending feedback retry rules to prevent repeated prompts.

Follow-up:
- Smoke test with a user older than 1 day: hit the daily text limit, wait 5 minutes, confirm the feedback prompt appears once and reward activates for 30 minutes.

### 2026-06-06 — Feedback limit discount offer

Changed:
- Bot feedback dislike option `limits` now schedules the same 5-minute 20% subscription discount offer as `price`.
- The limits offer uses a separate user-facing message about bot limits, but reuses the existing feedback discount checkout/payment flow.

Why:
- Users who say bot limits are too low should get the same conversion path as users who say subscription price is high.

Files touched:
- `app/repositories/bot_feedback_repo.py`
- `app/services/bot_feedback_service.py`
- `app/services/discount_service.py`
- `app/bot/utils/i18n.py`

Risk:
- Existing DB fields are reused; no migration. Scheduler still sends due offers from the existing 60-second background loop.

Follow-up:
- Smoke test in Telegram: choose `Limitlar kam`, wait 5 minutes, open the 20% discount flow, and submit a payment screenshot.

### 2026-06-06 — Image caption as AI command

Changed:
- Photo messages now pass Telegram caption text into the image AI flow.
- The image explainer treats caption text as the user's command and uses analyzer output as the image source context.
- Image file IDs are excluded from normal QA chat history; follow-up context should come from stored image context.
- QA AI history now keeps system context messages, so stored image context is available in follow-up questions.

Why:
- Users sending photo + text like "Tarjima qil" need the bot to follow the text instruction instead of only explaining the image.

Files touched:
- `app/bot/handlers/messages.py`
- `app/services/image_qa_service.py`
- `app/services/image_explainer_service.py`
- `app/services/qa_service.py`
- `app/services/ai_service.py`

Risk:
- Prompt-only behavior change; image limits, subscription access, and payment logic are unchanged.

Follow-up:
- Test in Telegram with a photo caption command such as "Tarjima qil".

### 2026-06-05 — Command/menu input cleanup

Changed:
- Private-chat slash commands and main/course reply menu button messages are deleted after their handlers run.

Why:
- Keep Telegram chats clean while preserving command behavior.

Files touched:
- `app/bot/middlewares/cleanup.py`
- `app/bot/create_bot.py`

Risk:
- Delete failures are ignored; group chats are not affected.

Follow-up:
- Verify on production bot that Telegram allows deleting incoming private-chat command messages.

### 2026-06-04 — Localized TJS card subscription blocks

Changed:
- Card/TJS subscription selection and checkout messages now keep one compact format while matching the user's language (TJ/RU/UZ).
- TJS plan prices show `💸 {amount} TJS 🇹🇯` in the plan list and `{amount} TJS 💸` in checkout.
- Alipay/WeChat QR payment flow remains separate.

Why:
- Avoid mixed-language payment instructions and keep card payment instructions easy to read.

Files touched:
- `app/bot/handlers/subscription.py`

Risk:
- Text-only card flow change; payment amount and subscription logic unchanged.

Follow-up:
- Verify rendered Telegram blockquote spacing on production bot after deploy.

### 2026-05-25 — Course narrative text formatting

Changed:
- Course text blocks with narrator-style lines (`旁白` / no speaker) now render as text instead of dialogue: bold Chinese line, pinyin below, translation below.
- Narrative blocks show `Matn/Текст/Матн` in the course message header instead of `Dialog`.

Why:
- Textbook passages without speakers were hard to read when formatted like dialogue lines.

Files touched:
- `app/bot/utils/course_formatter.py`

Risk:
- This is display-only; stored lesson JSON and progress logic are unchanged.

### 2026-05-25 — Referral trial active access

Changed:
- Users can unlock 3 days of non-paid `active` access after collecting 10 active referrals.
- This reward is separate from the existing referral bonus and referral discount flows: +5 bonus questions and 3-referral discount counters still use their existing fields.
- Referral active access does not set `payment_status=approved`; it creates a fixed $2 AI usage budget for the trial active window.
- In trial active, text/course/photo use the fixed $2 AI budget; photo no longer has a separate daily image limit during this reward window.
- If the fixed $2 AI budget is depleted before 3 days, the non-paid active user is downgraded back to `trial`; if 3 days expire first, the user is also downgraded even if budget remains.
- Voice is restricted to real paid subscribers (`status=active` and `payment_status=approved`); non-paid active windows do not unlock voice.
- Profile labels non-paid active as `Sinov muddati`, shows only referral count, and leaves the subscription line empty unless the user has a real paid subscription.
- A new `users.referral_trial_count_started_at` marker resets this feature's referral count after each 3-day reward window.

Why:
- Trial users need a referral path to temporarily become `active` without replacing a real paid subscription.

Files touched:
- `app/services/referral_service.py`
- `app/services/access_service.py`
- `app/services/ai_usage_budget_service.py`
- `app/services/qa_service.py`
- `app/services/image_qa_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/repositories/referral_repo.py`
- `app/db/models/user.py`
- `app/db/session.py`
- `app/bot/handlers/messages.py`
- `app/bot/handlers/referral.py`
- `app/bot/handlers/commands.py`
- `app/bot/handlers/menu.py`
- `app/bot/keyboards/referral.py`
- `app/bot/utils/i18n.py`
- `alembic/versions/0028_referral_trial_activation.py`

Risk:
- Paid users are still identified only by `payment_status=approved`; do not treat `status=active` alone as paid subscription.

Follow-up:
- Run DB migration in deploy environments before relying on referral trial progress display.

### 2026-05-25 — Referral bonus usage is lifetime

Changed:
- Daily trial limit reset now resets only `questions_used`; it does not reset `bonus_questions_used`.
- Referral trial active activation also keeps already-used referral bonus questions spent.

Why:
- Referral +5 questions are a one-time bonus, not a daily renewed allowance.

Files touched:
- `app/services/access_service.py`
- `app/services/referral_service.py`

Risk:
- Users who already reused bonus questions before this fix are not retroactively corrected.

Follow-up:
- If historical correction is required, add a separate data audit instead of mixing it into runtime access logic.

### 2026-05-24 — Dynamic course dialogue audio admin

Changed:
- Admin audio panel now builds required audio types from each lesson's current `dialogue_json` block count, so HSK4 lessons with 5 dialogues show `vocab` plus `dialogue_1` through `dialogue_5`.
- Audio status now distinguishes complete, partial, and missing lessons, and ignores obsolete audio types that no longer match the current lesson format.
- Course audio playback no longer falls back from `dialogue_2+` to `dialogue_1`; missing dialogue-specific audio now stays unavailable instead of playing the wrong old audio.

Why:
- After lessons were split into more dialogue blocks, the old admin/audio logic could hide later dialogues or reuse outdated audio under the wrong dialogue.

Files touched:
- `app/bot/handlers/admin_audio.py`
- `app/bot/handlers/course.py`
- `app/repositories/course_audio_repo.py`
- `app/services/course_engine_service.py`
- `app/services/course_tutor_service.py`

Risk:
- Existing lessons that only have `dialogue_1` uploaded will show missing audio for later dialogue blocks until admin uploads each specific dialogue audio.

Follow-up:
- If obsolete DB audio should be deleted automatically, add an explicit admin cleanup action instead of silently deleting rows.

### 2026-05-24 — HSK4 upper lesson localization quality

Changed:
- HSK4 上 lessons 1-3 now keep PDF-canonical Chinese dialogue/new-word material while adding Uzbek, Russian, and Tajik translations, dialogue pinyin, localized grammar explanations, and localized mini quiz/homework prompts.
- The HSK4 static mini app fallback data now uses language-aware vocabulary, grammar, and quiz strings instead of Uzbek-only strings.

Why:
- Bot course messages and Mini App could show blank or Uzbek-only explanations for Russian/Tajik users because HSK4 seed payload only contained Uzbek fields and empty dialogue pinyin.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/hsk4_upper_i18n.py`
- `scripts/verify_hsk4_upper_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Dialogue/new words remain source-locked to the textbook data in `scripts/hsk4_upper_pdf_materials.py`; only translations/explanations/pinyin are added in the i18n layer.

Follow-up:
- Use the same localization verifier before enabling HSK4 上 lessons 4-6 in Mini App support.

### 2026-05-24 — Course level completion upgrade flow

Changed:
- When a user finishes the last lesson in a HSK level, the bot now sends a level-completion congratulations message with lesson, vocabulary, dialogue, and study-duration progress.
- The bot then asks whether to move to the next HSK level in Uzbek, Russian, and Tajik. Yes upgrades `users.level`, resets course progress for the next level, and opens lesson 1. No keeps the user on the completed level and shows that level's lesson list.
- Final lessons are now marked completed only once, preventing repeated "next lesson" presses from double-counting progress.

Why:
- The previous final-lesson path only showed a generic "lesson completed" message when no next lesson existed.

Files touched:
- `app/services/course_engine_service.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/messages.py`
- `app/bot/keyboards/course_context.py`
- `app/bot/utils/i18n.py`

Risk:
- Advancing to the next level resets `CourseProgress.completed_lessons_count` for the new level because the current schema stores one course progress row per user.

Follow-up:
- If global cross-level progress is required later, add a dedicated course completion history table instead of overloading the current per-user progress row.

### 2026-05-24 — Course block AI context

Changed:
- HSK course AI prompts now receive block-level course context for block lessons: dialogue block, block vocabulary, grammar points, mini quiz, and mini homework.
- HSK3 lessons 13-16 were wired through `scripts/hsk3_pdf_materials.py`, so dialogue/new words are PDF canonical instead of synthetic seed content.

Why:
- Mini App quiz/homework review must explain the exact user mistakes using the same block material shown in the course.

Files touched:
- `app/services/course_tutor_service.py`

### 2026-05-24 — HSK3 block lesson completion

Changed:
- HSK3 lessons 17-20 now use PDF canonical dialogue/new-word material through `scripts/hsk3_pdf_materials.py`.
- All HSK3 lessons 1-20 now generate per-dialogue block steps with `block_vocab_N` before `dialogue_N`.

Why:
- Lessons 17-20 were still in the older V2 format, so later parts could start directly with `dialogue_3`/`dialogue_4` and skip the new-word section.

Files touched:
- `scripts/hsk3_pdf_materials.py`
- `scripts/seed_hsk3_lesson_17.py`
- `scripts/seed_hsk3_lesson_18.py`
- `scripts/seed_hsk3_lesson_19.py`
- `scripts/seed_hsk3_lesson_20.py`
- `scripts/verify_hsk3_pdf_materials.py`

Risk:
- Database must run the course seed sync or app restart so existing stored lesson JSON is refreshed.

Follow-up:
- If a deployed bot still shows old HSK3 lesson flow, restart/reseed first before debugging UI step logic.

### 2026-05-24 — Block grammar de-duplication

Changed:
- HSK1, HSK2, and HSK3 block lessons now normalize grammar per lesson so the same book grammar number is not shown repeatedly across multiple blocks.
- Every block still gets a short context grammar note based on the actual dialogue sentence used in that block.
- Telegram formatter and Mini App lesson payload prefer block `grammar_notes` over long book grammar items to avoid duplicate-looking explanations.

Why:
- Users saw repeated grammar material across blocks and some blocks felt like they had no useful grammar.

Files touched:
- `scripts/block_context_grammar.py`
- `scripts/hsk1_block_metadata.py`
- `scripts/hsk2_block_metadata.py`
- `scripts/hsk3_pdf_materials.py`
- `app/bot/utils/course_formatter.py`
- `app/services/course_miniapp_lesson_service.py`
- `app/services/course_tutor_service.py`
- `scripts/verify_course_block_grammar.py`

Risk:
- Existing database lesson JSON must be refreshed by seed sync/app restart before deployed users see the normalized grammar.
- `app/services/course_miniapp_result_service.py`
- `scripts/hsk3_pdf_materials.py`
- `scripts/seed_hsk3_lesson_13.py` to `scripts/seed_hsk3_lesson_16.py`
- `scripts/verify_hsk3_pdf_materials.py`

Why:
- 

Files touched:
- 

Risk:
- 

Follow-up:
- 

### 2026-05-24 — HSK4 上 first 3 lessons block format

Changed:
- HSK4 上 lessons 1-3 now use PDF-derived dialogue and vocabulary material through `scripts/hsk4_upper_pdf_materials.py`.
- Each of those lessons has 5 dialogue blocks, per-block vocabulary, one relevant PDF grammar point, mini quiz, and mini homework.
- HSK4 Mini App support is enabled only for lessons 1-3 for now via `hsk4.html`.

Why:
- HSK4 upper lessons had fewer dialogue blocks than the PDF and some lesson 2/3 grammar/vocabulary was from the wrong older seed format.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/seed_hsk4_lesson_01.py` to `scripts/seed_hsk4_lesson_03.py`
- `app/bot/utils/course_miniapp.py`
- `app/static/hsk4.html`

Risk:
- Lessons 4+ are intentionally not enabled in HSK4 Mini App yet; continue in small batches to avoid content errors.

### 2026-05-24 — HSK4 上 lessons 4-6 PDF alignment

Changed:
- HSK4 上 lessons 4-6 now use canonical textbook dialogue/new-word data through `scripts/hsk4_upper_pdf_materials_4_6.py`.
- Each lesson has 5 dialogue blocks, 31 textbook vocabulary items, 5 grammar points, three-language translations, pinyin, per-block mini quiz/homework, and Mini App fallback data.
- Seed files for lessons 4-6 are now thin wrappers so stale non-PDF fallback content cannot leak into runtime data.

Why:
- Lessons 4-6 previously still contained older non-canonical seed material and HSK4 Mini App fallback only covered lessons 1-3.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/hsk4_upper_pdf_materials_4_6.py`
- `scripts/seed_hsk4_lesson_04.py` to `scripts/seed_hsk4_lesson_06.py`
- `scripts/verify_hsk4_upper_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Database must be reseeded for deployed environments; local DB was updated for HSK4-L04, HSK4-L05, and HSK4-L06 in this session.

### 2026-05-25 — HSK4 上 lessons 7-10 PDF alignment

Changed:
- HSK4 上 lessons 7-10 now use canonical textbook dialogue/new-word data through `scripts/hsk4_upper_pdf_materials_7_10.py`.
- Each lesson has 5 dialogue blocks, per-block vocabulary, one relevant grammar point, three-language translations, pinyin, mini quiz, and mini homework.
- HSK4 static Mini App fallback data now covers lessons 1-10 with grammar-focused quiz questions and no fill-blank style quiz items.

Why:
- Lessons 7-10 still had stale seed JSON and Mini App coverage stopped at lesson 6.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/hsk4_upper_pdf_materials_7_10.py`
- `scripts/seed_hsk4_lesson_07.py` to `scripts/seed_hsk4_lesson_10.py`
- `scripts/verify_hsk4_upper_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Database must be reseeded for deployed environments; local DB was updated for HSK4-L07 through HSK4-L10 in this session.

### 2026-05-25 — HSK4 下 lessons 11-13 PDF alignment

Changed:
- HSK4 下 lessons 11-13 now use canonical textbook dialogue/new-word data through `scripts/hsk4_lower_pdf_materials.py`.
- Each lesson has 5 blocks, per-block vocabulary, relevant grammar, pinyin, three-language translations, mini quiz, and mini homework.
- HSK4 static Mini App fallback now recognizes lessons 1-13 and includes grammar quiz items for lessons 11-13.

Why:
- HSK4 下 needed to start from the textbook format; older lower seed data had incomplete lesson blocks and stale lesson 11 content.

Files touched:
- `scripts/hsk4_lower_pdf_materials.py`
- `scripts/hsk4_lower_seed_data.py`
- `scripts/seed_hsk4_lesson_11.py`
- `scripts/verify_hsk4_lower_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Database must be reseeded for deployed environments; local DB was updated for HSK4-L11 through HSK4-L13 in this session.

### 2026-05-25 — HSK4 Mini App support range

Changed:
- HSK4 Mini App support range is now lessons 1-13.

Why:
- HSK4 上 lessons 4-10 had Mini App content and API payloads, but course buttons were blocked by the stale supported range `1-3`.

Files touched:
- `app/bot/utils/course_miniapp.py`

Risk:
- HSK4 lessons beyond 13 stay unsupported until their lesson data is converted.

### 2026-05-25 — HSK4 下 lessons 14-16 PDF alignment

Changed:
- HSK4 下 lessons 14-16 now use canonical textbook dialogue/new-word data through `scripts/hsk4_lower_pdf_materials_14_16.py`.
- Each lesson has 5 blocks, per-block vocabulary, relevant grammar, pinyin, three-language translations, mini quiz, and mini homework generated through the lower seed pipeline.
- HSK4 static Mini App fallback and support range now cover lessons 1-16 with grammar-focused quiz items and no blank-fill quiz format.

Why:
- Lessons 14-16 needed the same PDF-based format as lessons 11-13 before continuing HSK4 下 in small batches.

Files touched:
- `scripts/hsk4_lower_pdf_materials.py`
- `scripts/hsk4_lower_pdf_materials_14_16.py`
- `scripts/verify_hsk4_lower_pdf_materials.py`
- `app/bot/utils/course_miniapp.py`
- `app/static/hsk4.html`

Risk:
- Runtime database must be reseeded or app restarted in deployed environments before Telegram course messages show HSK4-L14 through HSK4-L16.

### 2026-05-28 — HSK4 下 lessons 17-20 PDF alignment

Changed:
- HSK4 下 lessons 17-20 now use canonical textbook dialogue/new-word data through `scripts/hsk4_lower_pdf_materials_17_20.py`.
- Each lesson has 5 blocks, per-block vocabulary, relevant grammar, pinyin, three-language translations, mini quiz, and mini homework generated through the lower seed pipeline.
- HSK4 static Mini App fallback and support range now cover lessons 1-20 with grammar-focused quiz items and no blank-fill quiz format.

Why:
- Lessons 17-20 complete HSK4 下 in the same PDF-based format as lessons 11-16.

Files touched:
- `scripts/hsk4_lower_pdf_materials.py`
- `scripts/hsk4_lower_pdf_materials_17_20.py`
- `scripts/verify_hsk4_lower_pdf_materials.py`
- `app/bot/utils/course_miniapp.py`
- `app/static/hsk4.html`

Risk:
- Runtime database must be reseeded or app restarted in deployed environments before Telegram course messages show HSK4-L17 through HSK4-L20.

### 2026-06-04 — Localized admin messaging and TJS card subscriptions

Changed:
- Admin broadcast and ad campaign text can be written once in Tajik, then localized to TJ/UZ/RU through AI before sending; users receive the variant matching their language.
- Broadcast and ad campaign confirm flows include an admin test send without clearing the prepared message.
- Visa/Card subscription pricing is TJS-only: 10 days = 29 TJS, 1 month = 89 TJS by default. Alipay/WeChat remain in yuan.
- Stale checkout drafts are recalculated when a screenshot arrives so old USD drafts do not survive after the TJS switch.
- Expired admin/feedback discount buttons edit the original offer message to an expired text instead of only showing an alert.

Why:
- Admins should not send separate messages per language, and card subscription revenue should be priced in somoni.

Files touched:
- `app/services/broadcast_translation_service.py`
- `app/bot/handlers/admin_broadcast.py`
- `app/bot/handlers/admin_ads.py`
- `app/services/ad_campaign_service.py`
- `app/services/subscription_price_service.py`
- `app/bot/handlers/subscription.py`
- `app/services/payment_service.py`

Risk:
- Broadcast/ad translations depend on `OPENAI_API_KEY`; if translation fails, the Tajik source is used as a safe fallback.
- Telegram bot updates do not expose user IP, so non-TJ card users see a general bank-rate TJS payment note instead of IP-based country detection.

---

### 2026-06-11 — Menu subscription WebApp auth fix

Changed:
- Main reply keyboard `Obuna` is a normal text button again; the bot handler sends an inline Mini App button with `mode=subscription`.

Why:
- Reply-keyboard `web_app` launches were not reliably connecting the Subscription Mini App to the bot for some users. Inline WebApp buttons keep the Telegram init data flow stable.

Files touched:
- `app/bot/keyboards/main_menu.py`

Risk:
- The menu subscription path uses one bot message before opening the Mini App instead of opening directly from the reply keyboard.

---

### 2026-06-11 — New user course trial funnel and channel checkpoint

Changed:
- New users start as `status="trial"` instead of 24-hour active access.
- Onboarding keeps language and level selection, then asks which course lesson to start: recommended first lesson or another lesson from the selected level.
- Free users can fully complete one selected `CourseLesson`; access to another lesson, next lesson, or level upgrade shows the subscription Mini App offer.
- Added `users.trial_course_lesson_id`, `trial_course_started_at`, `trial_course_completed_at`, `trial_quiz_explanation_used_at`, and `force_sub_required_at`.
- Required-channel checks are skipped until `force_sub_required_at` is set; the flag is set when a free user reaches `block_vocab_2` (`2-qism yangi so'zlar`). After that, existing required-channel middleware checks every free-user event. Paid approved users bypass this check.
- Course Mini App quiz results also set the checkpoint flag if the next step is `block_vocab_2`.
- Admin stats now show paid users by `payment_status="approved"` plus trial course started/completed, trial AI explanation, channel checkpoint, trial-to-paid, completed-to-paid, checkpoint-to-paid, and post-trial revenue metrics.

Preserved:
- Paid approved users still use the existing `AIUsageBudgetService` structure for text/photo/voice-related AI usage.
- Free text AI and photo AI remain daily-limit based; voice remains subscription-only.
- Existing course lesson internals stay intact: vocab, dialogue, block quizzes, grammar, homework, and Mini App result flow are not rewritten.

Risk:
- Existing old users with course progress but no `trial_course_lesson_id` may get their current lesson assigned as their one free trial lesson when they enter course mode.

Files touched:
- `app/bot/handlers/start.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/messages.py`
- `app/bot/middlewares/required_channel.py`
- `app/bot/handlers/required_channel.py`
- `app/bot/utils/i18n.py`
- `app/services/course_trial_service.py`
- `app/services/access_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/services/study_miniapp_service.py`
- `app/db/models/user.py`
- `app/db/session.py`
- `alembic/versions/0038_add_user_trial_course_fields.py`

---

### 2026-06-12 — One-time onboarding tips and trial voice sample

Changed:
- Added `onboarding_tip_events` to queue contextual one-time bot tips per user.
- Course vocab/dialogue/grammar sections queue a 30-second tip; the scheduler sends it only if the user is still on that same course step.
- Normal text/photo usage can queue one-time photo and voice feature tips.
- Added `users.trial_voice_used_at`; trial users can try voice once, while paid approved users keep normal voice access.
- Course Mini App quiz results below 60% show an AI mistake-discussion button that sends the latest quiz context to `CourseTutorService` and edits the processing message into the AI explanation.

Files touched:
- `app/services/onboarding_tip_service.py`
- `app/db/models/onboarding_tip_event.py`
- `app/db/models/user.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/messages.py`
- `app/main.py`
- `alembic/versions/0039_add_onboarding_tip_events.py`

---

### 2026-06-19 — Direct AI message draft

Changed:
- QA text AI replies now call Telegram `sendMessageDraft` directly; no draft feature flag remains.
- New `MessageDraftService` tries Telegram `sendMessageDraft` first and falls back to the existing `ResponseEffect` loader or `sendChatAction("typing")`.
- Final AI replies still use the normal send message flow; draft is only a waiting effect.

Why:
- Allows testing Telegram draft-based AI typing UX without removing the existing emoji/progress loader.

Files touched:
- `app/services/message_draft_service.py`
- `app/bot/handlers/messages.py`
- `app/bot/handlers/commands.py`
- `app/config.py`
- `.env.example`

Risk:
- `aiogram==3.22.0` does not expose `sendMessageDraft`; raw Telegram HTTP is used only when the flag is enabled, and failures fall back safely.

Follow-up:
- Test `/draft_test` and one normal QA text question in Telegram.

---

### 2026-06-21 - Conversion funnel tracking and course-first recovery

Changed:
- Added append-only `conversion_funnel_events` table via `0046_add_conversion_funnel_events.py`.
- Canonical funnel events: `course_cta_seen`, `course_started`, `lesson_started`, `quiz_completed`, `ai_explanation_seen`, `homework_completed`, `paywall_seen`, `checkout_opened`, `payment_screenshot_submitted`, `payment_approved`, `payment_rejected`.
- Added `ConversionFunnelService`; event writes use a separate short transaction and should not block user flow if tracking fails.
- Admin stats now define Paid as `User.payment_status == "approved"` + `User.status == "active"` + `User.end_date > now`; old approved users are shown separately as Historical approved.
- Daily Practice completion now shows Course CTA first, Free QA second.
- QA daily limit now shows a course offer first with `📚 1-darsni bepul boshlash` and `💳 Obuna olish`, then existing required-channel/referral fallback.
- Trial first Mini App lesson keeps existing homework/completion flow; after the full quiz, non-paid users can receive one automatic AI explanation and a soft paywall teaser. Quiz completion itself does not mark the trial lesson completed.

Important:
- Rejected payment funnel event means admin reject callback succeeded. It is not a gateway failure or checkout abandonment signal.
- Prices, subscription plan logic, referral logic, payment approval rules, and Mini App auth were not intentionally changed.
- `course_pilot_events` remains pilot telemetry only; broad conversion stats use `conversion_funnel_events`.

Files:
- `app/db/models/conversion_funnel_event.py`
- `alembic/versions/0046_add_conversion_funnel_events.py`
- `app/services/conversion_funnel_service.py`
- `app/services/course_trial_value_service.py`
- `app/bot/utils/trial_value_flow.py`
- `app/bot/handlers/start.py`
- `app/bot/handlers/messages.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/payments.py`
- `app/bot/handlers/admin_payments.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/commands.py`
- `app/main.py`
- `app/static/subscription.html`

Risk:
- Funnel events are append-only and may contain duplicate raw events; admin funnel uses unique telegram users per event to avoid over-counting repeated opens.
- Auto AI explanation adds one extra AI call only for non-paid users on lesson 1 full quiz, guarded by an `ai_explanation_seen` event check.

---

### 2026-06-23 - Course Mini App onboarding migration

Changed:
- Language selection now ends with two explicit choices: Course Mini App or the existing Telegram QA mode.
- Course onboarding is owned by the Mini App and stores level, goal, daily time, start point and timezone in `course_miniapp_profiles`.
- Start points are `lesson_1`, `continue` and `placement`; existing cross-level progress is never silently reset.
- Existing course users open `study.html` at their current lesson, while the legacy Telegram course flow remains the fallback if the WebApp message cannot be sent.
- Onboarding selection/completion analytics are server-backed and deduplicated.

Important:
- This migration does not change payment, subscription, referral or QA access rules.
- `Beginner` reuses HSK1 content; HSK4 renders through existing `hsk4a`/`hsk4b` assets.

Files:
- `app/services/course_miniapp_onboarding_service.py`
- `app/services/study_miniapp_service.py`
- `app/bot/handlers/start.py`
- `app/bot/handlers/course.py`
- `app/static/study.html`
- `app/static/study-v2.js`

---

### 2026-06-23 - Server-graded interactive lesson flow

Changed:
- Course Mini App lessons now load an authenticated canonical flow generated from existing `course_lessons` HSK material.
- Each flow contains 3-4 active words plus meaning, listening, sentence builder, word order, translation, pronunciation and quick-quiz cards; card order varies by lesson.
- Lesson completion requires every required card response and is graded again on the server. Client-supplied completion percentages are no longer accepted.
- Only a passing server result advances existing `CourseProgress`; homework is not a completion gate.
- Free lesson access uses `CourseMiniAppAccessService` entitlement and the existing assigned trial lesson. Payment/subscription rules were not changed.

Key files:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/services/course_miniapp_lesson_service.py`
- `app/services/study_miniapp_service.py`
- `app/main.py`
- `app/static/study.html`
- `app/static/study-v2.js`

---

### 2026-06-23 - Server-backed Test and Training

Changed:
- Placement and HSK1-HSK4 mock tests now use canonical questions generated from existing `course_lessons` material and are graded server-side.
- Listening, Writing and Characters training use the same HSK progression with skill filtering. Speaking continues to open AI Voice; Mistakes routes to the Mistake Engine area.
- Placement uses the separate `placement` free entitlement. Mock tests and skill training share the single `training_test` free entitlement.
- A free session is consumed when it starts; the same session can resume, but switching to another mock/training session is blocked after the one free use.
- Server records `test_started`, `test_completed`, `training_started` and `training_completed` events.

Key file:
- `app/services/course_miniapp_practice_service.py`

---

### 2026-06-24 — Referral `/start` onboarding resume fix

Changed:
- New users are now persisted with `learning_mode="onboard_lang"` until they choose language, then `learning_mode="onboard_mode"` until they choose Course/Oddiy mode.
- `/start` resumes incomplete onboarding instead of treating default `language="tj"` and `level="beginner"` as a completed setup.
- Referral payloads can attach for existing incomplete onboarding users, and duplicate referral rows are avoided by checking invited user first.
- Referral payloads also attach for existing unpaid users who do not already have a referrer. If such a user already has `questions_used >= 2`, the referral is activated immediately after attach.
- Existing pending referral rows are also recovered on `/start <referral_code>`: if the invited user has `questions_used >= 2`, the pending referral activates without waiting for another AI question.

Why:
- Referral links created/committed a user before onboarding finished, so later `/start` skipped language/mode selection and looked like the bot ignored the start command.
- Users who opened the bot first and came back through a referral link could lose the referral attribution.
- A user could enter via referral link and use the free QA limit, but still not count if their account looked like an already completed non-referred user before attach.
- A referral row could exist as `pending`, but after the invited user hit the free limit there might be no next successful AI question to trigger activation.

Files touched:
- `app/services/onboarding_service.py`
- `app/bot/handlers/start.py`
- `app/repositories/user_repo.py`
- `app/services/referral_service.py`
- `tests/test_onboarding_service.py`

Risk:
- No database schema, payment, subscription, or access rule changes. Existing completed users keep `learning_mode="qa"` or normal course entry behavior.

Follow-up:
- Smoke test with a clean Telegram user: open `https://t.me/<bot>?start=<referral_code>`, confirm language selection appears, then choose mode and verify the referral row is stored.

---

## 11. Known Problems

### Problem 1
Problem:
- Unknown / needs inspection

Suspected cause:
- Unknown / needs inspection

Status:
- Open / Fixed / Needs testing

---

## 12. Next Planned Work

Priority 1:
- Unknown / needs inspection

Priority 2:
- Unknown / needs inspection

Priority 3:
- Unknown / needs inspection

---

## 13. Required Environment Variables

Do not write real values here.

Required:
- `BOT_TOKEN`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `ADMIN_IDS`

Optional:
- Unknown / needs inspection

---

## 14. AI Assistant Instructions

Any AI coding assistant working on this project must:

1. Read this file before changing code.
2. Understand the current architecture before editing.
3. Make minimal changes.
4. Preserve working flows.
5. Never store secrets in this file.
6. Update this file only after important changes.
7. Do not write small cosmetic changes here.
8. If changing database/payment/subscription logic, explain the risk.
9. If unsure, inspect the code before guessing.
10. Do not rewrite this file completely unless explicitly requested.
