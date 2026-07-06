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
 *   CourseAds.play("start").then(runSession).catch(runSession);
 *
 * play(placement) — "start" | "middle" | "end". Rolik(lar) ko'rilib, "davom"
 * bosilganda Promise resolve bo'ladi. Reklama topilmasa yoki yuklanmasa reject
 * bo'ladi (chaqiruvchi baribir davom etadi — userni obunaga majburlamaymiz). */
(function(){
  var CFG = {lang:"uz", initData:"", feature:"", level:"hsk1", onSubscribe:null};

  /* Darsdagi T() ad-* kalitlaridan olingan matnlar (3 til). */
  var I18N = {
    uz:{adStart:"Bo'limdan oldingi reklama",adMiddle:"Qisqa reklama pauzasi",adEnd:"Yakuniy reklama",adReady:"Davom etish",adNote:"Rolikni oxirigacha ko'ring. Premium reklamasisiz o'qiydi.",adSubTitle:"Obuna bo'ling — botdan reklamasiz va hech qanday limitsiz foydalaning",adSubPay:"Obuna olish",adSubCont:"Reklama bilan davom etish",adVisit:"Havolaga o'tish",adOpenLink:"Reklama havolasini ochasizmi?",b1:"Barcha HSK 1–4 darslar",b2:"AI Voice — cheksiz",b3:"Cheksiz test va xatolar mashqi",loading:"Reklama yuklanmoqda...",failed:"Reklama videosi yuklanmadi",failedNote:"Ekran qora qolsa, video MP4 H.264/AAC formatida bo'lishi kerak.",limitHead:"To'xtama — eng zo'r qismi oldinda!",limitSub:"Obunani ochsang, barcha cheklovlar yo'qoladi: tez, oson va cheksiz o'rganasan. Xitoy tilini bir necha oyda o'zlashtir — bugun boshlaganing ertaga natijaga aylanadi.",limitSubscribe:"Obunani ochish",limitAd:"Yoki reklama ko'rib davom etish"},
    ru:{adStart:"Реклама перед разделом",adMiddle:"Короткая пауза",adEnd:"Последняя реклама",adReady:"Продолжить",adNote:"Посмотрите ролик до конца. Premium учится без рекламы.",adSubTitle:"Оформите подписку — и пользуйтесь ботом без рекламы и без ограничений",adSubPay:"Оформить подписку",adSubCont:"Продолжить с рекламой",adVisit:"Перейти по ссылке",adOpenLink:"Открыть ссылку рекламодателя?",b1:"Все уроки HSK 1–4",b2:"AI Voice — безлимит",b3:"Безлимит тестов и работа над ошибками",loading:"Загрузка рекламы...",failed:"Видео рекламы не загрузилось",failedNote:"Если экран остаётся чёрным, нужен MP4 H.264/AAC.",limitHead:"Не останавливайся — впереди самое интересное!",limitSub:"С подпиской исчезают все ограничения: учишься быстро, легко и без лимитов. Освой китайский за пару месяцев — то, что начнёшь сегодня, завтра станет результатом.",limitSubscribe:"Открыть подписку",limitAd:"Или продолжить с рекламой"},
    tj:{adStart:"Реклама пеш аз бахш",adMiddle:"Танаффуси кӯтоҳи реклама",adEnd:"Рекламаи охирин",adReady:"Идома",adNote:"Роликро то охир бинед. Premium бе реклама меомӯзад.",adSubTitle:"Обуна шавед — аз бот бе реклама ва бе ягон маҳдудият истифода баред",adSubPay:"Обуна шудан",adSubCont:"Идома бо реклама",adVisit:"Гузаштан ба ҳавола",adOpenLink:"Ҳаволаи рекламаро мекушоед?",b1:"Ҳамаи дарсҳои HSK 1–4",b2:"AI Voice — бепоён",b3:"Тестҳои бепоён ва кор бар хатоҳо",loading:"Реклама бор мешавад...",failed:"Видеои реклама бор нашуд",failedNote:"Агар экран сиёҳ монад, видео бояд MP4 H.264/AAC бошад.",limitHead:"Наист — беҳтарин қисмаш дар пеш аст!",limitSub:"Бо обуна ҳама маҳдудиятҳо нест мешаванд: зуд, осон ва бе лимит меомӯзӣ. Забони чиниро дар чанд моҳ аз худ кун — он чи имрӯз оғоз мекунӣ, фардо натиҷа мешавад.",limitSubscribe:"Кушодани обуна",limitAd:"Ё бо реклама идома додан"}
  };
  function T(){ return I18N[CFG.lang] || I18N.uz; }

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
  +'.caa-video{width:100%;height:100%;min-height:320px;max-height:none;object-fit:contain;background:#000;border-radius:16px;border:1px solid rgba(255,255,255,.12)}'
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
  /* Limit-promo (bepul tugagach): obuna asosiy, reklama mayda ikkilamchi */
  +'.caa-ov.limit .caa-sub-t{font-size:17px;line-height:1.3;margin:0 0 6px}'
  +'.caa-sub-desc{margin:0 0 6px;font-size:13px;line-height:1.45;color:rgba(255,255,255,.72);text-align:center}'
  +'.caa-sub-desc[hidden]{display:none!important}'
  +'.caa-limit-foot{display:flex;flex-direction:column;gap:2px;margin-top:6px}'
  +'.caa-limit-foot[hidden]{display:none!important}'
  +'.caa-limit-link{background:transparent;border:none;color:rgba(255,255,255,.58);font-family:inherit;font-size:13px;font-weight:600;padding:9px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px}'
  +'.caa-limit-link[hidden]{display:none!important}'
  +'.caa-limit-link.ad{color:rgba(255,255,255,.84)}'
  +'.caa-limit-link i{font-size:15px}'
  /* Chiqish (X) — faqat limit-promoda, o\'ng yuqori burchakda */
  +'.caa-x{position:absolute;top:calc(10px + env(safe-area-inset-top,0px));right:12px;width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.16);color:#fff;display:none;align-items:center;justify-content:center;font-size:18px;z-index:6;cursor:pointer;-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}'
  +'.caa-ov.limit .caa-x{display:flex}';

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
      +'<div class="caa-status" hidden></div>'
      +'<span class="caa-visit" hidden><i class="ti ti-external-link"></i> <span class="caa-visit-t"></span></span></div>'
      +'<div class="caa-promo"><div class="caa-promo-slide"></div><div class="caa-dots"></div></div>'
      +'<div class="caa-meta"><b class="caa-title"></b><small class="caa-note"></small>'
      +'<button class="caa-cta caa-cta0" disabled></button>'
      +'<div class="caa-sub" hidden><p class="caa-sub-t"></p><p class="caa-sub-desc" hidden></p><div class="caa-benefits"></div>'
      +'<button class="caa-cta caa-pay"></button><button class="caa-cta ghost caa-cont"></button>'
      +'<div class="caa-limit-foot" hidden><button class="caa-limit-link ad caa-lim-ad" hidden></button></div></div>'
      +'</div>'
      +'<button class="caa-x" aria-label="close"><i class="ti ti-x"></i></button>'
      +'</div>';
    document.body.appendChild(ov);
    var q = function(s){return ov.querySelector(s)};
    els = {ov:ov, box:q(".caa-box"), label:q(".caa-label"), count:q(".caa-count"), vwrap:q(".caa-vwrap"),
      video:q(".caa-video"), status:q(".caa-status"), visit:q(".caa-visit"), visitT:q(".caa-visit-t"),
      promo:q(".caa-promo"), promoSlide:q(".caa-promo-slide"), dots:q(".caa-dots"),
      title:q(".caa-title"), note:q(".caa-note"), cta0:q(".caa-cta0"), sub:q(".caa-sub"),
      subTitle:q(".caa-sub-t"), subDesc:q(".caa-sub-desc"), benefits:q(".caa-benefits"), pay:q(".caa-pay"), cont:q(".caa-cont"),
      limFoot:q(".caa-limit-foot"), limAd:q(".caa-lim-ad"), x:q(".caa-x")};
    els.vwrap.addEventListener("click", openAdLink);
    return els;
  }

  function haptic(ok){try{var tg=window.Telegram&&window.Telegram.WebApp;tg&&tg.HapticFeedback&&tg.HapticFeedback.impactOccurred(ok?"medium":"light")}catch(e){}}

  var STATE = {timer:null,loadTimer:null,resolve:null,reject:null,ad:null,placement:"start",watched:0,ready:false,busy:false};
  function resetState(){STATE={timer:null,loadTimer:null,resolve:null,reject:null,ad:null,placement:"start",watched:0,ready:false,busy:false}}
  function placementTitle(p){var t=T();return p==="middle"?t.adMiddle:(p==="end"?t.adEnd:t.adStart)}
  function adDuration(ad){return Math.max(5,Math.min(120,Number(ad&&ad.duration_seconds)||7))}

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

  function fetchAds(placement){
    var url="/api/v3/ad?placement="+encodeURIComponent(placement)
      +"&level="+encodeURIComponent(CFG.level||"hsk1")
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
  function recordView(ad,placement,watched){
    if(!CFG.initData)return Promise.resolve({ok:true});
    return fetch("/api/v3/ad/view",{method:"POST",headers:{"Content-Type":"application/json","X-Telegram-Init-Data":CFG.initData},
      body:JSON.stringify({ad_id:ad.id,level:CFG.level||"hsk1",lesson_order:0,feature:CFG.feature||"",placement:placement,watched_seconds:watched})})
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
  function closeOverlay(){
    clearInterval(STATE.timer);clearTimeout(STATE.loadTimer);
    try{var v=els.video;resetVideo(v);v.pause();v.removeAttribute("src");v.load()}catch(e){}
    stopPromo();els.ov.classList.remove("caa-done");setStatus("");
    els.ov.classList.remove("on");els.ov.setAttribute("aria-hidden","true");
  }
  function setSubVisible(vis){els.sub.hidden=!vis;els.sub.style.display=vis?"grid":"none"}

  /* Rolik tugagach "davom" bosilganda. */
  function done(){
    if(!STATE.ready||STATE.busy)return;STATE.busy=true;
    els.cont.disabled=true;els.cont.innerHTML='<i class="ti ti-loader-2"></i> …';
    function finish(){closeOverlay();var r=STATE.resolve;resetState();if(r)r()}
    recordView(STATE.ad,STATE.placement,STATE.watched).then(finish).catch(finish);
  }
  function subscribe(){closeOverlay();resetState();if(typeof CFG.onSubscribe==="function")CFG.onSubscribe()}

  function play(placement){
    ensureDom();
    return new Promise(function(resolve,reject){
      fetchAds(placement).then(function(ads){
        var t=T();
        els.note.textContent=t.adNote;
        els.subTitle.textContent=t.adSubTitle;
        els.benefits.innerHTML=[t.b1,t.b2,t.b3].map(function(b){return '<div class="caa-ben"><i class="ti ti-circle-check"></i><span>'+esc(b)+'</span></div>'}).join("");
        els.pay.innerHTML='<i class="ti ti-lock-open"></i> '+esc(t.adSubPay);
        els.pay.onclick=subscribe;els.cont.onclick=done;
        /* Limit-promodan qolgan holatni tozalaymiz (subDesc, foot, cont ko'rinishi). */
        els.subDesc.hidden=true;els.limFoot.hidden=true;els.cont.style.display="";
        els.ov.classList.remove("limit");
        els.ov.classList.add("on");els.ov.setAttribute("aria-hidden","false");
        clearInterval(STATE.timer);
        var video=els.video;
        function playAd(i){
          var ad=ads[i],duration=adDuration(ad),isLast=(i>=ads.length-1),multi=ads.length>1;
          clearInterval(STATE.timer);clearTimeout(STATE.loadTimer);resetVideo(video);
          STATE={timer:null,loadTimer:null,resolve:resolve,reject:reject,ad:ad,placement:placement,watched:0,ready:false,busy:false};
          els.label.textContent=placementTitle(placement)+(multi?" · "+(i+1)+"/"+ads.length:"");
          els.title.textContent=ad.title||placementTitle(placement);
          els.note.textContent=t.adNote;
          var hasLink=!!ad.link_url;
          if(hasLink){els.visitT.textContent=t.adVisit;els.visit.hidden=false}else{els.visit.hidden=true}
          stopPromo();els.ov.classList.remove("caa-done");
          els.vwrap.style.display="";els.vwrap.style.cursor=hasLink?"pointer":"default";
          els.cont.disabled=false;els.cont.innerHTML='<i class="ti ti-arrow-right"></i> '+t.adSubCont;
          setSubVisible(false);els.cta0.style.display="none";els.cta0.disabled=true;
          els.count.textContent="...";setStatus(t.loading);
          var srcBase=ad.media_url,loadAttempt=0,left=duration,timer=null,started=false,failed=false;
          function setSrc(bust){
            try{video.pause()}catch(e){}
            video.removeAttribute("src");try{video.load()}catch(e){}
            video.src=bust?srcBase+(srcBase.indexOf("?")>=0?"&":"?")+"r="+Date.now():srcBase;
            video.loop=true;video.muted=true;try{video.load()}catch(e){}
          }
          function armGuard(ms){clearTimeout(STATE.loadTimer);STATE.loadTimer=setTimeout(onLoadTimeout,ms)}
          function tryPlay(){var p;try{p=video.play()}catch(e){}if(p&&p.then)p.then(startCountdown).catch(function(){if(video.readyState>=2)startCountdown()})}
          function onLoadTimeout(){
            if(started||failed||STATE.ad!==ad)return;
            if(video.readyState>=2){startCountdown();return}
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
            if(!isLast){recordView(ad,placement,duration).catch(function(){});playAd(i+1);}
            else if(placement==="end"){
              /* YAKUNIY reklama tugadi — "Obuna ol / Reklama bilan davom etish"
                 bloki chiqadi (davom bosilganda done() ko'rilganini yozib yakunlaydi). */
              try{video.pause()}catch(e){}
              els.vwrap.style.display="none";els.ov.classList.add("caa-done");startPromo();
              STATE.ready=true;els.cta0.style.display="none";els.cont.style.display="";setSubVisible(true);
            }else{
              /* start / middle reklama — obuna taklifi limit ekranida allaqachon
                 bo'lgan, shuning uchun bu yerda YANA obunaga majburlamaymiz:
                 ko'rilganini fonda yozib, to'g'ridan davom etamiz. */
              try{video.pause()}catch(e){}
              recordView(ad,placement,duration).catch(function(){});
              var resolve=STATE.resolve;
              closeOverlay();resetState();
              if(typeof resolve==="function")resolve();
            }
          }
          function startCountdown(){
            if(started||failed||STATE.ad!==ad)return;
            started=true;clearTimeout(STATE.loadTimer);setStatus("");draw();
            timer=setInterval(function(){left=Math.max(0,left-1);STATE.watched=duration-left;if(left<=0)clearInterval(timer);draw();},1000);
            STATE.timer=timer;
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
          video.onloadedmetadata=tryPlay;video.onloadeddata=startCountdown;video.oncanplay=startCountdown;
          video.onplaying=startCountdown;video.ontimeupdate=startCountdown;video.onerror=onMediaError;
          video.onstalled=video.onwaiting=function(){if(started||failed||STATE.ad!==ad)return;armGuard(12000)};
          setSrc(false);armGuard(12000);
          if(video.readyState>=2)startCountdown();
          tryPlay();
        }
        playAd(0);
      }).catch(function(){reject(new Error("course_ad_not_found"))});
    });
  }

  function _closeLimit(){
    stopPromo();
    els.ov.classList.remove("on","caa-done","limit");
    els.ov.setAttribute("aria-hidden","true");
    if(els.limFoot)els.limFoot.hidden=true;
  }
  /* Bepul limit tugagach ko'rsatiladigan promo ekran — reklama tugaganidagi
     ekran bilan bir xil uslub (aylanuvchi karusel + obuna), lekin obuna ASOSIY,
     "reklama bilan davom etish" esa mayda ikkilamchi havola.
     opts: {adAvailable, onSubscribe, onContinueAd, onBack}. */
  function showLimitPromo(opts){
    opts=opts||{};
    ensureDom();
    var t=T();
    els.subTitle.textContent=t.limitHead||t.adSubTitle;
    if(t.limitSub){els.subDesc.textContent=t.limitSub;els.subDesc.hidden=false}else{els.subDesc.hidden=true}
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
    /* Video yo'q — to'g'ridan promo (done) ko'rinishi. */
    try{els.video.pause();els.video.removeAttribute("src");els.video.load()}catch(e){}
    els.vwrap.style.display="none";
    setStatus("");
    els.ov.classList.add("on","caa-done","limit");
    els.ov.setAttribute("aria-hidden","false");
    setSubVisible(true);
    startPromo();
  }

  window.CourseAds = {
    config:function(o){for(var k in o){if(Object.prototype.hasOwnProperty.call(o,k))CFG[k]=o[k]}},
    play:play,
    showLimitPromo:showLimitPromo,
    closeLimit:_closeLimit,
    available:function(){return !!els}
  };
})();
