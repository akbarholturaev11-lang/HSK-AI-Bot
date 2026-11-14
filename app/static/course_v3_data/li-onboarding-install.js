/* Verified iPhone PWA installation guide: compact hero -> video.
   Browser-mode iOS only (an installed standalone PWA never sees it), shown
   once per opening: one Safari tab session, not a permanent per-account flag.
   Safari cannot tell whether the app is already on the Home Screen; only the
   current browser vs standalone display mode is known.
   UI only; owner/entitlements/progress are server-authoritative elsewhere. */
(function (global) {
  "use strict";
  var VIDEO = "/assets/onboarding/iphone-home-screen.mp4?v=20261109-3e099a0c0489";
  var HERO = "/assets/onboarding/iphone-install-home-focus.jpg?v=20261110-4250a78bf29e";
  var PWA_URL = "https://hskai.app/iphone-pwa";
  // Per tab: survives same-tab OAuth/Telegram returns, payment returns and
  // onboarding -> course, so one opening never shows the guide twice.
  var SHOWN_KEY = "hskai.pwa.install.guide.shown";
  var launchScript = document.currentScript;
  var openDialog = null, preloadedVideo = null, shownHere = false;

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
  function topLevel() {
    try { return global.top === global; } catch (_) { return false; }
  }
  function eligible() {
    return global.location.pathname.startsWith("/iphone-pwa/") && topLevel() &&
      ios() && !standalone();
  }
  function label(lang, key) {
    var all = global.HSKAI_LI_I18N || {};
    var locale = all[lang] || all.ru || {};
    return locale[key] || (all.ru && all.ru[key]) || "";
  }
  function verifiedUser(userId) {
    return Number.isSafeInteger(userId) && userId > 0;
  }
  function alreadyShown() {
    if (shownHere) return true;
    try { return global.sessionStorage.getItem(SHOWN_KEY) === "1"; } catch (_) { return false; }
  }
  function markShown() {
    shownHere = true;
    try { global.sessionStorage.setItem(SHOWN_KEY, "1"); } catch (_) {}
  }
  function element(tag, css, text) {
    var node = document.createElement(tag);
    if (css) node.className = css;
    if (typeof text === "string") node.textContent = text;
    return node;
  }
  function copyText(text, done) {
    function legacy() {
      var field = document.createElement("textarea");
      field.value = text;
      field.setAttribute("readonly", "");
      field.style.cssText = "position:fixed;top:0;left:0;width:1px;height:1px;opacity:0";
      document.body.appendChild(field);
      field.select();
      try { field.setSelectionRange(0, text.length); } catch (_) {}
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (_) {}
      field.remove();
      done(ok);
    }
    try {
      if (global.navigator.clipboard && global.navigator.clipboard.writeText) {
        global.navigator.clipboard.writeText(text).then(function () { done(true); }, legacy);
        return;
      }
    } catch (_) {}
    legacy();
  }
  function selectText(node) {
    // Copy denied: leave the visible link selected for the native Copy menu.
    try {
      var range = document.createRange();
      range.selectNodeContents(node);
      var selection = global.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    } catch (_) {}
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
    if (!eligible() || !verifiedUser(opts.userId) || alreadyShown() || openDialog ||
        typeof done !== "function") return false;
    var lang = ["uz", "ru", "tj"].includes(opts.lang) ? opts.lang : "ru";
    var overlay = element("div", "li-install-overlay");
    overlay.setAttribute("role", "presentation");
    var card = element("section", "li-install-card");
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-modal", "true");
    var close = element("button", "li-install-close");
    close.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M5 5L19 19M19 5L5 19"/></svg>';
    close.type = "button";
    close.setAttribute("aria-label", label(lang, "install.close"));
    var oldFocus = document.activeElement, oldOverflow = document.body.style.overflow;
    var finished = false, movie = null, failTimer = null, copyTimer = null;
    var handoffLink = null, howButton = null, copyButton = null;
    function finish() {
      if (finished) return;
      finished = true;
      markShown();
      clearTimeout(failTimer);
      clearTimeout(copyTimer);
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
      var a = [close, howButton, movie, handoffLink, copyButton].filter(function(n) {
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
      picture.width = 1254; picture.height = 1254;
      picture.alt = label(lang, "install.heroAlt");
      picture.decoding = "async"; picture.loading = "eager";
      howButton = element("button", "li-install-how", label(lang, "install.how"));
      howButton.type = "button";
      intro.append(title, picture, howButton);
      card.setAttribute("aria-labelledby", title.id);

      var detail = element("div", "li-install-video-page");
      detail.hidden = true;
      var mediaStage = element("div", "li-install-video-stage");
      var guideTitle = element("h2", "li-install-video-title", label(lang, "install.guideTitle"));
      guideTitle.id = "li-install-video-title";
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
      mediaStage.append(guideTitle, media);
      var more = element("div", "li-install-scroll-steps");
      more.appendChild(steps);
      detail.append(mediaStage, more);

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
        card.setAttribute("aria-labelledby", guideTitle.id);
        if (movie.error) showFallback();
        else if (movie.readyState >= 1) showMovie();
        else failTimer = setTimeout(showFallback, 10000);
        close.focus();
      });
      card.append(intro, detail);
    } else {
      var panda = element("div", "li-install-panda");
      panda.setAttribute("aria-hidden", "true");
      var draw = global.HSKCharacters && global.HSKCharacters.render;
      var art = typeof draw === "function" ? draw("panda", "talk") : "";
      if (typeof art === "string" && art) panda.innerHTML = art;
      else panda.textContent = "🐼";
      var browserTitle = element("h2", "li-install-browser-title");
      browserTitle.id = "li-install-browser-title";
      var safariIcon = element("span", "li-install-safari-icon");
      safariIcon.setAttribute("aria-hidden", "true");
      // Safari compass glyph: Font Awesome Free 6.7.2, CC BY 4.0.
      safariIcon.innerHTML = "<svg viewBox=\"0 0 512 512\" xmlns=\"http://www.w3.org/2000/svg\" focusable=\"false\"><path fill=\"currentColor\" d=\"M274.69,274.69l-37.38-37.38L166,346ZM256,8C119,8,8,119,8,256S119,504,256,504,504,393,504,256,393,8,256,8ZM411.85,182.79l14.78-6.13A8,8,0,0,1,437.08,181h0a8,8,0,0,1-4.33,10.46L418,197.57a8,8,0,0,1-10.45-4.33h0A8,8,0,0,1,411.85,182.79ZM314.43,94l6.12-14.78A8,8,0,0,1,331,74.92h0a8,8,0,0,1,4.33,10.45l-6.13,14.78a8,8,0,0,1-10.45,4.33h0A8,8,0,0,1,314.43,94ZM256,60h0a8,8,0,0,1,8,8V84a8,8,0,0,1-8,8h0a8,8,0,0,1-8-8V68A8,8,0,0,1,256,60ZM181,74.92a8,8,0,0,1,10.46,4.33L197.57,94a8,8,0,1,1-14.78,6.12l-6.13-14.78A8,8,0,0,1,181,74.92Zm-63.58,42.49h0a8,8,0,0,1,11.31,0L140,128.72A8,8,0,0,1,140,140h0a8,8,0,0,1-11.31,0l-11.31-11.31A8,8,0,0,1,117.41,117.41ZM60,256h0a8,8,0,0,1,8-8H84a8,8,0,0,1,8,8h0a8,8,0,0,1-8,8H68A8,8,0,0,1,60,256Zm40.15,73.21-14.78,6.13A8,8,0,0,1,74.92,331h0a8,8,0,0,1,4.33-10.46L94,314.43a8,8,0,0,1,10.45,4.33h0A8,8,0,0,1,100.15,329.21Zm4.33-136h0A8,8,0,0,1,94,197.57l-14.78-6.12A8,8,0,0,1,74.92,181h0a8,8,0,0,1,10.45-4.33l14.78,6.13A8,8,0,0,1,104.48,193.24ZM197.57,418l-6.12,14.78a8,8,0,0,1-14.79-6.12l6.13-14.78A8,8,0,1,1,197.57,418ZM264,444a8,8,0,0,1-8,8h0a8,8,0,0,1-8-8V428a8,8,0,0,1,8-8h0a8,8,0,0,1,8,8Zm67-6.92h0a8,8,0,0,1-10.46-4.33L314.43,418a8,8,0,0,1,4.33-10.45h0a8,8,0,0,1,10.45,4.33l6.13,14.78A8,8,0,0,1,331,437.08Zm63.58-42.49h0a8,8,0,0,1-11.31,0L372,383.28A8,8,0,0,1,372,372h0a8,8,0,0,1,11.31,0l11.31,11.31A8,8,0,0,1,394.59,394.59ZM286.25,286.25,110.34,401.66,225.75,225.75,401.66,110.34ZM437.08,331h0a8,8,0,0,1-10.45,4.33l-14.78-6.13a8,8,0,0,1-4.33-10.45h0A8,8,0,0,1,418,314.43l14.78,6.12A8,8,0,0,1,437.08,331ZM444,264H428a8,8,0,0,1-8-8h0a8,8,0,0,1,8-8h16a8,8,0,0,1,8,8h0A8,8,0,0,1,444,264Z\"/></svg>";
      browserTitle.append(safariIcon, document.createTextNode(label(lang, "install.safariTitle")));
      var hint = element("p", "li-install-browser-hint");
      hint.appendChild(document.createTextNode(label(lang, "install.safariHint") + " "));
      handoffLink = element("a", "li-install-browser-link", "hskai.app/iphone-pwa");
      handoffLink.href = PWA_URL;
      hint.appendChild(handoffLink);
      copyButton = element("button", "li-install-copy", label(lang, "install.copyLink"));
      copyButton.type = "button";
      copyButton.addEventListener("click", function() {
        copyText(PWA_URL, function(ok) {
          if (finished) return;
          if (!ok) { selectText(handoffLink); return; }
          copyButton.textContent = label(lang, "install.copied");
          clearTimeout(copyTimer);
          copyTimer = setTimeout(function() {
            if (!finished) copyButton.textContent = label(lang, "install.copyLink");
          }, 2000);
        });
      });
      card.setAttribute("aria-labelledby", browserTitle.id);
      card.append(panda, browserTitle, hint, copyButton);
    }
    overlay.appendChild(card);
    document.body.appendChild(overlay);
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKey);
    openDialog = overlay;
    close.focus();
    return true;
  }

  function loadAsset(url, css) {
    return new Promise(function(resolve, reject) {
      if (typeof url !== "string" || url.indexOf("/course_v3_data/") !== 0) {
        reject(new Error("install_asset_invalid")); return;
      }
      var node = document.createElement(css ? "link" : "script");
      node.onload = resolve;
      node.onerror = reject;
      if (css) { node.rel = "stylesheet"; node.href = url; }
      else { node.src = url; node.async = true; }
      document.head.appendChild(node);
    });
  }
  // /iphone-pwa/course: the server adds this script to the PWA response only
  // (shared course HTML is unchanged), with its versioned catalog/stylesheet.
  // Existing accounts thus get the same guide as a fresh sign-up.
  function launchCourse(script) {
    var query = new URLSearchParams(global.location.search);
    // An external payment return resumes checkout; never cover it.
    if (global.location.pathname !== "/iphone-pwa/course" || !eligible() || alreadyShown() ||
        query.has("pro_checkout") || query.has("pro_return") ||
        typeof global.pwaCourseActor !== "function") return;
    var nav = global.NavBack;
    // While open, course prompts (feedback, ads) treat it as a blocking layer.
    if (nav && Array.isArray(nav.BLOCK) && nav.BLOCK.indexOf(".li-install-overlay") < 0)
      nav.BLOCK.push(".li-install-overlay");
    Promise.all([
      global.HSKAI_LI_I18N ? null : loadAsset(script.getAttribute("data-i18n"), false),
      loadAsset(script.getAttribute("data-css"), true),
      global.pwaCourseActor()
    ]).then(function(results) {
      var actor = results[2] || {};
      function show() {
        if (document.visibilityState === "hidden") {
          document.addEventListener("visibilitychange", function again() {
            if (document.visibilityState !== "visible") return;
            document.removeEventListener("visibilitychange", again);
            show();
          });
          return;
        }
        open({userId: Number(actor.user_id), lang: actor.language || global.LANG}, function() {
          // Resume what the course queued while the guide covered it.
          if (typeof global.flushPendingCenterAd === "function") {
            try { global.flushPendingCenterAd(); } catch (_) {}
          }
        });
      }
      show();
    }).catch(function() { /* Optional guide: never block the course. */ });
  }

  global.HSKAILiInstallGuide = {
    open: open, preload: preload, eligible: eligible,
    standalone: standalone, safari: safari
  };
  if (launchScript && launchScript.getAttribute("data-hsk-install-launch") === "course")
    launchCourse(launchScript);
})(window);
