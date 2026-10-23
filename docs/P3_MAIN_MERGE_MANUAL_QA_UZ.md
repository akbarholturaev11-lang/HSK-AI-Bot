# Main bilan farq va merge’dan keyingi amaliy tekshiruv

## 1. Qaysi kod solishtirildi?

2026-10-23 kuni `git fetch origin`dan keyingi snapshot:

| Narsa | Tekshirilgan holat |
| --- | --- |
| `origin/main` | `dcd65418887502943067fe9320339eb5ba7a73bb` |
| Ish branch’i | `codex/p3-main-integration-20261020` |
| Solishtirilgan ish kodi | `a14e97ce6cb6c8a0f39d5f83251eeaaba8bb0985` |
| Orqada / oldinda | **0 / 610 commit**; main ish branch’ining ajdodi |
| Yakuniy farq | **408 fayl**; 95 520 qo‘shilgan, 4 368 o‘chirilgan qator |
| Asl `lesson_*.json` fayllari | O‘zgarmagan |
| `app/db/`, `alembic/`, `app/config.py` | Main bilan bir xil; bu farq yangi migratsiya qo‘shmaydi |
| Google/Apple kirish xizmatlari, asosiy subscription/payment xizmati | Main’da mavjud; bu branch ularni yangi funksiya sifatida kiritmaydi |
| WebGL Liquid Glass piloti | Olib tashlangan; main’da mavjud CSS navigatsiya saqlangan |

610 commit 610 ta mahsulot funksiyasi degani emas: bunda tarjima, test,
generator, audit va tarixiy merge/revert commitlari ham bor. Quyidagi ro‘yxat
yakuniy source farqiga asoslangan. Ushbu yo‘riqnomaning keyingi hujjat commiti
yuqoridagi ilova kodini o‘zgartirmaydi.

**Asosiy yangi imkoniyat:** matnni canonical manbada boshqarish va platformaga
mahalliy resurs qilib yetkazish. Mavjud ekranlarning ko‘pi qayta qurilmagan.
Qo‘shimcha xulq o‘zgarishlari: himoyalangan dars API’lari, tarjima overlay’i,
dars boshlash dalili, eskirgan kurs natijasini rad etish va receipt/concurrency
tuzatishlari. Ular uchun ham alohida sinovlar quyida bor.

## 2. Hozir nima tasdiqlangan?

Ilova kodi `a14e97ce` uchun GitHub natijalari:

- [P0 — SUCCESS, Python 3.11 va 3.14](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39891619141): har birida 460 test va read-only tekshiruvlar.
- [Backend — SUCCESS](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39891619275): `targeted-tests`, `miniapp-ui`, `native-postgres` uchalasi o‘tgan.
- Lokal: 53 generated artifact, 0 stale; original navigatsiya tekshiruvlari;
  real HTTP asset testlari; mavjud QA foydalanuvchisining imzolangan HTTP
  map so‘rovi va besh bo‘limi o‘tgan. Oxirgi browser sinovida Telegram SDK
  transporti almashtirilgan, API va DB haqiqiy bo‘lgan.

Bu natijalar quyidagi barcha qurilma va haqiqiy provider sinovlarini bajarilgan
deb belgilamaydi. Hozirgi Mac QA muhitida AI/provider OAuth kalitlari va real
to‘lov rekvizitlari ulanmagan, reminder scheduler’lari o‘chirilgan.

## 3. Sinovga tayyorlash

Agent/operator avval quyidagilarni tayyorlaydi:

1. Tekshiriladigan server va barcha o‘rnatiladigan client build’lari bir xil
   tekshirilgan kodga mos bo‘lsin. Faqat backend’ni yangilash Android/DMG/EXE
   ichidagi yangi UI resurslarini yangilamaydi.
2. Alohida QA hisoblar: eski progressli hisob, yangi beginner, Free, Trial,
   Pro, muddati tugagan va to‘lov ko‘rib chiqilayotgan hisob. HSK 3.0 uchun
   ruxsatli/ruxsatsiz hamda `nhsk2/16` va `/20` ochilgan test hisoblari.
