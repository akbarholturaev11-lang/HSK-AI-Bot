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
  function offer(source) {
    if (!inline) return false;
    return inline.open({source:source,lang:language()});
  }
  function wrapFunction(name, source, before) {
    var original = window[name];
    if (typeof original !== "function") return;
    window[name] = function () {
      if (before) {
        var result = original.apply(this, arguments);
        offer(source);
        return result;
      }
      if (offer(source)) return;
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
    return;
  }

  if (path === "/iphone-pwa/practice/voice") {
    wrapFunction("showPaywall", "v3_voice_limit", false);
    wrapFunction("goPremium", "v3_voice_limit", false);
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
    wrapFunction("showLimitNow", sources[path], true);
    wrapFunction(path.endsWith("/mistakes") ? "goPay" : "goPremium", sources[path], false);
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
      // Loaded immediately after the original script's async overview request.
      // applyOverview keeps "manual" on mode=both and the canonical receipt UI.
      try { if (typeof state !== "undefined") state.path = "manual"; } catch (_) {}
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
