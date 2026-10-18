# AI_RULES.md

## Main Rules

1. Follow the session startup order in `AGENTS.md` before changing code or project docs.
2. Do not redesign or rewrite the whole project; keep architecture changes within the requested task scope and ask if a broader redesign is needed.
3. Do not remove working code; remove code only when it is proven dead and the cleanup is in scope, and record the evidence and reason.
4. Preserve existing business logic.
5. If database schema changes, document the migration.
6. If payment/subscription/access logic changes, document the risk and never silently alter existing payment policy.
7. If something is unclear, inspect the code first instead of guessing.
8. Do not invent features or business logic that are not present in the project; inspect the existing contract first.

---

## Scope- and risk-based testing

Select checks by feature and regression risk rather than running every Mini App
flow after any change. For important changes, include the affected API/unit
tests, smoke/e2e path, and relevant security or business-flow regression.

- UI/navigation: changed viewport and route render without console errors.
- Lesson/quiz/homework: changed route, answer/score/submission and backend
  progress persistence.
- Telegram/auth: changed login/return-to-bot route and safe non-Telegram fallback
  where supported.
- Paywall/payment/access: relevant free/pending/approved/rejected cases with
  server-authoritative access decisions.
- Offline/localStorage: check fallback only where the client implements it.
- Query parameters like `?lesson=5` or `?tab=` when related routing changes.

Run broad Playwright E2E only for cross-cutting changes involving multiple
flows. Documentation-only edits need Markdown/reference/diff checks, not
unrelated browser E2E. Never report unexecuted tests as passed.

---

## Git Push And Main Branch Rule

Git branch, recovery, test, and push/promotion rules are maintained in `AGENTS.md` under “Git intizomi”. Follow that single repository-wide policy; this file does not define a separate branch count or push workflow.

---

## Desktop DMG/EXE Parity Rule

- macOS DMG and Windows EXE desktop apps are a paired product and must stay functionally aligned.
- If a feature, user-visible behavior, UI flow, backend/API contract, setting, security fix, or update behavior is added or changed in one desktop app, implement and test the corresponding change for the other app in the same task, adapted to that operating system.
- Do not mark the task complete or commit a one-sided desktop change unless the user explicitly limits the request to one platform.
- If exact parity is technically impossible because of an OS-specific limitation, document the reason, provide the closest safe equivalent for the other platform, and report the remaining difference clearly.

---

## Desktop Coming Soon Activation Rule

- Desktop UI blocks marked as `soonBlock`, "Soon", "Tez orada", or placeholders must stay in their current in-place location until the real feature is implemented.
- When one of these placeholder blocks becomes functional, remove the disabled/soon wrapper from that same block and connect the existing in-block button, row, or primary action to the real flow.
- Do not add a separate duplicate button, separate card, or extra CTA next to the placeholder unless the user explicitly asks for a redesign.
- Do not show invented progress numbers while activating a block. Keep `NO_VALUE` or verified backend data only.
- Preserve the current layout and parity across macOS and Windows desktop builds.

---

## Memory Discipline Rule

Do not treat `PROJECT_MEMORY.md` as a diary.

Before updating memory, ask internally:

> Will this help another AI assistant understand, debug, or safely continue this project later?

If the answer is no, do not update the memory file.

Write only important decisions and important changes.
Keep entries short.
Do not document every small edit.
Do not duplicate Git commit history.
Update the relevant topic section instead of appending a dated task log; keep files-touched and follow-up summaries in the task response.

---

## What Counts as Important Change

Update `PROJECT_MEMORY.md` if the change affects:
- Architecture
- Database schema
- Payment logic
- Subscription logic
- User access logic
- AI prompt behavior
- Course/lesson logic
- Deployment configuration
- Environment variables
- API endpoints
- Major bug fixes
- Security-sensitive logic
- Important business decisions

Do not update `PROJECT_MEMORY.md` for:
- Small text changes
- Emoji changes
- Minor CSS changes
- Typo fixes
- Console log cleanup
- Small refactoring with no logic change
- Temporary experiments

---

## Security Rules

Never store these anywhere in memory files:
- API keys
- Bot tokens
- Passwords
- Real `DATABASE_URL` values
- Webhook secrets
- Private links
- Payment credentials
- Admin private information

When documentation needs a credential example, use the variable name from `.env.example` and a non-secret placeholder value; never copy a real credential.
