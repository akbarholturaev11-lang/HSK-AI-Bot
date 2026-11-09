/* Post-registration iPhone Home Screen guide. Presentation only:
   verified account/Pro and onboarding continuation are owned by the caller. */
(function (global) {
  "use strict";
  var VIDEO = "/assets/onboarding/iphone-home-screen.mp4";
  var PWA_URL = "https://hskai.app/iphone-pwa";
  var openDialog = null;

  function standalone() {
    return !!((global.matchMedia && global.matchMedia("(display-mode: standalone)").matches)
      || global.navigator.standalone === true);
  }
  function ios() {
    var agent = global.navigator.userAgent || "";
    return /iPad|iPhone|iPod/i.test(agent)
      || (global.navigator.platform === "MacIntel" && global.navigator.maxTouchPoints > 1);
  }
  function safari() {
    var agent = global.navigator.userAgent || "";
    var webApp = global.Telegram && global.Telegram.WebApp;
    // iOS Chrome/Firefox/embedded browsers also contain "Safari" in their UA.
    // Be conservative: ambiguous browsers receive a copyable Safari URL.
    return ios() && /Version\/[\d.]+.*Safari\//i.test(agent)
      && !/(CriOS|FxiOS|EdgiOS|OPiOS|DuckDuckGo|GSA\/|YaBrowser|Instagram|FBAN|FBAV|FB_IAB|Telegram|Line\/|TikTok|MicroMessenger|KAKAOTALK)/i.test(agent)
      && !(webApp && webApp.initData);
  }
  function eligible() {
    return global.location.pathname.startsWith("/iphone-pwa/")
      && ios() && !standalone();
  }
  function label(lang, key) {
    var all = global.HSKAI_LI_I18N || {};
    var locale = all[lang] || all.ru || {};
    return locale[key] || (all.ru && all.ru[key]) || "";
  }
  function seenKey(userId) {
    if (!Number.isSafeInteger(userId) || userId <= 0) return null;
    return "hskai_li_install_guide_v1:" + userId;
  }
  function storageHas(key) {
    if (!key) return true;
    try { if (global.localStorage.getItem(key) === "seen") return true; } catch (_) {}
    try { return global.sessionStorage.getItem(key) === "seen"; } catch (_) { return false; }
  }
  function markSeen(key) {
    if (!key) return;
    try { global.localStorage.setItem(key, "seen"); } catch (_) {}
    try { global.sessionStorage.setItem(key, "seen"); } catch (_) {}
  }
  function element(tag, css, text) {
    var node = document.createElement(tag);
    if (css) node.className = css;
    if (typeof text === "string") node.textContent = text;
    return node;
  }
  function open(opts, done) {
    opts = opts || {};
    var key = seenKey(opts.userId);
    if (!eligible() || !key || storageHas(key) || openDialog || typeof done !== "function") return false;
    var lang = ["uz", "ru", "tj"].includes(opts.lang) ? opts.lang : "ru";
    var overlay = element("div", "li-install-overlay");
    overlay.setAttribute("role", "presentation");
    var card = element("section", "li-install-card");
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-modal", "true");
    var close = element("button", "li-install-close", "×");
    close.type = "button";
    close.setAttribute("aria-label", label(lang, "install.close"));
    card.appendChild(close);

    var movie = null;
    var handoffLink = null;
    if (safari()) {
      var title = element("h2", "li-install-title", label(lang, "install.title"));
      title.id = "li-install-title";
      card.setAttribute("aria-labelledby", title.id);
      card.appendChild(title);
      var videoArea = element("div", "li-install-media is-fallback");
      movie = element("video", "li-install-video");
      movie.controls = true;
      movie.playsInline = true;
      movie.preload = "metadata";
      movie.setAttribute("playsinline", "");
      movie.setAttribute("webkit-playsinline", "");
      movie.setAttribute("aria-label", label(lang, "install.videoLabel"));
      movie.hidden = true;
      movie.src = VIDEO;
      // Show four steps immediately if media is slow, missing or offline.
      // When metadata is valid, show only the video (never duplicate steps).
      var fallback = element("div", "li-install-video-fallback");
      fallback.setAttribute("aria-label", label(lang, "install.videoFallback"));
      var steps = element("ol", "li-install-steps");
      ["install.step1", "install.step2", "install.step3", "install.step4"].forEach(function (name) {
        steps.appendChild(element("li", "", label(lang, name)));
      });
      fallback.appendChild(steps);
      movie.addEventListener("loadedmetadata", function () {
        movie.hidden = false;
        fallback.hidden = true;
        videoArea.classList.remove("is-fallback");
      }, { once: true });
      movie.addEventListener("error", function () {
        movie.hidden = true;
        fallback.hidden = false;
        videoArea.classList.add("is-fallback");
      });
      videoArea.append(movie, fallback);
      card.appendChild(videoArea);
    } else {
      // iOS browsers cannot reliably force a switch to Safari.
      // Never include account credentials, referrals or callback tokens.
      var panda = element("div", "li-install-panda");
      panda.setAttribute("aria-hidden", "true");
      var render = global.HSKCharacters && global.HSKCharacters.render;
      var art = typeof render === "function" ? render("panda", "talk") : "";
      if (typeof art === "string" && art) panda.innerHTML = art;
      else panda.textContent = "🐼";
      var hint = element("p", "li-install-browser-hint");
      hint.id = "li-install-description";
      hint.appendChild(document.createTextNode(label(lang, "install.safariHint") + " "));
      handoffLink = element("a", "li-install-browser-link", "hskai.app/iphone-pwa");
      handoffLink.href = PWA_URL;
      hint.appendChild(handoffLink);
      card.setAttribute("aria-labelledby", hint.id);
      card.append(panda, hint);
    }

    var oldFocus = document.activeElement;
    var oldOverflow = document.body.style.overflow;
    var finished = false;
    function finish() {
      if (finished) return;
      finished = true;
      markSeen(key);
      if (movie) {
        movie.pause();
        movie.removeAttribute("src");
        try { movie.load(); } catch (_) {}
      }
      document.removeEventListener("keydown", keydown);
      document.body.style.overflow = oldOverflow;
      overlay.remove();
      openDialog = null;
      if (oldFocus && oldFocus.isConnected && oldFocus.focus) oldFocus.focus();
      done();
    }
    function keydown(event) {
      if (event.key === "Escape") { event.preventDefault(); finish(); return; }
      if (event.key === "Tab") {
        var focusable = [close, movie, handoffLink].filter(function (node) {
          return node && !node.hidden && node.getClientRects().length;
        });
        if (!focusable.length) return;
        if (event.shiftKey && document.activeElement === focusable[0]) {
          event.preventDefault(); focusable[focusable.length - 1].focus();
        } else if (!event.shiftKey && document.activeElement === focusable[focusable.length - 1]) {
          event.preventDefault(); focusable[0].focus();
        }
      }
    }
    close.addEventListener("click", finish);
    overlay.appendChild(card);
    document.body.appendChild(overlay);
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", keydown);
    openDialog = overlay;
    close.focus();
    if (movie) {
      try { movie.load(); } catch (_) { movie.hidden = true; }
    }
    return true;
  }
  global.HSKAILiInstallGuide = { open: open, eligible: eligible, standalone: standalone, safari: safari };
})(window);
