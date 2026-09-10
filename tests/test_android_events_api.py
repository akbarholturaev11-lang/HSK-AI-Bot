"""Native widget events use real bearer auth, strict fields and durable dedupe."""

import unittest
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.android_events import create_android_events_router
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.services.desktop_auth_service import DesktopAuthService
from tests.test_android_course_api import _settings, _user


class AndroidEventsApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user(1, 1001, "Widget test"))
            await session.commit()
        self.app = FastAPI()
        self.app.include_router(create_android_events_router(session_factory=self.sessions, settings_obj=_settings()))
        self.client = AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def token(self, platform="android"):
        async with self.sessions() as session:
            auth = DesktopAuthService(session, _settings())
            link = await auth.start_link(platform=platform, app_version="1.1.0", installation_key=uuid4().hex * 2)
            await auth.approve_link(display_code=link["display_code"], telegram_id=1001)
            linked = await auth.poll_link(link_request_id=link["link_request_id"], polling_secret=link["polling_secret"])
            return linked["access_token"]

    async def post(self, token, payload):
        return await self.client.post("/api/v3/android/events", headers={"Authorization": f"Bearer {token}"}, json=payload)

    async def test_bearer_required_and_desktop_token_rejected(self):
        payload = {"event_name": "android_widget_opened", "event_id": str(uuid4())}
        self.assertEqual(401, (await self.post("", payload)).status_code)
        self.assertEqual(403, (await self.post(await self.token("macos"), payload)).status_code)

    async def test_dedupe_uses_device_and_authenticated_user(self):
        token = await self.token()
        payload = {"event_name": "android_widget_opened", "event_id": str(uuid4())}
        first = await self.post(token, payload)
        second = await self.post(token, payload)
        self.assertEqual(200, first.status_code, first.text)
        self.assertTrue(first.json()["recorded"])
        self.assertTrue(second.json()["duplicate"])
        self.assertEqual("no-store", first.headers["cache-control"])
        async with self.sessions() as session:
            events = list((await session.scalars(select(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name == payload["event_name"]))).all())
            self.assertEqual(1, len(events))
            self.assertEqual(1001, events[0].telegram_id)
            self.assertEqual(1, events[0].user_id)
            self.assertEqual("android_native", events[0].source)

    async def test_event_allowlist_and_spoofed_identity_rejected(self):
        token = await self.token()
        valid = {"event_name": "android_widget_pinned", "event_id": str(uuid4())}
        for extra in ({"event_name": "android_lesson_completed"}, {"user_id": 2}, {"payload": {"xp": 999}}, {"event_id": "bad"}):
            response = await self.post(token, valid | extra)
            self.assertEqual(422, response.status_code, response.text)

    async def test_each_supported_event_and_revoked_token(self):
        token = await self.token()
        for name in ("android_widget_onboarding_viewed", "android_widget_pin_requested", "android_widget_pinned", "android_widget_opened", "android_notification_opened"):
            response = await self.post(token, {"event_name": name, "event_id": str(uuid4())})
            self.assertEqual(200, response.status_code, response.text)
        async with self.sessions() as session:
            await DesktopAuthService(session, _settings()).revoke(access_token=token, revoke_device=False)
        response = await self.post(token, {"event_name": "android_widget_opened", "event_id": str(uuid4())})
        self.assertEqual(401, response.status_code)

    async def test_oversized_body_rejected(self):
        response = await self.post(await self.token(), {"event_name": "x" * 10000, "event_id": str(uuid4())})
        self.assertEqual(413, response.status_code)
