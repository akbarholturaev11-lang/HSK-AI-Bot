"""Repeatable learner PWA lab profile (docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md).

Serves the existing e2e ``ScreenPage`` fixture over real HTTP and measures, in
Chromium and WebKit:
- the course launch (``launch``);
- learner actions (``flows``): lesson open, one exercise advance and lesson
  finish; the five practice pages and Voice, first and repeat open; a Test
  exam start and a Mistakes review start. Each is timed in the page from the
  tap to its ready state, one frame later so it is painted, with how long the
  parent entry was the only thing visible and how long the panda showed;
- login, Li onboarding and course onboarding first paint (``entry``).
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
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import mimetypes
import os
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
  var lab=window.__lab={fcp:null,courseReady:null,
    lcp:types.indexOf('largest-contentful-paint')<0?'unsupported':null,
    cls:types.indexOf('layout-shift')<0?'unsupported':0};
  try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){
    if(e.name==='first-contentful-paint')lab.fcp=Math.round(e.startTime)})})
    .observe({type:'paint',buffered:true})}catch(e){}
  if(lab.lcp!=='unsupported')try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){
    lab.lcp=Math.round(e.startTime)})}).observe({type:'largest-contentful-paint',buffered:true})}catch(e){}
  if(lab.cls!=='unsupported')try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){
    if(!e.hadRecentInput)lab.cls+=e.value})}).observe({type:'layout-shift',buffered:true})}catch(e){}
  (function poll(){
    if(window.MAP&&MAP.authenticated&&window.PWA_COURSE_USER_ID){lab.courseReady=Math.round(performance.now());return}
    requestAnimationFrame(poll)})();
  // Action timer (task 1.2). Times are epoch ms, so parent and child frames compare.
  var PANDA='.hsk-entry-overlay:not(.is-cancelled),.hsk-study-preparing-panda';
  lab.now=function(){return performance.timeOrigin+performance.now()};
  lab.visible=function(el){
    if(!el||!el.isConnected)return false;var r=el.getBoundingClientRect();
    if(r.width<1||r.height<1)return false;var s=el.ownerDocument.defaultView.getComputedStyle(el);
    return s.visibility!=='hidden'&&Number(s.opacity)>0.05};
  lab.frame=function(){return document.querySelector('#pwa-practice-layer iframe')};
  lab.child=function(expr){var f=lab.frame();if(!f||f.hidden)return false;
    try{return !!f.contentWindow.eval(expr)}catch(e){return false}};
  lab.pandaShown=function(){
    var docs=[document],f=lab.frame();
    if(f&&!f.hidden)try{if(f.contentDocument)docs.push(f.contentDocument)}catch(e){}
    return docs.some(function(d){return Array.prototype.some.call(d.querySelectorAll(PANDA),lab.visible)})};
  lab.arm=function(spec){
    var w=lab.w={start:null,ready:null,revealed:null,panda:0,pandaFirst:null,pandaOn:false,last:null,done:false,timedOut:false};
    var ready=new Function('lab','return ('+spec.ready+')'),limit=spec.timeout||30000,armedAt=lab.now();
    w.mark=function(){if(w.start===null)w.start=lab.now()};
    var docs=[document],f=lab.frame();
    if(f)try{if(f.contentDocument)docs.push(f.contentDocument)}catch(e){}
    docs.forEach(function(d){d.addEventListener('pointerdown',w.mark,true)});
    (function tick(){
      var t=lab.now();
      if(w.start!==null){
        if(w.pandaOn)w.panda+=t-w.last;
        w.pandaOn=lab.pandaShown();if(w.pandaOn&&w.pandaFirst===null)w.pandaFirst=t-w.start;
        if(w.revealed===null){var f=lab.frame();if(f&&!f.hidden)w.revealed=t-w.start}
        // Ready is stamped one frame after the state is reached: by then it is painted.
        if(w.seen){w.ready=t-w.start;w.done=true}
        else{var ok=false;try{ok=!!ready(lab)}catch(e){}
          if(ok)w.seen=true;else if(t-w.start>limit){w.timedOut=true;w.done=true}}
        w.last=t;
      }else if(t-armedAt>limit){w.timedOut=true;w.done=true}
      if(w.done)docs.forEach(function(d){d.removeEventListener('pointerdown',w.mark,true)});
      else requestAnimationFrame(tick)})()};
  lab.begin=function(){lab.w.mark()};
  lab.result=function(){var w=lab.w,r=function(v){return v===null?null:Math.round(v)};
    return{ready_ms:r(w.ready),parent_only_ms:r(w.revealed),panda_ms:Math.round(w.panda),
      panda_first_ms:r(w.pandaFirst),timed_out:w.timedOut}};
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

    def built(route, response, content_type="text/html; charset=utf-8"):
        headers = {k: v for k, v in response.headers.items()
                   if k.lower() not in ("content-length", "content-type")}
        route.fulfill(status=response.status_code, content_type=content_type,
                      body=bytes(response.body), headers=headers)

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

    class FlowPage(ScreenPage):
        def __init__(self):
            super().__init__(lang)
            self.exam = exam_session()
            self.review = review_session()
            self.lesson_completions = 0

        def serve(self, route):
            request = route.request
            parts = urlsplit(request.url)
            path = parts.path
            guest = GUEST_COOKIE in request.headers.get("cookie", "")
            fake = types.SimpleNamespace(
                headers={"if-none-match": request.headers.get("if-none-match", "")},
                query_params=QueryParams(parts.query))
            kind = path.rsplit("/", 1)[-1]
            if path == "/iphone-pwa/course":
                built(route, pwa_auth._pwa_inline_html(fake, pwa_auth._PWA_COURSE_HTML, {
                    "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY"}))
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
            elif path in ("/api/v3/pwa/voice/session/end", "/api/v3/clientlog"):
                route.fulfill(json={"ok": True})
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
    response = page.goto(server.origin + "/iphone-pwa/course?lang=uz&onboarded=1", wait_until="commit")
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
    html = next((row for row in log if row["path"] == "/iphone-pwa/course"), None)
    cls = lab["cls"]
    return {
        "fcp_ms": lab["fcp"],
        "lcp_ms": lab["lcp"],
        "cls": round(cls, 4) if isinstance(cls, (int, float)) else cls,
        "course_ready_ms": lab["courseReady"],
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


def act(page, ready: str, trigger, timeout: int = 30000) -> dict:
    """Time one action from the learner's tap (or ``lab.begin()``) to ``ready``, painted."""
    page.evaluate("s => window.__lab.arm(s)", {"ready": ready, "timeout": timeout})
    trigger()
    page.wait_for_function("window.__lab.w.done", timeout=timeout + 10000)
    return page.evaluate("window.__lab.result()")