3. Sinovdan oldin hisobning tili, kursi, yakunlangan darslari, XP, qolgan limit,
   Pro tugash sanasi va payment holatini qayd etsin. Tugagach shu raqamlar bilan
   solishtirilsin. Buni agent/operator oladi; foydalanuvchi SQL yozishi shart emas.
4. Har bir ekranni UZ → RU → TJ ketma-ketligida ko‘ring. Mini App’da iPhone
   Telegram va Android Telegram; Android’da Direct va Play; Desktop’da macOS
   va Windows alohida belgilansin. 320–390px ekran va dark/light tekshirilsin.
5. To‘lov approve/reject, limit o‘zgartirish, blocked hisob, buzilgan payload,
   parallel to‘lov va source-SHA buzish sinovlari QA muhitida bajariladi.
   Production’da eski haqiqiy hisoblarga kirish va mavjud holatni o‘qish bilan
   qisqa tekshiruv qilinadi.

**Natijani yozish:** `ID | qurilma/build | til | test hisob turi | oldingi/keyingi
raqamlar | PASS/FAIL | screenshot yoki xato`. Imzolar, tokenlar va chek rasmlari
umumiy hisobotga yozilmaydi. Quyidagi kataklar qo‘lda hali bajarildi degani emas.

## 4. Markazlashtirish: ekran va funksiya bo‘yicha

Har bir qatorni uch tilda bajaring. `undefined`, bo‘sh tugma, `{count}` kabi
to‘ldirilmagan shablon yoki eski til bilan aralashib qolish — FAIL.

