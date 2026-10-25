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
**V1 scope [D10 APPROVED 2026-10-25]:** ўқиш эслатмаси, incomplete lesson, daily goal, streak, inactive learner recovery, account-level policy, **Telegram бот/Mini App ва Android transport'ларига биринчи ишловчи релиз**, аналитика асоси. Серверда **бошидан users.id бўйича универсал multi-platform architecture**: provider adapter contracts, per-channel consent/capabilities, device eligibility, single-job account dedupe, notification policy ва deep-link routing platform-neutral; iPhone learner PWA/Desktop'ни кейин қўшиш учун core decision engine'ни қайта ёзиш талаб қилинмасин. Mini App Telegram bot channel орқали қабул қилади, browser native push'ини биринчи релизда бор деб ҳисоблама.
**V2 scope [D10 APPROVED]:** learner iPhone PWA Web Push ва macOS/Windows Desktop notification transport'лари V1'нинг блокери ЭМАС. Кейин шу умумий сервер policy/API'сига реал capability/OS permission билан боғланади. Ундан ташқари ML-based notification optimization (D09 gate), multi-armed bandit, smart review/word-mastery recommendation, admin analytics UI staged features. **[D09]:** V1 launch policy is already adaptive rule-based and must collect training-quality data; future ML infrastructure is staged/validated globally but automatically becomes active for an eligible user once sufficient high-quality personal signals and model-performance guardrails are met. No separate per-user ML training is required by product decision.
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

**I03 Account-level cadence [D03/D06 APPROVED 2026-10-25]:** Бир аккаунт учун каналлараро ягона study frequency policy: реакция ва фойдали ўқиш натижасига қараб индивидуал хабар тезлиги ўзгаради (ignored / no study → пасайсин; фойдали реакция → хавфсиз бюджетда кўпайиши мумкин). **Қатъий юқори чегара: календар маҳаллий кунида 1 тадан ортиқ study reminder йўқ**, ҳатто бир нечта қурилма бўлса ҳам. **D06:** сервер фойдаланувчи ҳақиқатан қайси платформада кўпроқ ўқиётганини, delivery reachability/permission ва ишончлиликни ҳисобга олиб *битта канал ва битта мақсадли қурилмани* танлайди; фойдаланувчи хоҳласа ўз каналини қўлда қотиради (auto selection override). Ҳафталик абсолют max ва adaptive thresholds ҳали owner томонидан тасдиқланмаган. Транзакцион хабарлар алоҳида категория.

**I04 Completed goal:** dispatch олдидан canonical daily progress'ни янгидан текшир; мақсад бажарилса бекор қил. Current lesson ва selected HSK track ҳам қайта текширилсин.

**I05 Adaptive time [D04 APPROVED 2026-10-25]:** Барча фойдаланувчилар учун умумий тақиқланган соатлар ёки 22:00–08:00 каби қотирилган вақт чегараси **йўқ**. Engine ишончли шахсий ўқиш одатига қараб куннинг исталган вақтида, шу жумладан кечаси ҳам, эслатма вақтини белгилаши мумкин. Фойдаланувчи аниқ вақтни қўлда белгиласа (D02) ёки махсус тинч вақт/пауза/ўчириш созламасини танласа, бу ихтиёрий чеклов устувор. OS Do Not Disturb/Focus ва notification permission'ларни четлаб ўтмаслик шарт. IANA timezone, DST, travel, day transition, late delivery ва duplicate guard сақлансин. D03 кунлик max 1 хабар ўзгармайди.

**I06 Access:** CTA реал ишлайди, URL signed/allowlisted/validated, paid content bypass қилинмайди; unlock, 7-day trials ва Play/direct split ўзгармайди.

**I07 Security:** push payload'да token/AI contents/sensitive account data бўлмасин; device ownership ҳар token read/ack'dа текширилади.

**I08 Localizations:** барча visible template, settings, CTA — UZ, RU, TJ; кейин тил ўзгарса inbox'да қайта кўрсатиш имкони.

**I09 Experiments:** control group хабар олмайди; эксперимент assignment stable, migration oldinги D1 holdout'ни бузмайди.

**I10 Observability:** ҳар қарор учун reason code (send/suppress); ҳақиқий sent, accepted, shown, opened ва completed бир-бирига тенг эмас.

**I11 Safe rollout:** flags, dry-run, kill switch, rollback, old sender migration. Parallel old+new study scheduler ишлаб турмасин.

**I12 No unearned guarantees [D07 APPROVED 2026-10-25]:** эслатма 100% ўз вақтида етказилади ёки exactly-once деб ваъда берилмайди (FCM/OS, retry, network); backend ledger + device ack билан натижа имкон қадар яқинлаштирилади. **D07: фақат биринчи канал/қурилмада хабар кўрсатилмагани ишончли исботланса**, consent/expiry/progress/cap текширувидан кейин шу logical job учун бошқа рухсатли каналга қайта юбориш мумкин. Биринчи натижа **номаълум** бўлса, таймаутнинг ўзи исбот эмас — бошқа каналга қайта юборилмайди. Account/payment transactional notices учун олдинги махсус fallback қоидаси ўзгармайди.

## 4. [PROPOSAL] Архитектура: сервер ягона decision owner

1. **LearningSignalCollector** — canonical progress, Xp, events, daily plan, active learning days, incomplete parts, timezone, consent, reachability.
2. **UserHabitEstimator** — одатий вақт слоти; ишонч даражаси (cold/warm/confident), weekday/weekend variation, travel changes.
3. **ReminderPolicyEngine (pure deterministic)** — send/suppress, priority, D03 frequency cap, D04 no global time blackout (only explicit user restrictions/OS permission), streak, daily goal, target access; explainable reason codes.
4. **ReminderScheduler/Planner** — account local-date + fire_time_utc + expiration; future jobs reschedule/cancel.
5. **DeliveryOrchestrator [D06/D07/D10]** — account-level claim/lock/idempotency, auto-select a single reachable permitted channel and a single eligible device using real per-platform study activity + delivery reliability; user-pinned channel wins if currently permitted and reachable. No parallel Telegram+Android+PWA+Desktop fanout. **D07:** alternate permitted channel only after verifiable first-channel non-display/failure and fresh eligibility check; ambiguous/missing acknowledgement means no cross-channel resend. **D10:** universal channel-neutral core and provider adapters from start; ship Telegram bot/Mini App + Android first, defer iPhone learner PWA and Desktop transports to V2 without rewriting core. Never select not-yet-supported adapters as deliverable endpoints.
6. **NotificationRenderer** — versioned notification template, canonical i18n, safe parameters, CTA target; no live LLM requirement.
7. **OutcomeAttribution** — planned/attempted/accepted/displayed/opened/resumed/completed/optout counters.
8. **Hybrid Optimizer [D09 OWNER APPROVED 2026-10-25]** — newly registered/low-data user: real functioning personalized rule-based policy, not a nonfunctional waiting period. Gather reliable learning/outcome signals. When a globally validated ML model exists and this user's evidence crosses a **quality/confidence eligibility threshold**, **automatically** switch this user to ML-guided time/content/channel/cadence optimization, with no feature-prompt or extra user consent beyond existing valid notification permissions (D01). Transition is gradual and versioned; insufficient/conflicting/stale data, degradation, unsupported platform, model failure or guardrail breach immediately uses safe rules again. Account/user override and D01–D08 constraints always override ML. Exact eligibility threshold/ML design/experiment gates are technical [OPEN] until audit/test, not invented as a fixed count.
9. **Admin Control & Analytics [D11 OWNER APPROVED 2026-10-25]** — existing Admin PWA'да жуда содда ягона Smart Reminder бошқарув/статистика юзаси: global kill switch (ва permissioned pause), current UZ/RU/TJ notification templates/edit/preview, ҳамда **фақат реал ҳисобланган** sent, suppressed, delivery status, opt-out, actual learning reactivation / completed study outcomes ва эксперимент натижаларининг қисқа кўриниши. Real attribution маъноси аниқ кўрсатилсин; 'sent'ни 'shown' ёки 'opened' деб аталмасин. Кераксиз filter/options ва фейк demo рақамлар йўқ. Admin PWA’нинг ўз администратор push'и learner notification орқали юборилмасин; auth/roles, audit trail, current template infrastructure ҳурмат қилинсин. Бу feature **тасдиқланган scope**, V1/V2 admin UI релиз санаси алоҳида техник режада аниқланади.

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
4. **reactivation [D08 APPROVED]:** шахсий ўқиш одатига нисбатан ғайриоддий узилиш; барчага бир хил 3/7/14 кун trigger эмас. Қайтиш учун ҳақиқатан мавжуд енгил вазифани таклиф қил; самара бермаса хабар оралиқлари узаяди, охирида reactivation серияси тўхтайди.
5. **due_review:** ишончли mastery/spaced repetition сигнали, реал ишлайдиган route.
6. **generic_habit:** фақат бошқа муҳим, ҳақиқий фойдали intent йўқ бўлса.

