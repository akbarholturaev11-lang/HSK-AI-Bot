# Telegram Mini App initData age: staged, non-breaking security review

## Verified root cause (2026-10-21)

Telegram supplies `auth_date` and signed `initData` at Mini App launch.
`app/static/course-v3.html` captures `tg.initData` once into `INIT_DATA`
and reuses it for API calls, including WebView bfcache/navigation recovery.
`extract_verified_webapp_user_id` validates the HMAC but **does not
enforce freshness**. The separate administrator verifier validates freshness
with `ADMIN_MINIAPP_AUTH_MAX_AGE_SECONDS` (24 hours). The Mini App cannot
guarantee a fresh launch credential on every HTTP request while left open.

## Safe first-stage implementation

- `classify_verified_webapp_init_data_age` checks the verified HMAC
  and buckets credentials into `fresh`, `stale`, `future_auth_date`,
  `invalid_auth_date`, `invalid_signature`. The default reference
  window is 24h (86,400 seconds), with 60s future-clock tolerance.
- For the Mini App entitlement/lesson-start router only, **1 out of 128**
  successfully authenticated requests is inspected when
  `MINIAPP_AUTH_AGE_AUDIT_ENABLED=True` (default). Only the category
  is logged. No tokens, user IDs, timestamps or request payloads are
  persisted by this observation. It adds no external/DB calls.
- **No expiry rejection was introduced.** The HMAC and existing account
  authorization are unchanged. The code does not affect free/trial/Pro,
  skip-test, lesson unlocking, grading or subscriptions.
- A long-lived signed session is still allowed even if its age exceeds
  the observation window. Do not claim the replay risk has been removed.

## Required next gate (not completed)

1. Run a consented staging/client test with a Telegram WebView kept open
   beyond 24 hours, background/resume and app navigation included, and
   observe whether Telegram refreshes `initData` without a full reopen.
2. Review aggregated **age-category only** telemetry, not user/session
   identifiers. Verify authenticated flow recovery for genuinely expired
   launch credentials, without using unsigned client state as identity.
3. Inventory all Telegram-dependent API entrypoints before applying a
   single consistent maximum age; partial enforcement on one route would
   leave others accepting replayed credentials.
4. Only after recovery and compatibility checks, enable real expiration
   enforcement with targeted 401/reopen UX and regressions for stale, future,
   valid, forged and long-lived sessions. Do not apply the admin TTL directly
   to learner requests without these checks.

References:
- https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
- https://docs.telegram-mini-apps.com/packages/tma-js-init-data/validating
