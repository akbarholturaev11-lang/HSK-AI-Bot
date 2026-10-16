# Release feedback draft — Android limits and panda reactions

Status: draft only. Do not send automatically; an admin must approve it in the
existing Release feedback module.

## Release name

Native Android — limit oynasi va 7 ta panda reaksiyasi

## User message

Limit tugaganda dars yoki mashq ichida blok tushunarli oynada chiqadi: nima
bloklangani, yangilanish vaqti va keyingi qadam ko‘rsatiladi. Android bosh
ekranidagi panda widgeti endi kun davomida 7 xil reaksiyani almashtiradi;
widget Telegram yoki Mini App emas, native HSK AI ilovasini ochadi.

## Sinab ko‘rish

Android ilova → Kurs → joriy darsni oching va bepul limitni tugating. Dars
xaritasi yoki darsning yakunida qizil limit oynasi chiqishi kerak. Mashqlar
bo‘limida xuddi shu hisob bilan test yoki Xatolarimni ochib ko‘ring. So‘ng
Profil → Sozlamalar → Panda bosh ekranda orqali widgetni qo‘shing va uni 2×1,
2×2 yoki 4×2 qilib torting.

`Sinab ko‘rish` tugmasi Android ilovasidagi Kurs ekranini ochadi; deep link
ishlamasa, yuqoridagi yo‘l ekranda ko‘rsatiladi.

## Baholash

1 dan 5 gacha baholang: “Limit tugaganda qaysi imkoniyat bloklanganini va
widgetdagi panda reaksiyalarini tushunish oson bo‘ldimi?”

## Mukofot (oldindan ko‘rsatiladi)

Baho va qisqa izoh qoldirgan foydalanuvchiga keyingi obuna uchun 10% chegirma
beriladi. Chegirma muddati va shartlari yuborishdan oldin admin tomonidan
tasdiqlanib ko‘rsatiladi.

Mukofot berilgandan keyin: “Rahmat. 10% chegirma mukofotingiz hisobingizga
qo‘shildi; amal qilish muddati profil yoki feedback oynasida ko‘rsatilgan.”

## Target segment

Android’dagi bepul/trial foydalanuvchilar, bugun kamida bitta dars yoki mashqni
boshlaganlar va native widgetni qo‘shgan yoki qo‘shishi mumkin bo‘lganlar.

## Statsda kuzatiladigan metriclar

- `android_limit_overlay_viewed` — dars va mashq bo‘yicha alohida;
- overlay → trial boshlash / obuna / support bosilishi;
- `android_widget_pin_requested`, `android_widget_pinned`,
  `android_widget_opened`;
- 7 reaksiya slotining ko‘rinish ulushi va widget tap → lesson start;
- feedback ko‘rish → yuborish, 1–5 baho, 10% reward redemption;
- limit API xato ulushi va overlaydan keyingi qayta urinish.

## Admin checklist

1. Limit oynasi dars yuklanishida ham, dars yakunida ham va barcha mashq
   kirishlarida ko‘rinishini tekshiring.
2. UZ/RU/TJ matnlarini va reset vaqtini tekshiring.
3. Widgetni launcherda 2×1, 2×2, 4×2 o‘lchamlarda, 09:00–19:00 slotlarda va
   slotdan tashqarida tekshiring; 20:00 reminder widget holatidan mustaqil.
4. Reward matni tasdiqlanmaguncha feedbackni yubormang.
