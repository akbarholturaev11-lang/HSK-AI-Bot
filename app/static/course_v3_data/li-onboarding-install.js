/* HSK AI Li onboarding: iPhone Home Screen installation guide.
   Private profile/Pro state is owned by onboarding runtime, not by this view.
   The optional MP4 is an official fixed-path file; until supplied, the
   local-first three-step illustrated fallback stays usable. */
(function (global) {
  "use strict";
  var VIDEO = "/assets/onboarding/iphone-home-screen.mp4";
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
  function eligible() {
    return global.location.pathname.startsWith("/iphone-pwa/")
      && ios() && !standalone()
      && !(global.Telegram && global.Telegram.WebApp && global.Telegram.WebApp.initData);
  }
  function label(lang, key) {
    var all = global.HSKAI_LI_I18N || {};
    var locale = all[lang] || all.ru || {};
    return locale[key] || (all.ru && all.ru[key]) || "";
  }
  function seenKey(userId) {
    // Scoped to one authenticated actor on this browser; no remote user data.
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
    // Safari private modes may restrict persistent storage. At minimum do
    // not repeat the guide during this tab's authenticated onboarding.
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
    if (!eligible() || !key || storageHas(key) || openDialog) return false;
    if (typeof done !== "function") return false;
    var lang = ["uz","ru","tj"].includes(opts.lang) ? opts.lang : "ru";
    var overlay = element("div", "li-install-overlay");
    overlay.setAttribute("role", "presentation");
    var card = element("section", "li-install-card");
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-modal", "true");
    card.setAttribute("aria-labelledby", "li-install-title");
    card.setAttribute("aria-describedby", "li-install-description");
    var title = element("h2", "li-install-title", label(lang, "install.title"));
    title.id = "li-install-title";
    var copy = element("p", "li-install-intro", label(lang, "install.description"));
    copy.id = "li-install-description";
    var videoArea = element("div", "li-install-media is-fallback");
    var movie = element("video", "li-install-video");
    movie.controls = true;
    movie.playsInline = true;
    movie.preload = "metadata";
    movie.setAttribute("playsinline", "");
    movie.setAttribute("webkit-playsinline", "");
    movie.setAttribute("aria-label", label(lang, "install.videoLabel"));
    movie.hidden = true;
    movie.src = VIDEO;
    // A missing or slow remote MP4 must never leave an empty grey player.
    // Text guidance is immediately usable; show the player only after
    // real media metadata has loaded.
    var fallback = element("div", "li-install-video-fallback", label(lang, "install.videoFallback"));
    fallback.hidden = false;
    movie.addEventListener("loadedmetadata", function () {
      movie.hidden = false;
      fallback.hidden = true;
      videoArea.classList.remove("is-fallback");
    }, { once: true });
    movie.addEventListener("error", function () {
      movie.hidden = true;
      fallback.hidden = false;
      videoArea.classList.add("is-fallback");
    }, { once: true });
    videoArea.append(movie, fallback);
    var steps = element("ol", "li-install-steps");
    ["install.step1", "install.step2", "install.step3"].forEach(function (k) {
      steps.appendChild(element("li", "", label(lang, k)));
    });
    var note = element("p", "li-install-note", label(lang, "install.note"));
    var continueButton = element("button", "li-install-continue", label(lang, "install.continue"));
    continueButton.type = "button";
    var close = element("button", "li-install-close", "×");
    close.type = "button";
    close.setAttribute("aria-label", label(lang, "install.close"));
    var oldFocus = document.activeElement;
    var oldOverflow = document.body.style.overflow;
    var finished = false;
    function finish() {
      if (finished) return;
      finished = true;
      markSeen(key);
      movie.pause();
      movie.removeAttribute("src");
      try { movie.load(); } catch (_) {}
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
        var active = [close, movie, continueButton].filter(function (node) {
          return !node.hidden && node.getClientRects().length;
        });
        if (!active.length) return;
        if (event.shiftKey && document.activeElement === active[0]) {
          event.preventDefault(); active[active.length - 1].focus();
        } else if (!event.shiftKey && document.activeElement === active[active.length - 1]) {
          event.preventDefault(); active[0].focus();
        }
      }
    }
    close.addEventListener("click", finish);
    continueButton.addEventListener("click", finish);
    card.append(close, title, copy, videoArea, steps, note, continueButton);
    overlay.appendChild(card);
    document.body.appendChild(overlay);
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", keydown);
    openDialog = overlay;
    close.focus();
    try { movie.load(); }
    catch (_) { movie.hidden = true; fallback.hidden = false; }
    return true;
  }
  global.HSKAILiInstallGuide = { open: open, eligible: eligible, standalone: standalone };
})(window);
