"""Isolated synthetic ASGI factory. Production continues to use app.main:app.

Run with uvicorn app.smart_reminder_qa:create_app --factory. No DB bootstrap,
seeding, provider, bot, scheduler, static/private lesson or public signup route.
"""
from contextlib import asynccontextmanager
from datetime import timedelta
from fractions import Fraction
import os
from pathlib import Path

from scripts import smart_reminder_qa_guard as guard


def qa_calibration():
    from app.services.smart_reminder_cadence import CadenceCalibration
    return CadenceCalibration(guard.FIXTURE_VERSION, 4, Fraction(2), Fraction(1), 2, 5, 3)


def create_app(*, session_factory=None, engine_obj=None, settings_obj=None):
    # Verify before importing settings/engine; .env must never inject providers.
    url = guard.validate(dict(os.environ))
    if Path(".env").exists():
        raise RuntimeError("smart_qa_dotenv_refused")
    os.environ["DATABASE_URL"] = url
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from sqlalchemy import func, select, text
    if settings_obj is None:
        from app.config import settings as settings_obj
    if session_factory is None or engine_obj is None:
        from app.db.session import engine, async_session_maker
        session_factory, engine_obj = async_session_maker, engine
    settings = settings_obj
    async_session_maker, engine = session_factory, engine_obj
    from app.db import models  # noqa: F401
    from app.db.models.user import User
    from app.db.models.payment import Payment
    from app.db.models.user_identity import UserIdentity
    from app.db.models.desktop import DesktopDevice, DesktopSession
    from app.db.models.smart_reminder import SmartReminderRouting
    from app.api.android_auth import create_android_auth_router
    from app.api.smart_reminder import create_smart_reminder_router
    from app.services.smart_reminder_android import AndroidAdmission, SmartReminderAndroidService
    from app.services.smart_reminder_telegram import LearningCoverage
    from scripts.qa_standalone_bootstrap import EXPECTED_HEAD

    # Explicit simulation values; cannot become a production default.
    calibration = qa_calibration()

    async def admission(session, actor, job_id, now):
        if actor.user_id != guard.USER_ID or actor.device_id != guard.DEVICE_IDS[0] or job_id not in guard.JOB_IDS:
            return None
        row = await session.get(SmartReminderRouting, guard.USER_ID)
        if not row or not row.verified_at or not row.verified_until or not row.evidence_sha256 or not row.inventory_sha256:
            return None
        return AndroidAdmission(user_id=guard.USER_ID,job_id=job_id,device_id=guard.DEVICE_IDS[0],
            session_id=guard.SESSION_IDS[0],generation=row.generation,preference_revision=row.preference_revision,
            grant_epoch=row.grant_epoch,verified_at=row.verified_at,valid_until=row.verified_until,
            history_since=row.verified_at-timedelta(days=30),evidence_sha256=row.evidence_sha256,inventory_sha256=row.inventory_sha256,
            legacy_quiesced=True,legacy_outcomes_reconciled=True,other_study_fenced=True)

    async def coverage(session, actor, since, now):
        if actor.user_id != guard.USER_ID:
            return None
        return LearningCoverage(actor.user_id,since,now,guard.FIXTURE_VERSION)

    def delivery(session):
        return SmartReminderAndroidService(session, enabled=True,admission_reader=admission,
            calibration=calibration,coverage_reader=coverage)

    @asynccontextmanager
    async def lifespan(_):
        try:
            async with async_session_maker() as session:
                revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
                users = (await session.execute(select(User.id,User.full_name))).all()
                devices = set((await session.scalars(select(DesktopDevice.id))).all())
                sessions = set((await session.scalars(select(DesktopSession.id))).all())
                payments = await session.scalar(select(func.count()).select_from(Payment))
                identities = await session.scalar(select(func.count()).select_from(UserIdentity))
                if (revision != EXPECTED_HEAD or users != [(guard.USER_ID,guard.FIXTURE_VERSION)] or
                        devices != set(guard.DEVICE_IDS) or sessions != set(guard.SESSION_IDS) or payments or identities):
                    raise RuntimeError("smart_qa_fixture_or_schema_unverified")
            yield
        finally:
            await engine.dispose()

    app = FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    auth = create_android_auth_router(session_factory=async_session_maker,settings_obj=settings)
    auth.routes[:] = [r for r in auth.routes if r.path in {
        "/api/v3/android-auth/refresh","/api/v3/android-auth/revoke","/api/v3/android/bootstrap"}]
    app.include_router(auth)
    smart = create_smart_reminder_router(session_factory=async_session_maker,settings_obj=settings,
        android_delivery_factory=delivery)
    smart.routes[:] = [r for r in smart.routes if r.path.startswith("/api/v3/android/")]
    app.include_router(smart)

    @app.middleware("http")
    async def bound_host(request: Request, call_next):
        if request.url.path != "/health" and request.url.hostname != guard.DOMAIN:
            return JSONResponse({"ok":False,"error":"qa_origin_invalid"},status_code=400)
        result = await call_next(request)
        result.headers["Cache-Control"] = "no-store"
        return result

    @app.get("/health")
    async def health():
        return {"ok":True,"synthetic_qa":True,"schema_revision":EXPECTED_HEAD}
    return app
