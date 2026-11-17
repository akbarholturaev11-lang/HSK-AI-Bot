# Learner PWA push must render the source event

- **Cause:** the regular outbox dispatcher and Smart PWA adapter replaced the
  existing Telegram/inbox content with `HSK AI` and a generic notification body.
  iOS already supplies the app name, so this also repeated the brand. The worker
  then silently cut every body to 160 characters.
- **Fix:** `learner_pwa_push_copy.py` renders owned source rows using the current
  account language and canonical bot/admin templates. Telegram HTML becomes
  plain text; its headline/emoji appears once. The app name is omitted from
  supplied copy. Trial/limit rows retain render arguments. Legacy rows without
  recoverable arguments use contextual UZ/RU/TJ fallbacks; dynamic campaign
  copy is kept when its language matches, never machine-translated at runtime.
  Smart PWA uses its existing per-language template and actual lesson number.
- **Risk:** opted-in notifications now display their educational/account message
  on the lock screen. Payment amounts, receipts and admin comments remain out
  of push. Source/template reads finish before provider IO. Text is bounded to
  80/1000 characters and 2400 UTF-8 body bytes, leaving Web Push payload room.
- **Prevention:** `tests/test_learner_pwa_push_copy.py` covers all source types,
  Telegram text, emoji, HTML, language switching, legacy fallback and payload
  limits. `tests/test_pwa_browser_auth.py` covers all three outbox sources,
  retry-language refresh, stable tags, deduplication, revocation, 410 and auth.
  `tests/test_smart_reminder_pwa.py` retains its single-attempt/no-mirror guards.
  `node tests/test_pwa_push_worker.js` and Chromium/WebKit
  `tests/e2e/test_pwa_push_worker.py` execute the actual worker handlers with
  OS/provider interfaces stubbed, checking copy, badges, tags and safe clicks.

**Analytics Impact:** presentation only. Existing outbox/Smart attempt facts,
acknowledgments and click route are unchanged; no new event/denominator or
inference of actual iOS display is introduced. Provider acceptance is still
not device-display proof. Physical installed-iPhone notification appearance
and Apple delivery cannot be established by the automated harness.

Validation in the task workspace: the broad backend/security/localization/
notification suite passed 319 tests (49 environment-gated tests skipped), plus
focused latest-change regressions and both three-locale Chromium/WebKit worker
runs. Catalog regeneration/check, the UI adoption audit, frozen-source guard,
Python compilation and Node worker/inbox checks passed. The pre-existing login
source assertion was updated to reflect main's conditional Li-resume redirect;
production login code was unchanged. WebKit's missing Debian libraries were
extracted into the user-owned browser cache; its system-only `ldconfig` check
was skipped only after verifying those libraries load. Browser assertions were
not skipped. Physical Apple delivery/display remains unverified.
