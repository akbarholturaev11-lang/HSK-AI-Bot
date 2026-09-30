from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(26, 35)),
    "printed_pages": list(range(10, 19)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk2",
    "lesson_order": 2,
    "lesson_code": "NHSK2-L02",
    "title": "还是打车去北大吧",
    "title_pinyin": "Háishi dǎchē qù Běidà ba",
    "goal": json.dumps(
        {
            "uz": "“还是……吧” orqali afzal variantni tavsiya qilish; “多” bilan taxminiy sonni ifodalash; fe’l/fe’lli birikma va ega-kesim birikmasini aniqlovchi sifatida ishlatish; transport va kampus haqida gaplashish.",
            "ru": "Советовать предпочтительный вариант с “还是……吧”; выражать приблизительные числа с “多”; использовать глаголы, глагольные и субъектно-предикативные группы как определения; говорить о транспорте и кампусе.",
            "tj": "Бо “还是……吧” варианти афзалро тавсия кардан; бо “多” шумораи тахминиро ифода кардан; феъл ва ибораҳои феълӣ/мубтадо-хабарро ҳамчун муайянкунанда истифода бурдан; дар бораи нақлиёт ва кампус суҳбат кардан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars Pekin universitetiga borish, kampusni tomosha qilish, kino haqida gaplashish va kampus taassurotlari haqidagi to‘rtta matn/dialog orqali uchta yangi grammatik tuzilmani o‘rgatadi.",
            "ru": "Урок через четыре текста/диалога о дороге в Пекинский университет, прогулке по кампусу, кино и впечатлениях вводит три грамматические конструкции.",
            "tj": "Дарс тавассути чор матн/гуфтугӯ дар бораи рафтан ба Донишгоҳи Пекин, тамошои кампус, кино ва таассурот се сохтори грамматикиро меомӯзонад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no":1,"zh":"公交车","pinyin":"gōngjiāochē","pos":"n.","uz":"avtobus","ru":"автобус","tj":"автобус"},
            {"no":2,"zh":"但","pinyin":"dàn","pos":"conj.","uz":"ammo; lekin","ru":"но; однако","tj":"аммо; лекин"},
            {"no":3,"zh":"车站","pinyin":"chēzhàn","pos":"n.","uz":"bekat; stansiya","ru":"остановка; станция","tj":"истгоҳ"},
            {"no":4,"zh":"远","pinyin":"yuǎn","pos":"adj.","uz":"uzoq","ru":"далёкий","tj":"дур"},
            {"no":5,"zh":"打车","pinyin":"dǎchē","pos":"v.","uz":"taksi tutmoq/minmoq","ru":"взять такси","tj":"таксӣ гирифтан"},
            {"no":6,"zh":"还是","pinyin":"háishi","pos":"adv.","uz":"yaxshisi; ma’quli","ru":"лучше; всё-таки","tj":"беҳтараш"},
            {"no":7,"zh":"啊","pinyin":"a","pos":"part.","uz":"his-hayajon/ma’qullash yuklamasi","ru":"модальная частица эмоции/согласия","tj":"ҳиссачаи эҳсос/розигӣ"},
            {"no":8,"zh":"万","pinyin":"wàn","pos":"num.","uz":"o‘n ming","ru":"десять тысяч","tj":"даҳ ҳазор"},
            {"no":9,"zh":"名","pinyin":"míng","pos":"m./n.","uz":"odamlar uchun hisob so‘zi; o‘rin; nom","ru":"счётное слово для людей; место; имя","tj":"воҳиди ҳисоб барои одам; ҷой; ном"},
            {"no":10,"zh":"网上","pinyin":"wǎngshang","pos":"n.","uz":"internetda","ru":"в интернете","tj":"дар интернет"},
            {"no":11,"zh":"外国","pinyin":"wàiguó","pos":"n.","uz":"chet davlat","ru":"иностранное государство","tj":"кишвари хориҷӣ"},
            {"no":12,"zh":"间","pinyin":"jiān","pos":"m.","uz":"xona/binoning kichik bo‘lagi uchun hisob so‘zi","ru":"счётное слово для комнат","tj":"воҳиди ҳисоб барои ҳуҷра"},
            {"no":13,"zh":"教室","pinyin":"jiàoshì","pos":"n.","uz":"sinfxona","ru":"аудитория; класс","tj":"синфхона"},
            {"no":14,"zh":"票","pinyin":"piào","pos":"n.","uz":"chipta","ru":"билет","tj":"чипта"},
            {"no":15,"zh":"别","pinyin":"bié","pos":"adv.","uz":"qilmang; yaxshisi qilma","ru":"не; лучше не","tj":"накун; беҳтараш не"},
            {"no":16,"zh":"过来","pinyin":"guòlai","pos":"v.","uz":"bu tomonga kelmoq","ru":"подойти; прийти сюда","tj":"ба ин тараф омадан"},
        ],
        ensure_ascii=False,
    ),
    "proper_nouns_json": json.dumps(
        [{"zh":"北京大学","pinyin":"Běijīng Dàxué","en":"Peking University","uz":"Pekin universiteti","ru":"Пекинский университет","tj":"Донишгоҳи Пекин"}],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no":1,"section_label":"课文 1",
                "scene_zh":"在宾馆前台，白家月和安妮向服务员咨询。",
                "scene_uz":"Mehmonxona resepsiyasida Bai Jiayue va Annie xodimdan ma’lumot so‘ramoqda.",
                "scene_ru":"На стойке гостиницы Бай Цзяюэ и Энни спрашивают сотрудника.",
                "scene_tj":"Дар қабули меҳмонхона Бай Ҷяюэ ва Энни аз корманд маълумот мепурсанд.",
                "dialogue":[
                    {"speaker":"Bai Jiayue","zh":"请问，这儿有到北京大学的公交车吗？","pinyin":"Qǐngwèn, zhèr yǒu dào Běijīng Dàxué de gōngjiāochē ma?","uz":"Kechirasiz, bu yerdan Pekin universitetiga boradigan avtobus bormi?","ru":"Скажите, отсюда есть автобус до Пекинского университета?","tj":"Мебахшед, аз ин ҷо то Донишгоҳи Пекин автобус ҳаст?"},
                    {"speaker":"Hotel staff","zh":"有，但车站有点儿远。","pinyin":"Yǒu, dàn chēzhàn yǒudiǎnr yuǎn.","uz":"Bor, lekin bekat biroz uzoq.","ru":"Есть, но остановка немного далеко.","tj":"Ҳаст, аммо истгоҳ каме дур аст."},
                    {"speaker":"Bai Jiayue","zh":"这儿好打车吗？","pinyin":"Zhèr hǎo dǎchē ma?","uz":"Bu yerda taksi tutish osonmi?","ru":"Здесь легко поймать такси?","tj":"Ин ҷо таксӣ гирифтан осон аст?"},
                    {"speaker":"Hotel staff","zh":"好打车。","pinyin":"Hǎo dǎchē.","uz":"Taksi tutish oson.","ru":"Легко.","tj":"Осон аст."},
                    {"speaker":"Bai Jiayue","zh":"谢谢。安妮，我们还是打车去吧。","pinyin":"Xièxie. Ānnī, wǒmen háishi dǎchē qù ba.","uz":"Rahmat. Annie, yaxshisi taksida boraylik.","ru":"Спасибо. Энни, давай лучше поедем на такси.","tj":"Раҳмат. Энни, беҳтараш бо таксӣ равем."},
                    {"speaker":"Annie","zh":"好，没问题。","pinyin":"Hǎo, méi wèntí.","uz":"Xo‘p, muammo yo‘q.","ru":"Хорошо, без проблем.","tj":"Хуб, мушкиле нест."}
                ]
            },
            {
                "block_no":2,"section_label":"课文 2",
                "scene_zh":"在北京大学，白家月和安妮在参观校园。",
                "scene_uz":"Pekin universitetida Bai Jiayue va Annie kampusni tomosha qilmoqda.",
                "scene_ru":"В Пекинском университете Бай Цзяюэ и Энни осматривают кампус.",
                "scene_tj":"Дар Донишгоҳи Пекин Бай Ҷяюэ ва Энни кампусро тамошо мекунанд.",
                "dialogue":[
                    {"speaker":"Bai Jiayue","zh":"学校里人真多啊！","pinyin":"Xuéxiào lǐ rén zhēn duō a!","uz":"Universitetda odam juda ko‘p ekan!","ru":"Как много людей в университете!","tj":"Дар донишгоҳ одам хеле бисёр будааст!"},
                    {"speaker":"Annie","zh":"是啊，北京大学有四万多名学生呢！","pinyin":"Shì a, Běijīng Dàxué yǒu sì wàn duō míng xuésheng ne!","uz":"Ha, Pekin universitetida qirq mingdan ortiq talaba bor!","ru":"Да, в Пекинском университете больше сорока тысяч студентов!","tj":"Ҳа, дар Донишгоҳи Пекин зиёда аз чил ҳазор донишҷӯ ҳаст!"},
                    {"speaker":"Bai Jiayue","zh":"你是怎么知道的？","pinyin":"Nǐ shì zěnme zhīdào de?","uz":"Buni qayerdan bilding?","ru":"Как ты это узнала?","tj":"Инро чӣ тавр фаҳмидӣ?"},
                    {"speaker":"Annie","zh":"是网上说的，网上还说北京大学有三千多名外国学生。","pinyin":"Shì wǎngshang shuō de, wǎngshang hái shuō Běijīng Dàxué yǒu sān qiān duō míng wàiguó xuésheng.","uz":"Internetda yozilgan. Internetda Pekin universitetida uch mingdan ortiq chet ellik talaba borligi ham aytilgan.","ru":"Так написано в интернете; там ещё сказано, что в Пекинском университете более трёх тысяч иностранных студентов.","tj":"Дар интернет гуфта шудааст; он ҷо ҳамчунин навиштааст, ки дар Донишгоҳи Пекин зиёда аз се ҳазор донишҷӯи хориҷӣ ҳаст."},
                    {"speaker":"Bai Jiayue","zh":"我也想来这儿学习。","pinyin":"Wǒ yě xiǎng lái zhèr xuéxí.","uz":"Men ham bu yerga o‘qishga kelishni xohlayman.","ru":"Я тоже хочу приехать сюда учиться.","tj":"Ман ҳам мехоҳам барои таҳсил ба ин ҷо биёям."},
                    {"speaker":"Annie","zh":"那边就有一间教室，我们去看一下吧。","pinyin":"Nàbian jiù yǒu yì jiān jiàoshì, wǒmen qù kàn yíxià ba.","uz":"Ana u tomonda bir sinfxona bor, borib ko‘raylik.","ru":"Вон там как раз есть аудитория, давай посмотрим.","tj":"Он тараф як синфхона ҳаст, биё рафта бинем."}
                ]
            },
            {
                "block_no":3,"section_label":"课文 3",
                "scene_zh":"在北京大学校园里，白家月和安妮看到了电影院。",
                "scene_uz":"Pekin universiteti kampusida Bai Jiayue va Annie kinoteatrni ko‘rdi.",
                "scene_ru":"На кампусе Пекинского университета Бай Цзяюэ и Энни увидели кинотеатр.",
                "scene_tj":"Дар кампуси Донишгоҳи Пекин Бай Ҷяюэ ва Энни кинотеатрро диданд.",
                "dialogue":[
                    {"speaker":"Annie","zh":"家月，你看，学校里有家电影院！","pinyin":"Jiāyuè, nǐ kàn, xuéxiào lǐ yǒu jiā diànyǐngyuàn!","uz":"Jiayue, qara, universitetda kinoteatr bor!","ru":"Цзяюэ, смотри, в университете есть кинотеатр!","tj":"Ҷяюэ, бин, дар донишгоҳ кинотеатр ҳаст!"},
                    {"speaker":"Bai Jiayue","zh":"是啊，电影院还不小。","pinyin":"Shì a, diànyǐngyuàn hái bù xiǎo.","uz":"Ha, kinoteatr ham kichik emas.","ru":"Да, и кинотеатр немаленький.","tj":"Ҳа, кинотеатр ҳам хурд нест."},
                    {"speaker":"Annie","zh":"他们卖的电影票也很便宜。","pinyin":"Tāmen mài de diànyǐngpiào yě hěn piányi.","uz":"Ular sotadigan kino chiptalari ham juda arzon.","ru":"Билеты в кино, которые они продают, тоже очень дешёвые.","tj":"Чиптаҳои кинои онҳо ҳам хеле арзонанд."},
                    {"speaker":"Bai Jiayue","zh":"天啊！有的还不到二十块钱。","pinyin":"Tiān a! Yǒude hái bú dào èrshí kuài qián.","uz":"Voy! Ba’zilari hatto yigirma yuanga ham yetmaydi.","ru":"Ничего себе! Некоторые стоят даже меньше двадцати юаней.","tj":"Вой! Баъзеаш ҳатто ба бист юан ҳам намерасад."},
                    {"speaker":"Annie","zh":"那你想不想去看个电影？","pinyin":"Nà nǐ xiǎng bu xiǎng qù kàn ge diànyǐng?","uz":"Unda film ko‘rgani bormoqchimisan?","ru":"Тогда хочешь сходить посмотреть фильм?","tj":"Пас мехоҳӣ филм тамошо кунӣ?"},
                    {"speaker":"Bai Jiayue","zh":"还是别看电影了，北京大学就很好看！","pinyin":"Háishi bié kàn diànyǐng le, Běijīng Dàxué jiù hěn hǎokàn!","uz":"Yaxshisi film ko‘rmaylik, Pekin universitetining o‘zi juda chiroyli!","ru":"Лучше не будем смотреть фильм — сам Пекинский университет очень красивый!","tj":"Беҳтараш филм набинем, худи Донишгоҳи Пекин хеле зебост!"}
                ]
            },
            {
                "block_no":4,"section_label":"课文 4",
                "scene_zh":"在北京大学门口，白家月给陈天中发信息。",
                "scene_uz":"Pekin universiteti darvozasi oldida Bai Jiayue Chen Tianzhongga xabar yubordi.",
                "scene_ru":"У входа в Пекинский университет Бай Цзяюэ отправила сообщение Чэнь Тяньчжуну.",
                "scene_tj":"Дар даромадгоҳи Донишгоҳи Пекин Бай Ҷяюэ ба Чэн Тянҷун паём фиристод.",
                "dialogue":[
                    {"speaker":"Bai Jiayue","zh":"北京大学很大，有四万多名学生。学校很漂亮，里边还有家电影院，电影票也不贵，我们有时间还想再过来看个电影。","pinyin":"Běijīng Dàxué hěn dà, yǒu sì wàn duō míng xuésheng. Xuéxiào hěn piàoliang, lǐbian hái yǒu jiā diànyǐngyuàn, diànyǐngpiào yě bú guì, wǒmen yǒu shíjiān hái xiǎng zài guòlai kàn ge diànyǐng.","uz":"Pekin universiteti juda katta, qirq mingdan ortiq talabasi bor. Universitet juda chiroyli, ichida yana kinoteatr ham bor, kino chiptalari ham qimmat emas. Vaqtimiz bo‘lsa, yana kelib film ko‘rmoqchimiz.","ru":"Пекинский университет очень большой, здесь более сорока тысяч студентов. Кампус красивый, внутри есть кинотеатр, билеты недорогие. Если будет время, мы хотим снова прийти посмотреть фильм.","tj":"Донишгоҳи Пекин хеле калон аст ва зиёда аз чил ҳазор донишҷӯ дорад. Донишгоҳ зебост, дар дохилаш кинотеатр ҳам ҳаст, чиптаҳо гарон нестанд. Агар вақт дошта бошем, боз омада филм тамошо кардан мехоҳем."}
                ]
            }
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no":1,"title_zh":"固定格式“还是……吧”","title_uz":"“还是……吧” qolipi","title_ru":"Конструкция “还是……吧”","title_tj":"Қолаби “还是……吧”",
                "rule_zh":"“还是……吧”表示在几个可能的选择中，建议采用说话人认为更合适的一种。",
                "rule_uz":"“还是……吧” bir necha variantdan gapiruvchi ma’qul deb hisoblagan variantni tavsiya qiladi.",
                "rule_ru":"“还是……吧” советует выбрать из нескольких вариантов тот, который говорящий считает более подходящим.",
                "rule_tj":"“还是……吧” аз чанд вариант онеро тавсия мекунад, ки гӯянда муносибтар мешуморад.",
                "examples":[
                    {"zh":"我们还是打车去吧。","pinyin":"Wǒmen háishi dǎchē qù ba.","uz":"Yaxshisi taksida boraylik.","ru":"Давай лучше поедем на такси.","tj":"Беҳтараш бо таксӣ равем."},
                    {"zh":"那件衣服很好看，还是买那件吧。","pinyin":"Nà jiàn yīfu hěn hǎokàn, háishi mǎi nà jiàn ba.","uz":"U kiyim chiroyli, yaxshisi o‘shanisini olaylik.","ru":"Та одежда красивая, лучше купить её.","tj":"Он либос зебост, беҳтараш ҳамонро бихарем."},
                    {"zh":"你第一次去北京，还是找个人接你吧。","pinyin":"Nǐ dì yī cì qù Běijīng, háishi zhǎo ge rén jiē nǐ ba.","uz":"Pekinga birinchi marta boryapsan, yaxshisi seni kutib oladigan odam top.","ru":"Ты впервые едешь в Пекин, лучше найди кого-нибудь, кто тебя встретит.","tj":"Бори аввал ба Пекин меравӣ, беҳтараш касеро ёб, ки пешвозат гирад."}
                ]
            },
            {
                "no":2,"title_zh":"用“多”表达概数","title_uz":"“多” bilan taxminiy son","title_ru":"Приблизительные числа с “多”","title_tj":"Шумораи тахминӣ бо “多”",
                "rule_zh":"在数词或数量短语后加“多”，表示比这个数稍多。数词是十的整数倍时，“多”一般紧跟数词；不是十的整数倍时，“多”一般放在量词后。",
                "rule_uz":"Son yoki miqdor birikmasidan keyin “多” qo‘shilib, shu sondan biroz ko‘proq miqdorni bildiradi. O‘nlik sonlarda “多” odatda sondan keyin, boshqa holatlarda o‘lchov so‘zidan keyin keladi.",
                "rule_ru":"“多” после числительного или количественной группы означает немного больше указанного числа. После круглых десятков “多” обычно следует сразу за числом, в других случаях — после счётного слова.",
                "rule_tj":"“多” пас аз шумора ё таркиби миқдорӣ миқдори каме зиёда аз он ададро нишон медиҳад. Бо даҳгонаҳои пурра “多” пас аз адад, дар ҳолатҳои дигар пас аз воҳиди ҳисоб меояд.",
                "examples":[
                    {"zh":"北京大学有四万多名学生呢！","pinyin":"Běijīng Dàxué yǒu sì wàn duō míng xuésheng ne!","uz":"Pekin universitetida qirq mingdan ortiq talaba bor!","ru":"В Пекинском университете больше сорока тысяч студентов!","tj":"Дар Донишгоҳи Пекин зиёда аз чил ҳазор донишҷӯ ҳаст!"},
                    {"zh":"教室里有二十多个学生。","pinyin":"Jiàoshì lǐ yǒu èrshí duō ge xuésheng.","uz":"Sinfda yigirmadan ortiq talaba bor.","ru":"В аудитории больше двадцати студентов.","tj":"Дар синф зиёда аз бист донишҷӯ ҳаст."},
                    {"zh":"这两个苹果五块多钱。","pinyin":"Zhè liǎng ge píngguǒ wǔ kuài duō qián.","uz":"Bu ikki olma besh yuandan sal ko‘proq turadi.","ru":"Эти два яблока стоят чуть больше пяти юаней.","tj":"Ин ду себ каме бештар аз панҷ юан меистад."}
                ]
            },
            {
                "no":3,"title_zh":"动词或动词性短语、主谓短语作定语","title_uz":"Fe’l/fe’lli va ega-kesimli birikmalarning aniqlovchi bo‘lishi","title_ru":"Глаголы, глагольные и субъектно-предикативные группы как определения","title_tj":"Феъл ва ибораҳои феълӣ/мубтадо-хабар ҳамчун муайянкунанда",
                "rule_zh":"动词、动词性短语或主谓短语可以放在名词前作定语，说明名词的特征、状态或相关动作。",
                "rule_uz":"Fe’l, fe’lli birikma yoki ega-kesim birikmasi ot oldidan kelib, uning belgisi, holati yoki unga bog‘liq harakatni ko‘rsatishi mumkin.",
                "rule_ru":"Глагол, глагольная или субъектно-предикативная группа может стоять перед существительным как определение и описывать его признак, состояние или связанное действие.",
                "rule_tj":"Феъл, ибораи феълӣ ё таркиби мубтадо-хабар пеш аз исм омада, хусусият, ҳолат ё амали вобастаи онро мефаҳмонад.",
                "examples":[
                    {"zh":"他们卖的电影票也很便宜。","pinyin":"Tāmen mài de diànyǐngpiào yě hěn piányi.","uz":"Ular sotadigan kino chiptalari ham arzon.","ru":"Билеты, которые они продают, тоже дешёвые.","tj":"Чиптаҳои киноие, ки онҳо мефурӯшанд, ҳам арзонанд."},
                    {"zh":"现在学中文的学生很多。","pinyin":"Xiànzài xué Zhōngwén de xuésheng hěn duō.","uz":"Hozir xitoy tilini o‘rganayotgan talabalar ko‘p.","ru":"Сейчас много студентов, изучающих китайский.","tj":"Ҳоло донишҷӯёне, ки чинӣ меомӯзанд, бисёранд."},
                    {"zh":"这是朋友给我的杯子。","pinyin":"Zhè shì péngyou gěi wǒ de bēizi.","uz":"Bu do‘stim menga bergan piyola.","ru":"Это чашка, которую мне подарил друг.","tj":"Ин пиёлаест, ки дӯстам ба ман додааст."}
                ]
            }
        ],
        ensure_ascii=False,
    ),
}
