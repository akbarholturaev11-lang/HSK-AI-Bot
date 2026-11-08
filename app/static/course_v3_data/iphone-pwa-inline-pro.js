/* PWA-only inline Pro checkout. Real price / entitlements always come from the server. */
(function () {
  "use strict";
  if (!/^\/iphone-pwa\/(?:course|practice\/(?:voice|recognition|pronunciation|memorize|test|mistakes))$/.test(location.pathname)) return;
  if (window.HSKPwaInlinePro) return;

  var API = {
    overview: "/api/v3/pwa/subscription/overview",
    start: "/api/v3/pwa/subscription/lava/start",
    status: "/api/v3/pwa/subscription/lava/status",
    offer: "/api/v3/pwa/subscription/exit-offer",
    analytics: "/api/v3/pwa/subscription/inline-event"
  };
  var WORDS = {
    ru: {title:"Лимит исчерпан",subtitle:"Оформите Pro, чтобы продолжить",benefits:["Уроки без ограничений","Разговорная практика с ИИ","Учёба без рекламы"],one:"1 месяц",
      three:"3 месяца",six:"6 месяцев",year:"1 год",pay:"Получить Pro",
      more:"Другие тарифы",lava:"Visa / Mastercard — Lava.top",
      manual:"Обычный способ оплаты",manualHint:"Банковская карта, Alipay или WeChat",
      choose:"Выберите способ оплаты",email:"Email для оплаты",continue:"Продолжить оплату",
      close:"Закрыть",back:"Назад",loading:"Загружаем тарифы…",unavailable:"Тарифы временно недоступны",
      retry:"Повторить",pending:"Оплата ожидает подтверждения",paying:"Проверяем оплату…",
      reopen:"Открыть Lava.top",paymentReady:"Ссылка Lava.top готова",paid:"Pro активирован",return:"Вернуться к обучению",
      error:"Не удалось загрузить оплату. Попробуйте ещё раз.",exitTitle:"Специальная скидка 20%",
      exitText:"Заберите скидку на первый платёж и продолжайте обучение",
      accept:"Забрать скидку",decline:"Нет, спасибо",
      renewal:"Продление оплачивается по стандартной цене. Автопродление можно отменить.",
      comparison:"Ориентировочная цена для сравнения, не предыдущая цена",
      saving:"Скидка 20% применена",normal:"Стоимость с учётом действующей скидки",
      manualNoExit:"Скидка при выходе действует только при оплате Lava.top",
      blocked:"Проверьте текущий платёж или действующую подписку",
      missingEmail:"Укажите действительный email",success:"Платёж подтверждён сервером"},
    uz: {title:"Limit tugadi",subtitle:"Davom etish uchun Pro oling",benefits:["Cheksiz darslar","AI bilan ovozli mashqlar","Reklamasiz o‘rganing"],one:"1 oy",
      three:"3 oy",six:"6 oy",year:"1 yil",pay:"Pro olish",
      more:"Boshqa tariflar",lava:"Visa / Mastercard — Lava.top",
      manual:"Oddiy to‘lov usuli",manualHint:"Bank kartasi, Alipay yoki WeChat",
      choose:"To‘lov usulini tanlang",email:"To‘lov uchun email",continue:"To‘lovni davom ettirish",
      close:"Yopish",back:"Orqaga",loading:"Tariflar yuklanmoqda…",unavailable:"Tariflar hozir mavjud emas",
      retry:"Qayta urinish",pending:"To‘lov tasdiqlanishi kutilmoqda",paying:"To‘lov tekshirilmoqda…",
      reopen:"Lava.top’ni ochish",paymentReady:"Lava.top havolasi tayyor",paid:"Pro faollashtirildi",return:"O‘qishga qaytish",
      error:"To‘lov ma’lumotlari yuklanmadi. Qayta urinib ko‘ring.",exitTitle:"Maxsus 20% chegirma",
      exitText:"Birinchi to‘lov uchun 20% chegirma oling",accept:"Chegirmani olish",decline:"Yo‘q, rahmat",
      renewal:"Keyingi to‘lovlar oddiy narxda. Avtoyangilanishni bekor qilish mumkin.",
      comparison:"Taqqoslash uchun taxminiy narx, oldingi narx emas",
      saving:"20% chegirma qo‘llandi",normal:"Amaldagi chegirmali narx",
      manualNoExit:"Chiqish chegirmasi faqat Lava.top to‘loviga tegishli",
      blocked:"Joriy to‘lov yoki faol obunani tekshiring",
      missingEmail:"To‘g‘ri email kiriting",success:"To‘lov serverda tasdiqlandi"},
    tj: {title:"Лимит тамом шуд",subtitle:"Барои идома Pro гиред",benefits:["Дарсҳо бе маҳдудият","Машқи овозӣ бо AI","Омӯзиш бе реклама"],one:"1 моҳ",
      three:"3 моҳ",six:"6 моҳ",year:"1 сол",pay:"Гирифтани Pro",
      more:"Тарифҳои дигар",lava:"Visa / Mastercard — Lava.top",
      manual:"Пардохти оддӣ",manualHint:"Корти бонкӣ, Alipay ё WeChat",
      choose:"Роҳи пардохтро интихоб кунед",email:"Email барои пардохт",continue:"Идомаи пардохт",
      close:"Пӯшидан",back:"Бозгашт",loading:"Тарифҳо бор шуда истодаанд…",unavailable:"Тарифҳо дастрас нестанд",
      retry:"Аз нав кӯшиш кунед",pending:"Пардохт интизори тасдиқ аст",paying:"Пардохт санҷида мешавад…",
      reopen:"Кушодани Lava.top",paymentReady:"Пайванди Lava.top омода аст",paid:"Pro фаъол шуд",return:"Бозгашт ба омӯзиш",
      error:"Маълумоти пардохт дастрас нашуд. Аз нав кӯшиш кунед.",exitTitle:"20% тахфифи махсус",
      exitText:"Барои пардохти аввал 20% тахфиф гиред",accept:"Гирифтани тахфиф",decline:"Не, ташаккур",
      renewal:"Пардохти навбатӣ бо нархи муқаррарӣ аст. Тамдиди худкорро бекор кардан мумкин.",
      comparison:"Нархи тахминӣ барои муқоиса, на нархи қаблӣ",
      saving:"20% тахфиф татбиқ шуд",normal:"Нарх бо тахфифи воқеӣ",
      manualNoExit:"Тахфифи баромад танҳо барои Lava.top аст",
      blocked:"Пардохти ҷорӣ ё обунаи фаъолро санҷед",
      missingEmail:"Email-и дуруст ворид кунед",success:"Пардохт аз тарафи сервер тасдиқ шуд"}
  };
  var NAMES = { "1_month":"one", "3_months":"three", "6_months":"six", "12_months":"year" };
  var order = ["1_month","3_months","6_months","12_months"];
  var root, body, heading, info, panda, back, closeButton, lastFocus, state, tick = null, actorPromise = null, run = 0;
  function txt(key) { return (WORDS[state.lang]||WORDS.ru)[key]; }
  function el(tag, cls, value) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (value !== undefined) node.textContent = value;
    return node;
  }
  function btn(label, cls, fn) {
    var node = el("button",cls,label);
    node.type="button";
    node.addEventListener("click",fn);
    return node;
  }
  function session() {
    if (!actorPromise) actorPromise = fetch("/api/v3/pwa-auth/session",{
      credentials:"same-origin",cache:"no-store",redirect:"error"
    }).then(function(r) {
      if (r.status===401) { location.assign("/iphone-pwa"); throw Error("login_required"); }
      if (!r.ok) throw Error("session_unavailable");
      return r.json();
    }).then(function(data) {
      if (!data || data.ok !== true || !data.csrf || !Number.isSafeInteger(Number(data.user_id)))
        throw Error("session_invalid");
      return data;
    }).catch(function(e) { actorPromise=null; throw e; });
    return actorPromise;
  }
  function request(path,payload) {
    return session().then(function(a) {
      return fetch(path,{method:"POST",credentials:"same-origin",cache:"no-store",redirect:"error",
        headers:{"Content-Type":"application/json","X-HSK-PWA-CSRF":a.csrf},
        body:JSON.stringify(payload||{})});
    }).then(function(r) {
      return r.json().catch(function(){return {}}).then(function(data) {
        if (!r.ok || !data || data.ok===false) {
          var error = Error(data.error||data.code||"request_failed"); error.code=data.error||data.code;
          throw error;
        }
        return data;
      });
    });
  }
  // Fire-and-forget analytics: real payment state never depends on telemetry.
  function emit(event,plan,method) {
    if (!state) return;
    var payload = {
      event:event,source:state.source,attempt_id:state.attempt,
      event_id:state.attempt+":"+(++state.eventSeq),
      plan_type:plan||state.plan||null,method:method||null
    };
    request(API.analytics,payload).catch(function(){});
  }
  function relativePrice(value) {
    var n=Number(value);
    if (!Number.isFinite(n)||n<=0) return null;
    // UI-only roughly +30% comparison, rounded to the nearest .99.
    // It is NOT a historical price and NEVER sent to the payment API.
    var result=Math.round(n*1.3-0.99)+0.99;
    if(result<=n)result=Math.ceil(n-0.99+1e-9)+0.99;
    return result.toFixed(2);
  }
  function money(value,currency) {
    var n=Number(value);
    if (!Number.isFinite(n)||n<0) return "";
    return n.toFixed(2)+" "+(currency||"");
  }
  function ensure() {
    if (root) return;
    root=el("section");root.id="hsk-inline-pro";root.hidden=true;
    root.setAttribute("role","dialog");root.setAttribute("aria-modal","true");
    var sheet=el("div","hip-sheet");
    var header=el("div","hip-header");
    panda=el("div","hip-panda");panda.setAttribute("aria-hidden","true");
    panda.innerHTML="<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 128 144\" role=\"img\" aria-hidden=\"true\" focusable=\"false\">\n  <ellipse cx=\"30\" cy=\"28\" rx=\"15\" ry=\"19\" transform=\"rotate(-27 30 28)\" fill=\"#302A26\"/>\n  <ellipse cx=\"98\" cy=\"28\" rx=\"15\" ry=\"19\" transform=\"rotate(27 98 28)\" fill=\"#302A26\"/>\n  <ellipse cx=\"64\" cy=\"110\" rx=\"29\" ry=\"29\" fill=\"#302A26\"/>\n  <ellipse cx=\"64\" cy=\"112\" rx=\"22\" ry=\"26\" fill=\"#FFFEFA\"/>\n  <ellipse cx=\"64\" cy=\"64\" rx=\"40\" ry=\"41\" fill=\"#FFFEFA\" stroke=\"#302A26\" stroke-width=\"2.6\"/>\n  <ellipse cx=\"46\" cy=\"61\" rx=\"13\" ry=\"18\" transform=\"rotate(21 46 61)\" fill=\"#302A26\"/>\n  <ellipse cx=\"82\" cy=\"61\" rx=\"13\" ry=\"18\" transform=\"rotate(-21 82 61)\" fill=\"#302A26\"/>\n  <ellipse cx=\"50\" cy=\"60\" rx=\"4.6\" ry=\"6.2\" fill=\"#FFFEFA\"/>\n  <ellipse cx=\"78\" cy=\"60\" rx=\"4.6\" ry=\"6.2\" fill=\"#FFFEFA\"/>\n  <circle cx=\"51\" cy=\"58\" r=\"1.8\" fill=\"#302A26\"/>\n  <circle cx=\"79\" cy=\"58\" r=\"1.8\" fill=\"#302A26\"/>\n  <ellipse cx=\"64\" cy=\"80\" rx=\"7.6\" ry=\"5.4\" fill=\"#302A26\"/>\n  <path d=\"M64 85q-6 10-12 3m12-3q6 10 12 3\" fill=\"none\" stroke=\"#302A26\" stroke-width=\"2.4\" stroke-linecap=\"round\"/>\n  <ellipse cx=\"40\" cy=\"102\" rx=\"10\" ry=\"16\" transform=\"rotate(-28 40 102)\" fill=\"#302A26\"/>\n  <ellipse cx=\"88\" cy=\"102\" rx=\"10\" ry=\"16\" transform=\"rotate(28 88 102)\" fill=\"#302A26\"/>\n  <ellipse cx=\"47\" cy=\"133\" rx=\"13\" ry=\"7\" fill=\"#302A26\"/>\n  <ellipse cx=\"81\" cy=\"133\" rx=\"13\" ry=\"7\" fill=\"#302A26\"/>\n  <path d=\"M47 108q9-4 17 2q8-6 17-2v25q-8-4-17 2q-9-6-17-2Z\" fill=\"#E04A40\" stroke=\"#B23530\" stroke-width=\"2\" stroke-linejoin=\"round\"/>\n  <path d=\"M64 110v25\" stroke=\"#FDF9F0\" stroke-width=\"2\" opacity=\".82\"/>\n  <path d=\"M36 113q4 7 12 8m44-8q-4 7-12 8\" fill=\"none\" stroke=\"#302A26\" stroke-width=\"7\" stroke-linecap=\"round\"/>\n</svg>";
    heading=el("h2","hip-title");
    info=el("p","hip-summary");
    header.append(panda,heading,info);
    body=el("div","hip-body");
    back=btn("‹","hip-back",goBack);
    closeButton=btn("×","hip-close",requestDismiss);
    sheet.append(back,closeButton,header,body);
    root.appendChild(sheet);
    document.body.appendChild(root);
    root.addEventListener("click",function(ev){if(ev.target===root)requestDismiss()});
  }
  function available() {
    var lava=state.data && state.data.lava;
    return lava && Array.isArray(lava.plans) ? lava.plans.filter(function(p) {
      return p && order.indexOf(p.plan_type)!==-1 && p.amount!==null && p.amount!==undefined;
    }) : [];
  }
  function selectedPlan() {
    return available().find(function(p){return p.plan_type===state.plan}) || null;
  }
  function elementPlans(all) {
    var plans=available().filter(function(p){return all||p.plan_type==="1_month"||p.plan_type==="12_months"});
    var grid=el("div","hip-plans"+(all?" all":""));
    plans.forEach(function(plan) {
      var card=btn("","hip-plan",function(){
        state.plan=plan.plan_type;emit("pwa_pro_plan_selected",plan.plan_type,"lava");render();
      });
      card.setAttribute("aria-pressed",String(state.plan===plan.plan_type));
      card.appendChild(el("span","term",txt(NAMES[plan.plan_type])));
      var priceLine=el("span","hip-price-line");
      priceLine.appendChild(el("span","price",money(plan.amount,plan.currency)));
      if (Number(plan.discount_percent)>0 && plan.base_amount!=null) {
        priceLine.appendChild(el("span","comparison",Number(plan.base_amount).toFixed(2)));
        card.appendChild(priceLine);
        card.appendChild(el("span","badge","−"+Number(plan.discount_percent)+"%"));
      } else {
        var reference=relativePrice(plan.amount);
        if (reference) {
          var strike=el("span","comparison",reference);
          strike.title=txt("comparison");
          strike.setAttribute("aria-label",txt("comparison")+": "+money(reference,plan.currency));
          priceLine.appendChild(strike);
        }
        card.appendChild(priceLine);
      }
      grid.appendChild(card);
    });
    return grid;
  }
  function render() {
    if (!root||!state||root.hidden) return;
    var s=state.screen, plans=available(), isLava=state.data&&state.data.lava;
    root.dataset.screen=s;
    body.style.padding="";
    heading.textContent=s==="exit"?txt("exitTitle"):s==="more"?txt("choose"):txt("title");
    info.textContent=s==="exit"?txt("exitText"):s==="more"?"":txt("subtitle");
    panda.hidden=!(["main","loading","exit"].includes(s));
    closeButton.setAttribute("aria-label",txt("close"));
    back.hidden=["main","loading","exit","success"].indexOf(s)!==-1;
    back.setAttribute("aria-label",txt("back"));
    body.replaceChildren();
    if (state.error && s!=="exit") body.appendChild(el("p","hip-error",state.error));
    if (s==="main"||s==="loading") {
      var benefits=el("ul","hip-benefits");
      (txt("benefits")||[]).forEach(function(value){
        benefits.appendChild(el("li","hip-benefit",value));
      });
      body.appendChild(benefits);
    }
    if (s==="loading") {
      var loadingPlans=el("div","hip-plans");
      for(var n=0;n<2;n++) loadingPlans.appendChild(el("div","hip-plan hip-skeleton"));
      body.appendChild(loadingPlans);
      var loadingCta=btn(txt("pay"),"hip-primary",function(){});
      loadingCta.disabled=true;
      body.appendChild(loadingCta);
      body.appendChild(el("div","hip-loading",txt("loading")));
      return;
    }
    if (s==="exit") {
      body.appendChild(el("p","hip-emphasis","−20%"));
      body.appendChild(btn(txt("accept"),"hip-primary",claimExit));
      body.appendChild(btn(txt("decline"),"hip-secondary",function(){emit("pwa_pro_exit_declined");close()}));
      body.appendChild(el("p","hip-small",txt("renewal")));
      return;
    }
    if (s==="success") {
      body.appendChild(el("p","hip-emphasis","✓ "+txt("paid")));
      body.appendChild(el("p","hip-small",txt("success")));
      body.appendChild(btn(txt("return"),"hip-primary",close));
      return;
    }
    if (s==="waiting") {
      body.appendChild(el("p","hip-emphasis",txt("paymentReady")));
      if (state.paymentUrl) {
        // An actual user tap opens the real provider URL. Never create a
        // blank popup before the asynchronous invoice is ready on iOS.
        var link=el("a","hip-primary",txt("reopen"));
        link.href=state.paymentUrl;
        link.target="_blank";link.rel="noopener noreferrer";
        body.appendChild(link);
      }
      body.appendChild(btn(txt("return"),"hip-secondary",close));
      return;
    }
    if (s!=="manual"&&state.data&&(state.data.pending_payment||state.data.access&&state.data.access.is_paid||
        state.data.lava&&state.data.lava.blocked_reason)) {
      body.appendChild(el("p","hip-emphasis",state.data.access&&state.data.access.is_paid?
        txt("paid"):(state.data.pending_payment?txt("pending"):txt("blocked"))));
      if (state.data.pending_payment) {
        body.appendChild(btn(txt("manual"),"hip-secondary",function(){emit("pwa_pro_method_selected",null,"manual");state.screen="manual";render()}));
      }
      body.appendChild(btn(txt("return"),"hip-primary",close));
      return;
    }
    if (s==="manual") {
      var iframe=el("iframe","hip-checkout");
      iframe.title=txt("manual");
      iframe.setAttribute("loading","eager");
      var q=new URLSearchParams({embedded:"1",source:state.source,lang:state.lang,mode:"subscription",return_to:"course",inline_manual:"1"});
      iframe.src="/iphone-pwa/checkout?"+q.toString();
      body.appendChild(iframe);
      return;
    }
    if (s==="email") {
      var p=selectedPlan();
      if (!p) {state.screen="main";return render()}
      body.appendChild(el("p","hip-emphasis",txt(NAMES[p.plan_type])+" · "+money(p.amount,p.currency)));
      var input=el("input","hip-input");
      input.type="email";input.autocomplete="email";input.inputMode="email";input.placeholder=txt("email");
      input.value=state.email||"";
      input.addEventListener("input",function(){state.email=input.value});
      body.appendChild(input);
      body.appendChild(btn(txt("continue"),"hip-primary",startPayment));
      body.appendChild(el("p","hip-small",txt("renewal")));
      return;
    }
    if (s==="more") {
      if (plans.length) {
        body.appendChild(btn(txt("lava"),"hip-method",function(){emit("pwa_pro_method_selected",null,"lava");state.screen="all";render()}));
      }
      if (state.data && state.data.lava && state.data.lava.mode==="lava_only") {
        body.appendChild(el("p","hip-small",txt("unavailable")));
      } else {
        body.appendChild(btn(txt("manual")+"  ›","hip-method",function(){
          emit("pwa_pro_method_selected",null,"manual");state.screen="manual";render();
        }));
        if (state.mode==="exit_discount") body.appendChild(el("p","hip-small",txt("manualNoExit")));
      }
      return;
    }
    if (!plans.length) {
      body.appendChild(el("p","hip-small",isLava&&isLava.blocked_reason?txt("blocked"):txt("unavailable")));
      body.appendChild(btn(txt("retry"),"hip-primary",load));
      if (!isLava||isLava.mode!=="lava_only") body.appendChild(btn(txt("manual"),"hip-secondary",function(){emit("pwa_pro_method_selected",null,"manual");state.screen="manual";render()}));
      return;
    }
    if (!selectedPlan() || (s==="main" && state.plan!=="1_month" && state.plan!=="12_months")) {
      state.plan=plans.some(function(p){return p.plan_type==="1_month"})?"1_month":plans[0].plan_type;
    }
    body.appendChild(elementPlans(s==="all"));
    if (state.mode==="exit_discount") body.appendChild(el("p","hip-small",txt("saving")));
    body.appendChild(btn(txt("pay"),"hip-primary",function() {
      if (!selectedPlan()) return;
      if (!state.email) {state.screen="email";render();return}
      startPayment();
    }));
    body.appendChild(btn(txt("more"),"hip-secondary",function(){emit("pwa_pro_more_opened");state.screen="more";render()}));
  }
  function load() {
    if (!state) return;
    var current=++run;
    state.screen="loading";state.error="";render();
    request(API.overview,{source:state.source,mode:state.mode,plan:state.plan,
      supports_lava:true,inline_preview:true,attempt_id:state.attempt}).then(function(data) {
      if (!state||current!==run) return;
      state.data=data;
      state.email=(data.lava&&data.lava.email)||state.email||"";
      state.screen="main";render();
    }).catch(function(err) {
      if (!state||current!==run) return;
      state.data={};state.screen="main";state.error=txt("error");render();
    });
  }
  function close() {
    if (!root||root.hidden) return;
    clearInterval(tick);tick=null;run++;root.hidden=true;body.replaceChildren();body.style.padding="";
    document.documentElement.style.overflow=state&&state.previousOverflow||"";
    if (lastFocus&&lastFocus.isConnected) lastFocus.focus({preventScroll:true});
    var wasPaid=Boolean(state&&state.paid);
    if (state&&typeof state.onClose==="function") state.onClose();
    state=null;
    if(wasPaid){
      if(location.pathname==="/iphone-pwa/course"){
        try {
          if(typeof window.refreshPwaCheckoutMap==="function") {
            window.refreshPwaCheckoutMap().catch(function(){});
          }
        }catch(e){}
      } else {
        // Standalone PWA practice re-runs its server-side gate as Pro.
        location.reload();
      }
    }
  }
  function requestDismiss() {
    if (!state) return;
    if (state.mode==="exit_discount"||state.screen==="success"||state.screen==="waiting"||state.screen==="manual") {emit("pwa_pro_dismissed");close();return}
    if (state.screen==="exit") {emit("pwa_pro_exit_declined");close();return}
    var current=++run;
    state.screen="loading";render();
    request(API.offer,{action:"view",source:state.source}).then(function(data) {
      if (!state||current!==run) return;
      if (!data.available) {emit("pwa_pro_dismissed");close();return}
      emit("pwa_pro_exit_offered");state.screen="exit";render();
    }).catch(function(){if(state&&current===run){emit("pwa_pro_dismissed");close()}});
  }
  function claimExit() {
    if (!state) return;
    var current=++run;
    state.screen="loading";render();
    request(API.offer,{action:"claim",source:state.source}).then(function(data) {
      if (!state||current!==run) return;
      if (!data.available) {close();return}
      emit("pwa_pro_exit_claimed");state.mode="exit_discount";
      load();
    }).catch(function(){if(state&&current===run){state.error=txt("error");state.screen="main";render()}});
  }
  function goBack() {
    if (!state) return;
    if (state.screen==="manual"||state.screen==="all"||state.screen==="email")state.screen="more";
    else if(state.screen==="more")state.screen="main";
    else {requestDismiss();return}
    state.error="";render();
  }
  function startPayment() {
    var plan=selectedPlan();
    if (!plan||!state) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((state.email||"").trim())) {
      state.screen="email";state.error=txt("missingEmail");render();return;
    }
    // Do not pre-open about:blank: iOS standalone PWAs can strand the
    // blank window even after a valid provider checkout URL is returned.
    var current=++run;
    state.screen="loading";state.error="";render();
    request(API.start,{plan_type:plan.plan_type,email:state.email.trim(),language:state.lang,
      mode:state.mode,attempt_id:state.attempt,ui_source:state.source}).then(function(data){
      if (!state||current!==run) return;
      var url=new URL(data.payment_url);
      if (url.protocol!=="https:" || !(url.hostname==="lava.top"||url.hostname.endsWith(".lava.top")))
        throw Error("invalid_lava_payment_url");
      state.checkoutId=data.checkout_id;state.paymentUrl=url.href;
      state.screen="waiting";render();beginPolling();
    }).catch(function(){
      if(!state||current!==run)return;
      emit("pwa_pro_checkout_failed",plan.plan_type,"lava");state.error=txt("error");state.screen="email";render();
    });
  }
  function beginPolling() {
    clearInterval(tick);
    var started=Date.now();
    tick=setInterval(function(){
      if (!state||!state.checkoutId||Date.now()-started>15*60*1000) {clearInterval(tick);tick=null;return}
      if (document.visibilityState==="visible")checkStatus();
    },5000);
    checkStatus();
  }
  function checkStatus() {
    if (!state||!state.checkoutId||state.polling)return;
    var current=run, id=state.checkoutId;
    state.polling=true;
    request(API.status,{checkout_id:id}).then(function(result) {
      if (!state||current!==run)return;
      if (result.status==="paid") {
        clearInterval(tick);tick=null;state.paid=true;state.screen="success";state.checkoutId=null;render();
      } else if (result.status==="failed") {
        clearInterval(tick);tick=null;state.screen="main";state.checkoutId=null;
        emit("pwa_pro_checkout_failed");state.error=txt("error");render();
      }
    }).catch(function(){}).finally(function(){if(state&&current===run)state.polling=false});
  }
  function open(opts) {
    opts=opts||{};
    ensure();
    if (!root.hidden)return true;
    lastFocus=document.activeElement;
    var lang=String(opts.lang||document.documentElement.lang||"ru").toLowerCase();
    if(lang==="tg")lang="tj";
    if(!WORDS[lang])lang="ru";
    state={lang:lang,source:String(opts.source||"v3_paywall").slice(0,80),
      mode:"subscription",screen:"loading",plan:"1_month",email:"",attempt:"inline-"+Date.now()+"-"+Math.floor(Math.random()*1000000),eventSeq:0,
      data:null,error:"",polling:false,onClose:opts.onClose,
      previousOverflow:document.documentElement.style.overflow};
    root.hidden=false;
    document.documentElement.style.overflow="hidden";
    root.setAttribute("aria-label","HSK AI Pro");
    closeButton.focus({preventScroll:true});
    emit("pwa_pro_opened");load();
    return true;
  }
  function closeEmbeddedCheckout(child) {
    if (!state||state.screen!=="manual"||!body)return false;
    var iframe=body.querySelector("iframe");
    if (!iframe||iframe.contentWindow!==child)return false;
    state.screen="more";render();return true;
  }
  document.addEventListener("keydown",function(ev) {
    if (!root||root.hidden)return;
    if (ev.key==="Escape"){ev.stopPropagation();ev.preventDefault();goBack()}
  });
  document.addEventListener("visibilitychange",function(){
    if(document.visibilityState==="visible"){
      actorPromise=null;
      if (state&&state.checkoutId)checkStatus();
    }
  });
  window.addEventListener("pageshow",function(e){if(e.persisted){actorPromise=null;if(state&&state.checkoutId)checkStatus()}});
  window.HSKPwaInlinePro={open:open,close:close,closeEmbeddedCheckout:closeEmbeddedCheckout};
})();