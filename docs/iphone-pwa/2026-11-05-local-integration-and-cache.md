# iPhone PWA — local Codex work + PR #262 integration, cache and slow-network walk (2026-11-05)

## Integration decisions

- Kept the local in-place layers: checkout and every practice screen mount inside the live course document (iframe layer). Back/swipe removes the layer in 5–45 ms and the course never reloads. PR #262's same-tab history/BFCache nonce became dead code and was removed; direct checkout links keep the deterministic course fallback.
- Kept the dedicated full-screen Settings screen (`#s-settings`) instead of the stretched sheet. Removed the PR's unused `pwa-settings-page`/`data-mode` CSS.
- Took from PR #262: server redirect for returning users, cancellable HSK level loads, `/api/v3/pwa/profile` and `/api/v3/pwa/invite`, browser Friends sharing, Safari `expirationTime` push fix, neutral mic/voice errors, deferred trail drawing. `/api/v3/pwa/preferences` was declared twice; the shared `miniapp_preferences` helper version remains.
- `hotspot_triage` line anchors (62 lines, 130 predicates, none added) and the three classified lesson reads were remapped to the new 9734-line course file.

## Measured walk-through (Playwright WebKit, iPhone 13 viewport)

Real shipped HTML/JS/CSS with synthetic authenticated API. Network simulated per request:
slow = +300 ms RTT, 120 KB/s; bad = +700 ms RTT, 40 KB/s. These are not device numbers.

| Step | fast | slow | bad |
|---|---:|---:|---:|
| Cold launch → course | 1.1 s | 3.0 s | 8.2 s |
| Tab switch (course/mashq/voice/profile) | 30–90 ms | 30–80 ms | 35–80 ms |
| Rating tab (leaderboard fetch) | 30 ms | 350 ms | 800 ms |
| Lesson open / swipe → exit confirm / exit | — | 0.8 s / 0.2 s / 50 ms | 1.7 s / 0.2 s / 85 ms |
| Practice layer first paint | 20–50 ms | 20–50 ms | 20–50 ms |
| Practice/checkout back (layer close) | 4–7 ms | 4–7 ms | 4–7 ms |
| Dictionary content, before fix | — | 12.2 s | — |
| Dictionary content, after fix (cold) | — | 1.7 s | 5.5 s |
| Dictionary content, after background warm | — | 0.68 s | — |
| Checkout prices | 36 ms | 0.6 s | 1.6 s |
| Inbox / Settings open | 40 ms | 0.7 s / 30 ms | 1.5 s / 30 ms |
| AI Voice start | 65 ms | 0.34 s | 0.74 s |
| HSK 1 → HSK 2 switch | — | 1.5 s | 1.6 s |

## Fixes in this pass

- **Dictionary outlier (P1):** `hsk-lugat.html` loaded `hsk-extra.js` (2.8 MB, 1.1 MB gzip: strokes, examples, HSK 4 grammar) as a blocking script, plus the Telegram SDK from `telegram.org`. Every reader already tolerates the absence of that data, so it now loads asynchronously; dictionary and phrases use the same-origin SDK copy.
- **Worker cache:** `iphone-pwa-sw.js` serves only same-origin, `?v=`-pinned JS/CSS/fonts/images Cache First, keeps up to three versions per path, and warms the dictionary/practice/checkout dependencies sequentially once the course is idle (at most every 12 h). HTML, API, lesson content and audio always use the network. iOS may evict the cache; every miss falls back to the network.
- **Version rule (guarded):** with Cache First, a changed asset with an unchanged `?v=` would stay stale. Every `iphone-pwa-*` reference now carries `<date>-<git blob sha1[:12]>`; `tests/test_iphone_pwa_asset_versions.py` fails if bytes change without a new token.
- **HTML revalidation:** course, practice, checkout, dictionary and phrases shells are `private, no-cache` with a content-hash ETag; a 304 is returned only after the session check. Verified in Chromium (304, 0 bytes). Playwright WebKit keeps no document HTTP cache, so iPhone Safari behaviour must be confirmed on a device.
- `/iphone-pwa/dictionary` and `/iphone-pwa/phrases` serve the public pages inside the worker scope. The manifest `start_url` is `/iphone-pwa/course` (new installs skip the sign-in redirect).
- An expired PWA session (map 401) now returns to the iPhone sign-in page instead of the Telegram "open in bot" gate.
- UI (hsk-ai-ui review): the Inbox button no longer sits on a white card (matches Settings); the Settings push row has a valid icon and a short state; Logout is the last Settings row; Ready phrases has a PWA-only back button before search (Android order); the Telegram/standalone layout is unchanged.
- Visible-copy scan of 21 screens in UZ/RU/TJ found no Telegram/bot/`/start` wording in the PWA.

## Still requires a real installed iPhone

304 revalidation in Safari, worker cache persistence, Apple Web Push receipt (payment approved/rejected, account restriction, course and admin notices are queued server-side behind `PWA_PUSH_ENABLED` and `PWA_PUSH_SEND_ENABLED`), and microphone and Live voice behaviour. Live remains disabled for the PWA (`live_available=false`).
