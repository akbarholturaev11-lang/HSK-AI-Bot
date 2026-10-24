"""Disabled-by-default, statistics-only MCP Streamable HTTP & OAuth transport.

This is a protocol boundary, NOT an activated ChatGPT connection. No browser
OAuth authorization/consent view is mounted yet. Its INDEPENDENT kill switch
ADMIN_PWA_MCP_TRANSPORT_ENABLED must remain false until a reviewed, localized
consent UI, strict client registration, audit, integration QA and owner approval
are complete.

OAuth access is NEVER a browser cookie, Google ID token or Telegram initData.
Only exact-audience, revocable, 5-minute OAuth grants authorize statistics.
"""
import json
import logging
from typing import Any, Callable
from urllib.parse import parse_qsl

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from app.admin_api.pwa_mcp_oauth import (
    _registered_client, exchange_mcp_code,
)
from app.admin_api.pwa_mcp_resource import (
    _ready, _REQUIRED_RESOURCE, _ANALYTICS_SCOPE,
    verify_readonly_mcp_bearer, read_mcp_statistics_with_verified_token,
    _TOKEN_SHAPE,
    McpBearerBadArguments, McpBearerDenied,
)
from app.admin_api.pwa_read import StatisticsRequest

logger = logging.getLogger(__name__)
_ISSUER = "https://hskai.app"
_PROTOCOL = "2025-11-25"
_SUPPORTED = frozenset({_PROTOCOL, "2025-06-18"})
_HEADERS = {
    "Cache-Control": "no-store", "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
}
_WWW_AUTH = 'Bearer resource_metadata="https://hskai.app/.well-known/oauth-protected-resource"'
_MAX_FORM = 4096
_MAX_RPC = 12000


def _inactive_response(request: Request, settings_obj: Any) -> Response | None:
    if not (_ready(settings_obj)
            and bool(getattr(settings_obj, "ADMIN_PWA_MCP_TRANSPORT_ENABLED", False))):
        return Response(status_code=404, headers=_HEADERS)
    if (not getattr(settings_obj, "ADMIN_PWA_MCP_CLIENT_ID", "")
            or not getattr(settings_obj, "ADMIN_PWA_MCP_REDIRECT_URI", "")):
        return Response(status_code=404, headers=_HEADERS)
    if request.url.scheme != "https" or request.url.netloc != "hskai.app":
        return Response(status_code=403, headers=_HEADERS)
    return None


def _invalid_request(code: int = 400, error: str = "invalid_request") -> JSONResponse:
    return JSONResponse(status_code=code, content={"error": error}, headers=_HEADERS)


def _unauthorized() -> Response:
    return Response(
        status_code=401,
        headers={**_HEADERS, "WWW-Authenticate": _WWW_AUTH},
    )


async def _limited_body(request: Request, maximum: int) -> bytes | None:
    """Bound request size BEFORE buffering untrusted client data."""
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > maximum:
            return None
        content.extend(chunk)
    return bytes(content)


async def _form(request: Request) -> dict[str, str] | None:
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/x-www-form-urlencoded":
        return None
    if len(request.headers.getlist("content-type")) != 1:
        return None
    body = await _limited_body(request, _MAX_FORM)
    if body is None:
        return None
    try:
        raw = body.decode("utf-8", "strict")
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True, max_num_fields=12)
    except (ValueError, UnicodeDecodeError):
        return None
    if len(pairs) != len({key for key, _ in pairs}):
        return None
    return dict(pairs)


