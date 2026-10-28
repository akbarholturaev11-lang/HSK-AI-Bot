# Proposal

## Why

Telegram course reminders, Android per-device FCM and Android local WorkManager currently make independent study-delivery decisions, so their local day guards cannot enforce one account-wide study intent or a common opt-out. The [Master Plan](../../../docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md) locks D01–D14; this requested OpenSpec delta turns its source audit into testable contracts and dependency-ordered implementation tasks, without replacing its sole execution ledger.

The owner's D15 extension adds personal widget behavior to this same plan. The existing Android widget already displays individual course facts, but its visual urgency follows fixed wall-clock hours. Widgets need the shared account learning context and personal rhythm, with Android first and later iOS/macOS/Windows adapters, rather than another independently learned schedule.

## What Changes

- Plan one `users.id` preference authority with revision-safe writes, separate channel consent/provenance and OS capability, seamless migration of previously enabled compatible study channels, and durable global OFF. No second Smart activation prompt.
- Plan deterministic adaptive time/cadence, current goal/access rechecks, one reserved study job per account/local day, one selected endpoint and failure-safe provider attempts. Unknown delivery never authorizes a second channel.
- Plan Telegram bot/Mini App and Android V1 adapters, including server-job participation by both WorkManager and FCM. Keep unsupported old offline APKs outside migrated cohorts until safe cutover is evidenced.
- Plan additive migration, dry-run/shadow/canary gates, privacy/deletion, truthful outcomes and protected minimal admin control. Keep functioning rules as the baseline and stage automatic evidence-gated ML separately.
- Plan one platform-neutral, versioned widget projection from the shared learning/personalization core. Android consumes it first; later iOS and paired macOS/Windows adapters retain the same semantic states, freshness, ownership and safe targets. Widget rendering never creates another study send or notification consent.
- Keep the core channel-neutral for learner iPhone PWA and macOS/Windows V2; no V2 transport is represented as implemented or required for V1 release.

These are proposed behavior changes for later implementation. This planning extension adds no runtime API, database, flag or dependency and enables no new notification or personalized widget renderer.

## Capabilities

### New Capabilities

- `smart-reminder-preferences`: Account study settings, authenticated CAS, channel consent, legacy compatibility and cutover eligibility (D01/D02/D06/D10/D14).
- `smart-reminder-orchestration`: Adaptive policy, account-day reservation, single endpoint, truthful receipts, safe fallback and category coordination (D02–D10).
- `smart-reminder-operations`: Migration/rollback, privacy, real learning attribution, protected admin control and staged optimizer governance (D09–D14).
- `smart-widget-personalization`: Personal study rhythm, real progress/goal presentation, safe passive rendering and a reusable authenticated contract for Android V1 and iOS/macOS/Windows V2 widgets (D15).

### Modified Capabilities

None. CLI inventory contains `admin-control-center-ui`, `admin-real-analytics`, `admin-campaign-delivery` and `private-admin-campaign-media`. The first two were read in full: their responsive editor, authorization and source-bound aggregate requirements remain applicable and unchanged. Smart-specific requirements belong to the new capability above, rather than rewriting existing admin requirements.

## Impact

- Authority: repository `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `openspec/config.yaml`, localization policy and Master Plan §§3/13/16.1 decisions remain authoritative. Master Plan §17.20 records this planning run; no parallel progress tracker.
- Source baseline: fresh `origin/main` `6693901cca909189313dbb1b2747499206114598`; only the Master Plan document is imported from planning ref `1e337621e0fd8280fe8a1bec6715d734f2222651`, without merging its diverged history.
- P1 continuation baseline: `origin/main@bedd14addc9e98ec9952c61d5e4b28685ed72fd1`; Master Plan §17.34 reconciles P0 with shared Direct/Play published-release gates and the owner-deferred cutover audit. Preserve new R2/private analytics behavior; dispatch-OFF storage proceeds without repeating fleet reads.
- D15 extension baseline: refreshed `origin/main@d897f65b9ca89f4936d6a58ad27e6283115dc6db`, preserving its Android update/deep-link/account-notice changes. Master Plan §17.31 owns this extension's source audit and implementation boundary; the existing read-only legacy bridge is a prerequisite, not implemented widget personalization or new dispatch.
- Future backend areas: `app/main.py`, existing course/motivation/Android push services, bot course handlers, new scoped preference/job services and authenticated platform adapters, SQLAlchemy/Alembic, deletion/revocation hooks and canonical learning signals.
- Future clients: Telegram/Mini App settings/CTA and Android Profile, `WidgetStore`, `StudyReminderCoordinator`, WorkManager, FCM and study notification permission; Direct and Play parity. Future admin changes reuse existing template infrastructure, live protected commands and minimal-action UX.
- Widget areas: the existing Android `widget/` projection/store/resolver/refresh/layout and their tests; an additive authenticated course-map projection from the shared backend; future Apple widget extension and supported Windows widget-provider integration with explicit host capability. Existing PWA installation or a Tauri desktop window alone is not an implemented OS widget.
- Observed risks: send-before-commit windows in Telegram/FCM, independent old APK worker, motivation default-ON mistaken for study consent, account-notice permission mistaken for study permission, stale preference writes, wrong-account devices and false displayed/causal metrics. Source details and bounded acceptance are in design/specs; production topology, installed fleet and real delivery remain unverified.
- Rollback: disable new dispatch, invalidate pending grants/jobs and preserve explicit OFF/revisions/provenance. Never blindly restore old senders, replay ambiguous attempts or destructively drop consent data.
- Excluded: runtime work in this task, billing/access/scoring/source lesson changes, Telegram SDK/auth redesign, transactional account-notice escalation changes, wholesale campaign migration, Admin PWA learner push reuse, invented weekly caps/TTL/ML/KPI values, production access or deployment.
