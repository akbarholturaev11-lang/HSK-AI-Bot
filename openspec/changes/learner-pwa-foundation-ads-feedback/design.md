# Design

## Context
See proposal.md for motivation. Foundation state already derives from course_miniapp_events through CourseMiniAppProfileService; Android completion currently writes there directly. PWA skips trackCourseEvent without INIT_DATA. ads.js calls Telegram-only routes. iphone-pwa-feedback.js and ordinary/release feedback routes already exist.

## Goals / Non-Goals
Use existing persistence, service and UI boundaries. No new dependency or database migration; no authored course/answer, entitlement, payment, Desktop or bot migration changes.

## Decisions
- Centralize current foundation completion in CourseMiniAppProfileService, locking canonical user before version validation/status/event write. Reuse the saved completion-intent key plus current version status and existing completion status, including historical events. Android and both browser transports commit before returning foundation state. Generic legacy Mini App completion also delegates here.
- PWA event route uses verified cookie, Origin and CSRF, a bounded learning-only whitelist and trusted source/owner. It cannot emit server-owned billing/result events. Existing Admin learning projection consumes the same event names; telemetry failure stays nonblocking except the authoritative completion write.
- Foundation.finish uses explicit transport and acknowledged completed state, never preview in PWA. Persist resume/mastery while pending, disable duplicate actions and retain retry after timeout/failure. Validate actor/version on acknowledgement.
- Extend miniapp_ads router with PWA transport; reuse Mini App placement policy/client selection to honor existing Admin settings. Existing ads.js receives transport callbacks; no second overlay.
- Extend the existing feedback module/ordinary prepare-submit schema with compact context answers and optional comment. Context codes explicitly identify positive/content/technical answers; existing BotFeedback completion/reward and Admin inbox remain owners. Do not overwrite partial bot answers. Server eligibility and UI session suppression prevent repeated prompts. Existing legacy form/release campaign remain compatible.

## Risks / Trade-offs
- Cross-account stale UI → PWA owner headers plus existing session/CSRF guards.
- Duplicate completion → user-first lock, existing canonical status and stable dedupe.
- Lost network response → retry same result, saved mastery, no success before acknowledgement.
- Overlay collision → only open feedback/ads after current flow closes; recheck visibility/navigation before and after asynchronous work.
- Historical missing PWA telemetry → no fabricated backfill; existing aggregate scope remains explicit.

## Migration Plan
Run focused database/API/Android tests and Chromium/WebKit retry/resume/geometry checks, localization generation/check and applicable CI. Promote tested commits following AGENTS.md and performance gates. Roll back UI/transports together without deleting saved results or feedback.
