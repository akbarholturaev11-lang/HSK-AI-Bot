# Proposal

## Why

Direct 1.7.29/60 was published from 503730e5 on 2026-11-05; latest reviewed main 66dea5be (including the owner-requested continuation after ffcab1c0) contains later PWA onboarding, provider checkout and independent loading behavior absent or partial in native Android. Existing web-specific handoffs deliberately exclude Android, so this bounded native delta is needed; they remain authoritative for their own flows.

## What Changes

- Audit shipped artifact, PWA, Compose and shared services in one evidence matrix.
- Add native onboarding choices and goal/level validation through the existing canonical service, with an independent default-OFF Android Li rollout gate; reuse existing auth proof polling, trial and course handoff.
- Add Direct-only native Lava 1/3/6/12-month checkout, status/cancellation and real server-owned exit offer; preserve manual receipts and Play's no-checkout policy.
- Settle profile/trial sections independently and use native reserved loading slots in affected screens.
- Preserve server-owned account/access/pricing/progress, UZ/RU/TJ, existing analytics storage/Admin consumers and unchanged PWA/Mini App adapters.

## Capabilities

### New Capabilities

- `android-learner-onboarding`: native additive choices and safe rollout using existing authenticated onboarding/trial/course services.
- `android-provider-checkout`: Direct-only provider checkout with authoritative pricing, ownership, discount and payment verification.
- `android-activity-feedback`: canonical bot/PWA one-question feedback after verified learning activity.
- `android-progressive-sections`: independent native profile sections and stable affected loading layouts.

### Modified Capabilities

None.

## Impact

Android Kotlin/Compose, canonical Android localization, narrow FastAPI Android adapters and existing Lava/exit-offer services; no new database migration, desktop code, WebView, production flag changes, APK/Play publication or main merge. Existing authority: AGENTS.md, AI_RULES.md, PROJECT_MEMORY.md, docs/onboarding-li/{PRODUCT_GOAL,IMPLEMENTATION_CONTEXT,RELEASE_READINESS}.md, docs/PWA_LI_TELEGRAM_AUTH_HANDOFF.md, docs/payments/LAVA_TOP.md, docs/PERFORMANCE_{BACKEND_PWA_GOALS_REQUIREMENTS,PWA_PROGRESSIVE_LOADING}.md and localization/README.md. Rollback is a reviewed revert; disable the new native rollout gate without mutating financial/account data. Automated checks do not replace device/provider acceptance. PR only; no merge or release.
