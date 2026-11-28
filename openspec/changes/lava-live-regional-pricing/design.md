# Design

## Context

See proposal.md and [current payment handoff](../../../docs/payments/LAVA_TOP.md). Main `3c47fec6` already routes Russia to RUB and Other to USD. `LavaConfig.currency` is a legacy default, while `regional_prices` implicitly exposes the other currency. Admin catalog reads are live; learner overview and start use stored snapshots. `LavaRuntime` already owns runtime-local state; `LavaClient.list_products()` is paginated/bounded and uses the official read-only product API.

## Goals / Non-Goals

**Goals:** automatic verified prices, an explicit three-choice currency selector, no provider IO while SQL is held, unchanged invoice/owner/access authority and old APK request compatibility.

**Non-Goals:** provider price mutation, exchange-rate estimation, a new background polling service, Redis, a new price editor/dashboard, schema migration, Desktop development or APK publication.

## Decisions

1. Add an optional enabled-currency list to the existing config/settings command. Missing policy preserves current USD+RUB availability; keep `currency` as the legacy default. The existing selector maps USD/RUB/both to that policy, with both retaining the existing default. Current regional helpers remain unchanged. This avoids overloading the old currency field with a non-currency value that old clients cannot understand.
2. Reuse the runtime-local state for a merchant-catalog cache: immutable parsed products, 60-second successful TTL, one shielded in-flight task, a 3-second whole-fetch deadline and short failed-read backoff. Cache no user, session, eligibility, discount, attempt or invoice data. The cache is runtime/merchant-scoped and is discarded on process restart. A stale stored snapshot is not a payable fallback. Do not add a worker or database polling.
3. Split overview into a SQL phase for the current config/account/subscription/discount templates, then close SQL before the catalog read and pure price projection. Move the two shared attachment adapters outside their existing SQL scopes; Android Direct uses the same safe service boundary. Recheck user/config within the owned service phase; never commit or roll back a caller's transaction to free a connection.
4. Keep start's User-first reservation and duplicate/rate/pending/discount guards. After reservation commits, resolve the exact catalog offer/period/currency outside SQL and record the verified expected amount before the single invoice POST. Catalog failure or a missing/disallowed price terminates that local reservation without a provider invoice; retain typed errors and existing provider monitoring. Actual invoice totals retain their current authoritative handling. Existing invoices and ledger decisions are untouched.
5. Admin Save continues its exact passkey/CAS/catalog validation for settings changes, but a catalog price change alone is no longer an unsaved setting. The existing offer selector already displays live catalog currency amounts; remove its redundant stored-price hint. Remove the snapshot-refresh-only Save override. No extra price rows, buttons or confirmation screens. USD + RUB is a currency-code label shared unchanged in UZ/RU/TJ; existing canonical currency-field copy stays unchanged.
6. Analytics Impact: no event/KPI changes. Keep real invoice-start and webhook-paid timing, route-owned platform, canonical account and attempt/source fields; no revenue from quote/cache reads. Monitoring Impact: use existing route/feature/site bindings and content-free provider failure reporting; registry and focused chain tests must retain current coverage honestly.

## Risks / Trade-offs

- Cold catalog latency → checkout keeps its existing immediate shell/skeleton; one read, 3-second deadline and 60-second cache bound cost. RUM collection and measurement settings remain unchanged.
- Merchant changes price between quote and provider page → the actual invoice total remains authoritative and visible before the learner completes payment; no repeated invoice POST and no historical invoice rewrite.
- Removed offer/currency → hide/refuse that verified-missing price, never use saved snapshots or estimate conversions. Keep mode permissions and old defaults explicit.
- Async cancellation → shield shared reads and bound their lifetime; one disconnected learner cannot cancel all others' lookup.
- SQL/cache coupling → synthetic transport asserts zero checked-out connections during actual provider GET/POST and concurrent request tests prove one read; no new production database writes.

## Migration Plan

No migration. Add backward-compatible config parsing, signed policy validation, bounded cache/service boundaries, then the existing Admin selector and canonical catalog. Verify focused backend/payment/owner/monitoring tests, PWA engines, Android adapter compatibility and mandatory CI. Deploy only tested code under the owner's existing main/deploy authorization. Roll back the isolated code/config reader delta without deleting policy fields, invoices, payments or access history. Real merchant/device acceptance remains separate from synthetic CI.