| ID | Qaerga kirish va nima qilish | Kutilgan natija |
| --- | --- | --- |
| L01 | Bot’da `/start`, `/language`; tilni almashtiring, profil/kurs menyusini oching va Bot’ni qayta oching. Yangi test hisobida til → kurs → daraja tanlang. | Tanlangan til saqlanadi; til tugmasi daraja yoki rejimga aylanib ketmaydi; callback’lar avvalgidek ishlaydi. Agent eskirgan/noma’lum callback’ni ham tekshiradi: hisob/FSM o‘zgarmasligi kerak. |
| L02 | Mini App → Profil → Til: UZ/RU/TJ ni tanlab, ilovani yoping va qayta oching. Dars/XP/Pro raqamlarini oldingi holat bilan solishtiring. | Til qayta ochilganda tiklanadi; til o‘zgartirish progress yoki obunani o‘zgartirmaydi. Agent noto‘g‘ri til va noto‘g‘ri JSON uchun hisob tili saqlanib qolishini tekshiradi. |
| L03 | Mini App’da yangi onboarding, HSK 2.0/3.0 tanlash, daraja/maqsad tanlash, course map, dars modal oynasi va yakunlash oynasini oching. | Sarlavha, tanlov, Back/Continue, progress, sana/sonlar to‘liq ko‘rinadi. Tanlangan kurs ID’si va dars tartibi til bilan almashmaydi. |
| L04 | Mini App Mashq: lug‘at/so‘z mashqi, yodlash, tanish, talaffuz, xatolar, tayyor gaplar va test markazini oching. Bittadan mashq bajaring; gapni saqlang va qidiring. | Ko‘rsatma, to‘g‘ri/noto‘g‘ri javob, natija, empty/loading/retry va limit oynalari shu tilda. Savolning xitoychasi, javob identifikatori va berilgan ball tarjima sabab o‘zgarmaydi. |
| L05 | Voice/AI ekranlari: scenario, boshlash/tugatish, sozlamalar va limit/paywall oynasini oching. Provider sozlangan QA’da bitta qisqa javob/qo‘ng‘iroqni bajaring. | Boshqaruv matnlari tarjima qilingan; mavjud ruxsat, timeout va limit ishlaydi. UI lokalizatsiyasi AI yaratadigan har bir javobni oldindan tarjima qilib qo‘yish degani emas. |
| L06 | Mini App Profil, reyting, challenge/taklif, reklama, limit, checkout, shaxsiy chegirma, yordam va Desktop yuklash kartasini oching. Chek yuborishdan oldin checkout’ni bekor qilib, orqaga qayting. | Tugmalar to‘g‘ri oynaga olib boradi; narx/foiz/kun/ball joyiga haqiqiy qiymat chiqadi. Chek yubormasdan bekor qilish Pro’ni yoqmaydi yoki tasdiqlangan payment holatini yaratmaydi. |
| L07 | Bot’dagi kundalik mashq, quiz natijasi, profil, yordam, tarif/to‘lov, referral va qurilma ulash xabarlarini oching. Account deletion’ning tasdiqlashgacha bo‘lgan matnini ham ko‘ring. | Matnlar tanlangan tilda; dars/qism/ball/sana/hisob va qurilma nomlari to‘g‘ri. HTML belgilar buzilmaydi. Xabarni tarjima qilish ulash, referral yoki o‘chirish qoidalarini o‘zgartirmaydi. |
| L08 | Android Direct va Play’da tilni almashtirib onboarding, kurs/dars, quiz/skip-test, lug‘at/yozish, mashq, Voice, reyting, profil va limit oynalarini oching. Ilovani qayta ishga tushiring. | APK/AAB ichidagi mahalliy resurslar ishlaydi; kesilgan yoki bo‘sh yozuv yo‘q; TJ tanlovi Android `tg` resurslariga to‘g‘ri ulanadi. Profil bildirishnoma/privacy sozlamalarining mavjud yo‘li ishlaydi. |
| L09 | macOS va Windows’da tilni almashtiring. Kirish, yon menyu, kurs/dars, AI/Voice, profil, bildirishnoma va checkout oynalarini oching; dasturni qayta ishga tushiring. | Ikkala OS’da bir xil funksional natija; label/placeholder va accessibility nomlari yangilanadi. Desktop’ning lokal saqlangan tilini boshqa client avtomatik o‘zgartirishi shart deb qabul qilmang. |
| L10 | QA admin’da reminder matni preview’sini, payment/referral/discount xabarini uch tilda ko‘ring. So‘ng bitta test template/campaign uchun admin matnini yozib, preview’ni qayta oching. | Default matn local catalog’dan; admin/DB/campaign matni mavjud ustuvorlik bilan saqlanadi. Son, sana, foiz va havola to‘g‘ri. Scheduler o‘chiq Mac QA’da xabar avtomatik kelishini kutib PASS qo‘ymang. |
| L11 | Public sayt, `/apps` yoki download sahifasi, Mini App’dagi yuklash kartasi: uch til, OS tanlash, yuklash va qaytish yo‘lini ko‘ring. | UI matni local manbadan; real versiya/link/referral manzili avvalgidek. Public saytning o‘zi bu farqda yangi mahsulot funksiyasi emas. |
| L12 | Avval ochilgan ekran/UI resurslari yuklangach internetni uzing, keyin qayta ulang. Android/Desktop’da mavjud offline ekranlarini ham oching. | Yuklangan UI matni uchun har bir so‘zga server so‘rovi ketmaydi. Internet talab qiladigan yangi dars/AI/to‘lov uchun aniq mavjud offline/error holati bo‘ladi. To‘liq Mini App offline ta’limi qo‘shilgan deb baholamang. |
| L13 | Ruxsatli QA hisobda **HSK 3.0 → nHSK2 → 16- va 20-dars** grammatika misollarini uch tilda oching. Mini App, Android va Desktop’ni solishtiring; o‘tilgan darsni qayta ko‘ring. | Ilgari bo‘sh bo‘lgan tarjimalar chiqadi; xitoycha/pinyin o‘sha-o‘sha. Oddiy grammatika va `_grammar` kartasidagi bir xil misol tarjimasi mos. Review yangi dars limitini sarflamaydi, lekin account/track ruxsati tekshiriladi. |

