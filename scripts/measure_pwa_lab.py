"""Repeatable learner PWA lab profile (docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md).

Serves the existing e2e ``ScreenPage`` fixture over real HTTP and measures the
course launch in Chromium and WebKit. Nothing here talks to production, real
accounts or secrets: every API answer is the e2e fixture.

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
        if ctype.startswith("text/html"):
            for host in EXTERNAL_HOSTS:
                body = body.replace(f"https://{host}/".encode(), f"/__ext/{host}/".encode())
        if status == 200 and ctype.startswith("text/html"):
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
        if (len(body) >= 1024 and accepts_gzip and "Content-Encoding" not in out
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


def median(values, digits=1):
    numbers = [v for v in values if isinstance(v, (int, float))]
    return round(statistics.median(numbers), digits) if numbers else None


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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--engines", default="chromium,webkit")
    parser.add_argument("--widths", default="320,390,430")
    parser.add_argument("--runs", type=int, default=3, help="cold+warm pairs per engine and width")
    parser.add_argument("--out", help="also write the JSON report to this file")
    args = parser.parse_args(argv)

    os.chdir(ROOT)  # the fixtures read app/ and localization/ relative to the repo
    from playwright.sync_api import sync_playwright
    from tests.e2e.test_pwa_screen_alignment import ScreenPage

    report = {
        "profile": {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_head": git_head(),
            "network": {"latency_ms": int(LATENCY_S * 1000), "down_mbps": 1.6, "shaping": "server, shared link"},
            "height_px": HEIGHT,
            "delivery": "gzip>=1KB, HTML private,no-cache+ETag, versioned+/assets immutable, real service worker",
            "fixture": "tests/e2e/test_pwa_screen_alignment.py::ScreenPage (uz, onboarded, free)",
        },
        "results": [],
    }
    with sync_playwright() as pw, LabServer(ScreenPage("uz")) as server:
        for engine in [e.strip() for e in args.engines.split(",") if e.strip()]:
            browser = getattr(pw, engine).launch()
            for width in [int(w) for w in args.widths.split(",") if w.strip()]:
                cold_runs, warm_runs = [], []
                for _ in range(args.runs):
                    context = browser.new_context(viewport={"width": width, "height": HEIGHT},
                                                  device_scale_factor=2, is_mobile=engine != "firefox",
                                                  has_touch=True)
                    context.add_init_script(PAGE_PROBE)
                    page = context.new_page()
                    if engine == "chromium":
                        context.new_cdp_session(page).send(
                            "Emulation.setCPUThrottlingRate", {"rate": CPU_SLOWDOWN})
                    cold_runs.append(launch(page, server, cold=True))
                    warm_runs.append(launch(page, server, cold=False))
                    context.close()
                report["results"].append({
                    "engine": engine, "browser_version": browser.version, "width": width,
                    "cpu_slowdown": CPU_SLOWDOWN if engine == "chromium" else 1,
                    "cold": {"median": summarise(cold_runs), "runs": cold_runs},
                    "warm": {"median": summarise(warm_runs), "runs": warm_runs},
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
