import copy
import json

from scripts.hsk4_upper_i18n import GRAMMAR_I18N, LINE_I18N, SCENE_I18N, VOCAB_I18N


def _j(value):
    return json.dumps(value, ensure_ascii=False)


def _word(no, zh, pinyin, pos, uz):
    return {"no": no, "zh": zh, "pinyin": pinyin, "pos": pos, "uz": uz}


def _line(speaker, zh, uz):
    return {"speaker": speaker, "zh": zh, "pinyin": "", "uz": uz}


def _grammar(no, title_zh, title_uz, rule_uz, example_zh, example_uz):
    return {
        "no": no,
        "title_zh": title_zh,
        "title_uz": title_uz,
        "rule_uz": rule_uz,
        "formula": title_zh,
        "examples": [{"zh": example_zh, "pinyin": "", "uz": example_uz}],
    }


HSK4_UPPER_PDF_MATERIALS = {
    1: {
        "title": "简单的爱情",
        "goal": {
            "uz": "sevgi va munosabatlar haqida gapirish; 不仅, 从来, 刚, 即使 va (在)...上 grammatikalarini ishlatish",
            "ru": "говорить о любви и отношениях; использовать 不仅, 从来, 刚, 即使 и (在)...上",
            "tj": "дар бораи муҳаббат ва муносибатҳо гуфтугӯ кардан; истифодаи 不仅, 从来, 刚, 即使 ва (在)...上",
        },
        "intro_text": {
            "uz": "Bu darsda sevgi, turmush qurish, romantika va xarakter haqida gapirishni o'rganasiz. Har qismda o'sha matndagi yangi so'zlar, pinyin, tarjima va kerakli grammatika beriladi.",
            "ru": "В этом уроке вы научитесь говорить о любви, браке, романтике и характере. В каждой части будут слова, pinyin, перевод и нужная грамматика именно к этому тексту.",
            "tj": "Дар ин дарс дар бораи муҳаббат, издивоҷ, романтика ва характер гуфтугӯ карданро меомӯзед. Дар ҳар қисм калимаҳо, pinyin, тарҷума ва грамматикаи лозими ҳамон матн дода мешавад.",
        },
        "vocabulary": [
            _word(1, "法律", "fǎlǜ", "n.", "qonun, huquq"),
            _word(2, "俩", "liǎ", "num.-m.", "ikkalasi, ikki kishi"),
            _word(3, "印象", "yìnxiàng", "n.", "taassurot"),
            _word(4, "深", "shēn", "adj.", "chuqur"),
            _word(5, "熟悉", "shúxī", "v.", "tanish bo'lmoq, yaxshi bilmoq"),
            _word(6, "不仅", "bùjǐn", "conj.", "nafaqat"),
            _word(7, "性格", "xìnggé", "n.", "xarakter, fe'l-atvor"),
            _word(8, "开玩笑", "kāi wánxiào", "v.", "hazil qilmoq"),
            _word(9, "从来", "cónglái", "adv.", "doim; hech qachon (inkor bilan)"),
            _word(10, "最好", "zuìhǎo", "adv.", "eng yaxshisi, yaxshisi"),
            _word(11, "共同", "gòngtóng", "adj.", "umumiy, birgalikdagi"),
            _word(12, "适合", "shìhé", "v.", "mos kelmoq"),
            _word(13, "幸福", "xìngfú", "adj.", "baxtli"),
            _word(14, "生活", "shēnghuó", "n./v.", "hayot; yashamoq"),
            _word(15, "刚", "gāng", "adv.", "endi, hozirgina"),
            _word(16, "浪漫", "làngmàn", "adj.", "romantik"),
            _word(17, "够", "gòu", "v.", "yetarli bo'lmoq"),
            _word(18, "缺点", "quēdiǎn", "n.", "kamchilik"),
            _word(19, "接受", "jiēshòu", "v.", "qabul qilmoq"),
            _word(20, "羡慕", "xiànmù", "v.", "havas qilmoq, qoyil qolmoq"),
            _word(21, "爱情", "àiqíng", "n.", "sevgi, muhabbat"),
            _word(22, "星星", "xīngxing", "n.", "yulduz"),
            _word(23, "即使", "jíshǐ", "conj.", "hatto ... bo'lsa ham"),
            _word(24, "加班", "jiā bān", "v.", "qo'shimcha ishlamoq"),
            _word(25, "亮", "liàng", "v.", "yorishmoq, chiroq yonmoq"),
            _word(26, "感动", "gǎndòng", "v.", "ta'sirlantirmoq"),
            _word(27, "自然", "zìrán", "adv.", "tabiiy ravishda"),
            _word(28, "原因", "yuányīn", "n.", "sabab"),
            _word(29, "互相", "hùxiāng", "adv.", "o'zaro, bir-biriga"),
            _word(30, "吸引", "xīyǐn", "v.", "jalb qilmoq"),
            _word(31, "幽默", "yōumò", "adj.", "hazilkash, yumorga boy"),
            _word(32, "脾气", "píqi", "n.", "fe'l, mijoz, xarakter"),
        ],
        "grammar": [
            _grammar(1, "不仅……也/还/而且……", "nafaqat..., balki/ham...", "Ikki ijobiy xususiyatni bog'lab, ikkinchi qismni kuchaytiradi.", "他不仅足球踢得好，性格也不错。", "U nafaqat futbolni yaxshi o'ynaydi, xarakteri ham yaxshi."),
            _grammar(2, "从来", "doim; hech qachon (inkor bilan)", "Odatda inkor bilan kelib, 'hech qachon bunday bo'lmagan' ma'nosini beradi.", "我从来没这么快乐过。", "Men hech qachon bunchalik xursand bo'lmaganman."),
            _grammar(3, "刚", "endi, hozirgina", "Harakat yaqinda yoki endi bo'lganini bildiradi.", "我和丈夫刚结婚的时候，每天都觉得很新鲜。", "Erim bilan endi turmush qurgan paytimda har kuni hamma narsa yangi tuyulardi."),
            _grammar(4, "即使……也……", "hatto ... bo'lsa ham", "Shart kuchli bo'lsa ham natija o'zgarmasligini bildiradi.", "即使晚上加班到零点，到家时，自己家里也还亮着灯。", "Hatto kechasi yarimgacha ishlasa ham, uyga kelganda uyida chiroq yonib turadi."),
            _grammar(5, "（在）……上", "... jihatdan, ... borasida", "Mavzu yoki sohani ko'rsatadi: xarakter jihatidan, ish borasida kabi.", "更需要性格上互相吸引。", "Xarakter jihatidan bir-birini jalb qilish yanada kerak."),
        ],
        "dialogues": [
            {
                "block_no": 1,
                "section_label": "课文 1",
                "scene_uz": "孙月 va 王静 uning yigit do'sti haqida gaplashadi",
                "word_nos": [1, 2, 3, 4, 5, 6, 7],
                "grammar_nos": [1],
                "dialogue": [
                    _line("孙月", "听说你男朋友李进跟你是一个学校的，是你同学吗？", "Eshitishimcha yigiting Li Jin sen bilan bir maktabda, u sening sinfdoshingmi?"),
                    _line("王静", "是的，他学的是新闻，我学的是法律，我和他不是一个班。", "Ha, u jurnalistika o'qiydi, men huquq o'qiyman, biz bir guruhda emasmiz."),
                    _line("孙月", "那你们俩是怎么认识的？", "Unda siz ikkalangiz qanday tanishgansiz?"),
                    _line("王静", "我们是在一次足球比赛中认识的。我们班跟他们班比赛，他一个人踢进两个球，我对他印象很深，后来就慢慢熟悉了。", "Biz bir futbol musobaqasida tanishganmiz. Bizning guruh ular guruhi bilan o'ynagan, u bir o'zi ikkita gol urgan, menda chuqur taassurot qoldirgan, keyin asta-sekin tanishib ketdik."),
                    _line("孙月", "你为什么喜欢他？", "Nega uni yoqtirasan?"),
                    _line("王静", "他不仅足球踢得好，性格也不错。", "U nafaqat futbolni yaxshi o'ynaydi, xarakteri ham yaxshi."),
                ],
            },
            {
                "block_no": 2,
                "section_label": "课文 2",
                "scene_uz": "王静 Li o'qituvchi bilan turmush qurishi haqida gaplashadi",
                "word_nos": [8, 9, 10, 11, 12, 13],
                "grammar_nos": [2],
                "dialogue": [
                    _line("王静", "李老师，我下个月5号就要结婚了。", "Li ustoz, men keyingi oyning 5-kuni turmushga chiqaman."),
                    _line("李老师", "你是在开玩笑吧？你们不是才认识一个月？", "Hazil qilyapsanmi? Sizlar endigina bir oy oldin tanishgansiz-ku?"),
                    _line("王静", "虽然我们认识的时间不长，但我从来没这么快乐过。", "Tanishganimizga ko'p bo'lmagan bo'lsa ham, men hech qachon bunchalik xursand bo'lmaganman."),
                    _line("李老师", "两个人在一起，最好能有共同的兴趣和爱好。", "Ikki kishi birga bo'lsa, umumiy qiziqish va hobbilari bo'lgani yaxshi."),
                    _line("王静", "我们有很多共同的爱好，经常一起打球、唱歌、做菜。", "Bizning umumiy qiziqishlarimiz ko'p, ko'pincha birga to'p o'ynaymiz, qo'shiq aytamiz, ovqat qilamiz."),
                    _line("李老师", "看来你真的找到适合你的人了。祝你们幸福！", "Demak sen haqiqatan ham o'zingga mos odamni topibsan. Sizlarga baxt tilayman!"),
                ],
            },
            {
                "block_no": 3,
                "section_label": "课文 3",
                "scene_uz": "高老师 va 李老师 turmush hayoti haqida gaplashadi",
                "word_nos": [14, 15, 16, 17, 18, 19],
                "grammar_nos": [3],
                "dialogue": [
                    _line("高老师", "听说您跟妻子结婚快二十年了？", "Eshitishimcha, siz rafiqangiz bilan turmush qurganingizga deyarli yigirma yil bo'libdi?"),
                    _line("李老师", "到6月9号，我们就结婚二十年了。这么多年，我们的生活一直挺幸福的。", "6-iyunga kelib turmush qurganimizga yigirma yil bo'ladi. Shu yillar davomida hayotimiz doim ancha baxtli bo'lgan."),
                    _line("高老师", "我和丈夫刚结婚的时候，每天都觉得很新鲜，在一起有说不完的话。但是现在……", "Erim bilan endi turmush qurgan paytimda har kuni hamma narsa yangi tuyulardi, birga bo'lsak gapimiz tugamasdi. Lekin hozir..."),
                    _line("李老师", "两个人共同生活，只有浪漫和新鲜感是不够的。", "Ikki kishi birga yashasa, faqat romantika va yangilik hissi yetarli emas."),
                    _line("高老师", "您说的对！我现在每天看到的都是他的缺点。", "To'g'ri aytasiz! Men hozir har kuni faqat uning kamchiliklarini ko'raman."),
                    _line("李老师", "两个人在一起时间长了，就会有很多问题。只有接受了他的缺点，你们才能更好地一起生活。", "Ikki kishi uzoq vaqt birga bo'lsa, ko'p muammo bo'ladi. Faqat uning kamchiliklarini qabul qilgandagina yaxshiroq birga yashay olasizlar."),
                ],
            },
            {
                "block_no": 4,
                "section_label": "课文 4",
                "scene_uz": "Romantik sevgi haqida matn",
                "word_nos": [20, 21, 22, 23, 24, 25, 26],
                "grammar_nos": [4],
                "dialogue": [
                    _line("旁白", "很多女孩子羡慕浪漫的爱情。", "Ko'p qizlar romantik sevgiga havas qiladi."),
                    _line("旁白", "那什么是浪漫呢？年轻人说：浪漫是她想要月亮时，你不会给她星星；中年人说：浪漫是即使晚上加班到零点，到家时，自己家里也还亮着灯；老年人说：浪漫其实就像歌中唱的那样，“我能想到最浪漫的事，就是和你一起慢慢变老。”其实，让我们感动的，就是生活中简单的爱情。有时候，简单就是最大的幸福。", "Romantika nima o'zi? Yoshlar aytadi: romantika - u oy so'rasa, unga yulduz bermaslik; o'rta yoshlilar aytadi: romantika - hatto kechasi yarimgacha ishlasa ham, uyga kelganda uy chirog'i yonib turishi; keksalar aytadi: romantika qo'shiqdagi kabi, 'men tasavvur qila oladigan eng romantik ish - sen bilan birga asta qarish'. Aslida bizni ta'sirlantiradigan narsa hayotdagi oddiy sevgi. Ba'zan oddiylik eng katta baxtdir."),
                ],
            },
            {
                "block_no": 5,
                "section_label": "课文 5",
                "scene_uz": "Turmush va xarakter haqida matn",
                "word_nos": [27, 28, 29, 30, 31, 32],
                "grammar_nos": [5],
                "dialogue": [
                    _line("旁白", "说到结婚，人们就会很自然地想起爱情。爱情是结婚的重要原因，但两个人共同生活，不仅需要浪漫的爱情，更需要性格上互相吸引。", "Turmush qurish haqida gap ketganda, odamlar tabiiy ravishda sevgini eslaydi. Sevgi turmushning muhim sababi, lekin ikki kishi birga yashashi uchun nafaqat romantik sevgi, balki xarakter jihatidan o'zaro jalb qilishi ham ko'proq kerak."),
                    _line("旁白", "我丈夫是个很幽默的人。即使是很普通的事情，从他嘴里说出来也会变得很有意思。在我难过的时候，他总是有办法让我高兴起来。而且他的脾气也不错，结婚快十年了，我们俩几乎没因为什么事红过脸，很多人都特别羡慕我们。", "Erim juda hazilkash odam. Hatto juda oddiy narsalar ham uning og'zidan chiqqanda qiziqarli bo'lib ketadi. Men xafa bo'lganimda u meni xursand qilishning yo'lini topadi. Bundan tashqari fe'li ham yaxshi: turmush qurganimizga qariyb o'n yil bo'ldi, deyarli hech narsa uchun yuzimiz qizargancha urishmaganmiz, ko'p odamlar bizga juda havas qiladi."),
                ],
            },
        ],
    },
    2: {
        "title": "真正的朋友",
        "goal": {
            "uz": "do'stlik, aloqa va haqiqiy do'st haqida gapirish; 正好, 差不多, 尽管, 却, 而 grammatikalarini ishlatish",
            "ru": "говорить о дружбе, связи и настоящих друзьях; использовать 正好, 差不多, 尽管, 却, 而",
            "tj": "дар бораи дӯстӣ, иртибот ва дӯсти ҳақиқӣ гуфтугӯ кардан; истифодаи 正好, 差不多, 尽管, 却, 而",
        },
        "intro_text": {
            "uz": "Bu darsda yangi do'st orttirish, sinfdoshlar bilan aloqani saqlash va haqiqiy do'stlik haqida gapirishni o'rganasiz. Har qismda matnga mos so'zlar, tarjima va grammatika bor.",
            "ru": "В этом уроке вы научитесь говорить о новых друзьях, связи с однокурсниками и настоящей дружбе. В каждой части есть слова, перевод и грамматика по своему тексту.",
            "tj": "Дар ин дарс дар бораи пайдо кардани дӯсти нав, нигоҳ доштани робита бо ҳамсинфон ва дӯстии ҳақиқӣ гуфтугӯ карданро меомӯзед. Дар ҳар қисм калимаҳо, тарҷума ва грамматикаи мувофиқи матн ҳаст.",
        },
        "vocabulary": [
            _word(1, "适应", "shìyìng", "v.", "moslashmoq, ko'nikmoq"),
            _word(2, "交", "jiāo", "v.", "do'st orttirmoq"),
            _word(3, "平时", "píngshí", "n.", "odatdagi vaqt, odatda"),
            _word(4, "逛", "guàng", "v.", "aylanmoq, sayr qilmoq"),
            _word(5, "短信", "duǎnxìn", "n.", "SMS, qisqa xabar"),
            _word(6, "正好", "zhènghǎo", "adv.", "aynan, juda mos paytda"),
            _word(7, "聚会", "jùhuì", "v./n.", "yig'ilmoq; uchrashuv"),
            _word(8, "联系", "liánxì", "v.", "aloqa qilmoq"),
            _word(9, "差不多", "chàbuduō", "adv.", "deyarli, taxminan"),
            _word(10, "专门", "zhuānmén", "adv.", "maxsus, ataylab"),
            _word(11, "毕业", "bìyè", "v.", "bitirmoq"),
            _word(12, "麻烦", "máfan", "v.", "bezovta qilmoq, ovora qilmoq"),
            _word(13, "好像", "hǎoxiàng", "adv.", "go'yo, xuddi"),
            _word(14, "重新", "chóngxīn", "adv.", "qaytadan"),
            _word(15, "尽管", "jǐnguǎn", "conj.", "garchi, ... bo'lsa ham"),
            _word(16, "真正", "zhēnzhèng", "adj.", "haqiqiy"),
            _word(17, "友谊", "yǒuyì", "n.", "do'stlik"),
            _word(18, "丰富", "fēngfù", "v.", "boyitmoq"),
            _word(19, "无聊", "wúliáo", "adj.", "zerikarli"),
            _word(20, "讨厌", "tǎoyàn", "v.", "yoqtirmaslik"),
            _word(21, "却", "què", "adv.", "lekin, ammo"),
            _word(22, "周围", "zhōuwéi", "n.", "atrof, atrofdagilar"),
            _word(23, "交流", "jiāoliú", "v.", "muloqot qilmoq, almashmoq"),
            _word(24, "理解", "lǐjiě", "v.", "tushunmoq"),
            _word(25, "镜子", "jìngzi", "n.", "ko'zgu"),
            _word(26, "而", "ér", "conj.", "esa, ammo"),
            _word(27, "当", "dāng", "prep.", "... paytda"),
            _word(28, "困难", "kùnnan", "n.", "qiyinchilik"),
            _word(29, "及时", "jíshí", "adv.", "o'z vaqtida"),
            _word(30, "陪", "péi", "v.", "hamrohlik qilmoq"),
        ],
        "grammar": [
            _grammar(1, "正好", "aynan, juda mos paytda", "Vaqt, holat yoki imkoniyat juda mos tushganini bildiradi.", "我们下午要去踢足球，正好一起去吧。", "Biz tushdan keyin futbol o'ynashga boramiz, aynan birga boraylik."),
            _grammar(2, "差不多", "deyarli, taxminan", "Raqam yoki holat to'liq aniq emas, taxminan shunga yaqinligini bildiradi.", "差不多一半儿吧。", "Taxminan yarmi bo'lsa kerak."),
            _grammar(3, "尽管", "garchi ... bo'lsa ham", "Qarama-qarshi vaziyatni tan olib, asosiy natijani keyin beradi.", "尽管已经毕业这么多年，我们还是经常联系的。", "Garchi bitirganimizga shuncha yil bo'lgan bo'lsa ham, biz baribir tez-tez aloqada bo'lamiz."),
            _grammar(4, "却", "lekin, ammo", "Kutilgan natijaga teskari holatni ko'rsatadi.", "一个脾气不好的人虽然不一定让人讨厌，但是却很难跟人交朋友。", "Fe'li yomon odam odamlarni albatta bezdirmasligi mumkin, lekin u bilan do'stlashish qiyin."),
            _grammar(5, "而", "esa, ammo", "Ikki qarash yoki holatni taqqoslab bog'laydi.", "而我的理解是：当你遇到困难的时候，真正的朋友会站出来。", "Mening tushuncham esa shuki: qiyinchilikka duch kelganingda haqiqiy do'st oldinga chiqadi."),
        ],
        "dialogues": [
            {
                "block_no": 1,
                "section_label": "课文 1",
                "scene_uz": "小夏 va 马克 uning xitoylik do'sti haqida gaplashadi",
                "word_nos": [1, 2, 3, 4, 5, 6],
                "grammar_nos": [1],
                "dialogue": [
                    _line("小夏", "来中国快一年了，你适应这儿的生活了吗？", "Xitoyga kelganingga deyarli bir yil bo'ldi, bu yerdagi hayotga moslashdingmi?"),
                    _line("马克", "开始有点儿不习惯，后来就慢慢适应了，最近我还交了一个中国朋友。", "Boshida biroz o'rganmagan edim, keyin asta-sekin moslashdim, yaqinda yana bir xitoylik do'st orttirdim."),
                    _line("小夏", "那就好，快给我讲讲你新交的中国朋友。", "Yaxshi bo'libdi, yangi xitoylik do'sting haqida tezroq aytib ber."),
                    _line("马克", "我们是在图书馆认识的。平时我们常常一起看书、逛街、踢足球。有时候他还给我发一些幽默短信。", "Biz kutubxonada tanishganmiz. Odatda birga kitob o'qiymiz, ko'cha aylanamiz, futbol o'ynaymiz. Ba'zan u menga hazilli SMSlar ham yuboradi."),
                    _line("小夏", "你的这个朋友真不错！下次介绍我们认识认识，怎么样？", "Bu do'sting juda yaxshi ekan! Keyingi safar meni ham tanishtirsang-chi?"),
                    _line("马克", "没问题！我们下午要去踢足球，正好一起去吧。", "Muammo yo'q! Tushdan keyin futbol o'ynashga boramiz, aynan birga boraylik."),
                ],
            },
            {
                "block_no": 2,
                "section_label": "课文 2",
                "scene_uz": "小李 va 小林 sinfdoshlar uchrashuvi haqida gaplashadi",
                "word_nos": [7, 8, 9, 10, 11, 12],
                "grammar_nos": [2],
                "dialogue": [
                    _line("小李", "星期天同学聚会，你能来吗？", "Yakshanba kuni sinfdoshlar uchrashuvi, kela olasanmi?"),
                    _line("小林", "能来。班里同学你联系得怎么样了？来多少人？", "Kela olaman. Guruhdagi sinfdoshlar bilan bog'lanish qanday ketdi? Necha kishi keladi?"),
                    _line("小李", "差不多一半儿吧，张远还专门从国外飞回来呢。", "Taxminan yarmi bo'lsa kerak, Zhang Yuan hatto maxsus chetdan uchib keladi."),
                    _line("小林", "是吗？毕业都快十年了，真想大家啊！对了，今天早上，我在地铁站遇到了王静，她毕业后就去上海工作了，她这次是来旅游的。", "Rostdanmi? Bitirganimizga deyarli o'n yil bo'ldi, hammani juda sog'indim! Aytgancha, bugun ertalab metro bekatida Wang Jingni uchratdim, u bitirgandan keyin Shanghaiga ishlashga ketgandi, bu safar sayohatga kelibdi."),
                    _line("小李", "那太好了！麻烦你跟她联系一下，请她一起来参加同学聚会。聚会就在学校门口那个饭店，六点半。别迟到啊！", "Juda yaxshi! Iltimos, u bilan bog'lanib, uni ham sinfdoshlar uchrashuviga taklif qil. Uchrashuv maktab eshigi oldidagi restoranda, olti yarimda. Kech qolma!"),
                    _line("小林", "放心吧。星期天六点半见！", "Xotirjam bo'l. Yakshanba olti yarimda ko'rishamiz!"),
                ],
            },
            {
                "block_no": 3,
                "section_label": "课文 3",
                "scene_uz": "孙月 va 王静 do'stlari haqida gaplashadi",
                "word_nos": [13, 14, 15, 16, 17],
                "grammar_nos": [3],
                "dialogue": [
                    _line("孙月", "这是什么时候的照片？你真年轻！", "Bu qachongi surat? Juda yosh ekansan!"),
                    _line("王静", "这是上大学时的照片。一看到这张照片，我就想起过去那段快乐的日子，好像重新回到了校园。", "Bu universitet paytidagi surat. Bu suratni ko'rishim bilan o'tmishdagi o'sha baxtli kunlar esimga tushadi, go'yo qaytadan kampusga qaytgandek bo'laman."),
                    _line("孙月", "旁边这个人一定是你的好朋友吧？你们现在还联系吗？", "Yonindagi bu odam albatta yaqin do'sting bo'lsa kerak? Hozir ham aloqadamisizlar?"),
                    _line("王静", "当然了，尽管已经毕业这么多年，我们还是经常联系的，每次都有说不完的话。", "Albatta, garchi bitirganimizga shuncha yil bo'lgan bo'lsa ham, biz baribir tez-tez aloqada bo'lamiz, har safar gapimiz tugamaydi."),
                    _line("孙月", "真羡慕你！我上大学时最好的朋友去了南方工作，我们俩已经好久没联系了。我一会儿就给她打个电话。", "Senga juda havas qildim! Universitetdagi eng yaxshi do'stim janubga ishlashga ketgan, biz anchadan beri bog'lanmadik. Hozir unga telefon qilaman."),
                    _line("王静", "对。要知道，能有一个真正的朋友，有一段真正的友谊，是多么不容易！", "To'g'ri. Bilasanmi, haqiqiy do'stga ega bo'lish, haqiqiy do'stlikka ega bo'lish naqadar oson emas!"),
                ],
            },
            {
                "block_no": 4,
                "section_label": "课文 4",
                "scene_uz": "Do'st orttirish haqida matn",
                "word_nos": [18, 19, 20, 21, 22, 23],
                "grammar_nos": [4],
                "dialogue": [
                    _line("旁白", "每个人都需要朋友，朋友可以丰富我们的生活。离开朋友，我们的生活一定会非常无聊。那么，怎样才能交到更多的朋友呢？当然，要有好脾气。一个脾气不好的人虽然不一定让人讨厌，但是却很难跟人交朋友。因为没有人会喜欢跟一个总是容易生气的人在一起。我们还要经常跟周围的人交流。交流能让人们互相了解，如果有共同的兴趣、爱好或者习惯，就更容易成为朋友了。", "Har bir odamga do'st kerak, do'stlar hayotimizni boyitadi. Do'stlarsiz hayotimiz juda zerikarli bo'ladi. Unda ko'proq do'stni qanday orttirish mumkin? Albatta, yaxshi fe'l bo'lishi kerak. Fe'li yomon odam odamlarni albatta bezdirmasligi mumkin, lekin u bilan do'stlashish qiyin. Chunki hech kim doim oson jahli chiqadigan odam bilan birga bo'lishni yoqtirmaydi. Biz atrofimizdagi odamlar bilan tez-tez muloqot qilishimiz ham kerak. Muloqot odamlarni bir-birini tushunishga yordam beradi, agar umumiy qiziqish, hobbi yoki odat bo'lsa, do'st bo'lish osonroq bo'ladi."),
                ],
            },
            {
                "block_no": 5,
                "section_label": "课文 5",
                "scene_uz": "Haqiqiy do'st haqida matn",
                "word_nos": [24, 25, 26, 27, 28, 29, 30],
                "grammar_nos": [5],
                "dialogue": [
                    _line("旁白", "人的一生可以什么也没有，但不能没有朋友，而且必须要有自己真正的朋友。什么是真正的朋友？不同的人会有不同的理解。有些人觉得朋友就是能和自己一起快乐的人；有些人觉得朋友应该像镜子，能帮自己看到缺点。而我的理解是：当你遇到困难的时候，真正的朋友会站出来，及时给你帮助；当你无聊或者难过的时候，真正的朋友会陪在你身边，想办法让你感到幸福。", "Inson hayotida hech narsa bo'lmasligi mumkin, lekin do'stsiz bo'lishi mumkin emas, yana o'zining haqiqiy do'sti bo'lishi shart. Haqiqiy do'st nima? Turli odamlar turlicha tushunadi. Ba'zilar do'st - o'zi bilan birga xursand bo'la oladigan odam deb o'ylaydi; ba'zilar do'st ko'zgu kabi bo'lishi, o'z kamchiligini ko'ra olishga yordam berishi kerak deb o'ylaydi. Mening tushuncham esa: qiyinchilikka duch kelganingda, haqiqiy do'st oldinga chiqib, o'z vaqtida yordam beradi; zerikkaningda yoki xafa bo'lganingda, haqiqiy do'st yoningda bo'lib, seni baxtli his qildirish yo'lini topadi."),
                ],
            },
        ],
    },
    3: {
        "title": "经理对我印象不错",
        "goal": {
            "uz": "intervyu, ishga qabul qilish va birinchi taassurot haqida gapirish; 挺, 本来, 另外, 首先, 不管 grammatikalarini ishlatish",
            "ru": "говорить о собеседовании, найме и первом впечатлении; использовать 挺, 本来, 另外, 首先, 不管",
            "tj": "дар бораи мусоҳиба, қабул ба кор ва таассуроти аввал гуфтугӯ кардан; истифодаи 挺, 本来, 另外, 首先, 不管",
        },
        "intro_text": {
            "uz": "Bu darsda ish intervyusi, ishga qabul, kasb va birinchi taassurot haqida gapirishni o'rganasiz. Har qismda shu matnga tegishli yangi so'zlar, pinyin, tarjima va grammatika beriladi.",
            "ru": "В этом уроке вы научитесь говорить о собеседовании, найме, профессии и первом впечатлении. В каждой части будут слова, pinyin, перевод и грамматика именно к этому тексту.",
            "tj": "Дар ин дарс дар бораи мусоҳибаи кор, қабул ба кор, касб ва таассуроти аввал гуфтугӯ карданро меомӯзед. Дар ҳар қисм калимаҳои нав, pinyin, тарҷума ва грамматикаи ҳамон матн дода мешавад.",
        },
        "vocabulary": [
            _word(1, "挺", "tǐng", "adv.", "ancha, juda"),
            _word(2, "紧张", "jǐnzhāng", "adj.", "hayajonlangan, asabiy"),
            _word(3, "信心", "xìnxīn", "n.", "ishonch"),
            _word(4, "能力", "nénglì", "n.", "qobiliyat"),
            _word(5, "招聘", "zhāopìn", "v.", "ishga qabul qilmoq, xodim izlamoq"),
            _word(6, "提供", "tígōng", "v.", "taqdim qilmoq, bermoq"),
            _word(7, "负责", "fùzé", "v.", "mas'ul bo'lmoq"),
            _word(8, "本来", "běnlái", "adv.", "aslida, boshida"),
            _word(9, "应聘", "yìngpìn", "v.", "ishga ariza bermoq"),
            _word(10, "材料", "cáiliào", "n.", "material, hujjat"),
            _word(11, "符合", "fúhé", "v.", "mos kelmoq"),
            _word(12, "通知", "tōngzhī", "v.", "xabar bermoq"),
            _word(13, "律师", "lǜshī", "n.", "advokat, yurist"),
            _word(14, "专业", "zhuānyè", "n.", "mutaxassislik, yo'nalish"),
            _word(15, "另外", "lìngwài", "conj.", "bundan tashqari"),
            _word(16, "收入", "shōurù", "n.", "daromad"),
            _word(17, "咱们", "zánmen", "pron.", "biz"),
            _word(18, "安排", "ānpái", "v.", "tartibga solmoq, rejalashtirmoq"),
            _word(19, "首先", "shǒuxiān", "pron.", "avvalo, birinchi navbatda"),
            _word(20, "正式", "zhèngshì", "adj.", "rasmiy"),
            _word(21, "留", "liú", "v.", "qoldirmoq"),
            _word(22, "其次", "qícì", "pron.", "ikkinchidan, keyin"),
            _word(23, "诚实", "chéngshí", "adj.", "halol, rostgo'y"),
            _word(24, "改变", "gǎibiàn", "v.", "o'zgartirmoq"),
            _word(25, "感觉", "gǎnjué", "n.", "his, taassurot"),
            _word(26, "判断", "pànduàn", "v.", "hukm qilmoq, baholamoq"),
            _word(27, "顾客", "gùkè", "n.", "mijoz"),
            _word(28, "准时", "zhǔnshí", "adj.", "vaqtida, punktual"),
            _word(29, "不管", "bùguǎn", "conj.", "nima bo'lishidan qat'i nazar"),
            _word(30, "与", "yǔ", "prep.", "bilan"),
            _word(31, "约会", "yuēhuì", "v.", "uchrashuvga chiqmoq, uchrashmoq"),
        ],
        "grammar": [
            _grammar(1, "挺", "ancha, juda", "Og'zaki tilda sifat yoki holat darajasini yumshoq kuchaytiradi.", "他们问的问题都挺容易的。", "Ular so'ragan savollar ancha oson edi."),
            _grammar(2, "本来", "aslida, boshida", "Dastlabki reja yoki oldingi holatni bildiradi; keyin ko'pincha o'zgarish keladi.", "本来是小李负责的，但是他突然生病住院了。", "Aslida Xiao Li mas'ul edi, lekin u to'satdan kasal bo'lib kasalxonaga yotdi."),
            _grammar(3, "另外", "bundan tashqari", "Oldingi fikrga qo'shimcha sabab yoki ma'lumot qo'shadi.", "另外，收入也不错。", "Bundan tashqari, daromadi ham yaxshi."),
            _grammar(4, "首先", "avvalo, birinchi navbatda", "Bir nechta maslahat yoki qadamning birinchisini ko'rsatadi.", "首先，要穿正式的衣服。", "Avvalo, rasmiy kiyim kiyish kerak."),
            _grammar(5, "不管……都……", "nima bo'lishidan qat'i nazar", "Shart qanday bo'lishidan qat'i nazar natija bir xil qolishini bildiradi.", "不管是上课、上班，还是与别人约会，准时都非常重要。", "Dars bo'ladimi, ish bo'ladimi yoki boshqalar bilan uchrashuv bo'ladimi, vaqtida borish juda muhim."),
        ],
        "dialogues": [
            {
                "block_no": 1,
                "section_label": "课文 1",
                "scene_uz": "小夏 va 小雨 intervyu haqida gaplashadi",
                "word_nos": [1, 2, 3, 4, 5, 6],
                "grammar_nos": [1],
                "dialogue": [
                    _line("小夏", "你上午的面试怎么样？", "Ertalabki intervyuing qanday bo'ldi?"),
                    _line("小雨", "还可以，他们问的问题都挺容易的，就是我有点儿紧张。", "Yomon emas, ular so'ragan savollar ancha oson edi, faqat men biroz hayajonlandim."),
                    _line("小夏", "面试的时候，一定要对自己有信心，要相信自己的能力。", "Intervyu paytida albatta o'zingga ishonishing, o'z qobiliyatingga ishonishing kerak."),
                    _line("小雨", "你说的对！3月15号上午8点在学校体育馆还有一个招聘会，你去吗？", "To'g'ri aytding! 15-mart ertalab soat 8 da maktab sport zalida yana bir ish yarmarkasi bor, borasanmi?"),
                    _line("小夏", "我还没决定呢。", "Hali qaror qilmadim."),
                    _line("小雨", "听说这次招聘会提供的工作机会很多，我们一起去看看吧。", "Eshitishimcha bu ish yarmarkasi ko'p ish imkoniyatlarini taqdim qiladi, birga borib ko'raylik."),
                ],
            },
            {
                "block_no": 2,
                "section_label": "课文 2",
                "scene_uz": "马经理 va 小林 ishga qabul qilish haqida gaplashadi",
                "word_nos": [7, 8, 9, 10, 11, 12],
                "grammar_nos": [2],
                "dialogue": [
                    _line("马经理", "小林，这次招聘不是小李负责吗？", "Xiao Lin, bu safargi ishga qabulga Xiao Li mas'ul emasmi?"),
                    _line("小林", "本来是小李负责的，但是他突然生病住院了，所以就交给我来做了。", "Aslida Xiao Li mas'ul edi, lekin u to'satdan kasal bo'lib kasalxonaga yotdi, shuning uchun menga topshirildi."),
                    _line("马经理", "哦，这次应聘的人多吗？", "Ha, bu safar ishga ariza berganlar ko'pmi?"),
                    _line("小林", "经理，这次来应聘的一共有15人。经过笔试和面试，有两个不错。这是他们的材料，您看看。", "Menejer, bu safar jami 15 kishi ishga ariza berdi. Yozma imtihon va intervyudan keyin ikkitasi yaxshi chiqdi. Mana ularning materiallari, ko'rib chiqing."),
                    _line("马经理", "这两个人的能力都比较符合我们的要求。你通知他们下周一上午九点来我办公室吧。", "Bu ikki kishining qobiliyati talablarimizga ancha mos. Ularga kelasi dushanba ertalab soat to'qqizda mening ofisimga kelishlarini xabar qil."),
                    _line("小林", "好的，那我马上跟他们联系。", "Xo'p, unda hoziroq ular bilan bog'lanaman."),
                ],
            },
            {
                "block_no": 3,
                "section_label": "课文 3",
                "scene_uz": "小林 va 王静 uning ishi haqida gaplashadi",
                "word_nos": [13, 14, 15, 16, 17, 18],
                "grammar_nos": [3],
                "dialogue": [
                    _line("小林", "王静，好久不见了！大学毕业后就没联系了，你现在在哪儿工作呢？", "Wang Jing, anchadan beri ko'rishmadik! Universitetni bitirgandan beri aloqada bo'lmadik, hozir qayerda ishlayapsan?"),
                    _line("王静", "我一毕业就去上海当律师了。", "Bitirishim bilan Shanghaiga advokat bo'lib ishlashga ketdim."),
                    _line("小林", "你对现在的工作一定非常满意吧？", "Hozirgi ishingdan albatta juda mamnundirsan?"),
                    _line("王静", "我很喜欢现在的工作，因为我学的就是法律专业，而且同事们都很喜欢我。另外，收入也不错。", "Hozirgi ishimni juda yoqtiraman, chunki men o'qigan yo'nalish aynan huquq, hamkasblarim ham meni juda yoqtiradi. Bundan tashqari, daromadi ham yaxshi."),
                    _line("小林", "星期天咱们同学聚会，你能来参加吗？", "Yakshanba kuni sinfdoshlar uchrashuvi, qatnasha olasanmi?"),
                    _line("王静", "能来。虽然这次来北京，时间安排得很紧张，但我一定借这次机会去跟大家见见面。", "Kela olaman. Bu safar Pekinga kelganimda vaqt jadvalim juda tig'iz bo'lsa ham, men albatta shu imkoniyatdan foydalanib hamma bilan uchrashaman."),
                ],
            },
            {
                "block_no": 4,
                "section_label": "课文 4",
                "scene_uz": "Intervyuda nimalarga e'tibor berish haqida matn",
                "word_nos": [19, 20, 21, 22, 23],
                "grammar_nos": [4],
                "dialogue": [
                    _line("旁白", "面试的时候，经理对我印象不错，还通知我明天就可以上班了。真没想到，我工作这么顺利。你想知道面试需要注意什么吗？首先，要穿正式的衣服，这会给面试者留下一个好的印象，让他觉得你是一个认真的人。其次，应聘时不要紧张。回答问题时，说得不要太快，声音也不要太小，要相信自己有能力做好。当然，最重要的是回答问题要诚实。", "Intervyu paytida menejer menda yaxshi taassurot oldi, yana menga ertagayoq ishga chiqishim mumkinligini xabar qildi. Rostdan ham o'ylamagandim, ishim shunchalik silliq ketdi. Intervyuda nimalarga e'tibor berish kerakligini bilmoqchimisiz? Avvalo, rasmiy kiyim kiyish kerak, bu intervyu oluvchida yaxshi taassurot qoldiradi va u sizni jiddiy odam deb o'ylaydi. Ikkinchidan, ishga ariza berganda hayajonlanmaslik kerak. Savollarga javob berayotganda juda tez gapirmang, ovozingiz ham juda past bo'lmasin, o'zingizda yaxshi bajarish qobiliyati borligiga ishoning. Albatta, eng muhimi savollarga halol javob berishdir."),
                ],
            },
            {
                "block_no": 5,
                "section_label": "课文 5",
                "scene_uz": "Birinchi taassurot haqida matn",
                "word_nos": [24, 25, 26, 27, 28, 29, 30, 31],
                "grammar_nos": [5],
                "dialogue": [
                    _line("旁白", "第一印象就是在第一次见面时给别人留下的印象。虽然第一印象不总是对的，但如果想改变却很困难。你给别人的第一印象会影响他们以后对你的感觉和判断。所以，给第一次见面的同事留下好的印象，以后的工作可能会更顺利；给第一次见面的顾客留下好的印象，你可能会卖出更多的东西。但是，如果第一次见面给别人留下像不准时这样的坏印象，那么以后就很难让别人相信你。所以不管是上课、上班，还是与别人约会，准时都非常重要。", "Birinchi taassurot - birinchi uchrashuvda boshqalarda qoldirgan taassurotingiz. Birinchi taassurot doim to'g'ri bo'lmasa ham, uni o'zgartirish juda qiyin. Siz boshqalarda qoldirgan birinchi taassurot ularning keyinchalik siz haqingizdagi hislari va bahosiga ta'sir qiladi. Shuning uchun birinchi marta uchrashgan hamkasbda yaxshi taassurot qoldirsangiz, keyingi ish yanada silliq bo'lishi mumkin; birinchi marta uchrashgan mijozda yaxshi taassurot qoldirsangiz, ko'proq narsa sotishingiz mumkin. Lekin birinchi uchrashuvda boshqalarda vaqtida kelmaslik kabi yomon taassurot qoldirsangiz, keyinchalik boshqalarni sizga ishontirish qiyin bo'ladi. Shuning uchun dars bo'ladimi, ish bo'ladimi yoki boshqalar bilan uchrashuv bo'ladimi, vaqtida borish juda muhim."),
                ],
            },
        ],
    },
}


