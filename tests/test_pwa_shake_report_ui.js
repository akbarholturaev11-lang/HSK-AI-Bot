/* Tests the actual PWA movement detector and JS/browser integration boundaries. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = "app/static/course_v3_data/iphone-pwa-shake-report.js";
const js = fs.readFileSync(path, "utf8");
new vm.Script(js, {filename:path});
const page = fs.readFileSync("app/static/course-v3.html", "utf8");
const backend = fs.readFileSync("app/api/pwa_auth.py", "utf8");
assert(page.includes('src="/course_v3_data/iphone-pwa-shake-report.js'));
assert(page.includes('href="/course_v3_data/iphone-pwa-shake-report.css'));
assert(page.includes("window.HskPwaShake.settingsRowHtml()"));
assert(js.includes('var onCourse = location.pathname === "/iphone-pwa/course"'));
assert(js.includes("navigator.standalone"));
assert(js.includes('matchMedia("(display-mode: standalone)")'));
assert(js.includes('DeviceMotionEvent.requestPermission()'));
assert(js.includes('"/course_v3_data/vendor/html2canvas.min.js?v=1"'));
assert(!js.includes("cdnjs.cloudflare.com"));
assert(js.includes('verifiedActor().then(function (session)'));
assert(js.includes('localStorage.getItem(storageKey())'));
assert(js.includes('desired = value.enabled !== false'));
assert(js.includes("owner = id"));
assert(js.includes("manual: startReport"));
assert(js.includes("previouslyGranted = true"));
assert(js.includes("reportDescription = previous.value"));
assert(js.includes("reportDescription = textarea.value"));
assert(js.includes("async function captureViewport()"));
assert(js.includes('var generation = ++epoch'));
assert(js.includes("function confirmReport()"));
assert(js.indexOf("function confirmReport()") < js.indexOf("function formReport()"));
assert(js.includes('screenshot_data_url: snapshot && (!checked || checked.checked) ? snapshot : ""'));
assert(js.includes('await fetch("/api/v3/pwa/bug-report"'));
assert(js.includes('method:"POST"'));
assert(js.includes('"X-HSK-PWA-CSRF":session.csrf'));
assert(!js.includes('"X-Telegram-Init-Data"'));
assert(backend.includes('@router.post("/api/v3/pwa/bug-report")'));
assert(backend.includes('await PwaAuthService(db, settings_obj).mutation_actor('));
assert(backend.includes("await reserve_native_report("));
assert(backend.includes("screenshot.startswith(b"));

// Exercise the original motion function with deterministic acceleration traces.
const start = js.indexOf("  function onMotion(event) {");
const end = js.indexOf("  function permissionClick()", start);
assert(start > 0 && end > start);
const originalDetector = js.slice(start, end);
const harnessCode = "var listening=true,root={hidden:true},desired=true,permitted=true;" +
  "var sampleReady=false,gx=0,gy=0,gz=0,above=false,firstPeak=null,lastShake=-100000,triggered=0;" +
  "function startReport(){triggered++;}\n" + originalDetector +
  "\nreturn {feed:function(x,y,z,t){onMotion({accelerationIncludingGravity:{x:x,y:y,z:z},timeStamp:t});}," +
  "count:function(){return triggered;},disable:function(){desired=false;}};";
const harness = new Function(harnessCode)();
harness.feed(0,0,9.81,1);
harness.feed(0,0,31,200);
assert.equal(harness.count(),0,"a single bump must not report");
harness.feed(0,0,9.81,270);
harness.feed(0,0,31,580);
assert.equal(harness.count(),1,"two deliberate peaks open one report");
harness.feed(0,0,9.81,790);
harness.feed(0,0,31,1100);
harness.feed(0,0,9.81,1150);
harness.feed(0,0,31,1300);
assert.equal(harness.count(),1,"cooldown suppresses repeat triggers");
harness.disable();
harness.feed(0,0,9.81,7000);
harness.feed(0,0,31,7200);
assert.equal(harness.count(),1,"OFF disables detector");
console.log("PWA shake report: syntax, gesture trace, permission, capture and API wiring checks passed");
