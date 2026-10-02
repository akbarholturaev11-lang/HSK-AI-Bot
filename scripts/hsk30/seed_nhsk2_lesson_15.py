from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(146, 157)),
    "printed_pages": list(range(130, 141)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level":"nhsk2",
    "lesson_order":15,
    "lesson_code":"NHSK2-L15",
    "title":"我想再去一次中国",
    "title_pinyin":"Wǒ xiǎng zài qù yí cì Zhōngguó",
    "goal":json.dumps({
        "uz":"“次” bilan harakat necha marta sodir bo‘lganini aytish; frequency complement va obyektning tartibini to‘g‘ri qo‘llash; “有+miqdor” bilan ma’lum miqdorga yetganlikni ifodalash; sayohat va qaytish rejalari haqida gaplashish.",
        "ru":"Выражать количество повторений действия с “次”; правильно располагать дополнение кратности и объект; выражать достигнутое количество конструкцией “有+количество”; говорить о путешествиях и возвращении домой.",
        "tj":"Бо “次” шумораи такрори амалро гуфтан; ҷойи пуркунандаи такрор ва объектро дуруст истифода бурдан; бо “有+миқдор” расидан ба миқдори муайянро ифода кардан; дар бораи сафар ва бозгашт суҳбат кардан."
    },ensure_ascii=False),
    "intro_text":json.dumps({
        "uz":"Dars imtihondan keyingi reja, Pekinga sayohat, aviachipta va uyga qaytish haqidagi suhbatlar hamda kundalik matni orqali frequency complement va “有” gapini o‘rgatadi.",
        "ru":"Урок через планы после экзамена, поездку в Пекин, авиабилеты, возвращение домой и дневниковую запись вводит дополнение кратности и конструкцию “有”.",
        "tj":"Дарс тавассути нақшаҳои баъди имтиҳон, сафар ба Пекин, чиптаи ҳавопаймо, бозгашт ба хона ва матни рӯзнома пуркунандаи такрор ва сохтори “有”-ро меомӯзонад."
    },ensure_ascii=False),
    "vocabulary_json":json.dumps([
        {"no":1,"zh":"姓名","pinyin":"xìngmíng","pos":"n.","uz":"ism-familiya","ru":"имя и фамилия","tj":"ному насаб"},
        {"no":2,"zh":"出国","pinyin":"chūguó","pos":"v.","uz":"chet elga chiqmoq","ru":"ехать за границу","tj":"ба хориҷ рафтан"},
        {"no":3,"zh":"门票","pinyin":"ménpiào","pos":"n.","uz":"kirish chiptasi","ru":"входной билет","tj":"чиптаи даромад"},
        {"no":4,"zh":"高中","pinyin":"gāozhōng","pos":"n.","uz":"yuqori sinf; o‘rta maktabning yuqori bosqichi","ru":"старшая школа","tj":"мактаби миёнаи болоӣ"},
        {"no":5,"zh":"出门","pinyin":"chūmén","pos":"v.","uz":"uydan chiqmoq","ru":"выходить из дома","tj":"аз хона баромадан"},
        {"no":6,"zh":"路","pinyin":"lù","pos":"n.","uz":"yo‘l","ru":"дорога; путь","tj":"роҳ"},
        {"no":7,"zh":"机场","pinyin":"jīchǎng","pos":"n.","uz":"aeroport","ru":"аэропорт","tj":"фурудгоҳ"},
        {"no":8,"zh":"机票","pinyin":"jīpiào","pos":"n.","uz":"aviachipta","ru":"авиабилет","tj":"чиптаи ҳавопаймо"},
        {"no":9,"zh":"飞","pinyin":"fēi","pos":"v.","uz":"uchmoq","ru":"лететь; летать","tj":"парвоз кардан"},
        {"no":10,"zh":"好像","pinyin":"hǎoxiàng","pos":"v./adv.","uz":"o‘xshamoq; go‘yo","ru":"быть похожим; как будто","tj":"монанд будан; гӯё"},
        {"no":11,"zh":"鸟","pinyin":"niǎo","pos":"n.","uz":"qush","ru":"птица","tj":"парранда"}
    ],ensure_ascii=False),
    "proper_nouns_json":json.dumps([
        {"zh":"颐和园","pinyin":"Yíhé Yuán","en":"Summer Palace","uz":"Yiheyuan (Yozgi saroy)","ru":"Ихэюань (Летний дворец)","tj":"Ихэюан (Қасри тобистона)"}
    ],ensure_ascii=False),
    "dialogue_json":json.dumps([
        {"block_no":1,"section_label":"课文 1","scene_zh":"在教室，同学们在考试。","scene_uz":"Sinfda o‘quvchilar imtihon topshirmoqda.","scene_ru":"В классе ученики сдают экзамен.","scene_tj":"Дар синф донишҷӯён имтиҳон месупоранд.","dialogue":[
            {"speaker":"Wang Yifei","zh":"考试就要开始了，请大家写上姓名，写好后就可以做题了。","pinyin":"Kǎoshì jiù yào kāishǐ le, qǐng dàjiā xiě shàng xìngmíng, xiěhǎo hòu jiù kěyǐ zuò tí le.","uz":"Imtihon boshlanishiga oz qoldi, iltimos ism-familiyangizni yozing, yozib bo‘lgach savollarni ishlashingiz mumkin.","ru":"Экзамен сейчас начнётся. Напишите имя и фамилию; после этого можно приступать к заданиям.","tj":"Имтиҳон ҳозир оғоз мешавад. Лутфан ному насабатонро нависед; баъд аз он саволҳоро иҷро кунед."},
            {"speaker":"Bai Jiayue","zh":"老师，我做完了。","pinyin":"Lǎoshī, wǒ zuòwán le.","uz":"Ustoz, men tugatdim.","ru":"Преподаватель, я закончила.","tj":"Устод, ман тамом кардам."},
            {"speaker":"Chen Tianzhong","zh":"老师，我也做完了。","pinyin":"Lǎoshī, wǒ yě zuòwán le.","uz":"Ustoz, men ham tugatdim.","ru":"Преподаватель, я тоже закончил.","tj":"Устод, ман ҳам тамом кардам."},
            {"speaker":"Wang Yifei","zh":"……对了，你们考完试想做什么？","pinyin":"... Duì le, nǐmen kǎowán shì xiǎng zuò shénme?","uz":"Aytgancha, imtihondan keyin nima qilmoqchisizlar?","ru":"Кстати, что хотите делать после экзамена?","tj":"Ростӣ, баъди имтиҳон чӣ кор кардан мехоҳед?"},
            {"speaker":"Bai Jiayue","zh":"我很想去中国，虽然去过一次，但是很想再去一次。","pinyin":"Wǒ hěn xiǎng qù Zhōngguó, suīrán qùguo yí cì, dànshì hěn xiǎng zài qù yí cì.","uz":"Xitoyga juda borgim keladi. Bir marta borgan bo‘lsam ham, yana bir marta borishni juda xohlayman.","ru":"Я очень хочу в Китай. Хотя уже была один раз, очень хочу съездить ещё раз.","tj":"Ба Чин хеле рафтан мехоҳам. Гарчанде як бор рафтаам, боз як бор рафтан мехоҳам."},
            {"speaker":"Wang Yifei","zh":"不错，到中国后就可以经常说中文了。","pinyin":"Búcuò, dào Zhōngguó hòu jiù kěyǐ jīngcháng shuō Zhōngwén le.","uz":"Yaxshi, Xitoyga borganingdan keyin tez-tez xitoycha gaplasha olasan.","ru":"Неплохо. В Китае сможешь часто говорить по-китайски.","tj":"Хуб. Ба Чин рафта, зуд-зуд бо чинӣ гап зада метавонӣ."}
        ]},
        {"block_no":2,"section_label":"课文 2","scene_zh":"在咖啡店，李文和白家月在聊天儿。","scene_uz":"Qahvaxonada Li Wen va Bai Jiayue suhbatlashmoqda.","scene_ru":"В кафе Ли Вэнь и Бай Цзяюэ разговаривают.","scene_tj":"Дар қаҳвахона Ли Вэн ва Бай Ҷяюэ суҳбат мекунанд.","dialogue":[
            {"speaker":"Bai Jiayue","zh":"考完试了，我现在可以出国旅游了。","pinyin":"Kǎowán shì le, wǒ xiànzài kěyǐ chūguó lǚyóu le.","uz":"Imtihon tugadi, endi chet elga sayohat qila olaman.","ru":"Экзамен закончился, теперь я могу путешествовать за границу.","tj":"Имтиҳон тамом шуд, ҳоло метавонам ба хориҷ саёҳат кунам."},
            {"speaker":"Li Wen","zh":"你要去哪儿？","pinyin":"Nǐ yào qù nǎr?","uz":"Qayerga bormoqchisan?","ru":"Куда собираешься?","tj":"Ба куҷо рафтан мехоҳӣ?"},
            {"speaker":"Bai Jiayue","zh":"我要再去一次北京。","pinyin":"Wǒ yào zài qù yí cì Běijīng.","uz":"Pekinga yana bir marta bormoqchiman.","ru":"Я хочу ещё раз поехать в Пекин.","tj":"Мехоҳам боз як бор ба Пекин равам."},
            {"speaker":"Li Wen","zh":"为什么还去北京？","pinyin":"Wèishénme hái qù Běijīng?","uz":"Nega yana Pekinga?","ru":"Почему снова в Пекин?","tj":"Чаро боз ба Пекин?"},
            {"speaker":"Bai Jiayue","zh":"因为我想再吃一次烤鸭，再喝一次奶茶，再去北京大学看一次电影……","pinyin":"Yīnwèi wǒ xiǎng zài chī yí cì kǎoyā, zài hē yí cì nǎichá, zài qù Běijīng Dàxué kàn yí cì diànyǐng...","uz":"Chunki yana bir marta Pekin o‘rdagi yegim, sutli choy ichgim va Pekin universitetiga borib yana bir film ko‘rgim keladi...","ru":"Потому что хочу ещё раз поесть пекинскую утку, выпить молочный чай и снова посмотреть фильм в Пекинском университете...","tj":"Зеро мехоҳам боз як бор мурғиобии пекинӣ бихӯрам, чойи ширӣ нӯшам ва дар Донишгоҳи Пекин боз як филм бинам..."},
            {"speaker":"Li Wen","zh":"你想做的事情很多啊！","pinyin":"Nǐ xiǎng zuò de shìqing hěn duō a!","uz":"Qilmoqchi bo‘lgan ishlaring juda ko‘p ekan!","ru":"У тебя столько планов!","tj":"Корҳое, ки кардан мехоҳӣ, хеле зиёданд!"},
            {"speaker":"Bai Jiayue","zh":"是啊。你看，我还在网上买好颐和园的门票了呢。","pinyin":"Shì a. Nǐ kàn, wǒ hái zài wǎngshang mǎihǎo Yíhé Yuán de ménpiào le ne.","uz":"Ha. Qara, men Yiheyuanga kirish chiptasini ham internetdan olib qo‘ydim.","ru":"Да. Смотри, я уже купила онлайн билет в Летний дворец.","tj":"Ҳа. Бин, ман чиптаи Ихэюанро ҳам аз интернет харида мондам."},
            {"speaker":"Li Wen","zh":"我的高中同学就在颐和园上班，可以让他给你好好介绍介绍。","pinyin":"Wǒ de gāozhōng tóngxué jiù zài Yíhé Yuán shàngbān, kěyǐ ràng tā gěi nǐ hǎohāo jièshao jièshao.","uz":"Mening maktabdagi sinfdoshim Yiheyuanda ishlaydi, u senga yaxshilab tanishtirib bera oladi.","ru":"Мой школьный одноклассник работает в Летнем дворце, он сможет хорошо всё тебе показать и рассказать.","tj":"Ҳамсинфи мактабиам дар Ихэюан кор мекунад, метавонад ба ту хуб шинос кунад."},
            {"speaker":"Bai Jiayue","zh":"太好了！出门旅游，多个朋友多条路。","pinyin":"Tài hǎo le! Chūmén lǚyóu, duō ge péngyou duō tiáo lù.","uz":"Zo‘r! Sayohatga chiqqanda bir do‘st ko‘p bo‘lsa, bir yo‘l ko‘p.","ru":"Отлично! В поездке лишний друг — лишний путь и возможность.","tj":"Олиҷаноб! Дар сафар як дӯст бештар — як роҳ бештар."}
        ]},
        {"block_no":3,"section_label":"课文 3","scene_zh":"在咖啡店，李文和白家月在聊天儿。","scene_uz":"Qahvaxonada Li Wen va Bai Jiayue suhbatlashmoqda.","scene_ru":"В кафе Ли Вэнь и Бай Цзяюэ разговаривают.","scene_tj":"Дар қаҳвахона Ли Вэн ва Бай Ҷяюэ суҳбат мекунанд.","dialogue":[
            {"speaker":"Bai Jiayue","zh":"李文，你有一年没回国了吧？","pinyin":"Lǐ Wén, nǐ yǒu yì nián méi huíguó le ba?","uz":"Li Wen, vatanga qaytmaganingga bir yil bo‘ldi-a?","ru":"Ли Вэнь, ты уже год не возвращался домой, да?","tj":"Ли Вэн, як сол шуд ба ватан барнагаштаӣ, дуруст?"},
            {"speaker":"Li Wen","zh":"不到一年。我六月的时候回去了一次。","pinyin":"Bú dào yì nián. Wǒ Liùyuè de shíhou huíqùle yí cì.","uz":"Bir yil bo‘lgani yo‘q. Iyun oyida bir marta qaytgandim.","ru":"Ещё не год. Я один раз ездил домой в июне.","tj":"Ҳанӯз як сол не. Моҳи июн як бор баргашта будам."},
            {"speaker":"Bai Jiayue","zh":"我怎么忘了？还是我送你去的机场呢。","pinyin":"Wǒ zěnme wàng le? Háishi wǒ sòng nǐ qù de jīchǎng ne.","uz":"Qanday unutibman? Axir seni aeroportga men kuzatgan edim.","ru":"Как я могла забыть? Ведь именно я провожала тебя в аэропорт.","tj":"Чӣ хел фаромӯш кардаам? Охир ман туро ба фурудгоҳ гусел карда будам."},
            {"speaker":"Li Wen","zh":"是啊。","pinyin":"Shì a.","uz":"Ha.","ru":"Да.","tj":"Ҳа."},
            {"speaker":"Bai Jiayue","zh":"我记得你那次的机票很便宜。","pinyin":"Wǒ jìde nǐ nà cì de jīpiào hěn piányi.","uz":"Esimda, o‘sha safardagi aviachiptang juda arzon edi.","ru":"Помню, тогда твой авиабилет был очень дешёвым.","tj":"Дар хотир дорам, он дафъа чиптаи ҳавопаймоят хеле арзон буд."},
            {"speaker":"Li Wen","zh":"没错，可能因为那个时候去北京的人不多吧。","pinyin":"Méi cuò, kěnéng yīnwèi nàge shíhou qù Běijīng de rén bù duō ba.","uz":"To‘g‘ri, ehtimol o‘sha paytda Pekinga boradigan odamlar ko‘p bo‘lmagan.","ru":"Верно, возможно, потому что тогда в Пекин ехало не так много людей.","tj":"Дуруст, шояд он вақт ба Пекин одамони зиёд намерафтанд."},
            {"speaker":"Bai Jiayue","zh":"这次的机票虽然有点儿贵，但想到就要飞北京了，我还是很高兴的。","pinyin":"Zhè cì de jīpiào suīrán yǒudiǎnr guì, dàn xiǎngdào jiù yào fēi Běijīng le, wǒ háishi hěn gāoxìng de.","uz":"Bu safargi chipta biroz qimmat bo‘lsa ham, tez orada Pekinga uchishimni o‘ylasam, baribir juda xursandman.","ru":"Хотя билет в этот раз дороговат, когда думаю, что скоро полечу в Пекин, всё равно очень радуюсь.","tj":"Гарчанде чиптаи ин дафъа каме гарон аст, вақте фикр мекунам ба зудӣ ба Пекин мепарам, боз ҳам хеле хушҳолам."}
        ]},
        {"block_no":4,"section_label":"课文 4","scene_zh":"在房间，李文在写日记。","scene_uz":"Xonada Li Wen kundalik yozmoqda.","scene_ru":"В комнате Ли Вэнь пишет дневник.","scene_tj":"Дар ҳуҷра Ли Вэн рӯзнома менависад.","dialogue":[
            {"speaker":"Narration","zh":"我六月的时候回过一次北京，现在有半年多没回去了，我有点儿想家。就要过年了，我要回家过年。家月这次也要去北京，我们都是星期五的飞机。家月说我们好像小鸟，一起飞到北京，再一起飞回这里。","pinyin":"Wǒ Liùyuè de shíhou huíguo yí cì Běijīng, xiànzài yǒu bàn nián duō méi huíqù le, wǒ yǒudiǎnr xiǎng jiā. Jiù yào guònián le, wǒ yào huí jiā guònián. Jiāyuè zhè cì yě yào qù Běijīng, wǒmen dōu shì Xīngqīwǔ de fēijī. Jiāyuè shuō wǒmen hǎoxiàng xiǎoniǎo, yìqǐ fēi dào Běijīng, zài yìqǐ fēi huí zhèlǐ.","uz":"Iyun oyida Pekinga bir marta qaytgan edim. Hozir qaytmaganimga yarim yildan oshdi, uyimni biroz sog‘indim. Yangi yil yaqin, uyga qaytib bayram qilaman. Bu safar Jiayue ham Pekinga boradi, ikkalamizning samolyotimiz juma kuni. Jiayue aytishicha, biz go‘yo kichik qushlarmiz: birga Pekinga uchamiz, keyin yana birga bu yerga uchib qaytamiz.","ru":"В июне я один раз ездил в Пекин, а теперь уже больше полугода не возвращался и немного скучаю по дому. Скоро Новый год, я поеду домой праздновать. Цзяюэ тоже летит в Пекин, у нас обоих рейс в пятницу. Она сказала, что мы похожи на маленьких птиц: вместе летим в Пекин, а потом вместе обратно сюда.","tj":"Моҳи июн як бор ба Пекин баргашта будам. Ҳоло зиёда аз ним сол аст барнагаштаам ва каме хонаамро пазмон шудам. Соли нав наздик аст, ба хона бармегардам. Ҷяюэ ҳам ин дафъа ба Пекин меравад, ҳардуямон рӯзи ҷумъа парвоз дорем. Ӯ гуфт мо гӯё паррандаҳои хурдем: якҷо ба Пекин мепарем ва боз якҷо ба ин ҷо бармегардем."}
        ]}
    ],ensure_ascii=False),
    "grammar_json":json.dumps([
        {"no":1,"title_zh":"动量补语（1）","title_uz":"Takror soni to‘ldiruvchisi (1)","title_ru":"Дополнение кратности (1)","title_tj":"Пуркунандаи такрор (1)","rule_zh":"“数词+次”用在动词后面，构成动量补语，表示动作发生的次数。动词同时带宾语时，如果宾语是人名或地名，放在动量补语前后都可以。","rule_uz":"“son+次” fe’ldan keyin kelib, harakat necha marta sodir bo‘lganini bildiradi. Fe’l obyekt ham olsa, obyekt odam yoki joy nomi bo‘lsa frequency complement oldida ham, keyin ham kelishi mumkin.","rule_ru":"“числительное+次” после глагола образует дополнение кратности и показывает число повторений действия. Если объект — имя человека или место, он может стоять до или после дополнения.","rule_tj":"“шумора+次” баъди феъл омада, шумораи рух додани амалро нишон медиҳад. Агар объект номи шахс ё ҷой бошад, метавонад пеш ё пас аз пуркунандаи такрор ояд.","examples":[{"zh":"我想去中国，虽然去过一次，但是很想再去一次。"},{"zh":"安妮去过一次北京。"},{"zh":"李文见了杨同乐两次。"}]},
        {"no":2,"title_zh":"动量补语（2）","title_uz":"Takror soni to‘ldiruvchisi (2)","title_ru":"Дополнение кратности (2)","title_tj":"Пуркунандаи такрор (2)","rule_zh":"动词既带动量补语，又带宾语时，如果宾语是事物名词，一般放在动量补语后面；如果宾语是代词，放在动量补语前面。","rule_uz":"Fe’l frequency complement va obyekt bilan kelganda, obyekt narsa oti bo‘lsa odatda frequency complementdan keyin; olmosh bo‘lsa uning oldidan keladi.","rule_ru":"Если у глагола есть и дополнение кратности, и объект: предметный объект обычно ставится после дополнения, а местоимение — перед ним.","rule_tj":"Агар феъл ҳам пуркунандаи такрор ва ҳам объект дошта бошад, объекти ашёӣ одатан пас аз пуркунанда, ҷонишин бошад пеш аз он меояд.","examples":[{"zh":"因为我想再吃一次烤鸭，再喝一次奶茶。"},{"zh":"我想找他一次。"},{"zh":"安妮来过这儿两次。"}]},
        {"no":3,"title_zh":"“有”字句（2）","title_uz":"“有” gapi (2)","title_ru":"Предложение с “有” (2)","title_tj":"Ҷумлаи “有” (2)","rule_zh":"“有+数量短语”表示达到一定的数量。","rule_uz":"“有+miqdor birikmasi” ma’lum bir miqdorga yetganlikni bildiradi.","rule_ru":"“有+количественная группа” показывает достижение определённого количества.","rule_tj":"“有+таркиби миқдорӣ” расидан ба миқдори муайянро нишон медиҳад.","examples":[{"zh":"你有一年没回国了吧？"},{"zh":"你女儿今年有10岁了吧？"},{"zh":"我有一个月没给家里打电话了。"}]}
    ],ensure_ascii=False)
}