L13 qamrovi: **136 noyob kontekst, 408 mustaqil UZ/RU/TJ qiymat, 48 dars,
272 original va 136 mirror display joyi**. Agent butun source/canonical mapping’ni
tekshiradi; 16/20 faqat amaliy namunalar. Foydalanuvchiga xitoy tili bo‘yicha
lingvistik tasdiqlash vazifasi yuklanmaydi.

### Markazlashtirishni kod orqali isbotlash — agent/operator

Ekranning tarjima qilingan ko‘rinishi o‘zi canonical manbaga ulanganini isbotlamaydi.

1. Alohida vaqtinchalik checkout’da amalda ishlatiladigan bitta `common` yoki
   `course` kalitini tanlang. Masalan, consumer mapping’ini tekshirib `action.back`.
2. UZ/RU/TJ canonical qiymatlariga vaqtinchalik `[QA]` belgisi qo‘shing;
   `python3 scripts/i18n_build_all_catalogs.py --write`ni bajaring.
3. Aynan shu kalitdan foydalanadigan Bot/Mini App/Android/Desktop consumer’larini
   qayta build/reload qilib belgini ko‘ring. Network’da alohida matn tarjima API’si
   bo‘lmasin. Bitta kalit har bir ekranga ulangan deb taxmin qilmang.
4. Vaqtinchalik o‘zgarishni o‘sha checkout’da olib tashlang, qayta generatsiya
   qiling; `--check` 0 stale qaytarsin. `[QA]` belgili resurs release’ga kirmasin.

Mualliflik manbalari va yangi til qo‘shish tartibi: [localization/README.md](../localization/README.md).
Generated fayllar matn yoziladigan manba emas. Public/native mavjud copy’ning
canonical joyga ko‘chishi yangi tarjima yoki yangi UI ekran qo‘shildi degani emas.

## 5. Dars, access va to‘lov mexanizmidagi farqlar

Quyidagi murakkab API/fixture holatlarini agent/operator bajaradi. Foydalanuvchi
oddiy boshlash/tugatish, qayta ochish va kurs almashtirish qismini sinashi mumkin.

