# Critical mechanics review — 2026-10-21

Scope: review substantive account, billing and course changes across earlier
sessions on `codex/p3-main-integration-20261020`, beyond the latest copy migration.
No main promotion, deployment, real credentials or production database access.

## Confirmed fixes

### Receipt preview idempotence (`abf63dff`)

- Cause: receipt A could claim again after approving a different receipt B
  restored the reusable ticket, creating another $0.50 preview budget.
- Fix: under the existing User lock, the current receipt pointer and any prior
  preview budget prevent another claim for that immutable receipt. Ambiguous
  historical duplicate budgets deny preview AI instead of throwing
  `MultipleResultsFound` or choosing another cap.
- Risk: historical ambiguous preview rows now deny preview AI. Financial facts,
  ticket replenishment for distinct approved purchases, prices, paid terms,
  independent paid/trial priority and existing caps are preserved. No migration.
- Prevention: four regressions cover A/B approval, pointer changes, ambiguous
  text/image/Voice budgets and independent paid/trial access. Broader billing
  suite: **134 passed, 10 isolated-PostgreSQL-only skipped**. GitHub P0
  [39607574270](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39607574270)
  and Backend
  [39607574265](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39607574265)
  succeeded at this commit.

### Private lesson entitlement and foundation

- Cause: unlimited Free/Trial admin settings create no reservation, but private
  content required one unless the user was specifically Pro/temporary-access.
  Start also consumed a slot before the content route rejected required foundation.
- Fix: honor the actual shared `allowed`/`unlimited` decision and check required
  beginner foundation before consumption. Direct Mini App complete/unlock also
  enforce foundation before progress/XP writes. Reads remain non-consuming/no-store.
- Risk: preserves configured Free/Trial limits, including zero and null, sequence,
  track access and existing Pro access. Original lesson sources remain unchanged.
- Prevention: real SQLite/shared-service ASGI cases cover Free/Trial 2/10 limits,
  unlimited zero-reservation reads, retries, blocked/zero limits and foundation.
  Four new tests were independently run against pre-fix source and failed there.
  Direct signed foundation bypasses were reproduced before the fix; denial and
  completed-foundation success are covered for both writes. Non-object JSON now
  returns 400 instead of raising an unhandled exception, without side effects.

### Course context on completion, skip and start

- Cause: Desktop did not propagate the already supported Android/shared-service
  `expected_level`. Mini App writes ignored their supplied course. An old lesson
  could complete or unlock the newly selected band's lesson; mismatched progress
  could be retagged with the old completed count.
- Fix: propagate the loaded Desktop lesson snapshot through JS/Rust/API. Mini App
  start/complete/unlock lock User first and reject stale supplied levels; complete
  and unlock also reject a mismatched saved progress band. Return 409 before
  progress, quota, XP, analytics or replay effects.
- Risk: optional course fields preserve legacy callers. A legacy request without
  its source course cannot convey cross-device staleness when saved progress
  already matches the new band; updated clients always send the snapshot.
  No new course override, passing score threshold or subscription policy.
- Prevention: signed SQLite ASGI state snapshots, Desktop replay-after-switch,
  JS invoke contract and macOS/Windows browser fixtures. Local Rust format and
  offline check pass; GitHub paired native tests/clippy subsequently passed on
  macOS and Windows (see final evidence below).

## Other reviewed areas and test maintenance

- Canonical identity, OIDC verification, linking, session rotation/revocation and
  AI/Voice owner isolation: **212 distinct tests passed, 26 PostgreSQL-only skipped**.
  No new confirmed defect in those reviewed paths. Mocked providers do not prove
  real Google/Apple/Telegram acceptance. The earlier PostgreSQL skips were
  subsequently covered by the dedicated run below.
- **22 critical browser tests passed** using actual local HTML/assets and synthetic
  APIs: foundation, lesson completion/retry, checkpoint recovery, recognition,
  exam/challenge server results, UZ/RU/TJ paywalls, checkout, pending receipts,
  discounts and paid renewal. Nine stale fixture/selector/copy assumptions were
  repaired without changing production UI. The challenge test now verifies the
  exact wrong-answer submit and Chinese/pinyin server correction.
- Eleven obsolete static tests were updated for signed private lesson URLs,
  canonical catalogs, current profile layout and actual browser content hashes.
  These were test failures on unchanged pre-review source, not newly introduced
  production defects. All 29 static tests pass. Rank-up source assertions now
  reflect reuse of the same verified leaderboard snapshot.
- Current CI adds the relevant course state, browser and Desktop snapshot tests.
  Final source CI evidence is recorded in the active handoff after push.
- Final local P0: **460 tests on each Python 3.11/3.14**, plus all **32 read-only
  checks per version**; 53 artifacts / 0 stale, 812 frozen sources / 746 lessons /
  0 blockers. The source audit now explicitly enforces the verified User lock
  before reservation progress/quota reads, with three negative regressions.

## Isolated PostgreSQL follow-up

At exact source `90fa883a`, **57 tests + 64 subtests passed, 0 skipped** on a
fresh PostgreSQL 15.17 cluster. It covered native account and OAuth races,
Telegram attachment/link races, canonical payment locks, HSK3 grant races,
receipt locking, referral rewards, migration 0108, statistics and purge ownership.
The server identity and new data directory were verified; the application DB
remained a loopback sentinel. The created cluster was stopped afterwards.
CI has a matching ephemeral PostgreSQL job with a no-skips assertion; no real
payment/provider credentials or existing database were used.

The first expanded Linux browser run at `90fa883a` passed 21/22 flows; the D1
recovery background `/api/v3/course-tracks` request had no fixture and a faster
DNS failure exposed it. A deterministic Chromium DNS rule reproduced the exact
failed URL. The specific local fixture fixes it; five repeated fast-DNS D1 cases
and all 22 selected flows passed. Console checks remain enabled. This is a test
harness correction; no runtime UI change.

## Final GitHub verification

Source `0a7d4607` contains the completed fixture fix and PostgreSQL CI job:

| Check | Run | Result |
| --- | --- | --- |
| P0 Python 3.11/3.14 | [39614374914](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39614374914) | SUCCESS; 460 tests each and read-only checks |
| Backend, browsers and PostgreSQL | [39614374478](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39614374478) | SUCCESS; all three jobs, 22 critical flows, PostgreSQL 57 passed / 0 skipped |
| Desktop macOS/Windows native and UI | [39611201161](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39611201161) | SUCCESS at runtime source `90fa883a` |

The complete `app/`, `android/` and `desktop/` trees are identical between
`90fa883a` and `0a7d4607`; the latter changes CI, tests and review evidence only.
The first failed Linux D1 run is superseded by the successful final browser job.
No main or production promotion was performed.

## Acceptance limits

No production or real-account certification. Real payment/provider flows,
production migration/restore rehearsal, account switching with installed clients,
offline/refresh and user's real Telegram bot acceptance still require their
intended isolated environment. Earlier localization completion does not mean
the whole branch changed text only: earlier account/private-content integrations
are substantive and were reviewed here. Do not rerun completed copy migrations.
