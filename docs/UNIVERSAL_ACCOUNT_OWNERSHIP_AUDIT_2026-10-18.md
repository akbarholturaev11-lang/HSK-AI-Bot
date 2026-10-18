# Universal account ownership audit

The audit found residual Telegram ownership assumptions after universal
registration was implemented. They are fixed on `codex/universal-sign-in`.
The ownership fix is `693ff6ec`; the practice bootstrap fix is `a6893778`.
This is not a production deployment or permission
to merge to `main`. All owner acceptance gates remain in force.

## Findings and fixes

| Area | Defect and resulting behavior |
| --- | --- |
| Payment status | Mini App status could reject an owned pre-attachment payment, crash on NULL metadata or match foreign stale Telegram metadata. PaymentRepository now resolves the verified actor's canonical ownership. |
| Personal discounts | A native target could not be represented safely. `target_user_id` owns the offer; canonical targets override Telegram metadata in eligibility, delivery and sales-experiment exclusions. Deleting the target deletes its personal offer instead of making it global. |
| Affiliate credits | Raw payment Telegram metadata could credit a foreign affiliate or miss a linked owner's historical native payment. The canonical payment owner determines current real Telegram transport; only unowned legacy payments use the old adapter. |
| Admin management | Native accounts were absent from some actions/details. Explicit `user_id` now selects detail, paid manual grant, block, delete, personal offer and trial revoke. A strict legacy `telegram_id` adapter remains. Conflicting dual IDs, malformed IDs and real admin deletion/blocking are rejected. |
| Statistics | Telegram-only distinct/grouping omitted native users, duplicated post-attachment aliases and could collide numeric ID spaces. Read-only canonical account keys now resolve legacy aliases and namespace unresolved histories. Metric event definitions stay unchanged. |
| Inventory and diagnostics | NULL casts and raw Telegram queries hid native devices/history or mixed foreign metadata. Canonical inventory and block-diagnostic predicates preserve the actual owner. Native accounts have no Telegram block episode. |
| Account purge | Some broad Telegram predicates could erase foreign canonical histories/devices or rewrite another payment's ledger association. Canonical precedence now applies throughout; only unowned legacy rows use the real-Telegram fallback. Approved payment retention and amounts are unchanged. |
| Scheduled bot delivery | Provider-only accounts could cause NULL casts or invalid bot-feedback rows and stop a batch. Bot reminders, reachability checks, broadcasts, feedback and bot advertisements require positive real Telegram transport. Native users remain in canonical league rankings and in-app advertisements. |
| Pilot/shadow events | Pilot NOT NULL metadata rejected native diagnostics; shadow sampling skipped them. Migration `0108` permits native records and adds canonical daily shadow dedupe without changing access verdicts or rollout settings. |

## Preserved business contracts

- Existing approved/unexpired paid-access predicates and 10/30/90-day terms.
- Existing prices, payment methods, receipt review, rejection, paid AI budgets,
  renewal and separate one-time HSK 3.0 grants.
- One reusable receipt-preview opportunity, its unpaid status and capped
  $0.50 pending-receipt budget. Manual admin grants create no revenue/budget
  or new preview opportunity.
- Existing referral eligibility, bonus and discount rules: two successful
  Assistant questions qualify once for five bonus questions; five active
  referrals retain the existing three-day/$2 benefit; three verified device
  invitations retain the existing 20% discount. No signup/link reattribution.
- Existing affiliate commission modes/rates, signup-bonus unlock, review-time
  rules, duplicate protection and HSK 3.0 exclusion.
- Advertisement caps, targeting filters, marketing cohorts and Mini App
  experiment hashing. The experiment does not silently enroll native users.
- Financial retention, atomic purge/rollback and isolation of unrelated users.

## Why real Telegram IDs still exist

Canonical ownership does not remove Telegram transport or provider identity.
Bot chats, Telegram auth/admin authorization, Mini App presence, bot-only
feedback, the separate affiliate partner program and existing Telegram
experiment buckets still require actual Telegram IDs. No provider receives
a fabricated Telegram ID; a missing ID never selects every NULL row.

