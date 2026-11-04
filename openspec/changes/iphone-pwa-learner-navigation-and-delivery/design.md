# Design

## Context

At ac0e75e0 the course and checkout are distinct guarded documents. The checkout close route replaces the document with a fresh course load. Course notices use a modal and a separate push overlay. The browser Live endpoint has only turn support.

## Goals / Non-Goals

Keep a same-origin learning shell, verify slow return and nested gestures, keep the Inbox/Settings layout simple, and reuse canonical payment, notification and Live contracts. Shared clients keep their existing transport, grading, access and billing behavior.

## Decisions

- Mount the existing authenticated checkout document as a full-screen course layer on the PWA entry path. Limit embedding to the site's origin and explicit PWA checkout mode. Direct checkout links retain the same verified actor and a deterministic course fallback. Frame closure restores the underlying view before requesting current access and progress. An operation already submitted keeps its existing uncertain-outcome semantics and server idempotency.
- Use the course history/gesture stack for Inbox and Settings. Load both bounded Inbox feeds independently and keep the final owner verification. Keep Web Push consent and send-time checks from the existing learner push service and Smart destination contract. Account restriction uses one recent, dedicated event recorded with the signed admin state transition, with a generic lock-screen message. It can reach only a still-consented, active PWA installation of a currently restricted canonical owner. Suppress stale episodes and all ordinary pushes while restricted. The restriction event does not restore access.
- Use a dedicated PWA Live rollout switch in addition to provider eligibility. Bind the first relay frame to the verified cookie and CSRF, enforce configured same origin, and use the shared session-owner lease and quotas. No client-provided user identity.

## Risks / Trade-offs

Exercise Back, native touch, cold/slow launch and network loss on WebKit with production source and synthetic account data. Run ASGI ownership and checkout regressions plus existing Mini App behavior. Installed Web Push and upstream voice acceptance need authorized device/provider evidence before declaring a live rollout. The previous standalone route remains the checkout rollback and existing feature switches remain delivery/Live rollbacks.
