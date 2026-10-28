# Universal accounts — joriy arxitektura

**Holat (2026-10-27):** Universal account kodlari `main` da va Railway production deploy'ida mavjud. Avvalgi `codex/universal-sign-in` branch'i uchun yozilgan "main/production release hold" matni **tarixiy**, hozirgi ishga taqiq emas. Loyiha egasi Google/Apple real qurilma oqimlarini sinaganini tasdiqlagan. Bu yozuv yangi relizlarni testsiz chiqarish huquqini bermaydi.

Bu fayl eskirgan release reja + QA handoff + ownership audit hujjatlarining qisqa joriy texnik xulosasidir. Haqiqiy xatti-harakat uchun doim `main` kodi, migratsiya holati va tegishli testlarni tekshiring; bu snapshot 2026-10-27 dagi `2a2289b2` commit asosida yangilandi.

## 1. Bitta hisob, bir nechta kirish usuli

- **Canonical owner:** `users.id`. Pro, kurs progressi, XP, AI byudjeti, to'lov va taklif/chegirma kabi hisob ma'lumotlari shu identifikatorga tegishli.
- **Telegram:** `users.telegram_id` haqiqiy Telegram identifikatori; Google/Apple bilan ochilgan akkauntda `NULL` bo'lishi mumkin. `users.id` ni hech qachon soxta Telegram ID sifatida ishlatmang.
- **Google/Apple:** `user_identities` jadvali verified provider subject'ini `users.id` ga bog'laydi. Tasdiqlangan yangi provider subject yangi account ochishi mumkin; ma'lum subject eski egasiga qaytadi.
- **Account linking:** faqat autentifikatsiyadan keyin foydalanuvchining aniq roziligi bilan. Bir xil email yoki ism asosida akkauntlar **hech qachon avtomatik merge qilinmaydi**. Begona akkauntdagi Pro/progress boshqa egaga o'tkazilmaydi.
- **Blocked:** bloklangan canonical hisob yangi provider bilan cheklovni aylanib o'tmasligi kerak. Identity unlink boshqa sessiyalarni bekor qiladi, oxirgi yagona kirish usulini olib tashlashga yo'l qo'yilmaydi.
- **Telegram transport:** bot DM, Telegram tasdiqlashi, chat notifications va bot-referral hodisalari uchun faqat haqiqiy Telegram ID qo'llanadi; `telegram_id=NULL` bilan yuborilmaydi.

Manbalar:
- `app/db/models/user.py`, `app/db/models/user_identity.py`
- `app/services/account_identity.py`, `app/services/identity_link_service.py`
- `app/services/desktop_auth_service.py`, `app/services/native_oauth_service.py`
- `app/api/native_oauth.py`, `app/api/android_auth.py`, `app/api/desktop_auth.py`

## 2. Platformalar va sessiya

| Platforma | Amaldagi autentifikatsiya |
| --- | --- |
| Telegram bot | Bot orqali haqiqiy Telegram identity |
| Course Mini App | Telegram imzolagan `initData` |
| Android (Direct / Play) | Native device/session token va bog'langan identity |
| macOS / Windows | Native device/session token va bog'langan identity |
| Kelajakdagi iPhone Course PWA | **Hali joriy etilmagan.** Mustaqil browser login/session va Telegram login-handoff zarur |

Native Google/Apple **birinchi kirish** oqimi bilan Mini App'dagi mavjud Google/Apple **akkauntga bog'lash** oqimini adashtirmang. `/api/v3/native-auth/oauth/start` hozir Android/macOS/Windows uchun. `miniapp` platformasi identity link uchun mavjud, lekin browser sign-in session emas.

Kelajakdagi PWA uchun umumiy `users.id` va mavjud course/payment service'larini qayta ishlating. Browser sessiyasi, cookie/CSRF, login linking, mikrofon, push va sessiya tiklanishini alohida xavfsizlik hamda qurilma sinovidan o'tkazing. Telegram `initData` tekshiruvini olib tashlash yoki native tokenni browser localStorage'ga ko'chirish yechim emas.

## 3. Saqlanishi shart bo'lgan biznes qoidalar

- Subscription entitlement, 7 kunlik Pro trial, referral/feedback vaqtinchalik access, **pending receipt preview**, va bir martalik HSK 3.0 unlock — **bir-biridan farqli**; ularni bitta `isPro` qiymatiga birlashtirmang.
- Pullik Pro faqat haqiqiy tasdiqlangan payment bilan belgilanadi. `pending` receipt hech qachon sotuv yoki cheksiz AI byudjeti emas.
- `payments.user_id` — canonical moliyaviy owner; legacy `user_telegram_id` transport/metama'lumot. Refund/review, pending dedupe, ko'rilgan chek bonusini bir marta berish va retention qoidalari o'zgartirilmaydi.
- `course_progress.user_id`, `course_track_states.user_id`, XP, rating, mistakes, learning history umumiy akkauntga bog'liq. HSK 2.0/3.0 track va level transition nazorati serverda qoladi.
- Referral attribution `referrer_user_id` va `invited_user_id` bilan hisoblanadi; mavjud linkdan yangi signup yoki duplicate reward yaratilmaydi.
- Clientlar bitta access policy/limit engine orqali qaror olishi kerak; tilda va kanalda turlicha ko'rsatiladigan Pro/limit natijalari regressiya hisoblanadi.

Manbalar:
- `app/services/entitlements/`, `app/services/user_access_state_service.py`
- `app/services/subscription_miniapp_service.py`, `app/services/payment_review_preview_service.py`
- `app/services/course_track_service.py`, `app/services/course_gamification_service.py`
- `app/services/referral_service.py`, `app/repositories/payment_repo.py`

## 4. Migratsiya va tekshirish

2026-10-18/19 dagi universal-account migratsiya va legacy-data tekshiruvlari **tarixiy dalil**, faol release hold emas. Tegishli `0103`–`0108` Alembic migratsiyalarini va quyidagi dalil JSON'larini o'chirmang:

- `docs/UNIVERSAL_NATIVE_ACCOUNTS_STAGING_AUDIT_2026-10-18.json`
- `docs/UNIVERSAL_LEGACY_ACCOUNT_AUDIT_2026-10-19.json`
- `docs/UNIVERSAL_NATIVE_AUTH_CODE_CHECK_2026-10-18.json`
- Qolgan `docs/UNIVERSAL_NATIVE_ACCOUNTS_STAGING_*.json` va Telegram-link tarixiy dalillari.

Oldingi juda uzun planning/QA/audit Markdown'lar repo Git tarixidan tiklanadi. Ular ish tugagan branch holatini tasvirlaydi va bugungi release ko'rsatmasi sifatida ishlatilmaydi.

**Yangi o'zgarish uchun:** shu vaqtdagi `main` HEAD, production schema/migration state, regression tests, provider config va ayni klient oqimini alohida tekshiring. Hech qanday ishlab turgan hisob, Pro, progress, to'lov yoki identity yozuvi almashtirilmasin. Production'da test akkauntlar yaratmang.

Konfiguratsiya/redirect tafsilotlari: [`OAUTH_SETUP.md`](../OAUTH_SETUP.md).
