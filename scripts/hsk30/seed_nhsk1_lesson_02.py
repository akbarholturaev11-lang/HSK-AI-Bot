from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程1",
    "pdf_path": "HSK 3.0 PDF/新HSK教程1.pdf",
    "pdf_pages": [19, 20, 21, 22, 23],
    "printed_pages": [5, 6, 7, 8, 9],
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk1",
    "lesson_order": 2,
    "lesson_code": "NHSK1-L02",
    "title": "我叫李文",
    "title_pinyin": "Wǒ jiào Lǐ Wén",
    "goal": json.dumps(
        {
            "uz": "Boshqalarning o'zini tanishtirishini tushunish va xitoycha ism bilan o'zini tanishtirish; 对不起 va 没关系 orqali uzr so'rash va javob berish; xitoy tilidagi asosiy so'z tartibini tushunish.",
            "ru": "Понимать самопрезентацию собеседника и представляться с китайским именем; извиняться с 对不起 и отвечать 没关系; освоить базовый порядок слов в китайском языке.",
            "tj": "Худмуаррифии дигаронро фаҳмидан ва бо номи чинӣ худро муаррифӣ кардан; бо 对不起 узр пурсидан ва бо 没关系 ҷавоб додан; тартиби асосии калимаҳои забони чиниро аз худ кардан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars ism so'rash va aytish, xato murojaat uchun uzr so'rash hamda birinchi tanishuv vaziyatlarini uchta dialog orqali o'rgatadi.",
            "ru": "Урок через три диалога учит спрашивать и называть имя, извиняться за ошибочное обращение и знакомиться впервые.",
            "tj": "Дарс тавассути се гуфтугӯ пурсидан ва гуфтани ном, барои иштибоҳи муроҷиат узр пурсидан ва шиносоии аввалро меомӯзонад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no": 1, "zh": "请问", "pinyin": "qǐngwèn", "pos": "v.", "uz": "kechirasiz, so'rasam", "ru": "разрешите спросить; извините", "tj": "мебахшед, пурсам"},
            {"no": 2, "zh": "你", "pinyin": "nǐ", "pos": "pron.", "uz": "sen", "ru": "ты", "tj": "ту"},
            {"no": 3, "zh": "叫", "pinyin": "jiào", "pos": "v.", "uz": "deb atalmoq; ismi bo'lmoq", "ru": "зваться; называться", "tj": "ном доштан; номида шудан"},
            {"no": 4, "zh": "什么", "pinyin": "shénme", "pos": "pron.", "uz": "nima; qanday", "ru": "что; какой", "tj": "чӣ; кадом"},
            {"no": 5, "zh": "名字", "pinyin": "míngzi", "pos": "n.", "uz": "ism", "ru": "имя", "tj": "ном"},
            {"no": 6, "zh": "我", "pinyin": "wǒ", "pos": "pron.", "uz": "men; meni", "ru": "я; меня", "tj": "ман; маро"},
            {"no": 7, "zh": "不", "pinyin": "bù", "pos": "adv.", "uz": "emas; yo'q; -ma", "ru": "не; нет", "tj": "не; нест"},
            {"no": 8, "zh": "是", "pinyin": "shì", "pos": "v.", "uz": "bo'lmoq; ...dir", "ru": "быть; являться", "tj": "будан; ...аст"},
            {"no": 9, "zh": "对不起", "pinyin": "duìbuqǐ", "pos": "v.", "uz": "kechirasiz; uzr", "ru": "извините; простите", "tj": "мебахшед; узр"},
            {"no": 10, "zh": "没关系", "pinyin": "méi guānxi", "pos": "phrase", "uz": "hechqisi yo'q; mayli", "ru": "ничего страшного; всё в порядке", "tj": "ҳеҷ гап не; майлаш"},
            {"no": 11, "zh": "没事", "pinyin": "méishì", "pos": "v.", "uz": "hechqisi yo'q; muammo emas", "ru": "ничего; неважно", "tj": "ҳеҷ гап не; мушкиле нест"},
            {"no": 12, "zh": "很", "pinyin": "hěn", "pos": "adv.", "uz": "juda", "ru": "очень", "tj": "хеле"},
            {"no": 13, "zh": "高兴", "pinyin": "gāoxìng", "pos": "adj.", "uz": "xursand", "ru": "рад; счастлив", "tj": "хурсанд"},
            {"no": 14, "zh": "认识", "pinyin": "rènshi", "pos": "v.", "uz": "tanimoq; tanishmoq", "ru": "знать; знакомиться", "tj": "шинохтан; шинос шудан"},
            {"no": 15, "zh": "也", "pinyin": "yě", "pos": "adv.", "uz": "ham", "ru": "тоже; также", "tj": "ҳам"},
        ],
        ensure_ascii=False,
    ),
    "proper_nouns_json": json.dumps(
        [
            {"zh": "李文", "pinyin": "Lǐ Wén", "en": "Li Wen", "uz": "Li Wen", "ru": "Ли Вэнь", "tj": "Ли Вэн"},
            {"zh": "陈天中", "pinyin": "Chén Tiānzhōng", "en": "Chen Tianzhong", "uz": "Chen Tianzhong", "ru": "Чэнь Тяньчжун", "tj": "Чэн Тянҷун"},
            {"zh": "白家月", "pinyin": "Bái Jiāyuè", "en": "Bai Jiayue", "uz": "Bai Jiayue", "ru": "Бай Цзяюэ", "tj": "Бай Ҷяюэ"},
            {"zh": "安妮", "pinyin": "Ānnī", "en": "Annie", "uz": "Annie", "ru": "Энни", "tj": "Энни"},
        ],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no": 1,
                "section_label": "课文 1",
                "scene_zh": "在教室里，王一飞在认识学生。",
                "scene_en": "In the classroom, Wang Yifei was getting to know the students.",
                "scene_uz": "Sinfda Wang Yifei talabalar bilan tanishmoqda.",
                "scene_ru": "В аудитории Ван Ифэй знакомится со студентами.",
                "scene_tj": "Дар синф Ван Ифэй бо донишҷӯён шинос мешавад.",
                "dialogue": [
                    {"speaker": "Wang Yifei", "zh": "请问，你叫什么名字？", "pinyin": "Qǐngwèn, nǐ jiào shénme míngzi?", "en": "May I ask, what's your name?", "uz": "Kechirasiz, ismingiz nima?", "ru": "Разрешите спросить, как вас зовут?", "tj": "Мебахшед, номи шумо чист?"},
                    {"speaker": "Chen Tianzhong", "zh": "我叫陈天中。", "pinyin": "Wǒ jiào Chén Tiānzhōng.", "en": "My name is Chen Tianzhong.", "uz": "Mening ismim Chen Tianzhong.", "ru": "Меня зовут Чэнь Тяньчжун.", "tj": "Номи ман Чэн Тянҷун аст."},
                ],
            },
            {
                "block_no": 2,
                "section_label": "课文 2",
                "scene_zh": "在校园里，陈天中和白家月打招呼时认错了人。",
                "scene_en": "On campus, Chen Tianzhong greeted Bai Jiayue but mistook her for someone else.",
                "scene_uz": "Kampusda Chen Tianzhong Bai Jiayue bilan salomlashayotib uni boshqa odam deb o'ylab qoladi.",
                "scene_ru": "В кампусе Чэнь Тяньчжун здоровается с Бай Цзяюэ, но принимает её за другого человека.",
                "scene_tj": "Дар кампус Чэн Тянҷун бо Бай Ҷяюэ салом мекунад, вале ӯро бо шахси дигар иштибоҳ мегирад.",
                "dialogue": [
                    {"speaker": "Chen Tianzhong", "zh": "你好，安妮！", "pinyin": "Nǐ hǎo, Ānnī!", "en": "Hello, Annie!", "uz": "Salom, Annie!", "ru": "Привет, Энни!", "tj": "Салом, Энни!"},
                    {"speaker": "Bai Jiayue", "zh": "你好，陈天中！我不是安妮，我是白家月。", "pinyin": "Nǐ hǎo, Chén Tiānzhōng! Wǒ bú shì Ānnī, wǒ shì Bái Jiāyuè.", "en": "Hello, Chen Tianzhong! I'm not Annie—I'm Bai Jiayue.", "uz": "Salom, Chen Tianzhong! Men Annie emasman, men Bai Jiayueman.", "ru": "Привет, Чэнь Тяньчжун! Я не Энни, я Бай Цзяюэ.", "tj": "Салом, Чэн Тянҷун! Ман Энни нестам, ман Бай Ҷяюэ ҳастам."},
                    {"speaker": "Chen Tianzhong", "zh": "对不起！", "pinyin": "Duìbuqǐ!", "en": "Sorry!", "uz": "Kechirasiz!", "ru": "Извините!", "tj": "Мебахшед!"},
                    {"speaker": "Bai Jiayue", "zh": "没关系！", "pinyin": "Méi guānxi!", "en": "It's okay!", "uz": "Hechqisi yo'q!", "ru": "Ничего страшного!", "tj": "Ҳеҷ гап не!"},
                ],
            },
            {
                "block_no": 3,
                "section_label": "课文 3",
                "scene_zh": "在校园里，李文和白家月第一次相遇。",
                "scene_en": "Li Wen and Bai Jiayue met for the first time on campus.",
                "scene_uz": "Kampusda Li Wen va Bai Jiayue birinchi marta uchrashadilar.",
                "scene_ru": "В кампусе Ли Вэнь и Бай Цзяюэ впервые встречаются.",
                "scene_tj": "Дар кампус Ли Вэн ва Бай Ҷяюэ бори аввал вомехӯранд.",
                "dialogue": [
                    {"speaker": "Li Wen", "zh": "你好！我叫李文。", "pinyin": "Nǐ hǎo! Wǒ jiào Lǐ Wén.", "en": "Hello! My name is Li Wen.", "uz": "Salom! Mening ismim Li Wen.", "ru": "Привет! Меня зовут Ли Вэнь.", "tj": "Салом! Номи ман Ли Вэн аст."},
                    {"speaker": "Bai Jiayue", "zh": "你好！我叫白家月。", "pinyin": "Nǐ hǎo! Wǒ jiào Bái Jiāyuè.", "en": "Hello! My name is Bai Jiayue.", "uz": "Salom! Mening ismim Bai Jiayue.", "ru": "Привет! Меня зовут Бай Цзяюэ.", "tj": "Салом! Номи ман Бай Ҷяюэ аст."},
                    {"speaker": "Li Wen", "zh": "很高兴认识你。", "pinyin": "Hěn gāoxìng rènshi nǐ.", "en": "Nice to meet you.", "uz": "Siz bilan tanishganimdan xursandman.", "ru": "Рад познакомиться с вами.", "tj": "Аз шиносоӣ бо шумо хурсанд ҳастам."},
                    {"speaker": "Bai Jiayue", "zh": "认识你我也很高兴。", "pinyin": "Rènshi nǐ wǒ yě hěn gāoxìng.", "en": "Nice to meet you too.", "uz": "Men ham siz bilan tanishganimdan xursandman.", "ru": "Я тоже рада знакомству.", "tj": "Ман ҳам аз шиносоӣ бо шумо хурсанд ҳастам."},
                ],
            },
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no": 1,
                "title_zh": "汉语的基本语序",
                "title_uz": "Xitoy tilidagi asosiy so'z tartibi",
                "title_ru": "Базовый порядок слов в китайском языке",
                "title_tj": "Тартиби асосии калимаҳо дар забони чинӣ",
                "rule_zh": "汉语的基本语序是：主语+谓语+宾语。例如：我（主语）叫（谓语）陈天中（宾语）。",
                "rule_en": "The basic word order in Chinese is: Subject + Predicate + Object.",
                "rule_uz": "Xitoy tilidagi asosiy tartib: ega + kesim + to'ldiruvchi.",
                "rule_ru": "Базовый порядок слов: подлежащее + сказуемое + дополнение.",
                "rule_tj": "Тартиби асосӣ: мубтадо + хабар + пуркунанда.",
                "examples": [
                    {"zh": "你叫什么名字？", "pinyin": "Nǐ jiào shénme míngzi?", "uz": "Sening isming nima?", "ru": "Как тебя зовут?", "tj": "Номи ту чист?"},
                    {"zh": "我叫白家月。", "pinyin": "Wǒ jiào Bái Jiāyuè.", "uz": "Mening ismim Bai Jiayue.", "ru": "Меня зовут Бай Цзяюэ.", "tj": "Номи ман Бай Ҷяюэ аст."},
                    {"zh": "我是学生。", "pinyin": "Wǒ shì xuésheng.", "uz": "Men talabaman.", "ru": "Я студент.", "tj": "Ман донишҷӯ ҳастам."},
                ],
            }
        ],
        ensure_ascii=False,
    ),
    "usage_notes_json": json.dumps(
        [
            {"topic": "请问", "zh": "敬辞，请求对方回答问题。", "en": "A polite expression used to request someone to answer a question.", "uz": "Savol berishdan oldin muloyim murojaat sifatida ishlatiladi.", "ru": "Вежливое выражение перед вопросом или просьбой ответить.", "tj": "Ибораи хушмуомила пеш аз савол ё дархости ҷавоб."},
            {"topic": "没事", "zh": "在口语中也说“没事”或“没事没事”。", "en": "In colloquial speech, people also say 没事 or 没事没事.", "uz": "Og'zaki nutqda 没事 yoki 没事没事 ham ishlatiladi.", "ru": "В разговорной речи также говорят 没事 или 没事没事.", "tj": "Дар гуфтори ҳаррӯза 没事 ё 没事没事 ҳам истифода мешавад."},
            {"topic": "中国人的姓名", "zh": "中国人的姓名：姓+名", "en": "Chinese names: surname + given name.", "uz": "Xitoycha ism: familiya + shaxsiy ism.", "ru": "Китайское имя: фамилия + личное имя.", "tj": "Номи чинӣ: насаб + ном."},
        ],
        ensure_ascii=False,
    ),
}
