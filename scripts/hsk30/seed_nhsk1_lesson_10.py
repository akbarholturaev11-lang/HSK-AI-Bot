from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程1",
    "pdf_path": "HSK 3.0 PDF/新HSK教程1.pdf",
    "pdf_pages": [84, 85, 86, 87, 88, 89, 90, 91],
    "printed_pages": [70, 71, 72, 73, 74, 75, 76, 77],
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk1",
    "lesson_order": 10,
    "lesson_code": "NHSK1-L10",
    "title": "这儿的苹果真便宜！",
    "title_pinyin": "Zhèr de píngguǒ zhēn piányi!",
    "goal": json.dumps(
        {
            "uz": "Mahsulot narxini tushunish va aytish; pul miqdorini xitoycha ifodalash; sifat-kesimli gaplardan foydalanish; “怎么样” bilan fikr yoki holatni so‘rash.",
            "ru": "Понимать и называть цены товаров; выражать денежные суммы; использовать предложения с прилагательным-сказуемым; спрашивать мнение или состояние с “怎么样”.",
            "tj": "Нархи молро фаҳмидан ва гуфтан; маблағи пулро ба чинӣ ифода кардан; ҷумлаҳои сифатӣ-хабариро истифода бурдан; бо “怎么样” фикр ё ҳолатро пурсидан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars stakan, meva va kiyim xaridi haqidagi uchta dialog orqali pul miqdori, sifat-kesimli gap va “怎么样” ni o‘rgatadi.",
            "ru": "Урок через три диалога о покупке чашки, фруктов и одежды вводит денежные суммы, прилагательное-сказуемое и “怎么样”.",
            "tj": "Дарс тавассути се гуфтугӯ дар бораи харидани пиёла, мева ва либос маблағи пул, ҷумлаи сифатӣ-хабарӣ ва “怎么样”-ро меомӯзонад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no":1,"zh":"杯子","pinyin":"bēizi","pos":"n.","uz":"piyola; stakan","ru":"чашка; стакан","tj":"пиёла; стакан"},
            {"no":2,"zh":"售货员","pinyin":"shòuhuòyuán","pos":"n.","uz":"sotuvchi","ru":"продавец","tj":"фурӯшанда"},
            {"no":3,"zh":"这边","pinyin":"zhèbiān","pos":"pron.","uz":"bu yer; bu tomon","ru":"здесь; эта сторона","tj":"ин ҷо; ин тараф"},
            {"no":4,"zh":"钱","pinyin":"qián","pos":"n.","uz":"pul","ru":"деньги","tj":"пул"},
            {"no":5,"zh":"这些","pinyin":"zhèxiē","pos":"pron.","uz":"bular","ru":"эти","tj":"инҳо"},
            {"no":6,"zh":"块","pinyin":"kuài","pos":"m.","uz":"yuan uchun og‘zaki hisob birligi","ru":"разг. счётная единица юаня","tj":"воҳиди гуфтугӯии юан"},
            {"no":7,"zh":"那些","pinyin":"nàxiē","pos":"pron.","uz":"anavilar; o‘shalar","ru":"те","tj":"онҳо; ҳамонҳо"},
            {"no":8,"zh":"这儿","pinyin":"zhèr","pos":"pron.","uz":"bu yer","ru":"здесь","tj":"ин ҷо"},
            {"no":9,"zh":"水果","pinyin":"shuǐguǒ","pos":"n.","uz":"meva","ru":"фрукты","tj":"мева"},
            {"no":10,"zh":"少","pinyin":"shǎo","pos":"adj.","uz":"kam","ru":"мало; немного","tj":"кам"},
            {"no":11,"zh":"斤","pinyin":"jīn","pos":"m.","uz":"jin (500 g)","ru":"цзинь (500 г)","tj":"ҷин (500 г)"},
            {"no":12,"zh":"苹果","pinyin":"píngguǒ","pos":"n.","uz":"olma","ru":"яблоко","tj":"себ"},
            {"no":13,"zh":"便宜","pinyin":"piányi","pos":"adj.","uz":"arzon","ru":"дешёвый","tj":"арзон"},
            {"no":14,"zh":"商店","pinyin":"shāngdiàn","pos":"n.","uz":"do‘kon","ru":"магазин","tj":"мағоза"},
            {"no":15,"zh":"衣服","pinyin":"yīfu","pos":"n.","uz":"kiyim","ru":"одежда","tj":"либос"},
            {"no":16,"zh":"件","pinyin":"jiàn","pos":"m.","uz":"kiyim uchun o‘lchov so‘zi","ru":"счётное слово для одежды","tj":"воҳиди ҳисоб барои либос"},
            {"no":17,"zh":"元","pinyin":"yuán","pos":"m.","uz":"yuan","ru":"юань","tj":"юан"},
            {"no":18,"zh":"怎么样","pinyin":"zěnmeyàng","pos":"pron.","uz":"qanday; qanday deb o‘ylaysan","ru":"как; как насчёт","tj":"чӣ хел; чӣ гуна"},
            {"no":19,"zh":"贵","pinyin":"guì","pos":"adj.","uz":"qimmat","ru":"дорогой","tj":"гарон"},
            {"no":20,"zh":"穿","pinyin":"chuān","pos":"v.","uz":"kiymoq","ru":"носить; надевать","tj":"пӯшидан"},
            {"no":21,"zh":"女","pinyin":"nǚ","pos":"adj.","uz":"ayol; qiz bolaga oid","ru":"женский; женщина","tj":"занона; зан"},
            {"no":22,"zh":"男","pinyin":"nán","pos":"adj.","uz":"erkak; o‘g‘il bolaga oid","ru":"мужской; мужчина","tj":"мардона; мард"},
            {"no":23,"zh":"那儿","pinyin":"nàr","pos":"pron.","uz":"u yer","ru":"там","tj":"он ҷо"},
        ],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no":1,"section_label":"课文 1",
                "scene_zh":"在一家小店，王一雪在买杯子。",
                "scene_en":"In a small shop, Wang Yixue was buying a cup.",
                "scene_uz":"Kichik do‘konda Wang Yixue piyola sotib olmoqda.",
                "scene_ru":"В маленьком магазине Ван Исюэ покупает чашку.",
                "scene_tj":"Дар як мағозаи хурд Ван Исюэ пиёла мехарад.",
                "dialogue":[
                    {"speaker":"Wang Yixue","zh":"请问，有杯子吗？","pinyin":"Qǐngwèn, yǒu bēizi ma?","en":"Excuse me, do you have any cups?","uz":"Kechirasiz, piyola bormi?","ru":"Извините, у вас есть чашки?","tj":"Мебахшед, пиёла доред?"},
                    {"speaker":"Shop assistant","zh":"有，杯子在这边。","pinyin":"Yǒu, bēizi zài zhèbiān.","en":"Yes, the cups are over here.","uz":"Ha, piyolalar bu yerda.","ru":"Да, чашки здесь.","tj":"Ҳа, пиёлаҳо ин ҷоанд."},
                    {"speaker":"Wang Yixue","zh":"多少钱一个？","pinyin":"Duōshao qián yí ge?","en":"How much is one?","uz":"Bittasi qancha turadi?","ru":"Сколько стоит одна?","tj":"Яктоаш чанд пул?"},
                    {"speaker":"Shop assistant","zh":"这些五块钱一个，那些十块钱一个。","pinyin":"Zhèxiē wǔ kuài qián yí ge, nàxiē shí kuài qián yí ge.","en":"These are five yuan each, and those are ten yuan each.","uz":"Bularning bittasi 5 yuan, anavilarning bittasi 10 yuan.","ru":"Эти по 5 юаней, а те по 10 юаней.","tj":"Инҳо яктоӣ 5 юан, онҳо яктоӣ 10 юан."},
                    {"speaker":"Wang Yixue","zh":"我买这个吧。","pinyin":"Wǒ mǎi zhège ba.","en":"I'll take this one, please.","uz":"Men mana bunisini olaman.","ru":"Я возьму эту.","tj":"Ман ҳаминро мегирам."},
                ]
            },
            {
                "block_no":2,"section_label":"课文 2",
                "scene_zh":"在菜市场，王一雪在买水果。",
                "scene_en":"At the market, Wang Yixue was buying fruit.",
                "scene_uz":"Bozorda Wang Yixue meva sotib olmoqda.",
                "scene_ru":"На рынке Ван Исюэ покупает фрукты.",
                "scene_tj":"Дар бозор Ван Исюэ мева мехарад.",
                "dialogue":[
                    {"speaker":"Wang Yixue","zh":"这儿的水果真不少！","pinyin":"Zhèr de shuǐguǒ zhēn bù shǎo!","en":"There's so much fruit here!","uz":"Bu yerda meva juda ko‘p ekan!","ru":"Здесь так много фруктов!","tj":"Ин ҷо мева хеле бисёр будааст!"},
                    {"speaker":"Vendor","zh":"您想买什么？","pinyin":"Nín xiǎng mǎi shénme?","en":"What would you like to buy?","uz":"Nima sotib olmoqchisiz?","ru":"Что вы хотите купить?","tj":"Чӣ харидан мехоҳед?"},
                    {"speaker":"Wang Yixue","zh":"我想买两斤苹果。","pinyin":"Wǒ xiǎng mǎi liǎng jīn píngguǒ.","en":"I'd like two jin of apples, please.","uz":"Ikki jin olma olmoqchiman.","ru":"Я хочу купить два цзиня яблок.","tj":"Ман мехоҳам ду ҷин себ харам."},
                    {"speaker":"Vendor","zh":"苹果三块五一斤。这些七块二，七块钱吧。","pinyin":"Píngguǒ sān kuài wǔ yì jīn. Zhèxiē qī kuài èr, qī kuài qián ba.","en":"The apples are 3.5 yuan per jin. That's 7.2 yuan in total—let's round it down to 7 yuan.","uz":"Olma bir jiniga 3,5 yuan. Bular 7,2 yuan bo‘ladi, 7 yuan bo‘lsin.","ru":"Яблоки по 3,5 юаня за цзинь. Всего 7,2 юаня — пусть будет 7.","tj":"Себ як ҷин 3,5 юан. Ҳамагӣ 7,2 юан мешавад, 7 юан диҳед."},
                    {"speaker":"Wang Yixue","zh":"好的，这儿的苹果真便宜！","pinyin":"Hǎo de, zhèr de píngguǒ zhēn piányi!","en":"Great! The apples here are really affordable!","uz":"Xo‘p, bu yerdagi olmalar juda arzon ekan!","ru":"Хорошо, яблоки здесь действительно дешёвые!","tj":"Хуб, себҳои ин ҷо воқеан арзонанд!"},
                ]
            },
            {
                "block_no":3,"section_label":"课文 3",
                "scene_zh":"在商场里，刘明和王一雪在给孩子买衣服。",
                "scene_en":"In the shopping mall, Liu Ming and Wang Yixue were shopping for clothes for their children.",
                "scene_uz":"Savdo markazida Liu Ming va Wang Yixue bolalariga kiyim sotib olmoqda.",
                "scene_ru":"В торговом центре Лю Мин и Ван Исюэ покупают одежду детям.",
                "scene_tj":"Дар маркази савдо Лю Мин ва Ван Исюэ барои фарзандонашон либос мехаранд.",
                "dialogue":[
                    {"speaker":"Wang Yixue","zh":"这家商店衣服真多！这件一百元，怎么样？","pinyin":"Zhè jiā shāngdiàn yīfu zhēn duō! Zhè jiàn yìbǎi yuán, zěnmeyàng?","en":"There are so many clothes in this store! This one is 100 yuan. What do you think?","uz":"Bu do‘konda kiyim juda ko‘p! Bu bittasi 100 yuan, qanday?","ru":"В этом магазине так много одежды! Эта вещь стоит 100 юаней. Как тебе?","tj":"Дар ин мағоза либос хеле бисёр! Ин дона 100 юан аст, чӣ хел?"},
                    {"speaker":"Liu Ming","zh":"好看，也不贵。","pinyin":"Hǎokàn, yě bú guì.","en":"It looks great, and it's not expensive.","uz":"Chiroyli, qimmat ham emas.","ru":"Красиво и недорого.","tj":"Зебо, гарон ҳам нест."},
                    {"speaker":"Wang Yixue","zh":"小雪能穿，买一件吧。","pinyin":"Xiǎoxuě néng chuān, mǎi yí jiàn ba.","en":"Xiaoxue can wear it. Let's get one.","uz":"Xiaoxuega mos keladi, bittasini olaylik.","ru":"Сяосюэ сможет носить. Давай купим одну.","tj":"Сяосюэ пӯшида метавонад, якто бихарем."},
                    {"speaker":"Liu Ming","zh":"好的。小明能穿吗？","pinyin":"Hǎo de. Xiǎomíng néng chuān ma?","en":"Okay. Do you think Xiaoming can wear it too?","uz":"Xo‘p. Xiaoming ham kiya oladimi?","ru":"Хорошо. Сяомин тоже сможет носить?","tj":"Хуб. Сяомин ҳам пӯшида метавонад?"},
                    {"speaker":"Wang Yixue","zh":"不能。这些是女孩子穿的衣服，男孩子的衣服在那儿。","pinyin":"Bù néng. Zhèxiē shì nǚ háizi chuān de yīfu, nán háizi de yīfu zài nàr.","en":"No. These are girls' clothes. The boys' section is over there.","uz":"Yo‘q. Bular qizlar kiyadigan kiyimlar, o‘g‘il bolalar kiyimi u yerda.","ru":"Нет. Это одежда для девочек, одежда для мальчиков там.","tj":"Не. Инҳо либоси духтаронаанд, либоси писарона он ҷост."},
                    {"speaker":"Liu Ming","zh":"好的。","pinyin":"Hǎo de.","en":"Alright.","uz":"Xo‘p.","ru":"Хорошо.","tj":"Хуб."},
                ]
            },
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no":1,"title_zh":"钱数的表达","title_uz":"Pul miqdorini ifodalash","title_ru":"Выражение денежной суммы","title_tj":"Ифодаи маблағи пул",
                "rule_zh":"人民币的单位由大到小是“元、角、分”，口语中也分别说“块、毛、分”。",
                "rule_en":"The units of RMB from larger to smaller are yuan, jiao and fen; colloquially 元/角 are often called 块/毛.",
                "rule_uz":"RMB birliklari kattadan kichikka 元、角、分; og‘zaki nutqda 元 ko‘pincha 块, 角 esa 毛 deyiladi.",
                "rule_ru":"Единицы RMB от крупной к мелкой: 元、角、分; в разговорной речи 元 часто называют 块, а 角 — 毛.",
                "rule_tj":"Воҳидҳои RMB аз калон ба хурд 元、角、分 мебошанд; дар гуфтор 元-ро 块 ва 角-ро 毛 мегӯянд.",
                "examples":[
                    {"zh":"三块二","pinyin":"sān kuài èr","uz":"3 yuan 2 mao","ru":"3 юаня 2 мао","tj":"3 юан 2 мао"},
                    {"zh":"六块零两分","pinyin":"liù kuài líng liǎng fēn","uz":"6 yuan 2 fen","ru":"6 юаней 2 фэня","tj":"6 юан 2 фэн"},
                    {"zh":"二百零二块两毛","pinyin":"èrbǎi líng èr kuài liǎng máo","uz":"202 yuan 2 mao","ru":"202 юаня 2 мао","tj":"202 юан 2 мао"},
                ]
            },
            {
                "no":2,"title_zh":"形容词谓语句","title_uz":"Sifat-kesimli gap","title_ru":"Предложение с прилагательным-сказуемым","title_tj":"Ҷумла бо хабари сифатӣ",
                "rule_zh":"形容词可以直接作谓语，前面可用程度副词或否定副词。",
                "rule_en":"Adjectives can be used directly as predicates, with adverbs of degree or negative adverbs optionally placed before them.",
                "rule_uz":"Sifat to‘g‘ridan-to‘g‘ri kesim bo‘la oladi; oldidan daraja ravishi yoki inkor ravishi kelishi mumkin.",
                "rule_ru":"Прилагательное может непосредственно выступать сказуемым; перед ним могут стоять наречие степени или отрицание.",
                "rule_tj":"Сифат метавонад бевосита хабар шавад; пеш аз он зарфи дараҷа ё инкор омада метавонад.",
                "examples":[
                    {"zh":"这儿的水果真不少！","pinyin":"Zhèr de shuǐguǒ zhēn bù shǎo!","uz":"Bu yerda meva juda ko‘p!","ru":"Здесь очень много фруктов!","tj":"Ин ҷо мева хеле бисёр!"},
                    {"zh":"我的房间不大。","pinyin":"Wǒ de fángjiān bú dà.","uz":"Mening xonam katta emas.","ru":"Моя комната небольшая.","tj":"Ҳуҷраи ман калон нест."},
                    {"zh":"那个苹果好吃。","pinyin":"Nàge píngguǒ hǎochī.","uz":"O‘sha olma mazali.","ru":"То яблоко вкусное.","tj":"Он себ болаззат аст."},
                ]
            },
            {
                "no":3,"title_zh":"疑问代词“怎么样”","title_uz":"“怎么样” so‘roq olmoshi","title_ru":"Вопросительное местоимение “怎么样”","title_tj":"Ҷонишини саволии “怎么样”",
                "rule_zh":"“怎么样”用来询问看法或某事物的性质、情况等。基本结构：……怎么样？",
                "rule_en":"“怎么样” is used to ask for opinions or inquire about the nature, condition, or situation of something.",
                "rule_uz":"“怎么样” fikrni yoki biror narsaning xususiyati/holatini so‘rash uchun ishlatiladi.",
                "rule_ru":"“怎么样” используется для запроса мнения или выяснения свойства/состояния чего-либо.",
                "rule_tj":"“怎么样” барои пурсидани фикр ё ҳолат/хусусияти чизе истифода мешавад.",
                "examples":[
                    {"zh":"这个杯子怎么样？","pinyin":"Zhège bēizi zěnmeyàng?","uz":"Bu piyola qanday?","ru":"Как эта чашка?","tj":"Ин пиёла чӣ хел?"},
                    {"zh":"这本书怎么样？","pinyin":"Zhè běn shū zěnmeyàng?","uz":"Bu kitob qanday?","ru":"Как эта книга?","tj":"Ин китоб чӣ хел?"},
                    {"zh":"这个菜怎么样？","pinyin":"Zhège cài zěnmeyàng?","uz":"Bu taom qanday?","ru":"Как это блюдо?","tj":"Ин таом чӣ хел?"},
                ]
            }
        ],
        ensure_ascii=False,
    ),
}
