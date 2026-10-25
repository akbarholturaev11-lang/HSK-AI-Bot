# Proposal

## Why

The standalone PWA has verified text-only, immediate campaign delivery, but the remaining legacy campaign controls are not connected: promotion buttons, owned photo/video, scheduled delivery and discount notices. The current [handoff](../../../../docs/admin-pwa/MCP_NEXT_CHAT_HANDOFF.md) and [management contract](../../../../docs/admin-pwa/MANAGEMENT_COMMANDS_CONTRACT.md) deliberately exclude these contracts; implementing them requires an explicit delta rather than enabling the unbounded legacy sender.

## What Changes

- Add the existing allowlisted promotion-button actions to signed campaign drafts and the bounded sender, with explicit localized labels and exact rendered-button commitments.
- Add private actor/session-owned campaign photo/video staging, strict content validation, metadata-only persistence and exact media binding. Reuse the existing Bot provider and media validators; never accept a browser-supplied provider ID.
- Add bounded scheduled delivery through the claimed PWA queue, preserving session revocation, current-admin checks, one-hour private payload lifetime, no uncertain retries and indexed limited due-work reads. Do not introduce a new persistent authority that outlives the existing session grant.
- Add explicit signed discount notices using the existing offer/eligibility and client-channel rules, without granting access or changing checkout/payment policy.
- Keep the V10 original editor, contextual action and one native passkey; fixed UZ/RU/TJ copy remains centrally authored. All changes remain first-party; external MCP stays statistics-only.

## Capabilities

### New Capabilities

- `admin-campaign-delivery`: Exact signed promotion buttons, bounded scheduled execution and explicit offer notices through the existing claimed queue.
- `private-admin-campaign-media`: Validated private owned campaign media references with bounded staging and retention.

### Modified Capabilities

None. There are no existing OpenSpec capabilities; this delta does not migrate the already implemented features into a parallel tracker.

## Impact

Standalone Admin PWA and its existing Telegram delivery adapter only. Relevant areas: `pwa_marketing.py`, `pwa_campaigns.py`, `pwa_outbound.py`, dedicated media staging, existing scheduler, ORM/Alembic for bounded metadata, V10 forms and canonical catalogs, corresponding API/PostgreSQL/browser tests. Preserve Telegram entry points, native notification channel policy, financial/access logic and daily aggregate reads. No new runtime dependency or automatic AI translation. Rollback disables the PWA boundary and cancels pending grants without dropping nonempty evidence; retained shared creatives/offers remain valid.
