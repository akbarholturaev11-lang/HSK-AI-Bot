/* iPhone standalone PWA only. Android behavior port; no Telegram Mini App hooks.
 * Permission is always requested from a user click (iOS transient activation).
 * Capture is local-only until the learner explicitly sends a report.
 */
(function () {
  "use strict";
  var onCourse = location.pathname === "/iphone-pwa/course";
  if (!onCourse && !/^\/iphone-pwa\/(?:checkout|practice\/(?:recognition|pronunciation|memorize|test|mistakes))$/.test(location.pathname)) return;
  // Only the top-level PWA owns the sensor. Embedded practice/checkout frames
  // would otherwise open a second report sheet for the same shake.
  if (window.parent !== window || window.HskPwaShake) return;
  var standalone = !!(navigator.standalone ||
    (window.matchMedia && matchMedia("(display-mode: standalone)").matches));
  if (!standalone) return;
  // Every independent practice/checkout HTML document needs the dialog skin.
  if (!document.querySelector('link[href*="iphone-pwa-shake-report.css"]')) {
    var reportCss = document.createElement("link");
    reportCss.rel = "stylesheet";
    reportCss.href = "/course_v3_data/iphone-pwa-shake-report.css?v=20261105-c97d140b3930";
    document.head.appendChild(reportCss);
  }

  var owner = null, desired = false, permitted = false, previouslyGranted = false;
  var motionError = "", manualImageSelected = false, capturePending = false;
  var permissionPending = false, listening = false, busy = false, epoch = 0;
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
  function l(key) {
    if (typeof courseMessage === "function") return courseMessage("pwaShake." + key, "");
    var lang = typeof LANG === "string" ? LANG : (new URLSearchParams(location.search).get("lang") || "ru");
    var catalog = (window.HSKAI_COURSE_I18N || {})[lang] || {};
    return catalog["pwaShake." + key] || "";
  }
  function c(key) {
    if (typeof courseMessage === "function") return courseMessage(key, "");
    var lang = typeof LANG === "string" ? LANG : (new URLSearchParams(location.search).get("lang") || "ru");
    return ((window.HSKAI_COURSE_I18N || {})[lang] || {})[key] || "";
  }
  function verifiedActor() {
    if (onCourse && typeof pwaCourseActor === "function") return pwaCourseActor();
    return fetch("/api/v3/pwa-auth/session", {
      credentials:"same-origin", cache:"no-store", redirect:"error"
    }).then(function (res) {
      if (!res.ok) throw Error("pwa_session_required");
      return res.json();
    });
  }
  function storageKey() { return "hskai.pwa.shake.v1." + owner; }
  function readPreference() {
    try {
      var value = JSON.parse(localStorage.getItem(storageKey()) || "{}");
      // No unsolicited sensor prompts. Existing explicit ON choices are retained.
      desired = value.enabled === true;
      previouslyGranted = value.motionGranted === true;
    } catch (_) { desired = false; previouslyGranted = false; }
  }
  function savePreference() {
    if (!owner) return;
    try { localStorage.setItem(storageKey(), JSON.stringify({enabled:desired,motionGranted:previouslyGranted})); }
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
    dialog.setAttribute("data-stage", step);
    closeButton.textContent = "\u00d7";
    closeButton.setAttribute("aria-label", c("subscriptionPage.close") || "Close");
    closeButton.hidden = step === "sent";
    root.hidden = false;
    dialog.focus();
    if (onCourse && typeof NavBack !== "undefined" && NavBack.sync) NavBack.sync();
  }
  function close() {
    if (submitting) return;
    root.hidden = true;
    closeButton.hidden = false;
    stage = "";
    snapshot = null;
    capturePending = false;
    reportDescription = "";
    manualImageSelected = false;
    busy = false;
    epoch += 1;
    if (lastFocus && lastFocus.isConnected && lastFocus.focus) lastFocus.focus();
    restartListening();
    if (onCourse && typeof NavBack !== "undefined" && NavBack.sync) NavBack.sync();
  }
  var closeButton = root.querySelector("#hsk-shake-close");
  closeButton.addEventListener("click", close);
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

  function refreshSettingsControl() {
    // Settings is a dedicated screen in the installed PWA, not the old modal.
    if (typeof SCREEN !== "undefined" && SCREEN === "settings" &&
        typeof renderPwaSettings === "function") renderPwaSettings();
    else if (typeof refreshSettingsRows === "function") refreshSettingsRows();
  }
  function permissionFailed(message) {
    permissionPending = false;
    desired = false;
    permitted = false;
    motionError = message;
    stopListening();
    savePreference();
    refreshSettingsControl();
  }
  function permissionClick() {
    if (permissionPending) return;
    permissionPending = true;
    // iOS requires the request in this exact user-click stack: no preliminary modal.
    var request;
    try {
      if (!window.DeviceMotionEvent) throw Error("unsupported");
      request = typeof DeviceMotionEvent.requestPermission === "function" ?
        DeviceMotionEvent.requestPermission() : Promise.resolve("granted");
    } catch (_) {
      permissionFailed(l("unavailable"));
      return;
    }
    Promise.resolve(request).then(function (result) {
      if (result !== "granted") { permissionFailed(l("denied")); return; }
      permissionPending = false;
      desired = true;
      permitted = true;
      previouslyGranted = true;
      motionError = "";
      savePreference();
      restartListening();
      refreshSettingsControl();
      // Best-effort render warm-up; no screenshot is sent without Submit.
      loadRenderer().catch(function () {});
    }).catch(function () { permissionFailed(l("denied")); });
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
    if (location.pathname === "/iphone-pwa/checkout" ||
        ["profile", "voice"].indexOf(typeof SCREEN === "string" ? SCREEN : "") >= 0 ||
        // Checkout is embedded inside /iphone-pwa/course in the installed PWA:
        // never capture its invoice, receipt, payment card or embedded frame.
        document.querySelector("#pwa-checkout-layer, #sheet.on .pwa-payment, #sheet.on [class*=receipt], #sheet.on [class*=checkout]")) return null;
    var renderer = await loadRenderer();
    // A slow renderer download must not allow a later navigation into checkout
    // or account screens to be captured after the first privacy check.
    if (location.pathname === "/iphone-pwa/checkout" ||
        ["profile","voice"].indexOf(typeof SCREEN === "string" ? SCREEN : "") >= 0 ||
        document.querySelector("#pwa-checkout-layer, #sheet.on .pwa-payment, #sheet.on [class*=receipt], #sheet.on [class*=checkout]")) return null;
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
    if (busy || !root.hidden || !owner) return;
    busy = true;
    stopListening();
    var generation = ++epoch;
    reportScreen = typeof SCREEN === "string" ? SCREEN.slice(0,80) :
      location.pathname.replace("/iphone-pwa/","").slice(0,80);
    reportDescription = "";
    snapshot = null;
    manualImageSelected = false;
    capturePending = true;
    // A shake opens the final form immediately: no introduction or confirm page.
    formReport();
    captureViewport().catch(function () { return null; }).then(function (image) {
      if (generation !== epoch || !owner || stage !== "form") return;
      capturePending = false;
      if (manualImageSelected) return;
      snapshot = image;
      var oldPreview = body.querySelector(".hsk-shake-preview");
      if (oldPreview) oldPreview.replaceWith(imagePreview());
    });
  }
  function imagePreview() {
    var wrap = document.createElement("div");
    wrap.className = "hsk-shake-preview";
    if (snapshot) {
      // Android parity: label + switch row, preview, then the privacy note.
      var label = document.createElement("label");
      label.className = "hsk-shake-switch-row";
      label.appendChild(document.createTextNode(l("screenshot")));
      var check = document.createElement("input");
      check.type = "checkbox";
      check.checked = true;
      check.id = "hsk-shake-attach";
      check.className = "hsk-shake-switch";
      check.setAttribute("role", "switch");
      label.appendChild(check);
      wrap.appendChild(label);
      var img = document.createElement("img");
      img.src = snapshot;
      img.alt = l("screenshot");
      wrap.appendChild(img);
      var privacy = document.createElement("p");
      privacy.className = "hsk-shake-privacy";
      privacy.textContent = l("privacy");
      wrap.appendChild(privacy);
      check.addEventListener("change", function () {
        img.hidden = !check.checked;
        privacy.hidden = !check.checked;
      });
    } else if (!capturePending) {
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
      manualImageSelected = true;
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
          if (!snapshot) { manualImageSelected = false; showMessage(l("imageTooLarge")); }
          else { showMessage(""); formReport(); }
        } catch (_) { manualImageSelected = false; showMessage(l("captureUnavailable")); }
        URL.revokeObjectURL(url);
      };
      image.onerror = function () { manualImageSelected = false; URL.revokeObjectURL(url); showMessage(l("captureUnavailable")); };
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
    var counter = document.createElement("small");
    counter.className = "hsk-shake-count";
    counter.textContent = reportDescription.length + " / 2000";
    textarea.addEventListener("input", function () {
      reportDescription = textarea.value;
      counter.textContent = textarea.value.length + " / 2000";
    });
    label.appendChild(textarea);
    body.appendChild(label);
    body.appendChild(counter);
    body.appendChild(imagePreview());
    makeButton("send", submit);
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

  function escapeLabel(value) {
    return String(value || "").replace(/[&<>"']/g, function (character) {
      return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[character];
    });
  }
  function settingsRowHtml() {
    if (!owner) return "";
    var active = desired && permitted;
    var error = motionError ?
      '<small class="hsk-shake-setting-error">' + escapeLabel(motionError) + '</small>' : "";
    return '<button type="button" class="srow hsk-shake-setting" role="switch" aria-checked="' +
      (active ? "true" : "false") + '" onclick="HskPwaShake.toggle()">' +
      '<i class="ti ti-device-mobile-vibration" aria-hidden="true"></i>' +
      '<span class="hsk-shake-setting-text">' + escapeLabel(l("setting")) + error + '</span>' +
      '<span class="toggle' + (active ? ' on' : '') + '" aria-hidden="true"></span></button>';
  }
  function toggle() {
    if (permissionPending) return;
    if (desired && permitted) {
      desired = false;
      permitted = false;
      motionError = "";
      stopListening();
      savePreference();
      refreshSettingsControl();
    } else {
      // Single switch tap requests OS permission when needed; no second dialog.
      permissionClick();
    }
  }
  function initialize() {
    verifiedActor().then(function (session) {
      var id = Number(session.user_id);
      if (!Number.isSafeInteger(id) || id <= 0) return;
      if (owner && owner !== id) { stopListening(); snapshot = null; epoch++; }
      owner = id;
      readPreference();
      // OS permission cannot be inferred from stored settings. On next
      // browser session, the learner may need to re-enable explicitly.
      if (previouslyGranted && !permitted && desired) {
        // A new HTML document can reuse only a browser-remembered OS grant.
        // Observe delivered events; never call requestPermission without a tap.
        var probe = function (event) {
          if (!event.accelerationIncludingGravity || !Number.isFinite(event.accelerationIncludingGravity.x)) return;
          window.removeEventListener("devicemotion", probe);
          permitted = true;
          restartListening();
          refreshSettingsControl();
        };
        window.addEventListener("devicemotion", probe, {passive:true});
      }
      restartListening();
      refreshSettingsControl();
    }).catch(function () { stopListening(); });
  }
  window.HskPwaShake = {
    settingsRowHtml: settingsRowHtml, toggle: toggle,
    manual: startReport,
    backTarget: function () { return root.hidden ? null : root; },
    close: close,
    isListening: function () { return listening; }
  };
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") {
      stopListening(); epoch++; snapshot = null;
    } else {
      // Do not assume same account after background / OAuth transitions.
      verifiedActor().then(function (session) {
        if (owner && Number(session.user_id) !== owner) {
          stopListening(); epoch++; snapshot = null;
          location.replace("/iphone-pwa");
        } else restartListening();
      }).catch(function () { stopListening(); });
    }
  });
  window.addEventListener("load", initialize, {once:true});
}());