| ID | Amaliy ssenariy | Kutilgan natija |
| --- | --- | --- |
| B01 | Ruxsatli hisob bilan odatiy yo‘ldan yangi darsni boshlang, so‘ng eski o‘tilgan darsni oching. Agent imzosiz, noto‘g‘ri hisob/kurs va qulflangan dars uchun content API’ni so‘rasin. | Ruxsatli dars ishlaydi; imzosiz 401, tegishli ruxsatsiz holat 403/404. `/course_v3_data/<level>/lesson_XX.json` endi 404. Xususiy javob `no-store`; darsning oddiy read so‘rovi limitni o‘zi sarflamaydi. Cheklangan yangi dars uchun avval ruxsatli start talab qilinishi mumkin. |
| B02 | Sales/paywall namunasi, yangi beginner foundation va qulflangan darsning skip-test yo‘lini oching. | Sales namuna ochiladi, to‘liq dars tarqalmaydi; foundation o‘zining kerakli qismini beradi. Skip-test ruxsatli kursda ko‘pi bilan 6 savol beradi; savollarni o‘qishning o‘zi dars ochmaydi yoki quota sarflamaydi. Oddiy full lesson hali sequence/access tekshiradi. |
| B03 | Darsni boshlang va odatiy yakunlang; javob kelishi kechiksa shu yakunlashni takrorlang. Agent begona/eskirgan/buzilgan completion proof bilan alohida urinadi. | Normal natija va progress saqlanadi; retry XP/progressni takror oshirmaydi; yaroqsiz proof yangi natija bermaydi. Proof darsga ruxsatli kirilganini bildiradi, har bir mashq serverda qayta baholandi degani emas. |
| B04 | Eski cache’li client yangi serverga ruxsatli `/lesson/start` qilgach proof maydonini yubormasdan tugatsin. Deploy’dan avval ochiq qolgan sessiyani ham alohida tekshiring. | Serverning oxirgi 24 soatlik shu hisob/kurs/dars start qaydi bilan eski client ishlaydi. Begona yoki eskirgan start dalili qabul qilinmaydi. Dalili yo‘q eski sessiyada yangidan ruxsatli start/reload zarur bo‘lishi mumkin; buni real yangilanish sinovida qayd eting, mavjud saqlangan progress yo‘qolmasin. |
| B05 | Foundation talab qilinadigan yangi beginner bilan uni tugatmasdan HSK1 dars start/complete/skip yo‘liga o‘tishga urining; keyin foundation’ni bajaring. | Oldin foundation ko‘rsatiladi: dars quota/XP/unlock yozilmaydi. Tugagach normal dars boshlanadi. Mavjud tajribali hisobga asossiz foundation qayta majburlanmaydi. |
| B06 | QA’da Free/Trial uchun admin sozlamasini limit=0, cheklangan qiymat va cheksiz holatga alohida tayyorlang. Yangi dars, o‘tilgan dars va Pro hisobni tekshiring. | Private API ham mavjud markaziy limit qaroriga amal qiladi. Cheksiz Free/Trial asossiz bloklanmaydi; tugagan limit yangi darsga yo‘l bermaydi; o‘tilgan review yangi quota yemaydi; Pro muddati/huquqi matn tarjimasi sabab o‘zgarmaydi. |
| B07 | HSK 3.0 bir martalik kirishi bor Free hisob, faol Pro va HSK 3.0 ruxsatsiz hisob bilan aynan bir xil yo‘llarni tekshiring. | Bir martalik track kirishi Free’ni Pro qilmaydi va dars limitini bekor qilmaydi. Ruxsatsiz track’da full content/review/skip orqali aylanib o‘tish bo‘lmaydi. Mustaqil amaldagi pulli huquq saqlanadi. |
| B08 | Yangilangan Mini App yoki Desktop’da A kurs darsini oching. Shu hisobning boshqa sessiyasida B kursga o‘ting. Eski A oynasidan start/complete/skip qiling. | Yangi kursga A natijasi yozilmaydi, XP/quota o‘zgarmaydi; mos endpoint `409 course_context_changed` beradi. Yangilab B kursga qaytiladi. Eski client’ning optional maydonni yubormasligi uchun mavjud compatibility alohida sinovdir. |
| B09 | A kursda bir necha dars tugating, B kursga o‘ting, A’ga qayting. Ikki sessiyada map refresh va kurs almashtirishni bir paytda takrorlang. Mini App hamda Android/Desktop umumiy map yo‘lini tekshiring. | Har kursning progressi tiklanadi; boshqa kursga qayta nomlanmaydi yoki nolga tushmaydi. Oddiy refresh dars yakunlamaydi/XP bermaydi. Parallel so‘rovlar yakuni serverdagi tanlangan kursga mos. |
| B10 | QA chekini yuboring; vaqtinchalik Pro holatini ko‘ring; approve va reject’ni alohida sinang. Keyin agent P1 eski pending chek, P2 yangi tasdiqlangan obuna va P1 qayta yuborish fixture’ini tayyorlasin. | Bitta o‘zgarmas chek ikkinchi vaqtinchalik Pro yoki AI budjeti bermaydi; yangi ticket’ni P1 yeb qo‘ymaydi. Reject preview’ni bekor qiladi; mustaqil amaldagi Pro/Trial huquqini buzmaydi. Eski takror budget yozuvlari yangi bepul cap yoki 500 yaratmasin. |
| B11 | Operator QA’da oldin bir ORM sessiyasi o‘qigan hisob uchun ikki ketma-ket 30 kunlik haqiqiy test-approval’ni mustaqil transaction’larda bajarsin. Alohida holatda hisobni boshqa transaction bloklasin. | Ikki to‘g‘ri renewal jami 60 kunni mavjud term qoidasi bo‘yicha qo‘shadi; eskirgan ORM ma’lumoti ikkinchi renewal’ni yo‘qotmaydi yoki bloklangan hisobni qayta yoqmaydi. Oddiy narx va 10/30/90 kunlik siyosat yangilanmagan. |
| B12 | Agent vaqtinchalik source nusxasida grammar source-SHA yoki himoyalangan xitoycha/answer maydonini o‘zgartirib overlay tekshiruvini bajarsin. Release source fayliga tegilmaydi. | Eskirgan tarjima boshqa manbaga yopishtirilmaydi; native’da mavjud original payload saqlanadi, Mini App patch qo‘llanmaydi. Original javob/grade/Pro maydonlari o‘zgarmaydi; normal source bilan tarjima yana ishlaydi. |

