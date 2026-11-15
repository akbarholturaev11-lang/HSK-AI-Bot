"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const { randomUUID } = require("node:crypto");

const script = fs.readFileSync("app/static/course_v3_data/hsk-diagnostics.js", "utf8");
const voice = fs.readFileSync("app/static/voice-live.js", "utf8");
const KEY = "hsk-diag-v1";
const turn = () => new Promise(setImmediate);
const json = (status, body) => ({ status, ok: status >= 200 && status < 300, json: async () => body });

function browser({ storage = new Map(), path = "/iphone-pwa/course", online = true, initData = "", storageDisabled = false, openedAt = Date.UTC(2026, 10, 13) } = {}) {
  const events = new Map(), timers = new Map(), posts = [];
  let now = Date.UTC(2026, 10, 13), actor = 1, answer = json(200, { accepted: 1 }), sequence = 0, calls = 0;
  const window = {
    location: { pathname: path, href: "https://hsk.test" + path },
    navigator: { onLine: online },
    performance: { timeOrigin: openedAt },
    Telegram: { WebApp: { initData } },
    get localStorage() {
      if (storageDisabled) throw new Error("storage blocked");
      return { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value) };
    },
    document: {
      querySelectorAll: () => [{ getAttribute: () => "/asset.js?v=20261113-0123456789ab" }],
      addEventListener() {},
    },
    addEventListener: (name, callback) => events.set(name, callback),
    crypto: { randomUUID },
    async fetch(url, options) {
      calls++;
      if (url === "/api/v3/pwa-auth/session") return actor ? json(200, { ok: true, user_id: actor, csrf: "csrf-" + actor }) : json(401, {});
      assert.ok(["/api/v3/pwa/diagnostics", "/api/miniapp/event"].includes(url));
      posts.push({ header: options.headers["X-HSK-PWA-CSRF"] || options.headers["X-Telegram-Init-Data"],
        wire: JSON.parse(options.body) });
      return answer;
    },
  };
  const context = vm.createContext({
    window, URL, Date: class extends Date { static now() { return now; } },
    setTimeout: (fn, ms) => { const id = ++sequence; timers.set(id, { fn, ms }); return id; },
    clearTimeout: (id) => timers.delete(id),
  });
  vm.runInContext(script, context);
  return { window, context, posts, events, storage, timers, calls: () => calls,
    queue: () => JSON.parse(storage.get(KEY) || '{"events":[]}'),
    clock: (ms) => { now += ms; }, actor: (id) => { actor = id; },
    response: (value) => { answer = value; }, diag: window.HskDiag };
}

