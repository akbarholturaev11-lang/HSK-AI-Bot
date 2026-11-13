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

function browser({ storage = new Map(), path = "/iphone-pwa/course", online = true } = {}) {
  const events = new Map(), timers = new Map(), posts = [];
  let now = Date.UTC(2026, 10, 13), actor = 1, answer = json(200, { accepted: 1 }), sequence = 0, calls = 0;
  const window = {
    location: { pathname: path, href: "https://hsk.test" + path },
    navigator: { onLine: online },
    localStorage: { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value) },
    document: {
      querySelectorAll: () => [{ getAttribute: () => "/asset.js?v=20261113-0123456789ab" }],
      addEventListener() {},
    },
    addEventListener: (name, callback) => events.set(name, callback),
    crypto: { randomUUID },
    async fetch(url, options) {
      calls++;
      if (url === "/api/v3/pwa-auth/session") return actor ? json(200, { ok: true, user_id: actor, csrf: "csrf-" + actor }) : json(401, {});
      assert.equal(url, "/api/v3/pwa/diagnostics");
      posts.push({ header: options.headers["X-HSK-PWA-CSRF"], wire: JSON.parse(options.body) });
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
    ["app_version", "build", "category", "client_time", "event_id", "failure_code", "feature_code", "outcome", "site_code"]);
  assert.equal(first.queue().events.length, 0);

  const original = browser({ online: false });
  original.diag.owner(1);
  original.diag.report("lessons", "load_failed", "lesson_open", 500);
  const other = browser({ storage: original.storage });
  other.actor(2);
  other.diag.owner(2);
  assert.equal(original.diag.report("lessons", "save_unconfirmed", "lesson_complete", 500), false);
  other.diag.flush();
  await turn();
  assert.equal(other.posts.length, 0, "previous owner's events discarded");
  assert.equal(other.diag.report("lessons", "load_failed", "lesson_open", 500), true, "reset coalescing on owner change");
  other.response(json(401, {}));
  other.diag.flush();
  await turn();
  assert.equal(other.queue().events.length, 0);
  assert.equal(other.diag.report("lessons", "load_failed", "lesson_open", 502), false);

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
  const telegram = browser({ path: "/course-v3.html" });
  assert.equal(telegram.diag.report("lessons", "load_failed", "lesson_open", 500), false);
  assert.equal(telegram.calls(), 0);

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
  invalid.socket.onmessage({ data: "not JSON" });
  await assert.rejects(broken, /live_response_invalid/);
  const disconnected = create();
  const ready = disconnected.connect("fixture", "", "csrf");
  disconnected.socket.onmessage({ data: '{"type":"ready","input_sample_rate":16000,"output_sample_rate":24000}' });
  await ready;
  disconnected.socket.onerror();
  disconnected.lost();
  assert.deepEqual(live.queue().events.map((e) => e.event.site_code), ["live_response_invalid", "live_socket_closed"]);
  console.log("Learner diagnostic privacy, owner isolation, retry, queue and Live Voice checks passed");
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
