# HSK AI — Agent ko‘rsatmalari

## Loyiha va aloqa

HSK AI — Xitoy tilini o‘rganish platformasi: Telegram bot va Mini App, Android
(direct/Play), macOS/Windows Desktop, public veb-sayt hamda umumiy FastAPI
backend. Hisob, kurs progressi, to‘lov va access qarorlari platformalar bo‘ylab
mos bo‘lishi kerak; haqiqiy kontraktni kod va tegishli testlardan tekshir.

- Asosiy kod va texnik identifikatorlar: English.
- Foydalanuvchiga odatda o‘zbek tilida javob ber; lotin yoki kirill yozuvini
  uning joriy so‘roviga moslashtir. Boshqa tilni aniq so‘rasa, o‘sha tilda javob ber.
- Qisqa, dalilga asoslangan yechimni tanla; taxminni tasdiqlangan fakt sifatida yozma.
- Kod o‘zgartirishda ishlab turgan funksiyalarni saqla va vazifadan tashqari refactor qilma.

---

## Hozirgi mahsulot ustuvorligi: PWA + Android (owner decision, 2026-11-10)

**Barcha keyingi agentlar uchun doimiy scope qoidasi.** Asosiy mahsulot —
foydalanuvchi PWA'si (iPhone/iOS va browser) hamda Android (Play/direct).
Backend, auth, kurs, obuna/to‘lov, Admin PWA, public sayt va infratuzilmaga
faqat shu ikki asosiy client'ni ishlatish, qo‘llab-quvvatlash yoki ularga
foydalanuvchi olib kelish uchun kerakli miqyosda vaqt/token ajrat.

- **macOS/Windows Desktop — hozircha development freeze.** Desktop'ga xos
  yangi funksiya, UI/UX, bugfix, DMG/EXE packaging, parity sinxronlash,
  alohida test/CI, refactor yoki kelajak uchun oldindan kod yozma.
  PWA/Android task'ini Desktop'ni rivojlantirish uchun bahona qilma.
- Shared backend/API/domain o‘zgarishida mavjud umumiy kontraktlarni
  imkon qadar barqaror, platformadan mustaqil va keyinchalik Desktop ulanishi
  oson bo‘ladigan qilib saqla. **Bu faqat arxitektura ehtiyot chorasi:**
  Desktop uchun yangi adapter, shim, stub, endpoint, scaffolding, test yoki
  funksiyani oldindan yaratish talab qilinmaydi.
- Mavjud Desktop kodini o‘chirma, ataylab sindirma. PWA/Android uchun
  zarur shared o‘zgarish Desktop'ga muqarrar jiddiy regression tug‘dirsa,
  faqat eng kichik compatibility fix'ni ko‘rib chiq yoki konfliktni aniq
  hisobot qil; butun Desktop feature/parity ishini boshlama.
- **Telegram botning kelajakdagi roli** — foydalanuvchini PWA yoki
  Android'ga yo‘naltirish, botning o‘zida dars bermaslik. **Bu kelajak
  strategiyasi, hozirgi migratsiya topshirig‘i emas.** Hozir bot/Mini App'ning
  ishlayotgan dars, login, referral, to‘lov, Pro va progress oqimlarini
  o‘chirib yoki o‘zgartirib yuborma. Yangi bot-only ta’lim funksiyalariga
  default holatda investitsiya qilma; keyingi migratsiya uchun alohida
  scope, xavfsiz account/entitlement/progress handoff va release talab qilinadi.
- Noaniq task'da PWA/Android foydasiga eng tor scope'ni tanla. Faqat egasi
  Desktop'ni aniq qayta ustuvor qilsa, shu task doirasida Desktop ishini och.
  Pastdagi Desktop-specific qoidalar **faqat shunday ruxsatlangan task** uchun
  amal qiladi; bu ustuvorlikni bekor qilmaydi.

---

## Javob qoidalari

