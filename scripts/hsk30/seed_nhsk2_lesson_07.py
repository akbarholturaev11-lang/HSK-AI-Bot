from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(72, 80)),
    "printed_pages": list(range(56, 64)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level":"nhsk2",
    "lesson_order":7,
    "lesson_code":"NHSK2-L07",
    "title":"他篮球打得很好",
    "title_pinyin":"Tā lánqiú dǎ de hěn hǎo",
    "goal":json.dumps({
        "uz":"“一……就……” bilan ketma-ket/tez sodir bo‘ladigan harakatlarni ifodalash; 得 orqali holat to‘ldiruvchisini ishlatish; ajraluvchi fe’l va obyektli fe’llarda holat to‘ldiruvchisi tartibini to‘g‘ri qo‘llash; sport haqida gaplashish.",
        "ru":"Выражать быстрое следование действий конструкцией “一……就……”；использовать дополнение состояния с 得; правильно строить его с разделяемыми и переходными глаголами; говорить о спорте.",
        "tj":"Бо “一……就……” пайдарпай ё зуд рух додани амалҳоро ифода кардан; пуркунандаи ҳолатро бо 得 истифода бурдан; тартиби онро бо феълҳои ҷудошаванда ва объектдор дуруст сохтани; дар бораи варзиш суҳбат кардан."
    },ensure_ascii=False),
    "intro_text":json.dumps({
        "uz":"Dars darsdan keyingi basketbol, futbol, yugurish va suzish haqidagi uch dialog hamda kundalik matni orqali 一……就…… va ikki turdagi holat to‘ldiruvchisini o‘rgatadi.",
        "ru":"Урок через три диалога о баскетболе, футболе, беге и плавании и запись в дневнике вводит 一……就…… и два типа дополнения состояния.",
        "tj":"Дарс тавассути се гуфтугӯ дар бораи баскетбол, футбол, давидан ва шиноварӣ ва матни рӯзнома 一……就…… ва ду навъи пуркунандаи ҳолатро меомӯзонад."
    },ensure_ascii=False),
    "vocabulary_json":json.dumps([
        {"no":1,"zh":"从","pinyin":"cóng","pos":"prep.","uz":"dan; ...dan boshlab","ru":"из; от","tj":"аз"},
        {"no":2,"zh":"往","pinyin":"wǎng","pos":"prep./v.","uz":"tomon; ...ga qarab bormoq","ru":"в направлении; направляться","tj":"ба сӯи; рафтан"},
        {"no":3,"zh":"跑","pinyin":"pǎo","pos":"v.","uz":"yugurmoq; chopmoq","ru":"бежать","tj":"давидан"},
        {"no":4,"zh":"打","pinyin":"dǎ","pos":"v.","uz":"o‘ynamoq (sport); urmoq","ru":"играть; ударять","tj":"бозӣ кардан; задан"},
        {"no":5,"zh":"篮球","pinyin":"lánqiú","pos":"n.","uz":"basketbol","ru":"баскетбол","tj":"баскетбол"},
        {"no":6,"zh":"运动","pinyin":"yùndòng","pos":"n./v.","uz":"sport; mashq qilmoq","ru":"спорт; заниматься","tj":"варзиш; машқ кардан"},
        {"no":7,"zh":"踢","pinyin":"tī","pos":"v.","uz":"tepmoq","ru":"пинать","tj":"лагад задан"},
        {"no":8,"zh":"足球","pinyin":"zúqiú","pos":"n.","uz":"futbol","ru":"футбол","tj":"футбол"},
        {"no":9,"zh":"球","pinyin":"qiú","pos":"n.","uz":"to‘p","ru":"мяч","tj":"тӯб"},
        {"no":10,"zh":"得","pinyin":"de","pos":"part.","uz":"fe’l/sifat bilan holat-daraja to‘ldiruvchisini bog‘lovchi yuklama","ru":"частица между глаголом/прилагательным и дополнением состояния/степени","tj":"ҳиссача байни феъл/сифат ва пуркунандаи ҳолат/дараҷа"},
        {"no":11,"zh":"跑步","pinyin":"pǎobù","pos":"v.","uz":"yugurmoq","ru":"бегать","tj":"давидан"},
        {"no":12,"zh":"游泳","pinyin":"yóuyǒng","pos":"v.","uz":"suzmoq","ru":"плавать","tj":"шино кардан"},
        {"no":13,"zh":"游","pinyin":"yóu","pos":"v.","uz":"suzmoq","ru":"плавать","tj":"шино кардан"},
        {"no":14,"zh":"爱好","pinyin":"àihào","pos":"n./v.","uz":"qiziqish; yoqtirmoq","ru":"хобби; увлекаться","tj":"шавқ; дӯст доштан"},
        {"no":15,"zh":"开始","pinyin":"kāishǐ","pos":"v./n.","uz":"boshlamoq; boshlanish","ru":"начинать; начало","tj":"оғоз кардан; оғоз"}
    ],ensure_ascii=False),
    "proper_nouns_json":json.dumps([],ensure_ascii=False),
    "dialogue_json":json.dumps([
        {"block_no":1,"section_label":"课文 1","scene_zh":"在教室，安妮和陈天中在聊天儿。","scene_uz":"Sinfda Annie va Chen Tianzhong suhbatlashmoqda.","scene_ru":"В классе Энни и Чэнь Тяньчжун разговаривают.","scene_tj":"Дар синф Энни ва Чэн Тянҷун суҳбат мекунанд.","dialogue":[
            {"speaker":"Chen Tianzhong","zh":"安妮，你是什么时候从北京回来的？","pinyin":"Ānnī, nǐ shì shénme shíhou cóng Běijīng huílái de?","uz":"Annie, sen Pekindan qachon qaytding?","ru":"Энни, когда ты вернулась из Пекина?","tj":"Энни, кай аз Пекин баргаштӣ?"},
            {"speaker":"Annie","zh":"昨天下午。天中，你怎么一下课就往外跑？","pinyin":"Zuótiān xiàwǔ. Tiānzhōng, nǐ zěnme yí xiàkè jiù wǎng wài pǎo?","uz":"Kecha tushdan keyin. Tianzhong, nega dars tugashi bilan tashqariga yugurasan?","ru":"Вчера днём. Тяньчжун, почему ты сразу после урока выбегаешь наружу?","tj":"Дирӯз баъд аз нисфирӯзӣ. Тянҷун, чаро ҳамин ки дарс тамом мешавад, ба берун медавӣ?"},
            {"speaker":"Chen Tianzhong","zh":"我跟同学说好了，一起去打篮球。","pinyin":"Wǒ gēn tóngxué shuōhǎo le, yìqǐ qù dǎ lánqiú.","uz":"Sinfdoshlar bilan kelishib qo‘ydim, birga basketbol o‘ynagani boramiz.","ru":"Я договорился с одноклассниками вместе поиграть в баскетбол.","tj":"Бо ҳамсинфон маслиҳат кардем, якҷо баскетбол бозӣ мекунем."},
            {"speaker":"Annie","zh":"我也想跟你们一起玩。","pinyin":"Wǒ yě xiǎng gēn nǐmen yìqǐ wán.","uz":"Men ham sizlar bilan birga o‘ynagim keladi.","ru":"Я тоже хочу поиграть с вами.","tj":"Ман ҳам мехоҳам бо шумо якҷо бозӣ кунам."},
            {"speaker":"Chen Tianzhong","zh":"没问题，走吧。","pinyin":"Méi wèntí, zǒu ba.","uz":"Muammo yo‘q, yur.","ru":"Без проблем, пошли.","tj":"Мушкил нест, равем."}
        ]},
        {"block_no":2,"section_label":"课文 2","scene_zh":"在校园，安妮和陈天中边走边聊。","scene_uz":"Kampusda Annie va Chen Tianzhong yurib suhbatlashmoqda.","scene_ru":"В кампусе Энни и Чэнь Тяньчжун разговаривают на ходу.","scene_tj":"Дар кампус Энни ва Чэн Тянҷун роҳравон суҳбат мекунанд.","dialogue":[
            {"speaker":"Annie","zh":"天中，你是不是很喜欢打篮球？","pinyin":"Tiānzhōng, nǐ shì bu shì hěn xǐhuan dǎ lánqiú?","uz":"Tianzhong, sen basketbol o‘ynashni juda yoqtirasanmi?","ru":"Тяньчжун, ты очень любишь играть в баскетбол?","tj":"Тянҷун, ту баскетбол бозӣ карданро хеле дӯст медорӣ?"},
            {"speaker":"Chen Tianzhong","zh":"没错。","pinyin":"Méi cuò.","uz":"To‘g‘ri.","ru":"Именно.","tj":"Дуруст."},
            {"speaker":"Annie","zh":"你还喜欢什么运动？","pinyin":"Nǐ hái xǐhuan shénme yùndòng?","uz":"Yana qaysi sportni yoqtirasan?","ru":"Какие ещё виды спорта ты любишь?","tj":"Боз кадом варзишро дӯст медорӣ?"},
            {"speaker":"Chen Tianzhong","zh":"我还喜欢踢足球，一到星期天就跟朋友们去踢球。","pinyin":"Wǒ hái xǐhuan tī zúqiú, yí dào Xīngqītiān jiù gēn péngyoumen qù tī qiú.","uz":"Futbolni ham yoqtiraman, yakshanba kelishi bilan do‘stlar bilan futbol o‘ynagani boraman.","ru":"Я ещё люблю футбол: как только наступает воскресенье, иду с друзьями играть.","tj":"Футболро ҳам дӯст медорам; ҳамин ки якшанбе шавад, бо дӯстон футбол бозӣ меравам."},
            {"speaker":"Annie","zh":"你踢得怎么样？","pinyin":"Nǐ tī de zěnmeyàng?","uz":"Qanday o‘ynaysan?","ru":"Как ты играешь?","tj":"Чӣ хел бозӣ мекунӣ?"},
            {"speaker":"Chen Tianzhong","zh":"我踢得还可以。","pinyin":"Wǒ tī de hái kěyǐ.","uz":"Yomon emas o‘ynayman.","ru":"Играю неплохо.","tj":"Бад не бозӣ мекунам."}
        ]},
        {"block_no":3,"section_label":"课文 3","scene_zh":"在校园，安妮和陈天中边走边聊。","scene_uz":"Kampusda Annie va Chen Tianzhong yurib suhbatlashmoqda.","scene_ru":"В кампусе Энни и Чэнь Тяньчжун разговаривают на ходу.","scene_tj":"Дар кампус Энни ва Чэн Тянҷун роҳравон суҳбат мекунанд.","dialogue":[
            {"speaker":"Chen Tianzhong","zh":"你篮球打得怎么样？","pinyin":"Nǐ lánqiú dǎ de zěnmeyàng?","uz":"Basketbolni qanday o‘ynaysan?","ru":"Как ты играешь в баскетбол?","tj":"Баскетболро чӣ хел бозӣ мекунӣ?"},
            {"speaker":"Annie","zh":"打得还可以。","pinyin":"Dǎ de hái kěyǐ.","uz":"Yomon emas.","ru":"Неплохо.","tj":"Бад не."},
            {"speaker":"Chen Tianzhong","zh":"跑步呢？你跑得快不快？","pinyin":"Pǎobù ne? Nǐ pǎo de kuài bu kuài?","uz":"Yugurish-chi? Tez yugurasanmi?","ru":"А бег? Ты быстро бегаешь?","tj":"Давидан чӣ? Тез медавӣ?"},
            {"speaker":"Annie","zh":"我跑得不快，也不太喜欢跑步。","pinyin":"Wǒ pǎo de bú kuài, yě bú tài xǐhuan pǎobù.","uz":"Tez yugurmayman, yugurishni ham uncha yoqtirmayman.","ru":"Я бегаю небыстро и не очень люблю бег.","tj":"Ман тез намедавам ва давиданро ҳам он қадар дӯст намедорам."},
            {"speaker":"Chen Tianzhong","zh":"那你喜欢游泳吗？","pinyin":"Nà nǐ xǐhuan yóuyǒng ma?","uz":"Unda suzishni yoqtirasanmi?","ru":"А плавать любишь?","tj":"Пас шиновариро дӯст медорӣ?"},
            {"speaker":"Annie","zh":"喜欢，但我游泳游得不快。","pinyin":"Xǐhuan, dàn wǒ yóuyǒng yóu de bú kuài.","uz":"Ha, lekin tez suzolmayman.","ru":"Люблю, но плаваю небыстро.","tj":"Дӯст медорам, аммо тез шино намекунам."}
        ]},
        {"block_no":4,"section_label":"课文 4","scene_zh":"在房间，陈天中在写日记。","scene_uz":"Xonada Chen Tianzhong kundalik yozmoqda.","scene_ru":"В комнате Чэнь Тяньчжун пишет дневник.","scene_tj":"Дар ҳуҷра Чэн Тянҷун рӯзнома менависад.","dialogue":[
            {"speaker":"Narration","zh":"我的爱好是运动。从上小学开始，我每天都跟爸爸去运动。现在我篮球打得很好，足球踢得不错，游泳游得也很快。我一有时间就去运动。","pinyin":"Wǒ de àihào shì yùndòng. Cóng shàng xiǎoxué kāishǐ, wǒ měitiān dōu gēn bàba qù yùndòng. Xiànzài wǒ lánqiú dǎ de hěn hǎo, zúqiú tī de búcuò, yóuyǒng yóu de yě hěn kuài. Wǒ yì yǒu shíjiān jiù qù yùndòng.","uz":"Mening qiziqishim sport. Boshlang‘ich maktabdan beri har kuni dadam bilan sport qilaman. Hozir basketbolni juda yaxshi, futbolni yomon emas o‘ynayman, suzishim ham tez. Vaqtim bo‘lishi bilan sport qilaman.","ru":"Моё хобби — спорт. С начальной школы я каждый день занимаюсь с папой. Сейчас я очень хорошо играю в баскетбол, неплохо в футбол и быстро плаваю. Как только есть время, иду заниматься спортом.","tj":"Шавқи ман варзиш аст. Аз мактаби ибтидоӣ ҳар рӯз бо падарам машқ мекунам. Ҳоло баскетболро хеле хуб, футболро бад не бозӣ мекунам ва тез шино мекунам. Ҳамин ки вақт дошта бошам, ба варзиш меравам."}
        ]}
    ],ensure_ascii=False),
    "grammar_json":json.dumps([
        {"no":1,"title_zh":"紧缩复句“一……就……”","title_uz":"“一……就……” ixcham qo‘shma gapi","title_ru":"Сжатое сложное предложение “一……就……”","title_tj":"Ҷумлаи фишурдаи “一……就……”","rule_zh":"紧缩复句“一……就……”表示后一动作紧跟着前一动作发生，也表示前一动作是条件和原因，后一动作是结果。主语相同时，主语在“一”或“就”前面；主语不同时，两个主语分别在“一”和“就”前面。","rule_uz":"“一……就……” ikkinchi harakat birinchidan darhol keyin sodir bo‘lishini yoki birinchi harakat shart/sabab, ikkinchisi natija ekanini bildiradi. Ega bir xil bo‘lsa ega 一 yoki 就 oldida; egalar turli bo‘lsa har biri 一 va 就 oldida keladi.","rule_ru":"“一……就……” показывает, что второе действие следует сразу за первым, либо первое является условием/причиной, а второе — результатом. При одном субъекте он ставится перед 一 или 就; при разных — каждый перед своей частью.","rule_tj":"“一……就……” нишон медиҳад, ки амали дуюм фавран пас аз якум рух медиҳад ё якум шарт/сабаб, дуюм натиҷа аст. Агар мубтадо як бошад, пеш аз 一 ё 就; агар гуногун бошад, ҳар мубтадо пеш аз қисми худ меояд.","examples":[{"zh":"你怎么一下课就往外跑？"},{"zh":"我一到家，妈妈就打来电话了。"},{"zh":"一到星期六，陈天中就跟同学去打篮球。"}]},
        {"no":2,"title_zh":"状态补语（1）","title_uz":"Holat to‘ldiruvchisi (1)","title_ru":"Дополнение состояния (1)","title_tj":"Пуркунандаи ҳолат (1)","rule_zh":"状态补语是在动词后边补充说明动作进行的状态的。基本结构：动词+得+形容词性短语。否定形式是在形容词的前面加“不”。疑问形式有三种：句尾加“吗”；动词+得+形容词+不+形容词；动词+得+怎么样。","rule_uz":"Holat to‘ldiruvchisi fe’ldan keyin harakat qanday bajarilganini ko‘rsatadi. Asosiy shakl: fe’l+得+sifatli birikma. Inkor sifat oldidan 不 bilan. Savol: 吗; V+得+Adj+不+Adj; V+得+怎么样.","rule_ru":"Дополнение состояния после глагола уточняет, как выполняется действие. Схема: глагол+得+прилагательная группа. Отрицание — 不 перед прилагательным. Вопрос: 吗; V+得+Adj+不+Adj; V+得+怎么样.","rule_tj":"Пуркунандаи ҳолат пас аз феъл тарзи иҷрои амалро мефаҳмонад. Сохтор: феъл+得+ибораи сифатӣ. Инкор бо 不 пеш аз сифат. Савол: 吗; V+得+Adj+不+Adj; V+得+怎么样.","examples":[{"zh":"我踢得还可以。"},{"zh":"他们玩得很高兴。"},{"zh":"白家月跑得不快。"},{"zh":"你跑得快吗？"},{"zh":"他来得早不早？"},{"zh":"他们玩得怎么样？"}]},
        {"no":3,"title_zh":"状态补语（2）","title_uz":"Holat to‘ldiruvchisi (2)","title_ru":"Дополнение состояния (2)","title_tj":"Пуркунандаи ҳолат (2)","rule_zh":"带状态补语的句子中，如果动词是离合词，需要重复动词性语素。如果动词有宾语，可以把宾语提前，或者重复动词。","rule_uz":"Holat to‘ldiruvchili gapda fe’l ajraluvchi so‘z bo‘lsa, fe’l morfemasi takrorlanadi. Fe’l obyekt olsa, obyektni oldinga chiqarish yoki fe’lni takrorlash mumkin.","rule_ru":"Если глагол разделяемый, его глагольный морф повторяется. Если у глагола есть объект, объект можно вынести перед глаголом либо повторить глагол.","rule_tj":"Агар феъл ҷудошаванда бошад, морфемаи феъл такрор мешавад. Агар объект дошта бошад, объектро пеш овардан ё феълро такрор кардан мумкин.","examples":[{"zh":"我游泳游得不快。"},{"zh":"你篮球打得怎么样？"},{"zh":"白家月写汉字写得很好看。"}]}
    ],ensure_ascii=False)
}
