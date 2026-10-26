# HSK AI Smart Reminder — next-chat entry point

> **Purpose:** A compact navigation and continuity file requested by the project owner on 2026-10-26. This is **not** a second execution tracker. The sole authoritative Smart Reminder decisions and progress ledger is `docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md`; this file only points future Codex/ChatGPT sessions to that ledger and the current OpenSpec tasks.

## Start here in every new chat

1. Read `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, and `openspec/config.yaml`. Honor the repository's Git, QA, security and UZ/TJ/RU localization policies.
2. Read `docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md`, **especially the latest numbered checkpoint at its end**; do not guess state from a prior chat. D01–D14 are owner-approved product decisions and must not be silently revised.
3. Read `openspec/changes/smart-reminder-account-orchestrator/{proposal.md,design.md,tasks.md}` and all three `specs/*/spec.md` files; Codex reported successful official strict OpenSpec validation on 2026-10-26. This means *planning validation only*, not tested or deployed Smart Reminder.
4. Fetch **current** `origin/main`, compare it with the latest Smart implementation branch and refresh relevant source files before any code change. The original P0 handoff branch **`codex/smart-reminder-p0-handoff-20261026`** was already merged via PR #233. The source-audit branch **`codex/smart-reminder-p0-coverage-20261026`** was merged via PR #235. The focused regression branch is **`codex/smart-reminder-p0-tests-20261026`**, based on historical `main@47a0554e2bbb2875fbf9e0d798a59c6f7737192e`. These are historical navigation references, not a guarantee of current HEAD. Work in a clean main-based worktree if the branch has diverged; do not force-push, merge unrelated commits or overwrite other agents' work.
5. Continue from the **latest unchecked work in `tasks.md`**, with evidence recorded **only in the Master Plan**. First stage **P0**: 1.1 sender ownership/source map, 1.2 channel consent/ON/OFF semantics, 1.3 historical APK/production fleet (authorized observation), 1.4 canonical learning/deletion signals and runnable baseline tests. No P1–P8 step is complete merely because OpenSpec spec files exist.
6. Before promoting any implementation to `main`, execute focused tests/CI, observe intended changes, verify no loss of unrelated commits, and re-read `origin/main`. If code cannot be tested in the current environment, leave a precise test handoff; **do not** claim completion/deployment.

## Current safety constraints — never infer these as deployed

- V1: Telegram bot/Mini App and Android; iPhone learner PWA and Desktop are later V2 adapters.
- Study reminders: one authorized logical study intent per canonical `users.id` and local day; one eligible endpoint; preserve explicit channel OFF and durable account OFF. D01 seamless migration cannot create consent on another channel. Never assume notification provider acceptance equals OS display/read.
- Current Android local WorkManager can post independently of the proposed server ledger; **unknown older/offline APKs prevent any truthful global physical exactly-once guarantee**. Don't enable a parallel new dispatcher before fencing/cutover proof.
- The existing Telegram course time-picker **Cancel** is setup cancellation, not proof of persisted study OFF. Mini App `/api/v3/notify` controls motivation, not canonical Smart study consent. Native `/push/preferences` is device-scoped and its `notifications_allowed` represents account notices rather than the study channel.
- Keep payment, subscription, Android transactional notice fallback, Admin PWA technical push, grading and Pro/Play entitlement behavior unchanged.
- Railway production read access was previously declined; no live instance settings, database stamp or real provider delivery were verified. Never reuse or solicit secrets in documentation.
- Source audits were performed via the GitHub connector. The isolated local container cannot clone github.com; however, GitHub Actions **Smart Reminder P0 regression run #40324231283 passed 45/45 real Python backend tests** (5 new). This is not Android JVM/device, staging, production FCM or Smart dispatch validation; read the latest Master Plan checkpoint for exact SHA and outstanding evidence. Do not mark P0 fully complete based only on these tests.

## What to request of a future agent

“Continue HSK AI Smart Reminder from `docs/smart-reminders/NEXT_CHAT_CONTEXT.md` and the **latest** checkpoint in `SMART_REMINDER_MASTER_PLAN.md`. Read the OpenSpec `smart-reminder-account-orchestrator` tasks and current `main`. Finish the next P0 evidence/test slice without touching unrelated user code. Write exact source SHA, changed files, tests executed, blockers and next step in the existing Master Plan; never call planning complete product implementation.”

## Source of truth / direct paths

- Canonical decisions and execution journal: `docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md`.
- Formal requirements and tasks: `openspec/changes/smart-reminder-account-orchestrator/`.
- The source-audit and first executed backend CI checkpoints include **§17.21–§17.23**. Always read the **latest checkpoint at the END** of the main-branch Master Plan for evidence, unexecuted tests and blockers; do not assume a fixed section number remains current.
- Treat this file as **navigation only**; do not maintain a parallel progress checklist here.