def close_practice(page) -> None:
    page.evaluate("(() => { const f = window.__lab.frame(); if (f) RESOURCE.closePracticeFrame(f.contentWindow); })()")
    page.wait_for_function("!document.querySelector('#pwa-practice-layer')")


def measured(results: dict, name: str, run) -> None:
    """Record one action; a failure is reported as unmeasured, never as passing."""
    try:
        results[name] = run()
    except Exception as exc:  # the next action still runs
        results[name] = {"unmeasured": str(exc).splitlines()[0][:160]}


def run_flows(page, server: LabServer) -> dict:
    """Drive lesson, practice, test, review and voice once; the course is ready."""
    results: dict = {}
    page.locator("#hsk-launch-splash:not(.is-done)").wait_for(state="hidden")

    page.locator("button.node.current").first.click()
    page.locator(".scta").first.wait_for()
    measured(results, "lesson_open", lambda: act(page, LESSON_READY, lambda: page.locator(".scta").first.click()))
    def advance():
        page.locator("#f-cta").wait_for(state="visible")  # the new-word card reveals it after 900 ms
        return act(page, "Flow.i === 1 && document.querySelector('#f-body').children.length > 0",
                   lambda: page.locator("#f-cta").click())
    measured(results, "exercise_next", advance)
    # Finishing runs what the last card's continue runs (Flow.next past the end).
    measured(results, "lesson_finish", lambda: act(page, "!!document.querySelector('#levelup.on')", lambda: page.evaluate(
        "window.__lab.begin(); Flow.exitRequired = []; Flow.i = Flow.queue.length; renderFlowCard()")))
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
                page, child(PRACTICE_READY[kind]), trigger))
            if visit == "first" and kind in SESSION_STARTS:
                name, button, ready = SESSION_STARTS[kind]
                frame = page.frame_locator("#pwa-practice-layer iframe")
                measured(results, name, lambda button=button, ready=ready: drop_parent_only(act(
                    page, child(ready), lambda: frame.locator(button).first.click())))
            close_practice(page)

    page.locator('#nav [data-s="voice"]').click()
    page.locator(".voicebox button").wait_for()
    for visit in ("first", "repeat"):
        measured(results, f"voice_open_{visit}", lambda: act(
            page, child(PRACTICE_READY["voice"]), lambda: page.locator(".voicebox button").click()))
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


