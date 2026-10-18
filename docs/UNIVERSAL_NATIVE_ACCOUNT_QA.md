# Universal kirish: amaliy test

`codex/universal-sign-in` branch’i uchun. `main` va production release hold
saqlanadi. Kod testlari real Google/Apple, Telegram bot va o‘rnatilgan ilova
sinovining o‘rnini bosmaydi.

## 2026-10-19 — eski Telegram akkauntlari uchun yakuniy gate

Egasi boshqa amaliy tekshiruvlarni bajarganini bildirdi; eski akkauntlar
tekshiruvi hali qolgan. Production va `main` hold saqlanadi.

- Amaldagi `HSK AI Universal QA / qa` bazasida faqat o‘qish orqali 3 ta user,
  5 ta payment va 3 ta course progress/profile qatori aniqlandi. Bu baza
  migratsiya auditidagi haqiqiy eski ma’lumotlar nusxasi emas. Yangi QA
  akkaunti bilan o‘tgan sinov eski akkauntning saqlanishini tasdiqlamaydi.
- [2026-10-18 audit dalili](UNIVERSAL_NATIVE_ACCOUNTS_STAGING_AUDIT_2026-10-18.json)
  61 jadvaldagi 190 155 yozuv, 2 118 user, 100 payment va 214 referralni
  qamraydi. `0102 → 0108` migratsiyasi hamda oldingi/keyingi backup restore
  solishtirishlarida billing, progress, XP/reyting, referral va account kalitlari
  saqlangan. `0103`–`0108` fayllari tekshirilgan versiya bilan bir xil;
  `0108` va read-only audit skripti SHA-256 qiymatlari hisobotga mos.
- Hozirgi kodda migratsiya/learning/payment/referral/subscription/progress
  regressionlari: 73 test va 66 subtest o‘tdi, alohida PostgreSQL test URL’i
  talab qiladigan 10 test skip qilindi. Acceptance/rehearsal/statistics
  to‘plami: 43 test va 46 subtest o‘tdi. Bu joriy yugurishda PostgreSQL 18
  migratsiya yoki backup restore qayta bajarildi degani emas.
- `test_legacy_paid_learner_keeps_payment_and_shared_progress_after_provider_signin`
  eski Pro hisobining ayni user/payment ID, status, muddat va summalarini,
  Android’da natija saqlanishini va Windows/macOS/Mini App’da progress, XP,
  Pro va reyting mosligini tekshiradi. Provider tasdiqlashi fixture bilan
  almashtirilgan; bu haqiqiy o‘rnatilgan ilova sinovi emas.

Qolgan amaliy qabul: egasiga tegishli tanlangan eski akkaunt nusxasi bilan
alohida yopiq staging’da oldingi user ID, Pro status/muddatlari, tugallangan
darslar, XP/reyting ballari, to‘lov/referral/preview qiymatlarini qayd etish;
Mini App hamda Android/Desktop’da shu akkauntni ochish va taqqoslash; bitta
darsdan keyin faqat kutilgan progress/XP o‘zgarishini tekshirish. Imkon bo‘lsa
free/expired/pending va HSK 3.0 ruxsat holatlari ham qamralsin. To‘liq shaxsiy
tarixli audit bazasini umumiy QA backend’ga ulab yubormang va hozirgi QA
hisoblarini almashtirmang. Shu tekshiruv yakunlanmaguncha gate ochiq qoladi.

## 2026-10-18 — QA fresh database blocker / guarded bootstrap

Railway `hsk-universal-qa-api` on commit `eecc56a1` built successfully but
**FAILED to deploy** because a completely fresh PostgreSQL 18 database reaches
migration `0011_add_course_workflow_fields` without `course_progress`.
Old Alembic revisions do not independently create all of the historical
course tables. Avoid rerunning `alembic upgrade head` against that partially
migrated database and NEVER stamp it to `0102` by guesswork.

Staging-only services:
- `hsk-universal-qa-db` — isolated disposable PostgreSQL 18 database service
- `hsk-universal-qa-api` — pinned universal sign-in QA app, failed at migration
- `Postgres-Iy93` — older staging PostgreSQL holding a previously verified
  `0102_payment_review_preview` restore; **contains real historical data**
- Production `main`, bot and production PostgreSQL are out of scope.

To set up a **new** account-testing database safely, an authorized operator can
use `scripts/qa_schema_only_bootstrap.py`. This is a reviewed helper, **not
an automatically performed copy**. Its default mode only validates the source
revision and that the destination does not exist. Application credentials and
database user passwords must stay in private Railway variables, never Git or
the chat. Environment must be `staging`, and both source and destination
must have distinct Railway private DNS hosts.

Set these variables only on a staging operator service/environment:

- `RAILWAY_ENVIRONMENT_NAME=staging`
- `QA_SCHEMA_ONLY_SOURCE_APPROVED=0102_payment_review_preview`
- `QA_SOURCE_HOST`, `QA_SOURCE_DB`, `QA_SOURCE_USER`, `QA_SOURCE_PASSWORD`
  must be **read-only** access to the verified staging `0102` restore, NOT a
  connection to production and NOT an account-test database
