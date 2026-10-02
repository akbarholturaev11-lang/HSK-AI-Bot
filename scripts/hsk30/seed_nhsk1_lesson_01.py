from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程1",
    "pdf_path": "HSK 3.0 PDF/新HSK教程1.pdf",
    "pdf_pages": [15, 16, 17, 18],
    "printed_pages": [1, 2, 3, 4],
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk1",
    "lesson_order": 1,
    "lesson_code": "NHSK1-L01",
    "title": "AI小语，你好！",
    "title_pinyin": "AI Xiǎoyǔ, nǐ hǎo!",
    "goal": json.dumps(
        {
            "uz": "Salomlashish, minnatdorchilik va xayrlashish uchun odobli iboralarni tushunish va ishlatish; xitoycha muloqot odobi hamda hurmat shakli 您 ni tushunish va qo'llash.",
            "ru": "Понимать и использовать вежливые выражения для приветствия, благодарности и прощания; понимать нормы китайского общения и употреблять уважительную форму 您.",
            "tj": "Ибораҳои хушмуомиларо барои салом, изҳори сипос ва хайрбод фаҳмидан ва истифода бурдан; одоби муоширати чинӣ ва шакли эҳтиромии 您-ро фаҳмидан ва ба кор бурдан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Darsda salomlashish, rahmat aytish va xayrlashish iboralari uchta qisqa dialog orqali o'rganiladi. Shuningdek, 您 hurmat shaklining ishlatilishi ko'rsatiladi.",
            "ru": "В уроке приветствие, благодарность и прощание изучаются через три коротких диалога. Также показано употребление уважительной формы 您.",
            "tj": "Дар дарс салом, изҳори сипос ва хайрбод тавассути се гуфтугӯи кӯтоҳ омӯхта мешаванд. Ҳамчунин истифодаи шакли эҳтиромии 您 нишон дода мешавад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no": 1, "zh": "你好", "pinyin": "nǐ hǎo", "pos": "phrase", "uz": "salom", "ru": "привет; здравствуйте", "tj": "салом"},
            {"no": 2, "zh": "大家", "pinyin": "dàjiā", "pos": "pron.", "uz": "hamma; barchangiz", "ru": "все; все вы", "tj": "ҳама; ҳамаи шумо"},
            {"no": 3, "zh": "好", "pinyin": "hǎo", "pos": "adj.", "uz": "yaxshi; yaxshi bo'lmoq", "ru": "хороший; хорошо", "tj": "хуб; хуб будан"},
            {"no": 4, "zh": "学生", "pinyin": "xuésheng", "pos": "n.", "uz": "o'quvchi; talaba", "ru": "ученик; студент", "tj": "хонанда; донишҷӯ"},
            {"no": 5, "zh": "们", "pinyin": "men", "pos": "suf.", "uz": "ko'plik qo'shimchasi", "ru": "суффикс множественного числа", "tj": "пасванди ҷамъ"},
            {"no": 6, "zh": "老师", "pinyin": "lǎoshī", "pos": "n.", "uz": "o'qituvchi; ustoz", "ru": "учитель; преподаватель", "tj": "омӯзгор; устод"},
            {"no": 7, "zh": "您", "pinyin": "nín", "pos": "pron.", "uz": "Siz (hurmat shakli)", "ru": "Вы (уважительная форма)", "tj": "Шумо (шакли эҳтиромӣ)"},
            {"no": 8, "zh": "你们", "pinyin": "nǐmen", "pos": "pron.", "uz": "sizlar", "ru": "вы (мн. ч.)", "tj": "шумо (ҷамъ)"},
            {"no": 9, "zh": "谢谢", "pinyin": "xièxie", "pos": "v.", "uz": "rahmat aytmoq; rahmat", "ru": "благодарить; спасибо", "tj": "ташаккур гуфтан; раҳмат"},
            {"no": 10, "zh": "不客气", "pinyin": "bú kèqi", "pos": "phrase", "uz": "arzimaydi", "ru": "не за что; пожалуйста", "tj": "марҳамат; ҳеҷ гап не"},
            {"no": 11, "zh": "同学", "pinyin": "tóngxué", "pos": "n.", "uz": "sinfdosh; kursdosh", "ru": "одноклассник; одногруппник", "tj": "ҳамсинф; ҳамкурс"},
            {"no": 12, "zh": "再见", "pinyin": "zàijiàn", "pos": "v.", "uz": "xayr; ko'rishguncha", "ru": "до свидания", "tj": "хайр; то боздид"},
        ],
        ensure_ascii=False,
    ),
    "proper_nouns_json": json.dumps(
        [{"zh": "王老师", "pinyin": "Wáng lǎoshī", "en": "Ms. Wang", "uz": "Ustoz Wang", "ru": "госпожа Ван; преподаватель Ван", "tj": "устод Ван"}],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no": 1,
                "section_label": "课文 1",
                "scene_zh": "开学第一天，在办公室里，王一飞和AI助教小语打招呼。",
                "scene_en": "On the first day of school, in the office, Wang Yifei was greeting the AI assistant Xiaoyu.",
                "scene_uz": "O'qishning birinchi kuni ofisda Wang Yifei AI yordamchi Xiaoyu bilan salomlashadi.",
                "scene_ru": "В первый учебный день в офисе Ван Ифэй здоровается с AI-помощником Сяоюй.",
                "scene_tj": "Дар рӯзи аввали таҳсил, дар идора Ван Ифэй бо ёвари AI Сяоюй салом мекунад.",
                "dialogue": [
                    {"speaker": "Wang Yifei", "zh": "AI小语，你好！", "pinyin": "AI Xiǎoyǔ, nǐ hǎo!", "en": "Hello, AI Xiaoyu!", "uz": "AI Xiaoyu, salom!", "ru": "AI Сяоюй, здравствуй!", "tj": "AI Сяоюй, салом!"},
                    {"speaker": "Xiaoyu", "zh": "王老师，你好！", "pinyin": "Wáng lǎoshī, nǐ hǎo!", "en": "Hello, Ms. Wang!", "uz": "Ustoz Wang, salom!", "ru": "Здравствуйте, госпожа Ван!", "tj": "Устод Ван, салом!"},
                ],
            },
            {
                "block_no": 2,
                "section_label": "课文 2",
                "scene_zh": "开学第一天，课堂上，学生们学习打招呼用语。",
                "scene_en": "On the first day of school, in class, the students were learning greeting expressions.",
                "scene_uz": "O'qishning birinchi kuni darsda talabalar salomlashish iboralarini o'rganadilar.",
                "scene_ru": "В первый учебный день на занятии студенты изучают выражения для приветствия.",
                "scene_tj": "Дар рӯзи аввали таҳсил, дар дарс донишҷӯён ибораҳои саломро меомӯзанд.",
                "dialogue": [
                    {"speaker": "Wang Yifei", "zh": "大家好！", "pinyin": "Dàjiā hǎo!", "en": "Hello, everyone!", "uz": "Hammaga salom!", "ru": "Здравствуйте, все!", "tj": "Салом ба ҳама!"},
                    {"speaker": "Students", "zh": "老师，您好！", "pinyin": "Lǎoshī, nín hǎo!", "en": "Hello, teacher!", "uz": "Ustoz, assalomu alaykum!", "ru": "Здравствуйте, преподаватель!", "tj": "Устод, салом!"},
                    {"speaker": "Xiaoyu", "zh": "你们好！", "pinyin": "Nǐmen hǎo!", "en": "Hello, all!", "uz": "Sizlarga salom!", "ru": "Здравствуйте!", "tj": "Ба шумо салом!"},
                    {"speaker": "Students", "zh": "你好，小语！", "pinyin": "Nǐ hǎo, Xiǎoyǔ!", "en": "Hello, Xiaoyu!", "uz": "Salom, Xiaoyu!", "ru": "Привет, Сяоюй!", "tj": "Салом, Сяоюй!"},
                ],
            },
            {
                "block_no": 3,
                "section_label": "课文 3",
                "scene_zh": "开学第一天，课堂上，学生们学习致谢语、告别语。",
                "scene_en": "On the first day of school, in class, the students were learning expressions of gratitude and farewell.",
                "scene_uz": "O'qishning birinchi kuni darsda talabalar minnatdorchilik va xayrlashish iboralarini o'rganadilar.",
                "scene_ru": "В первый учебный день на занятии студенты изучают выражения благодарности и прощания.",
                "scene_tj": "Дар рӯзи аввали таҳсил, дар дарс донишҷӯён ибораҳои сипос ва хайрбодро меомӯзанд.",
                "dialogue": [
                    {"speaker": "Students", "zh": "谢谢！", "pinyin": "Xièxie!", "en": "Thank you!", "uz": "Rahmat!", "ru": "Спасибо!", "tj": "Раҳмат!"},
                    {"speaker": "Xiaoyu", "zh": "不客气！", "pinyin": "Bú kèqi!", "en": "You're welcome!", "uz": "Arzimaydi!", "ru": "Не за что!", "tj": "Марҳамат!"},
                    {"speaker": "Wang Yifei", "zh": "同学们，再见！", "pinyin": "Tóngxuémen, zàijiàn!", "en": "Goodbye, class!", "uz": "Talabalar, xayr!", "ru": "Студенты, до свидания!", "tj": "Донишҷӯён, хайр!"},
                    {"speaker": "Students", "zh": "老师，再见！", "pinyin": "Lǎoshī, zàijiàn!", "en": "Goodbye, teacher!", "uz": "Ustoz, xayr!", "ru": "До свидания, преподаватель!", "tj": "Устод, хайр!"},
                ],
            },
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps([], ensure_ascii=False),
    "usage_notes_json": json.dumps(
        [
            {
                "topic": "您",
                "zh": "“您”，敬称，对年长者或尊敬的人使用。",
                "en": "“您” is an honorific pronoun used to address elders or individuals you respect.",
                "uz": "“您” hurmat olmoshi bo'lib, yoshi katta yoki hurmat qilinadigan kishilarga murojaatda ishlatiladi.",
                "ru": "“您” — уважительное местоимение, употребляемое при обращении к старшим или уважаемым людям.",
                "tj": "“您” ҷонишини эҳтиромӣ буда, ҳангоми муроҷиат ба калонсолон ё шахсони муҳтарам истифода мешавад.",
            }
        ],
        ensure_ascii=False,
    ),
}
