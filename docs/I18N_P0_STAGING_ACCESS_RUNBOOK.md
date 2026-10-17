# P0 staging-only lesson-delivery security QA runbook

**State: anonymous status-only staging checks EXECUTED; authenticated Free/Trial/Pro QA NOT YET EXECUTED.**
Owner approval is required before changing live lesson routes, auth, quotas,
or the Mini App JSON loader. This runbook is for trained QA with isolated,
disposable staging accounts only.

## What the automated probe can establish

`scripts/i18n_staging_anon_route_probe.py` performs a
small, **anonymous GET-status-only** check of **17 URL paths**:
7 top-level course maps, 7 `lesson_01.json` paths, two anonymous
native Android/Desktop lesson APIs, and one
private exam JSON path. It intentionally does **not** fetch private
entitlement state, use authentication credentials, consume lessons, or
read response bodies. The report records only path, HTTP status and
coarse error class. A 200/206 on anonymous lesson JSON means content was
served, **not proof of a subscription/payment bypass**. Other proxies,
tokens, Android/desktop builds and frontend behavior are out of scope.

To create an offline plan (safe at any time, **0 network calls**):

```bash
python scripts/i18n_staging_anon_route_probe.py \
  --output /tmp/hsk-p0-staging-anon-plan.json
```

After a real isolated QA HTTPS domain is provisioned and verified,
a human QA operator may explicitly opt in:

```bash
python scripts/i18n_staging_anon_route_probe.py \
  --execute \
  --base-url https://qa.example.test \
  --confirmed-host qa.example.test \
  --output /tmp/hsk-p0-staging-anon-status.json
```

Replace `qa.example.test` with the **actual authorized
staging** hostname. Never use the example hostname as if it exists;
never use the deployed production Railway domain. The script rejects
hosts without a QA/staging marker, plaintext HTTP, host mismatches,
embedded secrets, production names and redirects. CI runs the offline
plan only, with **no live requests**.

Review `exam_404_verified`. If false, block
the rollout and inspect exam-route handling and upstream routing.
If anonymous lesson paths return 200/206, treat as **source exposure
confirmed at that staging origin** requiring entitlement review.
Other statuses may reflect staging routing, middleware or downtime;
a 401/403/404 alone is not proof every paid content path is secure.

## Follow-up authenticated QA: manual, not automated by this script

Use disposable accounts, a staging test database and entitlement
fixtures. Run **before and after** each scenario with server-side
quota/progress snapshots stored in a restricted staging QA area.
Only save counters/statuses/opaque test IDs in shared reports. Never
include Telegram initData, Bearer tokens, receipts, payment details,
Chinese lesson bodies, graded answer keys, or other private content.

| Scenario | Test action | Required invariant |
| --- | --- | --- |
| Anonymous | Request the static lesson URL directly and the exam path | Report precise status only; exam file is 404; any anonymously served lesson requires review |
| Free, no quota use yet | Open course map; wait for nearby-lesson prefetch | **0** additional lesson consumptions |
| Free, no quota use yet | Open paywall and sales preview (HSK1 lesson 3) | **0** additional lesson consumptions |
| Free, no quota use yet | Open preview sheet and warm audio before Continue | **0** additional lesson consumptions |
| Free, eligible | Explicitly start a current lesson | A single entitlement/reservation action; preserve grading and progress IDs |
| Free, quota exhausted | Attempt locked/next lesson | Denied by server; no silent cached-data override |
| Trial / Pro | Explicitly open an eligible lesson, then next unavailable lesson | Only entitled/unlocked content; do not assume Pro overrides progression |
| Pending / rejected receipt | Retry lesson after admin decision | Existing receipt/entitlement policy; no accidental temporary bypass |
| Starter 0 | Begin foundation before ordinary lesson | Foundation-specific policy; no unintended normal lesson spend |
| Skip-ahead | Open quiz, retry/complete | Separately authorized quiz material; no public answer-key exposure |
| Blocked / expired login | Attempt API requests and reopening cached lesson | Explicit denial in online state; no server response-to-cache bypass |
| Android offline | Open previously downloaded authorized lesson, then disconnect | Only already cached authorized lesson per offline policy; do not test private content on shared device |
| Same WebView account A→B | A loads course lesson/resume; log out and log in as B; revisit level | B never sees A's cached lesson/resume/progress; reject in-flight A response |
| Cache revision | Change lesson source revision or switch course track | Correct version and locale, no stale lesson/language contamination |
| Android direct/Play and Desktop | Repeat minimal lesson/progression and logout checks on supported builds | Preserve Bearer authorization and existing cache behavior; no regressions |

## Decision and rollback gate

