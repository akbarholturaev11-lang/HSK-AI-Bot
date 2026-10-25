# HSK AI — Smart Reminder System
## MASTER PLAN · Техник қарорлар · Execution Tracker · Context Handoff

**Ҳолат:** PLANNING / NO RUNTIME CHANGE  
**Яратилган:** 2026-10-25  
**Репозиторий:** akbarholturaev11-lang/HSK-AI-Bot  
**Режа тармоғи:** feat/smart-reminder-master-plan-20261025  
**Текширув базаси:** main @ 30e747580f02f4a0acd7adeda15152307c6f66b7  
**Масъул:** HSK AI лойиҳаси эгаси; кодни амалга оширувчи агентлар  
**Қатъий чеклов:** Бу ҳужжатдаги режа ишлаб чиқилган функция, тасдиқланган бизнес қарори ёки production тест натижаси эмас.

> Бу файл Smart Reminder ишининг ягона узоқ муддатли handoff / execution журналидир. Янги чат/агент аввало шу файлни, кейин AGENTS.md, AI_RULES.md, PROJECT_MEMORY.md ва ишга тегишли РЕАЛ КОДНИ ўқийди. Файлда ёзилган эски фактлар кодга зид келса, код ва тегишли тест натижаси устун. Ҳар бир ўзгаришга далил, commit, тест ва қолган иш ёзилади. Сеанс хотирасига суянмаслик керак.

---

## 0. Ҳолат ва далил белгилаш қоидалари

- **[VERIFIED-CODE]** — кўрсатилган ref ва файлда код ўқиб тасдиқланган факт; runtime ишлаши исботланмаган.
- **[REQUIREMENT]** — лойиҳа эгасининг 2026-10-25 да билдирган мақсад/мажбурий шартлари.
- **[PROPOSAL]** — ишлаб чиқиш учун тавсия; ҳали эгаси тасдиқламаган ва код эмас.
- **[DECISION]** — эгаси аниқ қабул қилган қарор (сана ва қарор матни ёзилади).
- **[OPEN]** — қўшимча код аудити, маҳсулот қарори ёки ташқи техник текширув керак.
- **[DONE]** — тегишли commit ва тест далили билан бажарилган.
- **[BLOCKED]** — сабаби ва ҳал қилиш шарти ёзилган.
- **[NOT STARTED]** — иш бошланмаган. Чекбоксни тестсиз ёпма.
- Огоҳлантириш: GitHub’да commit борлиги production deploy, ҳақиқий пуш етказилгани ёки end-to-end QA ўтганини БИЛДИРМАЙДИ.
- Бу ҳужжатга токен, real device token, email, Telegram ID, FCM credentials, user-specific behavioral history ёзилмайди.

## 1. Мақсад ва маҳсулот чегараси

### 1.1 [REQUIREMENT] Асосий натижа
Фойдаланувчининг ўқиш одатлари, фаоллиги, тугалланмаган дарслари, кунлик мақсади ва streak’ини баҳолаб, ўқишга қайтиш эҳтимоли юқорироқ вақтда, тегишли мазмунда, фойдаланувчи рухсат берган каналда фойдали эслатма юбориш. Telegram, Android, келажакдаги iPhone PWA ва Desktop ягона аккаунт сиёсатида ишлайди. Бир ўқув мақсади учун бир неча платформадан такрорий хабар келмаслиги керак.

### 1.2 [REQUIREMENT] Муваффақият
1. Retention: фойдаланувчи реал ўқув фаолиятига қайтиши.
2. Engagement: дарсни давом эттириши/тугаллаши, ўқув сессиялари.
3. Learning consistency: ҳафта давомида фаол ўқиш кунлари.
4. Guardrail: opt-out, блоклаш, шикоят, ортиқча хабар, беўрин вақт, дубликат.

### 1.3 [REQUIREMENT] Ман этилади
- Барчага бир хил вақтда ва бир хил матнда хабар юборишни ягона стратегия деб қабул қилиш.
- Кунлик мақсад бажарилганидан кейин “бажаринг” деган эслатма юбориш.
- Ҳар бир платформа мустақил қарор қабул қилиб такрорлашини қолдириш.
- Усерни безовта қиладиган мажбурий push, рухсатсиз янги канал, ўчирилган хабарларни қайта ёқиш.
- Нотўғри/мавжуд бўлмаган дарсга deep-link ёки блокланган Pro контентга сохта ваъда.
- Ҳар хабар учун қиммат LLM генерациясини базавий dependency қилиш.
- Subscription/payment, direct APK vs Play, entitlement, scoring, HSK контент мантиғини ўзгартириш.

### 1.4 Scope / out-of-scope
**V1 scope:** ўқиш эслатмаси, incomplete lesson, daily goal, streak, inactive learner recovery, account-level policy, Telegram+Android, аналитика асоси.
**Кейинги scope:** learner iPhone PWA Web Push, Desktop каналлари, notification-optimize engine, multi-armed bandit, smart review/word-mastery recommendation, admin analytics UI.
**Out of scope:** Admin PWA’нинг ўз administrator push’ини learner’га айлантириш; тўлов/чеки каби транзакцион хабарларни маркетинг лимитига қўшиш; барча кампаниаларни автомат равишда бу engine’га кўчириш.

## 2. [VERIFIED-CODE] Бошланғич код аудити: 2026-10-25, main

