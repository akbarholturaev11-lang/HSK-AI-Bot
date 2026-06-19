# PROJECT_MEMORY.md

## 1. Project Identity

Project name: Unknown / needs inspection  
Project type: Telegram Bot / Mini App / Website / Backend / Other  
Main purpose: Unknown / needs inspection  
Target users: Unknown / needs inspection  
Current status: Unknown / needs inspection  

Short description:
- This project is built to: Unknown / needs inspection
- Main user problem: Unknown / needs inspection
- Main business goal: Unknown / needs inspection

---

## 2. Core Architecture

Frontend:
- Unknown / needs inspection

Backend:
- Unknown / needs inspection

Database:
- Unknown / needs inspection

Hosting:
- Unknown / needs inspection

Bot framework:
- Unknown / needs inspection

AI provider/model:
- Unknown / needs inspection

Payment system:
- Unknown / needs inspection

External services:
- Unknown / needs inspection

---

## 3. Important Project Rules

- Do not redesign the whole architecture without explicit request.
- Do not remove working logic unless there is a clear reason.
- Make minimal safe changes.
- Keep user/payment/subscription logic stable.
- If database schema changes, document the migration.
- If environment variables change, update `.env.example`.
- Never write secrets, API keys, tokens, passwords, or private URLs in this file.
- Before changing payment, subscription, or access logic, check the current flow first.
- If something is unclear, inspect the code first instead of guessing.

---

## 4. Memory Update Policy

This file is NOT a daily diary and must NOT become a dump of every small change.

Only update this file when the change is important for future AI assistants to understand, debug, or safely continue the project.

Update this file only for:
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

Do NOT update this file for:
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

If the answer is no, do not update this file.

When updating memory, keep it short and useful:
- What changed
- Why it changed
- Files touched
- Risk / follow-up if needed

Never turn this file into a long changelog.

---

## 5. Key Files and Folders

Main files:
- `main.py` — Unknown / needs inspection
- `bot.py` — Unknown / needs inspection
- `database.py` — Unknown / needs inspection
- `config.py` — Unknown / needs inspection
- `handlers/` — Unknown / needs inspection
- `keyboards/` — Unknown / needs inspection
- `services/` — Unknown / needs inspection
- `miniapp/` — Unknown / needs inspection
- `.env.example` — Unknown / needs inspection

Important note:
- Do not rename or delete important files unless necessary.

---

## 6. Database Schema Summary

### users
Purpose: stores Telegram users and access status.

Important fields:
- `telegram_id`
- `language`
- `status`
- `payment_status`
- `subscription_until`
- `question_limit`
- `questions_used`

### payments
Purpose: stores payment requests and confirmations.

Important fields:
- `payment_id`
- `telegram_id`
- `amount`
- `payment_code`
- `status`
- `created_at`
- `confirmed_at`

### logs / history
Purpose: stores important user actions or AI interactions.

Important fields:
- Unknown / needs inspection

---

## 7. Current Business Logic

### User onboarding
Current flow:
1. Unknown / needs inspection

### Subscription logic
Current logic:
- Free trial: Unknown / needs inspection
- Paid plans: Unknown / needs inspection
- Question limits: Unknown / needs inspection
- Expiration logic: Unknown / needs inspection
- Access blocked when: Unknown / needs inspection

### Payment logic
Current logic:
- Payment method: Unknown / needs inspection
- Manual approval: Unknown / needs inspection
- Auto approval: Unknown / needs inspection
- Admin notification: Unknown / needs inspection

### AI logic
Current logic:
- Unknown / needs inspection

---

## 8. Current Features

Working:
- Unknown / needs inspection

Partially working:
- Unknown / needs inspection

Not built yet:
- Unknown / needs inspection

---

## 9. Important Decisions

### Decision 1
Date: Unknown  
Decision: Unknown / needs inspection  
Reason: Unknown / needs inspection  
Risk: Unknown / needs inspection  

---

## 10. Recent Important Changes

### 2026-06-19 — Release feedback fixes and active stats

Changed:
- Release feedback now asks admin which bot area changed and routes `Sinab ko'rish` toward that feature when possible.
- Release feedback reward text is disclosed before rating; after feedback it confirms the promised 20% / 24-hour discount.
- Release feedback test access is 30 minutes and bypasses normal free daily/AI budget limits during that window, so users can actually test the changed feature.
- Per-user release feedback discount campaigns are one-use, and the Mini App can fall back to the standard 20% QR when a per-campaign QR is not uploaded.
- Admin main stats no longer include release feedback stats; bot feedback stats moved to a separate `Otziv statistikasi` page.
- `last_active_at` is updated on user messages/callbacks; admin active-user stats use Asia/Shanghai day boundaries and show 24-hour active users.

Why:
- Users must know the reward before giving feedback, must be able to test the actual changed feature, and admin stats must show real active usage.

Files touched:
- `app/bot/handlers/release_feedback.py`
- `app/services/release_feedback_service.py`
- `app/bot/keyboards/release_feedback.py`
- `app/db/models/release_feedback.py`
- `app/repositories/release_feedback_repo.py`
- `app/services/subscription_miniapp_service.py`
- `app/services/ai_usage_budget_service.py`
- `app/services/access_service.py`
- `app/bot/handlers/admin.py`
- `app/bot/middlewares/db.py`
- `app/bot/handlers/commands.py`
- `alembic/versions/0042_release_feedback_feature_trial.py`
- `alembic/versions/0043_restore_release_feedback_trial_30_minutes.py`
- `AI_RULES.md`

Risk:
- Release feedback test access is still not a paid subscription; it is a 30-minute non-paid test window, and paid checks must continue to rely on `payment_status="approved"`.
- Existing active stats only become accurate for a user after their next message/callback updates `last_active_at`.

Follow-up:
- Run migration/deploy, then smoke test release create/test/send, feature routing, 30-minute no-limit test access, QR checkout, and admin stats after a user interaction.

### 2026-06-19 — Release feedback approval workflow rule

Changed:
- Added a project rule that after every major user-visible update, Codex must prepare a release feedback draft tailored to that update.
- The draft must explain what changed, where the user should test it, what the `Sinab ko'rish` CTA should do, target segment, rating prompt, reward text before feedback, and stats to watch.
- Release feedback must not be sent automatically; after deploy, admin approval is required. If admin rejects or does not approve, nothing is sent.

Why:
- Release feedback should be tied to the exact update users need to test, without surprising users or sending unapproved broadcasts.

Files touched:
- `AGENTS.md`
- `AI_RULES.md`
- `PROJECT_MEMORY.md`

