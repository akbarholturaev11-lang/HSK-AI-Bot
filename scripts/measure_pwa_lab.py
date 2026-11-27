"""Repeatable learner PWA lab profile (docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md).

Serves the existing e2e ``ScreenPage`` fixture over real HTTP and measures, in
Chromium and WebKit:
- the course launch (``launch``);
- learner actions (``flows``): lesson open, one exercise advance and lesson
  finish; the five practice pages and Voice, first and repeat open; a Test
  exam start and a Mistakes review start. Each is timed in the page from the
  tap to its ready state, one frame later so it is painted, with how long the
  parent entry was the only thing visible and how long the panda showed;
- login, Li onboarding and course onboarding first paint (``entry``);
- task 1.3's baselines: tab switches at 320/390/430 (``tabs``); the first and
  repeat open of Dictionary, Phrases, Inbox and Settings, with when the
  embedded page first paints and when the parent's cover goes (``layers``);
  dictionary search per keystroke (``search``); swipe-back from a layer and a
  root tab (``swipe``); answer to feedback with the server answering now or
  held 1 s (``answers``); the limit/Pro sheet, trial and checkout layers
  (``pro``); today's pull-to-refresh (``refresh``); what each parser-blocking
  ``<head>`` resource costs the cold first paint, by lab-only removal
  (``blocking``); the launch filmstrip with the map answered or held
  (``film``); and ``telegram-web-app.js`` in the child pages (``sdk``).
Every action keeps the console errors and uncaught exceptions it raised.
Each action part starts from a cold launch whose icon font has arrived, and its context
drops the service worker's background warm-up: both happen on a first launch only, and an
action timed while they download would share the link with them. A first open therefore
means files not cached yet. ``layers`` and ``pro`` also time a returning learner's first open
after the warm-up, ``refresh`` pulls only as a returning learner, and ``launch`` times the
warm-up itself. Its warm launch is the steady state: the first launch under the worker's
control is a one-time switch, reported as ``takeover``.
Nothing here talks to production, real accounts or secrets: every API answer
is the e2e fixture, and the learner HTML is built by production's own code.

What makes the numbers comparable between runs and engines:
- production-like delivery, mirroring ``app/main.py`` and ``app/api/pwa_auth.py``:
  gzip for every body >= 1 KB (Starlette's GZipMiddleware), ``private,
  no-cache`` plus ETag/304 for HTML pages, ``immutable`` for versioned and
  ``/assets/`` files and the offline word-audio scripts, ``no-store`` for API
  answers, and the real service worker;
- the one third-party file (the cdnjs icon stylesheet and its fonts) is
  fetched once per run and then served through the same shaped link;
- one shared, server-side shaped link (150 ms to first byte, 1.6 Mbps down),
  so both engines see the same network; the run fails if the browser does not
  receive the production headers;
- Chromium also gets a 4x CPU slowdown. WebKit has no CPU throttle in
  Playwright, so its runs say ``cpu_slowdown: 1``.

TLS setup is not modelled; real-user launch timing covers it.

Usage (repository root):
    .venv/bin/python scripts/measure_pwa_lab.py
    .venv/bin/python scripts/measure_pwa_lab.py --engines webkit --widths 390 --runs 3
    .venv/bin/python scripts/measure_pwa_lab.py --parts flows,entry --runs 1
    .venv/bin/python scripts/measure_pwa_lab.py --parts layers,search --engines chromium --runs 1
A full run (``--parts all``, the default) takes about 41 minutes.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import mimetypes
import os
import re
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LATENCY_S = 0.150
DOWN_BYTES_PER_S = 1.6 * 1024 * 1024 / 8
CPU_SLOWDOWN = 4
HEIGHT = 844
IMMUTABLE = "public, max-age=31536000, immutable"
REVALIDATE = "private, no-cache"
GZIP_EXCLUDED = ("text/event-stream",)  # Starlette's default exclusion
EXTERNAL_HOSTS = ("cdnjs.cloudflare.com",)
STATIC = ROOT / "app/static"
# Production routes that serve a static file under another name (app/main.py).
ALIASED_ASSETS = {
    "/audio/words/client.js": STATIC / "audio/words-client.js",
    "/audio/words/index.js": STATIC / "audio/words-index.js",
}

# Recorded in the page from navigation start, so Playwright IPC never counts.
PAGE_PROBE = r"""
(function(){
  var types=(window.PerformanceObserver&&PerformanceObserver.supportedEntryTypes)||[];
  var lab=window.__lab={fcp:null,fcpAt:null,courseReady:null,icons:null,lcpEl:null,
    lcp:types.indexOf('largest-contentful-paint')<0?'unsupported':null,
    cls:types.indexOf('layout-shift')<0?'unsupported':0,
    slowestEvent:types.indexOf('event')<0?'unsupported':0,slowestEventName:null};
  lab.describe=function(el,up){if(!el||!el.tagName)return null;var s=el.tagName.toLowerCase();
    if(el.id)s+='#'+el.id;if(el.classList&&el.classList.length)s+='.'+Array.prototype.slice.call(el.classList,0,2).join('.');
    // A bare tag says little ("small"): name the nearest ancestor that has an id or class.
    if(!up&&s===el.tagName.toLowerCase())for(var p=el.parentElement,n=0;p&&n<4;p=p.parentElement,n++)
      if(p.id||(p.classList&&p.classList.length))return s+' in '+lab.describe(p,true);
    return s};
  try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){
    if(e.name==='first-contentful-paint'){lab.fcp=Math.round(e.startTime);lab.fcpAt=performance.timeOrigin+e.startTime}})})
    .observe({type:'paint',buffered:true})}catch(e){}
  if(lab.lcp!=='unsupported')try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){
    lab.lcp=Math.round(e.startTime);lab.lcpEl=lab.describe(e.element)||(e.url?'img '+e.url.split('?')[0]:null)})})
    .observe({type:'largest-contentful-paint',buffered:true})}catch(e){}
  if(lab.cls!=='unsupported')try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){
    if(!e.hadRecentInput)lab.cls+=e.value})}).observe({type:'layout-shift',buffered:true})}catch(e){}
  // The slowest event (INP proxy); "unsupported" where the engine has no Event Timing.
  if(lab.slowestEvent!=='unsupported')try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){
    if(e.duration>lab.slowestEvent){lab.slowestEvent=e.duration;lab.slowestEventName=e.name}})})
    .observe({type:'event',durationThreshold:16,buffered:true})}catch(e){}
  (function poll(){
    if(window.MAP&&MAP.authenticated&&window.PWA_COURSE_USER_ID){lab.courseReady=Math.round(performance.now());return}
    requestAnimationFrame(poll)})();
  // Tabler icons on screen: a loaded tabler font face, one frame later. check() on document.fonts
  // answers true when no face matches at all, so the faces are read one by one.
  if(location.pathname==='/iphone-pwa/course')(function icons(seen){
    if(seen){lab.icons=Math.round(performance.now());return}
    var ok=false;try{document.fonts.forEach(function(f){if(/tabler/i.test(f.family)&&f.status==='loaded')ok=true})}catch(e){}
    if(ok||performance.now()<60000)requestAnimationFrame(function(){icons(ok)})})(false);
  // Action timer (task 1.2). Times are epoch ms, so parent and child frames compare.
  var PANDA='.hsk-entry-overlay:not(.is-cancelled),.hsk-study-preparing-panda';
  lab.now=function(){return performance.timeOrigin+performance.now()};
  lab.visible=function(el){
    if(!el||!el.isConnected)return false;var r=el.getBoundingClientRect();
    if(r.width<1||r.height<1)return false;var s=el.ownerDocument.defaultView.getComputedStyle(el);
    return s.visibility!=='hidden'&&Number(s.opacity)>0.05};
  lab.frame=function(sel){return document.querySelector(sel||'#pwa-practice-layer iframe')};
  lab.frameLab=function(sel){var f=lab.frame(sel);try{return f&&f.contentWindow.__lab||null}catch(e){return null}};
  lab.childOf=function(sel,expr){var f=lab.frame(sel);if(!f||f.hidden)return false;
    try{return !!f.contentWindow.eval(expr)}catch(e){return false}};
  lab.child=function(expr){return lab.childOf(null,expr)};
  lab.pandaShown=function(){
    var docs=[document],f=lab.frame();
    if(f&&!f.hidden)try{if(f.contentDocument)docs.push(f.contentDocument)}catch(e){}
    return docs.some(function(d){return Array.prototype.some.call(d.querySelectorAll(PANDA),lab.visible)})};
  // Task 1.3: the looping (shimmer) animations under root, and how far apart their phases are.
  lab.shimmer=function(root){
    if(!root||!root.getAnimations)return null;
    var list=root.getAnimations({subtree:true}).filter(function(a){try{
      var t=a.effect.getComputedTiming();
      return a.playState==='running'&&t.iterations===Infinity&&a.effect.target&&lab.visible(a.effect.target)}catch(e){return false}});
    if(!list.length)return{count:0,names:[],spread_ms:0};
    var names={},phases=[],dur=null,mixed=false;
    list.forEach(function(a){var t=a.effect.getComputedTiming(),d=Number(t.duration)||1;
      names[a.animationName||'?']=1;if(dur===null)dur=d;else if(Math.abs(d-dur)>1)mixed=true;
      phases.push((Number(t.progress)||0)*dur)});
    phases.sort(function(x,y){return x-y});var gap=0;
    for(var i=0;i<phases.length;i++){var g=(i+1<phases.length?phases[i+1]:phases[0]+dur)-phases[i];if(g>gap)gap=g}
    return{count:list.length,names:Object.keys(names),spread_ms:Math.round(phases.length>1?dur-gap:0),mixed:mixed}};
  lab.arm=function(spec){
    var w=lab.w={start:null,ready:null,revealed:null,first:null,firstSeen:false,panda:0,pandaFirst:null,pandaOn:false,
      skel:0,skelFirst:null,skelOn:false,shimmer:null,last:null,done:false,timedOut:false};
    var fn=function(src){return src?new Function('lab','return ('+src+')'):null};
    var test=function(f){try{return !!f(lab)}catch(e){return false}};
    var ready=fn(spec.ready),first=fn(spec.first),reveal=fn(spec.reveal),skel=fn(spec.skel),shim=fn(spec.shimmer);
    var limit=spec.timeout||30000,armedAt=lab.now(),events=spec.events||['pointerdown'];
    w.mark=function(){if(w.start===null)w.start=lab.now()};
    var docs=[document],f=lab.frame(spec.frame);
    if(f)try{if(f.contentDocument)docs.push(f.contentDocument)}catch(e){}
    var listen=function(on){docs.forEach(function(d){events.forEach(function(n){
      if(on)d.addEventListener(n,w.mark,true);else d.removeEventListener(n,w.mark,true)})})};
    listen(true);
    (function tick(){
      var t=lab.now();
      if(w.start!==null){
        if(w.pandaOn)w.panda+=t-w.last;
        w.pandaOn=lab.pandaShown();if(w.pandaOn&&w.pandaFirst===null)w.pandaFirst=t-w.start;
        if(skel){
          if(w.skelOn)w.skel+=t-w.last;
          w.skelOn=test(skel);
          if(w.skelOn){if(w.skelFirst===null)w.skelFirst=t-w.start;
            if(shim){var s=null;try{s=lab.shimmer(shim(lab))}catch(e){}if(s&&(!w.shimmer||s.count>w.shimmer.count))w.shimmer=s}}}
        if(w.revealed===null){
          if(reveal){if(test(reveal))w.revealed=t-w.start}
          else{var pf=lab.frame();if(pf&&!pf.hidden)w.revealed=t-w.start}}
        if(first&&w.first===null){if(w.firstSeen)w.first=t-w.start;else if(test(first))w.firstSeen=true}
        // Ready is stamped one frame after the state is reached: by then it is painted.
        if(w.seen){w.ready=t-w.start;w.done=true;if(w.firstSeen&&w.first===null)w.first=w.ready}
        else{if(test(ready))w.seen=true;else if(t-w.start>limit){w.timedOut=true;w.done=true}}
        w.last=t;
      }else if(t-armedAt>limit){w.timedOut=true;w.done=true}
      if(w.done)listen(false);
      else requestAnimationFrame(tick)})()};
  lab.begin=function(){lab.w.mark()};
  lab.result=function(){var w=lab.w,r=function(v){return v===null||v===undefined?null:Math.round(v)};
    var out={ready_ms:r(w.ready),parent_only_ms:r(w.revealed),panda_ms:Math.round(w.panda),
      panda_first_ms:r(w.pandaFirst),timed_out:w.timedOut,start_at:w.start};
    if(w.first!==null)out.first_ms=r(w.first);
    if(w.skelFirst!==null){out.placeholder_ms=Math.round(w.skel);out.placeholder_first_ms=r(w.skelFirst)}
    if(w.shimmer){out.shimmer_count=w.shimmer.count;out.shimmer_spread_ms=w.shimmer.spread_ms;
      out.shimmer_names=w.shimmer.names.join(',')}
    return out};
  // Task 1.3 filmstrip: one entry [epoch ms, state] per change of classify(lab), each frame.
  lab.filmStart=function(classify,limit,stop){
    var fn=new Function('lab','return ('+classify+')'),film=lab.film={states:[],done:false};
    (function tick(){var t=lab.now(),s;try{s=String(fn(lab))}catch(e){s='error'}
      var last=film.states[film.states.length-1];if(!last||last[1]!==s)film.states.push([t,s]);
      if(s===(stop||'content')||t-film.states[0][0]>limit){film.done=true;return}
      requestAnimationFrame(tick)})()};
  // Task 1.3 swipe-back: NavBack gets one move per frame, as a finger would give it.
  lab.swipe=function(x0,x1,settled,steps){
    steps=steps||10;var ok=new Function('lab','return ('+settled+')');
    var touch=function(x){return{touches:[{clientX:x,clientY:420}],cancelable:true,target:document.body,
      edgeTarget:document.body,preventDefault:function(){}}};
    return new Promise(function(resolve){
      var t0=lab.now(),last=t0,frames=[],i=0,moved=null,movedSeen=false;
      NavBack.start(touch(x0));
      if(!NavBack._s){resolve({unmeasured:'NavBack did not start'});return}
      var el=NavBack._s.el;
      (function step(){var t=lab.now();frames.push(t-last);last=t;
        // The first frame after the drag moved the layer, stamped one frame later (painted).
        if(moved===null){if(movedSeen)moved=t-t0;else if(el.style.transform)movedSeen=true}
        if(i<steps){i++;NavBack.move(touch(x0+(x1-x0)*i/steps));requestAnimationFrame(step);return}
        var rel=lab.now();NavBack.end();
        (function wait(){var ready=false;try{ready=!!ok(lab)}catch(e){}
          if(ready){requestAnimationFrame(function(){var f=frames.slice(1).sort(function(a,b){return a-b});
            resolve({drag_first_frame_ms:moved===null?null:Math.round(moved),release_to_settled_ms:Math.round(lab.now()-rel),
              frame_p95_ms:Math.round(f[Math.min(f.length-1,Math.floor(f.length*0.95))]||0),frame_max_ms:Math.round(f[f.length-1]||0)})});return}
          if(lab.now()-rel>5000){resolve({unmeasured:'did not settle within 5 s'});return}
          requestAnimationFrame(wait)})()})()})};
})();
"""


class Link:
    """One shared downstream link: concurrent responses split its bandwidth."""

    def __init__(self, bytes_per_s: float):
        self.rate = bytes_per_s
        self.lock = threading.Lock()
        self.free_at = 0.0

    def send(self, wfile, data: bytes, chunk: int = 8192) -> None:
        for start in range(0, len(data), chunk):
            part = data[start:start + chunk]
            with self.lock:
                now = time.monotonic()
                self.free_at = max(now, self.free_at) + len(part) / self.rate
                done_at = self.free_at
            delay = done_at - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            wfile.write(part)


class _Frame:
    parent_frame = None


class _Request:
    """The slice of Playwright's Request that the e2e fixtures read."""

    def __init__(self, url: str, method: str, body: bytes, headers: dict):
        self.url = url
        self.method = method
        self.frame = _Frame()
        self.headers = {k.lower(): v for k, v in headers.items()}
        self._body = body

    @property
    def post_data_json(self):
        try:
            return json.loads(self._body or b"{}")
        except ValueError:
            return {}

    @property
    def post_data(self):
        return (self._body or b"").decode("utf-8", "replace")