- Qisqa va aniq yoz
- Avval yechim, keyin izoh
- Kod bo‘lsa tayyor holatda ber
- Kerak bo‘lsa 1-2 gap bilan sababini tushuntir
- Mavhum gapirma
- Agar request noto‘g‘ri bo‘lsa, to‘g‘ri yo‘l ko‘rsat

---

## Kod yozish standarti

Mavjud project style va tuzilishini saqla. Talabni bajaradigan eng sodda, tushunarli va qo‘llab-quvvatlash oson yechimni tanla; qayta ishlatiladigan abstraksiyani faqat real takrorni kamaytirsa qo‘sh. Yangi dependency’ni faqat real talab uchun zarur bo‘lsa qo‘sh va avval mavjud kutubxonalarni tekshir. Bog‘liq bo‘lmagan refactor qilma. Yangi fayl ochishdan oldin mavjud kodni tekshir va kerak bo‘lsa kengaytir.

---


## Permanent Backend / learner PWA performance contract

Before implementing **any future** Backend API or learner PWA screen, section or feature (including modifications to existing ones), read and apply [docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md](docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md). These rules remain active after the current optimization PR is merged; do not treat them as a one-time sprint.

- PWA: verified-session-first safe shell, above-the-fold logo/mascot priority, per-section skeleton/loading/empty/error/retry, progressive updates, stable layout, lazy offscreen assets, and no duplicate in-flight reads. Never block all UI on an unrelated API call.
- **Permanent layout-first skeleton requirement:** all new or modified learner PWA sections reserve the final visual layout before data arrives (e.g., Rating podium + header + member/countdown row + first leaderboard rows). No generic loading card in place of a complex screen, no large blank gap, no layout jump. Verified data replaces placeholders **in their own slot** with a short opacity fade; reduced-motion disables it. Check on iPhone/WebKit and include stable-geometry assertions in the affected browser test. See the mandatory "Layout-matched skeletons and smooth in-place settlement" section in the linked contract.
- Backend: before adding a route/query, check N+1, bounded data/pagination, pool/transaction scope, indexes based on plans, timeouts, request concurrency and cache invalidation/owner isolation; use existing infrastructure before Redis/new servers.
- Protect Trial/Free/Pro, payments, auth, CSRF, lesson progress and shared Mini App/Android contracts. No cached private cross-account content or optimistic entitlements.
- A Backend/PWA feature is not done without focused regression tests and relevant slow-network/SQL or browser evidence; if an optimization is unnecessary, document evidence rather than adding it.
- `.github/workflows/backend-pwa-performance-contract.yml` is the recurring CI check. Never bypass it by adding a dummy test or weakening assertions. Keep Android native optimization out of this phase.


## Bug fix standarti

Bug topsang quyidagicha ishlagin:

1. Root cause top
2. Minimal fix qil
3. Muhim side-effectlarni tekshir
4. Takrorlanadigan muammo bo‘lsa, uni tutib qoladigan regression test yoki guard qo‘sh

Format:

- Sabab:
- Fix:
- Risk:
- Prevention:

---

## Project bilan ishlash

Har session boshida:

1. `AGENTS.md` va `AI_RULES.md`ni o‘qi; `PROJECT_MEMORY.md`, tegishli log va TODO’ni “Memory tizimi” bo‘yicha tekshir.
2. Vazifaga tegishli project structure va working tree holatini tekshir.
3. User so‘rovi va joriy holatga qarab asosiy ishni aniqlab ol.

Har taskdan keyin:

- nima o‘zgardi
- qaysi fayl o‘zgardi
- next step nima

qisqa yoz.

---

## Memory tizimi

### Fayllar

- PROJECT_MEMORY.md = loyiha uchun yagona doimiy faktlar va invariantlar manbai
- memory/YYYY-MM-DD.md = faqat kerak bo‘lsa yoziladigan lokal ish tarixi
- knowledge/bugs/ = bug saboqlari
- TODO.md = mavjud bo‘lsa joriy vazifalar

### Session boshida

Agar mavjud bo‘lsa:

1. PROJECT_MEMORY.md o‘qi
2. tegishli memory/YYYY-MM-DD.md ish tarixini tekshir
3. TODO.md ni tekshir

### Session davomida

- PROJECT_MEMORY.md dagi update siyosatiga mos muhim, doimiy qarorni shu faylga kirit
- Faqat foydali bo‘lsa memory/YYYY-MM-DD.md ga qisqa ish qaydi yoz; diary yaratma
- Takror bug bo‘lsa knowledge/bugs ga yoz

### Session oxirida

Foydalanuvchiga qisqa ayt:

- Nima qilindi
- Nima qoldi
- Keyingi step

Har taskdan keyin kunlik log yaratish shart emas.

---

## Public site / iPhone PWA download invariant

Website UI navigation is **mobile-only** at widths <= 850px: brand, globe-only
language control, and a three-line menu. Desktop inline navigation must remain
unchanged. The canonical UZ/RU/TJ public copy is in
`localization/public_site/content.py` and must be regenerated into
`app/public_site/content.py` without manual divergence.

The official iOS/iPadOS entry on `/download` is **the browser PWA**
(`/iphone-pwa`), not a native IPA and not a Telegram Mini App launch.
Preserve the selected `lang=uz|ru|tj` from the public download page
through unauthenticated `/iphone-pwa` → `/iphone-pwa/onboarding/li`
when the Li entry flag is enabled; never let unrelated tokens, arbitrary query
parameters or legacy referral secrets pass through the handoff. An existing
verified PWA session keeps its own server account/language authority.

Keep the reviewed iPhone Safari installation video at
`/assets/onboarding/iphone-home-screen.mp4`, with explicit Share → Add to
Home Screen instructions and textual fallback. The 2026-11-09 replacement
shows the official `hskai.app/iphone-pwa` address rather than the obsolete
Railway URL; verify the committed SHA-256, browser playback and deployment
before releasing publicly. Android APK social-browser Telegram fallback
and the optional **verified** iPhone Telegram-referral path are separate
contracts and must not be silently removed or credited as PWA referrals.
Update UZ/RU/TJ local copy, metadata/JSON-LD, docs, tests and analytics
impact together; see `docs/iphone-pwa/SITE_DOWNLOAD_HANDOFF_2026-11-09.md`.

---

## Permanent analytics integrity and feature coverage

**This is a cross-session rule for Codex, cloud AI and every future feature change**, not
a one-time cleanup task. Read the canonical plan:
[`docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`](docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md).

Before implementing or completing any **user-observable behavior or business-flow
change** (onboarding, lessons, practice, AI/voice, Pro/paywall, checkout/payment,
referral, notifications, login, app/platform flows, and related error paths):

1. Inspect existing actual event writers, trusted identity and payment/access
   authority, persistence, Admin PWA aggregation, UI/report consumer and tests.
2. State the **Analytics Impact** explicitly: reuse an existing verified event,
   add/version needed instrumentation, report an unsupported metric as unavailable
   with a reason, or demonstrate **no measurement impact**. Cosmetic text/CSS or
   non-behavioral refactors do not require invented telemetry.
3. When behavior needs measurement, connect the **complete chain in the same
   task**: client/server event → authenticated canonical user/attempt →
   deduplicated storage → metric contract and Admin consumer → focused tests →
   analytics coverage registry (once created). A new event enum alone is NOT
   implementation; a working feature with an unconnected dashboard is unfinished.
4. Check affected platforms, cohort/time window, denominator, event loss and
   attribution limits. Never treat missing instrumentation as zero, infer
   conversions from unrelated events or call estimates verified revenue.
5. Put `Analytics Impact: ...` and evidence or the justified exemption in the
   PR/task completion notes. Preserve existing auth, payments, Pro, lesson results,
   privacy and performance. Telemetry must never block the user's critical flow.

**Enforcement status:** this agent rule is active; the coverage registry, CI
guard and remaining analytics repairs are planned tasks in the linked document.
Do not claim those mechanisms already exist until verified on `main`.