Risk:
- This is a required Codex handoff rule, not an automatic deploy hook. Future Codex sessions must include the draft after major user-visible changes and use the existing Release feedback admin module after admin approval.

Follow-up:
- For every major deploy, prepare the release feedback draft in the final handoff and wait for admin approval before sending.

### 2026-06-14 — Release feedback dashboard

Changed:
- Admin panel now has a Telegram-based Release feedback module for sending localized release announcements, collecting 1-5 ratings, required low-rating comments/screenshots, optional comments, and per-campaign stats.
- Release messages include a "Sinab ko'rish" CTA; non-paid users get temporary 30-minute active test access without changing `payment_status`.
- Completed release feedback from non-paid users creates a per-user 20% / 24-hour `admin_discount` campaign, so checkout reuses the existing Subscription Mini App admin discount flow.
- Added `release_feedback_campaigns`, `release_feedback_deliveries`, and `release_feedback_responses`.
- Admin statistics now includes overall bot feedback and release feedback metrics.

Why:
- Admin needs to announce new bot features, let users test them, collect actionable feedback, and track response/try/discount results.

Files touched:
- `app/bot/handlers/release_feedback.py`
- `app/services/release_feedback_service.py`
- `app/repositories/release_feedback_repo.py`
- `app/db/models/release_feedback.py`
- `app/bot/keyboards/release_feedback.py`
- `app/bot/fsm/release_feedback.py`
- `app/bot/handlers/admin.py`
- `app/main.py`
- `app/bot/create_bot.py`
- `alembic/versions/0041_add_release_feedback.py`

Risk:
- Temporary test access sets non-paid users to `status="active"` for 30 minutes but does not make them paid; paid logic must continue to rely on `payment_status="approved"`.
- Release feedback discounts are stored as normal admin discount campaigns targeted to one Telegram ID.

Follow-up:
- Run migration/deploy, then smoke test release create/test/send, user try access, 1-5 rating, low-rating comment, discount checkout, and admin stats.

### 2026-06-13 — Broadcast and ad campaign CTA buttons

Changed:
- Admin broadcast and ad campaign creation now ask whether to add one inline button under the outgoing message.
- Ready button actions include subscription Mini App, partner, course mode, reminder setup, help, admin contact, profile, plus a custom external URL with optional custom button text.
- Ad campaigns store the optional button as `ad_campaigns.button_config` JSON text, with migration/bootstrap support for existing databases.

Why:
- Marketing messages need direct CTA buttons without manually building separate bot flows for each campaign.

Files touched:
- `app/bot/keyboards/promo_button.py`
- `app/bot/handlers/admin_broadcast.py`
- `app/bot/handlers/admin_ads.py`
- `app/bot/handlers/menu.py`
- `app/db/models/ad_campaign.py`
- `app/repositories/ad_campaign_repo.py`
- `app/services/ad_campaign_service.py`
- `app/db/session.py`
- `alembic/versions/0040_add_ad_campaign_button_config.py`

Risk:
- Button action callbacks send a new message and leave the original broadcast/ad message intact; Telegram smoke testing is needed for each CTA type.

Follow-up:
- Run migration/deploy, then test broadcast and ad campaign with no button, subscription, profile, reminder, admin contact, and external URL buttons.

### 2026-06-13 — AI level ceiling hardened

Changed:
- General QA system prompt now explicitly forbids examples, vocabulary, grammar, sentence patterns, and explanations above the user's current level.
- Course tutor prompts now append the same level-ceiling rule to every step response and homework evaluation.
- Image explainer prompt now requires image explanations/examples to stay at or below the user's level.

Why:
- AI tutor behavior must not teach above the user's HSK level unless the user explicitly asks about higher-level content.

Files touched:
- `app/prompts/qa_system.txt`
- `app/services/course_tutor_service.py`
- `app/services/image_explainer_service.py`

Risk:
- Responses may become simpler and avoid advanced examples even when they would be interesting, which is intentional for level safety.

Follow-up:
- Smoke test HSK1/HSK2 QA, image explanation, and course lesson AI feedback with prompts asking for advanced examples.

### 2026-06-13 — Help links moved to admin-managed bot settings

Changed:
- `/help` and menu Help now build 3-language HTML help text from `bot_settings` video-link keys instead of hardcoded help content/contact.
- Admin panel now has one `Help sozlamalari` section containing 4 help video link types per language (`tj`, `ru`, `uz`) plus one global admin contact link.
- Empty help video links are skipped in user help text; admin contact is shown as an inline button below the help message when configured.

Why:
- Help video URLs and support contact must be editable from the admin panel without code changes.

Files touched:
- `app/services/help_settings_service.py`
- `app/services/support_contact_service.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/commands.py`
- `app/bot/handlers/menu.py`
- `app/bot/handlers/messages.py`
- `app/bot/fsm/admin_management.py`
- `app/bot/utils/i18n.py`
- `app/static/subscription.html`

Risk:
- Existing deployments without `admin_contact` in `bot_settings` will show the help text without the contact button until admin sets a contact link.

Follow-up:
- In Telegram, test Admin panel → Help sozlamalari, set one video link for each language, then test `/help` and Help menu in TJ/RU/UZ.

### 2026-06-13 — Admin user deletion flow simplified and hardened

Changed:
- Admin panel delete-user button now starts an FSM flow: admin taps delete, bot waits for Telegram ID, admin sends only the numeric ID, and the bot deletes the user.
- Duplicate `/deleteuser` handler was removed from the broadcast router; the legacy `/deleteuser TELEGRAM_ID` fallback now uses the same repository delete path.
- User deletion now explicitly clears direct internal user-linked rows (`messages`, course progress/attempts, onboarding tip events, bot feedback) before deleting the `users` row.

Why:
- `/deleteuser` was duplicated across routers and admin panel forced command usage instead of a simple ID prompt.
- Delete could fail or behave inconsistently when related user rows existed and DB cascade was not enough.

Files touched:
- `app/bot/fsm/admin_management.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/admin_broadcast.py`
- `app/bot/handlers/messages.py`
- `app/repositories/user_repo.py`

Risk:
- Payment/portfolio/partner audit rows are intentionally not deleted; they may still reference the Telegram ID for business history.

Follow-up:
- Deploy and smoke test in Telegram: Admin panel → Foydalanuvchini o'chirish → send numeric Telegram ID → confirm user disappears/restarts cleanly.

### 2026-06-13 — Subscription Mini App card payment display cleanup

