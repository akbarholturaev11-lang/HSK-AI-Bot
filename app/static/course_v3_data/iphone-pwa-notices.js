/* Existing iPhone PWA course enhancement: read-only inbox and latest rejected
   checkout action. Server remains the only account, payment and notice authority.
   No Telegram initData, synthetic rewards, push acknowledgments or local tokens. */
(function () {
  "use strict";
  if (location.pathname !== "/iphone-pwa/course") return;

  var overlay = document.createElement("div");
  overlay.id = "hsk-pwa-notice-root";
  overlay.hidden = true;
  overlay.innerHTML =
    '<div class="hsk-pwa-notice-scrim" data-pwa-close></div>' +
    '<section class="hsk-pwa-notice-card" role="dialog" aria-modal="true" aria-labelledby="hsk-pwa-notice-title" tabindex="-1">' +
      '<div class="hsk-pwa-notice-head"><h2 id="hsk-pwa-notice-title"></h2>' +
        '<button type="button" class="hsk-pwa-close" data-pwa-close aria-label="Close">×</button></div>' +
      '<div class="hsk-pwa-notice-tabs" role="tablist">' +
      '<button type="button" id="hsk-pwa-tab-course" role="tab" data-pwa-tab="course" aria-controls="hsk-pwa-notice-list"></button>' +
      '<button type="button" id="hsk-pwa-tab-account" role="tab" data-pwa-tab="account" aria-controls="hsk-pwa-notice-list"></button></div>' +
      '<div class="hsk-pwa-notice-list" id="hsk-pwa-notice-list" role="tabpanel" tabindex="0"></div>' +
      '<div class="hsk-pwa-notice-urgent" hidden>' +
        '<div class="hsk-pwa-notice-icon" aria-hidden="true"><i class="ti ti-credit-card-off"></i></div>' +
        '<h2 id="hsk-pwa-urgent-title"></h2>' +
        '<button type="button" class="hsk-pwa-notice-primary" data-pwa-retry></button>' +
        '<button type="button" class="hsk-pwa-notice-secondary" data-pwa-close></button>' +
      '</div>' +
    '</section>';
  document.body.appendChild(overlay);

  var panel = overlay.querySelector('[role="dialog"]');
  var list = overlay.querySelector("#hsk-pwa-notice-list");
  var tabs = overlay.querySelector(".hsk-pwa-notice-tabs");
  var heading = overlay.querySelector("#hsk-pwa-notice-title");
  var urgent = overlay.querySelector(".hsk-pwa-notice-urgent");
  var activeTab = "course";
  var activeMode = null;
  var owner = null;
  var latestData = null;
  var lastFocus = null;
  var inMemoryDismissals = new Set();
  var fetchInFlight = null;
  var urgentPending = null;
  var interruptRetries = 0;
  var checkGeneration = 0;
  var lastResumeCheck = 0;
  var displayedPaymentId = null;

  // These strings are already authored in the shared UZ/RU/TJ catalogs.
  // Do not create a second per-page translation dictionary.
  function courseLabel(key) { return courseMessage(key, ""); }
  function commonLabel(key) { return commonMessage(key, ""); }
  function labels() {
    return {
      title: commonLabel("desktopA11y.notifications"),
      course: courseLabel("nav.course"),
      account: courseLabel("nav.profile"),
      close: courseLabel("subscriptionPage.close") || commonLabel("action.close"),
      loading: courseLabel("subscriptionPage.loading"),
      error: courseLabel("subscriptionPage.error"),
      rejected: courseLabel("subscriptionPage.proRejectedTitle"),
      hsk30Rejected: courseLabel("subscriptionPage.paymentRejectedTitle"),
      retry: courseLabel("subscriptionPage.retryPayment")
    };
  }
  function actorId(data) {
    var id = Number(data && data.user_id);
    return Number.isSafeInteger(id) && id > 0 ? id : null;
  }
  function dismissedKey(paymentId) {
    return "hskai:pwa:rejected:" + owner + ":" + paymentId;
  }
  function wasDismissed(paymentId) {
    var key = dismissedKey(paymentId);
    if (inMemoryDismissals.has(key)) return true;
    try { return localStorage.getItem(key) === "1"; } catch (_) { return false; }
  }
  function rejectedTitle(payment) {
    var t = labels();
    return payment && payment.plan_type === "hsk30_unlock" ? t.hsk30Rejected : t.rejected;
  }
  function checkoutPath() {
    var pay = latestData && latestData.account && latestData.account.payment_action;
    var url = "/iphone-pwa/checkout?lang=" + encodeURIComponent(LANG);
    if (!pay) return url;
    if (pay.plan_type === "hsk30_unlock") return url + "&mode=hsk30_unlock&plan=hsk30_unlock";
    // Return to the original plan selector, keeping the learner's last choice
    // without trusting arbitrary unvalidated query strings.
    return ["10_days","1_month","3_months"].includes(pay.plan_type)
      ? url + "&plan=" + encodeURIComponent(pay.plan_type) : url;
  }
  function markDismissed() {
    // Freeze the exact receipt the user actually saw. An async refresh may
    // replace latestData with a newer receipt while this dialog remains open.
    if (activeMode !== "urgent" || !displayedPaymentId || !owner) return;
    var key = dismissedKey(displayedPaymentId);
    inMemoryDismissals.add(key);
    try { localStorage.setItem(key, "1"); } catch (_) { /* Safari private mode */ }
  }

  function close() {
    if (overlay.hidden) return;
    markDismissed();
    overlay.hidden = true;
    activeMode = null;
    displayedPaymentId = null;
    if (lastFocus && lastFocus.isConnected && typeof lastFocus.focus === "function") lastFocus.focus();
  }
  function openMode(mode) {
    if (overlay.hidden) lastFocus = document.activeElement;
    activeMode = mode;
    displayedPaymentId = mode === "urgent" && latestData && latestData.account &&
      latestData.account.payment_action
      ? latestData.account.payment_action.payment_id : null;
    overlay.hidden = false;
    var t = labels();
    var isUrgent = mode === "urgent";
    panel.setAttribute("aria-labelledby", isUrgent ? "hsk-pwa-urgent-title" : "hsk-pwa-notice-title");
    overlay.querySelector(".hsk-pwa-notice-head").hidden = isUrgent;
    tabs.hidden = isUrgent;
    list.hidden = isUrgent;
    urgent.hidden = !isUrgent;
    if (isUrgent) {
      overlay.querySelector("#hsk-pwa-urgent-title").textContent = rejectedTitle(latestData && latestData.account && latestData.account.payment_action);
      overlay.querySelector("[data-pwa-retry]").textContent = t.retry;
      urgent.querySelector("[data-pwa-close]").textContent = t.close;
    } else {
      heading.textContent = t.title;
      overlay.querySelector(".hsk-pwa-close").setAttribute("aria-label", t.close);
    }
    panel.focus();
  }
  function putMessage(title, body, action) {
    var isAction = action === "course" || action === "subscription" ||
      action === "rating" || action === "profile";
    var row = document.createElement(isAction ? "button" : "div");
    row.className = "hsk-pwa-notice-row";
    if (isAction) {
      row.type = "button";
      row.addEventListener("click", function () { navigate(action); });
    }
    var strong = document.createElement("strong");
    strong.textContent = String(title || "").slice(0, 160);
    row.appendChild(strong);
    if (body && body !== title) {
      var small = document.createElement("small");
      small.textContent = String(body).slice(0, 420);
      row.appendChild(small);
    }
    list.appendChild(row);
  }
  function navigate(action) {
    close();
    if (action === "subscription") {
      location.assign(checkoutPath());
    } else if (action === "rating" || action === "profile" || action === "course") {
      if (window.App && typeof App.show === "function") App.show(action);
    }
  }
  function render() {
    var t = labels();
    overlay.querySelector("#hsk-pwa-tab-course").textContent = t.course;
    overlay.querySelector("#hsk-pwa-tab-account").textContent = t.account;
    ["course", "account"].forEach(function (kind) {
      var tab = overlay.querySelector('[data-pwa-tab="' + kind + '"]');
      tab.setAttribute("aria-selected", String(activeTab === kind));
      tab.tabIndex = activeTab === kind ? 0 : -1;
    });
    list.setAttribute("aria-labelledby", activeTab === "account"
      ? "hsk-pwa-tab-account" : "hsk-pwa-tab-course");
    list.replaceChildren();
    if (!latestData) {
      var loading = document.createElement("p");
      loading.className = "hsk-pwa-notice-empty";
      loading.textContent = t.loading;
      list.appendChild(loading);
      return;
    }
    if (latestData.error) {
      putMessage(t.error, "", "");
      return;
    }
    var items = activeTab === "course"
      ? latestData.course.notifications : latestData.account.notices;
    if (activeTab === "account" && latestData.account.payment_action &&
        latestData.account.payment_action.status === "rejected") {
      putMessage(rejectedTitle(latestData.account.payment_action), "", "subscription");
    }
    (Array.isArray(items) ? items : []).slice(0, 20).forEach(function (item) {
      if (item && typeof item === "object") putMessage(item.title, item.body, item.action);
    });
    if (!list.children.length) {
      var empty = document.createElement("p");
      empty.className = "hsk-pwa-notice-empty";
      empty.textContent = "—";
      list.appendChild(empty);
    }
  }
  async function fetchData() {
    if (fetchInFlight) return fetchInFlight;
    fetchInFlight = (async function () {
      var actor = await pwaCourseActor();
      var verifiedOwner = actorId(actor);
      if (!verifiedOwner) throw new Error("pwa_owner_unavailable");
      if (owner && owner !== verifiedOwner) {
        close(); location.replace("/iphone-pwa"); throw new Error("pwa_actor_changed");
      }
      owner = verifiedOwner;
      var responses = await Promise.all([
        fetch("/api/v3/pwa/notifications", {credentials:"same-origin",cache:"no-store",redirect:"error"}),
        fetch("/api/v3/pwa/account-notices", {credentials:"same-origin",cache:"no-store",redirect:"error"})
      ]);
      if (responses.some(function (response) { return !response.ok; })) throw new Error("pwa_notice_unavailable");
      var content = await Promise.all(responses.map(function (response) { return response.json(); }));
      if (content.some(function (entry) { return !entry || entry.ok !== true; })) throw new Error("pwa_notice_invalid");
      // Actor may have changed during async fetch (logout or account switch).
      var refreshed = await fetch("/api/v3/pwa-auth/session", {credentials:"same-origin",cache:"no-store",redirect:"error"});
      if (!refreshed.ok || actorId(await refreshed.json()) !== owner) {
        close(); location.replace("/iphone-pwa"); throw new Error("pwa_actor_changed");
      }
      latestData = {course:content[0],account:content[1]};
      return latestData;
    }()).finally(function () { fetchInFlight = null; });
    return fetchInFlight;
  }
  async function open() {
    // If the learner intentionally opens the inbox, never reopen its alert
    // immediately after the inbox is closed.
    urgentPending = null;
    ++checkGeneration;
    activeTab = "course";
    latestData = null;
    openMode("inbox");
    render();
    try { await fetchData(); render(); }
    catch (_) {
      if (overlay.hidden) return;
      latestData = {error:true}; render();
    }
  }
  function canInterrupt() {
    if (document.visibilityState === "hidden" || !overlay.hidden) return false;
    // Never obscure lessons, other sheets, onboarding or browser restores.
    if (document.querySelector("#flow.on,#sheet.on,#paywall.on,#secov.on,#tour.on,#upov.on,#writeov.on,#levelup.on,#hsk-pwa-feedback-root:not([hidden])")) return false;
    // A payment alert must never steal the iOS keyboard or a learner's input focus.
    if (document.activeElement && typeof document.activeElement.matches === "function" &&
        document.activeElement.matches('input,textarea,select,[contenteditable="true"]')) return false;
    var splash = document.getElementById("hsk-launch-splash");
    if (splash && !splash.classList.contains("is-done")) return false;
    return true;
  }
  function presentPendingRejection() {
    var action = urgentPending;
    if (!action || !owner || wasDismissed(action.payment_id)) {
      urgentPending = null;
      return;
    }
    if (canInterrupt()) {
      urgentPending = null;
      openMode("urgent");
      return;
    }
    // Splash may outlast the initial delay on slower iPhones. Retry only
    // the visual check: never refetch data, poll a provider or interrupt a
    // lesson. The inbox remains accessible even if this window is missed.
    if (interruptRetries++ < 12) {
      window.setTimeout(presentPendingRejection, 1200);
    } else {
      urgentPending = null;
    }
  }
  async function offerLatestRejection() {
    // Browsing notices is an intentional user action, never interrupt it or
    // queue a surprise payment modal when the learner closes this inbox.
    if (document.visibilityState === "hidden" || activeMode === "inbox" ||
        document.querySelector("#hsk-pwa-feedback-root:not([hidden])")) return;
    var check = ++checkGeneration;
    urgentPending = null;
    interruptRetries = 0;
    try {
      var data = await fetchData();
      if (check !== checkGeneration) return;
      var action = data.account && data.account.payment_action;
      // If a newer pending/approved receipt supersedes the reviewed rejection,
      // do not leave a stale payment dialog on screen after Safari resumes.
      if (activeMode === "urgent" && (!action || action.payment_id !== displayedPaymentId ||
          action.status !== "rejected")) {
        close();
      }
      if (activeMode === "urgent" && action &&
          action.status === "rejected" && action.payment_id === displayedPaymentId) return;
      if (action && action.status === "rejected" && owner &&
          !wasDismissed(action.payment_id)) {
        urgentPending = action;
        presentPendingRejection();
      }
    } catch (_) { /* Read failure must not block course. */ }
  }
  function scheduleRecheck(force) {
    if (document.visibilityState === "hidden") return Promise.resolve();
    var now = Date.now();
    if (!force && now - lastResumeCheck < 3000) return Promise.resolve();
    lastResumeCheck = now;
    return offerLatestRejection();
  }
  overlay.addEventListener("click", function (ev) {
    if (ev.target.closest("[data-pwa-close]")) close();
    var tab = ev.target.closest("[data-pwa-tab]");
    if (tab && activeMode === "inbox") {
      activeTab = tab.dataset.pwaTab === "account" ? "account" : "course";
      render();
    }
    if (ev.target.closest("[data-pwa-retry]")) {
      markDismissed();
      location.assign(checkoutPath());
    }
  });
  tabs.addEventListener("keydown", function (ev) {
    if (["ArrowLeft", "ArrowRight", "Home", "End"].indexOf(ev.key) < 0) return;
    var order = ["course", "account"];
    var current = ev.target.closest("[data-pwa-tab]");
    var selected = current ? current.dataset.pwaTab : activeTab;
    var index = Math.max(0, order.indexOf(selected));
    if (ev.key === "Home") index = 0;
    else if (ev.key === "End") index = order.length - 1;
    else if (ev.key === "ArrowRight") index = (index + 1) % order.length;
    else index = (index + order.length - 1) % order.length;
    ev.preventDefault();
    activeTab = order[index];
    render();
    overlay.querySelector('[data-pwa-tab="' + activeTab + '"]').focus();
  });
  document.addEventListener("keydown", function (ev) {
    if (overlay.hidden) return;
    if (ev.key === "Escape") { ev.preventDefault(); close(); return; }
    if (ev.key !== "Tab") return;
    var buttons = Array.from(panel.querySelectorAll("button:not([hidden]):not(:disabled)"))
      .filter(function (button) { return button.offsetParent !== null && button.tabIndex >= 0; });
    if (!buttons.length) { ev.preventDefault(); panel.focus(); return; }
    var first = buttons[0], last = buttons[buttons.length - 1];
    if (ev.shiftKey && (document.activeElement === first || document.activeElement === panel)) {
      ev.preventDefault(); last.focus();
    } else if (!ev.shiftKey && document.activeElement === last) {
      ev.preventDefault(); first.focus();
    }
  });
  window.HskPwaInbox = {open:open,close:close};
  // Only the latest actionable rejected receipt may interrupt, once per
  // verified owner + payment. Ordinary/new-content notices never pop up.
  window.addEventListener("load", function () {
    window.setTimeout(function () { return scheduleRecheck(true); }, 1900);
  }, {once:true});
  // Installed iOS Home Screen apps and Safari may resume from BFCache without
  // a new load event. Always re-read the latest *server-owned* payment action.
  window.addEventListener("pageshow", function (ev) {
    if (ev.persisted) return scheduleRecheck(true);
  });
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") return scheduleRecheck(false);
  });
}());