Free/Trial cheklangan yangi darsni boshlash, skip-test savollarini o‘qish va
o‘tilgan dars review’i uch xil amal. Ularning birida quota o‘zgarmasligi boshqasida
ham cheksiz kirish bo‘lishi kerak degani emas.

### Asosiy kod va avtomatik dalillar

| Qamrov | Source / regression |
| --- | --- |
| B01–B07, B12 | `app/api/miniapp_entitlements.py`, `app/main.py`, `app/services/course_p3_grammar_localization.py`; `tests/test_i18n_miniapp_reservation_asgi.py`, `tests/test_hsk30_lesson_limits.py`, `tests/test_i18n_native_grammar_localization.py` |
| B03–B05, B08 | `app/services/course_lesson_completion_proof.py`, `app/services/course_lesson_start_grant.py`; `tests/test_course_lesson_completion_proof.py`, `tests/test_miniapp_course_context.py` |
| B08–B09 | `app/api/desktop_course.py`, `app/services/desktop_course_service.py`, `desktop/ui/js/lesson.js`, `desktop/src-tauri/src/lib.rs`; `tests/test_desktop_course_api.py`, `tests/test_miniapp_course_map_concurrency.py` |
| B10–B11 | `app/services/payment_review_preview_service.py`, `app/services/ai_usage_budget_service.py`, `app/repositories/user_repo.py`; `tests/test_payment_review_preview.py`, `tests/test_subscription_service.py` |

## 6. Mavjud funksiyalarning saqlanganini tekshirish

Quyidagilar yangi funksiya deb sanalmaydi, lekin umumiy UI va dars yo‘llari
almashgani uchun tekshiriladi:

- Eski hisobga qayta kirish: o‘sha account ID, progress, Pro tugash sanasi va
  payment holati. Google/Apple hamda Telegram bilan bog‘lashning mavjud yo‘li
  real provider sozlangan QA’da sinaladi; hisoblar email o‘xshashligi sabab
  birlashmasin. Logout/account switch’da boshqa hisobning darsi chiqmasin.
- Bir quiz’da bitta to‘g‘ri va bitta noto‘g‘ri javob; gap terish, tinglash va
  mavjud homework submission yo‘li. Natija, xatolar va progress qayta ochilganda
  saqlansin; til almashtirish javob indekslarini o‘zgartirmasin.
- Mavjud referral havolasi, chegirma, Pro renewal/reject va HSK 3.0 kirishi;
  tegishli hisob va summaga yozilsin. Real karta bilan test to‘lov qilish shart emas.
- Telegram Back, darsdan chiqish tasdig‘i, beshta navigatsiya tugmasi, modal va
  safe area. Desktop kengligi 900/916/940/1280px’da oyna kesilmasin.
- Oddiy URL ham, eski `?liquid_glass=1` URL ham WebGL pilotni yuklamasin.
  Hozirgi main’dagi CSS navigatsiya qoladi.

Texnik izoh: Android `ProfileScreen.kt` farqida uchta qo‘shimcha private sheet
Composable ta’rifi bor; snapshot’da ularga chaqiruv joyi yo‘q. Ularni alohida
ishga tushgan yangi settings funksiyalari deb hisoblamang. Yuqoridagi sinov
haqiqiy mavjud profil/sozlamalar yo‘lini qamraydi.

## 7. Agent bajaradigan build, source va QA tekshiruvlari

