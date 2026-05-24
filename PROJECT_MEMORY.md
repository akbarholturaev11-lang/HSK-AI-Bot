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
