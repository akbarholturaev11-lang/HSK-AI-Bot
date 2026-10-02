from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(62, 72)),
    "printed_pages": list(range(46, 56)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level":"nhsk2","lesson_order":6,"lesson_code":"NHSK2-L06",
    "title":"小雪，生日快乐！","title_pinyin":"Xiǎoxuě, shēngrì kuàilè!",
    "goal":json.dumps({"uz":"Sifat takrorlanishi bilan darajani kuchaytirish; “什么的” bilan ‘va hokazo’ ma’nosini berish; “地” bilan harakatning holat/usulini ko‘rsatish; tug‘ilgan kun haqida gaplashish.","ru":"Усиливать признак редупликацией прилагательных; выражать «и так далее» с “什么的”; описывать способ действия с “地”; говорить о дне рождения.","tj":"Бо такрори сифат дараҷаро қавитар кардан; бо “什么的” маънои «ва ғайра»-ро додан; бо “地” тарзи амалро нишон додан; дар бораи зодрӯз суҳбат кардан."},ensure_ascii=False),
    "intro_text":json.dumps({"uz":"Dars tug‘ilgan kun sovg‘asi, oilaviy bayram, taomlar va kundalik yozuvi orqali sifat takrorlanishi, 什么的 va 地 ni o‘rgatadi.","ru":"Урок через подарки на день рождения, семейный праздник, блюда и запись в дневнике вводит редупликацию прилагательных, 什么的 и 地.","tj":"Дарс тавассути тӯҳфаи зодрӯз, ҷашни оилавӣ, хӯрокҳо ва навиштаи рӯзнома такрори сифат, 什么的 ва 地-ро меомӯзонад."},ensure_ascii=False),
    "vocabulary_json":json.dumps([
        {"no":1,"zh":"生日","pinyin":"shēngrì","pos":"n.","uz":"tug‘ilgan kun","ru":"день рождения","tj":"зодрӯз"},
        {"no":2,"zh":"忘","pinyin":"wàng","pos":"v.","uz":"unutmoq","ru":"забывать","tj":"фаромӯш кардан"},
        {"no":3,"zh":"画","pinyin":"huà","pos":"v./n.","uz":"chizmoq; rasm","ru":"рисовать; рисунок","tj":"расм кашидан; расм"},
        {"no":4,"zh":"画笔","pinyin":"huàbǐ","pos":"n.","uz":"rangli qalam/mo‘yqalam","ru":"карандаш/кисть для рисования","tj":"қалам/мӯқалам барои расм"},
        {"no":5,"zh":"蛋糕","pinyin":"dàngāo","pos":"n.","uz":"tort","ru":"торт","tj":"торт"},
        {"no":6,"zh":"快乐","pinyin":"kuàilè","pos":"adj.","uz":"xursand; baxtli","ru":"счастливый; радостный","tj":"хурсанд; хушҳол"},
        {"no":7,"zh":"打开","pinyin":"dǎkāi","pos":"v.","uz":"ochmoq","ru":"открывать","tj":"кушодан"},
        {"no":8,"zh":"长","pinyin":"cháng","pos":"adj.","uz":"uzun","ru":"длинный","tj":"дароз"},
        {"no":9,"zh":"鱼","pinyin":"yú","pos":"n.","uz":"baliq","ru":"рыба","tj":"моҳӣ"},
        {"no":10,"zh":"肉","pinyin":"ròu","pos":"n.","uz":"go‘sht","ru":"мясо","tj":"гӯшт"},
        {"no":11,"zh":"过","pinyin":"guò","pos":"v.","uz":"o‘tkazmoq (vaqt/bayram)","ru":"проводить (время/праздник)","tj":"гузарондан (вақт/ид)"},
        {"no":12,"zh":"地","pinyin":"de","pos":"part.","uz":"ravish yasovchi yuklama","ru":"частица наречного определения","tj":"ҳиссачаи ҳол/зарф"},
        {"no":13,"zh":"床","pinyin":"chuáng","pos":"n.","uz":"karavot","ru":"кровать","tj":"кат"},
        {"no":14,"zh":"舒服","pinyin":"shūfu","pos":"adj.","uz":"qulay; rohat","ru":"удобный; комфортный","tj":"роҳат; бароҳат"},
    ],ensure_ascii=False),
    "proper_nouns_json":json.dumps([],ensure_ascii=False),
    "dialogue_json":json.dumps([
        {"block_no":1,"section_label":"课文 1","scene_zh":"在家里，刘明和王一雪在聊天儿。","scene_uz":"Uyda Liu Ming va Wang Yixue suhbatlashmoqda.","scene_ru":"Дома Лю Мин и Ван Исюэ разговаривают.","scene_tj":"Дар хона Лю Мин ва Ван Исюэ суҳбат мекунанд.","dialogue":[
            {"speaker":"Wang Yixue","zh":"明天就是女儿的生日了。","pinyin":"Míngtiān jiù shì nǚ'ér de shēngrì le.","uz":"Ertaga qizimizning tug‘ilgan kuni.","ru":"Завтра уже день рождения нашей дочери.","tj":"Фардо зодрӯзи духтарамон аст."},
            {"speaker":"Liu Ming","zh":"你不说，我还真忘了。我们给她准备个什么礼物呢？","pinyin":"Nǐ bù shuō, wǒ hái zhēn wàng le. Wǒmen gěi tā zhǔnbèi ge shénme lǐwù ne?","uz":"Aytinganing yaxshi bo‘ldi, rostdan unutibman. Unga qanday sovg‘a tayyorlaymiz?","ru":"Если бы ты не сказала, я бы и правда забыл. Что подарим ей?","tj":"Агар намегуфтӣ, ростӣ фаромӯш мекардам. Ба ӯ чӣ тӯҳфа тайёр кунем?"},
            {"speaker":"Wang Yixue","zh":"她喜欢画画，你觉得画笔怎么样？","pinyin":"Tā xǐhuan huàhuà, nǐ juéde huàbǐ zěnmeyàng?","uz":"U rasm chizishni yoqtiradi, rangli qalamlar qanday?","ru":"Она любит рисовать. Как насчёт карандашей/кистей?","tj":"Ӯ расм кашиданро дӯст медорад, қаламҳои расмкашӣ чӣ хел?"},
            {"speaker":"Liu Ming","zh":"就送画笔吧！","pinyin":"Jiù sòng huàbǐ ba!","uz":"Unda qalamlar sovg‘a qilamiz!","ru":"Тогда подарим ей набор для рисования!","tj":"Пас қаламҳои расмкаширо тӯҳфа кунем!"},
            {"speaker":"Wang Yixue","zh":"那我明天上午就去买。","pinyin":"Nà wǒ míngtiān shàngwǔ jiù qù mǎi.","uz":"Unda ertaga ertalab borib olaman.","ru":"Тогда завтра утром я пойду куплю.","tj":"Пас фардо саҳар рафта мехарам."},
            {"speaker":"Liu Ming","zh":"好的！我再给她买个大大的生日蛋糕。","pinyin":"Hǎo de! Wǒ zài gěi tā mǎi ge dàdà de shēngrì dàngāo.","uz":"Xo‘p! Men unga yana katta-katta tug‘ilgan kun torti olaman.","ru":"Хорошо! А я куплю ей ещё большой-большой торт.","tj":"Хуб! Ман боз барояш торти калони зодрӯз мехарам."},
        ]},
        {"block_no":2,"section_label":"课文 2","scene_zh":"在客厅，刘明一家人在聊天儿。","scene_uz":"Mehmonxonada Liu Ming oilasi suhbatlashmoqda.","scene_ru":"В гостиной семья Лю Мина разговаривает.","scene_tj":"Дар меҳмонхона оилаи Лю Мин суҳбат мекунанд.","dialogue":[
            {"speaker":"Liu Ming","zh":"小雪，生日快乐！","pinyin":"Xiǎoxuě, shēngrì kuàilè!","uz":"Xiaoxue, tug‘ilgan kuning bilan!","ru":"Сяосюэ, с днём рождения!","tj":"Сяосюэ, зодрӯз муборак!"},
            {"speaker":"Liu Xiaoming","zh":"姐姐，生日快乐！","pinyin":"Jiějie, shēngrì kuàilè!","uz":"Opa, tug‘ilgan kuning bilan!","ru":"Сестрёнка, с днём рождения!","tj":"Апа, зодрӯз муборак!"},
            {"speaker":"Wang Yixue","zh":"小雪，这是爸爸、妈妈送你的礼物。","pinyin":"Xiǎoxuě, zhè shì bàba, māma sòng nǐ de lǐwù.","uz":"Xiaoxue, bu dada va onangning senga sovg‘asi.","ru":"Сяосюэ, это подарок от папы и мамы.","tj":"Сяосюэ, ин тӯҳфаи падар ва модар барои туст."},
            {"speaker":"Liu Ming","zh":"你打开看看喜欢不喜欢。","pinyin":"Nǐ dǎkāi kànkan xǐhuan bu xǐhuan.","uz":"Ochib ko‘r, yoqadimi-yo‘qmi.","ru":"Открой и посмотри, понравится ли.","tj":"Кушода бин, писанд меояд ё не."},
            {"speaker":"Liu Xiaoxue","zh":"画笔！我很喜欢！","pinyin":"Huàbǐ! Wǒ hěn xǐhuan!","uz":"Rasm chizish qalamlari! Juda yoqdi!","ru":"Принадлежности для рисования! Очень нравится!","tj":"Қаламҳои расмкашӣ! Хеле писанд омад!"},
            {"speaker":"Wang Yixue","zh":"那你想画点儿什么？","pinyin":"Nà nǐ xiǎng huà diǎnr shénme?","uz":"Unda nima chizmoqchisan?","ru":"Что ты хочешь нарисовать?","tj":"Пас чӣ расм кашидан мехоҳӣ?"},
            {"speaker":"Liu Xiaoxue","zh":"画我们的家！有爸爸、妈妈、弟弟，还有黑色的狗、白色的猫什么的。","pinyin":"Huà wǒmen de jiā! Yǒu bàba, māma, dìdi, hái yǒu hēisè de gǒu, báisè de māo shénmede.","uz":"Oilamizni! Dada, oyi, ukam, yana qora it, oq mushuk va hokazolarni.","ru":"Наш дом! Папу, маму, младшего брата, ещё чёрную собаку, белую кошку и всё такое.","tj":"Оилаамонро! Падар, модар, додар, боз саги сиёҳ, гурбаи сафед ва ғайра."},
            {"speaker":"Liu Xiaoming","zh":"那我要画一个穿白色衣服的姐姐。","pinyin":"Nà wǒ yào huà yí ge chuān báisè yīfu de jiějie.","uz":"Unda men oq kiyim kiygan opamni chizaman.","ru":"Тогда я нарисую сестру в белой одежде.","tj":"Пас ман апаи либоси сафедпӯшро мекашам."},
        ]},
        {"block_no":3,"section_label":"课文 3","scene_zh":"在客厅，刘明一家人在给刘小雪过生日。","scene_uz":"Mehmonxonada Liu Ming oilasi Liu Xiaoxuening tug‘ilgan kunini nishonlamoqda.","scene_ru":"В гостиной семья Лю Мина празднует день рождения Лю Сяосюэ.","scene_tj":"Дар меҳмонхона оилаи Лю Мин зодрӯзи Лю Сяосюэро ҷашн мегиранд.","dialogue":[
            {"speaker":"Liu Ming","zh":"小雪，看看今天有什么好吃的。","pinyin":"Xiǎoxuě, kànkan jīntiān yǒu shénme hǎochī de.","uz":"Xiaoxue, bugun qanday mazali narsalar borligini qara.","ru":"Сяосюэ, посмотри, сколько сегодня вкусного.","tj":"Сяосюэ, бин имрӯз чӣ хӯрокҳои болаззат ҳаст."},
            {"speaker":"Liu Xiaoxue","zh":"长长的面条儿，大大的蛋糕。","pinyin":"Chángcháng de miàntiáor, dàdà de dàngāo.","uz":"Uzun-uzun lag‘mon va katta-katta tort.","ru":"Длинная-длинная лапша и большой-большой торт.","tj":"Угрои дароз-дароз ва торти калон-калон."},
            {"speaker":"Liu Ming","zh":"你看，还有鱼啊肉啊什么的，都是你喜欢吃的。","pinyin":"Nǐ kàn, hái yǒu yú a ròu a shénmede, dōu shì nǐ xǐhuan chī de.","uz":"Qara, yana baliq, go‘sht va hokazolar bor — hammasi sen yoqtiradiganlar.","ru":"Смотри, ещё рыба, мясо и всё такое — всё то, что ты любишь.","tj":"Бин, боз моҳӣ, гӯшт ва ғайра ҳаст — ҳамааш чизҳои дӯстдоштаи туст."},
            {"speaker":"Liu Xiaoxue","zh":"谢谢爸爸、妈妈！","pinyin":"Xièxie bàba, māma!","uz":"Rahmat, dada, oyi!","ru":"Спасибо, папа и мама!","tj":"Раҳмат, падар ва модар!"},
            {"speaker":"Wang Yixue","zh":"快去叫弟弟过来吃饭吧，吃完饭我们还要出去玩呢。","pinyin":"Kuài qù jiào dìdi guòlai chī fàn ba, chīwán fàn wǒmen hái yào chūqù wán ne.","uz":"Tez ukangni ovqatga chaqir, ovqatdan keyin yana tashqariga o‘ynagani chiqamiz.","ru":"Иди позови брата есть, после ужина мы ещё пойдём гулять.","tj":"Зуд додарро ба хӯрок даъват кун, баъди хӯрок боз ба берун бозӣ меравем."},
            {"speaker":"Liu Xiaoxue","zh":"过生日真好啊！","pinyin":"Guò shēngrì zhēn hǎo a!","uz":"Tug‘ilgan kun o‘tkazish juda zo‘r!","ru":"Как здорово праздновать день рождения!","tj":"Зодрӯз гузарондан чӣ қадар хуб!"},
            {"speaker":"Wang Yixue","zh":"是的，过生日就要吃好吃的，还要高高兴兴地玩。","pinyin":"Shì de, guò shēngrì jiù yào chī hǎochī de, hái yào gāogāoxìngxìng de wán.","uz":"Ha, tug‘ilgan kunda mazali narsalar yeyish va xursand bo‘lib o‘ynash kerak.","ru":"Да, в день рождения надо вкусно поесть и весело поиграть.","tj":"Ҳа, дар зодрӯз бояд хӯроки болаззат хӯрд ва хушҳолона бозӣ кард."},
        ]},
        {"block_no":4,"section_label":"课文 4","scene_zh":"在房间，王一雪在写日记。","scene_uz":"Xonada Wang Yixue kundalik yozmoqda.","scene_ru":"В комнате Ван Исюэ пишет дневник.","scene_tj":"Дар ҳуҷра Ван Исюэ рӯзнома менависад.","dialogue":[
            {"speaker":"Narration","zh":"今天是女儿的生日。我们买了蛋糕，做了面条儿，还做了鱼啊肉啊什么的。吃完晚饭，一家人去看了个电影。回家后，孩子们早早地就上床了。明天不上学，他们说要舒舒服服地睡一觉，让我们晚点儿叫他们起床。这是很忙、很累，但很快乐的一天。","pinyin":"Jīntiān shì nǚ'ér de shēngrì. Wǒmen mǎile dàngāo, zuòle miàntiáor, hái zuòle yú a ròu a shénmede. Chīwán wǎnfàn, yì jiā rén qù kànle ge diànyǐng. Huí jiā hòu, háizimen zǎozǎo de jiù shàng chuáng le. Míngtiān bù shàngxué, tāmen shuō yào shūshufúfu de shuì yí jiào, ràng wǒmen wǎn diǎnr jiào tāmen qǐchuáng. Zhè shì hěn máng, hěn lèi, dàn hěn kuàilè de yì tiān.","uz":"Bugun qizimizning tug‘ilgan kuni edi. Tort oldik, lag‘mon qildik, yana baliq, go‘sht va boshqa narsalar tayyorladik. Kechki ovqatdan so‘ng butun oila film ko‘rgani bordi. Uyga qaytgach, bolalar erta yotishdi. Ertaga maktab yo‘q, ular bemalol uxlab olishni va bizdan kechroq uyg‘otishni so‘rashdi. Juda band va charchatadigan, lekin juda quvonchli kun bo‘ldi.","ru":"Сегодня был день рождения дочери. Мы купили торт, приготовили лапшу, рыбу, мясо и другое. После ужина всей семьёй пошли в кино. Вернувшись домой, дети рано легли спать. Завтра школы нет, они сказали, что хотят хорошенько выспаться и попросили разбудить их попозже. День был очень занятым и утомительным, но радостным.","tj":"Имрӯз зодрӯзи духтарамон буд. Торт харидем, угро пухтем, боз моҳӣ, гӯшт ва чизҳои дигар тайёр кардем. Баъди шом тамоми оила ба кино рафт. Пас аз бозгашт кӯдакон барвақт хобиданд. Фардо мактаб нест, гуфтанд мехоҳанд бароҳат хоб кунанд ва хоҳиш карданд дертар бедорашон кунем. Рӯзи серкору хастакунанда, вале хеле хушҳол буд."},
        ]},
    ],ensure_ascii=False),
    "grammar_json":json.dumps([
        {"no":1,"title_zh":"形容词重叠","title_uz":"Sifat takrorlanishi","title_ru":"Редупликация прилагательных","title_tj":"Такрори сифат","rule_zh":"单音节形容词“A”的重叠形式为“AA”，双音节形容词“AB”的重叠形式一般为“AABB”。形容词重叠表示程度深或者表达喜爱的情感。","rule_uz":"Bir bo‘g‘inli A sifat AA, ikki bo‘g‘inli AB sifat odatda AABB shaklida takrorlanadi. Takrorlanish darajani kuchaytiradi yoki yoqimlilik hissini bildiradi.","rule_ru":"Односложное A редуплицируется как AA, двусложное AB обычно как AABB. Редупликация усиливает степень признака или выражает симпатию.","rule_tj":"Сифати якҳиҷоии A ба шакли AA, дуҳиҷоии AB одатан ба AABB такрор мешавад. Такрор дараҷаро қавӣ ё ҳисси писандро ифода мекунад.","examples":[{"zh":"我再给她买个大大的生日蛋糕。"},{"zh":"这只猫小小的，真让人喜欢。"},{"zh":"一雪的女儿每天都漂漂亮亮的。"}]},
        {"no":2,"title_zh":"固定短语“什么的”","title_uz":"“什么的” qolipi","title_ru":"Устойчивая фраза “什么的”","title_tj":"Ибораи собити “什么的”","rule_zh":"固定短语“什么的”表示“……之类”的意思。基本结构：……什么的。","rule_uz":"“什么的” ‘... va shunga o‘xshashlar / va hokazo’ ma’nosini beradi. Asosiy shakl: ...什么的.","rule_ru":"“什么的” означает «… и тому подобное / и так далее». Базовая схема: …什么的.","rule_tj":"“什么的” маънои «… ва монанди ин / ва ғайра»-ро медиҳад. Сохтор: …什么的.","examples":[{"zh":"画我们的家！有爸爸、妈妈、弟弟，还有黑色的狗、白色的猫什么的。"},{"zh":"桌子上有电脑、杯子、书和画笔什么的。"},{"zh":"她拿来了一些水、面包和苹果什么的。"}]},
        {"no":3,"title_zh":"结构助词“地”","title_uz":"Struktur yuklama “地”","title_ru":"Структурная частица “地”","title_tj":"Ҳиссачаи сохтории “地”","rule_zh":"结构助词“地”一般用在形容词和动词中间，表示动作行为的状态或方式。","rule_uz":"“地” odatda sifat bilan fe’l orasida kelib, harakatning holati yoki usulini bildiradi.","rule_ru":"“地” обычно ставится между прилагательным и глаголом и обозначает способ или состояние выполнения действия.","rule_tj":"“地” одатан байни сифат ва феъл омада, ҳолат ё тарзи иҷрои амалро нишон медиҳад.","examples":[{"zh":"过生日就要吃好吃的，还要高高兴兴地玩。"},{"zh":"老师早早地到了教室。"},{"zh":"爸爸很快地吃完早饭，就去上班了。"}]},
    ],ensure_ascii=False),
}
