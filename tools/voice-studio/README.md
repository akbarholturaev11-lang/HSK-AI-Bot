# Ovoz — lokal matndan ovoz studiyasi

Ruscha va tojikcha kirill matnni WAV ovozga aylantiruvchi alohida lokal ilova. HSK bot backendiga ulanmaydi.

## Hozirgi Mac’da ochish

`Start.command` faylini ikki marta bosing. Brauzerda http://127.0.0.1:8766 ochiladi. Terminal oynasini ishlatish davomida ochiq qoldiring. To‘xtatish: Ctrl+C.

1. Tilni tanlang: Тоҷикӣ yoki Русский.
2. Matn kiriting (1500 belgigacha), tezlikni tanlang.
3. **Ovoz yaratish** → tinglang → **WAV faylni saqlash**.

Modellar bu kompyuterga o‘rnatilgan. Keyingi ovoz yaratish uchun internet, API kalit yoki kredit kerak emas. Har tilda bitta model ovozi mavjud. Sonlar va qisqartmalarni so‘z bilan yozish talaffuzni yaxshilaydi. Model inson diktori sifatini kafolatlamaydi.

## Boshqa kompyuterga o‘rnatish

Python 3.11 kerak. Mac: `Install.command`, keyin `Start.command`. Windows: `Install.bat`, keyin `Start.bat`. Windows uchun bir xil server va UI ishlatiladi, lekin Windows’da bajarib sinash imkoni bo‘lmadi. Birinchi o‘rnatish internetdan kutubxonalar va 2 ta modelni yuklaydi; yetarli disk joy ajrating (taxminan 1–2 GB).

## Litsenziya va cheklov

Meta MMS modellari **CC BY-NC 4.0**: shaxsiy/notijoriy foydalanish. Ushbu variantni tijoriy reklama ovozi uchun tavsiya qilmaymiz. Litsenziya ilovada ham ko‘rsatiladi. Modellar:
- https://huggingface.co/facebook/mms-tts-tgk
- https://huggingface.co/facebook/mms-tts-rus

## Tuzilishi

- `server.py`: faqat loopback API, token bilan POST himoyasi, bitta faol job, 180 soniya timeout.
- `worker.py`: alohida jarayonda offline inference; uzun matn bo‘laklari; tezlik; 16-bit WAV.
- `download_models.py`: bir martalik, aniq revisionlarga bog‘langan model yuklash.
- `static/`: tashqi CDN ishlatmaydigan brauzer interfeysi.
- `.models/`, `.venv/`: lokal model va kutubxonalar, Git’dan chiqarilgan.
- `outputs/`: audio va metadata; kerak bo‘lsa Finder’dan fayllarni o‘zingiz boshqarasiz. Avtomatik o‘chirilmaydi.
- Matn qoralamasi brauzer localStorage’ida saqlanadi; **Tozalash** tugmasi uni olib tashlaydi.

Server matnni tashqi servisga yubormaydi. Worker modelni faqat diskdan yuklaydi (`HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, `local_files_only`).

## Tekshiruvlar

Mac’da ikki tilda haqiqiy WAV, input validation, parallel so‘rovni rad etish, UI orqali yaratish/yuklash, 390px mobil ko‘rinish va JS xatolari tekshirildi. Namunalar `outputs/sample-tj.wav`, `outputs/sample-ru.wav`.

Server ishlaganda API testi: `.venv/bin/python tests/smoke.py`. Browser testi Playwright o‘rnatilgan Python bilan: `python tests/browser.py`.
