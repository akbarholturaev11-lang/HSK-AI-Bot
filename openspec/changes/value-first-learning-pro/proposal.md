# Proposal

## Why

PWA and Android already take an eligible learner from onboarding to a real course part. Their completion views primarily celebrate points and accuracy, so a learner can finish a first part without seeing what to revisit or understanding how to continue toward the goal they selected.

## What Changes

- Use the existing confirmed completion view to name the lesson topic, show verified review evidence when available, and give one action that leads back to the existing learning path.
- Make the existing Daily Plan, Mistakes and eligible next-part destinations understandable at that handoff. Preserve the current day's task identities and server access decisions.
- Explain the relevant verified Pro benefit in the existing access context. Keep learning useful in Free and preserve Trial, Android Play restrictions and all payment terms.
- Measure the outcome using existing analytics, diagnostics and rollout controls. Keep the HSK1 checkpoint experiment's historical meaning and expose data gaps explicitly.

## Capabilities

### New Capabilities

- `course-learning-value` — confirmed result, actionable next step and accurate contextual access copy for learner PWA and Android.

### Modified Capabilities

- None. Existing `admin-real-analytics` aggregate, ownership, and privacy requirements apply unchanged.

## Impact

Baseline is GitHub `origin/main` at `5bbbf707ad5874284d1a509561abb54ceee48055`. Existing scoped work remains governed by [Li onboarding](../../../docs/onboarding-li/IMPLEMENTATION_CONTEXT.md), [Android guest entry](../android-li-guest-onboarding/), [adaptive reviews](../course-adaptive-lesson-engine/), [interactive flashcards](../course-interactive-flashcards/), [analytics integrity](../../../docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md), [monitoring](../../../docs/monitoring/MONITORING_CONTEXT.md) and the [joint performance contract](../../../docs/PERFORMANCE_BACKEND_PWA_GOALS_REQUIREMENTS.md). These cover their respective stages. The learning handoff spans stages and needs one acceptance contract.

Change the authenticated result adapters for learner PWA and Android, the existing result views and the applicable access context. Keep Telegram Mini App compatibility and the Desktop freeze. Course order, content, scoring, progress, authentication, entitlements, pricing and payment rules retain their existing owners. Use an additive display projection and an isolated feature branch. Rollback drops the optional projection and returns to existing result controls. Production rollout and payment changes are outside this worktree.
