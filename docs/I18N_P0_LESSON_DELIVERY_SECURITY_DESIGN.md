# P0 — Course JSON delivery, entitlement and i18n compatibility decision

Status: **DESIGN REVIEW ONLY; NO RUNTIME MIGRATION AUTHORIZED**.
Branch `codex/i18n-local-first-foundation-20261017`, PR #179 Draft.
This note scopes a security / backward-compatibility gate for future
language overlays; it does **not** authorize payments/auth/lesson code changes.

## Confirmed existing code contract

| Contract | Source evidence | P0 interpretation |
| --- | --- | --- |
| Existing lesson GET | `app/main.py` `/course_v3_data/{level}/{filename}`, `course_v3_lesson_file` | Returns static JSON without handler-level auth/entitlement dependency |
| Path constraints | Same handler uses `fullmatch` for 7 tracks and `lesson_*.json` | Restricts traversal/filenames but does **not** authenticate users |
| API-only blocked-user middleware | `app/services/blocked_user_guard.py`, `GUARDED_PATH_PREFIX = "/api/"` | Does not protect this `/course_v3_data/...` route |
| Exam private-route response | `app/main.py`, `/course_v3_data/exams/{filename}` | Explicit HTTP 404; exam grading is not performed by exposing these files |
| Public curriculum-level map | `app/main.py`, `/course_v3_data/{filename}` | Serves matching top-level JSON; classify actual map contents before using as language-pack host |
| Mini App lesson caller | `app/static/course-v3.html` `lessonDataUrl` and `loadLessonData` | Uses direct unauthenticated `fetch(lessonDataUrl(...))`; N1 includes content revision and `cache:"no-store"` |
| Exam client caller | `app/static/course-v3.html` `/api/v3/exams/start`, `/complete` | Separate API interaction carries `X-Telegram-Init-Data`; keep server-owned exam grading |
| Legacy answer fields | P0 lesson AST/JSON audit: 746 lesson files, 6,449 answer-like field occurrences | Source can disclose practice correct indexes; *not* evidence that Pro billing was bypassed in live deployment |

Source evidence is reproducible via
`scripts/i18n_route_boundary_audit.py` and
`tests/test_i18n_route_boundary_audit.py`, archived in dedicated P0 CI
`static-route-security.json`. This is code inspection; **no external
production HTTP probe, CDN/proxy configuration audit or billing test** was
performed. Audit status is `SOURCE_REVIEW_REQUIRED`.

## Non-negotiable compatibility and security constraints

1. **Do not immediately block/rename the legacy static route.**
   Current Mini App lesson loader depends on direct GET with no per-request
   initData header. Changing it alone can break HSK 2.0/3.0 reading,
   checkpoint flows, review/preload, cached app builds and older clients.
2. **Do not expand the problem with new public Pro lesson overlays.**
   Shared web locale packs may contain only genuinely public UI messages.
   No assessment answer keys, grading metadata, private exam files,
   account information, or new paid lesson bodies in a public pack.
3. **Preserve existing source identities.** Track/lesson/card/option keys,
   Chinese, pinyin, lesson order, answer identity, XP/progress and grading
   remain stable. A localized prompt is not an answer-key rewrite.
4. **Honor Android direct/Play differences, Telegram Mini App, and Tauri.**
   A future secure-delivery change must identify every client version and
   API caller and preserve current subscription/trial policy.
5. **Local-first applies to UI copy, not permanent anonymous Pro delivery.**
   Bundle UI translations in each client. A gated lesson snapshot may need
   one authorized download and an offline-compatible local cache; avoid
   per-string network calls. Authorized cached content can still be copied
   by a client; online exams retain server-side grading.
6. **Do not rely on the `BlockedUserApiMiddleware` to enforce Pro.**
   Blocking, identity verification, paid entitlement and exam authorization
   are different controls. Permission is required at the content boundary.

## Proposed staged remediation (not implemented)

