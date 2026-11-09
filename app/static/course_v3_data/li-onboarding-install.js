/* Verified iPhone PWA installation guide: compact hero -> video.
   UI only; owner/entitlements/progress are server-authoritative elsewhere. */
(function (global) {
  "use strict";
  var VIDEO = "/assets/onboarding/iphone-home-screen.mp4?v=20261109-3e099a0c0489";
  var HERO = "/assets/onboarding/iphone-install-home-focus.jpg?v=20261110-17848fda4d9c";
  var PWA_URL = "https://hskai.app/iphone-pwa";
  var openDialog = null, preloadedVideo = null;

  function standalone() {
    return !!((global.matchMedia && global.matchMedia("(display-mode: standalone)").matches)
      || global.navigator.standalone === true);
  }
  function ios() {
    var a = global.navigator.userAgent || "";
    return /iPad|iPhone|iPod/i.test(a)
      || (global.navigator.platform === "MacIntel" && global.navigator.maxTouchPoints > 1);
  }
  function safari() {
    var a = global.navigator.userAgent || "";
    var webApp = global.Telegram && global.Telegram.WebApp;
    return ios() && /Version\/[\d.]+.*Safari\//i.test(a)
      && !/(CriOS|FxiOS|EdgiOS|OPiOS|DuckDuckGo|GSA\/|YaBrowser|Instagram|FBAN|FBAV|FB_IAB|Telegram|Line\/|TikTok|MicroMessenger|KAKAOTALK)/i.test(a)
      && !(webApp && webApp.initData);
  }
  function eligible() {
    return global.location.pathname.startsWith("/iphone-pwa/") && ios() && !standalone();
  }
  function label(lang, key) {
    var all = global.HSKAI_LI_I18N || {};
    var locale = all[lang] || all.ru || {};
    return locale[key] || (all.ru && all.ru[key]) || "";
  }
  function seenKey(userId) {
    return Number.isSafeInteger(userId) && userId > 0
      ? "hskai_li_install_guide_v1:" + userId : null;
  }
  function storageHas(key) {
    if (!key) return true;
    try { if (global.localStorage.getItem(key) === "seen") return true; } catch (_) {}
    try { return global.sessionStorage.getItem(key) === "seen"; } catch (_) { return false; }
  }
  function markSeen(key) {
    try { global.localStorage.setItem(key, "seen"); } catch (_) {}
    try { global.sessionStorage.setItem(key, "seen"); } catch (_) {}
  }
  function element(tag, css, text) {
    var node = document.createElement(tag);
    if (css) node.className = css;
    if (typeof text === "string") node.textContent = text;
    return node;
  }
  function preload() {
    // Called only after verified PWA sign-in; the browser may still limit
    // prefetching. This never autoplays or starts an account-related request.
    if (!eligible() || !safari() || preloadedVideo) return;
    var movie = document.createElement("video");
    movie.src = VIDEO;
    movie.controls = true;
    movie.preload = "auto";
    movie.playsInline = true;
    movie.setAttribute("playsinline", "");
    movie.setAttribute("webkit-playsinline", "");
    movie.hidden = true;
    preloadedVideo = movie;
    try { movie.load(); } catch (_) {}
  }
  function open(opts, done) {
    opts = opts || {};
    var key = seenKey(opts.userId);
    if (!eligible() || !key || storageHas(key) || openDialog ||
        typeof done !== "function") return false;
    var lang = ["uz", "ru", "tj"].includes(opts.lang) ? opts.lang : "ru";
    var overlay = element("div", "li-install-overlay");
    overlay.setAttribute("role", "presentation");
    var card = element("section", "li-install-card");
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-modal", "true");
    var close = element("button", "li-install-close", "×");
    close.type = "button";
    close.setAttribute("aria-label", label(lang, "install.close"));
    var oldFocus = document.activeElement, oldOverflow = document.body.style.overflow;
    var finished = false, movie = null, failTimer = null, handoffLink = null, howButton = null;
    function finish() {
      if (finished) return;
      finished = true;
      markSeen(key);
      clearTimeout(failTimer);
      if (movie) {
        movie.pause();
        movie.removeAttribute("src");
        try { movie.load(); } catch (_) {}
        preloadedVideo = null;
      }
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = oldOverflow;
      overlay.remove();
      openDialog = null;
      if (oldFocus && oldFocus.isConnected && oldFocus.focus) oldFocus.focus();
      done();
    }
    function onKey(event) {
      if (event.key === "Escape") { event.preventDefault(); finish(); return; }
      if (event.key !== "Tab") return;
      var a = [close, howButton, handoffLink].filter(function(n) {
        return n && !n.hidden && n.getClientRects().length;
      });
      if (!a.length) return;
      if (event.shiftKey && document.activeElement === a[0]) {
        event.preventDefault(); a[a.length - 1].focus();
      } else if (!event.shiftKey && document.activeElement === a[a.length - 1]) {
        event.preventDefault(); a[0].focus();
      }
    }
    close.addEventListener("click", finish);
    card.appendChild(close);

    if (safari()) {
      preload();
      movie = preloadedVideo || element("video", "");
      movie.className = "li-install-video";
      movie.hidden = true;
      movie.controls = true;
      movie.playsInline = true;
      movie.setAttribute("aria-label", label(lang, "install.videoLabel"));
      if (!movie.src) movie.src = VIDEO;

      var intro = element("div", "li-install-intro-page");
      var title = element("h2", "li-install-title", label(lang, "install.title"));
      title.id = "li-install-title";
      var picture = element("img", "li-install-hero");
      picture.src = HERO;
      picture.width = 1448; picture.height = 1086;
      picture.alt = label(lang, "install.heroAlt");
      picture.decoding = "async"; picture.loading = "eager";
      howButton = element("button", "li-install-how", label(lang, "install.how"));
      howButton.type = "button";
      intro.append(title, picture, howButton);
      card.setAttribute("aria-labelledby", title.id);

      var detail = element("div", "li-install-video-page");
      detail.hidden = true;
      var back = element("button", "li-install-back", "‹");
      back.type = "button";
      back.setAttribute("aria-label", label(lang, "install.back"));
      var mediaStage = element("div", "li-install-video-stage");
      var media = element("div", "li-install-media");
      var loading = element("div", "li-install-video-loading");
      loading.setAttribute("role", "status");
      loading.setAttribute("aria-label", label(lang, "install.videoLabel"));
      var fallback = element("div", "li-install-video-fallback");
      fallback.hidden = true;
      var steps = element("ol", "li-install-steps");
      ["install.step1", "install.step2", "install.step3"].forEach(function(k) {
        steps.appendChild(element("li", "", label(lang, k)));
      });
      fallback.appendChild(steps.cloneNode(true));
      media.append(movie, loading, fallback);
      mediaStage.appendChild(media);
      var more = element("div", "li-install-scroll-steps");
      more.appendChild(steps);
      detail.append(back, mediaStage, more);

      function showFallback() {
        if (finished) return;
        movie.hidden = true; loading.hidden = true;
        fallback.hidden = false; more.hidden = true;
        media.classList.add("is-fallback");
      }
      function showMovie() {
        if (finished || !movie.videoWidth) return;
        clearTimeout(failTimer);
        movie.hidden = false; loading.hidden = true;
        fallback.hidden = true; more.hidden = false;
        media.classList.remove("is-fallback");
      }
      movie.addEventListener("loadedmetadata", showMovie);
      movie.addEventListener("error", showFallback);
      howButton.addEventListener("click", function() {
        intro.hidden = true; detail.hidden = false;
        card.classList.add("li-install-show-video");
        if (movie.readyState >= 1) showMovie();
        else failTimer = setTimeout(showFallback, 10000);
        back.focus();
      });
      back.addEventListener("click", function() {
        clearTimeout(failTimer);
        detail.hidden = true; intro.hidden = false;
        card.classList.remove("li-install-show-video");
        howButton.focus();
      });
      card.append(intro, detail);
    } else {
      var panda = element("div", "li-install-panda");
      panda.setAttribute("aria-hidden", "true");
      var draw = global.HSKCharacters && global.HSKCharacters.render;
      var art = typeof draw === "function" ? draw("panda", "talk") : "";
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
    overlay.appendChild(card);
    document.body.appendChild(overlay);
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKey);
    openDialog = overlay;
    close.focus();
    return true;
  }
  global.HSKAILiInstallGuide = {
    open: open, preload: preload, eligible: eligible,
    standalone: standalone, safari: safari
  };
})(window);
