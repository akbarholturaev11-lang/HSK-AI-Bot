/* Standalone iPhone PWA practice boot overlay; completely inert in Telegram. */
(function () {
  "use strict";
  if (!/^\/iphone-pwa\/practice\/(?:recognition|pronunciation|memorize|test|mistakes)$/.test(location.pathname)) return;
  document.documentElement.classList.add("hsk-pwa-practice");
  var params = new URLSearchParams(location.search);
  var lang = params.get("lang") || "ru";
  if (["uz", "ru", "tj"].indexOf(lang) === -1) lang = "ru";
  var leaving = false;
  function host() {
    if (params.get("embedded") !== "1" || parent === window) return null;
    try {
      var resource = parent.RESOURCE;
      return resource && resource.isPracticeFrame(window) ? resource : null;
    } catch (_) { return null; }
  }
  function back() {
    if (leaving) return;
    var resource = host();
    if (resource) { resource.closePracticeFrame(window); return; }
    beforeClose();
    var url = new URL("/iphone-pwa/course", location.origin);
    url.searchParams.set("tab", "mashq");
    url.searchParams.set("lang", lang);
    var level = params.get("level") || "";
    if (/^(?:hsk[1-4]|nhsk[1-3])$/.test(level)) url.searchParams.set("level", level);
    location.replace(url);
  }
  window.addEventListener("pageshow", function () { leaving = false; });
  function goCourse() {
    var resource = host();
    return !!(resource && resource.closePracticeFrame(window, "course"));
  }
  function checkout(source) {
    var resource = host();
    return !!(resource && resource.openPracticeCheckout(window, source));
  }
  function signIn() {
    var resource = host();
    if (resource) resource.signInFromPractice(window);
    else location.replace("/iphone-pwa");
  }
  function acceptActor(id) {
    var resource = host();
    return !resource || resource.acceptPracticeActor(window, id);
  }
  function beforeClose() {
    if (leaving) return;
    leaving = true;
    ["stopSpeak", "cancelPracticeRecording", "reportResults", "reportWrong"].forEach(function (name) {
      try { if (typeof window[name] === "function") window[name](); } catch (_) {}
    });
  }
  var overlay = document.createElement("div");
  overlay.id = "hsk-pwa-practice-loader";
  overlay.setAttribute("role", "status");
  overlay.setAttribute("aria-live", "polite");
  overlay.innerHTML =
    '<div class="hsk-pwa-practice-loading-content">' +
      '<div class="hsk-pwa-practice-placeholder" aria-hidden="true">🐼</div>' +
    '</div>';
  document.body.appendChild(overlay);
  var ready = false, waitingForInteraction = false, warningTimer = null;
  var practiceKind = location.pathname.split("/").pop();
  function revealFrame() {
    var resource = host();
    if (resource) resource.revealPracticeFrame(window);
  }
  function update() {
    if (ready) return;
    var component = window.HSKStudyPreparing;
    if (component && typeof component.render === "function") {
      overlay.firstElementChild.innerHTML = component.render(lang);
    }
  }
  function hide() {
    if (ready) return;
    ready = true;
    if (warningTimer) clearTimeout(warningTimer);
    warningTimer = null;
    overlay.hidden = true;
    document.documentElement.classList.remove("hsk-pwa-practice-loading");
    revealFrame();
  }
  function show() {
    ready = false;
    overlay.hidden = false;
    document.documentElement.classList.add("hsk-pwa-practice-loading");
    update();
    if (warningTimer) clearTimeout(warningTimer);
    warningTimer = setTimeout(function () {
      if (ready) return;
      var catalog = window.HSKAI_COURSE_I18N && window.HSKAI_COURSE_I18N[lang] || {};
      var p = document.createElement("p");
      p.textContent = catalog["practiceGateError.body"] || "Connection problem";
      var backButton = document.createElement("button");
      backButton.type = "button";
      backButton.className = "hsk-pwa-practice-back";
      backButton.textContent = catalog["practiceGate.back"] || "Back";
      backButton.addEventListener("click", back);
      overlay.firstElementChild.replaceChildren(p, backButton);
      revealFrame();
    }, 20000);
  }
  show();
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", update, {once:true});
  else update();
  // Exam/review pages are not gated like the three word exercises. Watch
  // the actual rendered content rather than assuming a network timeout means ready.
  function routeReady() {
    if (ready) return;
    if (practiceKind === "test") {
      var exams = document.querySelector("#exam.on, #empty.on, #placement.on");
      var hub = document.getElementById("hub");
      if (exams || (!waitingForInteraction && hub &&
          hub.style.display !== "none" &&
          document.querySelector("#ex-list .ex"))) hide();
    }
    if (practiceKind === "mistakes") {
      if (document.querySelector('#review:not([hidden]), #limit:not([hidden])')) hide();
      if (!waitingForInteraction && document.querySelector(
          "#content .cta, #content .empty, #content .state .ti-wifi-off")) hide();
    }
  }
  if (practiceKind === "test" || practiceKind === "mistakes") {
    var observer = new MutationObserver(routeReady);
    observer.observe(document.body, {subtree:true, childList:true,
      attributes:true, attributeFilter:["style","class","hidden"]});
    document.addEventListener("click", function(event) {
      var target = event.target;
      if (practiceKind === "test" && target.closest('[onclick^="openExam("]')) {
        waitingForInteraction = true; show();
      }
      if (practiceKind === "mistakes" && target.closest('[onclick^="startReview("]')) {
        waitingForInteraction = true; show();
      }
    }, true);
    document.addEventListener("DOMContentLoaded", routeReady, {once:true});
  }
  function swipeBack() {
    if (ready && practiceKind === "test") {
      if (document.querySelector("#exam.on")) { window.exitExam(); return; }
      if (document.querySelector("#placement.on, #empty.on")) { window.showHub(); return; }
    }
    if (ready && practiceKind === "mistakes") {
      if (document.querySelector("#limit:not([hidden])")) { window.closeLimit(); return; }
      if (document.querySelector("#review:not([hidden])")) { window.closeReview(); return; }
    }
    back();
  }
  var swipe = null;
  document.addEventListener("touchstart", function (event) {
    swipe = null;
    if (event.touches.length !== 1 || event.target.closest("input, textarea, select, [contenteditable]")) return;
    var touch = event.touches[0];
    swipe = {x:touch.clientX, y:touch.clientY, dx:0, active:false};
  }, {passive:true});
  document.addEventListener("touchmove", function (event) {
    if (!swipe) return;
    if (event.touches.length !== 1) { swipe = null; return; }
    var touch = event.touches[0], dx = touch.clientX - swipe.x, dy = Math.abs(touch.clientY - swipe.y);
    if (!swipe.active) {
      if (dy > 8 && dy >= Math.abs(dx) * 1.15) { swipe = null; return; }
      if (dx < 12 || dx < dy * 1.25) return;
      swipe.active = true;
    }
    swipe.dx = dx;
    if (event.cancelable) event.preventDefault();
  }, {passive:false});
  document.addEventListener("touchend", function () {
    var complete = swipe && swipe.active && swipe.dx >= Math.min(56, Math.max(32, innerWidth - swipe.x - 8));
    swipe = null;
    if (complete) swipeBack();
  }, {passive:true});
  document.addEventListener("touchcancel", function () { swipe = null; }, {passive:true});
  window.HskPwaPracticeBoot = {
    hide:hide, show:show, back:back, swipeBack:swipeBack, goCourse:goCourse,
    checkout:checkout, signIn:signIn, acceptActor:acceptActor, beforeClose:beforeClose,
    isClosing:function () { return leaving; }
  };
}());
