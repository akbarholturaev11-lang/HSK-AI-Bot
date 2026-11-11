# Design

## Context

See proposal.md and docs/ANDROID_PWA_PARITY_20261111.md for pinned evidence. Existing AndroidOnboardingApi/OnboardingRepository and CourseMiniAppOnboardingService already own status/save; native auth proof polling and trial calls already exist. LavaCheckoutService and PwaExitOfferService own provider state and a single account offer (migration 0152); use them without a new table. Historical Li docs say guest entry disabled, but a read-only live anonymous GET on 2026-11-11 local date redirects to Li. This observation does not authorize native activation.

## Goals / Non-Goals

Goals: independently reviewable onboarding, Direct billing and loading packages; additive legacy-compatible payloads; canonical UZ/RU/TJ bundles; strict server validation. Non-goals: web UI inside Android, duplicate financial services, desktop implementation, new production settings values, merging, distributing or provider purchases.

## Decisions

- Add ANDROID_LI_ONBOARDING_ENABLED=false to native status; keep legacy UI unchanged when off. Enabled native flow adapts authenticated Li choices using existing Compose panda/design, skips redundant web signup/install scenes and reuses actual course/trial flows. Do not equate 23 visual web scenes with 23 native network routes.
- Add Android bearer-authenticated Lava endpoints to the existing transport; require explicit Direct channel/capability, reject mixed cookie/Telegram credentials, authenticate native platform, and never accept a caller user ID. Existing PWA CSRF and Mini App signatures are unchanged. Direct-only Kotlin transport/UI isolates provider strings/CTAs from Play.
- Attach the optional Lava block only for capable native subscription overview; retain legacy manual shape and HSK unlock. Use existing runtime getter wired through app.main. Server-owned checkout mode governs provider/manual choice.
- Extend existing offer service/source allowlist to Android without renaming tables or creating another offer. Common account expiry/claim/consumption prevents cross-device reminting; source android keeps financial analytics attributable to Android rather than fabricated PWA events.
- Native view model uses bounded calls, duplicate-submit fences, lifecycle foreground status refresh and canonical server status. Provider navigation uses a validated allowlist; browser return never completes payment.
- Profile/trial launch sibling jobs and update their own sections with generation checks. Preserve mutation/read ordering and render existing content while optional trial fails.

## Risks / Trade-offs

- Billing regressions → existing Lava/manual/refund/preview/ownership tests, no live payment, Direct/Play build and artifact contracts.
- Native onboarding differs from Safari's guest ordering → independent OFF gate, authenticated adaptation and explicit device QA before activation; existing accounts never replay onboarding.
- Analytics → retain canonical CourseMiniAppEvent and Lava financial records/Admin consumers; do not repurpose pwa_pro_* events for Android or invent conversion denominators.
- Slow/stale response → bounded requests, server reconciliation, generation checks and deferred-response tests.

## Migration Plan

No database migration or production activation. PR from ffcab1c0; automated tests and audit evidence required. Existing provider reconciliation/refunds must continue if sales are disabled. Roll back via reviewed revert or keep native Li OFF; never reset accounts, offers or financial facts. Physical Android weak-device/real OAuth/provider QA remains separate from CI.
