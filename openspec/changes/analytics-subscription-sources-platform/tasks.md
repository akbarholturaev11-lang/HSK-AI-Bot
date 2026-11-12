# Tasks

Only checklist for R3. Context, decisions and the next step live in `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md` ("Next stage", R3). Stacked on R4, R2, R1 and PR #285. Nothing merges to `main` without the owner's permission; the migration merges only with the owner's explicit approval at its PR.

## 1. Schema and writers

- [x] 1.1 Alembic `0155_subscription_entry_client`: nullable `client` and `(client, created_at)` index; upgrade, downgrade and upgrade again tested on local PostgreSQL from the old and the new schema; `tests/test_subscription_entry_client_0155_migration.py` in CI; the QA bootstrap's reviewed head moves to `0155`.
- [x] 1.2 `record_entry(client)` keeps only `telegram`, `iphone_pwa`, `android`; the five writers pass their route's client; Desktop stays NULL.

## 2. Reader and UI

- [x] 2.1 `platform_sources_metrics`: same-client entries and payments from the platform boundary, nearest same-client entry, `attributed_since`; Overall unchanged.
- [x] 2.2 Registry: `entries` covered and `attribution` partial on the three mobile platforms, `attributed_since` metadata, `subscription_entries` flow partial; the checker passes.
- [x] 2.3 Admin UI: null values show the state, start dates, a UZ/RU/TJ same-platform note; the traffic panel is Overall-only; catalog regenerated.

## 3. Proof

- [x] 3.1 Writer tests: each route stores its client; unknown values are NULL; a caller field cannot set it; Desktop stays NULL.
- [x] 3.2 Stored-row tests: forged prefix stays Telegram, nearer other-client or untagged entry is skipped, pre-boundary payments are left out, `unknown`, no data before the first entry, Desktop unavailable.
- [x] 3.3 Route → PostgreSQL → `/api/admin/v1/analytics` chain test on the Telegram, PWA and Android routes; it fails on the old code.
- [x] 3.4 Golden test: only the three platform Sources cells change; Overall is byte-identical.
- [ ] 3.5 Full unit suite, PostgreSQL modules and Admin PWA browser suites on the final head; results recorded in the context file.
- [ ] 3.6 Owner approval of the migration at the PR, then owner acceptance on real clients after deploy.
