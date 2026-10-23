# Local-first UI authoring

Edit existing UZ/RU/TJ text under this directory, then build the committed local
resources once. Clients and the Bot read their bundled resources; no individual
UI translation needs a runtime server request.

```sh
python3 scripts/i18n_build_all_catalogs.py --write
python3 scripts/i18n_build_all_catalogs.py --check
```

The builder validates every namespace before writing any output, rejects
duplicate output ownership and reports missing/stale bundles. P0 checks all
53 generated artifacts. The unified builder also refreshes existing browser
asset cache tokens using the generated file's Git-blob content hash. It changes
tokens only in already reviewed HTML and updates the corresponding reviewed
hash; unrelated source changes require review first. `--check` reports stale
artifacts or cache tokens without writing them.

| Authoring source | Local consumer |
| --- | --- |
| `ui/{uz,ru,tj}/common.json` | Shared Android, browser, Desktop and Bot UI |
| `ui/{uz,ru,tj}/course.json` | Existing course and Mini App UI; platform bundles |
| `ui/{uz,ru,tj}/miniapp.json` | Mini App inline/helper maps through the bundled `hsk-miniapp-i18n.js`; shared messages retain common/course references |
| `ui/{uz,ru,tj}/desktop.json` | Desktop-specific labels, with shared keys owned by common/course |
| `ui/{uz,ru,tj}/bot.json` | Bot messages and compatibility key tables; shared keys are references |
| `ui/{uz,ru,tj}/notifications.json` | Fixed notification defaults/titles/CTAs; admin/custom campaign copy keeps precedence |
| `android/{main,direct,play}/values*/*.xml` | Native resources, byte-identical IDs/escaping/qualifiers and channel overlays |
| `public_site/content.py` | Existing public-page/SEO content module, byte-identical structured data |
| `lessons/nhsk2_grammar_uz_ru_tj.tsv` | Separately source-bound authenticated display overlays; never public UI bundles |

Native XML and structured public-site Python retain their existing formats to
preserve resource formatting, tuple/route contracts and platform behavior.
Generated application copies are delivery artifacts, not additional authoring
sources. Legacy inline browser/Desktop fallback dictionaries remain during
client rollover; editing one does not replace its canonical catalog value.

## Har bir matn o‘zgarishi uchun tartib

Bu yo‘riqnoma feature branch va keyinchalik `main`da ham amal qiladi.

1. **Manbani top.** Yuqoridagi jadvaldan namespace’ni tanla; mavjud kalit va
   consumer’ni `rg` bilan tekshir. Bir xil ma’nodagi umumiy matnni `common` yoki
   `course` egasida saqla. Boshqa namespace uchun mavjud reference/mapping’dan
   foydalan; bir xil gapni har platformaga mustaqil nusxalama.
2. **UZ/RU/TJ ni birga yoz.** JSON’da `schema_version`, `namespace`, `locale`
   va mavjud schema saqlanadi. Yangi kalit barcha uch tilda bo‘lishi kerak.
   Kalitni ekran/ma’noga qarab nomla; dinamik son yoki foydalanuvchi qiymatini
   kalitga aylantirma. `{count}` kabi placeholder nomlari va ularning
   namespace talab qilgan takror sonini barcha tillarda saqla. Gapni so‘zma-so‘z
   bo‘laklardan yig‘ish o‘rniga mavjud interpolation/plural usulidan foydalan.
3. **Consumer’ni ula.** Faqat JSON’ga kalit qo‘shish uni ekranga chiqarmaydi.
   Quyidagi adapterdan foydalan; kerak bo‘lsa uning mapping/layout/reference’ini
   yangila. Mavjud label, callback, icon identifikatori, resource ID, argument
   tartibi va fallback’ni tekshir. Yangi inline UZ/RU/TJ lug‘ati qo‘shma.
4. **Generatsiya qil.** Repo ildizidan `--write`, keyin `--check`ni bajar.
   Yuqoridagi buyruqlar canonical manbani, generated resurslarni va ruxsat
   berilgan browser cache tokenlarini moslashtiradi. `app/`, `desktop/` yoki
   Android’dagi generated faylni to‘g‘ridan-to‘g‘ri tahrirlama. Native XML uchun
   canonical `localization/android/` ichida Android escaping, plural quantity
   va Direct/Play overlay’larini saqla.
5. **Haqiqiy natijani tekshir.** Quyidagi read-only buyruqlarni va o‘zgargan
   consumer’ning mavjud unit/runtime testlarini bajar. UI o‘zgarsa uch tilda
   tegishli ekranni och: matn, parametrlar, til almashtirish va console xatolarini
   tekshir. Mini App uchun mobile viewport; Desktop uchun macOS/Windows parity;
   Android uchun ta’sirlangan Direct/Play variantlari hisobga olinadi.
