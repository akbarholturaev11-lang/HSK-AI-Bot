# AGENTS.md

## Purpose

This file gives instructions to Codex and other AI coding assistants working in this project.

Before making any code changes, always read:

- `PROJECT_MEMORY.md`
- `AI_RULES.md`

These files contain the project context, architecture, important business logic, rules, risks, and memory update policy.

---

## Required Behavior

1. Read `PROJECT_MEMORY.md` before making changes.
2. Read `AI_RULES.md` before making changes.
3. Understand the current project architecture before editing.
4. Make the smallest safe change possible.
5. Preserve existing working logic.
6. Do not redesign the project unless explicitly requested.
7. Do not invent missing features or business rules.
8. If something is unclear, inspect the code first instead of guessing.
9. Never store secrets in any memory file.
10. After important changes, update `PROJECT_MEMORY.md`.

---

## Memory Discipline

`PROJECT_MEMORY.md` is not a diary and not a changelog dump.

Only update `PROJECT_MEMORY.md` when the change is important for future AI assistants to understand, debug, or safely continue this project.

Update memory only for:
- Architecture changes
- Database schema changes
- Payment logic changes
- Subscription logic changes
- User access logic changes
- Important user flow changes
- Deployment or environment changes
- AI prompt behavior changes
- Course or lesson logic changes
- Important business logic decisions
- Major bug fixes
- Security-sensitive changes

Do not update memory for:
- Small text edits
- Emoji changes
- Typo fixes
- Minor UI/CSS changes
- Console log cleanup
- Small refactoring with no logic change
- Temporary experiments
- Changes already obvious from the code

Before updating memory, ask internally:

> Will this help another AI assistant understand, debug, or safely continue this project later?

If the answer is no, do not update the memory file.

---

## Security Rules

Never write these into memory files:
- API keys
- Bot tokens
- Passwords
- Real `DATABASE_URL` values
- Private links
- Payment credentials
- Admin private data
- Webhook secrets

Use placeholder names only, for example:
- `BOT_TOKEN`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `ADMIN_IDS`
