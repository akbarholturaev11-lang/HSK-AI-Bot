"""Distributed MCP quotas and content-free audit, isolated from read snapshots.

No IP, headers, URL/query, state, PKCE, cookie, token, arguments or response
payload is stored. Anonymous admission uses fixed endpoint-wide buckets, so
forged tokens cannot grow arbitrary buckets. Deployment still needs an edge
request limit; database admission is not a network denial-of-service defense.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.admin_api.pwa_approval import _utc
from app.db.models.admin_pwa_mcp_security import AdminPwaMcpAudit, AdminPwaMcpQuota

logger = logging.getLogger(__name__)
# Per minute, shared by every process and instance using the same database.
_LIMITS = {"authorize": 60, "authorize_decision": 60, "token": 60,
           "mcp_post": 300, "history": 60, "revoke": 30}
_ACTIONS = frozenset({*_LIMITS, "initialize", "ping", "tools/list", "tools/call",
                      "notifications/initialized", "consent_approved", "consent_denied",
                      "consent_revoked", "token_issued", "unknown"})
_STATISTICS_PER_ADMIN = 30
_RETENTION = timedelta(days=7)
_HEADERS = {"Cache-Control": "no-store", "Pragma": "no-cache"}


async def consume_mcp_quota(db: Any, *, key: str, limit: int,
                            now: datetime | None = None) -> tuple[bool, bool, int]:
    """Caller owns transaction. Returns allowed, first rejection, retry seconds.

    Upsert plus row lock serializes first use and subsequent admission across
    workers. SQLite is a test adapter; concurrency evidence uses PostgreSQL.
    """
    stamp = _utc(now or datetime.now(timezone.utc))
    window = stamp.replace(second=0, microsecond=0)
    retry = max(1, int((window + timedelta(minutes=1) - stamp).total_seconds() + .999))
    dialect = db.get_bind().dialect.name
    insert = {"postgresql": pg_insert, "sqlite": sqlite_insert}[dialect]
    await db.execute(insert(AdminPwaMcpQuota).values(
        key=key, window_start=window, hits=0,
    ).on_conflict_do_nothing(index_elements=["key"]))
    row = (await db.execute(select(AdminPwaMcpQuota).where(
        AdminPwaMcpQuota.key == key,
    ).with_for_update().execution_options(populate_existing=True))).scalar_one()
    if _utc(row.window_start) != window:
        row.window_start = window
        row.hits = 0
    previous = row.hits
    row.hits = min(previous + 1, limit + 1)
    await db.flush()
    return previous < limit, previous == limit, retry


async def admit_mcp_http(db: Any, *, action: str, now: datetime | None = None):
    stamp = _utc(now or datetime.now(timezone.utc))
    async with db.begin():
        allowed, first_denial, retry = await consume_mcp_quota(
            db, key="http:" + action, limit=_LIMITS[action], now=stamp)
        identifier = str(uuid4()) if allowed or first_denial else None
        if identifier:
            db.add(AdminPwaMcpAudit(
                id=identifier, action=action,
                outcome="started" if allowed else "limited",
                status_code=None if allowed else 429, created_at=stamp))
        # Bounded opportunistic retention; no mutation to analytics snapshots.
        old = select(AdminPwaMcpAudit.id).where(
            AdminPwaMcpAudit.created_at < stamp - _RETENTION,
        ).order_by(AdminPwaMcpAudit.created_at).limit(100)
        await db.execute(delete(AdminPwaMcpAudit).where(AdminPwaMcpAudit.id.in_(old)))
    return allowed, identifier, retry


async def finish_mcp_http(db: Any, *, identifier: str, action: str,
                          status_code: int, admin_user_id: int | None,
                          failed: bool = False):
    if action not in _ACTIONS:
        action = "unknown"
    async with db.begin():
        await db.execute(update(AdminPwaMcpAudit).where(
            AdminPwaMcpAudit.id == identifier,
        ).values(action=action, status_code=status_code, admin_user_id=admin_user_id,
                 outcome="rejected" if failed or status_code >= 400 else "completed"))


async def admit_mcp_statistics(db: Any, *, admin_user_id: int,
                                now: datetime | None = None) -> tuple[bool, int]:
    async with db.begin():
        allowed, _, retry = await consume_mcp_quota(
            db, key=f"admin:{admin_user_id}:statistics", limit=_STATISTICS_PER_ADMIN, now=now)
    return allowed, retry


def limited_response(retry: int):
    return JSONResponse({"error": "rate_limited"}, status_code=429,
                        headers={**_HEADERS, "Retry-After": str(retry)})


def mcp_route_class(*, settings_obj: Any, session_factory: Callable | None,
                    gate: Callable, admission: Callable = admit_mcp_http,
                    completion: Callable = finish_mcp_http):
    """Protect only these MCP routes, with an audit reservation BEFORE work.

    Missing quota/audit persistence fails shut. A crash leaves a started record
    instead of making an unaudited call. Repeated over-quota requests generate
    only one denial record per endpoint/window, preventing audit amplification.
    """
    class AuditedRoute(APIRoute):
        def get_route_handler(self):
            handler = super().get_route_handler()
            if self.name not in _LIMITS:
                return handler

            @wraps(handler)
            async def run(request: Request):
                failure = gate(request, settings_obj)
                if failure is not None:
                    return failure
                if session_factory is None:
                    return JSONResponse({"error": "temporarily_unavailable"}, status_code=503, headers=_HEADERS)
                try:
                    async with session_factory() as db:
                        allowed, identifier, retry = await admission(db, action=self.name)
                    if not allowed:
                        return limited_response(retry)
                    response = await handler(request)
                    failed = False
                    if response.status_code == 200 and isinstance(response, JSONResponse):
                        # Only inspect a server-created envelope, never persist it.
                        envelope = json.loads(response.body)
                        failed = "error" in envelope or envelope.get("result", {}).get("isError", False)
                    async with session_factory() as db:
                        await completion(
                            db, identifier=identifier,
                            action=getattr(request.state, "mcp_action", self.name),
                            status_code=response.status_code,
                            admin_user_id=getattr(request.state, "mcp_admin_id", None),
                            failed=failed)
                    return response
                except Exception:
                    # Exceptions/SQL parameters may contain OAuth secrets.
                    logger.error("MCP audit/admission or request failed")
                    return JSONResponse({"error": "temporarily_unavailable"}, status_code=503, headers=_HEADERS)
            return run
    return AuditedRoute
