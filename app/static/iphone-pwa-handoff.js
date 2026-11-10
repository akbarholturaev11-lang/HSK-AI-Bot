/* Telegram Mini App -> learner PWA handoff landing.
   The one-time secret arrives only in the URL fragment. It is removed from
   the address bar first, exchanged once over a same-origin POST for the
   normal HttpOnly session, and never stored. Identity, progress and Pro stay
   server-owned. Contract: docs/TELEGRAM_PWA_ANDROID_HANDOFF_CONTEXT.md */
(function () {
  "use strict";
  var fragment = "";
  try { fragment = String(window.location.hash || "").replace(/^#/, ""); } catch (_) {}
  // Before anything else: the secret must not survive in history, a reload,
  // a shared link or a screenshot of the address bar.
  try { window.history.replaceState(null, "", window.location.pathname); } catch (_) {}

  var values = {};
  fragment.split("&").forEach(function (part) {
    var at = part.indexOf("=");
    if (at > 0) values[part.slice(0, at)] = part.slice(at + 1);
  });
  var token = /^[A-Za-z0-9_-]{32,200}$/.test(values.t || "") ? values.t : "";
  var lang = ["uz", "ru", "tj"].indexOf(values.lang) >= 0 ? values.lang : "ru";

  var status = document.getElementById("status");
  var primary = document.getElementById("primary");
  var secondary = document.getElementById("secondary");
  var NETWORK_RETRIES = 2;

  function label(key) {
    var all = window.HSKAI_LI_I18N || {};
    var locale = all[lang] || all.ru || {};
    return locale[key] || (all.ru && all.ru[key]) || "";
  }
  function setLanguage(value) {
    if (["uz", "ru", "tj"].indexOf(value) >= 0) lang = value;
    document.documentElement.lang = lang === "tj" ? "tg" : lang;
  }
  function show(messageKey, busy, first, second) {
    status.textContent = label(messageKey);
    status.dataset.busy = busy ? "true" : "false";
    [[primary, first], [secondary, second]].forEach(function (pair) {
      var button = pair[0], action = pair[1];
      button.hidden = !action;
      button.onclick = null;
      if (!action) return;
      button.textContent = label(action[0]);
      button.onclick = action[1];
    });
    if (first) primary.focus();
  }
  function openCourse() { window.location.replace("/iphone-pwa/course"); }
  function openSignIn() { window.location.replace("/iphone-pwa?login=1&lang=" + lang); }
  function failed() {
    token = "";
    show("handoff.failed", false, ["handoff.signIn", openSignIn], null);
  }
  function json(path, options) {
    return fetch(path, Object.assign({ credentials: "same-origin", cache: "no-store" }, options))
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (data) {
          return { status: response.status, data: data || {} };
        });
      });
  }

  // Only a session the server confirms counts as signed in. The guide is the
  // existing one: shown once per learner on a browser that can still install.
  function continueSignedIn() {
    return json("/api/v3/pwa-auth/session").then(function (reply) {
      if (reply.status !== 200 || reply.data.ok !== true) return failed();
      setLanguage(reply.data.language);
      var guide = window.HSKAILiInstallGuide, opened = false;
      try {
        opened = !!(guide && guide.open(
          { userId: Number(reply.data.user_id), lang: lang }, openCourse));
      } catch (_) { opened = false; }
      if (!opened) openCourse();
    }, failed);
  }

  function redeem(switchAccount, attempt) {
    show("handoff.signingIn", true, null, null);
    var body = switchAccount ? { token: token, switch: true } : { token: token };
    return json("/api/v3/pwa-auth/handoff/redeem", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (reply) {
      if (reply.status === 200 && reply.data.ok === true) {
        token = "";
        return continueSignedIn();
      }
      if (reply.status === 409 && reply.data.error === "pwa_handoff_account_mismatch" &&
          !switchAccount) {
        // Another learner is signed in here. Never replace them silently.
        return show("handoff.accountMismatch", false,
          ["handoff.switchAccount", function () { redeem(true, 0); }],
          ["handoff.keepAccount", function () { token = ""; openCourse(); }]);
      }
      return failed();
    }, function () {
      // The request may not have reached the server; the link is still unused.
      if (attempt < NETWORK_RETRIES) {
        return new Promise(function (resolve) { window.setTimeout(resolve, 1500); })
          .then(function () { return redeem(switchAccount, attempt + 1); });
      }
      return failed();
    });
  }

  function start() {
    setLanguage(lang);
    var panda = document.getElementById("panda");
    try {
      var draw = window.HSKCharacters && window.HSKCharacters.render;
      var art = typeof draw === "function" ? draw("panda", "talk") : "";
      if (typeof art === "string" && art) panda.innerHTML = art;
    } catch (_) {}
    show("handoff.signingIn", true, null, null);
    // Opened without a link (reload, bookmark): continue only if this browser
    // already has a verified session; otherwise offer the normal sign-in.
    if (!token) return continueSignedIn();
    return redeem(false, 0);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
