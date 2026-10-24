"""First-party HTML OAuth consent, bound to real Admin PWA session and CSRF.

Route is unreachable unless all three MCP flags and the exact pre-registered
client are configured. No unsolicited grant, credential issuance on GET,
arbitrary redirect, Telegram initData, Google ID token or client OAuth state
as a CSRF token. The browser must explicitly click allow or deny.
"""
import html
import logging
from pathlib import Path
import re
from typing import Any, Callable
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.admin_api.pwa_mcp_http import (
    _inactive_response, _form, _invalid_request, _HEADERS, _ISSUER,
)
from app.admin_api.pwa_mcp_oauth import (
    begin_mcp_authorization, decide_mcp_consent,
    _registered_client, ApprovedMcpCode, DeniedMcpCode,
)
from app.admin_api.pwa_mcp_resource import _ANALYTICS_SCOPE, _REQUIRED_RESOURCE
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME

logger = logging.getLogger(__name__)
_ASSETS = Path(__file__).resolve().parents[1] / "static" / "admin-pwa"
_TEMPLATE = _ASSETS / "mcp-consent.html"
_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "img-src 'self'; form-action 'self'; base-uri 'none'; "
    "frame-ancestors 'none'; object-src 'none'; connect-src 'none'"
)
_CONSENT_HEADERS = {
    **_HEADERS, "X-Frame-Options": "DENY",
    "Content-Security-Policy": _CSP,
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
_QUERY_FIELDS = frozenset({
    "response_type", "client_id", "redirect_uri", "scope",
    "resource", "state", "code_challenge", "code_challenge_method",
})
_POST_FIELDS = frozenset({"request_id", "csrf", "decision"})
_PLACEHOLDERS = re.compile(r"__MCP_(CLIENT|DESTINATION|REQUEST_ID|CSRF)__")


def _redirect(registered_uri: str, fields: dict[str, str]) -> str:
    """Only previously validated, *registered*, exact HTTPS callback."""
    parsed = urlsplit(registered_uri)
    query = parsed.query + ("&" if parsed.query else "") + urlencode(fields)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))


def _page(client_id: str, redirect_uri: str, request_id: str, csrf_proof: str) -> HTMLResponse:
    hostname = urlsplit(redirect_uri).hostname or ""
    placeholders = {
        "CLIENT": client_id, "DESTINATION": hostname,
        "REQUEST_ID": request_id, "CSRF": csrf_proof,
    }
    # Substitute once, escaped; never evaluate nested placeholders or
    # interpolate any client-controlled HTML/JavaScript/CSS.
    document = _PLACEHOLDERS.sub(
        lambda match: html.escape(placeholders[match.group(1)], quote=True),
        _TEMPLATE.read_text(encoding="utf-8"),
    )
    return HTMLResponse(document, headers=_CONSENT_HEADERS)


def create_admin_pwa_mcp_consent_router(
    *, settings_obj: Any, session_factory: Callable | None = None,
    begin_service: Callable = begin_mcp_authorization,
    decide_service: Callable = decide_mcp_consent,
) -> APIRouter:
    router = APIRouter(tags=["admin-pwa-mcp-consent"])

    @router.get("/oauth/authorize", include_in_schema=False)
    async def authorize(request: Request):
        failure = _inactive_response(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _invalid_request(503, "temporarily_unavailable")
        query = list(request.query_params.multi_items())
        if (len(query) != len(_QUERY_FIELDS)
                or set(key for key, _ in query) != _QUERY_FIELDS
                or any(len(val) > 1024 for _, val in query)):
            return _invalid_request()
        args = dict(query)
        if (args["response_type"] != "code"
                or args["code_challenge_method"] != "S256"
                or not re.fullmatch(r"[A-Za-z0-9_-]{43}", args["code_challenge"])
                or not re.fullmatch(r"[A-Za-z0-9._~-]{16,256}", args["state"])
                or not _registered_client(
                    settings_obj, args["client_id"], args["redirect_uri"],
                    args["resource"], args["scope"],
                )):
            # NEVER redirect to a callback URI before exact client verification.
            return _invalid_request(400, "invalid_client")
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _invalid_request(401, "admin_login_required")
        try:
            async with session_factory() as db:
                pending = await begin_service(
                    db, session_cookie=cookie, client_id=args["client_id"],
                    redirect_uri=args["redirect_uri"], resource=args["resource"],
                    scope=args["scope"], state=args["state"],
                    code_challenge=args["code_challenge"],
                    code_challenge_method=args["code_challenge_method"],
                    settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("MCP OAuth consent start unavailable")
            return _invalid_request(503, "temporarily_unavailable")
        if pending is None or not pending.csrf_proof:
            return _invalid_request(403, "access_denied")
        return _page(pending.client_id, pending.redirect_uri,
                     pending.request_id, pending.csrf_proof)

    @router.post("/oauth/authorize", include_in_schema=False)
    async def authorize_decision(request: Request):
        failure = _inactive_response(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _invalid_request(503, "temporarily_unavailable")
        origins = request.headers.getlist("origin")
        if len(origins) != 1 or origins[0] != _ISSUER:
            return _invalid_request(403, "csrf_failed")
        if request.headers.get("sec-fetch-site") != "same-origin":
            return _invalid_request(403, "csrf_failed")
        form = await _form(request)
        if (form is None or set(form) != _POST_FIELDS
                or form["decision"] not in ("allow", "deny")):
            return _invalid_request()
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _invalid_request(401, "admin_login_required")
        try:
            async with session_factory() as db:
                result = await decide_service(
                    db, request_id=form["request_id"], session_cookie=cookie,
                    csrf_proof=form["csrf"], approved=form["decision"] == "allow",
                    settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("MCP OAuth consent decision unavailable")
            return _invalid_request(503, "temporarily_unavailable")
        if result is None:
            return _invalid_request(403, "access_denied")
        if not _registered_client(
            settings_obj, getattr(settings_obj, "ADMIN_PWA_MCP_CLIENT_ID", ""),
            result.redirect_uri, _REQUIRED_RESOURCE, _ANALYTICS_SCOPE,
        ):
            return _invalid_request(403, "access_denied")
        if isinstance(result, ApprovedMcpCode) and form["decision"] == "allow":
            location = _redirect(result.redirect_uri,
                                 {"code": result.code, "state": result.state, "iss": _ISSUER})
        elif isinstance(result, DeniedMcpCode) and form["decision"] == "deny":
            location = _redirect(result.redirect_uri,
                                 {"error": "access_denied", "state": result.state, "iss": _ISSUER})
        else:
            return _invalid_request(403, "access_denied")
        return RedirectResponse(location, status_code=303, headers=_CONSENT_HEADERS)

    return router