Changed:
- Card checkout payment summary no longer shows the card-country row or duplicate bot-price row.
- Card checkout now shows `Dushanbe City` as the TJK bank name and keeps the exchange-rate row only for non-TJ cards.
- Discounted card quotes now include the original local payable amount so the Mini App can show it as a small crossed-out amount above/beside the discounted payable amount.
- Card payment instructions are collapsed by default and expand on tap; Tajik wording was simplified and the `Intiqol` mention was removed.

Why:
- Users saw duplicate pricing and overly long payment instructions on the final card payment screen.

Files touched:
- `app/static/subscription.html`
- `app/services/subscription_miniapp_service.py`

Risk:
- Payment creation still uses the existing final amount; this change mainly affects display and quote payload shape.

Follow-up:
- Smoke test real Telegram Mini App card checkout with TJ and non-TJ cards, including a discount mode.

### 2026-06-13 — HSK1/HSK2 Mini App quiz and homework flow aligned with HSK4

Changed:
- HSK1 and HSK2 Mini App quiz pages now open directly into the lesson quiz, matching the HSK4 flow instead of showing a separate start card.
- HSK1 and HSK2 homework pages now use the same purpose text style as HSK4 and submit homework answers as `vocab_sentences`, `grammar_sentences`, and `translations`.
- Homework submit keeps the return-to-bot button visible after submission, with local/offline fallback and Telegram `sendData` fallback aligned to HSK4-style event handling.
- Mini App asset version was bumped so Telegram opens the updated static files.

Why:
- Quiz and homework Mini Apps needed consistent UI and behavior across all HSK levels.

Files touched:
- `app/static/hsk1.html`
- `app/static/hsk2.html`
- `app/bot/utils/course_miniapp.py`

Risk:
- HSK1/HSK2 direct quiz start removes the previous pre-quiz start screen; course result saving still uses the existing `/api/miniapp/event` path.

Follow-up:
- Smoke test Telegram Mini App links for HSK1 and HSK2: quiz result returns to bot, homework submission shows return button, and bot receives AI homework result.

### 2026-06-12 — Course text AI separated from QA daily text limit

Changed:
- Trial/free course-mode text AI checks now bypass the QA daily text limit and course text AI usage no longer increments `users.questions_used`.
- Normal QA text messages still use `questions_used/question_limit` exactly as before.

Why:
- Course-mode text help should not consume or block the user's QA-mode daily text allowance.

Files touched:
- `app/services/access_service.py`
- `app/bot/handlers/messages.py`

Risk:
- This affects only text AI access accounting; photo and voice limits are unchanged.

Follow-up:
- Smoke test with a trial user: ask course tutor/homework/mistake discussion, then switch to QA and confirm daily text remaining was not reduced.

### 2026-06-12 — Subscription Mini App referral, QR, and help contact fixes

Changed:
- Limit-offer referral buttons use clearer bonus-question wording and update the existing limit block into referral invite/progress text.
- Subscription Mini App referral sheet shows the referral link visibly, improves copy status, and uses a stronger QR download/open fallback.
- Help text is shorter and uses an admin contact inline button backed by configurable `bot_settings.admin_contact`.

Why:
- Users needed clearer referral actions, visible invite links, more reliable QR handling in Telegram WebView, and simpler help/contact access.

Files touched:
- `app/static/subscription.html`
- `app/services/subscription_miniapp_service.py`
- `app/services/support_contact_service.py`
- `app/bot/handlers/referral.py`
- `app/bot/keyboards/help.py`
- `app/bot/utils/i18n.py`

Risk:
- QR download still depends on Telegram WebView/browser behavior; fallback opens the image if direct download is blocked.

Follow-up:
- Smoke test Mini App referral copy/share, QR display/download, and `/help` admin contact button.

### 2026-06-12 — Course grammar and all-level quiz quality tuning

Changed:
- HSK4 grammar blocks render as concise useful blocks: pattern, usage, one lesson example, and one attention note.
- HSK1-HSK4 Mini App quiz selection prioritizes distinct new words before repeating alternate question types, limits grammar repetition, and deduplicates exact questions.
- Backend Mini App quiz questions include word metadata so frontend selection can avoid several early questions from the same word.
- Course quiz intro text was simplified into a direct challenge-style prompt.

Why:
- Quiz users should be tested on more newly learned words, not duplicate-style questions from the first few words.
- HSK4 grammar needed to be useful without becoming a long theory block.

Files touched:
- `app/bot/utils/course_formatter.py`
- `app/bot/utils/course_miniapp.py`
- `app/bot/utils/i18n.py`
- `app/services/course_miniapp_lesson_service.py`
- `app/services/course_tutor_service.py`
- `app/static/hsk1.html`
- `app/static/hsk2.html`
- `app/static/hsk3.html`
- `app/static/hsk4.html`

Risk:
- Small blocks can return fewer than the target count if there are not enough unique valid questions, but this avoids low-quality duplicates.

Follow-up:
- Smoke test HSK1-HSK4 block quiz in Telegram/Mini App and confirm the first questions cover different new words.

### 2026-06-12 — Course trial fallback and homework processing feedback

Changed:
- Course subscription offers shown after course/trial lock now include an "Oddiy rejim" fallback button that switches the user back to `learning_mode="qa"` with existing daily limits and sends a short explanation that no automatic lessons are sent in this mode.
- Mini App homework submission now sends an immediate "AI is checking" chat message and edits that same message into the final AI homework result.
- Text/photo/course/voice AI replies now use a safer send path: empty AI content returns a localized fallback, AI exceptions send a visible retry message, malformed HTML retries without parse mode, and long replies are split into Telegram-safe chunks.
- The temporary "bot is working" edit effect now chooses different emoji sequences by mode (`qa`, `course`, `image`) and a seed based on user question count/text.

Why:
- Trial users who finish the free course lesson need a clear non-paid path back to daily-limited QA instead of only seeing the subscription button.
- Homework AI checks can take time, so the bot should visibly work instead of staying silent.
- AI or Telegram formatting failures should not make the bot appear to ignore a user message when an app-level fallback can still be sent.

Files touched:
- `app/bot/keyboards/subscription.py`
- `app/bot/handlers/course.py`
- `app/main.py`
- `app/bot/handlers/messages.py`
- `app/bot/utils/i18n.py`

Risk:
- Free mode does not grant new access; it only sets `learning_mode="qa"` and existing daily limits still control usage.
- Telegram message edit failures fall back to sending the final result as a new message.
- The fallback cannot fix upstream outages or Telegram delivery failures, but it prevents silent app-level failures for empty AI output, exceptions, bad HTML, and overlong text.

