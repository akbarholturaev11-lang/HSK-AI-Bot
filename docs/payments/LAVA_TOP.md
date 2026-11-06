# lava.top — HSK AI Pro'ning 2-yo'li (avtomatik obuna)

Holat (2026-11-06): kod `feat/lava-top-pro-payments-20261106` branchida.
Production'da standart holat **o'chiq** (`LAVA_ENABLED=false`, rejim
`manual_only`), shuning uchun hozirgi qo'lda yo'l o'zgarmaydi. Reja va
qarorlar: `openspec/changes/lava-top-pro-payments/`.

## Nima qiladi

- Qo'lda yo'l (rekvizit/QR → chek → admin) **o'zgarishsiz qoladi**.
- 2-yo'l: Visa/Mastercard bilan avto-obuna. Muddatlar 1, 3, 6, 12 oy
  (lava `MONTHLY`, `PERIOD_90_DAYS`, `PERIOD_180_DAYS`, `PERIOD_YEAR`; Pro
  30/90/180/365 kun).
- Admin rejimi:
  - `manual_only` — faqat oddiy yo'l;
  - `lava_only` — faqat lava;
  - `both` — checkout boshida markazda «Visa karta orqali to'laysizmi?»
    savoli chiqadi: «Ha» → lava, «Yo'q, mahalliy karta» → oddiy yo'l.
- Klientlar (1-bosqich): Telegram Mini App va iPhone PWA (umumiy
  `subscription.html`). Android direct va Desktop — 2-bosqich; ular lava'ni
  qo'llamaguncha server ularga `manual_only` beradi. Play'da hech qachon yo'q.
- HSK 3.0 unlock va chegirmali oqimlar har doim qo'lda yo'lda qoladi.

## Pul xavfsizligi qoidalari

1. Invoice'ni faqat server yaratadi; foydalanuvchi faqat biz saqlagan
   `contractId` (renewal'da `parentContractId`) orqali aniqlanadi. Email
   bo'yicha hech qachon bog'lanmaydi.
2. Webhook — faqat signal. Pro faqat `GET /api/v2/invoices/{id}` COMPLETED
   va valyuta mos bo'lganda beriladi; lava javob bermasa webhook 503 oladi
   (lava ~5 soat qayta yuboradi) va reconcile worker ham tekshiradi.
3. Har kontrakt bir marta qo'llanadi (`lava_invoices.contract_id` UNIQUE,
   `payment_id` UNIQUE, event `dedupe_key` UNIQUE, user → invoice → payment
   lock tartibi).
4. `Payment` qatori faqat tasdiqlash tranzaksiyasi ichida yaratiladi va
   umumiy `review_locked_payment` orqali tasdiqlanadi — admin navbatiga lava
   "pending" qatori hech qachon tushmaydi.
5. Bekor qilish (foydalanuvchi, admin, lava, renewal xatosi) `end_date`ni
   o'zgartirmaydi. Faqat **to'liq refund** va **chargeback** shu to'lov
   bergan kunlarni olib tashlaydi (`refunded` / `chargeback`). Partial yoki
   noaniq refund → admin tekshiruvi, access o'zgarmaydi.
6. Kill-switch: `LAVA_ENABLED=false` yoki rejim `manual_only` faqat yangi
   sotuvni to'xtatadi; olingan pullar (to'lov, renewal, refund) qayta
   ishlanadi. Favqulodda: `LAVA_PROCESSING_PAUSED=true` — eventlar `queued`
   bo'lib saqlanadi, pauza olingach bir marta qo'llanadi.

## Komponentlar

| Joy | Fayl |
| --- | --- |
| Sozlamalar/rejim | `app/services/lava/config.py` (`bot_settings[lava_top_config_v1]`) |
| API mijoz | `app/services/lava/client.py` |
| Ledger (berish/olib tashlash/tiklash) | `app/services/lava/ledger.py` |
| Webhook va eventlar | `app/services/lava/events.py`, `app/api/lava_checkout.py` |
| Checkout (start/status/cancel) | `app/services/lava/checkout.py` |
| Reconcile worker | `app/services/lava/reconcile.py` (lifespan, bitta lease) |
| Preflight | `app/services/lava/preflight.py`, `scripts/lava_preflight.py` |
| Admin PWA | `app/admin_api/pwa_lava.py`, Moliya → To'lov usullari → lava.top |
| Jadval | migratsiya `0151_lava_top_payments` (`lava_invoices`, `lava_webhook_events`) |

Endpointlar: `POST /api/payments/lava/webhook`,
`/api/subscription-miniapp/lava/{start,status,cancel}`,
`/api/v3/pwa/subscription/lava/{start,status,cancel}`, `GET /pay/lava/return`.

Xabarlar: tasdiq — mavjud yo'l (Telegram + Android FCM + iPhone PWA push).
Refund, renewal xatosi, bekor qilish, chargeback — Telegram (UZ/RU/TJ).
Admin alertlari — Telegram adminlariga va Admin PWA ro'yxatida.

Statistika: Admin PWA → Statistika → Moliya: "To'lov yo'llari" (oddiy vs
lava) va "lava.top avto-obuna" (faol, renewal, bekor, refund, chargeback).
Refund/chargeback to'lovlari daromadga kirmaydi.

