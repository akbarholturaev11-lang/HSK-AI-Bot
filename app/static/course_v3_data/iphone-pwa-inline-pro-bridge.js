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

  if (path === "/iphone-pwa/course") {
    var app = window.App;
    if (!app || typeof app.openPaywall !== "function") return;
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
