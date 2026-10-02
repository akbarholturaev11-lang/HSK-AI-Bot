from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(137, 146)),
    "printed_pages": list(range(121, 130)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level":"nhsk2",
    "lesson_order":14,
    "lesson_code":"NHSK2-L14",
    "title":"一个人过年多没意思啊",
    "title_pinyin":"Yí ge rén guònián duō méi yìsi a",
    "goal":json.dumps({
        "uz":"“着” bilan mavjudlik gapini tuzish; undov gapida “多” bilan yuqori darajani ifodalash; qo‘shma yo‘nalish to‘ldiruvchilarini va obyektning joylashuvini to‘g‘ri ishlatish; tanishtirish va uy-joy haqida gaplashish.",
        "ru":"Строить экзистенциальные предложения с “着”; выражать высокую степень через “多” в восклицательных предложениях; правильно использовать составные направительные дополнения и позицию объекта; говорить о знакомстве и жилье.",
        "tj":"Бо “着” ҷумлаи мавҷудият сохтан; дар ҷумлаи хитобӣ бо “多” дараҷаи баландро ифода кардан; пуркунандаи мураккаби самт ва ҷойи объектро дуруст истифода бурдан; дар бораи шиносоӣ ва манзил суҳбат кардан."
    },ensure_ascii=False),
    "intro_text":json.dumps({
        "uz":"Dars Wang Yifeining yigit do‘sti bilan uchrashuv, qo‘shnilar, uy va kundalik matni orqali mavjudlik gapi, daraja ravishi 多 va qo‘shma yo‘nalish to‘ldiruvchisini o‘rgatadi.",
        "ru":"Урок через встречу с молодым человеком Ван Ифэй, соседей, жильё и дневниковую запись вводит экзистенциальное предложение, наречие степени 多 и составное направительное дополнение.",
        "tj":"Дарс тавассути вохӯрӣ бо дӯстписари Ван Ифэй, ҳамсояҳо, хона ва навиштаи рӯзнома ҷумлаи мавҷудият, зарфи дараҷаи 多 ва пуркунандаи мураккаби самтро меомӯзонад."
    },ensure_ascii=False),
    "vocabulary_json":json.dumps([
        {"no":1,"zh":"站","pinyin":"zhàn","pos":"v.","uz":"turmoq","ru":"стоять","tj":"истодан"},
        {"no":2,"zh":"包","pinyin":"bāo","pos":"n./v./m.","uz":"sumka; o‘ram; o‘ramoq","ru":"сумка; пакет; заворачивать","tj":"халта; баста; бастан"},
        {"no":3,"zh":"过年","pinyin":"guònián","pos":"v.","uz":"Bahor bayramini/Yangi yilni nishonlamoq","ru":"праздновать Китайский Новый год","tj":"Соли нави чиниро ҷашн гирифтан"},
        {"no":4,"zh":"没意思","pinyin":"méi yìsi","pos":"adj.","uz":"zerikarli; qiziq emas","ru":"скучно; неинтересно","tj":"дилгир; бе шавқ"},
        {"no":5,"zh":"位","pinyin":"wèi","pos":"m.","uz":"odamlar uchun hurmat hisob so‘zi","ru":"уважительное счётное слово для людей","tj":"воҳиди эҳтиромии ҳисоб барои одам"},
        {"no":6,"zh":"前面","pinyin":"qiánmian","pos":"n.","uz":"old tomon","ru":"впереди; передняя сторона","tj":"пеш; тарафи пеш"},
        {"no":7,"zh":"房子","pinyin":"fángzi","pos":"n.","uz":"uy; xona-joy","ru":"дом; жильё","tj":"хона; манзил"},
        {"no":8,"zh":"小孩儿","pinyin":"xiǎoháir","pos":"n.","uz":"bola","ru":"ребёнок","tj":"кӯдак"},
        {"no":9,"zh":"女孩儿","pinyin":"nǚháir","pos":"n.","uz":"qiz bola","ru":"девочка","tj":"духтар"},
        {"no":10,"zh":"姓","pinyin":"xìng","pos":"v.","uz":"familiyasi ... bo‘lmoq","ru":"носить фамилию","tj":"насаб доштан"},
        {"no":11,"zh":"眼睛","pinyin":"yǎnjing","pos":"n.","uz":"ko‘z","ru":"глаза","tj":"чашм"},
        {"no":12,"zh":"跳舞","pinyin":"tiàowǔ","pos":"v.","uz":"raqsga tushmoq","ru":"танцевать","tj":"рақсидан"}
    ],ensure_ascii=False),
    "proper_nouns_json":json.dumps([
        {"zh":"杨同乐","pinyin":"Yáng Tónglè","en":"Yang Tongle","uz":"Yang Tongle","ru":"Ян Тунлэ","tj":"Ян Тунлэ"}
    ],ensure_ascii=False),
    "dialogue_json":json.dumps([
        {"block_no":1,"section_label":"课文 1","scene_zh":"在回家路上，李文和王一飞边走边聊。","scene_uz":"Uyga qaytish yo‘lida Li Wen va Wang Yifei yurib suhbatlashmoqda.","scene_ru":"По дороге домой Ли Вэнь и Ван Ифэй разговаривают на ходу.","scene_tj":"Дар роҳи бозгашт ба хона Ли Вэн ва Ван Ифэй роҳравон суҳбат мекунанд.","dialogue":[
            {"speaker":"Li Wen","zh":"王老师，你家楼下站着一个人。","pinyin":"Wáng lǎoshī, nǐ jiā lóuxià zhànzhe yí ge rén.","uz":"Ustoz Wang, uyingiz pastida bir odam turibdi.","ru":"Преподаватель Ван, у вашего дома внизу стоит человек.","tj":"Устод Ван, поёни хонаи шумо як нафар истодааст."},
            {"speaker":"Wang Yifei","zh":"我家楼下？我看看。","pinyin":"Wǒ jiā lóuxià? Wǒ kànkan.","uz":"Uyim pastidami? Qani ko‘ray.","ru":"Внизу моего дома? Дай посмотрю.","tj":"Поёни хонаи ман? Бинам."},
            {"speaker":"Li Wen","zh":"那个人穿着黑色的裤子，手里还拿着一个黑色的包。","pinyin":"Nàge rén chuānzhe hēisè de kùzi, shǒulǐ hái názhe yí ge hēisè de bāo.","uz":"U odam qora shim kiygan, qo‘lida yana qora sumka bor.","ru":"На том человеке чёрные брюки, а в руке он держит чёрную сумку.","tj":"Он одам шими сиёҳ пӯшидааст ва дар дасташ халтаи сиёҳ дорад."},
            {"speaker":"Wang Yifei","zh":"我看见那个人了，他是我男朋友。","pinyin":"Wǒ kànjiàn nàge rén le, tā shì wǒ nánpéngyou.","uz":"Ko‘rdim, u mening yigitim.","ru":"Я его вижу, это мой молодой человек.","tj":"Ӯро дидам, ӯ дӯстписари ман аст."},
            {"speaker":"Li Wen","zh":"那我们快过去吧。","pinyin":"Nà wǒmen kuài guòqu ba.","uz":"Unda tezroq u tomonga boraylik.","ru":"Тогда пойдём скорее к нему.","tj":"Пас зуд ба он тараф равем."}
        ]},
        {"block_no":2,"section_label":"课文 2","scene_zh":"在楼下，王一飞见到杨同乐。","scene_uz":"Bino pastida Wang Yifei Yang Tongle bilan uchrashdi.","scene_ru":"Внизу дома Ван Ифэй встретила Ян Тунлэ.","scene_tj":"Дар поёни бино Ван Ифэй бо Ян Тунлэ вохӯрд.","dialogue":[
            {"speaker":"Wang Yifei","zh":"同乐，真是你啊！上次打电话，你说有时间过来看我，没想到这么快就来了！","pinyin":"Tónglè, zhēn shì nǐ a! Shàng cì dǎ diànhuà, nǐ shuō yǒu shíjiān guòlai kàn wǒ, méi xiǎngdào zhème kuài jiù lái le!","uz":"Tongle, rostdan ham sen ekansan! O‘tgan safar telefonlashganda vaqt topib meni ko‘rgani kelaman deganding, bunchalik tez kelasan deb o‘ylamagandim!","ru":"Тунлэ, это правда ты! В прошлый раз по телефону ты сказал, что приедешь навестить меня, когда будет время. Не думала, что так скоро!","tj":"Тунлэ, воқеан ту будаӣ! Дафъаи гузашта гуфтӣ вақте фурсат бошад ба диданам меоӣ, фикр намекардам ин қадар зуд биёӣ!"},
            {"speaker":"Yang Tongle","zh":"就要过年了，你一个人在这儿多没意思啊，所以我就早早过来了。","pinyin":"Jiù yào guònián le, nǐ yí ge rén zài zhèr duō méi yìsi a, suǒyǐ wǒ jiù zǎozǎo guòlai le.","uz":"Yangi yilga oz qoldi, bu yerda yolg‘iz qolish naqadar zerikarli, shuning uchun erta keldim.","ru":"Скоро Новый год, одному здесь так скучно, поэтому я приехал пораньше.","tj":"Ба Соли нав кам мондааст, танҳо будан дар ин ҷо чӣ қадар дилгир аст, барои ҳамин барвақт омадам."},
            {"speaker":"Wang Yifei","zh":"你能来，我太高兴了！","pinyin":"Nǐ néng lái, wǒ tài gāoxìng le!","uz":"Kelganingdan juda xursandman!","ru":"Я так рада, что ты приехал!","tj":"Аз омаданат хеле хурсанд шудам!"},
            {"speaker":"Yang Tongle","zh":"一飞，你旁边这位是？","pinyin":"Yīfēi, nǐ pángbian zhè wèi shì?","uz":"Yifei, yoningdagi bu kishi kim?","ru":"Ифэй, а кто этот человек рядом с тобой?","tj":"Ифэй, ин шахси паҳлӯят кист?"},
            {"speaker":"Wang Yifei","zh":"同乐，这是李文，他在我们学校学医。李文，这是我男朋友杨同乐。","pinyin":"Tónglè, zhè shì Lǐ Wén, tā zài wǒmen xuéxiào xué yī. Lǐ Wén, zhè shì wǒ nánpéngyou Yáng Tónglè.","uz":"Tongle, bu Li Wen, u bizning maktabda tibbiyot o‘qiydi. Li Wen, bu mening yigitim Yang Tongle.","ru":"Тунлэ, это Ли Вэнь, он изучает медицину в нашей школе. Ли Вэнь, это мой молодой человек Ян Тунлэ.","tj":"Тунлэ, ин Ли Вэн, ӯ дар мактаби мо тиб мехонад. Ли Вэн, ин дӯстписари ман Ян Тунлэ."},
            {"speaker":"Yang Tongle","zh":"李文，很高兴认识你！","pinyin":"Lǐ Wén, hěn gāoxìng rènshi nǐ!","uz":"Li Wen, tanishganimdan xursandman!","ru":"Ли Вэнь, приятно познакомиться!","tj":"Ли Вэн, аз шиносоӣ хушҳолам!"},
            {"speaker":"Li Wen","zh":"认识你我也很高兴！我家就在前面那个楼，有时间来玩。","pinyin":"Rènshi nǐ wǒ yě hěn gāoxìng! Wǒ jiā jiù zài qiánmian nàge lóu, yǒu shíjiān lái wán.","uz":"Men ham tanishganimdan xursandman! Uyim oldindagi binoda, vaqtingiz bo‘lsa mehmonga keling.","ru":"Я тоже рад познакомиться! Я живу вон в том доме впереди, заходите как-нибудь.","tj":"Ман ҳам аз шиносоӣ хушҳолам! Хонаам дар ҳамон бинои пеш аст, вақт бошад меҳмон шавед."}
        ]},
        {"block_no":3,"section_label":"课文 3","scene_zh":"在王一飞家里，王一飞和杨同乐在客厅聊天儿。","scene_uz":"Wang Yifeining uyida Wang Yifei va Yang Tongle mehmonxonada suhbatlashmoqda.","scene_ru":"Дома у Ван Ифэй она и Ян Тунлэ разговаривают в гостиной.","scene_tj":"Дар хонаи Ван Ифэй ӯ ва Ян Тунлэ дар меҳмонхона суҳбат мекунанд.","dialogue":[
            {"speaker":"Yang Tongle","zh":"一飞，你住的房子真不错，很大，离学校也不远。","pinyin":"Yīfēi, nǐ zhù de fángzi zhēn búcuò, hěn dà, lí xuéxiào yě bù yuǎn.","uz":"Yifei, yashaydigan uying juda yaxshi, katta va maktabdan ham uzoq emas.","ru":"Ифэй, у тебя отличный дом: большой и недалеко от школы.","tj":"Ифэй, хонае, ки зиндагӣ мекунӣ, хеле хубу калон аст ва аз мактаб ҳам дур нест."},
            {"speaker":"Wang Yifei","zh":"是啊！我楼下还住着一家中国人，他们人很好。","pinyin":"Shì a! Wǒ lóuxià hái zhùzhe yì jiā Zhōngguó rén, tāmen rén hěn hǎo.","uz":"Ha! Pastimda yana bir xitoylik oila yashaydi, juda yaxshi odamlar.","ru":"Да! Этажом ниже живёт китайская семья, очень хорошие люди.","tj":"Ҳа! Поёни ман як оилаи чинӣ зиндагӣ мекунад, одамони хеле хубанд."},
            {"speaker":"Yang Tongle","zh":"这样你有事情就可以找他们帮忙。","pinyin":"Zhèyàng nǐ yǒu shìqing jiù kěyǐ zhǎo tāmen bāngmáng.","uz":"Shunda biror ish bo‘lsa ulardan yordam so‘rashing mumkin.","ru":"Тогда, если что-то понадобится, можешь попросить их помочь.","tj":"Ҳамин тавр, агар коре шавад, аз онҳо кӯмак пурсидан мумкин."},
            {"speaker":"Wang Yifei","zh":"对，我也帮他们家的小孩儿学中文。","pinyin":"Duì, wǒ yě bāng tāmen jiā de xiǎoháir xué Zhōngwén.","uz":"Ha, men ham ularning bolasiga xitoy tilini o‘rganishda yordam beraman.","ru":"Да, а я помогаю их ребёнку учить китайский.","tj":"Ҳа, ман ҳам ба кӯдаки онҳо дар омӯхтани чинӣ кӯмак мекунам."},
            {"speaker":"Yang Tongle","zh":"我记得你跟我说过，是个女孩儿，学得也很好。","pinyin":"Wǒ jìde nǐ gēn wǒ shuōguo, shì ge nǚháir, xué de yě hěn hǎo.","uz":"Esimda, menga aytganding, u qiz bola va juda yaxshi o‘qiydi.","ru":"Помню, ты рассказывала: это девочка, и учится она хорошо.","tj":"Дар хотир дорам, гуфта будӣ, духтар аст ва хеле хуб мехонад."},
            {"speaker":"Wang Yifei","zh":"没错，她经常跑上来找我玩。","pinyin":"Méi cuò, tā jīngcháng pǎo shànglái zhǎo wǒ wán.","uz":"To‘g‘ri, u tez-tez yuqoriga yugurib kelib men bilan o‘ynaydi.","ru":"Верно, она часто прибегает наверх поиграть со мной.","tj":"Дуруст, ӯ зуд-зуд ба боло давида омада бо ман бозӣ мекунад."},
            {"speaker":"Yang Tongle","zh":"你问问他们什么时候有时间，我请他们吃个饭。","pinyin":"Nǐ wènwen tāmen shénme shíhou yǒu shíjiān, wǒ qǐng tāmen chī ge fàn.","uz":"Ulardan qachon vaqtlari borligini so‘ra, men ularni ovqatga taklif qilaman.","ru":"Спроси, когда у них будет время, я приглашу их поесть.","tj":"Аз онҳо пурс, кай вақт доранд, ман онҳоро ба хӯрок даъват мекунам."}
        ]},
        {"block_no":4,"section_label":"课文 4","scene_zh":"在房间，王一飞在写日记。","scene_uz":"Xonada Wang Yifei kundalik yozmoqda.","scene_ru":"В комнате Ван Ифэй пишет дневник.","scene_tj":"Дар ҳуҷра Ван Ифэй рӯзнома менависад.","dialogue":[
            {"speaker":"Narration","zh":"我男朋友姓杨，叫杨同乐。他高个子，大眼睛，唱歌唱得很好，跳舞跳得也不错。他和我姐姐一起工作，是姐姐介绍我们认识的。他告诉我，从见到我的第一天开始，他就喜欢上我了。","pinyin":"Wǒ nánpéngyou xìng Yáng, jiào Yáng Tónglè. Tā gāo gèzi, dà yǎnjing, chànggē chàng de hěn hǎo, tiàowǔ tiào de yě búcuò. Tā hé wǒ jiějie yìqǐ gōngzuò, shì jiějie jièshào wǒmen rènshi de. Tā gàosu wǒ, cóng jiàndào wǒ de dì-yī tiān kāishǐ, tā jiù xǐhuan shàng wǒ le.","uz":"Mening yigitimning familiyasi Yang, ismi Yang Tongle. U baland bo‘yli, ko‘zlari katta, juda yaxshi qo‘shiq aytadi va yaxshi raqsga tushadi. U opam bilan birga ishlaydi, bizni opam tanishtirgan. U menga birinchi ko‘rgan kunidan boshlab meni yoqtirib qolganini aytdi.","ru":"Фамилия моего молодого человека Ян, его зовут Ян Тунлэ. Он высокий, с большими глазами, хорошо поёт и неплохо танцует. Он работает вместе с моей сестрой; именно она нас познакомила. Он сказал, что полюбил меня с первого дня нашей встречи.","tj":"Насаби дӯстписари ман Ян, номаш Ян Тунлэ аст. Ӯ қадбаланду чашмкалон аст, хеле хуб месарояд ва хуб мерақсад. Ӯ бо апаам якҷо кор мекунад ва апаам моро шинос кард. Ӯ гуфт, ки аз рӯзи аввали диданаш маро дӯст доштааст."}
        ]}
    ],ensure_ascii=False),
    "grammar_json":json.dumps([
        {"no":1,"title_zh":"存现句（2）","title_uz":"Mavjudlik gapi (2)","title_ru":"Экзистенциальное предложение (2)","title_tj":"Ҷумлаи мавҷудият (2)","rule_zh":"动态助词“着”用在动词后面可以构成存现句，动词前面是表示处所的短语，后面一般是不确指的人或事物。基本结构：处所+动词+着+人/事物。","rule_uz":"“着” fe’ldan keyin kelib mavjudlik gapini tuzishi mumkin. Fe’l oldidan joy ifodasi, keyin odatda noaniq odam yoki narsa keladi. Tuzilishi: joy + fe’l + 着 + odam/narsa.","rule_ru":"“着” после глагола может образовывать экзистенциальное предложение. Перед глаголом стоит место, после него обычно неопределённый человек или предмет. Схема: место + глагол + 着 + человек/предмет.","rule_tj":"“着” баъди феъл омада ҷумлаи мавҷудият месозад. Пеш аз феъл ҷой, баъди он одатан шахс ё ашёи номуайян меояд. Сохтор: ҷой + феъл + 着 + шахс/ашё.","examples":[{"zh":"你家楼下站着一个人。"},{"zh":"爸爸手里拿着一杯咖啡。"},{"zh":"那间教室里坐着不少学生。"}]},
        {"no":2,"title_zh":"程度副词“多”","title_uz":"Daraja ravishi “多”","title_ru":"Наречие степени “多”","title_tj":"Зарфи дараҷаи “多”","rule_zh":"“多”用在感叹句中，表示程度很高。","rule_uz":"“多” undov gapida ishlatilib, darajaning juda yuqori ekanini bildiradi.","rule_ru":"“多” используется в восклицательных предложениях и выражает высокую степень признака.","rule_tj":"“多” дар ҷумлаи хитобӣ истифода шуда, дараҷаи хеле баландро нишон медиҳад.","examples":[{"zh":"你一个人在这儿多没意思啊！"},{"zh":"我们一起去多好啊！"},{"zh":"多好看呀！买这件吧。"}]},
        {"no":3,"title_zh":"复合趋向补语","title_uz":"Qo‘shma yo‘nalish to‘ldiruvchisi","title_ru":"Составное направительное дополнение","title_tj":"Пуркунандаи мураккаби самт","rule_zh":"“上、下、进、出、回、过”加上“来/去”，以及“起来”，用在动词后，可以构成复合趋向补语，表示动作的方向。动词带宾语时，地点名词放在“来/去”前面；事物名词放在“来/去”前后都可以。","rule_uz":"“上、下、进、出、回、过” + “来/去” hamda “起来” fe’ldan keyin kelib qo‘shma yo‘nalish to‘ldiruvchisini tuzadi. Joy oti obyekt bo‘lsa 来/去 oldida; narsa oti esa oldida ham, keyin ham kelishi mumkin.","rule_ru":"“上、下、进、出、回、过” + “来/去”, а также “起来”, после глагола образуют составное направительное дополнение. Объект-место ставится перед 来/去; предметный объект может стоять до или после 来/去.","rule_tj":"“上、下、进、出、回、过” + “来/去” ва “起来” баъди феъл пуркунандаи мураккаби самт месозанд. Объекти ҷой пеш аз 来/去; объекти ашёӣ пеш ё пас аз 来/去 меояд.","examples":[{"zh":"她经常跑上来找我玩。"},{"zh":"楼不高，我们走上去吧。"},{"zh":"一听到老师叫他的名字，他就站起来了。"},{"zh":"同学们都走出教室去了。"},{"zh":"妈妈让我买回来一些菜来。"},{"zh":"白家月从书包里找出来一个漂亮的本子。"}]}
    ],ensure_ascii=False)
}