## Joriy lava mahsuloti (2026-11-06 tekshirildi)

Sotuv havolasi: `https://app.lava.top/products/c696439c-b771-41fb-97fb-26ca0cc80c7f/c31f2e5a-68e9-4f8e-a299-a97dadc1706e`
(product `c696439c-…`, offer `c31f2e5a-68e9-4f8e-a299-a97dadc1706e`). Bitta offer
to'rtta davrni o'z ichiga oladi — Admin PWA'da 1/3/6/12 oyning hammasiga shu
offer tanlanadi:

| Muddat | USD | RUB |
| --- | --- | --- |
| 1 oy (MONTHLY) | 7.90 | 643.86 |
| 3 oy (PERIOD_90_DAYS) | 19.00 | 1548.51 |
| 6 oy (PERIOD_180_DAYS) | 34.90 | 2844.37 |
| 12 oy (PERIOD_YEAR) | 64.90 | 5289.40 |

Narxlar kasrli: `payments.amount` butun son bo'lgani uchun daromad, partner
komissiyasi va AI budjeti `app/services/payment_amounts.py` orqali aniq
`local_amount`dan hisoblanadi.

## Promokodlar (ilova chegirmalari)

- Admin PWA → lava.top sozlamalari → "Promokodlar": `referral:20`,
  `feedback_price_offer:20` va admin kampaniya foizlari uchun lava kodi.
- Chegirmani server o'zi hisoblaydi (mavjud `DiscountService`, metod `lava`).
  Mos kod bo'lsa, invoice `promoCode` bilan yaratiladi. Chegirma to'lov
  tasdiqlangandan keyingina "ishlatilgan" bo'ladi (referral/feedback/kampaniya
  qoidalari o'zgarmaydi).
- Kod yo'q bo'lsa, chegirmali oqim avvalgidek faqat oddiy yo'lda qoladi. Chegirma
  havolasi hech qachon jimgina to'liq narxga aylanmaydi (`discount_unavailable`).
- Renewal'lar chegirmasiz qayd qilinadi (lava qanday yechsa, shunday).
- **Xavf:** lava to'lov sahifasida xaridor o'zi kiritadigan "Промокод" maydoni
  bor. Kodlarni noyob qiling va lava kabinetida ishlatish limitini qo'ying.

## Egasi bajaradigan sozlash (staging'dan boshlab)

1. lava kabinetida **obuna** turidagi "HSK AI Pro ⭐️" mahsuloti, offer(lar)
   MONTHLY / PERIOD_90_DAYS / PERIOD_180_DAYS / PERIOD_YEAR narxlari bilan
   (tavsiya: USD). Profilda yashirish tavsiya etiladi.
2. Интеграции → API → API key. **Chatga yubormang**: Railway env
   `LAVA_API_KEY`ga o'zingiz qo'ying.
3. Tasodifiy webhook kaliti yarating (≤80 belgi), env `LAVA_WEBHOOK_SECRET`.
4. Интеграции → API → Добавить Webhook: URL
   `https://<domen>/api/payments/lava/webhook`, auth = "API key" (3-banddagi
   kalit), barcha 7 event.
5. `LAVA_ENABLED=true`, deploy.
6. Preflight: Admin PWA → lava.top sozlamalari (ulanish holati) yoki
   `python scripts/lava_preflight.py` (`--test-invoice-email` bilan checkout
   huquqi ham tekshiriladi; pul yechilmaydi).
7. Admin PWA'da muddatlarni yoqib, offer tanlang, rejimni `both` qiling.

## Staging qabul ssenariylari (main'dan oldin majburiy)

Real to'lovni egasi qiladi; server tomonini (log, DB qatorlari, end_date)
agent tekshiradi va dalilni `docs/payments/LAVA_TOP_STAGING_<sana>.md`ga
yozadi:

1. Preflight OK. 2. Muddat o'chirilsa ko'rinmaydi, yoqilsa qaytadi.
3. "Yo'q, mahalliy karta" → oddiy oqim o'zgarishsiz. 4. "Ha" → real to'lov →
Pro +30 kun, bitta `Payment(lava, approved)`. 5. iPhone PWA'da ham.
6. Webhook qayta yuborilsa — ikkinchi uzaytirish yo'q. 7. Webhook kaliti
noto'g'ri → reconcile ≤5 daqiqada beradi. 8. `LAVA_ENABLED=false` bilan
oldin yaratilgan invoice to'lansa ham Pro beriladi. 9. Pauza → navbat →
bir marta. 10. Avto-yangilashni o'chirish → `end_date` o'zgarmaydi.
11. To'liq refund → Pro qisqaradi.

Renewal va chargeback real sinab bo'lmaydi: unit/mock bilan qoplangan,
birinchi tabiiy renewal production'da kuzatiladi ("kutilgan renewal kelmadi"
alerti bor).

## Ochiq savollar (lava support)

- Chargeback yakuni (won/lost) haqida webhook bormi? Hozircha Admin PWA
  buyrug'i bilan yopiladi.
- Promokod renewal'larga ham ta'sir qiladimi? (3-bosqich promokodlar shunga
  bog'liq.)
- `GET /api/v1/subscriptions` dagi `id` = ota kontrakt id'mi? (kunlik
  "noma'lum obuna" sweep shu tasdiqlangach yoqiladi.)
