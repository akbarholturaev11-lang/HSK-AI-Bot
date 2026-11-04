/* iPhone standalone PWA only. Android behavior port; no Telegram Mini App hooks.
 * Permission is always requested from a user click (iOS transient activation).
 * Capture is local-only until the learner explicitly sends a report.
 */
(function () {
  "use strict";
  if (location.pathname !== "/iphone-pwa/course") return;
  var standalone = !!(navigator.standalone ||
    (window.matchMedia && matchMedia("(display-mode: standalone)").matches));
  if (!standalone) return;

  var owner = null, desired = true, seen = false, permitted = false;
  var permissionRequired = true, listening = false, busy = false, epoch = 0;
  var sampleReady = false, gx = 0, gy = 0, gz = 0, above = false;
  var firstPeak = null, lastShake = -100000, snapshot = null;
  var stage = "", submitting = false, reportScreen = "course", reportDescription = "";
  var lastFocus = null;
  var root = document.createElement("div");
  root.id = "hsk-pwa-shake-root";
  root.hidden = true;
  root.innerHTML = '<div class="hsk-shake-scrim"></div>' +
    '<section class="hsk-shake-dialog" role="dialog" aria-modal="true" aria-labelledby="hsk-shake-title" tabindex="-1">' +
    '<div class="hsk-shake-head"><h2 id="hsk-shake-title"></h2><button type="button" id="hsk-shake-close" aria-label="Close">×</button></div>' +
    '<div id="hsk-shake-body"></div><p id="hsk-shake-status" role="status" aria-live="polite"></p>' +
    '<div id="hsk-shake-actions"></div></section>';
  document.body.appendChild(root);
  var title = root.querySelector("#hsk-shake-title");
  var body = root.querySelector("#hsk-shake-body");
  var status = root.querySelector("#hsk-shake-status");
  var actions = root.querySelector("#hsk-shake-actions");
  var dialog = root.querySelector(".hsk-shake-dialog");
  function l(key) { return courseMessage("pwaShake." + key, ""); }
  function storageKey() { return "hskai.pwa.shake.v1." + owner; }
  function readPreference() {
    try {
      var value = JSON.parse(localStorage.getItem(storageKey()) || "{}");
      desired = value.enabled !== false;
      seen = value.seen === true;
    } catch (_) { desired = true; seen = false; }
  }
  function savePreference() {
    if (!owner) return;
    try { localStorage.setItem(storageKey(), JSON.stringify({enabled:desired,seen:seen})); }
    catch (_) { /* Storage failure never grants sensor permission. */ }
  }
  function showMessage(text) { status.textContent = text || ""; }
  function makeButton(key, handler, secondary) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = secondary ? "hsk-shake-secondary" : "hsk-shake-primary";
    button.textContent = l(key);
    button.addEventListener("click", handler);
    actions.appendChild(button);
    return button;
  }
  function renderShell(key) {
    title.textContent = l(key);
    body.replaceChildren();
    actions.replaceChildren();
    showMessage("");
  }
  function show(step) {
    if (root.hidden) lastFocus = document.activeElement;
    stage = step;
    root.hidden = false;
    dialog.focus();
  }
  function close() {
    if (submitting) return;
    var wasIntro = stage === "intro";
    root.hidden = true;
    stage = "";
    snapshot = null;
    reportDescription = "";
    busy = false;
    epoch += 1;
    if (wasIntro) { seen = true; savePreference(); }
    if (lastFocus && lastFocus.isConnected && lastFocus.focus) lastFocus.focus();
    restartListening();
  }
  root.querySelector("#hsk-shake-close").addEventListener("click", close);
  root.querySelector(".hsk-shake-scrim").addEventListener("click", close);
  root.addEventListener("keydown", function (event) {
    if (root.hidden) return;
    if (event.key === "Escape") { event.preventDefault(); close(); return; }
    if (event.key !== "Tab") return;
    var items = Array.from(dialog.querySelectorAll("button:not(:disabled),textarea:not(:disabled),input:not(:disabled)"))
      .filter(function (item) { return item.offsetParent !== null; });
    if (!items.length) { event.preventDefault(); dialog.focus(); return; }
    var first = items[0], last = items[items.length - 1];
    if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  });

  function stopListening() {
    if (listening) window.removeEventListener("devicemotion", onMotion);
    listening = false;
    sampleReady = false;
    firstPeak = null;
    above = false;
  }
  function restartListening() {
    stopListening();
    if (!desired || !permitted || !root.hidden || busy || submitting ||
        document.visibilityState === "hidden" || !owner) return;
    window.addEventListener("devicemotion", onMotion, {passive:true});
    listening = true;
  }
  function onMotion(event) {
    if (!listening || !root.hidden || !desired || !permitted) return;
    var a = event.accelerationIncludingGravity;
    if (!a || !Number.isFinite(a.x) || !Number.isFinite(a.y) || !Number.isFinite(a.z)) return;
    var now = Number.isFinite(event.timeStamp) && event.timeStamp > 0 ?
      event.timeStamp : performance.now();
    if (!sampleReady) {
      gx = a.x; gy = a.y; gz = a.z; sampleReady = true;
      return;
    }
    gx = gx * 0.82 + a.x * 0.18;
    gy = gy * 0.82 + a.y * 0.18;
    gz = gz * 0.82 + a.z * 0.18;
    var force = Math.hypot(a.x - gx, a.y - gy, a.z - gz);
    if (force < 5.5) { above = false; return; }
    if (force < 9 || above) return;
    above = true;
    if (now - lastShake < 4500) return;
    var delta = firstPeak === null ? -1 : now - firstPeak;
    if (delta >= 140 && delta <= 1500) {
      firstPeak = null;
      lastShake = now;
      startReport();
    } else if (delta < 0 || delta > 1500) firstPeak = now;
  }

  function permissionClick() {
    // IMPORTANT: no await, network call, or setTimeout before requestPermission().
    var request;
    try {
      if (!window.DeviceMotionEvent) throw Error("unsupported");
      request = typeof DeviceMotionEvent.requestPermission === "function" ?
        DeviceMotionEvent.requestPermission() : Promise.resolve("granted");
    } catch (_) {
      permitted = false;
      showMessage(l("unavailable"));
      return;
    }
    Promise.resolve(request).then(function (result) {
      if (result !== "granted") {
        permitted = false;
        showMessage(l("denied"));
        return;
      }
      permitted = true;
      permissionRequired = false;
      seen = true;
      savePreference();
      close();
      // Best-effort warm the viewport renderer, never transmit user content.
      loadRenderer().catch(function () {});
    }).catch(function () {
      permitted = false;
      showMessage(l("denied"));
    });
  }
  function introduction() {
    stopListening();
    renderShell("introTitle");
    var p = document.createElement("p");
    p.textContent = l("introBody");
    body.appendChild(p);
    makeButton("allow", permissionClick);
    makeButton("later", function () { seen = true; savePreference(); close(); }, true);
    show("intro");
  }
  function showSettingsPermission() {
    renderShell("introTitle");
    var p = document.createElement("p");
    p.textContent = l("permissionBody");
    body.appendChild(p);
    makeButton("allow", permissionClick);
    makeButton("later", close, true);
    show("permission");
  }

  var rendererPromise = null;
  function loadRenderer() {
    if (typeof window.html2canvas === "function") return Promise.resolve(window.html2canvas);
    if (rendererPromise) return rendererPromise;
    rendererPromise = new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = "/course_v3_data/vendor/html2canvas.min.js?v=1";
      script.onload = function () {
        if (typeof window.html2canvas === "function") resolve(window.html2canvas);
        else reject(Error("renderer_unavailable"));
      };
      script.onerror = function () { reject(Error("renderer_unavailable")); };
      document.head.appendChild(script);
    }).catch(function (error) { rendererPromise = null; throw error; });
    return rendererPromise;
  }
  function encodeJpeg(canvas) {
    var output = null;
    for (var quality = 0.78; quality >= 0.44; quality -= 0.09) {
      output = canvas.toDataURL("image/jpeg", quality);
      if (output.length <= 710000) break;
    }
    return output && output.length <= 710000 && output.indexOf("data:image/jpeg;base64,") === 0 ? output : null;
  }
  async function captureViewport() {
    // Profile, voice transcripts, purchase/auth screens may contain private data.
    if (["profile", "voice"].indexOf(typeof SCREEN === "string" ? SCREEN : "") >= 0 ||
        document.querySelector("#sheet.on .pwa-payment, #sheet.on [class*=receipt], #sheet.on [class*=checkout]")) return null;
    var renderer = await loadRenderer();
    var width = Math.max(1, Math.min(window.innerWidth, 1200));
    var height = Math.max(1, Math.min(window.innerHeight, 1600));
    var canvas = await renderer(document.body, {
      width:width, height:height, x:window.scrollX || 0, y:window.scrollY || 0,
      scrollY: -(window.scrollY || 0), scrollX: -(window.scrollX || 0),
      windowWidth:window.innerWidth, windowHeight:window.innerHeight,
      scale:Math.min(window.devicePixelRatio || 1, 1.5), backgroundColor:"#fff",
      logging:false, useCORS:true, allowTaint:false, imageTimeout:1800,
      onclone:function (doc) {
        // An in-memory clone is used: never alter or strip the visible page.
        var privateSelectors = 'input,textarea,[contenteditable],[type=password],' +
          '[data-private],[data-sensitive],.profile-display-name,' +
          '[class*=payment],[class*=receipt],[class*=checkout],' +
          '[class*=account-number],#hsk-pwa-shake-root';
        doc.querySelectorAll(privateSelectors).forEach(function (node) {
          node.textContent = "";
          node.style.visibility = "hidden";
        });
      }
    });
    try { return encodeJpeg(canvas); }
    finally { canvas.width = 0; canvas.height = 0; }
  }
  function startReport() {
    if (busy || !root.hidden) return;
    busy = true;
    stopListening();
    var generation = ++epoch;
    reportScreen = typeof SCREEN === "string" ? SCREEN.slice(0,80) : "course";
    reportDescription = "";
    captureViewport().catch(function () { return null; }).then(function (image) {
      if (generation !== epoch || !owner || !desired) return;
      snapshot = image;
      confirmReport();
    });
  }
  function confirmReport() {
    renderShell("confirmTitle");
    var p = document.createElement("p");
    p.textContent = l("confirmBody");
    body.appendChild(p);
    makeButton("continue", formReport);
    makeButton("cancel", close, true);
    show("confirm");
  }
  function imagePreview() {
    var wrap = document.createElement("div");
    wrap.className = "hsk-shake-preview";
    if (snapshot) {
      var img = document.createElement("img");
      img.src = snapshot;
      img.alt = l("screenshot");
      wrap.appendChild(img);
      var label = document.createElement("label");
      var check = document.createElement("input");
      check.type = "checkbox";
      check.checked = true;
      check.id = "hsk-shake-attach";
      label.appendChild(check);
      label.appendChild(document.createTextNode(" " + l("screenshot")));
      wrap.appendChild(label);
    } else {
      var note = document.createElement("p");
      note.textContent = l("captureUnavailable");
      wrap.appendChild(note);
    }
    var manual = document.createElement("label");
    manual.className = "hsk-shake-file-label";
    manual.textContent = l("chooseScreenshot");
    var chooser = document.createElement("input");
    chooser.type = "file";
    chooser.accept = "image/*";
    chooser.addEventListener("change", function () {
      if (!chooser.files || !chooser.files[0]) return;
      var file = chooser.files[0];
      if (file.size > 6 * 1024 * 1024) {
        showMessage(l("imageTooLarge")); return;
      }
      var url = URL.createObjectURL(file);
      var image = new Image();
      image.onload = function () {
        try {
          var factor = Math.min(1, 1600 / Math.max(image.width,image.height));
          var canvas = document.createElement("canvas");
          canvas.width = Math.max(1, Math.round(image.width * factor));
          canvas.height = Math.max(1, Math.round(image.height * factor));
          canvas.getContext("2d").drawImage(image,0,0,canvas.width,canvas.height);
          snapshot = encodeJpeg(canvas);
          canvas.width = canvas.height = 0;
          if (!snapshot) showMessage(l("imageTooLarge"));
          else { showMessage(""); formReport(); }
        } catch (_) { showMessage(l("captureUnavailable")); }
        URL.revokeObjectURL(url);
      };
      image.onerror = function () { URL.revokeObjectURL(url); showMessage(l("captureUnavailable")); };
      image.src = url;
    });
    manual.appendChild(chooser);
    wrap.appendChild(manual);
    return wrap;
  }
  function formReport() {
    if (stage === "form") {
      var previous = root.querySelector("#hsk-shake-description");
      if (previous) reportDescription = previous.value;
    }
    renderShell("formTitle");
    var label = document.createElement("label");
    label.textContent = l("description");
    var textarea = document.createElement("textarea");
    textarea.id = "hsk-shake-description";
    textarea.maxLength = 2000;
    textarea.rows = 4;
    textarea.placeholder = l("hint");
    textarea.value = reportDescription;
    textarea.addEventListener("input", function () { reportDescription = textarea.value; });
    label.appendChild(textarea);
    body.appendChild(label);
    body.appendChild(imagePreview());
    makeButton("send", submit);
    makeButton("cancel", close, true);
    show("form");
  }
  async function submit() {
    if (submitting || stage !== "form") return;
    var description = root.querySelector("#hsk-shake-description").value.trim();
    if (description.length < 5) { showMessage(l("minLength")); return; }
    submitting = true;
    var buttons = actions.querySelectorAll("button");
    buttons.forEach(function (b) { b.disabled = true; });
    showMessage(l("sending"));
    var originalOwner = owner;
    try {
      // Fresh cookie verification (cached PWA actor must not outlive a logout).
      var sessionRes = await fetch("/api/v3/pwa-auth/session", {
        credentials:"same-origin", cache:"no-store", redirect:"error"
      });
      if (!sessionRes.ok) throw Error("session");
      var session = await sessionRes.json();
      if (!session.ok || Number(session.user_id) !== originalOwner ||
          !session.csrf || !root.isConnected || stage !== "form") throw Error("session");
      var checked = root.querySelector("#hsk-shake-attach");
      var payload = {
        description:description,
        screen:reportScreen,
        app_version:"iphone-pwa",
        screenshot_data_url: snapshot && (!checked || checked.checked) ? snapshot : ""
      };
      var response = await fetch("/api/v3/pwa/bug-report",{
        method:"POST", credentials:"same-origin", cache:"no-store", redirect:"error",
        headers:{"Content-Type":"application/json","X-HSK-PWA-CSRF":session.csrf},
        body:JSON.stringify(payload)
      });
      var result = await response.json();
      if (!response.ok || !result || result.ok !== true) throw Error(result && result.error || "send");
      renderShell("sentTitle");
      var p = document.createElement("p"); p.textContent = l("sentBody");
      body.appendChild(p);
      makeButton("done", close);
      show("sent");
      snapshot = null;
    } catch (_) {
      showMessage(l("failed"));
    } finally {
      submitting = false;
      buttons.forEach(function (b) { if (b.isConnected) b.disabled = false; });
    }
  }

  function settingsRowHtml() {
    if (!owner) return "";
    var label = desired ? (permitted ? l("on") : l("needsPermission")) : l("off");
    var extra = desired && !permitted ?
      '<button type="button" class="srow" onclick="HskPwaShake.request()"><i class="ti ti-lock-open"></i> ' +
      l("allow") + '</button>' : "";
    return '<button type="button" class="srow" onclick="HskPwaShake.toggle()">' +
      '<i class="ti ti-device-mobile-vibration"></i> ' + l("setting") +
      '<span class="sv">' + label + '</span></button>' + extra;
  }
  function toggle() {
    desired = !desired;
    seen = true;
    savePreference();
    if (!desired) { permitted = false; stopListening(); }
    else { showSettingsPermission(); }
    if (typeof SETTINGS_SHEET !== "undefined" && SETTINGS_SHEET && window.App) App.openSettings();
  }
  function request() { if (desired) showSettingsPermission(); }
  function initialize() {
    if (typeof pwaCourseActor !== "function") return;
    pwaCourseActor().then(function (session) {
      var id = Number(session.user_id);
      if (!Number.isSafeInteger(id) || id <= 0) return;
      if (owner && owner !== id) { stopListening(); snapshot = null; epoch++; }
      owner = id;
      readPreference();
      if (!seen) {
        var attempts = 0;
        var promptWhenIdle = function () {
          if (!owner || seen || document.visibilityState === "hidden") return;
          if (attempts++ < 12 &&
              (document.querySelector("#sheet.on, #tour.on, #hsk-pwa-notice-root:not([hidden]), #hsk-pwa-feedback-root:not([hidden])"))) {
            setTimeout(promptWhenIdle,1000); return;
          }
          introduction();
        };
        setTimeout(promptWhenIdle,2200);
      }
      // OS permission cannot be inferred from stored settings. On next
      // browser session, the learner may need to re-enable explicitly.
      restartListening();
    }).catch(function () { stopListening(); });
  }
  window.HskPwaShake = {
    settingsRowHtml: settingsRowHtml, toggle: toggle, request: request,
    isListening: function () { return listening; }
  };
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") {
      stopListening(); epoch++; snapshot = null;
    } else {
      // Do not assume same account after background / OAuth transitions.
      pwaCourseActor().then(function (session) {
        if (owner && Number(session.user_id) !== owner) {
          stopListening(); epoch++; snapshot = null;
          location.replace("/iphone-pwa");
        } else restartListening();
      }).catch(function () { stopListening(); });
    }
  });
  window.addEventListener("load", initialize, {once:true});
}());
