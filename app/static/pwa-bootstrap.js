/* HSK AI web host detection, shared by the existing Mini App course UI and PWA.
 * Intentionally not an authentication mechanism: never infer user identity
 * from host mode, storage, Telegram initDataUnsafe or display-mode.
 */
(function () {
  "use strict";
  var telegram = window.Telegram && window.Telegram.WebApp;
  var telegramAuthenticated = !!(telegram && telegram.initData);
  var standalone = !!(
    (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) ||
    window.navigator.standalone === true
  );
  window.HSKAI_WEB_HOST = Object.freeze({
    mode: telegramAuthenticated ? "telegram-miniapp" : "browser",
    standalone: standalone
  });
  // Telegram Mini App must retain its existing SDK and network behavior.
  if (telegramAuthenticated || !window.isSecureContext || !("serviceWorker" in navigator)) {
    return;
  }
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/pwa-sw.js", { scope: "/" }).catch(function () {
      // Install enhancement is optional; the existing Mini App remains usable.
    });
  }, { once: true });
})();
