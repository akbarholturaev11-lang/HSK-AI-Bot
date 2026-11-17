# Proposal

## Why

PWA Li lets a first-time learner choose their study plan before creating an account. Android main `334368cc` has the native choice screens but opens provider login first. This delta corrects that ordering. The web reference is [Li implementation context](../../../docs/onboarding-li/IMPLEMENTATION_CONTEXT.md); the native rollout and invariants are in [Android parity evidence](../../../docs/ANDROID_PWA_PARITY_20261111.md).

## What Changes

- Under the existing default-off Android Li flag, separate first-time and returning entry. Reuse native study choices before opening the real provider screen.
- Keep a short-lived local draft across the provider handoff. Resume only for a server-authenticated, fresh account; leave saved progress and existing payment/trial rights intact.
- Keep the legacy entry on an old server, a disabled flag or an unavailable preview. No PWA/Mini App, desktop, release or deployment change.

## Capabilities

### New Capabilities

- `android-li-guest-entry`: native pre-account choices and verified resume.

### Modified Capabilities

None.

## Impact

Android entry and onboarding ViewModels, localized resources, read-only Android preview and existing bearer onboarding save. No new table or auth grant. Rollback is the independent native Li switch.
