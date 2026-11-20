# Tasks

## 1. Baseline and plan review

- [x] 1.1 Audit GitHub main, existing scoped work, competitor primary sources, course/checkout event ownership, and baseline tests. Record findings and source limits in design.md.
- [x] 1.2 Re-read the four artifacts against source and active work. Collapse duplicate UI, services and tests, document the decisions, verify local links, and run `openspec validate value-first-learning-pro --strict` before runtime edits.

## 2. First confirmed result and return to study

- [x] 2.1 Extend the existing authenticated PWA and Android save responses with the same optional first-part display block. Verify first save, canonical wrong vs forged/missing evidence, duplicate, rejected completion, and unchanged Telegram/Desktop payloads. Compare SQL statement counts and response size. Use existing lesson-completion metrics, errors and privacy contracts.
- [x] 2.2 Put the learner's topic and at most one verified correction in the existing result layout, with clear review and continue wording in UZ/RU/TJ. Reuse guarded navigation to the next part or course, and point to the existing Mistakes and Today destinations. Verify narrow/normal layout, slow and failed saves, older responses, no extra fetch, and single primary CTA in Chromium/WebKit and Android. Verify existing Daily Plan/Mastery access, order and frozen identities through focused regression.

## 3. Pro value at an existing learning limit

- [x] 3.1 Use the existing limit surfaces to explain the relevant Pro benefit where a learner encounters a subscription-eligible course or review limit. Verify localized copy and actual current actions for Free, Trial, Pro, pending, PWA and Direct, plus the existing Play behavior and unavailable-checkout fallback. Keep existing verified funnel/diagnostic attribution and run focused payment/access regressions.

## 4. Evaluation, rollback and isolated acceptance

- [x] 4.1 Verify existing lesson, activation/return, checkout and diagnostic paths and coverage registry for changed files. Document available metrics, denominators and unavailable comparisons. Use the existing experiment regression suite and prove historical sales behavior and telemetry privacy are unchanged.
- [x] 4.2 Run the integrated local main-versus-feature smoke, parity, locale, analytics/monitoring and performance guards. Exercise the old response path and test rollback by restoring the presentation boundary in isolation. Record exact commands/results and remaining real-client evidence.

## Local acceptance evidence

- Completion projection comparison with identical authenticated first-save fixtures preserved ordered SQL. PWA stayed at 78 statements (754 → 857 response bytes), Android at 94 statements (735 → 838 bytes). The 103-byte delta comes from one stored canonical example. Neither client started a result-specific request. Older, empty, failed, and repeated save cases are tested.
- Chromium and WebKit each passed all 33 cases in `tests/e2e/test_pwa_learning_parity.py` and six cases in `tests/e2e/test_pwa_inline_pro.py`. The result uses the existing CTA and routes, with three locales, 320/390/430 px viewports and reduced motion covered. The short next-part fixture now supplies a genuinely short example. Its separate long-Hanzi fit assertion is retained.
- Android QA ran 71 focused JVM cases per flavor and seven installed lesson-celebration cases each on isolated API 36 (Direct with reduced motion, Play with normal motion). The native result can render the former payload and suppressed optional data without a new call. An additional installed limit test passed per flavor in `SectionLimitOverlayTest` with production source keys and controlled actions. Direct showed the lesson and review benefit and routed to checkout. Play showed the existing access check.
- `tests/test_sales_value_analytics.py`, `tests/test_course_sales_experiment_service.py`, entitlement and checkout regression checks passed. The isolated feature branch uses the existing event ownership and reporting paths. The historical assignment scope and incomplete current exposure/retention measures are documented in design.md.
- Local PostgreSQL 15 covered the course platform, signed browser, Pro-funnel and Admin Inbox chains. The combined run finished with 197 passes, 320 passed subtests and 30 Smart Reminder skips. The monitoring proof verifier accepted all 20 registered covered feature/platform pairs.
- The analytics diff guard relative to `5bbbf707` validated 120 metric projection keys and 21 flows. The permanent Backend/PWA diff guard passed with required co-changed behavioral tests. Graphify confirmed the shared PWA and Telegram completion callers. Source and endpoint tests supplied the Android and checkout dependencies.
- The integrated API regression selection passed 296 tests and 198 subtests. It includes `test_pwa_browser_auth.py`, `test_android_course_api.py`, `test_desktop_course_api.py`, the Mini App context and completion proof, canonical mistake material, map cache, parity and Android foundation tests. The i18n and first-lesson selection finished with 549 passes, 4,064 passed subtests and 14 environment-related skips. Canonical generation checked 82 current artifacts.
- Existing initial-shell, independently rendered course and browser diagnostics passed 12 cases per engine. The progressive-loading comparison passed 11 of 13 per engine. The same two Russian Practice 320 px layout cases fail on main and this branch at both tested motion settings. They belong to the existing performance effort and are excluded from the result-screen delta.
- Rollback was checked using the previous completion response without the optional block, and a checkout preview without the display hint. Both paths retain their original actions. No data migration is involved.

## Safari simulator rehearsal (2026-11-20)

- Candidate `d03564c8` passed all three locale cases in iOS 26.4 Safari on an iPhone 17e simulator, using the actual browser app and authenticated API over loopback HTTPS with a disposable PostgreSQL database. The local fixture supplied the session and final-card input. Safari reserved and loaded the course part, then submitted through the existing completion UI and server handlers.
- UZ and RU each showed one verified correction and saved one mistake. The TJ case supplied no missed answer and showed no correction. Each learner advanced one part and wrote one completion event after the replay request. The existing continue sequence closed the result, and the existing inline Pro screen showed the localized benefit using the real checkout-preview response with synthetic configuration. Only display was exercised at checkout.
- Railway inspection found the existing staging environment paired with Professional 45 services. The Value-First candidate has no verified remote staging target. The iPhone was unavailable and ADB showed no Android device. Physical-device Home Screen, provider and staged-cohort acceptance remain open.

## Workflow follow-up

- Physical Safari/Home Screen, native Play/Direct and Telegram device acceptance, staged timing and privacy-safe cohort baselines require environment access and deployment permission.
- Any new commercial A/B requires proof of exposure/ownership, compatible surfaces and a mature baseline under existing infrastructure before enabling it.
- Promotion, production configuration, provider actions, percentage rollout and archive are outside this isolated feature worktree.
