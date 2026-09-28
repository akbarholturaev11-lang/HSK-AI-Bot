# Trial anti-abuse cloud handoff

Status: code complete on codex/cloud-ai, NOT promoted to main.

## Trial-specific commits

1. c5fa58da6668a919f502fa7ede62b60425827967
   - fix: make pro trial start atomic
2. 251dc57c1b63a257e1b0f6dd3b49168d2ccdffab
   - feat: add trial abuse shadow telemetry
3. 32cd89d552487ec06c91aee5827efe8b189ed443
   - feat: add trial abuse admin reporting
4. 8663341ce779bc5669ecec9851cbdb78610a951d
   - test: cover trial abuse shadow flow

## Behavior contract

- Existing ProTrialService eligibility remains authoritative.
- V1 is shadow-only: no risk score and no new deny rule.
- Mini App observes account age + Railway X-Real-IP HMAC.
- Android observes the same plus the existing server-side installation_key_hash.
- Raw IP, raw installation keys, card/payment identifiers, email and OAuth
  tokens are not stored.
- Risk telemetry uses savepoints and is fail-open; telemetry failure must not
  block a valid trial.
- Trial API responses do not expose risk signals.
- Payment, referral and entitlement state columns are unchanged.

## Current branch conflict

At handoff time:
- main: 055c9c199e879eef8eb742afe21fd4f025042984
- cloud head before this document: 8663341ce779bc5669ecec9851cbdb78610a951d
- main and codex/cloud-ai diverged after a listening-question fix landed on main.
- Draft PR #106 is intentionally NOT merge-ready.
- GitHub Actions did not start because the PR has no merge ref while conflicts
  remain. Do not treat CI as passed.

Do not force-reset either branch. Reconcile the unrelated listening/universal
mistake changes normally.

## Alembic dependency

This cloud branch already contained 0091_course_mistake_targets before the
trial task started. Therefore the new 0092_trial_risk_events currently revises
0091_course_mistake_targets.

If the existing 0091 work is promoted first, keep the chain as-is.

If the trial feature is promoted independently, DO NOT cherry-pick/deploy the
0092 migration unchanged. Rebase/renumber the trial migration against the
actual migration head on the clean target branch and verify that Alembic has
one head.

## Required local verification

Run from a clean local worktree after resolving main/cloud divergence:

    python -m compileall -q app tests
    python -m unittest       tests.test_pro_trial_service       tests.test_trial_risk_service       tests.test_trial_risk_entry_points       tests.test_admin_limits_api       tests.test_trial_entry_points       tests.test_referral_trial_contract       tests.test_entitlement_state       tests.test_entitlement_engine_limits
    alembic heads

Also run the repository's normal backend targeted tests. If a Postgres test
database is available, run upgrade/downgrade verification for the final
migration chain.

After code changes are reconciled locally, run:

    graphify update .

Only after all required checks pass should the intended trial commits be
promoted to origin/main. Then sync codex/local-ai and codex/cloud-ai back to
main according to AGENTS.md.
