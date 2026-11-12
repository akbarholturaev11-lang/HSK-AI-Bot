# Tasks

Only checklist for R4. Context, decisions and the next step live in `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md` ("Next stage", R4). Stacked on R2, R1 and PR #285; nothing merges to `main` without the owner's permission.

## 1. Reader

- [x] 1.1 `platform_use` and `platform_return_retention`: first verified use per account in one grouped subquery, both windows in one statement, with `attributed_since.return_retention`.
- [x] 1.2 Registry: `return_retention` covered on Android, Telegram and the PWA with the chain test; the checker passes.
- [x] 1.3 Admin UI: one UZ/RU/TJ cohort line under each mobile filter; catalog regenerated.

## 2. Proof

- [x] 2.1 Stored-row tests:
  - the first PWA open starts the PWA cohort;
  - a return on another platform does not count;
  - an immature cohort is excluded;
  - a client-writable start and a pre-boundary tagged row never anchor;
  - Android opens count for all history.
- [x] 2.2 Route → PostgreSQL → `/api/admin/v1/analytics` chain test on all three mobile routes. It fails on the old reader.
- [x] 2.3 Performance: a 1M-row PostgreSQL fixture (20k accounts). Each platform reads no slower than Overall `return_retention` on the same data; numbers are recorded in the context file. The first-use subquery splits `owner` into its owned and legacy branches; with the OR join it took 1.1–1.8 s even for a week.
- [ ] 2.4 Full unit suite, PostgreSQL modules and Admin PWA browser suites; results recorded in the context file.
- [ ] 2.5 Owner acceptance on real clients after deploy.
