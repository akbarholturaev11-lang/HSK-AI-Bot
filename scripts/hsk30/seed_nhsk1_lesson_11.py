from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程1",
    "pdf_path": "HSK 3.0 PDF/新HSK教程1.pdf",
    "pdf_pages": [92, 93, 94, 95, 96, 97, 98, 99],
    "printed_pages": [78, 79, 80, 81, 82, 83, 84, 85],
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk1",
    "lesson_order": 11,
    "lesson_code": "NHSK1-L11",
    "title": "我读大学呢",
    "title_pinyin": "Wǒ dú dàxué ne",
    "goal": json.dumps(
        {
            "uz": "正反问 shaklidagi savollarni tushunish va tuzish; “在/正在” bilan davom etayotgan harakatni ifodalash; “要” bilan xohish yoki niyatni bildirish.",
            "ru": "Понимать и строить утвердительно-отрицательные вопросы; выражать продолжающееся действие с “在/正在”; выражать желание или намерение с “要”.",
            "tj": "Саволҳои тасдиқӣ-инкориро фаҳмидан ва сохтан; бо “在/正在” амали давомдорро ифода кардан; бо “要” хоҳиш ё ниятро нишон додан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars restoran qidirish, universitetda o‘qish va ukasining rejalari haqidagi uchta dialog orqali 正反问, “在/正在” va “要” ni o‘rgatadi.",
            "ru": "Урок через три диалога о поиске ресторана, учёбе в университете и планах младшего брата вводит утвердительно-отрицательные вопросы, “在/正在” и “要”.",
            "tj": "Дарс тавассути се гуфтугӯ дар бораи ҷустуҷӯи тарабхона, таҳсил дар донишгоҳ ва нақшаҳои бародари хурдӣ саволҳои тасдиқӣ-инкорӣ, “在/正在” ва “要”-ро меомӯзонад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no":1,"zh":"时候","pinyin":"shíhou","pos":"n.","uz":"vaqt; payt","ru":"время; момент","tj":"вақт; лаҳза"},
            {"no":2,"zh":"饭店","pinyin":"fàndiàn","pos":"n.","uz":"restoran","ru":"ресторан","tj":"тарабхона"},
            {"no":3,"zh":"知道","pinyin":"zhīdào","pos":"v.","uz":"bilmoq","ru":"знать; понимать","tj":"донистан"},
            {"no":4,"zh":"正在","pinyin":"zhèngzài","pos":"adv.","uz":"ayni paytda ...yapti","ru":"в процессе; сейчас","tj":"ҳоло дар ҷараён"},
            {"no":5,"zh":"找","pinyin":"zhǎo","pos":"v.","uz":"qidirmoq","ru":"искать","tj":"ҷустуҷӯ кардан"},
            {"no":6,"zh":"开车","pinyin":"kāichē","pos":"v.","uz":"mashina haydamoq","ru":"водить машину","tj":"мошин рондан"},
            {"no":7,"zh":"车","pinyin":"chē","pos":"n.","uz":"mashina; transport","ru":"машина; транспорт","tj":"мошин; нақлиёт"},
            {"no":8,"zh":"在","pinyin":"zài","pos":"adv.","uz":"davom etayotgan harakat belgisi","ru":"показатель действия в процессе","tj":"нишондиҳандаи амали давомдор"},
            {"no":9,"zh":"读","pinyin":"dú","pos":"v.","uz":"o‘qimoq; tahsil olmoq","ru":"учиться; читать","tj":"хондан; таҳсил кардан"},
            {"no":10,"zh":"大学","pinyin":"dàxué","pos":"n.","uz":"universitet","ru":"университет","tj":"донишгоҳ"},
            {"no":11,"zh":"大学生","pinyin":"dàxuéshēng","pos":"n.","uz":"universitet talabasi","ru":"студент университета","tj":"донишҷӯи донишгоҳ"},
            {"no":12,"zh":"学","pinyin":"xué","pos":"v.","uz":"o‘rganmoq; o‘qimoq","ru":"учить; изучать","tj":"омӯхтан; хондан"},
            {"no":13,"zh":"医","pinyin":"yī","pos":"n.","uz":"tibbiyot","ru":"медицина","tj":"тиб"},
            {"no":14,"zh":"弟弟","pinyin":"dìdi","pos":"n.","uz":"uka","ru":"младший брат","tj":"бародари хурдӣ"},
            {"no":15,"zh":"起床","pinyin":"qǐchuáng","pos":"v.","uz":"uyg‘onib turmoq","ru":"вставать с постели","tj":"аз хоб хестан"},
            {"no":16,"zh":"睡觉","pinyin":"shuìjiào","pos":"v.","uz":"uxlamoq","ru":"спать","tj":"хобидан"},
            {"no":17,"zh":"睡","pinyin":"shuì","pos":"v.","uz":"uxlamoq","ru":"спать","tj":"хобидан"},
            {"no":18,"zh":"那里","pinyin":"nàli","pos":"pron.","uz":"u yer","ru":"там","tj":"он ҷо"},
            {"no":19,"zh":"哪里","pinyin":"nǎli","pos":"pron.","uz":"qayer","ru":"где; куда","tj":"куҷо"},
            {"no":20,"zh":"昨天","pinyin":"zuótiān","pos":"n.","uz":"kecha","ru":"вчера","tj":"дирӯз"},
            {"no":21,"zh":"问","pinyin":"wèn","pos":"v.","uz":"so‘ramoq","ru":"спрашивать","tj":"пурсидан"},
            {"no":22,"zh":"对","pinyin":"duì","pos":"prep.","uz":"ga; tomon","ru":"к; по отношению к","tj":"ба; нисбат ба"},
            {"no":23,"zh":"说","pinyin":"shuō","pos":"v.","uz":"gapirmoq; aytmoq","ru":"говорить; сказать","tj":"гуфтан; сухан гуфтан"},
            {"no":24,"zh":"要","pinyin":"yào","pos":"mod.","uz":"xohlamoq; niyat qilmoq","ru":"хотеть; намереваться","tj":"хостан; ният кардан"},
            {"no":25,"zh":"小朋友","pinyin":"xiǎopéngyou","pos":"n.","uz":"bola","ru":"ребёнок","tj":"кӯдак"},
        ],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no":1,"section_label":"课文 1",
                "scene_zh":"在路上，李文在找饭店，王一飞给他打电话。",
                "scene_en":"On the road, while Li Wen was looking for the restaurant, Wang Yifei called him.",
                "scene_uz":"Yo‘lda Li Wen restoran qidirayotganida Wang Yifei unga telefon qiladi.",
                "scene_ru":"По дороге, пока Ли Вэнь искал ресторан, Ван Ифэй позвонила ему.",
                "scene_tj":"Дар роҳ, вақте Ли Вэн тарабхонаро меҷуст, Ван Ифэй ба ӯ занг зад.",
                "dialogue":[
                    {"speaker":"Wang Yifei","zh":"喂，李文，你什么时候能到饭店？","pinyin":"Wèi, Lǐ Wén, nǐ shénme shíhou néng dào fàndiàn?","en":"Hello, Li Wen. When will you arrive at the restaurant?","uz":"Allo, Li Wen, restoranga qachon yetib kelasan?","ru":"Алло, Ли Вэнь, когда ты приедешь в ресторан?","tj":"Алло, Ли Вэн, кай ба тарабхона мерасӣ?"},
                    {"speaker":"Li Wen","zh":"还不知道，正在找呢。它是不是在超市后边？","pinyin":"Hái bù zhīdào, zhèngzài zhǎo ne. Tā shì bu shì zài chāoshì hòubian?","en":"Not sure yet. I'm looking for it now. Is it behind the supermarket?","uz":"Hali bilmayman, hozir qidiryapman. U supermarket orqasidami?","ru":"Пока не знаю, сейчас ищу. Он за супермаркетом?","tj":"Ҳоло намедонам, ҷустуҷӯ карда истодаам. Он паси супермаркет аст?"},
                    {"speaker":"Wang Yifei","zh":"是的。你开车没开车？","pinyin":"Shì de. Nǐ kāichē méi kāichē?","en":"Yes, it is. Are you driving or not?","uz":"Ha. Mashina haydayapsanmi yo‘qmi?","ru":"Да. Ты за рулём или нет?","tj":"Ҳа. Мошин меронӣ ё не?"},
                    {"speaker":"Li Wen","zh":"我没开车，坐车呢。","pinyin":"Wǒ méi kāichē, zuò chē ne.","en":"No, I'm not driving. I'm taking a taxi.","uz":"Mashina haydamayapman, transportda ketyapman.","ru":"Нет, я не за рулём, еду на машине.","tj":"Не, мошин намеронам, бо нақлиёт меравам."},
                ]
            },
            {
                "block_no":2,"section_label":"课文 2",
                "scene_zh":"在饭店里，王一飞和李文见面后聊天儿。",
                "scene_en":"After meeting at the restaurant, Wang Yifei and Li Wen were chatting.",
                "scene_uz":"Restoranda uchrashgach Wang Yifei va Li Wen suhbatlashmoqda.",
                "scene_ru":"После встречи в ресторане Ван Ифэй и Ли Вэнь разговаривают.",
                "scene_tj":"Пас аз вохӯрӣ дар тарабхона Ван Ифэй ва Ли Вэн суҳбат мекунанд.",
                "dialogue":[
                    {"speaker":"Wang Yifei","zh":"你还在读大学吗？","pinyin":"Nǐ hái zài dú dàxué ma?","en":"Are you still studying at university?","uz":"Hali ham universitetda o‘qiyapsanmi?","ru":"Ты всё ещё учишься в университете?","tj":"Ҳоло ҳам дар донишгоҳ мехонӣ?"},
                    {"speaker":"Li Wen","zh":"对，我读大学呢，还是大学生。","pinyin":"Duì, wǒ dú dàxué ne, hái shì dàxuéshēng.","en":"Yes, I'm studying at university, and I'm still an undergraduate.","uz":"Ha, universitetda o‘qiyman, hali talabaman.","ru":"Да, я учусь в университете, я ещё студент.","tj":"Ҳа, дар донишгоҳ мехонам, ҳоло ҳам донишҷӯ ҳастам."},
                    {"speaker":"Wang Yifei","zh":"你们学习忙不忙？","pinyin":"Nǐmen xuéxí máng bu máng?","en":"Are you busy with your studies?","uz":"O‘qishingiz bandmi yo‘qmi?","ru":"У вас учёба напряжённая?","tj":"Таҳсилатон сермашғул аст ё не?"},
                    {"speaker":"Li Wen","zh":"非常忙，我学医，我们的课很多。","pinyin":"Fēicháng máng, wǒ xué yī, wǒmen de kè hěn duō.","en":"Very busy. I major in medicine, and we have a lot of classes.","uz":"Juda band. Men tibbiyot o‘qiyman, darslarimiz juda ko‘p.","ru":"Очень заняты. Я изучаю медицину, у нас много занятий.","tj":"Хеле банд. Ман тиб мехонам, дарсҳоямон бисёранд."},
                ]
            },
            {
                "block_no":3,"section_label":"课文 3",
                "scene_zh":"星期六早上，刘明要去医院加班，出门前和女儿小雪说话。",
                "scene_en":"On Saturday morning, Liu Ming was going to the hospital to work overtime. Before leaving, he talked with his daughter.",
                "scene_uz":"Shanba ertalab Liu Ming kasalxonaga qo‘shimcha ishga ketishidan oldin qizi Xiaoxue bilan gaplashadi.",
                "scene_ru":"В субботу утром Лю Мин собирается на сверхурочную работу в больницу и перед выходом разговаривает с дочерью Сяосюэ.",
                "scene_tj":"Субҳи шанбе Лю Мин барои кори иловагӣ ба беморхона меравад ва пеш аз баромадан бо духтараш Сяосюэ суҳбат мекунад.",
                "dialogue":[
                    {"speaker":"Liu Ming","zh":"弟弟起床没起床呢？","pinyin":"Dìdi qǐchuáng méi qǐchuáng ne?","en":"Has your younger brother gotten up yet?","uz":"Ukang turdimi yo‘qmi?","ru":"Младший брат уже встал или нет?","tj":"Бародари хурдиат аз хоб хест ё не?"},
                    {"speaker":"Liu Xiaoxue","zh":"没起床呢，还在睡觉。","pinyin":"Méi qǐchuáng ne, hái zài shuìjiào.","en":"No, he hasn't gotten up yet. He's still sleeping.","uz":"Yo‘q, hali turmadi, hanuz uxlayapti.","ru":"Нет, ещё не встал, всё ещё спит.","tj":"Не, ҳоло нахестааст, ҳанӯз хоб аст."},
                    {"speaker":"Liu Ming","zh":"还睡呢？他今天去不去那里？","pinyin":"Hái shuì ne? Tā jīntiān qù bu qù nàli?","en":"Still sleeping? Is he going there today?","uz":"Hali uxlayaptimi? U bugun u yerga boradimi yo‘qmi?","ru":"Всё ещё спит? Он сегодня пойдёт туда или нет?","tj":"Ҳанӯз хоб аст? Ӯ имрӯз ба он ҷо меравад ё не?"},
                    {"speaker":"Liu Xiaoxue","zh":"去哪里？","pinyin":"Qù nǎli?","en":"Where?","uz":"Qayerga?","ru":"Куда?","tj":"Ба куҷо?"},
                    {"speaker":"Liu Ming","zh":"去超市。","pinyin":"Qù chāoshì.","en":"To the supermarket.","uz":"Supermarketga.","ru":"В супермаркет.","tj":"Ба супермаркет."},
                    {"speaker":"Liu Xiaoxue","zh":"我昨天问他，他对我说，他不去，他今天要和小朋友玩。","pinyin":"Wǒ zuótiān wèn tā, tā duì wǒ shuō, tā bú qù, tā jīntiān yào hé xiǎopéngyou wán.","en":"I asked him yesterday. He told me he wasn't going. He's going to play with his friends today.","uz":"Kecha undan so‘radim. U menga bormasligini aytdi, bugun bolalar bilan o‘ynamoqchi.","ru":"Я вчера спросила его. Он сказал мне, что не пойдёт; сегодня он хочет играть с друзьями.","tj":"Ман дирӯз аз ӯ пурсидам. Ӯ гуфт, ки намеравад; имрӯз мехоҳад бо кӯдакон бозӣ кунад."},
                ]
            },
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no":1,"title_zh":"正反问","title_uz":"Tasdiq-inkor savoli","title_ru":"Утвердительно-отрицательный вопрос","title_tj":"Саволи тасдиқӣ-инкорӣ",
                "rule_zh":"正反问用“肯定形式+否定形式”构成。动词常用“V+不/没+V”，形容词常用“Adj+不+Adj”。",
                "rule_en":"Affirmative-negative questions use an affirmative form followed by its negative form, such as V+不/没+V or Adj+不+Adj.",
                "rule_uz":"正反问 tasdiq va inkor shaklini ketma-ket qo‘yadi: V+不/没+V yoki sifat+不+sifat.",
                "rule_ru":"Утвердительно-отрицательный вопрос строится сочетанием утвердительной и отрицательной формы: V+不/没+V или Adj+不+Adj.",
                "rule_tj":"Саволи тасдиқӣ-инкорӣ аз шакли тасдиқӣ ва инкорӣ сохта мешавад: V+不/没+V ё сифат+不+сифат.",
                "examples":[
                    {"zh":"它是不是在超市后边？","pinyin":"Tā shì bu shì zài chāoshì hòubian?","uz":"U supermarket orqasidami yo‘qmi?","ru":"Он за супермаркетом или нет?","tj":"Он паси супермаркет аст ё не?"},
                    {"zh":"你去没去学校？","pinyin":"Nǐ qù méi qù xuéxiào?","uz":"Maktabga bordingmi yo‘qmi?","ru":"Ты ходил в школу или нет?","tj":"Ба мактаб рафтӣ ё не?"},
                    {"zh":"这种衣服好看不好看？","pinyin":"Zhè zhǒng yīfu hǎokàn bù hǎokàn?","uz":"Bu turdagi kiyim chiroylimi yo‘qmi?","ru":"Такая одежда красивая или нет?","tj":"Ин навъи либос зебост ё не?"},
                ]
            },
            {
                "no":2,"title_zh":"时间副词“在/正在”","title_uz":"Vaqt ravishlari “在/正在”","title_ru":"Временные наречия “在/正在”","title_tj":"Зарфҳои вақт “在/正在”",
                "rule_zh":"“在/正在”位于动词前，表示动作正在进行或情况在继续。可用“在/正在+动词”“在/正在+动词+呢”或“动词+呢”；否定回答用“没（有）”。",
                "rule_en":"“在/正在” are placed before verbs to indicate that an action is ongoing or a situation is continuing. Forms include 在/正在+Verb, 在/正在+Verb+呢, and Verb+呢; negative responses use 没（有）.",
                "rule_uz":"“在/正在” fe’l oldidan kelib harakat davom etayotganini bildiradi. Shakllar: 在/正在+fe’l, 在/正在+fe’l+呢, fe’l+呢; inkorda 没（有） ishlatiladi.",
                "rule_ru":"“在/正在” ставятся перед глаголом и показывают продолжающееся действие. Формы: 在/正在+глагол, 在/正在+глагол+呢, глагол+呢; отрицание — 没（有）.",
                "rule_tj":"“在/正在” пеш аз феъл омада, идома доштани амалро нишон медиҳанд. Шаклҳо: 在/正在+феъл, 在/正在+феъл+呢, феъл+呢; инкор бо 没（有）.",
                "examples":[
                    {"zh":"你还在读大学吗？","pinyin":"Nǐ hái zài dú dàxué ma?","uz":"Hali ham universitetda o‘qiyapsanmi?","ru":"Ты всё ещё учишься в университете?","tj":"Ҳоло ҳам дар донишгоҳ мехонӣ?"},
                    {"zh":"学生们在/正在上课呢。","pinyin":"Xuéshengmen zài/zhèngzài shàngkè ne.","uz":"Talabalar hozir darsda.","ru":"Студенты сейчас на занятии.","tj":"Донишҷӯён ҳоло дар дарсанд."},
                    {"zh":"他们读书呢。","pinyin":"Tāmen dú shū ne.","uz":"Ular hozir kitob o‘qishyapti.","ru":"Они сейчас читают.","tj":"Онҳо ҳоло китоб мехонанд."},
                ]
            },
            {
                "no":3,"title_zh":"能愿动词“要”","title_uz":"Modal fe’l “要”","title_ru":"Модальный глагол “要”","title_tj":"Феъли модалии “要”",
                "rule_zh":"“要”在动词前，表示愿望、打算做某事。",
                "rule_en":"In front of a verb, the modal verb “要” indicates the desire or intention to do something.",
                "rule_uz":"“要” fe’l oldidan kelib biror ishni qilish istagi yoki niyatini bildiradi.",
                "rule_ru":"“要” перед глаголом выражает желание или намерение что-то сделать.",
                "rule_tj":"“要” пеш аз феъл омада, хоҳиш ё нияти иҷрои амалро ифода мекунад.",
                "examples":[
                    {"zh":"他今天要和小朋友玩。","pinyin":"Tā jīntiān yào hé xiǎopéngyou wán.","uz":"U bugun bolalar bilan o‘ynamoqchi.","ru":"Сегодня он хочет играть с детьми.","tj":"Ӯ имрӯз мехоҳад бо кӯдакон бозӣ кунад."},
                    {"zh":"妈妈要去超市。","pinyin":"Māma yào qù chāoshì.","uz":"Onam supermarketga bormoqchi.","ru":"Мама собирается в супермаркет.","tj":"Модарам ба супермаркет рафтан мехоҳад."},
                    {"zh":"白家月要在家里学中文。","pinyin":"Bái Jiāyuè yào zài jiālǐ xué Zhōngwén.","uz":"Bai Jiayue uyda xitoy tilini o‘rganmoqchi.","ru":"Бай Цзяюэ хочет изучать китайский дома.","tj":"Бай Ҷяюэ мехоҳад дар хона забони чинӣ омӯзад."},
                ]
            }
        ],
        ensure_ascii=False,
    ),
}
