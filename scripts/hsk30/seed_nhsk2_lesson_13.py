from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(128, 137)),
    "printed_pages": list(range(112, 121)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level":"nhsk2",
    "lesson_order":13,
    "lesson_code":"NHSK2-L13",
    "title":"我们爱上中文课",
    "title_pinyin":"Wǒmen ài shàng Zhōngwén kè",
    "goal":json.dumps({
        "uz":"“拿/送/卖 + 给” bilan ikki obyektli gap tuzish; “比”dan keyin miqdor birikmasi bilan aniq farqni aytish; “一点儿/一些” bilan kichik farqni ifodalash; yangi yil sovg‘alari va dars haqida gaplashish.",
        "ru":"Строить двуобъектные предложения с “拿/送/卖 + 给”; выражать конкретную разницу количественной группой после 比; показывать небольшую разницу с “一点儿/一些”; говорить о новогодних подарках и занятиях.",
        "tj":"Бо “拿/送/卖 + 给” ҷумлаи дуобъектӣ сохтан; баъди 比 бо таркиби миқдорӣ фарқи дақиқро гуфтан; бо “一点儿/一些” фарқи хурдро ифода кардан; дар бораи тӯҳфаҳои Соли нав ва дарс суҳбат кардан."
    },ensure_ascii=False),
    "intro_text":json.dumps({
        "uz":"Dars ustozga yangi yil sovg‘asi, sinfdagi so‘z/ieroglif mashqi, daftar sovg‘asi va kundalik matni orqali ikki obyektli gap hamda taqqoslashning 7–8 turlarini o‘rgatadi.",
        "ru":"Урок через новогодний подарок преподавателю, словарно-иероглифическую работу в классе, подарок-блокнот и дневниковый текст вводит двуобъектные предложения и сравнительные конструкции 7–8.",
        "tj":"Дарс тавассути тӯҳфаи Соли нав ба устод, машқи калима/иероглиф дар синф, тӯҳфаи дафтар ва матни рӯзнома ҷумлаи дуобъектӣ ва муқоисаҳои 7–8-ро меомӯзонад."
    },ensure_ascii=False),
    "vocabulary_json":json.dumps([
        {"no":1,"zh":"新年","pinyin":"xīnnián","pos":"n.","uz":"Yangi yil","ru":"Новый год","tj":"Соли нав"},
        {"no":2,"zh":"教","pinyin":"jiāo","pos":"v.","uz":"o‘qitmoq","ru":"учить; преподавать","tj":"дарс додан; омӯзондан"},
        {"no":3,"zh":"花","pinyin":"huā","pos":"n.","uz":"gul","ru":"цветок","tj":"гул"},
        {"no":4,"zh":"希望","pinyin":"xīwàng","pos":"v.","uz":"umid qilmoq; tilamoq","ru":"надеяться; желать","tj":"умед кардан; орзу кардан"},
        {"no":5,"zh":"上面","pinyin":"shàngmian","pos":"n.","uz":"usti; yuqori qismi","ru":"сверху; поверхность","tj":"боло; рӯйи чиз"},
        {"no":6,"zh":"洗手间","pinyin":"xǐshǒujiān","pos":"n.","uz":"hojatxona; yuvinish xonasi","ru":"туалет; уборная","tj":"ҳоҷатхона"},
        {"no":7,"zh":"里面","pinyin":"lǐmian","pos":"n.","uz":"ichi; ichkarida","ru":"внутри","tj":"дарун; дохил"},
        {"no":8,"zh":"笔","pinyin":"bǐ","pos":"m.","uz":"chiziq (ieroglif zarbasi)","ru":"черта; штрих","tj":"хат; зарба"},
        {"no":9,"zh":"可能","pinyin":"kěnéng","pos":"v./adv.","uz":"mumkin; ehtimol","ru":"возможно; мочь","tj":"мумкин; эҳтимол"},
        {"no":10,"zh":"上网","pinyin":"shàngwǎng","pos":"v.","uz":"internetga kirmoq","ru":"выходить в интернет","tj":"ба интернет даромадан"},
        {"no":11,"zh":"那样","pinyin":"nàyàng","pos":"pron.","uz":"unday; shunday","ru":"так; таким образом","tj":"он тавр; чунин"},
        {"no":12,"zh":"告诉","pinyin":"gàosu","pos":"v.","uz":"aytmoq; xabar bermoq","ru":"сказать; сообщить","tj":"гуфтан; хабар додан"},
        {"no":13,"zh":"班","pinyin":"bān","pos":"n.","uz":"sinf; guruh","ru":"класс; группа","tj":"синф; гурӯҳ"}
    ],ensure_ascii=False),
    "proper_nouns_json":json.dumps([],ensure_ascii=False),
    "dialogue_json":json.dumps([
        {"block_no":1,"section_label":"课文 1","scene_zh":"在教室，白家月和陈天中在聊天儿。","scene_uz":"Sinfda Bai Jiayue va Chen Tianzhong suhbatlashmoqda.","scene_ru":"В классе Бай Цзяюэ и Чэнь Тяньчжун разговаривают.","scene_tj":"Дар синф Бай Ҷяюэ ва Чэн Тянҷун суҳбат мекунанд.","dialogue":[
            {"speaker":"Bai Jiayue","zh":"时间过得真快啊！新年就要到了。","pinyin":"Shíjiān guò de zhēn kuài a! Xīnnián jiù yào dào le.","uz":"Vaqt juda tez o‘tyapti! Yangi yilga ham oz qoldi.","ru":"Как быстро летит время! Новый год уже скоро.","tj":"Вақт чӣ қадар тез мегузарад! Соли нав ҳам наздик аст."},
            {"speaker":"Chen Tianzhong","zh":"这一年王老师教我们中文，每天工作都很累。","pinyin":"Zhè yì nián Wáng lǎoshī jiāo wǒmen Zhōngwén, měitiān gōngzuò dōu hěn lèi.","uz":"Bu yil ustoz Wang bizga xitoy tilidan dars berdi, har kuni juda ko‘p ishladi.","ru":"В этом году преподаватель Ван учила нас китайскому и каждый день много работала.","tj":"Ин сол устод Ван ба мо чинӣ дарс дод ва ҳар рӯз бисёр кор кард."},
            {"speaker":"Bai Jiayue","zh":"是啊，她教得很好。因为她，我们都非常爱上中文课。","pinyin":"Shì a, tā jiāo de hěn hǎo. Yīnwèi tā, wǒmen dōu fēicháng ài shàng Zhōngwén kè.","uz":"Ha, u juda yaxshi dars beradi. U sababli barchamiz xitoy tili darsini juda sevib qoldik.","ru":"Да, она очень хорошо преподаёт. Благодаря ей мы все полюбили уроки китайского.","tj":"Ҳа, ӯ хеле хуб дарс медиҳад. Бо шарофати ӯ ҳамаи мо дарси чиниро хеле дӯст доштем."},
            {"speaker":"Chen Tianzhong","zh":"我们给她准备个新年礼物吧。你觉得送给她什么好呢？","pinyin":"Wǒmen gěi tā zhǔnbèi ge xīnnián lǐwù ba. Nǐ juéde sòng gěi tā shénme hǎo ne?","uz":"Unga Yangi yil sovg‘asi tayyorlaylik. Nima sovg‘a qilsak yaxshi?","ru":"Давай приготовим ей новогодний подарок. Что лучше подарить?","tj":"Биё барояш тӯҳфаи Соли нав тайёр кунем. Чӣ тӯҳфа диҳем беҳтар?"},
            {"speaker":"Bai Jiayue","zh":"王老师喜欢花，就送给她花吧。","pinyin":"Wáng lǎoshī xǐhuan huā, jiù sòng gěi tā huā ba.","uz":"Ustoz Wang gullarni yoqtiradi, unga gul sovg‘a qilaylik.","ru":"Преподаватель Ван любит цветы, давай подарим ей цветы.","tj":"Устод Ван гулро дӯст медорад, барояш гул тӯҳфа кунем."},
            {"speaker":"Chen Tianzhong","zh":"那我们去花店看看，现在买花的人多，希望花店还有漂亮的花。","pinyin":"Nà wǒmen qù huādiàn kànkan, xiànzài mǎi huā de rén duō, xīwàng huādiàn hái yǒu piàoliang de huā.","uz":"Unda gul do‘koniga borib ko‘raylik. Hozir gul oladiganlar ko‘p, umid qilamanki, chiroyli gullar qolgan.","ru":"Тогда пойдём в цветочный магазин. Сейчас много покупателей; надеюсь, красивые цветы ещё остались.","tj":"Пас ба мағозаи гул рафта бинем. Ҳоло харидори гул зиёд аст, умедворам гулҳои зебо ҳанӯз ҳастанд."}
        ]},
        {"block_no":2,"section_label":"课文 2","scene_zh":"在教室，王一飞在上课。","scene_uz":"Sinfda Wang Yifei dars bermoqda.","scene_ru":"В классе Ван Ифэй ведёт урок.","scene_tj":"Дар синф Ван Ифэй дарс медиҳад.","dialogue":[
            {"speaker":"Bai Jiayue","zh":"王老师，今天的词比昨天多了十个。","pinyin":"Wáng lǎoshī, jīntiān de cí bǐ zuótiān duōle shí ge.","uz":"Ustoz Wang, bugungi so‘zlar kechagidan o‘nta ko‘p.","ru":"Преподаватель Ван, сегодня слов на десять больше, чем вчера.","tj":"Устод Ван, калимаҳои имрӯз аз дирӯз даҳто бештар аст."},
            {"speaker":"Wang Yifei","zh":"是啊！你们都学会了吗？","pinyin":"Shì a! Nǐmen dōu xuéhuì le ma?","uz":"Ha! Hammasini o‘rgandingizmi?","ru":"Да! Вы всё выучили?","tj":"Ҳа! Ҳамаашро омӯхтед?"},
            {"speaker":"Annie","zh":"学会了，没有问题。","pinyin":"Xuéhuì le, méiyǒu wèntí.","uz":"O‘rgandik, muammo yo‘q.","ru":"Выучили, без проблем.","tj":"Омӯхтем, мушкил нест."},
            {"speaker":"Wang Yifei","zh":"好。现在我来说，你们在本子上面写。","pinyin":"Hǎo. Xiànzài wǒ lái shuō, nǐmen zài běnzi shàngmian xiě.","uz":"Yaxshi. Endi men aytaman, sizlar daftarga yozinglar.","ru":"Хорошо. Теперь я буду говорить, а вы записывайте в тетради.","tj":"Хуб. Ҳоло ман мегӯям, шумо дар дафтар нависед."},
            {"speaker":"Wang Yifei","zh":"同学们，“洗手间”的“间”字写错了，它的里面是“日”，不是“口”。","pinyin":"Tóngxuémen, “xǐshǒujiān” de “jiān” zì xiěcuò le, tā de lǐmian shì “rì”, bú shì “kǒu”.","uz":"O‘quvchilar, “洗手间”dagi “间” xato yozilgan: ichida “日”, “口” emas.","ru":"Ребята, иероглиф “间” в “洗手间” написан неправильно: внутри “日”, а не “口”.","tj":"Донишҷӯён, “间” дар “洗手间” хато навишта шудааст: дарунаш “日” аст, на “口”."},
            {"speaker":"Bai Jiayue","zh":"“日”比“口”多一笔，写“口”就是“问题”的“问”了。","pinyin":"“Rì” bǐ “kǒu” duō yì bǐ, xiě “kǒu” jiù shì “wèntí” de “wèn” le.","uz":"“日” “口”dan bir chiziq ko‘p; “口” yozilsa, “问题”dagi “问” bo‘lib qoladi.","ru":"В “日” на одну черту больше, чем в “口”; если написать “口”, получится “问” из “问题”.","tj":"“日” аз “口” як хат бештар дорад; агар “口” нависем, “问”-и “问题” мешавад."},
            {"speaker":"Wang Yifei","zh":"没错，你说得很对。","pinyin":"Méi cuò, nǐ shuō de hěn duì.","uz":"To‘g‘ri, juda to‘g‘ri aytding.","ru":"Верно, ты совершенно права.","tj":"Дуруст, хеле дуруст гуфтӣ."}
        ]},
        {"block_no":3,"section_label":"课文 3","scene_zh":"在教室，安妮和白家月在聊天儿。","scene_uz":"Sinfda Annie va Bai Jiayue suhbatlashmoqda.","scene_ru":"В классе Энни и Бай Цзяюэ разговаривают.","scene_tj":"Дар синф Энни ва Бай Ҷяюэ суҳбат мекунанд.","dialogue":[
            {"speaker":"Annie","zh":"家月，你觉得这个本子怎么样？","pinyin":"Jiāyuè, nǐ juéde zhège běnzi zěnmeyàng?","uz":"Jiayue, bu daftar senga qanday?","ru":"Цзяюэ, как тебе этот блокнот?","tj":"Ҷяюэ, ин дафтар чӣ хел аст?"},
            {"speaker":"Bai Jiayue","zh":"很漂亮，多少钱一个？","pinyin":"Hěn piàoliang, duōshao qián yí ge?","uz":"Juda chiroyli, bittasi qancha?","ru":"Очень красивый. Сколько стоит один?","tj":"Хеле зебо, яктояш чанд пул?"},
            {"speaker":"Annie","zh":"比我们一起买的那个本子贵一点儿。","pinyin":"Bǐ wǒmen yìqǐ mǎi de nàge běnzi guì yìdiǎnr.","uz":"Birga olgan daftarimizdan biroz qimmatroq.","ru":"Немного дороже того блокнота, который мы покупали вместе.","tj":"Аз дафтаре, ки якҷо харида будем, каме гаронтар."},
            {"speaker":"Bai Jiayue","zh":"这么漂亮的本子，不可能贵一点儿吧？","pinyin":"Zhème piàoliang de běnzi, bù kěnéng guì yìdiǎnr ba?","uz":"Bunday chiroyli daftar faqat biroz qimmatroq bo‘lishi mumkin emas-a?","ru":"Такой красивый блокнот не может быть всего чуть дороже, правда?","tj":"Чунин дафтари зебо фақат каме гаронтар бошад, мумкин нест-ку?"},
            {"speaker":"Annie","zh":"我是上网买的，真没那么贵。我买了两个，送你一个。","pinyin":"Wǒ shì shàngwǎng mǎi de, zhēn méi nàme guì. Wǒ mǎile liǎng ge, sòng nǐ yí ge.","uz":"Internetdan oldim, aslida unchalik qimmat emas. Ikkita oldim, bittasini senga beraman.","ru":"Я купила в интернете, на самом деле не так дорого. Купила два, один подарю тебе.","tj":"Аз интернет харидам, аслан он қадар гарон нест. Дуто харидам, яктоашро ба ту медиҳам."},
            {"speaker":"Bai Jiayue","zh":"谢谢！那我送给你什么呢？","pinyin":"Xièxie! Nà wǒ sòng gěi nǐ shénme ne?","uz":"Rahmat! Unda men senga nima sovg‘a qilay?","ru":"Спасибо! А что мне подарить тебе?","tj":"Раҳмат! Пас ман ба ту чӣ тӯҳфа кунам?"},
            {"speaker":"Annie","zh":"咖啡杯吧，我最喜欢喝咖啡了。","pinyin":"Kāfēibēi ba, wǒ zuì xǐhuan hē kāfēi le.","uz":"Qahva piyolasi bo‘lsin, men qahvani eng ko‘p yoqtiraman.","ru":"Чашку для кофе — я больше всего люблю кофе.","tj":"Пиёлаи қаҳва бошад, ман қаҳваро аз ҳама бештар дӯст медорам."},
            {"speaker":"Bai Jiayue","zh":"好，那样我们就都有新年礼物了！","pinyin":"Hǎo, nàyàng wǒmen jiù dōu yǒu xīnnián lǐwù le!","uz":"Xo‘p, shunda ikkalamizda ham Yangi yil sovg‘asi bo‘ladi!","ru":"Хорошо, тогда у нас обеих будут новогодние подарки!","tj":"Хуб, он гоҳ ҳардуямон тӯҳфаи Соли нав дорем!"}
        ]},
        {"block_no":4,"section_label":"课文 4","scene_zh":"在夜间，白家月在写日记。","scene_uz":"Kechasi Bai Jiayue kundalik yozmoqda.","scene_ru":"Ночью Бай Цзяюэ пишет дневник.","scene_tj":"Шабона Бай Ҷяюэ рӯзнома менависад.","dialogue":[
            {"speaker":"Narration","zh":"新年就要到了，安妮送给我一个新本子。她告诉我是在网上买的，比我的本子贵一点儿。我们班同学也送了王老师漂亮的花，希望她高高兴兴地过个新年。","pinyin":"Xīnnián jiù yào dào le, Ānnī sòng gěi wǒ yí ge xīn běnzi. Tā gàosu wǒ shì zài wǎngshang mǎi de, bǐ wǒ de běnzi guì yìdiǎnr. Wǒmen bān tóngxué yě sòngle Wáng lǎoshī piàoliang de huā, xīwàng tā gāogāoxìngxìng de guò ge xīnnián.","uz":"Yangi yilga oz qoldi, Annie menga yangi daftar sovg‘a qildi. Uni internetdan olganini va mening daftarimdan biroz qimmatroq ekanini aytdi. Sinfdoshlarimiz ham ustoz Wangga chiroyli gullar sovg‘a qilib, Yangi yilni xursand o‘tkazishini tilashdi.","ru":"Новый год уже близко. Энни подарила мне новый блокнот. Она сказала, что купила его в интернете и он немного дороже моего. Наш класс тоже подарил преподавателю Ван красивые цветы, пожелав ей радостного Нового года.","tj":"Соли нав наздик аст, Энни ба ман дафтари нав тӯҳфа кард. Гуфт, ки онро аз интернет харидааст ва аз дафтари ман каме гаронтар аст. Ҳамсинфонамон ҳам ба устод Ван гулҳои зебо тӯҳфа карда, орзу карданд Соли навро хушҳолона гузаронад."}
        ]}
    ],ensure_ascii=False),
    "grammar_json":json.dumps([
        {"no":1,"title_zh":"双宾语句（2）","title_uz":"Ikki obyektli gap (2)","title_ru":"Предложение с двумя объектами (2)","title_tj":"Ҷумлаи дуобъектӣ (2)","rule_zh":"双宾语句是一个动词带两个宾语的句子，一般前一个宾语指人，后一个宾语指事物。本课学习动词“拿、送、卖”加“给”构成的双宾语句。","rule_uz":"Ikki obyektli gapda bir fe’l ikki obyekt oladi: odatda birinchisi odamni, ikkinchisi narsani bildiradi. Bu darsda 拿、送、卖 fe’llarining 给 bilan ikki obyektli qo‘llanilishi o‘rganiladi.","rule_ru":"В двуобъектном предложении глагол имеет два объекта: первый обычно обозначает человека, второй — предмет. Здесь изучаются конструкции с 拿、送、卖 + 给.","rule_tj":"Дар ҷумлаи дуобъектӣ як феъл ду объект мегирад: одатан якум шахс, дуюм ашё аст. Дар ин дарс сохторҳои 拿、送、卖 + 给 омӯхта мешаванд.","examples":[{"zh":"王老师喜欢花，就送给她花吧。"},{"zh":"她拿给我一杯水。"},{"zh":"他卖给我一本中文书。"}]},
        {"no":2,"title_zh":"比较句（7）","title_uz":"Taqqoslash gapi (7)","title_ru":"Сравнительное предложение (7)","title_tj":"Ҷумлаи муқоисавӣ (7)","rule_zh":"用“比”表示的比较句中，数量短语放在形容词后面，表示具体差别。基本结构：A比B+形容词+数量短语。","rule_uz":"“比” gapida miqdor birikmasi sifatdan keyin kelib, aniq farqni bildiradi. Tuzilishi: A 比 B + sifat + miqdor birikmasi.","rule_ru":"В сравнительном предложении с 比 количественная группа ставится после прилагательного и показывает конкретную разницу. Схема: A 比 B + прилагательное + количественная группа.","rule_tj":"Дар ҷумлаи 比 таркиби миқдорӣ пас аз сифат омада, фарқи дақиқро нишон медиҳад. Сохтор: A 比 B + сифат + таркиби миқдорӣ.","examples":[{"zh":"今天的词比昨天多了十个。"},{"zh":"姐姐比我大三岁。"},{"zh":"坐飞机比坐火车快五个多小时。"}]},
        {"no":3,"title_zh":"比较句（8）","title_uz":"Taqqoslash gapi (8)","title_ru":"Сравнительное предложение (8)","title_tj":"Ҷумлаи муқоисавӣ (8)","rule_zh":"用“比”表示的比较句中，“一点儿”或“一些”用在形容词后面，表示差别不大。基本结构：A比B+形容词+一点儿/一些。","rule_uz":"“比” gapida sifatdan keyin 一点儿 yoki 一些 kichik farqni bildiradi. Tuzilishi: A 比 B + sifat + 一点儿/一些.","rule_ru":"В сравнении с 比 一点儿 или 一些 после прилагательного обозначает небольшую разницу. Схема: A 比 B + прилагательное + 一点儿/一些.","rule_tj":"Дар ҷумлаи 比 一点儿 ё 一些 пас аз сифат фарқи хурдро нишон медиҳад. Сохтор: A 比 B + сифат + 一点儿/一些.","examples":[{"zh":"比我们一起买的那个本子贵一点儿。"},{"zh":"姐姐比我高一点儿。"},{"zh":"那间教室比这间大一些。"}]}
    ],ensure_ascii=False)
}