def _word_by_no(vocab, no):
    for word in vocab:
        if int(word.get("no") or 0) == int(no):
            return word
    return {}


def _grammar_by_no(grammar, no):
    for item in grammar:
        if int(item.get("no") or 0) == int(no):
            return item
    return {}


def _options(answer, pool):
    options = [answer]
    for value in pool:
        if value and value not in options:
            options.append(value)
        if len(options) == 4:
            break
    return options


def _meaning(word, lang):
    return word.get(lang) or word.get("uz") or word.get("meaning") or ""


def _grammar_title(item, lang):
    return item.get(f"title_{lang}") or item.get("title_uz") or item.get("title_zh") or ""


def _grammar_rule(item, lang):
    return item.get(f"rule_{lang}") or item.get("rule_uz") or item.get("rule") or ""


def _localize_materials(data):
    for word in data.get("vocabulary", []):
        word.update(VOCAB_I18N.get(word.get("zh") or "", {}))

    for item in data.get("grammar", []):
        loc = GRAMMAR_I18N.get(item.get("title_zh") or "", {})
        if loc:
            item.update(
                {
                    "title_ru": loc["title_ru"],
                    "title_tj": loc["title_tj"],
                    "rule_ru": loc["rule_ru"],
                    "rule_tj": loc["rule_tj"],
                }
            )
            for example in item.get("examples") or []:
                example["pinyin"] = loc["example_pinyin"]
                example["ru"] = loc["example_ru"]
                example["tj"] = loc["example_tj"]

    for block in data.get("dialogues", []):
        scene_uz = block.get("scene_uz") or ""
        scene_loc = SCENE_I18N.get(scene_uz, {})
        if scene_loc:
            block["scene_ru"] = scene_loc["ru"]
            block["scene_tj"] = scene_loc["tj"]

        for line in block.get("dialogue") or []:
            loc = LINE_I18N.get(line.get("zh") or "", {})
            if loc:
                line["pinyin"] = loc["pinyin"]
                line["ru"] = loc["ru"]
                line["tj"] = loc["tj"]

    return data


