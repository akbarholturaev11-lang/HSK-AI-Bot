# Release feedback draft — HSK AI Desktop 1.3

Bu draft deploydan keyin admin tasdig'isiz yuborilmaydi. Mavjud `Release
feedback` moduli orqali yuborish uchun tayyor.

## Release nomi

`HSK AI Desktop 1.3 — Mac/Windows, lokal AI va avtomatik yangilanish`

## Userga yuboriladigan qisqa matn

> 🐼 HSK AI endi Mac va Windows’da.
>
> Kurs, obuna va progressingiz Telegram bilan bitta hisobda qoladi. Ilovada
> internetsiz ishlaydigan ixtiyoriy lokal AI yordamchi va keyingi versiyalarni
> avtomatik o‘rnatish ham bor.
>
> `Sinab ko‘rish`ni bosing, Profil ichidan **Kompyuter ilovasi**ni oching va
> tizimingizga mos DMG yoki EXE’ni yuklang.
>
> Yangilikni 1–5 ball bilan baholang. Fikr qoldirsangiz va faol obunangiz
> bo‘lmasa, aytganimizdek sizga 24 soatlik 20% chegirma beriladi.

## Aynan nima yangilandi

- macOS universal DMG va Windows x64 EXE uchun bitta toza download oqimi;
- DMG/EXE bosilgach UZ/RU/TJ o‘rnatish qo‘llanmasi;
- Telegramda qo‘lda yoziladigan 8 belgili kod + alohida tasdiqlash;
- shu hisobdagi kurs, progress va obuna;
- ixtiyoriy lokal AI Pack, o‘rnatilgach AI chat internetsiz ishlaydi;
- idle holatda signed yangilanishni avtomatik o‘rnatish va restart.

## Qayerda sinash kerak

1. `Profil → Kompyuter ilovasi`.
2. Mac yoki Windows’ni tanlash.
3. Faylni o‘rnatib, ilovadagi kodni bot chatiga qo‘lda yuborish.
4. Kurs/progress/obunani tekshirish.
5. AI tugmasidan Local AI Pack’ni o‘rnatib, internetni uzgan holda savol berish.

## `Sinab ko‘rish` tugmasi

- `feature_key`: `profile`
- Modul avval botdagi Profilni ochadi.
- Profil klaviaturasidagi `Kompyuter ilovasi` Mini App’ni
  `tab=profile&desktop_download=1` bilan aynan download kartasiga olib boradi.
- Non-paid userga modulning mavjud qoidasi bo‘yicha 30 minut limitsiz test
  access beriladi.

## Baho va reward matni

- Baho: `1  2  3  4  5`
- 1–2 ball: qisqa izoh yoki screenshot majburiy.
- Oldindan aytiladigan reward: `Faol obunangiz bo‘lmasa, fikr qoldirgach 20%
  chegirma 24 soatga ochiladi.`
- Berilgandan keyingi tasdiq: `Rahmat. Aytganimizdek, sizga 24 soatlik 20%
  chegirma berildi.`

## Target segment

- `uz`, `ru`, `tj` tillari;
- oxirgi 30 kunda aktiv bo‘lgan userlar;
- birinchi yuborishda faol pullik obunachilarni chiqarib tashlash tavsiya
  etiladi, chunki download bepul va asosiy conversion — desktop install.

## Statsda kuzatiladigan metriclar

- campaign sent/delivered/try_clicked;
- 1–5 rating distribution va comment count;
- `desktop_download_requested` → `desktop_download_started`;
- `desktop_session_linked` → `desktop_first_open`;
- platform (`macos`/`windows`) va app version;
- DAU/WAU/MAU, `desktop_update_installed`;
- local AI Pack install/open/error eventlari;
- feedback discount offered/used.

## Admin yuborish gate'i

1. R2 manifest va ikkala installer public tekshiruvdan o‘tsin.
2. Railway download/update flaglari yoqilsin.
3. Clean Mac/Windows smoke-test yashil bo‘lsin.
4. Shundan keyin admin draftni ko‘rib `Release feedback` modulida tasdiqlaydi.