async function main() {
  const unverified = browser();
  unverified.events.get("error")({error: new Error("signed-out document")});
  unverified.actor(2);
  unverified.diag.flush();
  await turn();
  assert.equal(unverified.calls(), 0, "the reporter cannot bind an unverified page to a later actor");
  assert.equal(unverified.diag.owner(2), true);
  unverified.diag.flush();
  await turn();
  assert.equal(unverified.posts.length, 0, "pre-verification failures are never adopted");

  const withoutStorage = browser({ storageDisabled: true });
  withoutStorage.diag.owner(1);
  assert.equal(withoutStorage.diag.report("lessons", "load_failed", "lesson_open", 502), true);
  withoutStorage.diag.flush();
  await turn();
  assert.equal(withoutStorage.posts.length, 1, "restricted storage falls back to the current document");

  const first = browser({ online: false });
  assert.equal(first.calls(), 0, "initializing does not read the session");
  first.diag.owner(1);
  first.events.get("error")({ error: { name: "TypeError", message: "private", stack: "secret" }, filename: "/private?a=b" });
  first.events.get("error")({ error: { name: "ReferenceError" } });
  first.events.get("unhandledrejection")({ reason: { name: "AbortError" } });
  first.events.get("unhandledrejection")({ reason: { name: "TypeError", message: "Failed to fetch" } });
  first.events.get("unhandledrejection")({ reason: { name: "constructor", message: "a private answer" } });
  for (const status of [401, 403, 409, 429, 503]) assert.equal(first.diag.report("lessons", "load_failed", "course_v3", status), false);
  assert.equal(first.diag.report("lessons", "load_failed", "lesson_open", new SyntaxError("private response")), true);
  assert.equal(first.queue().events.length, 3);
  first.diag.flush();
  assert.equal(first.calls(), 0);
  const state = first.queue();
  state.events[0].event.stack = "never on the wire";
  state.events[0].event.user_id = 99;
  first.storage.set(KEY, JSON.stringify(state));
  first.window.navigator.onLine = true;
  first.events.get("online")();
  await turn();
  assert.equal(first.posts.length, 1);
  const { header, wire } = first.posts[0];
  assert.equal(header, "csrf-1");
  assert.equal(wire.schema, "diag.v1");
  assert.deepEqual(wire.events.map((e) => e.category), ["type", "other", undefined]);
  assert.equal(wire.events[0].event_id, state.events[0].event.event_id);
  assert.deepEqual(Object.keys(wire.events[0]).sort(),
    ["app_version", "build", "category", "client_time", "error_name", "event_id", "failure_code", "feature_code", "outcome", "site_code"]);
  assert.equal(wire.events[0].error_name, "TypeError");
  assert.equal(wire.events[1].error_name, undefined, "an unlisted exception name is never sent");
  assert.ok(!JSON.stringify(wire).includes("private") && !JSON.stringify(wire).includes("secret"));
  assert.equal(first.queue().events.length, 0);

  const original = browser({ online: false });
  original.diag.owner(1);
  original.diag.report("lessons", "load_failed", "lesson_open", 500);
  const oldUnbound = browser({ storage: original.storage });
  const other = browser({ storage: original.storage, openedAt: Date.UTC(2026, 10, 13) + 1 });
  other.actor(2);
  other.diag.owner(2);
  assert.equal(original.diag.report("lessons", "save_unconfirmed", "lesson_complete", 500), false);
  other.diag.flush();
  await turn();
  assert.equal(other.posts.length, 0, "previous owner's events discarded");
  assert.equal(other.diag.report("lessons", "load_failed", "lesson_open", 500), true, "reset coalescing on owner change");
  assert.equal(oldUnbound.diag.owner(1), false, "a stale actor reply cannot overwrite the next account");
  assert.equal(other.queue().events.length, 1);
  other.response(json(401, {}));
  other.diag.flush();
  await turn();
  assert.equal(other.queue().events.length, 0);
  assert.equal(other.diag.report("lessons", "load_failed", "lesson_open", 502), false);

  for (const staleReply of [json(403, {}), json(200, { accepted: 0, paused: true })]) {
    const openedAt = Date.UTC(2026, 10, 13);
    const old = browser();
    const changedTab = browser({ storage: old.storage, openedAt: openedAt + 1 });
    old.diag.owner(1);
    changedTab.diag.owner(1);
    let finishOldDelivery;
    old.response(new Promise(resolve => { finishOldDelivery = resolve; }));
    old.diag.report("lessons", "load_failed", "lesson_open", 500);
    old.diag.flush();
    await turn();
    assert.equal(old.posts.length, 1);
    changedTab.diag.logout(1);
    const replacement = browser({ storage: old.storage, openedAt: openedAt + 2 });
    assert.equal(replacement.diag.owner(1), true);
    replacement.diag.report("lessons", "save_unconfirmed", "lesson_complete", 500);
    finishOldDelivery(staleReply);
    await turn();
    assert.equal(replacement.queue().events.length, 1, "a stale reply cannot clear a later login for the same user");
    replacement.diag.flush();
    await turn();
    assert.equal(replacement.posts.length, 1, "a stale paused reply cannot suppress the replacement session");
  }

  const aged = browser();
  aged.diag.owner(1);
  aged.diag.report("lessons", "load_failed", "lesson_open", 500);
  aged.clock(24 * 60 * 60 * 1000);
  aged.diag.flush();
  await turn();
  assert.deepEqual(aged.posts[0].wire.events.map((e) => e.failure_code), ["queue_dropped"]);
  assert.equal(aged.queue().events.length, 0);

  const retried = browser();
  retried.diag.owner(1);
  retried.diag.report("lessons", "load_failed", "lesson_open", 500);
  retried.response(json(503, {}));
  retried.diag.flush();
  await turn();
  retried.diag.flush();
  await turn();
  assert.equal(retried.posts.length, 1, "backoff applies on explicit flush too");
  retried.clock(30000);
  retried.response(json(200, { accepted: 0, paused: true }));
  retried.diag.flush();
  await turn();
  assert.deepEqual(retried.posts[1], retried.posts[0], "retry carries the same event ID");
  assert.equal(retried.queue().events.length, 0);
  assert.equal(retried.diag.report("lessons", "save_unconfirmed", "lesson_complete", 500), false);

  const limit = browser({ online: false });
  limit.diag.owner(1);
  for (let i = 0; i < 12; i++) limit.diag.report("lessons", "load_failed", "site_" + i, 500);
  assert.equal(limit.queue().events.length, 10, "one document cannot flood the queue");
  const signals = browser({ online: false });
  signals.diag.owner(1);
  // Exercise the fixed tuples used by the priority call sites.
  for (const [feature, failure, site] of [
    ["auth_session", "restore_failed", "session_restore"],
    ["onboarding_activation", "save_unconfirmed", "li_onboarding"],
    ["practice", "save_unconfirmed", "practice"],
    ["checkout_payments", "save_unconfirmed", "payment"],
    ["pwa_pro_checkout", "save_unconfirmed", "payment"],
    ["distribution_handoff", "restore_failed", "pwa_handoff"],
  ]) {
    assert.equal(signals.diag.report(feature, failure, site, 502), true);
    const event = signals.queue().events.at(-1).event;
    assert.deepEqual([event.feature_code, event.failure_code, event.site_code], [feature, failure, site]);
  }
  const telegram = browser({ path: "/course-v3.html" });
  assert.equal(telegram.diag.report("lessons", "load_failed", "lesson_open", 500), false);
  assert.equal(telegram.calls(), 0);
  const miniApp = browser({ path: "/course-v3.html", initData: "synthetic-auth-only" });
  miniApp.response(json(200, { ok: true, accepted: 1 }));
  miniApp.events.get("error")({ error: new ReferenceError("private message") });
  miniApp.diag.flush();
  await turn();
  assert.equal(miniApp.posts[0].header, "synthetic-auth-only");
  assert.equal(miniApp.posts[0].wire.event, "app_error");
  assert.equal(miniApp.posts[0].wire.events[0].site_code, "course_v3");
  assert.equal(miniApp.storage.has(KEY), false, "no Telegram owner or queue is persisted");
  assert.ok(!JSON.stringify(miniApp.posts[0].wire).includes("synthetic-auth-only"));
  miniApp.diag.report("voice_practice", "load_failed", "voice");
  miniApp.window.Telegram.WebApp.initData = "different-launch";
  miniApp.diag.flush();
  await turn();
  assert.equal(miniApp.posts.length, 1, "do not deliver after Telegram proof changes");

  const live = browser({ path: "/iphone-pwa/practice/voice", online: false });
  live.diag.owner(1);
  live.context.WebSocket = class FakeSocket { send() {} close() {} };
  vm.runInContext(voice, live.context);
  const create = () => live.window.PompLiveVoice.create();
  const server = create();
  const connect = server.connect("fixture", "", "csrf");
  server.socket.onmessage({ data: '{"type":"error","code":"live_response_invalid"}' });
  await assert.rejects(connect, /live_response_invalid/);
  const learner = create();
  const stopped = learner.connect("fixture", "", "csrf");
  learner.stop();
  await assert.rejects(stopped, /cancelled/);
  for (const excluded of ["live_network_slow", "live_audio_suspended", "time_limit"]) create().fail(excluded);
  assert.equal(live.queue().events.length, 0);
  const invalid = create();
  const broken = invalid.connect("fixture", "", "csrf");
  invalid.socket.onmessage({ data: "null" });
  await assert.rejects(broken, /live_response_invalid/);
  const disconnected = create();
  const ready = disconnected.connect("fixture", "", "csrf");
  disconnected.socket.onmessage({ data: '{"type":"ready","input_sample_rate":16000,"output_sample_rate":24000}' });
  await ready;
  disconnected.socket.onerror();
  disconnected.lost();
  assert.deepEqual(live.queue().events.map((e) => e.event.site_code), ["live_response_invalid"], "offline socket closure is expected");
  live.window.navigator.onLine = true;
  const interrupted = create();
  const opened = interrupted.connect("fixture", "", "csrf");
  interrupted.socket.onmessage({ data: '{"type":"ready","input_sample_rate":16000,"output_sample_rate":24000}' });
  await opened;
  interrupted.socket.onerror();
  interrupted.lost();
  assert.deepEqual(live.queue().events.map((e) => e.event.site_code), ["live_response_invalid", "live_socket_closed"]);
  await precision();
  console.log("Learner diagnostic privacy, owner isolation, retry, queue and Live Voice checks passed");
}

