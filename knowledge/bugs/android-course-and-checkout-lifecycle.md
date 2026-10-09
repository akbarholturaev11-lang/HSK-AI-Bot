# Android course and checkout lifecycle regressions

Audit: 2026-10-08, based on `codex/local-ai` after the HSK 3.0 checkout repair.

## Causes and fixes

| Trigger | Failure | Required behavior and regression |
| --- | --- | --- |
| Pro checkout → HSK 3.0 checkout in one login | The session owner reused a ViewModel with the old immutable origin | Key by API origin; use the pending payment's actual plan. `SubscriptionCheckoutHostTest`, `SubscriptionCheckoutPaymentReviewTest`. |
| Close/reopen checkout while reads or receipt submission are pending | Old response overwrites the new offer or closes a different screen | Check checkout/receipt generations; collect navigation only in the displayed host. Still watch a successfully committed payment. `SubscriptionCheckoutLifecycleTest`, delayed receipt cases in `SubscriptionCheckoutHostTest`. |
| Image picker returns after changing product or payment step | An old receipt attaches to a different quote | Capture both model and receipt selection generation when launching the picker; invalidate preparation on changes. `pickerResultFromPreviousPaymentStepCannotAttachToNewQuote`. |
| Switch course while practice/exam/review has state or pending requests | Old questions, results and retries survive | Register the canonical fresh map level; reset old course state and reject requests before send and after response. `PracticeCourseChangeTest`. |
| A slower Profile read/save arrives after a course or access refresh | Old level/access overwrites the new profile | Preserve mutation flags/revision; reject superseded reads and reload after stale successful mutations. A failed old mutation must not cancel a newer refresh. `ProfileViewModelTest`. |
| Verified payment decision arrives during an existing access request | Approval is invisible until another navigation/notification click | Emit all authenticated decisions independently of notification permission. Coalesce Course refreshes and supersede Voice status reads. `PaymentDecisionMonitorTest`, `CourseRefreshQueueTest`, `VoiceCourseChangeTest`. |
| Leave Voice during start, send or delayed microphone initialization | Late responses revive the session or microphone | Invalidate session ownership, close abandoned sessions, stop on Back/disposal/tab exit, synchronize live engine start/stop. `VoiceCourseChangeTest`, `VoiceScreenBackTest`. |
| Start a skip test for a genuinely locked lesson | The normal playable-lesson endpoint correctly rejects it | Fetch only quiz material through `/api/v3/android/course/skip-test/{order}`. Validate owned active level/order/material refs; never populate the playable lesson cache or consume a lesson start. `SkipTestRepositoryContractTest`, `SkipTestViewModelTest`, Android course/Foundation API tests. |
| A skip unlock request arrives after the active course changes | An old test can advance the newly selected course | New APKs send `expected_level`; check it under the existing server user lock before any progress mutation. Treat it as a precondition, never a course override. Keep the preview → switch → old unlock API regression. |

## Rules for future changes

- A session-owned ViewModel must not keep an immutable screen parameter under an unrelated key.
- A server-confirmed course change closes temporary destinations and invalidates course-dependent work. Cached or failed map reads cannot confirm a switch.
- After a successful track POST, retry its map GET; repeating the level POST can reset progress.
- Do not silently discard access refresh requests while another request is running. Coalesce or supersede them, without an automatic infinite retry.
- A payment notification is a hint. Verify current login, device epoch, payment ID and decision before refreshing access or showing rejection UI. Preserve deduplication.
- Closing a UI cannot undo a payment or progress mutation already committed by the server. Suppress stale UI actions and reread authoritative state.
- Keep Foundation, HSK 3.0 entitlement, daily allowance and normal lesson-order checks. Skip-preview is quiz material, not permission to open or complete a lesson.
- Bind a course mutation to the course where its attempt began. UI generation checks alone cannot protect a server request already sent before navigation.

## Automatic prevention and release order

`.github/actions/android-flow-regressions/action.yml` runs actual Compose course,
skip-offer, Voice and payment-monitor regressions for Direct and Play, plus the
Direct checkout cases. Both `android-ci.yml` and `android-release.yml` call it;
release runs it before signing and publication. JVM, lint, interface/flavor,
translation and content checks remain enabled. Emulator reports are retained.

Deploy the authenticated skip-preview backend endpoint before releasing an APK
that calls it. Existing APKs require a new signed release to receive native fixes.
No database migration, lesson content rewrite, price or approval-policy change is
required. Validate the signed build's course switch, receipt picker and Voice
microphone behavior on the affected physical phone after release; fake API and
emulator tests cannot establish physical-device or production-provider behavior.
