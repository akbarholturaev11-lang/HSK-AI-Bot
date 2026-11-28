## 1. Android presentation
- [x] 1.1 Share Pro header, paper surfaces, plan anatomy and bottom actions between provider/manual checkout.
- [x] 1.2 Port the PWA inline limit offer to Direct, preserve Play access-only behavior and nested Back.
- [x] 1.3 Reuse/add canonical UZ/RU/TJ labels and regenerate native resources without editing PWA.

## 2. Payment return regression
- [x] 2.1 Add bounded foreground pending refresh, canonical recovery and honest success/failure presentation.
- [x] 2.2 Cover delayed confirmation, duplicate starts, lost replies and offer dismissal with JVM tests.

## 3. Verification and delivery
- [x] 3.1 Run Direct/Play compilation, relevant unit/static/localization and analytics/monitoring guards.
- [x] 3.2 Exercise native header/Back, provider/manual/limit states and locales on an emulator; retain screenshots.
- [x] 3.3 Review scoped diff and record local evidence, real-provider limits and delivery requirements below.

## Verification evidence
- Native Android API 36 emulator: Direct 26/26 and Play 5/5 focused UI tests passed. Includes canonical country labels/menu, removal of the limit footnote, retained email-stage terms, Play support icon/contact, UZ/RU/TJ, 200% type, manual/HSK30 receipts and foreground/delayed Lava confirmation.
- JVM regression: Direct 786 and Play 719 passed; final focused checkout/model rerun and Direct/Play lint passed (existing warnings retained).
- Both debug variants and instrumentation APKs compile. Canonical localization: 16 tests passed, 85 artifacts current, frozen-source guard has zero blockers; flavor/named-call/reference/translation guards passed.
- Analytics Impact: existing authenticated opening/plan/receipt/provider/ledger writers and ownership retained; status refresh creates no paid event. Existing route-to-Admin coverage remains partial.
- Monitoring Impact: existing apiCall(DiagTags.PAYMENT), feature/incident mapping and Admin diagnostic consumer retained. Exact reviewed source hashes record this Android-only UI/lifecycle change without claiming new Inbox chain coverage.
- No learner PWA, backend, Desktop, database or store policy source changed. Screenshots are local emulator fixture evidence, not a production payment/3DS or published APK claim.

## Workflow follow-up
- Promote only the tested candidate after the required Analytics integrity check and verify origin/main. Publish/install acceptance remains separate from a source merge; no real purchase or provider credential change was performed.
- Existing local/cloud AI refs diverge from main; preserve their work rather than force-resetting them during this UI task.
