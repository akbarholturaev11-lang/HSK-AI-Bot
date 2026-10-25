# Proposal

## Why

The owner supplied the V10 HTML again and explicitly requested both the control center and Statistics to match its layout while using complete real analytics. The existing handoff covers smaller read projections and the campaign delta; it does not specify the expanded section-level analytics/cache and visual mapping required here. The canonical execution checkpoint remains [the Admin PWA handoff](../../../docs/admin-pwa/MCP_NEXT_CHAT_HANDOFF.md), with [read definitions](../../../docs/admin-pwa/READ_PROJECTIONS.md) and the verified V10 source reference.

## What Changes

- Rebuild the existing Home view into real KPI cards, an activity chart, actionable review queues and functional shortcuts using the supplied V10 hierarchy. Preserve the compact toolbar, mobile safe area, single contextual action, native passkey and current navigation.
- Fill the seven existing Statistics tabs with real typed projections for overview, course, platforms, conversion, finance/AI, sources and report. Reuse audited business definitions; do not ship demo numbers, multipliers, fixture claims or fabricated growth/attribution.
- Add bounded, first-party, section-on-demand aggregate reads, reusing the private 24-hour Redis/optional R2 snapshot boundary. Unopened sections perform no work. Keep authentication and commands live and the external MCP tool unchanged.
- Author fixed UZ/RU/TJ text centrally, keep data age/grain visible, and distinguish real zero from missing/immature/uninstrumented data. Preserve currency separation and identify any explicitly estimated USD-equivalent calculation.

## Capabilities

### New Capabilities

- `admin-real-analytics`: source-bound section analytics with canonical identities, bounded reads, daily private snapshots and honest measurement/financial definitions.
- `admin-control-center-ui`: V10 Home and seven-tab Statistics presentation of real snapshots and functional existing actions across desktop/mobile/locales.

### Modified Capabilities

None; `openspec list --specs` returned no existing specs. Campaign planning remains a separate existing delta.

## Impact

Admin PWA read projections/cache composition, isolated frontend, canonical catalogs, scoped exports/reporting, tests and feature handoff only. Audit existing `AdminMiniAppService`, finance/course/platform/source analytics and schemas before reusing them: the full legacy overview loads unrelated/private data and some unbounded historical arrays, so it must not be blindly proxied. No database mutation, payment/access policy change, new external MCP tool, feature activation or manual deployment. Implement/test in verified increments; revert new reads/views within the existing disabled rollout boundary if regressions occur. Source lineage, canonical/legacy ownership, over-counting, currency and query cost are the main risks.
