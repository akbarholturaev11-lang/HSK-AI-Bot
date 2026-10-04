"""Unpaid HSK 3.0 entry requires unlock; authentication stays separate."""

import ast
import hashlib
import hmac
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.course_progress_repo import CourseProgressRepository
from app.repositories.user_repo import UserRepository
from app.services.course_access_policy_service import CourseAccessPolicyService
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.course_track_service import CourseTrackService
from app.services.entitlements.lesson_access import LessonAccessService
from app.services.entitlements.state import access_expires_at, resolve_state
from app.services.hsk30_feature_service import Hsk30FeatureService
from app.services.study_miniapp_service import StudyMiniAppService
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id


BOT_TOKEN = "12345:map-test-token"


def signed_init_data():
    values = {
        "auth_date": str(int(datetime.now(timezone.utc).timestamp())),
        "user": '{"id":7100,"first_name":"Map tester"}',
    }
    check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def map_handler(session_factory):
    # Compile the actual endpoint alone: importing app.main starts unrelated
    # bot/router configuration. Access, profile and progress services are real.
    source = Path("app/main.py").read_text(encoding="utf-8")
    handler = next(node for node in ast.parse(source).body
                   if isinstance(node, ast.AsyncFunctionDef) and node.name == "v3_course_map")
    handler.decorator_list = []
    snapshot = {"xp": 0, "streak": 0, "weekly_xp": 0, "league": "bronze"}
    namespace = dict(globals())
    namespace.update({
        "async_session_maker": session_factory,
        "settings": SimpleNamespace(BOT_TOKEN=BOT_TOKEN),
        "_course_v3_user_level": lambda user: user.level,
        "_course_v3_user_lang": lambda user: user.language,
        "_course_v3_level": lambda level: level,
        "_apply_course_v3_progress_marks": lambda data, completed: None,
        "_checkout_text": lambda value, limit: str(value or "")[:limit],
        "bot_username_value": lambda: "map_test_bot",
        "admin_contact_url": lambda value: "",
        "ADMIN_CONTACT_KEY": "admin_contact",
        "CourseGamificationService": lambda session: SimpleNamespace(snapshot=AsyncMock(return_value=snapshot)),
        "CourseNotificationService": lambda session: SimpleNamespace(list_for_user=AsyncMock(return_value=[])),
        "CourseTodayService": lambda session: SimpleNamespace(payload=AsyncMock(return_value=None)),
        "MiniAppHintService": lambda session: SimpleNamespace(hints_for=AsyncMock(return_value=[])),
        "CourseMiniAppAnalyticsService": lambda session: SimpleNamespace(record_server_event=AsyncMock()),
        "CourseSalesExperimentService": lambda session: SimpleNamespace(resolve_offer=AsyncMock(return_value={})),
    })
    exec(compile(ast.Module(body=[handler], type_ignores=[]), "app/main.py", "exec"), namespace)
    return namespace["v3_course_map"]


class Hsk30MapAccessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(User(id=1, telegram_id=7100, full_name="Map tester", language="uz",
                             level="nhsk1", learning_mode="course", status="free", payment_status="none"))
            await Hsk30FeatureService(session).set_enabled(True)
            await session.commit()
        app = FastAPI()
        app.get("/api/v3/map")(map_handler(self.sessions))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://map.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def test_unpaid_learner_requires_unlock_before_course_entry(self):
        response = await self.client.get("/api/v3/map", headers={"X-Telegram-Init-Data": signed_init_data()})
        self.assertEqual(403, response.status_code)
        data = response.json()
        self.assertEqual("hsk30_unlock_required", data["error"])
        self.assertFalse(data["hsk30_access"]["allowed"])
        self.assertNotIn("units", data)
        async with self.sessions() as session:
            user = await UserRepository(session).get_by_telegram_id(7100)
            material = await LessonAccessService(session).status(user, level="nhsk1", lesson_order=1, consume=True)
        self.assertFalse(material["allowed"])
        self.assertEqual("hsk30_unlock_required", material["error"])

    async def test_feature_disabled_still_blocks_map(self):
        async with self.sessions() as session:
            await Hsk30FeatureService(session).set_enabled(False)
            await session.commit()
        response = await self.client.get("/api/v3/map", headers={"X-Telegram-Init-Data": signed_init_data()})
        self.assertEqual(403, response.status_code)
        self.assertEqual("hsk30_disabled", response.json()["error"])

    async def test_unsigned_map_request_is_still_unauthorized(self):
        response = await self.client.get("/api/v3/map")
        self.assertEqual(401, response.status_code)
        self.assertEqual("auth_required", response.json()["error"])
