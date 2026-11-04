/* iPhone PWA pull-to-refresh for the Course, Rating and Profile tabs.
   A standalone Home Screen app has no browser reload control. Pulling the
   page down from its top edge reloads the same tab. Inert outside the PWA
   course route and whenever any layer, lesson or sheet is open. */
(function (root) {
  "use strict";
  if (!root.location || root.location.pathname !== "/iphone-pwa/course") return;
  var TABS = {course: 1, rating: 1, profile: 1}, THRESHOLD = 84, MAX = 120;
  var start = null, pull = 0, node = null, busy = false;
  function activeTab() {
    var on = document.querySelector(".scr.on");
    var id = on && on.id ? on.id.replace(/^s-/, "") : "";
    return TABS[id] ? id : "";
  }
  function blocked() {
    return !!document.querySelector(
      "#flow.on,#sheet.on,#paywall.on,#secov.on,#resourceov.on,#tour.on,#upov.on,#writeov.on," +
      "#levelup.on,#pwa-checkout-layer,#pwa-practice-layer:not([hidden])," +
      "#hsk-pwa-notice-root:not([hidden]),#hsk-pwa-feedback-root:not([hidden]),#hsk-launch-splash:not(.is-done)");
  }
  function indicator() {
    if (node) return node;
    node = document.createElement("div");
    node.setAttribute("aria-hidden", "true");
    node.style.cssText = "position:fixed;left:50%;top:calc(env(safe-area-inset-top,0px) + 6px);z-index:9000;" +
      "width:34px;height:34px;margin-left:-17px;border-radius:50%;display:grid;place-items:center;" +
      "background:var(--card,#fff);color:var(--ink2,#6b6258);box-shadow:0 2px 10px rgba(0,0,0,.12);" +
      "font-size:18px;opacity:0;pointer-events:none;transition:opacity .15s";
    node.innerHTML = '<i class="ti ti-refresh"></i>';
    document.body.appendChild(node);
    return node;
  }
  function reset() {
    start = null; pull = 0;
    if (node) { node.style.opacity = "0"; node.style.transform = ""; }
  }
  document.addEventListener("touchstart", function (ev) {
    if (busy || ev.touches.length !== 1 || (root.scrollY || 0) > 0) return;
    if (!activeTab() || blocked()) return;
    // Horizontal widgets and scrollers keep their own gestures.
    var el = ev.target && ev.target.nodeType === 1 ? ev.target : null;
    for (; el && el !== document.body; el = el.parentElement) {
      if (el.scrollTop > 0 || el.hasAttribute("data-nb-ignore")) return;
      var oy = getComputedStyle(el).overflowY;
      if ((oy === "auto" || oy === "scroll") && el.scrollHeight > el.clientHeight + 4) return;
    }
    start = {x: ev.touches[0].clientX, y: ev.touches[0].clientY};
  }, {passive: true});
  document.addEventListener("touchmove", function (ev) {
    if (!start || ev.touches.length !== 1) return;
    var dy = ev.touches[0].clientY - start.y, dx = ev.touches[0].clientX - start.x;
    if (dy <= 0 || Math.abs(dx) > dy || (root.scrollY || 0) > 0) { reset(); return; }
    pull = Math.min(MAX, dy * 0.6);
    var n = indicator();
    n.style.opacity = String(Math.min(1, pull / THRESHOLD));
    n.style.transform = "translateY(" + Math.round(pull / 2) + "px) rotate(" + Math.round(pull * 3) + "deg)";
  }, {passive: true});
  function finish() {
    var go = start && pull >= THRESHOLD, tab = activeTab();
    reset();
    if (!go || busy || blocked() || !tab) return;
    busy = true;
    try {
      var url = new URL(root.location.href);
      url.searchParams.set("tab", tab);
      root.location.replace(url.pathname + url.search + url.hash);
    } catch (_) { root.location.reload(); }
  }
  document.addEventListener("touchend", finish, {passive: true});
  document.addEventListener("touchcancel", reset, {passive: true});
}(window));
