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

- `users.id` is the canonical internal learner-account owner. In P3's **feature branch only**, migrations `0103`–`0106` and matching User/event, AI/Voice and payment models/repositories have been staged from main. `telegram_id` can be NULL for provider-only Google/Apple accounts and must never determine canonical ownership: Voice limits, lesson reservations, analytics dedupe and payment receipts use `users.id`; real positive Telegram IDs are retained only for scoped legacy fallback. The staged `0105`/`0106` integration passed targeted backend CI on 2026-10-20; this is NOT full native login/release, with `0107`–`0108`, OAuth/linking, payment/referral callers and production migration still to reconcile. Subscription state uses `status`, `payment_status`, `start_date`, `end_date`, not `subscription_until`.
- `payments` records the learner, plan, amount/currency, `payment_status`, submission/review timestamps, and payment evidence or discount metadata. Check `app/db/models/payment.py` for the current schema before changing payment code.
- Paid access requires approved payment state and an unexpired `end_date`. `app/services/subscription_service.py` owns paid-term activation and renewal; `app/services/user_access_state_service.py` distinguishes paid access from temporary trials and free/expired states.
- Temporary trial and referral benefits are not paid billing records. Keep their access predicates distinct from paid subscription checks.
- Manual subscription receipts have one reusable provisional Pro opportunity per user (`users.payment_preview_available`, `users.payment_preview_payment_id`, migration `0102_payment_review_preview`). It is consumed only after receipt submission, revoked on admin rejection, and restored on each *approved subscription payment* (not HSK 3.0 one-time unlock or manual Pro grant). It is temporary full content access, never paid revenue/status or a changed subscription term; Mini App and bot share the server-owned flag. A pending receipt gets a separate capped $0.50 AI budget until review, enforced for chat, image, Voice Practice and Live turns; do not override an existing paid/referral/7-day trial window. Temporary Pro receipt previews also grant HSK 3.0 track entry without treating the payment as approved. See `app/services/payment_review_preview_service.py` and `tests/test_payment_review_preview.py`.
- Course progress, attempts, learner state, mistakes/mastery, XP, and AI budgets are represented by separate model families and services. Preserve server-owned result and access decisions across clients.
- `user_identities` links Google/Apple provider identities to `users.id`. Match accounts by provider subject identity; email/display metadata is not proof of ownership and must not be used to merge accounts.
- Verified account-deletion requests enter `account_deletion_requests` via migration `0101_account_deletion_requests`; each account can have one active request with a 30-day processing target. Purging requires an explicit operator action, and documented financial-retention exceptions remain. Deletion does not cancel external-store renewals; see `docs/ACCOUNT_DELETION_OPERATIONS.md`.

## Important decisions and operational caveats

- Localization expansion is **local-first**: author shared translations centrally in GitHub, then generate bundled Android/Mini App/Desktop resources and local Bot/backend catalogs at build/deploy time; never require a per-UI-string runtime API. Keep existing `uz/ru/tj`, native source IDs, entitlements, and client backward compatibility while migrating incrementally. **Continue from `localization/PLAN_SCHEMA_ORDER.md` first** (plan, schema, phase order and verified status), then `docs/I18N_LOCAL_FIRST_WORKPLAN.md` and `localization/surface_registry.json`. Preparation stage only.
- Keep the HSK course and canonical lesson order/content at the center of the product. Supporting features should not replace the learning path.
- Mini App `朱雀` is a brand league; Android XP tiers remain the server-defined progression. These are separate representations, not interchangeable ranks.
- Each Android release must use a `versionCode` greater than the latest published release; it need not increase by exactly one. Verify the artifact against the release manifest because the current workflow does not reject every equal-code/different-artifact case.
- Source files and repository defaults do not prove live deployment, production environment values, provider credentials, or release status. Verify those in the owning environment before reporting them as live facts.

## Agent-owned Chinese-course translation QA (owner direction, 2026-10-19)

**Current resume state:** `localization/P3_ACTIVE_HANDOFF.md` (read first; historical progress in `localization/NEXT_CHAT_HANDOFF.md`).

For existing UZ/RU/TJ course texts, coding agents own semantic and grammar QA,
actual corrections, source-safe centralization, all three client checks, and
regression knowledge. Do not ask the owner to validate Chinese/UZ/RU/TJ or
treat independent human linguistic approval as the required release gate.
`localization/AI_CONTENT_QA_POLICY.md` supersedes historical manual-review
phrases in the P3 backlog. AI self-review is not evidence of native-speaker
certification; fail closed on unresolved wrong meaning and preserve P0 source,
mirror, quiz/grade, Pro and auth guards. Draft PR #179 is isolated until
applicable CI and client QA pass. A 136-context candidate ZIP or private
integration preview is not proof of a completed runtime migration.

## Key files

- Application and database: `app/main.py`, `app/config.py`, `app/db/session.py`, `app/db/models/`, `alembic/versions/`
- Bot: `app/bot/create_bot.py`, `app/bot/handlers/`, `app/bot/keyboards/`
- Payments/access: `app/repositories/payment_repo.py`, `app/repositories/user_repo.py`, `app/services/subscription_service.py`, `app/services/user_access_state_service.py`, `app/services/entitlements/`
- Course: `app/static/course-v3.html`, course data under `app/static/`, and related routers/services under `app/api/` and `app/services/`
- Account deletion: `app/api/account_deletion.py`, `app/services/account_deletion_service.py`, `scripts/process_account_deletion.py`, and `docs/ACCOUNT_DELETION_OPERATIONS.md`
- Clients: `android/`, `desktop/`
- Durable instructions and project context: `AGENTS.md`, `AI_RULES.md`, `ANDROID_CONTEXT.md`, and `ANDROID_RELEASE_CHECKLIST.md`