6. **Birga commit qil.** Canonical manba, consumer/mapping, generated fayllar
   va kerakli regressiya testlari bir commit yoki izchil commitlar ichida bo‘lsin.
   Haqiqiy diff’ni ko‘rib chiq. Faqat tekshiruvni yashil qilish uchun yangi
   exception qo‘shma, guard’ni o‘chirma yoki barcha baseline’larni qayta yozma.

```sh
python3 scripts/i18n_build_all_catalogs.py --check
python3 scripts/i18n_course_ui_catalog_guard.py --output /tmp/hsk-course-ui-catalog.json
python3 scripts/i18n_ui_adoption_audit.py --output /tmp/hsk-ui-adoption.json
python3 scripts/i18n_baseline_guard.py --output /tmp/hsk-i18n-baseline.json
```

`course` kalitlari soni hozir `scripts/i18n_course_ui_catalog_guard.py`da
`EXPECTED_COUNT` bilan cheklangan; boshqa testlarda ham tekshirilgan kalit soni
yoki snapshot bo‘lishi mumkin. Ataylab yangi UI kaliti qo‘shilganda uning egasi,
uch tildagi qiymatlari va haqiqiy consumer’ni tekshirgandan keyin faqat tegishli
count/snapshot kontraktini yangila. Eski dars/graded source SHA’larini o‘zgartirma.
Browser HTML o‘zgarganda `--write` unreviewed source drift sabab to‘xtasa,
haqiqiy kod diff’ini tekshir va tegishli aniq review yozuvini asos bilan yangila;
generator yangi kodni o‘z-o‘zidan tasdiqlamaydi.

## Qaysi consumer orqali o‘qiladi?

| Joy | Mavjud o‘qish yo‘li / ulash talabi |
| --- | --- |
| Mini App common/course | `commonMessage`, `courseMessage` va mavjud dictionary adoption helper; HTML’da kerakli lokal bundle helperdan oldin yuklansin |
| Mini App inline/helper | `HSKAILocaleMap`; `miniapp.json` ichidagi `messages` bilan birga `maps` layout yoki common/course reference’ini ham saqla |
| Desktop macOS/Windows | Umumiy `desktop/ui/js/i18n.js` ichidagi `t`; shared key uchun `SHARED_COMMON_KEY` / `SHARED_COURSE_KEY`, own key uchun `desktop.json`; ikkala OS bir xil JS’dan foydalanadi |
| Bot | `app/bot/utils/i18n.py` ichidagi `t`, `bot_locale_map`; `bot.json`ning `references`, `tables`, `maps` tuzilmalari kerakli lookup’ni bog‘laydi |
| Bildirishnoma | `notification_message` va mavjud xizmat adapterlari; admin/DB/campaign matni belgilangan ustuvorligini yo‘qotmasin |
| Android | Mavjud `stringResource` / `getString`; generator yaratgan `R.string` nomini tekshir, nomni taxmin qilma; named va Android positional placeholder usullarini aralashtirma |
| Public sayt | `localization/public_site/content.py` → generated `app/public_site/content.py` → mavjud render/SEO assembly |

Fallback lug‘atini yangilash canonical qiymatni almashtirmaydi. Backend’dan
har bir UI satri uchun alohida tarjima so‘rash yoki AI tarjimasini kutish mumkin
emas. User/AI/campaign matni va dars materiallari alohida ownership’da qoladi.

## Til kodlari va saqlash qoidasi

- Hisob/API va UI JSON kodi: **`uz`, `ru`, `tj`**. Android Tajik resource/device
  kodi **`tg`**, papkasi `values-tg`; asosiy `values` resurslari Uzbek. Konversiya
  `android/app/src/main/java/com/pomp/hskai/core/i18n/LanguageCodes.kt`da.
- Public sayt Tajik yo‘li/tili `tg`, downloader API/query kodi `tj` bo‘lishi
  mumkin; mavjud adapter va testni tekshir. Barcha platformalar uchun bitta
  yangi fallback yoki alias siyosatini taxminan joriy qilma.
- Hisob preference’ini yozishda faqat endpoint qo‘llaydigan kodni qabul qil.
  Mini App hozir `tg` / `tg-cyrl` aliasini `tj`ga aylantiradi; native API’lar
  canonical kod kutadi. Bo‘sh/noma’lum qiymatni display fallback orqali
  saqlangan til ustiga yozma. Bot callback’ini aniq prefix va uchta ruxsat
  berilgan tugma bilan tekshir; eski daraja tugmasi tilni o‘zgartirmasin.

## Butunlay yangi til qo‘shish

Bu mavjud uch tildagi matnni tahrirlashdan kengroq alohida implementation
vazifasi. Faqat `ui/<code>/` papkasini nusxalash tilni qo‘llab-quvvatlamaydi.

