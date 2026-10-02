"""Reviewed public copy. Never derive marketing claims from user statistics."""

DOWNLOAD_PATH = "/download"

# Legal notices are kept outside PAGES so they are not treated as marketing pages.
GOOGLE_SIGNIN_PRIVACY_PAGES = {
    "/privacy/google-sign-in/": {
        "lang": "uz",
        "title": "Google bilan kirish maxfiyligi — HSK AI",
        "description": "HSK AI Google bilan kirishida qaysi ma’lumotlar ishlatilishi haqida maxfiylik eslatmasi.",
        "updated": "23 sentyabr 2026",
        "h1": "Google bilan kirish: maxfiylik eslatmasi",
        "intro": "Bu eslatma HSK AI’da Google bilan kirish yoki Google hisobini mavjud HSK AI hisobiga ulash uchun qo‘llanadi.",
        "sections": [
            ("Qaysi ma’lumot ishlatiladi", "Google tasdiqlagan hisob identifikatori, email manzili, email tasdiqlanganligi holati va profil nomi olinadi. Bu ma’lumot Google bilan kirish va qaysi HSK AI hisobiga bog‘langanini ko‘rsatish uchun kerak."),
            ("Hisoblar qanday bog‘lanadi", "Google email manzili orqali HSK AI hisobi qidirilmaydi va hisoblar birlashtirilmaydi. Google profili faqat foydalanuvchining aniq harakati bilan, avval Telegram orqali yaratilgan HSK AI hisobiga ulanadi."),
            ("Nima saqlanadi", "Google hisobining barqaror identifikatori kalitli HMAC ko‘rinishida saqlanadi. Bog‘langan hisob uchun email, email tasdiqlanganligi, profil nomi hamda ulash va oxirgi kirish vaqtlari saqlanishi mumkin."),
            ("Tokenlar va tashqi xizmatlar", "Google access va refresh tokenlari saqlanmaydi; HSK AI foydalanuvchi nomidan Google API’lariga murojaat qilmaydi. Google autentifikatsiyasi Google orqali, ilova esa HSK AI texnik infratuzilmasi orqali qayta ishlanadi."),
            ("Sizning tanlovingiz", "Google bilan kirishdan foydalanmaslik mumkin. Bog‘lanishni HSK AI profilidagi Sozlamalar → Kirish usullari orqali uzish mumkin; bu boshqa qurilmalardagi sessiyalarni ham yakunlaydi. Savollar uchun Telegram’dagi @darsi_chini_bot ga yozing."),
        ],
    },
    "/privacy/google-sign-in/ru/": {
        "lang": "ru",
        "title": "Конфиденциальность входа через Google — HSK AI",
        "description": "Уведомление HSK AI о данных, используемых при входе через Google.",
        "updated": "23 сентября 2026",
        "h1": "Вход через Google: конфиденциальность",
        "intro": "Это уведомление относится к входу через Google в HSK AI и к привязке Google-аккаунта к существующему аккаунту HSK AI.",
        "sections": [
            ("Какие данные используются", "Мы получаем подтверждённые Google идентификатор аккаунта, email, статус подтверждения email и имя профиля. Эти данные нужны для входа через Google и отображения связанного аккаунта HSK AI."),
            ("Как связываются аккаунты", "Мы не ищем аккаунт HSK AI по Google email и не объединяем аккаунты по email. Профиль Google можно привязать только явным действием пользователя к уже созданному через Telegram аккаунту HSK AI."),
            ("Что хранится", "Стабильный идентификатор Google-аккаунта хранится в виде HMAC с секретным ключом. Для привязанного аккаунта могут храниться email, статус его подтверждения, имя профиля, а также время привязки и последнего входа."),
            ("Токены и внешние сервисы", "Google access- и refresh-токены не хранятся; HSK AI не обращается к Google API от имени пользователя. Аутентификация проходит через Google, а работа приложения обрабатывается технической инфраструктурой HSK AI."),
            ("Ваш выбор", "Вход через Google необязателен. Связь можно отключить в HSK AI: Профиль → Настройки → Способы входа; это завершит сессии на других устройствах. По вопросам напишите в Telegram-бот @darsi_chini_bot."),
        ],
    },
    "/privacy/google-sign-in/tj/": {
        "lang": "tg",
        "title": "Махфияти воридшавӣ бо Google — HSK AI",
        "description": "Огоҳиномаи HSK AI дар бораи маълумоте, ки ҳангоми воридшавӣ бо Google истифода мешавад.",
        "updated": "23 сентябри 2026",
        "h1": "Воридшавӣ бо Google: махфият",
        "intro": "Ин огоҳинома барои воридшавӣ бо Google ба HSK AI ва пайваст кардани ҳисоби Google ба ҳисоби мавҷудаи HSK AI мебошад.",
        "sections": [
            ("Кадом маълумот истифода мешавад", "Мо шиносномаи тасдиқшудаи ҳисоби Google, email, ҳолати тасдиқи email ва номи профилро мегирем. Ин маълумот барои воридшавӣ бо Google ва нишон додани ҳисоби пайвастшудаи HSK AI лозим аст."),
            ("Чӣ гуна ҳисобҳо пайваст мешаванд", "Мо ҳисоби HSK AI-ро аз рӯйи Google email ҷустуҷӯ ё якҷо намекунем. Профили Google танҳо бо амали ошкори корбар ба ҳисоби HSK AI, ки пештар тавассути Telegram сохта шудааст, пайваст мешавад."),
            ("Чӣ нигоҳ дошта мешавад", "Шиносномаи доимии ҳисоби Google ба шакли HMAC бо калиди махфӣ нигоҳ дошта мешавад. Барои ҳисоби пайвастшуда email, ҳолати тасдиқи он, номи профил ва вақти пайвастшавӣ ё воридшавии охирин нигоҳ дошта шуда метавонанд."),
            ("Токенҳо ва хизматрасониҳои беруна", "Google access ва refresh token-ҳо нигоҳ дошта намешаванд; HSK AI аз номи корбар ба Google API муроҷиат намекунад. Тасдиқи шахсият тавассути Google ва кори барнома тавассути инфрасохтори техникии HSK AI анҷом меёбад."),
            ("Интихоби шумо", "Воридшавӣ бо Google ҳатмӣ нест. Пайвастро дар HSK AI аз Профил → Танзимот → Роҳҳои воридшавӣ ҷудо кардан мумкин аст; ин сессияҳоро дар дастгоҳҳои дигар ҳам анҷом медиҳад. Барои саволҳо ба Telegram-боти @darsi_chini_bot нависед."),
        ],
    },
}

