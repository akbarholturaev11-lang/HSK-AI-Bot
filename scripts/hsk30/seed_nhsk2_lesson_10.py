from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(100, 109)),
    "printed_pages": list(range(84, 93)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk2",
    "lesson_order": 10,
    "lesson_code": "NHSK2-L10",
    "title": "就要考试了",
    "title_pinyin": "Jiù yào kǎoshì le",
    "goal": json.dumps({
        "uz": "Ega-kesim birikmasini kesim sifatida ishlatish; “还是” bilan tanlov savolini tuzish; “要/快/快要/就要……了” orqali yaqin kelajakdagi hodisani ifodalash; maktab va imtihon tayyorgarligi haqida gaplashish.",
        "ru": "Использовать субъектно-предикативную группу как сказуемое; задавать альтернативные вопросы с “还是”; выражать скорое наступление события с “要/快/快要/就要……了”; говорить о подготовке к школе и экзамену.",
        "tj": "Ибораи мубтадо-хабарро ҳамчун хабар истифода бурдан; бо “还是” саволи интихобӣ сохтан; бо “要/快/快要/就要……了” рӯйдоди наздикро ифода кардан; дар бораи омодагӣ ба мактаб ва имтиҳон суҳбат кардан.",
    }, ensure_ascii=False),
    "intro_text": json.dumps({
        "uz": "Dars maktab boshlanishi, imtihon tayyorgarligi, imtihondan keyingi suhbat va kundalik matni orqali uchta asosiy gap tuzilishini o‘rgatadi.",
        "ru": "Урок через подготовку к началу школы, экзамену, разговор после экзамена и дневниковый текст вводит три ключевые грамматические конструкции.",
        "tj": "Дарс тавассути омодагӣ ба оғози мактаб, имтиҳон, гуфтугӯи баъди имтиҳон ва матни рӯзнома се сохтори асосиро меомӯзонад.",
    }, ensure_ascii=False),
    "vocabulary_json": json.dumps([
        {"no":1,"zh":"开学","pinyin":"kāixué","pos":"v.","uz":"o‘qish/maktab boshlanmoq","ru":"начинаться (об учебном семестре)","tj":"оғоз шудани таҳсил"},
        {"no":2,"zh":"门","pinyin":"mén","pos":"n.","uz":"eshik","ru":"дверь","tj":"дар"},
        {"no":3,"zh":"后面","pinyin":"hòumian","pos":"n.","uz":"orqa tomon","ru":"сзади; задняя сторона","tj":"қафо; тарафи қафо"},
        {"no":4,"zh":"笔","pinyin":"bǐ","pos":"n.","uz":"ruchka; qalam","ru":"ручка; карандаш","tj":"ручка; қалам"},
        {"no":5,"zh":"帮","pinyin":"bāng","pos":"v.","uz":"yordam bermoq","ru":"помогать","tj":"кӯмак кардан"},
        {"no":6,"zh":"考试","pinyin":"kǎoshì","pos":"v./n.","uz":"imtihon topshirmoq; imtihon","ru":"сдавать экзамен; экзамен","tj":"имтиҳон супоридан; имтиҳон"},
        {"no":7,"zh":"词","pinyin":"cí","pos":"n.","uz":"so‘z","ru":"слово","tj":"калима"},
        {"no":8,"zh":"本子","pinyin":"běnzi","pos":"n.","uz":"daftar","ru":"тетрадь","tj":"дафтар"},
        {"no":9,"zh":"错","pinyin":"cuò","pos":"adj.","uz":"xato; noto‘g‘ri","ru":"ошибочный; неправильный","tj":"хато; нодуруст"},
        {"no":10,"zh":"题","pinyin":"tí","pos":"n.","uz":"savol; masala","ru":"вопрос; задача","tj":"савол; масъала"},
        {"no":11,"zh":"还是","pinyin":"háishi","pos":"conj.","uz":"yoki (tanlov savolida)","ru":"или (в альтернативном вопросе)","tj":"ё (дар саволи интихобӣ)"},
        {"no":12,"zh":"考","pinyin":"kǎo","pos":"v.","uz":"imtihon topshirmoq; tekshirmoq","ru":"сдавать экзамен; экзаменовать","tj":"имтиҳон супоридан; санҷидан"},
        {"no":13,"zh":"快要","pinyin":"kuàiyào","pos":"adv.","uz":"sal qoldi; tez orada","ru":"вот-вот; скоро","tj":"қариб; ба зудӣ"},
        {"no":14,"zh":"笑","pinyin":"xiào","pos":"v.","uz":"kulmoq; jilmaymoq","ru":"смеяться; улыбаться","tj":"хандидан; табассум кардан"},
    ], ensure_ascii=False),
    "proper_nouns_json": json.dumps([], ensure_ascii=False),
    "dialogue_json": json.dumps([
        {
            "block_no":1,
            "section_label":"课文 1",
            "scene_zh":"在房间，刘明在帮刘小明准备东西。",
            "scene_uz":"Xonada Liu Ming Liu Xiaominga narsalarni tayyorlashga yordam bermoqda.",
            "scene_ru":"В комнате Лю Мин помогает Лю Сяомину готовить вещи.",
            "scene_tj":"Дар ҳуҷра Лю Мин ба Лю Сяомин барои тайёр кардани чизҳо кӯмак мекунад.",
            "dialogue":[
                {"speaker":"Liu Ming","zh":"小明，你们明天开学，你准备好了吗？","pinyin":"Xiǎomíng, nǐmen míngtiān kāixué, nǐ zhǔnbèi hǎo le ma?","uz":"Xiaoming, ertaga o‘qish boshlanadi, tayyormisan?","ru":"Сяомин, завтра начинается учёба, ты готов?","tj":"Сяомин, фардо таҳсил оғоз мешавад, тайёрӣ?"},
                {"speaker":"Liu Xiaoming","zh":"明天就开学啊？爸爸，我的书包你看见了吗？","pinyin":"Míngtiān jiù kāixué a? Bàba, wǒ de shūbāo nǐ kànjiàn le ma?","uz":"Ertagayoq o‘qish boshlanadimi? Dada, mening sumkamni ko‘rdingizmi?","ru":"Учёба уже завтра начинается? Папа, ты видел мой рюкзак?","tj":"Фардо аллакай таҳсил сар мешавад? Дада, ҷузвдони маро дидед?"},
                {"speaker":"Liu Ming","zh":"书包在门后面。","pinyin":"Shūbāo zài mén hòumian.","uz":"Sumka eshik orqasida.","ru":"Рюкзак за дверью.","tj":"Ҷузвдон пушти дар аст."},
                {"speaker":"Liu Xiaoming","zh":"书在哪儿呢？笔呢？","pinyin":"Shū zài nǎr ne? Bǐ ne?","uz":"Kitob qayerda? Qalam-chi?","ru":"А книги где? А ручка?","tj":"Китоб куҷост? Қалам чӣ?"},
                {"speaker":"Liu Ming","zh":"书在床上，笔在桌子上。","pinyin":"Shū zài chuáng shàng, bǐ zài zhuōzi shàng.","uz":"Kitob karavot ustida, qalam stol ustida.","ru":"Книги на кровати, ручка на столе.","tj":"Китоб рӯйи кат, қалам рӯйи миз аст."},
                {"speaker":"Liu Xiaoming","zh":"太好了！现在都准备好了。","pinyin":"Tài hǎo le! Xiànzài dōu zhǔnbèi hǎo le.","uz":"Zo‘r! Endi hammasi tayyor.","ru":"Отлично! Теперь всё готово.","tj":"Олиҷаноб! Ҳоло ҳама чиз тайёр аст."},
                {"speaker":"Liu Ming","zh":"这次爸爸帮你，下次你自己准备，好不好？","pinyin":"Zhè cì bàba bāng nǐ, xià cì nǐ zìjǐ zhǔnbèi, hǎo bu hǎo?","uz":"Bu safar dada yordam berdi, keyingi safar o‘zing tayyorlaysan, xo‘pmi?","ru":"В этот раз папа помог, в следующий подготовишься сам, хорошо?","tj":"Ин дафъа падарат кӯмак кард, дафъаи дигар худат тайёр мекунӣ, хуб?"},
                {"speaker":"Liu Xiaoming","zh":"好！","pinyin":"Hǎo!","uz":"Xo‘p!","ru":"Хорошо!","tj":"Хуб!"}
            ]
        },
        {
            "block_no":2,
            "section_label":"课文 2",
            "scene_zh":"在房间，王一雪和刘小雪在聊学习。",
            "scene_uz":"Xonada Wang Yixue va Liu Xiaoxue o‘qish haqida suhbatlashmoqda.",
            "scene_ru":"В комнате Ван Исюэ и Лю Сяосюэ говорят об учёбе.",
            "scene_tj":"Дар ҳуҷра Ван Исюэ ва Лю Сяосюэ дар бораи таҳсил суҳбат мекунанд.",
            "dialogue":[
                {"speaker":"Wang Yixue","zh":"小雪，你在做什么呢？","pinyin":"Xiǎoxuě, nǐ zài zuò shénme ne?","uz":"Xiaoxue, nima qilyapsan?","ru":"Сяосюэ, что ты делаешь?","tj":"Сяосюэ, чӣ кор карда истодаӣ?"},
                {"speaker":"Liu Xiaoxue","zh":"明天考试，我在看书呢。","pinyin":"Míngtiān kǎoshì, wǒ zài kàn shū ne.","uz":"Ertaga imtihon, kitob o‘qiyapman.","ru":"Завтра экзамен, я читаю.","tj":"Фардо имтиҳон, китоб мехонам."},
                {"speaker":"Wang Yixue","zh":"这些词要好好看看。","pinyin":"Zhèxiē cí yào hǎohāo kànkan.","uz":"Bu so‘zlarni yaxshilab ko‘rib chiqish kerak.","ru":"Эти слова нужно как следует повторить.","tj":"Ин калимаҳоро хуб дида баромадан лозим."},
                {"speaker":"Liu Xiaoxue","zh":"我看过了，意思也都懂了。","pinyin":"Wǒ kànguo le, yìsi yě dōu dǒng le.","uz":"Ko‘rib chiqdim, ma’nolarini ham tushundim.","ru":"Я уже посмотрела и значения тоже поняла.","tj":"Ман дида баромадам, маъноҳояшро ҳам фаҳмидам."},
                {"speaker":"Wang Yixue","zh":"你的本子呢？本子上做错的题也要看一看。","pinyin":"Nǐ de běnzi ne? Běnzi shàng zuòcuò de tí yě yào kàn yí kàn.","uz":"Daftaring-chi? Daftardagi xato qilgan savollaringni ham ko‘rib chiq.","ru":"А тетрадь? Нужно ещё посмотреть задания, где ты ошиблась.","tj":"Дафтарат чӣ? Саволҳои хато кардаатро ҳам дида баро."},
                {"speaker":"Liu Xiaoxue","zh":"妈妈，是您准备考试还是我准备考试？","pinyin":"Māma, shì nín zhǔnbèi kǎoshì háishi wǒ zhǔnbèi kǎoshì?","uz":"Oyi, imtihonga siz tayyorlanyapsizmi yoki menmi?","ru":"Мама, к экзамену готовитесь вы или я?","tj":"Оча, ба имтиҳон шумо тайёр мешавед ё ман?"}
            ]
        },
        {
            "block_no":3,
            "section_label":"课文 3",
            "scene_zh":"在客厅，王一雪和孩子们在聊天儿。",
            "scene_uz":"Mehmonxonada Wang Yixue bolalar bilan suhbatlashmoqda.",
            "scene_ru":"В гостиной Ван Исюэ разговаривает с детьми.",
            "scene_tj":"Дар меҳмонхона Ван Исюэ бо кӯдакон суҳбат мекунад.",
            "dialogue":[
                {"speaker":"Liu Xiaoxue","zh":"妈妈，我回来了！","pinyin":"Māma, wǒ huílái le!","uz":"Oyi, men qaytdim!","ru":"Мама, я вернулась!","tj":"Оча, ман баргаштам!"},
                {"speaker":"Wang Yixue","zh":"我买了奶茶，就在桌子上，自己去拿吧。","pinyin":"Wǒ mǎile nǎichá, jiù zài zhuōzi shàng, zìjǐ qù ná ba.","uz":"Sutli choy oldim, stol ustida, o‘zing borib ol.","ru":"Я купила молочный чай, он на столе, возьми сама.","tj":"Чойи ширӣ харидам, рӯйи миз аст, худат гирифта гир."},
                {"speaker":"Liu Xiaoxue","zh":"谢谢妈妈！","pinyin":"Xièxie māma!","uz":"Rahmat, oyi!","ru":"Спасибо, мама!","tj":"Раҳмат, оча!"},
                {"speaker":"Wang Yixue","zh":"今天考试考得怎么样？","pinyin":"Jīntiān kǎoshì kǎo de zěnmeyàng?","uz":"Bugungi imtihonni qanday topshirding?","ru":"Как сегодня сдала экзамен?","tj":"Имтиҳони имрӯзаро чӣ хел супоридӣ?"},
                {"speaker":"Liu Xiaoxue","zh":"我觉得比上次好。","pinyin":"Wǒ juéde bǐ shàng cì hǎo.","uz":"Menimcha, o‘tgan safardagidan yaxshi.","ru":"Мне кажется, лучше, чем в прошлый раз.","tj":"Ба назарам, аз дафъаи гузашта беҳтар."},
                {"speaker":"Wang Yixue","zh":"真不错！饭菜快要做好了，你叫弟弟一起去洗手吧。","pinyin":"Zhēn búcuò! Fàncài kuàiyào zuòhǎo le, nǐ jiào dìdi yìqǐ qù xǐshǒu ba.","uz":"Juda yaxshi! Ovqat deyarli tayyor, ukangni chaqirib birga qo‘l yuvishga boringlar.","ru":"Очень хорошо! Еда почти готова, позови брата и идите вместе мыть руки.","tj":"Хеле хуб! Хӯрок қариб тайёр шуд, додарро даъват кун ва якҷо даст шӯед."},
                {"speaker":"Liu Xiaoming","zh":"妈妈，我是第一名，姐姐还没洗完呢。","pinyin":"Māma, wǒ shì dì-yī míng, jiějie hái méi xǐwán ne.","uz":"Oyi, men birinchi bo‘ldim, opam hali yuvib bo‘lmadi.","ru":"Мама, я первый закончил, сестра ещё не домыла руки.","tj":"Оча, ман якум шудам, апа ҳоло дасташро шуста тамом накардааст."},
                {"speaker":"Wang Yixue","zh":"你洗得真快啊！","pinyin":"Nǐ xǐ de zhēn kuài a!","uz":"Juda tez yuvibsan!","ru":"Как быстро ты помыл руки!","tj":"Чӣ қадар тез шустаӣ!"}
            ]
        },
        {
            "block_no":4,
            "section_label":"课文 4",
            "scene_zh":"在房间，刘小雪在写日记。",
            "scene_uz":"Xonada Liu Xiaoxue kundalik yozmoqda.",
            "scene_ru":"В комнате Лю Сяосюэ пишет дневник.",
            "scene_tj":"Дар ҳуҷра Лю Сяосюэ рӯзнома менависад.",
            "dialogue":[
                {"speaker":"Narration","zh":"快要开学了，爸爸帮弟弟准备书包、本子和笔。我就要考试了，妈妈让我看书、看做错的题。我们上学，爸爸、妈妈比我们还忙。我问他们：“是我和弟弟上学还是你们上学？”我问完，他们都笑了。","pinyin":"Kuàiyào kāixué le, bàba bāng dìdi zhǔnbèi shūbāo, běnzi hé bǐ. Wǒ jiù yào kǎoshì le, māma ràng wǒ kàn shū, kàn zuòcuò de tí. Wǒmen shàngxué, bàba, māma bǐ wǒmen hái máng. Wǒ wèn tāmen: “Shì wǒ hé dìdi shàngxué háishi nǐmen shàngxué?” Wǒ wènwán, tāmen dōu xiào le.","uz":"Maktab boshlanishiga oz qoldi, dada ukamga sumka, daftar va qalamlarini tayyorlashga yordam berdi. Men ham tez orada imtihon topshiraman, oyi menga kitob va xato qilgan savollarimni ko‘rishni aytdi. Maktabga biz borsak ham, dada va oyi bizdan ham band. Ulardan: “Maktabga men bilan ukam boramizmi yoki sizlarmi?” deb so‘radim. So‘rab bo‘lgach, ikkalasi ham kuldi.","ru":"Скоро начинается школа. Папа помогает брату подготовить рюкзак, тетради и ручки. У меня скоро экзамен, мама велит читать и повторять задания, где я ошиблась. Учимся мы, но папа и мама заняты ещё больше нас. Я спросила: «В школу идём мы с братом или вы?» После моего вопроса они оба рассмеялись.","tj":"Ба оғози мактаб кам мондааст, падарам ба додарам барои тайёр кардани ҷузвдон, дафтар ва қалам кӯмак кард. Ман ҳам ба зудӣ имтиҳон месупорам, модарам гуфт китоб ва саволҳои хато кардаамро бинам. Мо ба мактаб меравем, аммо падараму модарам аз мо ҳам бандтаранд. Пурсидам: «Ба мактаб ману додарам меравем ё шумо?» Баъди саволам ҳарду хандиданд."}
            ]
        }
    ], ensure_ascii=False),
    "grammar_json": json.dumps([
        {
            "no":1,
            "title_zh":"主谓谓语句",
            "title_uz":"Ega-kesim birikmasi kesim bo‘lgan gap",
            "title_ru":"Предложение с субъектно-предикативной группой в роли сказуемого",
            "title_tj":"Ҷумла бо ибораи мубтадо-хабар ҳамчун хабар",
            "rule_zh":"主谓短语可以作谓语，对主语加以说明或描写，构成主谓谓语句。一般来说，主谓短语中的主语是全句主语的一部分或跟它相关。基本结构：主语+主谓短语。",
            "rule_uz":"Ega-kesim birikmasi butun gapning kesimi bo‘lib, asosiy egani tavsiflaydi yoki izohlaydi. Ichki ega odatda asosiy eganing qismi yoki unga aloqador bo‘ladi. Tuzilishi: ega + ega-kesim birikmasi.",
            "rule_ru":"Субъектно-предикативная группа может быть сказуемым и описывать основное подлежащее. Внутренний субъект обычно является его частью или связан с ним. Схема: подлежащее + субъектно-предикативная группа.",
            "rule_tj":"Ибораи мубтадо-хабар метавонад ҳамчун хабар омада, мубтадои асосиро шарҳ диҳад. Мубтадои дохилӣ одатан қисми мубтадои умумӣ ё бо он вобаста аст. Сохтор: мубтадо + ибораи мубтадо-хабар.",
            "examples":[
                {"zh":"我的书包你看见了吗？"},
                {"zh":"弟弟手很小。"},
                {"zh":"这件事他知道。"}
            ]
        },
        {
            "no":2,
            "title_zh":"选择问句",
            "title_uz":"Tanlov savoli",
            "title_ru":"Альтернативный вопрос",
            "title_tj":"Саволи интихобӣ",
            "rule_zh":"连词“还是”用在疑问句中，表示选择。基本结构：（是）A还是B。",
            "rule_uz":"“还是” so‘roq gapida variantlar orasidan tanlashni bildiradi. Asosiy shakl: （是）A 还是 B.",
            "rule_ru":"Союз “还是” в вопросительном предложении обозначает выбор. Схема: （是）A 还是 B.",
            "rule_tj":"Пайвандаки “还是” дар ҷумлаи саволӣ интихобро нишон медиҳад. Сохтор: （是）A 还是 B.",
            "examples":[
                {"zh":"妈妈，是您准备考试还是我准备考试？"},
                {"zh":"你更喜欢打篮球、踢足球还是游泳？"},
                {"zh":"我们什么时候去看电影？今天还是明天？"}
            ]
        },
        {
            "no":3,
            "title_zh":"固定格式“要/快/快要/就要……了”",
            "title_uz":"“要/快/快要/就要……了” qolipi",
            "title_ru":"Конструкция “要/快/快要/就要……了”",
            "title_tj":"Қолаби “要/快/快要/就要……了”",
            "rule_zh":"固定格式“要/快/快要/就要……了”表示某事将要发生。如果句子中有时间状语，一般用“就要……了”。",
            "rule_uz":"“要/快/快要/就要……了” biror hodisa tez orada sodir bo‘lishini bildiradi. Gapda vaqt holi bo‘lsa, odatda “就要……了” ishlatiladi.",
            "rule_ru":"“要/快/快要/就要……了” показывает, что событие вот-вот произойдёт. Если в предложении есть обстоятельство времени, обычно употребляется “就要……了”.",
            "rule_tj":"“要/快/快要/就要……了” наздик будани рӯйдодро нишон медиҳад. Агар дар ҷумла ҳоли вақт бошад, одатан “就要……了” истифода мешавад.",
            "examples":[
                {"zh":"饭菜快要做好了。"},
                {"zh":"火车快开了。"},
                {"zh":"我们下星期就要考试了。"}
            ]
        }
    ], ensure_ascii=False),
}
