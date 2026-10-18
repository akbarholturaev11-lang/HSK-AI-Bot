# Universal kirish: amaliy test

`codex/universal-sign-in` branch’i uchun. `main` va production release hold
saqlanadi. Kod testlari real Google/Apple, Telegram bot va o‘rnatilgan ilova
sinovining o‘rnini bosmaydi.

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