Before implementing any secure endpoint or removing anonymous static
lesson content, obtain: named staging server owner; approved disposable
account list; client versions for Telegram iOS/Android, Android direct,
Android Play and Desktop; tested Free/Trial/Pro/blocked states;
no-consume background evidence; account-switch cache isolation;
content revision/integrity strategy; phased rollout and explicit
fallback/deprecation period for old clients. A new authorized endpoint
must **not** reuse a quota-consuming start action for speculative
prefetch, preview or the Starter/skip workflow.

Do **not** merge a runtime change into `main` on the
basis of passing source-only tests or this anonymous probe. P0 remains
open pending these independent human checks. No accounts, deployed
routes or billing state were touched while preparing this runbook.

## Railway staging backend — provisioned and health verified (2026-10-17)

**Supersedes the earlier database-only staging discovery.** Railway project
`patient-friendship`, environment `staging`, now runs two independent
services: staging PostgreSQL `Postgres-Iy93` and the new
`hsk-ai-p0-qa` API service. The staging API is sourced from PR #179's
branch, pinned to commit `c73ee00891e7be6fa8eca59d5b54e29c24c36fe4`
with a separate, staging-only startup module `app/staging_qa.py`.

**QA HTTPS origin:** `https://hsk-ai-p0-qa-staging.up.railway.app`
(Railway-managed domain). `PUBLIC_SITE_URL` and
`MINI_APP_BASE_URL` now point to this staging origin. A prior first
attempt failed because both were blank; this was corrected strictly in
staging service variables. The latest deployment
`cf4e66c5-8134-40e5-9f78-68b07b26b244` reports **SUCCESS**.
Railway's service startup log confirms `Application startup complete`
and internal `GET /health` responded **200 OK**; staging backend and
database both report **Online**.

**Safety:** production `app.main:app` entrypoint was not changed.
Staging's `app.staging_qa:app` deliberately skips Telegram polling,
notification/reminder/campaign schedulers and background seeding,
injects a **per-start randomized fake Telegram token** (does not accept
a real BOT_TOKEN), refuses inherited paid AI credentials, and validates
that the asyncpg DATABASE_URL hostname matches the configured staging
PostgreSQL host. Admin/push/OAuth are disabled on staging. The two
environments' databases/services are separately configured; the live
staging database was initialized but its user-data contents were not
independently inspected for existing fixtures. Staging compute may incur
Railway usage charges; sleep mode is enabled.

**Live anonymous check now confirmed on staging:** a dedicated,
scoped [GitHub Actions run 39017842475](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39017842475)
successfully reached the QA HTTPS origin, woke it using `GET /health`
(**200 OK**), and sent exactly **17 anonymous GET Range-status
requests** without reading or recording response bodies.

- Seven navigation maps returned **HTTP 206**.
- Seven static `/course_v3_data/{track}/lesson_01.json` returned
  **HTTP 206**, confirming anonymous partial delivery from all seven
  sampled legacy lesson paths *on staging*.
- Native Android and Desktop `/api/v3/{platform}/course/lesson/1`
  each returned **HTTP 401 Unauthorized**, confirming this particular
  no-Bearer request is denied.
- The private exam file probe returned **HTTP 404**.
- **Seven source-exposure review findings** remain for legacy lesson
  files; the native API denial is not a verified Pro access matrix.

The artifact `hsk-p0-staging-anon-status` was downloaded and verified
and the status-only evidence has been committed to
`localization/review/staging_anonymous_http_results_20261017.json`.
The first limited pass,
[run 39017607269](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39017607269),
tested 15 paths; the second extended pass is the current evidence.
No result above was measured on production.

**Still not executed:** Free, Trial, Pro, pending receipt, blocked or
expired authenticated sessions; paid/advanced lesson reachability;
production proxy/CDN behavior; quota-consuming preview behavior;
account A-to-B cache isolation or real-device tests. The randomized
dummy Telegram token is deliberately not a functioning bot, so these
require an isolated test bot or approved disposable signing fixture
and QA permissions. An anonymous 206 means the content was served,
not that a Pro payment bypass has been tested or established.

For an authorized operator who can resolve staging DNS, run:

```bash
python scripts/i18n_staging_anon_route_probe.py --execute \
  --base-url https://hsk-ai-p0-qa-staging.up.railway.app \
  --confirmed-host hsk-ai-p0-qa-staging.up.railway.app \
  --output /tmp/hsk-p0-staging-anon-status.json
```

This **only** reports HTTP statuses. Do not infer a billing bypass
without the manual account/entitlement matrix, and do not run against
production. Complete the no-consume prefetch and same-WebView A->B
cache checks on disposable staging accounts before any authorization
runtime migration or P0 closure.
