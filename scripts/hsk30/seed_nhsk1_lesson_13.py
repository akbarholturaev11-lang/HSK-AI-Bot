from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程1",
    "pdf_path": "HSK 3.0 PDF/新HSK教程1.pdf",
    "pdf_pages": [109, 110, 111, 112, 113, 114, 115, 116],
    "printed_pages": [95, 96, 97, 98, 99, 100, 101, 102],
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk1",
    "lesson_order": 13,
    "lesson_code": "NHSK1-L13",
    "title": "请给我一杯茶",
    "title_pinyin": "Qǐng gěi wǒ yì bēi chá",
    "goal": json.dumps(
        {
            "uz": "“可以” bilan ruxsat yoki imkoniyatni ifodalash; “动词+一下” bilan qisqa yoki sinab ko‘rish xarakteridagi harakatni aytish; ikki obyektli gaplardan foydalanish; ovqat buyurtma qilishdagi asosiy iboralarni tushunish.",
            "ru": "Выражать разрешение и возможность с “可以”; использовать “глагол+一下” для краткого или пробного действия; строить предложения с двумя дополнениями; понимать базовые фразы для заказа еды.",
            "tj": "Бо “可以” иҷозат ё имкониятро ифода кардан; бо “феъл+一下” амали кӯтоҳ ё озмоиширо гуфтан; ҷумлаҳои ду-объектиро истифода бурдан; ибораҳои асосии фармоиши хӯрокро фаҳмидан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars savol so‘rash, telefonda aniqlashtirish va kafeda/restoranda buyurtma berish haqidagi uchta dialog orqali “可以”, “动词+一下” va 双宾语句 ni o‘rgatadi.",
            "ru": "Урок через три диалога о вопросах, уточнении по телефону и заказе в кафе/ресторане вводит “可以”, “глагол+一下” и предложения с двумя дополнениями.",
            "tj": "Дарс тавассути се гуфтугӯ дар бораи савол пурсидан, бо телефон аниқ кардан ва фармоиш дар қаҳвахона/тарабхона “可以”, “феъл+一下” ва ҷумлаи ду-объектиро меомӯзонад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no":1,"zh":"可以","pinyin":"kěyǐ","pos":"mod.","uz":"mumkin; qila olmoq","ru":"можно; мочь","tj":"мумкин; тавонистан"},
            {"no":2,"zh":"再","pinyin":"zài","pos":"adv.","uz":"yana; yana bir marta","ru":"снова; ещё раз","tj":"боз; бори дигар"},
            {"no":3,"zh":"问题","pinyin":"wèntí","pos":"n.","uz":"savol; muammo","ru":"вопрос; проблема","tj":"савол; масъала"},
            {"no":4,"zh":"卖","pinyin":"mài","pos":"v.","uz":"sotmoq","ru":"продавать","tj":"фурӯхтан"},
            {"no":5,"zh":"打电话","pinyin":"dǎ diànhuà","pos":"v.","uz":"telefon qilmoq","ru":"звонить по телефону","tj":"телефон кардан"},
            {"no":6,"zh":"一下","pinyin":"yíxià","pos":"num.-m.","uz":"bir marta; qisqacha","ru":"разок; немного","tj":"як бор; каме"},
            {"no":7,"zh":"服务员","pinyin":"fúwùyuán","pos":"n.","uz":"xizmatchi; ofitsiant/ofitsiantka","ru":"обслуживающий персонал; официант","tj":"хизматрасон; пешхизмат"},
            {"no":8,"zh":"女士","pinyin":"nǚshì","pos":"n.","uz":"xonim","ru":"дама; госпожа","tj":"хонум"},
            {"no":9,"zh":"请","pinyin":"qǐng","pos":"v.","uz":"iltimos; marhamat","ru":"пожалуйста; просить","tj":"лутфан; марҳамат"},
            {"no":10,"zh":"坐","pinyin":"zuò","pos":"v.","uz":"o‘tirmoq","ru":"сидеть; садиться","tj":"нишастан"},
            {"no":11,"zh":"给","pinyin":"gěi","pos":"v.","uz":"bermoq","ru":"давать","tj":"додан"},
            {"no":12,"zh":"杯","pinyin":"bēi","pos":"m.","uz":"piyola/stakan uchun o‘lchov so‘zi","ru":"счётное слово для чашек/стаканов","tj":"воҳиди ҳисоб барои пиёла/стакан"},
            {"no":13,"zh":"要","pinyin":"yào","pos":"v.","uz":"so‘ramoq; xohlamoq","ru":"требовать; заказывать; хотеть","tj":"талаб/фармоиш кардан; хостан"},
            {"no":14,"zh":"早饭","pinyin":"zǎofàn","pos":"n.","uz":"nonushta","ru":"завтрак","tj":"наҳорӣ"},
            {"no":15,"zh":"这个","pinyin":"zhège","pos":"pron.","uz":"bu; mana bu","ru":"этот","tj":"ин"},
            {"no":16,"zh":"面包","pinyin":"miànbāo","pos":"n.","uz":"non","ru":"хлеб","tj":"нон"},
            {"no":17,"zh":"鸡蛋","pinyin":"jīdàn","pos":"n.","uz":"tuxum","ru":"куриное яйцо","tj":"тухм"},
            {"no":18,"zh":"先生","pinyin":"xiānsheng","pos":"n.","uz":"janob","ru":"господин; сэр","tj":"ҷаноб"},
            {"no":19,"zh":"一半","pinyin":"yíbàn","pos":"num.","uz":"yarim","ru":"половина","tj":"ним"},
            {"no":20,"zh":"茶","pinyin":"chá","pos":"n.","uz":"choy","ru":"чай","tj":"чой"},
        ],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no":1,"section_label":"课文 1",
                "scene_zh":"在教室里，下课后，白家月问王老师问题。",
                "scene_en":"In the classroom, after class, Bai Jiayue asked Ms. Wang a question.",
                "scene_uz":"Sinfda darsdan keyin Bai Jiayue ustoz Wangdan savol so‘raydi.",
                "scene_ru":"В аудитории после занятия Бай Цзяюэ задаёт вопрос преподавателю Ван.",
                "scene_tj":"Дар синф пас аз дарс Бай Ҷяюэ аз устод Ван савол мепурсад.",
                "dialogue":[
                    {"speaker":"Bai Jiayue","zh":"王老师，我可以再问您一个问题吗？","pinyin":"Wáng lǎoshī, wǒ kěyǐ zài wèn nín yí ge wèntí ma?","en":"Ms. Wang, may I ask you one more question?","uz":"Ustoz Wang, sizdan yana bitta savol so‘rasam bo‘ladimi?","ru":"Преподаватель Ван, можно задать вам ещё один вопрос?","tj":"Устод Ван, метавонам боз як савол пурсам?"},
                    {"speaker":"Wang Yifei","zh":"可以。你有什么问题？","pinyin":"Kěyǐ. Nǐ yǒu shénme wèntí?","en":"Yes, of course. What's your question?","uz":"Mumkin. Qanday savoling bor?","ru":"Можно. Какой у тебя вопрос?","tj":"Мумкин. Чӣ савол дорӣ?"},
                    {"speaker":"Bai Jiayue","zh":"那个小店卖不卖手机？","pinyin":"Nàge xiǎodiàn mài bu mài shǒujī?","en":"Does that small shop sell phones?","uz":"O‘sha kichik do‘kon telefon sotadimi yo‘qmi?","ru":"В том маленьком магазине продают телефоны?","tj":"Он мағозаи хурд телефон мефурӯшад ё не?"},
                    {"speaker":"Wang Yifei","zh":"我不知道。你可以打电话问一下。","pinyin":"Wǒ bù zhīdào. Nǐ kěyǐ dǎ diànhuà wèn yíxià.","en":"I'm not sure. You can call to ask.","uz":"Bilmayman. Telefon qilib so‘rab ko‘rishing mumkin.","ru":"Не знаю. Можешь позвонить и спросить.","tj":"Намедонам. Метавонӣ занг зада як бор пурсӣ."},
                ]
            },
            {
                "block_no":2,"section_label":"课文 2",
                "scene_zh":"在咖啡馆里，王一雪想吃早饭。",
                "scene_en":"In the café, Wang Yixue wanted to have breakfast.",
                "scene_uz":"Kafeda Wang Yixue nonushta qilmoqchi.",
                "scene_ru":"В кафе Ван Исюэ хочет позавтракать.",
                "scene_tj":"Дар қаҳвахона Ван Исюэ мехоҳад наҳорӣ кунад.",
                "dialogue":[
                    {"speaker":"Waitress","zh":"女士，请坐！您喝什么？","pinyin":"Nǚshì, qǐng zuò! Nín hē shénme?","en":"Madam, have a seat, please! What would you like to drink?","uz":"Xonim, marhamat o‘tiring! Nima ichasiz?","ru":"Госпожа, присаживайтесь! Что будете пить?","tj":"Хонум, марҳамат нишинед! Чӣ менӯшед?"},
                    {"speaker":"Wang Yixue","zh":"我看一下。请给我一杯牛奶。","pinyin":"Wǒ kàn yíxià. Qǐng gěi wǒ yì bēi niúnǎi.","en":"Let me have a look. I'll have a glass of milk, please.","uz":"Bir ko‘rib olay. Iltimos, menga bir stakan sut bering.","ru":"Дайте посмотреть. Пожалуйста, дайте мне стакан молока.","tj":"Бигзор як нигоҳ кунам. Лутфан, ба ман як пиёла шир диҳед."},
                    {"speaker":"Waitress","zh":"好的。您还要什么？","pinyin":"Hǎo de. Nín hái yào shénme?","en":"Alright. Would you like anything else?","uz":"Xo‘p. Yana nima olasiz?","ru":"Хорошо. Что-нибудь ещё?","tj":"Хуб. Боз чӣ мехоҳед?"},
                    {"speaker":"Wang Yixue","zh":"我还没吃早饭，再要这个面包和鸡蛋吧。","pinyin":"Wǒ hái méi chī zǎofàn, zài yào zhège miànbāo hé jīdàn ba.","en":"I haven't had breakfast yet, so I'll have a fried egg on bread.","uz":"Men hali nonushta qilmaganman, yana mana bu non va tuxumni olaman.","ru":"Я ещё не завтракала, возьму ещё этот хлеб и яйцо.","tj":"Ман ҳоло наҳорӣ накардаам, боз ҳамин нон ва тухмро мегирам."},
                ]
            },
            {
                "block_no":3,"section_label":"课文 3",
                "scene_zh":"在餐馆里，刘明在点餐。",
                "scene_en":"In the restaurant, Liu Ming was ordering food.",
                "scene_uz":"Restoranda Liu Ming ovqat buyurtma qilmoqda.",
                "scene_ru":"В ресторане Лю Мин делает заказ.",
                "scene_tj":"Дар тарабхона Лю Мин хӯрок фармоиш медиҳад.",
                "dialogue":[
                    {"speaker":"Waiter","zh":"先生，请坐！您要什么？","pinyin":"Xiānsheng, qǐng zuò! Nín yào shénme?","en":"Sir, have a seat, please! What would you like to order?","uz":"Janob, marhamat o‘tiring! Nima buyurtma qilasiz?","ru":"Господин, присаживайтесь! Что будете заказывать?","tj":"Ҷаноб, марҳамат нишинед! Чӣ фармоиш медиҳед?"},
                    {"speaker":"Liu Ming","zh":"我要一斤饺子。","pinyin":"Wǒ yào yì jīn jiǎozi.","en":"I'll have one jin of jiaozi.","uz":"Menga bir jin jiaozi bering.","ru":"Я возьму один цзинь цзяоцзы.","tj":"Ман як ҷин ҷяозы мегирам."},
                    {"speaker":"Waiter","zh":"好的。一斤饺子40个。","pinyin":"Hǎo de. Yì jīn jiǎozi sìshí ge.","en":"Alright. One jin of jiaozi has forty pieces.","uz":"Xo‘p. Bir jin jiaozi 40 dona bo‘ladi.","ru":"Хорошо. В одном цзине цзяоцзы 40 штук.","tj":"Хуб. Як ҷин ҷяозы 40 дона мешавад."},
                    {"speaker":"Liu Ming","zh":"40个太多了，我要一半吧。","pinyin":"Sìshí ge tài duō le, wǒ yào yíbàn ba.","en":"40 is too many. I'll have half of that.","uz":"40 dona juda ko‘p, yarmini olaman.","ru":"40 штук слишком много, возьму половину.","tj":"40 дона хеле зиёд, нисфашро мегирам."},
                    {"speaker":"Waiter","zh":"半斤20个。您想喝什么？","pinyin":"Bàn jīn èrshí ge. Nín xiǎng hē shénme?","en":"Half a jin is twenty. What would you like to drink?","uz":"Yarim jin 20 dona. Nima ichasiz?","ru":"Полцзиня — 20 штук. Что будете пить?","tj":"Ним ҷин 20 дона. Чӣ менӯшед?"},
                    {"speaker":"Liu Ming","zh":"请给我一杯茶吧。","pinyin":"Qǐng gěi wǒ yì bēi chá ba.","en":"I'll have a cup of tea, please.","uz":"Iltimos, menga bir piyola choy bering.","ru":"Пожалуйста, дайте мне чашку чая.","tj":"Лутфан, ба ман як пиёла чой диҳед."},
                ]
            },
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no":1,"title_zh":"能愿动词“可以”","title_uz":"Modal fe’l “可以”","title_ru":"Модальный глагол “可以”","title_tj":"Феъли модалии “可以”",
                "rule_zh":"能愿动词“可以”位于动词前，表示可能、能够或许可。",
                "rule_en":"The modal verb “可以” is placed before a verb to indicate possibility, capability, or permission.",
                "rule_uz":"“可以” fe’l oldidan kelib mumkinlik, qobiliyat yoki ruxsatni bildiradi.",
                "rule_ru":"“可以” ставится перед глаголом и выражает возможность, способность или разрешение.",
                "rule_tj":"“可以” пеш аз феъл омада, имкон, қобилият ё иҷозатро ифода мекунад.",
                "examples":[
                    {"zh":"我可以再问您一个问题吗？","pinyin":"Wǒ kěyǐ zài wèn nín yí ge wèntí ma?","uz":"Sizdan yana bir savol so‘rasam bo‘ladimi?","ru":"Можно задать вам ещё один вопрос?","tj":"Метавонам боз як савол пурсам?"},
                    {"zh":"你们可以看这本书。","pinyin":"Nǐmen kěyǐ kàn zhè běn shū.","uz":"Sizlar bu kitobni o‘qishingiz mumkin.","ru":"Вы можете прочитать эту книгу.","tj":"Шумо метавонед ин китобро хонед."},
                    {"zh":"我可以坐吗？可以，请坐！","pinyin":"Wǒ kěyǐ zuò ma? Kěyǐ, qǐng zuò!","uz":"O‘tirsam bo‘ladimi? Bo‘ladi, marhamat o‘tiring!","ru":"Можно сесть? Можно, присаживайтесь!","tj":"Нишастан мумкин? Мумкин, марҳамат нишинед!"},
                ]
            },
            {
                "no":2,"title_zh":"“动词+一下”结构","title_uz":"“Fe’l+一下” tuzilmasi","title_ru":"Конструкция “глагол+一下”","title_tj":"Сохтори “феъл+一下”",
                "rule_zh":"“动词+一下”表示动作时间短或动作的尝试。",
                "rule_en":"The “Verb+一下” structure indicates that an action is performed as a quick attempt or is brief.",
                "rule_uz":"“Fe’l+一下” harakatning qisqa davom etishini yoki sinab ko‘rish tarzida bajarilishini bildiradi.",
                "rule_ru":"“Глагол+一下” показывает краткое действие или попытку выполнить действие.",
                "rule_tj":"“Феъл+一下” кӯтоҳ будани амал ё иҷрои онро ҳамчун кӯшиш нишон медиҳад.",
                "examples":[
                    {"zh":"你可以打电话问一下。","pinyin":"Nǐ kěyǐ dǎ diànhuà wèn yíxià.","uz":"Telefon qilib so‘rab ko‘rishing mumkin.","ru":"Можешь позвонить и спросить.","tj":"Метавонӣ занг зада як бор пурсӣ."},
                    {"zh":"请休息一下。","pinyin":"Qǐng xiūxi yíxià.","uz":"Iltimos, biroz dam oling.","ru":"Пожалуйста, немного отдохните.","tj":"Лутфан, каме истироҳат кунед."},
                    {"zh":"你看一下吧。","pinyin":"Nǐ kàn yíxià ba.","uz":"Bir ko‘rib qo‘y.","ru":"Посмотри немного.","tj":"Як нигоҳ кун."},
                ]
            },
            {
                "no":3,"title_zh":"双宾语句（1）","title_uz":"Ikki obyektli gap (1)","title_ru":"Предложение с двумя дополнениями (1)","title_tj":"Ҷумлаи ду-объектӣ (1)",
                "rule_zh":"双宾语句是一个动词带两个宾语的句子。本册重点学习“给、问”构成的双宾语句。",
                "rule_en":"A double-object sentence is one where a verb takes two objects. This volume focuses on double-object sentences formed by 给 and 问.",
                "rule_uz":"Ikki obyektli gapda bitta fe’l ikkita obyekt oladi. Bu bosqichda asosan 给 va 问 bilan tuzilgan shakllar o‘rganiladi.",
                "rule_ru":"В предложении с двумя дополнениями один глагол принимает два объекта. Здесь основное внимание уделяется конструкциям с 给 и 问.",
                "rule_tj":"Дар ҷумлаи ду-объектӣ як феъл ду объект мегирад. Дар ин сатҳ асосан сохторҳои бо 给 ва 问 омӯхта мешаванд.",
                "examples":[
                    {"zh":"请给我一杯牛奶。","pinyin":"Qǐng gěi wǒ yì bēi niúnǎi.","uz":"Iltimos, menga bir stakan sut bering.","ru":"Пожалуйста, дайте мне стакан молока.","tj":"Лутфан, ба ман як пиёла шир диҳед."},
                    {"zh":"白家月给安妮一个苹果。","pinyin":"Bái Jiāyuè gěi Ānnī yí ge píngguǒ.","uz":"Bai Jiayue Anniega bitta olma berdi.","ru":"Бай Цзяюэ дала Энни яблоко.","tj":"Бай Ҷяюэ ба Энни як себ дод."},
                    {"zh":"我问老师两个问题。","pinyin":"Wǒ wèn lǎoshī liǎng ge wèntí.","uz":"Men o‘qituvchidan ikkita savol so‘radim.","ru":"Я задал преподавателю два вопроса.","tj":"Ман аз устод ду савол пурсидам."},
                ]
            }
        ],
        ensure_ascii=False,
    ),
}
