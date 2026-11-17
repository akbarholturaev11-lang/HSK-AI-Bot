"""Authenticated machine-to-machine on-demand verified aggregate refresh.

This route is intentionally NOT part of the browser cookie session or read-only
ChatGPT MCP transport. It accepts only a separate server-side secret, requests
no user rows and returns timestamps only. Disabled when not configured.
"""
import hmac
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.admin_api.pwa_full_refresh_manifest import MANIFEST_VERSION, group_for, manifest
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_statistics_cache import StatisticsUnavailable
from app.admin_api.pwa_webauthn_transport import _body

logger = logging.getLogger(__name__)
_PATH = "/api/internal/admin-pwa/analytics/refresh"
# Fixed reason codes for a full-refresh group; never exception text.
_FULL_REFRESH_REASONS = {
    "Manual refresh already in progress": "busy",
    "Manual statistics R2 read unavailable": "r2_read",
    "Manual statistics R2 write unavailable": "r2_write",
    "Manual statistics refresh timed out": "timeout",
    "Unexpected bundle projection": "invalid_projection",
    "Invalid bundle projection": "invalid_projection",
    "Unexpected overview projection": "invalid_projection",
    "Invalid overview projection": "invalid_projection",
}


async def _full_refresh(data, *, analytics_reader, feedback_reader):
    """One allowlisted group per request (ADMIN_PWA_FULL_REFRESH_ENABLED only).

    The orchestrator calls groups one after another; this handler never fans
    out. Bodies carry statuses, timestamps and fixed reason codes only.
    """
    if data == {"mode": "manifest"}:
        return JSONResponse({"ok": True, "mode": "manifest", **manifest()}, headers=_PRIVATE_HEADERS)
    if set(data) != {"mode", "section", "platform"} or data.get("mode") != "bundle":
        return _reply(400, "admin_pwa_invalid_payload")
    section, platform = data.get("section"), data.get("platform")
    group = group_for(section, platform) if isinstance(section, str) and isinstance(platform, str) else None
    if group is None:
        return _reply(400, "admin_pwa_invalid_payload")

    def reply(code, status, periods=None, reason=None):
        periods = dict(periods or {})
        for period, why in group["unsupported"].items():
            periods[period] = {"status": "unsupported", "reason": why}
        body = {"ok": status == "refreshed", "mode": "bundle", "manifest_version": MANIFEST_VERSION,
                "section": section, "platform": platform, "status": status, "periods": periods}
        if reason is not None:
            body["reason"] = reason
        return JSONResponse(body, status_code=code, headers=_PRIVATE_HEADERS)

    try:
        if section == "overview":
            reader = getattr(analytics_reader, "_readers", {}).get("overview")
            if reader is None:
                return reply(503, "failed", reason="unavailable")
            # The existing coherent Overview bundle, exactly as `{}` runs it.
            done = await reader.refresh_overview_bundle()
            result = {"status": "refreshed", "periods": {
                period: {"status": "refreshed", **done[period]} for period in group["periods"]}}
        elif section == "feedback":
            if feedback_reader is None:
                return reply(503, "failed", reason="unavailable")
            result = await feedback_reader.refresh_feedback_bundle(periods=group["periods"])
        else:
            reader = getattr(analytics_reader, "_readers", {}).get(section)
            if reader is None:
                return reply(503, "failed", reason="unavailable")
            result = await reader.refresh_section_bundle(
                section=section, platform=platform, periods=group["periods"])
    except StatisticsUnavailable as exc:
        if str(exc) == "Manual refresh recently completed":
            return reply(429, "unchanged_recent")
        reason = _FULL_REFRESH_REASONS.get(str(exc), "unavailable")
        logger.warning("Full analytics refresh failed; section=%s platform=%s reason=%s",
                       section, platform, reason)
        return reply(503, "failed", reason=reason)
    except Exception:
        logger.error("Full analytics refresh failed; section=%s platform=%s", section, platform)
        return reply(503, "failed", reason="unavailable")
    status = result["status"]
    if status in ("partial", "failed"):
        logger.warning("Full analytics refresh %s; section=%s platform=%s", status, section, platform)
    return reply(200 if status in ("refreshed", "unavailable") else 503, status, result["periods"])


def create_manual_aggregate_refresh_router(*, settings_obj, analytics_reader, feedback_reader=None):
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
        if "mode" in data:
            # Full refresh is additive and default OFF; while OFF, a `mode`
            # body is rejected exactly like any other unknown payload.
            if getattr(settings_obj, "ADMIN_PWA_FULL_REFRESH_ENABLED", False) is not True:
                return _reply(400, "admin_pwa_invalid_payload")
            return await _full_refresh(data, analytics_reader=analytics_reader,
                                       feedback_reader=feedback_reader)
        scoped = data != {}
        if scoped:
            # `platform` is optional: a filter's own snapshot (audit #44).
            if (set(data) not in ({"section", "period"}, {"section", "period", "platform"})
                    or data.get("section") not in ("course", "funnel", "money", "sources", "report")
                    or data.get("period") not in ("weekly", "monthly", "all_time")
                    or data.get("platform", "overall") not in ("overall", "android", "telegram", "iphone_pwa")):
                return _reply(400, "admin_pwa_invalid_payload")
            section, period, platform = data["section"], data["period"], data.get("platform", "overall")
        else:
            section, period, platform = "overview", None, "overall"

        reader = getattr(analytics_reader, "_readers", {}).get(section)
        if reader is None or not hasattr(reader, "refresh_overview_bundle"):
            return _reply(503, "admin_pwa_refresh_unavailable")

        try:
            if scoped:
                from app.admin_api.pwa_read import StatisticsRequest
                result = await reader.refresh_approved_section(
                    StatisticsRequest(platform=platform, period=period), section=section)
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
        return JSONResponse({"ok": True, "periods": results, "section": section, "platform": platform},
                            headers=_PRIVATE_HEADERS)

    return router
