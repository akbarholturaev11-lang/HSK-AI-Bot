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
      '<div class="hsk-pwa-push-view" id="hsk-pwa-push-view" hidden>' +
        '<p id="hsk-pwa-push-status" role="status" aria-live="polite"></p>' +
        '<p id="hsk-pwa-push-body"></p>' +
        '<button type="button" id="hsk-pwa-push-action"></button></div>' +
      '<div class="hsk-pwa-notice-list" id="hsk-pwa-notice-list"></div>' +
      '<div class="hsk-pwa-notice-urgent" hidden>' +
        '<div class="hsk-pwa-notice-icon" aria-hidden="true"><i class="ti ti-credit-card-off"></i></div>' +
        '<h2 id="hsk-pwa-urgent-title"></h2>' +
        '<button type="button" class="hsk-pwa-notice-primary" data-pwa-retry></button>' +
        '<button type="button" class="hsk-pwa-notice-secondary" data-pwa-close></button>' +
      '</div>' +
    '</section>';
  document.body.appendChild(overlay);
  overlay.querySelector(".hsk-pwa-close").setAttribute(
    "aria-label", commonMessage("action.close", "Close")
  );

  var panel = overlay.querySelector('[role="dialog"]');
  var list = overlay.querySelector("#hsk-pwa-notice-list");
  var heading = overlay.querySelector("#hsk-pwa-notice-title");
  var urgent = overlay.querySelector(".hsk-pwa-notice-urgent");
  var pushControl = overlay.querySelector("#hsk-pwa-push-view");
  var pushStatus = overlay.querySelector("#hsk-pwa-push-status");
  var pushBody = overlay.querySelector("#hsk-pwa-push-body");
  var pushButton = overlay.querySelector("#hsk-pwa-push-action");
  var activeMode = null;
  var owner = null;
  var latestData = null;
  var lastFocus = null;
  var inMemoryDismissals = new Set();
  var fetchInFlight = {};
  var urgentPending = null;
  var interruptRetries = 0;
  var checkGeneration = 0;
  var lastResumeCheck = 0;
  var displayedPaymentId = null;
  var pushState = null;
  var pushBusy = false;
  var pushRegistrationPromise = null;

  // These strings are already authored in the shared UZ/RU/TJ catalogs.
  // Do not create a second per-page translation dictionary.
  function courseLabel(key) { return courseMessage(key, ""); }
  function commonLabel(key) { return commonMessage(key, ""); }
  function labels() {
    return {
      title: commonLabel("desktopA11y.notifications"),
      back: commonLabel("action.back"),
      close: courseLabel("subscriptionPage.close") || commonLabel("action.close"),
      loading: courseLabel("subscriptionPage.loading"),
      error: courseLabel("subscriptionPage.error"),
      empty: courseLabel("pwaInbox.empty"),
      rejected: courseLabel("subscriptionPage.proRejectedTitle"),
      hsk30Rejected: courseLabel("subscriptionPage.paymentRejectedTitle"),
      approved: courseLabel("subscriptionPage.proApprovedTitle"),
      hsk30Approved: courseLabel("subscriptionPage.paymentApprovedTitle"),
      retry: courseLabel("subscriptionPage.retryPayment"),
      pushEnable: courseLabel("pwaPush.enable"),
      pushDisable: courseLabel("pwaPush.disable"),
      pushTitle: courseLabel("pwaPush.title"),
      pushBody: courseLabel("pwaPush.promptBody"),
      pushOff: courseLabel("pwaPush.off"),
      pushInstallRequired: courseLabel("pwaPush.installRequired"),
      pushEnabled: courseLabel("pwaPush.enabled"),
      pushBlocked: courseLabel("pwaPush.blocked"),
      pushError: courseLabel("pwaPush.error")
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
  function openCheckout(pay) {
    var url = "/iphone-pwa/checkout?lang=" + encodeURIComponent(LANG);
    if (pay && pay.plan_type === "hsk30_unlock") url += "&mode=hsk30_unlock&plan=hsk30_unlock";
    else if (pay && ["10_days","1_month","3_months"].includes(pay.plan_type))
      url += "&plan=" + encodeURIComponent(pay.plan_type);
    close();
    if (window.App && typeof App.openPwaCheckout === "function") {
      App.openPwaCheckout(new URL(url, location.href).searchParams);
    } else {
      location.assign(url);
    }
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
    ++checkGeneration;
    overlay.hidden = true;
    activeMode = null;
    displayedPaymentId = null;
    if (lastFocus && lastFocus.isConnected && typeof lastFocus.focus === "function") lastFocus.focus({preventScroll:true});
    if (window.NavBack) window.NavBack.sync();
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
    var isPush = mode === "push";
    overlay.className = isUrgent ? "" : "is-page";
    panel.setAttribute("aria-labelledby", isUrgent ? "hsk-pwa-urgent-title" : "hsk-pwa-notice-title");
    overlay.querySelector(".hsk-pwa-notice-head").hidden = isUrgent;
    list.hidden = isUrgent || isPush;
    pushControl.hidden = !isPush;
    urgent.hidden = !isUrgent;
    if (isUrgent) {
      overlay.querySelector("#hsk-pwa-urgent-title").textContent = rejectedTitle(latestData && latestData.account && latestData.account.payment_action);
      overlay.querySelector("[data-pwa-retry]").textContent = t.retry;
      urgent.querySelector("[data-pwa-close]").textContent = t.close;
    } else {
      heading.textContent = isPush ? t.pushTitle : t.title;
      var back = overlay.querySelector(".hsk-pwa-close");
      back.setAttribute("aria-label", t.back);
      back.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="m15 18-6-6 6-6"/></svg>';
    }
    panel.focus({preventScroll:true});
    if (window.NavBack) window.NavBack.sync();
  }
  function putMessage(title, body, action, paymentStatus, payment) {
    var isAction = action === "course" || action === "subscription" ||
      action === "rating" || action === "profile";
    var row = document.createElement(isAction ? "button" : "div");
    row.className = "hsk-pwa-notice-row";
    if (paymentStatus === "approved" || paymentStatus === "rejected") {
      row.className += " is-" + paymentStatus;
      row.setAttribute("data-payment-status", paymentStatus);
    }
    if (isAction) {
      row.type = "button";
      row.addEventListener("click", function () { navigate(action, payment); });
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
  function navigate(action, payment) {
    if (action === "subscription") {
      openCheckout(payment);
    } else if (action === "rating" || action === "profile" || action === "course") {
      close();
      if (window.App && typeof App.show === "function") App.show(action);
    }
  }
  function render() {
    var t = labels();
    if (activeMode === "push") {
      heading.textContent = t.pushTitle;
      pushBody.textContent = t.pushBody;
      paintPushControl();
      return;
    }
    if (activeMode !== "inbox") return;
    var scrollTop = list.scrollTop;
    list.replaceChildren();
    var course = latestData.course || {};
    var account = latestData.account || {};
    var rows = [];
    [course.notifications, account.notices].forEach(function (items) {
      (Array.isArray(items) ? items : []).slice(0, 20).forEach(function (item) {
        if (item && typeof item === "object") rows.push(item);
      });
    });
    var reviews = Array.isArray(account.payment_reviews) ? account.payment_reviews : [];
    var activePayment = account.payment_action;
    reviews.slice(0, 10).forEach(function (review) {
      if (!review || !["approved", "rejected"].includes(review.status)) return;
      var hsk30 = review.plan_type === "hsk30_unlock";
      var title = review.status === "rejected"
        ? (hsk30 ? t.hsk30Rejected : t.rejected)
        : (hsk30 ? t.hsk30Approved : t.approved);
      var retry = activePayment && activePayment.status === "rejected" &&
        Number(review.payment_id) === Number(activePayment.payment_id) ? activePayment : null;
      rows.push({title:title, action:retry ? "subscription" : review.status === "approved" ? "course" : "",
        payment:retry,
        paymentStatus:review.status, created_at:review.reviewed_at});
    });
    if (activePayment && activePayment.status === "rejected" &&
        !reviews.some(function (review) { return Number(review.payment_id) === Number(activePayment.payment_id); })) {
      rows.push({title:rejectedTitle(activePayment), action:"subscription",
        payment:activePayment, paymentStatus:"rejected", created_at:activePayment.reviewed_at});
    }
    rows.sort(function (a, b) {
      return (Date.parse(b.created_at) || 0) - (Date.parse(a.created_at) || 0);
    }).forEach(function (row) {
      putMessage(row.title, row.body, row.action, row.paymentStatus, row.payment);
    });
    if (!list.children.length) {
      var empty = document.createElement("p");
      empty.className = "hsk-pwa-notice-empty";
      empty.setAttribute("role", "status");
      empty.textContent = latestData.course === undefined || latestData.account === undefined
        ? t.loading : (latestData.course === null || latestData.account === null ? t.error : t.empty);
      list.appendChild(empty);
    }
    list.scrollTop = scrollTop || 0;
  }
  function fetchFeed(kind) {
    if (fetchInFlight[kind]) return fetchInFlight[kind];
    fetchInFlight[kind] = (async function () {
      var options = {credentials:"same-origin",cache:"no-store",redirect:"error"};
      if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function")
        options.signal = AbortSignal.timeout(6000);
      var actor = await pwaCourseActor();
      var verifiedOwner = actorId(actor);
      if (!verifiedOwner) throw new Error("pwa_owner_unavailable");
      if (owner && owner !== verifiedOwner) {
        close(); location.replace("/iphone-pwa"); throw new Error("pwa_actor_changed");
      }
      owner = verifiedOwner;
      var response = await fetch("/api/v3/pwa/" +
        (kind === "course" ? "notifications" : "account-notices"), options);
      if (!response.ok) throw new Error("pwa_notice_unavailable");
      var content = await response.json();
      if (!content || content.ok !== true) throw new Error("pwa_notice_invalid");
      // Revalidate the cookie after the feed returns. A slow feed cannot hold
      // up a second feed that already has a verified owner and response.
      var result = await fetch("/api/v3/pwa-auth/session", options);
      if (!result.ok && result.status !== 401 && result.status !== 403)
        throw new Error("pwa_session_unavailable");
      if (!result.ok || actorId(await result.json()) !== verifiedOwner) {
        latestData = null;
        close(); location.replace("/iphone-pwa"); throw new Error("pwa_actor_changed");
      }
      return content;
    }()).finally(function () { delete fetchInFlight[kind]; });
    return fetchInFlight[kind];
  }
  function isStandalonePwa() {
    return !!(window.navigator && window.navigator.standalone === true) ||
      !!(window.matchMedia && window.matchMedia("(display-mode: standalone)").matches);
  }
  function isAppleStandalonePwa() {
    // This sender is configured only for Apple's Web Push endpoint. Avoid
    // showing a broken opt-in on an installed Android/Chrome PWA.
    return isStandalonePwa() && !!window.navigator &&
      window.navigator.vendor === "Apple Computer, Inc.";
  }
  function pushSupported() {
    return isAppleStandalonePwa() && window.isSecureContext &&
      window.navigator && "serviceWorker" in window.navigator &&
      window.PushManager && window.Notification;
  }
  function updateSettingsPushStatus() {
    var node = document.getElementById("pwa-push-settings-status");
    if (!node) return;
    var t = labels();
    var value = !pushSupported() ? t.pushInstallRequired
      : !pushState || !pushState.enabled ? t.pushOff
        : Notification.permission === "denied" ? t.pushBlocked
          : pushState.subscribed ? t.pushEnabled : t.pushOff;
    node.textContent = value;
  }
  function paintPushControl() {
    var t = labels();
    var supported = pushSupported();
    var enabled = !!(pushState && pushState.enabled);
    var denied = supported && Notification.permission === "denied";
    var subscribed = !!(pushState && pushState.subscribed);
    pushControl.hidden = activeMode !== "push";
    pushStatus.textContent = !supported ? t.pushInstallRequired
      : !enabled ? t.pushOff : denied && !subscribed ? t.pushBlocked
        : subscribed ? t.pushEnabled : "";
    pushButton.hidden = !supported || !enabled || (denied && !subscribed);
    pushButton.disabled = pushBusy;
    pushButton.textContent = subscribed ? t.pushDisable : t.pushEnable;
    updateSettingsPushStatus();
  }
  async function preparePushRegistration() {
    if (!pushRegistrationPromise) {
      pushRegistrationPromise = (async function () {
        var registration = await navigator.serviceWorker.getRegistration("/iphone-pwa/");
        if (!registration) registration = await navigator.serviceWorker.register(
          "/iphone-pwa/sw.js", {scope:"/iphone-pwa/"}
        );
        await navigator.serviceWorker.ready;
        return registration;
      }()).catch(function (error) {
        pushRegistrationPromise = null;
        throw error;
      });
    }
    return pushRegistrationPromise;
  }
  async function refreshPushStatus() {
    if (!pushSupported()) {
      pushState = {enabled:false,subscribed:false,unsupported:true};
      paintPushControl();
      return;
    }
    var actor = await pwaCourseActor();
    var verifiedOwner = actorId(actor);
    if (!verifiedOwner || (owner && owner !== verifiedOwner)) {
      close(); location.replace("/iphone-pwa"); throw new Error("pwa_actor_changed");
    }
    owner = verifiedOwner;
    var response = await fetch("/api/v3/pwa/push/status", {
      credentials: "same-origin", cache: "no-store", redirect: "error"
    });
    var data = await response.json();
    if (!response.ok || !data || data.ok !== true || actorId(actor) !== actorId(data)) {
      throw new Error("pwa_push_status_unavailable");
    }
    pushState = data;
    paintPushControl();
    if (data.enabled && !data.subscribed && Notification.permission !== "denied")
      preparePushRegistration().catch(function () {});
  }
  function base64UrlBytes(value) {
    var padded = String(value || "").replace(/-/g, "+").replace(/_/g, "/");
    while (padded.length % 4) padded += "=";
    var raw = atob(padded), bytes = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
    return bytes;
  }
  async function pushRequest(url, method, body, actor) {
    var response = await fetch(url, {
      method: method, credentials: "same-origin", cache: "no-store", redirect: "error",
      headers: {"Content-Type": "application/json", "X-HSK-PWA-CSRF": actor.csrf},
      body: JSON.stringify(body || {})
    });
    var data = await response.json().catch(function () { return null; });
    if (!response.ok || !data || data.ok !== true) throw new Error("pwa_push_change_rejected");
    return data;
  }
  async function changePushSubscription() {
    if (pushBusy || !pushState) return;
    // iOS Safari requires the permission request to start in the trusted
    // button gesture; do this before any network/session await.
    var permissionPromise = !pushState.subscribed && Notification.permission === "default"
      ? Notification.requestPermission()
      : Promise.resolve(Notification.permission);
    pushBusy = true;
    paintPushControl();
    var failed = false;
    try {
      var actor = await pwaCourseActor();
      if (actorId(actor) !== owner) throw new Error("pwa_actor_changed");
      if (pushState.subscribed) {
        await pushRequest("/api/v3/pwa/push/revoke", "POST",
          {subscription_id: pushState.subscription_id}, actor);
        var currentRegistration = await navigator.serviceWorker.getRegistration("/iphone-pwa/");
        if (currentRegistration && currentRegistration.pushManager) {
          var currentSubscription = await currentRegistration.pushManager.getSubscription();
          if (currentSubscription) {
            try { await currentSubscription.unsubscribe(); }
            catch (_) { /* Server revocation is authoritative if local cleanup fails. */ }
          }
        }
      } else {
        var permission = await permissionPromise;
        if (permission !== "granted") {
          paintPushControl();
          return;
        }
        var registration = await preparePushRegistration();
        var subscription = await registration.pushManager.getSubscription();
        if (!subscription) {
          subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: base64UrlBytes(pushState.public_key)
          });
        }
        await pushRequest("/api/v3/pwa/push/subscribe", "POST", subscription.toJSON(), actor);
      }
      await refreshPushStatus();
    } catch (_) {
      failed = true;
    } finally {
      pushBusy = false;
      if (activeMode === "push") {
        render();
        if (failed) pushStatus.textContent = labels().pushError;
      } else {
        updateSettingsPushStatus();
      }
    }
  }
  async function openPushSettings() {
    urgentPending = null;
    ++checkGeneration;
    openMode("push");
    render();
    try { await refreshPushStatus(); }
    catch (_) { if (activeMode === "push") pushStatus.textContent = labels().pushError; }
  }
  async function open(fromPush) {
    urgentPending = null;
    var check = ++checkGeneration;
    latestData = {};
    openMode("inbox");
    render();
    await Promise.all(["course", "account"].map(async function (kind) {
      var result = await fetchFeed(kind).catch(function () { return null; });
      if (check !== checkGeneration) return;
      latestData[kind] = result;
      if (activeMode === "inbox") render();
      var action = kind === "account" && result && result.payment_action;
      if (fromPush && activeMode === "inbox" && action && action.status === "rejected" &&
          owner && !wasDismissed(action.payment_id)) openMode("urgent");
    }));
  }
  function canInterrupt() {
    if (document.visibilityState === "hidden" || !overlay.hidden) return false;
    // Never obscure lessons, other sheets, onboarding or browser restores.
    if (document.querySelector("#flow.on,#sheet.on,#paywall.on,#secov.on,#resourceov.on,#tour.on,#upov.on,#writeov.on,#levelup.on,#s-settings.on,#pwa-checkout-layer,#pwa-practice-layer:not([hidden]),#hsk-pwa-feedback-root:not([hidden])")) return false;
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
    if (document.visibilityState === "hidden" || activeMode === "inbox" || activeMode === "push" ||
        document.querySelector("#hsk-pwa-feedback-root:not([hidden])")) return;
    var check = ++checkGeneration;
    urgentPending = null;
    interruptRetries = 0;
    try {
      var account = await fetchFeed("account");
      if (check !== checkGeneration) return;
      latestData = {account:account};
      var action = account.payment_action;
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
    if (ev.target.closest("#hsk-pwa-push-action")) changePushSubscription();
    if (ev.target.closest("[data-pwa-retry]")) {
      openCheckout(latestData && latestData.account && latestData.account.payment_action);
    }
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
  window.HskPwaInbox = {open:open,close:close,openPushSettings:openPushSettings,
    back:close,backTarget:function () { return overlay.hidden ? null : panel; },
    refreshPushStatus:refreshPushStatus,updateSettingsPushStatus:updateSettingsPushStatus};
  // Only the latest actionable rejected receipt may interrupt, once per
  // verified owner + payment. Ordinary/new-content notices never pop up.
  window.addEventListener("load", function () {
    var pushRoute = false;
    try {
      var pushUrl = new URL(location.href);
      pushRoute = pushUrl.searchParams.get("notice") === "1";
      if (pushRoute) {
        pushUrl.searchParams.delete("notice");
        history.replaceState(history.state, "", pushUrl.pathname + pushUrl.search + pushUrl.hash);
      }
    } catch (_) { /* Keep normal course startup on malformed legacy URLs. */ }
    window.setTimeout(function () {
      // Browsers ignore the callback result, while deterministic harnesses
      // can await the scheduled refresh instead of racing its network reads.
      if (pushRoute) return open(true);
      return scheduleRecheck(true);
    }, 1900);
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
