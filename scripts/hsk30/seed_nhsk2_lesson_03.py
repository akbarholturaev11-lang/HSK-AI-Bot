from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(35, 45)),
    "printed_pages": list(range(19, 29)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk2",
    "lesson_order": 3,
    "lesson_code": "NHSK2-L03",
    "title": "我想去西安旅游",
    "title_pinyin": "Wǒ xiǎng qù Xī'ān lǚyóu",
    "goal": json.dumps(
        {
            "uz": "Natija to‘ldiruvchisi orqali harakat natijasini ifodalash; fe’l takrorlanishi bilan qisqa, yengil yoki sinab ko‘rish xarakteridagi harakatni aytish; sayohat rejasini muhokama qilish.",
            "ru": "Выражать результат действия с помощью результативного дополнения; использовать редупликацию глагола для краткого, непринуждённого или пробного действия; обсуждать планы поездки.",
            "tj": "Натиҷаи амалро бо пуркунандаи натиҷа ифода кардан; такрори феълро барои амали кӯтоҳ, сабук ё озмоишӣ истифода бурдан; нақшаи сафарро муҳокима кардан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars ish kuni, sayohat rejalari, Xi’anga borish va kundalik oilaviy vaziyatlar haqidagi to‘rtta matn/dialog orqali natija to‘ldiruvchisi va fe’l takrorlanishining ikki turini o‘rgatadi.",
            "ru": "Урок через четыре текста/диалога о рабочем дне, планах путешествия, поездке в Сиань и семейной повседневности вводит результативные дополнения и два типа редупликации глагола.",
            "tj": "Дарс тавассути чор матн/гуфтугӯ дар бораи рӯзи корӣ, нақшаҳои сафар, рафтан ба Сиан ва зиндагии оилавӣ пуркунандаи натиҷа ва ду навъи такрори феълро меомӯзонад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no":1,"zh":"回来","pinyin":"huílái","pos":"v.","uz":"qaytib kelmoq","ru":"вернуться; прийти обратно","tj":"баргашта омадан"},
            {"no":2,"zh":"这么","pinyin":"zhème","pos":"pron.","uz":"shunchalik; bunaqa","ru":"так; настолько","tj":"ин қадар; ҳамин тавр"},
            {"no":3,"zh":"完","pinyin":"wán","pos":"v.","uz":"tugatmoq","ru":"закончить; завершить","tj":"тамом кардан"},
            {"no":4,"zh":"一起","pinyin":"yìqǐ","pos":"adv.","uz":"birga","ru":"вместе","tj":"якҷо"},
            {"no":5,"zh":"出去","pinyin":"chūqù","pos":"v.","uz":"tashqariga chiqmoq","ru":"выйти; пойти наружу","tj":"ба берун баромадан"},
            {"no":6,"zh":"洗","pinyin":"xǐ","pos":"v.","uz":"yuvmoq","ru":"мыть","tj":"шустан"},
            {"no":7,"zh":"自己","pinyin":"zìjǐ","pos":"pron.","uz":"o‘zi; o‘zini","ru":"сам; себя","tj":"худ; худро"},
            {"no":8,"zh":"拿","pinyin":"ná","pos":"v.","uz":"olmoq; ushlamoq","ru":"брать; держать","tj":"гирифтан; доштан"},
            {"no":9,"zh":"手","pinyin":"shǒu","pos":"n.","uz":"qo‘l","ru":"рука","tj":"даст"},
            {"no":10,"zh":"为什么","pinyin":"wèishénme","pos":"pron.","uz":"nega; nima uchun","ru":"почему; зачем","tj":"чаро; барои чӣ"},
            {"no":11,"zh":"不错","pinyin":"búcuò","pos":"adj.","uz":"yomon emas; ancha yaxshi","ru":"неплохо; довольно хорошо","tj":"бад нест; хуб"},
            {"no":12,"zh":"送","pinyin":"sòng","pos":"v.","uz":"kuzatib qo‘ymoq; yetkazmoq; sovg‘a qilmoq","ru":"провожать; доставлять; дарить","tj":"гусел кардан; расондан; тӯҳфа кардан"},
            {"no":13,"zh":"回去","pinyin":"huíqù","pos":"v.","uz":"qaytib bormoq","ru":"вернуться туда","tj":"баргашта рафтан"},
            {"no":14,"zh":"每","pinyin":"měi","pos":"pron.","uz":"har; har bir","ru":"каждый","tj":"ҳар; ҳар як"},
            {"no":15,"zh":"累","pinyin":"lèi","pos":"adj.","uz":"charchagan","ru":"уставший","tj":"хаста"},
        ],
        ensure_ascii=False,
    ),
    "proper_nouns_json": json.dumps(
        [{"zh":"西安","pinyin":"Xī'ān","en":"Xi'an","uz":"Xi’an","ru":"Сиань","tj":"Сиан"}],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no":1,"section_label":"课文 1",
                "scene_zh":"在家门口，刘明开门进到家里。",
                "scene_uz":"Uy eshigi oldida Liu Ming eshikni ochib uyga kirdi.",
                "scene_ru":"У двери дома Лю Мин открыл дверь и вошёл.",
                "scene_tj":"Дар назди дари хона Лю Мин дарро кушода ба хона даромад.",
                "dialogue":[
                    {"speaker":"Wang Yixue","zh":"今天回来这么晚啊！","pinyin":"Jīntiān huílái zhème wǎn a!","uz":"Bugun juda kech qaytding-ku!","ru":"Сегодня ты так поздно вернулся!","tj":"Имрӯз ин қадар дер баргаштӣ!"},
                    {"speaker":"Liu Ming","zh":"工作太多了，下班的时候没做完。","pinyin":"Gōngzuò tài duō le, xiàbān de shíhou méi zuòwán.","uz":"Ish juda ko‘p edi, ishdan chiqish vaqtida tugata olmadim.","ru":"Работы было слишком много, к концу рабочего дня я не закончил.","tj":"Кор хеле зиёд буд, вақти аз кор баромадан тамом карда натавонистам."},
                    {"speaker":"Wang Yixue","zh":"菜都做好了，过来吃饭吧。","pinyin":"Cài dōu zuòhǎo le, guòlai chī fàn ba.","uz":"Ovqatlar tayyor, kelib ovqat ye.","ru":"Еда уже готова, иди есть.","tj":"Хӯрок тайёр шудааст, биё хӯрок бихӯр."},
                    {"speaker":"Liu Ming","zh":"我想休息一下，喝杯水。","pinyin":"Wǒ xiǎng xiūxi yíxià, hē bēi shuǐ.","uz":"Biroz dam olib, bir stakan suv ichmoqchiman.","ru":"Я хочу немного отдохнуть и выпить стакан воды.","tj":"Мехоҳам каме истироҳат карда, як пиёла об нӯшам."},
                    {"speaker":"Wang Yixue","zh":"好的。","pinyin":"Hǎo de.","uz":"Xo‘p.","ru":"Хорошо.","tj":"Хуб."}
                ]
            },
            {
                "block_no":2,"section_label":"课文 2",
                "scene_zh":"在客厅，刘明和王一雪在聊天儿。",
                "scene_uz":"Mehmonxonada Liu Ming va Wang Yixue suhbatlashmoqda.",
                "scene_ru":"В гостиной Лю Мин и Ван Исюэ разговаривают.",
                "scene_tj":"Дар меҳмонхона Лю Мин ва Ван Исюэ суҳбат мекунанд.",
                "dialogue":[
                    {"speaker":"Liu Ming","zh":"我们找个时间去旅游，怎么样？","pinyin":"Wǒmen zhǎo ge shíjiān qù lǚyóu, zěnmeyàng?","uz":"Bir vaqt topib sayohatga borsak, qanday?","ru":"Давай найдём время и съездим куда-нибудь, как тебе?","tj":"Як вақт ёфта ба саёҳат равем, чӣ хел?"},
                    {"speaker":"Wang Yixue","zh":"好啊，我也很想一起出去玩。","pinyin":"Hǎo a, wǒ yě hěn xiǎng yìqǐ chūqù wán.","uz":"Yaxshi, men ham birga tashqariga chiqib sayr qilishni juda xohlayman.","ru":"Хорошо, я тоже очень хочу куда-нибудь съездить вместе.","tj":"Хуб, ман ҳам хеле мехоҳам якҷо ба берун баромада сайр кунем."},
                    {"speaker":"Liu Ming","zh":"你想去哪儿？","pinyin":"Nǐ xiǎng qù nǎr?","uz":"Qayerga bormoqchisan?","ru":"Куда ты хочешь поехать?","tj":"Ба куҷо рафтан мехоҳӣ?"},
                    {"speaker":"Wang Yixue","zh":"我还没想好呢。","pinyin":"Wǒ hái méi xiǎnghǎo ne.","uz":"Hali aniq o‘ylab topmadim.","ru":"Я ещё не решила.","tj":"Ҳоло хуб фикр карда набаромадаам."},
                    {"speaker":"Liu Ming","zh":"那你再想一想，你想好了，我来买票。","pinyin":"Nà nǐ zài xiǎng yì xiǎng, nǐ xiǎnghǎo le, wǒ lái mǎi piào.","uz":"Unda yana o‘ylab ko‘r. Qaror qilganingda chiptani men olaman.","ru":"Тогда ещё подумай. Когда решишь, билеты куплю я.","tj":"Пас боз як бор фикр кун. Вақте қарор кардӣ, чиптаро ман мехарам."}
                ]
            },
            {
                "block_no":3,"section_label":"课文 3",
                "scene_zh":"在客厅，刘明和王一雪在聊天儿。",
                "scene_uz":"Mehmonxonada Liu Ming va Wang Yixue suhbatlashmoqda.",
                "scene_ru":"В гостиной Лю Мин и Ван Исюэ разговаривают.",
                "scene_tj":"Дар меҳмонхона Лю Мин ва Ван Исюэ суҳбат мекунанд.",
                "dialogue":[
                    {"speaker":"Liu Ming","zh":"吃个苹果吧，我都洗好了。","pinyin":"Chī ge píngguǒ ba, wǒ dōu xǐhǎo le.","uz":"Olma ye, men hammasini yuvib qo‘ydim.","ru":"Съешь яблоко, я их уже помыл.","tj":"Як себ бихӯр, ман ҳамаашро шуста мондам."},
                    {"speaker":"Wang Yixue","zh":"好的。","pinyin":"Hǎo de.","uz":"Xo‘p.","ru":"Хорошо.","tj":"Хуб."},
                    {"speaker":"Liu Ming","zh":"就在桌子上，你自己拿。","pinyin":"Jiù zài zhuōzi shàng, nǐ zìjǐ ná.","uz":"Stol ustida, o‘zing ol.","ru":"Они прямо на столе, возьми сама.","tj":"Рӯйи мизанд, худат бигир."},
                    {"speaker":"Wang Yixue","zh":"我去洗洗手。对了，我们去西安旅游，怎么样？","pinyin":"Wǒ qù xǐxǐ shǒu. Duì le, wǒmen qù Xī'ān lǚyóu, zěnmeyàng?","uz":"Men borib qo‘limni yuvib kelaman. Aytgancha, Xi’anga sayohatga borsak qanday?","ru":"Я пойду помою руки. Кстати, как насчёт поездки в Сиань?","tj":"Ман рафта дастамро мешӯям. Ростӣ, ба Сиан ба саёҳат равем, чӣ хел?"},
                    {"speaker":"Liu Ming","zh":"为什么想去西安？","pinyin":"Wèishénme xiǎng qù Xī'ān?","uz":"Nega Xi’anga bormoqchisan?","ru":"Почему хочешь поехать в Сиань?","tj":"Чаро мехоҳӣ ба Сиан равӣ?"},
                    {"speaker":"Wang Yixue","zh":"我看了看网上的介绍，这个时候去西安很不错！","pinyin":"Wǒ kànle kàn wǎngshang de jièshào, zhège shíhou qù Xī'ān hěn búcuò!","uz":"Internetdagi ma’lumotlarni bir ko‘rib chiqdim, shu paytda Xi’anga borish juda yaxshi ekan!","ru":"Я посмотрела информацию в интернете — в это время ехать в Сиань очень неплохо!","tj":"Маълумоти интернетро як назар кардам, дар ҳамин вақт ба Сиан рафтан хеле хуб будааст!"}
                ]
            },
            {
                "block_no":4,"section_label":"课文 4",
                "scene_zh":"在家里，王一雪给好朋友打电话。",
                "scene_uz":"Uyda Wang Yixue yaqin do‘stiga telefon qilmoqda.",
                "scene_ru":"Дома Ван Исюэ звонит своей близкой подруге.",
                "scene_tj":"Дар хона Ван Исюэ ба дӯсти наздикаш занг мезанад.",
                "dialogue":[
                    {"speaker":"Narration","zh":"早上，刘明开车送孩子去学校，送完孩子回家后，医院就来电话了，让他回去上班。我觉得他这个月每天都很累，真想让他休息休息。","pinyin":"Zǎoshang, Liú Míng kāichē sòng háizi qù xuéxiào, sòngwán háizi huí jiā hòu, yīyuàn jiù lái diànhuà le, ràng tā huíqù shàngbān. Wǒ juéde tā zhège yuè měitiān dōu hěn lèi, zhēn xiǎng ràng tā xiūxi xiūxi.","uz":"Ertalab Liu Ming bolani mashinada maktabga olib bordi. Bolani olib borib uyga qaytgach, kasalxonadan darrov qo‘ng‘iroq bo‘lib, uni ishga qaytishga chaqirishdi. Menimcha, u bu oy har kuni juda charchayapti, uni rosa dam oldirgim keladi.","ru":"Утром Лю Мин отвёз ребёнка в школу. Вернувшись домой, он сразу получил звонок из больницы — его попросили вернуться на работу. Мне кажется, в этом месяце он каждый день очень устаёт; очень хочется, чтобы он отдохнул.","tj":"Субҳ Лю Мин кӯдакро бо мошин ба мактаб бурд. Баъди расондани кӯдак ва баргаштан ба хона, аз беморхона фавран занг заданд ва аз ӯ хостанд ба кор баргардад. Ба назарам, ин моҳ ӯ ҳар рӯз хеле хаста мешавад; мехоҳам хуб истироҳат кунад."}
                ]
            }
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no":1,"title_zh":"结果补语","title_uz":"Natija to‘ldiruvchisi","title_ru":"Результативное дополнение","title_tj":"Пуркунандаи натиҷа",
                "rule_zh":"一些动词或者形容词用在动词后面，表示动作的结果。否定形式是在动词前加“没（有）”，同时去掉“了”。疑问可用“了吗”、“（了）没有”或“动词+没+动词+结果补语”。",
                "rule_uz":"Ba’zi fe’l yoki sifatlar fe’ldan keyin kelib harakat natijasini bildiradi. Inkor uchun fe’l oldiga 没（有） qo‘yiladi va 了 olib tashlanadi. Savol 了吗、（了）没有 yoki V+没+V+natija shaklida tuziladi.",
                "rule_ru":"Некоторые глаголы или прилагательные ставятся после глагола и выражают результат действия. В отрицании перед глаголом ставится 没（有）, а 了 убирается. Вопрос строится с 了吗, （了）没有 или V+没+V+результативное дополнение.",
                "rule_tj":"Баъзе феъл ё сифатҳо баъди феъл омада, натиҷаи амалро нишон медиҳанд. Дар инкор пеш аз феъл 没（有） меояд ва 了 ҳазф мешавад. Савол бо 了吗、（了）没有 ё V+没+V+пуркунандаи натиҷа сохта мешавад.",
                "examples":[
                    {"zh":"菜都做好了。","pinyin":"Cài dōu zuòhǎo le.","uz":"Ovqatlar tayyor bo‘ldi.","ru":"Блюда уже приготовлены.","tj":"Хӯрокҳо тайёр шуданд."},
                    {"zh":"我吃完饭了。","pinyin":"Wǒ chīwán fàn le.","uz":"Men ovqatni yeb bo‘ldim.","ru":"Я закончил есть.","tj":"Ман хӯрокро хӯрда тамом кардам."},
                    {"zh":"小雪今天来晚了。","pinyin":"Xiǎoxuě jīntiān láiwǎn le.","uz":"Xiaoxue bugun kech keldi.","ru":"Сяосюэ сегодня пришла поздно.","tj":"Сяосюэ имрӯз дер омад."},
                    {"zh":"我没吃完饭。","pinyin":"Wǒ méi chīwán fàn.","uz":"Men ovqatni tugatmadim.","ru":"Я не закончил есть.","tj":"Ман хӯрокро тамом накардам."},
                    {"zh":"你吃完饭了吗？","pinyin":"Nǐ chīwán fàn le ma?","uz":"Ovqatni yeb bo‘ldingmi?","ru":"Ты закончил есть?","tj":"Хӯрокро хӯрда тамом кардӣ?"}
                ]
            },
            {
                "no":2,"title_zh":"动词重叠（1）","title_uz":"Fe’l takrorlanishi (1)","title_ru":"Редупликация глагола (1)","title_tj":"Такрори феъл (1)",
                "rule_zh":"动作性比较强、能重复或持续的动词可以重叠使用，表示时间短、数量少、尝试等，语气比较轻松、随意，多用于口语。单音节动词常用“A（一）A”，双音节动词用“ABAB”，离合词用“AAB”。",
                "rule_uz":"Takrorlana yoki davom eta oladigan harakat fe’llari qisqa harakat, oz miqdor yoki sinab ko‘rish ma’nosida takrorlanadi. Bir bo‘g‘inli fe’l A（一）A, ikki bo‘g‘inli fe’l ABAB, ajraluvchi so‘z AAB shaklida keladi.",
                "rule_ru":"Динамические глаголы, которые можно повторять или продолжать, редуплицируются для краткого действия, небольшого количества или попытки. Односложные: A（一）A; двусложные: ABAB; разделяемые: AAB.",
                "rule_tj":"Феълҳои амалие, ки такрор ё идома меёбанд, барои амали кӯтоҳ, миқдори кам ё кӯшиш такрор мешаванд. Феъли якҳиҷоӣ: A（一）A; дуҳиҷоӣ: ABAB; калимаи ҷудошаванда: AAB.",
                "examples":[
                    {"zh":"那你再想一想，你想好了，我来买票。","pinyin":"Nà nǐ zài xiǎng yì xiǎng, nǐ xiǎnghǎo le, wǒ lái mǎi piào.","uz":"Unda yana bir o‘ylab ko‘r, qaror qilsang chiptani men olaman.","ru":"Тогда ещё подумай; когда решишь, билеты куплю я.","tj":"Пас боз як бор фикр кун, вақте қарор кардӣ, чиптаро ман мехарам."},
                    {"zh":"我有点儿累，现在想休息休息。","pinyin":"Wǒ yǒudiǎnr lèi, xiànzài xiǎng xiūxi xiūxi.","uz":"Biroz charchadim, hozir sal dam olmoqchiman.","ru":"Я немного устал и хочу сейчас немного отдохнуть.","tj":"Каме хастаам, ҳоло мехоҳам каме истироҳат кунам."},
                    {"zh":"你能过来帮帮忙吗？","pinyin":"Nǐ néng guòlai bāngbang máng ma?","uz":"Kelib ozgina yordam bera olasanmi?","ru":"Можешь подойти и немного помочь?","tj":"Метавонӣ омада каме кӯмак кунӣ?"}
                ]
            },
            {
                "no":3,"title_zh":"动词重叠（2）","title_uz":"Fe’l takrorlanishi (2)","title_ru":"Редупликация глагола (2)","title_tj":"Такрори феъл (2)",
                "rule_zh":"表达已经发生的情况时，单音节动词的重叠形式是“A了A”；双音节动词一般不能用重叠形式，只能用“AB了一下”；离合词的重叠形式是“A了AB”。",
                "rule_uz":"Sodir bo‘lgan harakatni ifodalaganda bir bo‘g‘inli fe’l A了A shaklida keladi. Ikki bo‘g‘inli fe’l odatda takrorlanmaydi, AB了一下 ishlatiladi. Ajraluvchi so‘z A了AB shaklida keladi.",
                "rule_ru":"Для уже произошедшего действия односложный глагол имеет форму A了A. Двусложный обычно не редуплицируется и употребляется как AB了一下. Разделяемое слово имеет форму A了AB.",
                "rule_tj":"Барои амали аллакай рухдода феъли якҳиҷоӣ шакли A了A мегирад. Феъли дуҳиҷоӣ одатан такрор намешавад ва AB了一下 истифода мешавад. Калимаи ҷудошаванда A了AB мешавад.",
                "examples":[
                    {"zh":"我看了看网上的介绍。","pinyin":"Wǒ kànle kàn wǎngshang de jièshào.","uz":"Internetdagi ma’lumotlarni bir ko‘rib chiqdim.","ru":"Я немного посмотрел информацию в интернете.","tj":"Маълумоти интернетро як назар кардам."},
                    {"zh":"我休息了一下，现在觉得不累了。","pinyin":"Wǒ xiūxile yíxià, xiànzài juéde bú lèi le.","uz":"Biroz dam oldim, hozir charchoq yo‘q.","ru":"Я немного отдохнул и теперь не чувствую усталости.","tj":"Каме истироҳат кардам, ҳоло дигар хаста нестам."},
                    {"zh":"他昨天来帮了帮忙。","pinyin":"Tā zuótiān lái bāngle bāngmáng.","uz":"U kecha kelib biroz yordam berdi.","ru":"Он вчера пришёл и немного помог.","tj":"Ӯ дирӯз омада каме кӯмак кард."}
                ]
            }
        ],
        ensure_ascii=False,
    ),
}
