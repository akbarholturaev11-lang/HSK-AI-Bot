from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(118, 128)),
    "printed_pages": list(range(102, 112)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level":"nhsk2",
    "lesson_order":12,
    "lesson_code":"NHSK2-L12",
    "title":"这里比北京冷多了",
    "title_pinyin":"Zhèlǐ bǐ Běijīng lěng duō le",
    "goal":json.dumps({
        "uz":"“比” gapida 多了/得多 bilan katta farqni ifodalash; holat to‘ldiruvchili fe’l bilan 比 ning ikki joylashuvini ishlatish; obyektli/ajraluvchi fe’llarda 比 taqqoslashini to‘g‘ri tuzish; ob-havo va sport haqida gaplashish.",
        "ru":"Выражать большую разницу с 多了/得多 в предложениях с 比; использовать два положения 比 при глаголе с дополнением состояния; правильно строить сравнение с объектными и разделяемыми глаголами; говорить о погоде и спорте.",
        "tj":"Дар ҷумлаи 比 бо 多了/得多 фарқи калонро ифода кардан; бо феъли дорои пуркунандаи ҳолат ду ҷойи 比-ро истифода бурдан; муқоисаро бо феълҳои объектдор/ҷудошаванда дуруст сохтан; дар бораи обу ҳаво ва варзиш суҳбат кардан."
    },ensure_ascii=False),
    "intro_text":json.dumps({
        "uz":"Dars ikki shahardagi ob-havo, qor, yugurish va kundalik matni orqali taqqoslash gaplarining 4–6 turlarini o‘rgatadi.",
        "ru":"Урок через погоду в двух городах, снег, бег и дневниковый текст вводит сравнительные конструкции 4–6.",
        "tj":"Дарс тавассути обу ҳавои ду шаҳр, барф, давидан ва матни рӯзнома сохторҳои муқоисавии 4–6-ро меомӯзонад."
    },ensure_ascii=False),
    "vocabulary_json":json.dumps([
        {"no":1,"zh":"事情","pinyin":"shìqing","pos":"n.","uz":"ish; voqea; masala","ru":"дело; событие","tj":"кор; ҳодиса; масъала"},
        {"no":2,"zh":"晴","pinyin":"qíng","pos":"adj.","uz":"ochiq; quyoshli","ru":"ясный; солнечный","tj":"соф; офтобӣ"},
        {"no":3,"zh":"正","pinyin":"zhèng","pos":"adv.","uz":"aynan hozir; davom etayotgan","ru":"как раз; прямо сейчас","tj":"айни ҳозир; маҳз"},
        {"no":4,"zh":"外面","pinyin":"wàimian","pos":"n.","uz":"tashqari; tashqarida","ru":"снаружи; на улице","tj":"берун"},
        {"no":5,"zh":"阴","pinyin":"yīn","pos":"adj.","uz":"bulutli","ru":"пасмурный; облачный","tj":"абрнок"},
        {"no":6,"zh":"从小","pinyin":"cóngxiǎo","pos":"adv.","uz":"bolalikdan","ru":"с детства","tj":"аз кӯдакӣ"},
        {"no":7,"zh":"地铁","pinyin":"dìtiě","pos":"n.","uz":"metro","ru":"метро","tj":"метро"},
        {"no":8,"zh":"楼","pinyin":"lóu","pos":"n.","uz":"bino; qavatli uy","ru":"здание; этаж","tj":"бино; ошёна"},
        {"no":9,"zh":"站","pinyin":"zhàn","pos":"n.","uz":"bekat; stansiya","ru":"остановка; станция","tj":"истгоҳ"},
        {"no":10,"zh":"小时候","pinyin":"xiǎoshíhou","pos":"n.","uz":"bolalik payti","ru":"в детстве","tj":"вақти кӯдакӣ"},
        {"no":11,"zh":"好","pinyin":"hǎo","pos":"adv.","uz":"juda; ancha","ru":"очень; довольно","tj":"хеле; бисёр"}
    ],ensure_ascii=False),
    "proper_nouns_json":json.dumps([],ensure_ascii=False),
    "dialogue_json":json.dumps([
        {"block_no":1,"section_label":"课文 1","scene_zh":"在房间，王一雪接到白家月的电话。","scene_uz":"Xonada Wang Yixue Bai Jiayuening qo‘ng‘irog‘ini qabul qildi.","scene_ru":"В комнате Ван Исюэ принимает звонок от Бай Цзяюэ.","scene_tj":"Дар ҳуҷра Ван Исюэ занги Бай Ҷяюэро қабул мекунад.","dialogue":[
            {"speaker":"Wang Yixue","zh":"喂，家月，是你啊！有什么事情吗？","pinyin":"Wèi, Jiāyuè, shì nǐ a! Yǒu shénme shìqing ma?","uz":"Allo, Jiayue, sen ekansan! Biror ish bormi?","ru":"Алло, Цзяюэ, это ты! Что-то случилось?","tj":"Алло, Ҷяюэ, ту будаӣ! Ягон кор ҳаст?"},
            {"speaker":"Bai Jiayue","zh":"没什么事，就想跟您说说话。","pinyin":"Méi shénme shì, jiù xiǎng gēn nín shuōshuo huà.","uz":"Hech qanday ish yo‘q, shunchaki siz bilan gaplashgim keldi.","ru":"Ничего особенного, просто захотелось с вами поговорить.","tj":"Кори махсус нест, танҳо мехостам бо шумо суҳбат кунам."},
            {"speaker":"Wang Yixue","zh":"好啊。你今天没课吗？","pinyin":"Hǎo a. Nǐ jīntiān méi kè ma?","uz":"Mayli. Bugun darsing yo‘qmi?","ru":"Хорошо. У тебя сегодня нет занятий?","tj":"Хуб. Имрӯз дарс надорӣ?"},
            {"speaker":"Bai Jiayue","zh":"下午有课。您那里天气怎么样？","pinyin":"Xiàwǔ yǒu kè. Nín nàli tiānqì zěnmeyàng?","uz":"Tushdan keyin darsim bor. Sizlarda ob-havo qanday?","ru":"Занятия днём. Какая у вас погода?","tj":"Баъд аз нисфирӯзӣ дарс дорам. Он ҷо ҳаво чӣ хел?"},
            {"speaker":"Wang Yixue","zh":"北京这几天虽然是晴天，但是有点儿冷。","pinyin":"Běijīng zhè jǐ tiān suīrán shì qíngtiān, dànshì yǒudiǎnr lěng.","uz":"Pekinda shu kunlarda havo ochiq bo‘lsa ham, biroz sovuq.","ru":"В Пекине эти дни солнечные, но немного холодно.","tj":"Дар Пекин ин чанд рӯз ҳаво соф бошад ҳам, каме хунук аст."},
            {"speaker":"Bai Jiayue","zh":"我这里比北京冷多了，外边还正下着雪呢！","pinyin":"Wǒ zhèlǐ bǐ Běijīng lěng duō le, wàibian hái zhèng xiàzhe xuě ne!","uz":"Bu yer Pekindan ancha sovuq, tashqarida hozir ham qor yog‘ayapti!","ru":"Здесь намного холоднее, чем в Пекине, и на улице сейчас ещё идёт снег!","tj":"Ин ҷо аз Пекин хеле хунуктар аст, берун ҳоло ҳам барф меборад!"}
        ]},
        {"block_no":2,"section_label":"课文 2","scene_zh":"在客厅，王一雪给王一飞打电话。","scene_uz":"Mehmonxonada Wang Yixue Wang Yifeiga telefon qilmoqda.","scene_ru":"В гостиной Ван Исюэ звонит Ван Ифэй.","scene_tj":"Дар меҳмонхона Ван Исюэ ба Ван Ифэй занг мезанад.","dialogue":[
            {"speaker":"Wang Yixue","zh":"喂，一飞，听家月说你那边下雪了，下得大不大？","pinyin":"Wèi, Yīfēi, tīng Jiāyuè shuō nǐ nàbian xià xuě le, xià de dà bu dà?","uz":"Allo, Yifei, Jiayuedan eshitdim, sizlarda qor yog‘ibdi. Kuchlimi?","ru":"Алло, Ифэй, Цзяюэ сказала, что у вас снег. Сильно идёт?","tj":"Алло, Ифэй, аз Ҷяюэ шунидам, он ҷо барф боридааст. Сахт меборад?"},
            {"speaker":"Wang Yifei","zh":"今天不大，昨天比今天下得大。","pinyin":"Jīntiān bú dà, zuótiān bǐ jīntiān xià de dà.","uz":"Bugun kuchli emas, kecha bugungidan kuchliroq yog‘di.","ru":"Сегодня не сильно, вчера снег шёл сильнее, чем сегодня.","tj":"Имрӯз сахт нест, дирӯз аз имрӯз сахттар борид."},
            {"speaker":"Wang Yixue","zh":"天气不好。你去外面的时候多穿点儿衣服。","pinyin":"Tiānqì bù hǎo. Nǐ qù wàimian de shíhou duō chuān diǎnr yīfu.","uz":"Havo yaxshi emas. Tashqariga chiqqanda ko‘proq kiyim kiy.","ru":"Погода плохая. Когда выходишь, одевайся теплее.","tj":"Ҳаво хуб нест. Вақте берун мебароӣ, бештар либос пӯш."},
            {"speaker":"Wang Yifei","zh":"这几天我在网上上课，没出去过。","pinyin":"Zhè jǐ tiān wǒ zài wǎngshang shàngkè, méi chūquguo.","uz":"Shu kunlarda onlayn dars beryapman, tashqariga chiqmadim.","ru":"Эти дни я преподаю онлайн и не выходила.","tj":"Ин чанд рӯз онлайн дарс медиҳам ва берун набаромадаам."},
            {"speaker":"Wang Yixue","zh":"那就好，有事记得给我打电话。","pinyin":"Nà jiù hǎo, yǒu shì jìde gěi wǒ dǎ diànhuà.","uz":"Yaxshi, biror narsa bo‘lsa menga telefon qilishni unutma.","ru":"Тогда хорошо. Если что — не забудь позвонить.","tj":"Хуб, агар коре шавад, ба ман занг заданро фаромӯш накун."},
            {"speaker":"Wang Yifei","zh":"好的。现在不下雪了，我出去买点儿吃的。","pinyin":"Hǎo de. Xiànzài bù xià xuě le, wǒ chūqu mǎi diǎnr chī de.","uz":"Xo‘p. Hozir qor yog‘mayapti, men tashqariga yegulik olgani chiqaman.","ru":"Хорошо. Сейчас снег прекратился, я выйду купить еды.","tj":"Хуб. Ҳоло барф намеборад, ман берун баромада хӯрданӣ мехарам."},
            {"speaker":"Wang Yixue","zh":"一次多买点儿，阴天下雪什么的就少出去吧。","pinyin":"Yí cì duō mǎi diǎnr, yīntiān xià xuě shénmede jiù shǎo chūqu ba.","uz":"Bir yo‘la ko‘proq ol, bulutli yoki qorli kunlarda kamroq chiq.","ru":"Купи побольше за один раз, а в пасмурную или снежную погоду выходи пореже.","tj":"Якбора бештар бихар, рӯзҳои абрнок ё барфӣ камтар берун баро."}
        ]},
        {"block_no":3,"section_label":"课文 3","scene_zh":"在房间，李文给白家月打电话。","scene_uz":"Xonada Li Wen Bai Jiayuega telefon qilmoqda.","scene_ru":"В комнате Ли Вэнь звонит Бай Цзяюэ.","scene_tj":"Дар ҳуҷра Ли Вэн ба Бай Ҷяюэ занг мезанад.","dialogue":[
            {"speaker":"Li Wen","zh":"喂，家月，今天天气不错，我们去跑步吧！","pinyin":"Wèi, Jiāyuè, jīntiān tiānqì búcuò, wǒmen qù pǎobù ba!","uz":"Allo, Jiayue, bugun havo yaxshi, yugurishga boraylik!","ru":"Алло, Цзяюэ, погода сегодня хорошая, пойдём побегаем!","tj":"Алло, Ҷяюэ, имрӯз ҳаво хуб аст, биё давидан равем!"},
            {"speaker":"Bai Jiayue","zh":"你跑步跑得比我快，我们能一起跑吗？","pinyin":"Nǐ pǎobù pǎo de bǐ wǒ kuài, wǒmen néng yìqǐ pǎo ma?","uz":"Sen mendan tezroq yugurasan, birga yugura olamizmi?","ru":"Ты бегаешь быстрее меня, сможем бежать вместе?","tj":"Ту аз ман тезтар медавӣ, якҷо давида метавонем?"},
            {"speaker":"Li Wen","zh":"可以的，我慢慢跑，等着你。","pinyin":"Kěyǐ de, wǒ mànmàn pǎo, děngzhe nǐ.","uz":"Bo‘ladi, men sekin yuguraman, seni kutib turaman.","ru":"Конечно, я буду бежать медленно и ждать тебя.","tj":"Мешавад, ман оҳиста медавам ва туро интизор мешавам."},
            {"speaker":"Bai Jiayue","zh":"好吧。你真爱跑步啊！","pinyin":"Hǎo ba. Nǐ zhēn ài pǎobù a!","uz":"Mayli. Sen yugurishni juda yaxshi ko‘rarkan-san!","ru":"Хорошо. Ты и правда любишь бегать!","tj":"Хуб. Ту воқеан давиданро дӯст медорӣ!"},
            {"speaker":"Li Wen","zh":"我从小就经常跟爸爸跑步，跑步能让人快乐！","pinyin":"Wǒ cóngxiǎo jiù jīngcháng gēn bàba pǎobù, pǎobù néng ràng rén kuàilè!","uz":"Men bolaligimdan dadam bilan tez-tez yuguraman, yugurish odamni xursand qiladi!","ru":"Я с детства часто бегаю с папой; бег делает людей счастливее!","tj":"Ман аз кӯдакӣ бо падарам зуд-зуд медавам, давидан одамро хушҳол мекунад!"},
            {"speaker":"Bai Jiayue","zh":"好，那我准备一下。","pinyin":"Hǎo, nà wǒ zhǔnbèi yíxià.","uz":"Xo‘p, unda men tayyorlanaman.","ru":"Хорошо, тогда я подготовлюсь.","tj":"Хуб, пас ман тайёр мешавам."},
            {"speaker":"Li Wen","zh":"我现在坐地铁去找你，一会儿楼下见。","pinyin":"Wǒ xiànzài zuò dìtiě qù zhǎo nǐ, yíhuìr lóuxià jiàn.","uz":"Hozir metroda oldingga boraman, birozdan keyin bino pastida ko‘rishamiz.","ru":"Сейчас поеду к тебе на метро, увидимся скоро внизу.","tj":"Ҳоло бо метро назди ту меоям, каме баъд поёни бино мебинем."}
        ]},
        {"block_no":4,"section_label":"课文 4","scene_zh":"在房间，白家月在写日记。","scene_uz":"Xonada Bai Jiayue kundalik yozmoqda.","scene_ru":"В комнате Бай Цзяюэ пишет дневник.","scene_tj":"Дар ҳуҷра Бай Ҷяюэ рӯзнома менависад.","dialogue":[
            {"speaker":"Narration","zh":"前几天天气不好，我没走路，每天坐两站地铁去学校。今天是个大晴天，李文让我跟他去外面跑步。他小时候经常跑步，跑得比我快，但是他会等我。跟李文一起跑步，我好高兴啊！","pinyin":"Qián jǐ tiān tiānqì bù hǎo, wǒ méi zǒulù, měitiān zuò liǎng zhàn dìtiě qù xuéxiào. Jīntiān shì ge dà qíngtiān, Lǐ Wén ràng wǒ gēn tā qù wàimian pǎobù. Tā xiǎoshíhou jīngcháng pǎobù, pǎo de bǐ wǒ kuài, dànshì tā huì děng wǒ. Gēn Lǐ Wén yìqǐ pǎobù, wǒ hǎo gāoxìng a!","uz":"Oldingi kunlarda havo yomon edi, piyoda yurmadim, har kuni maktabga ikki bekat metroda bordim. Bugun juda ochiq kun, Li Wen meni u bilan tashqarida yugurishga chaqirdi. U bolaligida tez-tez yugurgan, mendan tezroq yuguradi, lekin meni kutadi. Li Wen bilan birga yugurishdan juda xursandman!","ru":"Последние несколько дней погода была плохой, я не ходила пешком, каждый день ехала до школы две станции метро. Сегодня ясный день, Ли Вэнь позвал меня побегать на улице. Он часто бегал с детства и бегает быстрее меня, но ждёт меня. Я так рада бегать вместе с Ли Вэнем!","tj":"Чанд рӯзи пеш ҳаво бад буд, пиёда намерафтам, ҳар рӯз то мактаб ду истгоҳ метро мерафтам. Имрӯз рӯзи хеле офтобист, Ли Вэн маро ба давидан дар берун даъват кард. Ӯ аз кӯдакӣ зуд-зуд медавид ва аз ман тезтар медавад, аммо маро интизор мешавад. Бо Ли Вэн якҷо давидан маро хеле хушҳол мекунад!"}
        ]}
    ],ensure_ascii=False),
    "grammar_json":json.dumps([
        {"no":1,"title_zh":"比较句（4）","title_uz":"Taqqoslash gapi (4)","title_ru":"Сравнительное предложение (4)","title_tj":"Ҷумлаи муқоисавӣ (4)","rule_zh":"用“比”表示的比较句中，“多了”或“得多”用在形容词后面，表示差别很大。基本结构：A比B+形容词+多了/得多。","rule_uz":"“比” gapida sifatdan keyin 多了 yoki 得多 kelib, farq juda katta ekanini bildiradi. Tuzilishi: A 比 B + sifat + 多了/得多.","rule_ru":"В сравнении с 比 после прилагательного 多了 или 得多 обозначает значительную разницу. Схема: A 比 B + прилагательное + 多了/得多.","rule_tj":"Дар ҷумлаи 比 пас аз сифат 多了 ё 得多 омада, фарқи калонро нишон медиҳад. Сохтор: A 比 B + сифат + 多了/得多.","examples":[{"zh":"我这里比北京冷多了。"},{"zh":"坐飞机比坐火车快得多。"},{"zh":"他觉得红茶比绿茶好喝得多。"}]},
        {"no":2,"title_zh":"比较句（5）","title_uz":"Taqqoslash gapi (5)","title_ru":"Сравнительное предложение (5)","title_tj":"Ҷумлаи муқоисавӣ (5)","rule_zh":"用“比”表示的比较句中，如果动词带状态补语，“比”用在动词前后都可以。","rule_uz":"“比”li taqqoslashda fe’l holat to‘ldiruvchisi bilan kelsa, 比 fe’lning oldida ham, keyin ham kelishi mumkin.","rule_ru":"В сравнительном предложении с 比, если глагол имеет дополнение состояния, 比 может стоять как перед глаголом, так и после него.","rule_tj":"Дар ҷумлаи муқоисавӣ бо 比, агар феъл пуркунандаи ҳолат дошта бошад, 比 метавонад пеш ё пас аз феъл ояд.","examples":[{"zh":"昨天比今天下得大。"},{"zh":"妈妈比我睡得晚。"},{"zh":"李文跑得比白家月快。"}]},
        {"no":3,"title_zh":"比较句（6）","title_uz":"Taqqoslash gapi (6)","title_ru":"Сравнительное предложение (6)","title_tj":"Ҷумлаи муқоисавӣ (6)","rule_zh":"用“比”表示的比较句中，如果动词既带宾语，又带状态补语，可以把宾语提前，或者重复动词。如果动词是离合词，需要重复动词性语素。","rule_uz":"“比” gapida fe’l ham obyekt, ham holat to‘ldiruvchisini olsa, obyektni oldinga chiqarish yoki fe’lni takrorlash mumkin. Ajraluvchi fe’lda fe’l morfemasi takrorlanadi.","rule_ru":"В сравнении с 比, если глагол имеет и объект, и дополнение состояния, объект можно вынести вперёд или повторить глагол. У разделяемого глагола повторяется глагольный морф.","rule_tj":"Дар ҷумлаи 比, агар феъл ҳам объект ва ҳам пуркунандаи ҳолат дошта бошад, объектро пеш овардан ё феълро такрор кардан мумкин. Дар феъли ҷудошаванда морфемаи феъл такрор мешавад.","examples":[{"zh":"你跑步跑得比我快。"},{"zh":"白家月汉字写得比陈天中好。"},{"zh":"他踢足球比我踢得好。"}]}
    ],ensure_ascii=False)
}
