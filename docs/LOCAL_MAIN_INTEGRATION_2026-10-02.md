# Local AI promotion to main — 2026-10-02

## Scope and source of truth

Owner requested all accumulated updates on main, including other contributors'
work, excluded the iOS app branch, and held Android release preparation/publication.
The owner clarified that the completed work is already collected on local AI.

- Source: `codex/local-ai` at `5951ca81a796f1a5486bb6d2056071cba546023a`.
- Base: previously verified `origin/main` at
  `db7d96894954ad89c6aef8213149f9a0fc54bc42`.
- iOS branch remains excluded:
  `origin/codex/ios-app` at `f2fb11c89c32ff58e4dd60344ca2971c34cc5973`.
- Preserve the newer complete local HSK 3.0/payment/checkout implementations.
  Older cloud, textbook-source and country-first checkout commits overlap these
  features despite not being ancestors. Their prototype implementations were
  checked in a reversible review copy, then removed from this promotion.
- No Android release preparation, signing, publication, release tag, workflow
  dispatch or live migration. Committed Android version stays `1.7.3` / `34`.
  Android release workflow is manual-only; main push does not publish an APK.

## Integration adjustments

1. Preserve the existing main Mini App profile/settings/renewal changes and tests.
2. `0097_merge_course_and_currency` joins the course/ad-targeting and currency
   migration heads. It adds no schema operations itself; both parent migrations
   remain required. Verify the single head before deploying migrations.
3. Android permanent HSK 3.0 checkout reloads the same product overview after a
   currency change. The preference response contains subscription prices and
   cannot replace permanent-product prices. On refresh failure retain the
   previous product and let the learner retry. Three ViewModel regressions cover
   permanent purchase, refresh failure and ordinary subscription.
4. Legacy onboarding validates legacy levels without querying the HSK 3.0 flag;
   new HSK 3.0 levels still require the server flag. Existing legacy start tests
   and explicit flag/dependency tests cover this boundary.
5. Source verification distinguishes distinct senses of the same Chinese word
   using the existing translations. Textbook vocabulary/grammar was not edited.
6. Update obsolete test expectations for savepoint-isolated analytics, referral
   deep links, private identifiers and the permanent checkout starting step.
   A real SQLite regression verifies analytics failure preserves caller writes.

## Validation on the final review copy

| Check | Result |
|---|---|
| Full backend suite excluding browser E2E | 1,862 passed; 78,804 subtests; 7 warnings |
| Android Direct/Play unit suites | 386 / 354 passed |
| Android Direct/Play debug builds | Passed |
| Android interfaces, named args, flavor/string/palette parity | Passed |
| Android dictionary/stroke asset consistency | Passed |
| Android notification primer on read-only Pixel 8 emulator | 6 passed |
| Desktop Node contracts / offline Rust units | 28 / 24 passed |
| N1/N2 source, N3 normalized/enrichment, runtime integration | Passed |
| Changed Python syntax / Alembic head | Passed; one head: `0097_merge_course_and_currency` |
| Mini App full browser suite | 60 passed; 18 pre-existing failures |
| Baseline comparison for all 18 browser failures | All 18 reproduced on untouched prior `origin/main` |
| Knowledge graph AST refresh | Completed |

The Mini App suite is not entirely green. Its existing failures concern obsolete
checkpoint/repair fixtures, sales preview expectations, mistakes payloads, an
unmocked challenge request, admin wording, old desktop promo/profile selectors,
and earlier installer-page expectations. These failures were not hidden or
marked skipped; the same failing tests were run against the prior main snapshot.
See `ANDROID_MINIAPP_PARITY_AUDIT_2026-10-02.md` for still-open product parity issues.

## Recovery and operational boundaries

A verified bundle of all refs/history was saved before integration. Branch
history and earlier review patches remain recoverable; no force push/reset or
branch deletion was used. The primary checkout's unrelated PDF deletions are
excluded. Existing HSK 3.0 rollout flags remain server-owned; this integration
neither enables flags nor approves payments.

This document records the tested candidate. A main push is complete only after
fetching fresh remote state, pushing normally, and verifying the intended commit
against the remote main ref. Do not infer publication from this document alone.