PAGES = {
    "/": {
        "lang": "tg", "title": "HSK AI — омӯзиши забони чинӣ ва HSK",
        "description": "Забони чиниро бо курсҳои HSK 1–4, машқ ва шарҳи AI омӯзед. HSK AI дастгирии тоҷикӣ, русӣ ва ӯзбекиро дар Telegram Mini App пешниҳод мекунад.",
        "h1": "Забони чиниро қадам ба қадам омӯзед",
        "intro": "HSK AI курси пайдарпайи забони чинӣ, машқи луғат ва саволу ҷавоби AI-ро дар Telegram Mini App муттаҳид мекунад. Шарҳҳоро ба тоҷикӣ, русӣ ё ӯзбекӣ интихоб кунед.",
        "sections": [
            ("Аз курси HSK оғоз кунед", "Боти @darsi_chini_bot-ро кушоед ва ба Mini App гузаред. Дарсҳои HSK 1–4 калима, грамматика, гуфтугӯ ва санҷишро ба ҳам мепайванданд."),
            ("Шарҳро бо забони худ хонед", "Тоҷикӣ, русӣ ё ӯзбекиро интихоб кунед. Иероглиф, пинйин ва тарҷума ба шумо калимаро хондан, шунидан ва маънояшро санҷидан кӯмак мекунанд."),
            ("Бо AI ва овоз машқ кунед", "Дар бораи калима ё ҷумла саволи мушаххас диҳед, намунаи талаффузро гӯш кунед ва ҷавобро бо маводи дарс муқоиса намоед."),
            ("Барномаи мувофиқро интихоб кунед", "Telegram Mini App роҳи оғози курс аст. Барои рӯйхати барномаҳо ва файлҳои дастрас ба саҳифаи зеркашии HSK AI гузаред."),
        ],
    },
    "/tj/": {
        "lang": "tg", "title": "Омӯзиши забони чинӣ ба тоҷикӣ — HSK AI",
        "description": "Забони чиниро ба тоҷикӣ бо HSK AI омӯзед: курсҳои HSK 1–4, шарҳи AI, машқи талаффуз, луғат ва тестҳо дар Telegram Mini App.",
        "h1": "Забони чиниро ба тоҷикӣ омӯзед",
        "intro": "HSK AI — платформаи омӯзиши забони чинӣ бо ёрии AI барои омӯзандагони тоҷикзабон. Дарсро хонед, маъноро ба тоҷикӣ фаҳмед ва баъд бо ҷумлаи худ машқ кунед. Русӣ ва ӯзбекӣ низ дастгирӣ мешаванд.",
        "sections": [
            ("Курсҳои HSK 1–4", "Курсҳо калима, грамматика ва гуфтугӯро бо машқ мепайванданд. Дар HSK 1 аз ибораҳои сода оғоз кунед; барои идомаи омӯзиш маводи HSK 2, HSK 3 ва HSK 4 мавҷуд аст. Пешрафти дарсҳо дар барнома нишон дода мешавад."),
            ("AI барои фаҳмидани дарс", "Дар саволу ҷавоб аз AI шарҳи калима ё ҷумла пурсед. Барои талаффуз намунаи овозиро гӯш кунед ва такрор намоед; дар машқи овозӣ гуфтугӯ кунед. AI метавонад хато кунад: ҷавоби шубҳанокро бо маводи дарс ё омӯзгор санҷед."),
            ("Санҷиш ва такрор", "Тестҳо, луғат ва бахши хатоҳо барои мустаҳкам кардани мавод ҳастанд. Танҳо тарҷумаро аз ёд накунед: калимаро дар ҷумла истифода баред ва рӯзи дигар бе нигоҳ кардан ба ҷавоб такрор кунед."),
            ("Чӣ тавр оғоз кардан мумкин аст?", "Боти @darsi_chini_bot-ро кушоед, забонро интихоб кунед ва курси Mini App-ро оғоз намоед. Дастрасии ройгон маҳдудиятҳои рӯзона дорад; шартҳои ҷории обуна ва дастрасӣ дар бот нишон дода мешаванд."),
        ],
    },
    "/ru/": {
        "lang": "ru", "title": "Китайский язык и курсы HSK — HSK AI",
        "description": "Изучайте китайский по курсам HSK 1–4, практикуйтесь с AI и повторяйте слова. HSK AI поддерживает русский, таджикский и узбекский в Telegram Mini App.",
        "h1": "Учите китайский шаг за шагом",
        "intro": "HSK AI объединяет последовательный курс китайского языка, практику лексики и ответы AI в Telegram Mini App. Выберите объяснения на русском, таджикском или узбекском.",
        "sections": [
            ("Начните с курса HSK", "Откройте @darsi_chini_bot и перейдите в Mini App. Уроки HSK 1–4 объединяют лексику, грамматику, диалоги и задания."),
            ("Читайте объяснения на своём языке", "Выберите русский, таджикский или узбекский. Иероглиф, пиньинь и перевод помогают прочитать новое слово, услышать его и проверить значение."),
            ("Практикуйтесь с AI и аудио", "Задавайте конкретные вопросы о словах и предложениях, слушайте образец произношения и сверяйте ответы с уроком."),
            ("Выберите способ обучения", "Начать курс можно в Telegram Mini App. Список доступных приложений и файлов находится на отдельной странице загрузки HSK AI."),
        ],
    },
    "/uz/": {
        "lang": "uz", "title": "Xitoy tili va HSK kurslari — HSK AI",
        "description": "Xitoy tilini HSK 1–4 kurslari bilan o‘rganing, AI yordamchida mashq qiling va so‘zlarni takrorlang. HSK AI o‘zbek, rus va tojik tillarini qo‘llaydi.",
        "h1": "Xitoy tilini bosqichma-bosqich o‘rganing",
        "intro": "HSK AI xitoy tili kursi, lug‘at mashqlari va AI savol-javobini Telegram Mini App’da birlashtiradi. O‘zbekcha, ruscha yoki tojikcha izohlarni tanlang.",
        "sections": [
            ("HSK kursidan boshlang", "@darsi_chini_bot botini oching va Mini App’ga o‘ting. HSK 1–4 darslari lug‘at, grammatika, dialog va topshiriqlarni birlashtiradi."),
            ("Izohlarni o‘z tilingizda o‘qing", "O‘zbek, rus yoki tojik tilini tanlang. Iyeroglif, pinyin va tarjima yangi so‘zni o‘qish, tinglash va ma’nosini tekshirishga yordam beradi."),
            ("AI va audio bilan mashq qiling", "So‘z yoki gap haqida aniq savol bering, talaffuz namunasini tinglang va javobni dars bilan solishtiring."),
            ("O‘rganish usulini tanlang", "Kursni Telegram Mini App’da boshlash mumkin. HSK AI ilovalari va yuklab olish fayllari alohida sahifada berilgan."),
        ],
    },
    "/tj/hsk/": {
        "lang": "tg", "title": "HSK ба тоҷикӣ: курсҳои HSK 1–4 — HSK AI",
        "description": "Барои омӯзиши HSK ба тоҷикӣ аз куҷо оғоз кунем? Роҳнамои интихоби маводи HSK 1–4, машқи калимаҳо ва такрори дарсҳо дар HSK AI.",
        "h1": "HSK ба тоҷикӣ: роҳи омӯзиш аз дарс то машқ",
        "intro": "HSK AI барои омӯзиши забони чинӣ маводи HSK 1–4 дорад. Ин саҳифа ба интихоби роҳи омӯзиш кумак мекунад; он тавсифи расмии имтиҳон ё ваъдаи гирифтани сертификат нест.",
        "sections": [
            ("HSK 1: асосҳоро мустаҳкам кунед", "Агар нав оғоз карда бошед, ба пинйин, оҳангҳо ва ҷумлаҳои кӯтоҳ диққат диҳед. Калимаи навро танҳо нахонед: онро гӯш кунед, такрор кунед ва бо маънояш пайваст намоед. Салом додан ва худро шинос кардан барои машқи аввал муносибанд."),
            ("HSK 2: аз калима ба ҷумла", "Пеш аз маводи нав санҷед, ки оё бе нигоҳ кардан ба тарҷума ҷумлаи сода сохта метавонед. Барои машқ як хабарро ба савол табдил диҳед, шахс ё вақтро иваз кунед ва фарқи маъноро шарҳ диҳед."),
            ("HSK 3: матнро бо маъно хонед", "Ҳангоми хондани гуфтугӯ аввал мавзӯъро фаҳмед, баъд калимаҳои ношиносро ҷудо кунед. Ҳар ҷумларо калима ба калима тарҷума накунед. Дар охир мазмунро бо чанд ҷумлаи кӯтоҳи худ бозгӯ кунед."),
            ("HSK 4: истифодаи дақиқтар", "Дар маводи HSK 4 ба интихоби калима ва робитаи ҷумлаҳо диққат диҳед. Ду ҷумлаи монандро муқоиса кунед: чаро дар яке ин калима муносиб аст? Барои ҷавоб аз мисолҳои дарс ва шарҳи AI истифода баред, сипас худатон мисол нависед."),
            ("Реҷаи такрор", "Пешниҳод: аввал маводи дирӯзаро бе ҷавоб бинед, баъд як қисми дарсро гузаред ва дар охир хатоҳоро таҳлил кунед. Дар HSK AI тестҳо, луғат, пешрафт ва такрори хатоҳо мавҷуданд. Суръатро ба фаҳмиши худ мувофиқ кунед."),
            ("Курсро дар куҷо кушоем?", "Дар @darsi_chini_bot ба Telegram Mini App гузаред. HSK AI тоҷикӣ, русӣ ва ӯзбекиро дастгирӣ мекунад. Дастрасии ҳар бахш ва шартҳои ҷорӣ дар бот нишон дода мешаванд."),
        ],
    },
    "/tj/learn-chinese/": {
        "lang": "tg", "title": "Омӯзиши забони чинӣ аз сифр ба тоҷикӣ — HSK AI",
        "description": "Забони чиниро аз сифр оғоз кунед: пинйин, оҳангҳо, иероглиф ва ҷумлаи аввал. Роҳнамои кӯтоҳи тоҷикӣ бо намуна ва машқи мустақилона.",
        "h1": "Забони чиниро аз сифр чӣ гуна омӯзем?",
        "intro": "Дар оғоз се чизро якҷо омӯзед: садо, шакли иероглиф ва маъно. HSK AI — платформаи AI барои омӯзандагони тоҷикзабон — барои ин кор курсҳои HSK 1–4 ва машқҳоро дар Telegram пешниҳод мекунад.",
        "sections": [
            ("Пинйинро ҳамчун роҳнамои садо истифода баред", "Пинйин навишти талаффуз бо ҳарфҳои лотинӣ аст. Он тарҷума нест ва талаффузаш ҳамеша ба хондани ҳарфи лотинӣ дар тоҷикӣ монанд нест. Намунаи овозиро гӯш кунед ва баъд аз рӯйи пинйин такрор намоед."),
            ("Оҳанг ҷузъи калима аст", "Дар чинии мандарин чор оҳанги асосӣ ва оҳанги бетараф ҳаст. Масалан, 妈 — mā — модар; 马 — mǎ — асп. Аломати болои садонокро нодида нагиред. Аввал ҳар калимаро ҷудо, баъд дар ҷумла гӯш кунед."),
            ("Иероглиф, пинйин ва маъно", "Барои ҳар калима се сутун созед: иероглиф, пинйин, маънои тоҷикӣ. Як сутунро пӯшонда, аз хотир ҷавоб диҳед. Агар танҳо пинйинро хонед, шинохтани худи иероглифро алоҳида машқ кунед."),
            ("Ҷумлаи аввалро тағйир диҳед", "Намуна: 我学中文。 — Wǒ xué Zhōngwén. — Ман забони чинӣ меомӯзам. Барои савол зарраи 吗 — ma-ро дар охир илова кунед: 你学中文吗？ — Nǐ xué Zhōngwén ma? — Оё ту забони чинӣ меомӯзӣ? Ба ҷойи танҳо аз ёд кардан, фарқи ду ҷумларо фаҳмонед."),
            ("Машқи кӯтоҳи ҳаррӯза", "Пешниҳод: чанд дақиқа шунидан, як қисми дарс, баъд як ҷумлаи мустақилона. Рӯзи дигар аз хотир такрор кунед. Дар HSK AI луғат, тестҳо, машқи талаффуз ва пешрафт ҳастанд; AI барои саволҳо кумак мекунад. Русӣ ва ӯзбекӣ низ дастгирӣ мешаванд."),
        ],
    },
    "/tj/ai-chinese-teacher/": {
        "lang": "tg", "title": "Ёрдамчии AI барои забони чинӣ ба тоҷикӣ — HSK AI",
        "description": "Аз AI барои омӯзиши чинӣ чӣ гуна истифода барем? Намунаи саволҳо ба тоҷикӣ, таҳлили ҷумла, машқи овозӣ ва санҷидани ҷавобҳои AI дар HSK AI.",
        "h1": "Ёрдамчии AI барои фаҳмидан ва машқ кардани чинӣ",
        "intro": "HSK AI омӯзиши пайдарпайро бо саволу ҷавоби AI мепайвандад. Барои омӯзандагони тоҷикзабон, бо дастгирии русӣ ва ӯзбекӣ. AI ба дарс кумак мекунад; ҷои омӯзгор ё санҷиши мустақили донишро пурра намегирад.",
        "sections": [
            ("Саволи мушаххас диҳед", "Ба ҷойи «грамматикаро фаҳмон», ҷумла ва мушкили худро нависед. Масалан: «Дар ҷумлаи 我学中文。 — Wǒ xué Zhōngwén. — Ман забони чинӣ меомӯзам, тартиби калимаҳоро ба тоҷикӣ шарҳ деҳ». Баъд як мисоли ҳамсатҳ пурсед."),
            ("Аввал кӯшиши худро нишон диҳед", "Худатон ҷумла созед ва баъд пурсед: «Хатои ҷумлаам дар куҷост? Сабабро фаҳмон ва ба ман як машқи монанд деҳ». Бо ин роҳ шарҳ ба мушкили шумо дахл дорад. Ҷавоби тайёрро нусхабардорӣ накунед; ҷумлаи ислоҳшударо аз хотир нависед."),
            ("Овозро ба маъно пайваст кунед", "Дар машқи талаффуз аввал намунаро гӯш кунед, баъд такрор кунед. Барои гуфтугӯи AI мавзӯи шинос интихоб кунед: шиносоӣ, хӯрок ё нақшаи рӯз. Бо ҷумлаҳои кӯтоҳи сатҳи худ оғоз кунед ва калимаҳои курси охиринро истифода баред."),
            ("Ҷавобро санҷед", "AI метавонад тарҷума, оҳанг ё қоидаи грамматикаро нодуруст шарҳ диҳад. Агар ҷавоб ба маводи дарс мувофиқ набошад, аз омӯзгор ё манбаи боэътимод санҷед. Хатои шинохти овозро ҳамеша хатои дониши худ ҳисоб накунед."),
            ("Ба курс баргардед", "Пас аз саволу ҷавоб як машқи мустақилона кунед. Дар HSK AI курсҳои HSK 1–4, луғат, тестҳо, такрор ва пешрафт мавҷуданд. Барои оғоз @darsi_chini_bot-ро кушоед ва ба Telegram Mini App гузаред; лимит ва шартҳои дастрасӣ дар бот нишон дода мешаванд."),
        ],
    },
}