// Diagnostic precision (tasks 6.2/6.4): allowlisted debug evidence only.
const ORIGIN = "https://hsk.test";
const DEBUG_KEYS = ["error_name", "reason_code", "location", "frames"];
const SECRETS = ["secretProp", "evilFn", "hsk.test", "https://", "?v=", "token=", "initData", "learner@example.com",
  "private", "<script"];

async function captured(trigger, { path = "/iphone-pwa/handoff", kind = "error" } = {}) {
  const page = browser({ path });
  page.diag.owner(1);
  page.events.get(kind)(trigger);
  page.diag.flush();
  await turn();
  assert.equal(page.posts.length, 1);
  const body = JSON.stringify(page.posts[0].wire);
  for (const secret of SECRETS) assert.ok(!body.includes(secret), "leaked " + secret + ": " + body);
  assert.ok(!JSON.stringify(page.queue()).includes("secretProp"), "nothing private is queued either");
  return page.posts[0].wire.events[0];
}

async function precision() {
  // Chromium-shaped: ErrorEvent position plus a stack with every frame kind.
  const v8 = await captured({
    filename: ORIGIN + "/iphone-pwa-handoff.js", lineno: 57, colno: 9,
    message: "Uncaught TypeError: Cannot read properties of undefined (reading 'secretProp')",
    error: { name: "TypeError", message: "Cannot read properties of undefined (reading 'secretProp')", stack: [
      "TypeError: Cannot read properties of undefined (reading 'secretProp')",
      "    at evilFn (" + ORIGIN + "/iphone-pwa-handoff.js:57:9)",
      "    at Object.open (" + ORIGIN + "/course_v3_data/li-onboarding-install.js?v=20261114-b32fe2d0770a:120:14)",
      "    at " + ORIGIN + "/assets/characters/hsk-character-pack.js?v=0123456789ab&token=private:8:3",
      "    at inlineFn (" + ORIGIN + "/iphone-pwa/handoff:44:5)",
      "    at eval (eval at evilFn (" + ORIGIN + "/iphone-pwa-handoff.js:1:1), <anonymous>:3:4)",
      "    at vendor (" + ORIGIN + "/assets/telegram-web-app.js?v=20261019-1:1:9000)",
      "    at cdn (https://cdn.example.net/course_v3_data/hsk-diagnostics.js:5:5)",
      "    at mapped (" + ORIGIN + "/course_v3_data/hsk-diagnostics.js.map:5:5)",
      "    at <anonymous>",
      "    at async Promise.all (index 0)",
      "    at reporter (" + ORIGIN + "/course_v3_data/hsk-diagnostics.js?v=20261114-cde219a1e184:300:7)",
    ].join("\n") },
  });
  assert.deepEqual([v8.failure_code, v8.category, v8.error_name, v8.reason_code],
    ["js_uncaught", "type", "TypeError", "null_access"]);
  assert.deepEqual(v8.location, { asset_id: "iphone_pwa_handoff", line: 57, column: 9 });
  assert.deepEqual(v8.frames, [
    { asset_id: "li_onboarding_install", line: 120, column: 14, asset_version: "b32fe2d0770a" },
    { asset_id: "hsk_character_pack", line: 8, column: 3, asset_version: "0123456789ab" },
    { asset_id: "hsk_diagnostics", line: 300, column: 7, asset_version: "cde219a1e184" },
  ], "only listed first-party frames survive, without names, URLs or queries");

  // WebKit-shaped rejection: no ErrorEvent, so the top approved frame is the location.
  const webkit = await captured({ reason: { name: "TypeError",
    message: "undefined is not an object (evaluating 'state.secretProp.value')", stack: [
      "evilFn@" + ORIGIN + "/iphone-pwa/handoff:12:30",
      "redeem@" + ORIGIN + "/iphone-pwa-handoff.js:91:22",
      "@" + ORIGIN + "/iphone-pwa-handoff.js:118:14",
      "global code@" + ORIGIN + "/iphone-pwa-handoff.js:131:3",
      "[native code]",
    ].join("\n") } }, { kind: "unhandledrejection" });
  assert.deepEqual([webkit.failure_code, webkit.error_name, webkit.reason_code], ["js_rejection", "TypeError", "null_access"]);
  assert.deepEqual(webkit.location, { asset_id: "iphone_pwa_handoff", line: 91, column: 22 });
  assert.deepEqual(webkit.frames.map((f) => f.line), [118, 131]);

  // More than five approved frames: the first is the location, five follow.
  const deep = await captured({ reason: { name: "RangeError", message: "Maximum call stack size exceeded.",
    stack: Array.from({ length: 12 }, (_, i) => "loop@" + ORIGIN + "/voice-live.js:" + (i + 1) + ":2").join("\n") } },
    { kind: "unhandledrejection", path: "/iphone-pwa/practice/voice" });
  assert.equal(deep.reason_code, "stack_overflow");
  assert.deepEqual([deep.location.line, deep.frames.map((f) => f.line)], [1, [2, 3, 4, 5, 6]]);

  // Nothing usable: the incident is still reported, with no invented data.
  for (const [label, trigger, kind] of [
    ["cross-origin script error without an error object", { message: "Script error.", filename: "", lineno: 0, colno: 0 }, "error"],
    ["foreign origin", { filename: "https://evil.example/iphone-pwa-handoff.js", lineno: 3, colno: 1, error: null }, "error"],
    ["credentials in the URL", { filename: "https://u:p@hsk.test/iphone-pwa-handoff.js", lineno: 3, colno: 1 }, "error"],
    ["inline script", { filename: ORIGIN + "/iphone-pwa/handoff", lineno: 3, colno: 1 }, "error"],
    ["vendored minified script", { filename: ORIGIN + "/course_v3_data/vendor/html2canvas.min.js", lineno: 1, colno: 99 }, "error"],
    ["unlisted sibling", { filename: ORIGIN + "/iphone-pwa-handoff.js.map", lineno: 3, colno: 1 }, "error"],
    ["blob URL", { filename: "blob:" + ORIGIN + "/1234", lineno: 3, colno: 1 }, "error"],
    ["line overflow", { filename: ORIGIN + "/iphone-pwa-handoff.js", lineno: 1e9, colno: 1 }, "error"],
    ["negative line", { filename: ORIGIN + "/iphone-pwa-handoff.js", lineno: -4, colno: 1 }, "error"],
    ["fractional line", { filename: ORIGIN + "/iphone-pwa-handoff.js", lineno: 1.5, colno: 1 }, "error"],
    ["string rejection", { reason: "learner@example.com private text" }, "unhandledrejection"],
    ["stack getter throws", { reason: Object.defineProperty({ name: "constructor" }, "stack", { get() { throw new Error("x"); } }) }, "unhandledrejection"],
  ]) {
    const event = await captured(trigger, { kind });
    assert.deepEqual(DEBUG_KEYS.filter((key) => key in event), [], label);
    assert.equal(event.category, "other", label);
  }
  // A missing or invalid column keeps the file and line.
  const noColumn = await captured({ filename: ORIGIN + "/iphone-pwa-handoff.js?x=1#frag", lineno: 12, colno: 0,
    error: { name: "Error", message: "private" } });
  assert.deepEqual([noColumn.error_name, noColumn.reason_code, noColumn.location],
    ["Error", undefined, { asset_id: "iphone_pwa_handoff", line: 12 }]);

  // Deterministic reasons; anything ambiguous has none.
  for (const [name, message, expected] of [
    ["TypeError", "Cannot read properties of null (reading 'secretProp')", "null_access"],
    ["TypeError", "Cannot set properties of undefined (setting 'secretProp')", "null_access"],
    ["TypeError", "Cannot read property 'secretProp' of undefined", "null_access"],
    ["TypeError", "null is not an object (evaluating 'a.secretProp')", "null_access"],
    ["TypeError", "Cannot set property secretProp of #<Object> which has only a getter", undefined],
    ["TypeError", "secretProp is not a function", "not_callable"],
    ["TypeError", "a.secretProp is not a function. (In 'a.secretProp()', 'a.secretProp' is undefined)", "not_callable"],
    ["TypeError", "secretProp is not a constructor", "not_callable"],
    ["TypeError", "Failed to construct 'URL': Invalid URL", undefined],
    ["ReferenceError", "secretProp is not defined", "not_defined"],
    ["ReferenceError", "Can't find variable: secretProp", "not_defined"],
    ["ReferenceError", "Cannot access 'secretProp' before initialization", undefined],
    ["SyntaxError", "Unexpected token '<', \"<html> private\"... is not valid JSON", "json_parse"],
    ["SyntaxError", "JSON Parse error: Unrecognized token '<'", "json_parse"],
    ["SyntaxError", "Unexpected identifier 'secretProp'", "syntax"],
    ["RangeError", "Invalid array length", undefined],
    ["QuotaExceededError", "The quota has been exceeded.", "storage_quota"],
    ["Error", "Cannot read properties of undefined (reading 'secretProp')", undefined],
    ["TypeError", "", undefined],
  ]) {
    const event = await captured({ reason: { name, message } }, { kind: "unhandledrejection" });
    assert.deepEqual([event.error_name, event.reason_code], [name, expected], name + ": " + message);
  }

  // A modified queue cannot smuggle text, unknown assets or extra frames.
  const forged = browser({ online: false });
  forged.diag.owner(1);
  forged.events.get("error")({ filename: ORIGIN + "/voice-live.js", lineno: 5, colno: 6, error: { name: "TypeError" } });
  const tampered = forged.queue();
  const place = (line) => ({ asset_id: "voice_live", line, column: 1 });
  Object.assign(tampered.events[0].event, {
    error_name: "<script>alert(1)</script>", reason_code: "secretProp",
    location: { asset_id: "voice_live", line: 5, column: 6, url: ORIGIN + "/voice-live.js?token=private", function: "evilFn" },
    frames: [{ asset_id: "../../etc/passwd", line: 1, column: 1 }, { asset_id: "voice_live", line: -1 },
      { asset_id: "voice_live", line: 7, column: 2e9, asset_version: "ZZZ?v=private" }, "evilFn", null,
      place(8), place(9), place(10), place(11)],
    message: "private", stack: "evilFn@https://hsk.test",
  });
  forged.storage.set(KEY, JSON.stringify(tampered));
  forged.window.navigator.onLine = true;
  forged.events.get("online")();
  await turn();
  const cleaned = forged.posts[0].wire.events[0];
  assert.deepEqual(Object.keys(cleaned).sort(), ["app_version", "build", "category", "client_time", "event_id",
    "failure_code", "feature_code", "frames", "location", "outcome", "site_code"]);
  assert.deepEqual(cleaned.location, { asset_id: "voice_live", line: 5, column: 6 });
  assert.deepEqual(cleaned.frames, [{ asset_id: "voice_live", line: 7 }],
    "at most five stored frames are considered and invalid ones are dropped");
  for (const secret of SECRETS) assert.ok(!JSON.stringify(forged.posts).includes(secret), secret);
  // Debug evidence never rides on a non-JS failure.
  const handled = browser({ online: false });
  handled.diag.owner(1);
  handled.diag.report("lessons", "load_failed", "lesson_open", 500);
  const edited = handled.queue();
  Object.assign(edited.events[0].event, { category: "type", error_name: "TypeError", location: place(3) });
  handled.storage.set(KEY, JSON.stringify(edited));
  handled.window.navigator.onLine = true;
  handled.events.get("online")();
  await turn();
  assert.deepEqual(DEBUG_KEYS.filter((key) => key in handled.posts[0].wire.events[0]), []);

  // An older server refuses the optional fields: one plain resend, same event.
  const older = browser();
  older.diag.owner(1);
  older.response(json(422, { ok: false, error: "forbidden_field" }));
  older.events.get("error")({ filename: ORIGIN + "/voice-live.js", lineno: 5, colno: 6, error: { name: "TypeError" } });
  older.diag.flush();
  await turn();
  assert.equal(older.posts.length, 2);
  assert.ok("location" in older.posts[0].wire.events[0]);
  assert.deepEqual(DEBUG_KEYS.filter((key) => key in older.posts[1].wire.events[0]), []);
  assert.equal(older.posts[1].wire.events[0].event_id, older.posts[0].wire.events[0].event_id);
  assert.equal(older.queue().events.length, 0, "a refused plain batch is dropped as before, without a loop");
  const olderMiniApp = browser({ path: "/course-v3.html", initData: "synthetic-auth-only" });
  olderMiniApp.response(json(200, { ok: false, error: "forbidden_field" }));
  olderMiniApp.events.get("error")({ filename: ORIGIN + "/voice-live.js", lineno: 5, colno: 6, error: { name: "TypeError" } });
  olderMiniApp.diag.flush();
  await turn();
  assert.equal(olderMiniApp.posts.length, 2);
  assert.deepEqual(DEBUG_KEYS.filter((key) => key in olderMiniApp.posts[1].wire.events[0]), []);

  // A full queue of the largest events still fits the intake's 16 KB body.
  const full = browser({ online: false });
  full.diag.owner(1);
  full.events.get("error")({ filename: ORIGIN + "/voice-live.js", lineno: 5, colno: 6, error: { name: "TypeError" } });
  const big = full.queue();
  const template = big.events[0];
  const widest = { asset_id: "iphone_pwa_inline_pro_bridge", line: 999999, column: 999999, asset_version: "0123456789ab" };
  big.events = Array.from({ length: 30 }, () => ({ ...template, event: { ...template.event, event_id: randomUUID(),
    reason_code: "null_access", location: widest, frames: Array(5).fill(widest) } }));
  full.storage.set(KEY, JSON.stringify(big));
  full.window.navigator.onLine = true;
  full.events.get("online")();
  await turn();
  assert.ok(full.posts.length >= 2);
  for (const post of full.posts) {
    assert.ok(Buffer.byteLength(JSON.stringify(post.wire)) < 16 * 1024);
    assert.ok(post.wire.events.length >= 1 && post.wire.events.length <= 20);
  }
  assert.equal(new Set(full.posts.flatMap((post) => post.wire.events.map((e) => e.event_id))).size,
    full.posts.reduce((count, post) => count + post.wire.events.length, 0), "no event is sent twice");
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
