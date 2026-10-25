# HSK AI Admin PWA — current guide

Start with the [current handoff](MCP_NEXT_CHAT_HANDOFF.md), then root `AGENTS.md`,
`AI_RULES.md`, `PROJECT_MEMORY.md` and the relevant contracts below. Older PR #200
and feature-only checkpoints are historical. Current source branch:
`feat/admin-pwa-minimal-inbox-passkey-20261025`. The owner authorized promotion
of tested intended Admin PWA code to `origin/main`; verify remote evidence in
the handoff. Manual deployment, live migrations and feature activation remain
outside that authorization. All three Admin PWA/MCP defaults stay OFF.

## Home and Statistics

The owner-supplied V10 HTML is the visual reference, never a data source.
Home has real account/Pro/pending/today counts, a calendar learning-activity
chart, exact live queue/cohort navigation and existing protected quick actions.
Statistics has seven sections: overview, course, platforms, funnel, finance,
sources and report. Expanded experiment analysis loads only when opened.
No invented growth, chart values, platform shares or demo rows are shipped.

Cookie-only `POST /api/admin/v1/analytics` provides a separate first-party daily
snapshot per requested section/platform/period. Basic `/statistics`, its
allowlisted JSON/CSV files and the statistics-only MCP contract remain compatible.
The report labels those downloads as **basic aggregates**, not an export of all
new section tables. Feedback categories retain their separate sanitized files.

## Statistics load policy

Each requested variant refreshes on the first authorized request after its
rolling 24-hour expiry. Unopened sections do no work. There is no nightly scan,
card-by-card request, force refresh or background analytics polling. The UI shows
original `generated_at`; aggregate statistics can be up to 24 hours old.

Existing Redis coordinates healthy workers. Optional private R2 stores only
bounded aggregate snapshots for recovery; the adapter exists but credentials
and production configuration are not established by source code. Without R2,
Redis plus bounded worker-local daily fallback still works. During a Redis outage
or worker restart, separate workers can calculate separately. Auth/revocation,
payment/access decisions, queues, profiles and command authority stay live.
Private API responses remain no-store; browser/SW caches contain no private data.

## Contracts

| Subject | Guide |
|---|---|
| Section definitions, source/grain, bounds, daily cache and exports | [Read projections](READ_PROJECTIONS.md) |
| V10, one contextual action, localization and private-data handling | [Browser contract](BROWSER_UI_CONTRACT.md), [V10 reference](ADMIN_PWA_V10_UI_REFERENCE.md) |
| OAuth lifecycle and statistics-only tools | [MCP contract](MCP_CONNECTION_CONTRACT.md), [compatibility audit](MCP_CHATGPT_COMPATIBILITY_AUDIT_20261024.md) |
| Live review and exact-operation WebAuthn | [Payment review](PAYMENT_REVIEW_CONTRACT.md), [access grants](ACCESS_GRANTS_CONTRACT.md) |
| Campaign media/buttons/scheduling/discounts and other commands | [Management commands](MANAGEMENT_COMMANDS_CONTRACT.md) |
| Retained native intake and historical limits | [Native inbox](NATIVE_INBOX_INTAKE.md) |

The handoff records executed tests, latest CI, current main and remaining work.
Planning checkboxes, feature pushes and synthetic fixtures do not establish a
live rollout. Do not recreate completed OAuth, passkey, payment or Inbox work.
