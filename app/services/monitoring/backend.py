"""Backend failure reporter: post-response, never in the request transaction (D4).

The ASGI middleware never reads a request or response body and never changes
a response. Writes run in their own session as background tasks behind a
process-local semaphore, coalesced per fingerprint; when saturated they are
dropped and counted, and the hourly loop reports the count as a
`monitoring/self_dropped` self-incident.
"""
from __future__ import annotations

import asyncio
import logging

from app.services.monitoring import catalog, is_intake_request

logger = logging.getLogger(__name__)

# 503 is this codebase's "switched off / temporarily unavailable" answer
# (for example `pwa_auth_unavailable`), an expected outcome. Integration
# failures behind a 503 report explicitly through report_server_failure.
_CLIENT_PREFIXES = (
    ("/api/v3/android/", "android"), ("/api/v3/android-", "android"),
    ("/api/v3/pwa/", "iphone_pwa"), ("/api/v3/pwa-auth/", "iphone_pwa"),
    ("/api/miniapp/", "telegram"), ("/api/subscription-miniapp/", "telegram"),
)


def platform_for_route(path):
    """The client a route serves, when its prefix fixes it; otherwise `server`."""
    return next((platform for prefix, platform in _CLIENT_PREFIXES if path.startswith(prefix)), "server")


class BackendReporter:
    def __init__(self, *, session_factory=None, settings_obj=None,
                 concurrency=catalog.BACKEND_WRITE_CONCURRENCY,
                 coalesce_seconds=catalog.BACKEND_COALESCE_SECONDS):
        self.session_factory = session_factory
        self.settings_obj = settings_obj
        self.coalesce_seconds = coalesce_seconds
        self._semaphore = asyncio.Semaphore(concurrency)
        self._pending = {}
        self._waiting = {}
        self._tasks = set()
        self.dropped = 0

    def configure(self, *, session_factory, settings_obj):
        self.session_factory = session_factory
        self.settings_obj = settings_obj

    def _mode(self):
        from app.services.monitoring.intake import current_mode
        return current_mode(self.settings_obj)

    def report(self, feature_code, failure_code, site_code, platform="server"):
        """Queue one occurrence. Never raises, never blocks the caller."""
        try:
            if self.session_factory is None or self._mode() == "off":
                return
            if (feature_code not in catalog.FEATURES or failure_code not in catalog.SERVER_FAILURES
                    or site_code not in catalog.ALL_SITES or platform not in catalog.PLATFORMS):
                return
            key = (platform, feature_code, failure_code, site_code)
            if key in self._pending:
                if self._pending[key] < 10_000:
                    self._pending[key] += 1
                else:
                    self.dropped += 1
                return
            if len(self._pending) >= catalog.BACKEND_PENDING_FINGERPRINTS:
                self.dropped += 1
                return
            loop = asyncio.get_running_loop()
            self._pending[key] = 1
            task = loop.create_task(self._flush_later(key))
            self._waiting[key] = task
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        except Exception:  # noqa: BLE001 - the reporter must never affect a response
            logger.debug("diagnostic report skipped", exc_info=True)

    async def _flush_later(self, key):
        try:
            await asyncio.sleep(self.coalesce_seconds)
        finally:
            count = self._pending.pop(key, 0)
            self._waiting.pop(key, None)
        if not count:
            return
        if self._semaphore.locked():
            self.dropped += count
            return
        async with self._semaphore:
            await self._write(key, count)

    async def _write(self, key, count):
        from app.services.monitoring.intake import IntakeBusy, bound_write, diagnostic_slot, ingest_server
        platform, feature, failure, site = key
        mode = self._mode()
        if mode == "off":
            return
        try:
            with diagnostic_slot(self.settings_obj):
                async with self.session_factory() as session:
                    async with session.begin():
                        await bound_write(session)
                        await ingest_server(session, feature_code=feature, failure_code=failure, site_code=site,
                                            platform=platform, occurrences=count, mode=mode,
                                            settings_obj=self.settings_obj)
        except IntakeBusy:
            self.dropped += count
        except Exception:  # noqa: BLE001 - counted, never re-reported in a loop
            self.dropped += count
            logger.warning("diagnostic backend write failed")

    async def flush_self_dropped(self):
        """Hourly: report dropped backend writes as one self-incident."""
        if self._mode() != "off" and self.dropped:
            count = min(self.dropped, 10_000)
            self.dropped -= count
            await self._write(("server", "monitoring", "self_dropped", "backend_writer"), count)

    async def drain(self):
        """Tests and shutdown: flush pending writes now."""
        pending, self._pending = self._pending, {}
        waiting, self._waiting = self._waiting, {}
        tasks = tuple(self._tasks)
        for task in waiting.values():
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for key, count in pending.items():
            await self._write(key, count)


reporter = BackendReporter()


def report_server_failure(feature_code, failure_code="provider_failed", site_code="ai_provider", platform="server"):
    """Integration failures that do not surface as a 5xx (D4). Fire and forget."""
    reporter.report(feature_code, failure_code, site_code, platform)


class DiagnosticMiddleware:
    """Pure ASGI: records a 5xx or an unhandled exception on learner routes."""

    def __init__(self, app, reporter_obj=None):
        self.app = app
        self.reporter = reporter_obj or reporter

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not str(scope.get("path", "")).startswith("/api/"):
            await self.app(scope, receive, send)
            return
        if self.reporter is reporter and self.reporter._mode() == "off":
            await self.app(scope, receive, send)
            return
        status = None

        async def send_wrapper(message):
            nonlocal status
            if message.get("type") == "http.response.start":
                status = message.get("status")
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            self._record(scope, "server_exception")
            raise
        if isinstance(status, int) and 500 <= status < 600 and status != 503:
            self._record(scope, "server_5xx")

    def _record(self, scope, failure_code):
        try:
            route = scope.get("route")
            path = getattr(route, "path", None) or scope.get("path", "")
            if is_intake_request(scope, path):
                return  # Intake cannot report itself. Legacy events remain monitored.
            mapped = catalog.ROUTE_MAP.get(path)
            if mapped is None:
                return
            feature, site = mapped
            self.reporter.report(feature, failure_code, site, platform_for_route(path))
        except Exception:  # noqa: BLE001
            logger.debug("diagnostic middleware skipped", exc_info=True)