Repo ildizidan, loyiha Python muhiti bilan:

```bash
python3 scripts/i18n_build_all_catalogs.py --check
python3 scripts/i18n_canonical_grammar_catalog.py
python3 scripts/i18n_baseline_guard.py --output /tmp/hsk-main-merge-baseline.json
python3 scripts/i18n_ui_adoption_audit.py --output /tmp/hsk-main-merge-adoption.json
python3 scripts/i18n_course_ui_catalog_guard.py --output /tmp/hsk-main-merge-course-ui.json
```

Kutilgan: 53 artifact / 0 stale; grammar 136 kontekst / 48 dars va 0 yozilgan
source fayli; frozen source/consumer guard’larida blocker yo‘q. Bular real qurilma
sinovining o‘rnini bosmaydi.

P0 va Backend workflow’lari aynan tekshiriladigan SHA’da bajarilib, natijasi
GitHub’dan o‘qilsin. Android va Desktop installer’lari o‘zgargan resurslar bilan
qayta build qilinib tegishli CI/OS tekshiruviga kiradi. Dokument-only keyingi
commit uchun avvalgi test natijasini kod o‘zgarmaganini tekshirib izohlash mumkin.

Yangi bo‘sh QA bazasi yaratilsa `scripts/qa_standalone_bootstrap.py` guard’lari
bilan, jumladan `notification_templates` mavjudligi tekshirilsin. Mavjud learner
yozuvli bazada bootstrap qayta bajarilmaydi. Bu ishlab turgan bazaga yangi
migratsiya kerak degani emas. Schema/backup/restore amali alohida operator ishidir.

Anonymous staging probe va access snapshot tartibi:
[I18N_P0_STAGING_ACCESS_RUNBOOK.md](I18N_P0_STAGING_ACCESS_RUNBOOK.md).
Uning eski holat yozuvlari o‘rniga current SHA/domen dalili olinadi. Probe’ning
default rejimi dry run; u haqiqiy request yuborilganini tasdiqlamaydi va faqat
ruxsatli staging hostname’larini qabul qiladi. Mac’ning vaqtinchalik tunneliga
moslashtirish uchun guard’ni chetlab o‘tmang.

## 8. Merge va deploy’dan keyingi qisqa tekshiruv

Bu hujjat merge bajarishga buyruq emas. Merge ruxsatidan keyin:

1. Remote main qayta olinadi. Yuqoridagi bazadan o‘zgargan bo‘lsa farq qayta
   ko‘riladi. Qaysi SHA merge/deploy bo‘lgani yoziladi.
2. Merge’dan keyingi source’da generator `--check` va tegishli CI tekshiriladi;
   backend haqiqatan shu SHA’dan yurayotgani tekshiriladi. Git merge bo‘lishi
   server yoki APK/DMG/EXE o‘zidan-o‘zi yangilandi degani emas.
3. Deploy’dan so‘ng `/health`, uch til, eski hisob/progress/Pro, bir normal
   dars start → natija, bir review va bir kurs almashtirish tekshiriladi.
4. Private lesson URL anonymous ochilmasligi va ruxsatli dars yo‘li ishlashi
   birga tekshiriladi. Faqat 404 ko‘rish ilova ishladi degani emas.
5. Joriy, eski cache’li client va yangilangan Android/ikkala Desktop’da
   yuqoridagi tegishli kataklar belgilanadi. Kuzatilgan xato va muvaffaqiyat
   bir xil build/SHA bilan qayd etiladi.

**To‘xtatish mezoni:** eski hisob/progress/Pro yo‘qolishi, noto‘g‘ri quota/XP,
begona yoki ruxsatsiz dars chiqishi, noto‘g‘ri payment egasi, normal darsni
tugatib bo‘lmasligi yoki buzilgan quiz javobi. Bunday holat PASS qilinmaydi;
avval sabab va tor fix topiladi.

