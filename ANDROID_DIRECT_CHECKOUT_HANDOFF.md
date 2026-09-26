# Android direct APK checkout — handoff

Branch: `codex/android-direct-subscription`. Do not release or merge to `main` before the checks below pass.

## Implemented

- Full-window limit dialog in course, lesson, practice and voice. Direct APK: Pro opens native checkout; eligible account sees trial and quiet “Keyinroq”; trial-used account sees “Keyinroq” as the second button. The Play flavor has no manual checkout UI.
- Android bearer-authenticated `/api/v3/android/subscription/checkout/{overview,quote,submit}` delegates to `DesktopSubscriptionService` and the existing `SubscriptionMiniAppService`. Server owns prices, conversion, discounts, QR and admin approval; the device cannot set amount, user ID or entitlement. PNG/JPEG/WebP receipts up to 8 MiB use the existing strict data URL validator and Telegram photo delivery.
- `payments.source` migration `0087_payment_source` adds a default for old rows. New Android receipt writes `android`, Mini App `miniapp`, Desktop `desktop`. Admin Telegram caption includes the source and 3-month plan label; admin payments board shows an Android badge.

## Verification still required on a development machine

This runner has no FastAPI/SQLAlchemy/pytest environment and cannot download Gradle 8.14.5 from services.gradle.org. Python compilation, XML parsing, named arguments and flavor parity checks passed. Before merging:

`graphify update .` was attempted as required by AGENTS.md; `graphify` is absent here, so refresh the graph in the development environment.

1. Install `requirements-dev.txt` and run `python -m pytest tests/test_desktop_subscription_api.py tests/test_android_features_api.py tests/test_admin_billing_regressions.py`.
2. Run `cd android && ./gradlew :app:testDirectDebugUnitTest :app:testPlayDebugUnitTest :app:compileDirectDebugKotlin :app:compilePlayDebugKotlin`, plus `python tools/check_flavor_parity.py` and `python tools/check_named_arguments.py`.
3. Apply `alembic upgrade head` in a staging database before exposing the API. With a staging Android account, open the limit screen in both trial states; confirm Pro checkout receives live plan prices, card instructions and Alipay/WeChat QR. Upload a test receipt; verify only one pending payment, the actual photo arrives at the admin chat, its caption and admin payment board identify Android, and no Pro access opens before an admin approves. Verify rejection/approval refresh on reopen.
4. Only after staging verification, bump `appVersionCode` for an actual APK release, merge the tested commit to `main`, then use the existing release workflow. The Play artifact must have no manual checkout screen.
