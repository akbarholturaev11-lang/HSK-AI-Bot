# Pomp HSK AI Android — implementation plan

Audited against `be71926f`. This document records the **verified** current
backend behaviour, not assumptions. Where an older document disagrees with the
source, the source wins and the disagreement is listed in
"Corrected stale assumptions".

## 1. Product boundary

The Android app is a new **native client of the existing HSK AI ecosystem**, not
a new product. Telegram bot, Mini App, macOS, Windows and Android share one
canonical account, subscription entitlement, HSK level, course progress,
XP/streak/league, mistakes, referral identity and analytics user.

Android is not a WebView wrapper, not a second backend and not a second
account system.

## 2. Corrected stale assumptions

| Source | Stale claim | Verified reality |
|---|---|---|
| `DESKTOP_AUTH_CONTRACT.md` §Device-link flow, step 4 | User opens `https://t.me/<bot>?start=desktop_<code>` | `desktop_auth_service.py:272` returns `?start=desktop_link`. The 8-char code is **never** in the URL; the user types it manually into the bot chat (commit `28ac3dc4`). Android preserves this. |
| `PROJECT_MEMORY.md` §1–8 | Filled project profile | Still the unedited template ("Unknown / needs inspection"). Only §9–10 carry real history. |
| `graphify-out/GRAPH_REPORT.md` | Current graph | Built from `d69e67af`; HEAD is `be71926f`. Run `graphify update .` after this work. |
| General assumption | Sections carry a `type` field | Lesson sections expose `section_no`, `section_title{uz,ru,tj}`, `section_purpose`. There is no `section.type`. |

## 3. Verified backend facts

### 3.1 Auth core — `app/services/desktop_auth_service.py`

- Access token: custom HMAC-SHA256, header `{"alg":"HS256","typ":"POMP"}`,
  claims `typ/sid/did/uid/iat/exp/jti`. Default TTL 900 s
  (`DESKTOP_AUTH_ACCESS_TTL_SECONDS`, clamped 300–3600).
- Refresh token: `pomp_r1_` + `secrets.token_urlsafe(48)`. Default 30 days
  (`DESKTOP_AUTH_REFRESH_TTL_DAYS`, clamped 1–90). Stored server-side only as a
  keyed hash.
- Rotation on every refresh; `previous_refresh_token_hash` reuse immediately
  revokes the session (`desktop_refresh_reuse_detected`).
- Link request: 8 chars from `23456789ABCDEFGHJKLMNPQRSTUVWXYZ` (no ambiguous
  glyphs), single-use, default TTL 600 s, `with_for_update()` row lock,
  `hmac.compare_digest` on the polling secret.
- Installation binding: an active `DesktopDevice` cannot move to another user
  (`desktop_device_bound_to_other_user`) until explicitly unlinked.
- Rate limits: 5 link starts / 5 min per installation hash, plus a global
  window (`DESKTOP_AUTH_LINK_GLOBAL_RATE_LIMIT_*`). The global guard is a
  non-atomic `count → insert`; unchanged by this work, still an open item.
- Fail-closed: `DESKTOP_AUTH_SIGNING_SECRET` must be ≥ 32 chars, else `503
  desktop_auth_unavailable`.

**Android reuses this service unchanged.** Only the platform allowlist widens.

### 3.2 Storage — `app/db/models/desktop.py`

`desktop_link_requests`, `desktop_devices`, `desktop_sessions`. `platform` is
`String(16)`, so `"android"` needs **no migration and no table rename**. The
tables stay named `desktop_*`; renaming them for naming purity is explicitly out
of scope.

### 3.3 Course data — `app/static/course_v3_data/`

- 425 mini-parts, flat per level: `hsk1=63`, `hsk2=72`, `hsk3=109`, `hsk4=181`
  (`parts_manifest.json`, read by `app/services/course_v3_parts.py`).
  Kotlin must **never** hardcode these totals.
- `completed_lessons_count` counts **parts**, not textbook lessons.
- Lesson JSON top level: `schema_version`, `level`, `lesson_id`,
  `source_lesson`, `part_no`, `part_count`, `checkpoint`, `title`, `subtitle`,
  `intro_prebuilt`, `grammar_prebuilt`, `active_words`, `grammar`, `dialogues`,
  `sections`.