Xitoycha tarjimani qayta ekspertizadan o‘tkazish agentning vazifasi bo‘lib qoladi.
Foydalanuvchining vazifasi — ko‘rinish va odatiy foydalanish natijasini aytish.

## 9. Merge uchun tayyorlangan PR

[Draft PR #198](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/198)
aynan `codex/p3-main-integration-20261020` → `main` uchun ochildi.
Oldingi #179 boshqa source branch’dan, #196 esa qaytarilgan WebGL pilotidan.

Tayyorlashda main yana `dcd65418` ekanligi tekshirildi. `git merge-tree
--write-tree` sinovi konfliktsiz; natija ish branch’i tree’siga teng. Ilova,
Android, Desktop, scripts/tests/workflow fayllari green Backend/P0 tekshirilgan
`a14e97ce` bilan aynan bir xil. `4c440bc5` documentation HEAD P0’si ham SUCCESS.
Keyingi tayyorgarlik qaydi ham faqat hujjat; PR checks alohida kuzatiladi.

Old main/source ref’lari va main tarixiga tayanuvchi incremental Git bundle
alohida lokal joyda saqlandi; `git bundle verify` o‘tdi. Foydalanuvchining
Graphify o‘zgarishlari commit’ga qo‘shilmadi. Bu Git recovery nusxasi database
backup’i emas; yangi DB migratsiyasi ushbu farqqa kirmaydi.

Merge bajariladigan paytdagi tartib:

1. PR HEAD va remote main qayta olinadi. Main yuqoridagi SHA’dan yoki PR HEAD
   tekshirilgan SHA’dan siljigan bo‘lsa, yangilangan merge natijasi va CI ko‘riladi.
2. PR checks xatosiz yakunlanishi tekshiriladi; Draft va auto-merge holati
   tayyorgarlikni bajarilgan release deb ko‘rsatish uchun o‘zgartirilmaydi.
   Main hozir protected emas, shuning uchun GitHub merge tugmasi ochiqligining
   o‘zi testlar o‘tganini bildirmaydi.
3. Railway live source binding tekshirildi: production’dagi **HSK AI** servisi
   aynan shu GitHub repo’ning `main` branch’iga ulangan (`checkSuites: false`),
   pending staged change yo‘q. Primary connector/CLI login’i eskirgan bo‘lsa-da,
   boshqa mavjud Railway ulanishi orqali faqat o‘qish bilan tasdiqlandi.
   Main merge/push avtomatik production deploy’ni ham boshlashi mumkin;
   chiqarish amali shu chegarani hisobga olishi kerak. Hech qanday live sozlama
   o‘zgartirilmadi. Repo’dagi Android release manual; Desktop release tag/manual.
4. Chiqarish amali berilganda history saqlanadigan merge commit ishlatiladi,
   aniq HEAD mosligi tekshiriladi; force/reset, branch delete yoki DB downgrade
   qo‘llanmaydi. Aloqasiz lokal o‘zgarishlar sabab main lokal dirty checkout’dan
   chiqarilmaydi.
5. Main ref o‘qilib haqiqiy merge SHA va birinchi parent’i yoziladi. Hozirgi P0
   va Backend push trigger’lari main’ni qamramaydi; merge’dan keyin zarur bo‘lsa
   ularning `workflow_dispatch` rejimi `--ref main` bilan ishga tushiriladi.
   Eski one-time `p3-integration-merge.yml` workflow’i promotion usuli emas.
6. Deploy’dan keyin 8-bo‘limdagi tekshiruvlar bajariladi. Qolgan real-device va
   provider ssenariylari bajarilmaguncha ular PASS deb belgilanmaydi.

Recovery kerak bo‘lsa haqiqiy main merge SHA uchun alohida tekshiriladigan
`git revert -m 1 <merge_SHA>` commiti tayyorlanadi. Learner/payment yozuvlari
orqaga qaytarilmaydi. To‘liq revert eski public lesson route’larini qaytarishi
mumkinligi ham tekshiriladi. Tayyorgarlik so‘rovi main’ga merge/deploy qilish
amali sifatida bajarilmagan.
