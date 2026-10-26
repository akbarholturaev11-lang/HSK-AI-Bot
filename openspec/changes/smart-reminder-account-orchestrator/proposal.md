# Proposal

## Why

Telegram course reminders, Android per-device FCM and Android local WorkManager currently make independent study-delivery decisions, so their local day guards cannot enforce one account-wide study intent or a common opt-out. The [Master Plan](../../../docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md) locks D01–D14; this requested OpenSpec delta turns its source audit into testable contracts and dependency-ordered implementation tasks, without replacing its sole execution ledger.

## What Changes

- Plan one `users.id` preference authority with revision-safe writes, separate channel consent/provenance and OS capability, seamless migration of previously enabled compatible study channels, and durable global OFF. No second Smart activation prompt.
- Plan deterministic adaptive time/cadence, current goal/access rechecks, one reserved study job per account/local day, one selected endpoint and failure-safe provider attempts. Unknown delivery never authorizes a second channel.
- Plan Telegram bot/Mini App and Android V1 adapters, including server-job participation by both WorkManager and FCM. Keep unsupported old offline APKs outside migrated cohorts until safe cutover is evidenced.
- Plan additive migration, dry-run/shadow/canary gates, privacy/deletion, truthful outcomes and protected minimal admin control. Keep functioning rules as the baseline and stage automatic evidence-gated ML separately.
- Keep the core channel-neutral for learner iPhone PWA and macOS/Windows V2; no V2 transport is represented as implemented or required for V1 release.

These are proposed behavior changes for later implementation. This commit changes documentation only; it introduces no runtime API, database, flag, dependency, notification or deployment.

## Capabilities

### New Capabilities

- `smart-reminder-preferences`: Account study settings, authenticated CAS, channel consent, legacy compatibility and cutover eligibility (D01/D02/D06/D10/D14).
- `smart-reminder-orchestration`: Adaptive policy, account-day reservation, single endpoint, truthful receipts, safe fallback and category coordination (D02–D10).
- `smart-reminder-operations`: Migration/rollback, privacy, real learning attribution, protected admin control and staged optimizer governance (D09–D14).

### Modified Capabilities

None. CLI inventory contains `admin-control-center-ui`, `admin-real-analytics`, `admin-campaign-delivery` and `private-admin-campaign-media`. The first two were read in full: their responsive editor, authorization and source-bound aggregate requirements remain applicable and unchanged. Smart-specific requirements belong to the new capability above, rather than rewriting existing admin requirements.

## Impact

- Authority: repository `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `openspec/config.yaml`, localization policy and Master Plan §§3/13/16.1 decisions remain authoritative. Master Plan §17.20 records this planning run; no parallel progress tracker.
- Source baseline: fresh `origin/main` `6693901cca909189313dbb1b2747499206114598`; only the Master Plan document is imported from planning ref `1e337621e0fd8280fe8a1bec6715d734f2222651`, without merging its diverged history.
- Future backend areas: `app/main.py`, existing course/motivation/Android push services, bot course handlers, new scoped preference/job services and authenticated platform adapters, SQLAlchemy/Alembic, deletion/revocation hooks and canonical learning signals.
- Future clients: Telegram/Mini App settings/CTA and Android Profile, `WidgetStore`, `StudyReminderCoordinator`, WorkManager, FCM and study notification permission; Direct and Play parity. Future admin changes reuse existing template infrastructure, live protected commands and minimal-action UX.
- Observed risks: send-before-commit windows in Telegram/FCM, independent old APK worker, motivation default-ON mistaken for study consent, account-notice permission mistaken for study permission, stale preference writes, wrong-account devices and false displayed/causal metrics. Source details and bounded acceptance are in design/specs; production topology, installed fleet and real delivery remain unverified.
- Rollback: disable new dispatch, invalidate pending grants/jobs and preserve explicit OFF/revisions/provenance. Never blindly restore old senders, replay ambiguous attempts or destructively drop consent data.
- Excluded: runtime work in this task, billing/access/scoring/source lesson changes, Telegram SDK/auth redesign, transactional account-notice escalation changes, wholesale campaign migration, Admin PWA learner push reuse, invented weekly caps/TTL/ML/KPI values, production access or deployment.
