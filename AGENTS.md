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
