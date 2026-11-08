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
  // The learner never sees a payment provider name: one card checkout and
  // one "regular" (bank card / Alipay / WeChat receipt) method.
  var WORDS = {
    ru: {title:"Лимит исчерпан",subtitle:"Оформите Pro, чтобы продолжить",benefits:["Уроки без ограничений","Разговорная практика с ИИ","Учёба без рекламы"],one:"1 месяц",
      three:"3 месяца",six:"6 месяцев",year:"1 год",perMonth:"/ мес",pay:"Получить Pro",
      more:"Другие тарифы",
      manual:"Обычный способ оплаты",manualHint:"Банковская карта, Alipay или WeChat",
      email:"Email для оплаты",continue:"Продолжить оплату",
      close:"Закрыть",back:"Назад",loading:"Загружаем тарифы…",unavailable:"Тарифы временно недоступны",
      retry:"Повторить",pending:"Оплата ожидает подтверждения",paying:"Проверяем оплату…",
      reopen:"Перейти к оплате",paymentReady:"Страница оплаты готова",paid:"Pro активирован",return:"Вернуться к обучению",
      error:"Не удалось загрузить оплату. Попробуйте ещё раз.",exitTitle:"Специальная скидка 20%",
      exitText:"Заберите скидку на первый платёж и продолжайте обучение",
      accept:"Забрать скидку",decline:"Нет, спасибо",
      renewal:"Продление оплачивается по стандартной цене. Автопродление можно отменить.",
      comparison:"Ориентировочная цена для сравнения, не предыдущая цена",
      saving:"Скидка 20% применена",normal:"Стоимость с учётом действующей скидки",
      manualNoExit:"Скидка 20% действует только при онлайн-оплате картой",
      blocked:"Проверьте текущий платёж или действующую подписку",
      missingEmail:"Укажите действительный email",success:"Платёж подтверждён сервером"},
    uz: {title:"Limit tugadi",subtitle:"Davom etish uchun Pro oling",benefits:["Cheksiz darslar","AI bilan ovozli mashqlar","Reklamasiz o‘rganing"],one:"1 oy",
      three:"3 oy",six:"6 oy",year:"1 yil",perMonth:"/ oy",pay:"Pro olish",
      more:"Boshqa tariflar",
      manual:"Oddiy to‘lov usuli",manualHint:"Bank kartasi, Alipay yoki WeChat",
      email:"To‘lov uchun email",continue:"To‘lovni davom ettirish",
      close:"Yopish",back:"Orqaga",loading:"Tariflar yuklanmoqda…",unavailable:"Tariflar hozir mavjud emas",
      retry:"Qayta urinish",pending:"To‘lov tasdiqlanishi kutilmoqda",paying:"To‘lov tekshirilmoqda…",
      reopen:"To‘lovga o‘tish",paymentReady:"To‘lov sahifasi tayyor",paid:"Pro faollashtirildi",return:"O‘qishga qaytish",
      error:"To‘lov ma’lumotlari yuklanmadi. Qayta urinib ko‘ring.",exitTitle:"Maxsus 20% chegirma",
      exitText:"Birinchi to‘lov uchun 20% chegirma oling",accept:"Chegirmani olish",decline:"Yo‘q, rahmat",
      renewal:"Keyingi to‘lovlar oddiy narxda. Avtoyangilanishni bekor qilish mumkin.",
      comparison:"Taqqoslash uchun taxminiy narx, oldingi narx emas",
      saving:"20% chegirma qo‘llandi",normal:"Amaldagi chegirmali narx",
      manualNoExit:"20% chegirma faqat karta orqali onlayn to‘lovga tegishli",
      blocked:"Joriy to‘lov yoki faol obunani tekshiring",
      missingEmail:"To‘g‘ri email kiriting",success:"To‘lov serverda tasdiqlandi"},
    tj: {title:"Лимит тамом шуд",subtitle:"Барои идома Pro гиред",benefits:["Дарсҳо бе маҳдудият","Машқи овозӣ бо AI","Омӯзиш бе реклама"],one:"1 моҳ",
      three:"3 моҳ",six:"6 моҳ",year:"1 сол",perMonth:"/ моҳ",pay:"Гирифтани Pro",
      more:"Тарифҳои дигар",
      manual:"Пардохти оддӣ",manualHint:"Корти бонкӣ, Alipay ё WeChat",
      email:"Email барои пардохт",continue:"Идомаи пардохт",
      close:"Пӯшидан",back:"Бозгашт",loading:"Тарифҳо бор шуда истодаанд…",unavailable:"Тарифҳо дастрас нестанд",
      retry:"Аз нав кӯшиш кунед",pending:"Пардохт интизори тасдиқ аст",paying:"Пардохт санҷида мешавад…",
      reopen:"Ба пардохт гузаштан",paymentReady:"Саҳифаи пардохт омода аст",paid:"Pro фаъол шуд",return:"Бозгашт ба омӯзиш",
      error:"Маълумоти пардохт дастрас нашуд. Аз нав кӯшиш кунед.",exitTitle:"20% тахфифи махсус",
      exitText:"Барои пардохти аввал 20% тахфиф гиред",accept:"Гирифтани тахфиф",decline:"Не, ташаккур",
      renewal:"Пардохти навбатӣ бо нархи муқаррарӣ аст. Тамдиди худкорро бекор кардан мумкин.",
      comparison:"Нархи тахминӣ барои муқоиса, на нархи қаблӣ",
      saving:"20% тахфиф татбиқ шуд",normal:"Нарх бо тахфифи воқеӣ",
      manualNoExit:"Тахфифи 20% танҳо барои пардохти онлайн бо корт аст",
      blocked:"Пардохти ҷорӣ ё обунаи фаъолро санҷед",
      missingEmail:"Email-и дуруст ворид кунед",success:"Пардохт аз тарафи сервер тасдиқ шуд"}
  };
  var NAMES = { "1_month":"one", "3_months":"three", "6_months":"six", "12_months":"year" };
  var MONTHS = { "1_month":1, "3_months":3, "6_months":6, "12_months":12 };
  var order = ["1_month","3_months","6_months","12_months"];
  var root, sheet, scroll, body, actions, heading, info, panda, back, closeButton, lastFocus, state, tick = null, actorPromise = null, run = 0;
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
  function icon(path) {
    return "<svg viewBox=\"0 0 24 24\" width=\"22\" height=\"22\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\">"+path+"</svg>";
  }
  /* The course mascot (course-v3.html pandaChar: same head, ears, body,
     colors and motion) in a pose that belongs to each Pro moment. Local SVG,
     no network/font dependency, identical on course and practice pages. */
  function pandaSvg(pose) {
    var INK="#2B2620",MOUTH="#8E3A31",TONGUE="#E07B72",BLUSH="#F5B8C0",GOLD="#E9A916",FACE="#FFFDF7",CREAM="#FFF4DE",DEEP="#D4B27C";
    if (["celebrate","gift","read"].indexOf(pose)<0) pose="pro";
    var celebrate=pose==="celebrate", py=pose==="read"?36.2:34.8;
    function arm(d){return "<path d=\""+d+"\" fill=\"none\" stroke=\""+INK+"\" stroke-width=\"10\" stroke-linecap=\"round\"/>"}
    function paw(x,y,r){return "<ellipse cx=\""+x+"\" cy=\""+y+"\" rx=\"7\" ry=\"5.8\" fill=\""+INK+"\" transform=\"rotate("+r+" "+x+" "+y+")\"/>"}
    function star(x,y,s,delay){return "<path class=\"hip-pd-twinkle\" style=\"animation-delay:"+delay+"s\" transform=\"translate("+x+" "+y+") scale("+s+")\" d=\"M0 -5 L1.2 -1.2 L5 0 L1.2 1.2 L0 5 L-1.2 1.2 L-5 0 L-1.2 -1.2 Z\" fill=\""+GOLD+"\"/>"}
    var eyes=celebrate
      ? "<path d=\"M32 35 q6 -7 12 0\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\"/><path d=\"M56 35 q6 -7 12 0\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\"/>"
      : "<circle cx=\"38\" cy=\"34\" r=\"4.8\" fill=\"#fff\"/><circle cx=\"62\" cy=\"34\" r=\"4.8\" fill=\"#fff\"/>"
        +"<circle cx=\"38.6\" cy=\""+py+"\" r=\"2.7\" fill=\""+INK+"\"/><circle cx=\"61.4\" cy=\""+py+"\" r=\"2.7\" fill=\""+INK+"\"/>"
        +"<circle cx=\"39.8\" cy=\""+(py-1.6)+"\" r=\"1.1\" fill=\"#fff\"/><circle cx=\"62.6\" cy=\""+(py-1.6)+"\" r=\"1.1\" fill=\"#fff\"/>"
        +"<rect class=\"hip-pd-blink\" x=\"32\" y=\"28\" width=\"12\" height=\"12\" rx=\"5\" fill=\""+INK+"\"/><rect class=\"hip-pd-blink\" x=\"56\" y=\"28\" width=\"12\" height=\"12\" rx=\"5\" fill=\""+INK+"\"/>";
    var mouth=(celebrate||pose==="gift")
      ? "<path d=\"M41 52 q9 11 18 0 q-9 5 -18 0 z\" fill=\""+MOUTH+"\"/><path d=\"M45.5 56.5 q4.5 3.5 9 0 q-4.5 3 -9 0 z\" fill=\""+TONGUE+"\"/>"
      : "<path d=\"M43 53 q7 5 14 0\" stroke=\""+INK+"\" stroke-width=\"2.6\" fill=\"none\" stroke-linecap=\"round\"/>";
    var back="",front="";
    if (pose==="celebrate") {
      back="<path d=\"M30 62 q-15 -7 -17 -23 q6 -6 12 -2 q3 11 11 18 z\" fill=\""+INK+"\"/><path d=\"M70 62 q15 -7 17 -23 q-6 -6 -12 -2 q-3 11 -11 18 z\" fill=\""+INK+"\"/>";
      front=star(10,16,1,0)+star(92,12,.8,.3)+star(52,0,.68,.6);
    } else if (pose==="pro"||pose==="gift") {
      // Both paws present a card from its lower corners: a gold Pro card on
      // the limit screen, a red ticket only for the server-verified offer.
      var gift=pose==="gift";
      back=arm("M31 68 Q24 82 34 88")+arm("M69 68 Q76 82 66 88");
      front="<defs><linearGradient id=\"hipCard"+pose+"\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\">"
        +(gift?"<stop offset=\"0\" stop-color=\"#F0675C\"/><stop offset=\"1\" stop-color=\"#C93A31\"/>"
              :"<stop offset=\"0\" stop-color=\"#F8D376\"/><stop offset=\".55\" stop-color=\"#E9A916\"/><stop offset=\"1\" stop-color=\"#D18C0B\"/>")
        +"</linearGradient></defs>"
        +"<g transform=\"rotate(-4 50 79)\"><rect x=\"30\" y=\"66\" width=\"40\" height=\"24\" rx=\"5\" fill=\"url(#hipCard"+pose+")\" stroke=\""+(gift?"#A92E27":"#B9790A")+"\" stroke-width=\"1.2\"/>"
        +"<path d=\"M34 69.6 h32\" stroke=\""+(gift?"#FFC9C2":"#FFF1C4")+"\" stroke-width=\"1.2\" stroke-linecap=\"round\" opacity=\".8\"/>"
        +"<text x=\"50\" y=\"82\" text-anchor=\"middle\" font-size=\""+(gift?"10":"11")+"\" font-weight=\"900\" letter-spacing=\".4\" fill=\""+(gift?"#fff":"#4A3200")+"\" font-family=\"-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif\">"+(gift?"−20%":"PRO")+"</text></g>"
        +paw(34,89,10)+paw(66,88,-10)
        +star(11,22,.7,0)+star(90,18,.56,.45);
    } else if (pose==="read") {
      back=arm("M31 70 Q22 79 31 86")+arm("M69 70 Q78 79 69 86");
      front="<g transform=\"translate(50 82) scale(1.35)\"><path d=\"M-19 -10q10-5 19 1v25q-9-6-19-1Z\" fill=\"#FFF8E8\" stroke=\"#A8782B\" stroke-width=\"1.6\"/>"
        +"<path d=\"M19 -10q-10-5-19 1v25q9-6 19-1Z\" fill=\"#FFF8E8\" stroke=\"#A8782B\" stroke-width=\"1.6\"/><path d=\"M0 -9v25\" stroke=\"#D5A84C\" stroke-width=\"1.2\"/>"
        +"<path d=\"M-15 -4q6-2 11 1M-15 1q6-2 11 1M4 -3q6-3 11-1M4 2q6-3 11-1\" stroke=\"#D9C7A4\" stroke-width=\"1.1\" fill=\"none\" stroke-linecap=\"round\"/></g>"
        +paw(31,86,20)+paw(69,86,-20);
    }
    return "<svg class=\"hip-pd-char\" viewBox=\"-6 -8 112 116\" width=\"100%\" height=\"100%\" aria-hidden=\"true\" focusable=\"false\">"
      +"<ellipse class=\"hip-pd-ground\" cx=\"50\" cy=\"102\" rx=\"30\" ry=\"6\" fill=\"#211D17\" opacity=\".16\"/>"
      +"<g class=\"hip-pd-core "+(celebrate?"hip-pd-bounce":"hip-pd-breathe")+"\">"
      +back
      +"<ellipse cx=\"38\" cy=\"97\" rx=\"9.5\" ry=\"6.5\" fill=\""+INK+"\"/><ellipse cx=\"62\" cy=\"97\" rx=\"9.5\" ry=\"6.5\" fill=\""+INK+"\"/>"
      +"<path d=\"M31 96 q-7 -29 9 -40 h23 q17 10 10 40 q-20 10 -42 0 z\" fill=\""+DEEP+"\" opacity=\".34\"/>"
      +"<path d=\"M28 94 q-5 -28 9 -36 h26 q14 8 9 36 q-22 7 -44 0 z\" fill=\""+FACE+"\" stroke=\""+INK+"\" stroke-width=\"3\"/>"
      +"<path d=\"M61 61 q13 10 9 31 q-8 4 -18 5 q10 -13 9 -36 z\" fill=\"#B98442\" opacity=\".34\"/>"
      +"<ellipse cx=\"50\" cy=\"80\" rx=\"14\" ry=\"10.5\" fill=\""+CREAM+"\"/>"
      +"<circle cx=\"27\" cy=\"15\" r=\"12\" fill=\""+INK+"\"/><circle cx=\"73\" cy=\"15\" r=\"12\" fill=\""+INK+"\"/>"
      +"<circle cx=\"27\" cy=\"15\" r=\"5\" fill=\"#4A443C\"/><circle cx=\"73\" cy=\"15\" r=\"5\" fill=\"#4A443C\"/>"
      +"<circle cx=\"50\" cy=\"38\" r=\"30\" fill=\""+FACE+"\" stroke=\""+INK+"\" stroke-width=\"3\"/>"
      +"<path d=\"M61 12 q18 12 17 28 q-1 19 -20 27 q13 -17 3 -55 z\" fill=\""+DEEP+"\" opacity=\".34\"/>"
      +"<ellipse cx=\"40\" cy=\"24\" rx=\"13\" ry=\"8\" fill=\"#fff\" opacity=\".72\"/>"
      +"<ellipse cx=\"38\" cy=\"35\" rx=\"9\" ry=\"12\" fill=\""+INK+"\" transform=\"rotate(-12 38 35)\"/>"
      +"<ellipse cx=\"62\" cy=\"35\" rx=\"9\" ry=\"12\" fill=\""+INK+"\" transform=\"rotate(12 62 35)\"/>"
      +eyes
      +"<ellipse cx=\"50\" cy=\"51\" rx=\"11\" ry=\"8\" fill=\""+CREAM+"\" opacity=\".94\"/>"
      +"<path d=\"M46 46.5 q4 -3 8 0 q-2 4 -4 4 q-2 0 -4 -4 z\" fill=\""+INK+"\"/>"
      +"<path d=\"M50 50 v2.6\" stroke=\""+INK+"\" stroke-width=\"2\" stroke-linecap=\"round\"/>"
      +mouth
      +"<ellipse cx=\"29\" cy=\"46\" rx=\"4.8\" ry=\"3.2\" fill=\""+BLUSH+"\" opacity=\".85\"/><ellipse cx=\"71\" cy=\"46\" rx=\"4.8\" ry=\"3.2\" fill=\""+BLUSH+"\" opacity=\".85\"/>"
      +front
      +"</g></svg>";
  }
  function setPanda(pose) {
    panda.hidden=!pose;
    if (!pose || panda.dataset.pose===pose) return;
    panda.dataset.pose=pose;
    panda.innerHTML=pandaSvg(pose);
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
  function errorText(code) {
    if (code==="invalid_email") return txt("missingEmail");
    if (code==="subscription_active"||code==="payment_pending"||code==="chargeback_open") return txt("blocked");
    if (code==="plan_unavailable"||code==="lava_unavailable") return txt("unavailable");
    return txt("error");
  }
  function ensure() {
    if (root) return;
    root=el("section");root.id="hsk-inline-pro";root.hidden=true;
    root.setAttribute("role","dialog");root.setAttribute("aria-modal","true");
    sheet=el("div","hip-sheet");
    // The dialog itself takes focus on open, so no button shows a focus ring
    // to touch users; keyboard users tab to Back/Close as usual.
    sheet.tabIndex=-1;
    var header=el("div","hip-header");
    panda=el("div","hip-panda");panda.setAttribute("aria-hidden","true");
    heading=el("h2","hip-title");heading.id="hsk-inline-pro-title";
    info=el("p","hip-summary");
    header.append(panda,heading,info);
    body=el("div","hip-body");
    back=btn("","hip-back",goBack);back.innerHTML=icon("<path d=\"M15 5l-7 7 7 7\"/>");
    closeButton=btn("","hip-close",requestDismiss);closeButton.innerHTML=icon("<path d=\"M6 6l12 12M18 6L6 18\"/>");
    // Content scrolls; the actions stay at the bottom in the thumb zone.
    scroll=el("div","hip-scroll");scroll.append(header,body);
    actions=el("div","hip-actions");
    sheet.append(back,closeButton,scroll,actions);
    root.appendChild(sheet);
    root.setAttribute("aria-labelledby",heading.id);
    document.body.appendChild(root);
  }
  function lavaBlock() { return state.data && state.data.lava || null; }
  function manualAllowed() { var lava=lavaBlock(); return !lava || lava.mode!=="lava_only"; }
  function available() {
    var lava=lavaBlock();
    return lava && Array.isArray(lava.plans) ? lava.plans.filter(function(p) {
      return p && order.indexOf(p.plan_type)!==-1 && p.amount!==null && p.amount!==undefined;
    }).sort(function(a,b){return order.indexOf(a.plan_type)-order.indexOf(b.plan_type)}) : [];
  }
  function selectedPlan() {
    return available().find(function(p){return p.plan_type===state.plan}) || null;
  }
  function statusKind() {
    var d=state.data;
    if (!d) return "";
    if (d.access && d.access.is_paid) return "paid";
    if (d.pending_payment) return "pending";
    if (d.lava && d.lava.blocked_reason) return "blocked";
    return "";
  }
  function elementPlans(all) {
    var plans=available().filter(function(p){return all||p.plan_type==="1_month"||p.plan_type==="12_months"});
    var grid=el("div","hip-plans");
    plans.forEach(function(plan) {
      var card=btn("","hip-plan",function(){
        if (state.plan===plan.plan_type) return;
        state.plan=plan.plan_type;emit("pwa_pro_plan_selected",plan.plan_type,"lava");render();
      });
      card.setAttribute("aria-pressed",String(state.plan===plan.plan_type));
      var discounted=Number(plan.discount_percent)>0 && plan.base_amount!=null;
      var term=el("span","term",txt(NAMES[plan.plan_type]));
      if (discounted) term.appendChild(el("span","badge","−"+Number(plan.discount_percent)+"%"));
      card.appendChild(term);
      var priceLine=el("span","hip-price-line");
      priceLine.appendChild(el("span","price",money(plan.amount,plan.currency)));
      if (discounted) {
        priceLine.appendChild(el("span","comparison",Number(plan.base_amount).toFixed(2)));
      } else {
        var reference=relativePrice(plan.amount);
        if (reference) {
          var strike=el("span","comparison",reference);
          strike.title=txt("comparison");
          strike.setAttribute("aria-label",txt("comparison")+": "+money(reference,plan.currency));
          priceLine.appendChild(strike);
        }
      }
      card.appendChild(priceLine);
      // Per-month equivalent of the same server amount (display only).
      var months=Number(plan.months)||MONTHS[plan.plan_type]||1, amount=Number(plan.amount);
      if (months>1 && Number.isFinite(amount) && amount>0) {
        card.appendChild(el("span","per","≈ "+money(amount/months,plan.currency)+" "+txt("perMonth")));
      }
      grid.appendChild(card);
    });
    return grid;
  }
  function manualRow() {
    var row=btn("","hip-method",function(){
      emit("pwa_pro_method_selected",null,"manual");state.screen="manual";state.error="";render();
    });
    var text=el("span","hip-method-text");
    text.append(el("b",null,txt("manual")),el("small",null,txt("manualHint")));
    var chevron=el("span","hip-method-chevron");chevron.innerHTML=icon("<path d=\"M9 5l7 7-7 7\"/>");
    row.append(text,chevron);
    return row;
  }
  function payButton() {
    return btn(txt("pay"),"hip-primary",function() {
      if (!selectedPlan()) return;
      if (!state.email) {state.emailFrom=state.screen;state.screen="email";state.error="";render();return}
      startPayment();
    });
  }
  function header(pose,title,summary) {
    setPanda(pose);
    heading.textContent=title||"";
    info.textContent=summary||"";
    info.hidden=!summary;
  }
  function render() {
    if (!root||!state||root.hidden) return;
    var s=state.screen, plans=available();
    var status=(s==="main"||s==="more"||s==="email")?statusKind():"";
    var view=status?"status":s;
    root.dataset.screen=view;
    closeButton.setAttribute("aria-label",txt("close"));
    back.setAttribute("aria-label",txt("back"));
    back.hidden=["main","loading","exit","success","waiting","status"].indexOf(view)!==-1;
    body.replaceChildren();actions.replaceChildren();
    if (state.error && view!=="exit") body.appendChild(el("p","hip-error",state.error));
    if (view==="main"||view==="loading") {
      header("pro",txt("title"),txt("subtitle"));
      var benefits=el("ul","hip-benefits");
      (txt("benefits")||[]).forEach(function(value){
        benefits.appendChild(el("li","hip-benefit",value));
      });
      body.appendChild(benefits);
    }
    if (view==="loading") {
      var loadingPlans=el("div","hip-plans");
      loadingPlans.setAttribute("aria-hidden","true");
      for(var n=0;n<2;n++) loadingPlans.appendChild(el("div","hip-plan hip-skeleton"));
      body.appendChild(loadingPlans);
      var loadingCta=btn(txt("pay"),"hip-primary",function(){});
      loadingCta.disabled=true;
      actions.appendChild(loadingCta);
      // Reserve the secondary row so the primary button does not jump when
      // the real plans arrive.
      var placeholder=btn(txt("more"),"hip-secondary",function(){});
      placeholder.disabled=true;placeholder.style.visibility="hidden";placeholder.setAttribute("aria-hidden","true");
      actions.appendChild(placeholder);
      body.appendChild(el("div","hip-loading",txt("loading")));
      return;
    }
    if (view==="exit") {
      header("gift",txt("exitTitle"),txt("exitText"));
      actions.appendChild(btn(txt("accept"),"hip-primary",claimExit));
      actions.appendChild(btn(txt("decline"),"hip-secondary",function(){emit("pwa_pro_exit_declined");close()}));
      actions.appendChild(el("p","hip-small hip-center",txt("renewal")));
      return;
    }
    if (view==="success") {
      header("celebrate",txt("paid"),txt("success"));
      actions.appendChild(btn(txt("return"),"hip-primary",close));
      return;
    }
    if (view==="waiting") {
      var waitPlan=selectedPlan();
      header("read",txt("paymentReady"),waitPlan?txt(NAMES[waitPlan.plan_type])+" · "+money(waitPlan.amount,waitPlan.currency):"");
      if (state.paymentUrl) {
        // An actual user tap opens the real payment URL. Never create a
        // blank popup before the asynchronous invoice is ready on iOS.
        var link=el("a","hip-primary",txt("reopen"));
        link.href=state.paymentUrl;
        link.target="_blank";link.rel="noopener noreferrer";
        link.addEventListener("click",function(){
          if (!state||state.opened) return;
          state.opened=true;
          // Keep the same link for a re-tap; only add the honest status line.
          var line=actions.querySelector(".hip-checking");
          if (line) line.hidden=false;
        });
        actions.appendChild(link);
      }
      var checking=el("p","hip-checking",txt("paying"));
      checking.setAttribute("role","status");
      checking.hidden=!state.opened;
      actions.appendChild(checking);
      actions.appendChild(btn(txt("return"),"hip-secondary",close));
      return;
    }
    if (view==="status") {
      header(status==="paid"?"celebrate":"read",txt(status),"");
      actions.appendChild(btn(txt("return"),"hip-primary",close));
      if (status==="pending") {
        actions.appendChild(btn(txt("manual"),"hip-secondary",function(){emit("pwa_pro_method_selected",null,"manual");state.screen="manual";render()}));
      }
      return;
    }
    if (view==="manual") {
      header("","","");
      var iframe=el("iframe","hip-checkout");
      iframe.title=txt("manual");
      iframe.setAttribute("loading","eager");
      var q=new URLSearchParams({embedded:"1",source:state.source,lang:state.lang,mode:"subscription",return_to:"course",inline_manual:"1"});
      iframe.src="/iphone-pwa/checkout?"+q.toString();
      body.appendChild(iframe);
      return;
    }
    if (view==="email") {
      var p=selectedPlan();
      if (!p) {state.screen="main";return render()}
      header("",txt("email"),txt(NAMES[p.plan_type])+" · "+money(p.amount,p.currency));
      var input=el("input","hip-input");
      input.type="email";input.autocomplete="email";input.inputMode="email";
      input.placeholder="name@example.com";input.setAttribute("aria-label",txt("email"));
      input.value=state.email||"";
      input.addEventListener("input",function(){state.email=input.value});
      input.addEventListener("keydown",function(ev){if(ev.key==="Enter"){ev.preventDefault();startPayment()}});
      body.appendChild(input);
      body.appendChild(btn(txt("continue"),"hip-primary",startPayment));
      body.appendChild(el("p","hip-small hip-center",txt("renewal")));
      return;
    }
    if (view==="more") {
      // One screen: every sellable term plus the regular payment method.
      // No provider choice step and no provider names.
      header("",txt("more"),"");
      if (plans.length) {
        if (!selectedPlan()) state.plan=plans[0].plan_type;
        body.appendChild(elementPlans(true));
        if (state.mode==="exit_discount") body.appendChild(el("p","hip-small hip-center",txt("saving")));
        actions.appendChild(payButton());
      } else if (!manualAllowed()) {
        body.appendChild(el("p","hip-small hip-center",txt("unavailable")));
      }
      if (manualAllowed()) {
        if (plans.length) body.appendChild(el("div","hip-divider"));
        body.appendChild(manualRow());
        if (state.mode==="exit_discount") body.appendChild(el("p","hip-small",txt("manualNoExit")));
      }
      return;
    }
    // main
    if (!plans.length) {
      if (state.error || !manualAllowed()) {
        if (!state.error) body.appendChild(el("p","hip-small hip-center",txt("unavailable")));
        actions.appendChild(btn(txt("retry"),"hip-primary",load));
        if (manualAllowed()) actions.appendChild(btn(txt("manual"),"hip-secondary",function(){emit("pwa_pro_method_selected",null,"manual");state.screen="manual";state.error="";render()}));
        return;
      }
      // Card checkout is switched off: the regular method is the only path.
      actions.appendChild(btn(txt("pay"),"hip-primary",function(){emit("pwa_pro_method_selected",null,"manual");state.screen="manual";render()}));
      return;
    }
    if (!selectedPlan() || (state.plan!=="1_month" && state.plan!=="12_months")) {
      state.plan=plans.some(function(p){return p.plan_type==="1_month"})?"1_month":plans[0].plan_type;
    }
    body.appendChild(elementPlans(false));
    if (state.mode==="exit_discount") body.appendChild(el("p","hip-small hip-center",txt("saving")));
    actions.appendChild(payButton());
    actions.appendChild(btn(txt("more"),"hip-secondary",function(){emit("pwa_pro_more_opened");state.screen="more";state.error="";render()}));
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
    }).catch(function() {
      if (!state||current!==run) return;
      state.data={};state.screen="main";state.error=txt("error");render();
    });
  }
  function close() {
    if (!root||root.hidden) return;
    clearInterval(tick);tick=null;run++;root.hidden=true;body.replaceChildren();actions.replaceChildren();
    panda.dataset.pose="";panda.replaceChildren();
    document.documentElement.style.overflow=state&&state.previousOverflow||"";
    if (lastFocus&&lastFocus.isConnected) lastFocus.focus({preventScroll:true});
    var wasPaid=Boolean(state&&state.paid);
    if (state&&typeof state.onClose==="function") state.onClose({paid:wasPaid});
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
    // An invoice may be in flight or already open: never interrupt it with
    // a discount offer that would start a second checkout.
    if (state.mode==="exit_discount"||state.paying||state.checkoutId||
        state.screen==="success"||state.screen==="waiting"||state.screen==="manual") {emit("pwa_pro_dismissed");close();return}
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
    if (state.screen==="manual")state.screen=available().length?"more":"main";
    else if (state.screen==="email")state.screen=state.emailFrom==="more"?"more":"main";
    else if (state.screen==="more")state.screen="main";
    else {requestDismiss();return}
    state.error="";render();
  }
  function startPayment() {
    var plan=selectedPlan();
    if (!plan||!state||state.paying) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((state.email||"").trim())) {
      if (state.screen!=="email") state.emailFrom=state.screen;
      state.screen="email";state.error=txt("missingEmail");render();return;
    }
    // Do not pre-open about:blank: iOS standalone PWAs can strand the
    // blank window even after a valid payment URL is returned.
    var current=++run, from=state.screen==="email"?(state.emailFrom||"main"):state.screen;
    state.paying=true;state.screen="loading";state.error="";render();
    request(API.start,{plan_type:plan.plan_type,email:state.email.trim(),language:state.lang,
      mode:state.mode,attempt_id:state.attempt,ui_source:state.source}).then(function(data){
      if (!state||current!==run) return;
      state.paying=false;
      var url=new URL(data.payment_url);
      if (url.protocol!=="https:" || !(url.hostname==="lava.top"||url.hostname.endsWith(".lava.top")))
        throw Error("invalid_payment_url");
      state.checkoutId=data.checkout_id;state.paymentUrl=url.href;state.opened=false;
      state.screen="waiting";render();beginPolling();
    }).catch(function(err){
      if(!state||current!==run)return;
      state.paying=false;
      emit("pwa_pro_checkout_failed",plan.plan_type,"lava");
      state.error=errorText(err&&err.code);
      if (err&&err.code==="invalid_email") {state.emailFrom=from;state.screen="email";}
      else state.screen=from==="more"?"more":"main";
      render();
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
      data:null,error:"",polling:false,paying:false,opened:false,emailFrom:"main",onClose:opts.onClose,
      previousOverflow:document.documentElement.style.overflow};
    root.hidden=false;
    document.documentElement.style.overflow="hidden";
    root.setAttribute("aria-label","HSK AI Pro");
    sheet.focus({preventScroll:true});
    emit("pwa_pro_opened");load();
    return true;
  }
  function closeEmbeddedCheckout(child) {
    if (!state||state.screen!=="manual"||!body)return false;
    var iframe=body.querySelector("iframe");
    if (!iframe||iframe.contentWindow!==child)return false;
    state.screen=available().length?"more":"main";render();return true;
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