**A. Discover live access and client compatibility.** On a controlled QA
environment, check GET access matrix for seven tracks and source lessons
as anonymous, authenticated Free, Trial, Pro, blocked and expired users.
Determine CDN/reverse proxy rules and whether route responses are globally
cached. Review full source/client call sites including Android and Desktop
before proposing any 404/401 behavior. Do not log sensitive answers.

**B. Design a versioned, permission-checked lesson delivery path.**
Specify a separate authorized route with verified client credentials,
server-owned entitlement and lesson-access decision, bounded cache scope,
and a source-lesson revision bound to localized overlays. Version and
integrity-check authorized bundles; avoid shared CDN caches for private
content. Keep the existing public UI asset route independent.

**C. Migrate callers by compatibility group.** Mini App can ship new
fetch logic with authenticated lesson requests and private cache
management; evaluate Android direct and Play builds plus Desktop
separately. Old clients must receive a defined supported upgrade /
deprecation policy rather than being silently broken. Ensure failure
states distinguish network outage, access expiration, unavailable lesson
and incompatible revision.

**D. Remove unintended exposure only after compatibility and QA.**
Do not change the public route or relocate files until all supported
clients work with the replacement. Keep exam material private throughout.

## Required release gates / manual QA

- Identity/access table: anonymous, Free, Trial, Pro, pending receipt,
  rejected receipt, blocked, expired, and previously authorized offline.
- All 7 course tracks, old/new course switch, level restoration, checkpoints,
  review, quiz answer identity, XP/progress write, retry and cached fallback.
- Authenticated and unauthenticated direct URLs (including EXAM 404),
  CDN/private-cache behavior and stale signed/expired sessions.
- Mini App WebView (iOS/Android), native Android (direct + Play),
  Desktop (macOS/Windows), and Bot entry/deep links.
- Account language `uz/ru/tj` (UI `tg` alias), same source revision,
  localized asset cache/version update, offline launch and no per-string API.
- Monitor authorized/denied requests and compatibility failures using
  **status and counts only**, never lesson answers or sensitive headers.

**Exit condition:** documented identity/entitlement decision, actual route
and client E2E evidence, explicit user approval for runtime/billing scope,
green tests and rollout/rollback strategy. Until then P0 remains open;
P1/P2/P3/P4 stay blocked.

## Source-verified current client transport matrix (2026-10-17)

The separate `scripts/i18n_client_lesson_compat_audit.py` inventory
and `tests/test_i18n_client_lesson_compat_audit.py` guard the **present
client call chains**, without running a device or an HTTP request.

| Current client | Source call chain | Credentials and entitlement | Caching / migration |
| --- | --- | --- | --- |
| Mini App | `app/static/course-v3.html` `lessonDataUrl()` -> direct `fetch(/course_v3_data/<level>/lesson_*.json)` | **No auth header on that fetch**. Underlying static route has no handler-level entitlement dependency | In-memory per-lesson cache; N1 includes a revision parameter and `cache:no-store`. **Primary migration risk** |
| Native Android (shared `main` sources; direct/Play packaging) | `AndroidCourseApi.kt` Retrofit `api/v3/android/course/lesson/{lessonOrder}`, `CourseRepository.lesson()` | Bearer token supplied; Android route extracts token and calls `AndroidCourseService.lesson()` / inherited `DesktopCourseService.lesson()` | Server applies lesson-order and `LessonAccessService.status(..., consume=True)`; response `Cache-Control: no-store`. Room caches previously authorized envelope, with offline/timeout-only fallback; cache cleared on logout |
| Tauri Desktop | `desktop/ui/js/lesson.js` -> `bridge.lessonData` -> `desktop_lesson_data` Rust command | `authenticated_get_json` uses Bearer auth (including token refresh); backend `desktop_course_lesson` verifies token and calls `DesktopCourseService.lesson()` | Server enforces lesson-order and entitlement; `Cache-Control: no-store`. Any released Desktop version / desktop offline cache policy still requires QA |

These findings **narrow the proposed new delivery implementation**:
the currently checked native Android and Desktop flows **already use
authorized lesson APIs**, so replacing their content URL is not by
itself justified. The Mini App's unauthenticated static lesson URL is
the primary known caller to migrate. A complete repository/build audit,
released-binary inspection and live permission tests remain required
before legacy route removal.

