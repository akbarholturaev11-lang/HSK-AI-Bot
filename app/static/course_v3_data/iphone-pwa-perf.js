/* Optional iPhone PWA QA profiler. No network sends, user IDs, URL queries or storage.
   Enable with /iphone-pwa/course?pwa_perf=1 and inspect HskPwaPerf.snapshot().
   This is a diagnostic aid, NOT an iPhone or production load-time benchmark. */
(function(root) {
  "use strict";
  if (!root.location || root.location.pathname !== "/iphone-pwa/course" ||
      !root.performance || !root.App || typeof root.App.show !== "function") return;
  var events = [], maximum = 240;
  var perf = root.performance;
  var now = function() { return perf.now(); };
  function add(kind, name, duration, detail) {
    var item = {kind:kind, name:String(name).slice(0,72),
      duration_ms:Math.max(0,Math.round(Number(duration)||0)),
      at_ms:Math.round(now())};
    if (detail && typeof detail === "object") item.detail=detail;
    events.push(item);
    if (events.length > maximum) events.shift();
  }
  function pathLabel(entry) {
    try {
      var u = new URL(entry.name);
      if (u.origin !== root.location.origin) return "external";
      var p = u.pathname;
      if (/^\/api\/v3\/pwa(?:-auth)?\//.test(p)) return p.replace(/\/[0-9]+(?=\/|$)/g,"/:id");
      if (/^\/iphone-pwa(?:\/|$)/.test(p)) return p;
      if (/^\/course_v3_data\//.test(p)) return "bundle";
      if (/^\/audio\//.test(p)) return "audio";
      if (/^\/assets\//.test(p)) return "asset";
      return "other";
    } catch (_) { return "other"; }
  }
  var originalShow = root.App.show;
  root.App.show = function(section) {
    var started = now(), args=arguments, result;
    try { result=originalShow.apply(this,args); }
    finally {
      var first = now();
      add("tab-handler", String(section||"unknown"), first-started);
      root.requestAnimationFrame(function(){
        root.requestAnimationFrame(function(){
          add("tab-paint", String(section||"unknown"), now()-started);
        });
      });
    }
    return result;
  };
  try {
    if (root.PerformanceObserver) {
      var observer = new root.PerformanceObserver(function(list) {
        list.getEntries().forEach(function(entry) {
          if (entry.entryType==="longtask" && entry.duration >= 50)
            add("longtask","main-thread",entry.duration);
          if (entry.entryType==="resource" && entry.duration >= 200) {
            add("resource",pathLabel(entry),entry.duration,{
              size_bytes:Math.max(0,Math.round(Number(entry.transferSize)||0)),
              response_end_ms:Math.round(entry.responseEnd||0)
            });
          }
        });
      });
      try { observer.observe({entryTypes:["longtask","resource"]}); } catch (_) {}
    }
  } catch (_) {}
  root.HskPwaPerf=Object.freeze({
    snapshot:function() {
      var groups={};
      events.forEach(function(e) {
        var key=e.kind+":"+e.name;
        (groups[key]||(groups[key]=[])).push(e.duration_ms);
      });
      var summaries=Object.keys(groups).sort().map(function(key) {
        var s=groups[key].sort(function(a,b){return a-b;});
        return {metric:key,count:s.length,median_ms:s[Math.floor((s.length-1)/2)],
          p95_ms:s[Math.floor((s.length-1)*.95)],max_ms:s[s.length-1]};
      });
      return {samples:events.slice(),summary:summaries,notes:
        "QA-only main-thread/PerformanceObserver readings; use real iPhone device and network waterfall for validation."};
    },
    clear:function(){events.length=0}
  });
})(window);