| Контракт | Код манбаи | Кўрилган факт / интеграция хавфи |
|---|---|---|
| Cron/scheduler | app/main.py, _background_scheduler, ~596–652 | Цикл тахминан 60 сонияда; Trial, Daily Reset, Expiry, Motivation, Android study, account notice fallback, CourseReminder, weekly ва бошқалар кетма-кет чақирилади. Битта умумий try/except: битта хато циклда кейинги ишларни қолдириши мумкин. |
| Telegram lesson time | app/services/course_reminder_service.py | CourseProgress.reminder_enabled ва reminder_time билан ±2 дақиқалик ойна; time zone асосан integer offset; local-day sent guard. Telegram delivery ва inbox record алоҳида. |
| Motivation | app/services/motivation_reminder_service.py | incomplete, streak, daily goal, рейтинг, D1 recovery; 20:00–21:30 local goal window; Mini App profile’да notifications_enabled; фойдаланувчи Telegram’га уланган бўлиши керак. |
| D1 эксперимент | app/services/motivation_reminder_service.py + tests/test_motivation_reminder_service.py | D1 биринчи дарс recovery учун Telegram ID асосида 50/50 treatment/control hashing ва 48 соат holdout; мавжуд экспериментни янги rollout бузмасин. |
| Mini App notification toggle | app/main.py, /api/v3/notify; app/db/models/course_miniapp_profile.py | Telegram init-data билан тасдиқланган toggle; profile.notifications_enabled default=True; бу toggle асосан MotivationReminderService’га тегишли. Native-only account учун бу API автоматик ечим эмас. |
| Course reminder preference | app/db/models/course_progress.py | reminder_enabled default=False, reminder_time, reminder_tz_offset, last_reminder_sent_at. Бир нечта алоҳида consent/тартиб мавжуд. |
| Course inbox | app/services/course_notification_service.py; app/db/models/course_user_notification.py | CourseUserNotification user_id + legacy telegram_id, dedupe unique constraint; inbox record **транспортни** глобал dedupe қилмайди. |
| Admin motivation templates | app/services/notification_template_service.py; app/db/models/notification_template.py | UZ/RU/TJ templates, media ва enabled flag бор. Янги engine буларни бекор қилмаслиги шарт. |
| Android transport | app/services/android_push_service.py; app/db/models/android_push.py | FCM token device билан боғланган; Android study_reminders_enabled ва timezone_name мавжуд; device.last_study_push_day. |
| Android study trigger | app/services/android_realtime_push_service.py | Server Android push 20:00 локал соатда 0–29 дақиқалик device bucket билан data-only study_reminder hint жўнатади. Унинг ўзи displayed тасдиғи эмас. |
| Android decision | android/app/src/main/java/com/pomp/hskai/core/notify/StudyReminderCoordinator.kt + ReminderDecision.kt | Android курc map’дан daily goal ва streak текширади; WidgetStore local per-day dedupe; FCM ва WorkManager шу координаторни ишлатади. Бошқа қурилма ва Telegram билан глобал dedupe йўқ. |
| Android realtime receiver | android/app/src/main/java/com/pomp/hskai/core/notify/HskAiMessagingService.kt | study_reminder сервер hint’ини Android StudyReminderCoordinator’га узатади. |
| Account notice delivery | app/services/notification_delivery_service.py; app/db/models/account_notice_delivery.py | Subscription/limit notice учун Android ack + Telegram fallback (10 минут) бор. Бу learner study reminder’нинг ягона delivery механизми ЭМАС; кўчиришдан олдин scope ва duplicate semantics’ни текшир. |
| User identity | PROJECT_MEMORY.md; app/services/account_identity.py; app/db/models/desktop.py | users.id — canonical account. Telegram ID реал мусбат бўлса transport; native-only аккаунт ҳам бор. DesktopDevice.user_id билан қурилмага боғланади. |
| Learning events | app/db/models/course_miniapp_event.py; app/db/models/course_xp_event.py; app/services/daily_plan_service.py | lesson_started/completed, android_lesson_started/completed, XP ва daily plan сигналлари мавжуд. Event семантикаси ва coverage’ини audit қилиш керак. |
| Localization | localization/README.md; localization/ui/{uz,ru,tj}/notifications.json | Янги user-facing текст canonical UZ/RU/TJ source’дан генерация қилиниши шарт; generated файлга қўлда ёзма. |
| QA base | tests/test_motivation_reminder_service.py; tests/test_native_scheduler_transport.py; android/app/src/test/java/com/pomp/hskai/core/notify/* | Мавжуд тестлар бор; ушбу режалаштириш сессиясида тест ишга туширилмаган. |

### 2.1 [OPEN] Махсус текшириш керак бўлган код нуқталар
- [ ] CourseNotificationService.record() фақат params.get("template") бўлса params сақлаётгани, MotivationReminderService эса params["template_service"] юбораётгани текширилди: бу re-localization/inbox параметрларини тушириб қолдириши мумкин. Реал тест билан исботлаб, алоҳида минимал fix қилиш.
- [ ] Main scheduler task’лари error isolation, overlap, multi-worker/replica concurrency, late ticks, DB transaction чегараси: production deploy’га қараб текшириш.
- [ ] Бир user’га рейтинг, daily goal, scheduled course reminder, onboarding, churn, sales/ad campaign параллел келиши мумкинми? Total frequency аудит.
- [ ] Native-only account’да onboarding push розилиги, profile toggle ва Android notification option ўртасидаги семантика.
- [ ] Android FCM accepted vs posted ack, WorkManager stale snapshot, device timezone ва account switching.
- [ ] Бутун app’да deep-link access/entitlement guard ва exact lesson target сақланиши.
- [ ] User-data purge, consent changes, token revoke/logout, Redis/queue infra ва versioned migration conventions.
- [ ] Daily plan/date/XP semantics ва HSK 2.0/3.0 track-specific progress.
- [ ] Ҳозирги main билан фаол integration branch’лар ўртасидаги фарқ; код ишидан олдин target branch қайта белгилансин.
- [ ] iPhone learner PWA ва Desktop learner push қўллаб-қувватлашининг реал коди; Admin PWA push ни learner push деб ҳисоблама.

## 3. Инвариантлар (бузилмаслиги шарт)

**I01 Identity:** барча study delivery policy ва frequency user_id=users.id бўйича. Telegram ID фақат reachability; email тенглиги аккаунт бирлаштирмайди.

**I02 Consent [D01 OWNER APPROVED 2026-10-25]:** Smart Reminder фойдаланувчининг АВВАЛДАН ЁҚИЛГАН ўқиш эслатмалари ўрнига автоматик ишга тушади, янги функция номи билан қайта-қайта алоҳида розилик сўралмайди. Бироқ мавжуд OFF/opt-out ва OS/platform permission'лар мутлақ ҳурмат қилинади; олдин рухсат берилмаган янги OS push канали учун тизим талаб қиладиган илк рухсатни четлаб ўтиб бўлмайди. Legacy settings аниқ mapping қилинмагунча бу канални automatically ON қилма; opt-out pending jobs'ни бекор қилади. Delivery old/new parallel бўлмасин.

**I03 Account-level cadence [D03 APPROVED 2026-10-25]:** Бир аккаунт учун каналлараро ягона study frequency policy: реакция ва фойдали ўқиш натижасига қараб индивидуал хабар тезлиги ўзгаради (ignored / no study → пасайсин; фойдали реакция → хавфсиз бюджетда кўпайиши мумкин). **Қатъий юқори чегара: календар маҳаллий кунида 1 тадан ортиқ study reminder йўқ**, ҳатто бир нечта қурилма бўлса ҳам. Ҳафталик абсолют max ва adaptive thresholds ҳали owner томонидан тасдиқланмаган. Транзакцион хабарлар алоҳида категория.

**I04 Completed goal:** dispatch олдидан canonical daily progress'ни янгидан текшир; мақсад бажарилса бекор қил. Current lesson ва selected HSK track ҳам қайта текширилсин.

**I05 Adaptive time [D04 APPROVED 2026-10-25]:** Барча фойдаланувчилар учун умумий тақиқланган соатлар ёки 22:00–08:00 каби қотирилган вақт чегараси **йўқ**. Engine ишончли шахсий ўқиш одатига қараб куннинг исталган вақтида, шу жумладан кечаси ҳам, эслатма вақтини белгилаши мумкин. Фойдаланувчи аниқ вақтни қўлда белгиласа (D02) ёки махсус тинч вақт/пауза/ўчириш созламасини танласа, бу ихтиёрий чеклов устувор. OS Do Not Disturb/Focus ва notification permission'ларни четлаб ўтмаслик шарт. IANA timezone, DST, travel, day transition, late delivery ва duplicate guard сақлансин. D03 кунлик max 1 хабар ўзгармайди.

**I06 Access:** CTA реал ишлайди, URL signed/allowlisted/validated, paid content bypass қилинмайди; unlock, 7-day trials ва Play/direct split ўзгармайди.

**I07 Security:** push payload'да token/AI contents/sensitive account data бўлмасин; device ownership ҳар token read/ack'dа текширилади.

**I08 Localizations:** барча visible template, settings, CTA — UZ, RU, TJ; кейин тил ўзгарса inbox'да қайта кўрсатиш имкони.

**I09 Experiments:** control group хабар олмайди; эксперимент assignment stable, migration oldinги D1 holdout'ни бузмайди.

**I10 Observability:** ҳар қарор учун reason code (send/suppress); ҳақиқий sent, accepted, shown, opened ва completed бир-бирига тенг эмас.

**I11 Safe rollout:** flags, dry-run, kill switch, rollback, old sender migration. Parallel old+new study scheduler ишлаб турмасин.

**I12 No unearned guarantees:** эслатма 100% ўз вақтида етказилади ёки exactly-once деб ваъда берилмайди (FCM/OS, retry, network); backend ledger + device ack билан натижа имкон қадар яқинлаштирилади.

## 4. [PROPOSAL] Архитектура: сервер ягона decision owner

1. **LearningSignalCollector** — canonical progress, Xp, events, daily plan, active learning days, incomplete parts, timezone, consent, reachability.
2. **UserHabitEstimator** — одатий вақт слоти; ишонч даражаси (cold/warm/confident), weekday/weekend variation, travel changes.
3. **ReminderPolicyEngine (pure deterministic)** — send/suppress, priority, D03 frequency cap, D04 no global time blackout (only explicit user restrictions/OS permission), streak, daily goal, target access; explainable reason codes.
4. **ReminderScheduler/Planner** — account local-date + fire_time_utc + expiration; future jobs reschedule/cancel.
5. **DeliveryOrchestrator** — account-level claim/lock/idempotency, one selected channel; Telegram/Android ҳозир, learner iPhone PWA/Desktop кейин.
6. **NotificationRenderer** — versioned notification template, canonical i18n, safe parameters, CTA target; no live LLM requirement.
7. **OutcomeAttribution** — planned/attempted/accepted/displayed/opened/resumed/completed/optout counters.
8. **Optimizer** — аввал A/B, кейин маълумот етарли бўлса channel/time/content optimization; shadow→guarded ramp.
9. **Admin Control** — on/off kill switch, template controls, experiment sample, delivery metrics; Admin PWA’нинг техник push функционалидан мустақил.

**Қарор чиқариш кетма-кетлиги:**
- Auth/canonical account → study consent → active/blocked/allowed channel → current progress → goal already done? → D03 cooldown/cap and **user-selected** quiet/pause settings only (D04: no global night cutoff) → priority selection → target exists & accessible? → channel capability → reserve unique job → dispatch recheck → platform display confirmation → outcome tracking.
- Ҳеч бири ишончли бўлмаса **no push** — “кўпроқ юборайлик” fallback эмас.
- Upcoming content recommendation (spaced repetition/weak skill) фақат ҳақиқатан мавжуд клиент экран ва access guard билан берилади.
- Кузатилган “одат”ни бир мартаги 20:00 киришдан хулоса қилма.

### 4.1 Reminder intents ва proposed priority
Priority only among eligible intents, all study intents share frequency budget:
1. **resume_unfinished:** дарс бошланган, тугалланмаган, target accessible, session stale эмас.
2. **streak_risk:** ҳақиқий узилиш хавфи, бугун ўқиш қилинмаган, consent, D03 cadence ва фақат user explicitly selected restrictions (D04: no system-wide quiet hours).
3. **daily_goal:** кунлик мақсад реал қолган, attainable task.
4. **reactivation:** бир нечта кун ҳақиқий ўқув фаоллиги йўқ, енгил қайтиш.
5. **due_review:** ишончли mastery/spaced repetition сигнали, реал ишлайдиган route.
6. **generic_habit:** фақат бошқа муҳим, ҳақиқий фойдали intent йўқ бўлса.

Overtaken/rating, weekly progress, onboarding, trial/churn ва admin campaign'ларнинг scope/frequency budget'га кириш-кирмаслиги — [OPEN] бизнес қарори.

### 4.2 Habit/time estimator [D02 APPROVED: smart by default; technical details PROPOSAL]
- Event: real lesson/practice session start; app_open’нинг ўзи “ўқиди” эмас.
- Recent 14–28 days, уникал active study days, foreground/login ва offline duplicate'ларни тозалаш.
- “Confident” учун дастлаб тахминан 5+ мустақил active study day [НЕРАСМИЙ threshold].
- Бир-бирига яқин ўқиш вақтларини slot'ларга бирлаштириш (масалан, 30 минут интервал), айлана вақт чегараси (23:50/00:10)ни тўғри ҳисоблаш.
- **[DECISION D02, 2026-10-25]** Smart Reminder эслатма вақтини фойдаланувчининг амалдаги ўқиш одатлари асосида автоматик мослаштиради; аввалги белгиланган вақтни ўзгармас қоида деб ҳисоблама. Фойдаланувчи аниқ вақтни ўзи белгилаб **қотирса**, автоматик ўзгариш тўхтайди. Тизим етарли ишончли ўқиш маълумотини йиғмагунча аввалги ёқилган эслатманинг танланган вақтини сақлайди; аввалги вақт йўқ бўлса хавфсиз fallback аниқланади. Бунинг учун фойдаланувчига янги функцияни ёқиш ойнаси кўрсатилмайди (D01).
- [PROPOSAL] Auto/manual status аниқ сақланади; manual lock фақат фойдаланувчининг онгли ҳаракатидан келиб чиқсин. Legacy saved reminder time'ни automatic манба билан адаштирма; migration'да D14 билан мослаштир.
- Вақт ойнаси: фойдаланувчининг ўзи 20:00 да дарс бошласа 19:45–20:00 оралиғи [PROPOSAL]; аниқ вақт A/B далилсиз “optimal” эмас.
- Timezone: IANA ZoneInfo (Asia/Shanghai) canonical; эски offset'ни миграция даврида ўқиш, DST ва travel учун сақланган zone name'ни қайта аниқлаш.
- User маҳаллий куни турли OS/device'ларда бир хил ҳисоблансин; сервер authoritative clock.

### 4.3 Example decision contracts [PROPOSAL]
- lesson_completion today after schedule → cancel.
- lesson unfinished yesterday but course switched → revalidate → cancel or correct target; old lesson deep-link'ни чиқарма.
- opened app but not studied → daily goal completed деган хулоса эмас.
- after 3 inactive days → 3–5 minute restart task, агар реал мавжуд; “30 minute lesson required” демаслик.
- **[DECISION D03]** repeated ignore ёки хабардан кейин реал ўқиш бўлмаса кейинги reminder интервали автоматик узайсин. Реал ўқиш қайтиши кўп бўлса хавфсиз чегарада frequency ошиши мумкин; ҳар маҳаллий кунда 1 дан ошмайди. Аниқ observation window / weekly cap / thresholds [OPEN].
- repeated ignore → progressively lower frequency; max inactivity duration ва final stop threshold [OPEN].
- 2 Android phones + Telegram linked → single preferred endpoint / claimed device, no broadcast.

## 5. [PROPOSAL] Database design — migration олдидан код билан келишилади

Мавжуд User, CourseMiniAppProfile, CourseProgress, CourseUserNotification, AndroidPushToken, DesktopDevice, CourseMiniAppEvent, CourseXpEvent schema'ларини қайта ишлатиш; маълумотни икки марта store қилмаслик.

### 5.1 reminder_preferences (new; exact fields review)
- user_id PRIMARY KEY → users.id, ON DELETE CASCADE.
- study_enabled (explicit/effective consent semantics), user_selected_time_local nullable, time_mode: manual_locked|smart_auto (D02: smart automatically learns once sufficient real study history exists; old selected time is preserved during cold start; user may lock manual time). Persist mode and timestamp/source; do not infer explicit manual lock from mere presence of legacy reminder_time.
- timezone_name (IANA); user_quiet_start_local/user_quiet_end_local **nullable explicit override only**. Default = no predefined quiet-hours exclusion (D04). Auto schedule depends on individual reliable learning habit, not a global allowed-hours range.
- channel_policy: preferred|last_reliable|available; preferred_channel optional.
- daily_max (hard server maximum = **1 study reminder per local day**, D03 approved), weekly_max [exact upper bound OPEN; proposal default 3/week], adaptive_cadence_state/cooldown_until (proposed), snooze_until UTC, paused_until UTC. Across Telegram/Android/PWA/Desktop shared canonical account budget; never multiply caps by channel.
- settings_version, updated_at, consent_source, consent_at; **D01:** олдиндан ёқилган, мувофиқ legacy study reminder channel'ларида автоматик Smart upgrade (алоҳида қайта сўраш йўқ); ҳеч қандай old opt-out override эмас; бошқа/янги channel'га permission auto-grant қилиш йўқ. Янги аккаунт default'ини кўчиришдан олдин legacy semantics ва OS талабларига мувофиқ текшир.

### 5.2 reminder_jobs (new immutable logical-intent ledger)
- id UUID; user_id FK; local_day; intent; target_ref with validated type; timezone snapshot, scheduled_at_utc, expire_at_utc.
- policy_version, variant_id, experiment_id/arm, chosen_channel / chosen_device_id nullable.
- status: scheduled|claimed|suppressed|sent_unconfirmed|shown|failed|cancelled|expired.
- Unique constraint (user_id, local_day, category="study") ёки equivalent partial unique index; “битта study message/day” policy'си ўзгарса schema strategy version'ланган бўлсин.
- decision_reason, suppression_reason, attempt counter, last_attempt_at, claim lease/claimed_until.
- Atomic compare-and-set / SELECT FOR UPDATE SKIP LOCKED, multi worker safety; stale claim reclaim.

### 5.3 reminder_attempts (new append-only transport attempts)
- id, reminder_job_id, provider, device_id (nullable), attempted_at, provider_receipt_id (hash/opaque), status, retry_class, ack_at.
- FCM accepted != device shown; Telegram API success != human read; platform constraints bilan displayed unknown бўлиши мумкин.
- Unique attempt-id and idempotency keys; delivery fallback never creates an unrelated second logical reminder.

### 5.4 reminder_outcomes (or existing analytics events, decide by audit)
- event_id/idempotency, job_id, user_id, event_name, timestamp, platform, lesson_ref, session_ref, source.
- server-confirmed lesson completion/XP canonical; client open is supporting signal only.
- minimize payload; raw behavioral logs finite retention; aggregate counts longer.
- No per-user secret or private HSK answer content.

**Lean alternative [OPEN]:** 3 жадвал (preferences, jobs, attempts), outcomes'ни мавжуд canonical analytics event pipeline'га қўшиш. Алоҳида preference table фақат old settings mapping audit'дан кейин.

### 5.5 Migration/backfill rules
- Additive nullable columns/tables; unique constraints old data scan'дан кейин.
- Legacy Mini App notifications_enabled, CourseProgress.reminder_enabled, Android study_reminders_enabled — учта алоҳида setting; ҳуқуқсиз барчасини глобал ON қилиш мумкин эмас.
- **D01 тасдиқланган:** эски эслатмани аллақачон ON қилган ва рухсатли каналларда Smart Reminder'га seamless ўтказиш; қайта consent modal/banner талаб қилинмайди. Legacy OFF/disabled ва OS denied ўзгармайди. Бир channel ON бўлиши бошқа channel'га янги permission бермайди; аниқ per-source precedence/mapping D14 да ҳал қилинади. Backfill ўрганилган танловни сақлайди.
- Backfill one-time with source tag. Хавфли bulk re-send йўқ.
- Purge data, revoked device, logout ва account-link change cascade semantics.
- Alembic heads ва downstream old binaries compatibility.

## 6. Delivery state machine [PROPOSAL]

CANDIDATE → ELIGIBLE / SUPPRESSED → SCHEDULED → CLAIMED → PROVIDER_ATTEMPTED → ACCEPTED_UNCONFIRMED → DISPLAYED_ACK / FAILED / EXPIRED.

- BEFORE_DISPATCH: re-read consent, goal progress, selected course, account status, user timezone, frequency total.
- Unique reservation occurs BEFORE external send, not after it; retry cannot create second logical job.
- Retry transient network errors with bounded backoff, TTL, no stale-day sends.
- FCM provider accepted does not guarantee actual delivery or display. Shown ack from verified device where technically feasible.
- Telegram бот блокланган бўлса token/reachability update; native-only ҳисобга Telegram fallback ясама.
- If channel timeout has ambiguous delivery: no automatic cross-channel resend until suppression/cancel handshake semantics proved. Favor missing one reminder over disturbing with duplicates.
- On resume/offline app starts: perform reconciliation and suppress stale intents. Local notification fallback must consult server-issued logical job/lease or be explicitly disabled once migrated; purely local offline notification cannot guarantee cross-device exactly-once.
- Универсал background scheduler яхшиланса: independent worker failure isolation + process/replica lease, observability, cancellation and graceful shutdown.

## 7. Notification UX / localization / deep-link [PROPOSAL]

- **Settings [D02/D04]:** фойдаланувчи хоҳласа эслатма вақтини қўлда қотиради; акс ҳолда Smart вақт одатга қараб автоматик ўзгаради. Default 22:00–08:00 ёки бошқа тақиқланган соатлар йўқ. Фойдаланувчи ўзи танласа ихтиёрий quiet hours, pause, preferred channel ва opt-out амал қилади; OS Focus/DND'ни четлаб ўтмаймиз. Етарли ўқиш маълумоти йўқ пайтда эски белгиланган вақт сақланади (D02); мажбурий feature promo ёки қайта permission prompt йўқ (D01).
- **Permission flow [D01]:** мавжуд study notification рухсатини Smart upgrade учун такроран сўрама, функционал ҳақида мажбурий onboarding/marketing ойна очма. Янги platform/OS push permission ҳали йўқ бўлса, фақат OS талаб қиладиган рухсат user interaction орқали одатдаги бир марталик оқимда сўралиши мумкин; рад этишни ҳурмат қил. Existing OFF'ни ON қилма, app-level opt-out ва OS-level off'ни ажрат.
- **Content:** UZ/RU/TJ canonical catalog; polite, short, contextual; no invented lesson numbers/XP/minutes. Render placeholders validated and escaped.
- **CTA:** resume lesson vs daily goal vs review; deep-link internal validated target, track/level/access check. Telegram Mini App, Android native, later iPhone PWA and Desktop adaptors, all canonical data.
- **Feed:** existing CourseUserNotification reused where appropriate, inbox item ≠ delivery ledger; re-render after language change and template version handling.
- **Admin:** existing admin motivation template editor сақланади; new study message kinds mapping. No cross-contamination with Admin PWA technical notifications or receipts.
- **Play/Direct:** learner notification may navigate to existing content but cannot introduce forbidden external checkout/self-updater in Play flavour.
- **Privacy:** quiet lockscreen text defaults, user-level sensitive context in notification text must be restrained.

## 8. Channel strategy [PROPOSAL]

| Channel | First target | Eligibility | Delivery proof | Notes |
|---|---|---|---|---|
| Telegram Bot | V1 | real linked Telegram ID, reachable, opted in | Bot API accepted; read unknown | One user account → one logical intent, no fake telegram_id. |
| Android FCM+client | V1 | authorized Android device, FCM token, study opt-in, OS permission | server accepted + client optional shown ack | WorkManager fallback must not independently display duplicate. |
| Learner iPhone PWA | V2 | Home Screen app, user gesture permission, Push API subscription | Web Push provider + SW reporting | Separate learner implementation; Admin PWA push not reused blindly. |
| macOS Desktop / Windows Desktop | V2 | authenticated installation, OS permission, valid capability | platform-specific ack | Paired functional parity; avoid claiming universally reliable background notifications. |

**External platform facts:**
- WebKit iOS Home Screen Web Push support (iOS/iPadOS 16.4+) and user-interaction permission: https://webkit.org/blog/13878/
- Apple Web Push integration: https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers
- Firebase accepted ≠ device delivered; TTL caveats: https://firebase.google.com/docs/cloud-messaging/customize-messages/setting-message-lifespan
- Firebase background/priority behavior: https://firebase.google.com/docs/cloud-messaging/android-message-priority
- APIs/policies can change: reread before implementing corresponding channel.

## 9. Frequency/safety policy — D03 partial owner decision, other details PROPOSAL

- **[DECISION D03, 2026-10-25]:** **2-вариант — адаптив индивидуал лимит** танланди. Агар хабарлар реал ўқишга ёрдам берса, тизим хавфсиз бюджет ичида кўпроқ эслатиши мумкин; фойдаланувчи хабарни эътиборсиз қолдирса, сони камайсин. **Кунига барча каналлар бўйича кўпи билан 1 та study reminder** — ўзгармас юқори чегара. Тизим билдиришнома очилмаганини ягона 'ignored' белгиси деб қабул қилмайди (Telegram read receipt йўқ); canonical lesson progress устувор сигнал. Айни бир кун ичида иккинчи study reminder йўқ.
- [OPEN] Ҳафталик қаттиқ лимит ва адаптив тезликнинг minimum/maximum параметрлари ҳали тасдиқланмаган. **3/week — олдинги таклиф, қарор эмас.** Cold-start'да эски opt-in/мануал вақт созламаларини сақлайди; жадал янги хабар юборишни бошлама. Thresholds offline simulation ва guardrail metrics билан тасдиқланади.
- **[DECISION D04, 2026-10-25]:** умумий 22:00–08:00 ёки бошқа fixed blackout йўқ; вақт фойдаланувчининг исботланган ўқиш одатига максимал мослаштирилади, кечаси ўқийдиганлар учун ҳам. Шахсий тарих етарли бўлмаса D02'даги old scheduled time / conservative nonspamming fallback ишлатилади; global daytime fallback мажбурий эмас. User explicit quiet hours / pause / manual time, notification disabled ва OS Focus/DND устун; OS'ни bypass қилиш ёки одамга ҳеч қандай сигналсиз тунда кўп хабар юбориш мумкин эмас. D03 1/day сақланади.
- If daily goal done before send: cancel; do not silently reschedule to a different intent same day.
- Message ignored on repeated cycles: reduce frequency gradually; 14+ inactive days pause [OPEN].
- Cooldown after voluntary lesson session so it never nags somebody already learning.
- Frequency budget: do rating notifications and weekly reports share? [OPEN]; sales/marketing on different budgets but global annoyance cap considered.
- Consent “off” must trump AI recommendation. Snooze/disable easy from settings and where platform supports direct notification actions.
- No fear/pressure manipulative streak text. No false prediction that user “will lose all progress”.
- All numbers above are proposals, NOT final business decisions.

## 10. Analytics, causal evaluation, optimization

### 10.1 Events (server names proposals)
reminder_candidate_evaluated, reminder_suppressed, reminder_job_reserved, reminder_dispatch_attempted, reminder_provider_accepted, reminder_device_displayed, reminder_opened, reminder_lesson_resumed, reminder_learning_completed, reminder_user_opted_out.

Every event captures: canonical user_id or aggregate-safe key; reminder_id, experiment arm, policy_version, rendered template key/variant, platform, local_day, decision timestamp, reason, source; client facts cannot forge server-owned lesson completions.

### 10.2 Primary KPIs (formal definition before experiment)
1. **D7 learning retention:** eligible signup/exposure cohort users with server-confirmed learning activity on day 7 / all eligible cohort users. Cohort origin and exact day window versioned.
2. **Weekly active learning days:** per-user distinct local dates with server-confirmed lesson/practice activity, averaged over enrolled experiment participants.
3. **Completed learning units / learner-week:** unique server-confirmed completed lessons/eligible study tasks; protect against inflated repeats.

Supporting: resumed lessons per eligible user, percentage scheduled→shown→opened→learned; time/channel distribution. Guardrail: unsubscribe, bot blocks, OS denied, complaint, duplicate displayed, late arrival, crash/scheduler latency, notification cost.

**Crucial:** opened/delivered rates alone are not retention; outcome measured at user/account level, not notification level only.

### 10.3 Experiments [PROPOSAL]
- First rollout: deterministic rule policy shadow mode → small canary → treatment/control split; unit of randomization users.id, not device nor Telegram ID.
- Stable assignment persisted, migration old D1 experiment mapping protected. No overlap/multiple simultaneous experiments without mutual exclusion.
- Measure intent-to-treat (all assigned eligible users), also delivered-user diagnostics separately; never compare responders-only to all nonresponders.
- 1st experiments: (a) reminder vs holdout, (b) manual/default vs habit-based time after verified value, (c) short lesson-oriented vs generic content, (d) channel preference after real consent.
- Enforce safety guardrail thresholds + stop rule; sample size/power and duration chosen from real baseline, not arbitrary 7 days.
- Models only after enough data: explainable ranking / contextual bandit; offline evaluation, exploration budget, strict cap, fallback deterministic, versioned policy. LLM-generated marketing copy not core.

## 11. Иш босқичлари, рақамланган чеклист ва acceptance

### P0 — Full integration audit / policy lock
**Ҳолат:** [NOT STARTED]
- [ ] Main/current feature target ref SHA, runtime environment, production flags, active scheduler/replicas and schema head аниқлансин.
- [ ] Барча reminder senders, push/OS permissions, consent toggle, notification preferences ва policy matrix инвентаризация қилинсин; **D01 mandatory:** legacy enabled → silent Smart migration, disabled → remains off, denied channel → no push, no duplicate system permission prompt.
- [ ] Canonical study event granularity, day/timezone semantics, idempotency, deep-link ва lessons guards аниқлансин.
- [ ] P0 risks reported, owner-selected defaults and scope ledger DECISION деб қайд этилсин.
**Acceptance:** repo code references + event flow diagram + old/new coexistence switch table + no unverified architecture claims.
**QA:** static audit, affected existing unit tests baseline ва version/branch check; production metrics only if legitimately accessible.

### P1 — Instrumentation + schema foundation
**Ҳолат:** [NOT STARTED]
- [ ] Minimum additive models/migrations; unique keys, indexes, FK cleanup, dry-run explain reasons.
- [ ] Preference mapping/API endpoints: auth, validation, optimistic revision, old client compatibility; D01 seamless migration only for pre-enabled same channel, explicit opt-out preserved, no extra Smart opt-in dialog.
- [ ] Canonical event collector and daily-learning aggregation; no duplicate score/event counts.
- [ ] Privacy and deletion/retention hooks, diagnostics.
**Acceptance:** migration up/down where safe, invalid account/token rejected, dual-read settings coherent, no reminders newly sent.
**QA:** SQLite/Postgres migration, concurrent preference writes, NULL Telegram identity, legacy backfill, delete/logout/token revoke.

### P2 — Deterministic decision engine (DRY RUN)
**Ҳолат:** [NOT STARTED]
- [ ] Policy pure function: reasons, priorities, frequency budget, only user-selected quiet hours/pause (D04: no global preset), current-day done, snooze; D03 personalized cadence by verified learning reaction, one study reminder/user/local day absolute cap, ignored→decelerate, safe learning return→increase only under cap; weekly hard cap still OPEN.
- [ ] **D02:** Smart habit estimator with reliability; enough observed study days бўлмагунча existing reminder time сақлаш; user қўлда вақтни қотирган бўлса optimizer override қилмасин; changed habit adaptation and zone/DST tests.
- [ ] Job reservation/cancel/recompute and policy versioning; no network delivery.
- [ ] Shadow logs compared against old reminders without user notification.
**Acceptance:** identical inputs → identical decisions, safe suppress when data unknown, one study job/account/day, dry-run has no side effects.
**QA:** midnight/DST/travel, 0 offset, incomplete→done race, 2 schedulers, duplicate events, stale activity, account-switch.

### P3 — Telegram delivery integration
**Ҳолат:** [NOT STARTED]
- [ ] Telegram notifier adapter, templates UZ/RU/TJ, validated lesson deep-link; existing admin template edit.
- [ ] Feature flag selectively routes Telegram study reminders new engine. Old CourseReminder/Motivation senders skip users controlled by new engine. D01: eligible existing ON learners migrate without re-consent; OFF users are suppressed. D03: account daily study cap enforced also when course reminder and motivation intent compete.
- [ ] D1 holdout protected; opt-out/blocked, rate limiting, retry ledger and logging.
- [ ] Pilot cohort + rollback to old behavior without double-send.
**Acceptance:** canonical account receives no duplicate; all linked/unlinked/blocked cases correct; genuine reminder opens valid lesson.
**QA:** unit+integration with fake bot, multi-instance, callback/deeplink, rendered locale, 3-day cooldown, failure/retry.

### P4 — Android unified reminder
**Ҳолат:** [NOT STARTED]
- [ ] Android FCM data contract includes job ID, TTL, policy version, no sensitive payload.
- [ ] Client verifies account/device, current goal/consent, notified job state; post ack with safe auth.
- [ ] WorkManager local fallback consults shared job semantics or is suppressed when server-owned; no dual display.
- [ ] Direct+Play parity; OS notification channel user preference respected.
**Acceptance:** one account Telegram+2 Android devices ≤1 visible study reminder within policy, as far as ack/capability allows. No false done/failure statuses.
**QA:** Android 13 permission denied, offline FCM, revoked token, delayed hint, sign-out, two devices, old-client rollout, Play vs direct.

### P5 — Learner PWA + Desktop transport
**Ҳолат:** [NOT STARTED]
- [ ] Confirm learner PWA installability, HTTPS, manifest, service worker scope, consent, push subscription cleanup.
- [ ] Build learner push subscription endpoints; do not reuse Admin PWA auth/push as learner API.
- [ ] macOS/Windows OS notification parity, foreground/background support boundaries, deep-link and logged-out behavior.
- [ ] Cross-platform opt-out, channel preference, fallback and suppression tests; D03 adaptive cadence and at most one study reminder/account/local day even when Telegram+Android+PWA+Desktop are concurrently available.
**Acceptance:** supported conditions send, unsupported/denied conditions clearly no-send; shared ledger with Telegram/Android.
**QA:** real supported iPhone Home Screen PWA, Safari/macOS, Windows, multi-account, device removal, blocked OS notifications.

### P6 — Analytics + controlled experiments + admin observability
**Ҳолат:** [NOT STARTED]
- [ ] Server events, attribution IDs, cohorts, dashboards with real denominators.
- [ ] Stable user-level randomized control, D1 experiment interference audit, metrics baselines.
- [ ] Admin controls: kill switch, content preview, delivery/suppression counts, volume metrics, not fake sample data.
- [ ] Notification annoyance guardrails and alerting.
**Acceptance:** replay sample data deterministic, cohort reports consistent, control never dispatched, production users not exposed without policy gate.
**QA:** attribution late/duplicate event, logging failure isolation, control/treatment equality check, privacy.

### P7 — Optimization (after statistically useful evidence)
**Ҳолат:** [NOT STARTED]
- [ ] Compare time/content/channel randomized performance and data sufficiency.
- [ ] Simple transparent scoring first; stronger learner model only if causal uplift.
- [ ] Exploration frequency caps + model rollback, holdout continual.
**Acceptance:** experimentally measured better learning outcomes with guardrails; otherwise keep rule policy.
**QA:** simulations, data leakage, sparse/cold-start cohorts, silent users, missing channel ack.

### P8 — Release / documentation closeout
**Ҳолат:** [NOT STARTED]
- [ ] Versioned staged rollout, release flags/rollback, incident procedures and migration safety.
- [ ] Full regression in affected learning, auth, subscription, localization and device flows.
- [ ] Exact commit/PR/test evidence and production monitoring results archived in THIS file; update permanent PROJECT_MEMORY per AGENTS.md when justified.
- [ ] No leftover legacy double-senders / migration TODOs; clean owner handoff.
**Acceptance:** owner explicitly accepts real test outcomes and monitored rollout; mark COMPLETE only then.

## 12. Regression matrix (қатъий текширилади)

- [ ] Telegram-linked + Android same user, Telegram-only, native Google/Apple-only (Telegram ID NULL), unlinked, re-linked valid Telegram, blocked Telegram.
- [ ] Same user multiple Android devices, Android+PWA+Desktop, stale/revoked token, old APK clients.
- [ ] Global off / Android OS off / Telegram opt-out / wrong channel / double permission toggle / paused/snoozed.
- [ ] Daily goal complete just before send; unfinished lesson completed on another platform; course switched HSK2→HSK3; restricted course CTA.
- [ ] 2 workers concurrently tick; queue restart; DB timeout; send succeeds then commit fails; provider accepted but unshown; retry after cancellation.
- [ ] Zero timezone, fractional UTC offset, summer time DST, timezone edited, clock skew, midnight, long offline period, late push after local day; D04: observed late-night study may lead to a late-night reminder, but no invented global night blackout; respect user quiet override and OS Focus.
- [ ] UZ/RU/TJ template, HTML escaping, long text, after language change and admin template changes.
- [ ] Event duplicate/replay, experimental holdout, analytics attribution, client forgery safety.
- [ ] Free/trial/Pro/expired account; Android Play notification action never links prohibited direct payment.
- [ ] Notification enable/disable legacy migration, data export/purge and user deletion.
- [ ] Cost/frequency cap guardrail, study message vs subscription/receipt separate routing.

## 13. [OPEN] Owner product decisions — confirm BEFORE relevant code

| ID | Савол | Тавсия / олдинги маълумот | Status |
|---|---|---|---|
| D01 | Smart Reminder'ни фойдаланувчи қандай қабул қилади? | **1-вариант танланди:** аллақачон рухсат берилган/ёқилган ўқиш эслатмаларини Smart Reminder'га автоматик seamless upgrade; қайта-қайта рухсат сўралмайди; фойдаланувчига функция номи эмас, қулайлик муҳим. Илгари OFF қилган ва OS denied каналлар ўзгармайди, янги OS каналига қўшимча permission талабини четлаб ўтмаймиз; exact legacy mapping D14 да. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D02 | Эслатма вақти автоматик ўрганиладими? | **2-вариант тасдиқланди:** вақт фойдаланувчи одатига автоматик мослашади; ишончли маълумот йиғилмагунча мавжуд вақт сақланади; user истаса аниқ вақтни ўзи белгилаб автоматик ўзгаришни тўхтатади. D01'га мувофиқ янги activation prompt талаб қилинмайди. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D03 | Study reminder'лар қанчалик тез-тез юборилади? | **2-вариант тасдиқланди:** фойдаланувчининг ҳақиқий ўқиш реакциясига мосланувчи индивидуал frequency; эътиборсиз қолса камаяди, фойда берса хавфсиз доирада ошиши мумкин. **Қатъий чегара: 1 study reminder / account / local day, барча каналлар бирга.** Ҳафталик max ва аниқ adaptive thresholds OPEN, 3/week фақат таклиф. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D04 | Эслатманинг тақиқланган умумий соати борми? | **OWNER CUSTOM DECISION:** умумий белгиланган вақт лимити ЙЎҚ; вақт фойдаланувчининг ўқиш одатига максимал мослашади, ҳатто кечаси ҳам. User manual time / self-set quiet hours / pause / opt-out ва OS DND/permission устун; D03 кунлик 1 та лимит сақланади. Cold-start D02'га мувофиқ. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D05 | Рейтинг/weekly progress ҳам global study budget’гами? | Рейтингни камайтириш/алоҳида product decision. | OPEN |
| D06 | Channel preference? | User manually override, otherwise most reliable available single channel. | PROPOSAL |
| D07 | Multi-device ack timeout/fallback? | Unknown display бўлса blind Telegram duplicate’га йўл қўйма. | PROPOSAL |
| D08 | 3/7/14 кун inactivity sequences? | staged reactivation + cap, hard stop threshold after data. | PROPOSAL |
| D09 | AI/ML қачон? | Rules → A/B → verified lift → optimizer, LLM optional. | PROPOSAL |
| D10 | iPhone PWA ва Desktop биринчи release scope’дами? | V1 TG+Android; V2 learner PWA+Desktop. | PROPOSAL |
| D11 | Admin PWA'да қайси controls/statistics? | kill switch, templates, reachability, A/B results; no fake stats. | PROPOSAL |
| D12 | KPI target % ва эксперимент муддати? | Реал baseline ва sample size'сиз аниқ рақам тасдиқланмайди. | OPEN |
| D13 | User unread/replied behavior privacy retention? | Мін. керакли маълумот ва aggregate; exact TTL TBD. | OPEN |
| D14 | Existing reminder toggle UX migrates how? | Explicit mapping matrix; no surprise opt-in. | OPEN |

**Decision update rule:** owner қабул қилса бир қаторни “DECISION: YYYY-MM-DD, exact wording, effect, owner” деб ўзгартир; тегишли инвариант, migration ва phase қабул мезонини ҳам шу commit'да мосла. Мумкин бўлмаган функцияни DONE деб ёзма.

## 14. Upcoming audit / immediate next action

1. [ ] P0 source graph'ни тўлиқлаш: active branches, scheduler deployment/config/replicas, all existing reminder types and per-platform settings, existing devices/log tables.
2. [ ] All notifications consent / dedup collision matrix'ни concrete with code line references тайёрлаш.
3. [ ] D01–D14 product decisions'ни муҳокама қилиб қабул қилиш; ҳозир тасдиқланмаган proposals'ни code деб тушунмаслик.
4. [ ] Only then P1 migration/API design → implementation tasks.
5. [ ] Separate PRs by phase, explicit merge/production verification and update this plan at each milestone.

### 14.1 Session resume protocol (агент учун)
1. Бу файлни тўлиқ ўқи: sections 0, 2, 3, 11, 13, 14, 15 биринчи навбатда.
2. AGENTS.md, AI_RULES.md, PROJECT_MEMORY.md, localization/README.md ва ўзгартириладиган platform docs'ни ўқи.
3. Current branch HEAD, main HEAD ва relevant feature branches, PRs; production/test data if accessible; document ref drift.
4. Re-read real source before claims; PR/commit evidence; no .md-only audit.
5. Work exactly on first unchecked unblocked task; claim no previous test passing without logs.
6. Update same file: status, code refs, decisions, risks, executed tests with results, remaining tasks and recovery commands.
7. Re-read file after write, check branch / status / no unrelated diffs. Do not modify payment, admin push, production flags unrelated to scope.
8. In final response tell user: changed files, branch, commit, verified tests, next exact task.

## 15. Change log / verifiable work ledger

| Date | Scope | Result | Commit/PR | Tests | Next |
|---|---|---|---|---|---|
| 2026-10-25 | Initial discovery and single-file master-plan scaffold | Real main source inspected; planning proposals and unresolved decisions recorded. **Runtime unchanged.** | d01263f772f8cc72486cdfa8f6f113115783f615 (initial file commit) | NO TESTS RUN; code read only | P0 audit + D01–D14 lock |
| 2026-10-25 | D01 owner decision | Option 1 approved, existing ON study notifications silent upgrade; OFF/OS-denied protected. Docs only. | feca3f44086128fb213dbeb9e48814673c9c6c2c | NO TESTS RUN; requirements record only | D02 time behavior discussion; D14 mapping audit |
| 2026-10-25 | D02 owner decision | Option 2 approved: smart time learns habit and adapts; manual lock optional; old time kept until confident. Docs only. | 55aeb68f6b7a379e3bcd6b78ab88f065277dc4be | NO TESTS RUN; requirements record only | D03 notification frequency; D14 legacy time migration |
| 2026-10-25 | D03 owner decision | Option 2 approved: personalized adaptive cadence; strict 1 study reminder/account/local day; weekly ceiling and thresholds remain OPEN. Docs only. | 7989bb0d74a4d26f122e81423df8b33cf277bb80 | NO TESTS RUN; requirement record only | D04 quiet hours discussion, cadence tuning later |
| 2026-10-25 | D04 owner custom decision | No system-wide time-of-day limits: maximum personalization even at night; optional personal quiet/pause, OS Focus/DND preserved; 1/day from D03 unaffected. Docs only. | жорий docs commit | NO TESTS RUN; decision captured only | D05 rating and weekly progress notification budget |

**Final completion criteria:** P0–P8 acceptance achieved; automated + manual affected flow QA evidenced; global dedupe/opt-out/progress guards verified on real clients; experiment results/guardrails recorded; production rollout monitored; owner accepts completion. Until then status remains IN PROGRESS.

## 16. [DECISION] Қарорларни муҳокама қилиш ва файлга ёзиш протоколи

**Эгаси тасдиқлаган иш усули (2026-10-25):**
1. Бир мартада **фақат битта** маҳсулот ёки архитектура қарори муҳокама қилинади.
2. Агент аввал масалани оддий, техник бўлмаган тилда қисқача тушунтиради: нега муҳим, фойдаланувчида нима ўзгаради, асосий хавф нимада.
3. Ҳар бир масала учун **айнан иккита реал вариант** беради. Ҳар бир вариантнинг ютуғи ва камчилиги аниқ кўрсатилади.
4. Агент ўзининг **битта аниқ тавсияси**ни айтади ва сабабини тушунтиради. Вариантлар сунъий равишда тенг деб кўрсатилмайди.
5. **Якуний маҳсулот қарори фақат лойиҳа эгасига тегишли.** Агент тавсияни ўзбошимчалик билан тасдиқланган қарорга айлантирмайди.
6. Эгаси вариантни танласа ёки аниқ ўзгартириб тасдиқласа, агент **шу жавобнинг ўзида** `docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md` файлига GitHub орқали дарҳол ёзади; кейин файлни қайта ўқиб, commit натижасини текширади.
7. Ёзилган қарорда: ID, сана, тасдиқланган вариант/аниқ қоида, унинг техник оқибати, legacy compatibility, хавфлар ва acceptance criteria кўрсатилади. Тегишли инвариант, босқичлар ва очиқ саволлар ҳам синхронлаштирилади.
8. Ҳар тасдиқдан кейин муҳокама навбатдаги битта саволга ўтади. Эгаси ҳали қарор бермаган бўлса, статус **OPEN/PROPOSAL** қолади ва ҳеч қандай runtime код ўзгартирилмайди.
9. Муҳокамада аниқланган техник фактлар код билан қайта текширилиши шарт. Файлдаги қарорни implementation DONE деб белгилаш мумкин эмас; implementation ва тест алоҳида исботланади.
10. Янги чат очилганда агент шу протоколни сақлайди, кейинги тасдиқланмаган Dxx саволини топади, олдинги тасдиқларни қайта савол қилмайди (код ёки scope жиддий ўзгармагунча).

**Қарор берилиш формати (agent response):**
- **Масала Dxx:** содда тушунтириш, нима учун муҳим.
- **1-вариант:** қандай ишлайди; плюси ва минуси.
- **2-вариант:** қандай ишлайди; плюси ва минуси.
- **Менинг тавсиям:** 1 ёки 2 ва аниқ сабаб.
- **Сизнинг танловингиз:** 1 / 2 / ўзгартирилган қоида.

**Жорий навбат:** **D05** — рейтингда орқага тушиш ва ҳафталик ҳисоботлар ҳам study reminder'нинг битта кунлик лимитига кирадими ёки улар алоҳида, лекин global anti-spam guard биланми? **OPEN; owner қарори кутилмоқда.** D01/D02/D03/D04 тасдиқланган; D03 weekly upper cap ва D14 technical mapping алоҳида OPEN.

### 16.1 Decision log
| ID | Дата | Тасдиқ | Таъсир | Commit |
|---|---|---|---|---|
| PROCESS-01 | 2026-10-25 | Ҳар саволда содда тушунтириш + 2 вариант + агент тавсияси; фақат owner танлайди, сўнг дарҳол шу файлга қайд этилади | Барча кейинги Smart Reminder қарорларига | жорий docs commit |
| D01 | 2026-10-25 | **1-вариант:** аллақачон эслатма ёқилган каналларни Smart Reminder'га автоматик ўтказиш, қайта-қайта рухсат сўрамаслик. OFF/denied ва OS илк рухсати сақланади. | I02, preferences/migration, P0/P1/P3, UX; D14 mapping still OPEN; no runtime change | feca3f44086128fb213dbeb9e48814673c9c6c2c |
| D02 | 2026-10-25 | **2-вариант:** Smart Reminder ўқиш одатини ўрганиб вақтни автоматик мослаштиради; маълумот етарли бўлмагунча эски вақтни сақлайди; фойдаланувчи хоҳласа аниқ вақтни қўлда белгилаб қотиради. | Habit estimator, preferences/time_mode, UI, P2 ва timezone QA; time thresholds ҳали PROPOSAL; runtime ўзгармаган | 55aeb68f6b7a379e3bcd6b78ab88f065277dc4be |
| D03 | 2026-10-25 | **2-вариант:** individual adaptive cadence, ignored → frequency decreases; real study response → increases only within safe bound; **max 1 study reminder/user/local day** across platforms. Weekly absolute cap / algorithm thresholds NOT DECIDED. | I03, preferences, P2/P3/P5, policy and regressions; runtime unchanged | 7989bb0d74a4d26f122e81423df8b33cf277bb80 |
| D04 | 2026-10-25 | **Owner modification:** no predefined hours/blackout, completely habit-adaptive time including nighttime, user manual/quiet/pause and OS DND preserved, D03 cap remains. | I05, engine eligibility, user preferences, UX, policy, P2 DST/night-time test; runtime unchanged | жорий docs commit |
