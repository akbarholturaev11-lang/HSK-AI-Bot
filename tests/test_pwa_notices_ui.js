"use strict";
/* Browser-only PWA notices smoke harness; no browser dependencies or providers.
   Run: node tests/test_pwa_notices_ui.js */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("app/static/course_v3_data/iphone-pwa-notices.js", "utf8");
const shell = fs.readFileSync("app/static/course-v3.html", "utf8");
const css = fs.readFileSync("app/static/course_v3_data/iphone-pwa-glass.css", "utf8");
assert(shell.includes('src="/course_v3_data/iphone-pwa-notices.js'));
assert(shell.includes('href="/course_v3_data/iphone-pwa-glass.css'));
assert(shell.includes('PWA_COURSE_HOST?\'<button class="pwa-notices-button"'));
assert(css.includes("#hsk-pwa-notice-root [hidden] {display:none!important}"));
assert(css.includes("html.hsk-pwa-browser .nav"));
assert(!source.includes("X-Telegram-Init-Data"));
assert(!source.includes("PWA_SESSION_COOKIE"));

class Element {
  constructor(tag = "div") {
    this.tag = tag;
    this.children = [];
    this.attrs = {};
    this.hidden = false;
    this.dataset = {};
    this.tabIndex = 0;
    this.offsetParent = {};
    this.isConnected = true;
    this.classList = { contains: (item) => item === "is-done" };
    this.listeners = {};
    this.textContent = "";
  }
  querySelector(selector) {
    this.queries ||= new Map();
    if (!this.queries.has(selector)) this.queries.set(selector, new Element(selector));
    return this.queries.get(selector);
  }
  querySelectorAll() { return Array.from(this.queries?.values() || []); }
  setAttribute(key, value) { this.attrs[key] = String(value); }
  getAttribute(key) { return this.attrs[key]; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  appendChild(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  focus() {}
}

function harness({path = "/iphone-pwa/course", action = null, accountId = 7,
                  alreadyBusy = false, splashReady = true, sharedStorage = new Map()} = {}) {
  let splashDone = splashReady, currentAction = action;
  const timers = [], callbacks = {}, requests = [], navigation = [];
  let root = null, redirects = 0;
  const document = {
    visibilityState: "visible",
    activeElement: new Element("button"),
    body: {appendChild: (el) => {root = el;}},
    createElement: (tag) => new Element(tag),
    addEventListener: () => {},
    querySelector: () => alreadyBusy ? new Element("lesson") : null,
    getElementById: () => {
      const e = new Element("splash");
      e.classList = {contains:(name)=>name==="is-done" && splashDone};
      return e;
    }
  };
  const location = {
    pathname: path,
    assign: (url) => navigation.push(url),
    replace: (url) => {redirects++; navigation.push("replace:" + url);}
  };
  const window = {
    addEventListener: (type, handler) => {callbacks[type] = handler;},
    setTimeout: (callback) => timers.push(callback),
    App: {show: (screen) => navigation.push("show:" + screen)}
  };
  const fetch = async (url, options) => {
    requests.push({url, options});
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store");
    const response = url.endsWith("/session")
      ? {ok:true, user_id:accountId}
      : url.endsWith("/account-notices")
        ? {ok:true, notices:[{id:2, title:"Account notice", body:"Stored on server", action:"course"}],
           payment_action:currentAction}
        : {ok:true, notifications:[{id:1,title:"Lesson available",body:"HSK 3",action:"course"}]};
    return {ok:true,json:async()=>response};
  };
  vm.runInNewContext(source, {
    document, window, location, fetch, pwaCourseActor: async()=>({user_id:accountId}),
    courseMessage: (key) => key, commonMessage: (key) => key,
    LANG:"uz", App:window.App, Set, Number, Promise, Array, String,
    encodeURIComponent, localStorage:{
      getItem:(key)=>sharedStorage.get(key) || null,
      setItem:(key,value)=>sharedStorage.set(key,value)
    }
  }, {filename:"iphone-pwa-notices.js",timeout:1000});
  return {root:()=>root, window, navigation, requests, timers, callbacks, redirects:()=>redirects,
    setSplashDone(){splashDone = true;},
    setAction(value){currentAction = value;},
    async flushTimers(){for(const fn of timers.splice(0))await fn();},
    async loadAndTick(){
      assert.equal(typeof callbacks.load, "function");
      callbacks.load();
      for (const fn of timers.splice(0)) await fn();
    }};
}

async function main(){
  const telegram = harness({path:"/course-v3.html"});
  assert.equal(telegram.root(), null, "Telegram original course unchanged");
  assert.equal(telegram.window.HskPwaInbox, undefined);

  const standard = harness();
  assert(standard.root(), "PWA module mounted");
  assert(standard.root().hidden, "inbox hidden until requested");
  await standard.window.HskPwaInbox.open();
  const list = standard.root().querySelector("#hsk-pwa-notice-list");
  assert.equal(list.children.length, 1);
  assert.equal(list.children[0].children[0].textContent, "Lesson available");
  assert.equal(standard.requests.length, 3, "two owned feeds + session validation");
  assert(standard.requests.every((q) => q.options.credentials === "same-origin"));
  assert.equal(standard.navigation.length, 0, "reading inbox cannot navigate or grant access");

  const storage = new Map();
  const paid = harness({action:{payment_id:18,status:"rejected",plan_type:"1_month"},sharedStorage:storage});
  await paid.loadAndTick();
  assert.equal(paid.root().hidden,false, "latest rejection opens a dialog");
  assert.equal(paid.root().querySelector("#hsk-pwa-urgent-title").textContent,
    "subscriptionPage.proRejectedTitle");
  assert.equal(paid.root().querySelector('[role="dialog"]').attrs["aria-labelledby"], "hsk-pwa-urgent-title");
  assert.equal(paid.root().querySelector(".hsk-pwa-notice-head").hidden, true);
  paid.root().listeners.click({target:{closest:(selector)=>selector==="[data-pwa-close]"?{}:null}});
  assert.equal(paid.root().hidden,true, "dismiss closes alert");
  assert.equal(storage.get("hskai:pwa:rejected:7:18"),"1","per-owner receipt dismissal");

  const repeated = harness({action:{payment_id:18,status:"rejected",plan_type:"1_month"},sharedStorage:storage});
  await repeated.loadAndTick();
  assert.equal(repeated.root().hidden,true,"same reviewed payment does not interrupt again");

  const anotherOwner = harness({action:{payment_id:18,status:"rejected",plan_type:"1_month"},
    accountId:8,sharedStorage:storage});
  await anotherOwner.loadAndTick();
  assert.equal(anotherOwner.root().hidden,false,"dismissal not leaked across accounts");

  const hsk30 = harness({action:{payment_id:22,status:"rejected",plan_type:"hsk30_unlock"}});
  await hsk30.loadAndTick();
  assert.equal(hsk30.root().querySelector("#hsk-pwa-urgent-title").textContent,
    "subscriptionPage.paymentRejectedTitle");
  hsk30.root().listeners.click({target:{closest:(selector)=>selector==="[data-pwa-retry]"?{}:null}});
  assert(hsk30.navigation[0].includes("mode=hsk30_unlock&plan=hsk30_unlock"),
    "HSK3 rejection must reopen its exact unlock checkout");

  const tenDay = harness({action:{payment_id:23,status:"rejected",plan_type:"10_days"}});
  await tenDay.loadAndTick();
  tenDay.root().listeners.click({target:{closest:(selector)=>selector==="[data-pwa-retry]"?{}:null}});
  assert(tenDay.navigation[0].includes("&plan=10_days"),
    "retry must preserve a rejected 10-day Pro plan");

  const superseded = harness({action:null});
  await superseded.loadAndTick();
  assert.equal(superseded.root().hidden,true,"old rejected receipts cannot create fresh urgency");

  const busy = harness({action:{payment_id:55,status:"rejected",plan_type:"1_month"},alreadyBusy:true});
  await busy.loadAndTick();
  assert.equal(busy.root().hidden,true,"never interrupt active lesson or sheet");

  const delayed = harness({action:{payment_id:90,status:"rejected",plan_type:"1_month"},splashReady:false});
  await delayed.loadAndTick();
  assert.equal(delayed.root().hidden,true,"do not overlay loading/splash screen");
  delayed.setSplashDone();
  await delayed.flushTimers();
  assert.equal(delayed.root().hidden,false,"show latest rejected payment after the splash ends");

  const resumed = harness({action:null});
  await resumed.loadAndTick();
  assert.equal(resumed.root().hidden,true,"no initial payment action");
  resumed.setAction({payment_id:101,status:"rejected",plan_type:"1_month"});
  assert.equal(typeof resumed.callbacks.pageshow,"function");
  await resumed.callbacks.pageshow({persisted:true});
  assert.equal(resumed.root().hidden,false,"new reviewed rejection appears after BFCache resume");

  const resumeStorage = new Map();
  const latest = harness({
    action:{payment_id:102,status:"rejected",plan_type:"1_month"},
    sharedStorage:resumeStorage
  });
  await latest.loadAndTick();
  latest.setAction(null);
  await latest.callbacks.pageshow({persisted:true});
  assert.equal(latest.root().hidden,true,"newer pending/approved payment closes stale rejection");
  assert.equal(resumeStorage.get("hskai:pwa:rejected:7:102"),"1");
  latest.setAction({payment_id:103,status:"rejected",plan_type:"hsk30_unlock"});
  await latest.callbacks.pageshow({persisted:true});
  assert.equal(latest.root().hidden,false,"subsequent rejection remains actionable");
  assert.equal(latest.root().querySelector("#hsk-pwa-urgent-title").textContent,
    "subscriptionPage.paymentRejectedTitle");
  assert.equal(resumeStorage.get("hskai:pwa:rejected:7:103"),undefined,
    "newer payment must never be silently marked as displayed");
  latest.root().listeners.click({target:{closest:(selector)=>selector==="[data-pwa-close]"?{}:null}});
  assert.equal(resumeStorage.get("hskai:pwa:rejected:7:103"),"1");

  console.log("PWA notice UI: 13 behavior/ownership/safety checks passed");
}
main().catch((err)=>{console.error(err);process.exitCode=1;});
