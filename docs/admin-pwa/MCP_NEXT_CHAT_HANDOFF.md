# HSK AI Admin PWA — current MCP continuation checkpoint

Updated 2026-10-26. Read this first; older checkpoints are historical. Verify remote HEAD and CI before editing.

## Owner's latest V10 Home + Statistics request — 2026-10-26

The owner supplied `/Users/kaijimima1234/Downloads/hsk-ai-admin-ux-demo-v10 2.html`
again and explicitly requested the control center **and** Statistics to match
the demo using real complete analytics, with no fake copy or numbers. This is
current steering of the same Admin PWA task; preserve completed campaign work.
The file remains 182,765 bytes and matches the existing reference. Original
Home and all seven Statistics views were read and rendered at desktop/mobile:
`/tmp/hsk-admin-demo-reference-20261026`. No demo fixture is copied into runtime.

Read the new CLI-generated planning delta
`openspec/changes/admin-pwa-v10-control-center-statistics/` before implementation.
Proposal/design/specs/tasks are written and CLI strict validation passes.
Home and all seven Statistics sections are implemented through the new first-party
`/analytics` reader. Advanced experiments are a separate lazy disclosure. Real
canonical counts, Shanghai-calendar learning activity, mature retention, Starter,
timing/features, platform inventory/foreground, attempt funnel, currency/AI/renewal,
source/traffic and report coverage are connected. See `READ_PROJECTIONS.md` for
exact definitions, bounds, unsupported attribution and basic-export scope.
No demo data is shipped; original one-editor WebAuthn and all OFF flags remain.

Verification so far: focused actual PostgreSQL/Redis suite 46 passed; broader
Admin PWA/catalog/QA suite 706 passed and 567 subtests, no skips. Actual ASGI/
virtual-WebAuthn core browser passed seven tabs at 390/1440 in UZ/RU/TJ, including
lazy experiments and console/overflow checks. Separate export/access/attachment/
worker and minimal-Inbox browser passes are recorded under
`/tmp/hsk-admin-pwa-v10-browser-20261026` and
`/tmp/hsk-admin-pwa-v10-ui-cleanup-20261026`. A final small Home task correction
reuses the blocked cohort instead of duplicating the header Inbox bell;
focused/core reruns passed: 27 projection tests (including actual PostgreSQL),
plus private R2 recovery. The header retains exactly one Inbox control. Catalogs: 63 artifacts, zero stale; adoption
79 classified/zero stale and frozen baseline guard passed.