class _Route:
    """Playwright Route stand-in that writes a production-like HTTP response."""

    def __init__(self, server: "LabServer", handler: BaseHTTPRequestHandler, request: _Request):
        self.server = server
        self.handler = handler
        self.request = request
        self.done = False

    def fulfill(self, status=200, content_type=None, body=None, path=None, json=None, headers=None):
        import json as _json
        if json is not None:
            body = _json.dumps(json)
            content_type = content_type or "application/json"
        if path is not None:
            body = Path(path).read_bytes()
            content_type = content_type or mimetypes.guess_type(path)[0] or "application/octet-stream"
        if isinstance(body, str):
            body = body.encode("utf-8")
        body = body or b""
        ctype = content_type or "text/plain"
        parts = urlsplit(self.request.url)
        out = {"Content-Type": ctype, **(headers or {})}
        given = {key.lower() for key in out}
        if ctype.startswith("text/html"):
            for host in EXTERNAL_HOSTS:
                body = body.replace(f"https://{host}/".encode(), f"/__ext/{host}/".encode())
        if "cache-control" in given:
            pass  # a production page builder already chose (no-store, or no-cache + ETag)
        elif status == 200 and ctype.startswith("text/html"):
            etag = 'W/"' + hashlib.sha256(body).hexdigest()[:32] + '"'
            out.update({"Cache-Control": REVALIDATE, "ETag": etag})
            sent = self.request.headers.get("if-none-match", "")
            if sent.removeprefix("W/") == etag.removeprefix("W/"):
                self._write(304, {"Cache-Control": REVALIDATE, "ETag": etag}, b"")
                return
        elif ("v=" in parts.query or parts.path.startswith(("/assets/", "/__ext/"))
              or parts.path in ALIASED_ASSETS):
            out["Cache-Control"] = IMMUTABLE
        else:
            out.setdefault("Cache-Control", "no-store")
        accepts_gzip = "gzip" in self.request.headers.get("accept-encoding", "")
        if (len(body) >= 1024 and accepts_gzip and "content-encoding" not in given
                and not ctype.startswith(GZIP_EXCLUDED)):
            body = gzip.compress(body, compresslevel=9)
            out["Content-Encoding"] = "gzip"
        self._write(status, out, body)

    def _write(self, status: int, headers: dict, body: bytes) -> None:
        time.sleep(LATENCY_S)
        handler = self.handler
        handler.send_response(status)
        for key, value in headers.items():
            handler.send_header(key, value)
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        if body:
            self.server.link.send(handler.wfile, body)
        self.server.note(self.request.url, status, len(body))
        self.done = True

    def abort(self, *_):
        self.fulfill(status=502, body="aborted")

    def continue_(self):
        self.fulfill(status=404, body="not found")


