# Smart delivery analysis contract

The execution ledger is `SMART_REMINDER_MASTER_PLAN.md`, §17.55. This contract
defines the dormant P6 6.1a component, not live instrumentation or a rollout.

`SmartReminderAnalysisService.capture_job(user_id, job_id)` is an internal,
explicit operation over a committed owned job and its attempts/Android grants.
It owns a separate User-first transaction. A delivery transaction never calls
or depends on it; analytics failure cannot erase an already committed outcome.
There is no capture endpoint, production worker, provider, learner input or
automatic inventory scan. Only current reviewed v1 Android/Telegram policy
families with matching selected channels qualify; shadow/unknown policy jobs
are excluded. Source timestamps must be neither future nor older than 90 days.

| Analysis stage | Required source | Interpretation |
| --- | --- | --- |
| `reserved` | Owned selected v1 job's creation | Logical reservation, not a send |
| `in_flight` | Attempt's stored start | IO boundary may have been crossed |
| `provider_accepted` | Accepted attempt and resolution time | Provider acceptance, no display/read/learning proof |
| `client_posted_unverified` | Matching Android attempt and original immutable posted receipt | Client reports OS posting, still unverified display |
| `confirmed_not_displayed` | Matching Android attempt and original pre-call-decline receipt | This attempt did not reach the OS call; no alternate or budget refund |
| `outcome_unknown` | Resolved unknown attempt or matching unknown receipt | Uncertain; never infer failure, non-display or fallback eligibility |
| `cancelled`, `expired` | Terminal job and transition time | Job state, not proof that an earlier external attempt disappeared |
| `definite_failure` | Explicit resolved attempt state | Only the recorded boundary's failure |

The existing attempt enum alone cannot prove `verified_shown` or a client post
without its matching receipt. Shown, read, opened and attributed server learning
remain **unavailable**; these counters are not fabricated zeros or inferred from
FCM acceptance, widget/app opens or XP. Candidate/suppression instrumentation,
trusted open/learning linkage, production integration, denominator/experiment
and model evaluation remain separate parent 6.1/6.2/P7 work.

Migration `0137_smart_analysis` adds two tables:

- `smart_reminder_analysis_events`: owner/job FKs, a hash of immutable
  source-and-stage identity, a fixed stage/reason/channel and source time/expiry.
  No token, device/session identifier, body, copy, lesson, address or arbitrary
  payload. The owner lock and unique owner/key prevent duplicate/racing capture.
- `smart_reminder_analysis_monthly`: UTC month, stage, channel and fact count
  only. An inserted raw fact increments its bucket in the same transaction;
  duplicate capture increments nothing. These are stage facts, not unique
  learners/messages, a causal learning effect or a denominator.

## Retention and privacy boundary

| Class | Policy |
| --- | --- |
| New analysis detail | D21: expires at original source time + 90 days |
| Anonymous monthly totals | D21: current UTC month and eleven preceding buckets |
| Existing course progress, XP, canonical learning | Unchanged; analysis retention never deletes them |
| Consent/OFF, account-day jobs, attempts, grant/receipt tombstones | Separate operational evidence; no new TTL or replay/reset authority |
| Account deletion | Canonical purge explicitly removes own raw analysis; FK cascade is a second guard. Anonymous totals contain no account/source link. Submitted deletion prevents new capture. |

The monthly interpretation retains at most twelve complete/calendar buckets;
expiry is not extended by late capture. This is a minimal class review under
the approved D21 scope, with no new clickstream or personal feature store.
No private job state is exported into Redis/R2 or public metrics. Future small
cohort/experiment exposure requires its own reviewed read projection.

`python -m scripts.smart_reminder_analysis_retention` returns anonymous expiry
counts only. `--purge-expired --limit 128` explicitly removes at most one raw
page and one monthly page; valid limits are 1–128. It never deletes a source
job, attempt, grant, preference, course/XP record or another non-analysis class.
The operator must run enough pages to drain a backlog; no production schedule
or execution is implied. Source-time checks refuse expired replay after raw
deletion, and never recreate an old fact to increment totals again.

No initializer is run against an existing database. The reviewed empty-QA
initializer advances to 0137 and leaves both new tables to real migrations.
Downgrade refuses either populated analysis table rather than deleting data.
Disabling capture changes no delivery authority; preserve all consent/day/grant
guards and operational evidence during rollback.
