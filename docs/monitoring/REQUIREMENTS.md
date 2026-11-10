# HSK AI — Ягона автоматик хатолик мониторинги

**Ҳужжат тури:** Мақсад ва мажбурий талаблар (Codex / OpenSpec учун манба)  
**Сана:** 2026-11-10  
**Устуворлик:** P0 — келажакдаги функциялар учун CI мажбурияти  
**Репозиторий:** `akbarholturaev11-lang/HSK-AI-Bot`  
**Ҳолат:** Талаблар тасдиқлашга тайёр; код, миграция, CI ва production ўзгартирилмаган. Бу ҳужжат расмий OpenSpec validation ўрнини босмайди.

## 1. Асосий мақсад

HSK AI’даги техник хатоликларни **фойдаланувчи шикоят қилишини кутмасдан автоматик аниқлаш**, хавфсиз қайд этиш, бир хил муаммоларни гуруҳлаш ва мавжуд **Admin PWA** орқали таҳлил қилиш. Жиддий янги ёки кучайган муаммолар ҳақида **iPhone/Mac Admin PWA Apple Push** орқали хабар бериш. Тизим илова ривожланган сари янги функцияларни ҳам доимий қамраб олиши шарт.

**Кутиладиган натижа:** администратор қайси платформа, функция ва версияда муаммо борлиги, қачон бошлангани, қанча такрорлангани ва қанча фойдаланувчига таъсир қилганини (ишончли ҳисоблаш мумкин бўлса) кўради; муаммони текширади ва ҳал этилганини белгилайди. Барча хатоликларни 100% ушлаш ёки root cause’ни автоматик топиш кафолатланмайди.

## 2. Платформалар ва устуворлик

- **V1 / P0:** Android Direct + Play, iPhone/browser learner PWA ва уларнинг умумий FastAPI backend’и; қабул қилиш ва кўриш маркази — мавжуд Admin PWA.
- **V1 мослик:** Telegram Mini App’нинг ишлаб турган хатолик сигналларини сақлаш ва хавфсиз равишда ягона мониторингга улаш. Мавжуд ўқиш, логин, Pro ва referral оқимлари бузилмасин.
- **Admin огоҳлантириш:** мавжуд iPhone/macOS Admin PWA Apple Web Push; янги алоҳида push тизими қурилмасин.
- **Кейинги давр:** macOS/Windows Desktop учун фақат shared backend контрактини кенгайтириш имкони сақлансин. **Ҳозир Desktop’га махсус код, adapter ёки CI ёзилмасин** (development freeze).
- Telegram ботнинг келажакда PWA/Android’га йўналтирувчи ролини ҳисобга ол; ҳозирги Mini App/bot функцияларини муддатидан олдин ўчирма.

## 3. Қайси хатоликлар йиғилади

- Android: асосли crash/process-exit сигналлари, Kotlin/Java exception, муҳим API 5xx ва функциянинг кутилмаган ишламай қолиши.
- PWA/Mini App: JavaScript exception, unhandled promise rejection, муҳим API/юкланиш/сақлаш/қайта тиклаш хатоликлари.
- Backend: белгиланган муҳим 5xx, сервис ва интеграция носозликлари; аниқ allowlist ва чегаралар билан.
- Устувор user flow’лар: login/onboarding, дарсни очиш ва якунлаш, practice, course progress, обуна/тўлов, PWA↔Android ўтиш.
- **Оддий рад этиш ёки кутилган ҳолатлар** (лимит, paywall, фойдаланувчи бекор қилиши, оддий 401/403/409, вақтинча offline) автоматик критик crash деб ҳисобланмасин. Ҳақиқий тикланиш ёки муваффақиятсизлик сервер маълумотлари билан ажратилсин.
- Фойдаланувчи қўлда юборадиган bug report алоҳида мавжуд имконият бўлиб қолади; автоматик monitoring унинг ўрнини босмайди ва дубликат яратмайди.

## 4. Хавфсиз telemetry ва incident модели

- Клиент фақат версияланган, чекланган майдонларни юборади: `event_id`, вақт, client/platform, app/build версияси, `feature_code`, `failure_code`, `site_code`, натижа ва хавфсиз техник категория.
- `users.id` фақат текширилган сервер сессиясидан аниқланади; client юборган owner ID, severity ва arbitrary fingerprint’га ишонилмасин.
- **Тақиқланган:** token/cookie, Telegram `initData`, password, шахсий ёзишмалар, дарс жавоблари, payment маълумоти, screenshot, raw stack/error message, URL query, request/response body ва device fingerprint. Ҳеч бири Inbox, Push, лог ёки аналитикага чиқмасин.
- Бир event’нинг retry’лари `event_id` билан идемпотент бўлсин. Бир хил ҳақиқий хатоликлар сервер ҳисоблаган fingerprint орқали битта **incident**га йиғилсин; occurrence сони, first/last seen, версия ва таъсир доираси сақлансин.
- PostgreSQL’да atomic dedup, concurrency, retention, account deletion ва минимал индекслар режалаштирилсин. Янгидан Redis/сервис фақат зарурати исботланса қўшилсин.
- Incident ҳолатлари мавжуд Admin triage билан мувофиқ: **New → Investigating → Resolved**; такрорланган ҳолатни қайта очиш қоидаси аниқ ва audit’ли бўлсин.

