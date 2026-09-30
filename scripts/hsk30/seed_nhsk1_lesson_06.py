from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程1",
    "pdf_path": "HSK 3.0 PDF/新HSK教程1.pdf",
    "pdf_pages": [49, 50, 51, 52, 53, 54, 55, 56, 57, 58],
    "printed_pages": [35, 36, 37, 38, 39, 40, 41, 42, 43, 44],
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk1",
    "lesson_order": 6,
    "lesson_code": "NHSK1-L06",
    "title": "你的手机号是多少？",
    "title_pinyin": "Nǐ de shǒujīhào shì duōshao?",
    "goal": json.dumps(
        {
            "uz": "Telefon raqamini tushunish va aytish; “想” bilan xohish/niyatni ifodalash; ketma-ket fe’lli gaplarda maqsad va usulni ifodalash; “怎么” bilan harakat usulini so‘rash.",
            "ru": "Понимать и называть номера телефонов; выражать желание и намерение с “想”; использовать последовательности глаголов для цели и способа действия; спрашивать о способе действия с “怎么”.",
            "tj": "Рақами телефонро фаҳмидан ва гуфтан; бо “想” хоҳишу ниятро ифода кардан; ҷумлаҳои пайдарпайи феълӣ барои мақсад ва тарзи амал; бо “怎么” тарзи амалро пурсидан.",
        },
        ensure_ascii=False,
    ),
    "intro_text": json.dumps(
        {
            "uz": "Dars telefon raqami, supermarketga borish va kechki ovqat rejasiga oid uchta dialog orqali “想”, ketma-ket fe’lli gap va “怎么” ni o‘rgatadi.",
            "ru": "Урок через три диалога о номере телефона, походе в супермаркет и планах на ужин вводит “想”, серийные глагольные конструкции и “怎么”.",
            "tj": "Дарс тавассути се гуфтугӯ дар бораи рақами телефон, рафтан ба супермаркет ва нақшаи шом “想”, ҷумлаҳои пайдарпайи феълӣ ва “怎么”-ро меомӯзонад.",
        },
        ensure_ascii=False,
    ),
    "vocabulary_json": json.dumps(
        [
            {"no":1,"zh":"手机","pinyin":"shǒujī","pos":"n.","uz":"mobil telefon","ru":"мобильный телефон","tj":"телефони мобилӣ"},
            {"no":2,"zh":"电话","pinyin":"diànhuà","pos":"n.","uz":"telefon; qo‘ng‘iroq","ru":"телефон; звонок","tj":"телефон; занг"},
            {"no":3,"zh":"号","pinyin":"hào","pos":"n.","uz":"raqam","ru":"номер","tj":"рақам"},
            {"no":4,"zh":"明天","pinyin":"míngtiān","pos":"n.","uz":"ertaga","ru":"завтра","tj":"фардо"},
            {"no":5,"zh":"去","pinyin":"qù","pos":"v.","uz":"bormoq","ru":"идти; ехать","tj":"рафтан"},
            {"no":6,"zh":"哪儿","pinyin":"nǎr","pos":"pron.","uz":"qayer","ru":"где; куда","tj":"куҷо"},
            {"no":7,"zh":"想","pinyin":"xiǎng","pos":"mod.","uz":"xohlamoq; niyat qilmoq","ru":"хотеть; собираться","tj":"хостан; ният кардан"},
            {"no":8,"zh":"超市","pinyin":"chāoshì","pos":"n.","uz":"supermarket","ru":"супермаркет","tj":"супермаркет"},
            {"no":9,"zh":"买","pinyin":"mǎi","pos":"v.","uz":"sotib olmoq","ru":"покупать","tj":"харидан"},
            {"no":10,"zh":"东西","pinyin":"dōngxi","pos":"n.","uz":"narsa; buyum","ru":"вещь; вещи","tj":"чиз; ашё"},
            {"no":11,"zh":"些","pinyin":"xiē","pos":"m.","uz":"bir oz; bir necha","ru":"немного; несколько","tj":"каме; чанд"},
            {"no":12,"zh":"牛奶","pinyin":"niúnǎi","pos":"n.","uz":"sut","ru":"молоко","tj":"шир"},
            {"no":13,"zh":"吃","pinyin":"chī","pos":"v.","uz":"yemoq","ru":"есть","tj":"хӯрдан"},
            {"no":14,"zh":"晚饭","pinyin":"wǎnfàn","pos":"n.","uz":"kechki ovqat","ru":"ужин","tj":"хӯроки шом"},
            {"no":15,"zh":"那边","pinyin":"nàbian","pos":"pron.","uz":"u yer; o‘sha tomon","ru":"там; та сторона","tj":"он ҷо; он тараф"},
            {"no":16,"zh":"包子","pinyin":"bāozi","pos":"n.","uz":"bug‘da pishirilgan bulochka","ru":"баоцзы; булочка с начинкой","tj":"баоцзы; кулчаи буғӣ"},
            {"no":17,"zh":"非常","pinyin":"fēicháng","pos":"adv.","uz":"juda; nihoyatda","ru":"очень; чрезвычайно","tj":"хеле; ниҳоят"},
            {"no":18,"zh":"好吃","pinyin":"hǎochī","pos":"adj.","uz":"mazali","ru":"вкусный","tj":"бомаза"},
            {"no":19,"zh":"米饭","pinyin":"mǐfàn","pos":"n.","uz":"pishirilgan guruch","ru":"варёный рис","tj":"биринҷи пухта"},
            {"no":20,"zh":"怎么","pinyin":"zěnme","pos":"pron.","uz":"qanday; qanday qilib","ru":"как; каким образом","tj":"чӣ тавр"},
            {"no":21,"zh":"坐","pinyin":"zuò","pos":"v.","uz":"transportda bormoq; o‘tirmoq","ru":"ехать на; сидеть","tj":"бо нақлиёт рафтан; нишастан"},
            {"no":22,"zh":"出租车","pinyin":"chūzūchē","pos":"n.","uz":"taksi","ru":"такси","tj":"таксӣ"},
        ],
        ensure_ascii=False,
    ),
    "proper_nouns_json": json.dumps(
        [{"zh":"西安饭店","pinyin":"Xī'ān Fàndiàn","en":"Xi'an Restaurant","uz":"Xi’an restorani","ru":"ресторан «Сиань»","tj":"тарабхонаи «Сиан»"}],
        ensure_ascii=False,
    ),
    "dialogue_json": json.dumps(
        [
            {
                "block_no":1,"section_label":"课文 1",
                "scene_zh":"在校园里，李文向白家月要手机号。",
                "scene_en":"On campus, Li Wen was asking Bai Jiayue for her cell phone number.",
                "scene_uz":"Kampusda Li Wen Bai Jiayuedan telefon raqamini so‘ramoqda.",
                "scene_ru":"В кампусе Ли Вэнь спрашивает у Бай Цзяюэ номер мобильного телефона.",
                "scene_tj":"Дар кампус Ли Вэн аз Бай Ҷяюэ рақами телефонашро мепурсад.",
                "dialogue":[
                    {"speaker":"Li Wen","zh":"家月，你的手机号是多少？","pinyin":"Jiāyuè, nǐ de shǒujīhào shì duōshao?","en":"Jiayue, what's your cell phone number?","uz":"Jiayue, mobil raqaming nechchi?","ru":"Цзяюэ, какой у тебя номер мобильного?","tj":"Ҷяюэ, рақами мобилиат чанд аст?"},
                    {"speaker":"Bai Jiayue","zh":"我的手机号是+33 601493190。","pinyin":"Wǒ de shǒujīhào shì +33 601493190.","en":"My cell phone number is +33 601493190.","uz":"Mening mobil raqamim +33 601493190.","ru":"Мой номер мобильного +33 601493190.","tj":"Рақами мобилии ман +33 601493190 аст."},
                    {"speaker":"Li Wen","zh":"我的手机号是+86 13552721160。","pinyin":"Wǒ de shǒujīhào shì +86 13552721160.","en":"My cell phone number is +86 13552721160.","uz":"Mening mobil raqamim +86 13552721160.","ru":"Мой номер мобильного +86 13552721160.","tj":"Рақами мобилии ман +86 13552721160 аст."},
                    {"speaker":"Bai Jiayue","zh":"好的。","pinyin":"Hǎo de.","en":"Alright.","uz":"Xo‘p.","ru":"Хорошо.","tj":"Хуб."},
                ]
            },
            {
                "block_no":2,"section_label":"课文 2",
                "scene_zh":"在教室里，下课后，白家月和陈天中在聊天儿。",
                "scene_en":"After class, Bai Jiayue and Chen Tianzhong were chatting in the classroom.",
                "scene_uz":"Darsdan keyin sinfda Bai Jiayue va Chen Tianzhong suhbatlashmoqda.",
                "scene_ru":"После занятия Бай Цзяюэ и Чэнь Тяньчжун разговаривают в аудитории.",
                "scene_tj":"Пас аз дарс Бай Ҷяюэ ва Чэн Тянҷун дар синф суҳбат мекунанд.",
                "dialogue":[
                    {"speaker":"Chen Tianzhong","zh":"家月，明天你去哪儿？","pinyin":"Jiāyuè, míngtiān nǐ qù nǎr?","en":"Jiayue, where are you going tomorrow?","uz":"Jiayue, ertaga qayerga borasan?","ru":"Цзяюэ, куда ты пойдёшь завтра?","tj":"Ҷяюэ, фардо ба куҷо меравӣ?"},
                    {"speaker":"Bai Jiayue","zh":"我想去超市买东西。","pinyin":"Wǒ xiǎng qù chāoshì mǎi dōngxi.","en":"I want to go to the supermarket to buy groceries.","uz":"Men supermarketga narsa sotib olish uchun bormoqchiman.","ru":"Я хочу пойти в супермаркет купить продукты.","tj":"Ман мехоҳам ба супермаркет рафта чиз харам."},
                    {"speaker":"Chen Tianzhong","zh":"你去超市买什么？","pinyin":"Nǐ qù chāoshì mǎi shénme?","en":"What are you going to buy at the supermarket?","uz":"Supermarketga nima sotib olish uchun borasan?","ru":"Что ты собираешься купить в супермаркете?","tj":"Дар супермаркет чӣ мехарӣ?"},
                    {"speaker":"Bai Jiayue","zh":"我想买些牛奶。","pinyin":"Wǒ xiǎng mǎi xiē niúnǎi.","en":"I want to buy some milk.","uz":"Men biroz sut sotib olmoqchiman.","ru":"Я хочу купить немного молока.","tj":"Ман мехоҳам каме шир харам."},
                ]
            },
            {
                "block_no":3,"section_label":"课文 3",
                "scene_zh":"在家里，王一雪全家在讨论周末晚餐安排。",
                "scene_en":"At home, Wang Yixue's family was discussing their plans for the weekend dinner.",
                "scene_uz":"Uyda Wang Yixue oilasi dam olish kunidagi kechki ovqat rejasini muhokama qilmoqda.",
                "scene_ru":"Дома семья Ван Исюэ обсуждает планы на ужин в выходной.",
                "scene_tj":"Дар хона оилаи Ван Исюэ нақшаи хӯроки шоми рӯзҳои истироҳатро муҳокима мекунад.",
                "dialogue":[
                    {"speaker":"Wang Yixue","zh":"星期天我们去哪儿吃晚饭？","pinyin":"Xīngqītiān wǒmen qù nǎr chī wǎnfàn?","en":"Where are we going for dinner on Sunday?","uz":"Yakshanba kuni kechki ovqatni qayerda yeymiz?","ru":"Куда мы пойдём ужинать в воскресенье?","tj":"Рӯзи якшанбе барои шом ба куҷо меравем?"},
                    {"speaker":"Liu Ming","zh":"我还想去西安饭店。","pinyin":"Wǒ hái xiǎng qù Xī'ān Fàndiàn.","en":"I'd like to go to Xi'an Restaurant again.","uz":"Men yana Xi’an restoraniga bormoqchiman.","ru":"Я снова хочу пойти в ресторан «Сиань».","tj":"Ман боз мехоҳам ба тарабхонаи «Сиан» равам."},
                    {"speaker":"Liu Xiaoxue","zh":"那边的包子非常好吃，我想吃包子。","pinyin":"Nàbian de bāozi fēicháng hǎochī, wǒ xiǎng chī bāozi.","en":"The steamed stuffed buns there are very delicious—I’d love to eat some.","uz":"U yerdagi baozi juda mazali, men baozi yegim keladi.","ru":"Баоцзы там очень вкусные, я хочу поесть баоцзы.","tj":"Баоцзыи он ҷо хеле болаззат аст, ман мехоҳам баоцзы хӯрам."},
                    {"speaker":"Liu Ming","zh":"妈妈，晚饭吃米饭，不想吃包子。","pinyin":"Māma, wǎnfàn chī mǐfàn, bù xiǎng chī bāozi.","en":"Mom, I'd rather have rice—not steamed stuffed buns.","uz":"Oyi, kechki ovqatga guruch yeyman, baozi yegim kelmaydi.","ru":"Мама, на ужин я хочу рис, не хочу баоцзы.","tj":"Оча, барои шом биринҷ мехӯрам, баоцзы хӯрдан намехоҳам."},
                    {"speaker":"Wang Yixue","zh":"好的。我们怎么去？","pinyin":"Hǎo de. Wǒmen zěnme qù?","en":"Alright. How should we get there?","uz":"Xo‘p. Qanday boramiz?","ru":"Хорошо. Как мы туда поедем?","tj":"Хуб. Чӣ тавр меравем?"},
                    {"speaker":"Liu Ming","zh":"坐出租车去。","pinyin":"Zuò chūzūchē qù.","en":"Let's take a taxi.","uz":"Taksida boramiz.","ru":"Поедем на такси.","tj":"Бо таксӣ меравем."},
                ]
            },
        ],
        ensure_ascii=False,
    ),
    "grammar_json": json.dumps(
        [
            {
                "no":1,"title_zh":"能愿动词“想”","title_uz":"Modal fe’l “想”","title_ru":"Модальный глагол “想”","title_tj":"Феъли модалии “想”",
                "rule_zh":"“想”用在动词前，表示愿望、打算。",
                "rule_en":"“想” is placed before a verb to indicate desire or intention.",
                "rule_uz":"“想” fe’l oldidan kelib xohish yoki niyatni bildiradi.",
                "rule_ru":"“想” ставится перед глаголом и выражает желание или намерение.",
                "rule_tj":"“想” пеш аз феъл омада, хоҳиш ё ниятро ифода мекунад.",
                "examples":[
                    {"zh":"我想去超市。","pinyin":"Wǒ xiǎng qù chāoshì.","uz":"Men supermarketga bormoqchiman.","ru":"Я хочу пойти в супермаркет.","tj":"Ман мехоҳам ба супермаркет равам."},
                    {"zh":"我哥哥不想休息。","pinyin":"Wǒ gēge bù xiǎng xiūxi.","uz":"Akam dam olishni xohlamaydi.","ru":"Мой старший брат не хочет отдыхать.","tj":"Бародари калонам истироҳат кардан намехоҳад."},
                ]
            },
            {
                "no":2,"title_zh":"连动句（1）","title_uz":"Ketma-ket fe’lli gap (1)","title_ru":"Серийная глагольная конструкция (1)","title_tj":"Ҷумлаи пайдарпайи феълӣ (1)",
                "rule_zh":"连动句的谓语由两个或两个以上动词性短语构成，可表示动作目的或动作方式。",
                "rule_en":"A serial verb sentence contains two or more verbal phrases and may express the purpose or manner of an action.",
                "rule_uz":"Bunday gapda ikki yoki undan ko‘p fe’l birikmasi ketma-ket kelib, harakatning maqsadi yoki usulini bildiradi.",
                "rule_ru":"В серийной конструкции два или более глагольных сочетания следуют друг за другом и выражают цель или способ действия.",
                "rule_tj":"Дар чунин ҷумла ду ё зиёда гурӯҳи феълӣ пайи ҳам омада, мақсад ё тарзи амалро ифода мекунанд.",
                "examples":[
                    {"zh":"我想去超市买东西。","pinyin":"Wǒ xiǎng qù chāoshì mǎi dōngxi.","uz":"Men supermarketga narsa sotib olish uchun bormoqchiman.","ru":"Я хочу пойти в супермаркет купить вещи.","tj":"Ман мехоҳам ба супермаркет рафта чиз харам."},
                    {"zh":"她坐出租车去超市。","pinyin":"Tā zuò chūzūchē qù chāoshì.","uz":"U supermarketga taksida boradi.","ru":"Она едет в супермаркет на такси.","tj":"Ӯ бо таксӣ ба супермаркет меравад."},
                ]
            },
            {
                "no":3,"title_zh":"疑问代词“怎么”","title_uz":"“怎么” so‘roq olmoshi","title_ru":"Вопросительное местоимение “怎么”","title_tj":"Ҷонишини саволии “怎么”",
                "rule_zh":"“怎么”用在动词前，询问动作的方式或方法。",
                "rule_en":"“怎么” is used before a verb to ask about the manner or method of an action.",
                "rule_uz":"“怎么” fe’l oldidan kelib harakat qanday usulda bajarilishini so‘raydi.",
                "rule_ru":"“怎么” ставится перед глаголом и спрашивает о способе или методе действия.",
                "rule_tj":"“怎么” пеш аз феъл омада, тарз ё усули амалро мепурсад.",
                "examples":[
                    {"zh":"我们怎么去？","pinyin":"Wǒmen zěnme qù?","uz":"Qanday boramiz?","ru":"Как мы поедем?","tj":"Чӣ тавр меравем?"},
                    {"zh":"她怎么去超市？","pinyin":"Tā zěnme qù chāoshì?","uz":"U supermarketga qanday boradi?","ru":"Как она едет в супермаркет?","tj":"Ӯ чӣ тавр ба супермаркет меравад?"},
                ]
            }
        ],
        ensure_ascii=False,
    ),
}