def _mini_quiz(lesson_order, block_no, vocab, grammar, block):
    words = [_word_by_no(vocab, no) for no in block.get("word_nos", [])]
    words = [word for word in words if word]
    meaning_pool = [word.get("uz") or "" for word in vocab]
    meaning_pool_ru = [word.get("ru") or "" for word in vocab]
    meaning_pool_tj = [word.get("tj") or "" for word in vocab]
    hanzi_pool = [word.get("zh") or "" for word in vocab]
    grammar_pool = [item.get("title_zh") or "" for item in grammar]
    quiz = []

    if words:
        word = words[0]
        answer = word.get("uz") or ""
        quiz.append(
            {
                "type": "meaning",
                "prompt_uz": f"“{word.get('zh')}” nimani anglatadi?",
                "prompt_ru": f"Что означает “{word.get('zh')}”?",
                "prompt_tj": f"“{word.get('zh')}” чӣ маъно дорад?",
                "answer": answer,
                "options": _options(answer, meaning_pool),
                "answer_ru": word.get("ru") or "",
                "options_ru": _options(word.get("ru") or "", meaning_pool_ru),
                "answer_tj": word.get("tj") or "",
                "options_tj": _options(word.get("tj") or "", meaning_pool_tj),
            }
        )

    if len(words) > 1:
        word = words[1]
        answer = word.get("zh") or ""
        quiz.append(
            {
                "type": "hanzi",
                "prompt_uz": f"“{word.get('uz')}” qaysi so'z?",
                "prompt_ru": f"Какое слово означает “{word.get('ru')}”?",
                "prompt_tj": f"Кадом калима маънои “{word.get('tj')}”-ро дорад?",
                "answer": answer,
                "options": _options(answer, hanzi_pool),
            }
        )

    grammar_nos = block.get("grammar_nos") or []
    if grammar_nos:
        item = _grammar_by_no(grammar, grammar_nos[0])
        answer = item.get("title_zh") or ""
        example = (item.get("examples") or [{}])[0].get("zh") or ""
        quiz.append(
            {
                "type": "grammar",
                "prompt_uz": f"“{example}” gapida qaysi grammatika ishlatilgan?",
                "prompt_ru": f"Какая грамматика используется в этом предложении?\n“{example}”",
                "prompt_tj": f"Дар ин ҷумла кадом грамматика истифода шудааст?\n“{example}”",
                "answer": answer,
                "options": _options(answer, grammar_pool),
            }
        )

    for index, item in enumerate(quiz, 1):
        item["lesson_order"] = lesson_order
        item["block_no"] = block_no
        item["no"] = index
    return quiz


