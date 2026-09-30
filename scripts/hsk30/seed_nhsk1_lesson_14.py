from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程1",
    "pdf_path": "HSK 3.0 PDF/新HSK教程1.pdf",
    "pdf_pages": [117, 118, 119, 120, 121, 122, 123, 124, 125],
    "printed_pages": [103, 104, 105, 106, 107, 108, 109, 110, 111],
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk1",
    "lesson_order": 14,
    "lesson_code": "NHSK1-L14",
    "title": "我看了一个电影",
    "title_pinyin": "Wǒ kànle yí ge diànyǐng",
    "goal": json.dumps(
        {
            "uz": "Fe’ldan keyingi “了（2）” bilan tugallangan harakatni ifodalash; 离合词 ning ajralish xususiyatini tushunish; “都” bilan umumlashtirish; o‘qish jarayoni va o‘rgangan narsalarni tasvirlash.",
            "ru": "Выражать завершённое действие с аспектуальной частицей “了（2）”; понимать разделяемые слова; использовать “都” для обобщения; описывать прогресс в обучении.",
            "tj": "Бо ҳиссачаи намудии “了（2）” амали анҷомёфтаро ифода кардан; хусусияти калимаҳои ҷудошавандаро фаҳмидан; бо “都” умумисозӣ кардан; пешрафти омӯзишро тасвир кардан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars safardan qaytish, xitoycha gapirish/yozish va bolalarning maktabi haqidagi uchta dialog orqali “了（2）”, 离合词 va “都” ni o‘rgatadi.",
            "ru": "Урок через три диалога о возвращении из поездки, китайской речи/письме и школе детей вводит “了（2）”, разделяемые слова и “都”.",
            "tj": "Дарс тавассути се гуфтугӯ дар бораи бозгашт аз сафар, гуфтан/навиштани чинӣ ва мактаби кӯдакон “了（2）”, калимаҳои ҷудошаванда ва “都”-ро меомӯзонад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no":1,"zh":"上","pinyin":"shàng","pos":"v.","uz":"chiqmoq; transportga minmoq","ru":"подниматься; садиться в транспорт","tj":"баромадан; ба нақлиёт савор шудан"},
            {"no":2,"zh":"火车","pinyin":"huǒchē","pos":"n.","uz":"poyezd","ru":"поезд","tj":"қатор"},
            {"no":3,"zh":"中午","pinyin":"zhōngwǔ","pos":"n.","uz":"tush payti","ru":"полдень","tj":"нисфирӯзӣ"},
            {"no":4,"zh":"开","pinyin":"kāi","pos":"v.","uz":"jo‘namoq (transport)","ru":"отправляться о транспорте","tj":"ҳаракат кардан; рафтан (нақлиёт)"},
            {"no":5,"zh":"有些","pinyin":"yǒuxiē","pos":"pron.","uz":"ba’zilar; ayrim","ru":"некоторые","tj":"баъзе"},
            {"no":6,"zh":"有的","pinyin":"yǒude","pos":"pron.","uz":"ba’zilar","ru":"некоторые","tj":"баъзе"},
            {"no":7,"zh":"了","pinyin":"le","pos":"part.","uz":"tugallangan harakat aspekt yuklamasi","ru":"аспектуальная частица завершённости","tj":"ҳиссачаи намуди амали анҷомёфта"},
            {"no":8,"zh":"写","pinyin":"xiě","pos":"v.","uz":"yozmoq","ru":"писать","tj":"навиштан"},
            {"no":9,"zh":"都","pinyin":"dōu","pos":"adv.","uz":"hammasi; barchasi","ru":"все; оба","tj":"ҳама; ҳар ду"},
            {"no":10,"zh":"听见","pinyin":"tīngjiàn","pos":"v.","uz":"eshitmoq","ru":"услышать","tj":"шунидан"},
            {"no":11,"zh":"不要","pinyin":"búyào","pos":"adv.","uz":"qilmang; kerak emas","ru":"не надо; не делайте","tj":"накунед; лозим нест"},
            {"no":12,"zh":"说话","pinyin":"shuōhuà","pos":"v.","uz":"gapirmoq","ru":"говорить; разговаривать","tj":"гап задан"},
            {"no":13,"zh":"听","pinyin":"tīng","pos":"v.","uz":"tinglamoq; eshitmoq","ru":"слушать; слышать","tj":"гӯш кардан; шунидан"},
            {"no":14,"zh":"哪些","pinyin":"nǎxiē","pos":"pron.","uz":"qaysilar","ru":"какие; которые","tj":"кадомҳо"},
            {"no":15,"zh":"字","pinyin":"zì","pos":"n.","uz":"ieroglif; belgi; so‘z","ru":"иероглиф; знак; слово","tj":"иероглиф; аломат; калима"},
            {"no":16,"zh":"明年","pinyin":"míngnián","pos":"n.","uz":"kelasi yil","ru":"следующий год","tj":"соли оянда"},
            {"no":17,"zh":"上","pinyin":"shàng","pos":"v.","uz":"belgilangan vaqtda boshlamoq/qatnashmoq","ru":"начинать/посещать в установленное время","tj":"дар вақти муайян оғоз/иштирок кардан"},
            {"no":18,"zh":"中学","pinyin":"zhōngxué","pos":"n.","uz":"o‘rta maktab","ru":"средняя школа","tj":"мактаби миёна"},
            {"no":19,"zh":"小学","pinyin":"xiǎoxué","pos":"n.","uz":"boshlang‘ich maktab","ru":"начальная школа","tj":"мактаби ибтидоӣ"},
            {"no":20,"zh":"中学生","pinyin":"zhōngxuéshēng","pos":"n.","uz":"o‘rta maktab o‘quvchisi","ru":"ученик средней школы","tj":"хонандаи мактаби миёна"},
            {"no":21,"zh":"小学生","pinyin":"xiǎoxuéshēng","pos":"n.","uz":"boshlang‘ich maktab o‘quvchisi","ru":"ученик начальной школы","tj":"хонандаи мактаби ибтидоӣ"},
            {"no":22,"zh":"上学","pinyin":"shàngxué","pos":"v.","uz":"maktabga bormoq; o‘qishni boshlamoq","ru":"идти в школу; начать учиться","tj":"ба мактаб рафтан; таҳсилро оғоз кардан"},
            {"no":23,"zh":"他们","pinyin":"tāmen","pos":"pron.","uz":"ular","ru":"они; их","tj":"онҳо"},
            {"no":24,"zh":"她们","pinyin":"tāmen","pos":"pron.","uz":"ular (ayollar)","ru":"они о женщинах; их","tj":"онҳо (занон)"},
            {"no":25,"zh":"它们","pinyin":"tāmen","pos":"pron.","uz":"ular (narsalar/hayvonlar)","ru":"они о предметах/животных; их","tj":"онҳо (чизҳо/ҳайвонот)"},
            {"no":26,"zh":"晚","pinyin":"wǎn","pos":"adj.","uz":"kech","ru":"поздний; поздно","tj":"дер"},
        ],
        ensure_ascii=False,
    ),
    "proper_nouns_json": json.dumps(
        [
            {"zh":"汉语","pinyin":"Hànyǔ","en":"Chinese language","uz":"xitoy tili","ru":"китайский язык","tj":"забони чинӣ"},
            {"zh":"汉字","pinyin":"Hànzì","en":"Chinese character","uz":"xitoy ieroglifi","ru":"китайский иероглиф","tj":"иероглифи чинӣ"},
        ],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no":1,"section_label":"课文 1",
                "scene_zh":"在教室里，下课后，白家月和陈天中在谈论上一次课外旅行。",
                "scene_en":"After class, Bai Jiayue and Chen Tianzhong were talking about their last school trip in the classroom.",
                "scene_uz":"Sinfda darsdan keyin Bai Jiayue va Chen Tianzhong oldingi sayohat haqida suhbatlashmoqda.",
                "scene_ru":"В аудитории после занятия Бай Цзяюэ и Чэнь Тяньчжун обсуждают прошлую поездку.",
                "scene_tj":"Дар синф пас аз дарс Бай Ҷяюэ ва Чэн Тянҷун сафари гузаштаро муҳокима мекунанд.",
                "dialogue":[
                    {"speaker":"Bai Jiayue","zh":"你们上火车后看见王老师了吗？","pinyin":"Nǐmen shàng huǒchē hòu kànjiàn Wáng lǎoshī le ma?","en":"Did you see Ms. Wang after boarding the train?","uz":"Poyezdga chiqqaningizdan keyin ustoz Wangni ko‘rdingizmi?","ru":"После посадки в поезд вы видели преподавателя Ван?","tj":"Баъди савор шудан ба қатор устод Ванро дидед?"},
                    {"speaker":"Chen Tianzhong","zh":"没看见。中午车开以后，有些人睡觉，有些人看书，有些人听歌。","pinyin":"Méi kànjiàn. Zhōngwǔ chē kāi yǐhòu, yǒuxiē rén shuìjiào, yǒuxiē rén kàn shū, yǒuxiē rén tīng gē.","en":"No, I didn't. After the train departed at noon, some people were reading, while others fell asleep.","uz":"Yo‘q. Tushda poyezd jo‘nagach, ba’zilar uxladilar, ba’zilar kitob o‘qidilar, ba’zilar musiqa tingladilar.","ru":"Нет. После отправления поезда в полдень одни спали, другие читали, третьи слушали песни.","tj":"Не. Баъди нисфирӯзӣ қатор рафт, баъзеҳо хобиданд, баъзеҳо китоб хонданд, баъзеҳо суруд гӯш карданд."},
                    {"speaker":"Bai Jiayue","zh":"你呢？","pinyin":"Nǐ ne?","en":"What about you?","uz":"Sen-chi?","ru":"А ты?","tj":"Ту чӣ?"},
                    {"speaker":"Chen Tianzhong","zh":"我看了一个电影。","pinyin":"Wǒ kànle yí ge diànyǐng.","en":"I watched a movie.","uz":"Men bitta film ko‘rdim.","ru":"Я посмотрел фильм.","tj":"Ман як филм тамошо кардам."},
                ]
            },
            {
                "block_no":2,"section_label":"课文 2",
                "scene_zh":"在课堂上，王一飞询问学生们的学习情况。",
                "scene_en":"In class, Wang Yifei was asking the students about their learning progress.",
                "scene_uz":"Darsda Wang Yifei talabalarining o‘qish holatini so‘ramoqda.",
                "scene_ru":"На занятии Ван Ифэй спрашивает студентов об их успехах в учёбе.",
                "scene_tj":"Дар дарс Ван Ифэй аз донишҷӯён дар бораи пешрафти таҳсил мепурсад.",
                "dialogue":[
                    {"speaker":"Wang Yifei","zh":"你们会说汉语了，也会写汉字了吗？","pinyin":"Nǐmen huì shuō Hànyǔ le, yě huì xiě Hànzì le ma?","en":"You can speak Chinese now. Can you also write Chinese characters?","uz":"Endi xitoycha gapira olasizlar, xitoy ierogliflarini ham yoza olasizlarmi?","ru":"Теперь вы умеете говорить по-китайски. А писать иероглифы тоже умеете?","tj":"Ҳоло бо чинӣ гап зада метавонед, иероглифҳои чиниро ҳам навишта метавонед?"},
                    {"speaker":"Bai Jiayue","zh":"我们都会写了。","pinyin":"Wǒmen dōu huì xiě le.","en":"We can all write them now.","uz":"Hammamiz yoza olamiz.","ru":"Мы все уже умеем писать.","tj":"Ҳамаамон навишта метавонем."},
                    {"speaker":"Chen Tianzhong","zh":"老师，我听不见。","pinyin":"Lǎoshī, wǒ tīng bu jiàn.","en":"Teacher, I can't hear you.","uz":"Ustoz, eshitmayapman.","ru":"Преподаватель, я не слышу.","tj":"Устод, ман намешунавам."},
                    {"speaker":"Wang Yifei","zh":"请大家不要说话！请听老师的问题：你们都会写哪些汉字了？","pinyin":"Qǐng dàjiā búyào shuōhuà! Qǐng tīng lǎoshī de wèntí: nǐmen dōu huì xiě nǎxiē Hànzì le?","en":"Everyone, please stop talking! Listen to my question: Which Chinese characters can you write?","uz":"Hamma gapirmasin! Ustozning savolini tinglang: qaysi xitoy ierogliflarini yoza olasizlar?","ru":"Пожалуйста, не разговаривайте! Слушайте вопрос преподавателя: какие иероглифы вы уже умеете писать?","tj":"Лутфан, гап назанед! Саволи устодро гӯш кунед: кадом иероглифҳои чиниро навишта метавонед?"},
                    {"speaker":"Chen Tianzhong","zh":"我会写这些字了，您看！","pinyin":"Wǒ huì xiě zhèxiē zì le, nín kàn!","en":"I can write these characters. Look!","uz":"Men mana bu ierogliflarni yoza olaman, qarang!","ru":"Я уже умею писать эти иероглифы, посмотрите!","tj":"Ман ин иероглифҳоро навишта метавонам, бинед!"},
                ]
            },
            {
                "block_no":3,"section_label":"课文 3",
                "scene_zh":"在家里，刘明和王一雪在谈论孩子的升学情况。",
                "scene_en":"At home, Liu Ming and Wang Yixue were talking about their children's school admission.",
                "scene_uz":"Uyda Liu Ming va Wang Yixue bolalarining keyingi maktabga o‘tishi haqida gaplashmoqda.",
                "scene_ru":"Дома Лю Мин и Ван Исюэ обсуждают поступление детей в следующую школу.",
                "scene_tj":"Дар хона Лю Мин ва Ван Исюэ дар бораи гузаштани фарзандон ба мактаби нав суҳбат мекунанд.",
                "dialogue":[
                    {"speaker":"Liu Ming","zh":"明年女儿上中学。","pinyin":"Míngnián nǚ'ér shàng zhōngxué.","en":"Our daughter will start middle school next year.","uz":"Kelasi yil qizimiz o‘rta maktabga boradi.","ru":"В следующем году дочь пойдёт в среднюю школу.","tj":"Соли оянда духтарамон ба мактаби миёна меравад."},
                    {"speaker":"Wang Yixue","zh":"对。儿子也上小学了。","pinyin":"Duì. Érzi yě shàng xiǎoxué le.","en":"That's right. Our son will also start primary school.","uz":"Ha. O‘g‘limiz ham boshlang‘ich maktabga boradi.","ru":"Да. Сын тоже пойдёт в начальную школу.","tj":"Ҳа. Писарамон ҳам ба мактаби ибтидоӣ меравад."},
                    {"speaker":"Liu Ming","zh":"我们家有了一个中学生。","pinyin":"Wǒmen jiā yǒule yí ge zhōngxuéshēng.","en":"We will have a middle school student in our family.","uz":"Oilamizda bitta o‘rta maktab o‘quvchisi bo‘ladi.","ru":"В нашей семье будет ученик средней школы.","tj":"Дар оилаи мо як хонандаи мактаби миёна мешавад."},
                    {"speaker":"Wang Yixue","zh":"还有了一个小学生。","pinyin":"Hái yǒule yí ge xiǎoxuéshēng.","en":"And a primary school student.","uz":"Yana bitta boshlang‘ich maktab o‘quvchisi ham bo‘ladi.","ru":"И ещё ученик начальной школы.","tj":"Боз як хонандаи мактаби ибтидоӣ ҳам мешавад."},
                    {"speaker":"Liu Ming","zh":"上学后，他们都忙了。","pinyin":"Shàngxué hòu, tāmen dōu máng le.","en":"Once they start school, they will both be busy.","uz":"Maktab boshlangach, ikkalasi ham band bo‘ladi.","ru":"Когда начнётся школа, оба будут заняты.","tj":"Баъди мактаб сар кардан, ҳар ду банд мешаванд."},
                    {"speaker":"Wang Yixue","zh":"是的。太晚了，睡觉吧。","pinyin":"Shì de. Tài wǎn le, shuìjiào ba.","en":"Yes. It's too late. Let's go to bed.","uz":"Ha. Juda kech bo‘ldi, uxlaylik.","ru":"Да. Уже очень поздно, давай спать.","tj":"Ҳа. Хеле дер шуд, биё хоб равем."},
                ]
            },
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no":1,"title_zh":"动态助词“了（2）”","title_uz":"Aspekt yuklamasi “了（2）”","title_ru":"Аспектуальная частица “了（2）”","title_tj":"Ҳиссачаи намудии “了（2）”",
                "rule_zh":"“了（2）”放在动词后，表示动作行为已经发生或完成。否定时用“没”，不用“了”。",
                "rule_en":"The aspect particle “了（2）” is placed after a verb to indicate that an action has occurred or been completed. When negating, 没 is used and 了 is omitted.",
                "rule_uz":"“了（2）” fe’ldan keyin kelib harakat sodir bo‘lganini yoki tugallanganini bildiradi. Inkorda 没 ishlatiladi va 了 tushiriladi.",
                "rule_ru":"“了（2）” ставится после глагола и показывает, что действие произошло или завершилось. В отрицании используется 没, а 了 опускается.",
                "rule_tj":"“了（2）” пас аз феъл омада, рух додан ё анҷом ёфтани амалро нишон медиҳад. Дар инкор 没 истифода шуда, 了 намеояд.",
                "examples":[
                    {"zh":"我看了一个电影。","pinyin":"Wǒ kànle yí ge diànyǐng.","uz":"Men bitta film ko‘rdim.","ru":"Я посмотрел фильм.","tj":"Ман як филм тамошо кардам."},
                    {"zh":"我买了一个新电脑。","pinyin":"Wǒ mǎile yí ge xīn diànnǎo.","uz":"Men yangi kompyuter sotib oldim.","ru":"Я купил новый компьютер.","tj":"Ман компютери нав харидам."},
                    {"zh":"我昨天没去商店买东西。","pinyin":"Wǒ zuótiān méi qù shāngdiàn mǎi dōngxi.","uz":"Men kecha do‘konga narsa sotib olishga bormadim.","ru":"Я вчера не ходил в магазин за покупками.","tj":"Ман дирӯз барои харид ба мағоза нарафтам."},
                ]
            },
            {
                "no":2,"title_zh":"离合词（1）","title_uz":"Ajraluvchi so‘zlar (1)","title_ru":"Разделяемые слова (1)","title_tj":"Калимаҳои ҷудошаванда (1)",
                "rule_zh":"“上课、下课、上班、下班、说话、读书、睡觉”等由动词和宾语组成，插入成分时要拆开。",
                "rule_en":"Words such as 上课, 下课, 上班, 下班, 说话, 读书 and 睡觉 consist of a verb and object; when inserting another element, the two parts are separated.",
                "rule_uz":"上课、下课、上班、下班、说话、读书、睡觉 kabi so‘zlar fe’l+obyektdan tuzilgan; orasiga boshqa unsur kirsa, qismlari ajraladi.",
                "rule_ru":"Слова 上课、下课、上班、下班、说话、读书、睡觉 состоят из глагола и объекта; при вставке другого элемента они разделяются.",
                "rule_tj":"Калимаҳои 上课、下课、上班、下班、说话、读书、睡觉 аз феъл+объект сохта шудаанд; ҳангоми ворид кардани унсур қисмҳо ҷудо мешаванд.",
                "examples":[
                    {"zh":"睡了觉；睡了一觉","pinyin":"shuìle jiào; shuìle yí jiào","uz":"uxladi; bir uxlab oldi","ru":"поспал; поспал один раз","tj":"хобид; як бор хобид"},
                    {"zh":"上了课；上了一次课","pinyin":"shàngle kè; shàngle yí cì kè","uz":"darsga qatnashdi; bir marta darsga qatnashdi","ru":"был на занятии; сходил на одно занятие","tj":"ба дарс рафт; як бор ба дарс рафт"},
                    {"zh":"说了话；说了很多话","pinyin":"shuōle huà; shuōle hěn duō huà","uz":"gapirdi; juda ko‘p gapirdi","ru":"говорил; много говорил","tj":"гап зад; бисёр гап зад"},
                ]
            },
            {
                "no":3,"title_zh":"范围副词“都”","title_uz":"Qamrov ravishi “都”","title_ru":"Наречие охвата “都”","title_tj":"Зарфи фарогирии “都”",
                "rule_zh":"“都”表示“全部、概括”，被概括的对象一般放在“都”前面。否定时，否定词在“都”后。",
                "rule_en":"The scope adverb “都” means “all” or “in general”. The item being generalized is placed before 都; when negating, the negative word is placed after 都.",
                "rule_uz":"“都” “hammasi/barchasi” ma’nosini beradi; umumlashtirilayotgan unsur 都 dan oldin keladi. Inkorda inkor so‘zi 都 dan keyin turadi.",
                "rule_ru":"“都” означает «все/в целом»; обобщаемый объект ставится перед 都. В отрицании отрицательное слово ставится после 都.",
                "rule_tj":"“都” маънои «ҳама/умуман»-ро медиҳад; объекти умумисозиш пеш аз 都 меояд. Дар инкор калимаи инкор пас аз 都 меояд.",
                "examples":[
                    {"zh":"我们都会写了。","pinyin":"Wǒmen dōu huì xiě le.","uz":"Hammamiz yoza olamiz.","ru":"Мы все умеем писать.","tj":"Ҳамаамон навишта метавонем."},
                    {"zh":"我和我的朋友们都去。","pinyin":"Wǒ hé wǒ de péngyoumen dōu qù.","uz":"Men va do‘stlarimning hammasi boramiz.","ru":"Я и мои друзья все пойдём.","tj":"Ман ва дӯстонам ҳама меравем."},
                    {"zh":"同学们都没听见。","pinyin":"Tóngxuémen dōu méi tīngjiàn.","uz":"Talabalarning hech biri eshitmadi.","ru":"Студенты все не услышали.","tj":"Ҳеҷ кадом аз донишҷӯён нашуниданд."},
                ]
            }
        ],
        ensure_ascii=False,
    ),
    "usage_notes_json": json.dumps(
        [
            {
                "topic":"他们 / 她们 / 它们",
                "zh":"“他们”可指男性或男女混合群体；“她们”专指女性群体；“它们”指多个事物。三个词读音相同。",
                "en":"他们 can refer to a male or mixed group; 她们 refers to females; 它们 refers to multiple things. All three have the same pronunciation.",
                "uz":"他们 erkaklar yoki aralash guruhga, 她们 ayollar guruhiga, 它们 esa narsalar/hayvonlarga ishlatiladi. Uchalasining talaffuzi bir xil.",
                "ru":"他们 относится к мужской или смешанной группе, 她们 — к женщинам, 它们 — к предметам/животным. Произношение одинаковое.",
                "tj":"他们 барои гурӯҳи мардон ё омехта, 她们 барои занон, 它们 барои чизҳо/ҳайвонот аст. Талаффузи ҳар се якхела аст.",
            }
        ],
        ensure_ascii=False,
    ),
}
