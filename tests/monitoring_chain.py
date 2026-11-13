"""Shared runtime chain helper for monitoring coverage (design D10).

`assert_monitoring_chain` drives the real intake for one platform into
PostgreSQL and the authenticated Admin Inbox. Only then does it append
`platform|feature|failure` to the file named by `MONITORING_CHAIN_PROOF`,
which the post-pytest `--chain-proof` checker step reads. A skipped, mocked or
SQLite run therefore leaves no proof.

"""
import hashlib
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401  (register every table)
from app.db.base import Base
from app.admin_api.pwa_inbox_triage import create_admin_pwa_inbox_triage_router
from app.admin_api.pwa_read import create_admin_pwa_read_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.diagnostic import DiagnosticIncident
from app.db.models.user import User
from app.services.monitoring import catalog
from app.services.monitoring.intake import fingerprint

PG_URL = os.getenv("MONITORING_TEST_DATABASE_URL") or os.getenv("ANALYTICS_TEST_DATABASE_URL") or ""
PROOF_ENV = "MONITORING_CHAIN_PROOF"
CLIENT_INTAKE = {"android": "/api/v3/android/diagnostics", "iphone_pwa": "/api/v3/pwa/diagnostics",
                 "telegram": "/api/miniapp/event"}
ADMIN_ORIGIN = "https://hskai.app"


@asynccontextmanager
async def admin_client(sessions, *, admin_user_id=2, telegram_id=2002):
    """Seed a verified-session fixture, then use the real API."""
    cookie = secrets.token_urlsafe(48)
    async with sessions() as db, db.begin():
        if await db.get(User, admin_user_id) is None:
            db.add(User(id=admin_user_id, telegram_id=telegram_id, status="free"))
            await db.flush()
        db.add(AdminPwaSession(
            id=str(uuid4()), user_id=admin_user_id, token_hash=hashlib.sha256(cookie.encode()).hexdigest(),
            auth_method="webauthn", expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ))
    settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN=ADMIN_ORIGIN,
                               admin_id_list=[telegram_id])
    app = FastAPI()
    app.include_router(create_admin_pwa_read_router(settings_obj=settings, session_factory=sessions))
    app.include_router(create_admin_pwa_inbox_triage_router(settings_obj=settings, session_factory=sessions))
    async with AsyncClient(transport=ASGITransport(app=app), base_url=ADMIN_ORIGIN,
                           headers={"Origin": ADMIN_ORIGIN},
                           cookies={ADMIN_PWA_COOKIE_NAME: cookie}) as client:
        yield client


@asynccontextmanager
async def pg_sessions(url, users=((1, 1001), (2, 2002))):
    """A disposable schema on a loopback `*_test` PostgreSQL database."""
    parsed = urlsplit(url)
    if parsed.scheme != "postgresql+asyncpg" or parsed.hostname not in {"127.0.0.1", "::1", "localhost"} \
            or not parsed.path.endswith("_test"):
        raise ValueError("the monitoring PostgreSQL URL must name a disposable *_test database over loopback")
    schema = "monitoring_test_" + uuid4().hex
    engine = create_async_engine(url, pool_size=4, connect_args={"server_settings": {"search_path": schema,
                                                                                      "timezone": "UTC"}})
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {schema}"))
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        if users:
            async with sessions() as db, db.begin():
                db.add_all([User(id=uid, telegram_id=tid, status="free") for uid, tid in users])
        yield sessions
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        await engine.dispose()


def client_event(feature, failure, site, platform="android", **overrides):
    """One diag.v1 event, content-free, with the owner left to the session.
    Only Android sends a release channel."""
    item = {"event_id": str(uuid4()), "client_time": int(datetime.now(timezone.utc).timestamp() * 1000),
            "feature_code": feature,
            "failure_code": failure, "site_code": site, "outcome": "failed"}
    if platform == "android":
        item.update(channel="play", app_version="1.8.0", build=40)
    else:
        item.update(app_version="20261113-abcdef123456", build=20261113)
    item.update(overrides)
    return item


def _write_proof(platform, feature, failure):
    path = os.environ.get(PROOF_ENV, "").strip()
    if path:
        with open(path, "a", encoding="utf-8") as proof:
            proof.write(f"{platform}|{feature}|{failure}\n")


async def assert_monitoring_chain(case, *, platform, feature, failure, site, sessions,
                                  inbox_route, intake_route=None, client=None, headers=None, reporter=None, trigger=None):
    """Intake → PostgreSQL incident → authenticated Inbox → proof row.

    Client platforms post through their real intake route. The server chain runs
    through `reporter`: `trigger` (for example a request through the real
    middleware) causes the failure; without it the helper reports it directly.
    """
    case.assertIn(feature, catalog.FEATURES)
    case.assertIn(failure, catalog.FAILURES)
    async with sessions() as db:
        case.assertEqual(db.get_bind().dialect.name, "postgresql", "a chain proof needs PostgreSQL")
        before = await db.scalar(select(DiagnosticIncident.occurrence_count).where(
            DiagnosticIncident.fingerprint == fingerprint(platform, feature, failure, site))) or 0

    if platform in CLIENT_INTAKE:
        case.assertIsNotNone(client, "client platforms post through the real intake route")
        case.assertEqual(intake_route, CLIENT_INTAKE[platform])
        payload = {"schema": catalog.SCHEMA, "events": [client_event(feature, failure, site, platform)]}
        if platform == "telegram":
            payload["event"] = "app_error"
        response = await client.post(intake_route, headers=headers or {}, json=payload)
        case.assertEqual(response.status_code, 200, response.text)
        case.assertEqual(response.json().get("accepted"), 1, response.text)
        retry = await client.post(intake_route, headers=headers or {}, json=payload)
        case.assertEqual(retry.status_code, 200, retry.text)
        case.assertEqual(retry.json().get("duplicates"), 1, retry.text)
    elif platform == "server":
        case.assertIsNotNone(reporter, "the server chain runs through the backend reporter")
        if trigger is None:
            reporter.report(feature, failure, site)
        else:
            await trigger()
        await reporter.drain()
    else:
        case.fail(f"no monitoring chain for {platform!r} yet (task 4.1)")

    async with sessions() as db:
        incident = (await db.execute(select(DiagnosticIncident).where(
            DiagnosticIncident.fingerprint == fingerprint(platform, feature, failure, site)))).scalar_one_or_none()
    case.assertIsNotNone(incident, f"no incident for {platform}|{feature}|{failure}|{site}")
    case.assertEqual((incident.platform, incident.feature_code, incident.failure_code, incident.site_code),
                     (platform, feature, failure, site))
    case.assertEqual(incident.occurrence_count, before + 1)
    async with admin_client(sessions) as admin:
        response = await admin.post(inbox_route, json={"source": "diagnostic", "platform": platform})
    case.assertEqual(response.status_code, 200, response.text)
    rows = [row for row in response.json()["items"] if row["source_id"] == incident.id]
    case.assertEqual(len(rows), 1, response.text)
    item = rows[0]
    case.assertEqual((item["platform"], item["feature_code"], item["failure_code"], item["occurrences"]),
                     (platform, feature, failure, before + 1))
    case.assertTrue({"user_id", "telegram_id", "message", "fingerprint", "stack", "event_id"}.isdisjoint(item))
    _write_proof(platform, feature, failure)
    return incident
