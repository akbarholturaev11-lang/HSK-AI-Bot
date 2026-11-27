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
| A lesson completion request arrives after the active course changes | The old result can award progress/XP to the newly selected course | Send the immutable lesson level and check the optional `expected_level` precondition under the same fresh user lock before progress, allowance, mistakes or XP writes. Keep delayed-dispatch client and preview → switch → old completion server regressions. |
| Open a lesson while the course map refreshes | Android/Desktop lesson start locked progress before the account, while the map locked the account first; PostgreSQL detected a deadlock and returned `503` | Lock and refresh the canonical account before deriving the lesson level or locking progress, matching map/completion. Keep the PostgreSQL parallel map/lesson regression in `tests/test_native_course_lesson_locking.py`; an APK update cannot repair this server lock inversion. |

| Process stops after replacement credentials persist but before widget relink | The previous account cache can survive beside the new credentials | Clear only the old widget projection before persisting replacement credentials, retain the existing post-token link callback, and hold the auth-generation lock through widget acceptance. `AuthRepositoryTest` injects an interrupted credential write; `WidgetPersonalContextTest` covers late success/401, epoch/revision/time replays and foreground invalidation. |
| Restore Pro after a cancelled Lava term expires | The old contract hides every buy action in Direct checkout | Preserve the cancellation status while paid access is active. Expose the current plan catalog once that access ends. The Android Lava API regression verifies expiry, restore attribution and a new invoice. |
| Reopen a personalized lesson after its picture deck or optional-card plan changes | A rendered numeric index points at different material, skipping an unshown pronunciation/teaching card | Persist the existing `material_ref` beside the original-deck index atomically. Resolve legacy indices through the original served order; an omitted optional card falls forward to retained material. `LessonPictureReviewTest` covers removed plans, old APK positions, omitted cards and the same synthetic deck; `PictureReviewDeckTest` verifies real DataStore write/clear compatibility. |
| Replace or clear an account while an old lesson save/completion is pending | Global per-level resume keys could carry the old learner's position to the next account | Clear resume positions at both auth lifecycle boundaries and bind each lesson's existing store to that local generation. Check the generation inside DataStore edits, including completion clears. The native DataStore regression proves a late old write/clear cannot affect the new login. |
| Checkout instrumentation starts the real application | The app can fall through to auth or network setup beyond the fixture; a script-line export is lost because the emulator runner starts each line in a fresh shell | Set the invalid HTTPS QA origin in the runner step's `env`, inherited by every Gradle command, with the separate QA app identity. The native DataStore test fails closed unless the package is `.qa`. Stub both checkout transports and assert current fake request ownership. Keep the unchanged Direct/Play signature guard. |

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
