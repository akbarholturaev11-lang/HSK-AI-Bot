"""Authenticated machine-to-machine on-demand overview refresh.

This route is intentionally NOT part of the browser cookie session or read-only
ChatGPT MCP transport. It accepts only a separate server-side secret, requests
no user rows and returns timestamps only. Disabled when not configured.
"""
import hmac
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_statistics_cache import StatisticsUnavailable
from app.admin_api.pwa_webauthn_transport import _body

logger = logging.getLogger(__name__)
_PATH = "/api/internal/admin-pwa/analytics/refresh"


def create_manual_aggregate_refresh_router(*, settings_obj, analytics_reader):
    router = APIRouter(tags=["admin-pwa-internal-analytics"])

    @router.post(_PATH, include_in_schema=False)
    async def manual_refresh(request: Request):
        # Fail closed unless all explicit production gates are configured.
        secret = str(getattr(settings_obj, "ADMIN_PWA_MANUAL_AGGREGATE_REFRESH_TOKEN", "") or "")
        if (not getattr(settings_obj, "ADMIN_PWA_ENABLED", False)
                or not getattr(settings_obj, "ADMIN_PWA_R2_AGGREGATE_ENABLED", False)
                or not 48 <= len(secret) <= 128):
            return _reply(404, "not_found")
        origin = str(getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", "") or "")
        if (not origin.startswith("https://") or
                f"{request.url.scheme}://{request.url.netloc}" != origin):
            return _reply(403, "admin_pwa_wrong_origin")
        headers = request.headers.getlist("authorization")
        if (len(headers) != 1
                or not hmac.compare_digest(headers[0], "Bearer " + secret)):
            return _reply(401, "admin_pwa_unauthorized")
        if request.query_params:
            return _reply(400, "admin_pwa_invalid_payload")
        if (request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                != "application/json"):
            return _reply(415, "unsupported_media_type")
        data = await _body(request, 32)
        if data != {}:
            return _reply(400, "admin_pwa_invalid_payload")

        reader = getattr(analytics_reader, "_readers", {}).get("overview")
        if reader is None or not hasattr(reader, "refresh_overview_bundle"):
            return _reply(503, "admin_pwa_refresh_unavailable")

        try:
            results = await reader.refresh_overview_bundle()
        except StatisticsUnavailable as exc:
            if str(exc) == "Manual refresh recently completed":
                return _reply(429, "admin_pwa_refresh_rate_limited")
            logger.warning("Manual overview refresh unavailable; partial R2 updates possible")
            return _reply(503, "admin_pwa_refresh_unavailable")
        except Exception:
            logger.error("Manual overview refresh failed")
            return _reply(503, "admin_pwa_refresh_unavailable")
        return JSONResponse({"ok": True, "periods": results}, headers=_PRIVATE_HEADERS)

    return router
