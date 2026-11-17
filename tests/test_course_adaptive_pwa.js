"use strict";
/* UIUX-007: course-v3.html ichidagi shaxsiy takror moduli.
   Modul sahifadan kesib olinadi va soxta DOM/tarmoq bilan ishga tushiriladi:
   joylashuv serverdagi placement_slots bilan bir xil, rasmiy dars holati
   (indeks, ball, yurak, XP, navbat) o'zgarmaydi, offline javob faqat shu
   akkaunt navbatida saqlanadi. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const page = fs.readFileSync("app/static/course-v3.html", "utf8");
const start = page.indexOf("var ADAPTIVE_FORMATS=");
const end = page.indexOf("function luRain(){", start);
assert.ok(start > 0 && end > start, "adaptive module must sit right before luRain()");
const source = page.slice(start, end);
const turn = () => new Promise(setImmediate);
const settle = async () => { for (let n = 0; n < 8; n++) await turn(); };

class El {
  constructor(attrs = {}) {
    this.attrs = attrs; this.dataset = {}; this.style = {}; this.children = []; this.onclick = null;
    this._html = ""; this.textContent = ""; this.className = "";
    const set = new Set();
    this.classList = { add: (c) => set.add(c), remove: (c) => set.delete(c), contains: (c) => set.has(c), _set: set };
  }
  set innerHTML(html) {
    this._html = html;
    this.children = [];
    const re = /<button class="([^"]*)" type="button"((?: data-[a-z]+="\d+")*)>/g;
    let m;
    while ((m = re.exec(html))) {
      const el = new El(); el.className = m[1];
      for (const d of m[2].matchAll(/data-([a-z]+)="(\d+)"/g)) el.dataset[d[1]] = d[2];
      this.children.push(el);
    }
  }
  get innerHTML() { return this._html; }
  querySelectorAll(sel) {
    if (sel === "button") return this.children;
    if (sel === ".opt") return this.children.filter((c) => c.className.split(" ").includes("opt"));
    throw new Error("unexpected selector " + sel);
  }
  scrollIntoView() {}
}

function lessonQueue() {
  const graded = (id) => ({ id, type: "choice", options: ["a", "b", "c"] });
  return [
    { id: "intro", type: "info" },         // 0
    graded("g1"),                          // 1
    graded("g2"),                          // 2
    graded("g3"),                          // 3
    { id: "info2", type: "info" },         // 4
    graded("g5"),                          // 5
    { id: "exit", _exitTicket: true, options: ["a", "b"] }, // 6
    graded("g7"),                          // 7
  ];
}

function question(format, extra = {}) {
  return { id: "q-" + format, format, prompt: "Choose", options: ["你", "好", "我"], ...extra };
}

function plan(items, id = 41) {
  return { ok: true, enabled: true, plan: { id, version: 1, level: "hsk1", lesson_order: 3, items } };
}

function item(slot, format = "meaning_choice", extra = {}) {
  return { id: `a${slot}:${10 + slot}:${format}`, slot, kind: "review", skill: "meaning", answered: false,
    question: question(format, extra) };
}

function harness({ scope = "u1", now = Date.UTC(2026, 10, 17) } = {}) {
  const els = {};
  const $ = (sel) => (els[sel] ||= new El());
  const storage = new Map();
  const posts = [], rendered = [], respond = { plan: null, answer: null };
  let clock = now, userScope = scope, order = 3;
  const Flow = {
    queue: lessonQueue(), i: 0, lessonIdx: 2, test: false, challenge: false, previewHalf: false,
    answered: false, score: 4, hearts: 3, xp: 20, streak: 2, wrong: 1, _cheered: true,
  };
  const reply = (status, body) => ({ status, ok: status >= 200 && status < 300, json: async () => body });
  const context = vm.createContext({
    window: {}, $, Flow, LANG: "uz", INIT_DATA: "", PWA_COURSE_HOST: true,
    document: { querySelectorAll: (sel) => (sel === "#f-body .opt" ? $("#f-body").querySelectorAll(".opt") : []) },
    localStorage: {
      getItem: (k) => (storage.has(k) ? storage.get(k) : null),
      setItem: (k, v) => storage.set(k, String(v)), removeItem: (k) => storage.delete(k),
    },
    Date: class extends Date { static now() { return clock; } },
    setTimeout: () => 0, clearTimeout: () => {},
    courseMessage: (key, fallback) => fallback,
    T: () => ({ listen: "Tingla", rightAns: "To'g'ri javob:", correct: "To'g'ri!", wrong: "Xato", next: "Davom etish" }),
    esc: (s) => String(s).replace(/[<>&"]/g, ""),
    localUserScope: () => userScope,
    flowLessonOrder: () => order,
    cancelLessonPron() {}, setWriteBtn() {}, saveLessonResume() {}, speak() {}, beep() {}, haptic() {},
    hideBar: () => { $("#f-bar").className = "fbar"; },
    renderFlowCard: () => rendered.push(Flow.i),
    flowDone: () => rendered.push("done"),
    renderCheer() {}, trackSectionCompleted() {}, saveLessonMastery() {},
    skipN1PilotRechecks: (i) => i,
    _apiPost(url, body) {
      posts.push({ url, body: JSON.parse(JSON.stringify(body)) });
      const kind = url.endsWith("/plan") ? "plan" : "answer";
      const r = typeof respond[kind] === "function" ? respond[kind](body) : respond[kind];
      if (r instanceof Error) return Promise.reject(r);
      return Promise.resolve(reply(r ? r[0] : 200, r ? r[1] : { ok: true, enabled: false, plan: null }));
    },
  });
  vm.runInContext(source, context);
  $("#f-barbtn").onclick = Flow.next;
  const official = () => JSON.stringify({ q: Flow.queue, s: Flow.score, h: Flow.hearts, x: Flow.xp,
    st: Flow.streak, w: Flow.wrong, a: Flow.answered });
  return {
    context, Flow, $, posts, rendered, storage, respond, official,
    clock: (ms) => { clock += ms; }, scope: (s) => { userScope = s; }, order: (n) => { order = n; },
    outbox: (s = userScope) => JSON.parse(storage.get("hsk_v3_adaptive_outbox:v1:" + s) || "[]"),
    run: (code) => vm.runInContext(code, context),
  };
}

async function loadPlan(h, body) {
  h.respond.plan = [200, body];
  h.run("adaptiveLoad('hsk1',3)");
  await settle();
}

async function main() {
  // 1) Joylashuv serverdagi placement_slots bilan aynan bir xil.
  {
    const h = harness();
    const cases = [
      [[2, 3, 4, 5, 6, 7, 8, 9], 3, [4, 6, 8]], [[2, 3], 3, [2, 3]], [[5], 1, [5]],
      [[2, 3, 4, 5, 6], 2, [3, 5]], [Array.from({ length: 18 }, (_, k) => k + 2), 3, [6, 11, 15]], [[], 2, []],
    ];
    for (const [eligible, count, expected] of cases) {
      assert.deepEqual(Array.from(h.context.adaptiveSlots(eligible, count)), expected, JSON.stringify(eligible));
    }
  }

  // 2) Faqat baholangan kartadan keyin, exit-ticketgacha; resume o'tgan chegaralarni olmaydi.
  {
    const h = harness();
    await loadPlan(h, plan([item(1), item(2), item(3)]));
    assert.deepEqual(Object.keys(h.context.Adaptive.slots).map(Number), [2, 3, 4]);
    await loadPlan(h, plan([item(1)]));
    assert.deepEqual(Object.keys(h.context.Adaptive.slots).map(Number), [3]);
    h.Flow.i = 2;
    await loadPlan(h, plan([item(1), item(2)]));
    assert.deepEqual(Object.keys(h.context.Adaptive.slots).map(Number), [3, 4], "resume uses only boundaries ahead");
    await loadPlan(h, plan([{ ...item(1), answered: true }, item(2, "unknown_format"), item(3)]));
    assert.equal(Object.keys(h.context.Adaptive.slots).length, 1, "answered and unsupported items are skipped");
  }

  // 3) To'liq oqim: overlay → server javobi → davom; rasmiy holat o'zgarmaydi.
  {
    const h = harness();
    await loadPlan(h, plan([item(1), item(2), item(3)]));
    const before = h.official();
    h.Flow.i = 1;
    h.run("Flow.next()");
    assert.equal(h.Flow.i, 2);
    assert.deepEqual(h.rendered, [], "the base card waits behind the adaptive question");
    assert.match(h.$("#f-stage").innerHTML, /Shaxsiy takror/);
    assert.match(h.$("#f-body").innerHTML, /Avvalgi xatongiz asosida/);
    h.respond.answer = [200, { ok: true, item_id: "a1:11:meaning_choice", correct: false, correct_index: 1,
      selected_index: 0, correct_answer: "好" }];
    const options = h.$("#f-body").querySelectorAll(".opt");
    assert.equal(options.length, 3);
    options[0].onclick();
    options[2].onclick();
    await settle();
    const answers = h.posts.filter((p) => p.url === "/api/v3/adaptive/answer");
    assert.deepEqual(answers.map((p) => p.body), [{ plan_id: 41, item_id: "a1:11:meaning_choice", selected_index: 0 }],
      "one locked answer with only plan/item/choice — never a score or owner");
    assert.ok(options[1].classList.contains("sel") && options[0].classList.contains("bad"));
    assert.match(h.$("#f-bar").className, /show no/);
    assert.match(h.$("#f-msg").innerHTML, /To'g'ri javob: 好/);
    assert.equal(h.$("#f-barbtn").onclick, h.context.adaptiveContinue);
    h.$("#f-barbtn").onclick();
    assert.deepEqual(h.rendered, [2], "the same base card renders after the review");
    assert.equal(h.$("#f-barbtn").onclick, h.Flow.next, "the base button is restored");
    assert.equal(h.Flow.i, 2);
    assert.equal(h.official(), before, "score, hearts, XP, streak, queue and answered flag are untouched");
    h.run("Flow.next()");
    assert.equal(h.Flow.i, 3);
    assert.match(h.$("#f-body").innerHTML, /Avvalgi xatongiz/, "next boundary shows the next item");
  }

  // 4) O'chirilgan, eskirgan yoki boshqa darsga tegishli reja e'tiborsiz qoladi.
  {
    const h = harness();
    await loadPlan(h, { ok: true, enabled: false, plan: null });
    assert.equal(h.context.Adaptive.plan, null);
    h.respond.plan = [200, plan([item(1)])];
    h.run("adaptiveLoad('hsk1',3); adaptiveReset()");
    await settle();
    assert.equal(h.context.Adaptive.plan, null, "a reply after exitFlow is dropped");
    h.order(4);
    await loadPlan(h, plan([item(1)]));
    assert.equal(h.context.Adaptive.plan, null, "a reply for another lesson is dropped");
    h.order(3);
    for (const flag of ["test", "challenge", "previewHalf"]) {
      h.Flow[flag] = true;
      const count = h.posts.length;
      h.run("adaptiveLoad('hsk1',3)");
      await settle();
      assert.equal(h.posts.length, count, flag + " never asks for a plan");
      h.Flow[flag] = false;
    }
    h.respond.plan = new Error("network");
    h.run("adaptiveLoad('hsk1',3)");
    await settle();
    h.Flow.i = 1;
    h.run("Flow.next()");
    assert.deepEqual(h.rendered, [2], "a failed plan leaves the lesson unchanged");
  }

  // 5) Rad etilgan javob (4xx) darsni to'xtatmaydi.
  {
    const h = harness();
    await loadPlan(h, plan([item(1)]));
    h.Flow.i = 2;
    h.run("Flow.next()");
    h.respond.answer = [409, { ok: false, error: "adaptive_plan_stale" }];
    h.$("#f-body").querySelectorAll(".opt")[0].onclick();
    await settle();
    assert.deepEqual(h.rendered, [3]);
    assert.deepEqual(h.outbox(), []);
  }

  // 6) Tarmoq/5xx: javob shu akkaunt navbatiga tushadi va keyin yuboriladi.
  {
    const h = harness();
    await loadPlan(h, plan([item(1), item(2)]));
    h.Flow.i = 2;
    h.run("Flow.next()");
    h.respond.answer = [503, { ok: false, error: "adaptive_unavailable" }];
    h.$("#f-body").querySelectorAll(".opt")[1].onclick();
    await settle();
    assert.match(h.$("#f-msg").innerHTML, /internet qaytganda/);
    assert.equal(h.outbox().length, 1);
    h.$("#f-barbtn").onclick();
    h.run("Flow.next()");
    h.respond.answer = new Error("offline");
    h.$("#f-body").querySelectorAll(".opt")[0].onclick();
    await settle();
    assert.equal(h.outbox().length, 2);
    h.run("adaptiveQueue({plan_id:41,item_id:'a2:12:meaning_choice',selected_index:2})");
    assert.equal(h.outbox().length, 2, "a repeat replaces the same item instead of duplicating it");
    assert.equal(h.outbox().find((e) => e.body.item_id === "a2:12:meaning_choice").body.selected_index, 2);

    h.scope("u2");
    assert.deepEqual(h.outbox(), [], "another account never sees this outbox");
    h.respond.plan = [200, { ok: true, enabled: false, plan: null }];
    const count = h.posts.length;
    h.run("adaptiveLoad('hsk1',3)");
    await settle();
    assert.equal(h.posts.filter((p, k) => k >= count && p.url.endsWith("/answer")).length, 0);

    h.scope("u1");
    const replies = { "a1:11:meaning_choice": [200, { ok: true, duplicate: true }], "a2:12:meaning_choice": [503, {}] };
    h.respond.answer = (body) => replies[body.item_id];
    h.run("adaptiveLoad('hsk1',3)");
    await settle();
    assert.deepEqual(h.outbox().map((e) => e.body.item_id), ["a2:12:meaning_choice"], "only the 5xx answer is kept");

    h.clock(37 * 60 * 60 * 1000);
    const sent = h.posts.length;
    h.run("adaptiveLoad('hsk1',3)");
    await settle();
    assert.equal(h.posts.slice(sent).filter((p) => p.url.endsWith("/answer")).length, 0, "expired answers are not sent");
    assert.deepEqual(h.outbox(), []);
  }

  // 7) So'z yig'ish: tanlangan tartib aynan yuboriladi.
  {
    const h = harness();
    await loadPlan(h, plan([item(1, "sentence_builder", { options: undefined, tokens: ["我", "是", "学生"] })]));
    h.Flow.i = 2;
    h.run("Flow.next()");
    h.respond.answer = [200, { ok: true, correct: true }];
    const bank = () => h.$("#ad-bank").querySelectorAll("button");
    bank().find((b) => b.dataset.i === "1").onclick();
    h.$("#ad-line").querySelectorAll("button")[0].onclick();
    for (const i of ["0", "1", "2"]) bank().find((b) => b.dataset.i === i).onclick();
    await settle();
    const answer = h.posts.find((p) => p.url.endsWith("/answer"));
    assert.deepEqual(answer.body.selected_tokens, ["我", "是", "学生"]);
    assert.match(h.$("#f-bar").className, /show ok/);
  }

  console.log("course adaptive PWA module: ok");
}

main().catch((error) => { console.error(error); process.exit(1); });
