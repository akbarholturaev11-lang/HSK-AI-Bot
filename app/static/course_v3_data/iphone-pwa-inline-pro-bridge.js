/* Runtime PWA-only glue: shared Mini App/checkout HTML remains byte-identical. */
(function () {
  "use strict";
  if (!location.pathname.startsWith("/iphone-pwa/")) return;
  var inline = window.HSKPwaInlinePro;
  var path = location.pathname;

  function language() {
    var lang = "ru";
    try { if (typeof LANG === "string" && LANG) lang = LANG; } catch (_) {}
    if (lang === "ru") {
      var q = new URLSearchParams(location.search);
      lang = q.get("lang") || document.documentElement.lang || lang;
    }
    if (lang === "tg") lang = "tj";
    return ["ru", "uz", "tj"].includes(lang) ? lang : "ru";
  }
  function practiceExit(source, paid) {
    if (paid) return; // The inline modal refreshes the server gate on payment.
    if (path === "/iphone-pwa/course") {
      try {
        var exits = {
          v3_recognition_limit:window.RECOG&&RECOG.close,
          v3_pronunciation_limit:window.PRON&&PRON.close,
          v3_mistake_review:window.MIST&&MIST.close,
          v3_test_limit:window.TEST&&(TEST.showHub||TEST.close),
          v3_voice_limit:window.VOICE&&VOICE.endCall
        };
        if (typeof exits[source] === "function") {exits[source]();return}
      } catch (_) {}
      return;
    }
    if (typeof window.goBack === "function") {
      try {window.goBack();return} catch (_) {}
    }
    location.assign("/iphone-pwa/course?lang="+encodeURIComponent(language()));
  }
  function offer(source, exitToCourse) {
    if (!inline) return false;
    return inline.open({
      source:source,lang:language(),
      onClose:exitToCourse?function(result){practiceExit(source,Boolean(result&&result.paid))}:undefined
    });
  }
  function wrapFunction(name, source) {
    var original = window[name];
    if (typeof original !== "function") return;
    window[name] = function () {
      // On PWA the original showLimitNow mutates the page into a second
      // locked screen. The single fullscreen Pro surface replaces it.
      if (inline) {
        try {window.HskPwaPracticeBoot?.hide?.()}catch(_){}
        try {window.PracticeCoach?.hide?.();window.PracticeCoach?.reset?.()}catch(_){}
        if (offer(source,true)) return;
      }
      return original.apply(this, arguments);
    };
  }

  // Manual checkout inside the PWA Pro surface: fill the screen edge to edge
  // (the parent hides its own Back/X), keep the bottom button on the bottom
  // edge, and turn the header back chevron into the single X that leaves it.
  function embedInProSurface() {
    var doc = document.documentElement, area = {top: 0, bottom: 0};
    try { area = window.parent.HSKPwaInlinePro.safeArea() || area; } catch (_) {}
    doc.classList.add("hsk-inline-embed");
    doc.style.setProperty("--hip-embed-t", Math.max(0, Number(area.top) || 0) + "px");
    doc.style.setProperty("--hip-embed-b", Math.max(0, Number(area.bottom) || 0) + "px");
    var style = document.createElement("style");
    style.textContent =
      "html.hsk-inline-embed .app{padding-top:calc(16px + var(--hip-embed-t));padding-bottom:calc(96px + var(--hip-embed-b))}" +
      "html.hsk-inline-embed .bottom{padding-bottom:calc(11px + var(--hip-embed-b))}" +
      "html.hsk-inline-embed .qr-preview{padding-top:calc(18px + var(--hip-embed-t));padding-bottom:calc(88px + var(--hip-embed-b))}" +
      "html.hsk-inline-embed .qr-preview-bottom{padding-bottom:calc(11px + var(--hip-embed-b))}" +
      "html.hsk-inline-embed .sheet-panel{padding-bottom:calc(17px + var(--hip-embed-b))}" +
      "html.hsk-inline-embed .toast{bottom:calc(88px + var(--hip-embed-b))}";
    document.head.appendChild(style);
    var chevron = document.getElementById("pwaCheckoutBackBtn");
    if (!chevron) return;
    var closeLabels = {uz: "Yopish", ru: "Закрыть", tj: "Пӯшидан"};
    var x = chevron.cloneNode(false); // drops the step-back listener
    x.innerHTML = '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>';
    x.addEventListener("click", function () {
      try {
        if (typeof state !== "undefined") {
          if (state.paymentSubmitting) return;
          // An open sheet/preview closes first, exactly like before.
          if ((state.qrPreviewOpen || state.supportOpen || state.inviteOpen || state.renewalOpen) &&
              typeof window.hskPwaCheckoutBack === "function") { window.hskPwaCheckoutBack(); return; }
        }
      } catch (_) {}
      if (typeof window.returnToCourseFromCheckout === "function") window.returnToCourseFromCheckout();
    });
    chevron.replaceWith(x);
    function label() {
      var lang = "ru";
      try { if (typeof state !== "undefined" && state.lang) lang = state.lang; } catch (_) {}
      x.setAttribute("aria-label", closeLabels[lang] || closeLabels.ru);
    }
    var baseRender = window.render;
    if (typeof baseRender === "function") {
      window.render = function () { var result = baseRender.apply(this, arguments); label(); return result; };
    }
    label();
  }

  if (path === "/iphone-pwa/course") {
    var app = window.App;
    if (!app || typeof app.openPaywall !== "function") return;
    var trialReadOwner=null,trialReadAt=0,trialEpoch=0,trialIntentPending=false;
    var trialOffer=null,installedShown={},trialStatusEdge=null;
    // Do not dynamically mutate apple-mobile-web-app-status-bar-style:
    // installed iOS can freeze it at launch, and switching translucent modes
    // can change viewport geometry. A real fixed strip can be sampled by newer
    // WebKit status-bar chrome and also paints the existing viewport safe inset.
    // This node neither participates in flex layout nor intercepts touches.
    function trialStatusBar(active){
      if(active){
        var layer=document.getElementById("pwa-checkout-layer");
        if(!layer||!layer.classList.contains("pwa-checkout-trial")||trialStatusEdge)return;
        var edge=document.createElement("div");
        edge.className="pwa-trial-status-edge";
        edge.setAttribute("aria-hidden","true");
        edge.style.cssText="position:fixed;top:0;left:0;right:0;height:max(16px,var(--safe-t,0px));background:#211D17;pointer-events:none;z-index:1";
        layer.appendChild(edge);trialStatusEdge=edge;
      }else if(trialStatusEdge){
        trialStatusEdge.remove();trialStatusEdge=null;
      }
    }
    function standalone(){return !!(navigator.standalone===true||window.matchMedia&&matchMedia("(display-mode: standalone)").matches)}
    function installedKey(owner){return "hskai.pwa.trial.presented.v1:"+owner}
    function wasPresented(owner){try{return installedShown[owner]||localStorage.getItem(installedKey(owner))==="1"}catch(_){return !!installedShown[owner]}}
    function sameOwner(owner,map){return window.PWA_COURSE_USER_ID===owner&&window.MAP===map}
    function getTrial(force){
      var owner=window.PWA_COURSE_USER_ID,map=window.MAP;
      if(!owner||!map||typeof window._apiGet!=="function")return Promise.resolve(null);
      if(TRIAL_PROMISE&&trialReadOwner===owner)return TRIAL_PROMISE;
      if(!force&&TRIAL_LOADED&&trialReadOwner===owner&&Date.now()-trialReadAt<30000)return Promise.resolve(TRIAL_STATE);
      var epoch=++trialEpoch,controller=new AbortController();
      trialReadOwner=owner;
      var request=boundedSectionRequest(_apiGet("/api/v3/trial/status",{signal:controller.signal}).then(function(response){
        if(!response.ok)throw Error("trial_status_http");return response.json();
      }),controller).then(function(result){
        if(epoch!==trialEpoch||!sameOwner(owner,map))return null;
        if(!result||result.ok!==true||!result.trial||typeof result.trial.eligible!=="boolean")throw Error("trial_status_invalid");
        TRIAL_STATE=result.trial;TRIAL_LOADED=true;trialReadAt=Date.now();return TRIAL_STATE;
      }).catch(function(){
        if(epoch===trialEpoch&&sameOwner(owner,map)){TRIAL_STATE=null;TRIAL_LOADED=false;}
        return null;
      }).finally(function(){if(TRIAL_PROMISE===request)TRIAL_PROMISE=null});
      TRIAL_PROMISE=request;return request;
    }
    function offerChild(child){
      return trialOffer&&sameOwner(trialOffer.owner,trialOffer.map)&&
        window.PWA_CHECKOUT_FRAME&&PWA_CHECKOUT_FRAME.contentWindow===child;
    }
    function showTrial(source,entry,done){
      if(trialOffer||window.PWA_CHECKOUT_FRAME)return false;
      var query=typeof window.courseCheckoutReturnParams==="function"?courseCheckoutReturnParams():new URLSearchParams();
      query.set("offer","trial");query.set("lang",language());
      trialOffer={source:source||"profile_subscription",entry:entry||"profile",owner:PWA_COURSE_USER_ID,map:MAP,done:done};
      app.openPwaCheckout(query);
      // WebKit pointer activation need not focus its button. Restore the
      // existing Profile Pro control rather than the document body on exit.
      if(SCREEN==="profile"&&window.PWA_CHECKOUT_RETURN_FOCUS===document.body){
        var trigger=document.querySelector('.hp-promo-slide[data-promo-kind="pro"] .hp-promo-action');
        if(trigger)window.PWA_CHECKOUT_RETURN_FOCUS=trigger;
      }
      if(!window.PWA_CHECKOUT_FRAME){trialOffer=null;return false;}
      trialStatusBar(true);
      return true;
    }
    function closeTrial(child,activated){
      if(!offerChild(child))return false;
      var current=trialOffer;trialOffer=null;
      function resume(updated){
        if(activated===true&&updated!==true)return;
        if(PWA_COURSE_USER_ID===current.owner&&window.MAP&&MAP.level===current.map.level&&
           SCREEN==="course"&&!NavBack.top()&&!NavBack.blocked()&&typeof current.done==="function")current.done();
      }
      if(activated===true){TRIAL_STATE=null;TRIAL_LOADED=false;trialReadAt=0;}
      // Use the layer's existing access refresh; a second progress read can
      // race its map replacement and lose the deferred foundation intent.
      if(!app.closePwaCheckout(child,function(updated){
        if(activated===true)resume(updated);
        // Refresh can remount Profile after its original trigger was focused.
        if(updated&&PWA_COURSE_USER_ID===current.owner&&SCREEN==="profile"&&
           !window.PWA_CHECKOUT_FRAME&&!NavBack.top()&&!NavBack.blocked()&&document.activeElement===document.body){
          var trigger=document.querySelector('.hp-promo-slide[data-promo-kind="pro"] .hp-promo-action');
          if(trigger)trigger.focus({preventScroll:true});
        }
      }))return false;
      trialStatusBar(false);
      if(activated!==true)resume();
      return true;
    }
    // Back/Escape can dismiss the parent iframe before Li's child runtime has
    // loaded and registered hskPwaCheckoutBack. In that case the host falls
    // back to App.closePwaCheckout directly. Route that same-origin, owned
    // fallback through the normal trial cleanup so no stale trialOffer, dark
    // top-edge overlay or deferred course continuation is left behind.
    var closeCheckoutUnwrapped=app.closePwaCheckout;
    app.closePwaCheckout=function(child,afterRefresh){
      if(trialOffer&&window.PWA_CHECKOUT_FRAME&&PWA_CHECKOUT_FRAME.contentWindow===child){
        if(offerChild(child))return closeTrial(child,false);
        // Map/actor changed while the child was loading: close without
        // resuming the old actor's lesson intent.
        var closed=closeCheckoutUnwrapped.apply(this,arguments);
        if(closed){trialOffer=null;trialStatusBar(false)}
        return closed;
      }
      return closeCheckoutUnwrapped.apply(this,arguments);
    };
    function trialError(){if(typeof window.toast==="function")toast(courseMessage("trialFail",T().trialFail),2200)}
    function viewIntent(){return {screen:SCREEN,layer:NavBack.top(),blocked:NavBack.blocked()}}
    function sameIntent(intent){return SCREEN===intent.screen&&NavBack.top()===intent.layer&&NavBack.blocked()===intent.blocked}
    function beforePurchase(source,fallback){
      if(trialIntentPending||CHECKOUT_NAVIGATING||trialOffer)return Promise.resolve(false);
      var owner=PWA_COURSE_USER_ID,map=MAP,control=document.activeElement,intent=viewIntent();
      if(["PRO_ACTIVE","TRIAL_ACTIVE","TEMP_ACCESS","BLOCKED"].indexOf(map.user&&map.user.state)>=0){fallback();return Promise.resolve(true);}
      trialIntentPending=true;
      if(control&&control.tagName==="BUTTON")control.setAttribute("aria-busy","true");
      return getTrial(true).then(function(state){
        if(!sameOwner(owner,map)||!sameIntent(intent))return false;
        if(!state){trialError();return false;}
        if(state.eligible)return showTrial(source,"purchase");
        fallback();return true;
      }).finally(function(){trialIntentPending=false;if(control&&control.isConnected)control.removeAttribute("aria-busy")});
    }
    function afterBoot(next){
      var owner=window.PWA_COURSE_USER_ID,map=window.MAP,q=new URLSearchParams(location.search);
      if(!standalone()||!owner||!map||wasPresented(owner)||document.hidden||
         ["PRO_ACTIVE","TRIAL_ACTIVE","TEMP_ACCESS","BLOCKED"].indexOf(map.user&&map.user.state)>=0||
         q.has("pro_checkout")||q.has("pro_return")||q.has("lesson")||q.has("resume")||q.has("autostart")||q.has("challenge_id")||q.has("tour")||
         (q.get("tab")&&q.get("tab")!=="course")||SCREEN!=="course"||NavBack.top()||NavBack.blocked()){
        next();return;
      }
      getTrial(true).then(function(state){
        if(!sameOwner(owner,map))return;
        // A new learner interaction takes over from startup. In particular,
        // never launch the deferred foundation beneath a newly opened section.
        // Lesson entry retains its existing required-foundation gate.
        if(trialIntentPending||SCREEN!=="course"||NavBack.top()||NavBack.blocked()||document.hidden)return;
        if(!state||!state.eligible||!showTrial("installed_pwa","installed",next))next();
      });
    }
    window.HskPwaTrialOffer={
      get:getTrial,afterBoot:afterBoot,
      acceptActor:function(child,owner){
        if(!offerChild(child))return false;
        if(Number(owner)!==trialOffer.owner){location.replace("/iphone-pwa");return false;}
        return true;
      },
      open:function(source){
        if(trialIntentPending||trialOffer)return Promise.resolve(false);
        var owner=PWA_COURSE_USER_ID,map=MAP,intent=viewIntent();trialIntentPending=true;
        return getTrial(false).then(function(state){
          if(!sameOwner(owner,map)||!sameIntent(intent))return false;
          if(!state){trialError();return false;}
          if(!state.eligible){if(SCREEN==="profile")renderProfile();return false;}
          return showTrial(source,"profile");
        }).finally(function(){trialIntentPending=false});
      },
      presented:function(child,owner){
        if(!this.acceptActor(child,owner))return false;
        if(standalone()){
          installedShown[trialOffer.owner]=true;
          try{localStorage.setItem(installedKey(trialOffer.owner),"1")}catch(_){}
        }
        return true;
      },
      close:closeTrial,
      purchase:function(child){
        if(!offerChild(child))return false;
        var source=trialOffer.source;
        // An explicit paid choice continues the existing checkout, without a
        // second trial prompt. X/Back simply returns to the prior screen.
        trialOffer.done=null;
        if(!closeTrial(child,false))return false;
        originalGoPay.call(app,source);return true;
      }
    };
    var legacy = app.openPaywall;
    app.openPaywall = function (ctx) {
      var limit = ctx === "lockedLesson" || ctx === "pronLimit" ||
        !!(ctx && typeof ctx === "object" && ctx.lesson);
      if (limit && inline) {
        var source = ctx === "pronLimit" ? "v3_pronunciation_limit" : "v3_locked_lesson";
        try { if (window.SCREEN && document.querySelector("#sheet.on")) app.closeSheet(); } catch (_) {}
        // Preserve server-owned limit source, rather than a synthetic profile purchase.
        if (offer(source)) return;
      }
      return legacy.apply(this, arguments);
    };
    // Internal practice modules use App.goPay directly; intercept only
    // server-confirmed limit sources, never profile/onboarding purchases.
    var originalGoPay = app.goPay;
    if (typeof originalGoPay === "function") {
      app.goPay = function(src) {
        var limitSources = {
          v3_recognition_limit:1,v3_memorize_limit:1,v3_pronunciation_limit:1,
          v3_mistake_review:1,v3_test_limit:1,v3_voice_limit:1,
          v3_locked_lesson:1,v3_qa_limit:1
        };
        if (limitSources[src] && offer(src)) return;
        var self=this,args=arguments;
        if(window.MAP&&window.PWA_COURSE_USER_ID)
          return beforePurchase(src||window.PAY_SOURCE,function(){originalGoPay.apply(self,args)});
        return originalGoPay.apply(this,arguments);
      };
    }
    // Older course module limits are rendered by private showLimit()
    // closures instead of App.openPaywall. Detect only the explicit legacy
    // lock CTA and replace it before paint; avoid overlaying two paywalls.
    var observerTarget=document.getElementById("secov")||document.body;
    var legacyObserver=new MutationObserver(function(){
      var shown=document.getElementById("hsk-inline-pro");
      if (shown&&!shown.hidden)return;
      var source=null;
      if(document.querySelector("#rc-body .rc-done .rc-prem"))source="v3_recognition_limit";
      else if(document.querySelector("#pr-done.on .pr-prem"))source="v3_pronunciation_limit";
      else if(document.querySelector("#mk-limit:not([hidden])"))source="v3_mistake_review";
      else if(document.querySelector('#tc-empty.on button[onclick*="TEST.premium"]'))source="v3_test_limit";
      else if(document.querySelector("#paywall.on #pwb"))source="v3_voice_limit";
      if (!source) return;
      try {
        if(source==="v3_recognition_limit"){
          var node=document.querySelector("#rc-body .rc-done");
          if(node)node.remove();
        }
        if(source==="v3_pronunciation_limit")document.getElementById("pr-done")?.classList.remove("on");
        if(source==="v3_mistake_review")document.getElementById("mk-limit").hidden=true;
        if(source==="v3_test_limit")document.getElementById("tc-empty")?.classList.remove("on");
        if(source==="v3_voice_limit")document.getElementById("paywall")?.classList.remove("on");
      }catch(_){}
      offer(source,true);
    });
    legacyObserver.observe(observerTarget,{subtree:true,childList:true,attributes:true,attributeFilter:["class","hidden"]});
    return;
  }

  if (path === "/iphone-pwa/practice/voice") {
    wrapFunction("showPaywall", "v3_voice_limit");
    wrapFunction("goPremium", "v3_voice_limit");
    return;
  }

  var sources = {
    "/iphone-pwa/practice/recognition":"v3_recognition_limit",
    "/iphone-pwa/practice/memorize":"v3_memorize_limit",
    "/iphone-pwa/practice/pronunciation":"v3_pronunciation_limit",
    "/iphone-pwa/practice/test":"v3_test_limit",
    "/iphone-pwa/practice/mistakes":"v3_mistake_review"
  };
  if (sources[path]) {
    wrapFunction("showLimitNow", sources[path]);
    wrapFunction(path.endsWith("/mistakes") ? "goPay" : "goPremium", sources[path]);
    return;
  }

  if (path === "/iphone-pwa/checkout") {
    // Nested manual receipt flow: parent inline sheet owns the return action.
    var originalReturn = window.returnToCourseFromCheckout;
    if (typeof originalReturn === "function") {
      window.returnToCourseFromCheckout = function () {
        try {
          if (window.parent !== window && window.parent.HSKPwaInlinePro &&
              window.parent.HSKPwaInlinePro.closeEmbeddedCheckout(window)) return;
        } catch (_) {}
        return originalReturn.apply(this, arguments);
      };
    }
    if (new URLSearchParams(location.search).get("inline_manual") === "1") {
      // The canonical checkout has a shared first-step Lava card question
      // whenever both methods are configured. The parent Pro sheet ALREADY
      // chose manual, so strip exactly that question on this PWA iframe.
      try { if (typeof state !== "undefined") state.path = "manual"; } catch (_) {}
      var originalFlow=window.flow;
      if(typeof originalFlow==="function"){
        window.flow=function(){
          var steps=originalFlow.apply(this,arguments);
          if (typeof state !== "undefined" && state.path==="manual")
            return steps.filter(function(step){return step!=="card"});
          return steps;
        };
      }
      embedInProSurface();
      // The source checkout renders once before this PWA-only bridge is
      // injected. Immediately re-render using the selected manual path
      // so the intermediate Visa question cannot flash during loading.
      try { if (typeof window.render==="function") window.render() } catch (_) {}
    }
    // Actual manual discount supersedes the comparison. This is display only.
    var renderPlans = window.renderPlans;
    if (typeof renderPlans === "function") {
      window.renderPlans = function () {
        var result = renderPlans.apply(this, arguments);
        try {
          if (typeof state === "undefined") return result;
          document.querySelectorAll("#plans button.plan").forEach(function (card) {
            if (card.classList.contains("discounted")) return;
            var plan = card.getAttribute("data-plan");
            var p = typeof planPrice === "function" ? planPrice(plan) : null;
            var price = p && Number(p.final);
            if (!Number.isFinite(price) || price <= 0) return;
            var fake = Math.round(price * 1.3 - 0.99) + 0.99;
            if (fake <= price) fake = Math.ceil(price - 0.99 + 1e-9) + 0.99;
            var old = card.querySelector(".old-price");
            if (!old) return;
            old.textContent = fake.toFixed(2) + " " + (p.currency || "");
            old.title = "Visual comparison only; not a previous sales price";
            card.classList.add("pwa-reference-price");
          });
        } catch (_) {}
        return result;
      };
    }
  }
})();
