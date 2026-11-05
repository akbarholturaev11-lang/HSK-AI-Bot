/* Tests the actual PWA movement detector and JS/browser integration boundaries. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = "app/static/course_v3_data/iphone-pwa-shake-report.js";
const js = fs.readFileSync(path, "utf8");
new vm.Script(js, {filename:path});
const page = fs.readFileSync("app/static/course-v3.html", "utf8");
const checkout = fs.readFileSync("app/static/subscription.html", "utf8");
const css = fs.readFileSync("app/static/course_v3_data/iphone-pwa-shake-report.css", "utf8");
const backend = fs.readFileSync("app/api/pwa_auth.py", "utf8");
assert(page.includes('src="/course_v3_data/iphone-pwa-shake-report.js'));
assert(page.includes('href="/course_v3_data/iphone-pwa-shake-report.css'));

for (const [name, html] of [
  ["course-v3.html", page],
  ["subscription.html", checkout]
]) {
  // Parse all inline scripts; catching syntax faults in unrelated course code.
  const tags = /<script\b([^>]*)>([\s\S]*?)<\/script>/g;
  let match, parsed = 0;
  while ((match = tags.exec(html)) !== null) {
    if (match[1].includes("application/json") || !match[2].trim()) continue;
    new vm.Script(match[2], {filename:name + ":inline-" + parsed});
    parsed++;
  }
  assert(parsed >= 1, name + " must contain parsed inline JS");
}

assert(page.includes("window.HskPwaShake.settingsRowHtml()"));
// Practice opens as an in-document iframe layer (no full-page navigation).
assert(page.includes('layer.id="pwa-practice-layer"'));
assert(page.includes("entry.innerHTML=renderStudyPreparing()"));
assert(js.includes('var onCourse = location.pathname === "/iphone-pwa/course"'));
assert(js.includes("navigator.standalone"));
assert(js.includes("window.parent !== window || window.HskPwaShake"),"nested PWA iframes cannot open duplicate sheets");
assert(js.includes('"#pwa-checkout-layer, #sheet.on, #paywall.on, #flow.on, "'),"embedded checkout and modal overlays block automatic capture");
assert(js.includes('var renderer = await loadRenderer();') && js.includes('safeReportCaptureSurface(expectedScreen)'),"privacy checked at each async capture boundary");
assert(js.includes('if (!safeReportCaptureSurface(expectedScreen)) return null;'),"privacy prevents automatic capture on sensitive surfaces");
assert(js.includes('if (onCourse && (screen !== expectedScreen ||'),"tab switch invalidates in-progress capture");
assert(js.includes('canvas.width = 0; canvas.height = 0;'),"privacy-rejected canvas memory is released");
assert(js.includes('backTarget: function () { return root.hidden ? null : root; }'),"sheet exposes back stack target");
assert(js.includes('close: close'),"sheet back dispatch closes only the active report");
assert(page.includes('{id:"pwa-shake",target:function(){return PWA_COURSE_HOST&&window.HskPwaShake&&HskPwaShake.backTarget()}'),"shake report has PWA-only back priority");
assert(page.indexOf('{id:"pwa-shake"') < page.indexOf('{id:"pwa-checkout-layer"'),"report closes before checkout");
assert(js.includes('matchMedia("(display-mode: standalone)")'));
assert(js.includes('DeviceMotionEvent.requestPermission()'));
assert(js.includes('"/course_v3_data/vendor/html2canvas.min.js?v=1"'));
assert(!js.includes("cdnjs.cloudflare.com"));
assert(js.includes('verifiedActor().then(function (session)'));
assert(js.includes('localStorage.getItem(storageKey())'));
assert(js.includes('desired = value.enabled === true'));
assert(js.includes("owner = id"));
assert(js.includes("manual: startReport"));
assert(js.includes("previouslyGranted = true"));
assert(js.includes("reportDescription = previous.value"));
assert(js.includes("reportDescription = textarea.value"));
assert(js.includes("selectionId === imageSelectionSerial"),"only latest manual screenshot decode may update visible form");
assert(js.includes('stage === "form" && !root.hidden'),"closed report rejects stale manual image callbacks");
assert(js.includes("async function captureViewport()"));
assert(js.includes('var generation = ++epoch'));
assert(!js.includes("function introduction()"),"no unsolicited first-run permission modal");
assert(!js.includes("function confirmReport()"),"shake must enter form directly");
assert(!js.includes('makeButton("later"'),"no redundant Not now button");
assert(!js.includes("showSettingsPermission()"),"OS permission comes from the setting switch tap");
assert(js.includes("formReport();\n    captureViewport()"),"sheet opens before async screenshot capture");
assert(js.includes('role="switch" aria-checked="'),"accessible single settings switch");
assert(js.includes('closeButton.hidden = step === "sent"'),"avoid duplicate close on success");
const settings = js.slice(js.indexOf("function settingsRowHtml()"),js.indexOf("function toggle()"));
assert.equal((settings.match(/<button/g)||[]).length,1,"one settings control only");
assert(css.includes("align-items:flex-end"),"report anchored to bottom");
assert(css.includes('max-height:min(88dvh,820px)'),"sheet fits available viewport");
assert(checkout.includes("html.hsk-pwa-browser .bottom{padding-bottom:max(30px,env(safe-area-inset-bottom,0px))}"),"PWA checkout maintains home-indicator clearance without duplicate reserve");
assert(page.includes("html.hsk-pwa-browser #pwa-checkout-layer{padding-bottom:0}"),"parent embedded checkout must not reserve bottom safe area twice");
assert(!checkout.includes("html.hsk-pwa-browser .bottom{bottom:-"),"avoid unsafe offscreen positioning");
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
const end = js.indexOf("  function refreshSettingsControl()", start);
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
// PWA-only session revalidation: network/5xx must not turn into logout.
// An actual 401/owner switch still redirects inside each verifier.
for (const [file, verifier] of [
  ["course_v3_recognition.html", "recognitionPwaSession"],
  ["course_v3_pronunciation.html", "pronunciationPwaSession"],
  ["course_v3_memorize.html", "memorizePwaSession"],
  ["course_v3_test.html", "testPwaActor"],
  ["course_v3_mistakes.html", "mistakesPwaSession"],
  ["subscription.html", "checkoutPwaActor"],
]) {
  const html = fs.readFileSync("app/static/" + file, "utf8");
  assert(html.includes(verifier + '().catch(function(error){'),file + ": explicit retry guard");
  // Framed practice pages return to sign-in through practiceSignIn().
  assert(/if\(error&&error\.message==="pwa_session_invalid"\)(location\.replace\("\/iphone-pwa"\)|practiceSignIn\(\))/.test(html),
    file + ": invalid actor fails closed");
  assert(/if\(r\.status===401\)\{(location\.replace\("\/iphone-pwa"\)|practiceSignIn\(\))/.test(html),
    file + ": confirmed 401 must redirect");
  assert(html.includes('src="/course_v3_data/iphone-pwa-shake-report.js'),
    file + ": reporting must be available beyond course");
}
for (const file of [
  "course_v3_recognition.html", "course_v3_pronunciation.html",
  "course_v3_memorize.html", "course_v3_test.html", "course_v3_mistakes.html",
]) {
  const html = fs.readFileSync("app/static/" + file, "utf8");
  assert(html.includes('src="/course_v3_data/iphone-pwa-practice-boot.js'),
    file + ": panda preparing should cover the initial exercise load");
}
console.log("PWA shake report: syntax, gesture trace, permission, capture and API wiring checks passed");
