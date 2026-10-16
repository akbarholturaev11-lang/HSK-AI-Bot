# PROJECT_MEMORY.md

## Project purpose

HSK AI helps Uzbek-, Russian-, and Tajik-speaking learners study Chinese through structured HSK lessons, practice, AI assistance, and related tools. The course is the core product; AI, voice, XP, reminders, rewards, and subscriptions support it.

## Architecture

- `app/main.py` composes the FastAPI application; `app/bot/create_bot.py` creates the Aiogram bot and registers handlers.
- `app/static/` contains the Telegram Mini App and public web pages. Course content and browser-side flows live under `app/static/`.
- `android/` is the native Kotlin/Jetpack Compose client; `desktop/` is the Tauri client. Backend APIs own shared account, course-result, and entitlement behavior where implemented.
- Backend handlers and logic are divided among `app/api/`, `app/services/`, `app/repositories/`, and `app/bot/handlers/`.
- Persistence uses async SQLAlchemy models under `app/db/models/`; schema changes use `alembic/versions/`. Database settings and sessions live in `app/config.py` and `app/db/session.py`.
- AI provider calls are centralized in `app/services/ai_provider.py`; the current source uses Gemini first and OpenAI as fallback where supported. Feature services may set their own models and limits.

## Data model and business logic

- `users.id` is the canonical learner account key; unique `telegram_id` is optional and always a real Telegram identity. Subscription state includes `status`, `payment_status`, `start_date`, and `end_date`; there is no `subscription_until` column.
- `payments` records the learner, plan, amount/currency, `payment_status`, submission/review timestamps, and payment evidence or discount metadata. Check `app/db/models/payment.py` for the current schema before changing payment code.
- Paid access requires approved payment state and an unexpired `end_date`. `app/services/subscription_service.py` owns paid-term activation and renewal; `app/services/user_access_state_service.py` distinguishes paid access from temporary trials and free/expired states.
- Temporary trial and referral benefits are not paid billing records. Keep their access predicates distinct from paid subscription checks.
- Manual subscription receipts have one reusable provisional Pro opportunity per user (`users.payment_preview_available`, `users.payment_preview_payment_id`, migration `0102_payment_review_preview`). It is consumed only after receipt submission, revoked on admin rejection, and restored on each *approved subscription payment* (not HSK 3.0 one-time unlock or manual Pro grant). It is temporary full content access, never paid revenue/status or a changed subscription term; Mini App and bot share the server-owned flag. A pending receipt gets a separate capped $0.50 AI budget until review, enforced for chat, image, Voice Practice and Live turns; do not override an existing paid/referral/7-day trial window. Temporary Pro receipt previews also grant HSK 3.0 track entry without treating the payment as approved. See `app/services/payment_review_preview_service.py` and `tests/test_payment_review_preview.py`.
- Course progress, attempts, learner state, mistakes/mastery, XP, and AI budgets are represented by separate model families and services. Preserve server-owned result and access decisions across clients.
- `user_identities` links Google/Apple provider identities to `users.id`. Match accounts by provider subject identity; email/display metadata is not proof of ownership and must not be used to merge accounts.
- Verified account-deletion requests enter `account_deletion_requests` via migration `0101_account_deletion_requests`; each account can have one active request with a 30-day processing target. Purging requires an explicit operator action, and documented financial-retention exceptions remain. Deletion does not cancel external-store renewals; see `docs/ACCOUNT_DELETION_OPERATIONS.md`.

## Native account identity
- Google/Apple first sign-in creates `users.id` only after existing OIDC verification; a known `(provider, subject_hash)` signs into its owner. Telegram private-chat approval can create a new Telegram learner. Email equality and a bound installation never authorize account merging/linking; no fake Telegram ID is stored.
- Native learning, profile, progress, trial/risk, ad caps, AI budgets, voice and notices use canonical user ownership. Legacy integer service arguments remain real Telegram IDs. Missing Telegram metadata must never become an ownership query matching all NULL rows.
- Migrations `0102`–`0104` make Telegram metadata nullable, backfill canonical owners, add canonical dedupe constraints and AI/voice FKs. Downgrade refuses native data. Existing starter access policy, paid dates, trial eligibility, billing amounts and referral rules remain authoritative.
- Identity changes serialize on the user row and cannot remove the last sign-in method. Approved sign-in proofs retain the exact identity ID; native link proofs retain their originating session ID and are revalidated before use. Blocked accounts cannot refresh; raw session validation remains available for the narrow account-deletion path.
- Existing manual payment and referral flows still require a real Telegram identity and return explicit availability errors for provider-only accounts. This does not introduce store billing or automatic Telegram attachment. Rollout/test details: `docs/UNIVERSAL_NATIVE_ACCOUNTS.md`.

## Important decisions and operational caveats

- Keep the HSK course and canonical lesson order/content at the center of the product. Supporting features should not replace the learning path.
- Mini App `朱雀` is a brand league; Android XP tiers remain the server-defined progression. These are separate representations, not interchangeable ranks.
- Each Android release must use a `versionCode` greater than the latest published release; it need not increase by exactly one. Verify the artifact against the release manifest because the current workflow does not reject every equal-code/different-artifact case.
- Source files and repository defaults do not prove live deployment, production environment values, provider credentials, or release status. Verify those in the owning environment before reporting them as live facts.

## Key files

- Application and database: `app/main.py`, `app/config.py`, `app/db/session.py`, `app/db/models/`, `alembic/versions/`
- Bot: `app/bot/create_bot.py`, `app/bot/handlers/`, `app/bot/keyboards/`
- Payments/access: `app/repositories/payment_repo.py`, `app/repositories/user_repo.py`, `app/services/subscription_service.py`, `app/services/user_access_state_service.py`, `app/services/entitlements/`
- Course: `app/static/course-v3.html`, course data under `app/static/`, and related routers/services under `app/api/` and `app/services/`
- Account deletion: `app/api/account_deletion.py`, `app/services/account_deletion_service.py`, `scripts/process_account_deletion.py`, and `docs/ACCOUNT_DELETION_OPERATIONS.md`
- Clients: `android/`, `desktop/`
- Durable instructions and project context: `AGENTS.md`, `AI_RULES.md`, `ANDROID_CONTEXT.md`, and `ANDROID_RELEASE_CHECKLIST.md`