- Section: `section_no`, `section_title{uz,ru,tj}`, `section_purpose`, `cards`.

**Card types actually present (14, exhaustive):**

| type | count | payload keys beyond `type` |
|---|---|---|
| `active_word` | 1312 | `word` |
| `pronunciation` | 843 | `phrase`, `pinyin`, `translation` |
| `listening_choice` | 820 | `audio_text`, `pinyin`, `title`, `options`, `correct_index`, `explanation` |
| `meaning_guess` | 787 | `prompt`, `title`, `options`, `correct_index`, `explanation`, `review_mix`, `review_origin`, `review_word` |
| `translation_choice` | 770 | same shape as `meaning_guess` |
| `match_pairs` | 621 | `pairs`, `explanation` |
| `hanzi_choice` | 397 | `prompt`, `title`, `options`, `correct_index`, `explanation` |
| `pinyin_choice` | 378 | same as `hanzi_choice` |
| `_grammar` | 251 | `g` |
| `quick_quiz` | 246 | same as `hanzi_choice` |
| `sentence_builder` | 183 | `sentence`, `tokens`, `answer_tokens`, `explanation` |
| `reverse_builder` | 178 | `zh`, `pinyin`, `translation`, `tokens`, `answer_tokens`, `explanation` |
| `gap_fill` | 133 | `sentence`, `prompt`, `options`, `correct_index`, `explanation` |
| `dialog_cloze` | 70 | `lines`, `title`, `options`, `correct_index`, `explanation` |

`review_mix` / `review_origin` mark the end-of-lesson retention-review deck
(one card from the previous part, one from the current part).

Unknown future card types must render a recoverable "unsupported card" state,
emit a non-sensitive diagnostic event, and **never auto-grade as correct**.

### 3.4 Access policy — `desktop_course_service.apply_course_v3_access_policy`

- `FREE_COURSE_LESSONS_PER_LEVEL = 2` — first two mini-lessons fully free.
- Part `FREE_COURSE_LESSONS_PER_LEVEL + 1` when it is the current lesson:
  `preview_half = true`, `completion_allowed = false`,
  `completion_error = "free_feature_limit_reached"`.
- Everything later: `locked_premium = true`, `completion_allowed = false`.
- Server decides. The client renders entitlement; it never invents unlocks.
  An offline cache may only ever be a **conservative** snapshot of the last
  known server entitlement.

### 3.5 Existing bearer surface (reusable pattern)

`app/api/desktop_course.py` + `DesktopCourseService` is the reference adapter:
`Authorization: Bearer <access>` → `DesktopAuthService.authenticate()` →
canonical `User` → existing service. Android copies this pattern and adds no
business logic of its own.

Already bearer-authenticated today:

```
POST /api/v3/desktop-auth/link/start
POST /api/v3/desktop-auth/link/status
POST /api/v3/desktop-auth/refresh
POST /api/v3/desktop-auth/revoke
GET  /api/v3/desktop/bootstrap
GET  /api/v3/desktop/course/map
GET  /api/v3/desktop/course/lesson/{lesson_order}
POST /api/v3/desktop/course/complete
POST /api/v3/desktop/preferences/language
POST /api/v3/desktop/events
GET  /api/v3/desktop/subscription/overview
POST /api/v3/desktop/subscription/{discount-start,quote,event,submit}
```

Still Telegram-`initData`-only, therefore needing Android bearer adapters:

```
/api/v3/map  /api/v3/lesson/complete  /api/v3/lesson/unlock  /api/v3/language
/api/v3/invite  /api/v3/notify  /api/v3/avatar/{telegram_id}  /api/v3/tts
/api/v3/exams/start  /api/v3/exams/complete
/api/v3/practice/daily-gate  /api/v3/practice/ad-gate  /api/v3/ad*
/api/miniapp/profile  /api/miniapp/gamification  /api/miniapp/access
/api/miniapp/practice/start  /api/miniapp/practice/complete
/api/miniapp/mistakes  /api/miniapp/mistakes/review/{start,answer,complete}
/api/miniapp/reward-chest/open  /api/miniapp/challenges*  /api/miniapp/event
/api/voice-practice/me  /api/voice-practice/session/start
/api/voice-practice/message  /api/voice-practice/session/end
/api/voice-practice/pronounce
```

