/* iPhone PWA feedback: the Telegram haptic API is absent in a browser, so
   answer feedback falls back to a Safari switch tick (iOS 17.4+) or
   navigator.vibrate (Android), plus a short tone for pages with no sound.
   Inert outside /iphone-pwa/ and when reduced motion is requested. */
(function (root) {
  "use strict";
  if (!root.location || root.location.pathname.indexOf("/iphone-pwa/") !== 0) return;
  var label = null, ctx = null;
  function quiet() {
    try { return !!(root.matchMedia && root.matchMedia("(prefers-reduced-motion: reduce)").matches); }
    catch (_) { return false; }
  }
  function tick() {
    try {
      if (!label) {
        label = document.createElement("label");
        label.setAttribute("aria-hidden", "true");
        label.style.cssText = "position:fixed;left:-99px;top:-99px;width:1px;height:1px;opacity:0;pointer-events:none";
        var box = document.createElement("input");
        box.type = "checkbox"; box.setAttribute("switch", ""); box.tabIndex = -1;
        label.appendChild(box);
        (document.body || document.documentElement).appendChild(label);
      }
      label.click();
    } catch (_) { /* Haptics are best-effort. */ }
  }
  var PATTERNS = {
    success: [0, 90], error: [0, 70, 140], light: [0], ok: [0, 90], no: [0, 70, 140],
    med: [0], medium: [0], heavy: [0, 80, 160]
  };
  function haptic(kind) {
    if (quiet()) return;
    var steps = PATTERNS[kind] || PATTERNS.light;
    if (root.navigator && typeof root.navigator.vibrate === "function") {
      try { root.navigator.vibrate(kind === "error" || kind === "no" ? [30, 40, 30, 40, 50] : kind === "heavy" ? 40 : 18); return; }
      catch (_) { /* Fall through to the Safari tick. */ }
    }
    steps.forEach(function (delay) { delay ? root.setTimeout(tick, delay) : tick(); });
  }
  var TONES = {success: [523, 659, 784], ok: [523, 659, 784], error: [220, 180], no: [220, 180]};
  function tone(kind) {
    var seq = TONES[kind];
    if (!seq || quiet()) return;
    try {
      var Ctx = root.AudioContext || root.webkitAudioContext;
      if (!Ctx) return;
      ctx = ctx || new Ctx();
      if (ctx.state === "suspended") ctx.resume();
      var t0 = ctx.currentTime;
      seq.forEach(function (freq, i) {
        var osc = ctx.createOscillator(), gain = ctx.createGain(), at = t0 + i * 0.09;
        osc.frequency.value = freq; osc.connect(gain); gain.connect(ctx.destination);
        gain.gain.setValueAtTime(0.0001, at);
        gain.gain.exponentialRampToValueAtTime(0.12, at + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.16);
        osc.start(at); osc.stop(at + 0.18);
      });
    } catch (_) { /* Sound is best-effort. */ }
  }
  root.HskPwaFx = {haptic: haptic, tone: tone,
    feedback: function (kind) { haptic(kind); tone(kind); }};
}(window));