Follow-up:
- Smoke test in Telegram: finish a trial lesson, tap "Oddiy rejim", ask text/photo/course questions, then submit homework from the Mini App and confirm the processing message edits into the final result.

### 2026-06-12 — AI usage budget live-rate calculation

Changed:
- Paid subscription AI usage budgets now try live USD exchange rates when a payment is approved, including TJS and CNY, with admin-set subscription rates as fallback.
- The admin subscription price panel now includes a CNY fallback rate for Alipay/WeChat AI budget conversion.
- AI usage budget profit reserve changed from 40% to 50%.
- The fixed $1 Railway/server deduction was removed from per-payment AI budget calculation.

Why:
- Subscription limits should follow real exchange rates and updated business margin rules, but live-rate failures must fall back to admin-controlled rates instead of hardcoded TJS/CNY values.

Files touched:
- `app/bot/handlers/admin.py`
- `app/services/ai_usage_budget_service.py`
- `app/services/subscription_currency_service.py`

Risk:
- New approved payments will receive smaller AI budgets than before because profit reserve increased to 50%, but no extra $1 deduction is taken.
- Existing active AI budgets are not recalculated automatically.

Follow-up:
- After deploy, approve a small test payment and verify the created `ai_usage_budgets.total_budget_usd` against live/fallback rates.

### 2026-06-11 — Mini App subscription payment/referral repair

Changed:
- Subscription Mini App no longer shows demo/fallback payment data to real Telegram users when quote/overview APIs fail.
- VISA/card checkout now fails with a clear error if admin payment details are not configured.
- Mini App submit creates a pending payment only if at least one admin payment-review notification is delivered; otherwise it rolls back and returns an error.
- Referral 20% discount progress is recalculated from active referral records instead of trusting only `users.discount_referral_count`.
- Referral links for the 3-friend discount use the live bot username when possible, and the Mini App invite flow now supports localized share text plus copy-link-only.
- Legacy chat checkout reads admin-updated card payment details from `bot_settings.subscription_payment_details`.
- Reopening the Subscription Mini App while a payment is still pending shows a localized waiting screen instead of allowing duplicate payment submissions.
- The first Subscription Mini App screen now removes the extra explanatory hero block and keeps only concrete subscription benefits plus plan/payment choices.
- Profile and text/photo limit subscription buttons now open the Subscription Mini App directly with WebApp buttons instead of routing through the legacy `subscription:open` entry block.
- Subscription, referral discount, feedback discount, and admin campaign discount checkout now run through the Subscription Mini App modes (`subscription`, `referral_discount`, `feedback_discount`, `admin_discount`). Chat checkout plan/payment callbacks are legacy fallbacks that redirect to Mini App, and admin campaign notifications use a short Mini App entry instead of chat checkout blocks.
- Users who already used the referral discount no longer receive discount UI or discounted pricing from the Mini App.
- VISA/card payment details are rendered as readable rows with copy buttons for card-like numbers; Tajikistan card payments hide the exchange-rate row.
- The main reply-keyboard subscription button is now a Web App button that opens the Subscription Mini App directly; command/profile flows still send the explanatory Mini App entry block.
- QR payment screens let the user tap the QR to reveal a download button for saving the QR image.
- Card exchange-rate rows shown to users use direct TJS rates, for example `1 TJS = ... RUB`, instead of displaying USD/USDT-style cross-rate chains.
- Subscription Mini App has a top Help button with the public admin contact for payment-confirmation problems and visible errors; it remains available on pending-payment screens.

Why:
- Users were seeing wrong/fallback QR, card details, referral links, and discount state in the subscription Mini App, and payment submits could appear successful even if admin review did not receive the request.

Files touched:
- `app/static/subscription.html`
- `app/services/subscription_miniapp_service.py`
- `app/services/admin_notify_service.py`
- `app/services/discount_service.py`
- `app/services/subscription_progress_service.py`
- `app/bot/handlers/subscription.py`
- `app/bot/utils/course_miniapp.py`
- `app/main.py`

Risk:
- If admin IDs are wrong or blocked, Mini App payment submit now returns an error instead of silently accepting the request.
- Graphify update was attempted but refused to overwrite the existing graph because the rebuilt graph had fewer nodes.

Follow-up:
- After deploy, test inside Telegram with real `initData`: VISA/card quote, Alipay/WeChat QR quote, screenshot submit, admin approval, and referral share/copy in UZ/RU/TJ.

### 2026-06-09 — Subscription flow moved to Mini App

Changed:
- Normal subscription entrypoints now open `subscription.html` as a Telegram Mini App instead of continuing the chat checkout flow.
- Mini App APIs `/api/subscription-miniapp/overview`, `/quote`, and `/submit` calculate prices server-side, apply only the normal referral 20% discount path, and send submitted screenshots to the existing admin payment review queue without AI screenshot verification.
- Admin price panel now includes manual bank-card rates for TJS/UZS/RUB and an AUTO live-rate toggle; Mini App card quotes use admin rates unless AUTO live rates are enabled and available.
- `payments` now stores optional `card_country`, `local_amount`, `local_currency`, and `exchange_rate` for Mini App card payments.

Why:
- Subscription checkout should stay inside the Mini App, avoid chat-return steps for the normal Obuna button, and prevent frontend-side price/rate mistakes.

Files touched:
- `app/static/subscription.html`, `app/main.py`, `app/services/subscription_miniapp_service.py`, `app/services/subscription_currency_service.py`, `app/bot/handlers/*`, `app/bot/keyboards/subscription.py`, `app/db/models/payment.py`, `app/repositories/payment_repo.py`, `alembic/versions/0037_add_miniapp_payment_local_fields.py`

Risk:
- Live exchange rates depend on the external rate provider; if unavailable, backend falls back to admin manual rates.

Follow-up:
- Verify the Mini App inside Telegram with real `initData`, uploaded QR codes for non-default Alipay/WeChat prices, and a real admin approval.

### 2026-06-07 — Price-specific Alipay/WeChat QR codes

Changed:
- Added `payment_qr_codes` storage for uploaded Telegram QR `file_id`s by scope, payment method, plan, amount, and currency.
- Alipay/WeChat custom subscription prices now require admin to upload the matching regular QR and the matching 20% discount QR before the price is saved.
- Admin discount campaigns that target or include Alipay/WeChat now require campaign QR codes per affected method/plan discounted amount.
- Checkout uses old static QR files only for default Alipay/WeChat prices and default 20% referral/feedback discounts; non-default missing QR no longer falls back to an old fixed-price QR.

