/* CourseAds — mustaqil reklama moduli.
 *
 * Ilgari bu oqim faqat course-v3.html darslarida edi. Endi reklama darslardan
 * mashq bo'limlariga ko'chdi, shuning uchun oqim shu yerga — har bir mashq
 * sahifasi (recognition/pronunciation/memorize/test) foydalana oladigan qilib —
 * mustaqil modul sifatida chiqarildi. Mantiq darsdagidek: bir yoki bir nechta
 * reklama ketma-ket majburiy ko'rsatiladi, tugagach "Obuna ol / Reklama bilan
 * davom et" tanlovi chiqadi.
 *
 * Foydalanish:
 *   CourseAds.config({lang:"uz", initData:tg.initData, feature:"recognition",
 *                     level:"hsk1", onSubscribe:function(){ ... }});
 *   CourseAds.play("start", accessRef).then(runSession).catch(showRetry);
 *
 * play(placement, accessRef) — "start" | "middle" | "end". Protected start
 * oqimida accessRef beriladi; server reklama ko'rilganini aynan shu sessiyaga
 * bog'laydi. Reklama yoki server yozuvi muvaffaqiyatsiz bo'lsa Promise reject. */
(function(){
  /* slot: "" (mashq bo'limlari) yoki "lesson_end" (dars yakuni bloki —
     server faqat `dars_yakuni` turidagi reklamani qaytaradi, oxirida esa
     obuna knopkasi va sozlangan bo'lsa tashqi CTA chiqadi).
     lessonOrder — dars yakunida qaysi qism edi. */
  var CFG = {lang:"uz", initData:"", feature:"", level:"hsk1", slot:"", lessonOrder:0, onSubscribe:null, onOffer:null};
  function isLessonEnd(){return CFG.slot==="lesson_end"}

  /* Darsdagi T() ad-* kalitlaridan olingan matnlar (3 til). */
  var I18N = {
    uz:{adStart:"Bo'limdan oldingi reklama",adMiddle:"Qisqa reklama pauzasi",adEnd:"Yakuniy reklama",adReady:"Davom etish",adNote:"Rolikni oxirigacha ko'ring. Premium reklamasisiz o'qiydi.",adSubTitle:"Obuna bo'ling — botdan reklamasiz va hech qanday limitsiz foydalaning",adSubPay:"Obuna olish",adSubCont:"Reklama bilan davom etish",adVisit:"Havolaga o'tish",adOpenLink:"Reklama havolasini ochasizmi?",b1:"Barcha HSK 1–4 darslar",b2:"AI Voice — cheksiz",b3:"Cheksiz test va xatolar mashqi",loading:"Reklama yuklanmoqda...",failed:"Reklama videosi yuklanmadi",failedNote:"Ekran qora qolsa, video MP4 H.264/AAC formatida bo'lishi kerak.",limitSubscribe:"Obunani ochish",limitAd:"Yoki reklama ko'rib davom etish",limitWhy:"Bugungi bepul mashqing tugadi: «{s}» bepul rejimda kuniga 1 marta ochiladi. Ertaga yana bepul ochiladi — obuna bilan esa bugun ham cheklovsiz davom etasan.",limitWhyPlain:"Bugungi bepul limiting tugadi. Ertaga yana bepul ochiladi — obuna bilan esa bugun ham cheklovsiz davom etasan.",psWrite:"Hamkorlik uchun yozing",psTry:"Sinab ko'rish",psCopy:"Nusxalash",psCopied:"Nusxalandi ✓",psShare:"Do'stga yuborish",
        leLabel:"Dars yakuni · reklama",leNote:"Qisqa rolik. Obuna bo'lsangiz reklama umuman chiqmaydi.",leSubTitle:"Darsni tugatdingiz — endi to'liq yo'lni oching",leExternal:"Reklama havolasini ochish",
        appCta:"Yuklab olish",appCloseIn:"Yopish {s}s",
        f_recognition:"Ieroglif tanish",f_pronunciation:"Talaffuz mashqi",f_memorize:"Yodlash",f_training_test:"Test markazi",f_placement:"Daraja aniqlash testi",f_mistake_review:"Xatolar ustida ishlash"},
    ru:{adStart:"Реклама перед разделом",adMiddle:"Короткая пауза",adEnd:"Последняя реклама",adReady:"Продолжить",adNote:"Посмотрите ролик до конца. Premium учится без рекламы.",adSubTitle:"Оформите подписку — и пользуйтесь ботом без рекламы и без ограничений",adSubPay:"Оформить подписку",adSubCont:"Продолжить с рекламой",adVisit:"Перейти по ссылке",adOpenLink:"Открыть ссылку рекламодателя?",b1:"Все уроки HSK 1–4",b2:"AI Voice — безлимит",b3:"Безлимит тестов и работа над ошибками",loading:"Загрузка рекламы...",failed:"Видео рекламы не загрузилось",failedNote:"Если экран остаётся чёрным, нужен MP4 H.264/AAC.",limitSubscribe:"Открыть подписку",limitAd:"Или продолжить с рекламой",limitWhy:"Бесплатная практика на сегодня закончилась: «{s}» в бесплатном режиме открывается 1 раз в день. Завтра снова бесплатно — а с подпиской продолжите без ограничений уже сегодня.",limitWhyPlain:"Бесплатный лимит на сегодня исчерпан. Завтра снова бесплатно — а с подпиской продолжите без ограничений уже сегодня.",psWrite:"Написать для сотрудничества",psTry:"Попробовать",psCopy:"Копировать",psCopied:"Скопировано ✓",psShare:"Другу",
        leLabel:"Конец урока · реклама",leNote:"Короткий ролик. С подпиской рекламы не будет вообще.",leSubTitle:"Урок пройден — откройте весь путь",leExternal:"Открыть ссылку рекламы",
        appCta:"Скачать",appCloseIn:"Закрыть через {s}с",
        f_recognition:"Распознавание иероглифов",f_pronunciation:"Произношение",f_memorize:"Запоминание",f_training_test:"Тест-центр",f_placement:"Тест на уровень",f_mistake_review:"Работа над ошибками"},
    tj:{adStart:"Реклама пеш аз бахш",adMiddle:"Танаффуси кӯтоҳи реклама",adEnd:"Рекламаи охирин",adReady:"Идома",adNote:"Роликро то охир бинед. Premium бе реклама меомӯзад.",adSubTitle:"Обуна шавед — аз бот бе реклама ва бе ягон маҳдудият истифода баред",adSubPay:"Обуна шудан",adSubCont:"Идома бо реклама",adVisit:"Гузаштан ба ҳавола",adOpenLink:"Ҳаволаи рекламаро мекушоед?",b1:"Ҳамаи дарсҳои HSK 1–4",b2:"AI Voice — бепоён",b3:"Тестҳои бепоён ва кор бар хатоҳо",loading:"Реклама бор мешавад...",failed:"Видеои реклама бор нашуд",failedNote:"Агар экран сиёҳ монад, видео бояд MP4 H.264/AAC бошад.",limitSubscribe:"Кушодани обуна",limitAd:"Ё бо реклама идома додан",limitWhy:"Машқи ройгони имрӯза тамом шуд: «{s}» дар ҳолати ройгон рӯзе 1 маротиба кушода мешавад. Фардо боз ройгон — бо обуна бошад, ҳамин имрӯз бе маҳдудият идома медиҳӣ.",limitWhyPlain:"Лимити ройгони имрӯза тамом шуд. Фардо боз ройгон — бо обуна бошад, ҳамин имрӯз бе маҳдудият идома медиҳӣ.",psWrite:"Барои ҳамкорӣ нависед",psTry:"Санҷидан",psCopy:"Нусха",psCopied:"Нусха шуд ✓",psShare:"Ба дӯст",
        leLabel:"Анҷоми дарс · реклама",leNote:"Ролики кӯтоҳ. Бо обуна реклама тамоман намешавад.",leSubTitle:"Дарсро тамом кардед — тамоми роҳро кушоед",leExternal:"Кушодани ҳаволаи реклама",
        appCta:"Боргирӣ",appCloseIn:"Пӯшидан пас аз {s}с",
        f_recognition:"Шинохти иероглиф",f_pronunciation:"Машқи талаффуз",f_memorize:"Азёдкунӣ",f_training_test:"Маркази тест",f_placement:"Тести муайянкунии сатҳ",f_mistake_review:"Кор бар хатоҳо"}
  };
  function T(){ return I18N[CFG.lang] || I18N.uz; }
  /* "Nega bu oyna chiqdi?" — limit ekranida sababni ochiq aytamiz: qaysi bo'lim,
     qanday limit, qachon yana ochiladi. Bo'lim nomi topilmasa umumiy matn. */
  function limitWhyText(feature){
    var t=T(),name=t["f_"+String(feature||"")];
    if(!name)return t.limitWhyPlain||"";
    return String(t.limitWhy||"").replace("{s}",name);
  }

  var PROMO = {
    uz:[{i:"microphone-2",t:"Birinchi kundan gapirasan",s:"Panda 阿宝 sabr bilan tinglaydi va xatoingni yumshoq tuzatadi"},
        {i:"books",t:"Adashmaysan — yo'l tayyor",s:"HSK 1–4: har kuni aniq keyingi qadam ko'rsatiladi"},
        {i:"clipboard-check",t:"Imtihonga ishonch bilan borasan",s:"Cheksiz test va aniq daraja — qayerda turganingni bilasan"},
        {i:"target-arrow",t:"Xatoing yo'qolmaydi",s:"Har xato ustida ishlab, uni butunlay o'zlashtirasan"},
        {i:"infinity",t:"Diqqating faqat o'rganishda",s:"Reklama va limitlarsiz — hech narsa chalg'itmaydi"}],
    ru:[{i:"microphone-2",t:"Заговоришь с первого дня",s:"Панда 阿宝 терпеливо слушает и мягко исправляет ошибки"},
        {i:"books",t:"Не собьёшься с пути",s:"HSK 1–4: каждый день — понятный следующий шаг"},
        {i:"clipboard-check",t:"Придёшь на экзамен уверенно",s:"Безлимит тестов и точный уровень — знаешь, где ты"},
        {i:"target-arrow",t:"Ошибки не теряются",s:"Прорабатываешь каждую и осваиваешь до конца"},
        {i:"infinity",t:"Внимание только на учёбе",s:"Без рекламы и лимитов — ничто не отвлекает"}],
    tj:[{i:"microphone-2",t:"Аз рӯзи аввал гап мезанӣ",s:"Панда 阿宝 бо сабр гӯш мекунад ва хатоятро нарм ислоҳ мекунад"},
        {i:"books",t:"Аз роҳ намемонӣ",s:"HSK 1–4: ҳар рӯз қадами оянда равшан аст"},
        {i:"clipboard-check",t:"Ба имтиҳон боварӣ меравӣ",s:"Тести бепоён ва сатҳи аниқ — медонӣ дар куҷоӣ"},
        {i:"target-arrow",t:"Хатоҳо гум намешаванд",s:"Ҳар хаторо кор карда, пурра аз худ мекунӣ"},
        {i:"infinity",t:"Диққат танҳо ба омӯзиш",s:"Бе реклама ва маҳдудият — ҳеҷ чиз халал намерасонад"}]
  };
  function promoSlides(){ return PROMO[CFG.lang] || PROMO.uz; }

  var CSS = ''
  +'.caa-ov{position:fixed;inset:0;z-index:9000;background:#15120f;display:none;max-width:480px;margin:0 auto;color:#fff;font-family:inherit}'
  +'.caa-ov.on{display:flex;flex-direction:column}'
  +'.caa-box{min-height:100%;display:grid;grid-template-rows:auto minmax(0,1fr) auto;padding:calc(14px + env(safe-area-inset-top,0px)) 14px calc(16px + env(safe-area-inset-bottom,0px));gap:12px}'
  +'.caa-top{display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:12px;color:rgba(255,255,255,.78);font-weight:600}'
  +'.caa-count{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);border-radius:20px;padding:7px 10px;white-space:nowrap}'
  +'.caa-vwrap{position:relative;min-height:0;height:100%;display:block}'
  +'.caa-video,.caa-photo{width:100%;height:100%;min-height:320px;max-height:none;object-fit:contain;background:#000;border-radius:16px;border:1px solid rgba(255,255,255,.12)}'
  +'.caa-video[hidden],.caa-photo[hidden]{display:none!important}'
  +'.caa-visit{position:absolute;left:10px;bottom:10px;display:inline-flex;align-items:center;gap:6px;background:rgba(0,0,0,.6);border:1px solid rgba(255,255,255,.24);color:#fff;border-radius:20px;padding:7px 12px;font-size:12px;font-weight:600;-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}'
  +'.caa-status{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;padding:20px;border-radius:16px;background:rgba(0,0,0,.58);color:#fff;font-size:14px;font-weight:600;line-height:1.35}'
  +'.caa-status[hidden]{display:none!important}'
  +'.caa-meta{display:grid;gap:8px}'
  +'.caa-meta b{font-size:15px;font-weight:600}.caa-meta small{font-size:12px;color:rgba(255,255,255,.68);line-height:1.4}'
  +'.caa-cta{width:100%;border:none;border-radius:14px;padding:15px;font-family:inherit;font-size:15px;font-weight:600;background:#fff;color:#211D17;display:flex;align-items:center;justify-content:center;gap:8px}'
  +'.caa-cta:disabled{background:rgba(255,255,255,.14);color:rgba(255,255,255,.62)}'
  +'.caa-cta:active:not(:disabled){transform:translateY(1px)}'
  +'.caa-sub{display:grid;gap:11px;background:linear-gradient(180deg,rgba(255,255,255,.10),rgba(255,255,255,.035));border:1px solid rgba(255,255,255,.14);border-radius:20px;padding:18px 16px;box-shadow:0 12px 34px rgba(0,0,0,.38),inset 0 1px 0 rgba(255,255,255,.08)}'
  +'.caa-sub[hidden]{display:none!important}'
  +'.caa-sub-t{margin:2px 0 4px;font-size:15px;line-height:1.42;color:#fff;text-align:center;font-weight:700;letter-spacing:-.01em}'
  +'.caa-benefits{display:grid;gap:10px;margin:0 0 4px;padding:13px 13px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.08);border-radius:15px}'
  +'.caa-ben{display:flex;align-items:center;gap:11px;font-size:14px;line-height:1.35;color:rgba(255,255,255,.95);text-align:left}'
  +'.caa-ben i{color:#7BE0B3;font-size:20px;flex-shrink:0}'
  +'.caa-pay{background:linear-gradient(180deg,#ffffff,#f1eee9);color:#211D17;font-weight:700;box-shadow:0 8px 24px rgba(0,0,0,.28),0 0 0 1px rgba(255,255,255,.5) inset}'
  +'.caa-cta.ghost{background:rgba(255,255,255,.08);color:rgba(255,255,255,.9);border:1px solid rgba(255,255,255,.16);font-weight:600}'
  +'.caa-ov.caa-done .caa-top{display:none}'
  +'.caa-ov.caa-done .caa-box{grid-template-rows:minmax(0,1fr) auto}'
  +'.caa-ov.caa-done .caa-meta>b,.caa-ov.caa-done .caa-meta>small,.caa-ov.caa-done .caa-cta0{display:none}'
  +'.caa-ov.caa-done .caa-benefits{display:none}'
  +'.caa-ov.caa-done .caa-sub{gap:8px;padding:14px}'
  +'.caa-ov.caa-done .caa-sub-t{font-size:14px;margin:0 0 2px}'
  +'.caa-ov.caa-done .caa-pay,.caa-ov.caa-done .caa-cta.ghost{padding:12px;font-size:14px;border-radius:12px}'
  +'.caa-ext[hidden]{display:none!important}'
  +'.caa-ext{background:rgba(255,255,255,.13)!important;color:#fff!important}'
  +'.caa-promo{position:relative;height:100%;min-height:0;display:none;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:24px 20px;background:radial-gradient(120% 90% at 50% 0,rgba(194,64,58,.22),transparent 62%),rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.10);border-radius:18px;overflow:hidden}'
  +'.caa-ov.caa-done .caa-promo{display:flex}'
  +'.caa-promo-slide{display:flex;flex-direction:column;align-items:center;animation:caaPromoIn .5s ease}'
  +'@keyframes caaPromoIn{from{opacity:0;transform:translateY(12px) scale(.97)}to{opacity:1;transform:none}}'
  +'.caa-promo-ic{width:78px;height:78px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:35px;color:#fff;background:linear-gradient(160deg,#D6493C,#9A2F2B);box-shadow:0 14px 34px rgba(194,64,58,.42);margin-bottom:20px}'
  +'.caa-promo-t{font-size:20px;font-weight:800;letter-spacing:-.02em;color:#fff;margin:0 0 9px;max-width:300px;line-height:1.25}'
  +'.caa-promo-s{font-size:14px;line-height:1.5;color:rgba(255,255,255,.74);max-width:290px;margin:0}'
  +'.caa-dots{position:absolute;left:0;right:0;bottom:14px;display:flex;justify-content:center;gap:6px}'
  +'.caa-dots i{width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,.22);transition:width .3s,background .3s}'
  +'.caa-dots i.on{width:18px;border-radius:6px;background:#D6493C}'
  /* Limit-promo (bepul tugagach): obuna asosiy, reklama mayda ikkilamchi.
     Matn uzun tilda (ru/tj) ekranga sig'masligi mumkin — shuning uchun bu
     rejimda karusel o'z balandligini oladi va blok kerak bo'lsa scroll bo'ladi
     (aks holda promo bloki obuna kartasining ustiga chiqib ketardi). */
  +'.caa-ov.limit{overflow-y:auto;-webkit-overflow-scrolling:touch}'
  +'.caa-ov.limit .caa-promo{height:auto;min-height:210px}'
  +'.caa-ov.limit .caa-sub-t{display:none!important}'
  +'.caa-sub-desc{margin:0 0 6px;font-size:13px;line-height:1.45;color:rgba(255,255,255,.72);text-align:center}'
  +'.caa-sub-desc[hidden]{display:none!important}'
  +'.caa-ov.limit .caa-sub-desc{display:none!important}'
  /* "Nega bu oyna chiqdi?" — sabab qatori (limit ekranida, sarlavha ustida) */
  +'.caa-why{display:flex;align-items:flex-start;gap:9px;margin:0 0 4px;padding:11px 12px;background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.11);border-radius:13px;font-size:12.5px;line-height:1.45;color:rgba(255,255,255,.8);text-align:left}'
  +'.caa-why[hidden]{display:none!important}'
  +'.caa-why i{color:#F0C56A;font-size:17px;flex-shrink:0;margin-top:1px}'
  +'.caa-limit-foot{display:flex;flex-direction:column;gap:2px;margin-top:6px}'
  +'.caa-limit-foot[hidden]{display:none!important}'
  +'.caa-limit-link{background:transparent;border:none;color:rgba(255,255,255,.58);font-family:inherit;font-size:13px;font-weight:600;padding:9px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px}'
  +'.caa-limit-link[hidden]{display:none!important}'
  +'.caa-limit-link.ad{color:rgba(255,255,255,.84)}'
  +'.caa-limit-link i{font-size:15px}'
  /* Chiqish (X) — faqat limit-promoda, o\'ng yuqori burchakda */
  +'.caa-x{position:absolute;top:calc(10px + env(safe-area-inset-top,0px));right:12px;width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.16);color:#fff;display:none;align-items:center;justify-content:center;font-size:18px;z-index:6;cursor:pointer;-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}'
  +'.caa-ov.limit .caa-x{display:flex}'
  /* App reklamasi — Mini App ochilganda MARKAZDA chiqadigan alohida modal.
     Boshqa reklama oqimlariga tegmaydi, o\'z overlayida ishlaydi. */
  +'.caa-app{position:fixed;inset:0;z-index:9100;display:none;align-items:center;justify-content:center;padding:18px;background:rgba(10,8,6,.72);-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px);font-family:inherit}'
  +'.caa-app.on{display:flex}'
  +'.caa-app-card{position:relative;width:100%;max-width:340px;background:#15120f;border:1px solid rgba(255,255,255,.14);border-radius:20px;padding:14px;display:grid;gap:12px;box-shadow:0 18px 48px rgba(0,0,0,.5);color:#fff}'
  +'.caa-app-media{position:relative;width:100%;aspect-ratio:9/16;max-height:52vh;border-radius:14px;overflow:hidden;background:#000}'
  +'.caa-app-media video,.caa-app-media img{width:100%;height:100%;object-fit:contain;display:block}'
  +'.caa-app-media video[hidden],.caa-app-media img[hidden]{display:none!important}'
  +'.caa-app-t{font-size:15px;font-weight:700;line-height:1.35;text-align:center;margin:0}'
  +'.caa-app-cta{width:100%;border:none;border-radius:13px;padding:14px;font-family:inherit;font-size:15px;font-weight:700;background:#fff;color:#211D17;cursor:pointer}'
  +'.caa-app-cta:active{transform:translateY(1px)}'
  +'.caa-app-plats{display:flex;gap:8px}'
  +'.caa-app-plats[hidden]{display:none!important}'
  +'.caa-app-plat{flex:1;display:inline-flex;align-items:center;justify-content:center;gap:7px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.08);color:#fff;border-radius:12px;padding:12px 8px;font-family:inherit;font-size:14px;font-weight:600;cursor:pointer}'
  +'.caa-app-plat:active{transform:translateY(1px)}'
  +'.caa-app-plat i{font-size:17px}'
  +'.caa-app-x{position:absolute;top:-10px;right:-10px;width:34px;height:34px;border-radius:50%;background:#15120f;border:1px solid rgba(255,255,255,.22);color:#fff;display:none;align-items:center;justify-content:center;font-size:18px;cursor:pointer;z-index:2}'
  +'.caa-app-x.on{display:flex}'
  +'.caa-app-wait{position:absolute;top:-10px;right:-10px;min-width:34px;height:34px;padding:0 10px;border-radius:20px;background:rgba(0,0,0,.72);border:1px solid rgba(255,255,255,.18);color:rgba(255,255,255,.82);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;white-space:nowrap;z-index:2}'
  +'.caa-app-wait[hidden]{display:none!important}'
  /* Reklama turiga qarab video ostidagi knopka bloki (hamkorlik / bot) */
  +'.caa-ps{display:none;gap:8px;text-align:left}'
  +'.caa-ps.on{display:grid}'
  +'.caa-ov.caa-done .caa-ps{display:none!important}'
  +'.caa-ps-btns{display:flex;flex-wrap:wrap;gap:7px}'
  +'.caa-ps-btn{flex:1;min-width:92px;display:inline-flex;align-items:center;justify-content:center;gap:6px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.08);color:#fff;border-radius:11px;padding:11px 8px;font-family:inherit;font-size:13px;font-weight:600;cursor:pointer}'
  +'.caa-ps-btn.primary{background:#fff;color:#211D17;border-color:#fff}'
  +'.caa-ps-btn:active{transform:translateY(1px)}'
  +'.caa-ps-btn i{font-size:15px}'
  +'.caa-desktop{display:none;width:100%}'
  +'.caa-desktop:not([hidden]){display:block}';

  var els = null;
  function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
  function ensureDom(){
    if(els) return els;
    var style = document.createElement("style"); style.textContent = CSS; document.head.appendChild(style);
    var ov = document.createElement("div"); ov.className = "caa-ov"; ov.setAttribute("aria-hidden","true");
    ov.innerHTML = ''
      +'<div class="caa-box">'
      +'<div class="caa-top"><span class="caa-label"></span><span class="caa-count"></span></div>'
      +'<div class="caa-vwrap"><video class="caa-video" muted playsinline webkit-playsinline preload="auto"></video>'
      +'<img class="caa-photo" alt="" hidden>'
      +'<div class="caa-status" hidden></div>'
      +'<span class="caa-visit" hidden><i class="ti ti-external-link"></i> <span class="caa-visit-t"></span></span></div>'
      +'<div class="caa-promo"><div class="caa-promo-slide"></div><div class="caa-dots"></div></div>'
      +'<div class="caa-meta"><b class="caa-title"></b><small class="caa-note"></small>'
      +'<div class="caa-ps"></div>'
      +'<button class="caa-cta caa-cta0" disabled></button>'
      +'<div class="caa-sub" hidden><div class="caa-why" hidden><i class="ti ti-info-circle"></i><span class="caa-why-t"></span></div>'
      +'<p class="caa-sub-t"></p><p class="caa-sub-desc" hidden></p><div class="caa-benefits"></div>'
      +'<button class="caa-cta caa-pay"></button><button class="caa-cta ghost caa-ext" hidden></button><button class="caa-cta ghost caa-cont"></button><div class="caa-desktop" hidden></div>'
      +'<div class="caa-limit-foot" hidden><button class="caa-limit-link ad caa-lim-ad" hidden></button></div></div>'
      +'</div>'
      +'<button class="caa-x" aria-label="close"><i class="ti ti-x"></i></button>'
      +'</div>';
    document.body.appendChild(ov);
    var q = function(s){return ov.querySelector(s)};
    els = {ov:ov, box:q(".caa-box"), label:q(".caa-label"), count:q(".caa-count"), vwrap:q(".caa-vwrap"),
      video:q(".caa-video"), photo:q(".caa-photo"), status:q(".caa-status"), visit:q(".caa-visit"), visitT:q(".caa-visit-t"),
      promo:q(".caa-promo"), promoSlide:q(".caa-promo-slide"), dots:q(".caa-dots"),
      title:q(".caa-title"), note:q(".caa-note"), ps:q(".caa-ps"), cta0:q(".caa-cta0"), sub:q(".caa-sub"),
      subTitle:q(".caa-sub-t"), subDesc:q(".caa-sub-desc"), why:q(".caa-why"), whyT:q(".caa-why-t"),
      benefits:q(".caa-benefits"), pay:q(".caa-pay"), external:q(".caa-ext"), cont:q(".caa-cont"),
      desktop:q(".caa-desktop"), limFoot:q(".caa-limit-foot"), limAd:q(".caa-lim-ad"), x:q(".caa-x")};
    els.vwrap.addEventListener("click", openAdLink);
    els.ps.addEventListener("click", onPsClick);
    return els;
  }

  function haptic(ok){try{var tg=window.Telegram&&window.Telegram.WebApp;tg&&tg.HapticFeedback&&tg.HapticFeedback.impactOccurred(ok?"medium":"light")}catch(e){}}

  var STATE = {timer:null,loadTimer:null,resolve:null,reject:null,ad:null,placement:"start",accessRef:"",attemptToken:"",watched:0,ready:false,busy:false};
  function resetState(){STATE={timer:null,loadTimer:null,resolve:null,reject:null,ad:null,placement:"start",accessRef:"",attemptToken:"",watched:0,ready:false,busy:false}}
  function placementTitle(p){var t=T();if(isLessonEnd())return t.leLabel||t.adEnd;return p==="middle"?t.adMiddle:(p==="end"?t.adEnd:t.adStart)}
  function adDuration(ad){return Math.max(5,Math.min(120,Number(ad&&ad.duration_seconds)||7))}
  /* Dars yakuni blokining matnlari boshqacha: bu joyda "reklama bilan davom
     etish" ma'nosiz (reklama allaqachon tugadi) — oddiy "Davom etish" bo'ladi. */
  function noteText(){var t=T();return (isLessonEnd()&&t.leNote)||t.adNote}
  function subTitleText(){var t=T();return (isLessonEnd()&&t.leSubTitle)||t.adSubTitle}
  function contText(){var t=T();return isLessonEnd()?(t.adReady||t.adSubCont):t.adSubCont}

  /* Promo karusel (reklamalar tugagach). */
  var promoStop=null;
  function renderPromo(slides,idx){
    var s=slides[idx];
    els.promoSlide.innerHTML='<div class="caa-promo-ic"><i class="ti ti-'+esc(s.i)+'"></i></div>'
      +'<div class="caa-promo-t">'+esc(s.t)+'</div><p class="caa-promo-s">'+esc(s.s)+'</p>';
    els.promoSlide.style.animation="none";void els.promoSlide.offsetWidth;els.promoSlide.style.animation="";
    els.dots.innerHTML=slides.map(function(_,k){return '<i class="'+(k===idx?"on":"")+'"></i>'}).join("");
  }
  function startPromo(){stopPromo();var slides=promoSlides(),i=0;renderPromo(slides,i);promoStop=setInterval(function(){i=(i+1)%slides.length;renderPromo(slides,i)},4500)}
  function stopPromo(){if(promoStop){clearInterval(promoStop);promoStop=null}}

  /* Reklama turiga qarab (video ostidagi) knopka(lar). Odiy reklama — knopka
     yo'q (avvalgi "Havolaga o'tish" chipi ishlaydi). Hamkorlik — bitta CTA.
     Bot — sinab ko'rish + linkni nusxalash + do'stga yuborish. Knopka nomi
     admin bergan `button_text` yoki turga mos default. */
  var psCurrent=null;
  function openUrl(url){
    if(!url)return;haptic(true);
    var tg=window.Telegram&&window.Telegram.WebApp;
    var isTg=/^(https?:\/\/)?(t\.me|telegram\.me|telegram\.dog)\//i.test(url)||url.indexOf("tg://")===0;
    try{if(isTg&&tg&&tg.openTelegramLink){tg.openTelegramLink(url);return}}catch(e){}
    try{if(tg&&tg.openLink){tg.openLink(url);return}}catch(e){}
    try{window.open(url,"_blank")}catch(e){}
  }
  function hideLessonEndExternal(){
    if(!els||!els.external)return;
    els.external.hidden=true;els.external.style.display="none";els.external.onclick=null;
  }
  function renderLessonEndExternal(ad){
    hideLessonEndExternal();
    if(!isLessonEnd()||!ad||!ad.link_url)return;
    var label=(ad.button_text&&String(ad.button_text).trim())?String(ad.button_text).trim():(T().leExternal||T().adVisit);
    var url=ad.link_url;
    els.external.innerHTML='<i class="ti ti-external-link"></i> '+esc(label);
    els.external.hidden=false;els.external.style.display="flex";
    els.external.onclick=function(){openUrl(url)};
  }
  function copyUrl(url,btn){
    if(!url)return;haptic(true);
    function done(){if(!btn)return;var old=btn.getAttribute("data-old")||btn.innerHTML;btn.setAttribute("data-old",old);btn.innerHTML='<i class="ti ti-check"></i> '+esc(T().psCopied);setTimeout(function(){btn.innerHTML=old;btn.removeAttribute("data-old")},1500)}
    try{if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(url).then(done).catch(fallbackCopy);return}}catch(e){}
    fallbackCopy();
    function fallbackCopy(){try{var ta=document.createElement("textarea");ta.value=url;ta.style.position="fixed";ta.style.opacity="0";document.body.appendChild(ta);ta.focus();ta.select();document.execCommand("copy");document.body.removeChild(ta);done()}catch(e){}}
  }
  function shareUrl(url,text){
    if(!url)return;haptic(true);
    var share="https://t.me/share/url?url="+encodeURIComponent(url)+"&text="+encodeURIComponent(text||"");
    var tg=window.Telegram&&window.Telegram.WebApp;
    try{if(tg&&tg.openTelegramLink){tg.openTelegramLink(share);return}}catch(e){}
    try{window.open(share,"_blank")}catch(e){}
  }
  function onPsClick(e){
    var node=e.target,btn=null;
    while(node&&node!==els.ps){if(node.classList&&node.classList.contains("caa-ps-btn")){btn=node;break}node=node.parentNode}
    if(!btn||!psCurrent)return;
    var act=btn.getAttribute("data-psact"),sec=psCurrent;
    if(act==="open")openUrl(sec.link_url);
    else if(act==="copy")copyUrl(sec.link_url,btn);
    else if(act==="share")shareUrl(sec.link_url,sec.title);
  }
  function hidePs(){if(els&&els.ps){els.ps.classList.remove("on");els.ps.innerHTML=""}psCurrent=null}
  function renderAdButtons(ad){
    hidePs();
    if(!ad)return;
    var type=ad.ad_type||"odiy";
    if((type!=="hamkorlik"&&type!=="bot")||!ad.link_url)return;
    var t=T(),bt=(ad.button_text&&String(ad.button_text).trim())?String(ad.button_text).trim():(type==="hamkorlik"?t.psWrite:t.psTry);
    psCurrent={link_url:ad.link_url,title:ad.title||""};
    var btns;
    if(type==="hamkorlik"){
      btns='<button class="caa-ps-btn primary" data-psact="open"><i class="ti ti-external-link"></i> '+esc(bt)+'</button>';
    }else{
      btns='<button class="caa-ps-btn primary" data-psact="open"><i class="ti ti-player-play"></i> '+esc(bt)+'</button>'
          +'<button class="caa-ps-btn" data-psact="copy"><i class="ti ti-copy"></i> '+esc(t.psCopy)+'</button>'
          +'<button class="caa-ps-btn" data-psact="share"><i class="ti ti-send"></i> '+esc(t.psShare)+'</button>';
    }
    els.ps.innerHTML='<div class="caa-ps-btns">'+btns+'</div>';
    els.ps.classList.add("on");
  }

  function fetchAds(placement){
    var url="/api/v3/ad?placement="+encodeURIComponent(placement)
      +"&level="+encodeURIComponent(CFG.level||"hsk1")
      +"&lesson="+encodeURIComponent(Number(CFG.lessonOrder)||0)
      +"&slot="+encodeURIComponent(CFG.slot||"")
      +"&feature="+encodeURIComponent(CFG.feature||"")
      +"&lang="+encodeURIComponent(CFG.lang||"uz");
    return fetch(url,{headers:{"X-Telegram-Init-Data":CFG.initData||""}})
      .then(function(r){return r.json().then(function(d){d._status=r.status;return d})})
      .then(function(d){
        var ads=(d&&d.ads&&d.ads.length)?d.ads:(d&&d.ad?[d.ad]:[]);
        if(!d.ok||!ads.length)throw new Error("course_ad_not_found");
        return ads;
      });
  }
  function startAttempt(ad,placement,accessRef){
    accessRef=String(accessRef||"").trim().slice(0,48);
    if(!CFG.initData||!accessRef)return Promise.reject(new Error("ad_attempt_requires_auth"));
    /* Protected oqimda lesson_order mashqlar uchun 0, dars access reklamasida
       esa aniq dars raqami bo'ladi. Dars yakuni bloki ruxsat bermaydi. */
    return fetch("/api/v3/ad/attempt",{method:"POST",headers:{"Content-Type":"application/json","X-Telegram-Init-Data":CFG.initData},
      body:JSON.stringify({ad_id:ad.id,level:CFG.level||"hsk1",lesson_order:Number(CFG.lessonOrder)||0,feature:CFG.feature||"",access_ref:accessRef,placement:placement})})
      .then(function(r){return r.json().catch(function(){return {ok:false}})})
      .then(function(d){if(!d||!d.ok||!d.attempt_token)throw new Error("ad_attempt_failed");return d});
  }
  function recordView(ad,placement,watched,accessRef,attemptToken){
    accessRef=String(accessRef||"").trim().slice(0,48);
    if(!CFG.initData)return Promise.resolve({ok:!accessRef});
    return fetch("/api/v3/ad/view",{method:"POST",headers:{"Content-Type":"application/json","X-Telegram-Init-Data":CFG.initData},
      body:JSON.stringify({ad_id:ad.id,level:CFG.level||"hsk1",lesson_order:Number(CFG.lessonOrder)||0,feature:CFG.feature||"",access_ref:accessRef,attempt_token:String(attemptToken||""),placement:placement,watched_seconds:watched})})
      .then(function(r){return r.json()}).catch(function(){return {ok:false}});
  }
  function openAdLink(){
    var ad=STATE.ad;if(!ad||!ad.link_url)return;var url=ad.link_url;haptic(true);
    var tg=window.Telegram&&window.Telegram.WebApp;
    function go(){try{if(tg&&tg.openLink){tg.openLink(url);return}}catch(e){}try{window.open(url,"_blank")}catch(e){}}
    try{if(tg&&tg.showConfirm){tg.showConfirm(T().adOpenLink,function(ok){if(ok)go()});return}}catch(e){}
    if(window.confirm(T().adOpenLink))go();
  }

  function setStatus(text){els.status.hidden=!text;els.status.textContent=text||""}
  function resetVideo(v){if(!v)return;v.onloadedmetadata=v.onloadeddata=v.oncanplay=v.onplaying=v.ontimeupdate=v.onerror=v.onstalled=v.onwaiting=null}
  function resetPhoto(p){if(!p)return;p.onload=p.onerror=null}
  /* Surat reklamasi: `media_type==="photo"` bo'lsa <video> o'rniga <img> ishlaydi.
     Eski yozuvlarda maydon bo'lmasligi mumkin — u holda video deb qaraladi. */
  function isPhotoAd(ad){return !!(ad&&ad.media_type==="photo")}
  function closeOverlay(){
    clearInterval(STATE.timer);clearTimeout(STATE.loadTimer);
    try{var v=els.video;resetVideo(v);v.pause();v.removeAttribute("src");v.load()}catch(e){}
    try{var p=els.photo;resetPhoto(p);p.removeAttribute("src");p.hidden=true;els.video.hidden=false}catch(e){}
    stopPromo();hidePs();hideLessonEndExternal();els.desktop.hidden=true;els.ov.classList.remove("caa-done");setStatus("");
    els.ov.classList.remove("on");els.ov.setAttribute("aria-hidden","true");
  }
  function setSubVisible(vis){els.sub.hidden=!vis;els.sub.style.display=vis?"grid":"none"}

  /* Rolik tugagach "davom" bosilganda. */
  function done(){
    if(!STATE.ready||STATE.busy)return;STATE.busy=true;
    els.cont.disabled=true;els.cont.innerHTML='<i class="ti ti-loader-2"></i> …';
    function finish(){closeOverlay();var r=STATE.resolve;resetState();if(r)r()}
    recordView(STATE.ad,STATE.placement,STATE.watched,"","").then(finish).catch(finish);
  }
  function subscribe(){closeOverlay();resetState();if(typeof CFG.onSubscribe==="function")CFG.onSubscribe()}

  function play(placement,accessRef){
    ensureDom();
    hideLessonEndExternal();
    accessRef=String(accessRef||"").trim().slice(0,48);
    return new Promise(function(resolve,reject){
      fetchAds(placement).then(function(ads){
        var t=T();
        els.note.textContent=noteText();
        els.subTitle.textContent=subTitleText();
        els.benefits.innerHTML=[t.b1,t.b2,t.b3].map(function(b){return '<div class="caa-ben"><i class="ti ti-circle-check"></i><span>'+esc(b)+'</span></div>'}).join("");
        els.pay.innerHTML='<i class="ti ti-lock-open"></i> '+esc(t.adSubPay);
        els.pay.onclick=subscribe;els.cont.onclick=done;
        /* Limit-promodan qolgan holatni tozalaymiz (subDesc, foot, cont ko'rinishi). */
        els.subDesc.hidden=true;els.why.hidden=true;els.limFoot.hidden=true;els.cont.style.display="";
        els.ov.classList.remove("limit");
        els.ov.classList.add("on");els.ov.setAttribute("aria-hidden","false");
        clearInterval(STATE.timer);
        var video=els.video;
        function playAd(i){
          var ad=ads[i],duration=adDuration(ad),isLast=(i>=ads.length-1),multi=ads.length>1;
          var photoAd=isPhotoAd(ad),photo=els.photo;
          clearInterval(STATE.timer);clearTimeout(STATE.loadTimer);resetVideo(video);resetPhoto(photo);
          video.hidden=photoAd;photo.hidden=!photoAd;
          STATE={timer:null,loadTimer:null,resolve:resolve,reject:reject,ad:ad,placement:placement,accessRef:accessRef,attemptToken:"",watched:0,ready:false,busy:false};
          els.label.textContent=placementTitle(placement)+(multi?" · "+(i+1)+"/"+ads.length:"");
          els.title.textContent=ad.title||placementTitle(placement);
          els.note.textContent=noteText();
          hideLessonEndExternal();
          var hasLink=!!ad.link_url;
          var typed=(ad.ad_type==="hamkorlik"||ad.ad_type==="bot");
          /* Odiy reklamada havola bo'lsa — video ustidagi "Havolaga o'tish" chipi.
             Hamkorlik/bot turida esa video ostidagi knopka(lar) ishlaydi. */
          if(hasLink&&!typed){els.visitT.textContent=t.adVisit;els.visit.hidden=false}else{els.visit.hidden=true}
          renderAdButtons(ad);
          stopPromo();els.ov.classList.remove("caa-done");
          els.vwrap.style.display="";els.vwrap.style.cursor=hasLink?"pointer":"default";
          els.cont.disabled=false;els.cont.innerHTML='<i class="ti ti-arrow-right"></i> '+contText();
          setSubVisible(false);els.cta0.style.display="none";els.cta0.disabled=true;
          els.count.textContent="...";setStatus(t.loading);
          var srcBase=ad.media_url,loadAttempt=0,left=duration,timer=null,started=false,failed=false,attemptStarting=false;
          var requiresAttempt=!!accessRef&&placement==="start"&&isLast;
          function srcWith(bust){return bust?srcBase+(srcBase.indexOf("?")>=0?"&":"?")+"r="+Date.now():srcBase}
          function setSrc(bust){
            if(photoAd){photo.removeAttribute("src");photo.src=srcWith(bust);return}
            try{video.pause()}catch(e){}
            video.removeAttribute("src");try{video.load()}catch(e){}
            video.src=srcWith(bust);
            video.loop=true;video.muted=true;try{video.load()}catch(e){}
          }
          function armGuard(ms){clearTimeout(STATE.loadTimer);STATE.loadTimer=setTimeout(onLoadTimeout,ms)}
          function mediaReady(){return photoAd?(photo.complete&&photo.naturalWidth>0):(video.readyState>=2)}
          /* Suratda ijro yo'q — faqat yuklanishini kutamiz. */
          function tryPlay(){
            if(photoAd){if(mediaReady())startCountdown();return}
            var p;try{p=video.play()}catch(e){}if(p&&p.then)p.then(startCountdown).catch(function(){if(video.readyState>=2)startCountdown()})
          }
          function onLoadTimeout(){
            if(started||failed||STATE.ad!==ad)return;
            if(mediaReady()){startCountdown();return}
            if(loadAttempt<2){loadAttempt++;setStatus(t.loading);setSrc(true);armGuard(loadAttempt>=2?16000:12000);tryPlay();return}
            mediaFailed();
          }
          function onMediaError(){
            if(started||failed||STATE.ad!==ad)return;
            if(loadAttempt<2){loadAttempt++;setStatus(t.loading);setSrc(true);armGuard(12000);tryPlay();return}
            mediaFailed();
          }
          function draw(){
            els.count.textContent=left>0?left+"s":"OK";
            if(left>0){els.cta0.style.display="none";setSubVisible(false);return}
            if(!isLast){recordView(ad,placement,duration,"","").catch(function(){});playAd(i+1);}
            else if(placement==="end"){
              /* YAKUNIY reklama tugadi — "Obuna ol / Reklama bilan davom etish"
                 bloki chiqadi (davom bosilganda done() ko'rilganini yozib yakunlaydi). */
              try{video.pause()}catch(e){}
              hidePs();
              renderLessonEndExternal(ad);
              els.vwrap.style.display="none";els.ov.classList.add("caa-done");startPromo();
              STATE.ready=true;els.cta0.style.display="none";els.cont.style.display="";setSubVisible(true);
              if(window.PompDesktopDownload&&typeof window.PompDesktopDownload.mountAdPromoTrigger==="function"){
                var desktopPlacement=isLessonEnd()?"lesson_end_ad":"practice_"+String(CFG.feature||"unknown")+"_end";
                window.PompDesktopDownload.mountAdPromoTrigger(els.desktop,{placement:desktopPlacement});
              }else{els.desktop.hidden=true}
              /* Obuna taklifi ko'rindi — chaqiruvchi buni analitikaga yozishi mumkin. */
              if(typeof CFG.onOffer==="function"){try{CFG.onOffer()}catch(e){}}
            }else{
              /* start / middle reklama — obuna taklifi limit ekranida allaqachon
                 bo'lgan, shuning uchun bu yerda YANA obunaga majburlamaymiz:
                 ko'rilganini fonda yozib, to'g'ridan davom etamiz. */
              try{video.pause()}catch(e){}
              var finishStart=function(result){
                if(!result||!result.ok){failFlow();return}
                var resolve=STATE.resolve;
                closeOverlay();resetState();
                if(typeof resolve==="function")resolve(result);
              };
              recordView(ad,placement,duration,accessRef,STATE.attemptToken).then(finishStart).catch(failFlow);
            }
          }
          function beginCountdown(){
            if(started||failed||STATE.ad!==ad)return;
            started=true;clearTimeout(STATE.loadTimer);setStatus("");draw();
            timer=setInterval(function(){left=Math.max(0,left-1);STATE.watched=duration-left;if(left<=0)clearInterval(timer);draw();},1000);
            STATE.timer=timer;
          }
          function startCountdown(){
            if(started||failed||STATE.ad!==ad)return;
            if(!requiresAttempt){beginCountdown();return}
            if(attemptStarting)return;attemptStarting=true;clearTimeout(STATE.loadTimer);
            startAttempt(ad,placement,accessRef).then(function(result){
              if(failed||STATE.ad!==ad)return;
              STATE.attemptToken=String(result.attempt_token||"");beginCountdown();
            }).catch(failFlow);
          }
          function failFlow(){if(STATE.ad!==ad)return;var rej=STATE.reject||reject;closeOverlay();resetState();if(rej)rej(new Error("course_ad_media_failed"))}
          function mediaFailed(){
            if(started||failed||STATE.ad!==ad)return;failed=true;
            clearTimeout(STATE.loadTimer);clearInterval(STATE.timer);STATE.ready=false;STATE.watched=0;
            try{video.pause()}catch(e){}setStatus(t.failed);els.note.textContent=t.failedNote;els.count.textContent="!";
            els.cta0.style.display="";els.cta0.disabled=false;els.cta0.innerHTML='<i class="ti ti-arrow-right"></i> '+t.adReady;
            els.cta0.onclick=function(ev){if(ev)ev.stopPropagation();failFlow()};
            setTimeout(failFlow,1600);
          }
          if(photoAd){
            photo.onload=startCountdown;photo.onerror=onMediaError;
          }else{
            video.onloadedmetadata=tryPlay;video.onloadeddata=startCountdown;video.oncanplay=startCountdown;
            video.onplaying=startCountdown;video.ontimeupdate=startCountdown;video.onerror=onMediaError;
            video.onstalled=video.onwaiting=function(){if(started||failed||STATE.ad!==ad)return;armGuard(12000)};
          }
          setSrc(false);armGuard(12000);
          if(mediaReady())startCountdown();
          tryPlay();
        }
        playAd(0);
      }).catch(function(){reject(new Error("course_ad_not_found"))});
    });
  }

  function _closeLimit(){
    stopPromo();hidePs();hideLessonEndExternal();els.desktop.hidden=true;
    els.ov.classList.remove("on","caa-done","limit");
    els.ov.setAttribute("aria-hidden","true");
    if(els.limFoot)els.limFoot.hidden=true;
    if(els.why)els.why.hidden=true;
  }
  /* Bepul limit tugagach ko'rsatiladigan promo ekran — reklama tugaganidagi
     ekran bilan bir xil uslub (aylanuvchi karusel + obuna), lekin obuna ASOSIY,
     "reklama bilan davom etish" esa mayda ikkilamchi havola.
     Eng tepada — "nega bu oyna chiqdi" sababi (qaysi bo'lim, qanday limit,
     qachon yana ochiladi), keyin obunaning foydasi.
     opts: {adAvailable, onSubscribe, onContinueAd, onBack, reason}. */
  function showLimitPromo(opts){
    opts=opts||{};
    ensureDom();
    hidePs();hideLessonEndExternal();els.desktop.hidden=true;
    var t=T();
    var why=opts.reason||limitWhyText(CFG.feature);
    if(why){els.whyT.textContent=why;els.why.hidden=false}else{els.why.hidden=true}
    els.subTitle.textContent="";
    els.subDesc.textContent="";
    els.subDesc.hidden=true;
    els.benefits.innerHTML="";
    els.pay.style.display="";
    els.pay.innerHTML='<i class="ti ti-crown"></i> '+esc(t.limitSubscribe||t.adSubPay);
    els.pay.onclick=function(){var cb=opts.onSubscribe;_closeLimit();if(typeof cb==="function")cb()};
    els.cont.style.display="none";
    /* Pastda faqat "reklama bilan davom etish" (agar mavjud) — mayda ikkilamchi. */
    els.limFoot.hidden=false;
    if(opts.adAvailable&&typeof opts.onContinueAd==="function"){
      els.limAd.hidden=false;
      els.limAd.innerHTML='<i class="ti ti-player-play"></i> '+esc(t.limitAd||t.adSubCont);
      els.limAd.onclick=function(){var cb=opts.onContinueAd;_closeLimit();if(typeof cb==="function")cb()};
    }else{els.limAd.hidden=true}
    /* Chiqish — o'ng yuqori burchakdagi X (pastda "orqaga" tugma yo'q). */
    els.x.onclick=function(){var cb=opts.onBack;_closeLimit();if(typeof cb==="function")cb()};
    /* Media yo'q — to'g'ridan promo (done) ko'rinishi. */
    try{els.video.pause();els.video.removeAttribute("src");els.video.load()}catch(e){}
    try{els.photo.removeAttribute("src");els.photo.hidden=true;els.video.hidden=false}catch(e){}
    els.vwrap.style.display="none";
    setStatus("");
    els.ov.classList.add("on","caa-done","limit");
    els.ov.setAttribute("aria-hidden","false");
    setSubVisible(true);
    startPromo();
  }

  /* ============================================================
     App reklamasi — Mini App ochilganda markazda chiqadigan modal.

     Boshqa reklama oqimlaridan MUSTAQIL: o'z overlayi, o'z holati.
     Dars, mashq va dars-yakuni oqimlariga umuman tegmaydi.

     Ketma-ketlik: video markazda o'ynaydi → `skip_after_seconds`
     tugagach X paydo bo'ladi → foydalanuvchi O'ZI yopadi (avtomatik
     yopilmaydi). `daily_limit` — kuniga necha marta (0 = cheklovsiz).
     ============================================================ */
  var appEls=null, appState={open:false,timer:null,shownInSession:false};

  function appDayKey(){ var d=new Date(); return d.getFullYear()+"-"+(d.getMonth()+1)+"-"+d.getDate(); }
  function appLimitStorageKey(adId){ return "caa_app_seen_"+String(adId||0); }
  function appSeenToday(adId){
    try{
      var raw=JSON.parse(localStorage.getItem(appLimitStorageKey(adId))||"{}");
      return raw&&raw.day===appDayKey()?(Number(raw.count)||0):0;
    }catch(e){ return 0; }
  }
  function appMarkSeen(adId){
    try{
      localStorage.setItem(appLimitStorageKey(adId),JSON.stringify({day:appDayKey(),count:appSeenToday(adId)+1}));
    }catch(e){}
  }

  function ensureAppDom(){
    if(appEls) return appEls;
    ensureDom();
    var ov=document.createElement("div"); ov.className="caa-app"; ov.setAttribute("aria-hidden","true");
    ov.innerHTML=''
      +'<div class="caa-app-card">'
      +'<button class="caa-app-x" aria-label="close"><i class="ti ti-x"></i></button>'
      +'<span class="caa-app-wait" hidden></span>'
      +'<div class="caa-app-media"><video muted playsinline webkit-playsinline preload="auto"></video><img alt="" hidden></div>'
      +'<p class="caa-app-t"></p>'
      +'<div class="caa-app-plats" hidden></div>'
      +'<button class="caa-app-cta"></button>'
      +'</div>';
    document.body.appendChild(ov);
    var q=function(s){return ov.querySelector(s)};
    appEls={ov:ov,card:q(".caa-app-card"),x:q(".caa-app-x"),wait:q(".caa-app-wait"),
      video:q("video"),photo:q(".caa-app-media img"),title:q(".caa-app-t"),plats:q(".caa-app-plats"),cta:q(".caa-app-cta")};
    return appEls;
  }

  function closeAppAd(){
    if(!appEls) return;
    if(appState.timer){ clearInterval(appState.timer); appState.timer=null; }
    try{ appEls.video.pause(); appEls.video.removeAttribute("src"); appEls.video.load(); }catch(e){}
    try{ appEls.photo.removeAttribute("src"); appEls.photo.hidden=true; appEls.video.hidden=false; }catch(e){}
    appEls.ov.classList.remove("on");
    appEls.ov.setAttribute("aria-hidden","true");
    appState.open=false;
  }

  /* Platforma tugmalari — serverdan tayyor ro'yxat keladi (`app_buttons`).
     Server faqat KO'RINADIGAN va havolasi BOR platformalarni yuboradi:
     hozircha MacBook va Windows. iPhone/Android reliz tayyor bo'lgach
     serverdagi ro'yxatga qo'shiladi, bu yerda o'zgartirish kerak emas. */
  var APP_PLATFORM_META={
    macos:{icon:"ti-brand-apple",label:"MacBook"},
    windows:{icon:"ti-brand-windows",label:"Windows"},
    ios:{icon:"ti-device-mobile",label:"iPhone"},
    android:{icon:"ti-brand-android",label:"Android"}
  };

  function openAppLink(url){
    if(!url) return;
    try{
      var tg=window.Telegram&&window.Telegram.WebApp;
      if(tg&&typeof tg.openLink==="function") tg.openLink(url);
      else window.open(url,"_blank","noopener");
    }catch(err){}
  }

  function renderAppPlatforms(e,ad){
    var list=(ad&&ad.app_buttons&&ad.app_buttons.length)?ad.app_buttons:[];
    if(!list.length){ e.plats.hidden=true; e.plats.innerHTML=""; return; }
    e.plats.innerHTML=list.map(function(b){
      var meta=APP_PLATFORM_META[b.platform]||{icon:"ti-download",label:b.platform};
      return '<button class="caa-app-plat" data-plat="'+b.platform+'">'
        +'<i class="ti '+meta.icon+'"></i> '+meta.label+'</button>';
    }).join("");
    e.plats.hidden=false;
    var btns=e.plats.querySelectorAll(".caa-app-plat");
    for(var i=0;i<btns.length;i++){
      (function(btn){
        btn.onclick=function(){
          var found=null;
          for(var j=0;j<list.length;j++){ if(list[j].platform===btn.dataset.plat) found=list[j]; }
          openAppLink(found&&found.url);
        };
      })(btns[i]);
    }
  }

  function showAppAd(ad){
    var e=ensureAppDom(), t=T();
    var skip=Math.max(0,Math.min(60,Number(ad&&ad.skip_after_seconds)||0));
    appState.open=true;
    appState.shownInSession=true;
    e.title.textContent=String(ad.title||"");
    renderAppPlatforms(e,ad);
    e.cta.textContent=String(ad.button_text||t.appCta);
    /* Platforma tugmalari bo'lsa umumiy CTA ortiqcha — takror bo'lmasin. */
    var hasPlatforms=!!(ad&&ad.app_buttons&&ad.app_buttons.length);
    e.cta.style.display=(ad.link_url&&!hasPlatforms)?"":"none";
    e.cta.onclick=function(){ openAppLink(ad.link_url); };
    e.x.classList.remove("on");
    e.x.onclick=closeAppAd;
    /* Surat reklamasi bo'lsa <img>, aks holda avvalgidek <video>. */
    if(isPhotoAd(ad)){
      e.video.hidden=true;e.photo.hidden=false;
      try{ e.video.pause(); e.video.removeAttribute("src"); }catch(err){}
      try{ e.photo.src=ad.media_url; }catch(err){}
    }else{
      e.photo.hidden=true;e.video.hidden=false;
      try{ e.photo.removeAttribute("src"); }catch(err){}
      try{ e.video.src=ad.media_url; e.video.currentTime=0; e.video.play().catch(function(){}); }catch(err){}
    }
    e.ov.classList.add("on");
    e.ov.setAttribute("aria-hidden","false");
    appMarkSeen(ad.id);

    /* X taymer: `skip` soniya kutiladi, keyin yopish tugmasi ochiladi. */
    if(skip<=0){ e.wait.hidden=true; e.x.classList.add("on"); return; }
    var left=skip;
    e.wait.hidden=false;
    e.wait.textContent=String(t.appCloseIn||"{s}").replace("{s}",left);
    appState.timer=setInterval(function(){
      left=Math.max(0,left-1);
      if(left<=0){
        clearInterval(appState.timer); appState.timer=null;
        e.wait.hidden=true; e.x.classList.add("on");
        return;
      }
      e.wait.textContent=String(t.appCloseIn||"{s}").replace("{s}",left);
    },1000);
  }

  /* Mini App ochilganda chaqiriladi. Reklama bo'lmasa jimgina qaytadi. */
  function playAppOpen(){
    if(appState.open||appState.shownInSession) return Promise.resolve(false);
    var url="/api/v3/ad?slot=app_open&placement=start&level="+encodeURIComponent(CFG.level||"hsk1")
      +"&lesson=0&feature=&lang="+encodeURIComponent(CFG.lang||"uz");
    return fetch(url,{headers:{"X-Telegram-Init-Data":CFG.initData||""}})
      .then(function(r){return r.json().catch(function(){return {}})})
      .then(function(d){
        var ads=(d&&d.ads&&d.ads.length)?d.ads:(d&&d.ad?[d.ad]:[]);
        if(!d||d.ok!==true||!ads.length) return false;
        var ad=ads[0];
        if(!ad||!ad.media_url||ad.media_available===false) return false;
        var limit=Math.max(0,Number(ad.daily_limit)||0);
        if(limit>0&&appSeenToday(ad.id)>=limit) return false;
        showAppAd(ad);
        return true;
      })
      .catch(function(){ return false; });
  }

  window.CourseAds = {
    config:function(o){for(var k in o){if(Object.prototype.hasOwnProperty.call(o,k))CFG[k]=o[k]}},
    play:play,
    playAppOpen:playAppOpen,
    closeAppAd:closeAppAd,
    showLimitPromo:showLimitPromo,
    closeLimit:_closeLimit,
    available:function(){return !!els}
  };
})();
