"""Authenticated machine-to-machine on-demand verified aggregate refresh.

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
                or not 48 <= len(secret) <= 128 or not secret.isascii()):
            return _reply(404, "not_found")
        origin = str(getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", "") or "")
        if (not origin.startswith("https://") or
                f"{request.url.scheme}://{request.url.netloc}" != origin):
            return _reply(403, "admin_pwa_wrong_origin")
        headers = request.headers.getlist("authorization")
        if (len(headers) != 1 or len(headers[0]) > 256
                or not headers[0].isascii()
                or not hmac.compare_digest(headers[0], "Bearer " + secret)):
            return _reply(401, "admin_pwa_unauthorized")
        if request.query_params:
            return _reply(400, "admin_pwa_invalid_payload")
        if (request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                != "application/json"):
            return _reply(415, "unsupported_media_type")
        data = await _body(request, 128)
        if not isinstance(data, dict):
            return _reply(400, "admin_pwa_invalid_payload")
        scoped = data != {}
        if scoped:
            if (set(data) != {"section", "period"}
                    or data.get("section") not in ("course", "funnel", "money", "sources")
                    or data.get("period") not in ("weekly", "monthly", "all_time")):
                return _reply(400, "admin_pwa_invalid_payload")
            section, period = data["section"], data["period"]
        else:
            section, period = "overview", None

        reader = getattr(analytics_reader, "_readers", {}).get(section)
        if reader is None or not hasattr(reader, "refresh_overview_bundle"):
            return _reply(503, "admin_pwa_refresh_unavailable")

        try:
            if scoped:
                from app.admin_api.pwa_read import StatisticsRequest
                result = await reader.refresh_approved_section(
                    StatisticsRequest(platform="overall", period=period), section=section)
                results = {period: {"generated_at": result["generated_at"],
                                    "expires_at": result["expires_at"]}}
            else:
                results = await reader.refresh_overview_bundle()
        except StatisticsUnavailable as exc:
            if str(exc) == "Manual refresh recently completed":
                return _reply(429, "admin_pwa_refresh_rate_limited")
            # The exception is an internal fixed-code reason, not raw SQL or
            # user data. Log only an enumerated reason; never a bearer token.
            safe_reasons = {
                "Manual statistics refresh unavailable",
                "Manual refresh coordination unavailable",
                "Manual refresh already in progress",
                "Statistics refresh unavailable",
                "Statistics refresh cooling down",
                "Manual statistics coordination unavailable",
                "Statistics refresh already in progress",
                "Manual statistics R2 write unavailable",
                "Manual statistics coordination lost",
                "Manual statistics lease lost",
                "Manual statistics refresh timed out",
                "Manual refresh recently completed",
                "Unexpected overview projection",
                "Unexpected scoped projection",
                "Invalid scoped projection",
            }
            reason = str(exc)
            logger.warning("Manual aggregate refresh failed; reason=%s",
                           reason if reason in safe_reasons else "unclassified")
            return _reply(503, "admin_pwa_refresh_unavailable")
        except Exception:
            logger.error("Manual aggregate refresh failed")
            return _reply(503, "admin_pwa_refresh_unavailable")
        return JSONResponse({"ok": True, "periods": results, "section": section}, headers=_PRIVATE_HEADERS)

    return router