def summarise_actions(runs: list[dict]) -> dict:
    """Per action: medians over the runs that measured it, plus how often it did not."""
    names = sorted({name for run in runs for name in run})
    summary = {}
    for name in names:
        rows = [run.get(name) or {"unmeasured": "not run"} for run in runs]
        ok = [row for row in rows if "unmeasured" not in row and not row.get("timed_out")]
        entry = {"measured_runs": len(ok), "of": len(rows)}
        for key in ("ready_ms", "parent_only_ms", "panda_ms", "fcp_ms"):
            value = median([row.get(key) for row in ok], 0)
            if value is not None:
                entry[key] = value
        if ok and any("panda_ms" in row for row in ok):
            entry["panda_seen_runs"] = sum(1 for row in ok if (row.get("panda_ms") or 0) > 0)
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
    keys = ("fcp_ms", "lcp_ms", "cls", "course_ready_ms", "response_end_ms", "network_kb")
    summary = {}
    for key in keys:
        values = [run[key] for run in runs]
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


def open_page(browser, engine: str, width: int, *, guest: bool = False, origin: str = ""):
    """One fresh profile context: mobile viewport, touch, a fake microphone, CPU slowdown."""
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
    page = context.new_page()
    page.set_default_timeout(30000)
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
    parser.add_argument("--flow-widths", default="390", help="widths for the lesson, practice and entry actions")
    parser.add_argument("--runs", type=int, default=3, help="cold+warm pairs (and action runs) per engine and width")
    parser.add_argument("--parts", default="launch,flows,entry", help="any of launch, flows, entry")
    parser.add_argument("--out", help="also write the JSON report to this file")
    args = parser.parse_args(argv)
    parts = {p.strip() for p in args.parts.split(",") if p.strip()}

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
    }
    with sync_playwright() as pw, LabServer(flow_fixture("uz")) as server:
        for engine in [e.strip() for e in args.engines.split(",") if e.strip()]:
            browser = launch_browser(pw, engine)
            cpu = CPU_SLOWDOWN if engine == "chromium" else 1
            for width in [int(w) for w in args.widths.split(",") if w.strip()] if "launch" in parts else []:
                cold_runs, warm_runs = [], []
                for _ in range(args.runs):
                    context, page = open_page(browser, engine, width)
                    cold_runs.append(launch(page, server, cold=True))
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
                        context, page = open_page(browser, engine, width)
                        page.on("pageerror", lambda exc: errors.append(str(exc)[:160]))
                        launch(page, server, cold=True)
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
                report["flows"].append({
                    "engine": engine, "browser_version": browser.version, "width": width, "cpu_slowdown": cpu,
                    "actions": {"median": summarise_actions(action_runs), "runs": action_runs},
                    "entry": {"median": summarise_actions(entry_runs), "runs": entry_runs},
                    "page_errors": sorted(set(errors))[:10],
                })
            browser.close()
        report["profile"]["external_unavailable"] = server.unavailable_external()
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
