"""Disabled-by-default, statistics-only MCP Streamable HTTP & OAuth transport.

This is a protocol boundary, NOT an activated ChatGPT connection. No browser
OAuth authorization/consent view is mounted yet. Its INDEPENDENT kill switch
ADMIN_PWA_MCP_TRANSPORT_ENABLED must remain false until a reviewed, localized
consent UI, strict client registration, audit, integration QA and owner approval
are complete.

OAuth access is NEVER a browser cookie, Google ID token or Telegram initData.
Only exact-audience, revocable, 5-minute OAuth grants authorize statistics.
"""
import asyncio
import json
import logging
from functools import partial
from typing import Any, Callable
from urllib.parse import parse_qsl

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.admin_api.pwa_mcp_oauth import (
    _registered_client, exchange_mcp_code,
)
from app.admin_api.pwa_mcp_resource import (
    _ready, _REQUIRED_RESOURCE, _ANALYTICS_SCOPE,
    verify_readonly_mcp_bearer, read_mcp_statistics_with_verified_token,
    _TOKEN_SHAPE,
    McpBearerBadArguments, McpBearerDenied,
)
from app.admin_api.pwa_mcp_security import (
    mcp_route_class, admit_mcp_http, finish_mcp_http,
    admit_mcp_statistics, limited_response,
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
_WWW_AUTH = ('Bearer resource_metadata="https://hskai.app/.well-known/oauth-protected-resource", '
             'scope="admin:analytics:read"')
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
    if request.url.path == "/mcp":
        origins = request.headers.getlist("origin")
        if (len(origins) > 1 or origins and origins != [_ISSUER]
                or request.headers.get("sec-fetch-site") == "cross-site"):
            return Response(status_code=403, headers=_HEADERS)
    return None


def _invalid_request(code: int = 400, error: str = "invalid_request") -> JSONResponse:
    return JSONResponse(status_code=code, content={"error": error}, headers=_HEADERS)


def _unauthorized(*, invalid_token: bool = False) -> Response:
    return Response(
        status_code=401,
        headers={**_HEADERS, "WWW-Authenticate": _WWW_AUTH + (
            ', error="invalid_token", error_description="Authorization expired or revoked; reconnect to authorize again"'
            if invalid_token else "") },
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


def _reject_json_constant(value: str):
    raise ValueError("nonfinite JSON")


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
        obj = json.loads(data.decode("utf-8", "strict"), object_pairs_hook=_no_duplicates,
                         parse_constant=_reject_json_constant)
    except (ValueError, UnicodeDecodeError, RecursionError):
        return None
    if not isinstance(obj, dict) or obj.get("jsonrpc") != "2.0":
        return None
    if (set(obj) - {"jsonrpc", "method", "params", "id"}
            or "params" in obj and not isinstance(obj["params"], dict)):
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
    admission_service: Callable = admit_mcp_http,
    completion_service: Callable = finish_mcp_http,
    statistics_admission: Callable = admit_mcp_statistics,
    statistics_reader=None,
) -> APIRouter:
    """Mountable only behind three default-off settings; no write tools."""
    if read_service is read_mcp_statistics_with_verified_token and session_factory is not None:
        from app.admin_api.pwa_statistics_cache import AdminPwaStatisticsReader
        reader = statistics_reader or AdminPwaStatisticsReader(
            settings_obj=settings_obj, session_factory=session_factory)
        read_service = partial(read_service, statistics_reader=reader)
    router = APIRouter(tags=["admin-pwa-mcp"], route_class=mcp_route_class(
        settings_obj=settings_obj, session_factory=session_factory, gate=_inactive_response,
        admission=admission_service, completion=completion_service))

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
            "authorization_response_iss_parameter_supported": True,
        }, headers=_HEADERS)

    @router.post("/oauth/token", include_in_schema=False)
    async def token(request: Request):
        failure = _inactive_response(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _invalid_request(503, "temporarily_unavailable")
        if (request.headers.get("authorization") or request.headers.get("cookie")
                or request.query_params or request.headers.get("origin") not in (None, _ISSUER)):
            return _invalid_request(400, "invalid_client")
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
            logger.error("Admin MCP OAuth token exchange unavailable")
            return _invalid_request(503, "temporarily_unavailable")
        if result is None:
            return _invalid_request(400, "invalid_grant")
        request.state.mcp_admin_id = getattr(result, "admin_user_id", None)
        request.state.mcp_action = "token_issued"
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
        accepts = set()
        for item in ",".join(request.headers.getlist("accept")).split(","):
            parts = item.strip().lower().split(";")
            try:
                quality = [float(p.strip()[2:]) for p in parts[1:] if p.strip().startswith("q=")]
                if len(quality) > 1 or quality and not 0 < quality[0] <= 1:
                    continue
            except ValueError:
                continue
            accepts.add(parts[0].strip())
        if not {"application/json", "text/event-stream"}.issubset(accepts):
            return _invalid_request(406)
        if len(request.headers.getlist("mcp-protocol-version")) > 1:
            return _invalid_request()
        version = request.headers.get("mcp-protocol-version")
        if version is not None and version not in _SUPPORTED:
            return _invalid_request(400, "unsupported_protocol_version")
        rpc = await _rpc_body(request)
        if rpc is None:
            return _reply_error(None, -32700, "Invalid JSON-RPC request", http_status=400)
        # This stateless server cannot recover a negotiated version from a
        # session and does not implement the legacy 2025-03-26 fallback.
        if rpc["method"] != "initialize" and version is None:
            return _invalid_request(400, "unsupported_protocol_version")
        auth = bearer_headers[0]
        try:
            async with session_factory() as db:
                actor = await verify_service(
                    db, authorization=auth, settings_obj=settings_obj,
                )
        except Exception:
            logger.error("Admin MCP authorization unavailable")
            return _invalid_request(503, "temporarily_unavailable")
        if actor is None:
            return _unauthorized(invalid_token=True)
        request.state.mcp_admin_id = actor.admin_user_id
        method = rpc["method"]
        request.state.mcp_action = method if method in {
            "initialize", "ping", "tools/list", "tools/call", "notifications/initialized",
        } else "unknown"
        ident = rpc.get("id")
        if method == "notifications/initialized" and ident is None:
            return Response(status_code=202, headers=_HEADERS)
        if ident is None:
            if method == "notifications/cancelled":
                return Response(status_code=202, headers=_HEADERS)
            return _reply_error(None, -32600, "Request ID required", http_status=400)
        if method == "initialize":
            params = rpc.get("params", {})
            if (not isinstance(params, dict)
                    or not isinstance(params.get("protocolVersion"), str)
                    or not isinstance(params.get("capabilities"), dict)
                    or not isinstance(params.get("clientInfo"), dict)
                    or not all(isinstance(params["clientInfo"].get(key), str)
                               and params["clientInfo"][key] for key in ("name", "version"))):
                return _reply_error(ident, -32602, "Invalid params")
            return _reply_result(ident, {
                "protocolVersion": params["protocolVersion"] if params["protocolVersion"] in _SUPPORTED else _PROTOCOL,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "hskai-admin-readonly", "version": "0.1"},
                "instructions": "Read-only statistics; no access to payments, users or feedback.",
            })
        if method == "ping":
            return _reply_result(ident, {})
        if method == "tools/list":
            return _reply_result(ident, {"tools": [{
                "name": "hskai_statistics",
                "description": "Read verified daily HSK AI statistics; generated_at identifies the 24-hour snapshot.",
                "inputSchema": StatisticsRequest.model_json_schema(),
                "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
                "securitySchemes": [{"type": "oauth2", "scopes": [_ANALYTICS_SCOPE]}],
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
                allowed, retry = await statistics_admission(db, admin_user_id=actor.admin_user_id)
            if not allowed:
                return limited_response(retry)
            async with asyncio.timeout(10), session_factory() as db:
                data = await read_service(
                    db, authorization=auth,
                    args=params["arguments"], settings_obj=settings_obj,
                )
        except McpBearerDenied:
            return _unauthorized(invalid_token=True)
        except McpBearerBadArguments:
            return _reply_error(ident, -32602, "Invalid tool arguments")
        except Exception:
            logger.error("Admin MCP statistics read unavailable")
            return _reply_error(ident, -32603, "Tool temporarily unavailable")
        payload = data.get("data")
        return _reply_result(ident, {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, default=str)}],
            "structuredContent": payload,
            "isError": False,
        })
    return router