**[DECISION D05, 2026-10-25]:** рейтингда орқага тушиш ва ҳафталик натижа каби хабарлар study reminder'нинг D03 **1/day** лимитига автоматик киритилмайди — алоҳида мақсадда сақланади. Лекин **барча шу турдаги ўқиш/мотивация хабарлари users.id бўйича ягона cross-channel coordination/anti-spam policy'дан ўтади**: устма-уст вақтда юбориш, такрорланиш ва фойдасиз ranking хабарлари камайтирилади; фойдали weekly summary эса ўринсиз ташлаб юборилмайди, зарур бўлса кейинги маъқул вақтга сурилади. Бу бир кунда study + рейтинг + ҳисобот учун чекланмаган хабар юбориш дегани эмас. Аниқ cross-category cooldown ва priority чегаралари [OPEN], реал audit/owner қарордан кейин. Payment/receipt/account-decision transactional notices ҳозирги ўз жойида ва study cap'га аралашмайди. Onboarding, trial/churn ва marketing campaign budget қоидаларини кейин алоҳида audit/қарор билан белгилаш.

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
- **[DECISION D08, 2026-10-25]:** 3/7/14 кун бўйича барчага бир хил мажбурий reactivation режа йўқ. Фойдаланувчининг ҳақиқий ўқиш ритми, одатий танаффус давомийлиги ва охирги lesson/practice activity асосида ноодатий узилишни баҳола. Реал очиладиган қисқа ва енгил дарсни таклиф қил; бўлмаган 3–5 дақиқалик дарсга ваъда берма. Қайтиш бўлмаса хабарлар ораси узаяди ва охирида reactivation тўхтайди. Аниқ босқичлар, кун/сон thresholds ва қайта фаоллашув trigger'и [OPEN], ҳали owner қарори эмас.
- **[DECISION D03]** repeated ignore ёки хабардан кейин реал ўқиш бўлмаса кейинги reminder интервали автоматик узайсин. Реал ўқиш қайтиши кўп бўлса хавфсиз чегарада frequency ошиши мумкин; ҳар маҳаллий кунда 1 дан ошмайди. Аниқ observation window / weekly cap / thresholds [OPEN].
- **D08:** қайта-қайта натижа бермаган reactivation эслатмалар орасини узайтир ва охирида тўхтат. 'Push opened' ёки 'no read receipt'нинг ўзи фойдаланувчи ўқиди ёки эътиборсиз қолдирди дегани эмас; canonical learning progress'га қара. Кечиктириш/stop threshold ва қайта ўқиш бошланса restart қоидаси [OPEN].
- 2 Android phones + Telegram linked → single preferred endpoint / claimed device, no broadcast.

## 5. [PROPOSAL] Database design — migration олдидан код билан келишилади

Мавжуд User, CourseMiniAppProfile, CourseProgress, CourseUserNotification, AndroidPushToken, DesktopDevice, CourseMiniAppEvent, CourseXpEvent schema'ларини қайта ишлатиш; маълумотни икки марта store қилмаслик.

### 5.1 reminder_preferences (new; exact fields review)
- user_id PRIMARY KEY → users.id, ON DELETE CASCADE.
- study_enabled (explicit/effective consent semantics), user_selected_time_local nullable, time_mode: manual_locked|smart_auto (D02: smart automatically learns once sufficient real study history exists; old selected time is preserved during cold start; user may lock manual time). Persist mode and timestamp/source; do not infer explicit manual lock from mere presence of legacy reminder_time.
- timezone_name (IANA); user_quiet_start_local/user_quiet_end_local **nullable explicit override only**. Default = no predefined quiet-hours exclusion (D04). Auto schedule depends on individual reliable learning habit, not a global allowed-hours range.
- channel_policy: **auto|manual_locked** (D06 approved: auto selects one channel/device based on actual account learning activity and observed delivery reliability; user may lock a preferred channel); preferred_channel nullable, optional preferred_device_id subject to ownership verification, last_channel_selection_reason / capability snapshot (proposed). Existing disabled/blocked/OS-denied channels never silently enabled.
- daily_max (hard server maximum = **1 study reminder per local day**, D03 approved), weekly_max [exact upper bound OPEN; proposal default 3/week], adaptive_cadence_state/cooldown_until (proposed), snooze_until UTC, paused_until UTC. Across Telegram/Android/PWA/Desktop shared canonical account budget; never multiply caps by channel.
- settings_version, updated_at, consent_source, consent_at; **D01:** олдиндан ёқилган, мувофиқ legacy study reminder channel'ларида автоматик Smart upgrade (алоҳида қайта сўраш йўқ); ҳеч қандай old opt-out override эмас; бошқа/янги channel'га permission auto-grant қилиш йўқ. Янги аккаунт default'ини кўчиришдан олдин legacy semantics ва OS талабларига мувофиқ текшир.

### 5.2 reminder_jobs (new immutable logical-intent ledger)
- id UUID; user_id FK; local_day; intent; target_ref with validated type; timezone snapshot, scheduled_at_utc, expire_at_utc.
- policy_version, variant_id, experiment_id/arm, chosen_channel / chosen_device_id nullable, channel_selection_reason (D06), manual_override_applied bool, selection evidence timestamp; only ONE account-level job per logical study reminder.
- status: scheduled|claimed|suppressed|sent_unconfirmed|shown|failed|cancelled|expired.
- Unique constraint (user_id, local_day, category="study") ёки equivalent partial unique index; “битта study message/day” policy'си ўзгарса schema strategy version'ланган бўлсин.
- decision_reason, suppression_reason, attempt counter, last_attempt_at, claim lease/claimed_until.
- Atomic compare-and-set / SELECT FOR UPDATE SKIP LOCKED, multi worker safety; stale claim reclaim.