- `QA_TARGET_HOST`, `QA_TARGET_USER`, `QA_TARGET_PASSWORD` are for the new
  separate QA PostgreSQL 18 service
- `QA_TARGET_DB=hsk_universal_qa_schema` must **not already exist**
- `QA_SCHEMA_ONLY_CONFIRM=I_APPROVE_STAGING_SCHEMA_ONLY` is required for
  the writing step, in addition to the explicit `--apply` switch

Operator flow (inside an authorized, isolated staging environment):

```sh
# Read-only: verify exact 0102 source and absence of the target
python scripts/qa_schema_only_bootstrap.py
# Explicit action. pg_dump --schema-only copies no learner/payment/token rows
python scripts/qa_schema_only_bootstrap.py --apply
```

The script refuses source/target host equality, unknown revisions, non-staging
environment, existing destinations or suspicious names. It does not run in CI
or app startup and must **not** be used on production. If import fails, the
partially created target remains quarantined for operator review; the script
does not delete/recreate databases.

After a genuine `QA_SCHEMA_ONLY_COPY_PASS` from the real database:
1. Verify the new target has **zero** rows in users, payments, referrals,
   progress and all other personal-data tables; inspect `alembic_version`
   exactly `0102_payment_review_preview`. Do not connect clients before
   verification.
2. Point the staging **only** API's `DATABASE_URL` to this new destination.
   Execute formal `alembic upgrade head` to `0108_native_audit_ownership`;
   inspect the migration head and constraints. Do not redirect the current
   production environment or the staging source-copy service.
3. Launch the staging HTTP-only API with Telegram polling/schedulers suppressed
   (existing QA uses Uvicorn `--lifespan off`). Do not reuse the production bot
   token, Telegram webhook, AI provider secrets, or receipt storage.
4. Verify `/health`, provider discovery, malformed/expired callback behavior.
   Then configure private staging Google/Apple OAuth credentials and callback
   URLs; install QA Android and desktop builds; test real login, provider
   linking, cancellation and cross-client parity.
5. Add actual proof to the release acceptance matrix. Green source CI or a
   schema-only copy cannot substitute for real callbacks. No `main` merge,
   production DB changes, or public registration until all gates pass.

