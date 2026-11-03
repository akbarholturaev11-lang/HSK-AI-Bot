# Offline study-time comparison

Authority: [Master Plan](SMART_REMINDER_MASTER_PLAN.md), D09 gates §17.50 and
owner scope correction §17.73. This is P7's local diagnostic tool, independent
of the application and all production dispatch. It changes no database,
preference, provider, source result or runtime model selection.

`app/services/smart_reminder_offline.py` trains one shared circular nearest-neighbor
regressor in memory and compares it with the **actual** personalized rule
`evaluate`, using the approved 60-minute/3–5-day habit calibration. There is no
new dependency, LLM call, model registry or new source instrumentation.

## Run

```sh
python3 scripts/smart_reminder_offline_eval.py \
  --input /path/to/reviewed-snapshot.json \
  --cutoff 2026-10-24T00:00:00+00:00 \
  --min-group-accounts 5
```

The path and cutoff are explicit operator inputs. The cohort floor is an
explicit privacy setting (at least two distinct accounts), **not** ML confidence,
sample-size/power or admission approval. `--neighbors` defaults to five and is a
fixed candidate hyperparameter, not a product policy or eligibility threshold.
Do not tune it using held-out outcomes. The command writes aggregate JSON to
stdout, scrubbed errors to stderr, and never modifies input or exports a model.
It imports no app configuration/session and has no database fallback.

## Input contract

`Dataset` and `Snapshot` in the service are the strict versioned JSON contract:

- `version`: `smart-offline-time-v1`.
- `data_kind`: `synthetic` or `reviewed_snapshot`; QA must remain synthetic.
- `generated_at`: timezone-aware snapshot extraction instant.
- `snapshots`: at most 4096 rows; file at most 16 MiB, no silent truncation.
- Each row has an export-specific salted 64-hex `learner_key`, V1 `platform`
  (`android`/`telegram`), `locale` (`uz`/`ru`/`tj`), the real as-of `PolicyContext`,
  `history_available_at`, optional `outcome` and `outcome_available_at`.
- `context.studies` and `outcome` use `VerifiedStudy`: a 64-hex pseudonymous
  original reference, activity type, original aware `accepted_at`, local
  `course_day` and integer XP. No names, canonical IDs, tokens or transcripts.
- `history_available_at` maps every history reference to its original proof
  availability instant, or null if unknown. At most 128 history entries per row.
  A later receipt proving an old event cannot be treated as known at the old
  event time. Known original facts/availability cannot change between snapshots;
  an unknown availability may become known without backfilling the earlier row.
- `outcome` is the original positive lesson/test/training completion selected by
  the reviewed export protocol, after the decision on its frozen local date.
  Missing/unverified/zero-XP/reward outcomes stay unobserved, never negative.
  It measures a positive completion clock, not first app/session opening.

Only original server evidence and historically known preferences/access/progress
may populate a real snapshot. The current mutable context reader cannot
reconstruct past preferences merely by changing `observed_at`. There is no real
as-of export identified or new exporter in this change. Do not fabricate that
provenance or feed current state into a retrospective historical prediction.
The file is an operator-owned private input, not an anonymized long-term store.
The tool refuses expired private facts outside 90 elapsed days and future
extraction times. It never creates private files; retention/account deletion of
externally supplied exports remains the export owner's responsibility. No
claim is made that app account purge can discover arbitrary operator files.

## Validation and outputs

The temporal cutoff is fixed before fitting. Training decisions **and original
label availability** must precede it. Later decisions are held out; the model
never refits or learns from those labels. Per-row original history must have
been available before that decision. Duplicate account/local-date observations,
reused labels, conflicting original proofs and unknown JSON fields are refused.
This follows the [training/test separation principle](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).

Features contain the rule's circular clock, weekday phase, distinct active days,
observed gap and concentration. Account keys, platform, locale and target labels
are excluded. Rule consent/OFF, manual time, access, goal, quiet, timezone/DST and
source-coverage guards remain authoritative. The model averages nearby **past**
circular targets; equal-distance ties include all tied samples. Opposite/ambiguous
predictions fall back to the rule clock in the same paired comparison.

The report contains versions, normalized input hash, cutoff, exclusion counts,
train/test counts and circular absolute minute errors. Errors are averaged per
account first, then across accounts, so frequent learners do not dominate the
reported average. `model_minus_rules_minutes` is negative for less prediction
error, **not causal learning uplift**. Each platform, locale, their intersection,
rule time source and seen/unseen learner group exposes its counts. Small or
unsupported groups have null errors, never an invented zero or confident benefit.
No per-user predictions, keys, references, features or training records leave RAM.

Every report has `ml_ready=false`, `dispatch_allowed=false` and learning benefit
unavailable. Synthetic success and prediction error cannot establish retention,
notification benefit, D09 confidence/advantage, D12 statistical power or release
readiness. Real baseline, reviewed held-out data, registered controlled outcome
validation and normal canary/rollback/consent gates remain required. Existing
rules must not wait for an unproven model. Further optional trace/ML framework
expansion is deferred while those real inputs are unavailable; D24 artwork stays
last. Rollback can remove this standalone tool without affecting current rules.
