/* Standalone iPhone PWA practice boot overlay; completely inert in Telegram. */
(function () {
  "use strict";
  if (!/^\/iphone-pwa\/practice\/(?:recognition|pronunciation|memorize|test|mistakes)$/.test(location.pathname)) return;
  document.documentElement.classList.add("hsk-pwa-practice");
  var lang = new URLSearchParams(location.search).get("lang") || "ru";
  if (["uz", "ru", "tj"].indexOf(lang) === -1) lang = "ru";
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
      var back = document.createElement("button");
      back.type = "button";
      back.className = "hsk-pwa-practice-back";
      back.textContent = catalog["practiceGate.back"] || "Back";
      back.addEventListener("click", function () { location.href = "/iphone-pwa/course?tab=mashq&lang=" + lang; });
      overlay.firstElementChild.replaceChildren(p, back);
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
  window.HskPwaPracticeBoot = {hide:hide, show:show};
}());
