# Design

## Context

The authoritative state remains [the handoff](../../../docs/admin-pwa/MCP_NEXT_CHAT_HANDOFF.md) and [the management contract](../../../docs/admin-pwa/MANAGEMENT_COMMANDS_CONTRACT.md). Current `pwa_campaigns.py` authorizes one exact audience and queues text; `pwa_outbound.py` commits recipient claims before provider IO, rechecks session revocation and expires private bodies after one hour. `promo_button.py` already owns the allowlisted learner actions. Existing payout proof staging demonstrates owner/session isolation; course-ad media validation already bounds raster/video processing. Main now includes user filters, compact Mac layout and automatic Apple Web Push; retain those changes.

## Goals / Non-Goals

Implement the remaining first-party campaign controls in separately verified increments. Keep every external MCP permission statistics-only. Do not make the legacy unbounded sender the PWA execution path, grant access on send, change checkout eligibility, extend a session grant silently, cache current authorization or add runtime translation calls.

## Decisions

1. Promotion buttons use a strict PWA input model and the existing shared builder. Shared config supports optional explicit three-language labels while preserving old single-label/default behavior. Prepare signs a hash of each fully rendered button; save repeats it under the contact-setting lock where needed. The queue stores the reviewed markup, so later settings cannot substitute a destination. Arbitrary callback JSON and permissive legacy URL normalization are not browser contracts.
2. Media gets dedicated purpose-bound owned metadata, not a reused payout proof. Reuse existing 2-MiB/8M-pixel raster and 25-MiB video validation, single encode slot, two provider IO slots and 20-upload/hour actor quota. Stage to the uploading admin's private Bot chat. Asset references expire after 15 minutes unless consumed by a signed campaign; no BLOB or public URL. Upload/encoding occur outside the short DB transactions. Caption/prompt limits are validated for a single provider attempt, avoiding an unreviewed second message.
3. Scheduling stays within the existing one-hour private job/session grant. Accept explicit UTC time up to 30 minutes ahead and only before current session expiry; show that limit in UZ/RU/TJ. A nullable indexed `not_before` on outbound jobs fences early sends. The existing minute worker selects at most two due jobs and uses the same drainer/claim rules. No new long-lived offline authority or statistics cron. Reopening/revoking the browser session fences pending work and requires the existing signed pending-only resume.
4. Discount notices are separate signed commands bound to current offer, canonical eligibility and rendered localized notice, with notifications disabled in the shared legacy scheduler. Audit existing native/Play channel policy before implementing transport; preserve Android-first/suppressed promotional behavior rather than introduce a Telegram fallback that bypasses it. No access or payment mutation is performed by notice delivery.
5. Every UI increment uses the existing original-editor controller and contextual button. New fixed text is canonical UZ/RU/TJ; dynamic authored copy is not a UI catalog. No separate confirmation screen or browser provider reference field.

## Risks / Trade-offs

- Destination/media tampering → exact rendered/asset commitments, same-session ownership and post-wait proof rechecks.
- Scheduled send after logout → existing live session check and explicit bounded scheduling window; do not claim unattended long-term delivery.
- Duplicate provider work → durable pre-IO claims, unique shared delivery evidence, no uncertain automatic retry.
- Binary/encoder cost → preflight quotas, bounded bytes/time/slots and no DB during IO.
- Native offer-policy drift → preserve the existing delivery policy and regress its excluded Play/native cases before enabling notice send.
- Legacy compatibility → optional shared fields retain old decoding/build behavior; unrelated entry points remain unchanged.

## Migration Plan

Use additive Alembic changes only when the media/scheduling increment is implemented. Update ORM/migration parity, isolated QA initializer and CI bounds together; preserve all nonempty data on downgrade. Keep existing rollout defaults. Rollback fences new commands and pending jobs; never drop or delete referenced shared assets or immutable audits. Planning validation is not application QA.
