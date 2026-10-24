# First-party management commands

Only the standalone Admin PWA uses these `/api/admin/v1` routes. Existing
Telegram guards and shared business services remain separate entry points.
External MCP has no management capability. Rollout defaults remain OFF.

Every command requires an active canonical allowlisted WebAuthn cookie, strict
same-origin HTTPS POST and a validated bounded body. Prepare returns the exact
operation for confirmation; the browser passes it unchanged through the
existing step-up ceremony. Save validates the canonical payload again, locks
the target, compares the prepared revision, rechecks current actor/expiry, and
commits the shared-service change, one-use proof consumption and immutable
0126 command audit together. No mutation is automatically retried after an
uncertain response.

| Command | Routes | Scope and existing owner |
| --- | --- | --- |
| `payments.review` | `/payments/prepare-review`, `/payments/review` | Existing payment review and entitlement services; receipt confirmation required |
| `users.grant_access` | `/users/prepare-access`, `/users/grant-access` | Shared manual subscription grant, 1–365 days, no fake Payment/revenue/AI budget |
| `course.access_policy` | `/course-access/read`, `/prepare`, `/save` | Global subscription/free-until policy, explicit timezone, maximum 365-day free deadline |
| `hsk30.settings` | `/hsk30/read`, `/prepare`, `/save` | Global rollout, canonical live levels, checkout switch, 1–10000 TJS price; no direct permanent grants |
| `subscription.prices` | `/subscription-prices/read`, `/prepare`, `/save` | Nine fixed payment-method/plan targets; shared Visa normalization and currencies |

Subscription price read returns a fixed nine-row projection, never a paginated
scan. Prepare accepts only `method=visa|alipay|wechat`,
`plan=10_days|1_month|3_months`, integer `amount=1..1000000`. Its operation target
is `method-plan`, with a raw stored-state revision hash. An absent row has its
own revision; normalized legacy currency cannot conceal an intervening write.

PostgreSQL setting/price writers share deterministic transaction advisory locks
through `BotSettingRepository.lock_key`; this covers absent rows as well as
existing row locks. Read paths never acquire these locks or write defaults.
Multi-key callers lock touched keys in sorted order. PWA save transactions bound
lock/statement waits to five/eight seconds and validate proof/session expiry
after the target wait. Legacy Telegram HSK30 updates acquire the same sorted
keys without changing their partial-update semantics.

Regression evidence lives in `test_admin_pwa_course_access.py`,
`test_admin_pwa_subscription_prices.py`, `test_admin_pwa_hsk30_settings.py` and
the UUID-schema-only `test_admin_pwa_settings_postgres.py`. The PostgreSQL suite
covers two admins on an absent setting, legacy-vs-PWA first-row writes and
expiry during a real lock wait. Failure rolls back proof, audit and settings.