## 4. Auth strategy — option B (thin adapter)

Chosen deliberately over generalising the core, because the core is live in
production for macOS and Windows.

1. `DESKTOP_PLATFORMS` gains `"android"`. Nothing else in the service changes.
2. New `app/api/android_auth.py` exposes `/api/v3/android-auth/*` and
   `/api/v3/android/bootstrap`, delegating to the **same** `DesktopAuthService`.
   No cryptographic or session logic is duplicated.
3. `app/bot/handlers/desktop_auth.py` gets a platform→label map (fixing the
   `"Mac" if macos else "Windows"` shortcut that would show Android devices as
   Windows) and Android-appropriate UZ/RU/TJ copy.
4. No migration. No table rename. Desktop endpoints are untouched.

### Android link flow (identical security properties)

1. App generates a random installation key, stored in Android
   Keystore-backed encrypted storage.
2. `POST /api/v3/android-auth/link/start` → `link_request_id`, `display_code`,
   `polling_secret`, `bot_deep_link`, `expires_in`.
3. App shows the code and a `Telegramni ochish` button opening
   `https://t.me/<bot>?start=desktop_link`. **The code is never in the URL.**
4. User sends the 8 characters manually. Bot shows `Android`, app version and
   code, then requires explicit Approve/Cancel.
5. App polls `link/status`; the first approved poll consumes the link and
   returns the access + refresh pair. Later polls never return tokens again.

### Client token rules

- Access token lives in memory; refreshed transparently on 401.
- Refresh token lives only in Keystore-backed encrypted storage — never
  DataStore plaintext, SharedPreferences, logs, analytics, crash reports or
  URLs.
- Rotation is persisted atomically before the old token is discarded, so
  process death cannot strand the session.
- `desktop_refresh_reuse_detected` / `desktop_session_revoked` → clear local
  credentials and return to the link screen.
- Logout attempts server revoke, then always clears local credentials.
  `Unlink this device` additionally sets `revoke_device=true`.

## 5. Android architecture

Single Gradle application module, strong package boundaries, `com.pomp.hskai`.
`compileSdk`/`targetSdk` 36. ViewModel + StateFlow, unidirectional state; no
networking in composables, no business logic in Activities.

```
android/app/src/main/java/com/pomp/hskai/
  core/{auth,network,storage,design,navigation}
  data/{api,local,repository}
  domain/model
  feature/{onboarding,today,course,lesson,practice,voice,mistakes,profile,subscription}
  widget  notifications  billing  analytics
```

### Localisation note

Backend language codes are `uz` / `ru` / `tj`. Android resource qualifiers are
`values` (uz default), `values-ru`, and **`values-tg`** — Tajik is ISO-639-1
`tg` on Android, not `tj`. A single mapping helper owns this conversion; the
backend value is never sent as `tg` and the resource folder is never named `tj`.

## 6. Design tokens

Paper `#FDF9F0`, ink `#211D17`, secondary ink `#665D50`, cinnabar `#E04A40`,
dark red `#B23530`, jade `#2FA06A`, gold `#E9A916`. Material 3 is the technical
base only — no default Material blue. Dark mode ships only when it is designed
intentionally, never as an automatic inversion of the cream palette.

The panda uses the project's own identity (`hsk-ai-avatar.webp`,
`hsk-ai-cover.webp`, and the Course v3 `pandaChar` pose language). No Duolingo
artwork, no one-to-one imitation. Reduced-motion settings are honoured.

## 7. Policies

**Offline.** Room caches the course map, current lesson, next few accessible
lessons, recent completions, a progress snapshot and widget data. Server stays
authoritative. AI Voice, new premium unlocks, billing and server-gated practice
require network. Offline completion queueing ships only when it is
conflict-safe and idempotent; until then, study offline but reconcile on
reconnect. Correctness beats fake offline completeness.

