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
  var ready = false;
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
    overlay.hidden = true;
    document.documentElement.classList.remove("hsk-pwa-practice-loading");
  }
  function show() {
    ready = false;
    overlay.hidden = false;
    document.documentElement.classList.add("hsk-pwa-practice-loading");
    update();
  }
  show();
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", update, {once:true});
  else update();
  window.HskPwaPracticeBoot = {hide:hide, show:show};
}());
