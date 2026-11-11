# Design

## Context

Android main starts in `MainActivity`'s `LinkScreen`, then creates `OnboardingViewModel` with bearer transport. PWA guest Li starts with account choice, reads public track metadata and saves only on verified provider return.

## Goals / Non-Goals

Move existing Compose choices before account creation, including proper back and retry behavior. Preserve original native proof polling, language selection, session ownership, default-off rollout, PWA, billing and progress. Do not add iOS installation or a fake lesson.

## Decisions

- A bounded public preview returns only the native flag and live course metadata. It grants no access. Reuse the existing screen and ViewModel in a draft-only mode; neither asks for a token.
- Persist only the finished non-secret choices with an expiry, and arm the draft only for the new-account provider path. Claim it once only after verified status, using the same bearer for resume. The server refuses automatic writes to completed accounts or existing course progress under the canonical User lock. The server validates track/level; denied selections return to native choice. Failed saves keep editable choices in that session.
- Reuse PWA canonical strings and native provider UI. Do not persist provider tokens or introduce a new grant/analytics path.

## Risks / Trade-offs

Feature flag and a short lookup deadline keep legacy login usable; cancelled proof stays in the native auth flow. Automated coverage must check preview privacy, invalid/locked selections, draft expiry, existing account skip, process recreation before proof and no mixed-session save. Real provider/device QA remains separate.
