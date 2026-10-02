from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(53, 62)),
    "printed_pages": list(range(37, 46)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level":"nhsk2","lesson_order":5,"lesson_code":"NHSK2-L05",
    "title":"第一次去中国朋友家","title_pinyin":"Dì-yī cì qù Zhōngguó péngyou jiā",
    "goal":json.dumps({"uz":"Oddiy yo‘nalish to‘ldiruvchilarini 来/去 bilan ishlatish; obyektning joylashuvini to‘g‘ri tanlash; “都……了” bilan ‘allaqachon/shu darajaga yetdi’ ma’nosini berish; xitoylik do‘stnikiga mehmon bo‘lish vaziyatida muloqot qilish.","ru":"Использовать простые направительные дополнения с 来/去; правильно располагать объект; выражать ‘уже/дошло до’ конструкцией “都……了”; общаться в ситуации первого визита к китайским друзьям.","tj":"Пуркунандаи самти соддаро бо 来/去 истифода бурдан; ҷойи объектро дуруст гузоштан; бо “都……了” маънои ‘аллакай/то ин дараҷа’ додан; ҳангоми меҳмонӣ ба хонаи дӯсти чинӣ суҳбат кардан."},ensure_ascii=False),
    "intro_text":json.dumps({"uz":"Dars mehmonxonadan do‘stnikiga borish, uyga kirish, sovg‘a topshirish, ovqatlanish va qaytish haqidagi matnlar orqali yo‘nalish to‘ldiruvchisi va 都……了 qolipini o‘rgatadi.","ru":"Урок через визит к друзьям, вход в дом, подарки, обед и возвращение вводит направительные дополнения и конструкцию 都……了.","tj":"Дарс тавассути рафтан ба хонаи дӯст, даромадан, тӯҳфа додан, хӯрок хӯрдан ва баргаштан пуркунандаи самт ва қолаби 都……了-ро меомӯзонад."},ensure_ascii=False),
    "vocabulary_json":json.dumps([
        {"no":1,"zh":"快","pinyin":"kuài","pos":"adv./adj.","uz":"tez; shoshil","ru":"быстро; скорый","tj":"тез; зуд"},
        {"no":2,"zh":"下来","pinyin":"xiàlái","pos":"v.","uz":"pastga tushib kelmoq","ru":"спуститься сюда","tj":"поён омада расидан"},
        {"no":3,"zh":"上来","pinyin":"shànglái","pos":"v.","uz":"yuqoriga chiqib kelmoq","ru":"подняться сюда","tj":"боло омада баромадан"},
        {"no":4,"zh":"上去","pinyin":"shàngqù","pos":"v.","uz":"yuqoriga chiqib bormoq","ru":"подняться туда","tj":"боло рафтан"},
        {"no":5,"zh":"下面","pinyin":"xiàmian","pos":"n.","uz":"past; pastki tomon","ru":"внизу","tj":"поён; қисми поён"},
        {"no":6,"zh":"面","pinyin":"miàn","pos":"suf.","uz":"joy otini yasovchi qo‘shimcha","ru":"суффикс для слов места","tj":"пасванд барои номи ҷой"},
        {"no":7,"zh":"等","pinyin":"děng","pos":"v.","uz":"kutmoq","ru":"ждать","tj":"интизор шудан"},
        {"no":8,"zh":"一会儿","pinyin":"yíhuìr","pos":"num.-m.","uz":"birozdan so‘ng; bir oz","ru":"через некоторое время; немного","tj":"каме баъд; андаке"},
        {"no":9,"zh":"下去","pinyin":"xiàqù","pos":"v.","uz":"pastga tushib bormoq","ru":"спуститься туда","tj":"поён рафтан"},
        {"no":10,"zh":"进来","pinyin":"jìnlái","pos":"v.","uz":"ichkariga kirib kelmoq","ru":"войти сюда","tj":"ба дарун омада даромадан"},
        {"no":11,"zh":"爷爷","pinyin":"yéye","pos":"n.","uz":"bobo","ru":"дедушка","tj":"бобо"},
        {"no":12,"zh":"奶奶","pinyin":"nǎinai","pos":"n.","uz":"buvi","ru":"бабушка","tj":"бибӣ"},
        {"no":13,"zh":"礼物","pinyin":"lǐwù","pos":"n.","uz":"sovg‘a","ru":"подарок","tj":"тӯҳфа"},
        {"no":14,"zh":"准备","pinyin":"zhǔnbèi","pos":"v.","uz":"tayyorlamoq","ru":"готовить; подготавливать","tj":"тайёр кардан"},
        {"no":15,"zh":"奶茶","pinyin":"nǎichá","pos":"n.","uz":"sutli choy; milk tea","ru":"чай с молоком; milk tea","tj":"чойи ширӣ"},
        {"no":16,"zh":"跟","pinyin":"gēn","pos":"prep./conj.","uz":"bilan","ru":"с; и","tj":"бо; ва"},
        {"no":17,"zh":"走","pinyin":"zǒu","pos":"v.","uz":"yurmoq; bormoq","ru":"идти пешком","tj":"пиёда рафтан"},
        {"no":18,"zh":"酒店","pinyin":"jiǔdiàn","pos":"n.","uz":"mehmonxona","ru":"гостиница","tj":"меҳмонхона"},
    ],ensure_ascii=False),
    "proper_nouns_json":json.dumps([],ensure_ascii=False),
    "dialogue_json":json.dumps([
        {"block_no":1,"section_label":"课文 1","scene_zh":"在宾馆楼下，安妮给白家月打电话。","scene_uz":"Mehmonxona pastida Annie Bai Jiayuega telefon qilmoqda.","scene_ru":"Внизу гостиницы Энни звонит Бай Цзяюэ.","scene_tj":"Дар поёни меҳмонхона Энни ба Бай Ҷяюэ занг мезанад.","dialogue":[
            {"speaker":"Annie","zh":"家月，快下来吧，第一次去中国朋友家，别晚了。","pinyin":"Jiāyuè, kuài xiàlái ba, dì-yī cì qù Zhōngguó péngyou jiā, bié wǎn le.","uz":"Jiayue, tez tush, xitoylik do‘stnikiga birinchi marta ketyapmiz, kechikmaylik.","ru":"Цзяюэ, скорее спускайся, мы впервые идём в гости к китайским друзьям, не опоздай.","tj":"Ҷяюэ, зуд поён биё, бори аввал ба хонаи дӯсти чинӣ меравем, дер накун."},
            {"speaker":"Bai Jiayue","zh":"还有时间，你上来吧。","pinyin":"Hái yǒu shíjiān, nǐ shànglái ba.","uz":"Hali vaqt bor, sen yuqoriga chiq.","ru":"Время ещё есть, поднимайся ко мне.","tj":"Ҳоло вақт ҳаст, ту боло биё."},
            {"speaker":"Annie","zh":"我不上去了，就在下面等你。","pinyin":"Wǒ bú shàngqù le, jiù zài xiàmian děng nǐ.","uz":"Men yuqoriga chiqmayman, pastda seni kutaman.","ru":"Я не буду подниматься, подожду тебя внизу.","tj":"Ман боло намебароям, дар поён туро интизор мешавам."},
            {"speaker":"Bai Jiayue","zh":"那我一会儿就下去。","pinyin":"Nà wǒ yíhuìr jiù xiàqù.","uz":"Unda men birozdan keyin tushaman.","ru":"Тогда я через минуту спущусь.","tj":"Пас ман каме баъд поён мефароям."},
            {"speaker":"Annie","zh":"你快点儿吧。","pinyin":"Nǐ kuài diǎnr ba.","uz":"Tezroq bo‘l.","ru":"Побыстрее, пожалуйста.","tj":"Тезтар шав."},
            {"speaker":"Bai Jiayue","zh":"没事，一雪姐说11点前到就可以。","pinyin":"Méishì, Yīxuě jiě shuō shíyī diǎn qián dào jiù kěyǐ.","uz":"Hechqisi yo‘q, opa Yixue soat 11 gacha yetib borsak bo‘ladi dedi.","ru":"Ничего, сестра Исюэ сказала, что достаточно приехать до 11.","tj":"Ҳеҷ гап не, апаи Исюэ гуфт то соати 11 расем бас аст."},
        ]},
        {"block_no":2,"section_label":"课文 2","scene_zh":"在王一雪家，白家月和安妮来做客。","scene_uz":"Wang Yixue uyida Bai Jiayue va Annie mehmon bo‘lib kelgan.","scene_ru":"У Ван Исюэ дома Бай Цзяюэ и Энни пришли в гости.","scene_tj":"Дар хонаи Ван Исюэ Бай Ҷяюэ ва Энни ба меҳмонӣ омадаанд.","dialogue":[
            {"speaker":"Wang Yixue","zh":"家月、安妮，快进来！我给你们介绍一下，这是孩子们的爷爷、奶奶。","pinyin":"Jiāyuè, Ānnī, kuài jìnlái! Wǒ gěi nǐmen jièshào yíxià, zhè shì háizimen de yéye, nǎinai.","uz":"Jiayue, Annie, tez kiring! Sizlarni tanishtiray: bular bolalarning bobosi va buvisi.","ru":"Цзяюэ, Энни, заходите! Познакомлю вас: это дедушка и бабушка детей.","tj":"Ҷяюэ, Энни, дароед! Шуморо шинос мекунам: инҳо бобо ва бибии кӯдаконанд."},
            {"speaker":"Bai Jiayue & Annie","zh":"你们好！","pinyin":"Nǐmen hǎo!","uz":"Salom!","ru":"Здравствуйте!","tj":"Салом!"},
            {"speaker":"Wang Yixue","zh":"爸，妈，这是白家月，这是安妮。她们都是一飞的学生。","pinyin":"Bà, mā, zhè shì Bái Jiāyuè, zhè shì Ānnī. Tāmen dōu shì Yīfēi de xuésheng.","uz":"Dada, oyi, bu Bai Jiayue, bu Annie. Ikkalasi ham Yifeining talabalari.","ru":"Папа, мама, это Бай Цзяюэ, а это Энни. Они обе ученицы Ифэй.","tj":"Дада, оча, ин Бай Ҷяюэ, ин Энни. Ҳарду донишҷӯи Ифэй ҳастанд."},
            {"speaker":"Grandpa Liu","zh":"家月、安妮，你们好！","pinyin":"Jiāyuè, Ānnī, nǐmen hǎo!","uz":"Jiayue, Annie, salom!","ru":"Цзяюэ, Энни, здравствуйте!","tj":"Ҷяюэ, Энни, салом!"},
            {"speaker":"Bai Jiayue","zh":"这是送你们的礼物。","pinyin":"Zhè shì sòng nǐmen de lǐwù.","uz":"Bu sizlarga sovg‘a.","ru":"Это подарок для вас.","tj":"Ин тӯҳфа барои шумост."},
            {"speaker":"Grandpa Liu","zh":"你们太客气了，还拿这么多礼物来！","pinyin":"Nǐmen tài kèqi le, hái ná zhème duō lǐwù lái!","uz":"Juda ovora bo‘libsizlar, yana shuncha sovg‘a olib kelibsizlar!","ru":"Ну что вы, ещё столько подарков принесли!","tj":"Ин қадар заҳмат кашида, боз ин қадар тӯҳфа овардаед!"},
            {"speaker":"Bai Jiayue","zh":"一雪姐，这是给孩子们准备的礼物。","pinyin":"Yīxuě jiě, zhè shì gěi háizimen zhǔnbèi de lǐwù.","uz":"Opa Yixue, bu bolalar uchun tayyorlagan sovg‘amiz.","ru":"Сестра Исюэ, это подарок, который мы приготовили детям.","tj":"Апа Исюэ, ин тӯҳфаест, ки барои кӯдакон тайёр кардем."},
            {"speaker":"Wang Yixue","zh":"谢谢！你们别客气，快坐吧！","pinyin":"Xièxie! Nǐmen bié kèqi, kuài zuò ba!","uz":"Rahmat! Bemalol bo‘linglar, o‘tiringlar!","ru":"Спасибо! Не стесняйтесь, садитесь!","tj":"Раҳмат! Худатонро озод ҳис кунед, нишинед!"},
        ]},
        {"block_no":3,"section_label":"课文 3","scene_zh":"在王一雪家，白家月和安妮在吃饭。","scene_uz":"Wang Yixue uyida Bai Jiayue va Annie ovqatlanmoqda.","scene_ru":"У Ван Исюэ дома Бай Цзяюэ и Энни обедают.","scene_tj":"Дар хонаи Ван Исюэ Бай Ҷяюэ ва Энни хӯрок мехӯранд.","dialogue":[
            {"speaker":"Wang Yixue","zh":"都12点了，我们吃饭吧。","pinyin":"Dōu shí'èr diǎn le, wǒmen chī fàn ba.","uz":"Soat allaqachon 12 bo‘ldi, ovqatlanaylik.","ru":"Уже двенадцать, давайте есть.","tj":"Соат аллакай 12 шуд, биёед хӯрок хӯрем."},
            {"speaker":"Bai Jiayue","zh":"这么多好吃的，您太客气了！","pinyin":"Zhème duō hǎochī de, nín tài kèqi le!","uz":"Shuncha mazali taom, juda ovora bo‘libsiz!","ru":"Столько вкусного, вы так постарались!","tj":"Ин қадар хӯроки болаззат, хеле заҳмат кашидаед!"},
            {"speaker":"Wang Yixue","zh":"都是我自己做的，你们多吃点儿。","pinyin":"Dōu shì wǒ zìjǐ zuò de, nǐmen duō chī diǎnr.","uz":"Hammasini o‘zim qildim, ko‘proq yenglar.","ru":"Я всё приготовила сама, ешьте побольше.","tj":"Ҳамаашро худам тайёр кардам, бештар бихӯред."},
            {"speaker":"Bai Jiayue","zh":"奶茶也很好喝，是您自己做的吗？","pinyin":"Nǎichá yě hěn hǎohē, shì nín zìjǐ zuò de ma?","uz":"Sutli choy ham juda mazali, uni ham o‘zingiz qildingizmi?","ru":"Чай с молоком тоже очень вкусный, вы сами сделали?","tj":"Чойи ширӣ ҳам хеле болаззат аст, худатон тайёр кардед?"},
            {"speaker":"Wang Yixue","zh":"不是，奶茶是爷爷买的。","pinyin":"Bú shì, nǎichá shì yéye mǎi de.","uz":"Yo‘q, sutli choyni bobo sotib olgan.","ru":"Нет, чай с молоком купил дедушка.","tj":"Не, чойи шириро бобо харидааст."},
            {"speaker":"Bai Jiayue","zh":"在哪儿买的？我还没喝过这么好喝的奶茶。","pinyin":"Zài nǎr mǎi de? Wǒ hái méi hēguo zhème hǎohē de nǎichá.","uz":"Qayerdan olgan? Men hali bunday mazali sutli choy ichmaganman.","ru":"Где он его купил? Я ещё никогда не пила такой вкусный чай с молоком.","tj":"Аз куҷо харидааст? Ман ҳоло чунин чойи ширии болаззат нанӯшидаам."},
            {"speaker":"Wang Yixue","zh":"就在前边的商场，吃完饭你们可以跟我去看看。","pinyin":"Jiù zài qiánbian de shāngchǎng, chīwán fàn nǐmen kěyǐ gēn wǒ qù kànkan.","uz":"Oldindagi savdo markazida. Ovqatdan keyin men bilan borib ko‘rishingiz mumkin.","ru":"В торговом центре впереди. После еды можете сходить со мной посмотреть.","tj":"Дар маркази савдои пештар. Баъди хӯрок метавонед бо ман рафта бинед."},
        ]},
        {"block_no":4,"section_label":"课文 4","scene_zh":"在宾馆，白家月给李文发信息。","scene_uz":"Mehmonxonada Bai Jiayue Li Wenga xabar yubormoqda.","scene_ru":"В гостинице Бай Цзяюэ отправляет сообщение Ли Вэню.","scene_tj":"Дар меҳмонхона Бай Ҷяюэ ба Ли Вэн паём мефиристад.","dialogue":[
            {"speaker":"Narration","zh":"回国前一天，我们去一雪姐家了。到她家的时候，饭菜都做好了。刘爷爷还准备了奶茶。因为吃了太多东西，我们吃完饭是走回酒店的。","pinyin":"Huíguó qián yì tiān, wǒmen qù Yīxuě jiě jiā le. Dào tā jiā de shíhou, fàncài dōu zuòhǎo le. Liú yéye hái zhǔnbèile nǎichá. Yīnwèi chīle tài duō dōngxi, wǒmen chīwán fàn shì zǒu huí jiǔdiàn de.","uz":"Vatanga qaytishimizdan bir kun oldin opa Yixuenikiga bordik. Yetib borganimizda ovqatlar tayyor edi. Liu bobo sutli choy ham tayyorlagan ekan. Juda ko‘p ovqat yeganimiz uchun ovqatdan keyin mehmonxonaga piyoda qaytdik.","ru":"За день до возвращения домой мы пошли к сестре Исюэ. Когда пришли, еда уже была готова. Дедушка Лю приготовил ещё и чай с молоком. Мы съели слишком много, поэтому после еды вернулись в гостиницу пешком.","tj":"Як рӯз пеш аз бозгашт ба ватан ба хонаи апаи Исюэ рафтем. Вақте расидем, хӯрокҳо тайёр буданд. Бобои Лю чойи ширӣ ҳам тайёр карда буд. Азбаски бисёр хӯрок хӯрдем, баъди хӯрок пиёда ба меҳмонхона баргаштем."},
        ]},
    ],ensure_ascii=False),
    "grammar_json":json.dumps([
        {"no":1,"title_zh":"简单趋向补语（1）","title_uz":"Oddiy yo‘nalish to‘ldiruvchisi (1)","title_ru":"Простое направительное дополнение (1)","title_tj":"Пуркунандаи самти содда (1)","rule_zh":"简单趋向补语的基本结构是“动词+来/去”。“来”表示动作朝着说话人的方向进行，“去”表示动作背离说话人的方向进行。常用动词有“上、下、进、出、回、过”。","rule_uz":"Asosiy tuzilma “fe’l+来/去”. 来 harakat gapiruvchi tomonga, 去 esa gapiruvchidan uzoqlashayotganini bildiradi. Ko‘p ishlatiladigan fe’llar: 上、下、进、出、回、过.","rule_ru":"Базовая схема: «глагол+来/去». 来 показывает движение к говорящему, 去 — от говорящего. Часто используются 上、下、进、出、回、过.","rule_tj":"Сохтори асосӣ «феъл+来/去» аст. 来 ҳаракат ба сӯи гӯянда, 去 аз гӯянда дур шуданро нишон медиҳад. Феълҳои маъмул: 上、下、进、出、回、过.","examples":[{"zh":"我不上去了，就在下面等你。"},{"zh":"家月到下边了，你下去接她吧。"},{"zh":"我在外边呢，你出来吧。"},{"zh":"她拿来一本中文书。"},{"zh":"你别过来拿了，我给你送去。"},{"zh":"今天早上5点她就起来了。"}]},
        {"no":2,"title_zh":"简单趋向补语（2）","title_uz":"Oddiy yo‘nalish to‘ldiruvchisi (2)","title_ru":"Простое направительное дополнение (2)","title_tj":"Пуркунандаи самти содда (2)","rule_zh":"动词带简单趋向补语又带宾语时，如果宾语是地点名词，放在“来/去”前面；宾语是事物名词，放在“来/去”前后都可以。动词“开、买、拿、请、送、要、找、走”等也可以加上“上、下、进、出、回、过”等简单趋向补语。","rule_uz":"Fe’l yo‘nalish to‘ldiruvchisi va obyekt bilan kelganda, joy oti bo‘lsa obyekt 来/去 dan oldin turadi; narsa oti bo‘lsa oldin ham, keyin ham kelishi mumkin. 开、买、拿、请、送、要、找、走 kabi fe’llar ham yo‘nalish elementlari bilan birikadi.","rule_ru":"Если при глаголе есть простое направительное дополнение и объект, топоним/место ставится перед 来/去; предметный объект может стоять и до, и после 来/去. Глаголы 开、买、拿、请、送、要、找、走 также сочетаются с 上、下、进、出、回、过.","rule_tj":"Агар феъл ҳам пуркунандаи самт ва ҳам объект дошта бошад, исми ҷой пеш аз 来/去 меояд; исми ашё метавонад пеш ё баъд аз 来/去 ояд. Феълҳои 开、买、拿、请、送、要、找、走 низ бо 上、下、进、出、回、过 меоянд.","examples":[{"zh":"你们太客气了，还拿这么多礼物来！"},{"zh":"家月给我送来了一本书。"},{"zh":"上课了，你们快进教室来吧。"},{"zh":"爸爸今天买回了很多水果。"},{"zh":"妈妈拿出了二十块钱，让小雪自己去买点儿吃的。"}]},
        {"no":3,"title_zh":"固定格式“都……了”","title_uz":"“都……了” qolipi","title_ru":"Конструкция “都……了”","title_tj":"Қолаби “都……了”","rule_zh":"固定格式“都……了”表示已经、达到，一般含有强调或者不满的语气。","rule_uz":"“都……了” ‘allaqachon’ yoki ma’lum bosqichga yetganlikni bildiradi va odatda ta’kid yoki norozilik ohangiga ega.","rule_ru":"“都……了” выражает значение «уже, дошло до» и обычно несёт оттенок усиления или недовольства.","rule_tj":"“都……了” маънои «аллакай, то ин дараҷа расидааст»-ро медиҳад ва одатан таъкид ё норозигиро мефаҳмонад.","examples":[{"zh":"都12点了，我们吃饭吧。"},{"zh":"都8点半了，你还不起床吗？"},{"zh":"我都去过北京了，不想再去了。"}]},
    ],ensure_ascii=False),
}
