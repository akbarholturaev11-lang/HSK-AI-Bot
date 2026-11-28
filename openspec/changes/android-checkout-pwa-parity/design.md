## Context
See proposal.md. PWA references are subscription.html and iphone-pwa-inline-pro.{js,css}; no PWA edits. Direct currently renders provider FilterChips independently of manual checkout and refreshes status once on resume. Shared SectionLimitOverlay renders the old Telegram sheet.

## Goals / Non-Goals
Use current Compose/ViewModels and native dp/sp/insets for the authorized PWA adaptation. No payment policy, entitlement, schema, provider integration or Play purchase expansion.

## Decisions
- Extract a small Direct checkout chrome/plan component shared by both real routes; reuse existing palette, native receipt picker and quote/result model. Avoid WebView or duplicated manual payment engine.
- Direct limit presentation owns an ephemeral checkout ViewModel store in a full-screen dialog; Play keeps its neutral channel gate. Close rechecks existing account/learning access.
- Keep UI selection state local/saveable, invoice recovery server-owned. Lifecycle-aware pending polling uses the existing status API, serialized by the model busy guard, stops on background/terminal status and caps each foreground visit at 15 minutes.
- Existing authenticated provider overview/start and manual opening receipt preserve analytics attribution. Existing apiCall(DiagTags.PAYMENT) retains diagnostics; no new event route or fabricated payment success.

## Risks / Trade-offs
- Delayed webhooks → foreground polling plus explicit retry; pending never becomes paid locally.
- Nested dialog/system Back → one handler per visible step and overlay-first dismissal tests.
- Small displays/large UZ/RU/TJ text → scrollable body, fixed reachable action, 48dp controls and emulator geometry tests.
- Server-disabled provider/manual recovery → reuse original route decisions and provider_entry_id; preserve one opening receipt.
- Real provider/3DS acceptance cannot be simulated by unit tests → report separately from fixture UI evidence.

## Migration Plan
No migration. Run Direct/Play checks, focused JVM and emulator tests, localization generator/guards and coverage checks; promote only scoped files under repository Git rules. Revert the commit for rollback.
