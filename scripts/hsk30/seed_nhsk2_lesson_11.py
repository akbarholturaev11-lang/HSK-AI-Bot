from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(109, 118)),
    "printed_pages": list(range(93, 102)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk2",
    "lesson_order": 11,
    "lesson_code": "NHSK2-L11",
    "title": "我最喜欢吃中国菜",
    "title_pinyin": "Wǒ zuì xǐhuan chī Zhōngguó cài",
    "goal": json.dumps({
        "uz": "“着” bilan davom etayotgan holat yoki harakatni ifodalash; “着”li gapda obyekt va savol shakllarini to‘g‘ri ishlatish; “最” bilan eng yuqori darajani ifodalash; salomatlik va ovqat haqida gaplashish.",
        "ru": "Выражать продолжающееся действие или состояние с “着”; правильно располагать объект и строить вопросы в предложениях с “着”; выражать превосходную степень с “最”; говорить о самочувствии и еде.",
        "tj": "Бо “着” амал ё ҳолати давомдорро ифода кардан; объект ва шаклҳои саволро дар ҷумлаҳои “着” дуруст истифода бурдан; бо “最” дараҷаи олитаринро ифода кардан; дар бораи саломатӣ ва хӯрок суҳбат кардан.",
    }, ensure_ascii=False),
    "intro_text": json.dumps({
        "uz": "Dars bosh og‘rig‘i, shifoxonaga borish, do‘stni ko‘rishga kelish va kundalik matni orqali “着”ning ikki qo‘llanilishi hamda “最”ni o‘rgatadi.",
        "ru": "Урок через головную боль, поездку в больницу, визит друга и дневниковую запись вводит два употребления “着” и наречие “最”.",
        "tj": "Дарс тавассути дарди сар, рафтан ба беморхона, дидани дӯст ва навиштаи рӯзнома ду истифодаи “着” ва “最”-ро меомӯзонад.",
    }, ensure_ascii=False),
    "vocabulary_json": json.dumps([
        {"no":1,"zh":"头","pinyin":"tóu","pos":"n.","uz":"bosh","ru":"голова","tj":"сар"},
        {"no":2,"zh":"疼","pinyin":"téng","pos":"adj.","uz":"og‘rimoq; og‘riqli","ru":"болеть; больной","tj":"дард кардан"},
        {"no":3,"zh":"经常","pinyin":"jīngcháng","pos":"adv.","uz":"tez-tez; ko‘pincha","ru":"часто","tj":"зуд-зуд; аксар вақт"},
        {"no":4,"zh":"动","pinyin":"dòng","pos":"v.","uz":"qimirlamoq; harakatlanmoq","ru":"двигаться","tj":"ҳаракат кардан"},
        {"no":5,"zh":"着","pinyin":"zhe","pos":"part.","uz":"davomiy holat/harakat yuklamasi","ru":"аспектная частица продолженности","tj":"ҳиссачаи давомнокии ҳолат/амал"},
        {"no":6,"zh":"路上","pinyin":"lùshang","pos":"n.","uz":"yo‘lda","ru":"в дороге; на дороге","tj":"дар роҳ"},
        {"no":7,"zh":"慢","pinyin":"màn","pos":"adj.","uz":"sekin","ru":"медленный","tj":"суст"},
        {"no":8,"zh":"进","pinyin":"jìn","pos":"v.","uz":"kirmoq","ru":"входить","tj":"даромадан"},
        {"no":9,"zh":"药","pinyin":"yào","pos":"n.","uz":"dori","ru":"лекарство","tj":"дору"},
        {"no":10,"zh":"身体","pinyin":"shēntǐ","pos":"n.","uz":"tana; salomatlik","ru":"тело; здоровье","tj":"бадан; саломатӣ"},
        {"no":11,"zh":"时","pinyin":"shí","pos":"n.","uz":"vaqt; payt","ru":"время; период","tj":"вақт; ҳангом"},
        {"no":12,"zh":"最","pinyin":"zuì","pos":"adv.","uz":"eng","ru":"самый; наиболее","tj":"аз ҳама; бештар"},
        {"no":13,"zh":"药店","pinyin":"yàodiàn","pos":"n.","uz":"dorixona","ru":"аптека","tj":"дорухона"},
    ], ensure_ascii=False),
    "proper_nouns_json": json.dumps([], ensure_ascii=False),
    "dialogue_json": json.dumps([
        {
            "block_no":1,
            "section_label":"课文 1",
            "scene_zh":"在教室，王一飞和白家月在聊天儿。",
            "scene_uz":"Sinfda Wang Yifei va Bai Jiayue suhbatlashmoqda.",
            "scene_ru":"В классе Ван Ифэй и Бай Цзяюэ разговаривают.",
            "scene_tj":"Дар синф Ван Ифэй ва Бай Ҷяюэ суҳбат мекунанд.",
            "dialogue":[
                {"speaker":"Wang Yifei","zh":"家月，都下课了，你怎么还不回家？","pinyin":"Jiāyuè, dōu xiàkè le, nǐ zěnme hái bù huí jiā?","uz":"Jiayue, dars tugadi-ku, nega hali uyga ketmading?","ru":"Цзяюэ, урок уже закончился, почему ты ещё не идёшь домой?","tj":"Ҷяюэ, дарс тамом шуд, чаро ҳоло ҳам ба хона намеравӣ?"},
                {"speaker":"Bai Jiayue","zh":"我头疼，不太舒服。","pinyin":"Wǒ tóu téng, bú tài shūfu.","uz":"Boshim og‘riyapti, o‘zimni yaxshi his qilmayapman.","ru":"У меня болит голова, я не очень хорошо себя чувствую.","tj":"Сарам дард мекунад, худро хуб ҳис намекунам."},
                {"speaker":"Wang Yifei","zh":"你这几天经常头疼，去医院看看吧。","pinyin":"Nǐ zhè jǐ tiān jīngcháng tóu téng, qù yīyuàn kànkan ba.","uz":"Shu kunlarda boshing tez-tez og‘riyapti, shifoxonaga borib ko‘rin.","ru":"В последние дни у тебя часто болит голова, сходи в больницу.","tj":"Ин чанд рӯз сарат зуд-зуд дард мекунад, ба беморхона рафта муоина шав."},
                {"speaker":"Bai Jiayue","zh":"我想休息一下，现在不能动，一动就疼。","pinyin":"Wǒ xiǎng xiūxi yíxià, xiànzài bù néng dòng, yí dòng jiù téng.","uz":"Biroz dam olmoqchiman, hozir qimirlolmayman, qimirlasam darrov og‘riydi.","ru":"Хочу немного отдохнуть. Сейчас не могу двигаться: как только двигаюсь, сразу болит.","tj":"Мехоҳам каме истироҳат кунам, ҳоло ҳаракат карда наметавонам, ҳамин ки ҳаракат кунам, дард мекунад."},
                {"speaker":"Wang Yifei","zh":"那你在这儿坐着，我去开车，一会儿送你去医院。","pinyin":"Nà nǐ zài zhèr zuòzhe, wǒ qù kāichē, yíhuìr sòng nǐ qù yīyuàn.","uz":"Unda shu yerda o‘tirib tur, men mashinani olib kelaman, keyin seni shifoxonaga olib boraman.","ru":"Тогда посиди здесь, я возьму машину и через немного времени отвезу тебя в больницу.","tj":"Пас ҳамин ҷо нишаста ист, ман мошинро меорам ва каме баъд туро ба беморхона мебарам."},
                {"speaker":"Bai Jiayue","zh":"谢谢王老师。","pinyin":"Xièxie Wáng lǎoshī.","uz":"Rahmat, ustoz Wang.","ru":"Спасибо, преподаватель Ван.","tj":"Раҳмат, устод Ван."}
            ]
        },
        {
            "block_no":2,
            "section_label":"课文 2",
            "scene_zh":"在王一飞车里，王一飞和白家月在聊天儿，李文打来一个电话。",
            "scene_uz":"Wang Yifeining mashinasida Wang Yifei va Bai Jiayue suhbatlashmoqda, Li Wen telefon qildi.",
            "scene_ru":"В машине Ван Ифэй разговаривает с Бай Цзяюэ; звонит Ли Вэнь.",
            "scene_tj":"Дар мошини Ван Ифэй ӯ бо Бай Ҷяюэ суҳбат мекунад ва Ли Вэн занг мезанад.",
            "dialogue":[
                {"speaker":"Wang Yifei","zh":"现在路上车多，还下着雪，我开慢一点儿。","pinyin":"Xiànzài lùshang chē duō, hái xiàzhe xuě, wǒ kāi màn yìdiǎnr.","uz":"Hozir yo‘lda mashina ko‘p, yana qor yog‘ayapti, men sekinroq haydayman.","ru":"Сейчас на дороге много машин, ещё идёт снег, я поеду помедленнее.","tj":"Ҳоло дар роҳ мошин зиёд аст, барф ҳам меборад, ман сусттар меронам."},
                {"speaker":"Bai Jiayue","zh":"没问题，现在头没那么疼了。","pinyin":"Méi wèntí, xiànzài tóu méi nàme téng le.","uz":"Mayli, hozir boshim unchalik og‘rimayapti.","ru":"Хорошо, сейчас голова уже не так сильно болит.","tj":"Хуб, ҳоло сарам он қадар дард намекунад."},
                {"speaker":"Wang Yifei","zh":"好。李文来电话了，你帮我接一下。","pinyin":"Hǎo. Lǐ Wén lái diànhuà le, nǐ bāng wǒ jiē yíxià.","uz":"Xo‘p. Li Wen qo‘ng‘iroq qilyapti, men uchun javob ber.","ru":"Хорошо. Звонит Ли Вэнь, ответь за меня.","tj":"Хуб. Ли Вэн занг мезанад, барои ман ҷавоб деҳ."},
                {"speaker":"Bai Jiayue","zh":"喂，李文，王老师开着车呢，你找她有事吗？","pinyin":"Wèi, Lǐ Wén, Wáng lǎoshī kāizhe chē ne, nǐ zhǎo tā yǒu shì ma?","uz":"Allo, Li Wen, ustoz Wang mashina haydayapti, unga ishing bormi?","ru":"Алло, Ли Вэнь, преподаватель Ван сейчас за рулём. Ты по делу?","tj":"Алло, Ли Вэн, устод Ван ҳоло мошин меронад, ба ӯ кор дорӣ?"},
                {"speaker":"Li Wen","zh":"没什么事。今天雪这么大，你们开车去哪儿啊？","pinyin":"Méi shénme shì. Jīntiān xuě zhème dà, nǐmen kāichē qù nǎr a?","uz":"Muhim ish yo‘q. Bugun qor juda kuchli, mashinada qayerga ketyapsizlar?","ru":"Ничего важного. Сегодня такой сильный снег, куда вы едете?","tj":"Кори муҳиме нест. Имрӯз барф ин қадар зиёд, бо мошин ба куҷо меравед?"},
                {"speaker":"Bai Jiayue","zh":"去医院，我头有点儿疼。","pinyin":"Qù yīyuàn, wǒ tóu yǒudiǎnr téng.","uz":"Shifoxonaga, boshim biroz og‘riyapti.","ru":"В больницу, у меня немного болит голова.","tj":"Ба беморхона, сарам каме дард мекунад."},
                {"speaker":"Li Wen","zh":"那我一会儿去看看你。","pinyin":"Nà wǒ yíhuìr qù kànkan nǐ.","uz":"Unda birozdan keyin seni ko‘rgani boraman.","ru":"Тогда я чуть позже зайду тебя навестить.","tj":"Пас каме баъд туро дидан меоям."}
            ]
        },
        {
            "block_no":3,
            "section_label":"课文 3",
            "scene_zh":"在房间，李文来看望白家月。",
            "scene_uz":"Xonada Li Wen Bai Jiayueni ko‘rgani keldi.",
            "scene_ru":"В комнате Ли Вэнь пришёл навестить Бай Цзяюэ.",
            "scene_tj":"Дар ҳуҷра Ли Вэн барои дидани Бай Ҷяюэ омадааст.",
            "dialogue":[
                {"speaker":"Bai Jiayue","zh":"李文，快请进！","pinyin":"Lǐ Wén, kuài qǐng jìn!","uz":"Li Wen, tez kir!","ru":"Ли Вэнь, заходи скорее!","tj":"Ли Вэн, зуд даро!"},
                {"speaker":"Li Wen","zh":"家月，你怎么样了？头还疼吗？","pinyin":"Jiāyuè, nǐ zěnmeyàng le? Tóu hái téng ma?","uz":"Jiayue, qalaysan? Boshing hali og‘riyaptimi?","ru":"Цзяюэ, как ты? Голова ещё болит?","tj":"Ҷяюэ, аҳволат чӣ хел? Сарат ҳоло ҳам дард мекунад?"},
                {"speaker":"Bai Jiayue","zh":"不那么疼了。医生开了一些药，吃完就好多了。","pinyin":"Bú nàme téng le. Yīshēng kāile yìxiē yào, chīwán jiù hǎoduō le.","uz":"Unchalik og‘rimayapti. Shifokor dori yozib berdi, ichganimdan keyin ancha yaxshi bo‘ldim.","ru":"Уже не так болит. Врач выписал лекарства, после них стало намного лучше.","tj":"Дигар он қадар дард намекунад. Духтур дору навишт, баъди истеъмол хеле беҳтар шудам."},
                {"speaker":"Li Wen","zh":"那就好！","pinyin":"Nà jiù hǎo!","uz":"Unda yaxshi!","ru":"Вот и хорошо!","tj":"Хуб шудааст!"},
                {"speaker":"Wang Yifei","zh":"家月，你想不想吃点儿东西？","pinyin":"Jiāyuè, nǐ xiǎng bu xiǎng chī diǎnr dōngxi?","uz":"Jiayue, biror narsa yeging keladimi?","ru":"Цзяюэ, хочешь что-нибудь поесть?","tj":"Ҷяюэ, чизе хӯрдан мехоҳӣ?"},
                {"speaker":"Li Wen","zh":"吃点儿吧，身体不舒服时更要好好吃饭。","pinyin":"Chī diǎnr ba, shēntǐ bù shūfu shí gèng yào hǎohāo chī fàn.","uz":"Biroz ye, o‘zingni yomon his qilgan paytingda yanada yaxshiroq ovqatlanish kerak.","ru":"Поешь немного. Когда плохо себя чувствуешь, особенно важно нормально питаться.","tj":"Каме бихӯр, вақте худро бад ҳис мекунӣ, боз ҳам хубтар хӯрок хӯрдан лозим."},
                {"speaker":"Bai Jiayue","zh":"吃点儿什么呢？","pinyin":"Chī diǎnr shénme ne?","uz":"Nima yesam ekan?","ru":"Что бы поесть?","tj":"Чӣ бихӯрам?"},
                {"speaker":"Wang Yifei","zh":"你最喜欢吃中国菜，我做几个中国菜吧。","pinyin":"Nǐ zuì xǐhuan chī Zhōngguó cài, wǒ zuò jǐ ge Zhōngguó cài ba.","uz":"Sen eng ko‘p xitoy taomlarini yoqtirasan, bir nechta xitoy taomi tayyorlayman.","ru":"Ты больше всего любишь китайскую кухню, приготовлю несколько китайских блюд.","tj":"Ту аз ҳама бештар хӯроки чиниро дӯст медорӣ, чанд хӯроки чинӣ тайёр мекунам."},
                {"speaker":"Bai Jiayue","zh":"好的，谢谢王老师。","pinyin":"Hǎo de, xièxie Wáng lǎoshī.","uz":"Xo‘p, rahmat, ustoz Wang.","ru":"Хорошо, спасибо, преподаватель Ван.","tj":"Хуб, раҳмат, устод Ван."}
            ]
        },
        {
            "block_no":4,
            "section_label":"课文 4",
            "scene_zh":"在房间，白家月在写日记。",
            "scene_uz":"Xonada Bai Jiayue kundalik yozmoqda.",
            "scene_ru":"В комнате Бай Цзяюэ пишет дневник.",
            "scene_tj":"Дар ҳуҷра Бай Ҷяюэ рӯзнома менависад.",
            "dialogue":[
                {"speaker":"Narration","zh":"我这几天经常头疼，从药店买了点儿药，没去医院。今天下课后，王老师看我不舒服，就送我去医院了。从医院回来，李文也来看我了。现在他们都回去了，我也要睡觉了。","pinyin":"Wǒ zhè jǐ tiān jīngcháng tóu téng, cóng yàodiàn mǎile diǎnr yào, méi qù yīyuàn. Jīntiān xiàkè hòu, Wáng lǎoshī kàn wǒ bù shūfu, jiù sòng wǒ qù yīyuàn le. Cóng yīyuàn huílái, Lǐ Wén yě lái kàn wǒ le. Xiànzài tāmen dōu huíqù le, wǒ yě yào shuìjiào le.","uz":"Shu kunlarda boshim tez-tez og‘riyapti. Dorixonadan biroz dori oldim, lekin shifoxonaga bormadim. Bugun darsdan keyin ustoz Wang o‘zimni yomon his qilayotganimni ko‘rib, meni shifoxonaga olib bordi. Shifoxonadan qaytgach, Li Wen ham ko‘rgani keldi. Hozir ular qaytishdi, men ham uxlamoqchiman.","ru":"Последние дни у меня часто болела голова. Я купила лекарство в аптеке, но в больницу не ходила. Сегодня после урока преподаватель Ван увидела, что мне плохо, и отвезла меня в больницу. После возвращения Ли Вэнь тоже пришёл меня навестить. Сейчас они уже ушли, и я тоже собираюсь спать.","tj":"Ин чанд рӯз сарам зуд-зуд дард мекард. Аз дорухона каме дору харидам, аммо ба беморхона нарафтам. Имрӯз баъди дарс устод Ван дид, ки худро бад ҳис мекунам ва маро ба беморхона бурд. Баъди бозгашт Ли Вэн ҳам ба диданам омад. Ҳоло онҳо рафтанд, ман ҳам хоб карданӣ ҳастам."}
            ]
        }
    ], ensure_ascii=False),
    "grammar_json": json.dumps([
        {
            "no":1,
            "title_zh":"动态助词“着”（1）",
            "title_uz":"Aspekt yuklamasi “着” (1)",
            "title_ru":"Аспектная частица “着” (1)",
            "title_tj":"Ҳиссачаи аспектии “着” (1)",
            "rule_zh":"动态助词“着”用在动词后面，表示动作或状态的持续，否定形式是在动词前面加“没（有）”。",
            "rule_uz":"“着” fe’ldan keyin kelib, harakat yoki holatning davom etishini bildiradi. Inkor shakli fe’l oldiga 没（有） qo‘yish bilan tuziladi.",
            "rule_ru":"“着” ставится после глагола и выражает продолжение действия или состояния. Отрицание образуется с 没（有） перед глаголом.",
            "rule_tj":"“着” баъди феъл омада, давом ёфтани амал ё ҳолатро ифода мекунад. Инкор бо 没（有） пеш аз феъл сохта мешавад.",
            "examples":[{"zh":"那你在这儿坐着。"},{"zh":"教室的门开着。"},{"zh":"教室的门没开着。"}]
        },
        {
            "no":2,
            "title_zh":"动态助词“着”（2）",
            "title_uz":"Aspekt yuklamasi “着” (2)",
            "title_ru":"Аспектная частица “着” (2)",
            "title_tj":"Ҳиссачаи аспектии “着” (2)",
            "rule_zh":"表示动作或状态持续的句子中，宾语要在动态助词“着”的后面。疑问形式有三种：（1）在句尾加“吗”；（2）在句尾加“没有”；（3）动词+没+动词+着。",
            "rule_uz":"Davom etayotgan harakat/holat gapida obyekt “着”dan keyin turadi. Savolning uch shakli bor: gap oxiriga 吗; gap oxiriga 没有; yoki V+没+V+着.",
            "rule_ru":"В предложении с продолжающимся действием/состоянием объект ставится после “着”. Три вопросительные формы: 吗 в конце; 没有 в конце; либо V+没+V+着.",
            "rule_tj":"Дар ҷумлаи амали/ҳолати давомдор объект пас аз “着” меояд. Се шакли савол: 吗 дар охир; 没有 дар охир; ё V+没+V+着.",
            "examples":[{"zh":"现在路上车多，还下着雪，我开慢一点儿。"},{"zh":"她穿着白色的裤子。"},{"zh":"陈天中没拿着咖啡。"},{"zh":"教室的门开着吗？"},{"zh":"白家月坐着没有？"},{"zh":"她拿没拿着手机？"}]
        },
        {
            "no":3,
            "title_zh":"程度副词“最”",
            "title_uz":"Daraja ravishi “最”",
            "title_ru":"Наречие степени “最”",
            "title_tj":"Зарфи дараҷаи “最”",
            "rule_zh":"程度副词“最”用在形容词或心理动词前面，表示某种属性超过所有同类的人或事物。",
            "rule_uz":"“最” sifat yoki psixologik fe’l oldidan kelib, ma’lum xususiyat bir xil turdagi hamma odam yoki narsadan yuqori ekanini bildiradi.",
            "rule_ru":"“最” ставится перед прилагательным или психологическим глаголом и показывает высшую степень признака среди однородных людей или предметов.",
            "rule_tj":"“最” пеш аз сифат ё феъли равонӣ омада, баландтарин дараҷаи хусусиятро миёни ашхос ё ашёи ҳамнавъ нишон медиҳад.",
            "examples":[{"zh":"你最喜欢吃中国菜。"},{"zh":"在我们家，爸爸最高。"},{"zh":"你们班谁说中文说得最好？"}]
        }
    ], ensure_ascii=False),
}
