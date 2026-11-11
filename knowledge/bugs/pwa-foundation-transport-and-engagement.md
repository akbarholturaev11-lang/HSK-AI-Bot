# PWA foundation completion and existing engagement transports

## Sabab
`Foundation.finish` treated absent Telegram initData as successful preview even on the authenticated browser PWA. `trackCourseEvent` also skipped that client. The existing ad module called Telegram-only routes, and the existing feedback dialog only hooked normal completed lessons.

## Fix
- Shared `CourseMiniAppProfileService.complete_foundation` validates the current version, locks the canonical user before reading/writing completion, preserves historical ownership and returns stored completion on every replay. PWA, Telegram and Android use it; transports commit before acknowledging.
- The real course UI requires an owner-matched completed foundation response, persists mastery/queue/completion intent and exposes retry after network error, timeout or malformed acknowledgement. Browser completion never falls into preview success.
- Authenticated bounded learning telemetry uses existing event storage, forced PWA attribution and existing Admin foundation metrics. Only foundation completion is authoritative; generic telemetry cannot submit server-owned completion/payment events.
- Existing ads.js receives PWA GET/POST adapters; existing two placement rules, audience, language and canonical caps remain authoritative. Views retain the actual UI language. The saved PWA lesson queues its existing lesson-end placement; an eight-second deadline skips unavailable ads. Closing a lesson-end ad resumes its original continuation once; pending requests cannot overlay a newly opened learning flow.
- Existing centered feedback UI supports one contextual question, three answers and optional issue text. Saved lesson/foundation or recent owned practice/Voice activity is required. Actual embedded practice exits use the existing RESOURCE frame lifecycle; a verified `card_seen` practice-entry event proves a visited screen and never claims a scored/completed attempt. Shared bot eligibility, 24-hour prompt retry, 30-day completion cooldown and single reward remain. Existing partial bot answers are not overwritten.

## Risk
Historical missing PWA events stay missing, and foundation cohort conversion still requires an earlier recorded start. Technical contextual feedback is explicitly grouped as `other`, not inferred as pricing or payment failure. The generic “Progress saqlanmadi” toast also covers the existing `android_foundation_required` lesson-completion refusal; an image alone cannot distinguish it from network/session errors. Browser fixtures verify transport/layout; they do not certify an installed physical iPhone or live production deployment.

## Prevention
- `tests/test_pwa_learning_parity.py`: authenticated ownership, Google-only accounts, error/no-ACK, cross-client replay, event dedupe/attribution, Admin foundation calculation, ad caps/language, compact feedback/cooldown/reward and Admin categories.
- `tests/test_pwa_learning_parity_postgres.py`: twelve concurrent client completion intents in an isolated PostgreSQL schema result in one committed event.
- `tests/e2e/test_pwa_learning_parity.py`: real 11-step flow with a repair, offline failure, reload/resume, double click, timed-out/invalid/foreign-owner acknowledgement, both ad placements and callback, three locales at 320/390/430px and compact feedback session suppression in Chromium/WebKit.
- Existing Android foundation and PWA auth regression suites remain required. CI adds the new browser/API tests and real PostgreSQL concurrency case to existing jobs.

## Analytics Impact
| Feature | Trusted writer and persisted grain | Existing consumer | Evidence |
| --- | --- | --- | --- |
| Foundation start and exercise | PWA session/CSRF → CourseMiniAppAnalyticsService → course_miniapp_events, canonical owner/event/dedupe key | build_foundation_metrics → Admin learning foundation projection | API integration, browser actual flow, existing analytics suite |
| Foundation completion | shared complete_foundation → one current version event per canonical learner, commit before ACK | foundation_status for all clients; same Admin foundation projection | cross-client retry and real PostgreSQL parallel test |
| PWA advertising | existing AdPlacementService.record_view → CourseAdView owner/placement/local-day | existing course ad statistics and caps | ad transport, language and cross-client cap tests |
| Context feedback | existing BotFeedbackRepository/Service → one completed BotFeedback and reward | existing Admin inbox and feedback_analytics categories | saved-context/cooldown/replay/category tests |

The broader analytics registry/CI initiative remains owned by `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`; this task does not claim historical PWA platform analytics are complete.

## Bot questionnaire activation correction
- **Sabab:** activity exits selected the three-answer compact presentation, so the existing free liked/disliked and paid value/reason bot forms were not automatically shown.
- **Fix:** the same prepare route accepts the additive `presentation=bot` selector after the original owned-activity and cooldown checks. The existing dialog displays one canonical question at a time as its heading (no repeated context/question line), with a solid existing theme surface so page text cannot show through. It advances radio choices in one tap, requests text only where the original bot requires it, and preserves native back, failure retry and pending bot answers. Full submissions retain the original codes, validation, one reward and Admin notification path. Legacy compact clients keep their original contract.
- **Risk:** new automatic forms use the app's existing feature option sets, not unavailable Telegram-only tools. Release campaign delivery rules are unchanged. No new schema or entitlement/discount/reward policy.
- **Prevention:** real authenticated free/paid/partial-answer API tests on SQLite and disposable PostgreSQL; three-language 320/390/430px Chromium/WebKit flows, native back, required text, failed-write retry, session suppression and the legacy Node UI harness.
- **Analytics Impact:** new full answers use the same BotFeedback codes and existing Admin inbox/category readers as bot answers. Existing compact rows and their explicit category mapping remain readable; no historical rows are rewritten.
