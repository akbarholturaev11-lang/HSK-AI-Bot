# Smart analysis background capture: owner contention and shrinking timeouts

- **Cause:** reconciliation and baseline capture used blocking canonical User
  locks and passed the remainder of one 2-second tick budget to each operation.
  A busy owner consumed the tick and cancelled SQL. A healthy capture near the
  tick boundary could also be cancelled despite taking less than 2 seconds.
- **Evidence:** Railway PostgreSQL on 2026-11-14 reported cancellation while
  locking `users` at 04:56:18.769 and 05:18:12.095 UTC, immediately followed by
  reconciliation warnings; baseline cancelled on the same physical tuple about
  two seconds later. The failed SQL matches the first lock in `capture_job()`
  and `observe_member()`. These logs identify the waiter, not the blocker; no
  claim is made about the historical production lock holder. A local PostgreSQL
  regression uses actual `BotBlockStatusService.handle_send_success()` User
  update/flush as a known, uncommitted competing transaction.
- **Fix:** background reconciliation/aggregation request `FOR UPDATE SKIP LOCKED`
  on User. An existing but locked owner is explicitly `deferred`, never a
  missing owner, measured zero or capture failure. Release the observation
  transaction and revisit through the existing durable cursor pass. Direct
  service callers retain their existing blocking lock by default.
- **Budget:** the tick deadline now limits admission of new work. Each admitted
  operation gets the full existing timeout, rather than the tick's shrinking
  remainder. With the default settings a tick can take up to roughly four
  seconds plus cancellation/transaction cleanup: two seconds of admission and
  at most one additional two-second operation. Batch size and minute interval
  remain unchanged. Genuine operation timeouts still warn with `reason=timeout`;
  other exceptions remain visible without SQL, user IDs or exception text.
  Each existing scan logs anonymous INFO counts so production verification can
  distinguish actual capture/recovery from a stopped or endlessly deferred scan.
- **Safety:** keep User-first locking and fresh deletion/block checks, separate
  committed delivery and projection transactions, source-stage deduplication,
  monthly atomicity and parent cancellation. `pass_finished` still means cursor
  traversal, not complete fact coverage, especially when `deferred > 0`.
- **Regression:** `tests/test_smart_reminder_analysis_reconciliation.py` covers
  healthy work crossing the admission deadline, busy-owner deferral with another
  owner captured in the same tick, replay, missing-owner distinction, and real
  failures remaining visible. `tests/test_smart_reminder_baseline_outcomes.py`
  covers the same busy-owner recovery and connection release for aggregation.

Analytics Impact: no new learner event, denominator or metric definition. The
change repairs optional projection scheduling; missed facts retain replay and
deduplication. Monitoring Impact: no learner route or intake changes. Expected
owner contention has its own anonymous result count; real failures still warn.