Latest `main` `d9e70fa5` (PR #218) is now integrated locally, preserving course
limits/Trial, the seven-column user directory and explicit payment choice before
signing. Home's Limits shortcut opens that actual access/limits tab; it does not
load the unopened course funnel. Combined core browser passed all seven tabs and
actual signed review; relevant backend/PG/media/discount/import regressions:
118 passed, 57 subtests. Legacy payment/subscription/native notice suite:
96 passed, 114 subtests. Full settings and campaign browsers passed on the combined code, including
actual signed limits/Trial writes, dirty-state/reversion, payment decisions,
owned media, scheduling and one-round discount sends. The old stale promotion candidate is archived; a fresh managed candidate
from `d9e70fa5` is attached at `admin-pwa-v10-promotion-20261026/HSK AI bot`.
No new campaign/analytics promotion has been pushed yet.

Campaign code is pushed through `194ae4df`, which fixes legacy active-offer
dirty-state hydration and the CI branded media browser.
Core/revoke Linux browser, consent, inbox, settings and outbound passed in CI
40222121551; only actual H.264 preview failed in Linux Chromium. The correction
installs/uses branded Chrome for the campaign media test without weakening
videoWidth assertions (official Playwright media-codec guidance is recorded).
CI 40223121959 completed successfully for `194ae4df`, including PostgreSQL
and the actual branded-Chrome MP4 preview.
The latest local campaign browser including legacy offer Off/revert/sign passed
in `/tmp/hsk-admin-pwa-final-legacy-offer-20261026`; shell tests: eight passed.

The older promotion base was `1db08846`; **no new campaign/analytics promotion
has been pushed yet**. Remote main has advanced as described above. A clean
managed promotion worktree is attached at
`/Users/kaijimima1234/.codex/worktrees/admin-pwa-campaign-promotion-20261026/HSK AI bot`,
currently prepared at `c93443f8` (campaigns plus deterministic revoke test).
It must receive the final media CI/offer correction and any later approved
code before promotion, and current remote main must be refreshed. Root source
branch remains `feat/admin-pwa-minimal-inbox-passkey-20261025`. Graphify outputs
are unrelated dirty files: never stage them or reset the user's local main.
Owned local PostgreSQL 55137 and Redis 55138 were stopped after verification.

## Current campaign continuation — 2026-10-26

- Prior ready code is verified on `origin/main` at `8d473cd9`. The feature was
  synchronized with that promotion, then the latest main `0905dedc` was merged:
  compact Mac layout, user/profile filters and audited billing state, automatic
  Apple Web Push and selective OpenSpec planning are preserved. Their upstream
  defaults are not reverted by this work.
- The owner asked to continue remaining Admin PWA work. The CLI-generated
  [campaign delta](../../openspec/changes/admin-pwa-campaign-completion/proposal.md)
  records button/media/scheduling/discount-notice contracts; OpenSpec 1.15.0
  `validate --strict` passes. That is planning validation only. This handoff
  remains the canonical execution checkpoint.
- First increment implemented: strict optional promotion button in a signed ad
  draft, existing allowlisted actions and HTTPS/@username link, existing
  localized defaults or explicit three-language labels. Shared legacy behavior
  remains compatible. Rendered labels/targets participate in detail revision
  and send commitment; save rechecks contact under the shared key lock. The
  queue holds the reviewed markup, so later changes cannot replace it and no
  per-recipient contact query is added. Browser callback/provider JSON is denied.
- Tests: campaign button/marketing/outbound/shared Bot regressions with real
  isolated PostgreSQL **65 passed, 71 subtests**. Actual campaign browser passed
  UZ/RU/TJ at 390/1440, native cancellation preserving all inputs, real signed
  draft creation, safe preview and one exact callback delivery. Full settings
  browser passed after latest main integration. Evidence:
  `/tmp/hsk-admin-pwa-campaign-buttons*-20261026`. Mobile screenshot reviewed.
  JS/Python syntax, diff and catalog checks passed: 63 artifacts, zero stale.
- Owned media increment is implemented: migration 0131, same-admin/session
  ready assets (15 min), 20/hour quota, two upload slots and one encoder.
  Photo 2 MiB/8MP; video 25 MiB/4K/3min, forced local containers/protocols.
  Provider references stay server-owned; SQL contains no binary. Ad drafts
  and release feedback consume ready media atomically with proof/audit/queue.
  Caption plus release prompt is bounded to 1024 escaped UTF-16 units.
  Metadata retention preserves the one-hour quota window and referenced media.
- Media/campaign/button/outbound/shared/QA/import regressions: 93 passed and
  105 subtests; an added release test's incorrect callback expectation was
  corrected to the shared `relfb:` contract and its rerun passed. All 13 media
  tests including actual PostgreSQL migration/expiry-lock tests then passed.
  Actual campaign ASGI/virtual-WebAuthn browser passed local photo and real MP4
  decode, CSP, native cancellation, signed ad/release sends and UZ/RU/TJ mobile
  layout. Existing course media browser passed. Evidence:
  `/tmp/hsk-admin-pwa-release-media-20261026`,
  `/tmp/hsk-admin-pwa-course-media-secure-20261026`. Screenshot reviewed.
  Catalogs: 63 artifacts, zero stale; syntax/diff/OpenSpec checks passed.
- Newly fetched main `1db08846` original-editor/swipe UX is integrated; media
  readiness shares the dirty-state controller, without duplicate footer actions.
  Shell tests (8) and actual campaign browser passed on the merged code.
- Next: policy-preserving discount notices after scheduling below. No external MCP scope or manual deployment change.

## Session-bound campaign scheduling — 2026-10-26

- 0132 adds nullable indexed `not_before`. Ad/release send accepts explicit
  UTC time up to 30 minutes ahead, strictly before session expiry and the ad
  window end. Prepare and save recheck it; no session/private-body TTL extension.
  Early manual/API/background sends refuse before claim/provider IO.
- The existing minute worker selects at most two due ready jobs under a 3s
  statement deadline, excluding revoked/expired/non-admin sessions. Two tracked
  tasks reuse the existing shared drainer slots; disabled PWA causes zero SQL.
  Cross-worker job claims prevent duplicate attempts. Shutdown cancels tasks;
  an uncertain claim still requires explicit pending-only handling.
- Native cancel retains the selected local time. The same original editor
  sends once through passkey; successful queue save uses main's existing short
  checkmark/dismiss UX. Job detail shows due time and no early Run/Resume CTA.
  Fresh signed pending-only resume preserves original due time and expiry.
- Verification: scheduling tests **8 passed** including real PostgreSQL
  migration parity/refused nonempty downgrade/concurrent drainers. Related
  campaign/media/outbound/QA/import suite **56 passed, 46 subtests**. Actual
  ASGI/WebAuthn campaign browser passed staged media, UTC schedule, native
  cancellation, no early send and due poll delivery. Evidence:
  `/tmp/hsk-admin-pwa-schedule-final-20261026`; RU mobile screenshot reviewed.
  Main211 full settings browser also passed. Catalog/syntax/diff checks passed.
- Next code increment: policy-preserving discount notices, then integration
  verification and authorized main promotion. No manual deployment/flag change.

## Signed discount notices — 2026-10-26

- A separate `discount_send` signs active-offer revision, exact canonical
  audience, escaped three-language Telegram/phone copy and shared subscription
  entry markup. `notification_sent_at` reserves one round atomically with
  proof/audit/queue; legacy notifications stay off and checkout is unchanged.
- The audience is one bounded query (1001 sentinel), using canonical/legacy
  payment ownership, shared quota/repeat rules and global paid-user exclusion.
  Native-only/Bot-blocked accounts retain the existing Android-first notice
  route. Provider fanout is capped at eight recent native devices.
- The production adapter uses shared `discount_offer` delivery and existing
  Play silent acknowledgement, never a direct promotional Bot bypass. The
  dedicated session releases SQL before provider IO. Unknown native attempts
  have no automatic fallback deadline; known accepted ones keep the existing
  ten-minute acknowledgement policy. Stop/late receipt and uncertain no-retry
  behavior remain consistent. Notice sending changes no access/payment state.
- Focused new notice/shared Android suite **32 passed**, including actual
  PostgreSQL ownership/claim tests, one-query audience, bounded native fanout,
  SQL release, Play acknowledgement, no unknown fallback, Stop/late counters,
  stale-offer/audit rollback and live usage/expiry. Earlier combined
  notice/shared/campaign/outbound/import run: **70 passed, 31 subtests**.
  Actual ASGI/WebAuthn campaign browser passed UZ/RU/TJ no-channel errors,
  operation selector dirty-state, native cancellation, exact signed notice and
  one-round denial after send, plus media and scheduling regression. Evidence:
  `/tmp/hsk-admin-pwa-discount-final-20261026`; mobile screenshot reviewed.
- Full integration suite and authorized main promotion are next. Do not call
  planning checkboxes, feature push or provider acceptance product completion.

## Owner-approved main promotion — 2026-10-25

- The owner explicitly authorized pushing the ready Admin PWA code to `main`.
  This supersedes this workstream's earlier feature-only push restriction for
  the verified code promotion. Feature defaults remain OFF; no flag activation
  or manual deployment is included in that authorization.
- Source is `e7470a28ac85c167ebf54381d78d4c5a23430746`, including main PR #209.
  GitHub Actions [40199126920](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40199126920)
  completed successfully for code parent `71629eda`: both `admin-pwa` and
  `postgres-locks-and-migrations` passed, including all browser commands.
- Promotion uses an isolated clean worktree from `origin/main`; only the
  intended Admin PWA commits are copied. The prepared application, tests,
  catalogs and workflow are byte-identical to the verified source; only this
  promotion documentation is added. Unrelated local Graphify outputs stay out
  of the commit. Existing AI-branch work must be preserved when synchronizing.

## Latest owner-requested main sync — PR #209, 2026-10-25

- A fresh owner request found `origin/main` at
  `1cb799c6` (PR #209, biometric on each open). Merge this source into the
  existing feature branch; no feature-to-main promotion or deployment.
- **Current auth policy:** each launch/foreground resume revokes the previous
  cookie session and requires a new native passkey assertion. Keep automatic
  prompting and the manual browser-gesture fallback. Private DOM clears before
  login; active native biometric/transaction sheets do not cause prompt loops.
  Dashboard and unread reads run concurrently after verification. This
  supersedes the earlier seamless cookie-reuse checkpoints below.
- Queued jobs reopened after a fresh login use the existing signed pending-only
  resume. Preserve all feature commands, original-editor contextual actions,
  V10 statistics/navigation, daily snapshots and statistics-only external MCP.
- Merge validation: shell/import **9 passed, 11 subtests**, actual core,
  outbound and campaign ASGI/virtual-WebAuthn browser suites passed against
  the merged policy. Evidence `/tmp/hsk-admin-pwa-main209-*-20261025`.
  JavaScript syntax, diff and 63-artifact catalog checks passed (zero stale).
- Code increment `74e48740` and merge `71629eda30b5791d5b4c9b12e6b3c892aba793e1`
  are pushed to the owner feature branch; the exact remote SHA was verified.
  The broad checkpoint’s single skip was the local optional official MCP SDK.
  Installing the workflow’s existing pinned QA dependencies (`mcp==1.27.0`,
  `sse-starlette==3.0.3`) allowed that protocol harness to run: **1 passed** on
  the merged code. Application requirements are unchanged. GitHub Actions run
  `40199126920` started for the merge; no CI-success claim is made while pending.

## Current bounded campaigns increment — 2026-10-25

- `pwa_campaigns.py` and `/campaigns/read|prepare|save` add metadata-only keyset
  lists, explicit details, signed one-round text ad delivery, release-feedback
  creation/delivery and discount create/state. V10 Marketing links the actual
  forms; UZ/RU/TJ sources generate the bundled catalog. Contextual Send/Create/
  Save uses the original editor and one native passkey; no confirmation screen.
- Ads reserve one existing shared round without scheduling the legacy sender.
  Release campaigns use existing try/rating callbacks and unchanged reward
  policy, durable shared delivery evidence and the same claimed outbound queue.
  No DB connection spans provider IO. A recipient filter/transport/campaign
  change skips before claim; Stop, late acknowledgement, signed pending-only
  resume, expired payload retention and no uncertain retry remain coherent.
- Discount offers preserve the existing checkout/eligibility/quota/repeat
  contract and canonical native ownership. Plain three-language copy is stored
  for the existing text consumers; no entity double-escaping. Creation defaults
  paused and never sends a notification or grants access. Enabling an existing
  notification-enabled offer through this command is refused.
- No schema/migration/cron, AI translation, DB media BLOB, feature-default or
  external MCP scope change. Private aggregate snapshots remain daily-on-demand.
- Broad PWA/catalog/initializer/legacy payment suite with isolated PostgreSQL
  and Redis: **694 passed, 1 skipped, 632 subtests passed**. Later focused final
  campaign/outbound/marketing/discount regressions: **77 passed, 54 subtests**,
  including real PostgreSQL single-round races, proof expiry during recipient
  lock waits and concurrent drainers. This includes stop-during-provider and
  original-transport reservation regressions added after the broad checkpoint.
- Actual campaign ASGI/virtual-WebAuthn browser passed UZ/RU/TJ at 390/1440,
  missing-language disclosure, native cancellation/draft preservation, native
  personal discount, release markup and one-round ad delivery. Shared outbound,
  full settings/management and media-only browser suites also passed. Evidence
  `/tmp/hsk-admin-pwa-campaigns*-20261025`; mobile screenshots reviewed.
- Security workflow now follows this owner feature branch and includes campaign
  browser and PostgreSQL tests. Arbitrary campaign media/buttons and unattended
  scheduling are outside the explicit standalone contract, not silently proxied.

## Latest statistics/navigation sync — 2026-10-25

- A second owner-requested refresh found `origin/main` at
  `7aee50bd` (PR #206). Its seven real-data statistics tabs, five-icon mobile
  navigation, bottom More sheet, responsive users/payments and browser QA
  are integrated into this feature branch. Feature single-window native
  signing and course-ad creation remain intact. Generated catalogs were
  rebuilt from the merged canonical UZ/RU/TJ sources.
- Actual core and full settings/management ASGI/WebAuthn browser suites passed
  after conflict resolution. Evidence: `/tmp/hsk-admin-pwa-main2-sync-*-20261025`.
  Merge direction remains main into feature; no feature promotion/deploy.

## Current new-course-ad creation increment — 2026-10-25

- The owner feature branch now supports signed `course_ad_create`: one-language
  or explicit UZ/RU/TJ title/CTA, photo/video, fixed type/placements, bounded
  duration/link and paused default. The original V10 editor uses one contextual
  Create action and native passkey; cancellation preserves the draft. Media
  stays on the existing volume with no BLOB/migration/AI request.
- UTF-8 binary-command metadata uses strict base64url under the existing header
  bound. Video proof ownership is checked against the actual cookie session
  before any encoding, including two sessions for the same actor. Encoding
  stays outside DB transactions with one worker slot; creative/proof/audit are
  atomic and rollback cleanup uses only the exact created PK.
- Marketing/media/shared translation tests: **76 passed, 50 subtests passed**.
  Actual ASGI/virtual-WebAuthn media browser passed image/video replacement,
  QR and new multilingual creation. UZ/RU/TJ 390px cancellation retains inputs;
  the signed all-language create writes one inactive creative, one audit,
  authored copy and disk bytes. Screenshots under
  `/tmp/hsk-admin-pwa-course-ad-create-20261025` were visually reviewed.
- Remaining code: bounded campaign activation/delivery, release-feedback and
  discount campaigns. No main promotion, deployment or feature-default change.

## Current main synchronization — owner request, 2026-10-25

- The owner explicitly requested the latest `main` changes in the existing
  feature branch. Sync source is `origin/main` at
  `fb9772d3255166fca3ff3e37baa60fbbdfbf9c24` (PR #207 seamless-passkey policy).
  Merge direction is main **into** the owner feature branch. Preserve the later
  single-action command UI below; no feature-to-main promotion or deployment.
- Launch/resume first revalidates the existing HttpOnly cookie with `/me`.
  A valid authorized session opens directly. A 401 triggers one automatic
  native passkey attempt per foreground visit with a manual browser fallback.
  Explicit logout still revokes the session; private browser memory clears on
  hide/pagehide/offline. This supersedes mandatory logout on every launch.
  Sensitive commands still require their exact fresh one-use step-up proof.
- Outbound browser QA now distinguishes a cookie-backed reload (same signed
  job session) from explicit logout/reauthentication (fresh signed pending-only
  resume). The one-click command flow and all backend limits remain intact.
- Merge validation passed: shell contract **7 tests**, JS syntax and the
  63-artifact catalog check (zero stale), plus full core browser,
  settings/management and outbound browser suites under
  `/tmp/hsk-admin-pwa-main-sync-*-20261025`. No merge conflicts or backend
  permission/feature-default changes were introduced.

## Current all-section single-window owner instruction — 2026-10-25

- The owner extended the payout instruction to **all** Admin PWA sections:
  remove the second confirmation screen. The original editor's contextual
  Send/Save/Delete/Grant/Accept-payment action prepares the exact server payload,
  opens native WebAuthn and executes immediately after that one ceremony.
  Generic “confirm with passkey” and action-related “Next” buttons are removed.
  Pagination and navigation Next buttons are unrelated and remain.
  The editor/ceremony flow lives in `app/static/admin-pwa/app.js`;
  `singleEditorAction` owns draft locking and cancellation isolation.
- Shared management, payment decisions with loaded receipts, access grants,
  course policy and HSK 3.0 settings use that flow. Inputs freeze while the
  operation is prepared/signed; loaded state is checked before signing where
  available. Native cancellation restores the original editor/draft. A closed
  old native promise cannot clear a newer editor's busy/controller state.
  Lost save responses expose only reread recovery. Backend proof/CAS/audit,
  receipt loading, typed account-deletion ID and messaging bounds remain active.
- Existing scope-reducing message-stop and MCP-revoke buttons no longer open
  an extra app confirmation. They use their original cookie/CSRF contracts;
  no new write capability or external MCP scope is added.
- Canonical UZ/RU/TJ labels and browser QA now follow this interaction. Browser
  tests pause the real native ceremony using a test-only gate to exercise
  cancellation, stale writes and lost responses without adding a second UI.
- Validation: all Admin PWA unit/API and affected catalog tests passed:
  **546 passed, 58 environment-dependent skipped, 457 subtests passed**.
  Full core browser (including payment/access/receipt/revoke/offline/SW), full
  settings/management, media-only, outbound, payout and minimal-Inbox browser
  suites passed. Settings QA additionally exercises course/HSK 3.0 saves,
  native cancellation retaining drafts, stale state before the ceremony and
  stale writes after it. The local environment was missing the existing pinned
  `pywebpush==2.5.0` dependency; installing that pin resolved its encoder test.
  The service-worker harness explicitly reapplies CDP offline state after a
  SW-controlled reload for the current Chromium build.
- `node --check`, Python compile, diff checks and the 63-artifact catalog check
  passed (zero stale). UZ/RU/TJ mobile/desktop controls have no overflow.
  `/tmp/hsk-admin-pwa-single-action-outbound-20261025/direct-message-confirm-uz-390.png`
  and `/tmp/hsk-admin-pwa-single-action-browser-20261025/mobile-payment-receipt.png`
  were visually checked: the original editor has Send/Accept-payment actions.
  Screenshot filenames retaining “confirm” are historical names, not a second
  confirmation screen. Implementation commit
  `f188c243c80a9a339db731d757bd84376db39c52` is pushed to the owner branch;
  `git ls-remote` returned that exact SHA. GitHub combined status and Actions
  queries returned zero entries for this SHA, so no GitHub CI result is
  available. All feature defaults remain OFF; no main merge or deployment.

## Current owner-selected branch and UI baseline

- Continue **only** on `feat/admin-pwa-minimal-inbox-passkey-20261025`.
  PR #204/#205 were merged at older heads; branch commits after those merges remain
  on this feature branch and must not be redirected to `main`.
  The owner selected this branch and accepted its notification-window changes
  on 2026-10-25. The previous MCP branch/PR #201 references below are historical;
  those changes are already ancestors. Keep work on this feature branch and
  preserve minimal Inbox/swipe behavior plus the current session policy above.
- Owner baseline at `72d17493`: unread-first title-only notification rows,
  automatic-only importance, explicit read-on-open detail, receipt handoff to
  financial review and return to the originating user's inbox. Preserve the
  single close control, red important state and one-step narrow left-zone
  iPhone back gesture with native scrolling/selection/edge exclusions. Existing
  audited backend triage/Push contracts remain compatible; no manual priority UI.
- Launch/resume follows the owner-approved seamless session policy above;
  it does not force a logout of a still-valid server-verified session.
  Sensitive commands keep their own exact transaction-bound proof.
  No OAuth/MCP permission expansion.
- Payment reconciliation code/migration was committed at `e72c945a`; the branch
  adds its initial tests. Continuing work validates rollback, stale in-flight
  attempts, bounded queue pages, concurrent resolutions and real migration
  preservation, and adapts remaining management browser QA to real fresh login.

## Current payout proof / one-window owner instruction

- The owner rejected the second payout confirmation window. Payout state and
  completion now execute from the original editor with one primary passkey
  button. A 2-MiB raster is staged on file selection, privately previewed in
  that editor and required to load before completion. Current read revision
  must match prepare before any native ceremony. Preserve this new baseline.
- `pwa_payout_completion.py` and migration 0130 implement private same-session
  proof metadata, bounded upload quota/IO, no DB image BLOB/public file, exact
  proof/recipient/copy signature and shared reserved-owner `mark_payout_paid`.
  Post-lock authority/expiry, asset consumption, financial state, immutable
  command and optional one-recipient claimed photo notice are atomic.
- Provider upload goes only to the current uploading admin's private Bot chat;
  partner notification occurs after signed commit through the shared outbound
  drainer. Both routers share two worker slots. A provider timeout is never an
  automatic retry and does not undo a paid record. No actual money transfer.
- Explicit proof metadata retention CLI defaults to bounded dry run. Expired
  staging cleanup preserves financial proof, command/stop evidence and notice.
  Nonempty actual migration downgrade refuses data loss. QA head is now 0130;
  the fixture DDL rehearsal covers 0103–0130, including required payout FK.
- Before final one-window browser additions, payout/outbound/state/PG/QA suite
  passed **71 tests**. Final broad PWA/catalog/initializer and affected legacy
  payment/access/import suite with real isolated PostgreSQL/Redis: **642 passed,
  zero skipped**. Actual ASGI/WebAuthn management and outbound browser suites
  passed. The single-window payout browser passed UZ/RU/TJ 390px, private image
  decode, unchanged original editor during native preparation, no extra confirm
  control, closing cancellation, stale initial revision before FIDO, genuine
  completion and lost-response no-retry. One notice and one command only.
  Screenshots `/tmp/hsk-admin-pwa-payout-single-final-20261025` inspected.
  Catalogs: 63 artifacts, zero stale; JS/Python syntax and diff checks passed.
- Remaining code: campaign activation/delivery, release-feedback/discount
  campaign commands and general media/QR/creative uploads.
  External MCP is still statistics-only; all feature
  defaults remain OFF, no main/deploy/live migration.

## Current partner-application notice increment — 2026-10-25

- PWA approve/reject now bind the canonical recipient, current account-language
  snapshot and fixed UZ/RU/TJ notice copy to the existing `partners.update`
  passkey proof. The status/bonus decision, hash-only command audit and one-user
  outbound job commit together. A missing canonical Telegram account creates
  no invented recipient and does not block the status decision. Block/unblock
  remain unchanged.
- The existing bounded outbound drainer starts only after commit, shares its
  two worker slots, and rechecks recipient eligibility before its one attempt.
  Unknown delivery is not automatically retried. The V10 comparison now shows
  the actual localized notice before the action details; safe preview preserves
  only fixed bold tags and escapes all other markup.
- Local checks: partner, outbound, payout and payout-completion regression
  suites **53 passed**, including disposable PostgreSQL lock-wait tests; main
  import/catalog checks **9 passed**. Actual management browser/WebAuthn suite
  passed UZ/RU/TJ at 390/1440px. Approval/rejection each produce one queued
  notice; browser screenshots are in
  `/tmp/hsk-admin-pwa-partner-notices-final-20261025`. Catalogs: 63 artifacts,
  zero stale; JavaScript/Python syntax checks passed.
- Next code: general media/QR/creative uploads and safe campaign delivery.
  Feature defaults remain OFF; external MCP remains statistics-only.

## Current campaign-draft increment — 2026-10-25

- `/marketing/prepare|save` accepts a strict text-only campaign draft with
  explicit UZ/RU/TJ copy, selected target languages, optional HSK track and a
  1–720 hour window. The transaction-bound passkey proof signs a compact hash
  of all three texts; text is HTML-escaped before the existing localized ad
  payload storage. The same transaction creates one inactive ad campaign and
  content-free hash-only command audit. No audience query, AI translation,
  provider IO, delivery row, migration or automatic sender is added.
- The V10 composer has localized controls and one before/after review followed
  by one passkey ceremony. New records use `is_active=false` and
  `next_send_at=NULL`, so the legacy due-ad worker cannot send them.
- Local checks: marketing API plus legacy HSK ad-target regression **17 passed,
  11 subtests passed**. Actual
  ASGI/virtual-WebAuthn browser management passed at 390/1440px in UZ/RU/TJ,
  including escaped hostile markup, persisted inactive state and no horizontal
  overflow. Screenshots: `/tmp/hsk-admin-pwa-campaign-draft-20261025`.
  Catalogs: 63 artifacts, zero stale; Python/JavaScript syntax and diff checks
  passed. Commit/CI SHA will be recorded after push.
- Remaining: bounded campaign activation/delivery, release-feedback/discount
  campaign commands and general media/QR/creative uploads. Feature flags remain
  OFF; MCP remains statistics-only.

## Current desktop-promo raster media increment — 2026-10-25

- The first-party Marketing editor can add, replace or clear the existing
  desktop-promo image using one exact passkey confirmation. Only JPEG/PNG/WebP
  raster files are accepted (2 MiB, 8 million pixels, one frame); bytes are
  decoded server-side, hashed against the signed command, and written to the
  existing media volume using a random server filename. The DB stores a path
  in the existing settings record, never an image BLOB or new migration.
- Settings and content-free audit commit together. Uncertain commits retain a
  potentially referenced file; replacement cleanup runs only after commit. The
  public route allowlists generated image names. Upload requires the active
  same-origin WebAuthn session and exact transaction-bound one-use proof.
- Browser UI stages and previews locally, binds digest/size into the review,
  and asks for one passkey ceremony. No media goes to a provider, Bot, AI,
  campaign, or external MCP; all rollout flags stay OFF.
- Local evidence: marketing regression suite **18 passed / 11 subtests**;
  desktop-download compatibility suite **21 passed**;
  full ASGI/virtual-WebAuthn browser management suite passed at UZ/RU/TJ,
  390/1440px. The file preview was checked in RU/TJ; upload and clear were
  exercised in UZ. The final mobile
  comparison screenshot
  `/tmp/hsk-admin-pwa-desktop-promo-media-final2-20261025/desktop-promo-image-confirm-390.png`
  was visually checked: the preview fits above the single footer confirmation.
  Catalogs: 63 artifacts, zero stale; JS syntax, Python compilation and
  `git diff --check` passed. Commit `0f099b3555ef4d8eeb4576ebf5d54d816456aeea`
  is pushed and the feature branch remote was verified at that SHA. No CI
  status for that exact SHA has been recorded here.
- Remaining at this historical checkpoint: course-ad image replacement, new
  creative/video uploads and payment QR media, safe campaign activation/delivery,
  release-feedback/discount campaigns, and the other unimplemented items in
  the acceptance contract. Do not infer full PWA completion from that increment.

## Current course-ad image replacement increment — 2026-10-25

- An existing course-ad creative can replace its media with one JPEG/PNG/WebP
  image up to 1 MiB and 8 million pixels. The exact image hash/size and current
  creative revision are bound into the existing `marketing.update` passkey
  proof. Only the existing creative row changes; title, target, placement and
  activation state are preserved. New creative creation and video upload stay
  out of scope.
- The upload streams within its small limit, checks the same-origin active
  WebAuthn session, decodes a single-frame raster server-side, and atomically
  writes a random filename to the existing course-ad media volume. The row and
  content-free audit commit together; no DB image BLOB, backup metadata or
  migration is added. Shared old media is retained; unshared old media is
  cleaned only after commit. Uncertain commit outcomes preserve a potentially
  referenced file.
- The V10 editor shows current and proposed media, local preview and byte size
  before one passkey confirmation. Copy is localized in UZ/RU/TJ. The mobile
  review screenshot is
  `/tmp/hsk-admin-pwa-course-ad-media-focused-20261025/course-ad-image-confirm-390.png`;
  it was visually checked after correcting the course-ad title label.
- Local evidence: marketing plus existing course-ad media/type suites
  **55 passed / 33 subtests**; focused actual ASGI/virtual-WebAuthn image upload
  passed at 390px with SQL/disk assertions;
  the full management browser regression suite passed at UZ/RU/TJ 390/1440px
  for the existing settings/prices/course-ad state/delete/account flows.
  Catalogs: 63 artifacts, zero stale. Feature defaults stay OFF, external MCP
  stays statistics-only. The full PWA remains incomplete.
- Remaining media/code: new course-ad creative creation, payment QR,
  campaign activation/delivery, feedback/discount commands and the other open
  acceptance items. Keep each in its own exact signed contract and avoid
  provider/media IO during read paths.

## Current course-ad video replacement increment — 2026-10-25

- `marketing.update` now has a distinct signed `replace_video` command for one
  existing course-ad creative. It binds the existing row revision, exact
  source SHA-256 and byte count to one passkey. Only MP4, MOV, WebM and M4V up
  to 25 MiB are accepted; FFmpeg converts the upload to the established
  WebView-safe H.264/AAC MP4 output. The operation cannot create a creative,
  change its title/status/placement, or deliver a campaign.
- Before streaming, the endpoint requires the current admin session and the
  exact unexpired verified proof, including its still-active credential.
  Encoding runs outside the target-row DB transaction, with one PWA video
  encoder slot per worker and the established 120-second subprocess timeout.
  A short write transaction consumes the proof, rechecks the creative revision,
  attaches the atomically published random MP4 path and content-free audit.
  Rollback cleanup re-reads the row and preserves media if commit state is
  uncertain. The existing 1-MiB decoded-raster replacement remains separate.
- The V10 editor uses the existing one-passkey confirmation, the browser-local
  video preview and an escaped file name/size review. UZ/RU/TJ copy is sourced
  from `localization/ui/*/miniapp.json`. Screenshot
  `/tmp/hsk-admin-pwa-course-ad-video-20261025/course-ad-video-confirm-390.png`
  was visually checked at 390px; there is one passkey action and no overflow.
- Local evidence: `.venv/bin/python -m pytest -q tests/test_course_ad_media.py tests/test_admin_pwa_marketing.py`
  **26 passed, 11 subtests passed**; actual ASGI + virtual-WebAuthn browser
  upload/preview/save for course-ad image/video and payment QR passed at 390px.
  `node --check`, Python compile checks and the 63-artifact catalog check
  passed. Exact-head GitHub CI has not yet been queried for the implementation
  commit. Feature flags remain OFF, MCP stays statistics-only, and no staging,
  live ChatGPT, physical-device, merge or deployment action occurred.
- The implementation was included in owner sync commit
  `486052607d40fa37dbae456b92e062218b02e2dc`, now an ancestor of the verified
  feature branch. Remaining code: new course-ad creation, safe campaign
  activation/delivery and release-feedback/discount commands, plus other open
  acceptance items. Full PWA acceptance/staging remains incomplete.

## Current subscription QR media increment — 2026-10-25

- `pwa_payment_qr.py` and `/payment-qr/read|prepare|media/save` now support
  replacement for the six existing Alipay/WeChat plan targets in the standard
  subscription scope. One WebAuthn confirmation binds the exact price/QR
  revision plus image SHA-256 and byte count. Only a decoded one-frame
  JPEG/PNG/WebP raster up to 1 MiB and 8 million pixels is accepted. Visa,
  HSK 3.0 unlock, discount and campaign QR scopes are excluded.
- The existing checkout contract uses Telegram `file_id`, so the image is
  sent once to the authenticated admin's private Bot chat. The short database
  transaction then rechecks proof, current target and revision, and atomically
  saves only the `file_id` plus content-free command audit. No DB image BLOB,
  new migration, price/payment/access write or network call in a DB transaction
  is added. A failed write deletes the Bot message only if a fresh DB query
  proves its media ID is unreferenced; uncertainty preserves the message. No
  provider retry is automatic.
- The V10 editor is reachable from the existing price editor for Alipay/WeChat.
  It displays current QR-set state, a local preview and unchanged amount in the
  original editor; Replace opens native passkey directly under the current
  all-section interaction rule above. Copy is canonical in
  UZ/RU/TJ. Mobile screenshot `/tmp/hsk-admin-pwa-payment-qr-e2e-20261025/payment-qr-confirm-390.png`
  was visually checked; the old and proposed state fit at 390px.
- Local evidence: payment QR, subscription prices, marketing, course-ad media
  and type regression suites **72 passed, 40 subtests passed**; actual ASGI + virtual-WebAuthn media editor passed at
  390px with Bot stub, SQL price/QR checks and one audit. `node --check` passed;
  catalog generation/check: 63 artifacts, zero stale. Commit
  `f355bef761c55c924c2212e55457d222b99a94f5` is pushed to
  `feat/admin-pwa-minimal-inbox-passkey-20261025`; `git ls-remote` returned the
  same SHA. GitHub combined commit status and commit workflow-run queries
  returned no entries for this SHA, so no exact-head CI result is available.
  Feature flags remain OFF, external MCP remains statistics-only; no staging,
  ChatGPT live integration, physical-device QA, merge or deployment occurred.
- Remaining: course-ad video and new creative creation, safe campaign
  activation/delivery, release-feedback/discount commands, and other open
  acceptance/staging gates. Do not infer full PWA completion from QR support.

## Mobile Inbox touch and fresh-login regression

- Cause: the minimal detail image/back buttons inherited a sub-44px height;
  browser login QA also incorrectly required the desktop-only sidebar to be
  visible after a mobile reload. The real passkey API had succeeded.
- Fix: scope `min-height:44px` to detail buttons; fresh-login QA checks the
  authenticated shell on both viewports. No list/detail redesign or auth bypass.
- Risk/prevention: existing 390px image-target assertion remains strict; full
  WebAuthn/payment/access/export/image/offline/revoke/SW browser suite passed
  at `/tmp/hsk-admin-pwa-touch-and-auth-20261025`. New payout work is separate.

## Current bounded outbound text increment

- `pwa_outbound.py`, migration 0129 and V10 Messages/profile editors implement
  direct canonical target, current-admin self-test and filtered broadcast.
  Maximum 1000 recipients, one private three-language copy, compact exact
  content/audience commitment, atomic proof/audit/queue and pre-provider claims.
  Existing shared filtering/Bot sender/reachability logic is preserved.
- Two local drainer slots process ten-recipient batches, with no DB connection
  during provider IO/pacing, no UI polling or automatic uncertain retry.
  Session/authority/TTL is checked before every claim. A new session needs a
  fresh exact signed pending-only resume. Stop only reduces scope and appends
  separate content-free evidence; one already claimed attempt may finish.
- Private payload lifetime is one hour. Explicit bounded retention CLI previews
  by default, purges only with `--purge-expired`, retains command/stop audits.
  Canonical deletion removes direct payload/recipient; broadcast deleted count
  is visible. Nonempty migration downgrade refuses data loss.
- Actual ASGI/fresh virtual-WebAuthn outbound browser passed UZ/RU/TJ 390px,
  self-test, 12-recipient broadcast split at ten, fresh-login signed resume of
  only two remaining recipients, XSS escaping and no overflow/script errors.
  Screenshots `/tmp/hsk-admin-pwa-outbound-verified-20261025` visually inspected.
  API/PG/initializer/0103–0129 DDL gate: **44 passed**. Broader PWA, catalog,
  initializer and affected legacy payment/access/import gate with actual local
  PostgreSQL/Redis: **622 passed, zero skipped**. After final narrow-query and
  audit-preservation additions, outbound gate: **15 passed**, including real PG
  worker contention, canonical purge and nonempty actual-migration refusal.
  Catalogs: 63 artifacts, zero stale; JS/Python syntax and diff checks passed.
- Remaining code: campaign creation, media/QR/creative uploads and partner payout
  verified proof/completion plus recipient notices. Preserve owner's Inbox and
  current branch; all defaults OFF, external MCP remains statistics-only.

## Current payment-delivery reconciliation validation

- The existing `/payment-deliveries/read|prepare|save` command now has actual
  rollback, recent-versus-stale attempting, bounded mixed queue pagination,
  real-PG concurrent-resolution and nonempty migration-downgrade regressions.
  Operator notes retain reason hashes only, update reconciliation metadata and
  never change payment decisions or resend. Two exact-status index pages cap
  queue reads at 62 metadata rows; no private effects/review payload in lists.
- Migration `0128_admin_pwa_command_lookup` adds nullable reconciliation time,
  an unresolved-status partial index and action/target audit lookup. Nonempty
  reconciliation metadata prevents destructive downgrade. Empty QA baseline
  defers the 0127-owned Message index without mutating application metadata;
  real PG now exercises every migration 0103–0128, rather than stopping at 0126.
- Reconciliation/initializer tests: **19 passed** with actual PostgreSQL. The
  combined reconciliation/PG/initializer gate before the additional cases also
  passed **34 tests**, including the full 0103–0128 DDL rehearsal.
- Actual ASGI/virtual-WebAuthn management browser now performs real fresh
  passkey login, preserves secure cookie responses and revokes the genuinely
  issued session in the final security check. All prior management commands
  plus localized reconciliation confirm/save/queue removal passed at 1440/390
  UZ/RU/TJ. Screenshots inspected; owner's notification window is unchanged.
- Fixed two operator-view labels through canonical UZ/RU/TJ: payment ID and
  reconciliation reason, avoiding the unrelated payment-rejection reason.

## Current orphan-triage retention increment

- `scan_orphaned_inbox_triage` and operator CLI
  `python -m scripts.admin_pwa_inbox_retention` add one explicit metadata-only
  keyset page (default 100, hard maximum 1000), at most five indexed source-ID
  checks and exact missing-source deletes. All five sources are covered.
  No raw text/BLOB, global COUNT, periodic scan, source deletion or audit change.
- Default is read-only dry run. `--purge-orphans` opts into one transaction with
  metadata `FOR UPDATE SKIP LOCKED`; `--after-source/--after-id` continue the
  returned primary-key cursor. Full final pages may produce one empty next page;
  locked rows/concurrent later source deletions wait for the next explicit sweep.
- Five new cleanup tests plus payout regression: **11 passed**, zero skips with
  disposable PostgreSQL. Tests cover all live/missing sources, exact keysets,
  content-free/no-write dry run, audit/source preservation, rollback/idempotence,
  strict bounds and actual PG locked-row skip. CLI help has no engine/startup IO.
- Payout state checkpoint pushed at `6810c016`. Remaining code: messaging/
  campaigns, payout proof upload/completion and recipient notices, other media/QR
  uploads and payment-outbox operator reconciliation. Orphan metadata cleanup
  is implemented; do not keep reporting it as wholly missing code.

## Current partner-payout state increment

- `/partner-payouts/read|prepare|save` implements shared reservation/release,
  rejection and signed exact UTC deadlines (1/3/7 days). Reservation ownership
  is enforced; another admin cannot release, reject or steal a processing row.
  Full raw payout revision binds amounts, destination and provider references;
  post-row-wait authority/expiry and shared conditional updates precede atomic
  one-use proof/audit. No money transfer, paid flag, Payment or ledger entry.
- Marketing payout list projects at most 31 metadata rows; details explicitly
  load bounded bank/account data without exposing Telegram file IDs. Compact
  editors use a single operation select and passkey confirmation. UZ/RU/TJ
  actual ASGI/virtual-WebAuthn desktop/mobile browser passed all four state
  operations and existing management flows; screenshots visually checked.
- Payout/import gate: eight passed, including real ES256/replay, exact deadline,
  wrong reservation owner/closed row, destination and date tamper, audit rollback,
  no-payment/access/ledger mutation and real-PG competing-admin reservation.
- Payout completion with verified proof upload and outbound recipient notices
  remain separate media/durable-delivery work. No arbitrary file-ID acceptance
  or claim of payment delivery is added. Other remaining code remains below.

## Current partner-application increment

- `/partners/read|prepare|save` now implements pending approve/reject and
  partnership block/unblock through shared PartnerService. Exact passkey proof,
  raw application/bonus revision, shared bonus-setting + partner-row locks,
  post-wait authority/expiry and atomic content-free audit. Existing locked
  signup bonus is granted once; no Payment/learner block/Pro/budget changes.
- Marketing has a compact partner row, 30-row metadata keysets and explicit
  details/operation select/before-after confirmation. Canonical UZ/RU/TJ, mobile
  screenshots checked, stored promotion text escaped, no polling/provider IO.
- Partner/ownership/import gate: **18 passed**, including real ES256/replay,
  bonus config and decision tamper, rollback, fixed page projections, real-PG
  legacy row conflict and proof expiry during partner-row wait. Extended actual
  ASGI/virtual-WebAuthn management browser passed all four partner operations
  and prior management flows; 390px confirmation screenshots in all locales.
- Reminder/late-feedback checkpoint pushed at `cfde1c49`; its broad local gate
  passed 522 tests without service skips. Its GitHub CI outcome must be checked
  for that exact head, not inferred from local success.
- Remaining code parity: direct/mass messaging, campaigns, partner payout and
  outbound notice delivery, media/QR/creative uploads, operator reconciliation
  and non-native orphan-triage cleanup. Keep these explicit; no complete-product
  claim and no automatic proxy to legacy mutation routes.

## Current reminder-template and late-feedback UI increment

- Five fixed reminder keys have `/notifications/read|prepare|save`, current
  enabled state and canonical UZ/RU/TJ custom/default text. Safe placeholders,
  UTF-16 text/caption limits, raw revision CAS, shared legacy-writer locks,
  exact one-use passkey commitment and atomic hash-only audit. No provider IO.
  The full three-language copy stays separate from its compact signed digest;
  the existing 4096-byte step-up payload limit is unchanged.
- System's compact template list and single-language editor preserve unsaved
  drafts across language switches and invalid input. Escaped per-language
  before/after confirmation, default restoration, no auto retry. New localized
  copy is canonical and generated. Screenshots checked at 390px in UZ/RU/TJ.
- Broad local PWA/catalog/reminder gate with actual isolated PostgreSQL and
  Redis: **522 passed, zero skipped**. Full auth/payment/grant/export/image/SW
  browser suite passed. Template/import gate: nine passed, including real ES256 for large multi-locale
  copy, tamper/default/media changes, replay, audit rollback, strict placeholders,
  UTF-16 limits, bounded metadata reads and real-PG legacy first-insert conflict.
  Extended real ASGI/virtual-WebAuthn management browser passed real template
  save/reread, validation/draft retention and existing management flows.
- CI at `2cea2fd5` passed Python/Redis and PG but reproduced a late feedback
  response replacing the whole statistics page and closing its open export
  menu (run 40158996994). Feedback refresh now updates only its own panel.
  A deterministic held-response browser regression verifies the unrelated
  menu and keyboard focus remain open; full export/cancellation checks passed.
  No extra request, polling, CSP exception or weaker hit-target assertion.
- Remaining code: messaging/campaigns, partner actions/payouts, media/QR uploads
  and operator/retention items. Historical checkpoints below retain old scope.

## Current manual-ledger increment

- `/portfolio/read|prepare|save` uses integer minor units, fixed currencies and
  existing PortfolioService conversion. Exact conversion is reviewed/signed;
  stale rates or payload changes deny without a ledger append. One-use proof,
  append and hash-only note audit are atomic. No Payment/access/budget changes.
- Read-only history uses 30-row keysets over manual sources only, preserves
  legacy subcent values and bounds note projection. No payment synchronization,
  all-ledger scan, provider request or background refresh. System navigation
  adds compact history/new-entry editors with canonical UZ/RU/TJ and passkeys.
- Local ledger/import gate: nine passed, including real-PG duplicate-proof
  contention, ES256/replay, conversion changes, rollback and no-write/no-payment
  history checks. Actual ASGI/virtual-WebAuthn management browser passed the
  ledger confirmation and append together with all existing management flows.
- Remaining code: messaging/campaigns, partner actions/payouts, notice templates,
  media/QR uploads and the operator/retention items in the management contract.

## CI follow-up — healthy Redis coordination versus outage timing

- At `c6d4af7a`, [run 40157595462](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40157595462)
  passed PG but the healthy Redis concurrency case entered outage fallback:
  asyncio debug logs show a 415ms event-loop stall, exceeding the fixed 350ms
  IO deadline. Per-worker fallback correctly allowed separate worker refreshes;
  that is not the healthy coordination guarantee this test intended to check.
- Production budgets remain 250ms socket / 350ms IO, now named constants.
  Healthy-service integration tests use a bounded three-second test budget and
  explicitly assert that fallback was never entered. A separate deterministic
  10ms stalled-IO regression confirms one local daily refresh and no repeated
  Redis/SQL attempts after timeout. No production timeout, quota or coordination
  assertion was weakened.
- Built Redis 7.4.2 under `/tmp` and ran an isolated loopback-only 64MiB test
  service, with no global installation or application config changes. Actual
  Redis/cache/R2/feedback gate: **29 passed**, zero service skips; healthy
  coordinator and timeout cases passed again independently.

## Current required-channel increment

- First-party `/channels/read|prepare|save` adds strict mode, add/upsert, state
  and delete schemas; exact `channels.update` passkey proof, raw-state CAS,
  post-lock authority/expiry and atomic hash-only 0126 audit. Shared service/
  repository semantics remain authoritative, including correct missing-row
  results. Shared key locks serialize first writes and row locks protect
  legacy updates. No new table, scheduler, dependency or Telegram IO.
- System section exposes compact list/mode rows; lists use 30-row keysets.
  Add/state/delete editors show exact before/after values, escaped stored
  titles and private invitation URLs only to the current first-party admin.
  UZ/RU/TJ canonical text, no background polling, no external MCP scope change.
- Local broad Admin PWA/catalog/bootstrap gate with real PostgreSQL and CI's
  minimal public baseline: **511 passed, five Redis-only skipped**. Shared
  course/access/unlock/ad regressions **55 passed**. Channel command/import
  gate **eight passed**, including real PG legacy-vs-PWA first-add contention,
  genuine passkey/replay, strict URL/target validation, rollback, alias-aware
  stale confirmation and keyset/no-default-write behavior.
- Extended real ASGI/virtual-WebAuthn browser suite passed settings/prices,
  marketing, account management and all four channel operations, with mobile
  UZ/RU/TJ mode screens. No provider requests occur. CI explicitly includes
  the channel PG case. Previous CI fixes are recorded immediately below.
- Remaining code parity: direct/mass messaging, campaign creation, partner
  actions/payouts, manual ledger, notice templates and media/QR uploads; keep
  them absent/disabled until their own exact audited commands exist.

## CI follow-up — strict CSP browser polling

- At `1d4d593b`, [Admin PWA run 40156625123](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40156625123)
  confirmed the PG migration/contention job SUCCESS. The primary suite passed
  its Python/Redis, legacy and catalog steps, then failed the export browser's
  remaining `page.wait_for_function` call under Linux's strict CSP.
- That single wait now uses the existing debugger-evaluation `wait_js` helper,
  matching all other protected browser checks. The connected/visible >=44px
  action invariant is retained; no CSP relaxation or browser bypass was added.
  Targeted real ASGI statistics/feedback export browser checks passed locally.
- Two old course-level test doubles now supply the repository's required
  `lock_key` method; their existing value/no-op timestamp assertions remain.
  Shared course/access/unlock/ad regressions: **55 passed**.

## CI correction — isolate ORM fixtures from migrated public tables

- [Admin PWA run 40155795894](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40155795894)
  at `06b99d08` passed the primary app/Redis/browser/legacy gate and scoped
  migration/rollback steps. Five new PG cases failed at fixture seeding with
  `UndefinedColumnError: users.telegram_id`.
- Root cause: the new UUID-schema fixture used `search_path=<schema>,public`.
  SQLAlchemy `create_all(checkfirst=True)` found CI's intentionally minimal
  migrated `public.users`, skipped creating the full local-schema User table,
  and attempted fixture inserts into the wrong table. A local empty public
  schema had concealed this isolation bug.
- Fix: test connections use only their own UUID schema, matching the existing
  PG suite; no production schema, migration or validation is changed. Reproduced
  CI's minimal public users table in a new disposable local database: all nine
  affected settings/HSK30/account cases passed with that baseline present.
  Do not resolve this by widening public.users or skipping the PG tests.
- Final combined local gate with that populated public baseline: **35 passed**
  across existing PG locks/revocation, new setting/price/account contention and
  HSK30 transition regressions. Shared HSK30 enable now takes its setting lock
  before deciding a no-op; record reads refresh already-loaded ORM state.
  Real PG regression holds a concurrent disable uncommitted and keeps an old
  identity-map row alive: explicit enable waits, sees the committed disable
  and restores enabled, preserving actual-transition timestamp semantics.

## Current account increment — canonical block/unblock/delete

- Settings/marketing checkpoint pushed at `06b99d08d25af896ace5b1ed901656c14248e3ae`.
  New `/users/prepare-management` and `/users/manage` use exact `users.block` /
  `users.delete` proofs, current target hash/row lock, self/admin target
  protection and atomic immutable command audit. Existing shared UserRepository
  owns blocked-state restoration and personal-data deletion/anonymous finance
  retention. No synthetic payment or independent entitlement logic.
- Profile overflow keeps one main subscription action. Localized UZ/RU/TJ
  block/unblock/removal forms show exact canonical ID/current state/requested
  operation; removal requires typing that ID. Lost responses offer read-current
  recovery only. Optional unblock notice runs once after commit, no network IO
  under account locks and no delivery guarantee. Guard cache invalidates after
  commit only.
- Local gate: six new security/financial/rollback tests plus existing native
  and import regressions **20 passed**; legacy delete/cleanup/block guards
  **35 passed**. Extended ASGI/virtual-WebAuthn management browser passed real
  block/unblock/removal, mobile UZ/RU/TJ confirmation/ID validation, existing
  settings/price/marketing saves and cancel/stale/lost-response/revoke flows.
  Real-PG target-lock expiry regression is included in the dedicated CI job.
- Remaining legacy parity stays explicit in the management contract, including
  required channels, messaging/campaigns, partners, manual ledger and media.

## Current completed increment — localized settings and marketing editors

- Last pushed checkpoint is `1a3be7bc0ad9e45f2613450e1113a58cfeca921f`;
  new increment adds `/settings/read|prepare|save` and
  `/marketing/read|prepare|save`, exact `settings.update` / `marketing.update`
  step-up actions and existing 0126 atomic command audit. No migration needed.
- Fixed-key settings: bank details, allowed AI model, support contact and
  language-specific help videos. One 16-key read, no arbitrary configuration
  access/default writes, shared normalization, hash-only audit, postcommit AI
  cache update. Marketing: shared sales experiment/app promotion controls and
  bounded existing creative activation/deletion, no media BLOB or file scan.
- Course/System/Marketing sections are usable through desktop navigation and
  mobile More. Calm section rows fetch only when an editor opens. Before/after
  confirmation, actual WebAuthn ceremony, stale 409 and lost-response read-only
  recovery are shared across editors. Canonical UZ/RU/TJ regenerated. V10 and
  four mobile tabs preserved; no polling or new dependency.
- Hardened newly fetched HSK30 settings: deterministic locks cover all four
  absent keys, raw timestamps participate in CAS, bounded strict read input,
  coherent read-only snapshot. Added real-PG two-admin first-write race case.
  Course policy read now uses the same strict body/coherent snapshot contract.
- Native retention piggybacks metadata deletion on its existing indexed
  expiry batch: remove corresponding Android triage state atomically, retain
  content-free audit. No recurring orphan-table scan or additional scheduler.
- Local broad gate: **497 passed, five Redis-only skipped**, including
  isolated PostgreSQL contention; **61 legacy financial/import passed**.
  Settings/prices/marketing ASGI+virtual-WebAuthn browser suite passed at
  1440/390 UZ/RU/TJ: real saves, creative delete, cancel, stale confirmation,
  lost response, revoked session, escaped stored text and strict CSP. Separate
  compact Inbox/menu suite passed; screenshots visually inspected. Python,
  JavaScript, catalogs and diff checks pass. CI includes both new browser and
  PG suites. Exact committed-head CI is checked after push.
- See [management contract](MANAGEMENT_COMMANDS_CONTRACT.md). Remaining code
  parity is recorded there; do not equate these implemented commands with
  unrestricted legacy admin endpoint access. External MCP stays statistics-only.

## Current continuation — inbox layout and live authority, 2026-10-25

- Fetched and fast-forwarded 37 GitHub commits through `cb806ad1`; pricing caps,
  daily private R2/Redis snapshots, feedback analytics UI, sanitized technical
  inbox and course-policy commands already existed. Do not rebuild them.
- Fixed technical inbox projection missing `source_type` (previously a 503 on
  untriaged technical events). Triage locks only source eligibility metadata,
  without reading Android attachment BLOBs or feedback bodies.
- Inbox accepts strict `status=all|new|read|assigned|resolved` and
  `period=all_time|weekly|monthly`; predicates apply before source limits and
  stable cross-source pagination. Source labels do not invent OS attribution.
- Push eligibility reads narrow metadata, cancels resolved Android/technical
  alerts before delivery, and rechecks current blocked/allowlisted admin state.
- Statistics JSON as well as files, and feedback JSON/files, recheck rollout
  and live session authority after Redis/R2 IO. Cache contents never authorize
  a request. No new aggregate refreshes or background scans were added.
- UI cleanup uses repository `hsk-ai-ui` and `webapp-testing`: one main triage
  action per entry, secondary action menu, lightweight media link, labeled
  filters and collapsed status/time controls; downloads, Push, MCP and account
  controls receive the same hierarchy. UZ/RU/TJ source catalogs stay canonical.
- Local verification: affected backend suites passed, including real isolated
  PostgreSQL setting contention; full existing Chromium ASGI/virtual-WebAuthn
  suite passed (auth, financial commands, downloads, images, offline and SW).
  Separate mobile/desktop menu/filter screenshots and keyboard checks cover
  the screenshot regression. Exact new commit/CI evidence follows after push.
- Scope remains this feature branch only. Three feature defaults stay OFF;
  external MCP remains statistics-only. Further typed management adapters are
  being completed; disabled management sections are not completion evidence.

## Current management increment — price revision and absent-key locks

- Integrated additional remote commits `efe29a79` / `0c10c27e` (HSK30 signed
  backend and localized editor), preserving the new compact Inbox/More layout.
- Added first-party signed nine-target subscription pricing adapter, strict
  integer amount/method/plan validation, raw-state CAS and existing shared
  currency/default behavior. No payment/entitlement changes. See
  [management contract](MANAGEMENT_COMMANDS_CONTRACT.md).
- Shared setting and price writers take deterministic PG transaction locks for
  absent as well as existing rows. Course policy rechecks expiry after that
  lock. Legacy HSK30 partial writes prelock their actual keys in sorted order.
- Local checks: **26 passed** across course/HSK30/pricing/shared feature/import
  and **four real PostgreSQL contention cases**; prior pricing-specific gate
  **35 passed**, including legacy card-bank and discount behavior. New PG cases
  cover legacy price first-row write vs signed PWA stale confirmation. CI now
  explicitly runs this PG file and the dedicated mobile menu/filter browser
  suite. No new DB migration is needed.

## Owner clarification — daily R2-backed aggregate snapshots, 2026-10-25

- User requires both Statistics and Feedback Analytics to **avoid aggregate DB queries at each page open**. The 30/min per-worker limit was not caching and does not fulfill that requirement by itself.
- Code now adds optional **private** Cloudflare R2 snapshot read/write (server-only S3V4, max 128 KiB) for both existing Statistics and new Feedback, keeping existing Redis lease/process cache as hot layer and one 24h rolling generation per requested variant. JSON/CSV feedback export reuses same feedback reader. Exact commits: `b4d0ec1a` R2 adapter/Stats; `6b9d8daf` Feedback reuse; `1d67d682` isolated fake-R2/no-network tests. R2 itself is **NOT active** until dedicated bucket/credentials and staging readiness exist. No production main/flags deployment.
- Never expose private R2 objects or access credentials to clients; authorization stays live per request. Updating the same category snapshot after 24h is demand-driven, not guaranteed by cron when no admin opens it. Release acceptance still needs real R2 integration and production-safe multi-worker behavior. See `READ_PROJECTIONS.md`.

## Current increment — bounded first-party feedback categories, 2026-10-25

- **Runtime commits:** `61d80109` (initial code), `47b98f17` (test-only authentication-vs-feedback SQL assertion), `0472f44f` (indexed native retention ordering), `a77b1168` (native SQL projection regression). Confirm full CI for the exact latest branch SHA before marking this verified; local/physical/staging were not executed here.
- New first-party, WebAuthn-admin-cookie-only `POST /api/admin/v1/feedback/categories` and `/api/admin/v1/feedback/categories/export` (JSON/CSV). Strict HTTPS/Origin/Fetch Metadata and bounded JSON; no bearer/MCP. Existing read-only PG transaction, no new migrations/tables, cache scans, scheduler, image loading or writes. Data kept exclusively in bounded memory.
- Source-bounded queries: per-source <=500 recent rows plus one sentinel, weekly/monthly only. Bot: only completed disliked codes from the existing fixed `DISLIKED_OPTIONS` list; unknown/missing codes become `unclassified`. Release: stored 1-2/3/4-5 star groups; invalid rating explicitly unclassified. Android: only retained, unexpired reports labelled `reported_issue` without guessing a complaint category from private description. Native row order uses the existing `expires_at` index and 30-day retention policy, not an unindexed `created_at` sort; window filter remains on created_at.
- Output includes per-source `records_scanned`, `truncated` boolean, exact date basis, time window and `historical_android_reports_complete=false`. Counts are **sampled recent source records, not whole-population totals** if truncated. Strict code-controlled category labels and output size <=128 KiB; raw user feedback text, IDs, Telegram metadata, campaign titles, media/file references, prompts and screenshots never selected or exported. Formula-like stored codes become `unclassified`. Tests check privacy, current WebAuthn/admin flags, CSRF, response bounds, truncation semantics, no DB writes, no raw fields and existing index. All external MCP scopes stay statistics-only.
- **Remaining:** V10 first-party feedback categories/export button and canonical UZ/RU/TJ copy + browser download and stale-response tests; separate technical-event sanitization/retention, remaining management, real staging/Apple/ChatGPT acceptance. No main merge or deploy.

## Verified continuation checkpoint — 2026-10-25

- **Last tested code commit:** `1175a5144d202a56f07a9ee5cc522aa9189d9f48` (`feat(admin-pwa): add audited access grants`), [Draft PR #201](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/201) remains OPEN / Draft, base `main`, mergeable and not merged. Remote code HEAD was this commit when checked. Do not infer that `main`, staging, production or live migrations changed.
- **All seven GitHub Actions workflow families SUCCESS at exact code HEAD:** [Admin PWA security 40113941873](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40113941873), [Backend 40113941822](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40113941822), [Android 40113941874](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40113941874), [Desktop 40113941823](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40113941823), [Localization 40113941846](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40113941846), [Voice 40113941890](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40113941890), [TTS 40113941827](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40113941827).
- Independently inspected Admin PWA job logs: **402 passed / 20 skipped** in primary Python suite, **61 legacy passed**, **63 generated UI catalog artifacts / 0 stale**, browser synthetic/virtual WebAuthn registration/login/payment and manual access grant (UZ/RU/TJ 1440/390 confirmation/cancellation, stale confirmation, lost-response no retry), plus 11 native API regressions passed. Isolated real PostgreSQL job: **20 passed**. The primary-suite skips are handled in separate service-dependent gates where applicable, not evidence of live external provider acceptance. PostgreSQL job also passed its 0126 DDL and nonempty downgrade checks. Runtime application code was **not changed** by this documentation checkpoint.
- Manual grant audit confirms dedicated `users.grant_access` action, frozen exact snapshot/one-use verified passkey receipt, target lock, canonical `users.id`, current admin/session/receipt rechecks, transactionally atomic grant/audit, paid-term extension, blocked-user guard and no Payment/revenue/AI budget mutation. No corresponding MCP mutation or external feedback exposure. **Nonblocking UX refinement:** confirmation currently displays current expiry + days, not a separately calculated *expected resulting expiry*. Add only with appropriate server-derived semantics and UZ/TJ/RU strings; never present a precommit estimate as guaranteed.
- **Next coding priority** (do not repeat implemented grant/export/media): implement separately scoped, PII-minimized **first-party feedback category analytics / sanitized bounded export** based on the existing canonical Bot/Release/Android tables, with explicit missing-category/identity semantics, source definitions, period filters, CSV formula hardening, 128 KiB-style bounded response, current WebAuthn authorization before returning private content, no automatic polling/new full-table scans, no external MCP scope expansion and actual tests. Inspect `app/admin_api/pwa_read.py`, `pwa_inbox.py`, `pwa_statistics_export.py`, current models and `docs/admin-pwa/READ_PROJECTIONS.md` before coding. Then review privacy-safe technical events/retention and remaining management commands as separate increments.
- **Acceptance still pending:** isolated HTTPS staging/OAuth/MCP ChatGPT real protocol and physical iPhone Home Screen/Mac Safari passkeys/Apple Push, reverse proxy and true production database migration/rollback procedures. All feature flags OFF; no merge, deploy or production data changes. The final-result checklist remains unmarked until its exact acceptance evidence exists.

## Current increment — manual Pro access command, 2026-10-25

- Owner now requests continuing until the full final-result contract is handled; do not stop at a single new increment while independent code work remains. Commit/push tested increments only to this feature branch. Existing no-main/no-deploy/default-OFF and statistics-only external MCP boundaries persist. Real staging/ChatGPT/physical-device evidence remains necessary, never simulated as complete.
- Previous docs-only head `6c4774c815915ef192174d31800f00f447b48050` has **all seven workflows SUCCESS**, including [Android 40109338512](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40109338512) and [PWA 40109338494](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40109338494). Runtime bytes match `c1d83d80`; earlier emulator failures below are historical, not a current baseline failure. Underlying transient device-loss cause was not established or patched. This does not prove new access-command CI success.
- `pwa_access_grants.py` adds first-party canonical manual grant prepare/execute, strict 1–36500 days, exact access-state/paid-active snapshot and one-use `users.grant_access` step-up. Target is locked only when executing; expiry/actor/flag rechecked after target wait, PG lock/statement limits 5/8 seconds. Calls existing `SubscriptionService.grant_manual_paid_access`; no payment/revenue/new AI budget/preview replenishment, blocked targets never implicitly unblocked. New 0126 immutable command evidence commits with proof/access or all roll back. Nonempty downgrade refuses destruction; QA initializer and scoped migration CI updated, no live schema change. See [contract](ACCESS_GRANTS_CONTRACT.md).
- V10 account drawer adds a days form, separate target/day/current-expiry confirmation, actual passkey ceremony and committed result. Cancel/stale response guards preserved; known 409 shows changed, lost response offers profile reread without resend. Repo hsk-ai-ui/webapp-testing read/applied; five canonical UZ/RU/TJ labels regenerated (63 artifacts, zero stale).
- Local broad Admin PWA/catalog/bootstrap with real disposable PG15: **400 passed / five Redis-only skipped**; **61 legacy passed**. Final grant + all real PG cases after transaction-limit patch: **28 passed** (eight grant, 20 PG). 0126 real DDL/rollback, concurrent proofs and lock-expiry tested in isolated UUID schemas. No production DB, credentials or provider used. Local server is dedicated `/tmp/hsk-admin-pwa-completion-20261025`, loopback port 55440, test DB `adminpwa_completion`; stop when no longer needed.
- Full browser virtual-WebAuthn/login/payment/export/grant/image/SW suite passed. New grant QA at 1440/390 UZ/RU/TJ verifies no write before confirmation/cancel, real signatures, stale snapshot rejection and lost committed response without retry. Initial selectors chose hidden desktop rows on mobile and then an underlying profile button too early; fixed test selectors to visible rows and the current drawer footer, without forced clicks or production guard changes. Screenshots `/tmp/hsk-admin-completion-browser-20261025`; Uzbek mobile confirmation visually inspected. Syntax/catalog/diff checks passed. New exact-SHA CI will be inspected after push.
- Continue next with sanitized first-party feedback analytics/files, privacy-safe technical events and retention, then remaining shared management adapters; keep current plan/final acceptance aligned and all real provider/device gates explicit.

## Current increment — daily statistics JSON/CSV, 2026-10-24

- `pwa_read.py` adds cookie-only `POST /api/admin/v1/statistics/export` with strict format/platform/period validation and existing HTTPS/Origin/Fetch Metadata/body guards. A current WebAuthn admin is required before and after cache IO; auth connections close while waiting. The same daily reader serves dashboard/MCP/export, without a new aggregate query on a warm cache. Cold/expired variants still refresh under the existing 24-hour contract. Small live auth reads remain; no new DB writes, schema, dependency, flag, R2 or background export job.
- `pwa_statistics_export.py` selects only allowlisted numeric/null aggregate paths, fixed metadata and shared metric definitions. Original UTC generation/expiry/range/source/scope retained; currencies separate, uppercase three-letter validated. Limits: 128 KiB / 96 metric rows / 32 currencies. Unknown nested fields omitted; identities, raw feedback/payment rows, contacts, prompts, references and credentials never exported. Invalid/nonfinite/expired/foreign snapshots fail closed. Telegram/iPhone unavailable remains explicit, desktop remains rolling 30 days, Android grains unchanged. JSON dictionary and CSV row definitions are usable without DB credentials.
- V10 Statistics uses two existing toolbar buttons, JSON/CSV, 44px and canonical UZ/RU/TJ labels. Repo hsk-ai-ui and webapp-testing skills read/applied for the file-download interaction missing from the visual demo. Explicit tap only; same-origin/no-store/no-redirect POST, 15-second deadline, streamed 128 KiB browser bound, one pending download, Blob cleanup and epoch/view/locale cancellation. Route/filter/locale/offline/pagehide/session changes discard stale files; 401 clears private UI. No preload, auto retry, private browser/SW cache or claimed filesystem-save success.
- Local verification: **372 passed / 22 service-dependent skipped** across Admin PWA/catalog/bootstrap suites (17 disposable PG, five real Redis unavailable locally); targeted read/cache/export/shell/catalog **46 passed / five Redis skipped**. New tests cover all 18 selectors, current cookie-only auth, CSRF/malformed/extra fields, separate currencies/formula rejection, PII canaries, numeric/size bounds, warm-cache SELECT-only/no repeated aggregates and revocation during cache wait. Initial test fixtures incorrectly expected an empty cohort and omitted required `plan_type`; corrected fixture/assertion, no production guard weakened.
- Full browser run passed actual virtual WebAuthn/payment regressions, real JSON/CSV downloads in UZ/RU/TJ at 1440/390, stable daily timestamp, definitions/PII omission, 44px controls/no overflow, error/type/oversize rejection, delayed route/locale/offline/pagehide cancellation, existing three-source images and public-only SW. Screenshots `/tmp/hsk-statistics-export-browser-20261024`; mobile Uzbek and desktop Russian visually inspected. Extra null/range/currency/size assertions: eight export tests passed. Legacy financial/import regressions: **61 passed**. Catalog builder: 63 artifacts / one written / zero stale; Python compile, JS syntax and diff/link checks passed. Local PG/Redis skips are explicit, not live-service evidence.
- **Verified export runtime `c1d83d800dd41666bd337e031563396b640386c7`:** [Admin PWA CI 40108141318](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40108141318), both jobs SUCCESS. Independently fetched logs confirm **394 scoped passed / 17 PG-only skipped, 61 legacy passed, 17 disposable PostgreSQL 16 passed, 11 native/API passed**, 63 catalogs / zero stale and full Linux browser/WebAuthn/export/image/SW checks. Backend, Desktop, Localization, Voice and TTS also SUCCESS at this SHA. **Six workflow families passed; Android remains FAILED, not all-green.**
- **Unresolved Android CI evidence:** [run 40108141280](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40108141280). First attempt lost emulator-5554 after 42/57 tests (empty failure in `RatingNavigationTest.pullingTheLeaderboardReloadsWithoutSendingAChallenge`, no assertion stack); logs/XML artifact inspected, no captured fatal app marker. Retried only failed job once on identical code; retry job `120915684885` lost the emulator after 46/57 tests during `RatingNavigationTest.bell_opens_the_challenge_inbox`. Both say device-not-found/incomplete run. The Android backend adapter job passed. Device loss is confirmed; underlying runner/emulator cause is not established and no blanket flaky-test or application-fix claim is made. No Android/Desktop/dependency/learner-bundle bytes changed from the previous verified runtime. Do not remove tests, loosen guards or repeatedly rerun. Investigate this separately before release acceptance. Later docs-only commits do not change the runtime SHA. Keep Draft PR #201, all feature defaults OFF and main unchanged. No live provider, ChatGPT, physical device, migration or deploy exercised.
- **Next:** inspect one remaining first-party management command and add exact WebAuthn-bound adapter/confirmation/audit tests before enabling it. Candidate source: legacy `main.py::admin_miniapp_user_give_access` already calls `SubscriptionService.grant_manual_paid_access`; preserve canonical target locks, existing paid-term extension and no payment/revenue/AI-budget creation. `pwa_step_up.py::_ACTIONS` does not yet allow access grants: a dedicated schema/action/audit contract is required, not a generic legacy-route bypass. Sanitized feedback exports, technical producers, triage retention/audit and unsupported media remain separately scoped; isolated staging/real ChatGPT/physical Apple acceptance remains open. Do not recreate the completed daily statistics export.

## Current increment — Bot/Release images with bounded server load, 2026-10-24

- **Verified runtime `bcecb6ab514bf1f9d27272f4d35fac309a1294d0`** (media foundation `fbd8868b` + sign-in readiness fix): [Admin PWA CI 40105600218](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40105600218), **both jobs SUCCESS**. Independently checked logs: **386 scoped passed / 17 PG-only skipped**, **61 legacy passed**, **17 real disposable PostgreSQL 16 passed**, **11 native/API regressions passed**, browser virtual-WebAuthn/login readiness + three-source image lifecycle + public-only SW and 63 catalogs/0 stale. All seven returned workflow families (PWA, Backend, Android, Desktop, Localization, Voice, TTS) are SUCCESS at this exact SHA. Later CI-record docs do not change runtime code. Main remains `891d9d9b`; no live provider/device/deploy/flags were exercised.
- First media head `fbd8868b` [CI 40104930873](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40104930873): **386 scoped passed / 17 PG-only skipped, 61 legacy passed, 17 real PG16 passed**; full workflow failed on the existing mobile login/logout browser scenario before new media checks. Cause: authenticated shell/More appeared while login still awaited its last unread-count response; `busy` silently ignored the early tap. Fix: More is disabled until sign-in completes. Regression deliberately holds that last real ASGI response, asserts disabled, releases it and verifies More/logout. Full local WebAuthn/browser/images/SW rerun passed. No extra server requests, auth bypass, timeout increase or forced click. The follow-up is verified at `bcecb6ab` above; do not relabel the original `fbd8868b` run fully green.
- Extends `pwa_inbox_attachments.py` with first-party Bot/Release image GETs; reuses the existing Bot client / bounded receipt-image loader. Current WebAuthn admin + canonical source owner + exact file/type/source binding are verified before and after provider IO. Orphans, bearer-only credentials, unknown sources, unsupported media, replaced/rebound/deleted sources and revoked sessions fail closed. Native retained JPEG semantics stay intact. No Telegram path/reference/token or image bytes enter inbox lists, logs or external MCP.
- Owner clarified that server/DB load should stay low. Only explicit admin taps load media; source-ID queries select metadata only, and DB sessions close before network IO. Two simultaneous loads, 30 attempts/minute and a 10-second provider deadline **per worker**, implemented with constant-sized memory and no new quota DB writes. No preload, polling, automatic retry, media cache, backfill, new scheduler or R2 upload. Existing 24-hour aggregate snapshots remain unchanged; live auth/ownership checks are preserved.
- `pwa_inbox.py` adds a boolean image-candidate hint in its existing bounded SELECTs. `app.js` reuses V10 inline preview, current UZ/RU/TJ labels, source+ID DOM/path identity and object-URL cleanup. Android: JPEG/550 KiB; Bot/Release: verified JPEG/PNG/WebP, 8 MiB/20 MP. Other formats remain unavailable. Repo hsk-ai-ui / webapp-testing skills were read/applied; no new UI copy, schema, flag, runtime dependency or business-rule change.
- Local full Admin PWA + catalogs + guarded bootstrap: **364 passed / 22 skipped** (17 disposable PostgreSQL, five real-Redis cases unavailable locally). Browser virtual-WebAuthn/payment/SW and extended actual-ASGI image lifecycle passed: native JPEG, Bot WebP, Release PNG through actual image decoding with only Bot transport mocked, 1440/390 UZ/RU/TJ, equal IDs, retention/revocation and stale-response cleanup. Builder: 63 artifacts / 0 written / 0 stale. No live Telegram/provider/DB/device was used. Screenshots `/tmp/hsk-feedback-images-browser-20261024`; mobile Bot WebP and desktop Release PNG visually inspected. New unit-test class placement and async assertion errors were corrected before the passing run, without changing production guards.
- **Next safe low-load increment:** bounded sanitized statistics JSON/CSV from the existing daily reader, preserving source timestamps and avoiding new aggregate SQL. Technical producers (never raw Mini App diagnostic stacks/URLs), triage retention/audit, unsupported media and management remain separately scoped. All Admin PWA/MCP/Push rollout defaults stay OFF; no main push/merge, deploy, secrets or live migration. Verify the new exact SHA's CI before claiming its success.

## Current increment — Android JPEG preview in V10, 2026-10-24

- **Verified runtime:** `ff8c6df8746a41e6763299bd0f66a71c27174153`, [Admin PWA CI 40102251694](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40102251694), **both jobs SUCCESS**. Logs independently confirm **372 passed / 17 PG-only skipped**, **61 legacy passed**, **17 real disposable PostgreSQL 16 passed**, **11 native/API regressions passed**, 63 catalogs / 0 stale and browser virtual-WebAuthn + Android preview lifecycle + public-only SW checks. Desktop, Localization, Voice and TTS also passed for that SHA; Backend/Android were still running when checked. Later docs-only commits do not change this runtime evidence. No real provider/proxy/device/ChatGPT acceptance is implied.
- GitHub updates through `9a8f906b` were integrated without history rewrite. Guide synchronization commit `44a96a67` and concurrent-doc merge `19fd8c70` were pushed to the feature branch. Main remains `891d9d9b`.
- `app/static/admin-pwa/app.js` / `styles.css`: explicit inline Android-only preview using the existing private JPEG endpoint. Fixed route, cookie/no-store fetch, no redirects, 15-second abort, bounded JPEG, current server auth/retention, 401 clears private UI. One preview at a time; close, source/page/locale navigation, offline/pagehide and session invalidation abort/revoke object URLs. Generation checks prevent late responses entering a new drawer. No private browser/SW cache or new MCP capability.
- Canonical UZ/RU/TJ image toggle/alt labels and generated `catalog.js`; V10 layout and 44px actions preserved. Actual repo hsk-ai-ui / webapp-testing skills were read/applied for the new inline preview pattern. No runtime dependency, schema, config/flag, legacy admin or payment/access logic change.
- Local targeted API/inbox/triage/shell regressions: **31 passed**; catalog regressions: **7 passed**. Builder `--write`: 63 artifacts / one updated; `--check`: 63 / 0 stale. Browser virtual-WebAuthn/payment regressions, new real-ASGI Android preview lifecycle and public-only SW suite passed. Screenshots: `/tmp/hsk-inbox-preview-browser-20261024`, desktop/mobile UZ/RU/TJ; mobile Uzbek and desktop Russian preview screenshots visually inspected. Initial new-fixture omissions (required Telegram ID and intercepted Fetch Metadata expectation) were corrected before passing, without weakening production guards. No new PostgreSQL DDL or real provider/device test was needed/performed for this frontend increment.
- **Next:** reviewed Bot/Release media ownership/type/size proxy; privacy-safe technical event intake (never raw Mini App diagnostic stacks/URLs), triage retention/audit follow-ups, remaining first-party management and bounded exports. Staging/real ChatGPT and physical Apple delivery remain separate approval/configuration gates. All feature defaults remain OFF. Check the new exact commit's CI before any head-specific green claim.

## Current continuation and guide synchronization — 2026-10-24

Fetched runtime `d93b75fe468c217dee66e2c4fe277ccfeabadb4f` by fast-forward,
preserving local documentation edits. Inbox read/triage/search, Apple Push
sender code and retained Android JPEG proxy already exist; do not rebuild them.
Android preview is now connected in V10. Next separately review other media and
privacy-safe technical producers, remaining management/exports and approved
staging/device/real ChatGPT gates. All rollout defaults remain OFF.

Guides now route through this handoff; PR #200 resume/merge preparation and
original phase checkpoints are historical. [READ_PROJECTIONS.md](READ_PROJECTIONS.md)
is the detailed daily-cache contract: rolling 24 hours on authorized demand,
private existing Redis, per-worker outage fallback, live auth/audit/quotas and
billing/access, HTTP/SW no-store, no R2. Docs-only changes were checked for
Markdown links and whitespace; no runtime tests are attributed to that edit.

## VERIFIED private Android attachment route — 2026-10-24

- **Last code HEAD:** `d93b75fe468c217dee66e2c4fe277ccfeabadb4f`. [Admin PWA workflow 40101181445](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40101181445): **both jobs SUCCESS**; 372 Python passed / 17 PostgreSQL-specific skipped, 61 legacy passed, 17 disposable PostgreSQL passed, 63 generated UI artifacts / 0 stale; synthetic mobile/desktop virtual-WebAuthn browser and Android API regressions passed. No production DB, TLS/provider or physical device exercised.
- `a4ae3660` added the first **server-only Android JPEG attachment proxy** with a current canonical WebAuthn admin session, secure same-origin GET and nonexpired private retained source check, bounded/verified JPEG, read-only SQL and no-store/no-sniff response. It does not expose DB bytes through the Inbox list or MCP, and there is no UI button yet. Bot/Release Telegram media access remains unimplemented.
- The initial build uncovered an actual flag-OFF route privacy regression: FastAPI converted `{report_id}` to integer *before* the guard, causing 422 instead of 404 while disabled. `63fd4723` changed ID parsing to occur **after** the rollout gate; `d93b75fe` added malformed placeholder and enabled/disabled regression assertions. Fixed head CI green; no legacy Telegram/admin auth changes.
- Next scoped work: safe approved UI attachment view with canonical UZ/RU/TJ + browser tests, then reviewed Bot/Release attachment source validation. Keep raw Mini App stack/URL diagnostics excluded until independent redacted producer and retention schema are designed. Production/main/flags are untouched.

## PRIVATE NATIVE INBOX ATTACHMENT PROXY — 2026-10-24

- **New branch-only scoped increment:** `app/admin_api/pwa_inbox_attachments.py` serves only valid, retained Android JPEG attachment bytes via `GET /api/admin/v1/inbox/android/{id}/attachment`. It requires canonical HTTPS admin origin, active allowlisted WebAuthn Admin PWA session, same-origin Fetch Metadata, exact bounded DB record ID, valid nonexpired row and a structurally verified JPEG up to the existing 550 KiB intake limit. No Telegram file ID, path, student text or attachment metadata is reflected. Responses are private no-store with nosniff; SQL is READ ONLY. Missing/expired/corrupt files fail closed.
- Router is mounted in `app/main.py` behind the existing Admin PWA flag. Regression `tests/test_admin_pwa_inbox_attachments.py` covers valid bytes and privacy; no session/forged cookie, Google-only auth, blocked admin, cross-site/foreign origin, query tampering, missing/expired/corrupt records, disabled rollout. **No UI attachment action, Bot/Release Telegram media loader, real-device staging or MCP exposure is part of this increment.** This line describes authored scope; refer to CI at the new exact SHA before claiming verified.

## VERIFIED BOUNDED UNIVERSAL INBOX SEARCH — 2026-10-24

- **Latest CI-verified implementation HEAD:** `15eeea3fc91d1d0d419165eba8d73b25ad5bfe82`, [Admin PWA Actions run 40100198739](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40100198739), **both jobs SUCCESS**. 368 Python passed / 17 PG-only skipped, 61 legacy passed, 17 disposable PostgreSQL 16 passed; 63 localized artifacts / 0 stale and actual headless Chromium virtual WebAuthn/mobile/desktop/Service Worker tests passed. No real device/proxy/production test was run. Other GitHub workflows are independent.
- `app/admin_api/pwa_inbox.py` now supports **optional 3–80-char sanitized search**, case-insensitive substring against the already-displayed Bot, Release and retained Android report text, with literal SQL percent/underscore escape and a **30-day** search horizon; pending screenshot payment searches use **only exact numeric payment ID**. Existing source, priority, canonical user, keyset limits and private no-store WebAuthn session guards remain. Without search, older Inbox browsing remains unchanged. Query never touches Mini App diagnostic stack or receipt/bank data.
- `app/static/admin-pwa/app.js` and `styles.css`: compact search form in the existing V10 notifications drawer, preserved source/important/account filters and pagination, 390px layout, escaped value and actor-bound request. Clears on session invalidation, stores no search in localStorage or SW. Reused existing canonical UZ/RU/TJ `find` and `monthly` keys; **no new generated UI catalog edits**. Unit and Playwright regressions were extended.
- Commits: backend `8024e46a`, responsive UI `3abe4aa7`, test quotation fix `790ac83e`, actual-row-count E2E correction `15eeea3f`. Earlier browser E2E failed on an incorrect assumption that clearing search should restore 1 row; fixture had 2 unfiltered canonical account rows. Fixed to capture/restore the true baseline and rerun to green. This was a test defect, not a PWA query failure.
- `docs/admin-pwa/TECHNICAL_ERROR_SOURCE_AUDIT.md` records verified source/privacy boundaries. **Do not turn Mini App `Message(content_type='app_error_context')` stack/URL/freeform content into admin alerts**, Apple Push or MCP without a separately designed, rate-limited, redacted event schema and trusted producer integration. Current Android durable bug intake and payment important alerts remain the only source-backed automatic important events.
- **Next tasks:** audited system/Mini App technical event intake with explicit safe fields and retention; attachment proxy requiring live authorized admin checks; remaining first-party course/access/marketing commands and bounded JSON/CSV exports; real isolated ChatGPT/MCP, Google/Bot, Apple iPhone/Mac staging QA. Keep all Admin PWA/MCP/Push rollout flags default OFF. No `main` merge, live migration, credentials or provider delivery test in this work increment.

## VERIFIED Apple sender integration + PWA status fix — 2026-10-24

- Latest **code** commit: `108a8a994aa39b8fd5eb88922f5835c6a51a2c9e`. [Admin PWA CI run 40098811486](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40098811486) **BOTH jobs SUCCESS**: 366 Python passed / 17 skipped in that job; 17 disposable PostgreSQL passed; 61 legacy passed; 63 generated UI catalogs / 0 stale; virtual WebAuthn, mobile/desktop browser and 11 native/report regressions passed. Wider Android/Backend workflows are separate checks.
- `4d6cf0b8`: `app/static/admin-pwa/app.js` stops displaying the old canonical `pushNotSending` warning when the authenticated Push API reports `sending_enabled=true`; when sender config is OFF, the existing warning remains. No new UI copy or catalog edit. `tests/test_admin_pwa_shell.py` guards this rendering contract. The existing shell-content-derived SW hash automatically changes with `app.js`.
- `94e9887a` + `108a8a99`: offline integration test exercises the **real pinned pywebpush encryption + VAPID signing code**, intercepting only the final `requests.post` boundary. First run failed because test fixture omitted fake Response `text`/`headers`; fixture fixed, latest CI green. This is **not** Apple push-service acceptance or a physical notification.
- Existing outbox, sender, conditional in-app scheduler and native report retention remain default OFF via independent feature flags. No production/staging secrets, real provider network, live device, migration, deployment or main merge was performed in this work increment.
- **Next implementation priority:** inventory source-backed technical error/system alert producers and integrate only verified, rate-limited, privacy-safe important events; then secure screenshot/feedback attachment access and Inbox search. Separately, expand first-party management and sanitized JSON/CSV export under their own security tests. Staging and physical iPhone/Mac remain owner-authorized acceptance gates. No AI write/MCP-feedback exposure has been added.

## CURRENT sender/retention continuation — 2026-10-24

- **Branch verified prior to this incremental UI/doc/test patch:** `171fc3efdc5d2109d6ef542c7441489f72509f14` on `feat/admin-pwa-mcp-readonly-20261024`, Draft PR #201 (not merged). [Admin PWA CI 40096641518](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40096641518) for that baseline: two jobs successful, **364 Python passed / 17 PG-only skipped**, **17 disposable PG passed**, 61 legacy, 63 localization artifacts/0 stale and browser virtual WebAuthn checks passed. This is not an Apple-provider or real-device test.
- **Later source supersedes the stale "NO sender" statements below:** `app/services/admin_pwa_push_dispatch.py` and `scripts/admin_pwa_push_dispatch.py` implement a default-OFF VAPID-signed, encrypted, leased/retry Apple Push sender; `app/main.py` conditionally schedules it only when all flags, trusted origin and secrets validate (`d8125beb`). `171fc3ef` adds hourly bounded private native-report retention cleanup under the PWA flag. CI exercised mocked provider and disposable DB only.
- **UI follow-up:** the Push drawer must use the actual `push/list.sending_enabled` response instead of always showing the canonical `pushNotSending` warning. Preserve explicit per-device opt-in, and do not claim device delivery from readiness. A public-shell regression assertion guards this; new UI copy was unnecessary, so canonical/generated UZ/RU/TJ catalogs remain untouched.
- **Still missing:** first-party system/Mini App technical-error producers, authenticated attachment viewing and inbox search; non-payment management adapters; bounded sanitized JSON/CSV, broader authorized feedback analytics, approved ChatGPT/real MCP network integration, isolated staging and physical iPhone Home Screen/Mac Safari delivery. No flag enablement, production credentials, real Apple provider requests, production migration or main merge. Earlier dated checkpoints below are historical, not current code status.

## VERIFIED DEFAULT-IMPORTANT PAYMENT & ERROR ALERTS — 2026-10-24

- Owner's default: **new pending payment receipt with uploaded screenshot** and **new durable Android bug report** are **important by default**. Ordinary Bot/Release feedback stays normal, unless manually marked important. Server/Mini App error producers remain **unintegrated**; do not promise alerts for them yet.
- **CI-verified implementation head:** `e4e5868a1c7409dcd9a9d55f23e09d5ada00f4e3`, [Admin PWA CI 40095348846](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40095348846), BOTH jobs SUCCESS: **341 Python passed / 17 PG-only skipped**, **17 disposable PostgreSQL passed**, **61 legacy passed**, **63 catalog artifacts / 0 stale** and synthetic iPhone-width + desktop WebAuthn Chromium tests passed.
- `alembic/versions/0125_admin_pwa_push_outbox.py` + `app/db/models/admin_pwa_push_outbox.py`: content-free, per-device, immutable dedup-event outbox with retry/lease fields and guarded non-empty downgrade. Migration 0123 Inbox triage and 0125 outbox allow the `payment` source. Tested only in disposable PG; no live migration.
- `app/admin_api/pwa_push_outbox.py`: new payment receipts and Android errors queue only for actively opted-in iPhone/Mac subscriptions of allowlisted canonical admins, one event per source ID / subscription, no private student/receipt/message/push endpoint/key in the outbox. Manual mark-important still enqueues voluntary flagged feedback separately. Duplicate receipt reattachments are idempotent.
- `app/services/payment_service.py` hooks pending-with-screenshot creation/attachment; `app/services/admin_pwa_native_reports.py` hooks newly stored private Android bugs. Both optional push queue operations are isolated with savepoints and sanitized exception handling to avoid blocking checkout/intake. Both `ADMIN_PWA_ENABLED` and `ADMIN_PWA_PUSH_ENABLED` default OFF and must be enabled for enqueue.
- V10 `inbox/list` now has four sources: Bot/Release/Android/**payment**. Payment rows must be pending with a real screenshot ID, default important, with generic/empty body (no amount, receipt or personal data); Android reports also default important. Filters and unread count include them. Payment Inbox offers mark-read and navigation to Payments, **not approve/reject**; prior WebAuthn payment review remains authoritative. Generated UZ/RU/TJ payment receipt label.
- Tested: two separately enrolled Apple devices, revoked-device exclusion, dedup, optional-push DB failure not blocking payment, four-source Inbox, default-priority filtering, unread-count and browser. New regression tests included in the 341-pass suite.
- **Still NO sender / live APNs delivery**; `sending_enabled=false`. Next tasks: VAPID-signed payload encryption, rate-limited and leased delivery worker, 404/410 stale auto-revoke, retries without duplicate storm, privacy-safe copy, real approved HTTPS staging and iPhone/Mac physical tests. Further technical error sources must be audited and connected. No actual flags, production, secrets, or main merge.

## VERIFIED APPLE WEB PUSH GESTURE + SERVICE WORKER INCREMENT — 2026-10-24

- **Exact latest CI-verified code SHA:** `bcbb04d63e98c1f4754a3580f8bd7583360e40b3`, [Admin PWA workflow 40093608662](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40093608662): **both jobs SUCCESS**, **332 Python passed, 17 PostgreSQL-only skipped**, **61 affected legacy tests passed**, **17 real disposable PostgreSQL tests passed**, 63 localized artifacts / 0 stale; Chromium synthetic login / Apple iPhone-width responsive inbox / cross-page tests green. This proves code/API QA only, **not physical Apple Web Push delivery**. Other workflows have independent results.
- New `app/static/admin-pwa/sw.js` reacts to a push by **always** showing a generic visible notification. It ignores any push payload / user text / payment metadata. Notification click opens only a fixed first-party `/admin/?inbox=1` URL and never uses an externally supplied redirect. `app/static/admin-pwa/app.js` recognizes that exact query only after a valid admin cookie + current session, so private Inbox never opens without login.
- Safari/iPhone reliability fix: `pushSettings()` prepares an active Service Worker and the server-published **public** VAPID application key before the user presses Enable; `enablePush()` then invokes `PushManager.subscribe({userVisibleOnly:true,...})` synchronously from that click, with no preceding `await`, `fetch`, or deferred permission prompt. Concurrent taps are serialized; failing new subscriptions are locally cleaned up only if no pre-existing device subscription existed. Existing owner WebAuthn/session/CSRF and default-off config still gate server registration. Tested by `tests/test_admin_pwa_shell.py` plus browser mock/real ASGI suite; **real Safari tests pending**.
- `tests/e2e/admin_pwa_browser.py` verifies fixed notification deep link after WebAuthn session. `tests/test_admin_pwa_shell.py` scopes the no-untrusted-push-data assertion strictly to the `push` handler; existing safe `message` handler may use `event.data` for public shell version update. `tests/test_admin_pwa_sessions.py` now asserts the explicit `push_available=false` extension to the minimal identity response.
- Still **NO push sender or live APNs delivery**; `sending_enabled=false`, `ADMIN_PWA_PUSH_ENABLED=false`, VAPID/storage secrets empty by default; no production deployment, no actual device subscriptions, no live schema migrations, no external ChatGPT MCP changes, no main merge.
- Next development increment: guarded event-driven **new important inbox/system alert** producer, durable deduplicated delivery outbox, mock-tested encrypted Web Push payload + VAPID private signing, per-device throttling and 404/410 auto-revoke. Then operator-approved isolated HTTPS staging and physical iPhone Home Screen + Mac Safari/Dock verification. Avoid sending push from every read/triage update or polling historical source records.


## APPLE PUSH SUBSCRIPTIONS + INBOX BADGE — 2026-10-24

- **Verified unread + important filter code:** `5fae57d41673fcee7dc86a6f3ab8165ec4232a16`, [CI 40092001022](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40092001022): BOTH Admin PWA/PG jobs green, **327 Python passed, 17 PG-specific skipped, 61 legacy passed, 17 real PostgreSQL passed, 63 catalog artifacts/0 stale, synthetic WebAuthn browser with 390px iPhone UI passed**. `inbox/list.priority=important` is applied in the source SQL queries, `inbox/unread-count` counts at most 100 source IDs (capped 99+), not first-page rows; expired Android excluded. Bell count refresh on authenticated boot and after triage; NO periodic background DB scan.
- **New Apple subscription foundation (test latest HEAD before declaring green):** `alembic/versions/0124_admin_pwa_push_subscriptions.py`, `app/db/models/admin_pwa_push.py`, `app/admin_api/pwa_push.py`, `tests/test_admin_pwa_push.py`. Per canonical allowlisted WebAuthn admin and per-install iPhone/Mac encrypted endpoint/keys (Fernet), endpoint hash uniqueness, max four active devices, strict Apple `*.push.apple.com` HTTPS host validation, same-origin/CSRF and revoke. Staging HTTPS origin validation fixed. Per-device registration/list/revoke API; plaintext endpoint/secret keys never returned. Separate flag `ADMIN_PWA_PUSH_ENABLED=false`, blank `ADMIN_PWA_PUSH_VAPID_PUBLIC_KEY` and `ADMIN_PWA_PUSH_STORAGE_KEY` by default.
- Current owner scope: **iPhone Home Screen PWA and Mac Safari/Add to Dock** only for Admin PWA. First-party UI includes explicit gesture-driven Apple permission and subscription management (not enabled without flag); localized UZ/RU/TJ, supports independent iPhone/Mac subscriptions. Public Service Worker has a visible generic, private-data-free Web Push handler and fixed `/admin/?inbox=1` click navigation; new login guard is required before showing inbox.
- **NO real delivery yet:** `sending_enabled=false` remains explicit. Push service sender/VAPID private signing, outbox/idempotent retry, Apple network access and physical Apple device testing, privacy/retention review and production rollout are still undone. The browser UI is NOT evidence that APNs accepts live sends. No staging deploy, live migration, secrets, flag activation, or main merge. External MCP remains stats-only.
- Migration chain head advanced to `0124_admin_pwa_push_subscriptions`, with guarded standalone QA bootstrap, workflow and disposable PostgreSQL DDL test updates. `docs/admin-pwa/APPLE_PUSH_ACCEPTANCE.md` lists the exact remaining acceptance gates. Verify current remote branch and latest CI after docs commits; documentation-only changes can cancel old concurrent workflow runs.
- Next: complete sender/outbox and server-triggered important-inbox dispatch with privacy-safe generic copy, provider status/expiry behavior, per-device enable/disable UX, then isolated HTTPS staging and **real iPhone+Mac** tests. Do NOT claim owner device notifications work before physical Apple provider E2E.

## VERIFIED APPLE-PRIORITIZED INBOX TRIAGE UI — 2026-10-24

- **Last CI-verified code SHA:** `a2ea94d6d9d95b0fa0159dcaee6f54574dab9ed8`; [Admin PWA run 40091110808](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40091110808): both jobs green, 325 Python passed (17 skipped PostgreSQL-only), 61 legacy passed, 17 disposable PostgreSQL 16 passed, 63 localization artifacts / 0 stale; browser virtual WebAuthn / V10 source & triage taps / 390px 44px touch target passed. Other workflow families may still be running.
- `app/static/admin-pwa/app.js` now renders each item with server-derived read/assigned/resolved and important/normal state plus context-specific first-party triage buttons; compares `expected_revision`, reloads after success/409, disables controls during mutation, never fabricates success on an unknown response. New `styles.css` targets iPhone 390px touch controls and Mac desktop. `tests/e2e/admin_pwa_browser.py` clicks the real POST endpoint and awaits durable audit + re-render (first early test failed due to clicking twice before API completion; fixed without weakening backend checks). Synthetic screenshot `mobile-inbox-triage.png` is collected in CI.
- New triage labels are canonical in `localization/ui/{uz,ru,tj}/miniapp.json`; regenerated `app/static/admin-pwa/catalog.js` matches the existing catalog builder. No learner bundle copy changed; `scripts/i18n_build_all_catalogs.py --check` green.
- **Owner priority:** Apple **iPhone + Mac**, not Windows/Android Admin PWA. Important distinction: the current Inbox receives/manages stored feedback; **Web Push to the owner's iPhone/Mac is NOT implemented**. The staged security/device acceptance checklist is `docs/admin-pwa/APPLE_PUSH_ACCEPTANCE.md`. This new capability needs per-device VAPID subscriptions, server push/outbox, explicit installed-iPhone/ Mac consent and real physical device QA. No notification permission prompt, push subscription storage, production keys or live delivery was enabled.
- Next scoped work: source-backed unread count + filters/severity search + system/admin event inventory, then secure attachment proxy and opt-in Apple Web Push. Keep all three rollout flags default OFF and external MCP statistics-only, no main merge/deploy.

## VERIFIED INBOX TRIAGE BACKEND INCREMENT — 2026-10-24

- **CI-tested implementation head:** `838026d9a5ea33695d29a2b3be613d153eec642b`. [Admin PWA CI 40089654035](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40089654035): BOTH jobs green; **325 Python passed / 17 PostgreSQL-only skipped**, **17 real PostgreSQL 16** tests green, 61 affected legacy regressions green, 63 catalogs / 0 stale, desktop/mobile virtual-WebAuthn/Service Worker browser regression green. This is synthetic CI, **not** a production or physical-device test.
- `alembic/versions/0123_admin_pwa_inbox_triage.py` introduces `admin_pwa_inbox_triage` (composite per-source identity, status, priority, optional canonical assignee, read/resolved timestamps, CAS revision) and `admin_pwa_inbox_triage_audit` (append-only operation/actor/time, without message/file/Telegram identifiers). Downgrade rejects nonempty state/audit; separate live migrations were NOT run.
- `app/admin_api/pwa_inbox_triage.py` mounts first-party **POST `/api/admin/v1/inbox/triage`**. Exact Origin/CSRF, strict JSON schema, current WebAuthn Admin PWA session, current ADMIN_IDS, source existence and Android expiry guards; source-row locks, expected revision, atomic state+audit commit. Allowed operations: mark_read, assign_self, resolve, reopen, mark_important, clear_important. Cannot assign arbitrary users or alter source feedback, payouts, access or broadcasts. Stale revisions -> 409, invalid source -> 403. No external MCP write tool.
- `app/admin_api/pwa_inbox.py` joins the persisted triage state onto the existing bounded read projection. Missing triage defaults to new/normal/revision 0; return `triage_available=true`, revision, priority, timestamps and canonical assigned admin ID. The existing V10 inbox **still only renders source filtering/read-only rows**: triage action controls, unread badge, advanced filters and UZ/RU/TJ labels are NOT yet implemented.
- `tests/test_admin_pwa_inbox_triage.py` proves all three source types, state transitions/audit, idempotent no-op, CAS/stale rejection, cookie/origin/flag expiry guards, no arbitrary assignee and denied non-passkey admin cookie. Updated guarded empty-QA bootstrap, model registry, isolated migration workflow and real disposable 0103–0123 DDL rehearsal.
- Important release follow-ups: triage audit/metadata retention and cleanup for removed/expired sources; update V10 UI with canonical UZ/RU/TJ via real catalog builder; secure attachment proxy; system/admin notices and alert severity; private inbox search/filters. Before staging, monitor cache/DB impact and retention. Existing `ADMIN_PWA_ENABLED` and both MCP feature defaults remain false; no staging/production deployment or main push/merge.

## VERIFIED FIRST UNIVERSAL INBOX INCREMENT — 2026-10-24

- **Exact CI-tested head:** `42e6a7b7bf6edde0ac53d4fe9fc3542c591697bf`. [Admin PWA run 40088791629](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40088791629): BOTH jobs success; **322 Python tests passed / 17 PostgreSQL-only skipped**, affected legacy 61 passed, **17 real disposable PostgreSQL 16** tests passed, 63 localization artifacts / 0 stale, desktop/mobile virtual-WebAuthn and Service Worker/browser 11 passed. Other workflows at the exact head must be checked independently. Do not present these tests as live staging/production evidence.
- `app/admin_api/pwa_inbox.py`: an explicitly bounded read-only unified service for BotFeedback, ReleaseFeedbackResponse and *retained* AdminPwaNativeReport, capped messages, no Telegram IDs or screenshot/attachment bytes. Per-source query limit+1 and stable cross-source UTC timestamp/source/id cursor, canonical-only account filter, expired Android exclusion. All sources and owner constraints checked by tests. Old single-source `feedback/list` preserved unchanged for compatibility.
- `app/admin_api/pwa_read.py`: added cookie-only, strict same-origin+CSRF-guarded POST `/api/admin/v1/inbox/list`, reuses normal admin authorization and PostgreSQL READ ONLY transaction; no MCP tools or schema change.
- `app/static/admin-pwa/app.js`: existing V10 Notifications bell now opens chronological `all` by default; Bot / Release / Android filter tabs, persisted canonical-user filter and cursor-backed next button. Reuses the already localized labels; no new static copy, generated catalog or layout redesign. `tests/e2e/admin_pwa_browser.py` exercises tabs in headless Chromium.
- `tests/test_admin_pwa_read.py`: synthetic mixed-source same-timestamp page ordering, orphan identity, expired native removal, no byte/file/Telegram ID leakage, strict ISO timezone-aware cursor validation, tampering/other origin, no cookie, revocation, flag OFF, only SELECT statements and route mounting. Initial CI caught strict-string cursor parsing 400; fixed it and reran to green.
- **Not finished:** durable triage read/assigned/resolved and audit; indexed filters/severity/search; secured screenshot/Telegram attachment proxy; admin/system alerts; visually localized historical gap notice; retained Android reports are not reconstructable from pre-intake Telegram-only notifications. No real deployment, main merge, flags, new secrets, schema or production operations.
- Next focused step: design and implement server-authoritative Inbox event/triage model and authenticated status updates under current PWA security rules. Keep external MCP statistics-only, and keep legacy Telegram/Android behavior untouched. Review native report retention setup before staging.


## Repository and boundaries

- Repository: `akbarholturaev11-lang/HSK-AI-Bot`; ONLY work branch `feat/admin-pwa-mcp-readonly-20261024`; [Draft PR #201](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/201), open and unmerged.
- MCP transport foundation changes: `e0270fb91d0c7e24c629d600964a09eb9816be9e`; integrated with concurrent documentation-only updates at `5ef02f1fc1716be8e9026f02aa41e6d312780e8c`. No history rewrite. Official SDK regression/QA dependency pin: `4009e903bb9ddbdbe7361280e229d4997903988b`. Later documentation commits advance HEAD without changing runtime code.
- Remote `main` verified unchanged at `891d9d9b6ffda5fba114d9c5c169eeb2f8a7836f` after the feature push. PR #200 is already merged; do not repeat its foundation work.
- Keep `ADMIN_PWA_ENABLED=false`, `ADMIN_PWA_MCP_ENABLED=false`, `ADMIN_PWA_MCP_TRANSPORT_ENABLED=false`. Resource/client/callback/public-origin defaults remain empty. Defaults do not prove production environment values.
- No main merge/push, production/staging deployment, live migration, secret configuration, flag activation or real external ChatGPT linking is authorized by this checkpoint.
- External MCP exposes ONLY `hskai_statistics` / `admin:analytics:read`. Users, feedback, payment, delete, broadcast, arbitrary SQL/URL and other write tools stay excluded.

## Daily statistics policy — implemented at `4709c660`, 2026-10-24

The owner clarified that minimizing unnecessary DB work is the purpose, then
selected once-per-day updates. Implemented in `pwa_statistics_cache.py`: private
24-hour on-demand aggregate snapshots, shared across browser/MCP through one
reader in `app/main.py`. It reuses the already pinned Redis 6.4.0 dependency and
`REDIS_URL`; no R2 integration, new dependency/flag/schema or live configuration.
Only requested expired variants refresh. Auth transactions close before cache
IO/waits, and cached hits still revalidate the current session/token/admin and
MCP audit/quotas. Current user/billing/access/review commands remain uncached.

`READ_PROJECTIONS.md` specifies the temporal contract, scope/version keys,
bounded JSON, 45-second shared refresh lease, fencing, eight-second load limit,
failure cooldown and explicitly weaker per-worker daily fallback during Redis
outage. Existing V10 generated_at display shows actual data age. HTTP and SW
no-store/privacy constraints are unchanged. Relevant rules, target, plan,
browser/MCP contracts were reconciled with the owner's daily-update decision.

Local verification: **380 passed, 17 PG-only skipped** in the broad Admin PWA/
catalog/bootstrap plus affected legacy payment/access/import suite. After final
warm-CSRF/timeout additions: **14 cache tests passed**, including five tests on
an actual temporary Redis **7.4.0** server (URL/client path, cross-worker reuse,
serialization across variants, failed refresh lease and old-owner fencing).
SQLite HTTP/MCP tests demonstrate warm responses still deny revoked/expired
OAuth and blocked admins, release the auth DB session before cache work, and
keep current billing/access reads live. Twenty simultaneous same-key requests
invoke one loader. No performance claim about production is implied.

Existing virtual-WebAuthn/browser/PWA/SW suite passed with the new daily reader;
screenshots `/tmp/hsk-daily-cache-browser-20261024`. No UI/copy/layout change or
new physical-device/staging evidence. CI now provisions an isolated Redis 7
service for the real shared-cache tests. Check the new commit's own CI result
before claiming head-specific success.

Previous native-intake head `5304cb7ae687f2db0f38891c1da8e73cb9fd015d`: all seven
returned workflows, including [Admin PWA 40085415751](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40085415751),
Backend and Android, were independently verified green before this increment.
Next original work remains universal inbox read/triage/attachments, remaining
management/exports and approved staging/real ChatGPT acceptance. All three
feature defaults remain false; no main push, deployment or live migration.

## Broader Admin PWA continuation — user profile increment, 2026-10-24

The owner requested the remaining final-product work in tested parts, committing
and pushing each part only to this feature branch. The active ordered worklist
is in `IMPLEMENTATION_PLAN.md`; PR #200 and the MCP foundations below remain done.

First increment: real read-only user profile and paginated all-status billing
history (`pwa_read.py` users/detail and users/payments); existing V10 drawer,
UZ/RU/TJ, course/track snapshots, canonical referral/device aggregates and
account-filtered feedback. See `READ_PROJECTIONS.md` for field/grain boundaries.
No MCP tool, flag default, schema migration or legacy mutation was changed.

Validation in isolated local fixtures: **300 passed, 16 PostgreSQL-only skipped**
for the Admin PWA/catalog/standalone suite; **16 passed on disposable PostgreSQL
15**, including the extended read-only transaction test for profile/payment
history. Real virtual-WebAuthn/browser and service-worker suites passed, with
profile paging, canonical account filter, XSS, 1440px desktop and 390px UZ/RU/TJ
screenshots in `/tmp/hsk-profile-browser-20261024`; mobile Uzbek and desktop
profile screenshots visually inspected. Synthetic fixtures are not staging or
physical-device evidence. Catalog generation: 63 artifacts, one bundle updated.

Next: bounded AI-spend, course-engagement and clearly defined conversion
statistics; then durable inbox and remaining management/export/staging gates.

## Overall activity metrics increment, 2026-10-24

User profiles were committed/pushed as `996ea0582994439d7ab3a483827990f2cb571143`;
[Admin PWA CI 40084429379](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40084429379)
passed. Main remained `891d9d9b6ffda5fba114d9c5c169eeb2f8a7836f`.

Next increment: `pwa_metrics.py` fixed-grain AI ledger cost/token/request totals,
canonical course engagement and registration-cohort Pro conversion, with inline
metric definitions and V10 UZ/RU/TJ panels. See `READ_PROJECTIONS.md` for exact
populations, dates, deduplication and exclusions. No schema/flag changes, new
MCP permission or inferred Telegram attribution.

Validation: **302 passed, 16 PostgreSQL-only skipped**; the affected read + real
MCP SDK tests rerun after final query changes: **14 passed**. Disposable PG15
projection/read-only snapshot: **1 passed** (15 unrelated PG tests deselected).
Browser/WebAuthn/SW checks passed; metric panels and profile regression checked
at desktop/mobile, screenshots `/tmp/hsk-metrics-browser-20261024`, desktop and
mobile statistic screenshots visually inspected. These remain synthetic QA,
not real ChatGPT or staging acceptance. Next work: universal durable inbox.

## Durable native intake increment, 2026-10-24

Statistics increment committed/pushed as `a7f0a5d13660c365ebd39dd108f715c644a39446`;
[Admin PWA CI 40084708364](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40084708364)
passed, as did Backend/Desktop/Localization/TTS for that head. Android was still
running at the check; do not infer its outcome.

`0122_admin_pwa_native_reports` adds private durable Android report intake,
canonical ownership, DB-coordinated throttle/UTC-day deduplication, delivery
state and bounded retention. The native API commits intake before Telegram only
when the existing PWA flag is enabled; flag-off Telegram-only behavior and the
existing success/503 contract remain. See `NATIVE_INBOX_INTAKE.md` for lifecycle,
retention command and mandatory cleanup scheduling before activation. Reports
and JPEG bytes are private; no inbox/attachment/MCP endpoint is added yet.
Downgrade refuses nonempty report data. No live schema/flag/deploy change.

Validation: combined Admin PWA/catalog/bootstrap + Android feature/report-flow +
legacy financial/access/import suite: **443 passed, 17 PostgreSQL-only skipped**.
Separate disposable PG15: **17 passed**, including concurrent intake, nonempty
rollback refusal and actual 0103–0122 empty-QA migration DDL. Isolated Alembic
0121→0122→0121→0122 succeeded. Retention CLI help/count-only exercised against
that empty disposable DB, no rows removed. Full-history legacy cold start at
0011 remains out of scope. No UI changes in this increment.

Next: connect bot/release/native reports to the bounded inbox, then triage,
secure attachments, admin/system sources, exports and remaining management and
staging gates. Historical Android Telegram-only messages remain unrecoverable.

## Required reading

Read root `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`; `HSK_AI_ADMIN_PWA_TEMP_RULES.md`, latest `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md`, `MCP_CONNECTION_CONTRACT.md`, `MCP_CHATGPT_COMPATIBILITY_AUDIT_20261024.md`, `BROWSER_UI_CONTRACT.md`, `ADMIN_PWA_V10_UI_REFERENCE.md`; then real source/tests. Historical `codex/admin-pwa` branch references are superseded by the user-selected feature branch above.

For UI, read actual `.agents/skills/hsk-ai-ui/SKILL.md` and `.agents/skills/webapp-testing/SKILL.md`; these were read and applied in this increment. Read `localization/README.md` before copy changes. Author UZ/RU/TJ `ui.admin_pwa.*` in canonical `localization/ui/*/miniapp.json`, generate/check with `scripts/i18n_build_all_catalogs.py`; never edit generated catalogs directly.

## Implemented — do not rebuild

- `pwa_mcp_oauth.py`: one exact predefined public client/callback, authorization code + S256 PKCE, session-bound three-minute explicit consent, hashed one-use CSRF, 60-second single-use code and 300-second hashed opaque access token. Client-ID shape now matches the resource verifier; configured callbacks cannot preseed/duplicate OAuth response fields. CSRF hash is cleared after allow/deny.
- `pwa_mcp_consent_transport.py`: actual GET/POST `/oauth/authorize`, same-session allow/deny, exact Origin + Fetch Metadata + CSRF, RFC 9207 `iss` on successful/denied redirects, state preservation. New V10 localized sign-in/retry and expired/restart screens contain no reflected OAuth query or credentials.
- **Browser bug fixed:** `no-referrer` caused native form POST to send `Origin: null`, failing CSRF. Consent HTML/header now use `strict-origin`; native browser tests assert real Origin and origin-only Referer, while CSRF checks remain strict. See the Fetch standard reference in the compatibility audit.
- `pwa_mcp_management.py`: mounted owner-only cookie API for last 30 consent records and atomic revocation of outstanding codes plus ALL issued grants. Current canonical WebAuthn admin and same-user ownership required. History includes actual active-access expiry and expires pending records correctly. APIs now use the existing PWA `ok` envelope.
- `pwa_bootstrap.py`, `app.js`, `styles.css`: server-gated MCP availability; V10 existing drawer for history and separate revoke confirmation, accessible focus/close/Escape, mobile More entry, UZ/RU/TJ labels and explicit loading/empty/error/uncertain/offline/auth states. No new MCP write tool. Lost revoke response requires a history reread.
- `pwa_mcp_http.py`: protected-resource/AS metadata, token endpoint and stateless authenticated JSON-RPC. Supported versions remain `2025-06-18`, `2025-11-25`; initialize echoes a supported request or offers the newest supported version. Subsequent calls require a supported version header. Strict UTF-8/JSON, duplicate/nonfinite/deep input rejection, media/Accept quality checks, invalid Origin -> 403 on every MCP method, notifications -> 202, unknown methods/tools rejected, stats timeout 10s, tool OAuth metadata. Expired/revoked access -> 401 with resource metadata, scope and invalid_token challenge.
- **New security module** `pwa_mcp_security.py`, models `admin_pwa_mcp_security.py`, migration `0121_admin_pwa_mcp_security`: DB-shared minute quotas, audit admission BEFORE protected work, safe completion outcome/actor, seven-day audit retention with bounded 100-row cleanup per admitted/over-limit attempt. Failed audit/admission returns 503 without exposing results. Audit remains separate from the analytics READ ONLY transaction.
- Revocation blocks subsequent authorization checks. A statistics snapshot already authorized before revocation may finish within its existing 10s bound; revocation does not cancel an in-flight SQL statement.
- Quotas: authorize GET 60/min, consent POST 60/min, token 60/min, MCP POST 300/min, history 60/min, revoke 30/min; additional statistics cap 30/min per verified canonical admin across all tokens/workers. Endpoint-wide anonymous buckets prevent token/IP-driven bucket growth. 429 includes Retry-After; repeated global denials are aggregated to one audit row per endpoint/window. Edge network/connection limits still required before staging.
- Audit stores only UUID, allowlisted action, outcome, HTTP status, canonical admin ID if verified, timestamp. No IP, URL/query, header, cookie, code/token/hash, state, PKCE, arguments or statistics result. Exceptions use content-free logs. Downgrade refuses to erase nonempty audit evidence.
- Security foundation models registered at 0121; later inbox/push work advances the QA/migration head to 0125. Existing `pwa_mcp_grants.py` is an earlier unmounted helper; the real mounted implementation is `pwa_mcp_management.py`.

## Historical OAuth/SDK validation (`5ef02f1f` / `4009e903`)

Local Python 3.12 at those foundation snapshots:

- Full scoped Admin PWA + localization/QA suite with official SDK regression: **298 passed, 16 PostgreSQL-only skipped** (297 before the SDK-only test commit).
- Disposable local PostgreSQL **15**: **16 passed**, including atomic first-use quota under eight connections, simultaneous code redemption/revocation, READ ONLY checks and migration audit-preservation guard. CI independently uses PostgreSQL 16.
- Real disposable 0109 baseline -> 0110–0121 upgrade, 0121 -> 0120 downgrade and re-upgrade passed. Full historical cold-start migration remains independently broken at old 0011 (missing course_progress); do not claim it fixed.
- Affected legacy payment/subscription/preview/affiliate/import regressions: **61 passed**.
- Catalog check: **63 artifacts, 0 stale**; Python compile and git diff checks passed.
- Actual headless Chromium: virtual WebAuthn/PWA/SW suites passed; real cookie/DB management, revoke cancellation/success and token rejection verified; desktop 1440 + iPhone viewport 390, UZ/RU/TJ history screenshots; consent/sign-in/expired screens passed with no script errors or horizontal overflow. Screenshots: `/tmp/hsk-mcp-browser-20261024` on the original host; CI uploads equivalent synthetic evidence.
- Synthetic consent bridge explicitly supplies Fetch Metadata (Chromium route interception omits network-generated headers). It asserts the real browser Origin and Referer first. This does NOT prove actual HTTPS/proxy or physical iPhone behavior.
- Verified runtime CI: [Admin PWA run 40081833261](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40081833261), exact `5ef02f1f`, **both jobs green**: 297 passed/16 PG-only skipped, 61 legacy, 16 real PostgreSQL 16, scoped migrations and browser/catalog checks passed. Desktop, TTS and Localization were green at this checkpoint; Backend/Android still required completion verification.
- Verified SDK-test head `4009e903` CI: [Admin PWA run 40082233884](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40082233884) **both jobs green**: 298 passed/16 PG-only skipped, 61 legacy, 16 real PostgreSQL 16, catalogs, migrations and browser QA. TTS/Localization/Desktop also green; Backend/Android still running when recorded.
- Official Python MCP SDK **1.27.0** controlled-client test `tests/test_admin_pwa_mcp_sdk.py` passed locally: real HTTP authorize/approve/PKCE token, replay rejection, SDK initialize/notification/list/call, actual SQLite statistics and owner revoke -> bearer 401, audit actor/outcomes. No OAuth/statistics service mocks. Only ASGI transport replaces external networking. SDK + compatible sse-starlette 3.0.3 are pinned in CI QA installation alongside all application requirements; no runtime dependency was added.

## Next safe work / release gates

1. Runtime/SDK Admin PWA CI is verified; check latest documentation-head and remaining Backend/Android statuses before any new all-CI-success claim. Do not repeat implemented history/revoke/audit/quota/UI or RFC 9207.
2. Official SDK 1.27.0 controlled compatibility is now tested; do not repeat that foundation. Inspector/real ChatGPT and actual network/TLS remain staging checks. Modern `2026-07-28` discovery/routing features are not implemented or advertised; verify whether the chosen real client negotiates the supported protocol before expanding scope.
3. Official OpenAI docs permit CIMD, DCR OR predefined OAuth clients. This implementation deliberately supports only exact predefined public-client `none` + S256. Obtain actual client ID/callback from the owner’s permitted isolated ChatGPT connection page; do not invent them, treat a CIMD URL as a static identity, fetch arbitrary metadata, or add DCR just because static config is blank.
4. Deliberate lifecycle: no refresh token, access lasts at most 300s; reauthorization requires fresh client PKCE/state and explicit owner consent. Browser logout prevents code redemption but existing OAuth access lasts until its own expiry or explicit revoke. Test this separately approved OAuth-session policy and automatic ChatGPT reconnection on isolated staging. If refresh is necessary, design rotated one-use families with replay detection and consent-wide revocation first; never simply lengthen the access token.
5. After separate owner approval and actual isolated environment/client details: stage under verified DNS/TLS/trusted proxy, configure exact resource/issuer/callback without weakening production constants, enforce edge limits and log redaction, test initial consent/denial, expiry/reconnect, owner revoke, quota and a real statistics-only ChatGPT call. Staging host/resource/RP currently need an explicit isolation design; no permissive wildcard was added.
6. No main/production promotion or full-connector-complete claim until the above release gates have actual evidence. Preserve Telegram `/admin.html`, legacy auth, Android Direct/Play, payments/access and lesson data.