## 5. Admin PWA ва Apple Push

- Мавжуд Inbox’га ягона `diagnostic` incident манбаси ёки код аудити асосида унга тенг минимал интеграция қўшилсин. Иккинчи Admin панел, triage ёки notification worker яратилмасин.
- Кўриниш: платформа, функция, failure code’нинг тушунарли изоҳи, версия, вақт, такрорланиш, таъсир доираси, приоритет, ҳолат ва қулай фильтрлар. Махфий деталлар чиқмасин; UI UZ/RU/TJ локализация ва минимал тугмалар қоидасига мос бўлсин.
- Apple Push **фақат муҳим янги/жиддийлашган incident** учун: server-owned severity, дедупликация, cooldown, rate limit; бир хил 100 та event → 100 та push эмас.
- Push payload’да фақат хавфсиз категория бўлсин; босилганда авторизациядан кейин тегишли Inbox кўриниши очилсин. Payment ва мавжуд Android/technical хабарномаларининг приоритети ва ишлаши ўзгармасин.
- Push қабул қилингани iPhone/Mac’да кўринганини исботламайди: real-device acceptance алоҳида.

## 6. Ишончлилик ва ресурс назорати

- Monitoring **non-blocking**: хатолик юбориш муваффақиятсиз бўлса ҳам login, курс, progress, тўлов ва асосий API ишлайверсин.
- Android/PWA учун мавжуд имкониятга мос, қисқа TTL ва ҳажмли offline queue, чекланган retry/backoff; logout ва account switch пайтида аввалги owner event’лари бошқа аккаунт номидан юборилмасин.
- Reporter ўз хатолигини қайта report қилиб чексиз циклга тушмасин. Crash handler тармоққа blocking request юбормасин.
- Client/server rate limit, abuse protection, максимал payload, вақт/версия текшируви, multi-worker atomic admission ва retention/cleanup бўлсин.
- Feature flags, босқичли rollout, кузатув, алоҳида diagnostic kill switch ва хавфсиз rollback; monitoring’ни ўчириш тўлов, дарс ёки мавжуд push’ни ўчирмасин.

## 7. **P0 — Янги функциялар учун доимий monitoring + CI қоидаси**

**Бу бир марталик интеграция эмас.** HSK AI’га кейин қўшиладиган ёки хулқи муҳим ўзгарадиган ҳар бир PWA, Android ва Backend функцияси **ўша вазифанинг ўзидаёқ** хатолик мониторингига уланиши шарт.

1. `AGENTS.md` ва тегишли иш жараёнида доимий **Monitoring Impact** талаби бўлсин: қайси failure signals, event/feature codes, server intake, incident mapping, Admin Inbox projection ва test coverage мавжудлиги ёзилади.
2. Ягона ихчам **coverage registry** сақлансин: `feature → client/error source → reporter → authenticated intake → incident → Admin consumer → tests`, ҳолати `covered / partial / not_applicable` ва далиллари билан. Мавжуд Analytics Integrity registry’сига зид ёки дубликат бўлмасин; бирлаштириш имкони аввал текширилсин.
3. Муҳим функциянинг янги/ўзгарган коди учун CI **реал integration ва regression тестларини** талаб қилсин: хатолик сигналидан privacy-safe қабул қилиш, dedup ва Admin’да кўринишгача камида тегишли тест занжири тасдиқлансин. Фақат enum, registry сатри ёки сохта mock мавжудлиги етарли эмас.
4. Қамровсиз муҳим функция ёки бузилган monitoring contract бўлса, **CI fail ва merge block**. Фақат cosmetic/copy/ҳақиқатан мониторингга алоқасиз ўзгаришлар асосланган `not_applicable` билан ўтсин; CI текширувини сохта файл/тест билан айланиб ўтиш тақиқлансин.
5. Эски функцияларни бир кунда тўлиқ қоплашни талаб қилма: аввал baseline/inventory, кейин хавфи юқори legacy flow’ларни босқичма-босқич қамра. **Аммо янги муҳим функцияларга талаб биринчи кундан мажбурий.**
6. Monitor’нинг ўзини ҳам текшир: schema compatibility, auth/privacy, dedup/concurrency, rate-limit, offline/account-switch ва Admin projection регрессиялари; CI билан бирга staging/device acceptance алоҳида қолади.
7. Performance contract сақлансин: telemetry PWA first paint, section loading, backend latency ёки Android responsiveness’ни секинлаштирмасин.

