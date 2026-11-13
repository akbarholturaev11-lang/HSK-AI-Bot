# Proposal

## Why

Subscription Sources (audit rows F6/F7) is Overall-only. The entry table has no platform column, and its `source` is caller text. A Telegram caller can send `android_subscription`, so a source prefix cannot name a platform. This is requirement 3 of the next stage in `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`, the single context file for this work (section "Next stage", R3).

## What Changes

- **Schema (owner approval needed at the PR):** Alembic `0155_subscription_entry_client` adds a nullable `client VARCHAR(16)` to `subscription_entry_events` and an index on `(client, created_at)`.
  - Additive and nullable: PostgreSQL does not rewrite the table.
  - No backfill: old rows stay Overall-only.
  - Downgrade drops the index, then the column.
- **Writers:** `record_entry(..., client=...)` stores only `telegram`, `iphone_pwa` or `android`; any other value is stored as NULL. Each route passes its own client:
  - the Telegram Mini App subscription overview: `telegram`, whatever `source` the caller sends;
  - the PWA subscription overview: `iphone_pwa`;
  - the Android subscription open route, the Android checkout overview and the Android Lava overview: `android`;
  - Desktop entries stay NULL (Desktop freeze).
- **Reader:** `platform_sources_metrics` under the Android, Telegram and iPhone PWA filters.
  - `entries`: that client's entries, from its first one (`attributed_since`).
  - `attribution`: approved payments of that platform (server-set `payments.source`, as in Finance) submitted from that boundary. Each is matched to the nearest earlier entry of the same account **on the same client**, else `unknown`.
  - Before the first entry both are null (`no_data`), never an empty table.
  - `traffic` is not a platform value (`not_applicable`): public-site visits are company-wide.
- **Admin UI:** the Sources tab under a mobile filter shows the two tables, their start dates and a UZ/RU/TJ note on the same-platform rule. The traffic panel is Overall-only.
- **Registry and CI:** `entries` is `covered` on the three mobile platforms with a route chain test. `attribution` is `partial`: its payment side has projection evidence only, as in Finance.

Overall impact: none. Overall Sources keeps today's any-platform rule; the golden test pins it.

## Capabilities

### Modified Capabilities
- `admin-real-analytics`: Subscription Sources becomes a platform-scoped section on the three mobile clients.
