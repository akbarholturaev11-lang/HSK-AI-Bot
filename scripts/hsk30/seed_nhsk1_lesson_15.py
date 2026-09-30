from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程1",
    "pdf_path": "HSK 3.0 PDF/新HSK教程1.pdf",
    "pdf_pages": [126, 127, 128, 129, 130, 131, 132, 133, 134, 135],
    "printed_pages": [112, 113, 114, 115, 116, 117, 118, 119, 120, 121],
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk1",
    "lesson_order": 15,
    "lesson_code": "NHSK1-L15",
    "title": "大兴机场见！",
    "title_pinyin": "Dàxīng Jīchǎng jiàn!",
    "goal": json.dumps(
        {
            "uz": "Safar niyati va rejasini ifodalovchi so‘zlarni tushunish va ishlatish; “……，还/也……” bilan mantiqan teng bog‘langan gaplarni tuzish; xitoycha mehmondo‘stlik va ovqatlanish odobining asosiy jihatlarini tushunish.",
            "ru": "Понимать и использовать лексику намерений и планов поездки; строить сочинённые предложения с “……，还/也……” ; понимать базовые нормы китайского застолья и гостеприимства.",
            "tj": "Луғати ният ва нақшаи сафарро фаҳмидан ва истифода бурдан; бо “……，还/也……” ҷумлаҳои ҳампайванд сохтан; асосҳои одоби меҳмондорӣ ва хӯрокхӯрии чиниро фаҳмидан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars xitoy taomlari, sayohat rejalari va Pekinga parvoz haqidagi uchta dialog orqali “……，还/也……” qo‘shma gapini va sayohat leksikasini mustahkamlaydi.",
            "ru": "Урок через три диалога о китайской еде, планах путешествия и полёте в Пекин закрепляет конструкцию “……，还/也……” и лексику путешествий.",
            "tj": "Дарс тавассути се гуфтугӯ дар бораи таоми чинӣ, нақшаи сафар ва парвоз ба Пекин сохтори “……，还/也……” ва луғати сафарро мустаҳкам мекунад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no":1,"zh":"爱","pinyin":"ài","pos":"v.","uz":"sevmoq; juda yoqtirmoq","ru":"любить; очень нравиться","tj":"дӯст доштан"},
            {"no":2,"zh":"哪个","pinyin":"nǎge","pos":"pron.","uz":"qaysi biri","ru":"который; какой","tj":"кадомаш"},
            {"no":3,"zh":"去年","pinyin":"qùnián","pos":"n.","uz":"o‘tgan yil","ru":"прошлый год","tj":"соли гузашта"},
            {"no":4,"zh":"男朋友","pinyin":"nánpéngyou","pos":"n.","uz":"yigit; sevgili","ru":"парень; бойфренд","tj":"дӯстписар"},
            {"no":5,"zh":"几","pinyin":"jǐ","pos":"num.","uz":"bir necha","ru":"несколько","tj":"чанд"},
            {"no":6,"zh":"非常","pinyin":"fēicháng","pos":"adv.","uz":"juda; nihoyatda","ru":"очень","tj":"хеле"},
            {"no":7,"zh":"好玩儿","pinyin":"hǎowánr","pos":"adj.","uz":"qiziqarli; maroqli","ru":"интересный; весёлый","tj":"шавқовар; ҷолиб"},
            {"no":8,"zh":"飞机","pinyin":"fēijī","pos":"n.","uz":"samolyot","ru":"самолёт","tj":"ҳавопаймо"},
            {"no":9,"zh":"要","pinyin":"yào","pos":"v.","uz":"kerak bo‘lmoq; vaqt olmoq","ru":"требоваться; занимать времени","tj":"лозим шудан; вақт гирифтан"},
            {"no":10,"zh":"小时","pinyin":"xiǎoshí","pos":"n.","uz":"soat (davomiylik)","ru":"час","tj":"соат"},
            {"no":11,"zh":"家人","pinyin":"jiārén","pos":"n.","uz":"oila a’zosi; oila","ru":"член семьи; семья","tj":"аъзои оила; оила"},
            {"no":12,"zh":"时间","pinyin":"shíjiān","pos":"n.","uz":"vaqt; vaqt davomiyligi","ru":"время; продолжительность","tj":"вақт; давомнокӣ"},
            {"no":13,"zh":"机场","pinyin":"jīchǎng","pos":"n.","uz":"aeroport","ru":"аэропорт","tj":"фурудгоҳ"},
            {"no":14,"zh":"接","pinyin":"jiē","pos":"v.","uz":"kutib olmoq","ru":"встречать","tj":"пешвоз гирифтан"},
            {"no":15,"zh":"住","pinyin":"zhù","pos":"v.","uz":"yashamoq; turmoq","ru":"жить; останавливаться","tj":"зиндагӣ кардан; мондан"},
            {"no":16,"zh":"早","pinyin":"zǎo","pos":"adj.","uz":"erta","ru":"ранний; рано","tj":"барвақт"},
            {"no":17,"zh":"那","pinyin":"nà","pos":"conj.","uz":"unda; shunda","ru":"тогда","tj":"пас; он гоҳ"},
        ],
        ensure_ascii=False,
    ),
    "proper_nouns_json": json.dumps(
        [
            {"zh":"西安","pinyin":"Xī'ān","en":"Xi'an","uz":"Xi’an","ru":"Сиань","tj":"Сиан"},
            {"zh":"北京","pinyin":"Běijīng","en":"Beijing","uz":"Pekin","ru":"Пекин","tj":"Пекин"},
            {"zh":"大兴机场","pinyin":"Dàxīng Jīchǎng","en":"Daxing Airport","uz":"Daxing aeroporti","ru":"аэропорт Дасин","tj":"Фурудгоҳи Дасин"},
        ],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no":1,"section_label":"课文 1",
                "scene_zh":"在李文家，李文邀请陈天中、白家月等朋友品尝中国菜。",
                "scene_en":"At Li Wen's home, Li Wen invited friends, including Chen Tianzhong and Bai Jiayue, to taste Chinese food.",
                "scene_uz":"Li Wenning uyida u Chen Tianzhong, Bai Jiayue va boshqa do‘stlarini xitoy taomlarini tatib ko‘rishga taklif qilgan.",
                "scene_ru":"Дома у Ли Вэня он угощает китайской едой Чэнь Тяньчжуна, Бай Цзяюэ и других друзей.",
                "scene_tj":"Дар хонаи Ли Вэн ӯ Чэн Тянҷун, Бай Ҷяюэ ва дигар дӯстонашро бо таоми чинӣ меҳмондорӣ мекунад.",
                "dialogue":[
                    {"speaker":"Li Wen","zh":"你们爱吃哪个菜？","pinyin":"Nǐmen ài chī nǎge cài?","en":"Which dish do you like?","uz":"Qaysi taomni yoqtirasizlar?","ru":"Какое блюдо вам нравится?","tj":"Кадом таомро дӯст медоред?"},
                    {"speaker":"Bai Jiayue","zh":"我喜欢这个，也喜欢那个。","pinyin":"Wǒ xǐhuan zhège, yě xǐhuan nàge.","en":"I like this one, and I also like that one.","uz":"Buni yoqtiraman, anavini ham yoqtiraman.","ru":"Мне нравится это, и то тоже нравится.","tj":"Инро дӯст медорам, онро ҳам дӯст медорам."},
                    {"speaker":"Chen Tianzhong","zh":"这些菜都好吃，还很好看。","pinyin":"Zhèxiē cài dōu hǎochī, hái hěn hǎokàn.","en":"All of these dishes are delicious, and they look great too.","uz":"Bu taomlarning hammasi mazali, ko‘rinishi ham juda chiroyli.","ru":"Все эти блюда вкусные и ещё очень красиво выглядят.","tj":"Ҳамаи ин таомҳо болаззатанд ва хеле зебо ҳам менамоянд."},
                    {"speaker":"Li Wen","zh":"我爱吃中国菜，也喜欢做。大家多吃点儿。","pinyin":"Wǒ ài chī Zhōngguó cài, yě xǐhuan zuò. Dàjiā duō chī diǎnr.","en":"I like eating Chinese food, and I also like cooking it. Everyone, please help yourselves and eat more.","uz":"Men xitoy taomlarini yeyishni ham, pishirishni ham yoqtiraman. Hamma ko‘proq yesin.","ru":"Я люблю есть китайскую еду и люблю её готовить. Ешьте побольше.","tj":"Ман хӯрдани таоми чинӣ ва пухтани онро дӯст медорам. Ҳама бештар хӯред."},
                ]
            },
            {
                "block_no":2,"section_label":"课文 2",
                "scene_zh":"在李文家，大家边吃饭边谈论假期计划。",
                "scene_en":"At Li Wen's home, everyone was talking about their holiday plans while eating.",
                "scene_uz":"Li Wenning uyida hamma ovqatlanib turib ta’til rejalarini muhokama qilmoqda.",
                "scene_ru":"Дома у Ли Вэня все за едой обсуждают планы на каникулы.",
                "scene_tj":"Дар хонаи Ли Вэн ҳама ҳангоми хӯрок нақшаҳои таътилро муҳокима мекунанд.",
                "dialogue":[
                    {"speaker":"Li Wen","zh":"你们都想去哪儿？","pinyin":"Nǐmen dōu xiǎng qù nǎr?","en":"Where do you all want to go?","uz":"Hammangiz qayerga bormoqchisiz?","ru":"Куда вы все хотите поехать?","tj":"Ҳамаатон ба куҷо рафтан мехоҳед?"},
                    {"speaker":"Annie","zh":"去年我和男朋友去了西安，今年我想去北京。","pinyin":"Qùnián wǒ hé nánpéngyou qùle Xī'ān, qiánnián wǒ māma qù Shānxī.","en":"My boyfriend and I went to Xi'an last year, and I want to visit Beijing this year.","uz":"O‘tgan yili men yigitim bilan Xi’anga bordim, bu yil Pekinga bormoqchiman.","ru":"В прошлом году мы с моим парнем ездили в Сиань, а в этом году я хочу поехать в Пекин.","tj":"Соли гузашта ман бо дӯстписарам ба Сиан рафтам, имсол мехоҳам ба Пекин равам."},
                    {"speaker":"Bai Jiayue","zh":"前几年我去了西安，非常好玩儿。今年我也想去北京。","pinyin":"Qián jǐ nián wǒ qùle Xī'ān, fēicháng hǎowánr. Jīnnián wǒ yě xiǎng qù Běijīng.","en":"A few years ago I went to Xi'an; it was really fun. This year, I want to go to Beijing too.","uz":"Bir necha yil oldin Xi’anga bordim, juda maroqli edi. Bu yil Pekinga ham bormoqchiman.","ru":"Несколько лет назад я была в Сиане, там было очень интересно. В этом году тоже хочу поехать в Пекин.","tj":"Чанд сол пеш ба Сиан рафтам, хеле шавқовар буд. Имсол ҳам мехоҳам ба Пекин равам."},
                    {"speaker":"Li Wen","zh":"我和王老师都是北京人，北京非常漂亮。","pinyin":"Wǒ hé Wáng lǎoshī dōu shì Běijīng rén, Běijīng fēicháng piàoliang.","en":"Ms. Wang and I are both from Beijing. Beijing is very beautiful.","uz":"Men va ustoz Wang ikkalamiz ham Pekinlikmiz. Pekin juda chiroyli.","ru":"Мы с преподавателем Ван оба из Пекина. Пекин очень красивый.","tj":"Ман ва устод Ван ҳар ду аз Пекин ҳастем. Пекин хеле зебост."},
                ]
            },
            {
                "block_no":3,"section_label":"课文 3",
                "scene_zh":"在教室外，白家月、安妮和王老师在谈论去北京旅游的事。",
                "scene_en":"Outside the classroom, Bai Jiayue, Annie, and Ms. Wang were talking about traveling to Beijing.",
                "scene_uz":"Sinf tashqarisida Bai Jiayue, Annie va ustoz Wang Pekinga sayohat haqida gaplashmoqda.",
                "scene_ru":"У аудитории Бай Цзяюэ, Энни и преподаватель Ван обсуждают поездку в Пекин.",
                "scene_tj":"Берун аз синф Бай Ҷяюэ, Энни ва устод Ван дар бораи сафар ба Пекин суҳбат мекунанд.",
                "dialogue":[
                    {"speaker":"Wang Yifei","zh":"你们的飞机到北京要几个小时？","pinyin":"Nǐmen de fēijī dào Běijīng yào jǐ ge xiǎoshí?","en":"How many hours will your flight take to get to Beijing?","uz":"Samolyotingiz Pekinga necha soatda yetib boradi?","ru":"Сколько часов займёт ваш полёт до Пекина?","tj":"Ҳавопаймои шумо то Пекин чанд соат вақт мегирад?"},
                    {"speaker":"Bai Jiayue","zh":"九个小时。","pinyin":"Jiǔ ge xiǎoshí.","en":"Nine hours.","uz":"To‘qqiz soat.","ru":"Девять часов.","tj":"Нӯҳ соат."},
                    {"speaker":"Wang Yifei","zh":"我家人都在北京，星期天我姐姐也有时间，她可以去机场接你们，你们也可以住我家。","pinyin":"Wǒ jiārén dōu zài Běijīng, Xīngqītiān wǒ jiějie yě yǒu shíjiān, tā kěyǐ qù jīchǎng jiē nǐmen, nǐmen yě kěyǐ zhù wǒ jiā.","en":"My whole family lives in Beijing. My sister will be free on Sunday. She can pick you up at the airport, and you can stay at my home.","uz":"Oilamning hammasi Pekinda. Yakshanba kuni opamning ham vaqti bor, u sizlarni aeroportdan kutib olishi mumkin, sizlar biznikida ham turishingiz mumkin.","ru":"Вся моя семья в Пекине. В воскресенье моя старшая сестра свободна, она может встретить вас в аэропорту, а вы можете остановиться у меня.","tj":"Ҳамаи оилаи ман дар Пекинанд. Рӯзи якшанбе апаам вақт дорад, метавонад шуморо аз фурудгоҳ пешвоз гирад ва шумо метавонед дар хонаи ман монед."},
                    {"speaker":"Annie","zh":"我们星期日早上八点到大兴机场，早不早？","pinyin":"Wǒmen Xīngqīrì zǎoshang bā diǎn dào Dàxīng Jīchǎng, zǎo bu zǎo?","en":"We'll arrive at Daxing Airport at 8:00 on Sunday morning. Is that early?","uz":"Yakshanba ertalab soat 8 da Daxing aeroportiga yetib kelamiz, juda ertami?","ru":"Мы прилетим в аэропорт Дасин в 8 утра в воскресенье. Это рано?","tj":"Якшанбе субҳ соати 8 ба Фурудгоҳи Дасин мерасем, барвақт аст ё не?"},
                    {"speaker":"Wang Yifei","zh":"不早。","pinyin":"Bù zǎo.","en":"Not early at all.","uz":"Erta emas.","ru":"Нет, не рано.","tj":"Не, барвақт нест."},
                    {"speaker":"Bai Jiayue","zh":"谢谢老师！那我们和您姐姐在大兴机场见！","pinyin":"Xièxie lǎoshī! Nà wǒmen hé nín jiějie zài Dàxīng Jīchǎng jiàn!","en":"Thank you, teacher! Then we'll meet your sister at Daxing Airport!","uz":"Rahmat, ustoz! Unda opangiz bilan Daxing aeroportida uchrashamiz!","ru":"Спасибо, преподаватель! Тогда встретимся с вашей сестрой в аэропорту Дасин!","tj":"Раҳмат, устод! Пас бо апаатон дар Фурудгоҳи Дасин вомехӯрем!"},
                ]
            },
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no":1,"title_zh":"并列复句“……，还/也……”","title_uz":"“……，还/也……” teng bog‘langan qo‘shma gap","title_ru":"Сочинённое предложение “……，还/也……”","title_tj":"Ҷумлаи ҳампайванди “……，还/也……”",
                "rule_zh":"并列复句由两个或两个以上逻辑关系平等的分句构成，本册学习并列复句“……，还/也……”。",
                "rule_en":"A coordinate compound sentence consists of two or more clauses that are logically related and structurally parallel. This volume focuses on “……，还/也……”.",
                "rule_uz":"Teng bog‘langan qo‘shma gap ikki yoki undan ko‘p mantiqan teng qismlardan tuziladi. Bu bosqichda “……，还/也……” o‘rganiladi.",
                "rule_ru":"Сочинённое предложение состоит из двух или более логически равноправных частей. Здесь изучается модель “……，还/也……”.",
                "rule_tj":"Ҷумлаи ҳампайванд аз ду ё зиёда қисми аз ҷиҳати мантиқӣ баробар сохта мешавад. Дар ин сатҳ қолаби “……，还/也……” омӯхта мешавад.",
                "examples":[
                    {"zh":"我喜欢这个，也喜欢那个。","pinyin":"Wǒ xǐhuan zhège, yě xǐhuan nàge.","uz":"Buni yoqtiraman, anavini ham yoqtiraman.","ru":"Мне нравится это, и то тоже нравится.","tj":"Инро дӯст медорам, онро ҳам дӯст медорам."},
                    {"zh":"王老师是北京人，李文也是北京人。","pinyin":"Wáng lǎoshī shì Běijīng rén, Lǐ Wén yě shì Běijīng rén.","uz":"Ustoz Wang Pekinlik, Li Wen ham Pekinlik.","ru":"Преподаватель Ван из Пекина, и Ли Вэнь тоже из Пекина.","tj":"Устод Ван аз Пекин аст, Ли Вэн ҳам аз Пекин аст."},
                    {"zh":"我喜欢喝中国茶，还喜欢吃中国菜。","pinyin":"Wǒ xǐhuan hē Zhōngguó chá, hái xǐhuan chī Zhōngguó cài.","uz":"Xitoy choyini ichishni yoqtiraman, xitoy taomlarini yeyishni ham yoqtiraman.","ru":"Мне нравится пить китайский чай, а ещё я люблю китайскую еду.","tj":"Нӯшидани чойи чиниро дӯст медорам ва хӯрдани таоми чиниро ҳам дӯст медорам."},
                ]
            }
        ],
        ensure_ascii=False,
    ),
    "usage_notes_json": json.dumps(
        [
            {
                "topic":"劝菜",
                "zh":"劝客人多吃菜是中国餐桌文化的一部分，体现中国人的热情好客。",
                "en":"Encouraging others to eat more is part of Chinese dining culture and reflects hospitality.",
                "uz":"Mehmonga ko‘proq ovqat yeyishni taklif qilish xitoy dasturxon madaniyatining bir qismi bo‘lib, mehmondo‘stlikni bildiradi.",
                "ru":"Предлагать гостям есть побольше — часть китайской застольной культуры и проявление гостеприимства.",
                "tj":"Ба меҳмон бештар хӯрок пешниҳод кардан қисми фарҳанги дастархони чинӣ буда, меҳмондӯстиро нишон медиҳад.",
            }
        ],
        ensure_ascii=False,
    ),
}
