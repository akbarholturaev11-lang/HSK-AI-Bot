# HSK AI Admin PWA — start Codex from the current checkpoint

**Authoritative single entry point: [CODEX_RESUME.md](CODEX_RESUME.md)**. Do not rely on historical/status snapshots pasted into old chats. Detailed implementation/test history remains in `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` (latest sections at bottom). Rules are in `HSK_AI_ADMIN_PWA_TEMP_RULES.md`.

## Copy this into Codex

> Continue HSK AI Admin PWA **from the current real GitHub code**. Repo: `akbarholturaev11-lang/HSK-AI-Bot`, ONLY branch `codex/admin-pwa`.
>
> FIRST read `docs/admin-pwa/CODEX_RESUME.md` in full and follow its prerequisite documents and branch/safety rules. Check CURRENT branch HEAD and diff with `main`. Do NOT redesign/redo the completed Google+Telegram, passkey login and action-specific WebAuthn foundation. Do NOT merge/rebase into `main`, deploy, enable `ADMIN_PWA_ENABLED`, or change legacy Telegram `/admin.html`.
>
> Next: inspect real `app/main.py::_review_admin_payment` and its payment/entitlement/notification dependencies. **It commits internally; blindly calling it after a step-up receipt consume BREAKS atomicity.** Prepare and implement a safe backward-compatible payment review unit of work: exact server-validated operation bound to one-use passkey step-up, reviewed payment/entitlement and audit/outbox in ONE transaction. No new dangerous PWA write route until atomicity and legacy behavior are verified by tests. Refactor only what is safely justified by code/tests. Continue further increments in order from CODEX_RESUME.md, update handoff and commit only to the feature branch.
>
> Run exact Admin PWA tests and both GitHub Actions jobs including real PostgreSQL migrations/concurrency; report exact commits and any failures. Last verified CI is https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40029175593 (152 passed / 3 PG-only skipped; 3 real PG passed). That is the LAST checkpoint, not proof for newer changes. Legacy fresh DB Alembic revision 0011 is independently broken; do not claim fixed. UI requires actual V10 HTML and in-repo UI skills.
>
> Work on code, not another plan. If unsafe to integrate payment commit path, do not expose write API; isolate the blockers, add safe tests or reversible refactoring and document next safe action.

## Guardrails

- `ADMIN_PWA_ENABLED=false` until separately approved.
- Latest code wins over historical handoff prose.
- Keep V10 real-data, UZ/RU/TJ, and full test/commit/report requirements.
- Never invent passkey physical-device testing, staging deployment or production verification.