Why:
- Alipay/WeChat QR codes are amount-specific, so users must never receive a QR for a different price after admin changes prices or creates a discount.

Files touched:
- `app/db/models/payment_qr_code.py`
- `app/repositories/payment_qr_code_repo.py`
- `app/services/payment_qr_code_service.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/admin_discount.py`
- `app/bot/handlers/subscription.py`
- `alembic/versions/0036_add_payment_qr_codes.py`

Risk:
- Existing active admin discount campaigns created before this change do not have campaign-scoped QR records; for Alipay/WeChat checkout they may show "QR not ready" instead of the old generic admin discount QR.

Follow-up:
- Run migration/init DB, then smoke test: custom Alipay/WeChat price, 20% referral/feedback checkout, and admin discount campaign checkout.

### 2026-06-06 — Feedback prompt and reward timing

Changed:
- Feedback reward access is now 30 minutes instead of 1 day.
- Feedback requests are sent only after the user is at least 1 day old and has hit the daily text limit; the prompt becomes due 5 minutes after that limit event.

Why:
- Feedback should be requested after real limit friction, not just because the account is old.
- Feedback reward should not give a full day by default.

Files touched:
- `app/services/access_service.py`
- `app/services/bot_feedback_service.py`
- `app/main.py`
- `app/bot/handlers/messages.py`
- `app/bot/utils/i18n.py`

Risk:
- Existing `users.daily_limit_offer_sent_at` is reused as the limit-hit timestamp; no migration.
- Scheduler now checks feedback requests every 60 seconds, relying on pending feedback retry rules to prevent repeated prompts.

Follow-up:
- Smoke test with a user older than 1 day: hit the daily text limit, wait 5 minutes, confirm the feedback prompt appears once and reward activates for 30 minutes.

### 2026-06-06 — Feedback limit discount offer

Changed:
- Bot feedback dislike option `limits` now schedules the same 5-minute 20% subscription discount offer as `price`.
- The limits offer uses a separate user-facing message about bot limits, but reuses the existing feedback discount checkout/payment flow.

Why:
- Users who say bot limits are too low should get the same conversion path as users who say subscription price is high.

Files touched:
- `app/repositories/bot_feedback_repo.py`
- `app/services/bot_feedback_service.py`
- `app/services/discount_service.py`
- `app/bot/utils/i18n.py`

Risk:
- Existing DB fields are reused; no migration. Scheduler still sends due offers from the existing 60-second background loop.

Follow-up:
- Smoke test in Telegram: choose `Limitlar kam`, wait 5 minutes, open the 20% discount flow, and submit a payment screenshot.

### 2026-06-06 — Image caption as AI command

Changed:
- Photo messages now pass Telegram caption text into the image AI flow.
- The image explainer treats caption text as the user's command and uses analyzer output as the image source context.
- Image file IDs are excluded from normal QA chat history; follow-up context should come from stored image context.
- QA AI history now keeps system context messages, so stored image context is available in follow-up questions.

Why:
- Users sending photo + text like "Tarjima qil" need the bot to follow the text instruction instead of only explaining the image.

Files touched:
- `app/bot/handlers/messages.py`
- `app/services/image_qa_service.py`
- `app/services/image_explainer_service.py`
- `app/services/qa_service.py`
- `app/services/ai_service.py`

Risk:
- Prompt-only behavior change; image limits, subscription access, and payment logic are unchanged.

Follow-up:
- Test in Telegram with a photo caption command such as "Tarjima qil".

### 2026-06-05 — Command/menu input cleanup

Changed:
- Private-chat slash commands and main/course reply menu button messages are deleted after their handlers run.

Why:
- Keep Telegram chats clean while preserving command behavior.

Files touched:
- `app/bot/middlewares/cleanup.py`
- `app/bot/create_bot.py`

Risk:
- Delete failures are ignored; group chats are not affected.

Follow-up:
- Verify on production bot that Telegram allows deleting incoming private-chat command messages.

### 2026-06-04 — Localized TJS card subscription blocks

Changed:
- Card/TJS subscription selection and checkout messages now keep one compact format while matching the user's language (TJ/RU/UZ).
- TJS plan prices show `💸 {amount} TJS 🇹🇯` in the plan list and `{amount} TJS 💸` in checkout.
- Alipay/WeChat QR payment flow remains separate.

Why:
- Avoid mixed-language payment instructions and keep card payment instructions easy to read.

Files touched:
- `app/bot/handlers/subscription.py`

Risk:
- Text-only card flow change; payment amount and subscription logic unchanged.

Follow-up:
- Verify rendered Telegram blockquote spacing on production bot after deploy.

### 2026-05-25 — Course narrative text formatting

Changed:
- Course text blocks with narrator-style lines (`旁白` / no speaker) now render as text instead of dialogue: bold Chinese line, pinyin below, translation below.
- Narrative blocks show `Matn/Текст/Матн` in the course message header instead of `Dialog`.

Why:
- Textbook passages without speakers were hard to read when formatted like dialogue lines.

Files touched:
- `app/bot/utils/course_formatter.py`

Risk:
- This is display-only; stored lesson JSON and progress logic are unchanged.

### 2026-05-25 — Referral trial active access

Changed:
- Users can unlock 3 days of non-paid `active` access after collecting 10 active referrals.
- This reward is separate from the existing referral bonus and referral discount flows: +5 bonus questions and 3-referral discount counters still use their existing fields.
- Referral active access does not set `payment_status=approved`; it creates a fixed $2 AI usage budget for the trial active window.
- In trial active, text/course/photo use the fixed $2 AI budget; photo no longer has a separate daily image limit during this reward window.
- If the fixed $2 AI budget is depleted before 3 days, the non-paid active user is downgraded back to `trial`; if 3 days expire first, the user is also downgraded even if budget remains.
- Voice is restricted to real paid subscribers (`status=active` and `payment_status=approved`); non-paid active windows do not unlock voice.
- Profile labels non-paid active as `Sinov muddati`, shows only referral count, and leaves the subscription line empty unless the user has a real paid subscription.
- A new `users.referral_trial_count_started_at` marker resets this feature's referral count after each 3-day reward window.

Why:
- Trial users need a referral path to temporarily become `active` without replacing a real paid subscription.