**Натижа:** Code AI янги функция ишлаб чиққанда мониторингни эслатиш шарт бўлмасин; ҳам агент қоидаси, ҳам CI буни мажбурий текширсин.

## 8. Analytics билан интеграция

- Monitoring — **incident ва техник диагностика**, Analytics — **маҳсулот/KPI ҳисоботи**. Ўхшаш event’лар икки марта ҳисобланмасин.
- `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md` ва `AGENTS.md`даги Analytics Impact қоидаси билан event writer → storage → aggregator → Admin projection занжири келишилсин.
- Ишончсиз impact/user count, lost events, rate-limit ва coverage gap’лар «0» эмас, **unknown/partial** деб кўрсатилсин. Monitoring failure ва data quality ҳолатларини ўзини кузатиш ҳам режалаштирилсин.

## 9. Режалаштириш, тест ва қабул қилиш

- Codex энг янги `origin/main`ни олиб, мавжуд Android bug report, Mini App `app_error_context`, iPhone PWA report, Admin Inbox/Apple Push, analytics, schema ва тестларни **қайта аудит қилсин**. Эски 28 октябр режаси фактлар учун эмас, контекст учун ишлатилсин.
- Режа айнан `$hsk-ai-openspec-planning` skill ва ҳақиқий OpenSpec CLI жараёни билан `proposal`, `specs`, `design`, `tasks` шаклида тузилсин. Дубликат change/plan яратилмасин.
- **Режадан кейин мажбурий соддалаштириш аудити:** тайёрланган барча OpenSpec артефактларини қайта кўриб чиқ; ортиқча, тахминий ёки исботсиз мураккаблаштирилган блокларни олиб ташла; мақсади бир хил ёки бир-бирига қаттиқ боғланган вазифаларни битта аниқ иш пакетига бирлаштир; такрорланган acceptance criteria, test, ҳужжат ва инфратузилма вазифаларини қисқартир. Мавжуд ишлайдиган компонентлар бор жойда янги сервис, абстракция ёки алоҳида pipeline таклиф қилма. Босқичлар сонини зарур минимумга тушир, лекин амалга ошириш тартиби ва масъулият чегаралари аниқ қолсин.
- **Соддалаштиришда кесиб ташлаш мумкин эмас:** автоматик error intake, privacy/auth, dedup/incident, Admin PWA/Apple Push, Android/PWA ва Mini App мослиги, rollback, асосий хавфсизлик тестлари ҳамда **келажакдаги янги муҳим функциялар учун P0 Monitoring Impact + CI merge-block** талаби. CI қоидаси охирги босқичга сурилиб ёки «кейин» деб қолдирилмасин.
- Соддалаштирилган якуний OpenSpec режани `openspec validate` билан текшир; агар қайта таҳрир қилинса, validation’ни қайта ишлат. Якунда нима бирлаштирилгани ва нима асосли равишда олиб ташланганини қисқа change summary’да кўрсат.
- Босқичлар: **(1)** архитектура ва intake/DB, **(2)** Android+PWA reporters, **(3)** Inbox+Push, **(4)** Mini App мослик, **(5)** P0 CI/coverage enforcement ва staged acceptance. **CI қоидаси P0 сифатида илк босқичдан лойиҳаланиб, янги функциялар учун release олдидан ишга тушиши шарт.**
- Acceptance: repeated event → 1 receipt/incident increment; cross-worker race; privacy payload reject; critical push bounded; resolved/reopen; offline→retry; owner switch; blocked/revoked user; account deletion; Android Direct+Play; PWA Safari; Mini App regression; backend 5xx; CI янги unmonitored муҳим функцияни рад эта олиши.
- Unit/integration/CI натижалари, staging, production ва physical iPhone/Android/Mac текширувлари **алоҳида** ҳисоблансин; бажарилмагани бажарилган деб белгиланмасин.

## 10. Қатъий чеклов

Бу файл — **барча мақсад ва талабларнинг ягона жамланмаси**, ҳали implementation ёки расмий OpenSpec change эмас. Фақат шу ҳужжатни тайёрлаш GitHub `main`, runtime, production, тўлов, auth, миграция, feature flags ёки CI’ни ўзгартиришга рухсат бермайди. Кодлаш бошланганда актуал `main` ва репозиторий қоидалари биринчи ўринда туради; мавжуд ишлайдиган функциялар қайта қурилмайди, фақат зарур интеграция қўшилади.