def _page(lang, group, content_group, title, description, h1, intro, sections):
    return {
        "lang": lang,
        "translation_group": group,
        "content_group": content_group,
        "title": title,
        "description": description,
        "h1": h1,
        "intro": intro,
        "sections": sections,
    }


PAGES.update({
    "/uz/hsk/": _page(
        "uz", "hsk", "hsk",
        "HSK imtihoniga tayyorgarlik: HSK 1–4 — HSK AI",
        "HSK 1–4 ni o‘zbek tilida o‘rganish: darslar, lug‘at, grammatika va mashqlar. HSK AI kurslari Telegram Mini App’da.",
        "HSK 1–4 ni bosqichma-bosqich o‘rganing",
        "HSK AI’da xitoy tilini darajalar bo‘yicha o‘rganish uchun HSK 1–4 kurs materiallari bor. Dars, mashq va takrorni bir tartibda olib boring; imtihon natijasi kafolatlanmaydi.",
        [
            ("HSK 1: asoslardan boshlang", "Pinyin, ohanglar va kundalik iboralarni o‘rganing. Yangi so‘zni tinglang, ieroglifini ko‘ring va tarjimasini eslab, oddiy gapda ishlating."),
            ("HSK 2: gap tuzishni mashq qiling", "Tanish so‘zlarni yangi vaziyatda ishlating. Gapdagi shaxs yoki vaqtni almashtirib, ma’no qanday o‘zgarishini tekshiring."),
            ("HSK 3: matnni mazmuni bilan o‘qing", "Avval dialogning umumiy mazmunini tushuning, so‘ng notanish so‘zlarni ajrating. Oxirida fikrni o‘z so‘zlaringiz bilan qayta ayting."),
            ("HSK 4: aniqroq ifoda qiling", "O‘xshash so‘z va gaplarni dars misollari bilan taqqoslang. AI izohidan yordam sifatida foydalaning va o‘zingiz yangi misol tuzing."),
            ("Dars va takrorni bog‘lang", "Mini App’da darslarni ketma-ket o‘ting, testlarni bajaring va xatolarga qayting. Mavjud darajalar hamda kirish shartlari ilovaning o‘zida ko‘rsatiladi."),
        ],
    ),
    "/ru/hsk/": _page(
        "ru", "hsk", "hsk",
        "Подготовка к HSK: уровни 1–4 — HSK AI",
        "Изучайте HSK 1–4 с уроками, лексикой, грамматикой и практикой. Курсы HSK AI открываются в Telegram Mini App.",
        "Изучайте HSK 1–4 последовательно",
        "В HSK AI есть материалы курсов HSK 1–4. Связывайте уроки, практику и повторение; платформа не гарантирует результат экзамена.",
        [
            ("HSK 1: начните с основ", "Изучайте пиньинь, тоны и повседневные фразы. Слушайте новое слово, смотрите иероглиф, вспоминайте перевод и используйте слово в коротком предложении."),
            ("HSK 2: практикуйте построение фраз", "Используйте знакомую лексику в новой ситуации. Меняйте в предложении человека или время и проверяйте, как меняется смысл."),
            ("HSK 3: читайте, понимая содержание", "Сначала уловите общий смысл диалога, затем разберите незнакомые слова. В конце перескажите содержание своими словами."),
            ("HSK 4: выражайте мысли точнее", "Сравнивайте похожие слова и предложения на примерах из урока. Используйте объяснение AI как подсказку и составьте собственный пример."),
            ("Связывайте урок и повторение", "Проходите уроки в Mini App по порядку, выполняйте тесты и возвращайтесь к ошибкам. Доступные уровни и условия доступа показаны в приложении."),
        ],
    ),
    "/uz/learn-chinese/": _page(
        "uz", "learn-chinese", "learn-chinese",
        "Xitoy tilini noldan o‘rganish — HSK AI",
        "Xitoy tilini noldan boshlang: pinyin, ohanglar, ierogliflar va sodda gaplar. O‘zbek tilidagi tavsiyalar va HSK AI kurslari.",
        "Xitoy tilini noldan qanday o‘rganish kerak?",
        "Boshida tovush, ieroglif va ma’noni birga o‘rganing. HSK AI darslari xitoy tilini HSK 1–4 bosqichlari bo‘yicha o‘rganish va mashq qilishga yordam beradi.",
        [
            ("Pinyin talaffuzga yo‘l ko‘rsatadi", "Pinyin xitoycha tovushlarni lotin harflarida ko‘rsatadi; u tarjima emas. Harfni o‘qish bilan cheklanmay, audio namunani tinglang va takrorlang."),
            ("Ohangni ham eshiting", "Mandarin tilida ohang so‘z ma’nosini o‘zgartirishi mumkin. Avval bo‘g‘inlarni alohida tinglang, keyin ularni gap ichida qayta mashq qiling."),
            ("Iyeroglif, pinyin va tarjima", "Har bir yangi so‘zni uch tomondan eslab qoling: ieroglifini taning, pinyinini ayting va ma’nosini tushuntiring. Bir ustunni yopib, javobni xotiradan toping."),
            ("Birinchi gapni o‘zgartirib ko‘ring", "我学中文。 — Wǒ xué Zhōngwén. — Men xitoy tilini o‘rganyapman. Shu gapni savolga aylantiring yoki undagi so‘zlardan birini almashtiring."),
            ("Qisqa mashqni odat qiling", "Bir darsni o‘ting, bir necha so‘zni takrorlang va mustaqil gap tuzing. HSK AI’da kurs, lug‘at, testlar va talaffuz mashqlari mavjud; kirish shartlari ilovada ko‘rsatiladi."),
        ],
    ),
    "/ru/learn-chinese/": _page(
        "ru", "learn-chinese", "learn-chinese",
        "Как начать учить китайский язык — HSK AI",
        "Начните с нуля: пиньинь, тоны, иероглифы и простые фразы. Практические советы и курсы HSK AI.",
        "Как учить китайский язык с нуля?",
        "С самого начала связывайте звучание, иероглиф и значение. Уроки HSK AI помогают изучать китайский по уровням HSK 1–4 и сразу переходить к практике.",
        [
            ("Пиньинь помогает услышать произношение", "Пиньинь записывает китайские звуки латинскими буквами, но не является переводом. Слушайте аудиообразец и повторяйте, а не полагайтесь только на чтение."),
            ("Слушайте тоны", "В китайском языке тон может менять значение слова. Сначала слушайте слоги отдельно, затем повторяйте их в коротких фразах."),
            ("Иероглиф, пиньинь и перевод", "Запоминайте новое слово с трёх сторон: узнавайте иероглиф, произносите пиньинь и вспоминайте значение. Закройте один столбец и проверьте себя."),
            ("Измените первую фразу", "我学中文。 — Wǒ xué Zhōngwén. — Я учу китайский. Попробуйте превратить фразу в вопрос или заменить в ней одно слово."),
            ("Занимайтесь небольшими подходами", "Пройдите урок, повторите несколько слов и составьте собственную фразу. В HSK AI есть курсы, словарь, тесты и упражнения на произношение; условия доступа показаны в приложении."),
        ],
    ),
    "/uz/ai-chinese-teacher/": _page(
        "uz", "ai-teacher", "ai-teacher",
        "Xitoy tilini o‘rganishda AI yordamchi — HSK AI",
        "Xitoycha so‘z va gaplarni AI yordamchiga qanday tushuntirish mumkin? Namuna savollar, ovozli mashq va javobni tekshirish bo‘yicha yo‘riqnoma.",
        "AI yordamchi bilan xitoy tilini tushuning va mashq qiling",
        "HSK AI kurs darslarini AI savol-javobi bilan birlashtiradi. Yordamchidan aniq so‘z, gap yoki xato haqida so‘rang; AI javobini dars bilan tekshirib boring.",
        [
            ("Savolni aniq bering", "Faqat «grammatikani tushuntir» demang. Xitoycha gapni yuboring va qaysi qismi tushunarsizligini yozing: «我学中文 jumlasidagi so‘z tartibini tushuntir» kabi."),
            ("Avval o‘zingiz urinib ko‘ring", "O‘z gapingizni yozib, xatoni va sababini so‘rang. Keyin o‘xshash mashq so‘rab, tuzatilgan gapni xotiradan qayta yozing."),
            ("Ovoz bilan mashq qiling", "Talaffuz bo‘limidagi namunani tinglang va takrorlang. Ovozli suhbatda qisqa va tanish mavzudan boshlang; kerakli funksiya ilovadagi tegishli bo‘limda ochiladi."),
            ("Javobni tekshiring", "AI ba’zan tarjima, ohang yoki grammatikani noto‘g‘ri izohlashi mumkin. Shubhali javobni dars materiali yoki o‘qituvchi bilan solishtiring."),
            ("Mashqni kursga qaytaring", "AI izohidan keyin shu mavzuga oid testni bajaring yoki o‘zingiz yangi gap tuzing. Bepul foydalanish limitlari va obuna shartlari ilovada ko‘rsatiladi."),
        ],
    ),
    "/ru/ai-chinese-teacher/": _page(
        "ru", "ai-teacher", "ai-teacher",
        "AI-помощник для изучения китайского — HSK AI",
        "Как спрашивать AI о китайских словах и предложениях: примеры запросов, голосовая практика и проверка ответов.",
        "Разбирайте китайский и практикуйтесь с AI-помощником",
        "HSK AI объединяет последовательные уроки с вопросами к AI. Спрашивайте о конкретном слове, предложении или ошибке и сверяйте ответ с материалом урока.",
        [
            ("Задавайте конкретный вопрос", "Вместо общего «объясни грамматику» отправьте китайское предложение и укажите, что именно непонятно: например, попросите разобрать порядок слов в 我学中文。"),
            ("Сначала попробуйте сами", "Напишите собственную фразу, затем спросите, где ошибка и почему. Попросите похожее упражнение и попробуйте восстановить исправленное предложение по памяти."),
            ("Практикуйте произношение", "Слушайте аудиообразец в разделе произношения и повторяйте. В голосовом разговоре начните с короткой знакомой темы; функция открывается в соответствующем разделе приложения."),
            ("Проверяйте ответы", "AI иногда ошибается в переводе, тонах или грамматике. Сомнительное объяснение сравните с уроком или уточните у преподавателя."),
            ("Возвращайтесь к курсу", "После объяснения выполните тест по теме или составьте собственную фразу. Бесплатные лимиты и условия подписки показаны в приложении."),
        ],
    ),
    "/tj/guide/": _page(
        "tg", "guide", "guide",
        "Роҳнамои истифодаи HSK AI — курс, AI ва обуна",
        "Роҳнамои HSK AI ба тоҷикӣ: аз куҷо оғоз кардан, чӣ гуна истифода бурдани курс ва AI, ва чӣ гуна харидани обуна.",
        "Роҳнамои HSK AI",
        "Дар ин ҷо тарзи оғоз, истифодаи курс ва функсияҳо, инчунин қадамҳои обуна шарҳ дода мешаванд. Шартҳои дастрасӣ ва нархи ҷорӣ ҳамеша дар худи барнома нишон дода мешаванд.",
        [
            ("Оғоз ва омӯзиш", "Боти @darsi_chini_bot-ро кушоед, забонро интихоб кунед ва ба Telegram Mini App гузаред. Барои омӯзиши пайдарпай аз курси дастрас оғоз кунед."),
            ("Курс ва функсияҳо", "Дарсҳо луғат, грамматика ва машқро мепайванданд. Тестҳоро анҷом диҳед, талаффузро машқ кунед ва ба хатоҳо баргардед."),
            ("Обуна ва пардохт", "Муддатро интихоб кунед, нархи дар экрани пардохт нишон додашударо бинед ва танҳо бо реквизитҳои ҳамон экран пардохт кунед. Расиди пардохт барои санҷиш фиристода мешавад."),
        ],
    ),
    "/ru/guide/": _page(
        "ru", "guide", "guide",
        "Руководство HSK AI: курс, функции и подписка",
        "Руководство HSK AI на русском: с чего начать, как пользоваться курсом и AI, как оформить подписку и подтвердить оплату.",
        "Руководство HSK AI",
        "Здесь собраны инструкции по началу обучения, курсу и функциям, а также по оформлению подписки. Актуальные условия доступа и цены всегда отображаются в приложении.",
        [
            ("Начало обучения", "Откройте бота @darsi_chini_bot, выберите язык и перейдите в Telegram Mini App. Для последовательного обучения начните с доступного вам курса."),
            ("Курс и функции", "Уроки объединяют лексику, грамматику и практику. Выполняйте тесты, тренируйте произношение и возвращайтесь к ошибкам."),
            ("Подписка и оплата", "Выберите срок, проверьте цену на экране оплаты и используйте только показанные там реквизиты. Для проверки потребуется отправить подтверждение платежа."),
        ],
    ),
    "/uz/guide/": _page(
        "uz", "guide", "guide",
        "HSK AI qo‘llanmasi: kurs, funksiyalar va obuna",
        "HSK AI o‘zbekcha qo‘llanmasi: boshlash, kurs va AI funksiyalaridan foydalanish, obunani olish va to‘lovni tasdiqlash.",
        "HSK AI qo‘llanmasi",
        "Bu bo‘limda o‘qishni boshlash, kurs va funksiyalardan foydalanish hamda obuna olish tartibi tushuntiriladi. Joriy kirish shartlari va narx ilovaning o‘zida ko‘rsatiladi.",
        [
            ("O‘qishni boshlash", "@darsi_chini_bot botini oching, tilni tanlang va Telegram Mini App’ga o‘ting. Ketma-ket o‘rganish uchun o‘zingizga ochiq kursdan boshlang."),
            ("Kurs va funksiyalar", "Darslarda lug‘at, grammatika va mashqlar birlashadi. Testlarni bajaring, talaffuzni mashq qiling va xatolaringizga qayting."),
            ("Obuna va to‘lov", "Muddatni tanlang, to‘lov oynasidagi narxni tekshiring va faqat o‘sha yerda ko‘rsatilgan rekvizitlardan foydalaning. To‘lovni tekshirish uchun chek rasmi yuboriladi."),
        ],
    ),
    "/tj/guide/features/": _page(
        "tg", "guide-features", "features",
        "Курс ва функсияҳои HSK AI чӣ гуна кор мекунанд?",
        "Тарзи истифодаи дарсҳо, луғат, тестҳо, такрори хатоҳо, AI ва машқи талаффуз дар HSK AI.",
        "Курс ва функсияҳоро чӣ гуна истифода барем?",
        "HSK AI барои пайвастани дарс ва машқи мустақилона сохта шудааст. Функсияҳои дастрас ба ҳисоб ва шартҳои ҷорӣ вобастаанд; онҳоро дар барнома бинед.",
        [
            ("Дарсҳои HSK 1–4", "Аз курси дастрас оғоз кунед ва дарсҳоро пайдарпай гузаред. Дар мавод калимаҳо, грамматика, гуфтугӯ ва супоришҳо ҳастанд."),
            ("Калимаро бо се ҷузъ омӯзед", "Иероглифро бинед, пинйинро гӯш кунед ва маъниро ба тоҷикӣ, русӣ ё ӯзбекӣ фаҳмед. Баъд тарҷумаро пӯшонда, калимаро аз хотир ба ёд оред."),
            ("Машқ ва тест", "Супоришро дар дохили дарс иҷро кунед ва натиҷаро фиристед. Агар хато кунед, тест ё дарси мувофиқро такрор кунед."),
            ("Аз AI шарҳ пурсед", "AI-ро дар бораи калима, сохти ҷумла ё хатои худ пурсед. Саволи мушаххас диҳед; ҷавоби шубҳанокро бо дарс ё омӯзгор санҷед."),
            ("Талаффуз ва пешрафт", "Намунаи овозиро гӯш кунед ва такрор намоед. Пешрафт ва бахши хатоҳо барои дидани мавзӯъҳои гузашта кӯмак мекунанд; мавҷудияти баъзе функсияҳо метавонад аз дастрасии ҳисоб вобаста бошад."),
        ],
    ),
    "/ru/guide/features/": _page(
        "ru", "guide-features", "features",
        "Как работают курс и функции HSK AI?",
        "Как пользоваться уроками, словарём, тестами, повторением ошибок, AI-помощником и практикой произношения в HSK AI.",
        "Как пользоваться курсом и функциями?",
        "HSK AI помогает связывать урок с самостоятельной практикой. Доступные функции зависят от аккаунта и текущих условий; проверьте их в приложении.",
        [
            ("Курсы HSK 1–4", "Начните с доступного курса и проходите уроки последовательно. В материалах есть лексика, грамматика, диалоги и задания."),
            ("Учите слово в трёх формах", "Посмотрите на иероглиф, прослушайте пиньинь и разберите перевод на таджикском, русском или узбекском. Затем закройте перевод и вспомните значение."),
            ("Упражнения и тесты", "Выполните задание в уроке и отправьте результат. Если ошиблись, повторите тест или соответствующий урок."),
            ("Попросите AI объяснить", "Задавайте вопросы о слове, порядке слов или собственной ошибке. Чем конкретнее вопрос, тем полезнее ответ; сомнительное объяснение сверьте с уроком или преподавателем."),
            ("Произношение и прогресс", "Слушайте образец и повторяйте. Прогресс и раздел ошибок помогают вернуться к пройденному; доступность отдельных функций может зависеть от аккаунта."),
        ],
    ),
    "/uz/guide/features/": _page(
        "uz", "guide-features", "features",
        "HSK AI kursi va funksiyalari qanday ishlaydi?",
        "HSK AI’da dars, lug‘at, test, xatolarni takrorlash, AI yordamchi va talaffuz mashqlaridan foydalanish bo‘yicha qo‘llanma.",
        "Kurs va funksiyalardan qanday foydalaniladi?",
        "HSK AI darsni mustaqil mashq bilan bog‘lashga yordam beradi. Hisobingiz uchun ochiq funksiyalar va joriy shartlarni ilovada tekshiring.",
        [
            ("HSK 1–4 kurslari", "Siz uchun ochiq kursdan boshlang va darslarni ketma-ket o‘ting. Materiallarda so‘zlar, grammatika, dialoglar va topshiriqlar bor."),
            ("So‘zni uch tomondan o‘rganing", "Iyeroglifni ko‘ring, pinyinini tinglang va o‘zbekcha, ruscha yoki tojikcha ma’nosini tushuning. Keyin tarjimani yopib, ma’noni xotiradan eslang."),
            ("Mashqlar va testlar", "Dars ichidagi topshiriqni bajaring va natijani yuboring. Xato qilsangiz, testni yoki shu mavzudagi darsni qayta ko‘ring."),
            ("AI’dan izoh so‘rang", "So‘z, gap tartibi yoki o‘zingiz qilgan xato haqida savol bering. Savol qanchalik aniq bo‘lsa, javob shunchalik foydali; shubhali izohni dars yoki o‘qituvchi bilan tekshiring."),
            ("Talaffuz va o‘zlashtirish", "Audio namunani tinglab takrorlang. O‘zlashtirish holati va xatolar bo‘limi o‘tilgan mavzularni qayta ko‘rishga yordam beradi; ayrim funksiyalar hisobdagi kirish shartlariga bog‘liq bo‘lishi mumkin."),
        ],
    ),
    "/tj/guide/subscription/": _page(
        "tg", "guide-subscription", "subscription",
        "Чӣ гуна обунаи HSK AI-ро харидан мумкин аст?",
        "Қадамҳои харидани обунаи HSK AI: интихоби муҳлат, дидани нархи ҷорӣ, пардохт, фиристодани расид ва тасдиқ.",
        "Обуна чӣ гуна гирифта мешавад?",
        "Обуна дар боти HSK AI кушода мешавад. Муҳлат, нарх ва усули пардохти дастрасро пеш аз пардохт дар экрани барнома санҷед; нархи собитро аз ин саҳифа гирифта нашавад.",
        [
            ("Обуна ва муҳлатро кушоед", "Ба @darsi_chini_bot дароед, аз профил бахши обунаро кушоед ва яке аз муҳлатҳои дастрасро интихоб кунед: 10 рӯз, 1 моҳ ё 3 моҳ."),
            ("Нарх ва роҳи пардохтро бинед", "Нарх мувофиқи танзимоти ҷорӣ ва кишвари пардохт нишон дода мешавад. Барои корт ё Alipay/WeChat танҳо маълумот ва QR-и дохили экрани пардохтро истифода баред; имконот аз минтақа вобастаанд."),
            ("Расиди пардохтро фиристед", "Пас аз пардохт акси расидро дар ҳамин раванд бор кунед. То ҳалли дархости интизорӣ пардохти нав нафиристед; система метавонад дар як вақт пардохти дигари интизориро қабул накунад."),
            ("Тасдиқро интизор шавед", "Расид аз тарафи админ дастӣ санҷида мешавад. Пас аз тасдиқ обуна фаъол мегардад; бот натиҷаи санҷишро хабар медиҳад."),
            ("Оё обуна худкор тамдид мешавад?", "Не. Барои гирифтани муҳлати нав, онро аз нав интихоб карда, пардохтро алоҳида анҷом диҳед."),
            ("Тамдид ва кушодани HSK 3.0", "Агар обунаи пулакӣ ҳоло фаъол бошад, муҳлати нав ба охири муҳлати мавҷуда илова мешавад. Якбор кушодани HSK 3.0 маҳсулоти алоҳида аст ва бо обуна омехта намешавад."),
        ],
    ),
    "/ru/guide/subscription/": _page(
        "ru", "guide-subscription", "subscription",
        "Как оформить подписку HSK AI?",
        "Пошаговая инструкция: выбрать срок подписки HSK AI, проверить актуальную цену, оплатить, отправить чек и дождаться подтверждения.",
        "Как оформить подписку?",
        "Оформление подписки открывается в боте HSK AI. Перед оплатой проверьте срок, актуальную цену и доступный способ платежа на экране приложения; фиксированные цены на этой странице не указаны.",
        [
            ("Откройте подписку и выберите срок", "Перейдите в @darsi_chini_bot, откройте подписку из профиля и выберите доступный срок: 10 дней, 1 месяц или 3 месяца."),
            ("Проверьте цену и способ оплаты", "Цена рассчитывается по текущим настройкам и стране оплаты. Для карты или Alipay/WeChat используйте только реквизиты и QR-код, показанные на экране оплаты; доступность зависит от региона."),
            ("Отправьте подтверждение платежа", "После оплаты загрузите фотографию чека в том же процессе. Не отправляйте новый платёж, пока предыдущий запрос ожидает проверки: система может не принять второй ожидающий платёж."),
            ("Дождитесь проверки", "Администратор проверит чек вручную. После подтверждения подписка активируется; бот сообщит результат проверки."),
            ("Подписка продлевается автоматически?", "Нет. Чтобы получить новый срок, выберите его и оплатите отдельно."),
            ("Продление и HSK 3.0", "Если платная подписка ещё действует, новый срок добавляется к её текущей дате окончания. Разовая разблокировка HSK 3.0 оформляется отдельно и не является подпиской."),
        ],
    ),
    "/uz/guide/subscription/": _page(
        "uz", "guide-subscription", "subscription",
        "HSK AI obunasini qanday olish mumkin?",
        "HSK AI obunasini olish bo‘yicha qadamlar: muddat va joriy narxni ko‘rish, to‘lov, chekni yuborish va tasdiqni kutish.",
        "Obuna qanday olinadi?",
        "Obuna HSK AI botida rasmiylashtiriladi. To‘lovdan oldin ilova oynasida muddat, joriy narx va siz uchun ochiq to‘lov usulini tekshiring; aniq narx shu qo‘llanmada belgilanmaydi.",
        [
            ("Obunani ochib, muddatni tanlang", "@darsi_chini_bot botiga kiring, profildan obuna bo‘limini oching va mavjud muddatlardan birini tanlang: 10 kun, 1 oy yoki 3 oy."),
            ("Narx va to‘lov usulini tekshiring", "Narx joriy sozlamalar va to‘lov mamlakatiga qarab ko‘rsatiladi. Karta yoki Alipay/WeChat uchun faqat to‘lov oynasidagi rekvizit va QR’dan foydalaning; usullar hududga qarab farq qiladi."),
            ("To‘lov chekini yuboring", "To‘lovdan so‘ng chek rasmini shu jarayonda yuklang. Oldingi so‘rov tekshirilayotgan paytda yana to‘lov yubormang: tizim bir vaqtda ikkinchi kutilayotgan to‘lovni qabul qilmasligi mumkin."),
            ("Tekshiruv yakunini kuting", "Chekni admin qo‘lda tekshiradi. Tasdiqlangach obuna faollashadi; bot tekshiruv natijasini xabar qiladi."),
            ("Obuna avtomatik uzayadimi?", "Yo‘q. Yangi muddat olish uchun uni qayta tanlab, to‘lovni alohida amalga oshiring."),
            ("Uzaytirish va HSK 3.0", "Agar pulli obunangiz hali faol bo‘lsa, yangi muddat amaldagi tugash sanasiga qo‘shiladi. HSK 3.0’ni bir marta ochish alohida mahsulot, obunaning bir qismi emas."),
        ],
    ),
})

