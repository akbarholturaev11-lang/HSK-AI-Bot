# Proposal

## Why

Returning from checkout rebuilds the authenticated course document and blocks on a new map. The standalone PWA also inherits Telegram-only controls and cannot start a Live voice session under its own browser identity. Changes to checkout embedding, Live authentication, and notification delivery require coordinated acceptance across the PWA and shared backend.

## What Changes

- Skip the sign-in view when the server verifies a returning browser session. Keep the first course launch effect brief.
- Keep the active course view mounted during checkout and make Back and swipe available on slow connections. Restore the underlying screen immediately and refresh authoritative data in the background.
- Consolidate Inbox and open Settings as dedicated, full-screen views. Retain current consent and privacy controls for delivery.
- Remove Telegram-only controls where there is no browser equivalent. Enable eligible PWA Live sessions through the same provider gates and limits as other clients.

## Capabilities

### New Capabilities

- `learner-pwa-navigation` governs returning launch, checkout, and native-feeling browser navigation.
- `learner-pwa-delivery` governs the unified authenticated Inbox and consented installed delivery.
- `learner-pwa-live-voice` governs Live eligibility and browser session authorization.

### Modified Capabilities

None.

## Impact

Learner PWA and shared course, checkout, and voice sources. The authority for notices is the existing learner push service and [Smart delivery contract](../../../docs/smart-reminders/SMART_REMINDER_DESTINATION.md). Payment decisions, entitlement policy, Telegram SDK/auth, lesson grading, and other clients retain existing contracts. Release evidence includes WebKit and API regressions plus installed-device/provider acceptance when available. Roll back PWA UI commits independently or leave the existing delivery and Live flags closed if runtime acceptance fails.
