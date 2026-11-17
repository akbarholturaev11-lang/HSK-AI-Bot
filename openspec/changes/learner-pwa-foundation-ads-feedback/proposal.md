# Proposal

## Why
PWA foundation completion treats missing Telegram credentials as successful preview and skips telemetry. Ads and contextual feedback already exist but their PWA transports/lifecycle hooks are incomplete. This combined cross-client correction needs a bounded contract beyond an isolated bug patch.

## What Changes
- Share canonical, idempotent foundation persistence across Android, Telegram and PWA; show completion only after committed server acknowledgement and retain retry/resume on failure.
- Reuse existing course event storage and Admin foundation projections for authenticated PWA start/interaction/completion.
- Connect existing two ad placements to PWA cookie/CSRF transport, preserving Mini App placement settings and account caps.
- Extend the existing feedback dialog and BotFeedback service for brief contextual lesson/practice/voice exit feedback with server eligibility and cooldown.

## Capabilities

### New Capabilities
- `learner-foundation`: acknowledged, recoverable, cross-client foundation completion and analytics.
- `learner-pwa-engagement`: existing advertising and contextual feedback through authenticated PWA.

### Modified Capabilities
None.

## Impact
Baseline origin/main 972a4044. Authorities: AGENTS.md, AI_RULES.md, PROJECT_MEMORY.md, localization/README.md, docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md, docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md. Existing PWA navigation OpenSpec remains authoritative for navigation; this delta only fixes the three requested paths. No schema, pricing, entitlement, authored lesson/answer, Desktop development or bot migration. Risks: false completion, duplicate writes, cross-account state, overlapping overlays and unintended rewards. Rollback transports/UI together while retaining committed results; never restore preview-success in authenticated PWA. Focused API/database, Android compatibility and Chromium/WebKit offline/retry/geometry tests precede promotion; installed-device acceptance is reported separately.

Analytics Impact: reuse course_miniapp_events canonical user/event dedupe and existing foundation Admin learning projection; ad views remain canonical CourseAdView and feedback remains BotFeedback/Admin inbox. Unsupported historical PWA metrics remain unavailable; do not backfill invented starts/results.
