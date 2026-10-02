from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(89, 100)),
    "printed_pages": list(range(73, 84)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level":"nhsk2",
    "lesson_order":9,
    "lesson_code":"NHSK2-L09",
    "title":"我去买杯奶茶",
    "title_pinyin":"Wǒ qù mǎi bēi nǎichá",
    "goal":json.dumps({
        "uz":"“没有” bilan ‘...chalik emas’ taqqoslashini ifodalash; “离” bilan makon/vaqt masofasini aytish; vaqt davomiyligi to‘ldiruvchisini ishlatish; kiyim tanlash, ichimlik va yo‘l haqida gaplashish.",
        "ru":"Сравнивать через “没有” в значении «не такой, как»; выражать пространственную/временную дистанцию с “离”; использовать дополнение длительности; говорить об одежде, напитках и дороге.",
        "tj":"Бо “没有” муқоисаи «ба дараҷаи ... нест»-ро ифода кардан; бо “离” масофаи макон/вақтро гуфтан; пуркунандаи давомнокии вақтро истифода бурдан; дар бораи либос, нӯшокӣ ва роҳ суҳбат кардан."
    },ensure_ascii=False),
    "intro_text":json.dumps({
        "uz":"Dars shim tanlash, qahva/sutli choy, piyoda uyga qaytish va kundalik matni orqali taqqoslashning uchinchi turi, 离 va davomiylik to‘ldiruvchisini o‘rgatadi.",
        "ru":"Урок через выбор брюк, кофе/молочный чай, возвращение домой пешком и запись в дневнике вводит третий тип сравнения, 离 и дополнение длительности.",
        "tj":"Дарс тавассути интихоби шим, қаҳва/чойи ширӣ, пиёда ба хона баргаштан ва матни рӯзнома навъи сеюми муқоиса, 离 ва пуркунандаи давомнокиро меомӯзонад."
    },ensure_ascii=False),
    "vocabulary_json":json.dumps([
        {"no":1,"zh":"坏","pinyin":"huài","pos":"adj.","uz":"yomon; buzilgan","ru":"плохой; испорченный","tj":"бад; вайрон"},
        {"no":2,"zh":"旁边","pinyin":"pángbian","pos":"n.","uz":"yon; yon tomon","ru":"рядом; сбоку","tj":"паҳлӯ; наздик"},
        {"no":3,"zh":"男孩儿","pinyin":"nánháir","pos":"n.","uz":"o‘g‘il bola","ru":"мальчик","tj":"писарбача"},
        {"no":4,"zh":"这样","pinyin":"zhèyàng","pos":"pron.","uz":"bunday; shunday","ru":"такой; так","tj":"чунин; ҳамин тавр"},
        {"no":5,"zh":"个子","pinyin":"gèzi","pos":"n.","uz":"bo‘y","ru":"рост","tj":"қад"},
        {"no":6,"zh":"那么","pinyin":"nàme","pos":"pron.","uz":"unchalik; shunday","ru":"так; настолько","tj":"он қадар"},
        {"no":7,"zh":"高","pinyin":"gāo","pos":"adj.","uz":"baland; bo‘yi uzun","ru":"высокий","tj":"баланд"},
        {"no":8,"zh":"门口","pinyin":"ménkǒu","pos":"n.","uz":"eshik oldi; kirish joyi","ru":"вход; у двери","tj":"даромадгоҳ; назди дар"},
        {"no":9,"zh":"咖啡","pinyin":"kāfēi","pos":"n.","uz":"qahva","ru":"кофе","tj":"қаҳва"},
        {"no":10,"zh":"离","pinyin":"lí","pos":"v.","uz":"...dan masofada bo‘lmoq","ru":"находиться на расстоянии от","tj":"аз ... фосила доштан"},
        {"no":11,"zh":"近","pinyin":"jìn","pos":"adj.","uz":"yaqin","ru":"близкий; рядом","tj":"наздик"},
        {"no":12,"zh":"走路","pinyin":"zǒulù","pos":"v.","uz":"piyoda yurmoq","ru":"ходить пешком","tj":"пиёда рафтан"},
        {"no":13,"zh":"周","pinyin":"zhōu","pos":"n.","uz":"hafta","ru":"неделя","tj":"ҳафта"}
    ],ensure_ascii=False),
    "proper_nouns_json":json.dumps([],ensure_ascii=False),
    "dialogue_json":json.dumps([
        {"block_no":1,"section_label":"课文 1","scene_zh":"在商店，王一雪和刘明在看裤子。","scene_uz":"Do‘konda Wang Yixue va Liu Ming shimlarni ko‘rmoqda.","scene_ru":"В магазине Ван Исюэ и Лю Мин смотрят брюки.","scene_tj":"Дар мағоза Ван Исюэ ва Лю Мин шим мебинанд.","dialogue":[
            {"speaker":"Wang Yixue","zh":"儿子的裤子坏了，我们给他买条新的吧。","pinyin":"Érzi de kùzi huài le, wǒmen gěi tā mǎi tiáo xīn de ba.","uz":"O‘g‘limizning shimi buzilibdi, unga yangisini olaylik.","ru":"Брюки сына испортились, давай купим ему новые.","tj":"Шими писарамон вайрон шудааст, барояш нав бихарем."},
            {"speaker":"Liu Ming","zh":"好啊。","pinyin":"Hǎo a.","uz":"Mayli.","ru":"Хорошо.","tj":"Хуб."},
            {"speaker":"Wang Yixue","zh":"你看这条黑色的怎么样？","pinyin":"Nǐ kàn zhè tiáo hēisè de zěnmeyàng?","uz":"Bu qora shim qanday?","ru":"Как тебе эти чёрные брюки?","tj":"Ин шими сиёҳ чӣ хел?"},
            {"speaker":"Liu Ming","zh":"没有你上次买的那条好看。","pinyin":"Méiyǒu nǐ shàng cì mǎi de nà tiáo hǎokàn.","uz":"O‘tgan safar olganingchalik chiroyli emas.","ru":"Не такие красивые, как те, что ты купила в прошлый раз.","tj":"Ба зебоии оне, ки дафъаи гузашта харидӣ, намерасад."},
            {"speaker":"Wang Yixue","zh":"旁边那个男孩儿就穿了这样的裤子，我觉得很好看啊！","pinyin":"Pángbian nàge nánháir jiù chuānle zhèyàng de kùzi, wǒ juéde hěn hǎokàn a!","uz":"Yonimizdagi bola ham shunday shim kiygan, menimcha juda chiroyli!","ru":"Вон мальчик рядом носит такие брюки, по-моему, выглядят отлично!","tj":"Писарбачаи паҳлӯ ҳамин хел шим пӯшидааст, ба назарам хеле зебост!"},
            {"speaker":"Liu Ming","zh":"儿子的个子没有他那么高，穿上就不会太好看。","pinyin":"Érzi de gèzi méiyǒu tā nàme gāo, chuānshang jiù bú huì tài hǎokàn.","uz":"O‘g‘limizning bo‘yi unchalik baland emas, kiysa bunchalik yarashmaydi.","ru":"Наш сын не такой высокий, как он; на нём они будут смотреться хуже.","tj":"Қади писарамон ба он қадар баланд нест, пӯшад он қадар зебо намешавад."},
            {"speaker":"Wang Yixue","zh":"好吧，我们再去那边看看。","pinyin":"Hǎo ba, wǒmen zài qù nàbian kànkan.","uz":"Mayli, yana u tomonga borib ko‘raylik.","ru":"Ладно, давай посмотрим ещё там.","tj":"Хуб, боз он тараф рафта бинем."}
        ]},
        {"block_no":2,"section_label":"课文 2","scene_zh":"在商店门口，王一雪和刘明往外走。","scene_uz":"Do‘kon kirishida Wang Yixue va Liu Ming tashqariga chiqmoqda.","scene_ru":"У входа в магазин Ван Исюэ и Лю Мин выходят наружу.","scene_tj":"Дар назди даромадгоҳи мағоза Ван Исюэ ва Лю Мин ба берун мебароянд.","dialogue":[
            {"speaker":"Wang Yixue","zh":"门口有家奶茶店。你想喝杯奶茶吗？","pinyin":"Ménkǒu yǒu jiā nǎichádiàn. Nǐ xiǎng hē bēi nǎichá ma?","uz":"Kirishda sutli choy do‘koni bor. Bir piyola sutli choy ichasanmi?","ru":"У входа есть магазин молочного чая. Хочешь чашку?","tj":"Дар назди даромадгоҳ дӯкони чойи ширӣ ҳаст. Як пиёла мехоҳӣ?"},
            {"speaker":"Liu Ming","zh":"我想喝咖啡，还是去咖啡店吧。","pinyin":"Wǒ xiǎng hē kāfēi, háishi qù kāfēidiàn ba.","uz":"Men qahva ichmoqchiman, yaxshisi qahvaxonaga boraylik.","ru":"Я хочу кофе, лучше пойдём в кофейню.","tj":"Ман қаҳва мехоҳам, беҳтараш ба қаҳвахона равем."},
            {"speaker":"Wang Yixue","zh":"咖啡店离这儿有点儿远。","pinyin":"Kāfēidiàn lí zhèr yǒudiǎnr yuǎn.","uz":"Qahvaxona bu yerdan biroz uzoq.","ru":"Кофейня немного далеко отсюда.","tj":"Қаҳвахона аз ин ҷо каме дур аст."},
            {"speaker":"Liu Ming","zh":"没关系，那家店的咖啡很好喝。","pinyin":"Méi guānxi, nà jiā diàn de kāfēi hěn hǎohē.","uz":"Hechqisi yo‘q, u yerdagi qahva juda mazali.","ru":"Ничего, там очень хороший кофе.","tj":"Ҳеҷ гап не, қаҳваи он ҷо хеле болаззат аст."},
            {"speaker":"Wang Yixue","zh":"那你等一下，我去买杯奶茶。","pinyin":"Nà nǐ děng yíxià, wǒ qù mǎi bēi nǎichá.","uz":"Unda biroz kut, men bir piyola sutli choy olib kelaman.","ru":"Тогда подожди, я схожу куплю молочный чай.","tj":"Пас каме интизор шав, ман рафта як пиёла чойи ширӣ мехарам."},
            {"speaker":"Liu Ming","zh":"你不想喝咖啡吗？","pinyin":"Nǐ bù xiǎng hē kāfēi ma?","uz":"Qahva ichging kelmayaptimi?","ru":"Ты не хочешь кофе?","tj":"Қаҳва нӯшидан намехоҳӣ?"},
            {"speaker":"Wang Yixue","zh":"喝了咖啡，晚上就别想睡觉了。","pinyin":"Hēle kāfēi, wǎnshang jiù bié xiǎng shuìjiào le.","uz":"Qahva ichsam, kechasi uyqu yo‘q.","ru":"Если выпью кофе, ночью не усну.","tj":"Агар қаҳва нӯшам, шаб хобам намебарад."}
        ]},
        {"block_no":3,"section_label":"课文 3","scene_zh":"在咖啡店门口，王一雪和刘明在聊天儿。","scene_uz":"Qahvaxona oldida Wang Yixue va Liu Ming suhbatlashmoqda.","scene_ru":"У входа в кофейню Ван Исюэ и Лю Мин разговаривают.","scene_tj":"Дар назди қаҳвахона Ван Исюэ ва Лю Мин суҳбат мекунанд.","dialogue":[
            {"speaker":"Liu Ming","zh":"我们打车回去吧。","pinyin":"Wǒmen dǎchē huíqù ba.","uz":"Uyga taksida qaytaylik.","ru":"Давай поедем обратно на такси.","tj":"Биё бо таксӣ ба хона баргардем."},
            {"speaker":"Wang Yixue","zh":"这里离家很近，还是走路吧。","pinyin":"Zhèlǐ lí jiā hěn jìn, háishi zǒulù ba.","uz":"Bu yer uyga yaqin, yaxshisi piyoda yuraylik.","ru":"Отсюда до дома близко, лучше пойдём пешком.","tj":"Аз ин ҷо то хона наздик аст, беҳтараш пиёда равем."},
            {"speaker":"Liu Ming","zh":"要走多长时间？","pinyin":"Yào zǒu duō cháng shíjiān?","uz":"Qancha vaqt yurish kerak?","ru":"Сколько времени идти?","tj":"Чанд вақт роҳ рафтан лозим?"},
            {"speaker":"Wang Yixue","zh":"走半个多小时就到了。","pinyin":"Zǒu bàn ge duō xiǎoshí jiù dào le.","uz":"Yarim soatdan sal ko‘proq yursak yetamiz.","ru":"Чуть больше получаса пешком — и дойдём.","tj":"Каме бештар аз ним соат роҳ равем, мерасем."},
            {"speaker":"Liu Ming","zh":"好的。每天上下班都坐车，今天运动运动吧。","pinyin":"Hǎo de. Měitiān shàngxiàbān dōu zuò chē, jīntiān yùndong yùndong ba.","uz":"Xo‘p. Har kuni ishga borib-kelishda mashinada yuraman, bugun sal harakat qilay.","ru":"Хорошо. Каждый день езжу на работу и обратно, сегодня немного разомнёмся.","tj":"Хуб. Ҳар рӯз ба кору аз кор бо мошин меравам, имрӯз каме машқ кунем."}
        ]},
        {"block_no":4,"section_label":"课文 4","scene_zh":"在房间，王一雪在写日记。","scene_uz":"Xonada Wang Yixue kundalik yozmoqda.","scene_ru":"В комнате Ван Исюэ пишет дневник.","scene_tj":"Дар ҳуҷра Ван Исюэ рӯзнома менависад.","dialogue":[
            {"speaker":"Narration","zh":"这周刘明休息，我下班后跟他去了一家商店。商店里边的衣服没有大商场里的好看。我们没有买到喜欢的衣服，从商店出来就到咖啡店坐了坐。因为想运动运动，所以喝完东西，我们就走回家了。","pinyin":"Zhè zhōu Liú Míng xiūxi, wǒ xiàbān hòu gēn tā qùle yì jiā shāngdiàn. Shāngdiàn lǐbian de yīfu méiyǒu dà shāngchǎng lǐ de hǎokàn. Wǒmen méiyǒu mǎidào xǐhuan de yīfu, cóng shāngdiàn chūlái jiù dào kāfēidiàn zuòle zuò. Yīnwèi xiǎng yùndong yùndong, suǒyǐ hēwán dōngxi, wǒmen jiù zǒu huí jiā le.","uz":"Bu hafta Liu Ming dam oladi. Ishdan keyin u bilan bir do‘konga bordik. U yerdagi kiyimlar katta savdo markazidagilardek chiroyli emas edi. Yoqtirgan kiyim topolmadik, do‘kondan chiqib qahvaxonada biroz o‘tirdik. Harakat qilgimiz kelgani uchun ichimliklarni tugatgach uyga piyoda qaytdik.","ru":"На этой неделе Лю Мин отдыхает. После работы мы пошли в магазин. Одежда там была не такой красивой, как в большом торговом центре. Ничего подходящего не купили, вышли и немного посидели в кофейне. Хотели размяться, поэтому после напитков пошли домой пешком.","tj":"Ин ҳафта Лю Мин истироҳат мекунад. Баъди кор бо ӯ ба мағоза рафтем. Либосҳои он ҷо ба зебоии либосҳои маркази калони савдо намерасид. Либоси писанд наёфтем, аз мағоза баромада каме дар қаҳвахона нишастем. Азбаски мехостем ҳаракат кунем, баъди нӯшидан пиёда ба хона баргаштем."}
        ]}
    ],ensure_ascii=False),
    "grammar_json":json.dumps([
        {"no":1,"title_zh":"比较句（3）","title_uz":"Taqqoslash gapi (3)","title_ru":"Сравнительное предложение (3)","title_tj":"Ҷумлаи муқоисавӣ (3)","rule_zh":"本课学习用“没有”表示比较的比较句，意思是“不如”“不及”。基本结构：A没有B+形容词或形容词性短语。形容词前面可以加“这么”或者“那么”，表示B的程度更高。“没有”的肯定形式“有”常用在表示比较的疑问句中。","rule_uz":"“没有” taqqoslashda A B darajasiga yetmasligini bildiradi. Shakl: A 没有 B + sifat/sifatli birikma. Sifat oldidan 这么/那么 B ning darajasi yuqoriligini ko‘rsatadi. Tasdiq shakli 有 ko‘pincha taqqoslovchi savolda ishlatiladi.","rule_ru":"“没有” в сравнении означает «не такой, как / уступает». Схема: A 没有 B + прилагательное/группа. 这么/那么 перед прилагательным подчёркивают более высокую степень у B. Утвердительное 有 часто встречается в сравнительных вопросах.","rule_tj":"“没有” дар муқоиса маънои «ба B намерасад»-ро медиҳад. Сохтор: A 没有 B + сифат/ибораи сифатӣ. 这么/那么 дараҷаи баландтари B-ро нишон медиҳад. Шакли тасдиқии 有 аксаран дар саволҳои муқоисавӣ меояд.","examples":[{"zh":"儿子的个子没有他那么高。"},{"zh":"昨天没有今天这么冷。"},{"zh":"这块手表没有那块好看。"},{"zh":"妹妹有姐姐高吗？"},{"zh":"那件衣服有这件好看吗？"}]},
        {"no":2,"title_zh":"动词“离”","title_uz":"“离” fe’li","title_ru":"Глагол “离”","title_tj":"Феъли “离”","rule_zh":"动词“离”表示处所、时间的距离。基本结构：A离B……。","rule_uz":"“离” makon yoki vaqt orasidagi masofani bildiradi. Asosiy shakl: A 离 B ...","rule_ru":"“离” обозначает пространственное или временное расстояние. Схема: A 离 B ...","rule_tj":"“离” фосилаи макон ё вақтро нишон медиҳад. Сохтор: A 离 B ...","examples":[{"zh":"咖啡店离这儿有点儿远。"},{"zh":"学校离医院不远。"},{"zh":"现在离我的生日还有三天。"}]},
        {"no":3,"title_zh":"时量补语（1）","title_uz":"Vaqt davomiyligi to‘ldiruvchisi (1)","title_ru":"Дополнение длительности (1)","title_tj":"Пуркунандаи давомнокӣ (1)","rule_zh":"表示时间段的词语用在动词后面构成时量补语，说明动作或状态持续的时间。基本结构：主语+动词+时量补语。动词带宾语时，事物名词一般在时量补语后；称呼或代词一般在时量补语前。也可以重复动词后再加时量补语。离合词需要重复动词性语素。动词后有“了”且句尾还有语气助词“了”时，表示动作仍在进行。","rule_uz":"Vaqt oralig‘i ifodasi fe’ldan keyin kelib harakat/holat qancha davom etganini ko‘rsatadi: ega+fe’l+davomiylik. Obyekt narsa oti bo‘lsa odatda davomiylikdan keyin, murojaat/olmosh bo‘lsa oldin keladi. Fe’l takrorlanishi mumkin; ajraluvchi fe’lda fe’l morfemasi takrorlanadi. V dan keyin 了 va gap oxirida yana 了 bo‘lsa harakat hali davom etmoqda.","rule_ru":"Выражение периода после глагола показывает длительность действия/состояния: субъект+глагол+длительность. Предметный объект обычно после длительности, обращение/местоимение — перед ней. Глагол можно повторять; у разделяемого глагола повторяется глагольный морф. 了 после глагола и ещё 了 в конце означает продолжающееся действие.","rule_tj":"Ифодаи муддат пас аз феъл давомнокии амал/ҳолатро нишон медиҳад: мубтадо+феъл+муддат. Объекти ашёӣ одатан пас аз муддат, муроҷиат/ҷонишин пеш аз он меояд. Феълро такрор кардан мумкин; дар феъли ҷудошаванда морфемаи феъл такрор мешавад. 了 баъди феъл ва 了 дар охир давом доштани амалро нишон медиҳад.","examples":[{"zh":"走半个多小时就到了。"},{"zh":"他们学了两年。"},{"zh":"我们休息十分钟。"},{"zh":"我看了一个晚上电视。"},{"zh":"李文等了她一个小时。"},{"zh":"我找了陈天中二十多分钟。"},{"zh":"他们学中文学了两年。"},{"zh":"李文等她等了一个小时。"},{"zh":"安妮游泳游了一个下午。"},{"zh":"陈天中跑步跑了两个小时。"},{"zh":"他写了半个小时汉字了。"},{"zh":"陈天中跑步跑了两个小时了。"}]}
    ],ensure_ascii=False)
}
