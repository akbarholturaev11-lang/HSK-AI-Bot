/* Learner web failure reporter (unified error monitoring, design D5).
 *
 * Sends content-free diag.v1 events: fixed feature, failure, page and
 * category codes only. It never queues or sends an error message, stack, URL,
 * learner text, credential or identity. Active on the browser PWA;
 * the Telegram Mini App transport is added in task 4.1, until then it is inert.
 *
 * HskDiag.report(feature, failure, site[, outcome | cause])
 *   outcome: "failed" (default) or "recovered".
 *   cause:   an HTTP status or an Error; the event is sent only for a server
 *            failure (5xx except 503) or an unreadable answer (SyntaxError).
 *            Offline, 4xx, limits and cancels are expected and never sent.
 */
(function (root) {
  "use strict";
  if (!root || root.HskDiag) return;

  var SCHEMA = "diag.v1";
  var KEY = "hsk-diag-v1";
  var PAUSE_KEY = "hsk-diag-pause-v1";
  var MAX_QUEUE = 30;
  var TTL_MS = 24 * 60 * 60 * 1000;
  var MAX_PER_PAGE = 10;
  var COALESCE_MS = 10 * 60 * 1000;
  var BATCH = 20;
  var MAX_BATCHES = 3;
  var MAX_ATTEMPTS = 3;
  var PAUSE_MS = 24 * 60 * 60 * 1000;
  var RETRY_MS = [30000, 120000];
  var CODE = /^[a-z][a-z0-9_]{0,47}$/;
  var TOKEN = /[?&]v=(\d{8})-([0-9a-f]{12})(?:&|$)/;
  var VERSION = /^\d{8}-[0-9a-f]{12}$/;
  var EVENT_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

  // Page path -> [feature, site]; mirrors `pwa_pages` in the coverage registry.
  var PAGES = {
    "/iphone-pwa": ["auth_session", "pwa_login"],
    "/iphone-pwa/course": ["lessons", "course_v3"],
    "/iphone-pwa/onboarding": ["onboarding_activation", "pwa_onboarding"],
    "/iphone-pwa/onboarding/li": ["onboarding_activation", "li_onboarding"],
    "/iphone-pwa/practice/memorize": ["practice", "memorize"],
    "/iphone-pwa/practice/pronunciation": ["practice", "pronunciation"],
    "/iphone-pwa/practice/recognition": ["practice", "recognition"],
    "/iphone-pwa/practice/test": ["assessments", "test"],
    "/iphone-pwa/practice/mistakes": ["mistake_review", "mistakes"],
    "/iphone-pwa/practice/voice": ["voice_practice", "pwa_voice"],
    "/iphone-pwa/checkout": ["checkout_payments", "checkout"],
    "/iphone-pwa/handoff": ["distribution_handoff", "pwa_handoff"]
  };
  var CATEGORIES = {
    TypeError: "type", ReferenceError: "reference", RangeError: "range", SyntaxError: "syntax",
    EvalError: "other", URIError: "argument", SecurityError: "security", NotAllowedError: "security",
    InvalidStateError: "state", DataCloneError: "serialization", NetworkError: "network",
    AbortError: "abort"
  };
  // Expected rejections an app flow already handles by navigating or retrying.
  var EXPECTED = /^(?:cancelled|pwa_actor_changed|pwa_session_required|pwa_route_unavailable|lesson_identity_changed)$/;
  var NETWORK = /failed to fetch|load failed|networkerror|network request failed/i;

  var path = String(root.location && root.location.pathname || "").replace(/\/+$/, "") || "/";
  var page = PAGES[path] || null;
  var pwa = !!page;
  var busy = false, sent = 0, flushing = false, failures = 0, timer = null, retryAt = 0;
  var documentOwner = "", signedOut = false, pageVersion;
  var pending = { owner: "", events: [], seen: {} };

  function storage() {
    try { return root.localStorage || null; } catch (_) { return null; }
  }
  function read(key) {
    try { var s = storage(); return s ? JSON.parse(s.getItem(key) || "null") : null; } catch (_) { return null; }
  }
  function write(key, value) {
    try { var s = storage(); if (s) s.setItem(key, JSON.stringify(value)); } catch (_) {}
  }
  function load() {
    var state = read(KEY);
    if (!state || typeof state !== "object" || !Array.isArray(state.events)) state = {};
    var storedOwner = typeof state.owner === "string" && /^[1-9][0-9]{0,18}$/.test(state.owner) ? state.owner : "";
    return {
      owner: storedOwner,
      events: Array.isArray(state.events) ? state.events.filter(function (e) {
        return e && e.owner === storedOwner && Number.isFinite(e.at) && wireEvent(e.event);
      }) : [],
      seen: state.seen && typeof state.seen === "object" ? state.seen : {}
    };
  }
  function save(state) { write(KEY, state); }

  function paused(now) {
    var until = Number(read(PAUSE_KEY)) || 0;
    return now < until;
  }

  function uuid() {
    var c = root.crypto;
    if (c && typeof c.randomUUID === "function") return c.randomUUID();
    var b = new Uint8Array(16);
    if (c && c.getRandomValues) c.getRandomValues(b);
    else for (var i = 0; i < 16; i++) b[i] = Math.floor(Math.random() * 256);
    b[6] = (b[6] & 15) | 64; b[8] = (b[8] & 63) | 128;
    var h = Array.prototype.map.call(b, function (x) { return (x + 256).toString(16).slice(1); }).join("");
    return h.slice(0, 8) + "-" + h.slice(8, 12) + "-" + h.slice(12, 16) + "-" + h.slice(16, 20) + "-" + h.slice(20);
  }

  /* The newest content token on the page: date-blobhash of its assets. Its
     date orders versions for the Inbox reopen rule; nothing else is read. */
  function version() {
    if (pageVersion !== undefined) return pageVersion;
    var best = null;
    try {
      var nodes = root.document.querySelectorAll("script[src],link[href]");
      for (var i = 0; i < nodes.length; i++) {
        var m = TOKEN.exec(nodes[i].getAttribute("src") || nodes[i].getAttribute("href") || "");
        if (m && (!best || m[1] + m[2] > best[1] + best[2])) best = m;
      }
    } catch (_) {}
    pageVersion = best ? { app_version: best[1] + "-" + best[2], build: Number(best[1]) } : null;
    return pageVersion;
  }

  function category(error) {
    var name = error && typeof error === "object" ? String(error.name || "") : "";
    return Object.prototype.hasOwnProperty.call(CATEGORIES, name) ? CATEGORIES[name] : "other";
  }

  function serverSide(cause) {
    if (typeof cause === "number") return cause >= 500 && cause <= 599 && cause !== 503;
    return !!(cause && typeof cause === "object" && cause.name === "SyntaxError");
  }

  /* Drop expired and over-cap events; one queue_dropped marker replaces them. */
  function trim(state, now) {
    var dropped = false;
    var count = state.events.length;
    var marker = function (e) { return e.event.feature_code === "monitoring" && e.event.failure_code === "queue_dropped"; };
    state.events = state.events.filter(function (e) {
      var keep = now - e.at < TTL_MS && e.at <= now + TTL_MS;
      if (!keep && !marker(e)) dropped = true;
      return keep;
    });
    while (state.events.length > MAX_QUEUE) {
      var index = 0;
      while (index < state.events.length - 1 && marker(state.events[index])) index++;
      state.events.splice(index, 1);
      dropped = true;
    }
    if (dropped && !state.events.some(function (e) { return marker(e) && e.owner === state.owner; })) {
      if (state.events.length >= MAX_QUEUE) state.events.shift();
      state.events.push({ owner: state.owner, at: now, event: build("monitoring", "queue_dropped", "queue", "failed", null, now) });
    }
    Object.keys(state.seen).forEach(function (key) {
      if (!(now - state.seen[key] < COALESCE_MS)) delete state.seen[key];
    });
    return dropped || state.events.length !== count;
  }

  function build(feature, failure, site, outcome, cat, now) {
    var event = {
      event_id: uuid(), client_time: now, feature_code: feature, failure_code: failure,
      site_code: site, outcome: outcome
    };
    var v = version();
    if (v) { event.app_version = v.app_version; event.build = v.build; }
    if (cat) event.category = cat;
    return event;
  }

  // Rebuild the outbound DTO even when storage has been modified. Never send
  // arbitrary fields, or derive codes from an exception or a server payload.
  function wireEvent(e) {
    if (!e || typeof e.event_id !== "string" || !EVENT_ID.test(e.event_id) ||
        !Number.isSafeInteger(e.client_time) || e.client_time <= 0 ||
        ![e.feature_code, e.failure_code, e.site_code].every(function (code) {
          return typeof code === "string" && CODE.test(code);
        }) || (e.outcome !== "failed" && e.outcome !== "recovered")) return null;
    var out = { event_id: e.event_id, client_time: e.client_time, feature_code: e.feature_code,
      failure_code: e.failure_code, site_code: e.site_code, outcome: e.outcome };
    if (typeof e.app_version === "string" && VERSION.test(e.app_version)) {
      out.app_version = e.app_version;
      out.build = Number(e.app_version.slice(0, 8));
    }
    if (typeof e.category === "string" && Object.values(CATEGORIES).indexOf(e.category) >= 0) out.category = e.category;
    return out;
  }

  function enqueue(feature, failure, site, outcome, cat) {
    if (busy || !pwa || signedOut) return false;
    busy = true;
    try {
      if (![feature, failure, site].every(function (code) {
        return typeof code === "string" && CODE.test(code);
      })) return false;
      if (outcome !== "failed" && outcome !== "recovered") return false;
      var now = Date.now();
      if (sent >= MAX_PER_PAGE || paused(now)) return false;
      var state = load();
      if (documentOwner && state.owner !== documentOwner) return false;
      // An unverified document cannot append to a previous owner's queue.
      if (!documentOwner) state = pending;
      var fp = feature + "|" + failure + "|" + site + "|" + outcome;
      if (now - (Number(state.seen[fp]) || 0) < COALESCE_MS) return false;
      state.seen[fp] = now;
      sent++;
      state.events.push({ owner: state.owner, at: now, event: build(feature, failure, site, outcome, cat, now) });
      trim(state, now);
      if (state !== pending) save(state);
      schedule(0);
      return true;
    } catch (_) {
      return false;
    } finally {
      busy = false;
    }
  }

  function report(feature, failure, site, extra) {
    try {
      var outcome = "failed";
      if (typeof extra === "string") outcome = extra;
      else if (extra !== undefined && !serverSide(extra)) return false;
      return enqueue(feature, failure, site, outcome, null);
    } catch (_) { return false; }
  }

  /* The verified account: another account's queue is discarded, events
     recorded before sign-in (owner "") are adopted. */
  function owner(id) {
    var value = id === null || id === undefined ? "" : String(id);
    if (!pwa || signedOut || !/^[1-9][0-9]{0,18}$/.test(value)) return false;
    if (documentOwner && documentOwner !== value) {
      logout(documentOwner);
      return false;
    }
    var state = load();
    if (documentOwner && state.owner && state.owner !== value) return false;
    if (documentOwner === value && state.owner === value) return true;
    if (state.owner && state.owner !== value) { state.events = []; state.seen = {}; }
    state.events = state.events.concat(pending.events);
    Object.assign(state.seen, pending.seen);
    pending = { owner: "", events: [], seen: {} };
    state.events.forEach(function (e) { e.owner = value; });
    state.owner = value;
    documentOwner = value;
    trim(state, Date.now());
    save(state);
    if (state.events.length) schedule(0);
    return true;
  }

  function remove(ids) {
    var state = load();
    state.events = state.events.filter(function (e) { return !ids[e.event.event_id]; });
    save(state);
  }
  function clear(id, unbind) {
    var state = load();
    if (state.owner === id) {
      state.events = [];
      state.seen = {};
      if (unbind) state.owner = "";
      save(state);
    }
  }

  function logout(id) {
    signedOut = true;
    pending.events = [];
    clear(String(id || documentOwner), true);
  }

  function schedule(delay) {
    if (!pwa || signedOut || timer || flushing || failures >= MAX_ATTEMPTS) return;
    delay = Math.max(delay, retryAt - Date.now());
    var run = function () { timer = null; flush(); };
    if (!delay && typeof root.requestIdleCallback === "function") {
      timer = true;
      root.requestIdleCallback(run, { timeout: 5000 });
    } else {
      timer = setTimeout(run, delay || 1500);
    }
  }

  function boundedFetch(path, options, consume) {
    var controller = typeof root.AbortController === "function" ? new root.AbortController() : null;
    var timeout = controller && setTimeout(function () { controller.abort(); }, 10000);
    return Promise.resolve().then(function () {
      if (controller) options.signal = controller.signal;
      return root.fetch(path, options);
    }).then(consume).finally(function () { if (timeout) clearTimeout(timeout); });
  }

  function pwaSession() {
    return boundedFetch("/api/v3/pwa-auth/session", { credentials: "same-origin", cache: "no-store", redirect: "error" },
      function (r) {
        if (r.status === 401 || r.status === 403) return null;
        if (!r.ok) throw new Error("retry");
        return r.json().then(function (a) {
          if (!a || a.ok !== true || !Number.isSafeInteger(a.user_id) || a.user_id <= 0 ||
              typeof a.csrf !== "string" || !a.csrf) throw new Error("retry");
          return a;
        });
      });
  }

  function pwaBatch(actor, round) {
    var id = String(actor.user_id);
    if (signedOut) return Promise.resolve();
    var batch = load().events.filter(function (e) { return e.owner === id; }).slice(0, BATCH);
    if (!batch.length || round >= MAX_BATCHES) return Promise.resolve();
    var ids = {};
    batch.forEach(function (e) { ids[e.event.event_id] = true; });
    return boundedFetch("/api/v3/pwa/diagnostics", {
      method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error", keepalive: true,
      headers: { "Content-Type": "application/json", "X-HSK-PWA-CSRF": actor.csrf },
      body: JSON.stringify({ schema: SCHEMA, events: batch.map(function (e) { return wireEvent(e.event); }) })
    }, function (r) {
      if (r.status === 401 || r.status === 403) { logout(id); return; }
      if (r.status >= 500) throw new Error("retry");
      if (!r.ok) { remove(ids); return pwaBatch(actor, round + 1); }
      return r.json().then(function (body) {
        if (!body || !Number.isSafeInteger(body.accepted)) throw new Error("retry");
        remove(ids);
        if (body && body.paused === true) {
          write(PAUSE_KEY, Date.now() + PAUSE_MS);
          clear(id, false);
          return;
        }
        return pwaBatch(actor, round + 1);
      });
    });
  }

  function flush() {
    if (!pwa || signedOut || flushing || failures >= MAX_ATTEMPTS || typeof root.fetch !== "function") return;
    if (root.navigator && root.navigator.onLine === false) return;
    if (Date.now() < retryAt) { schedule(retryAt - Date.now()); return; }
    var state = load();
    var now = Date.now();
    if (trim(state, now)) save(state);
    if (!state.events.length && !pending.events.length) return;
    if (paused(now)) { clear(state.owner, false); return; }
    flushing = true;
    pwaSession().then(function (actor) {
      if (!actor) {
        // An anonymous failure must never become a future account's event.
        pending = { owner: "", events: [], seen: {} };
        if (state.owner) {
          if (documentOwner) logout(state.owner);
          else clear(state.owner, true);
        }
        return;
      }
      if (owner(actor.user_id)) return pwaBatch(actor, 0);
    }).then(function () {
      flushing = false;
      failures = 0;
      retryAt = 0;
    }, function () {
      flushing = false;
      failures++;
      if (failures < MAX_ATTEMPTS) {
        retryAt = Date.now() + RETRY_MS[failures - 1];
        schedule(RETRY_MS[failures - 1]);
      }
    });
  }

  function onError(event) {
    if (!page || !event) return;
    try { enqueue(page[0], "js_uncaught", page[1], "failed", category(event.error)); } catch (_) {}
  }
  function onRejection(event) {
    if (!page || !event) return;
    try {
      var reason = event.reason;
      var name = reason && typeof reason === "object" ? String(reason.name || "") : "";
      var message = reason && typeof reason === "object" ? String(reason.message || "") : String(reason || "");
      // Read locally to skip expected cases; never stored or sent.
      if (name === "AbortError" || name === "TimeoutError" || name === "NetworkError" || EXPECTED.test(message)) return;
      if (name === "TypeError" && NETWORK.test(message)) return;
      enqueue(page[0], "js_rejection", page[1], "failed", category(reason));
    } catch (_) {}
  }

  root.HskDiag = { report: report, owner: owner, logout: logout, flush: flush };
  if (!pwa) return;
  try {
    root.addEventListener("error", onError);
    root.addEventListener("unhandledrejection", onRejection);
    root.addEventListener("online", flush);
    root.document.addEventListener("visibilitychange", function () {
      if (root.document.visibilityState === "hidden") flush();
    });
    schedule(0);
  } catch (_) {}
})(typeof window !== "undefined" ? window : null);