## Schema and rollback

`0108_native_audit_ownership` follows `0107_canonical_referral_owners`.
It backfills only missing owners from positive real Telegram identities and
never overwrites a canonical owner. Pilot/shadow Telegram metadata is nullable;
shadow ownership uses an indexed SET NULL FK and canonical daily uniqueness.
Personal offers use an indexed `target_user_id` FK with CASCADE.

Duplicate canonical shadow samples or an unexpected existing owner FK abort
before any DDL/backfill; reconcile them explicitly rather than deleting data.
Downgrade validates all three tables before mutation and refuses native or
conflicting ownership that the old schema cannot represent. Global offers
remain global. Existing user IDs and business columns are preserved.

## Verification and remaining gates

[Final source CI](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39104275053)
passed on `a6893778`: all 16 backend groups, **1,138 test executions**, zero
failures/skips, including PostgreSQL 18 integration/concurrency checks. The
admin/practice browser job also passed **18 tests**. Local backend and browser regressions
passed independently with disposable PostgreSQL 15 schemas. Fixture/CI tests
alone do not prove a real-schema migration or a provider callback.

The new migration suite includes 20 SQLite/PostgreSQL cases. New purge cases
exercise 13 history families, device/session/push isolation, referrer and offer
ownership, and approved financial retention. Old purge code fails 18 assertions
in these five regressions; current code passes. New payment, affiliate,
statistics, transport and sales regressions also reproduced their old defects
before fixes. Compilation, one Alembic head and diff checks pass.

The six new admin browser tests cover 390px and 1440px layouts, canonical
grants/block/unblock/delete, personal discounts, real Telegram messages,
disabled native Telegram messaging and console errors. Adjacent existing
admin and checkout/browser cases also pass. The backend workflow now retains
the six new cases and two existing admin smoke cases as a separate browser job.

For repeatable local backend verification, use the workflow's separate
unittest processes with a syntactically valid dummy bot token and isolated
PostgreSQL. Shared import-time application settings make a combined pytest
collection an unreliable substitute for that process isolation.

Five broader Mini App cases also failed against an archived, byte-identical
pre-audit snapshot (`d3967c8a`). Four involve missing offline-audio fixture
resources, retired `.pdd-card` markup, an old `items`/`targets` mistake fixture
or an unmocked gamification request. They must not be reported as passing.
Recognition exposed an actual preexisting bootstrap defect: inline startup
used `HSKStudyPreparing` before its deferred script executed. The same pattern
was present in pronunciation and memorization. Their preparer render now waits
for scripts while the server gate request still starts immediately; completed,
denied or failed gate responses cannot be overwritten by a late loading card.
No layout, scoring, question selection or server limit policy is changed.
Ten new real-browser cases and six existing practice regressions pass after
that fix, including recognition's ten-answer result submission. The new
matrix covers all three successful starts, permission denial and server error
followed by retry while the real helper script is deliberately delayed. It is
also retained in the browser CI job.

[The real-schema rehearsal](UNIVERSAL_NATIVE_ACCOUNTS_STAGING_AUDIT_2026-10-18.json)
also passed the full `0102 → 0108` chain on isolated Railway PostgreSQL 18:
61 data tables, 190,155 legacy rows and 2,118 users. Both pre/post-migration
backups were independently restored. Three strict comparisons preserved
schema, rows, account keys, sequences, billing, progress, XP/rating and referral
facts. All 14,732 owner-field backfills were verified, including 363 shadow
samples and 36 personal offers; pilot owners were already canonical. No
production connection, existing database replacement or app deployment was
needed. Private backups remain outside Git.

Real Google/Apple callbacks, upstream Voice and installed Android/macOS/Windows
cross-client walkthroughs remain owner acceptance work. Play stays
consumption-only. Neither local tests nor CI authorize production migration,
public registration or a `main` push. See the
[universal account guide](UNIVERSAL_NATIVE_ACCOUNTS.md) and
[manual QA checklist](UNIVERSAL_NATIVE_ACCOUNT_QA.md).
