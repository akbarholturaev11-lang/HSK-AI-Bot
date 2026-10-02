from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程1",
    "pdf_path": "HSK 3.0 PDF/新HSK教程1.pdf",
    "pdf_pages": [41, 42, 43, 44, 45, 46, 47, 48],
    "printed_pages": [27, 28, 29, 30, 31, 32, 33, 34],
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk1",
    "lesson_order": 5,
    "lesson_code": "NHSK1-L05",
    "title": "今天我休息",
    "title_pinyin": "Jīntiān wǒ xiūxi",
    "goal": json.dumps(
        {
            "uz": "Sana va hafta kunlarini xitoycha tartibda aytish; “会” bilan o‘rganilgan qobiliyatni ifodalash; nominal-predikativ gaplarni tushunish va ishlatish.",
            "ru": "Называть даты и дни недели по-китайски; выражать приобретённое умение с “会”; понимать и использовать именные сказуемые.",
            "tj": "Сана ва рӯзҳои ҳафтаро бо тартиби чинӣ гуфтан; бо “会” қобилияти омӯхташударо ифода кардан; ҷумлаҳои номӣ-хабариро фаҳмидан ва истифода бурдан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars sana, dam olish kuni, ovqat pishirish va yangi kompyuter haqidagi uchta dialog orqali vaqt ifodasi, nominal gap va “会” ni o‘rgatadi.",
            "ru": "Урок через три диалога о дате, выходном дне, готовке и новом компьютере вводит выражение времени, именное сказуемое и “会”.",
            "tj": "Дарс тавассути се гуфтугӯ дар бораи сана, рӯзи истироҳат, пухтупаз ва компютери нав ифодаи вақт, ҷумлаи номӣ ва “会”-ро меомӯзонад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no":1,"zh":"今天","pinyin":"jīntiān","pos":"n.","uz":"bugun","ru":"сегодня","tj":"имрӯз"},
            {"no":2,"zh":"号","pinyin":"hào","pos":"m.","uz":"sana (oy kuni)","ru":"число месяца","tj":"санаи моҳ"},
            {"no":3,"zh":"月","pinyin":"yuè","pos":"n.","uz":"oy","ru":"месяц","tj":"моҳ"},
            {"no":4,"zh":"日","pinyin":"rì","pos":"m.","uz":"kun; sana","ru":"день; дата","tj":"рӯз; сана"},
            {"no":5,"zh":"星期","pinyin":"xīngqī","pos":"n.","uz":"hafta","ru":"неделя","tj":"ҳафта"},
            {"no":6,"zh":"星期日","pinyin":"Xīngqīrì","pos":"n.","uz":"yakshanba","ru":"воскресенье","tj":"якшанбе"},
            {"no":7,"zh":"星期天","pinyin":"Xīngqītiān","pos":"n.","uz":"yakshanba","ru":"воскресенье","tj":"якшанбе"},
            {"no":8,"zh":"休息","pinyin":"xiūxi","pos":"v.","uz":"dam olmoq","ru":"отдыхать","tj":"истироҳат кардан"},
            {"no":9,"zh":"会","pinyin":"huì","pos":"mod.","uz":"qila olmoq; bilmoq","ru":"уметь; мочь","tj":"тавонистан; уҳда кардан"},
            {"no":10,"zh":"做饭","pinyin":"zuò fàn","pos":"comp.","uz":"ovqat pishirmoq","ru":"готовить еду","tj":"хӯрок пухтан"},
            {"no":11,"zh":"做","pinyin":"zuò","pos":"v.","uz":"qilmoq; tayyorlamoq","ru":"делать; готовить","tj":"кардан; тайёр кардан"},
            {"no":12,"zh":"面条儿","pinyin":"miàntiáor","pos":"n.","uz":"lag‘mon; lapsha","ru":"лапша","tj":"угро"},
            {"no":13,"zh":"饺子","pinyin":"jiǎozi","pos":"n.","uz":"jiaozi; chuchvara","ru":"цзяоцзы; пельмени","tj":"ҷяозы; тушбера"},
            {"no":14,"zh":"一些","pinyin":"yìxiē","pos":"num.","uz":"bir oz; ba’zi","ru":"немного; некоторые","tj":"каме; баъзе"},
            {"no":15,"zh":"菜","pinyin":"cài","pos":"n.","uz":"taom; ovqat","ru":"блюдо; еда","tj":"таом; хӯрок"},
            {"no":16,"zh":"下班","pinyin":"xiàbān","pos":"v.","uz":"ishdan chiqmoq","ru":"заканчивать работу","tj":"аз кор баромадан"},
            {"no":17,"zh":"新","pinyin":"xīn","pos":"adj.","uz":"yangi","ru":"новый","tj":"нав"},
            {"no":18,"zh":"电脑","pinyin":"diànnǎo","pos":"n.","uz":"kompyuter","ru":"компьютер","tj":"компютер"},
            {"no":19,"zh":"真","pinyin":"zhēn","pos":"adv.","uz":"haqiqatan; juda","ru":"действительно; очень","tj":"воқеан; хеле"},
            {"no":20,"zh":"好看","pinyin":"hǎokàn","pos":"adj.","uz":"chiroyli; yaxshi ko‘rinadigan","ru":"красивый; хорошо выглядящий","tj":"зебо; хушнамо"},
            {"no":21,"zh":"喜欢","pinyin":"xǐhuan","pos":"v.","uz":"yoqtirmoq","ru":"нравиться; любить","tj":"писанд кардан"},
            {"no":22,"zh":"它","pinyin":"tā","pos":"pron.","uz":"u (narsa/hayvon)","ru":"оно; он/она о предмете","tj":"он/он (барои чиз)"},
        ],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no":1,"section_label":"课文 1",
                "scene_zh":"在家里，刘明和王一雪在聊天儿。",
                "scene_en":"At home, Liu Ming and Wang Yixue were chatting.",
                "scene_uz":"Uyda Liu Ming va Wang Yixue suhbatlashmoqda.",
                "scene_ru":"Дома Лю Мин и Ван Исюэ разговаривают.",
                "scene_tj":"Дар хона Лю Мин ва Ван Исюэ суҳбат мекунанд.",
                "dialogue":[
                    {"speaker":"Wang Yixue","zh":"今天几号？","pinyin":"Jīntiān jǐ hào?","en":"What's the date today?","uz":"Bugun nechanchi sana?","ru":"Какое сегодня число?","tj":"Имрӯз чандум аст?"},
                    {"speaker":"Liu Ming","zh":"今天9月8号。","pinyin":"Jīntiān jiǔ yuè bā hào.","en":"It's September 8.","uz":"Bugun 8-sentabr.","ru":"Сегодня 8 сентября.","tj":"Имрӯз 8 сентябр аст."},
                    {"speaker":"Wang Yixue","zh":"星期几？","pinyin":"Xīngqī jǐ?","en":"What day is it today?","uz":"Bugun haftaning qaysi kuni?","ru":"Какой сегодня день недели?","tj":"Имрӯз кадом рӯзи ҳафта аст?"},
                    {"speaker":"Liu Ming","zh":"星期日。今天我休息。","pinyin":"Xīngqīrì. Jīntiān wǒ xiūxi.","en":"It's Sunday. I'm off today.","uz":"Yakshanba. Bugun men dam olaman.","ru":"Воскресенье. Сегодня я отдыхаю.","tj":"Якшанбе. Имрӯз ман истироҳат мекунам."},
                ]
            },
            {
                "block_no":2,"section_label":"课文 2",
                "scene_zh":"在公司里，王一雪和杨同乐休息时聊天儿。",
                "scene_en":"At the company, Wang Yixue and Yang Tongle were chatting during a break.",
                "scene_uz":"Kompaniyada Wang Yixue va Yang Tongle tanaffusda suhbatlashmoqda.",
                "scene_ru":"В компании Ван Исюэ и Ян Тунлэ разговаривают во время перерыва.",
                "scene_tj":"Дар ширкат Ван Исюэ ва Ян Тунлэ ҳангоми танаффус суҳбат мекунанд.",
                "dialogue":[
                    {"speaker":"Wang Yixue","zh":"你会做饭吗？","pinyin":"Nǐ huì zuò fàn ma?","en":"Do you know how to cook?","uz":"Ovqat pishira olasanmi?","ru":"Ты умеешь готовить?","tj":"Ту хӯрок пухта метавонӣ?"},
                    {"speaker":"Yang Tongle","zh":"我会做。","pinyin":"Wǒ huì zuò.","en":"Yes, I do.","uz":"Ha, pishira olaman.","ru":"Да, умею.","tj":"Ҳа, метавонам."},
                    {"speaker":"Wang Yixue","zh":"你会做什么？","pinyin":"Nǐ huì zuò shénme?","en":"What dishes can you make?","uz":"Nima pishira olasan?","ru":"Что ты умеешь готовить?","tj":"Чӣ пухта метавонӣ?"},
                    {"speaker":"Yang Tongle","zh":"我会做面条儿、饺子，也会做一些菜。星期天我也做饭。","pinyin":"Wǒ huì zuò miàntiáor, jiǎozi, yě huì zuò yìxiē cài. Xīngqītiān wǒ yě zuò fàn.","en":"I can make noodles, jiaozi, and some other dishes. I also cook on Sundays.","uz":"Men ugra, jiaozi va ba’zi taomlarni pishira olaman. Yakshanba kuni ham ovqat pishiraman.","ru":"Я умею готовить лапшу, цзяоцзы и некоторые другие блюда. По воскресеньям я тоже готовлю.","tj":"Ман угро, ҷяозы ва баъзе таомҳоро пухта метавонам. Рӯзи якшанбе ҳам хӯрок мепазам."},
                ]
            },
            {
                "block_no":3,"section_label":"课文 3",
                "scene_zh":"在公司里，王一雪和杨同乐下班时聊天儿。",
                "scene_en":"At the company, Wang Yixue and Yang Tongle were chatting as they got off work.",
                "scene_uz":"Kompaniyada Wang Yixue va Yang Tongle ishdan chiqish payti suhbatlashmoqda.",
                "scene_ru":"В компании Ван Исюэ и Ян Тунлэ разговаривают после работы.",
                "scene_tj":"Дар ширкат Ван Исюэ ва Ян Тунлэ баъди кор суҳбат мекунанд.",
                "dialogue":[
                    {"speaker":"Wang Yixue","zh":"同乐，下班吗？","pinyin":"Tónglè, xiàbān ma?","en":"Tongle, are you off work?","uz":"Tongle, ishdan chiqdingmi?","ru":"Тунлэ, ты уже закончил работу?","tj":"Тунлэ, аз кор баромадӣ?"},
                    {"speaker":"Yang Tongle","zh":"下班。","pinyin":"Xiàbān.","en":"Yes, I am.","uz":"Ha, chiqdim.","ru":"Да.","tj":"Ҳа."},
                    {"speaker":"Wang Yixue","zh":"这是你的新电脑吗？","pinyin":"Zhè shì nǐ de xīn diànnǎo ma?","en":"Is this your new computer?","uz":"Bu sening yangi kompyuteringmi?","ru":"Это твой новый компьютер?","tj":"Ин компютери нави туст?"},
                    {"speaker":"Yang Tongle","zh":"是的，是我的新电脑。","pinyin":"Shì de, shì wǒ de xīn diànnǎo.","en":"Yes, it's my new computer.","uz":"Ha, bu mening yangi kompyuterim.","ru":"Да, это мой новый компьютер.","tj":"Ҳа, ин компютери нави ман аст."},
                    {"speaker":"Wang Yixue","zh":"真好看！","pinyin":"Zhēn hǎokàn!","en":"It looks really nice!","uz":"Juda chiroyli ekan!","ru":"Очень красивый!","tj":"Хеле зебо будааст!"},
                    {"speaker":"Yang Tongle","zh":"我也很喜欢它。","pinyin":"Wǒ yě hěn xǐhuan tā.","en":"I really like it too.","uz":"Men ham uni juda yoqtiraman.","ru":"Мне он тоже очень нравится.","tj":"Ман ҳам онро хеле писанд мекунам."},
                ]
            },
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no":1,"title_zh":"时间的表达（1）","title_uz":"Vaqt/sanani ifodalash (1)","title_ru":"Выражение времени и даты (1)","title_tj":"Ифодаи вақт ва сана (1)",
                "rule_zh":"汉语日期常按“年—月—日/号—星期”从大到小表达。",
                "rule_en":"Chinese dates are generally expressed from larger to smaller units: year, month, day/date, then weekday.",
                "rule_uz":"Xitoychada sana odatda kattadan kichikka: yil → oy → kun/sana → hafta kuni tartibida aytiladi.",
                "rule_ru":"Дата по-китайски обычно выражается от крупной единицы к мелкой: год → месяц → число → день недели.",
                "rule_tj":"Сана ба чинӣ одатан аз калон ба хурд гуфта мешавад: сол → моҳ → рӯз/сана → рӯзи ҳафта.",
                "examples":[
                    {"zh":"今天9月8号。","pinyin":"Jīntiān jiǔ yuè bā hào.","uz":"Bugun 8-sentabr.","ru":"Сегодня 8 сентября.","tj":"Имрӯз 8 сентябр аст."},
                    {"zh":"今天星期日。","pinyin":"Jīntiān Xīngqīrì.","uz":"Bugun yakshanba.","ru":"Сегодня воскресенье.","tj":"Имрӯз якшанбе аст."},
                ]
            },
            {
                "no":2,"title_zh":"名词谓语句","title_uz":"Nominal-predikativ gap","title_ru":"Предложение с именным сказуемым","title_tj":"Ҷумла бо хабари номӣ",
                "rule_zh":"名词谓语句中谓语由名词或名词性成分充当，常用于表达时间、日期、年龄等。",
                "rule_en":"In a nominal-predicate sentence, the predicate is a noun or nominal phrase, often used for time, date, age, and similar information.",
                "rule_uz":"Nominal gapda kesim ot yoki ot birikmasidan iborat bo‘lib, ko‘pincha vaqt, sana va yoshni bildiradi.",
                "rule_ru":"В предложении с именным сказуемым сказуемое выражено существительным или именной группой; часто так говорят о времени, дате и возрасте.",
                "rule_tj":"Дар ҷумлаи номӣ хабар аз исм ё гурӯҳи исмӣ иборат буда, бештар вақт, сана ва синну солро ифода мекунад.",
                "examples":[
                    {"zh":"今天星期四。","pinyin":"Jīntiān Xīngqīsì.","uz":"Bugun payshanba.","ru":"Сегодня четверг.","tj":"Имрӯз панҷшанбе аст."},
                    {"zh":"今天5月8号。","pinyin":"Jīntiān wǔ yuè bā hào.","uz":"Bugun 8-may.","ru":"Сегодня 8 мая.","tj":"Имрӯз 8 май аст."},
                ]
            },
            {
                "no":3,"title_zh":"能愿动词“会”","title_uz":"Modal fe’l “会”","title_ru":"Модальный глагол “会”","title_tj":"Феъли модалии “会”",
                "rule_zh":"“会”用在动词前，表示通过学习后获得的做某事的能力。",
                "rule_en":"“会” is placed before a verb and indicates knowledge or ability acquired through learning.",
                "rule_uz":"“会” fe’l oldidan kelib o‘rganish orqali hosil qilingan qobiliyatni bildiradi.",
                "rule_ru":"“会” ставится перед глаголом и выражает умение, приобретённое в результате обучения.",
                "rule_tj":"“会” пеш аз феъл омада, қобилияти тавассути омӯзиш бадастомадаро ифода мекунад.",
                "examples":[
                    {"zh":"你会做饭吗？","pinyin":"Nǐ huì zuò fàn ma?","uz":"Ovqat pishira olasanmi?","ru":"Ты умеешь готовить?","tj":"Ту хӯрок пухта метавонӣ?"},
                    {"zh":"我不会做菜。","pinyin":"Wǒ bú huì zuò cài.","uz":"Men taom pishira olmayman.","ru":"Я не умею готовить блюда.","tj":"Ман таом пухта наметавонам."},
                ]
            }
        ],
        ensure_ascii=False,
    ),
}