**Completion.** Server-authoritative and idempotent. Client event IDs are
`android:<uuid>`; the backend adapter uses an Android-specific dedupe namespace
rather than impersonating desktop. Duplicate retries return the existing result
and never double-award XP or progress.

**Widget.** Jetpack Glance, responsive layouts (not fixed cell sizes). Content
derives from local cached state plus the current time slot, so a delayed
background refresh never makes it useless. Roughly hourly WorkManager refresh,
plus immediate refresh after bootstrap, course sync, lesson completion,
XP/streak change, language change and login/logout. No permanent foreground
service, no exact-alarm abuse. Widget actions use the fixed subset
`pomp-hsk-ai://lesson/current`, `…/practice/<tool>`, `…/voice`, `…/course` —
never arbitrary URLs from a payload. Widget state is cleared on logout and
never contains tokens.

**Deep links.** The allowlist is exact-arity, mirroring the desktop client's
exact path matching: a trailing segment invalidates the whole URI instead of
resolving to its prefix. `pomp-hsk-ai://lesson/<n>` **is** addressable, because
the existing reminder flows already target an exact lesson
(`motivation_reminder_service` sends `target_level` + `target_lesson` with
`autostart`) and those become Android notifications in Phase H. The number is
bounded to the backend contract `1..500` (`app/api/desktop_course.py`).
Resolving a URI is never authorisation: `AppDestination.Lesson` carries only an
order, and navigation must confirm progress and entitlement against the server
before showing anything.

**Notifications.** At most ~1–2 useful reminders per day by default, respecting
existing user notification settings and avoiding duplication with the Telegram
bot. Android 13+ permission is requested only after the benefit is explained;
denial keeps the app fully usable.

**Billing.** Google Play Billing for Play-distributed purchases. The existing
Telegram/desktop Visa/Alipay/WeChat checkout is **not** copied into the Play
build. `POST /api/v3/android/billing/verify` resolves the user from the bearer
token, verifies the purchase with Google, is idempotent, maps product/base-plan
to the canonical entitlement, and never trusts client-sent price or duration.
An existing paid Telegram user must get Android access without repurchasing,
and an existing manual subscription is never auto-converted to a Play
subscription. The desktop guard against unsafe renewal (activation can start a
fresh period rather than extend the remaining one) is preserved.

**Analytics.** Separate `android_*` event names; never mixed into `desktop_*`.
Never logged: access token, refresh token, polling secret, installation key,
raw purchase token, private audio.

**Pronunciation.** Existing scoring is STT/CJK-match based. It must not be
described as tone analysis anywhere in the UI or the Play listing.

## 8. Phases

| Phase | Content | State |
|---|---|---|
| A | Audit + this document | done |
| B | Gradle/Compose/theme/nav/network/storage foundation | in progress |
| C | Telegram device auth, backend adapter + client + tests | in progress |
| D | Today + Course map | planned |
| E | Native lesson renderer (all 14 card types) | planned |
| F | Practice (mistakes, recognition, memorize, pronunciation, tests, gates) | planned |
| G | AI Voice | planned |
| H | Widget + notifications | planned |
| I | Profile / referral / settings | planned |
| J | Google Play Billing | planned |
| K | Offline hardening | planned |
| L | Analytics, admin stats, CI, release | planned |

## 9. External blockers (code path implemented, fail-closed)

These cannot be resolved from the repository and must be supplied later:

- Google Play Console subscription product IDs and base plans.
- Google Play service-account credentials for server-side purchase verification.
- Android release signing keystore (never committed).
- Play store listing values and Data Safety declaration inputs.
- `gradle/wrapper/gradle-wrapper.jar` — a binary that must be generated once by
  `gradle wrapper` or Android Studio; it is not fabricated here.

## 10. Release gates

- `targetSdk 36`, release AAB builds, no committed signing secrets.
- Play Billing handles Android digital purchases; the backend verifies them.
- An existing externally-paid user reaches Android content without repurchase.
- Telegram auth verified on a clean device; widget verified on a real launcher.
- Permissions minimal (`INTERNET`, `RECORD_AUDIO`, `POST_NOTIFICATIONS`).
- Data Safety declaration is truthful; no fake production data anywhere.
- macOS, Windows, Telegram bot and Mini App still work unchanged.
