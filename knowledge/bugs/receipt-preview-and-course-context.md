# Preserve immutable receipt and opened-course identity

## Receipt preview

Cause: a separately approved payment replenished the preview ticket while an
older receipt remained pending. Reusing the receipt minted another AI cap.

Fix: claim under User lock; reject a receipt with a current pointer or any prior
preview budget. Duplicate historical rows fail closed for preview AI only.

Risk: never delete financial rows, change a cap, or suppress independent paid or
trial access to repair this state. Do not replenish on HSK3 unlock/manual grants.

Prevention: `tests/test_payment_review_preview.py` models approval and receipt
resubmission using real SQLite repositories, plus duplicate budgets and priority.

## Course writes and private reads

Cause: UI course state can outlive another device's course switch. A caller's
lesson order alone does not identify the opened lesson. Separately, unlimited
admin access cannot be inferred solely from a named Pro state/reservation.

Fix: lock User before progress; use client course only as a stale precondition,
never an override. Reject mismatched saved progress instead of relabelling its
completed count. Honor the shared entitlement's unlimited result and check
required foundation before spending a slot.

Risk: preserve optional fields for old clients, shared limits and existing
client-decided weak-score skip behavior. New clients send the course snapshot.

Prevention: `tests/test_miniapp_course_context.py`,
`tests/test_i18n_miniapp_reservation_asgi.py`, Desktop API/bridge and paired
macOS/Windows browser tests. The reservation boundary audit requires the locked
identity lookup before downstream progress/entitlement work.