def _mini_homework(block_no, words):
    return {
        "block_no": block_no,
        "instruction_uz": "Shu qismdagi yangi so'zlardan 1-2 ta sodda gap yozing.",
        "instruction_ru": "Напишите 1-2 простых предложения с новыми словами этой части.",
        "instruction_tj": "Бо калимаҳои нави ҳамин қисм 1-2 ҷумлаи содда нависед.",
        "words": [word.get("zh") for word in words if word.get("zh")],
    }


def _exercise_payload(vocab, grammar):
    word_items = [
        {
            "prompt_uz": f"{word['zh']} ({word['pinyin']})",
            "prompt_ru": f"{word['zh']} ({word['pinyin']})",
            "prompt_tj": f"{word['zh']} ({word['pinyin']})",
            "answer": word["uz"],
            "answer_ru": _meaning(word, "ru"),
            "answer_tj": _meaning(word, "tj"),
            "pinyin": word["pinyin"],
        }
        for word in vocab[:5]
    ]
    grammar_items = [
        {
            "prompt_uz": (item.get("examples") or [{}])[0].get("zh") or item.get("title_zh"),
            "prompt_ru": (item.get("examples") or [{}])[0].get("zh") or item.get("title_zh"),
            "prompt_tj": (item.get("examples") or [{}])[0].get("zh") or item.get("title_zh"),
            "answer": item.get("title_zh"),
            "answer_ru": _grammar_title(item, "ru"),
            "answer_tj": _grammar_title(item, "tj"),
        }
        for item in grammar[:3]
    ]
    exercises = [
        {
            "no": 1,
            "type": "word_meaning",
            "instruction_uz": "Quyidagi yangi so'zlarning ma'nosini yozing:",
            "instruction_ru": "Напишите значения следующих новых слов:",
            "instruction_tj": "Маънои калимаҳои нави зеринро нависед:",
            "items": word_items,
        },
        {
            "no": 2,
            "type": "grammar_identify",
            "instruction_uz": "Gapda qaysi grammatika ishlatilganini yozing:",
            "instruction_ru": "Напишите, какая грамматика используется в предложении:",
            "instruction_tj": "Нависед, дар ҷумла кадом грамматика истифода шудааст:",
            "items": grammar_items,
        },
    ]
    answers = [
        {"no": 1, "answers": [item["answer"] for item in word_items]},
        {"no": 2, "answers": [item["answer"] for item in grammar_items]},
    ]
    return exercises, answers


