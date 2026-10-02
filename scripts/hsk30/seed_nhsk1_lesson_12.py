from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程1",
    "pdf_path": "HSK 3.0 PDF/新HSK教程1.pdf",
    "pdf_pages": [100, 101, 102, 103, 104, 105, 106, 107, 108],
    "printed_pages": [86, 87, 88, 89, 90, 91, 92, 93, 94],
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk1",
    "lesson_order": 12,
    "lesson_code": "NHSK1-L12",
    "title": "昨天下雪了",
    "title_pinyin": "Zuótiān xià xuě le",
    "goal": json.dumps(
        {
            "uz": "Ob-havo holatini tushunish va aytish; tibbiy holatni qisqa tasvirlash; no-subject-predicate gaplarni, holat o‘zgarishini bildiruvchi “了（1）” ni va “太……了” qolipini ishlatish.",
            "ru": "Понимать и описывать погоду; кратко описывать состояние здоровья; использовать безличные/нерасчленённые предложения, “了（1）” для изменения ситуации и модель “太……了”.",
            "tj": "Ҳолати обу ҳаворо фаҳмидан ва гуфтан; ҳолати саломатиро кӯтоҳ тасвир кардан; ҷумлаҳои бемуайян, “了（1）” барои тағйири ҳолат ва қолаби “太……了”-ро истифода бурдан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars yomg‘irli ob-havo, qor yog‘ishi va shifokor ko‘rigi haqidagi uchta dialog orqali 非主谓句, “了（1）” va “太……了” ni o‘rgatadi.",
            "ru": "Урок через три диалога о дождливой погоде, снегопаде и визите к врачу вводит 非主谓句, “了（1）” и “太……了”.",
            "tj": "Дарс тавассути се гуфтугӯ дар бораи борон, барф ва муоинаи духтур 非主谓句, “了（1）” ва “太……了”-ро меомӯзонад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no":1,"zh":"天气","pinyin":"tiānqì","pos":"n.","uz":"ob-havo","ru":"погода","tj":"обу ҳаво"},
            {"no":2,"zh":"这里","pinyin":"zhèlǐ","pos":"pron.","uz":"bu yer","ru":"здесь","tj":"ин ҷо"},
            {"no":3,"zh":"天","pinyin":"tiān","pos":"n.","uz":"ob-havo; osmon","ru":"погода; небо","tj":"обу ҳаво; осмон"},
            {"no":4,"zh":"下雨","pinyin":"xiàyǔ","pos":"v.","uz":"yomg‘ir yog‘moq","ru":"идти о дожде","tj":"борон боридан"},
            {"no":5,"zh":"了","pinyin":"le","pos":"part.","uz":"holat o‘zgarishi yuklamasi","ru":"частица изменения состояния","tj":"ҳиссачаи тағйири ҳолат"},
            {"no":6,"zh":"雨","pinyin":"yǔ","pos":"n.","uz":"yomg‘ir","ru":"дождь","tj":"борон"},
            {"no":7,"zh":"有点儿","pinyin":"yǒudiǎnr","pos":"adv.","uz":"biroz; sal","ru":"немного; довольно","tj":"каме"},
            {"no":8,"zh":"觉得","pinyin":"juéde","pos":"v.","uz":"his qilmoq; deb o‘ylamoq","ru":"чувствовать; считать","tj":"ҳис кардан; фикр кардан"},
            {"no":9,"zh":"冷","pinyin":"lěng","pos":"adj.","uz":"sovuq","ru":"холодный","tj":"сард"},
            {"no":10,"zh":"下","pinyin":"xià","pos":"v.","uz":"yog‘moq (qor/yomg‘ir)","ru":"идти; выпадать осадкам","tj":"боридан; фуромадан"},
            {"no":11,"zh":"雪","pinyin":"xuě","pos":"n.","uz":"qor","ru":"снег","tj":"барф"},
            {"no":12,"zh":"来","pinyin":"lái","pos":"v.","uz":"kelmoq","ru":"приходить","tj":"омадан"},
            {"no":13,"zh":"公司","pinyin":"gōngsī","pos":"n.","uz":"kompaniya","ru":"компания","tj":"ширкат"},
            {"no":14,"zh":"生病","pinyin":"shēngbìng","pos":"v.","uz":"kasal bo‘lmoq","ru":"заболеть","tj":"бемор шудан"},
            {"no":15,"zh":"看病","pinyin":"kànbìng","pos":"v.","uz":"shifokorga ko‘rinmoq","ru":"обращаться к врачу","tj":"ба духтур муроҷиат кардан"},
            {"no":16,"zh":"病","pinyin":"bìng","pos":"v.","uz":"kasal bo‘lmoq","ru":"болеть","tj":"бемор будан"},
            {"no":17,"zh":"一点儿","pinyin":"yìdiǎnr","pos":"num.-m.","uz":"biroz","ru":"немного","tj":"каме"},
            {"no":18,"zh":"药","pinyin":"yào","pos":"n.","uz":"dori","ru":"лекарство","tj":"дору"},
            {"no":19,"zh":"天","pinyin":"tiān","pos":"m.","uz":"kun","ru":"день","tj":"рӯз"},
            {"no":20,"zh":"回","pinyin":"huí","pos":"v.","uz":"qaytmoq","ru":"возвращаться","tj":"баргаштан"},
            {"no":21,"zh":"再","pinyin":"zài","pos":"adv.","uz":"keyin; shundan so‘ng","ru":"затем; потом","tj":"баъд; сипас"},
            {"no":22,"zh":"喝","pinyin":"hē","pos":"v.","uz":"ichmoq","ru":"пить","tj":"нӯшидан"},
            {"no":23,"zh":"热","pinyin":"rè","pos":"adj.","uz":"issiq; iliq","ru":"горячий; тёплый","tj":"гарм"},
            {"no":24,"zh":"水","pinyin":"shuǐ","pos":"n.","uz":"suv","ru":"вода","tj":"об"},
        ],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no":1,"section_label":"课文 1",
                "scene_zh":"王一雪给王一飞打电话，询问王一飞那边的情况。",
                "scene_en":"Wang Yixue was calling Wang Yifei to ask about the situation on her end.",
                "scene_uz":"Wang Yixue Wang Yifeiga telefon qilib, u tomondagi vaziyatni so‘ramoqda.",
                "scene_ru":"Ван Исюэ звонит Ван Ифэй и спрашивает, как там обстановка.",
                "scene_tj":"Ван Исюэ ба Ван Ифэй занг зада, вазъияти он ҷоро мепурсад.",
                "dialogue":[
                    {"speaker":"Wang Yixue","zh":"今天天气怎么样？","pinyin":"Jīntiān tiānqì zěnmeyàng?","en":"How's the weather today?","uz":"Bugun ob-havo qanday?","ru":"Какая сегодня погода?","tj":"Имрӯз обу ҳаво чӣ хел?"},
                    {"speaker":"Wang Yifei","zh":"这里的天不太好，下雨了。","pinyin":"Zhèlǐ de tiān bú tài hǎo, xià yǔ le.","en":"It's not great here. It's raining.","uz":"Bu yerda ob-havo unchalik yaxshi emas, yomg‘ir yog‘yapti.","ru":"Здесь погода не очень, идёт дождь.","tj":"Ин ҷо ҳаво он қадар хуб нест, борон меборад."},
                    {"speaker":"Wang Yixue","zh":"雨大吗？","pinyin":"Yǔ dà ma?","en":"Is it raining heavily?","uz":"Yomg‘ir kuchlimi?","ru":"Дождь сильный?","tj":"Борон сахт аст?"},
                    {"speaker":"Wang Yifei","zh":"有点儿大，我觉得很冷。","pinyin":"Yǒudiǎnr dà, wǒ juéde hěn lěng.","en":"A bit, and I feel really cold.","uz":"Biroz kuchli, men juda sovqotyapman.","ru":"Немного сильный, и мне очень холодно.","tj":"Каме сахт аст, ман хеле сард ҳис мекунам."},
                ]
            },
            {
                "block_no":2,"section_label":"课文 2",
                "scene_zh":"在公司电梯里，王一雪和杨同乐在聊天儿。",
                "scene_en":"In the company elevator, Wang Yixue and Yang Tongle were chatting.",
                "scene_uz":"Kompaniya liftida Wang Yixue va Yang Tongle suhbatlashmoqda.",
                "scene_ru":"В лифте компании Ван Исюэ и Ян Тунлэ разговаривают.",
                "scene_tj":"Дар лифти ширкат Ван Исюэ ва Ян Тунлэ суҳбат мекунанд.",
                "dialogue":[
                    {"speaker":"Wang Yixue","zh":"昨天下雪了。","pinyin":"Zuótiān xià xuě le.","en":"It snowed yesterday.","uz":"Kecha qor yog‘di.","ru":"Вчера шёл снег.","tj":"Дирӯз барф борид."},
                    {"speaker":"Yang Tongle","zh":"是的，太冷了。","pinyin":"Shì de, tài lěng le.","en":"Yes, it was so cold.","uz":"Ha, juda sovuq edi.","ru":"Да, было очень холодно.","tj":"Ҳа, хеле сард буд."},
                    {"speaker":"Wang Yixue","zh":"你昨天没来公司，生病了？","pinyin":"Nǐ zuótiān méi lái gōngsī, shēngbìng le?","en":"You didn't come to the company yesterday. Were you feeling unwell?","uz":"Kecha kompaniyaga kelmading, kasal bo‘ldingmi?","ru":"Ты вчера не пришёл на работу, заболел?","tj":"Дирӯз ба ширкат наомадӣ, бемор шудӣ?"},
                    {"speaker":"Yang Tongle","zh":"对，我昨天去医院看病了。","pinyin":"Duì, wǒ zuótiān qù yīyuàn kànbìng le.","en":"Yes, I went to the hospital to see a doctor.","uz":"Ha, kecha kasalxonaga shifokorga ko‘ringani bordim.","ru":"Да, вчера я ходил в больницу к врачу.","tj":"Ҳа, дирӯз ба беморхона назди духтур рафтам."},
                ]
            },
            {
                "block_no":3,"section_label":"课文 3",
                "scene_zh":"昨天在医院，医生给杨同乐看病。",
                "scene_en":"Yesterday at the hospital, the doctor examined Yang Tongle.",
                "scene_uz":"Kecha kasalxonada shifokor Yang Tongleni ko‘rikdan o‘tkazdi.",
                "scene_ru":"Вчера в больнице врач осматривал Ян Тунлэ.",
                "scene_tj":"Дирӯз дар беморхона духтур Ян Тунлэро муоина кард.",
                "dialogue":[
                    {"speaker":"Yang Tongle","zh":"医生，我病了。","pinyin":"Yīshēng, wǒ bìng le.","en":"Doctor, I'm not feeling well.","uz":"Doktor, men kasal bo‘ldim.","ru":"Доктор, я заболел.","tj":"Духтур, ман бемор шудам."},
                    {"speaker":"Dr. Hu","zh":"我看看。你觉得怎么样？","pinyin":"Wǒ kànkan. Nǐ juéde zěnmeyàng?","en":"Let me take a look. How are you feeling?","uz":"Ko‘rib qo‘yay. O‘zingni qanday his qilyapsan?","ru":"Давайте посмотрю. Как вы себя чувствуете?","tj":"Бигзор бинам. Худатонро чӣ хел ҳис мекунед?"},
                    {"speaker":"Yang Tongle","zh":"我很冷。","pinyin":"Wǒ hěn lěng.","en":"I feel very cold.","uz":"Juda sovqotyapman.","ru":"Мне очень холодно.","tj":"Ман хеле сард ҳис мекунам."},
                    {"speaker":"Dr. Hu","zh":"好的，吃一点儿药，今天休息半天吧。","pinyin":"Hǎo de, chī yìdiǎnr yào, jīntiān xiūxi bàn tiān ba.","en":"Alright. Take some medicine and rest for half a day today.","uz":"Xo‘p, biroz dori iching, bugun yarim kun dam oling.","ru":"Хорошо, примите немного лекарства и сегодня отдохните полдня.","tj":"Хуб, каме дору гиред ва имрӯз ним рӯз истироҳат кунед."},
                    {"speaker":"Yang Tongle","zh":"好的。","pinyin":"Hǎo de.","en":"OK.","uz":"Xo‘p.","ru":"Хорошо.","tj":"Хуб."},
                    {"speaker":"Dr. Hu","zh":"回家后再喝些热水。","pinyin":"Huí jiā hòu zài hē xiē rè shuǐ.","en":"Make sure to drink some warm water after you get home.","uz":"Uyga qaytgach, keyin biroz iliq suv iching.","ru":"После возвращения домой выпейте тёплой воды.","tj":"Баъди ба хона баргаштан, каме оби гарм нӯшед."},
                ]
            },
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no":1,"title_zh":"非主谓句","title_uz":"Ega-kesimi ajralmagan gap","title_ru":"Нерасчленённое предложение","title_tj":"Ҷумлаи бе мубтадо-хабар",
                "rule_zh":"非主谓句是由词或短语构成、不分主语和谓语的句子，口语中常用。",
                "rule_en":"Non-subject-predicate sentences are composed of words or phrases without distinct subjects or predicates and are commonly used in colloquial speech.",
                "rule_uz":"Bunday gap so‘z yoki iboradan tuziladi, ega va kesimga ajratilmaydi va og‘zaki nutqda ko‘p ishlatiladi.",
                "rule_ru":"Такие предложения состоят из слова или словосочетания без чёткого подлежащего и сказуемого и часто употребляются в разговорной речи.",
                "rule_tj":"Ин гуна ҷумла аз калима ё ибора сохта шуда, мубтадо ва хабар ба таври равшан ҷудо намешаванд ва дар гуфтор бисёр истифода мешаванд.",
                "examples":[
                    {"zh":"下雨了。","pinyin":"Xià yǔ le.","uz":"Yomg‘ir yog‘di.","ru":"Пошёл дождь.","tj":"Борон борид."},
                    {"zh":"下雪了。","pinyin":"Xià xuě le.","uz":"Qor yog‘di.","ru":"Пошёл снег.","tj":"Барф борид."},
                    {"zh":"真漂亮！","pinyin":"Zhēn piàoliang!","uz":"Juda chiroyli!","ru":"Очень красиво!","tj":"Хеле зебо!"},
                ]
            },
            {
                "no":2,"title_zh":"语气助词“了（1）”","title_uz":"Modal yuklama “了（1）”","title_ru":"Модальная частица “了（1）”","title_tj":"Ҳиссачаи модалии “了（1）”",
                "rule_zh":"“了（1）”位于句子末尾或句中停顿处，表示有变化或出现新情况。否定回答时用“没”，句末不用“了”。",
                "rule_en":"The modal particle “了（1）” is placed at the end of a sentence or at a pause within it to indicate a change or a new situation. Negative responses use “没” and omit “了” at the end.",
                "rule_uz":"“了（1）” gap oxirida yoki pauza joyida kelib holat o‘zgargani yoki yangi vaziyat paydo bo‘lganini bildiradi. Inkor javobida 没 ishlatiladi va oxirida 了 bo‘lmaydi.",
                "rule_ru":"“了（1）” ставится в конце предложения или перед паузой и показывает изменение/новую ситуацию. В отрицательном ответе используется 没, а 了 в конце не ставится.",
                "rule_tj":"“了（1）” дар охири ҷумла ё ҷойи таваққуф омада, тағйир ё вазъияти навро нишон медиҳад. Дар ҷавоби инкорӣ 没 истифода мешавад ва 了 дар охир намеояд.",
                "examples":[
                    {"zh":"下雨了。","pinyin":"Xià yǔ le.","uz":"Yomg‘ir yog‘di.","ru":"Пошёл дождь.","tj":"Борон борид."},
                    {"zh":"十二点了，吃午饭吧。","pinyin":"Shí'èr diǎn le, chī wǔfàn ba.","uz":"Soat 12 bo‘ldi, tushlik qilaylik.","ru":"Уже 12 часов, давай пообедаем.","tj":"Соат 12 шуд, биёед нисфирӯзӣ хӯрем."},
                    {"zh":"弟弟起床了吗？没起床呢。","pinyin":"Dìdi qǐchuáng le ma? Méi qǐchuáng ne.","uz":"Uka turdimi? Yo‘q, hali turmadi.","ru":"Младший брат встал? Нет, ещё не встал.","tj":"Бародари хурдӣ хест? Не, ҳоло нахестааст."},
                ]
            },
            {
                "no":3,"title_zh":"“太……了”格式","title_uz":"“太……了” qolipi","title_ru":"Конструкция “太……了”","title_tj":"Қолаби “太……了”",
                "rule_zh":"“太……了”用在感叹程度很高或很深。",
                "rule_en":"The “太……了” pattern expresses a very high or intense degree of exclamation.",
                "rule_uz":"“太……了” juda yuqori darajani hissiy tarzda ta’kidlash uchun ishlatiladi.",
                "rule_ru":"“太……了” выражает очень высокую или сильную степень восклицания.",
                "rule_tj":"“太……了” дараҷаи хеле баланд ё пурзӯрро бо оҳанги таъкидӣ ифода мекунад.",
                "examples":[
                    {"zh":"太冷了！","pinyin":"Tài lěng le!","uz":"Juda sovuq!","ru":"Очень холодно!","tj":"Хеле сард!"},
                    {"zh":"这个杯子太小了。","pinyin":"Zhège bēizi tài xiǎo le.","uz":"Bu piyola juda kichik.","ru":"Эта чашка слишком маленькая.","tj":"Ин пиёла хеле хурд аст."},
                    {"zh":"我们今天太高兴了！","pinyin":"Wǒmen jīntiān tài gāoxìng le!","uz":"Bugun juda xursandmiz!","ru":"Мы сегодня очень рады!","tj":"Мо имрӯз хеле хурсандем!"},
                ]
            }
        ],
        ensure_ascii=False,
    ),
    "usage_notes_json": json.dumps(
        [
            {
                "topic":"看看",
                "zh":"“看看”是“看”的重叠式，表示动作时间短。",
                "en":"“看看” is the reduplicated form of “看”, indicating a brief action.",
                "uz":"“看看” — “看” fe’lining takroriy shakli bo‘lib, harakat qisqa davom etishini bildiradi.",
                "ru":"“看看” — удвоенная форма “看”, обозначающая кратковременное действие.",
                "tj":"“看看” шакли такрории “看” буда, кӯтоҳ будани амалро нишон медиҳад.",
            },
            {
                "topic":"热水",
                "zh":"中国人喜欢喝热水，认为喝热水更健康。",
                "en":"Chinese people like drinking warm water and believe that it is healthier.",
                "uz":"Xitoyliklar iliq/issiq suv ichishni yoqtiradi va uni sog‘lomroq deb hisoblaydi.",
                "ru":"Китайцы любят пить тёплую воду и считают её более полезной для здоровья.",
                "tj":"Чиниҳо нӯшидани оби гармро дӯст медоранд ва онро барои саломатӣ беҳтар мешуморанд.",
            },
        ],
        ensure_ascii=False,
    ),
}