### Cache and unauthorized-state invariant

A previously authorized lesson copied to Android's offline Room store
may be reopened **only on transport `Offline` or `Timeout`**.
When the server returns an authenticated denial (401, expired,
403, quota exhausted, lesson still locked), this source-level policy
must not silently fall back to a cached lesson. Logging out clears
both `course_lesson_cache` and `course_map_cache` via their DAOs.
Offline access to already downloaded content cannot guarantee
instant revocation without network access; define an explicit
commercial/security policy rather than assuming otherwise.

**Regressions:** source-only P0 CI fails when the current native
lesson endpoint disappears, client auth-header contract changes,
native server authorization or `consume=True` checks disappear,
Android offline cache fallback broadens beyond network failures,
or the existing Mini App loading behavior unexpectedly changes.
The current Mini App public GET remains a **manual P0 blocker**,
not a CI failure. These checks do not prove that deployed clients,
upstream proxies or billing states behave as source suggests.

### QA access table to execute before any runtime change

For each of seven tracks, test a real allowed and a real locked
lesson, with at least one `n=01` and a paid/advanced lesson.
Run identical states using Mini App, Android direct, Android Play,
and Desktop. Do not collect real user tokens or quiz answers in reports.

| Identity state | Expected secure API behavior to verify | Legacy public route question |
| --- | --- | --- |
| Anonymous / no credentials | 401/403 from new gated API | Does static JSON remain obtainable anonymously? |
| Authenticated Free, quota available | Only eligible lesson and policy-defined daily consumption | Can advanced lesson JSON be fetched bypassing UI? |
| Free, quota exhausted | Deny paid/consumed lesson; no stale-cache bypass | Is the underlying static JSON still readable? |
| Trial / active Pro | Permit only currently entitled and unlocked lesson | Is it accessible without user authentication anyway? |
| Pending / rejected receipt | Existing established entitlement policy, not guessed from UI | Does download bypass admin approval? |
| Blocked / expired session | Explicitly deny API access; preserve logout/cache policy | Does a direct anonymous GET bypass the account block? |
| Offline with earlier approved lesson | Allow only policy-defined already downloaded lesson on native Android | No new network fetch; verify cache isolation per account |

On denial, confirm Android does **not** use disk content when the
server explicitly rejected the request. Test offline timeout
separately from revoked/expired token. For all clients verify
checkpoint and assessment IDs, language switching `uz/ru/tj`,
level/track restoration and source revision / cache invalidation.
**No part of this matrix was executed against QA/production yet.**

### Android account-switch cache-clear chain (source verified)

This extends the offline/cache contract beyond the DAO alone:

- `AuthRepository.logout()` invokes `clearLocalSession()`, and
  `HskAiApplication` registers `onSessionCleared = ::clearWidgetSession`.
  The widget callback by itself is **not** responsible for course data.
- The Android screen `MainActivity.kt` calls `app.clearLocalData()`
  after an explicit `authRepository.logout(...)`. Its
  `AuthState.Unauthenticated` branch also calls
  `app.clearLocalData()` on entry.
- `HskAiApplication.clearLocalData()` invokes
  `courseRepository.clearCache()`, which calls both
  `dao.clear()` and `lessonDao?.clear()`. These are the
  Room cached course maps and previously opened lesson envelopes.

`scripts/i18n_client_lesson_compat_audit.py` now checks this
full source-level chain, not merely the existence of a DELETE DAO
method; negative regression fixtures intentionally remove the
actual logout cleanup invocation and the app-to-repository call.
[Fast P0 CI 39012928501](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39012928501)
**SUCCESS**.

**Not a device-level guarantee:** process death, multiple accounts,
rapid logout/login, concurrent in-flight cache writes, interrupted
Room clearing, older installed APKs and device security remain
separate QA cases. Release gate: with account A's downloaded Pro
lesson on disk, sign out (including offline), sign into B, and
confirm A's course/lesson cache is not available to B.