Files touched:
- `app/services/referral_service.py`
- `app/services/access_service.py`
- `app/services/ai_usage_budget_service.py`
- `app/services/qa_service.py`
- `app/services/image_qa_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/repositories/referral_repo.py`
- `app/db/models/user.py`
- `app/db/session.py`
- `app/bot/handlers/messages.py`
- `app/bot/handlers/referral.py`
- `app/bot/handlers/commands.py`
- `app/bot/handlers/menu.py`
- `app/bot/keyboards/referral.py`
- `app/bot/utils/i18n.py`
- `alembic/versions/0028_referral_trial_activation.py`

Risk:
- Paid users are still identified only by `payment_status=approved`; do not treat `status=active` alone as paid subscription.

Follow-up:
- Run DB migration in deploy environments before relying on referral trial progress display.

### 2026-05-25 — Referral bonus usage is lifetime

Changed:
- Daily trial limit reset now resets only `questions_used`; it does not reset `bonus_questions_used`.
- Referral trial active activation also keeps already-used referral bonus questions spent.

Why:
- Referral +5 questions are a one-time bonus, not a daily renewed allowance.

Files touched:
- `app/services/access_service.py`
- `app/services/referral_service.py`

Risk:
- Users who already reused bonus questions before this fix are not retroactively corrected.

Follow-up:
- If historical correction is required, add a separate data audit instead of mixing it into runtime access logic.

### 2026-05-24 — Dynamic course dialogue audio admin

Changed:
- Admin audio panel now builds required audio types from each lesson's current `dialogue_json` block count, so HSK4 lessons with 5 dialogues show `vocab` plus `dialogue_1` through `dialogue_5`.
- Audio status now distinguishes complete, partial, and missing lessons, and ignores obsolete audio types that no longer match the current lesson format.
- Course audio playback no longer falls back from `dialogue_2+` to `dialogue_1`; missing dialogue-specific audio now stays unavailable instead of playing the wrong old audio.

Why:
- After lessons were split into more dialogue blocks, the old admin/audio logic could hide later dialogues or reuse outdated audio under the wrong dialogue.

Files touched:
- `app/bot/handlers/admin_audio.py`
- `app/bot/handlers/course.py`
- `app/repositories/course_audio_repo.py`
- `app/services/course_engine_service.py`
- `app/services/course_tutor_service.py`

Risk:
- Existing lessons that only have `dialogue_1` uploaded will show missing audio for later dialogue blocks until admin uploads each specific dialogue audio.

Follow-up:
- If obsolete DB audio should be deleted automatically, add an explicit admin cleanup action instead of silently deleting rows.

### 2026-05-24 — HSK4 upper lesson localization quality

Changed:
- HSK4 上 lessons 1-3 now keep PDF-canonical Chinese dialogue/new-word material while adding Uzbek, Russian, and Tajik translations, dialogue pinyin, localized grammar explanations, and localized mini quiz/homework prompts.
- The HSK4 static mini app fallback data now uses language-aware vocabulary, grammar, and quiz strings instead of Uzbek-only strings.

Why:
- Bot course messages and Mini App could show blank or Uzbek-only explanations for Russian/Tajik users because HSK4 seed payload only contained Uzbek fields and empty dialogue pinyin.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/hsk4_upper_i18n.py`
- `scripts/verify_hsk4_upper_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Dialogue/new words remain source-locked to the textbook data in `scripts/hsk4_upper_pdf_materials.py`; only translations/explanations/pinyin are added in the i18n layer.

Follow-up:
- Use the same localization verifier before enabling HSK4 上 lessons 4-6 in Mini App support.

### 2026-05-24 — Course level completion upgrade flow

Changed:
- When a user finishes the last lesson in a HSK level, the bot now sends a level-completion congratulations message with lesson, vocabulary, dialogue, and study-duration progress.
- The bot then asks whether to move to the next HSK level in Uzbek, Russian, and Tajik. Yes upgrades `users.level`, resets course progress for the next level, and opens lesson 1. No keeps the user on the completed level and shows that level's lesson list.
- Final lessons are now marked completed only once, preventing repeated "next lesson" presses from double-counting progress.

Why:
- The previous final-lesson path only showed a generic "lesson completed" message when no next lesson existed.

Files touched:
- `app/services/course_engine_service.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/messages.py`
- `app/bot/keyboards/course_context.py`
- `app/bot/utils/i18n.py`

Risk:
- Advancing to the next level resets `CourseProgress.completed_lessons_count` for the new level because the current schema stores one course progress row per user.

Follow-up:
- If global cross-level progress is required later, add a dedicated course completion history table instead of overloading the current per-user progress row.

### 2026-05-24 — Course block AI context

Changed:
- HSK course AI prompts now receive block-level course context for block lessons: dialogue block, block vocabulary, grammar points, mini quiz, and mini homework.
- HSK3 lessons 13-16 were wired through `scripts/hsk3_pdf_materials.py`, so dialogue/new words are PDF canonical instead of synthetic seed content.

Why:
- Mini App quiz/homework review must explain the exact user mistakes using the same block material shown in the course.

Files touched:
- `app/services/course_tutor_service.py`

### 2026-05-24 — HSK3 block lesson completion

Changed:
- HSK3 lessons 17-20 now use PDF canonical dialogue/new-word material through `scripts/hsk3_pdf_materials.py`.
- All HSK3 lessons 1-20 now generate per-dialogue block steps with `block_vocab_N` before `dialogue_N`.

Why:
- Lessons 17-20 were still in the older V2 format, so later parts could start directly with `dialogue_3`/`dialogue_4` and skip the new-word section.

Files touched:
- `scripts/hsk3_pdf_materials.py`
- `scripts/seed_hsk3_lesson_17.py`
- `scripts/seed_hsk3_lesson_18.py`
- `scripts/seed_hsk3_lesson_19.py`
- `scripts/seed_hsk3_lesson_20.py`
- `scripts/verify_hsk3_pdf_materials.py`

Risk:
- Database must run the course seed sync or app restart so existing stored lesson JSON is refreshed.

Follow-up:
- If a deployed bot still shows old HSK3 lesson flow, restart/reseed first before debugging UI step logic.

### 2026-05-24 — Block grammar de-duplication

Changed:
- HSK1, HSK2, and HSK3 block lessons now normalize grammar per lesson so the same book grammar number is not shown repeatedly across multiple blocks.
- Every block still gets a short context grammar note based on the actual dialogue sentence used in that block.
- Telegram formatter and Mini App lesson payload prefer block `grammar_notes` over long book grammar items to avoid duplicate-looking explanations.

Why:
- Users saw repeated grammar material across blocks and some blocks felt like they had no useful grammar.