def _homework_payload(vocab, grammar):
    return [
        {
            "no": 1,
            "instruction_uz": "Bugungi yangi so'zlardan kamida 5 tasini ishlatib 5-6 gap yozing.",
            "instruction_ru": "Напишите 5-6 предложений, используя минимум 5 новых слов сегодняшнего урока.",
            "instruction_tj": "Бо истифода аз ҳадди ақал 5 калимаи нави дарси имрӯз 5-6 ҷумла нависед.",
            "words": [word["zh"] for word in vocab[:10]],
        },
        {
            "no": 2,
            "instruction_uz": "Bugungi grammatikalardan 2 tasini tanlab, har biriga bittadan gap tuzing.",
            "instruction_ru": "Выберите 2 грамматики сегодняшнего урока и составьте по одному предложению к каждой.",
            "instruction_tj": "Аз грамматикаҳои имрӯза 2-то интихоб карда, барои ҳар кадом як ҷумла созед.",
            "words": [item["title_zh"] for item in grammar],
        },
    ]


def apply_hsk4_upper_pdf_materials(lesson):
    raw_data = HSK4_UPPER_PDF_MATERIALS.get(int(lesson.get("lesson_order") or 0))
    data = copy.deepcopy(raw_data) if raw_data else None
    if not data:
        return lesson
    data = _localize_materials(data)

    vocab = data["vocabulary"]
    grammar = data["grammar"]
    dialogues = data["dialogues"]

    for block in dialogues:
        block_no = int(block.get("block_no") or 0)
        words = [_word_by_no(vocab, no) for no in block.get("word_nos", [])]
        words = [word for word in words if word]
        block["mini_quiz"] = _mini_quiz(lesson["lesson_order"], block_no, vocab, grammar, block)
        block["mini_homework"] = _mini_homework(block_no, words)

    exercises, answers = _exercise_payload(vocab, grammar)
    lesson["title"] = data["title"]
    lesson["goal"] = _j(data["goal"])
    lesson["intro_text"] = _j(data["intro_text"])
    lesson["vocabulary_json"] = _j(vocab)
    lesson["grammar_json"] = _j(grammar)
    lesson["dialogue_json"] = _j(dialogues)
    lesson["exercise_json"] = _j(exercises)
    lesson["answers_json"] = _j(answers)
    lesson["homework_json"] = _j(_homework_payload(vocab, grammar))
    return lesson