Issue: [#181](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/issues/181).

## Test muhiti

- Universal branch’ning aynan tekshirilgan commitidan alohida staging backend
  ishlating. Hozir production eski `main`da; unda yangi oqimni sinamang.
- Sinov bazasini `0108_native_audit_ownership`gacha migratsiya qiling. Ilova
  startupidagi `create_all` mavjud jadvalga yangi ownership ustunlarini
  qo‘shmaydi; formal migratsiya backend ishga tushishidan oldin bajariladi.
- Staging uchun alohida database, bot, webhook, receipt storage va provider
  callback sozlamalari kerak. Production tokenlari, webhook yoki to‘lovlarini
  staging’ga ko‘chirmang. Oldingi migration/restore nusxalarini test akkauntlari
  bazasi sifatida ishlatmang: ularda haqiqiy foydalanuvchi ma’lumotlari bor.
- `OAUTH_REDIRECT_BASE_URL` staging HTTPS origin bo‘lsin.
  `OAUTH_NATIVE_RETURN_SCHEME=pomp-hsk-ai-qa` qo‘ying. Bu faqat ilovani
  ochadigan signal; unda login tokeni yoki tasdiqlash ma’lumoti bo‘lmaydi.
- Google browser oqimi uchun `GOOGLE_OAUTH_ENABLED`,
  `GOOGLE_DESKTOP_CLIENT_ID`, `GOOGLE_DESKTOP_CLIENT_SECRET` kerak. Console’da
  staging `/api/v3/native-auth/oauth/callback/google` callback’ini ro‘yxatga oling.
- Apple uchun `OAUTH_SETUP.md`dagi Service ID, Team ID, Key ID, private key va
  enable sozlamalari hamda staging
  `/api/v3/native-auth/oauth/callback/apple` return URL kerak. Ular hozirgi
  production’da mavjud emas. Maxfiy qiymatlarni chatga yoki Git’ga qo‘ymang.
- `/health` 200 qaytarsin. `/api/v3/native-auth/providers?platform=macos`
  va `?platform=windows` browser providerlarini ko‘rsatsin. Android browser
  oqimi ham shu confidential web client sozlamalaridan foydalanadi.
  Provider ro‘yxatda chiqishi real callback muvaffaqiyatini tasdiqlamaydi.

## Test ilovalari

Android’ni `android/` ichidan real staging origin bilan quring:

```sh
./gradlew :app:assembleDirectDebug :app:assemblePlayDebug \
  -PPOMP_QA_API_ORIGIN=https://YOUR-STAGING-HOST
```

QA varianti production’dan alohida paket/credential store va
`pomp-hsk-ai-qa` sxemasini ishlatadi. QA updater production ilovaga
almashtirmasligi kerak. `example.invalid` bilan yig‘ilgan konfiguratsiya
tekshiruvi haqiqiy login uchun test ilovasi hisoblanmaydi.

macOS/Windows uchun `desktop/README.md`dagi staging build ko‘rsatmalaridan
foydalaning: staging origin, alohida bundle ID, QA protocol va o‘chirilgan
updater birga qo‘llanishi kerak. Har ikki OS’da o‘rnatilgan buildni sinang;
brauzer fixture testi OS protocol ro‘yxatdan o‘tganini isbotlamaydi.

## Har bir qurilmada tekshiriladigan oqim

Android Direct, Android Play, macOS va Windows’da takrorlang:

1. Chiqilgan holatdan Google orqali kiring. Brauzer tasdiqlashdan keyin aynan
   QA ilovasini ochsin. Avtomatik ochish browser tomonidan bloklansa,
   callback sahifasidagi `HSK AI` tugmasi ishlasin. Apple bilan ham takrorlang.
   Telegram so‘rovi alohida staging botning private chatida tasdiqlansin.
2. Google-first va Apple-first yangi akkauntlarda Telegram bo‘lmasin. Dars
   boshlang, natija saqlang va haqiqiy AI Voice bilan gaplashing. Ichki user ID,
   XP, progress, Pro va HSK 3.0 holatini qayd eting.
3. Profildan qolgan Google/Apple/Telegram usulini ulang. Har biri alohida
   tasdiqlansin; ulangan usulni qayta ulash kartasi yo‘qolsin. Boshqa qurilmada
   shu provider bilan kirganda avvalgi user ID va ma’lumotlar chiqsin.
4. Bir identity bilan ikki qurilmada bir vaqtda registratsiya qiling: bitta
   user ID bo‘lsin. Bir xil email boshqa provider identity’sini avtomatik
   birlashtirmasin. Boshqa akkauntga tegishli identity ulanishi rad etilsin.
5. Browser/botda bekor qilish, oynani yopish, timeout, tarmoq uzilishi, profilni
   tark etish va logoutdan keyin kech kelgan javoblarni tekshiring. Bekor
   qilingan proof akkauntni almashtirmasin yoki keyinroq identity ulamasin.
   Ilova OS tomonidan yopilgan bo‘lsa, qayta urinish tushunarli va xavfsiz
   bo‘lsin; return URI o‘zi login qilmasin.
6. Ulangan akkauntni bloklab, barcha providerlar orqali kirishni qayta sinang.
   Eski session refresh ham rad etilsin. Ulanmagan, butunlay boshqa identity
   orqali odamni aniqlash bu vazifa doirasiga kirmaydi.
7. Direct va desktop’da test cheki bilan Pro va HSK 3.0 xarid/admin review
   oqimini bajaring. Faqat o‘sha user ID’ning access’i o‘zgarsin. Play’da xarid
   va tashqi to‘lovga yo‘naltirish bo‘lmasin; mavjud access ko‘rinsin.
8. Telegram ulangach Mini App, Android va ikkala desktop’da user ID, Pro,
   XP, darslar va reyting mos kelsin. In-app va public `/account-deletion`
   orqali egalik tasdiqlanib so‘rov yuborilsin; retention qoidalari saqlansin.

## Ownership auditidan keyingi qo‘shimcha tekshiruv

Faqat staging’dagi disposable hisoblarda bajaring:

- Google-first, Apple-first va eski Telegram hisobini alohida User ID orqali
  admin paneldan oching. Bir xil son boshqa hisobning Telegram ID’si bo‘lsa,
  tanlangan ichki User ID o‘zgarmasin.
- Native hisobga qo‘lda Pro va shaxsiy chegirma bering; boshqa hisobga
  ta’sir qilmasin. Chegirma Direct/desktop checkout’da ko‘rinsin. Qo‘lda Pro
  berish chek, revenue, yangi AI budjet yoki preview imkoniyati yaratmasin.
- Telegram ulashdan oldin yuborilgan native chek holati Mini App’da ulashdan
  keyin ham o‘qilsin. Boshqa hisob cheki ochilmasin.
- Referral/bonusni takroriy kirish yoki provider ulash bilan qayta olish
  mumkin bo‘lmasin. XP, reyting va reklama kunlik cap’i bitta hisobga tegishli
  bo‘lib qolsin. Adminning Android/Desktop/statistikasi shu hisobni sanasin.
- Staging test hisobini o‘chirishda ikkinchi hisob qurilmasi, sessiyasi,
  shaxsiy chegirmasi va tarixi saqlansin. Tasdiqlangan moliyaviy faktlar
  mavjud retention qoidalari bo‘yicha qolishini operator tekshirsin.

Har xatoda build commit/versiyasi, OS, provider, kirish yoki ulash ekani,
vaqt/timezone va maxfiy ma’lumotsiz xato matnini yozing. OAuth code, state,
polling secret, token, private key yoki raw credential loglarini yubormang.
Natijalarni [asosiy acceptance jadvaliga](UNIVERSAL_NATIVE_ACCOUNTS.md)
qo‘shing. Barcha real gate’lar o‘tmaguncha `main`ga chiqarmang.