1. Hisob/API kodi, BCP-47/device kodi va Android qualifier mosligini belgilab,
   eski UZ/RU/TJ kodlarini, saqlangan hisob qiymatlarini va fallback’larni saqla.
2. Barcha tegishli canonical namespace, native XML source-set/overlay va
   public-site strukturalariga tarjima qo‘sh. UI va dars kontenti qamrovini
   ajrat; UI tili mavjudligi barcha darslar o‘sha tilga o‘girilganini anglatmaydi.
3. Generator/validator’lardagi locale ro‘yxatlari va Android tag mapping’lari,
   key/placeholder parity, manifestlar va artifact kutilmalarini kengaytir.
4. Backend request schema/allowlist, til saqlash xizmatlari, Bot keyboard/FSM
   filterlari, Mini App/Desktop selector/lookup, Android `AppLanguage`/`AppLocale`
   hamda public-site route/SEO adapterlarini birgalikda yangila. Qidiruvni
   `LANGUAGES`, `LOCALES`, `SUPPORTED_LANGUAGES`, `COURSE_V3_LANGUAGES`,
   `Literal["uz", "ru", "tj"]` va aniq til ro‘yxatlaridan boshla; bu misollar
   to‘liq avtomatik inventar o‘rnini bosmaydi.
5. Generatsiya, P0 va tegishli runtime/CI’dan tashqari yangi hisob va mavjud
   hisobda til tanlash/saqlash/qayta ochish, clientlar orasida sync,
   placeholder/plural, xatosiz render va mavjud offline fallback’ni tekshir.
   Android Direct/Play va Desktop macOS/Windows mosligi saqlansin.

## Main’ga olib o‘tishda

Qoida fayllari, ushbu yo‘riqnoma, canonical manbalar, generator/guard’lar,
consumer’lar, generated resurslar va regressiya testlari birgalikda saqlansin.
Faqat tayyor bundle’larni ko‘chirish yoki original source guard’larini tashlab
ketish mumkin emas. Kelajakdagi agent `AGENTS.md` / `AI_RULES.md` orqali shu
yo‘riqnomaga yetib kelishi kerak.

Merge konfliktida haqiqiy kod va eng yangi main diff’ini tekshir, tarjima
egalarini saqla, keyin qayta generatsiya va tegishli testlarni bajar. Release
uchun `.github/workflows/i18n-p0.yml` va ta’sirlangan Backend/Android/Desktop
CI natijalarini aynan chiqariladigan kod uchun tekshir; real bot/account/device
sinovini avvalgi fixture testi bilan almashtirma. Dars tartibi, Chinese/pinyin,
answer ID, grading, progress, auth, obuna, narx va entitlement mexanizmlarini
tarjima vazifasi sabab o‘zgartirma. Dars tarjimalari uchun
[`AI_CONTENT_QA_POLICY.md`](AI_CONTENT_QA_POLICY.md)dagi source-bound yo‘l amal
qiladi. Ushbu yo‘riqnoma main push yoki production deploy uchun yangi ruxsat
bermaydi; foydalanuvchining amaldagi branch/release cheklovi saqlanadi.

## Completed fixed-copy ownership

The full Desktop dictionary, Bot `TEXTS`/`COURSE_I18N`, all 36 native XML files,
fixed notification surfaces, public-page content, and all 18 registered Mini App
dictionaries have canonical sources. Bot ownership now includes **658 own
messages and 41 shared references per locale**, **98 static Bot maps**, **11
dynamic Bot templates**, profile templates, and **64 backend fixed maps**.
Entitlement text formatting resolves local display copy while retaining the
existing access decisions, limits and formatting values. Mini App inline/helper
maps resolve through the separate local Mini App namespace; legacy dictionaries
remain explicit compatibility fallbacks. The short active checkpoint is
`RESUME_NEXT_CHAT.md`; do not repeat completed UI.

The remaining **79 Python locale maps** are individually classified in
`review/ui_map_exceptions.json`. `scripts/i18n_ui_adoption_audit.py` checks their
content-free AST hashes and counts, rejecting new unclassified maps and stale
exceptions. A new learner-facing fixed-copy map belongs in its canonical
namespace rather than an exception. Learning material, graded data, dynamic
campaign content, admin-only copy and provider/locale metadata retain their
existing ownership.

Source-text tests must inspect effective generated catalogs when copy moves out
of a helper. Keep behavioral assertions for callbacks, access/advertising/payment
constants and thresholds; use actual local JavaScript execution where a source
substring no longer represents the delivered behavior.

Dynamic campaign/user/AI copy, Chinese course and graded answer data are not UI
catalogs. Preserve their existing producers, source hashes, access and identity.
Actual staging/accounts, installed clients and release authorization remain
separate from this deterministic source build. This ownership checkpoint does
not establish final CI success or real-account/device acceptance.