PAGE_TRANSLATIONS = {
    "home": {"tg": "/tj/", "ru": "/ru/", "uz": "/uz/", "x-default": "/"},
    "hsk": {"tg": "/tj/hsk/", "ru": "/ru/hsk/", "uz": "/uz/hsk/"},
    "learn-chinese": {"tg": "/tj/learn-chinese/", "ru": "/ru/learn-chinese/", "uz": "/uz/learn-chinese/"},
    "ai-teacher": {"tg": "/tj/ai-chinese-teacher/", "ru": "/ru/ai-chinese-teacher/", "uz": "/uz/ai-chinese-teacher/"},
    "guide": {"tg": "/tj/guide/", "ru": "/ru/guide/", "uz": "/uz/guide/"},
    "guide-features": {"tg": "/tj/guide/features/", "ru": "/ru/guide/features/", "uz": "/uz/guide/features/"},
    "guide-subscription": {"tg": "/tj/guide/subscription/", "ru": "/ru/guide/subscription/", "uz": "/uz/guide/subscription/"},
}

PAGE_TRANSLATIONS["guide-faq"] = {
    "tg": "/tj/guide/faq/", "ru": "/ru/guide/faq/", "uz": "/uz/guide/faq/",
}

PAGES.update({
    "/tj/guide/faq/": _page(
        "tg", "guide-faq", "faq",
        "Саволҳои маъмул дар бораи HSK AI",
        "Ҷавоб ба саволҳои маъмул дар бораи забонҳои HSK AI, лимитҳо, AI ва санҷиши пардохти обуна.",
        "Саволҳои маъмул",
        "Ҷавобҳои кӯтоҳ ба саволҳое, ки ҳангоми омӯзиш ва истифодаи HSK AI пайдо мешаванд. Маълумоти ҳисоби шумо ва нархи ҷорӣ дар барнома нишон дода мешаванд.",
        [
            ("HSK AI-ро аз куҷо оғоз кунам?", "@darsi_chini_bot-ро кушоед, забонро интихоб кунед ва ба Telegram Mini App гузаред. Баъд аз курси барои шумо дастрас оғоз намоед."),
            ("Обуна чӣ қадар арзиш дорад?", "Нарх аз рӯйи муҳлат, минтақа ва усули пардохт муайян шуда, пеш аз пардохт дар экран нишон дода мешавад. Нархи дар ин саҳифа навишташуда ҳисобида нашавад."),
            ("Пас аз фиристодани расид чӣ кор кунам?", "Расидро админ месанҷад. Дархости интизориро такрор накунед; тасдиқ ё рад шудани пардохт ба воситаи бот хабар дода мешавад."),
            ("Обуна худкор тамдид мешавад?", "Не. Барои муҳлати нав онро аз нав интихоб карда, пардохтро алоҳида анҷом диҳед."),
            ("Оё дар барномаи Android обуна харидан мумкин аст?", "Дар версияи Google Play харид ҳоло пайваст нашудааст; он ҷо танҳо ҳолати обуна нишон дода мешавад. Пардохтро тавассути @darsi_chini_bot анҷом диҳед."),
            ("Оё ҷавобҳои AI ҳамеша дурустанд?", "Не. AI метавонад иштибоҳ кунад; шарҳи шубҳанокро бо маводи дарс ё омӯзгор санҷед."),
            ("Чаро ягон функсия барои ман дастрас нест?", "Баъзе функсияҳо метавонанд аз дастрасии ҳисоби шумо вобаста бошанд. Шартҳои ҷорӣ ва лимитҳоро дар профил ва бахши обуна бинед."),
        ],
    ),
    "/ru/guide/faq/": _page(
        "ru", "guide-faq", "faq",
        "Частые вопросы о HSK AI",
        "Ответы на вопросы о языках HSK AI, лимитах, AI-помощнике и проверке оплаты подписки.",
        "Частые вопросы",
        "Короткие ответы на вопросы, которые возникают при обучении и использовании HSK AI. Состояние аккаунта и актуальная цена отображаются в приложении.",
        [
            ("С чего начать в HSK AI?", "Откройте @darsi_chini_bot, выберите язык и перейдите в Telegram Mini App. Затем начните с доступного вам курса."),
            ("Сколько стоит подписка?", "Цена зависит от срока, региона и способа оплаты и показывается перед платежом. Не используйте цену с этой страницы как актуальную."),
            ("Что делать после отправки чека?", "Чек проверяет администратор. Не отправляйте повторный запрос, пока он ожидает проверки; бот сообщит о подтверждении или отклонении платежа."),
            ("Подписка продлевается автоматически?", "Нет. Чтобы получить новый срок, выберите его заново и оплатите отдельно."),
            ("Можно ли купить подписку в Android-приложении?", "В версии из Google Play покупка пока не подключена; там отображается только статус подписки. Завершите оплату через @darsi_chini_bot."),
            ("Ответы AI всегда точны?", "Нет. AI может ошибаться; сомнительное объяснение сверьте с материалом урока или преподавателем."),
            ("Почему функция мне недоступна?", "Доступ к некоторым функциям может зависеть от состояния аккаунта. Проверьте текущие лимиты и условия в профиле и разделе подписки."),
        ],
    ),
    "/uz/guide/faq/": _page(
        "uz", "guide-faq", "faq",
        "HSK AI haqida ko‘p so‘raladigan savollar",
        "HSK AI tillari, kunlik limitlar, AI yordamchi va obuna to‘lovini tekshirish haqida savollarga javoblar.",
        "Ko‘p so‘raladigan savollar",
        "HSK AI’dan foydalanish va o‘rganish paytida ko‘p uchraydigan savollarga qisqa javoblar. Hisob holati va joriy narx ilovada ko‘rsatiladi.",
        [
            ("HSK AI’dan foydalanishni nimadan boshlayman?", "@darsi_chini_bot botini oching, tilni tanlang va Telegram Mini App’ga o‘ting. Keyin siz uchun ochiq kursdan boshlang."),
            ("Obuna qancha turadi?", "Narx muddat, hudud va to‘lov usuliga qarab belgilanadi va to‘lovdan oldin oynada ko‘rsatiladi. Bu sahifadagi matnni joriy narx deb qabul qilmang."),
            ("Chek yuborgandan keyin nima qilaman?", "Chekni admin tekshiradi. So‘rov tekshirilayotgan paytda uni qayta yubormang; to‘lov tasdiqlansa yoki rad qilinsa bot xabar beradi."),
            ("Obuna avtomatik uzayadimi?", "Yo‘q. Yangi muddat olish uchun uni qayta tanlab, to‘lovni alohida amalga oshiring."),
            ("Android ilovasida obuna sotib olsa bo‘ladimi?", "Google Play versiyasida xarid hozircha ulanmagan, u yerda obuna holati ko‘rsatiladi. To‘lovni @darsi_chini_bot orqali yakunlang."),
            ("AI javoblari doim to‘g‘rimi?", "Yo‘q. AI xato qilishi mumkin; shubhali izohni dars materiali yoki o‘qituvchi bilan tekshiring."),
            ("Nega biror funksiya ochilmayapti?", "Ayrim funksiyalar hisobingizdagi kirish shartlariga bog‘liq bo‘lishi mumkin. Joriy limit va shartlarni profil hamda obuna bo‘limidan ko‘ring."),
        ],
    ),
})

