# Canonical account and child-row lock order

Manual checkout, admin review and course-track mutations must lock the canonical
User before payment, progress or track-state rows. A course switch that first
locked progress/track state could deadlock against an HSK 3.0 grant holding the
User lock. When the target track did not yet exist, the same race could create
two states and violate its unique owner/track constraint.

`CourseTrackService.switch` and `change_level` now lock and refresh the User
before access checks or child-row mutations, matching checkout/admin grant.
Do not move this lock below a state query or reuse stale access after waiting.

Regression: `NativeHsk30ConcurrencyTests.test_course_switch_and_admin_grant_share_user_before_track_lock_order`
uses real PostgreSQL and covers existing and absent target track states. It
reproduced both failures before the fix. Keep the canonical receipt/admin race
tests as well: both cases rely on the same account-before-child ordering.

Referral rewards modify a different user's non-key fields while native message
inserts hold FK key-share locks. Their narrowly scoped `FOR NO KEY UPDATE`
reward-owner lock serializes rewards without conflicting with those FK locks;
the mutual-referral PostgreSQL test protects this separate requirement.
