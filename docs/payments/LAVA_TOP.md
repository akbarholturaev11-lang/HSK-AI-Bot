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

## Regional checkout on PR #357

Ordinary checkout uses the learner's account-scoped device hint or saved region.
In `both`, Tajikistan and China prefer manual payment, Russia prefers verified
RUB, and Uzbekistan and Other prefer verified USD. The subscription screen has
no Other plans button: all enabled terms are visible in its plan grid, and
changing region recomputes its ordinary route without preserving a manual
alternative. Admin modes, provider availability, pending receipts and special
products retain their existing authority and safety rules. The Admin PWA signs the provider catalog
snapshots and validates them again on save. Older clients keep the configured
default currency. Google Play remains consumption-only.

The separate limit offer retains Other plans. Once its tariff is selected,
manual checkout proceeds to method selection when the authenticated overview
confirms that same sellable plan; it does not repeat the tariff screen. Missing
or invalid plans keep the canonical selection step. Lava proceeds to email,
or directly to the existing invoice start when a verified receipt email is known.

Admin PWA's existing currency selector supports USD, RUB, or USD + RUB.
The dual selection preserves the existing regional route: Russia prefers RUB,
Other prefers USD; it does not change the old default currency for clients
that omit currency. Legacy configs without `enabled_currencies` keep both.
A single-currency selection explicitly limits new invoices to that currency.

Prices for enabled offers/periods come from Lava's read-only product catalog,
not the stored Admin price snapshot. Successful results are cached per runtime
for 60 seconds; concurrent readers share one lookup with a 3-second whole-fetch
deadline and a 5-second failed-read backoff. No user/session/discount data is
cached. On the next checkout read after expiry, merchant price changes become
visible automatically without Admin Save. The offer selector already displays
live provider currencies; a price change alone is not an unsaved setting.
Settings edits retain signed catalog validation, revision checks and the exact
passkey-bound command.

Overview and invoice preparation close SQL before provider IO. Missing or
unavailable prices are never estimated, converted locally or replaced with an
expired snapshot. A catalog failure reports through the existing content-free
monitoring pipeline; no provider invoice is posted. The selected exact
subscription offer/period/currency must be priced. Actual created invoice totals
and verified webhook payments keep their existing authority; historical
invoice totals and currencies are never rewritten by a catalog refresh.
Implementation delta: `openspec/changes/lava-live-regional-pricing/`.

The checkout uses the authenticated account's most recent paid Lava receipt
email, then its linked, verified Google email. With either address, the learner
can proceed from the selected plan without entering an email. With neither,
checkout asks for an email. Email is receipt metadata. The verified canonical
user ID and contract ID continue to determine payment ownership.

The Pro expiry sheet uses a server-issued period notice. A cancelled Lava
subscription remains manageable through the paid period. After expiry its
historical management record no longer prevents a new checkout. Pending reviews,
unresolved invoices and active auto-renewals suppress the notice.

This describes the PR implementation. Live merchant catalog, receipt delivery
and real-device checkout still require isolated acceptance.

Local checkout refusals log only their typed error code and HTTP status. Provider
invoice failures separately log provider code/status/uncertainty. Neither log
contains request bodies, email, credentials, invoice IDs or provider responses.
A local 400 is not proof that Lava rejected an invoice; preserve the distinction
when diagnosing Profile versus limit entry paths. POST is never retried automatically.

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