for path, page in PAGES.items():
    if path in ("/", "/tj/", "/ru/", "/uz/"):
        page.setdefault("translation_group", "home")
        page.setdefault("content_group", "home")
    elif path == "/tj/hsk/":
        page.setdefault("translation_group", "hsk")
        page.setdefault("content_group", "hsk")
    elif path == "/tj/learn-chinese/":
        page.setdefault("translation_group", "learn-chinese")
        page.setdefault("content_group", "learn-chinese")
    elif path == "/tj/ai-chinese-teacher/":
        page.setdefault("translation_group", "ai-teacher")
        page.setdefault("content_group", "ai-teacher")

NAV_LABELS = {
    "tg": {"courses": "Курсҳои HSK", "guide": "Роҳнамо", "download": "Боргирӣ", "language": "Забон", "more": "Идома диҳед", "home": "Саҳифаи асосӣ"},
    "ru": {"courses": "Курсы HSK", "guide": "Руководство", "download": "Скачать", "language": "Язык", "more": "Продолжить", "home": "Главная"},
    "uz": {"courses": "HSK kurslari", "guide": "Qo‘llanma", "download": "Yuklab olish", "language": "Til", "more": "Davom eting", "home": "Bosh sahifa"},
}

RELATED_LINKS = {
    "home": {
        "tg": [("hsk", "Курсҳои HSK 1–4", "Аз асосҳо то сатҳҳои пешрафтатар бо дарс ва машқ."), ("guide", "Роҳнамои истифода", "Оғоз, функсияҳо ва қадамҳои обунаро бинед."), ("ai-teacher", "Ёрдамчии AI", "Саволи хуб диҳед ва ҷавобро бо дарс санҷед.")],
        "ru": [("hsk", "Курсы HSK 1–4", "От основ до следующих уровней через уроки и практику."), ("guide", "Руководство", "Как начать, пользоваться функциями и оформить подписку."), ("ai-teacher", "AI-помощник", "Задавайте вопросы и сверяйте ответы с уроком.")],
        "uz": [("hsk", "HSK 1–4 kurslari", "Dars va mashqlar bilan bosqichma-bosqich o‘rganing."), ("guide", "Foydalanish qo‘llanmasi", "Boshlash, funksiyalar va obuna olish tartibi."), ("ai-teacher", "AI yordamchi", "Savol bering va javobni dars bilan tekshiring.")],
    },
    "guide": {
        "tg": [("guide-features", "Курс ва функсияҳо", "Дарс, машқ, AI ва талаффузро чӣ гуна истифода бурдан."), ("guide-subscription", "Обуна ва пардохт", "Интихоби муҳлат, пардохт, расид ва тасдиқ."), ("guide-faq", "Саволҳои маъмул", "Ҷавобҳои кӯтоҳ дар бораи лимитҳо ва омӯзиш.")],
        "ru": [("guide-features", "Курс и функции", "Уроки, практика, AI и произношение."), ("guide-subscription", "Подписка и оплата", "Срок, способы оплаты, чек и подтверждение."), ("guide-faq", "Частые вопросы", "Короткие ответы об обучении и лимитах.")],
        "uz": [("guide-features", "Kurs va funksiyalar", "Dars, mashq, AI va talaffuzdan foydalanish."), ("guide-subscription", "Obuna va to‘lov", "Muddat, to‘lov usuli, chek va tasdiq."), ("guide-faq", "Ko‘p so‘raladigan savollar", "O‘qish va limitlar haqida qisqa javoblar.")],
    },
    "hsk": {
        "tg": [("learn-chinese", "Оғози забони чинӣ", "Пинйин, оҳангҳо ва ҷумлаҳои аввал."), ("guide", "Роҳнамои HSK AI", "Тарзи истифодаи курс ва функсияҳо.")],
        "ru": [("learn-chinese", "Начало изучения китайского", "Пиньинь, тоны и первые фразы."), ("guide", "Руководство HSK AI", "Как пользоваться курсом и функциями.")],
        "uz": [("learn-chinese", "Xitoy tilini boshlash", "Pinyin, ohanglar va ilk gaplar."), ("guide", "HSK AI qo‘llanmasi", "Kurs va funksiyalardan foydalanish.")],
    },
    "learn-chinese": {
        "tg": [("hsk", "Курсҳои HSK 1–4", "Омӯзишро аз дарсҳои пайдарпай идома диҳед."), ("guide", "Роҳнамои истифода", "Курс, AI ва обунаро шарҳ медиҳад.")],
        "ru": [("hsk", "Курсы HSK 1–4", "Продолжайте обучение по последовательным урокам."), ("guide", "Руководство", "Курс, AI и оформление подписки.")],
        "uz": [("hsk", "HSK 1–4 kurslari", "Ketma-ket darslar bilan davom eting."), ("guide", "Foydalanish qo‘llanmasi", "Kurs, AI va obuna haqida.")],
    },
    "ai-teacher": {
        "tg": [("guide-features", "Курс ва функсияҳо", "AI, дарсҳо ва машқҳоро якҷо истифода баред."), ("guide", "Роҳнамои HSK AI", "Тарзи истифода ва шароити дастрасӣ.")],
        "ru": [("guide-features", "Курс и функции", "Используйте AI вместе с уроками и практикой."), ("guide", "Руководство HSK AI", "Как пользоваться и проверить условия доступа.")],
        "uz": [("guide-features", "Kurs va funksiyalar", "AI’ni dars va mashqlar bilan birga ishlating."), ("guide", "HSK AI qo‘llanmasi", "Foydalanish va kirish shartlari.")],
    },
    "features": {
        "tg": [("hsk", "Курсҳои HSK", "Дарсҳои пайдарпайро оғоз кунед ё идома диҳед."), ("guide-subscription", "Обуна", "Муҳлат, пардохт ва санҷиши расид.")],
        "ru": [("hsk", "Курсы HSK", "Начните или продолжите последовательные уроки."), ("guide-subscription", "Подписка", "Срок, оплата и проверка чека.")],
        "uz": [("hsk", "HSK kurslari", "Ketma-ket darslarni boshlang yoki davom ettiring."), ("guide-subscription", "Obuna", "Muddat, to‘lov va chek tekshiruvi.")],
    },
    "subscription": {
        "tg": [("guide-features", "Курс ва функсияҳо", "Функсияҳои барномаро бо тартиб омӯзед."), ("hsk", "Курсҳои HSK", "Дарс ва машқро кушоед.")],
        "ru": [("guide-features", "Курс и функции", "Разберитесь в возможностях приложения."), ("hsk", "Курсы HSK", "Откройте уроки и практику.")],
        "uz": [("guide-features", "Kurs va funksiyalar", "Ilovadagi imkoniyatlardan foydalanishni ko‘ring."), ("hsk", "HSK kurslari", "Darslar va mashqlarni oching.")],
    },
    "faq": {
        "tg": [("guide-subscription", "Обуна", "Муҳлат, нарх ва расиди пардохтро бинед."), ("guide-features", "Курс ва функсияҳо", "Тарзи истифодаи HSK AI.")],
        "ru": [("guide-subscription", "Подписка", "Срок, цена и подтверждение платежа."), ("guide-features", "Курс и функции", "Как пользоваться HSK AI.")],
        "uz": [("guide-subscription", "Obuna", "Muddat, narx va to‘lov tasdig‘i."), ("guide-features", "Kurs va funksiyalar", "HSK AI’dan foydalanish tartibi.")],
    },
}

HOME_PATHS = {"tg": "/tj/", "ru": "/ru/", "uz": "/uz/", "x-default": "/"}
PAGE_PATHS = PAGE_TRANSLATIONS
CTA = {"tg": "Ботро дар Telegram кушоед", "ru": "Открыть бота в Telegram", "uz": "Telegram botni ochish"}
DOWNLOAD_CTA = {"tg": "Барномаҳои HSK AI-ро боргирӣ кунед",
                "ru": "Скачать приложения HSK AI",
                "uz": "HSK AI ilovalarini yuklab olish"}
