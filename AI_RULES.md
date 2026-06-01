# AI_RULES.md

## Main Rules

1. Always read `AGENTS.md` and `PROJECT_MEMORY.md` before making changes.
2. Do not redesign the project unless explicitly requested.
3. Do not delete working code without explaining why.
4. Make the smallest safe change possible.
5. Preserve existing business logic.
6. Never expose or write secrets.
7. Do not put API keys, tokens, passwords, real database URLs, private links, or payment credentials into memory files.
8. If database schema changes, document the migration.
9. If payment/subscription/access logic changes, document the risk.
10. After important changes, update `PROJECT_MEMORY.md`.
11. If something is unclear, inspect the code first instead of guessing.
12. Do not invent features that are not already present in the project.

---

## Git Push And Main Branch Rule

- When the user says `push`, asks to publish to GitHub, or requests a deploy push without naming a separate branch or PR workflow, treat `origin/main` as the final target.
- A feature-branch push is not completion. Do not report success until the intended commit is confirmed on the remote `origin/main` ref.
- Fetch the current remote state before pushing and inspect the intended commit against `origin/main` history.
- If the working tree is dirty or histories diverge, do not include unrelated user changes, force-push, or reset. Create a clean temporary worktree from `origin/main`, cherry-pick only the intended commit, and push `HEAD:main`.
- After pushing, verify the remote `origin/main` ref again and report the commit hash that reached `main`.

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

## Change Summary Format

When updating `PROJECT_MEMORY.md`, use this format:

```md
### YYYY-MM-DD — Short title

Changed:
- 

Why:
- 

Files touched:
- 

Risk:
- 

Follow-up:
- 
```

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

Use placeholders only:
- `BOT_TOKEN`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `ADMIN_IDS`

---

## Do Not Do

- Do not rewrite the whole project.
- Do not change architecture without permission.
- Do not invent missing business logic.
- Do not silently change payment or subscription rules.
- Do not store secrets.
- Do not add unnecessary libraries.
- Do not overcomplicate simple flows.
- Do not update memory for tiny changes.