def _no_duplicates(items: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


async def _rpc_body(request: Request) -> dict | None:
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        return None
    if len(request.headers.getlist("content-type")) != 1:
        return None
    if request.headers.get("origin") not in (None, _ISSUER):
        # A remote host may omit Origin entirely; arbitrary web origins may
        # not invoke a bearer-authenticated MCP resource as a browser API.
        return None
    if request.headers.get("sec-fetch-site", "same-origin") == "cross-site":
        return None
    data = await _limited_body(request, _MAX_RPC)
    if data is None:
        return None
    try:
        obj = json.loads(data, object_pairs_hook=_no_duplicates)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(obj, dict) or obj.get("jsonrpc") != "2.0":
        return None
    if not isinstance(obj.get("method"), str):
        return None
    if "id" in obj and (
        isinstance(obj["id"], bool) or not isinstance(obj["id"], (str, int))
        or isinstance(obj["id"], str) and len(obj["id"]) > 128
    ):
        return None
    return obj


def _reply_result(id_value: str | int, result: Any) -> JSONResponse:
    return JSONResponse(content={"jsonrpc": "2.0", "id": id_value, "result": result}, headers=_HEADERS)


def _reply_error(id_value: str | int | None, code: int, message: str, *, http_status: int = 200) -> JSONResponse:
    return JSONResponse(content={
        "jsonrpc": "2.0", "id": id_value,
        "error": {"code": code, "message": message},
    }, status_code=http_status, headers=_HEADERS)


def create_admin_pwa_mcp_http_router(
    *, settings_obj: Any, session_factory: Callable | None = None,
    exchange_service: Callable = exchange_mcp_code,
    verify_service: Callable = verify_readonly_mcp_bearer,
    read_service: Callable = read_mcp_statistics_with_verified_token,
) -> APIRouter:
    """Mountable only behind three default-off settings; no write tools."""
    router = APIRouter(tags=["admin-pwa-mcp"])

    @router.get("/.well-known/oauth-protected-resource", include_in_schema=False)
    async def protected_resource(request: Request):
        failure = _inactive_response(request, settings_obj)
        if failure is not None:
            return failure
        return JSONResponse(content={
            "resource": _REQUIRED_RESOURCE,
            "authorization_servers": [_ISSUER],
            "scopes_supported": [_ANALYTICS_SCOPE],
            "bearer_methods_supported": ["header"],
        }, headers=_HEADERS)

    @router.get("/.well-known/oauth-authorization-server", include_in_schema=False)
    async def authorization_server(request: Request):
        failure = _inactive_response(request, settings_obj)
        if failure is not None:
            return failure
        # This metadata is intentionally invisible while transport is OFF.
        # Turning it ON requires a separate reviewed /oauth/authorize UI,
        # which is NOT mounted in this increment.
        return JSONResponse(content={
            "issuer": _ISSUER,
            "authorization_endpoint": _ISSUER + "/oauth/authorize",
            "token_endpoint": _ISSUER + "/oauth/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": [_ANALYTICS_SCOPE],
            "client_id_metadata_document_supported": False,
        }, headers=_HEADERS)

    @router.post("/oauth/token", include_in_schema=False)
    async def token(request: Request):
        failure = _inactive_response(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _invalid_request(503, "temporarily_unavailable")
        values = await _form(request)
        if values is None or set(values) != {
            "grant_type", "code", "code_verifier", "client_id",
            "redirect_uri", "resource",
        } or values["grant_type"] != "authorization_code":
            return _invalid_request()
        if not _registered_client(
            settings_obj, values["client_id"], values["redirect_uri"],
            values["resource"], _ANALYTICS_SCOPE,
        ):
            return _invalid_request(400, "invalid_client")
        try:
            async with session_factory() as db:
                result = await exchange_service(
                    db, code=values["code"], code_verifier=values["code_verifier"],
                    client_id=values["client_id"], redirect_uri=values["redirect_uri"],
                    resource=values["resource"], settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("Admin MCP OAuth token exchange unavailable")
            return _invalid_request(503, "temporarily_unavailable")
        if result is None:
            return _invalid_request(400, "invalid_grant")
        return JSONResponse(content={
            "access_token": result.token, "token_type": result.token_type,
            "expires_in": result.expires_in, "scope": result.scope,
        }, headers=_HEADERS)

    @router.get("/mcp", include_in_schema=False)
    async def unsupported_stream(request: Request):
        failure = _inactive_response(request, settings_obj)
        return failure if failure is not None else Response(
            status_code=405, headers={**_HEADERS, "Allow": "POST"},
        )

    @router.delete("/mcp", include_in_schema=False)
    async def unsupported_session_delete(request: Request):
        failure = _inactive_response(request, settings_obj)
        return failure if failure is not None else Response(
            status_code=405, headers={**_HEADERS, "Allow": "POST"},
        )

    @router.post("/mcp", include_in_schema=False)
    async def mcp_post(request: Request):
        failure = _inactive_response(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _invalid_request(503, "temporarily_unavailable")
        bearer_headers = request.headers.getlist("authorization")
        if len(bearer_headers) != 1:
            return _unauthorized()
        if (not bearer_headers[0].startswith("Bearer ")
                or not _TOKEN_SHAPE.fullmatch(bearer_headers[0][7:])):
            return _unauthorized()
        # Do not allow browser session cookies, query access tokens, or
        # legacy Telegram initData as MCP authentication mechanisms.
        if (request.headers.get("cookie") or request.query_params
                or request.headers.get("x-telegram-init-data")):
            return _unauthorized()
        # Stateless MCP JSON response only; no SSE sessions/streaming and no
        # server-to-client notifications, resources or prompts.
        accepts = request.headers.get("accept", "")
        if "application/json" not in accepts or "text/event-stream" not in accepts:
            return _invalid_request(406)
        version = request.headers.get("mcp-protocol-version")
        if version and version not in _SUPPORTED:
            return _invalid_request(400, "unsupported_protocol_version")
        rpc = await _rpc_body(request)
        if rpc is None:
            return _reply_error(None, -32700, "Invalid JSON-RPC request", http_status=400)
        auth = bearer_headers[0]
        try:
            async with session_factory() as db:
                actor = await verify_service(
                    db, authorization=auth, settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("Admin MCP authorization unavailable")
            return _invalid_request(503, "temporarily_unavailable")
        if actor is None:
            return _unauthorized()
        method = rpc["method"]
        ident = rpc.get("id")
        if method == "notifications/initialized" and ident is None:
            return Response(status_code=202, headers=_HEADERS)
        if ident is None:
            return _reply_error(None, -32600, "Request ID required")
        if method == "initialize":
            params = rpc.get("params", {})
            if not isinstance(params, dict):
                return _reply_error(ident, -32602, "Invalid params")
            return _reply_result(ident, {
                "protocolVersion": _PROTOCOL,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "hskai-admin-readonly", "version": "0.1"},
                "instructions": "Read-only statistics; no access to payments, users or feedback.",
            })
        if method == "ping":
            return _reply_result(ident, {})
        if method == "tools/list":
            return _reply_result(ident, {"tools": [{
                "name": "hskai_statistics",
                "description": "Read verified HSK AI administration statistics.",
                "inputSchema": StatisticsRequest.model_json_schema(),
                "annotations": {"readOnlyHint": True, "destructiveHint": False},
            }]})
        if method != "tools/call":
            return _reply_error(ident, -32601, "Method not found")
        params = rpc.get("params")
        if (not isinstance(params, dict) or set(params) != {"name", "arguments"}
                or params["name"] != "hskai_statistics"
                or not isinstance(params["arguments"], dict)):
            return _reply_error(ident, -32602, "Invalid tool arguments")
        try:
            async with session_factory() as db:
                data = await read_service(
                    db, authorization=auth,
                    args=params["arguments"], settings_obj=settings_obj,
                )
        except McpBearerDenied:
            return _unauthorized()
        except McpBearerBadArguments:
            return _reply_error(ident, -32602, "Invalid tool arguments")
        except Exception:
            logger.exception("Admin MCP statistics read unavailable")
            return _reply_error(ident, -32603, "Tool temporarily unavailable")
        payload = data.get("data")
        return _reply_result(ident, {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, default=str)}],
            "structuredContent": payload,
            "isError": False,
        })
    return router