Files touched:
- `scripts/block_context_grammar.py`
- `scripts/hsk1_block_metadata.py`
- `scripts/hsk2_block_metadata.py`
- `scripts/hsk3_pdf_materials.py`
- `app/bot/utils/course_formatter.py`
- `app/services/course_miniapp_lesson_service.py`
- `app/services/course_tutor_service.py`
- `scripts/verify_course_block_grammar.py`

Risk:
- Existing database lesson JSON must be refreshed by seed sync/app restart before deployed users see the normalized grammar.
- `app/services/course_miniapp_result_service.py`
- `scripts/hsk3_pdf_materials.py`
- `scripts/seed_hsk3_lesson_13.py` to `scripts/seed_hsk3_lesson_16.py`
- `scripts/verify_hsk3_pdf_materials.py`

Why:
- 

Files touched:
- 

Risk:
- 

Follow-up:
- 

### 2026-05-24 — HSK4 上 first 3 lessons block format

Changed:
- HSK4 上 lessons 1-3 now use PDF-derived dialogue and vocabulary material through `scripts/hsk4_upper_pdf_materials.py`.
- Each of those lessons has 5 dialogue blocks, per-block vocabulary, one relevant PDF grammar point, mini quiz, and mini homework.
- HSK4 Mini App support is enabled only for lessons 1-3 for now via `hsk4.html`.

Why:
- HSK4 upper lessons had fewer dialogue blocks than the PDF and some lesson 2/3 grammar/vocabulary was from the wrong older seed format.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/seed_hsk4_lesson_01.py` to `scripts/seed_hsk4_lesson_03.py`
- `app/bot/utils/course_miniapp.py`
- `app/static/hsk4.html`

Risk:
- Lessons 4+ are intentionally not enabled in HSK4 Mini App yet; continue in small batches to avoid content errors.

### 2026-05-24 — HSK4 上 lessons 4-6 PDF alignment

Changed:
- HSK4 上 lessons 4-6 now use canonical textbook dialogue/new-word data through `scripts/hsk4_upper_pdf_materials_4_6.py`.
- Each lesson has 5 dialogue blocks, 31 textbook vocabulary items, 5 grammar points, three-language translations, pinyin, per-block mini quiz/homework, and Mini App fallback data.
- Seed files for lessons 4-6 are now thin wrappers so stale non-PDF fallback content cannot leak into runtime data.

Why:
- Lessons 4-6 previously still contained older non-canonical seed material and HSK4 Mini App fallback only covered lessons 1-3.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/hsk4_upper_pdf_materials_4_6.py`
- `scripts/seed_hsk4_lesson_04.py` to `scripts/seed_hsk4_lesson_06.py`
- `scripts/verify_hsk4_upper_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Database must be reseeded for deployed environments; local DB was updated for HSK4-L04, HSK4-L05, and HSK4-L06 in this session.

### 2026-05-25 — HSK4 上 lessons 7-10 PDF alignment

Changed:
- HSK4 上 lessons 7-10 now use canonical textbook dialogue/new-word data through `scripts/hsk4_upper_pdf_materials_7_10.py`.
- Each lesson has 5 dialogue blocks, per-block vocabulary, one relevant grammar point, three-language translations, pinyin, mini quiz, and mini homework.
- HSK4 static Mini App fallback data now covers lessons 1-10 with grammar-focused quiz questions and no fill-blank style quiz items.

Why:
- Lessons 7-10 still had stale seed JSON and Mini App coverage stopped at lesson 6.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/hsk4_upper_pdf_materials_7_10.py`
- `scripts/seed_hsk4_lesson_07.py` to `scripts/seed_hsk4_lesson_10.py`
- `scripts/verify_hsk4_upper_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Database must be reseeded for deployed environments; local DB was updated for HSK4-L07 through HSK4-L10 in this session.

### 2026-05-25 — HSK4 下 lessons 11-13 PDF alignment

Changed:
- HSK4 下 lessons 11-13 now use canonical textbook dialogue/new-word data through `scripts/hsk4_lower_pdf_materials.py`.
- Each lesson has 5 blocks, per-block vocabulary, relevant grammar, pinyin, three-language translations, mini quiz, and mini homework.
- HSK4 static Mini App fallback now recognizes lessons 1-13 and includes grammar quiz items for lessons 11-13.

Why:
- HSK4 下 needed to start from the textbook format; older lower seed data had incomplete lesson blocks and stale lesson 11 content.

Files touched:
- `scripts/hsk4_lower_pdf_materials.py`
- `scripts/hsk4_lower_seed_data.py`
- `scripts/seed_hsk4_lesson_11.py`
- `scripts/verify_hsk4_lower_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Database must be reseeded for deployed environments; local DB was updated for HSK4-L11 through HSK4-L13 in this session.

### 2026-05-25 — HSK4 Mini App support range

Changed:
- HSK4 Mini App support range is now lessons 1-13.

Why:
- HSK4 上 lessons 4-10 had Mini App content and API payloads, but course buttons were blocked by the stale supported range `1-3`.

Files touched:
- `app/bot/utils/course_miniapp.py`

Risk:
- HSK4 lessons beyond 13 stay unsupported until their lesson data is converted.

### 2026-05-25 — HSK4 下 lessons 14-16 PDF alignment

Changed:
- HSK4 下 lessons 14-16 now use canonical textbook dialogue/new-word data through `scripts/hsk4_lower_pdf_materials_14_16.py`.
- Each lesson has 5 blocks, per-block vocabulary, relevant grammar, pinyin, three-language translations, mini quiz, and mini homework generated through the lower seed pipeline.
- HSK4 static Mini App fallback and support range now cover lessons 1-16 with grammar-focused quiz items and no blank-fill quiz format.

Why:
- Lessons 14-16 needed the same PDF-based format as lessons 11-13 before continuing HSK4 下 in small batches.

Files touched:
- `scripts/hsk4_lower_pdf_materials.py`
- `scripts/hsk4_lower_pdf_materials_14_16.py`
- `scripts/verify_hsk4_lower_pdf_materials.py`
- `app/bot/utils/course_miniapp.py`
- `app/static/hsk4.html`

Risk:
- Runtime database must be reseeded or app restarted in deployed environments before Telegram course messages show HSK4-L14 through HSK4-L16.

### 2026-05-28 — HSK4 下 lessons 17-20 PDF alignment

Changed:
- HSK4 下 lessons 17-20 now use canonical textbook dialogue/new-word data through `scripts/hsk4_lower_pdf_materials_17_20.py`.
- Each lesson has 5 blocks, per-block vocabulary, relevant grammar, pinyin, three-language translations, mini quiz, and mini homework generated through the lower seed pipeline.
- HSK4 static Mini App fallback and support range now cover lessons 1-20 with grammar-focused quiz items and no blank-fill quiz format.

