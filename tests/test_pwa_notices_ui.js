"use strict";
/* Browser-only PWA notices smoke harness; no browser dependencies or providers.
   Run: node tests/test_pwa_notices_ui.js */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("app/static/course_v3_data/iphone-pwa-notices.js", "utf8");
const shell = fs.readFileSync("app/static/course-v3.html", "utf8");
const css = fs.readFileSync("app/static/course_v3_data/iphone-pwa-glass.css", "utf8");
assert(shell.includes('src="/course_v3_data/iphone-pwa-notices.js?v=20261104-0a68a6704a78"'));
assert(shell.includes('href="/course_v3_data/iphone-pwa-glass.css?v=20261105-5421046cea3a'));
assert(shell.includes('PWA_COURSE_HOST?\'<button class="pwa-notices-button"'));
assert(shell.includes('pwaPushSettingsRowHtml()'));
assert(!shell.includes('class="pwa-feedback-button"'),"profile feedback shortcut is removed");
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

function harness({path = "/iphone-pwa/course", href = null, action = null, accountId = 7,
                  alreadyBusy = false, feedbackOpen = false, inputFocused = false,
                  splashReady = true, sharedStorage = new Map(), standalone = false,
                  vendor = "Apple Computer, Inc.",
                  pushEnabled = true, initiallySubscribed = false, permission = "default"} = {}) {
  let splashDone = splashReady, currentAction = action;
  const timers = [], callbacks = {}, requests = [], navigation = [], pushCalls = [];
  let root = null, redirects = 0, serverSubscribed = initiallySubscribed, localSubscription = null;
  let notificationPermission = permission, permissionFetchCount = null;
  const key = "B".repeat(87);
  const subscription = {
    toJSON: () => ({endpoint:"https://web.push.apple.com/example/token",keys:{p256dh:key,auth:"A".repeat(22)}}),
    unsubscribe: async () => {pushCalls.push("unsubscribe"); localSubscription = null; return true;}
  };
  const registration = {pushManager:{
    getSubscription:async()=>localSubscription,
    subscribe:async(options)=>{pushCalls.push(["subscribe",options.userVisibleOnly]);localSubscription=subscription;return subscription;}
  }};
  const navigator = {standalone,vendor,serviceWorker:{
    register:async(url,options)=>{pushCalls.push(["register",url,options.scope]);return registration;},
    ready:Promise.resolve(registration),
    getRegistration:async(scope)=>{pushCalls.push(["getRegistration",scope]);return registration;}
  }};
  const Notification = {get permission(){return notificationPermission;},
    requestPermission:()=>{permissionFetchCount=requests.length;pushCalls.push("permission");notificationPermission="granted";return Promise.resolve("granted");}};
  const historyCalls = [];
  const document = {
    visibilityState: "visible",
    activeElement: Object.assign(new Element("button"), {matches: () => inputFocused}),
    body: {appendChild: (el) => {root = el;}},
    createElement: (tag) => new Element(tag),
    addEventListener: () => {},
    querySelector: () => (alreadyBusy || feedbackOpen) ? new Element("lesson") : null,
    getElementById: () => {
      const e = new Element("splash");
      e.classList = {contains:(name)=>name==="is-done" && splashDone};
      return e;
    }
  };
  const location = {
    pathname: path, href: href || ("https://app.example.test" + path),
    assign: (url) => navigation.push(url),
    replace: (url) => {redirects++; navigation.push("replace:" + url);}
  };
  const window = {
    addEventListener: (type, handler) => {callbacks[type] = handler;},
    setTimeout: (callback) => timers.push(callback),
    App: {show: (screen) => navigation.push("show:" + screen)},
    navigator, isSecureContext: true, matchMedia: () => ({matches:standalone}), Notification, PushManager: {}
  };
  const history = {state:{route:"course"},replaceState:(state,title,url)=>historyCalls.push({state,title,url})};
  const fetch = async (url, options) => {
    requests.push({url, options});
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store");
    const response = url.endsWith("/push/status")
      ? {ok:true, enabled:pushEnabled, public_key:pushEnabled?key:null, subscribed:serverSubscribed,
         subscription_id:serverSubscribed?"11111111-1111-4111-8111-111111111111":null, user_id:accountId}
      : url.endsWith("/session")
      ? {ok:true, user_id:accountId}
      : url.endsWith("/account-notices")
        ? {ok:true, notices:[{id:2, title:"Account notice", body:"Stored on server", action:"course"}],
           payment_reviews:[{payment_id:30,status:"approved",plan_type:"1_month"},
             {payment_id:31,status:"rejected",plan_type:"1_month"}],
           payment_action:currentAction}
        : {ok:true, notifications:[{id:1,title:"Lesson available",body:"HSK 3",action:"course"}]};
    if (url.endsWith("/push/subscribe")) serverSubscribed = true;
    if (url.endsWith("/push/revoke")) serverSubscribed = false;
    return {ok:true,json:async()=>response};
  };
  vm.runInNewContext(source, {
    document, window, location, history, URL, navigator, Notification, atob, Uint8Array, fetch, pwaCourseActor: async()=>({user_id:accountId,csrf:"csrf-token"}),
    courseMessage: (key) => key, commonMessage: (key) => key,
    LANG:"uz", App:window.App, Set, Number, Promise, Array, String,
    encodeURIComponent, localStorage:{
      getItem:(key)=>sharedStorage.get(key) || null,
      setItem:(key,value)=>sharedStorage.set(key,value)
    }
  }, {filename:"iphone-pwa-notices.js",timeout:1000});
  return {root:()=>root, window, navigation, requests, timers, callbacks, redirects:()=>redirects,
    pushCalls, historyCalls, permissionFetchCount:()=>permissionFetchCount,
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
  assert.equal(standard.root().querySelector(".hsk-pwa-close").attrs["aria-label"], "action.close",
    "dismiss button uses the canonical localized accessibility label");
  await standard.window.HskPwaInbox.open();
  const list = standard.root().querySelector("#hsk-pwa-notice-list");
  assert.equal(list.children.length, 4, "course, account and two reviewed receipts are merged");
  assert(list.children.some(row=>row.children[0]?.textContent==="Lesson available"));
  assert(list.children.some(row=>row.children[0]?.textContent==="Account notice"));
  assert.equal(standard.root().getAttribute("data-mode"),"inbox",
    "unified notification view uses its own full-screen presentation");
  assert(!source.includes('data-pwa-tab="course"'),"no course/profile switch remains");
  const accountRows = standard.root().querySelector("#hsk-pwa-notice-list").children;
  assert(accountRows.some((row)=>row.attrs["data-payment-status"]==="approved"&&row.className.includes("is-approved")),
    "confirmed subscription receipts use the success color");
  assert(accountRows.some((row)=>row.attrs["data-payment-status"]==="rejected"&&row.className.includes("is-rejected")),
    "rejected subscription receipts use the error color");
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

  const feedbackOverlay = harness({action:{payment_id:105,status:"rejected",plan_type:"1_month"},
    feedbackOpen:true});
  await feedbackOverlay.loadAndTick();
  assert.equal(feedbackOverlay.root().hidden,true,"active feedback dialog must not lose focus to payment alert");

  const typingField = harness({action:{payment_id:106,status:"rejected",plan_type:"1_month"},
    inputFocused:true});
  await typingField.loadAndTick();
  assert.equal(typingField.root().hidden,true,"focused iOS input keyboard must not lose focus");

  const browserTab = harness({standalone:false});
  await browserTab.window.HskPwaInbox.open();
  assert.equal(browserTab.root().querySelector("#hsk-pwa-push-view").hidden,true,
    "push consent control is hidden outside installed standalone mode");
  assert(!browserTab.requests.some((request)=>request.url.endsWith("/push/status")),
    "ordinary Safari tab does not query for push subscription state");

  const firstOpenStorage = new Map();
  const firstOpen = harness({standalone:true,sharedStorage:firstOpenStorage});
  await firstOpen.loadAndTick();
  assert.equal(firstOpen.root().querySelector("#hsk-pwa-push-view").hidden,false,
    "first installed PWA open automatically offers the in-app push consent screen");
  assert.equal(firstOpen.permissionFetchCount(),null,
    "first-load prompt does not open the iOS permission sheet without a tap");
  assert.equal(firstOpenStorage.get("hskai:pwa:push-prompt-seen:v1:7"),"1",
    "first prompt state is scoped to the verified account");

  const delayedFirstOpen = harness({standalone:true,splashReady:false});
  await delayedFirstOpen.loadAndTick();
  assert.equal(delayedFirstOpen.root().querySelector("#hsk-pwa-push-view").hidden,true,
    "permission prompt waits while the course splash is active");
  delayedFirstOpen.setSplashDone();
  await delayedFirstOpen.flushTimers();
  assert.equal(delayedFirstOpen.root().querySelector("#hsk-pwa-push-view").hidden,false,
    "first-load prompt resumes once the course is ready");

  const androidPwa = harness({standalone:true,vendor:"Google Inc."});
  await androidPwa.window.HskPwaInbox.open();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(androidPwa.root().querySelector("#hsk-pwa-push-view").hidden,true,
    "Apple-only Web Push consent is hidden in installed Android PWA");
  assert(!androidPwa.requests.some((request)=>request.url.endsWith("/push/status")),
    "installed Android PWA does not request Apple push configuration");

  const installed = harness({standalone:true});
  await installed.window.HskPwaInbox.open();
  await new Promise(resolve=>setImmediate(resolve));
  const pushControl = installed.root().querySelector("#hsk-pwa-push-view");
  assert.equal(pushControl.hidden,true,"the one-screen inbox never contains push access controls");
  assert.equal(installed.root().querySelector("#hsk-pwa-notice-list").hidden,false,
    "the inbox remains visible when push permission is missing");
  assert.equal(installed.permissionFetchCount(),null,"opening the inbox never requests OS permission");
  await installed.window.HskPwaInbox.openPushSettings();
  assert.equal(pushControl.hidden,false,"the Settings preference opens the separate push access screen");
  assert.equal(installed.root().querySelector("#hsk-pwa-notice-list").hidden,true,
    "push access controls stay outside the one-screen inbox");
  const requestCountBeforeEnable = installed.requests.length;
  assert.equal(installed.permissionFetchCount(),null,"permission is not requested before the Settings action tap");
  installed.root().listeners.click({target:{closest:(selector)=>selector==="#hsk-pwa-push-action"?{}:null}});
  for(let i=0;i<8 && !installed.requests.some((request)=>request.url.endsWith("/push/subscribe"));i++)
    await new Promise(resolve=>setImmediate(resolve));
  assert(installed.pushCalls.includes("permission"),"permission prompt starts in the trusted button gesture");
  assert(installed.pushCalls.indexOf("permission")<installed.pushCalls.findIndex((call)=>Array.isArray(call)&&call[0]==="subscribe"),
    "native permission is requested before browser subscription creation");
  assert.equal(installed.permissionFetchCount(),requestCountBeforeEnable,
    "the system permission prompt is requested directly from the Settings tap before subscription calls");
  assert(installed.pushCalls.some((call)=>Array.isArray(call)&&call[0]==="getRegistration"&&call[1]==="/iphone-pwa/"),
    "push manager is warmed only under the iPhone PWA scope");
  assert(installed.requests.some((request)=>request.url.endsWith("/push/subscribe")&&request.options.headers["X-HSK-PWA-CSRF"]==="csrf-token"),
    "subscription is sent through the existing CSRF-protected account session");
  for(let i=0;i<8 && installed.root().querySelector("#hsk-pwa-push-action").textContent!=="pwaPush.disable";i++)
    await new Promise(resolve=>setImmediate(resolve));
  assert.equal(installed.root().querySelector("#hsk-pwa-push-action").textContent,"pwaPush.disable",
    "server-confirmed subscription exposes one disable action");
  installed.root().listeners.click({target:{closest:(selector)=>selector==="#hsk-pwa-push-action"?{}:null}});
  for(let i=0;i<8 && !installed.requests.some((request)=>request.url.endsWith("/push/revoke"));i++)
    await new Promise(resolve=>setImmediate(resolve));
  assert(installed.requests.some((request)=>request.url.endsWith("/push/revoke")&&request.options.headers["X-HSK-PWA-CSRF"]==="csrf-token"),
    "disable revokes the server-owned device subscription with CSRF");
  assert(installed.pushCalls.includes("unsubscribe"),"disable also removes the local browser subscription");

  const denied = harness({standalone:true,permission:"denied"});
  await denied.window.HskPwaInbox.open();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(denied.root().querySelector("#hsk-pwa-push-view").hidden,true,
    "a blocked permission never inserts an access card into the inbox");
  assert.equal(denied.root().querySelector("#hsk-pwa-notice-list").hidden,false,
    "the denied-permission inbox still shows its notices");
  await denied.window.HskPwaInbox.openPushSettings();
  assert.equal(denied.root().querySelector("#hsk-pwa-push-status").textContent,"pwaPush.blocked",
    "blocked browser permission is announced accessibly without requesting OS permission again");
  assert.equal(denied.root().querySelector("#hsk-pwa-push-action").hidden,true);
  denied.root().listeners.click({target:{closest:(selector)=>selector==="#hsk-pwa-push-later"?{}:null}});
  await denied.window.HskPwaInbox.open();
  assert.equal(denied.root().querySelector("#hsk-pwa-push-view").hidden,true,
    "reopening the inbox never moves the Settings access screen into notices");
  assert(!denied.pushCalls.includes("permission"),
    "a blocked iOS permission is never re-requested without the user going to Settings");
  const settingsPush = harness({standalone:true});
  await settingsPush.window.HskPwaInbox.openPushSettings();
  assert.equal(settingsPush.root().querySelector("#hsk-pwa-push-view").hidden,false,
    "the Settings row opens the same existing push preference screen");
  assert.equal(settingsPush.permissionFetchCount(),null,
    "opening Settings never requests iOS permission before the enable tap");

  const pushRoute = harness({href:"https://app.example.test/iphone-pwa/course?notice=1&lang=uz#lesson",
    action:{payment_id:120,status:"rejected",plan_type:"1_month"}});
  await pushRoute.loadAndTick();
  assert.deepEqual(pushRoute.historyCalls[0].url,"/iphone-pwa/course?lang=uz#lesson",
    "push deep link is removed while language and fragment are preserved");
  assert.equal(pushRoute.root().hidden,false,"push click opens the server-owned latest rejection");

  const intentionalInbox = harness({
    action:{payment_id:107,status:"rejected",plan_type:"1_month"}
  });
  await intentionalInbox.window.HskPwaInbox.open();
  await intentionalInbox.callbacks.pageshow({persisted:true});
  intentionalInbox.window.HskPwaInbox.close();
  await intentionalInbox.flushTimers();
  assert.equal(intentionalInbox.root().hidden,true,
    "a learner-opened inbox must not queue a payment alert behind it");

  console.log("PWA notice UI: 28 behavior/ownership/safety checks passed");
}
main().catch((err)=>{console.error(err);process.exitCode=1;});