### 5.3 reminder_attempts (new append-only transport attempts)
- id, reminder_job_id, provider, device_id (nullable), attempted_at, provider_receipt_id (hash/opaque), status, retry_class, ack_at.
- FCM accepted != device shown; Telegram API success != human read; platform constraints bilan displayed unknown бўлиши мумкин.
- Unique attempt-id and idempotency keys; **D07:** fallback only within the same logical reminder job, never separate user/day job; if first channel conclusively could not display, allow *one controlled alternate attempt* only after atomic claim and D03 consent/progress/cap recheck; unknown first-channel display status → suppress alternate, record ambiguity. Actual retry counts/backoff/TTL are technical proposals until tests verify safety.

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

## 6. Delivery state machine [D07 OWNER DECISION + IMPLEMENTATION PROPOSALS]

CANDIDATE → ELIGIBLE / SUPPRESSED → SCHEDULED → CLAIMED → PROVIDER_ATTEMPTED → ACCEPTED_UNCONFIRMED → DISPLAYED_ACK / FAILED / EXPIRED.

- BEFORE_DISPATCH: re-read consent, goal progress, selected course, account status, user timezone, frequency total.
- Unique reservation occurs BEFORE external send, not after it; retry cannot create second logical job.
- Retry transient network errors with bounded backoff, TTL, no stale-day sends.
- FCM provider accepted does not guarantee actual delivery or display. Shown ack from verified device where technically feasible.
- Telegram бот блокланган бўлса token/reachability update; native-only ҳисобга Telegram fallback ясама.
- **[DECISION D07, 2026-10-25]: 2-вариант — хавфсиз қайта юбориш.** Study reminder биринчи танланган канал/қурилмада **кўрсатилмагани ишончли исботланса** (масалан, provider send'ни аниқ рад этган ёки authenticated client no-display деб тасдиқлаган), бошқа мавжуд рухсатли каналга фақат шу logical job бўйича назоратли fallback мумкин. **FCM қабул қилди, аммо client ack йўқ / таймаут / интернет йўқ / delivery unknown** ҳолатларида биринчи қурилмада кўринмагани исботланмайди; шунинг учун автоматик иккинчи каналга хабар юборилмайди. Эски биринчи push кечикиб пайдо бўлиш эҳтимоли ҳам guard'da ҳисобга олинсин; claim/expiry/ack races regression тестда текширилсин. Ҳар бир fallback олдидан D01 opt-out, D03 daily study cap, actual goal done, D04 explicit quiet/pause ва D06 permitted channel текширилсин. Баъзи хабарлар етмай қолиши мумкин — duplicate'дан қочиш устувор. **Scope:** фақат study reminder; Subscription/limit/payment/account notice'нинг мавжуд Android→Telegram махсус эскалацияси бу қарор билан ўзгармайди.
- On resume/offline app starts: perform reconciliation and suppress stale intents. Local notification fallback must consult server-issued logical job/lease or be explicitly disabled once migrated; purely local offline notification cannot guarantee cross-device exactly-once.
- Универсал background scheduler яхшиланса: independent worker failure isolation + process/replica lease, observability, cancellation and graceful shutdown.

## 7. Notification UX / localization / deep-link [PROPOSAL]

- **Settings [D02/D04/D06]:** фойдаланувчи хоҳласа эслатма вақтини қўлда қотиради; акс ҳолда Smart вақт одатга қараб автоматик ўзгаради. Default 22:00–08:00 ёки бошқа тақиқланган соатлар йўқ. **D06:** эслатма канали ҳам фойдаланувчи қайси платформада ҳақиқий ўқиётганига ва етказиш ишончлилигига қараб автоматик танланади; хоҳласа фойдаланувчи битта канални қўлда белгилай олади. Хоҳласа quiet hours, pause ва opt-out амал қилади; OS Focus/DND'ни четлаб ўтмаймиз. Етарли ўқиш маълумоти йўқ пайтда эски белгиланган вақт сақланади (D02); мажбурий feature promo ёки қайта permission prompt йўқ (D01).
- **Permission flow [D01]:** мавжуд study notification рухсатини Smart upgrade учун такроран сўрама, функционал ҳақида мажбурий onboarding/marketing ойна очма. Янги platform/OS push permission ҳали йўқ бўлса, фақат OS талаб қиладиган рухсат user interaction орқали одатдаги бир марталик оқимда сўралиши мумкин; рад этишни ҳурмат қил. Existing OFF'ни ON қилма, app-level opt-out ва OS-level off'ни ажрат.
- **Content:** UZ/RU/TJ canonical catalog; polite, short, contextual; no invented lesson numbers/XP/minutes. Render placeholders validated and escaped.
- **CTA:** resume lesson vs daily goal vs review; deep-link internal validated target, track/level/access check. Telegram Mini App, Android native, later iPhone PWA and Desktop adaptors, all canonical data.
- **Feed:** existing CourseUserNotification reused where appropriate, inbox item ≠ delivery ledger; re-render after language change and template version handling.
- **Admin [D11]:** existing admin motivation template editor сақланади; new study message kinds mapping. Admin PWA'да фақат бир содда Smart Reminder control+analytics section: ON/OFF emergency kill switch, хабар шаблонлари, real sent/suppressed/opt-out ва real study return attribution statistics, experiment summary if evidence sufficient. Натижа йўқ бўлса 'маълумот етарли эмас' кўрсат, fake metrics/тасдиқланмаган % йўқ. Admin PWA technical push ва receipts билан аралаштирма.
- **Play/Direct:** learner notification may navigate to existing content but cannot introduce forbidden external checkout/self-updater in Play flavour.
- **Privacy:** quiet lockscreen text defaults, user-level sensitive context in notification text must be restrained.

## 8. Channel strategy — D06/D10 owner approved, channel adapters/ACK mechanics proposed

**[DECISION D10, 2026-10-25 — 1-вариант]:** Биринчи релизда Smart Reminder Telegram (бот орқали Mini App user) ва Android'да ишлайди. Learner iPhone PWA Web Push ва Desktop OS push кейинги V2 босқичда. Лекин **универсал сервер architecture V1 билан бирга тайёр бўлиши шарт**: user-level single-source policy, adapter interface, shared identity/preferences/events/jobs, platform capability inventory, extendable target routing, consent and cross-device dedup. Кейинги платформани улашда core reminder engine, tables'нинг асосий семантикаси ёки фойдаланувчининг аккаунт сиёсати қайта қурилмасин. Ҳозирги Admin PWA пушларини learner iPhone PWA билан адаштирма; номаълум PWA/Desktop capability'ни 'implemented' деб белгилама.

**[DECISION D06, 2026-10-25]:** 2-вариант тасдиқланди. Агар бир аккаунтда Telegram/Android/iPhone PWA/Desktop бир нечтаси бўлса, система мавжуд рухсатли каналлардан фойдаланувчи амалда кўпроқ ўқийдиган ва эслатма ишончлироқ етказиладиган **биттасини** автоматик танлайди. Битта study reminder'ни ҳамма платформага бирдан тарқатмайди. Фойдаланувчи хоҳласа канални қўлда танлаб қотиради; ўчирилган канал, OS permission йўқ канал, blocked Telegram ёки аккаунтга тегишли бўлмаган қурилма танланмайди. Бу танлов ҳозирча ишловчи код эмас. Қайси сигналларга неча балл ва no-ack/fallback handling D07/P0–P4 дизайнида аниқланади; фақат 'app open' ҳақиқий study engagement дегани эмас.

**[PROPOSAL] Selection order:** (1) explicit user locked channel if permitted and reachable; (2) verified platform-level recent actual learning + reliable displayed ack when supported; (3) permitted/reachable channel with sufficient confidence; (4) none → no send. Do not mistake FCM accepted for shown. A manually locked but unavailable channel should not silently trigger a second channel without D07 approved fallback semantics. D03 global daily cap ва D05 cross-category coordination сақланади.

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
- **[DECISION D08]:** Inactive learner'ни қайтариш индивидуал: шахсий ўқиш ритми бузилганда содда вазифа билан таклиф қилиш; ҳеч қандай натижа бўлмаса таклифлар сони камайиб боради ва охирида тўхтайди. **14+ кун умумий автоматик stop қоидаси тасдиқланмаган.** Аниқ stop ва cooldown рақамлари [OPEN].
- Cooldown after voluntary lesson session so it never nags somebody already learning.
- **[DECISION D05, 2026-10-25]:** study reminder, рейтинг ва ҳафталик натижа алоҳида мақсадли категориялар; D03 daily max=1 фақат study reminder'га тааллуқли. Лекин ягона per-account notification coordinator ҳаммасининг юборилиш вақти, duplicate key, category priority ва global nuisance/anti-spam ҳолатини ҳисоблайди. Категориялар яқин келса кўпинча рейтинг каби кам аҳамиятли хабарни suppression/defer қилиш, фойдали weekly report'ни эса алоҳида навбатда сақлаш. Нормал хабарлар consent/blocked ва per-channel permission'га бўйсунади. Аниқ global cap/cooldown [OPEN], олдиндан рақам тўқилмайди. Receipt/payment/security/account notices study cap'га киритилмайди, мавжуд алоҳида доставка ва эскалация қоидалари ўзгармайди.
- Consent “off” must trump AI recommendation. Snooze/disable easy from settings and where platform supports direct notification actions.
- No fear/pressure manipulative streak text. No false prediction that user “will lose all progress”.
- All numbers above are proposals, NOT final business decisions.

## 10. Analytics, causal evaluation, optimization

### 10.1 Events (server names proposals)
reminder_candidate_evaluated, reminder_suppressed, reminder_job_reserved, reminder_dispatch_attempted, reminder_provider_accepted, reminder_device_displayed, reminder_opened, reminder_lesson_resumed, reminder_learning_completed, reminder_user_opted_out.

Every event captures: canonical user_id or aggregate-safe key; reminder_id, experiment arm, policy_version, rendered template key/variant, platform, local_day, decision timestamp, reason, source; client facts cannot forge server-owned lesson completions.

### 10.2 Primary KPIs [D12 owner decision: target/duration based on real baseline]
1. **D7 learning retention:** eligible signup/exposure cohort users with server-confirmed learning activity on day 7 / all eligible cohort users. Cohort origin and exact day window versioned.
2. **Weekly active learning days:** per-user distinct local dates with server-confirmed lesson/practice activity, averaged over enrolled experiment participants.
3. **Completed learning units / learner-week:** unique server-confirmed completed lessons/eligible study tasks; protect against inflated repeats.

Supporting: resumed lessons per eligible user, percentage scheduled→shown→opened→learned; time/channel distribution. Guardrail: unsubscribe, bot blocks, OS denied, complaint, duplicate displayed, late arrival, crash/scheduler latency, notification cost.

**Crucial:** opened/delivered rates alone are not retention; outcome measured at user/account level, not notification level only.

**[DECISION D12 — 2026-10-25]:** 2-вариант — натижани баҳолаш учун ҳозирдан сунъий **10% ўсиш / 14 кун синов** ёки бошқа қотирилган KPI threshold/давомийлик белгиланмайди. Аввал амалдаги Telegram/Android'даги **baseline** (сегмент/платформа, ўқишга қайтиш, D7 retention, active learning days, lesson completion, opt-out/complaint) ва eligible traffic аниқ ўлчанади. Сўнг meaningful minimum detectable effect (MDE), sample size, statistical power, cohorts, user-level randomized control/treatment allocation, expected observation period ва guardrail stop criteria ҳисобланади ва experiment олдидан versioned protocol сифатида ёзилади. Мақсад ҳам, синов муддати ҳам **реал маълумотга асосланган**, owner рақамларни keyingi tasdiqlashda қабул қилади; baseline йўқда тахминий ROI/impact фоизлари ишлатилмайди. D09 model migration ҳам шу ўлчовли uplift/guardrails'га қараб баҳоланади.

### 10.3 Experiments [PROPOSAL]
- First rollout: deterministic rule policy shadow mode → small canary → treatment/control split; unit of randomization users.id, not device nor Telegram ID.
- Stable assignment persisted, migration old D1 experiment mapping protected. No overlap/multiple simultaneous experiments without mutual exclusion.
- Measure intent-to-treat (all assigned eligible users), also delivered-user diagnostics separately; never compare responders-only to all nonresponders.
- 1st experiments: (a) reminder vs holdout, (b) manual/default vs habit-based time after verified value, (c) short lesson-oriented vs generic content, (d) channel preference after real consent.
- **[D12 APPROVED]:** safety guardrail thresholds + stop rule, MDE, sample size/power, exposure/cohort window and duration real baseline+eligible traffic'дан ҳисобланади; arbitrary 7/14-day cutoff ва олдиндан 10% uplift тахмини тасдиқланмаган. Experiment registration/decision written before exposing users; report effect with uncertainty and actual eligible denominators.
- **[DECISION D09 2026-10-25 — HYBRID]:** two stages are **one continuous product**, not two products and not a manual user toggle: stage 1 immediately runs adaptive deterministic rules for new and sparse-history users and captures verified learning signals; stage 2 turns on an already-trained and experimentally validated ML optimizer **automatically per eligible user** when their usable history meets an approved reliability/confidence gate. ML may personalize best time, content, channel, and reminder cadence but must honor fixed rule guardrails. If model unavailable/uncertain/regresses, auto fallback to stage 1 with no missing opt-out or extra push. A shared model with per-user features is preferred over training a separate model per person; architecture choice to verify during P7.
- [OPEN technical thresholds]: define minimum distinct study days, quality/coverage of signal, warm/cold start, sample-size/causal lift, model confidence, max age of data, model version, staged cohort release, shadow test and rollback before ML dispatch goes live. No arbitrary numeric threshold approved; no claim model implemented. LLM-generated marketing copy not core.

## 11. Иш босқичлари, рақамланган чеклист ва acceptance

### P0 — Full integration audit / policy lock
**Ҳолат:** [NOT STARTED]
- [ ] Main/current feature target ref SHA, runtime environment, production flags, active scheduler/replicas and schema head аниқлансин.
- [ ] Барча reminder senders, push/OS permissions, consent toggle, notification preferences ва policy matrix инвентаризация қилинсин; **D01 mandatory:** legacy enabled → silent Smart migration, disabled → remains off, denied channel → no push, no duplicate system permission prompt. **D05:** study/rating/weekly reports and transactional/marketing notices category ownership, eligibility, urgency and cross-category overlap matrix.
- [ ] Canonical study event granularity, day/timezone semantics, idempotency, deep-link ва lessons guards аниқлансин.
- [ ] P0 risks reported, owner-selected defaults and scope ledger DECISION деб қайд этилсин.
**Acceptance:** repo code references + event flow diagram + old/new coexistence switch table + no unverified architecture claims.
**QA:** static audit, affected existing unit tests baseline ва version/branch check; production metrics only if legitimately accessible.

### P1 — Instrumentation + schema foundation
**Ҳолат:** [NOT STARTED]
- [ ] Minimum additive models/migrations; unique keys, indexes, FK cleanup, dry-run explain reasons; D07 distinguish confirmed_not_displayed vs unconfirmed/unknown, provider accepted vs shown ACK, fallback attempt on SAME job, authenticated device and monotonic state transition. Exact enum/database schema to be selected after source audit.
- [ ] Preference mapping/API endpoints: auth, validation, optimistic revision, old client compatibility; D01 seamless migration only for pre-enabled same channel, explicit opt-out preserved, no extra Smart opt-in dialog. D06 channel_policy auto/manual_locked, manual priority, account/device ownership validation and conservative unavailable-channel behavior.
- [ ] Canonical event collector and daily-learning aggregation; no duplicate score/event counts.
- [ ] Privacy and deletion/retention hooks, diagnostics.
**Acceptance:** migration up/down where safe, invalid account/token rejected, dual-read settings coherent, no reminders newly sent.
**QA:** SQLite/Postgres migration, concurrent preference writes, NULL Telegram identity, legacy backfill, delete/logout/token revoke.

### P2 — Deterministic decision engine (DRY RUN)
**Ҳолат:** [NOT STARTED]
- [ ] Policy pure function: reasons, priorities, frequency budget, only user-selected quiet hours/pause (D04: no global preset), current-day done, snooze; D03 personalized cadence by verified learning reaction, one study reminder/user/local day absolute cap, ignored→decelerate, safe learning return→increase only under cap; weekly hard cap still OPEN. **D05:** eligible study/rating/weekly category coordination: collisions suppressed or deferred (ranking low priority, weekly summary retained where possible), all platforms counted by users.id; account/payment transactional notices excluded. **D07:** fail-closed alternate-channel routing on ambiguous delivery; confirmed failure only, no timeout-based blind resend.
- [ ] **D02:** Smart habit estimator with reliability; enough observed study days бўлмагунча existing reminder time сақлаш; user қўлда вақтни қотирган бўлса optimizer override қилмасин; changed habit adaptation and zone/DST tests. **D08:** user-specific typical inter-study gap vs abnormal inactivity, gradual reactivation cooldown and final stop; cold-start sparse histories and real study resumption QA. **D09 stage 1:** already-functioning personalized rule-based reminders from first eligible account use; persist model eligibility evidence without blocking core reminders.
- [ ] Job reservation/cancel/recompute and policy versioning; no network delivery.
- [ ] Shadow logs compared against old reminders without user notification.
**Acceptance:** identical inputs → identical decisions, safe suppress when data unknown, one study job/account/day, dry-run has no side effects.
**QA:** midnight/DST/travel, 0 offset, incomplete→done race, 2 schedulers, duplicate events, stale activity, account-switch.

### P3 — Telegram delivery integration [D10 V1]
**Ҳолат:** [NOT STARTED]
- [ ] Telegram notifier adapter, templates UZ/RU/TJ, validated lesson deep-link; existing admin template edit. D06 only one chosen allowed channel can claim a study job; Telegram study sender cannot independently fire after Android was selected.
- [ ] Feature flag selectively routes Telegram study reminders new engine. Old CourseReminder/Motivation senders skip users controlled by new engine. D01: eligible existing ON learners migrate without re-consent; OFF users are suppressed. D03: account daily study cap enforced also when course reminder and motivation intent compete.
- [ ] D1 holdout protected; opt-out/blocked, rate limiting, retry ledger and logging. D07: provider definite failure can release controlled same-job fallback, ambiguous result cannot trigger another channel; mark reason and verify transaction/ack race.
- [ ] Pilot cohort + rollback to old behavior without double-send. D05: existing Telegram ranking/weekly sender must consult global category anti-spam policy without dropping useful weekly summary or violating D03 study cap; no double dispatch during migration.
**Acceptance:** canonical account receives no duplicate; all linked/unlinked/blocked cases correct; genuine reminder opens valid lesson.
**QA:** unit+integration with fake bot, multi-instance, callback/deeplink, rendered locale, 3-day cooldown, failure/retry.

### P4 — Android unified reminder [D10 V1]
**Ҳолат:** [NOT STARTED]
- [ ] Android FCM data contract includes job ID, TTL, policy version, no sensitive payload.
- [ ] Client verifies account/device, current goal/consent, notified job state; post ack with safe auth. D06: chosen device only; app activity and delivery reliability derive from verified cross-platform signals rather than mere device installation.
- [ ] WorkManager local fallback consults shared job semantics or is suppressed when server-owned; no dual display. D07: securely signed-in and device-owned shown/no-display ack distinction; lack of ack is NOT no-display; stale original FCM cannot produce an extra post after confirmed alternate routing.
- [ ] Direct+Play parity; OS notification channel user preference respected.
**Acceptance:** one account Telegram+2 Android devices ≤1 visible study reminder within policy, as far as ack/capability allows. No false done/failure statuses.
**QA:** Android 13 permission denied, offline FCM, revoked token, delayed hint, sign-out, two devices, old-client rollout, Play vs direct.

### P5 — Learner PWA + Desktop transport [D10 V2; NOT a blocker for V1]
**Ҳолат:** [NOT STARTED]
- [ ] **D10 phase boundary:** V1 must expose stable provider-neutral contracts and safe unknown/unsupported-channel suppression; do not make iPhone learner PWA or Desktop OS push a launch blocker. V2 adds channel-specific adapters without changing core engine, existing user preferences or global dedup. Verify backwards-compatible API/schema evolution.
- [ ] Confirm learner PWA installability, HTTPS, manifest, service worker scope, consent, push subscription cleanup.
- [ ] Build learner push subscription endpoints; do not reuse Admin PWA auth/push as learner API.
- [ ] macOS/Windows OS notification parity, foreground/background support boundaries, deep-link and logged-out behavior.
- [ ] Cross-platform opt-out, channel preference, fallback and suppression tests; D03 adaptive cadence and at most one study reminder/account/local day even when Telegram+Android+PWA+Desktop are concurrently available. D06: auto choose one channel/device using real study activity+reliability, manual channel lock. **D07:** only verified non-display triggers controlled alternate; unknown/timeout/no-ACK doesn't trigger resend; transactional separate.
**Acceptance:** supported conditions send, unsupported/denied conditions clearly no-send; shared ledger with Telegram/Android.
**QA:** real supported iPhone Home Screen PWA, Safari/macOS, Windows, multi-account, device removal, blocked OS notifications.

### P6 — Analytics + controlled experiments + admin observability
**Ҳолат:** [NOT STARTED]
- [ ] Server events, attribution IDs, cohorts, dashboards with real denominators; D05 category-level suppression/defer/dispatch counts and per-account all-category frequency, duplicate and nuisance metrics. **D11:** structured read-only admin metrics endpoint with distinct dispatch accepted/shown/opened/returned-to-study definitions; empty/insufficient data rendered honestly; no fabricated recovery count.
- [ ] Stable user-level randomized control, D1 experiment interference audit, metrics baselines; D09 verify ML uplift and safety against the actual working rule baseline rather than against no reminders, and model readiness based on meaningful learning outcomes. **D12:** measure baseline cohorts/traffic FIRST; calculate justified KPI target, MDE, sample size/power and duration/stop criteria, document owner-approved experiment before launch; zero/few users → report insufficient evidence, don't invent a positive uplift.
- [ ] **D11 approved:** Admin PWA'да минималистик битта Smart Reminder section: master kill switch and authorized template edit/preview, succinct *real* sent/suppressed/opt-out and genuine resumed learning, plus A/B effect only if validated; avoid filters clutter, duplicate headers, marketing-style explanatory UI and extra decorative controls. Use existing HSK AI admin template system rather than second editor; role checks + audit logs + safe fail-closed off handling.
- [ ] Notification annoyance guardrails and alerting.
**Acceptance:** replay sample data deterministic, cohort reports consistent, control never dispatched, production users not exposed without policy gate; **D11** Admin PWA view has real backed metrics with denominator/time window and safe on/off/template controls, empty data stays empty, no false 'sent=shown' attribution and no unauthorized edit. **D12:** metric definitions, measured baseline, eligible cohort estimate, sample size and justified experiment duration recorded before experiment; no hard-coded success percentage or calendar-day expiry unsupported by data.
**QA:** attribution late/duplicate event, logging failure isolation, control/treatment equality check, privacy; D11 role authorization, missing/stale aggregate, zero traffic, kill switch concurrency and opt-out precedence, template localization and no duplicate admin UI blocks. **D12:** baseline sampling, low-traffic and uneven cohorts, underpowered experiment correctly flagged, no early winner claims from repeated looks, denominator and local-day consistency.

### P7 — Optimization: automatic rule-to-ML upgrade [D09 OWNER APPROVED; implementation not started]
**Ҳолат:** [NOT STARTED]
- [ ] First production stage already uses useful rule-based personalized reminder decisioning (P2–P6); there is **no waiting for an ML model before users receive eligible reminders**.
- [ ] Collect quality-checked canonical learning events/outcomes, compare verified time/content/channel/cadence performance and data sufficiency with a rule-policy baseline.
- [ ] Train/validate shared user-personalizing model offline; assess leakage, consent/privacy, fairness for sparse-history users, silent users, and underrepresented languages/platforms. ML implementation and production support remain conditional on evidence.
- [ ] Define and version `optimizer_mode=rules|ml`, `model_version`, user eligibility/confidence gate, feature freshness, evaluation and automatic transition reasons; **automatically enter ML mode once both the model is safely deployed and user eligibility is satisfied**, without manual opt-in. Use reversible gate: automatically fall back to rule mode when signals/model fail.
- [ ] Shadow ML predictions against existing rule policy, controlled randomized A/B, explicit metric lift and safety thresholds, staged release/kill switch; preserve experimental holdout and all D01–D08 guards.
- [ ] Exploration frequency caps + model rollback, no more than one study reminder/user/local day and no cross-channel duplicate.
**Acceptance:** new users get rule-based reminders immediately; eligible users automatically adopt demonstrably better ML decisions when criteria are met, while ineligible ones stay on functioning rules; model failure or degraded evidence falls back automatically, respecting user preferences/permissions, channel and cadence limits. If ML uplift is unproven, rules remain the deployed policy; never claim model is production-ready merely because personal data count reached a threshold.
**QA:** cold vs warm cohort, threshold-cross event, automatic transition, threshold lost/stale feature, model down or unreliable, model-rules conflict, duplicate/opt-out, experimental holdout and rollback.

### P8 — Release / documentation closeout
**Ҳолат:** [NOT STARTED]
- [ ] Versioned staged rollout, release flags/rollback, incident procedures and migration safety.
- [ ] Full regression in affected learning, auth, subscription, localization and device flows.
- [ ] Exact commit/PR/test evidence and production monitoring results archived in THIS file; update permanent PROJECT_MEMORY per AGENTS.md when justified.
- [ ] No leftover legacy double-senders / migration TODOs; clean owner handoff.
**Acceptance:** owner explicitly accepts real test outcomes and monitored rollout; mark COMPLETE only then.

## 12. Regression matrix (қатъий текширилади)

- [ ] Telegram-linked + Android same user, Telegram-only, native Google/Apple-only (Telegram ID NULL), unlinked, re-linked valid Telegram, blocked Telegram.
- [ ] Same user multiple Android devices, Android+PWA+Desktop, stale/revoked token, old APK clients; D06 test auto selection using verified recent study activity and channel availability, same-account multi-device singular target, manual override and unavailable user-locked channel.
- [ ] Global off / Android OS off / Telegram opt-out / wrong channel / double permission toggle / paused/snoozed.
- [ ] Daily goal complete just before send; unfinished lesson completed on another platform; course switched HSK2→HSK3; restricted course CTA.
- [ ] 2 workers concurrently tick; queue restart; DB timeout; send succeeds then commit fails; provider accepted but unshown; retry after cancellation; **D07:** authenticated confirmed-no-display → one same-job alternate, no ACK after acceptance → no alternate, original late push vs claimed alternate race, account cap+optout preserved; transactional notices unaffected.
- [ ] Zero timezone, fractional UTC offset, summer time DST, timezone edited, clock skew, midnight, long offline period, late push after local day; D04: observed late-night study may lead to a late-night reminder, but no invented global night blackout; respect user quiet override and OS Focus.
- [ ] UZ/RU/TJ template, HTML escaping, long text, after language change and admin template changes.
- [ ] Event duplicate/replay, experimental holdout, analytics attribution, client forgery safety.
- [ ] Free/trial/Pro/expired account; Android Play notification action never links prohibited direct payment.
- [ ] Notification enable/disable legacy migration, data export/purge and user deletion.
- [ ] Cost/frequency cap guardrail, study message vs subscription/receipt separate routing; D05: same-day study + rating + weekly collision, rating suppressed/deferrable, weekly report not silently lost, transactional delivery unaffected.

## 13. [OPEN] Owner product decisions — confirm BEFORE relevant code

| ID | Савол | Тавсия / олдинги маълумот | Status |
|---|---|---|---|
| D01 | Smart Reminder'ни фойдаланувчи қандай қабул қилади? | **1-вариант танланди:** аллақачон рухсат берилган/ёқилган ўқиш эслатмаларини Smart Reminder'га автоматик seamless upgrade; қайта-қайта рухсат сўралмайди; фойдаланувчига функция номи эмас, қулайлик муҳим. Илгари OFF қилган ва OS denied каналлар ўзгармайди, янги OS каналига қўшимча permission талабини четлаб ўтмаймиз; exact legacy mapping D14 да. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D02 | Эслатма вақти автоматик ўрганиладими? | **2-вариант тасдиқланди:** вақт фойдаланувчи одатига автоматик мослашади; ишончли маълумот йиғилмагунча мавжуд вақт сақланади; user истаса аниқ вақтни ўзи белгилаб автоматик ўзгаришни тўхтатади. D01'га мувофиқ янги activation prompt талаб қилинмайди. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D03 | Study reminder'лар қанчалик тез-тез юборилади? | **2-вариант тасдиқланди:** фойдаланувчининг ҳақиқий ўқиш реакциясига мосланувчи индивидуал frequency; эътиборсиз қолса камаяди, фойда берса хавфсиз доирада ошиши мумкин. **Қатъий чегара: 1 study reminder / account / local day, барча каналлар бирга.** Ҳафталик max ва аниқ adaptive thresholds OPEN, 3/week фақат таклиф. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D04 | Эслатманинг тақиқланган умумий соати борми? | **OWNER CUSTOM DECISION:** умумий белгиланган вақт лимити ЙЎҚ; вақт фойдаланувчининг ўқиш одатига максимал мослашади, ҳатто кечаси ҳам. User manual time / self-set quiet hours / pause / opt-out ва OS DND/permission устун; D03 кунлик 1 та лимит сақланади. Cold-start D02'га мувофиқ. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D05 | Рейтинг ва ҳафталик натижалар дарс лимитига кирадими? | **2-вариант тасдиқланди:** дарс, рейтинг ва ҳафталик натижа алоҳида category сифатида қолади, лекин битта account-level anti-spam/coordinator ўзаро устма-уст тушишини назорат қилади. Рейтинг хабарлари камайтирилиши/кечиктирилиши мумкин; фойдали ҳафталик натижа сақланади. D03 кунига 1 та фақат study reminder учун; глобал category лимит рақами ҳали OPEN. Payment/receipt transactional хабарлари мавжуд йўлда қолади. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D06 | Қайси платформага эслатма келади? | **2-вариант тасдиқланди:** ҳар бир study reminder учун Telegram/Android/learner PWA/Desktop орасидан битта рухсатли, reachable канал ва битта eligible device автоматик танланади; меъёр — ҳақиқий platform learning activity ва delivery reliability. User битта канални қўлда қотириши мумкин; off/denied каналлар ёқилмайди, all-platform broadcast йўқ. Delivery uncertain fallback D07 ҳали OPEN. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D07 | Биринчи платформада хабар кўрсатилмагани/етказилгани номаълум бўлса fallback? | **2-вариант тасдиқланди:** бошқа каналга фақат биринчи канал хабарни **кўрсатмагани ишончли тасдиқланганда** шу logical job орқали назоратли қайта юбориш мумкин; provider accepted/no shown-ack, timeout, offline, unknown → **қайта юборилмайди**. D01/D03/D04/D06 қайта текширилади; study reminders scope, account/payment notices алоҳида. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D08 | Узоқ ўқимаган фойдаланувчини қандай қайтарамиз? | **2-вариант тасдиқланди:** умумий 3/7/14 кунлик схема эмас, ҳар бир одамнинг шахсий ўқиш одатига қараб ноодатий танаффус; реал мавжуд енгил дарс таклиф этилади. Реакция бўлмаса камроқ эслатилади ва охирида тўхтайди. Exact observation/cooldown/stop/restart thresholds [OPEN]. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D09 | Rules ва ML модели қандай бирлашади? | **OWNER HYBRID DECISION:** янги ва кам маълумотли user'га rule-based шахсий Smart Reminder **дарҳол ишлайди**; тизим ҳақиқий ўқиш маълумотларини йиғади. Етарли сифатли user signal/confidence threshold'и бажарилиб, умумий ML модели offline/A-B билан хавфсизлиги ва фойдаси тасдиқланиб production'da мавжуд бўлса, user **автоматик** ML оптимизацияга ўтади (time/content/channel/cadence). Фойдаланувчидан алоҳида AI activation сўралмайди. Model нотўғри/ишламаса auto rules fallback; D01–D08 override сақланади. Exact gate values/ML validation [OPEN technical]. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D10 | Биринчи Smart Reminder релиз қайси платформаларда? | **1-вариант тасдиқланди:** V1 — Telegram бот/Mini App + Android. iPhone learner PWA Web Push ва Desktop push — V2. **Universal provider-neutral сервер architecture V1'дан тайёр**, кейинги platform adapter'лар қўшилганда core policy, users.id, account-wide dedup, preferences ва events қайта ёзилмайди. Existing platform capability ва OS permission'лар ҳақиқий бўлиши шарт. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D11 | Admin PWA'да Smart Reminder қандай кўринади? | **2-вариант тасдиқланди:** битта минималистик бошқарув + ҳақиқий статистика юзаси: on/off kill switch, мавжуд notification template таҳрирлаш/preview, реал юборилган/бекор қилинган/opt-out ва ҳақиқий ўқишга қайтиш натижалари, ҳақиқий A/B натижа бўлса кўрсатилади. Ортиқча фильтрлар/матнлар, fake/demo саноқлар, дубликат блоклар қўшилмайди. Admin role/audit ва асосий Telegram/Android V1 rollout'га халал бермайди. Admin UI'ни V1 ёки кейин чиқариш бўйича аниқ milestone ҳали техник [OPEN]. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
| D12 | KPI target фоизи ва A/B синов муддати қандай белгиланади? | **2-вариант тасдиқланди:** аввал ҳозирги ҳақиқий ўқиш/retention baseline ва eligible traffic'ни ўлча; кейин MDE, sample size/power, cohort windows, guardrails ва experiment duration'ни асослаб ҳисобла. Ҳозирдан 10%/14 кун ёки бошқа рақам **тасдиқланмайди**. Ҳақиқий ҳисобдан сўнг аниқ мақсад/муддат owner'га тасдиқ учун тақдим этилади. | **DECISION 2026-10-25 — APPROVED / IMPLEMENTATION PENDING** |
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
| 2026-10-25 | D04 owner custom decision | No system-wide time-of-day limits: maximum personalization even at night; optional personal quiet/pause, OS Focus/DND preserved; 1/day from D03 unaffected. Docs only. | 78da152f698f1283acb309fa0b919c5bccc0fb95 | NO TESTS RUN; decision captured only | D05 rating and weekly progress notification budget |
| 2026-10-25 | D05 owner decision | Option 2 approved: separate study/rating/weekly purposes, shared account-level anti-spam coordination; low-value ranking de-prioritized; useful weekly summary retained; exact global threshold still OPEN. Docs only. | 430d81841698a5ec26e62e1d4847c15fbd5c1dc2 | NO TESTS RUN; decision captured only | D06 cross-platform preferred notification channel |
| 2026-10-25 | D06 owner decision | Option 2 approved: auto pick a single user-permitted study channel/device based on actual platform study behavior and delivery reliability, optional manual channel lock; D07 delivery-uncertain fallback OPEN. Docs only. | 1cec1d2a2c4745243249fbb6a5ec9c5a1f61c4ee | NO TESTS RUN; decision recorded, runtime unchanged | D07 fallback/ACK behavior |
| 2026-10-25 | D07 owner decision | Option 2: fallback only when original channel conclusively did NOT display (or send definitively failed); no resend on unknown/no ACK/timeout; same study job, verified consent/goal/cap; transactional notifications unaffected. Docs only. | 16ff220752a35731d6032f56c9c1d05c00c0d9a7 | NO TESTS RUN; requirement recorded, runtime unchanged | D08 inactivity/reactivation sequence |
| 2026-10-25 | D08 owner decision | Option 2: individual abnormal inactivity recognition, realistic easy learning task, increasing gaps after unhelpful reminders and eventual stop; 3/7/14 day fixed schedule rejected. Docs only. | a3d31cd369b078356cea263bd7f5dbe904fbd9ee | NO TESTS RUN; requirements only | D09 AI/ML timing and implementation |
| 2026-10-25 | D09 owner decision | HYBRID: personal adaptive rules operate immediately, collect high-quality user events, auto upgrade to safeguarded validated ML once model globally ready + user data sufficient; auto fallback to rules if quality/availability degrades. No extra UX permission and no hard threshold picked yet. Documentation only. | 2a28cc263579eb226289364863a38464b9461efa | NO TESTS RUN; requirement record only | D10 release platform scope |
| 2026-10-25 | D10 owner decision | 1-вариант: first release Telegram/Mini App + Android, iPhone learner PWA and Desktop V2; universal channel-neutral server core and per-account policy/identity/dedup provider contract delivered from V1. Docs only. | cecfa718f70e4b1b6142542b958976555e37f5a9 | NO TESTS RUN; requirement recorded, runtime unchanged | D11 admin controls and analytics exposure |
| 2026-10-25 | D11 owner decision | Option 2: simple one-section Admin PWA control (global switch and existing message template editor) plus source-backed sent/suppressed/opt-out/actual study return metrics, no fake data, low clutter; admin release sequencing separately planned. Docs only. | 2f7aa95ce44f8cff46984e63b2854474d01cd089 | NO TESTS RUN; requirement captured only | D12 KPI targets and experiment duration |
| 2026-10-25 | D12 owner decision | 2-вариант: KPI effect target and A/B runtime to be computed from verified baseline, traffic, MDE, sample size, power, safeguards; no invented uplift or arbitrary 7/14 day experiment. Docs only. | this docs commit | NO TESTS RUN; decision logged, runtime unchanged | D13 privacy and retention scope |

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

**Жорий навбат:** **D13** — Smart Reminder ўқиш/хабар реакцияси тарихи ва шахсий маълумотларини қанчалик батафсил ва узоқ сақлайди? **OPEN; owner қарори кутилмоқда.** D01–D12 тасдиқланган; D03 weekly cap, D05 global anti-spam, D09 model confidence gate ва D14 legacy mapping ҳали OPEN.

### 16.1 Decision log
| ID | Дата | Тасдиқ | Таъсир | Commit |
|---|---|---|---|---|
| PROCESS-01 | 2026-10-25 | Ҳар саволда содда тушунтириш + 2 вариант + агент тавсияси; фақат owner танлайди, сўнг дарҳол шу файлга қайд этилади | Барча кейинги Smart Reminder қарорларига | жорий docs commit |
| D01 | 2026-10-25 | **1-вариант:** аллақачон эслатма ёқилган каналларни Smart Reminder'га автоматик ўтказиш, қайта-қайта рухсат сўрамаслик. OFF/denied ва OS илк рухсати сақланади. | I02, preferences/migration, P0/P1/P3, UX; D14 mapping still OPEN; no runtime change | feca3f44086128fb213dbeb9e48814673c9c6c2c |
| D02 | 2026-10-25 | **2-вариант:** Smart Reminder ўқиш одатини ўрганиб вақтни автоматик мослаштиради; маълумот етарли бўлмагунча эски вақтни сақлайди; фойдаланувчи хоҳласа аниқ вақтни қўлда белгилаб қотиради. | Habit estimator, preferences/time_mode, UI, P2 ва timezone QA; time thresholds ҳали PROPOSAL; runtime ўзгармаган | 55aeb68f6b7a379e3bcd6b78ab88f065277dc4be |
| D03 | 2026-10-25 | **2-вариант:** individual adaptive cadence, ignored → frequency decreases; real study response → increases only within safe bound; **max 1 study reminder/user/local day** across platforms. Weekly absolute cap / algorithm thresholds NOT DECIDED. | I03, preferences, P2/P3/P5, policy and regressions; runtime unchanged | 7989bb0d74a4d26f122e81423df8b33cf277bb80 |
| D04 | 2026-10-25 | **Owner modification:** no predefined hours/blackout, completely habit-adaptive time including nighttime, user manual/quiet/pause and OS DND preserved, D03 cap remains. | I05, engine eligibility, user preferences, UX, policy, P2 DST/night-time test; runtime unchanged | 78da152f698f1283acb309fa0b919c5bccc0fb95 |
| D05 | 2026-10-25 | **2-вариант:** study, ranking and weekly results keep separate purposes; global per-account category-aware dedup/anti-spam coordination; low-value ranking suppressed/deferred; valuable weekly summary not blindly dropped; no hard global numeric threshold decided. | Priorities, frequency/collision policy, P0/P2/P3/P6 and QA; transaction notifications separately governed; runtime unchanged | 430d81841698a5ec26e62e1d4847c15fbd5c1dc2 |
| D06 | 2026-10-25 | **2-вариант:** select ONE notification channel/device automatically from genuine user learning activity + notification delivery reliability; optional user manual lock; no parallel cross-channel broadcast; denied/unavailable must be respected. | I03, delivery orchestrator, preferences/schema, Android+Telegram+PWA/Desktop adapter rules, P1/P3/P4/P5, QA; D07 fallback remains OPEN, runtime unchanged | 1cec1d2a2c4745243249fbb6a5ec9c5a1f61c4ee |
| D07 | 2026-10-25 | **2-вариант:** safe fallback only upon verified non-display/definitive send failure; unknown (no ACK/timeout/offline) → no cross-channel retry. Same job, account-level guards, study category only. | I12, delivery state machine, persistence, P1–P5, edge-case QA; runtime unchanged | 16ff220752a35731d6032f56c9c1d05c00c0d9a7 |
| D08 | 2026-10-25 | **2-вариант:** analyze individual study rhythm; on unusual inactivity offer valid easy lesson; no useful response → progressively less frequent reminders and eventual stop, exact thresholds OPEN. | Reactivation policy, P2/P6, tracking and QA; only docs changed | a3d31cd369b078356cea263bd7f5dbe904fbd9ee |
| D09 | 2026-10-25 | **Owner hybrid choice:** immediately working rule-based personalized reminders → collect verified account-level learning data → if safely validated shared ML available and user evidence reliable, automatic per-user ML switch; reversible fallbacks, D01–D08 always win. | Architecture optimizer, event capture, eligibility/version gates, P2/P6/P7, analytics/control/rollback; no runtime change | 2a28cc263579eb226289364863a38464b9461efa |
| D10 | 2026-10-25 | **1-вариант:** Telegram bot/Mini App and Android V1; learner PWA and Desktop V2; universal provider-neutral core, cross-platform account policy/identity/dedup built from start. | V1/V2 scope, architecture, P3/P4/P5 and regression, no runtime change | cecfa718f70e4b1b6142542b958976555e37f5a9 |
| D11 | 2026-10-25 | **2-вариант:** one minimal Smart Reminder Admin PWA section with global control, existing message templates and real notification/learning-outcome analytics; source-backed metrics/experiment results only, no fake numbers. | Admin controls, P6 implementation, security and QA, runtime unchanged; placement milestone TBD | 2f7aa95ce44f8cff46984e63b2854474d01cd089 |
| D12 | 2026-10-25 | **2-вариант:** experiment targets and duration from actual baseline/traffic with sample size/power and guardrails, owner reviews concrete values after evidence; no fixed target invented. | Metrics definitions P6, controlled experiments, D09 model evaluation and admin reporting; docs only | this docs commit |