---

## Doimiy lokalizatsiya qoidasi

UI matni qo‘shish, tarjimani tahrirlash yoki yangi til kiritishdan oldin
[`localization/README.md`](localization/README.md)ni o‘qi. Bu qoida ushbu ish
keyinchalik `main`ga o‘tgandan keyin ham barcha platformalar uchun amal qiladi.

- Foydalanuvchiga ko‘rinadigan yangi doimiy matnni mavjud canonical namespace’da
  UZ/RU/TJ uchun birga yoz; avval mavjud kalitni qayta ishlatish imkonini tekshir.
- Generated fayllarni qo‘lda tahrirlama va yangi inline tarjima lug‘ati yaratma.
  Matnni canonical manbadan generatsiya qilib, haqiqiy consumer’ga ulagin.
- Placeholder, plural, escaping, callback, resource ID va mavjud fallback
  kontraktlarini saqla. UI tarjimasiga dars javobi, baholash yoki access qarorini
  ko‘chirma; dars kontenti uchun quyidagi alohida QA siyosati amal qiladi.
- `python3 scripts/i18n_build_all_catalogs.py --write` va `--check`ni bajar;
  canonical manba, kerakli consumer/mapping va generated natijani birga commit qil.
  Ta’sirlangan tillar/platformalar uchun yo‘riqnomadagi tekshiruvlarni bajar.
- Yangi til faqat yangi papka yaratish bilan yoqilmaydi: API validation,
  generator, barcha client adapterlari/tanlagichlari va testlari birga yangilanadi.
  Tilni saqlashda noto‘g‘ri qiymatni display fallback orqali hisobga yozma.
- Source SHA, grading, private lesson, auth, obuna/to‘lov guard’larini chetlab
  o‘tma. Main/release ruxsati va Git qoidalari alohida saqlanadi.

## HSK AI P3 localization — agent-owned QA

Current P3 cross-session execution entry point: `localization/P3_ACTIVE_HANDOFF.md`. Read it before touching P3; the large `localization/NEXT_CHAT_HANDOFF.md` is historical detail.

For existing UZ/RU/TJ course translation work, follow
`localization/AI_CONTENT_QA_POLICY.md`. The agent checks and fixes the
Chinese-context meaning, grammar and natural UZ/RU/TJ, migrates verified
content into the local-first course architecture, tests every affected
consumer, and writes prevention/regression notes for each bug.
**Do not send the user translation review homework or require human
linguistic signoff.** Structural tests are not semantic approval. Keep
original answer/grade/Pro/auth data and source SHA guards intact;
do not merge or release with unresolved content/safety failures.

## Selective OpenSpec planning (opt-in by risk)