class LabServer:
    HOST = "127.0.0.1"

    def __init__(self, fixture, port: int = 0):
        self.fixture = fixture
        self.link = Link(DOWN_BYTES_PER_S)
        self.external: dict[str, tuple[bytes, str] | None] = {}
        self.external_lock = threading.Lock()
        self.log: list[dict] = []
        self.log_lock = threading.Lock()
        lab = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _go(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                url = f"http://{LabServer.HOST}:{lab.port}{self.path}"
                route = _Route(lab, self, _Request(url, self.command, body, dict(self.headers)))
                try:
                    lab.serve(route)
                except Exception as exc:  # a fixture assertion must not stall the page
                    if not route.done:
                        route.fulfill(status=500, body=str(exc)[:200])
                if not route.done:
                    # Held fixture routes (e.g. lesson completion) are not in this profile.
                    route.fulfill(status=503, json={"ok": False, "error": "lab_held"})

            do_GET = do_POST = do_PUT = do_DELETE = _go

            def handle(self):
                try:
                    super().handle()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer((self.HOST, port), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.origin = f"http://{self.HOST}:{self.port}"

    def serve(self, route: _Route) -> None:
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/sw.js":
            # The real worker, with production's own headers (app/api/pwa_auth.py).
            route.fulfill(path=str(ROOT / "app/static/iphone-pwa-sw.js"),
                          content_type="application/javascript",
                          headers={"Cache-Control": "no-store",
                                   "Service-Worker-Allowed": "/iphone-pwa/"})
            return
        if path in ALIASED_ASSETS:
            route.fulfill(path=str(ALIASED_ASSETS[path]), content_type="application/javascript")
            return
        if path.startswith("/__ext/"):
            self.serve_external(route, path)
            return
        self.fixture.serve(route)

    def serve_external(self, route: _Route, path: str) -> None:
        """Third-party files: real bytes, fetched once, then the shaped link."""
        host, _, rest = path.removeprefix("/__ext/").partition("/")
        if host not in EXTERNAL_HOSTS:
            route.fulfill(status=404, body="unknown host")
            return
        url = f"https://{host}/{rest}"
        with self.external_lock:
            if url not in self.external:
                request = urllib.request.Request(url, headers={"Accept-Encoding": "identity",
                                                               "User-Agent": "hsk-pwa-lab"})
                try:
                    with urllib.request.urlopen(request, timeout=20) as answer:
                        self.external[url] = (answer.read(), answer.headers.get_content_type())
                except OSError:
                    self.external[url] = None
            cached = self.external[url]
        if cached is None:
            route.fulfill(status=204, body="")
            return
        route.fulfill(body=cached[0], content_type=cached[1])

    def unavailable_external(self) -> list[str]:
        with self.external_lock:
            return sorted(url for url, value in self.external.items() if value is None)

    def note(self, url: str, status: int, size: int) -> None:
        # Diagnostics beacons (clientlog, including the 1.4 launch beacon) are not part of the
        # learner's path, and would add a request to whichever window they happen to land in.
        if urlsplit(url).path == "/api/v3/clientlog":
            return
        with self.log_lock:
            self.log.append({"path": urlsplit(url).path + ("?v" if "?v=" in url else ""),
                             "status": status, "bytes": size})

    def take_log(self) -> list[dict]:
        with self.log_lock:
            log, self.log = self.log, []
        return log

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *_):
        self.httpd.shutdown()
        self.httpd.server_close()


COURSE_PATH = "/iphone-pwa/course?lang=uz&onboarded=1"
GUEST_COOKIE = "hsk_lab_guest=1"  # the lab's signed-out visitor (login, Li onboarding)
PRACTICE_PAGES = {
    "recognition": "course_v3_recognition.html",
    "memorize": "course_v3_memorize.html",
    "pronunciation": "course_v3_pronunciation.html",
    "test": "course_v3_test.html",
    "mistakes": "course_v3_mistakes.html",
    "voice": "iphone-pwa-voice.html",
}
ENTRY_FILES = {  # production FileResponse routes in app/api/pwa_auth.py
    "/iphone-pwa": "iphone-pwa-login.html",
    "/iphone-pwa/onboarding": "course_v3_onboarding.html",
    "/iphone-pwa/onboarding/li": "course_v3_li_onboarding.html",
}
LAYER_FILES = {  # embedded layers, built like production (task 1.3)
    "/iphone-pwa/dictionary": "hsk-lugat.html",
    "/iphone-pwa/phrases": "hsk-gaplar.html",
    "/iphone-pwa/checkout": "subscription.html",
}
HEAD_TAG = r"<(script|link)\b[^>]*>"


def head_blocking_resources(html: str) -> list[str]:
    """The parser-blocking scripts and stylesheets in ``<head>``, in document order."""
    head = html[:html.find("</head>")] if "</head>" in html else html
    found = []
    for match in re.finditer(HEAD_TAG, head, re.I):
        tag = match.group(0)
        if match.group(1).lower() == "script":
            src = re.search(r'\bsrc="([^"]+)"', tag)
            if src and not re.search(r"\b(defer|async)\b|type=\"module\"", tag):
                found.append(src.group(1))
        elif re.search(r'\brel="stylesheet"', tag) and not re.search(r'\bmedia="print"|\bdisabled\b', tag):
            href = re.search(r'\bhref="([^"]+)"', tag)
            if href:
                found.append(href.group(1))
    return found


def strip_resources(html: str, urls) -> str:
    """The page without the given ``<head>`` scripts/stylesheets (lab-only cost reading)."""
    cut = html.find("</head>")
    head, rest = (html[:cut], html[cut:]) if cut >= 0 else (html, "")
    for url in urls:
        quoted = re.escape(url)
        head = re.sub(r'<script\b[^>]*\bsrc="' + quoted + r'"[^>]*>\s*</script>\s*', "", head)
        head = re.sub(r'<link\b[^>]*\bhref="' + quoted + r'"[^>]*>\s*', "", head)
    return head + rest


def flow_fixture(lang: str = "uz"):
    """The e2e ``ScreenPage`` fixture, extended to drive task 1.2's actions.

    Pages are the bytes production sends: the learner HTML comes from
    ``app/api/pwa_auth.py``'s own builders, the exam from the exam service's
    own material helpers. Lesson completion is answered instead of held.
    Imported lazily so the CI guard can import this module without the app.
    """
    import types
    from starlette.datastructures import QueryParams
    from app.api import pwa_auth
    from app.services.course_hsk_exam_service import CourseHskExamService
    from app.services.course_question_material import (
        public_questions_projection, shuffle_exam_questions)
    from tests.e2e.test_pwa_screen_alignment import ScreenPage

    def body_of(response) -> bytes:
        # _pwa_html answers with a FileResponse (its bytes are the file); the inline builder with bytes.
        return Path(response.path).read_bytes() if hasattr(response, "path") else bytes(response.body)

    def built(route, response, drop=(), content_type="text/html; charset=utf-8"):
        headers = {k: v for k, v in response.headers.items()
                   if k.lower() not in ("content-length", "content-type")}
        body = body_of(response)
        if drop and response.status_code == 200:
            # A lab-only variant: its own ETag, so no cache ever mixes it with the real page,
            # and a 304 for it, like the production page gets for its own ETag.
            body = strip_resources(body.decode("utf-8"), drop).encode("utf-8")
            tag = hashlib.sha1(repr(sorted(drop)).encode()).hexdigest()[:8]
            headers = {k: (v[:-1] + "-lab-" + tag + '"' if k.lower() == "etag" else v) for k, v in headers.items()}
            etag = next((v for k, v in headers.items() if k.lower() == "etag"), None)
            if etag and etag in route.request.headers.get("if-none-match", ""):
                route.fulfill(status=304, content_type=content_type, body=b"", headers=headers)
                return
        route.fulfill(status=response.status_code, content_type=content_type, body=body, headers=headers)

    def exam_session():
        material = CourseHskExamService.load_material("hsk1", lang)
        issued = CourseHskExamService._inflate_grading_snapshot(
            CourseHskExamService._grading_snapshot(
                shuffle_exam_questions(material["questions"], "lab-exam")),
            level="hsk1", lang=lang)
        return {"id": "hsk-exam:lab", "level": "hsk1",
                "duration_min": int(material["duration_min"]),
                "pass_score": int(material["pass_score"]),
                "questions": public_questions_projection(issued)}

    def review_session():
        # The shape CourseMistakeService.start_review returns (render fields only).
        words = []
        for order in (1, 2, 3):
            lesson = json.loads((STATIC / f"course_v3_data/hsk1/lesson_{order:02d}.json").read_text())
            words += [w for w in lesson.get("active_words", []) if isinstance(w, dict)]
        words = [w for w in words if w.get("zh") and isinstance(w.get("meaning"), dict)][:10]
        prompt = {"uz": "Ma'noni tanlang", "ru": "Выберите значение", "tj": "Маъноро интихоб кунед"}[lang]
        meanings = [w["meaning"][lang] for w in words]
        questions = [{"id": f"lab-review:{i}", "format": "meaning_choice", "category": "word",
                      "prompt": prompt, "sentence": w["zh"], "pinyin": w.get("pinyin", ""),
                      "audio_text": w["zh"],
                      "options": [meanings[(i + k) % len(meanings)] for k in range(4)]}
                     for i, w in enumerate(words)]
        return {"id": "mistake-review:lab", "version": 2, "category": "all",
                "targets": len(questions), "questions": questions}

    def adaptive_plan():
        # The shape CourseAdaptiveLessonService returns: one meaning_choice item per slot.
        words = [w for w in json.loads((STATIC / "course_v3_data/hsk1/lesson_01.json").read_text())
                 .get("active_words", []) if isinstance(w, dict) and isinstance(w.get("meaning"), dict)][:4]
        meanings = [w["meaning"][lang] for w in words]
        items = [{"id": f"lab-ad:{i}", "answered": False, "question": {
            "id": f"lab-ad-q:{i}", "format": "meaning_choice", "prompt": "Ma'noni tanlang",
            "sentence": w["zh"], "pinyin": w.get("pinyin", ""),
            "options": [meanings[(i + k) % len(meanings)] for k in range(len(meanings))]}}
                 for i, w in enumerate(words)]
        return {"id": "lab-plan", "items": items}

    def leaderboard():
        names = ["Aziza", "Bekzod", "Dilnoza", "Farrux", "Gulnora", "Jasur", "Kamola", "Laziz", "Madina", "Nodir"]
        rows = [{"rank": r, "is_current_user": r == 7, "name": names[(r - 1) % len(names)] + ("" if r <= 10 else f" {r}"),
                 "total_xp": 3000 - r * 90, "weekly_xp": 900 - r * 25, "level": "hsk1"} for r in range(1, 31)]
        return {"ok": True, "league": "zhuque", "league_size": len(rows), "rank": 7, "xp": 2370, "weekly_xp": 725,
                "streak": 3, "weekly_reset_seconds": 3 * 86400, "week_activity_dates": [], "leaderboard": rows}

    def overview():
        # The fields iphone-pwa-inline-pro.js reads from /api/v3/pwa/subscription/overview.
        return {"ok": True, "access": {"is_paid": False, "state": "FREE"}, "pending_payment": None,
                "learning_pro_eligible": False,
                "lava": {"mode": "lava_or_manual", "email": "", "blocked_reason": None, "plans": [
                    {"plan_type": "1_month", "amount": 99000, "currency": "UZS"},
                    {"plan_type": "3_months", "amount": 249000, "currency": "UZS"},
                    {"plan_type": "12_months", "amount": 790000, "currency": "UZS"}]}}

    class FlowPage(ScreenPage):
        def __init__(self):
            super().__init__(lang)
            self.exam = exam_session()
            self.review = review_session()
            self.lesson_completions = 0
            # Task 1.3 controls, set by the part that needs them.
            self.holds: dict[str, float] = {}  # path -> extra seconds before the answer (a held server)
            self.drop: tuple = ()  # <head> resources removed from built pages (cost readings)
            self.adaptive_enabled = False  # production's adaptive flag is off today

        def page_html(self, path_qs: str) -> str:
            """The HTML production builds for ``path_qs`` (course, dictionary or phrases)."""
            parts = urlsplit(path_qs)
            fake = types.SimpleNamespace(headers={"if-none-match": ""}, query_params=QueryParams(parts.query))
            if parts.path == "/iphone-pwa/course":
                response = pwa_auth._pwa_inline_html(fake, pwa_auth._PWA_COURSE_HTML, {})
            else:
                response = pwa_auth._pwa_html(fake, "app/static/" + LAYER_FILES[parts.path], {})
            return body_of(response).decode("utf-8")

        def course_html(self) -> str:
            return self.page_html(COURSE_PATH)

        def serve(self, route):
            request = route.request
            parts = urlsplit(request.url)
            path = parts.path
            guest = GUEST_COOKIE in request.headers.get("cookie", "")
            fake = types.SimpleNamespace(
                headers={"if-none-match": request.headers.get("if-none-match", "")},
                query_params=QueryParams(parts.query))
            kind = path.rsplit("/", 1)[-1]
            hold = self.holds.get(path)
            if hold:
                time.sleep(hold)
            if path == "/iphone-pwa/course":
                built(route, pwa_auth._pwa_inline_html(fake, pwa_auth._PWA_COURSE_HTML, {
                    "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY"}), self.drop)
            elif path in ("/iphone-pwa/dictionary", "/iphone-pwa/phrases"):
                built(route, pwa_auth._pwa_html(fake, "app/static/" + LAYER_FILES[path],
                                                pwa_auth._embeddable_pwa_page_headers(fake)), self.drop)
            elif path == "/iphone-pwa/checkout":
                built(route, pwa_auth._pwa_inline_html(fake, "app/static/" + LAYER_FILES[path],
                                                       pwa_auth._embeddable_pwa_page_headers(fake)))
            elif path.startswith("/iphone-pwa/practice/") and kind in PRACTICE_PAGES:
                built(route, pwa_auth._pwa_inline_html(
                    fake, "app/static/" + PRACTICE_PAGES[kind],
                    pwa_auth._embeddable_pwa_page_headers(fake), revalidate=kind != "voice"))
            elif path in ENTRY_FILES:
                # FileResponse routes: no-store, like production (CSP is not reproduced).
                route.fulfill(content_type="text/html; charset=utf-8", path=str(STATIC / ENTRY_FILES[path]),
                              headers=dict(pwa_auth._NO_STORE))
            elif path == "/api/v3/pwa-auth/session" and guest:
                route.fulfill(status=401, json={"ok": False, "error": "pwa_session_required"})
            elif path == "/api/v3/pwa-auth/providers":
                route.fulfill(json={"ok": True, "providers": ["telegram", "google", "apple"]})
            elif path == "/api/v3/pwa/onboarding/public-tracks":
                route.fulfill(json={"ok": True, "tracks": {"hsk30": {
                    "access": {"feature_enabled": False, "allowed": False}, "live_levels": []}}})
            elif path == "/api/v3/pwa/lesson/start":
                route.fulfill(json={"ok": True, "allowed": True, "completion_proof": "lab-proof"})
            elif path.startswith("/api/v3/pwa/lesson/content/"):
                level, order = path.rsplit("/", 2)[-2:]
                route.fulfill(path=str(STATIC / f"course_v3_data/{level}/lesson_{int(order):02d}.json"),
                              content_type="application/json")
            elif path == "/api/v3/pwa/lesson/complete":
                self.lesson_completions += 1
                route.fulfill(json={"ok": True, "completed_lessons_count": 1, "gamification": {
                    "awarded_xp": 10, "streak": 1, "previous_streak": 1, "streak_updated": False}})
            elif path == "/api/v3/tts":
                # A server-cached phrase (first-time synthesis is slower; real-user timing covers it).
                route.fulfill(path=str(STATIC / "audio/tts_fallback/nihao-cc-by-sa.mp3"),
                              content_type="audio/mpeg", headers={"Cache-Control": IMMUTABLE})
            elif path == "/api/v3/pwa/practice/profile":
                route.fulfill(json={"ok": True, "level": "hsk1", "completed_lessons": 40})
            elif path == "/api/v3/pwa/practice/daily-gate":
                route.fulfill(json={"ok": True, "allowed": True})
            elif path == "/api/v3/pwa/practice/words":
                route.fulfill(json={"ok": True, "words": [{"zh": "你", "kind": "new", "box": 0},
                                                          {"zh": "好", "kind": "new", "box": 0}]})
            elif path == "/api/v3/pwa/practice/report":
                route.fulfill(json={"ok": True, "recorded": 10, "scheduled": 10})
            elif path == "/api/v3/pwa/exams/start":
                route.fulfill(json={"ok": True, "duplicate": False, "session": self.exam})
            elif path == "/api/v3/pwa/mistakes/review/start":
                route.fulfill(json={"ok": True, "duplicate": False, "session": self.review})
            elif path == "/api/v3/pwa/voice/session/start":
                route.fulfill(json={"ok": True, "session_id": "voice-lab", "live_available": False,
                                    "course_context": {"words": [], "review_words": []},
                                    "opening_message": {"chinese_reply": "你好！", "pinyin": "nǐ hǎo",
                                                        "translation": "Salom!", "suggestions": []}})
            elif path in ("/api/v3/pwa/voice/session/end", "/api/v3/clientlog",
                          "/api/v3/pwa/subscription/inline-event"):
                route.fulfill(json={"ok": True})
            elif path == "/api/v3/pwa/gamification":
                route.fulfill(json=leaderboard())
            elif path == "/api/v3/pwa/notifications":
                route.fulfill(json={"ok": True, "notifications": [
                    {"id": i, "title": f"Eslatma {i}", "body": "Bugungi darsingiz kutmoqda.", "action": "course",
                     "created_at": f"2026-11-2{i}T09:00:00+00:00"} for i in range(1, 6)]})
            elif path == "/api/v3/pwa/account-notices":
                route.fulfill(json={"ok": True, "notices": [], "payment_reviews": [], "payment_action": None})
            elif path == "/api/v3/pwa/subscription/overview":
                route.fulfill(json=overview())
            elif path == "/api/v3/pwa/adaptive/plan":
                route.fulfill(json={"ok": True, "enabled": self.adaptive_enabled,
                                    "plan": adaptive_plan() if self.adaptive_enabled else None})
            elif path == "/api/v3/pwa/adaptive/answer":
                picked = (request.post_data_json or {}).get("selected_index")
                route.fulfill(json={"ok": True, "correct": picked == 0, "correct_index": 0,
                                    "selected_index": picked, "correct_answer": "", "explanation": ""})
            elif path == "/api/v3/pwa/mistakes/review/answer":
                picked = (request.post_data_json or {}).get("selected_index")
                route.fulfill(json={"ok": True, "correct": picked == 0, "correct_index": 0,
                                    "selected_index": picked, "correct_answer": "", "explanation": ""})
            else:
                super().serve(route)

    return FlowPage()


def check_production_headers(response, asset_response) -> None:
    """Refuse to report numbers the production delivery would not produce."""
    page = response.headers if response else {}
    problems = []
    if page.get("content-encoding") != "gzip":
        problems.append("course HTML not gzip")
    if "no-cache" not in page.get("cache-control", "") or not page.get("etag"):
        problems.append("course HTML lacks no-cache + ETag")
    if asset_response is None or "immutable" not in asset_response.headers.get("cache-control", ""):
        problems.append("versioned asset not immutable")
    if problems:
        raise SystemExit("lab profile is not production-like: " + "; ".join(problems))


def wait_icons(page, timeout: int = 60000):
    """ms from navigation start until the Tabler icons are on screen, or None if they never are."""
    try:
        page.wait_for_function("window.__lab && window.__lab.icons !== null", timeout=timeout)
    except Exception:
        return None
    return page.evaluate("window.__lab.icons")


# The service worker's background warm-up (app/static/iphone-pwa-sw.js): the course posts
# "hsk-pwa-warm" 3 s after its load; the worker fetches about 1.4 MB of dictionary and practice
# files and then writes this stamp. Action contexts drop that message (NO_WARM_UP), so a first
# open always means files not yet cached and a quiet link. ``settle`` times the warm-up itself.
NO_WARM_UP = r"""(function(){if(!window.ServiceWorker)return;var post=ServiceWorker.prototype.postMessage;
  ServiceWorker.prototype.postMessage=function(m){
    if(m&&m.type==='hsk-pwa-warm'&&!window.__labAllowWarm)return;return post.apply(this,arguments)}})();"""
START_WARM_UP_JS = """async () => { window.__labAllowWarm = true; const r = await navigator.serviceWorker.ready;
  r.active.postMessage({type: 'hsk-pwa-warm'}); return true; }"""
WARM_STAMP_JS = """async () => { if (!window.caches) return -1;
  try { const c = await caches.open('hsk-pwa-static-v1');
        return (await c.match('/__hsk-pwa-warm-stamp')) ? Math.round(performance.now()) : null; }
  catch (e) { return -1; } }"""


def settle(page, server, timeout_s: float = 120) -> dict:
    """Wait for the service worker's background warm-up and report when it was done.

    On a first launch, and once every 12 h, it fetches about 1.4 MB of dictionary and
    practice files, starting 3 s after the page's load.
    """
    start, at = time.time(), None
    while time.time() - start < timeout_s:
        at = page.evaluate(WARM_STAMP_JS)
        if at is not None:
            break
        page.wait_for_timeout(250)
    log = server.take_log()
    out = {"link_kb": round(sum(row["bytes"] for row in log) / 1024, 1)}
    if at == -1:
        out["warm_up_ms"] = "unsupported"
    elif at is None:
        out["unmeasured"] = f"no warm-up stamp within {timeout_s:.0f} s"
    else:
        out["warm_up_ms"] = at
    return out


def steady(page, server) -> dict:
    """A returning learner's state: the warm-up done, then one launch with the worker in control.

    That first controlled launch is a one-time transition (WebKit fetches the course's files
    again, through the worker). It is reported as ``takeover`` and kept out of the warm readings.
    """
    warm_up = settle(page, server)
    if "unmeasured" in warm_up:
        return warm_up
    takeover = launch(page, server, cold=False)
    warm_up["takeover"] = {key: takeover[key] for key in ("fcp_ms", "network_kb", "requests")}
    return warm_up


def wait_controlled(page, timeout: int = 30000) -> None:
    """The service worker registers 3 s after the course's load and then controls the page.

    Actions start once it does, so no action straddles the switch.
    """
    try:
        page.wait_for_function("!!(navigator.serviceWorker && navigator.serviceWorker.controller)", timeout=timeout)
    except Exception:
        pass  # no worker (insecure context): the page stays as it is


def launch(page, server: LabServer, cold: bool) -> dict:
    """One course launch in ``page``; a warm launch re-navigates the same page.

    Playwright's WebKit keeps the HTTP cache only within one page, so a new
    page would make every WebKit warm launch look cold. Re-navigating keeps
    both engines on the same, cache-aware path.
    """
    errors: list[str] = []
    asset: dict = {}

    def on_error(exc):
        errors.append(str(exc)[:160])

    def on_response(resp):
        if "asset" not in asset and "?v=" in resp.url:
            asset["asset"] = resp

    page.on("pageerror", on_error)
    page.on("response", on_response)
    if not cold:
        page.goto("about:blank")
    server.take_log()
    response = page.goto(server.origin + COURSE_PATH, wait_until="commit")
    page.wait_for_function("window.__lab && window.__lab.courseReady !== null", timeout=60000)
    page.wait_for_timeout(1500)  # let late paints and shifts land
    lab = page.evaluate("window.__lab")
    nav = page.evaluate("""(() => { const n = performance.getEntriesByType('navigation')[0] || {};
        return {responseEnd: Math.round(n.responseEnd || 0),
                domContentLoaded: Math.round(n.domContentLoadedEventEnd || 0)}; })()""")
    log = server.take_log()
    page.remove_listener("pageerror", on_error)
    page.remove_listener("response", on_response)
    if cold:
        check_production_headers(response, asset.get("asset"))
    # The icon font (about 870 KB) arrives long after course ready on a cold launch. Wait for it
    # outside the window above, so the next measurement does not share the link with it.
    icons = wait_icons(page)
    server.take_log()
    html = next((row for row in log if row["path"] == "/iphone-pwa/course"), None)
    cls = lab["cls"]
    return {
        "fcp_ms": lab["fcp"],
        "lcp_ms": lab["lcp"],
        "cls": round(cls, 4) if isinstance(cls, (int, float)) else cls,
        "course_ready_ms": lab["courseReady"],
        "icons_ms": icons,
        "lcp_element": lab["lcpEl"],
        "response_end_ms": nav["responseEnd"],
        "dom_content_loaded_ms": nav["domContentLoaded"],
        "html_status": html["status"] if html else "cache",
        "network_kb": round(sum(row["bytes"] for row in log) / 1024, 1),
        "requests": len(log),
        "page_errors": errors[:5],
    }


# Task 1.2 actions. Each ready state is checked in the course page every frame
# (``lab`` is ``window.__lab``; ``lab.child`` evaluates inside the practice frame).
LESSON_READY = ("document.querySelector('#flow.on') && document.querySelector('#f-body').children.length > 0"
                " && !document.querySelector('.hsk-entry-overlay:not(.is-revealing)')")
PRACTICE_READY = {
    # The first question on screen: tests/e2e/test_practice_bootstrap.py READY.
    "recognition": "quiz.length > 0 && document.querySelectorAll('.tile').length === 4",
    "pronunciation": "list.length > 0 && document.getElementById('ctrl').style.display === 'flex'",
    "memorize": "deck.length > 0 && document.querySelector('#body').innerText !== '…'",
    # The exam list and the review button: the centre is usable.
    "test": "document.querySelectorAll('#ex-list .ex').length > 0 && document.getElementById('hub').style.display !== 'none'",
    "mistakes": "!!document.querySelector('button[onclick=\"startReview()\"]')",
    # Microphone open and the AI's opening line shown.
    "voice": "document.getElementById('dialogue').children.length > 0",
}
PRACTICE_TILES = {"recognition": "#m-recog", "pronunciation": "#m-pron", "test": "#m-test",
                  "mistakes": "#m-mist", "memorize": None}  # memorize has no PWA tile today
SESSION_STARTS = {
    "test": ("exam_start", "#ex-list .ex",
             "document.getElementById('exam').classList.contains('on') && EQ.length > 0"),
    "mistakes": ("review_start", 'button[onclick="startReview()"]',
                 "!document.getElementById('review').hidden && RV && RV.questions.length > 0"),
}
# Signed-out (guest) or signed-in first paint: (path, guest, ready).
ENTRY_PAGES = {
    "login": ("/iphone-pwa?login=1&lang=uz", True,
              "!document.getElementById('actions').hidden"
              " && !!document.querySelector('#actions .provider:not([hidden])')"),
    "li_onboarding": ("/iphone-pwa/onboarding/li?lang=uz", True,
                      "document.getElementById('stage').getAttribute('aria-busy') !== 'true'"
                      " && !!document.querySelector('#footer button')"),
    "onboarding": ("/iphone-pwa/onboarding?lang=uz", False,
                   "typeof nextBtn === 'function' && lab.visible(document.getElementById('cta'))"),
}


def child(expr: str) -> str:
    return "lab.child(" + json.dumps(expr) + ")"


def act(page, ready: str, trigger, timeout: int = 30000, *, keep_start: bool = False, **spec) -> dict:
    """Time one action from the learner's tap (or ``lab.begin()``) to ``ready``, painted.

    ``spec`` adds optional in-page readings (expressions over ``lab``): ``first`` (the
    first frame of the new state), ``reveal`` (a parent cover removed), ``skel`` (a
    placeholder is visible) with ``shimmer`` (its root element), ``frame`` (the iframe
    whose document also starts the timer) and ``events`` (what starts it).
    """
    spec = {"ready": ready, "timeout": timeout, **{k: v for k, v in spec.items() if v is not None}}
    page.evaluate("s => window.__lab.arm(s)", spec)
    trigger()
    page.wait_for_function("window.__lab.w.done", timeout=timeout + 10000)
    result = page.evaluate("window.__lab.result()")
    if not keep_start:
        result.pop("start_at", None)
    return result


def close_practice(page) -> None:
    page.evaluate("(() => { const f = window.__lab.frame(); if (f) RESOURCE.closePracticeFrame(f.contentWindow); })()")
    page.wait_for_function("!document.querySelector('#pwa-practice-layer')")


def measured(results: dict, name: str, run, page=None) -> None:
    """Record one action; a failure is reported as unmeasured, never as passing.

    With ``page``, the console errors and uncaught exceptions raised while the action
    ran are recorded with it (the "no new error" baseline).
    """
    log = page_errors(page) if page is not None else None
    before = len(log) if log is not None else 0
    try:
        results[name] = run()
    except Exception as exc:  # the next action still runs
        results[name] = {"unmeasured": str(exc).splitlines()[0][:160]}
    if log is not None:
        results[name]["errors"] = log[before:]


ERROR_LOGS: dict[int, list] = {}


def page_errors(page) -> list:
    return ERROR_LOGS.setdefault(id(page), [])


def watch_errors(page) -> None:
    """Console errors and uncaught exceptions of the page and its frames, in order."""
    log = page_errors(page)

    def on_console(msg):
        if msg.type == "error":
            where = urlsplit((msg.location or {}).get("url") or "").path
            log.append(f"console: {msg.text[:140]}" + (f" @ {where}" if where else ""))

    page.on("console", on_console)
    page.on("pageerror", lambda exc: log.append(f"pageerror: {str(exc)[:140]}"))


def run_flows(page, server: LabServer) -> dict:
    """Drive lesson, practice, test, review and voice once; the course is ready."""
    results: dict = {}
    page.locator("#hsk-launch-splash:not(.is-done)").wait_for(state="hidden")

    page.locator("button.node.current").first.click()
    page.locator(".scta").first.wait_for()
    measured(results, "lesson_open", lambda: act(page, LESSON_READY, lambda: page.locator(".scta").first.click()), page)
    def advance():
        page.locator("#f-cta").wait_for(state="visible")  # the new-word card reveals it after 900 ms
        return act(page, "Flow.i === 1 && document.querySelector('#f-body').children.length > 0",
                   lambda: page.locator("#f-cta").click())
    measured(results, "exercise_next", advance, page)
    # Finishing runs what the last card's continue runs (Flow.next past the end).
    measured(results, "lesson_finish", lambda: act(page, "!!document.querySelector('#levelup.on')", lambda: page.evaluate(
        "window.__lab.begin(); Flow.exitRequired = []; Flow.i = Flow.queue.length; renderFlowCard()")), page)
    launch(page, server, cold=False)  # back to a fresh course for the practice actions
    page.locator("#hsk-launch-splash:not(.is-done)").wait_for(state="hidden")

    page.locator('#nav [data-s="mashq"]').click()
    page.locator("#m-recog").wait_for()
    for kind, tile in PRACTICE_TILES.items():
        for visit in ("first", "repeat"):
            if tile:
                trigger = lambda tile=tile: page.locator(tile).click()
            else:
                trigger = lambda kind=kind: page.evaluate(
                    "k => { window.__lab.begin(); RESOURCE.openPractice('/course_v3_' + k + '.html?lang=uz&level=hsk1'); }", kind)
            measured(results, f"{kind}_open_{visit}", lambda trigger=trigger, kind=kind: act(
                page, child(PRACTICE_READY[kind]), trigger), page)
            if visit == "first" and kind in SESSION_STARTS:
                name, button, ready = SESSION_STARTS[kind]
                frame = page.frame_locator("#pwa-practice-layer iframe")
                measured(results, name, lambda button=button, ready=ready: drop_parent_only(act(
                    page, child(ready), lambda: frame.locator(button).first.click())), page)
            close_practice(page)

    page.locator('#nav [data-s="voice"]').click()
    page.locator(".voicebox button").wait_for()
    for visit in ("first", "repeat"):
        measured(results, f"voice_open_{visit}", lambda: act(
            page, child(PRACTICE_READY["voice"]), lambda: page.locator(".voicebox button").click()), page)
        close_practice(page)
    return results


def drop_parent_only(result: dict) -> dict:
    """Inside an already open practice page there is no parent-only interval."""
    result = dict(result)
    result.pop("parent_only_ms", None)
    return result


def entry_paint(page, origin: str, path: str, ready: str, cold: bool) -> dict:
    """First paint and first useful frame of a page opened directly (login, onboarding)."""
    if not cold:
        page.goto("about:blank")
    page.goto(origin + path, wait_until="commit")
    page.wait_for_function(
        "() => { const lab = window.__lab; if (!lab) return false;"
        " if (lab.entryReady == null) { let ok = false; try { ok = !!(" + ready + "); } catch (e) {}"
        " if (ok) lab.entryReady = Math.round(performance.now()); }"
        " return lab.entryReady != null; }", polling="raf", timeout=30000)
    page.wait_for_timeout(300)
    lab = page.evaluate("({fcp: window.__lab.fcp, ready: window.__lab.entryReady})")
    return {"fcp_ms": lab["fcp"], "ready_ms": lab["ready"]}


# --------------------------------------------------------------------------------------------
# Task 1.3 readings. Every action is timed in the page, like task 1.2's, and keeps its errors.
def visible_any(selector: str) -> str:
    return "Array.prototype.some.call(document.querySelectorAll(" + json.dumps(selector) + "),lab.visible)"


def child_of(frame: str, expr: str) -> str:
    return "lab.childOf(" + json.dumps(frame) + "," + json.dumps(expr) + ")"


def tab_busy(tab: str) -> str:
    return visible_any(f'#s-{tab} [aria-busy="true"],#s-{tab} .pwa-initial-shell,#s-{tab} .hsk-pwa-section-loading')


def tab_shown(tab: str) -> str:
    return (f"(function(){{var s=document.getElementById('s-{tab}');"
            "return !!s&&s.classList.contains('on')&&lab.visible(s)})()")


TABS = ("mashq", "voice", "rating", "profile", "course")
TAB_SETTLED = {  # the tab's own content, with no placeholder left
    "course": "!!(window.MAP&&MAP.authenticated)&&lab.visible(document.querySelector('#s-course button.node'))",
    "mashq": "lab.visible(document.getElementById('m-recog'))",
    "voice": "lab.visible(document.querySelector('#s-voice .voicebox button'))",
    "rating": "SCREEN==='rating'&&ratingMeta.loaded&&!ratingMeta.loading",
    "profile": "SCREEN==='profile'&&lab.visible(document.querySelector('#s-profile .phero'))",
}


def tab_ready(tab: str) -> str:
    return f"({TAB_SETTLED[tab]})&&!{tab_busy(tab)}"


DICT_FRAME, PHRASES_FRAME = "#resource-dict iframe", "#resource-phrases iframe"
CHECKOUT_FRAME = "#pwa-checkout-layer iframe"
# A child page's own first frames: skeleton, content, or an empty list (task 1.3 embedding).
CHILD_CLASSIFY = r"""(function(){if(!document.body)return 'blank';
 if(document.querySelector('#list .row,#list .phrase:not(.phrase-skeleton)'))return 'content';
 if(Array.prototype.some.call(document.querySelectorAll('.phrase-skeleton,[aria-busy="true"]'),lab.visible))return 'skeleton';
 var e=document.querySelector('#list .empty,#empty:not([hidden])');if(e&&lab.visible(e))return 'empty-text';
 return 'empty'})()"""
CHILD_FILM = ("if(window!==top&&/^\\/iphone-pwa\\/(dictionary|phrases)$/.test(location.pathname))"
              "window.__lab.filmStart(" + json.dumps(CHILD_CLASSIFY) + ",15000)")
LAYERS = {
    # name: (root tab, tap, first frame, ready, placeholder, close, closed, iframe)
    "dict": ("mashq", "#m-dict",
             "document.getElementById('resourceov').classList.contains('on')&&lab.visible(document.getElementById('resource-dict'))",
             child_of(DICT_FRAME, "document.querySelectorAll('#list .row').length>0"),
             visible_any("#resource-dict .resource-status"),
             "RESOURCE.close()", "!document.getElementById('resourceov').classList.contains('on')", DICT_FRAME),
    "phrases": ("mashq", "#m-ready-phrases",
                "document.getElementById('resourceov').classList.contains('on')&&lab.visible(document.getElementById('resource-phrases'))",
                child_of(PHRASES_FRAME, "document.querySelectorAll('#list .phrase:not(.phrase-skeleton)').length>0"),
                visible_any("#resource-phrases .resource-status"),
                "RESOURCE.close()", "!document.getElementById('resourceov').classList.contains('on')", PHRASES_FRAME),
    # Ready means a real notice row; the placeholder is the loading text (before 2.3) or the
    # notice-shaped skeleton rows (2.3), which carry the row class too.
    "inbox": ("profile", "#s-profile .pwa-notices-button",
              "lab.visible(document.getElementById('hsk-pwa-notice-root'))",
              "document.querySelectorAll('#hsk-pwa-notice-list .hsk-pwa-notice-row:not(.is-skeleton)').length>0",
              visible_any("#hsk-pwa-notice-list .hsk-pwa-notice-empty,#hsk-pwa-notice-list .hsk-pwa-notice-row.is-skeleton"),
              "HskPwaInbox.close()", "document.getElementById('hsk-pwa-notice-root').hidden", None),
    "settings": ("profile", "#s-profile .profile-settings", tab_shown("settings"),
                 "SCREEN==='settings'&&document.querySelectorAll('#s-settings .srow').length>2&&!"
                 + tab_busy("settings"), tab_busy("settings"),
                 "App.show('profile')", "SCREEN==='profile'", None),
}
SEARCH_QUERIES = {"hanzi": "学", "pinyin": "xue", "translation": "kitob"}
PRO_READY = ("!!document.querySelector('#hsk-inline-pro .hip-primary:not([disabled])')"
             "&&!document.querySelector('#hsk-inline-pro .hip-skeleton')")
EMBEDDED_LAYERS = ("dict", "phrases")
PRO_PLACEHOLDER = visible_any("#hsk-inline-pro .hip-skeleton,#hsk-inline-pro .hip-loading")
CHECKOUT_LAYERS = {  # name: (opener, closer)
    "trial_open": ("HskPwaTrialOffer.open('profile_subscription')",
                   "HskPwaTrialOffer.close(PWA_CHECKOUT_FRAME.contentWindow,false)"),
    "checkout_open": ("App.openPwaCheckout(new URLSearchParams({lang:'uz',source:'profile_subscription'}))",
                      "App.closePwaCheckout(PWA_CHECKOUT_FRAME.contentWindow)"),
}
ANSWER_HOLDS = {"now": 0.0, "held_1s": 1.0}  # extra server time on top of the shaped link
# Each answer waits for the question's audio prefetch to finish first: on the shared link a quick
# first answer otherwise queues behind ~90 KB of TTS (564 ms instead of ~230 ms in a probe run).
SETTLE_MS = 2000
REFRESH_TABS = ("course", "rating", "profile")
PULL_JS = r"""(x) => new Promise(resolve => {
  const target = document.elementFromPoint(x, 240) || document.body;
  const fire = (type, y) => {
    const ev = new Event(type, {bubbles: true, cancelable: true});
    const touch = {clientX: x, clientY: y, screenX: x, screenY: y, target, identifier: 1};
    Object.defineProperty(ev, 'touches', {value: type === 'touchend' ? [] : [touch]});
    Object.defineProperty(ev, 'changedTouches', {value: [touch]});
    target.dispatchEvent(ev);
  };
  let i = 0;
  fire('touchstart', 200);
  (function step() {
    if (i < 10) { i++; fire('touchmove', 200 + 18 * i); requestAnimationFrame(step); return; }
    resolve(true);
    setTimeout(() => {
      try { sessionStorage.setItem('__labRelease', String(performance.timeOrigin + performance.now())); } catch (e) {}
      fire('touchend', 380);
    }, 0);
  })();
})"""
# The launch filmstrip (decision 13): what the course page shows, frame by frame, until ready.
LAUNCH_CLASSIFY = r"""(function(){var b=document.body;if(!b)return 'blank';
 var sp=document.getElementById('hsk-launch-splash');if(sp&&!sp.classList.contains('is-done')&&lab.visible(sp))return 'splash';
 if(window.MAP&&MAP.authenticated&&window.PWA_COURSE_USER_ID&&lab.visible(document.querySelector('#s-course button.node')))return 'content';
 var c=document.getElementById('s-course');if(!c)return 'blank';
 var shell=c.querySelector('.pwa-initial-shell');if(shell&&lab.visible(shell))return 'shell';
 var dots=c.querySelector(':scope>.loading');if(dots&&lab.visible(dots))return 'dots';
 return c.innerText.trim()?'other':'blank'})()"""
LAUNCH_FILM = ("if(window===top&&location.pathname==='/iphone-pwa/course')"
               "window.__lab.filmStart(" + json.dumps(LAUNCH_CLASSIFY) + ",30000)")
FILM_BAD = ("blank", "dots", "other", "error")
MAP_PATH = "/api/v3/pwa/map"
SDK_PAGES = {"dictionary": "/iphone-pwa/dictionary?embedded=1&lang=uz&level=hsk1&filter=hsk1",
             "phrases": "/iphone-pwa/phrases?embedded=1&lang=uz"}
TRACE_CATEGORIES = ["devtools.timeline", "v8", "disabled-by-default-devtools.timeline"]


def plain(result: dict) -> dict:
    """An action with no practice frame and no panda: drop those readings."""
    return {k: v for k, v in result.items() if k not in ("parent_only_ms", "panda_ms", "panda_first_ms")}


def in_page(expr: str) -> str:
    """An expression over ``lab`` for page.wait_for_function, which has no ``lab`` in scope."""
    return "(function(lab){return (" + expr + ")})(window.__lab)"


def wait_course(page) -> None:
    page.locator("#hsk-launch-splash:not(.is-done)").wait_for(state="hidden")
    page.wait_for_function(in_page(TAB_SETTLED["course"]))


def go_tab(page, tab: str) -> None:
    if page.evaluate("SCREEN") != tab:
        page.locator(f'#nav [data-s="{tab}"]').click()
    page.wait_for_function(in_page(tab_ready(tab)), timeout=30000)


def run_tabs(page, server) -> dict:
    """Tab switches: tap to the tab's first frame, and to its settled content."""
    results: dict = {}
    wait_course(page)
    for visit in ("first", "repeat"):
        for tab in TABS:
            measured(results, f"tab_{tab}_{visit}", lambda tab=tab: plain(act(
                page, tab_ready(tab), lambda: page.locator(f'#nav [data-s="{tab}"]').click(),
                first=tab_shown(tab), skel=tab_busy(tab), shimmer=f"document.getElementById('s-{tab}')")), page)
    return results


def child_paint(page, frame: str, start: float) -> dict:
    """When the layer's own page first painted, and what its first frames showed."""
    child = page.evaluate("sel => { const l = window.__lab.frameLab(sel);"
                          " return l ? {fcpAt: l.fcpAt, film: l.film ? l.film.states : null} : null }", frame)
    if not child or start is None:
        return {"child_unmeasured": "no child page"}
    out = {}
    if child["fcpAt"]:
        out["child_first_paint_ms"] = round(child["fcpAt"] - start)
    film = child.get("film") or []
    if film:
        out["child_first_state"] = film[0][1]
        out["child_first_frame_ms"] = round(film[0][0] - start)
        out["child_states"] = ">".join(state for _, state in film)
        content = next((t for t, state in film if state == "content"), None)
        if content is not None:
            out["child_content_ms"] = round(content - start)
    return out


def open_layer(page, name: str, visit: str) -> dict:
    tab, tap, first, ready, placeholder, _, _, frame = LAYERS[name]
    go_tab(page, tab)
    # The cover is removed on the first frame with the layer open and no loading cover left. An
    # embedded page is ready when its content is on screen: rendered, and no longer under the cover.
    if frame is not None:
        ready = f"({ready})&&!{placeholder}"
    result = act(page, ready, lambda: page.locator(tap).first.click(), keep_start=True,
                 first=first, skel=placeholder, frame=frame,
                 reveal=None if frame is None else f"({first})&&!{placeholder}")
    start = result.pop("start_at", None)
    for key in ("panda_ms", "panda_first_ms"):
        result.pop(key, None)
    cover = result.pop("parent_only_ms", None)
    if frame is not None:
        result["cover_removed_ms"] = cover
        if visit == "first":
            result.update(child_paint(page, frame, start))
    return result


def close_layer(page, name: str) -> None:
    *_, close, closed, _ = LAYERS[name]
    page.evaluate(close)
    page.wait_for_function(in_page(closed))


def run_layers(page, server) -> dict:
    """First and repeat open of Dictionary, Phrases, Inbox and Settings.

    Then a returning learner: the warm-up has cached the embedded pages' files, and a new page
    session opens Dictionary and Phrases for the first time (``returning``).
    """
    results: dict = {}
    wait_course(page)
    for name in LAYERS:
        for visit in ("first", "repeat"):
            measured(results, f"{name}_open_{visit}", lambda name=name, visit=visit: open_layer(page, name, visit), page)
            close_layer(page, name)
    page.evaluate(START_WARM_UP_JS)
    warm_up = steady(page, server)
    if "unmeasured" in warm_up:
        for name in EMBEDDED_LAYERS:
            results[f"{name}_open_returning"] = {"unmeasured": warm_up["unmeasured"]}
        return results
    launch(page, server, cold=False)
    wait_course(page)
    for name in EMBEDDED_LAYERS:
        measured(results, f"{name}_open_returning", lambda name=name: open_layer(page, name, "first"), page)
        close_layer(page, name)
    return results


def run_search(page, server) -> dict:
    """Dictionary search, one keystroke at a time: keydown (or input) to the painted list."""
    results: dict = {}
    wait_course(page)
    open_layer(page, "dict", "first")
    frame = page.frame_locator(DICT_FRAME)
    for name, query in SEARCH_QUERIES.items():
        def one(query=query):
            frame.locator("#search").fill("")
            page.evaluate("sel => { const l = window.__lab.frameLab(sel);"
                          " if (l && typeof l.slowestEvent === 'number') { l.slowestEvent = 0; l.slowestEventName = null; } }",
                          DICT_FRAME)
            keys = []
            for i, char in enumerate(query):
                prefix = json.dumps(query[:i + 1])
                keys.append(act(page, child_of(DICT_FRAME, f"document.getElementById('search').value==={prefix}"),
                                lambda char=char: frame.locator("#search").press_sequentially(char),
                                frame=DICT_FRAME, events=["keydown", "beforeinput", "input"])["ready_ms"])
            child = page.evaluate("sel => { const l = window.__lab.frameLab(sel), f = document.querySelector(sel);"
                                  " return {slowest: l && l.slowestEvent, slowestName: l && l.slowestEventName,"
                                  " shown: Number(f.contentDocument.getElementById('count').textContent)} }", DICT_FRAME)
            out = {"keystroke_median_ms": median(keys, 0), "keystroke_max_ms": max(keys), "results": child["shown"]}
            if isinstance(child["slowest"], (int, float)):
                out["slowest_event_ms"] = round(child["slowest"])
                if child["slowestName"]:
                    out["slowest_event"] = child["slowestName"]
            if not child["shown"]:
                out["unmeasured"] = f"no results for {query!r}"
            return out
        measured(results, f"search_{name}", one, page)
    return results


def swipe(page, settled: str) -> dict:
    return page.evaluate("([s]) => window.__lab.swipe(8, 300, s, 10)", [settled])


def run_swipe(page, server) -> dict:
    """Swipe-back from a layer (Dictionary) and from a root tab, one move per frame."""
    results: dict = {}
    wait_course(page)
    open_layer(page, "dict", "first")
    measured(results, "swipe_layer", lambda: swipe(
        page, "!document.getElementById('resourceov').classList.contains('on')&&SCREEN==='mashq'"
              "&&!document.querySelector('.nb-snap,.nb-drag')"), page)
    go_tab(page, "rating")
    destination = page.evaluate("SCREEN_HISTORY[SCREEN_HISTORY.length - 1] || 'course'")

    def root():
        out = swipe(page, f"SCREEN==={json.dumps(destination)}&&!document.querySelector('.nb-snap,.nb-drag')")
        page.wait_for_timeout(600)  # a second back step would land by now
        out["one_step"] = "yes" if page.evaluate("SCREEN") == destination else "no"
        return out
    measured(results, "swipe_root_tab", root, page)
    return results


def run_answers(page, server) -> dict:
    """Answer tap to feedback, in the in-lesson personal review and the Mistakes review."""
    results: dict = {}
    fixture = server.fixture
    fixture.adaptive_enabled = True
    try:
        wait_course(page)
        page.locator("button.node.current").first.click()
        page.locator(".scta").first.click()
        page.wait_for_function(in_page(LESSON_READY) + "&&!!(Adaptive.plan&&Adaptive.plan.items.length>=2)")
        for k, (variant, hold) in enumerate(ANSWER_HOLDS.items()):
            fixture.holds["/api/v3/pwa/adaptive/answer"] = hold
            page.evaluate("k => { Adaptive.slots[Flow.i] = Adaptive.plan.items[k]; adaptiveShow(); }", k)
            page.locator("#f-body .opt").first.wait_for()
            page.wait_for_timeout(SETTLE_MS)  # the answer's own round trip, not queued behind audio
            measured(results, f"adaptive_answer_{variant}", lambda: plain(act(
                page, "document.getElementById('f-bar').classList.contains('show')",
                lambda: page.locator('#f-body .opt[data-k="0"]').click())), page)
            page.locator("#f-barbtn").click()
            page.wait_for_function("!Adaptive.card")
        launch(page, server, cold=False)
        wait_course(page)
        go_tab(page, "mashq")
        page.locator(PRACTICE_TILES["mistakes"]).click()
        page.wait_for_function(in_page(child(PRACTICE_READY["mistakes"])))
        frame = page.frame_locator("#pwa-practice-layer iframe")
        frame.locator(SESSION_STARTS["mistakes"][1]).first.click()
        page.wait_for_function(in_page(child(SESSION_STARTS["mistakes"][2])))
        for variant, hold in ANSWER_HOLDS.items():
            fixture.holds["/api/v3/pwa/mistakes/review/answer"] = hold
            page.wait_for_timeout(SETTLE_MS)
            measured(results, f"review_answer_{variant}", lambda: plain(act(
                page, child("!!document.querySelector('#rv-fb .rv-fb')"),
                lambda: frame.locator('#rv-opts .rv-opt[data-i="0"]').click())), page)
            frame.locator("#rv-foot button").click()
            page.wait_for_function(in_page(child("!document.querySelector('#rv-fb .rv-fb')")))
    finally:
        fixture.adaptive_enabled = False
        fixture.holds.pop("/api/v3/pwa/adaptive/answer", None)
        fixture.holds.pop("/api/v3/pwa/mistakes/review/answer", None)
    return results


def run_pro(page, server) -> dict:
    """The limit/Pro sheet (first and repeat), the trial layer and the checkout layer.

    The two layers open twice: in the first session, before the warm-up has cached the
    checkout page's files, and as a returning learner (``_returning``), after it.
    """
    results: dict = {}
    wait_course(page)
    for visit in ("first", "repeat"):
        measured(results, f"pro_sheet_{visit}", lambda: plain(act(
            page, PRO_READY, lambda: page.evaluate("window.__lab.begin(); App.openPaywall('lockedLesson')"),
            first="lab.visible(document.querySelector('#hsk-inline-pro .hip-sheet'))", skel=PRO_PLACEHOLDER)), page)
        page.evaluate("HSKPwaInlinePro.close()")
        page.wait_for_function("document.getElementById('hsk-inline-pro').hidden")
    open_checkout_layers(page, results, "")
    page.evaluate(START_WARM_UP_JS)
    warm_up = steady(page, server)
    if "unmeasured" in warm_up:
        for name in CHECKOUT_LAYERS:
            results[f"{name}_returning"] = {"unmeasured": warm_up["unmeasured"]}
        return results
    launch(page, server, cold=False)
    wait_course(page)
    open_checkout_layers(page, results, "_returning")
    return results


def open_checkout_layers(page, results: dict, suffix: str) -> None:
    go_tab(page, "profile")
    for name, (opener, closer) in CHECKOUT_LAYERS.items():
        def open_one(opener=opener):
            result = act(page, f"(function(){{var l=lab.frameLab({json.dumps(CHECKOUT_FRAME)});return !!(l&&l.fcpAt)}})()",
                         lambda: page.evaluate("o => { window.__lab.begin(); eval(o); }", opener), keep_start=True,
                         first="lab.visible(document.getElementById('pwa-checkout-layer'))")
            start = result.pop("start_at")
            fcp = page.evaluate("sel => window.__lab.frameLab(sel).fcpAt", CHECKOUT_FRAME)
            out = plain(result)
            out.pop("ready_ms", None)  # the frame after the child's paint; the paint itself is below
            out["child_first_paint_ms"] = round(fcp - start)
            return out
        measured(results, name + suffix, open_one, page)
        page.evaluate(closer)
        page.wait_for_function("!document.getElementById('pwa-checkout-layer')")


def pull_refresh(page, server, tab: str) -> dict:
    """Today's pull-to-refresh: release to the new page's first paint, and to settled content."""
    go_tab(page, tab)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(SETTLE_MS)
    server.take_log()
    try:
        with page.expect_navigation(wait_until="commit", timeout=8000):
            page.evaluate(PULL_JS, 195)
    except Exception:
        return {"unmeasured": "the pull did not reload the page"}
    page.wait_for_function(
        "() => { const lab = window.__lab; if (!lab || !lab.fcpAt) return false;"
        " if (lab.settledAt == null) { let ok = false; try { ok = !!(" + in_page(tab_ready(tab)) + "); } catch (e) {}"
        " if (ok) lab.settledAt = lab.now(); } return lab.settledAt != null; }", polling="raf", timeout=30000)
    read = page.evaluate("({release: Number(sessionStorage.getItem('__labRelease')), fcpAt: window.__lab.fcpAt,"
                         " settledAt: window.__lab.settledAt, type: (performance.getEntriesByType('navigation')[0]"
                         " || {}).type || ''})")
    html = next((row for row in server.take_log() if row["path"] == "/iphone-pwa/course"), None)
    return {"first_frame_ms": round(read["fcpAt"] - read["release"]),
            "settled_ms": round(read["settledAt"] - read["release"]), "navigation": read["type"] or "unknown",
            "html_status": str(html["status"]) if html else "cache",
            "html_kb": round(html["bytes"] / 1024, 1) if html else 0}


def run_refresh(page, server) -> dict:
    """Pull-to-refresh as a returning learner: the warm-up and the worker's takeover are done.

    In a first session the first pull is also the first launch under the worker's control,
    a one-time switch that ``launch`` reports as ``takeover``.
    """
    results: dict = {}
    page.evaluate(START_WARM_UP_JS)
    warm_up = steady(page, server)
    if "unmeasured" in warm_up:
        return {f"pull_{tab}": {"unmeasured": warm_up["unmeasured"]} for tab in REFRESH_TABS}
    launch(page, server, cold=False)
    wait_course(page)
    for tab in REFRESH_TABS:
        measured(results, f"pull_{tab}", lambda tab=tab: pull_refresh(page, server, tab), page)
        page.wait_for_function(in_page(tab_ready(tab)), timeout=30000)
    return results


ACTION_PARTS = {"tabs": run_tabs, "layers": run_layers, "search": run_search, "swipe": run_swipe,
                "answers": run_answers, "pro": run_pro, "refresh": run_refresh}
ALL_PARTS = ("launch", "flows", "entry", *ACTION_PARTS, "blocking", "film", "sdk")


def cold_paint(page, url: str, resources=()) -> dict:
    """A cold page load to its first contentful paint, with the blocking resources' timing."""
    page.goto(url, wait_until="commit")
    page.wait_for_function("window.__lab && window.__lab.fcp !== null", timeout=30000)
    out = page.evaluate("""(paths) => { const t = {}; performance.getEntriesByType('resource').forEach(e => {
        const u = new URL(e.name); const p = u.pathname + u.search;
        if (paths.includes(p)) t[p] = {start: Math.round(e.startTime), end: Math.round(e.responseEnd),
                                       kb: Math.round((e.transferSize || 0) / 102.4) / 10}; });
        return {fcp: window.__lab.fcp, timing: t}; }""", list(resources))
    return out


def blocking_variants(resources: list[str]) -> dict:
    """``none``, each resource alone, and the groups decision 13 names."""
    scripts = tuple(r for r in resources if r.split("?")[0].endswith(".js"))
    sheets = tuple(r for r in resources if r.split("?")[0].endswith(".css"))
    variants = {"none": ()}
    variants.update({r.split("?")[0].rsplit("/", 1)[-1]: (r,) for r in resources})
    variants.update({"all_scripts": scripts, "all_stylesheets": sheets, "all_blocking": tuple(resources)})
    return variants


def run_blocking(browser, engine: str, width: int, server, runs: int) -> dict:
    """What each parser-blocking <head> resource costs the cold first paint (lab-only removal)."""
    resources = head_blocking_resources(server.fixture.course_html())
    variants = blocking_variants(resources)
    fcp = {name: [] for name in variants}
    timing = []
    try:
        for _ in range(runs):
            for name, drop in variants.items():
                server.fixture.drop = drop
                context, page = open_page(browser, engine, width)
                try:
                    read = cold_paint(page, server.origin + COURSE_PATH, resources if name == "none" else ())
                    fcp[name].append(read["fcp"])
                    if name == "none":
                        timing.append(read["timing"])
                except Exception as exc:
                    fcp[name].append(None)
                    print(f"blocking {engine} {name}: {str(exc).splitlines()[0][:120]}", file=sys.stderr)
                finally:
                    context.close()
    finally:
        server.fixture.drop = ()
    base = median(fcp["none"], 0)
    summary = {}
    for name, values in fcp.items():
        value = median(values, 0)
        summary[name] = {"fcp_ms": value, "runs": values,
                         "saves_ms": None if value is None or base is None or name == "none" else base - value}
    per_resource = {}
    for path in resources:
        rows = [t[path] for t in timing if path in t]
        if rows:
            per_resource[path] = {key: median([row[key] for row in rows], 1) for key in ("start", "end", "kb")}
    return {"resources": resources, "variants": summary, "resource_timing": per_resource}


def film_summary(states: list, origin: float, fcp=None) -> dict:
    """A launch filmstrip as ms from navigation start, with the time spent on a bad frame.

    Browsers keep showing the previous screen (or the launch screen) until the first
    contentful paint, so a bad frame counts only from ``fcp`` (ms) on.
    """
    rows = [[round(t - origin), state] for t, state in states]
    out = {"states": " > ".join(f"{state}@{t}" for t, state in rows)}
    if not rows:
        return out
    out["first_frame_ms"], out["first_state"] = rows[0]
    shell = next((t for t, state in rows if state == "shell"), None)
    content = next((t for t, state in rows if state == "content"), None)
    if shell is not None:
        out["shell_ms"] = shell
    if content is not None:
        out["content_ms"] = content
    end = content if content is not None else rows[-1][0]
    shown = fcp if isinstance(fcp, (int, float)) else rows[0][0]
    bad, seen = 0, set()
    for (t, state), nxt in zip(rows, rows[1:] + [[end, None]]):
        span = min(nxt[0], end) - max(t, shown)
        if state in FILM_BAD and span > 0:
            bad += span
            seen.add(state)
    out["bad_frames_ms"] = bad
    out["bad_states"] = ",".join(sorted(seen)) or "none"
    return out


def run_film(page, server, cold: bool, hold: float) -> dict:
    """The launch filmstrip from the first frame to course ready, with the map held or not."""
    server.fixture.holds[MAP_PATH] = hold
    try:
        if not cold:
            page.goto("about:blank")
        page.goto(server.origin + COURSE_PATH, wait_until="commit")
        page.wait_for_function("window.__lab && window.__lab.film && window.__lab.film.done", timeout=60000)
        read = page.evaluate("({states: window.__lab.film.states, origin: performance.timeOrigin, fcp: window.__lab.fcp})")
    finally:
        server.fixture.holds.pop(MAP_PATH, None)
    out = film_summary(read["states"], read["origin"], read["fcp"])
    out["fcp_ms"] = read["fcp"]
    out["icons_ms"] = wait_icons(page)  # and the warm film that follows does not share the link with the font
    return out


def script_main_thread_ms(events: list, needle: str) -> dict:
    """Main-thread time of one script in a Chromium trace: its evaluation, and compiles outside it."""
    def url(event):
        args = event.get("args") or {}
        data = args.get("data") or {}
        return str(data.get("url") or args.get("fileName") or data.get("fileName") or "")

    mine = [e for e in events if e.get("ph") == "X" and needle in url(e)]
    evaluate = [e for e in mine if e.get("name") == "EvaluateScript"]
    spans = [(e["ts"], e["ts"] + e.get("dur", 0)) for e in evaluate]
    compile_outside = [e for e in mine if e.get("name") in ("v8.compile", "CompileScript")
                       and not any(a <= e["ts"] < b for a, b in spans)]
    return {"evaluate_ms": round(sum(e.get("dur", 0) for e in evaluate) / 1000, 1),
            "compile_outside_ms": round(sum(e.get("dur", 0) for e in compile_outside) / 1000, 1)}


def sdk_paint(browser, page, url: str, engine: str, needle: str, cold: bool) -> dict:
    if not cold:
        page.goto("about:blank")
    tracing = engine == "chromium" and needle
    if tracing:
        browser.start_tracing(page=page, categories=TRACE_CATEGORIES)
    try:
        read = cold_paint(page, url)
    finally:
        trace = browser.stop_tracing() if tracing else None
    out = {"fcp_ms": read["fcp"]}
    if trace:
        data = json.loads(trace)
        events = data.get("traceEvents", data) if isinstance(data, dict) else data
        out.update(script_main_thread_ms(events, needle))
    return out


def run_sdk(browser, engine: str, width: int, server, runs: int) -> dict:
    """telegram-web-app.js in the child pages: main-thread time (Chromium trace) and FCP without it."""
    readings: dict = {}
    for name, path in SDK_PAGES.items():
        sdk = next((r for r in head_blocking_resources(server.fixture.page_html(path)) if "telegram-web-app.js" in r), None)
        rows: dict = {}
        for _ in range(runs):
            for variant, drop in (("with_sdk", ()), ("without_sdk", (sdk,) if sdk else ())):
                server.fixture.drop = drop
                context, page = open_page(browser, engine, width)
                try:
                    for cold in (True, False):
                        key = f"{variant}_{'cold' if cold else 'warm'}"
                        try:
                            rows.setdefault(key, []).append(sdk_paint(
                                browser, page, server.origin + path, engine,
                                "telegram-web-app.js" if variant == "with_sdk" else "", cold))
                        except Exception as exc:
                            rows.setdefault(key, []).append({"unmeasured": str(exc).splitlines()[0][:120]})
                finally:
                    context.close()
                    server.fixture.drop = ()
        readings[name] = {"sdk": sdk, "median": summarise_actions([{k: v[i] for k, v in rows.items()}
                                                                   for i in range(runs)]), "runs": rows}
    return readings


# Decision 12: one target rule by action type. ``metric`` is the reading the rule is applied to.
BOUNDS_MS = {"interaction": 200, "opening": 1000, "cold_shell": 1500}
ACTION_TARGETS = (  # (action name pattern, metric, kind, owning task)
    (r"lesson_open$", "ready_ms", "opening", "2.7"),
    (r"exercise_next$", "ready_ms", "interaction", "2.7"),
    (r"lesson_finish$", "ready_ms", "opening", "2.7"),
    (r"(recognition|pronunciation|memorize|test|mistakes|voice)_open_(first|repeat)$", "ready_ms", "opening", "2.8"),
    (r"(exam|review)_start$", "ready_ms", "opening", "2.8"),
    (r"tab_\w+_(first|repeat)$", "first_ms", "interaction", "2.5"),
    (r"(dict|phrases)_open_(first|repeat|returning)$", "ready_ms", "opening", "2.4"),
    (r"inbox_open_(first|repeat)$", "ready_ms", "opening", "2.3"),
    (r"settings_open_(first|repeat)$", "ready_ms", "opening", "2.6"),
    (r"search_\w+$", "keystroke_max_ms", "interaction", "2.4"),
    (r"swipe_\w+$", "drag_first_frame_ms", "interaction", "2.5"),
    (r"pull_\w+$", "first_frame_ms", "interaction", "2.10"),
    (r"(adaptive|review)_answer_\w+$", "ready_ms", "interaction", "2.11"),
    (r"pro_sheet_(first|repeat)$", "ready_ms", "opening", "2.12"),
    (r"(checkout|trial)_open(_returning)?$", "child_first_paint_ms", "opening", "2.12"),
    (r"(login|li_onboarding|onboarding)_(cold|warm)$", "ready_ms", "opening", "new item"),
)


def decision_12_target(kind: str, baseline) -> dict:
    """Inside the bound: no more than 10% worse. Outside it: the bound, fixed by its owning task."""
    if not isinstance(baseline, (int, float)) or isinstance(baseline, bool):
        return {"target_ms": None, "status": "unmeasured"}
    bound = BOUNDS_MS.get(kind)
    if bound is None:  # "keep": a reading with no bound keeps its baseline
        return {"target_ms": round(baseline * 1.1), "status": "keep"}
    if baseline <= bound:
        return {"target_ms": min(bound, round(baseline * 1.1)), "status": "within"}
    return {"target_ms": bound, "status": "over"}


def with_targets(summary: dict) -> dict:
    for name, entry in summary.items():
        for pattern, metric, kind, owner in ACTION_TARGETS:
            if re.search(pattern, name):
                entry["target"] = {"metric": metric, "kind": kind, "owner": owner,
                                   **decision_12_target(kind, entry.get(metric))}
                break
    return summary


def summarise_actions(runs: list[dict]) -> dict:
    """Per action: medians over the runs that measured it, plus how often it did not.

    Every numeric reading gets its median; a text reading lists the values seen; the
    errors are the union over all runs, with how many runs had any.
    """
    names = sorted({name for run in runs for name in run})
    summary = {}
    for name in names:
        rows = [run.get(name) or {"unmeasured": "not run"} for run in runs]
        ok = [row for row in rows if "unmeasured" not in row and not row.get("timed_out")]
        entry = {"measured_runs": len(ok), "of": len(rows)}
        numeric = sorted({key for row in ok for key, value in row.items()
                          if isinstance(value, (int, float)) and not isinstance(value, bool)})
        for key in numeric:
            value = median([row.get(key) for row in ok], 0)
            if value is not None:
                entry[key] = value
        for key in sorted({key for row in ok for key, value in row.items() if isinstance(value, str)}):
            entry[key] = sorted({row[key] for row in ok if isinstance(row.get(key), str)})
        if ok and any("panda_ms" in row for row in ok):
            entry["panda_seen_runs"] = sum(1 for row in ok if (row.get("panda_ms") or 0) > 0)
        if any("errors" in row for row in rows):
            entry["error_runs"] = sum(1 for row in rows if row.get("errors"))
            errors = sorted({error for row in rows for error in row.get("errors") or []})
            if errors:
                entry["errors"] = errors[:8]
        problems = sorted({row.get("unmeasured") or "timed out" for row in rows if row not in ok})
        if problems:
            entry["unmeasured"] = problems
        summary[name] = entry
    return summary


def median(values, digits=1):
    numbers = [v for v in values if isinstance(v, (int, float))]
    if not numbers:
        return None
    value = round(statistics.median(numbers), digits)
    return int(value) if digits == 0 else value


def summarise(runs: list[dict]) -> dict:
    keys = ("fcp_ms", "lcp_ms", "cls", "course_ready_ms", "icons_ms", "warm_up_ms", "warm_up_kb",
            "takeover_fcp_ms", "takeover_kb", "response_end_ms", "network_kb")
    summary = {"lcp_element": sorted({run["lcp_element"] for run in runs if run.get("lcp_element")})}
    for key in keys:
        if not any(key in run for run in runs):
            continue  # a warm launch has no warm-up reading
        values = [run.get(key) for run in runs]
        value = median(values, 4 if key == "cls" else 1)
        if value is None and values and all(v == "unsupported" for v in values):
            value = "unsupported"  # the engine has no such entry type; never report 0
        summary[key] = value
    return summary


def git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def open_page(browser, engine: str, width: int, *, guest: bool = False, origin: str = "", scripts=()):
    """One fresh profile context: mobile viewport, touch, a fake microphone, CPU slowdown.

    ``scripts`` are extra init scripts that run after the probe (task 1.3 filmstrips).
    """
    context = browser.new_context(viewport={"width": width, "height": HEIGHT}, device_scale_factor=2,
                                  is_mobile=engine != "firefox", has_touch=True)
    try:
        context.grant_permissions(["microphone"])
    except Exception:  # the engine has no such permission; Voice then reports unmeasured
        pass
    if guest:
        name, _, value = GUEST_COOKIE.partition("=")
        context.add_cookies([{"name": name, "value": value, "url": origin}])
    context.add_init_script(PAGE_PROBE)
    for script in scripts:
        context.add_init_script(script)
    page = context.new_page()
    page.set_default_timeout(30000)
    watch_errors(page)
    if engine == "chromium":
        context.new_cdp_session(page).send("Emulation.setCPUThrottlingRate", {"rate": CPU_SLOWDOWN})
    return context, page


def launch_browser(pw, engine: str):
    # Chromium's fake capture device stands in for a phone microphone (Voice).
    args = ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] if engine == "chromium" else []
    return getattr(pw, engine).launch(args=args)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--engines", default="chromium,webkit")
    parser.add_argument("--widths", default="320,390,430", help="launch widths")
    parser.add_argument("--flow-widths", default="390", help="widths for every action part except tabs")
    parser.add_argument("--tab-widths", default="320,390,430", help="widths for the tab switches")
    parser.add_argument("--runs", type=int, default=3, help="cold+warm pairs (and action runs) per engine and width")
    parser.add_argument("--blocking-runs", type=int, default=5,
                        help="cold loads per <head> resource variant (one removal moves FCP less than run noise)")
    parser.add_argument("--parts", default="all", help="all, or any of " + ", ".join(ALL_PARTS))
    parser.add_argument("--out", help="also write the JSON report to this file")
    args = parser.parse_args(argv)
    parts = set(ALL_PARTS) if args.parts == "all" else {p.strip() for p in args.parts.split(",") if p.strip()}
    unknown = parts - set(ALL_PARTS)
    if unknown:
        parser.error("unknown parts: " + ", ".join(sorted(unknown)))

    os.chdir(ROOT)  # the fixtures read app/ and localization/ relative to the repo
    from playwright.sync_api import sync_playwright

    report = {
        "profile": {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_head": git_head(),
            "network": {"latency_ms": int(LATENCY_S * 1000), "down_mbps": 1.6, "shaping": "server, shared link"},
            "height_px": HEIGHT,
            "delivery": "gzip>=1KB, HTML private,no-cache+ETag, versioned+/assets immutable, real service worker",
            "fixture": ("scripts/measure_pwa_lab.py::flow_fixture (tests/e2e ScreenPage, uz, onboarded, free;"
                        " learner HTML from app/api/pwa_auth.py builders)"),
        },
        "results": [],
        "flows": [],
        "parts": [],  # task 1.3: one entry per part, engine and width
    }
    with sync_playwright() as pw, LabServer(flow_fixture("uz")) as server:
        for engine in [e.strip() for e in args.engines.split(",") if e.strip()]:
            browser = launch_browser(pw, engine)
            cpu = CPU_SLOWDOWN if engine == "chromium" else 1
            for width in [int(w) for w in args.widths.split(",") if w.strip()] if "launch" in parts else []:
                cold_runs, warm_runs = [], []
                for _ in range(args.runs):
                    context, page = open_page(browser, engine, width)
                    cold = launch(page, server, cold=True)
                    warm_up = steady(page, server)
                    takeover = warm_up.get("takeover", {})
                    cold.update({"warm_up_ms": warm_up.get("warm_up_ms"), "warm_up_kb": warm_up["link_kb"],
                                 "takeover_fcp_ms": takeover.get("fcp_ms"), "takeover_kb": takeover.get("network_kb")})
                    cold_runs.append(cold)
                    warm_runs.append(launch(page, server, cold=False))
                    context.close()
                report["results"].append({
                    "engine": engine, "browser_version": browser.version, "width": width,
                    "cpu_slowdown": cpu,
                    "cold": {"median": summarise(cold_runs), "runs": cold_runs},
                    "warm": {"median": summarise(warm_runs), "runs": warm_runs},
                })
            for width in [int(w) for w in args.flow_widths.split(",") if w.strip()]:
                action_runs, entry_runs, errors = [], [], []
                for _ in range(args.runs if parts & {"flows", "entry"} else 0):
                    if "flows" in parts:
                        context, page = open_page(browser, engine, width, scripts=(NO_WARM_UP,))
                        page.on("pageerror", lambda exc: errors.append(str(exc)[:160]))
                        launch(page, server, cold=True)
                        wait_controlled(page)
                        action_runs.append(run_flows(page, server))
                        context.close()
                    if "entry" in parts:
                        entry: dict = {}
                        for name, (path, guest, ready) in ENTRY_PAGES.items():
                            context, page = open_page(browser, engine, width, guest=guest, origin=server.origin)
                            page.on("pageerror", lambda exc: errors.append(str(exc)[:160]))
                            measured(entry, name + "_cold", lambda: entry_paint(page, server.origin, path, ready, True))
                            measured(entry, name + "_warm", lambda: entry_paint(page, server.origin, path, ready, False))
                            context.close()
                        entry_runs.append(entry)
                if parts & {"flows", "entry"}:
                    report["flows"].append({
                        "engine": engine, "browser_version": browser.version, "width": width, "cpu_slowdown": cpu,
                        "actions": {"median": with_targets(summarise_actions(action_runs)), "runs": action_runs},
                        "entry": {"median": with_targets(summarise_actions(entry_runs)), "runs": entry_runs},
                        "page_errors": sorted(set(errors))[:10],
                    })
            for name, run_part in ACTION_PARTS.items():
                if name not in parts:
                    continue
                widths = args.tab_widths if name == "tabs" else args.flow_widths
                for width in [int(w) for w in widths.split(",") if w.strip()]:
                    runs = []
                    for _ in range(args.runs):
                        context, page = open_page(browser, engine, width,
                                                  scripts=(NO_WARM_UP, CHILD_FILM) if name == "layers" else (NO_WARM_UP,))
                        try:
                            launch(page, server, cold=True)
                            wait_controlled(page)
                            runs.append(run_part(page, server))
                        except Exception as exc:  # the part's setup failed: say so, keep the run going
                            runs.append({"_setup": {"unmeasured": str(exc).splitlines()[0][:160]}})
                        finally:
                            context.close()
                    report["parts"].append({"part": name, "engine": engine, "width": width, "cpu_slowdown": cpu,
                                            "median": with_targets(summarise_actions(runs)), "runs": runs})
            for width in [int(w) for w in args.flow_widths.split(",") if w.strip()]:
                base = {"engine": engine, "width": width, "cpu_slowdown": cpu}
                if "blocking" in parts:
                    report["parts"].append({"part": "blocking", **base,
                                            **run_blocking(browser, engine, width, server, args.blocking_runs)})
                if "film" in parts:
                    runs = []
                    for _ in range(args.runs):
                        run: dict = {}
                        for hold_name, hold in (("map_now", 0.0), ("map_held_3s", 3.0)):
                            context, page = open_page(browser, engine, width, scripts=(LAUNCH_FILM,))
                            try:  # a fresh profile per hold, so its first launch is cold
                                for cold in (True, False):
                                    measured(run, f"{'cold' if cold else 'warm'}_{hold_name}",
                                             lambda cold=cold, hold=hold: run_film(page, server, cold, hold), page)
                            finally:
                                context.close()
                        runs.append(run)
                    report["parts"].append({"part": "film", **base, "median": summarise_actions(runs), "runs": runs})
                if "sdk" in parts:
                    report["parts"].append({"part": "sdk", **base, **run_sdk(browser, engine, width, server, args.runs)})
            browser.close()
        report["profile"]["external_unavailable"] = server.unavailable_external()
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
