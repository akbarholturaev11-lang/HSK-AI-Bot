# Proposal

## Why

At main `3c47fec6`, Admin reads the live Lava catalog, while learner overviews and invoice preparation read price snapshots persisted by Admin Save. This makes merchant price/currency changes depend on another Save. The owner explicitly requests automatic server pricing and one existing currency selector with USD, RUB and USD + RUB; regional routing itself already exists and must remain unchanged.

This extends the scoped [payment handoff](../../../docs/payments/LAVA_TOP.md), whose snapshot-only policy is superseded only by this delta. AGENTS, AI_RULES, localization and performance contracts remain authoritative. New payment authority and cache behavior require a short plan rather than treating this as a cosmetic selector edit.

## What Changes

- Resolve sellable USD/RUB prices from the existing read-only Lava product catalog automatically, with a bounded merchant-only cache and one in-flight read per runtime. Never hold SQL transactions during provider IO.
- Extend the existing signed settings command and currency selector to enable USD, RUB or both, preserving the legacy default currency for old clients. Do not add redundant price controls or alter existing regional routes.
- Use verified catalog prices for new invoice preparation; preserve actual provider totals, fixed historical invoices, discount/promo validation, webhook-only access, cancellation/refund and renewal rules.
- Retain existing errors, monitoring/Inbox, attempt/source attribution and revenue authority. No new KPI, provider mutation, schema migration, live test charge or APK release.

## Capabilities

### New Capabilities

- `lava-pricing`: Provider-owned automatically refreshed prices and explicit enabled-currency policy across learner PWA, existing Mini App and Android Direct transports.

### Modified Capabilities

None. Existing installed specs cover Admin campaigns rather than Lava pricing.

## Impact

Shared Lava runtime/config/checkout, existing overview adapters, signed Admin settings, canonical UZ/RU/TJ labels and focused API/browser tests. Play external-payment restrictions and existing installed APK request shapes stay intact; Desktop-specific work is excluded.

Risks are stale catalog/merchant failure, currency-policy bypass, SQL connection retention, duplicate invoice creation and changes between display and invoice. Tests must prove bounded freshness/fail-closed behavior, no provider IO under SQL locks, unchanged canonical ownership/deduplication and real invoice totals. Roll back this isolated delta without rewriting existing invoices or entitlements; reverting restores the prior stored-snapshot behavior and requires explicitly documenting that limitation.