For high-risk/cross-platform features, auth, payments, entitlements, database schema changes, or substantial new modules, use the HSK AI planning skill at `.agents/skills/hsk-ai-openspec-planning/SKILL.md` and the project configuration `openspec/config.yaml` **before implementation**. Start from current source, tests, and authoritative scoped handoff documents. OpenSpec records a **proposed delta**, not a replacement for `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, localization policy, or existing product contracts.

Do not require OpenSpec for small UI/copy changes, isolated bug fixes, routine documentation, or already-scoped tasks. Do not retroactively migrate active plans or maintain parallel progress logs. If using OpenSpec, keep the proposal linked to the canonical relevant feature handoff; it must not silently overrule it. Never equate a spec or checked task with passing tests, a main push, or production acceptance. Continue to follow the repository's existing risk-based tests and Git rules.

## Git intizomi

Agar git ishlatilsa:

- kichik commitlar qil
- working state saqla
- commit message aniq bo‘lsin
- Repositoryda 3 ta asosiy, doimiy branch bo'ladi. Vazifani izolyatsiya qilish uchun qo‘shimcha vaqtinchalik branch yoki worktree ishlatish mumkin; ular asosiy branchlar hisoblanmaydi:
  - `main` — glavniy/production branch. Faqat testdan o'tgan ish shu yerga chiqadi.
  - `codex/local-ai` — lokal Codex/local AI uchun asosiy ish branchi; odatiy lokal testlar shu branchda bajariladi.
  - `codex/cloud-ai` — cloud/oblaka AI agentlari uchun asosiy ish branchi; test qilinmaguncha o'zgarish shu branchda turadi.
- Cloud AI ishni tugatsa, avval testlarni o'tkazsin. Agar cloud muhitida test o'tkazish imkoni bo'lmasa, context/yuriqnoma faylida nima o'zgargani, qanday test qilish va `main`ga qanday chiqarish kerakligini aniq qoldirsin; keyin lokal Codex `codex/local-ai`da test qilib push qiladi.
- Lokal AI/Codex odatda `codex/local-ai`da ishlaydi. Vazifa mavjud yoki ataylab ajratilgan vaqtinchalik branch/worktree’da boshlangan bo‘lsa, o‘sha joyda davom etadi va tegishli testlarni o‘tkazadi. Task scope’idagi o‘zgarishlar testlardan o‘tgach, alohida to‘xtab push ruxsatini so‘ramasdan `origin/main`ga chiqariladi; unrelated user o‘zgarishlari qo‘shilmaydi.
- `main`ga push qilingandan keyin `codex/local-ai` va `codex/cloud-ai` `main` bilan tenglashtiriladi, shunda keyingi AI eski kod ustidan ishlamaydi.
- Eski branchlarni o'chirishdan oldin backup bundle yoki aniq recover yo'li bo'lishi shart; kod yo'qolishi mumkin bo'lgan force/reset/delete ishlarini tasdiqsiz qilma.
- Testdan o‘tgan task o‘zgarishlari uchun odatiy yakuniy target `origin/main`; user alohida branch yoki PR so‘rasa, o‘sha target ishlatiladi. Pushni userdan qayta tasdiqlatish shart emas.
- Feature branchga push qilish ish tugadi degani emas. Kerakli commit `origin/main` ga yetib borganini remote ref orqali tekshirmaguncha push muvaffaqiyatli deb xabar berma.
- Pushdan oldin remote holatini yangila va intended commit bilan `origin/main` history holatini tekshir.
- Dirty working tree yoki branch divergence bo‘lsa unrelated user o‘zgarishlarini commit qilma, force push qilma va reset qilma. `origin/main` dan vaqtinchalik toza worktree yaratib, faqat intended commitni cherry-pick qil va `HEAD:main` ga push qil.
- Pushdan keyin `origin/main` refini qayta tekshir va final javobda `main` ga chiqqan commit hashni yoz.

Format:

- feat:
- fix:
- refactor:
- docs:

---

## Xavfsizlik

Har doim:

- .env ni commit qilma
- secret topilsa ogohlantir
- Destructive amaldan oldin aniq tasdiq ol; foydalanuvchi shu amal va qamrovga oldindan ruxsat bergan bo‘lsa, qayta so‘rama.
- deploy oldidan syntax/import check qil
- database delete/reset oldidan ogohlantir

---

## Telegram Bot rejimi

Priority:

- handlers tartibi
- state management
- callback clarity
- DB consistency
- anti-spam
- admin tools
- payment flow
- subscription logic

---

## Web loyiha rejimi

Priority:

- responsive UI
- clean backend
- auth security
- fast loading
- SEO basics
- maintainable structure

---

## AI integratsiya rejimi

Agar AI feature qo‘shilsa:

- token cost o‘yla
- fallback bo‘lsin
- timeout handling bo‘lsin
- logs bo‘lsin
- abuse protection bo‘lsin

---

## Davom ettirish qoidasi

Agar men "davom et" desam:

1. Oldingi holatni tekshir
2. Qayerda to‘xtaganimizni top
3. O‘sha joydan davom et
4. Noldan boshlama

---

# HSK AI platforma ko‘rsatmalari

HSK AI o‘quv platformasi Telegram bot/Mini App, Android, macOS/Windows Desktop,
public sayt va shared backend'dan iborat. Mini App uchun Telegram SDK qoidalari
faqat shu client'ga tegishli; API, access va progress kontraktlari barcha
client'lar uchun xavfsiz saqlansin.

## Critical rules

Do not break:
- existing lesson order
- VOCAB data
- GRAMMAR data
- quiz logic
- homework logic
- Telegram WebApp SDK integration
- backend result flow
- subscription/payment logic
- referral logic

UI o‘zgarishini xavfiga qarab tekshir:
- Navigatsiya, dars/test, onboarding, paywall, to‘lov, auth yoki keng dizayn
  o‘zgarishida avval zaif nuqtalar, user ta’siri, aniq patch, fayllar va xavfni
  ko‘rsat; keyin so‘ralgan scope doirasida ishlagin.
- Faqat matn, rang, spacing yoki kichik kosmetik xatoni tuzatishda mavjud
  komponent va ta’sirlangan ekranlarni tez tekshirib, minimal patch va
  tegishli visual smoke test yetarli. To‘liq UX audit shart emas.
- Aniq so‘ralgan o‘zgarish uchun qayta ruxsat so‘rama; mahsulot xulqi yoki
  scope noaniq bo‘lsa aniqlashtir.

## Skills to use

Use these skills when relevant:
- hsk-ai-ui
- frontend-design
- webapp-testing
- playwright

## Admin PWA — mandatory minimal-action UX contract

All Admin PWA screens and editors MUST follow [docs/admin-pwa/BROWSER_UI_CONTRACT.md](docs/admin-pwa/BROWSER_UI_CONTRACT.md) whenever adding or modifying UI. **Do not reintroduce redundant buttons, duplicate Cancel/Close actions, secondary Save/Confirm/Passkey prompts, or buttons that repeat an existing X, swipe-back or contextual action.** An edit drawer has one top-right X dismissal, supported right-swipe dismissal and at most one contextual primary action (Save/Send/etc.); no redundant footer Cancel/Close. Save remains disabled until there is a real persisted-value change and must disable again if reverted. On server-confirmed success show the existing animated checkmark then dismiss after 2.5 s. Existing transaction-bound WebAuthn, legally necessary confirmations and explicit unknown/error states are exceptions to *simplification*, not grounds to add duplicate UI. Before adding a control, verify it performs a necessary **distinct** task not already available; changes that intentionally add a second control for the same action require explicit owner approval. Keep this invariant across desktop, mobile, all future Admin PWA pages, and test updates.

## UI/UX rules

The interface must be:
- mobile-first
- Telegram Mini App safe-area compatible
- premium, clean, not childish
- clear for Uzbek, Russian, and Tajik users
- optimized for HSK learners

Chinese learning content must show:
- Chinese characters
- pinyin
- translation

Course is the core product. AI, voice, XP, streak, rewards, and subscription must support the course, not replace it.

## Quiz rules

Good quiz formats:
- fill blank in full sentence
- choose correct Chinese word
- choose correct pinyin
- choose correct translation
- arrange sentence order
- listen and choose
- mistake correction

Avoid:
- dry school-test layout
- unclear correct/wrong feedback
- too much text on one screen
- hidden progress

## Testing

Mini App, Telegram integration, UI yoki learning-flow o‘zgarishidan keyin ta’sirlangan yo‘lga mos smoke checklarni bajargin:
- layout yoki route o‘zgarsa, ilova mobile viewport’da ochiladi
- Telegram SDK/auth o‘zgarsa, ilova Telegram tashqarisida ham qulamaydi
- quiz/practice o‘zgarsa, natija yuboriladi
- homework o‘zgarsa, submission ishlaydi
- lesson navigation o‘zgarsa, darslar orasida yurish ishlaydi
- tekshirilgan ekranlarda console error yo‘q

Hujjat-only o‘zgarishlarda aloqasiz Mini App smoke testlarni talab qilma; backend o‘zgarishiga mos backend testini tanla.
