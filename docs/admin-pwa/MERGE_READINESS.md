# Admin PWA — main merge preparation, rollout OFF

Owner request (2026-10-24): prepare the Admin PWA for merging into main.
Actual main promotion, activation and production deployment are separate actions.
Work remains on `codex/admin-pwa`; no main push, rebase or history rewrite.

## Base synchronization and review

- Main snapshot: `fb185be5cf481afcc62964951377fdd769df2fbe`.
- Feature starting checkpoint: `bfc5b41756b5c3d891788e8ed9f477018ba9143a`;
  previous verified code/test checkpoint: `f6ec223dbab7db46695237fa82c511204badb809`.
- A normal merge brings all three existing main commits into the feature,
  preserving Android Play consumption-only, report and release safeguards.
  No Android/Voice source is authored by this task.
- Two actual conflicts: `localization/README.md` and
  `tests/test_i18n_all_catalogs.py`. Main has 62 generated artifacts; PWA adds
  one admin catalog. Keep both and require 63; no weakened count assertion.
- AST comparison of existing top-level `app/main.py` functions against main:
  only `_review_admin_payment` changed; none removed. Its shared locked unit
  of work and existing commit/post-commit wrapper are covered by financial
  regressions. New functions are the dedicated PWA delivery dispatcher and
  extracted effects emitter. Telegram authentication helpers/route functions
  remain unchanged, as does the existing `/admin.html` file.

## Integration checks

- Full ASGI flag-OFF regression enumerates every mounted PWA route and proves
  private 404/no cookies before any session factory use. PWA cookie/forged
  headers never authorize it. With the rollout either on or off, PWA cookies
  cannot authorize Telegram overview/search/payment/delete/broadcast endpoints.
- Existing genuine signature, one-use proof, payload, financial rollback,
  entitlements, audit/outbox, concurrency and legacy regressions remain required.
- Workflow now covers feature/main pushes and main-targeted PRs. PR checkout
  tests GitHub's actual merge candidate; no PR code receives production secrets.
  Both Admin PWA security/catalog/browser and PostgreSQL migration jobs must pass
  for the final tested SHA. Existing backend/i18n/Android/Desktop PR checks remain
  in force; they are not suppressed by this workflow.
- PostgreSQL migration scope remains 0110–0117 from a synthetic stamped 0109
  baseline, with audit/outbox parity, rollback/re-upgrade and nonempty-audit
  retention. Empty full-history migration failure at legacy 0011 predates PWA
  and is not repaired or claimed as passing.

PR: https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/200.
Integration commit `9eace423b441818c9071f9ff4623d40058de3217` has the same tree
as GitHub's test merge `738d8195d40d5d435f47be312daebe3de0e61421`.
PR Admin PWA run 40065222994 passed both jobs; the earlier wider P0/Android
checks found main's stale 42-file Android count. Preserve all three new Play
bundles and require 45 native resources; total generated artifacts stay 63.
Latest-head results are in PR Checks and the final PR description/task report.
Do not treat an earlier head's checks as proof for later runtime changes.

## Merge versus activation

This change is prepared for **integration with `ADMIN_PWA_ENABLED=false`**,
not an authorized production launch. Blank origin and disabled flag remain
repository defaults. Dangerous delete/broadcast/grant-access commands remain
unwired; normal Telegram admin and native/manual checkout keep their existing
contracts. Public PWA assets contain no secret or embedded customer data.

No live environment, DNS/TLS, provider account, production database or device
state was inspected/changed. Repository defaults do not prove the live flag.
Existing versioned startup runs Alembic upgrade before starting the app, even
with the feature off; any later deployment must account for the new tables.
A nonempty financial audit refuses downgrade and must never be discarded to
roll back. Disable the rollout and retain audit/outbox data instead.

Before activation, use separately authorized staging/device/provider QA:
actual Google/Bot onboarding/recovery, secure proxy/origin/cookies, installed
iPhone PWA/Face ID, Mac Touch ID and Windows Hello. Virtual Chromium authenticators
are signature/interaction evidence, not physical biometric/device acceptance.
Pending outbox recovery/monitoring and explicit uncertain-send reconciliation,
Telegram attribution, durable Android feedback history and separately audited
management/export adapters remain follow-up scope. Never auto-resend an
attempting/uncertain financial delivery or expose unaudited management writes.


## Initializer compatibility repair

The isolated empty-QA initializer now pins reviewed head 0117 and lets the real
0109–0117 migrations create their eleven owned tables; it does not precreate
PWA tables and skip DDL. All original target/approval/nonempty guards remain.
A disposable PG regression applies actual 0103–0117 upgrades using the exact
initial table selection, checks column parity/zero rows, and leaves production
and the guarded Railway CLI untouched. The current native Close-action test
also matches main's existing neutral Play behavior without permitting trial
or checkout actions. Current CI/check evidence is available on PR #200.
