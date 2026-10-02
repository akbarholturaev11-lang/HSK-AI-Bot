from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(17, 26)),
    "printed_pages": list(range(1, 10)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk2",
    "lesson_order": 1,
    "lesson_code": "NHSK2-L01",
    "title": "她请我们吃了北京烤鸭",
    "title_pinyin": "Tā qǐng wǒmen chīle Běijīng Kǎoyā",
    "goal": json.dumps(
        {
            "uz": "Taxminni “吧” bilan ifodalash; “是……的” orqali voqeaning vaqt, joy, usul yoki maqsadini ta’kidlash; “请/让/叫” bilan pivotal gaplardan foydalanish; aeroportda kutib olish va safar haqida gaplashish.",
            "ru": "Выражать предположение с “吧”; подчёркивать время, место, способ или цель события с “是……的”; использовать pivotal-предложения с “请/让/叫”; общаться при встрече в аэропорту и о поездке.",
            "tj": "Бо “吧” тахминро ифода кардан; бо “是……的” вақт, ҷой, тарз ё мақсади воқеаро таъкид кардан; ҷумлаҳои pivotal бо “请/让/叫”-ро истифода бурдан; дар бораи пешвозгирӣ дар фурудгоҳ ва сафар суҳбат кардан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars aeroportda kutib olish, Pekinga birinchi safar, yordam so‘rash va Pekin o‘rdagi haqidagi to‘rtta matn/dialog orqali yangi tuzilmalarni o‘rgatadi.",
            "ru": "Урок через четыре текста/диалога о встрече в аэропорту, первой поездке в Пекин, просьбе о помощи и пекинской утке вводит новые конструкции.",
            "tj": "Дарс тавассути чор матн/гуфтугӯ дар бораи пешвозгирӣ дар фурудгоҳ, сафари аввал ба Пекин, дархости кӯмак ва мурғиобии пекинӣ сохторҳои навро меомӯзонад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no":1,"zh":"就","pinyin":"jiù","pos":"adv.","uz":"aynan; xuddi","ru":"именно; как раз","tj":"маҳз; айнан"},
            {"no":2,"zh":"给","pinyin":"gěi","pos":"prep.","uz":"ga; uchun","ru":"кому; для","tj":"ба; барои"},
            {"no":3,"zh":"让","pinyin":"ràng","pos":"v.","uz":"ruxsat bermoq; qildirmoq","ru":"позволять; велеть","tj":"иҷозат додан; водор кардан"},
            {"no":4,"zh":"接","pinyin":"jiē","pos":"v.","uz":"kutib olmoq; qabul qilmoq","ru":"встречать; принимать","tj":"пешвоз гирифтан; қабул кардан"},
            {"no":5,"zh":"次","pinyin":"cì","pos":"m.","uz":"marta","ru":"раз; случай","tj":"бор"},
            {"no":6,"zh":"旅游","pinyin":"lǚyóu","pos":"v.","uz":"sayohat qilmoq","ru":"путешествовать","tj":"саёҳат кардан"},
            {"no":7,"zh":"帮忙","pinyin":"bāngmáng","pos":"v.","uz":"yordam bermoq","ru":"помогать","tj":"кӯмак кардан"},
            {"no":8,"zh":"不好意思","pinyin":"bù hǎoyìsi","pos":"phrase","uz":"noqulay his qilmoq; uzr","ru":"неловко; извините","tj":"хиҷолат; мебахшед"},
            {"no":9,"zh":"已经","pinyin":"yǐjīng","pos":"adv.","uz":"allaqachon","ru":"уже","tj":"аллакай"},
            {"no":10,"zh":"那","pinyin":"nà","pos":"conj.","uz":"unda; shunda","ru":"тогда","tj":"пас; он гоҳ"},
            {"no":11,"zh":"介绍","pinyin":"jièshào","pos":"v.","uz":"tanishtirmoq; tanishtirib bermoq","ru":"представлять; знакомить","tj":"шинос кардан; муаррифӣ кардан"},
            {"no":12,"zh":"有时","pinyin":"yǒushí","pos":"adv.","uz":"ba’zan","ru":"иногда","tj":"баъзан"},
            {"no":13,"zh":"懂","pinyin":"dǒng","pos":"v.","uz":"tushunmoq; bilmoq","ru":"понимать; знать","tj":"фаҳмидан; донистан"},
            {"no":14,"zh":"意思","pinyin":"yìsi","pos":"n.","uz":"ma’no; fikr","ru":"значение; смысл","tj":"маъно; фикр"},
        ],
        ensure_ascii=False,
    ),
    "proper_nouns_json": json.dumps(
        [
            {"zh":"北京烤鸭","pinyin":"Běijīng Kǎoyā","en":"Peking Duck","uz":"Pekin o‘rdagi","ru":"пекинская утка","tj":"мурғиобии пекинӣ"}
        ],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no":1,
                "section_label":"课文 1",
                "scene_zh":"在机场，王一雪接到了白家月和安妮。",
                "scene_uz":"Aeroportda Wang Yixue Bai Jiayue va Annieni kutib oldi.",
                "scene_ru":"В аэропорту Ван Исюэ встретила Бай Цзяюэ и Энни.",
                "scene_tj":"Дар фурудгоҳ Ван Исюэ Бай Ҷяюэ ва Энниро пешвоз гирифт.",
                "dialogue":[
                    {"speaker":"Bai Jiayue","zh":"请问，您是王一飞老师的姐姐吗？","pinyin":"Qǐngwèn, nín shì Wáng Yīfēi lǎoshī de jiějie ma?","uz":"Kechirasiz, siz ustoz Wang Yifeining opasimisiz?","ru":"Извините, вы старшая сестра преподавателя Ван Ифэй?","tj":"Мебахшед, шумо апаи устод Ван Ифэй ҳастед?"},
                    {"speaker":"Wang Yixue","zh":"是的，你们就是她的学生吧？","pinyin":"Shì de, nǐmen jiù shì tā de xuésheng ba?","uz":"Ha, sizlar aynan uning talabalarisiz, shundaymi?","ru":"Да. Вы как раз её студенты, верно?","tj":"Ҳа, шумо ҳамон донишҷӯёни ӯ ҳастед, дуруст?"},
                    {"speaker":"Bai Jiayue","zh":"对。我是白家月，她是安妮。","pinyin":"Duì. Wǒ shì Bái Jiāyuè, tā shì Ānnī.","uz":"Ha. Men Bai Jiayue, u Annie.","ru":"Да. Я Бай Цзяюэ, а она Энни.","tj":"Ҳа. Ман Бай Ҷяюэ, ӯ Энни аст."},
                    {"speaker":"Wang Yixue","zh":"你们好，我叫王一雪。王一飞给我打电话了，让我来接你们。","pinyin":"Nǐmen hǎo, wǒ jiào Wáng Yīxuě. Wáng Yīfēi gěi wǒ dǎ diànhuà le, ràng wǒ lái jiē nǐmen.","uz":"Salom, mening ismim Wang Yixue. Wang Yifei menga telefon qilib, sizlarni kutib olishimni aytdi.","ru":"Здравствуйте, меня зовут Ван Исюэ. Ван Ифэй позвонила мне и попросила встретить вас.","tj":"Салом, номи ман Ван Исюэ аст. Ван Ифэй ба ман занг зада, хоҳиш кард шуморо пешвоз гирам."},
                    {"speaker":"Bai Jiayue & Annie","zh":"谢谢您。","pinyin":"Xièxie nín.","uz":"Rahmat sizga.","ru":"Спасибо вам.","tj":"Раҳмат ба шумо."},
                    {"speaker":"Wang Yixue","zh":"不客气。","pinyin":"Bú kèqi.","uz":"Arzimaydi.","ru":"Не за что.","tj":"Марҳамат."}
                ]
            },
            {
                "block_no":2,
                "section_label":"课文 2",
                "scene_zh":"在王一雪的车里，白家月、安妮和王一雪在聊天儿。",
                "scene_uz":"Wang Yixuening mashinasida Bai Jiayue, Annie va Wang Yixue suhbatlashmoqda.",
                "scene_ru":"В машине Ван Исюэ Бай Цзяюэ, Энни и Ван Исюэ разговаривают.",
                "scene_tj":"Дар мошини Ван Исюэ Бай Ҷяюэ, Энни ва Ван Исюэ суҳбат мекунанд.",
                "dialogue":[
                    {"speaker":"Wang Yixue","zh":"你们是第一次来北京吗？","pinyin":"Nǐmen shì dì yī cì lái Běijīng ma?","uz":"Sizlar Pekinga birinchi marta keldingizlarmi?","ru":"Вы впервые приехали в Пекин?","tj":"Шумо бори аввал ба Пекин омадед?"},
                    {"speaker":"Bai Jiayue","zh":"是的，我们都是第一次来。","pinyin":"Shì de, wǒmen dōu shì dì yī cì lái.","uz":"Ha, hammamiz birinchi marta keldik.","ru":"Да, мы обе приехали впервые.","tj":"Ҳа, ҳамаи мо бори аввал омадем."},
                    {"speaker":"Wang Yixue","zh":"你们是来学中文的吗？","pinyin":"Nǐmen shì lái xué Zhōngwén de ma?","uz":"Sizlar xitoy tilini o‘rganish uchun keldingizlarmi?","ru":"Вы приехали изучать китайский?","tj":"Шумо барои омӯхтани забони чинӣ омадед?"},
                    {"speaker":"Annie","zh":"不是，我们是来旅游的。","pinyin":"Bú shì, wǒmen shì lái lǚyóu de.","uz":"Yo‘q, biz sayohat qilish uchun keldik.","ru":"Нет, мы приехали путешествовать.","tj":"Не, мо барои саёҳат омадем."},
                    {"speaker":"Wang Yixue","zh":"我这几天都不忙，你们有事就找我。","pinyin":"Wǒ zhè jǐ tiān dōu bù máng, nǐmen yǒu shì jiù zhǎo wǒ.","uz":"Shu kunlarda band emasman, ishingiz bo‘lsa meni toping.","ru":"В эти дни я не занята, если что-то понадобится — обращайтесь ко мне.","tj":"Ин чанд рӯз ман банд нестам, агар коре бошад ба ман муроҷиат кунед."},
                    {"speaker":"Bai Jiayue","zh":"好的，谢谢您。","pinyin":"Hǎo de, xièxie nín.","uz":"Xo‘p, rahmat sizga.","ru":"Хорошо, спасибо вам.","tj":"Хуб, раҳмат ба шумо."}
                ]
            },
            {
                "block_no":3,
                "section_label":"课文 3",
                "scene_zh":"在王一雪的车上，白家月接了个电话。",
                "scene_uz":"Wang Yixuening mashinasida Bai Jiayue telefon qo‘ng‘irog‘iga javob berdi.",
                "scene_ru":"В машине Ван Исюэ Бай Цзяюэ ответила на звонок.",
                "scene_tj":"Дар мошини Ван Исюэ Бай Ҷяюэ ба занги телефон ҷавоб дод.",
                "dialogue":[
                    {"speaker":"Chen Tianzhong","zh":"喂，家月，你明天有时间吗？我想请你帮个忙。","pinyin":"Wèi, Jiāyuè, nǐ míngtiān yǒu shíjiān ma? Wǒ xiǎng qǐng nǐ bāng ge máng.","uz":"Allo, Jiayue, ertaga vaqting bormi? Sendan bir yordam so‘ramoqchiman.","ru":"Алло, Цзяюэ, у тебя завтра есть время? Я хочу попросить тебя помочь.","tj":"Алло, Ҷяюэ, фардо вақт дорӣ? Мехоҳам аз ту як кӯмак пурсам."},
                    {"speaker":"Bai Jiayue","zh":"不好意思，天中，我已经到北京了。","pinyin":"Bù hǎoyìsi, Tiānzhōng, wǒ yǐjīng dào Běijīng le.","uz":"Kechirasan, Tianzhong, men allaqachon Pekinga yetib keldim.","ru":"Извини, Тяньчжун, я уже приехала в Пекин.","tj":"Мебахшӣ, Тянҷун, ман аллакай ба Пекин расидам."},
                    {"speaker":"Chen Tianzhong","zh":"你是什么时候到的？","pinyin":"Nǐ shì shénme shíhou dào de?","uz":"Qachon yetib kelding?","ru":"Когда ты приехала?","tj":"Кай расидӣ?"},
                    {"speaker":"Bai Jiayue","zh":"我是今天早上到的。你有事可以叫李文帮忙，他还在学校呢。","pinyin":"Wǒ shì jīntiān zǎoshang dào de. Nǐ yǒu shì kěyǐ jiào Lǐ Wén bāngmáng, tā hái zài xuéxiào ne.","uz":"Men bugun ertalab yetib keldim. Ishing bo‘lsa Li Wendan yordam so‘rashing mumkin, u hali maktabda.","ru":"Я приехала сегодня утром. Если нужна помощь, можешь попросить Ли Вэня, он ещё в школе.","tj":"Ман имрӯз субҳ расидам. Агар коре бошад, метавонӣ аз Ли Вэн кӯмак пурсӣ, ӯ ҳоло ҳам дар мактаб аст."},
                    {"speaker":"Chen Tianzhong","zh":"好的，那我给他打个电话。","pinyin":"Hǎo de, nà wǒ gěi tā dǎ ge diànhuà.","uz":"Xo‘p, unda unga telefon qilaman.","ru":"Хорошо, тогда я ему позвоню.","tj":"Хуб, пас ба ӯ занг мезанам."},
                    {"speaker":"Bai Jiayue","zh":"好，再见！","pinyin":"Hǎo, zàijiàn!","uz":"Xo‘p, xayr!","ru":"Хорошо, до свидания!","tj":"Хуб, хайр!"}
                ]
            },
            {
                "block_no":4,
                "section_label":"课文 4",
                "scene_zh":"在酒店，白家月给王一飞发信息。",
                "scene_uz":"Mehmonxonada Bai Jiayue Wang Yifeiga xabar yubordi.",
                "scene_ru":"В гостинице Бай Цзяюэ отправила сообщение Ван Ифэй.",
                "scene_tj":"Дар меҳмонхона Бай Ҷяюэ ба Ван Ифэй паём фиристод.",
                "dialogue":[
                    {"speaker":"Bai Jiayue","zh":"王老师，我们已经到北京了，是您姐姐来接的我们。她请我们吃了北京烤鸭，还给我们介绍了很多东西。我们的中文不太好，有时不太懂她的意思。","pinyin":"Wáng lǎoshī, wǒmen yǐjīng dào Běijīng le, shì nín jiějie lái jiē de wǒmen. Tā qǐng wǒmen chīle Běijīng Kǎoyā, hái gěi wǒmen jièshàole hěn duō dōngxi. Wǒmen de Zhōngwén bú tài hǎo, yǒushí bú tài dǒng tā de yìsi.","uz":"Ustoz Wang, biz allaqachon Pekinga yetib keldik, bizni opangiz kutib oldi. U bizni Pekin o‘rdagiga mehmon qildi va bizga ko‘p narsalarni tanishtirdi. Xitoy tilimiz unchalik yaxshi emas, ba’zan uning ma’nosini yaxshi tushunmaymiz.","ru":"Преподаватель Ван, мы уже приехали в Пекин, нас встретила ваша старшая сестра. Она угостила нас пекинской уткой и многое нам показала и объяснила. Наш китайский пока не очень хороший, иногда мы не совсем понимаем, что она имеет в виду.","tj":"Устод Ван, мо аллакай ба Пекин расидем, апаатон моро пешвоз гирифт. Ӯ моро бо мурғиобии пекинӣ меҳмондорӣ кард ва бисёр чизҳоро муаррифӣ намуд. Забони чинии мо ҳоло он қадар хуб нест, баъзан маънои гуфтаҳояшро хуб намефаҳмем."}
                ]
            }
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no":1,
                "title_zh":"语气助词“吧”（2）",
                "title_uz":"Modal yuklama “吧” (2)",
                "title_ru":"Модальная частица “吧” (2)",
                "title_tj":"Ҳиссачаи модалии “吧” (2)",
                "rule_zh":"“吧”位于疑问句句末，表示说话人的推测、估计。",
                "rule_uz":"“吧” so‘roq gap oxirida kelib, gapiruvchining taxmini yoki gumonini bildiradi.",
                "rule_ru":"“吧” в конце вопросительного предложения выражает предположение или оценку говорящего.",
                "rule_tj":"“吧” дар охири ҷумлаи саволӣ омада, тахмин ё гумони гӯяндаро ифода мекунад.",
                "examples":[
                    {"zh":"你们就是她的学生吧？","pinyin":"Nǐmen jiù shì tā de xuésheng ba?","uz":"Sizlar aynan uning talabalarisiz, shundaymi?","ru":"Вы как раз её студенты, верно?","tj":"Шумо ҳамон донишҷӯёни ӯ ҳастед, дуруст?"},
                    {"zh":"她唱歌很好听吧？","pinyin":"Tā chànggē hěn hǎotīng ba?","uz":"U juda yaxshi kuylaydi, shundaymi?","ru":"Она хорошо поёт, правда?","tj":"Ӯ хеле хуб месарояд, дуруст?"},
                    {"zh":"陈天中是泰国人吧？","pinyin":"Chén Tiānzhōng shì Tàiguó rén ba?","uz":"Chen Tianzhong tailandlik, shundaymi?","ru":"Чэнь Тяньчжун из Таиланда, верно?","tj":"Чэн Тянҷун таиландӣ аст, дуруст?"}
                ]
            },
            {
                "no":2,
                "title_zh":"“是……的”句",
                "title_uz":"“是……的” gapi",
                "title_ru":"Предложение “是……的”",
                "title_tj":"Ҷумлаи “是……的”",
                "rule_zh":"“是……的”用来强调已经发生事件的时间、地点、方式、实施者或目的等。肯定句和疑问句中的“是”有时可以省略，否定句中的“是”不能省略。",
                "rule_uz":"“是……的” sodir bo‘lgan voqeaning vaqt, joy, usul, bajaruvchi yoki maqsadini ta’kidlaydi. Tasdiq va savolda “是” ba’zan tushishi mumkin, inkorda esa tushmaydi.",
                "rule_ru":"“是……的” подчёркивает время, место, способ, исполнителя или цель уже произошедшего события. В утверждении и вопросе “是” иногда опускается, в отрицании — нет.",
                "rule_tj":"“是……的” вақт, ҷой, тарз, иҷрокунанда ё мақсади воқеаи рӯйдодаро таъкид мекунад. Дар тасдиқ ва савол “是” баъзан ҳазф мешавад, дар инкор не.",
                "examples":[
                    {"zh":"我们是来旅游的。","pinyin":"Wǒmen shì lái lǚyóu de.","uz":"Biz sayohat qilish uchun keldik.","ru":"Мы приехали путешествовать.","tj":"Мо барои саёҳат омадем."},
                    {"zh":"苹果在哪儿买的？","pinyin":"Píngguǒ zài nǎr mǎi de?","uz":"Olmani qayerdan sotib olding?","ru":"Где купили яблоки?","tj":"Себро аз куҷо харидед?"},
                    {"zh":"我们不是坐出租车去的。","pinyin":"Wǒmen bú shì zuò chūzūchē qù de.","uz":"Biz taksida bormadik.","ru":"Мы поехали не на такси.","tj":"Мо бо таксӣ нарафтем."}
                ]
            },
            {
                "no":3,
                "title_zh":"兼语句",
                "title_uz":"Pivotal gap",
                "title_ru":"Pivotal-предложение",
                "title_tj":"Ҷумлаи pivotal",
                "rule_zh":"兼语句的谓语由两个动词性短语构成，前一动词的宾语又是后一动词的主语。用“请、让、叫”等动词时，可表示请某人、让某人做某事。",
                "rule_uz":"Pivotal gapda ikki fe’lli birikma bo‘ladi: birinchi fe’lning obyekti keyingi fe’lning egasi vazifasini bajaradi. 请、让、叫 bilan birovdan bir ishni qilish so‘raladi yoki qildiriladi.",
                "rule_ru":"В pivotal-предложении объект первого глагола одновременно является субъектом второго. С 请、让、叫 выражается просьба или побуждение кого-то сделать что-то.",
                "rule_tj":"Дар ҷумлаи pivotal объекти феъли аввал ҳамзамон мубтадои феъли дуюм мешавад. Бо 请、让、叫 аз касе иҷрои амал дархост ё талаб мешавад.",
                "examples":[
                    {"zh":"我想请你帮个忙。","pinyin":"Wǒ xiǎng qǐng nǐ bāng ge máng.","uz":"Sendan bir yordam so‘ramoqchiman.","ru":"Я хочу попросить тебя помочь.","tj":"Мехоҳам аз ту як кӯмак пурсам."},
                    {"zh":"王老师让我们说中文。","pinyin":"Wáng lǎoshī ràng wǒmen shuō Zhōngwén.","uz":"Ustoz Wang bizga xitoycha gapirishni aytdi.","ru":"Преподаватель Ван велела нам говорить по-китайски.","tj":"Устод Ван аз мо хост бо чинӣ гап занем."},
                    {"zh":"妈妈叫孩子们回家。","pinyin":"Māma jiào háizimen huí jiā.","uz":"Onasi bolalarni uyga qaytishga chaqirdi.","ru":"Мама велела детям вернуться домой.","tj":"Модар ба кӯдакон гуфт ба хона баргарданд."}
                ]
            }
        ],
        ensure_ascii=False,
    ),
}
