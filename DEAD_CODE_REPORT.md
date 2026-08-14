# O'lik kod hisoboti — HSK AI bot

Statik tahlil: AST + butun repo bo'ylab token qidiruvi (1065 fayl).

**Metod va istisnolar**

- Chiqarib tashlandi: `@router.*` va `@app.*` handlerlari, testlar, alembic `upgrade`/`downgrade`, dunder metodlar
- Qidiruvga kirdi: `.py .html .js .json .toml .yml .md .txt .kt .sh` + alohida `.rs .css .xml .kts .properties .patch`
- Chiqarib tashlangan papkalar: `.git .claude/worktrees venv .venv node_modules __pycache__ graphify-out build target dist tmp output` va `*.bak*`, `*.save`
- Loyihada dinamik chaqiruv (`getattr(sys.modules)`, `globals()[]`, `eval`, `importlib.import_module`) **yo'q** — tekshirildi, shuning uchun statik tahlil ishonchli
- `import ... as ...` aliaslari hisobga olindi (`current_car`/`current_part` kabi yolg'on ijobiylar olib tashlandi)


## 1. To'g'ridan-to'g'ri o'lik — 33 ta

Butun repoda **atigi 1 marta** uchraydi: o'z ta'rifi. Hech kim import ham qilmaydi.


**./app/api/android_features.py**

- `91-92` (2 qator) — `class AndroidEmptyRequest`

**./app/bot/handlers/commands.py**

- `60-66` (7 qator) — `def _fmt_date`
- `147-152` (6 qator) — `def _days_label`

**./app/bot/handlers/course.py**

- `169-175` (7 qator) — `def _entry_lesson_ordinal`

**./app/bot/handlers/start.py**

- `50-54` (5 qator) — `def _menu_keyboard_for_user`
- `114-133` (20 qator) — `async def _send_trial_lesson_choice`
- `136-146` (11 qator) — `async def _send_daily_practice_entry_message`
- `149-169` (21 qator) — `async def _send_daily_practice_entry_callback`

**./app/bot/handlers/subscription.py**

- `377-410` (34 qator) — `async def _admin_discount_offer`
- `467-469` (3 qator) — `async def _visa_plan_line`
- `518-522` (5 qator) — `async def _referral_link`
- `525-571` (47 qator) — `async def build_subscription_discount_progress_text`
- `613-617` (5 qator) — `async def build_subscription_main_view`
- `620-632` (13 qator) — `async def build_admin_discount_entry_view`
- `635-657` (23 qator) — `async def build_admin_discount_payment_view`
- `713-725` (13 qator) — `async def build_feedback_discount_payment_view`
- `728-757` (30 qator) — `async def build_feedback_discount_plan_view`
- `1298-1359` (62 qator) — `async def _show_checkout`

**./app/bot/keyboards/course.py**

- `78-87` (10 qator) — `def course_vocab_keyboard`
- `120-129` (10 qator) — `def course_exercise_keyboard`
- `177-192` (16 qator) — `def course_vocab_v2_keyboard`
- `274-282` (9 qator) — `def course_reminder_notification_keyboard`

**./app/bot/keyboards/course_context.py**

- `54-64` (11 qator) — `def course_tushundim_keyboard`

**./app/bot/keyboards/course_miniapp.py**

- `162-185` (24 qator) — `def course_miniapp_understood_keyboard`

**./app/bot/keyboards/mode.py**

- `6-16` (11 qator) — `def course_promo_keyboard`
- `19-35` (17 qator) — `def mode_keyboard`

**./app/bot/keyboards/release_feedback.py**

- `35-41` (7 qator) — `def release_feedback_optional_comment_keyboard`

**./app/bot/middlewares/db_session.py**

- `8-19` (12 qator) — `class DbSessionMiddleware`

**./app/main.py**

- `708-715` (8 qator) — `def _admin_miniapp_section_keyboard`

**./app/services/admin_miniapp_service.py**

- `1229-1235` (7 qator) — `def _hot_lead_filter`

**./app/services/airtable_sync_service.py**

- `6-178` (173 qator) — `class AirtableSyncService`

**./app/services/background_tasks.py**

- `4-11` (8 qator) — `def run_background`

**./app/services/course_engine_service.py**

- `171-175` (5 qator) — `def get_block_by_no`


## 2. Tranzitiv o'lik — 45 ta

Faqat import qatorlarida yoki boshqa o'lik funksiya ichida uchraydi. Tirik chaqiruvchi yo'q.


**./app/bot/handlers/course.py**

- `630-632` (3 qator) — `def filter_unlocked_lessons`
- `1059-1088` (30 qator) — `async def activate_free_qa_mode`
- `1093-1304` (212 qator) — `async def run_course_entry_flow`

**./app/bot/handlers/start.py**

- `46-47` (2 qator) — `def _challenge_context`
- `381-573` (193 qator) — `def _get_demo_lesson`

**./app/bot/handlers/subscription.py**

- `60-92` (33 qator) — `def _static_qr_key_for_checkout`
- `117-124` (8 qator) — `async def _checkout_qr_photo`
- `137-138` (2 qator) — `def _campaign_back_callback`
- `150-151` (2 qator) — `async def _visa_local_hint`
- `158-170` (13 qator) — `def _card_payment_note`
- `246-247` (2 qator) — `def _card_checkout_price`
- `278-280` (3 qator) — `async def _payment_details_text`
- `283-306` (24 qator) — `async def _card_checkout_text`
- `309-329` (21 qator) — `async def _discount_plan_line`
- `332-343` (12 qator) — `async def _admin_discount_choices`
- `346-366` (21 qator) — `async def _admin_discount_matrix`
- `369-370` (2 qator) — `def _available_methods`
- `373-374` (2 qator) — `def _available_plans`
- `422-438` (17 qator) — `def _discount_price_detail_line`
- `441-464` (24 qator) — `def _discount_plan_card`
- `574-610` (37 qator) — `def build_subscription_main_keyboard_for_user`
- `660-703` (44 qator) — `async def build_admin_discount_plan_view`
- `706-710` (5 qator) — `async def _get_available_feedback_offer`
- `844-925` (82 qator) — `async def build_checkout_text`

**./app/bot/keyboards/course.py**

- `285-307` (23 qator) — `def next_study_time_inline_keyboard`

**./app/bot/keyboards/course_context.py**

- `67-83` (17 qator) — `def course_review_offer_keyboard`

**./app/bot/keyboards/main_menu.py**

- `27-44` (18 qator) — `def course_menu_keyboard`

**./app/bot/keyboards/onboarding.py**

- `55-67` (13 qator) — `def trial_lesson_choice_keyboard`
- `70-82` (13 qator) — `def daily_practice_entry_keyboard`

**./app/bot/keyboards/subscription.py**

- `68-106` (39 qator) — `def subscription_main_keyboard`
- `109-122` (14 qator) — `def subscription_discount_progress_keyboard`
- `125-154` (30 qator) — `def subscription_discount_ready_keyboard`
- `157-176` (20 qator) — `def payment_method_keyboard`
- `226-276` (51 qator) — `def admin_discount_plan_keyboard`
- `279-301` (23 qator) — `def feedback_discount_payment_method_keyboard`
- `304-341` (38 qator) — `def feedback_discount_plan_keyboard`

**./app/bot/utils/course_formatter.py**

- `503-542` (40 qator) — `def format_grammar`

**./app/bot/utils/discount_formatter.py**

- `13-18` (6 qator) — `def discount_title_for_lang`
- `21-26` (6 qator) — `def discount_reason_for_lang`
- `39-65` (27 qator) — `def format_discount_duration`
- `68-71` (4 qator) — `def format_discount_time`
- `74-75` (2 qator) — `def format_discount_quota`
- `78-81` (4 qator) — `def format_discount_rule`
- `84-111` (28 qator) — `def build_discount_plan_line`
- `114-144` (31 qator) — `def build_admin_discount_block`


## 3. To'liq o'lik modullar — 5 ta

Hech qayerdan import qilinmaydi, Procfile/railway/nixpacks/scripts da ham yo'q.

- **app/bot/keyboards/mode.py** (35 qator) — `course_promo_keyboard`, `mode_keyboard` — ikkalasi ham o'lik
- **app/bot/middlewares/db_session.py** (19 qator) — `DbSessionMiddleware` — bot middleware sifatida ro'yxatga olinmagan
- **app/db/init_db.py** (16 qator) — alembic bor, bu qo'lda ishga tushiriladigan eski skript
- **app/services/airtable_sync_service.py** (178 qator) — `AirtableSyncService` — Airtale integratsiyasi ulanmagan
- **app/services/background_tasks.py** (11 qator) — `run_background` — hech qayerda ishlatilmaydi


## 4. Ishlatilmaydigan i18n kalitlari — 97 ta

Har biri 3 tilda takrorlanadi → taxminan **291 qator matn**.

Dinamik yasaladigan `feedback_*`, `subscription_churn_reason_*`, `onboarding_tip_*` prefikslari **chiqarib tashlangan** (ular `t(f"...")` orqali ishlatiladi).


**course_\*** — 47 ta

```
course_ai_followup_blocked
course_back_to_qa
course_choose_mode_first
course_completed_lessons
course_continue_button
course_current_lesson
course_dialogue_title
course_exercise_title
course_failed
course_grammar_title
course_homework_button
course_homework_saved
course_intro_title
course_lesson_completed_after_homework
course_lesson_started
course_menu_title
course_mode_subscription_benefit
course_next_lesson_button
course_next_lesson_offer
course_next_study_time_optional
course_next_study_time_saved
course_no_button
course_no_progress
course_passed
course_prev_step
course_promo_caption
course_quiz_title
course_reminder_choose_time
course_reminder_disabled
course_reminder_enabled
course_reminder_saved
course_reminder_saved_msg
course_reminder_settings
course_reminder_tz_title
course_resume_lesson
course_resume_offer
course_retry_test
course_review_offer
course_score
course_start_button
course_start_quiz
course_step_completed
course_test_start_button
course_test_submitted
course_try_again
course_vocab_title
course_yes_button
```

**subscription_\*** — 19 ta

```
subscription_admin_discount_window
subscription_block
subscription_checkout_block
subscription_checkout_title
subscription_choose_plan_first
subscription_discount_counter_done
subscription_discount_counter_progress
subscription_discount_plan_10_days
subscription_discount_plan_10_days_yuan
subscription_discount_plan_1_month
subscription_discount_plan_1_month_yuan
subscription_discount_text_blocked
subscription_invite_button
subscription_main_benefits
subscription_payment_request_sent
subscription_plan_10_days
subscription_plan_10_days_yuan
subscription_plan_1_month
subscription_plan_1_month_yuan
```

**admin_\*** — 10 ta

```
admin_approve_button
admin_payment_already_reviewed
admin_payment_amount
admin_payment_full_name
admin_payment_id
admin_payment_new_request
admin_payment_not_found
admin_payment_plan
admin_payment_user_id
admin_reject_button
```

**voice_\*** — 7 ta

```
voice_course_only
voice_mode_activated_qa
voice_mode_activated_translator
voice_status_answering
voice_status_received
voice_status_transcribing
voice_status_understanding
```

**payment_\*** — 4 ta

```
payment_method_choose
payment_pending_created
payment_screenshot_received
payment_waiting_review
```

**btn_\*** — 3 ta

```
btn_alipay
btn_visa
btn_wechat
```

**access_\*** — 2 ta

```
access_subscription_expired
access_trial_expired
```

**choose_\*** — 1 ta

```
choose_mode_after_level
```

**level_\*** — 1 ta

```
level_saved_explained
```

**profile_\*** — 1 ta

```
profile_to_qa_button
```

**referral_\*** — 1 ta

```
referral_invite_button
```

**welcome_\*** — 1 ta

```
welcome_back
```


## Xulosa

| Toifa | Soni | Taxminiy hajm |
|---|---|---|
| To'g'ridan-to'g'ri o'lik | 33 | ~642 qator |
| Tranzitiv o'lik | 45 | ~1241 qator |
| To'liq o'lik modullar | 5 fayl | ~259 qator |
| Ishlatilmagan i18n kalitlari | 97 | ~291 qator matn |
| **Jami** | **78 ta ta'rif + 97 kalit** | **~2170 qator** |

Eng ko'p o'lik kod `app/bot/handlers/subscription.py` da (589 qator) — obuna oqimi Mini App'ga ko'chgach eski Telegram view builderlari qolib ketganga o'xshaydi.


> Hisobot faqat tahlil. Hech narsa o'chirilmadi.