Why:
- Lessons 17-20 complete HSK4 下 in the same PDF-based format as lessons 11-16.

Files touched:
- `scripts/hsk4_lower_pdf_materials.py`
- `scripts/hsk4_lower_pdf_materials_17_20.py`
- `scripts/verify_hsk4_lower_pdf_materials.py`
- `app/bot/utils/course_miniapp.py`
- `app/static/hsk4.html`

Risk:
- Runtime database must be reseeded or app restarted in deployed environments before Telegram course messages show HSK4-L17 through HSK4-L20.

### 2026-06-04 — Localized admin messaging and TJS card subscriptions

Changed:
- Admin broadcast and ad campaign text can be written once in Tajik, then localized to TJ/UZ/RU through AI before sending; users receive the variant matching their language.
- Broadcast and ad campaign confirm flows include an admin test send without clearing the prepared message.
- Visa/Card subscription pricing is TJS-only: 10 days = 29 TJS, 1 month = 89 TJS by default. Alipay/WeChat remain in yuan.
- Stale checkout drafts are recalculated when a screenshot arrives so old USD drafts do not survive after the TJS switch.
- Expired admin/feedback discount buttons edit the original offer message to an expired text instead of only showing an alert.

Why:
- Admins should not send separate messages per language, and card subscription revenue should be priced in somoni.

Files touched:
- `app/services/broadcast_translation_service.py`
- `app/bot/handlers/admin_broadcast.py`
- `app/bot/handlers/admin_ads.py`
- `app/services/ad_campaign_service.py`
- `app/services/subscription_price_service.py`
- `app/bot/handlers/subscription.py`
- `app/services/payment_service.py`

Risk:
- Broadcast/ad translations depend on `OPENAI_API_KEY`; if translation fails, the Tajik source is used as a safe fallback.
- Telegram bot updates do not expose user IP, so non-TJ card users see a general bank-rate TJS payment note instead of IP-based country detection.

---

### 2026-06-11 — Menu subscription WebApp auth fix

Changed:
- Main reply keyboard `Obuna` is a normal text button again; the bot handler sends an inline Mini App button with `mode=subscription`.

Why:
- Reply-keyboard `web_app` launches were not reliably connecting the Subscription Mini App to the bot for some users. Inline WebApp buttons keep the Telegram init data flow stable.

Files touched:
- `app/bot/keyboards/main_menu.py`

Risk:
- The menu subscription path uses one bot message before opening the Mini App instead of opening directly from the reply keyboard.

---

### 2026-06-11 — New user course trial funnel and channel checkpoint

Changed:
- New users start as `status="trial"` instead of 24-hour active access.
- Onboarding keeps language and level selection, then asks which course lesson to start: recommended first lesson or another lesson from the selected level.
- Free users can fully complete one selected `CourseLesson`; access to another lesson, next lesson, or level upgrade shows the subscription Mini App offer.
- Added `users.trial_course_lesson_id`, `trial_course_started_at`, `trial_course_completed_at`, `trial_quiz_explanation_used_at`, and `force_sub_required_at`.
- Required-channel checks are skipped until `force_sub_required_at` is set; the flag is set when a free user reaches `block_vocab_2` (`2-qism yangi so'zlar`). After that, existing required-channel middleware checks every free-user event. Paid approved users bypass this check.
- Course Mini App quiz results also set the checkpoint flag if the next step is `block_vocab_2`.
- Admin stats now show paid users by `payment_status="approved"` plus trial course started/completed, trial AI explanation, channel checkpoint, trial-to-paid, completed-to-paid, checkpoint-to-paid, and post-trial revenue metrics.

Preserved:
- Paid approved users still use the existing `AIUsageBudgetService` structure for text/photo/voice-related AI usage.
- Free text AI and photo AI remain daily-limit based; voice remains subscription-only.
- Existing course lesson internals stay intact: vocab, dialogue, block quizzes, grammar, homework, and Mini App result flow are not rewritten.

Risk:
- Existing old users with course progress but no `trial_course_lesson_id` may get their current lesson assigned as their one free trial lesson when they enter course mode.

Files touched:
- `app/bot/handlers/start.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/messages.py`
- `app/bot/middlewares/required_channel.py`
- `app/bot/handlers/required_channel.py`
- `app/bot/utils/i18n.py`
- `app/services/course_trial_service.py`
- `app/services/access_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/services/study_miniapp_service.py`
- `app/db/models/user.py`
- `app/db/session.py`
- `alembic/versions/0038_add_user_trial_course_fields.py`

---

### 2026-06-12 — One-time onboarding tips and trial voice sample

Changed:
- Added `onboarding_tip_events` to queue contextual one-time bot tips per user.
- Course vocab/dialogue/grammar sections queue a 30-second tip; the scheduler sends it only if the user is still on that same course step.
- Normal text/photo usage can queue one-time photo and voice feature tips.
- Added `users.trial_voice_used_at`; trial users can try voice once, while paid approved users keep normal voice access.
- Course Mini App quiz results below 60% show an AI mistake-discussion button that sends the latest quiz context to `CourseTutorService` and edits the processing message into the AI explanation.

Files touched:
- `app/services/onboarding_tip_service.py`
- `app/db/models/onboarding_tip_event.py`
- `app/db/models/user.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/messages.py`
- `app/main.py`
- `alembic/versions/0039_add_onboarding_tip_events.py`

---

## 11. Known Problems

### Problem 1
Problem:
- Unknown / needs inspection

Suspected cause:
- Unknown / needs inspection

Status:
- Open / Fixed / Needs testing

---

## 12. Next Planned Work

Priority 1:
- Unknown / needs inspection

Priority 2:
- Unknown / needs inspection

Priority 3:
- Unknown / needs inspection

---

## 13. Required Environment Variables

Do not write real values here.

Required:
- `BOT_TOKEN`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `ADMIN_IDS`

Optional:
- Unknown / needs inspection

---

## 14. AI Assistant Instructions

Any AI coding assistant working on this project must:

1. Read this file before changing code.
2. Understand the current architecture before editing.
3. Make minimal changes.
4. Preserve working flows.
5. Never store secrets in this file.
6. Update this file only after important changes.
7. Do not write small cosmetic changes here.
8. If changing database/payment/subscription logic, explain the risk.
9. If unsure, inspect the code before guessing.
10. Do not rewrite this file completely unless explicitly requested.
