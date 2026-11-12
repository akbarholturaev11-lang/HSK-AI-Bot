"""Mini App app-offer events reach the server cooldown for iPhone and Play.

Calls the real `/api/miniapp/event` handler with a SQLite session; only the
Telegram signature check is replaced. Contract:
docs/TELEGRAM_PWA_ANDROID_HANDOFF_CONTEXT.md.
"""
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import main
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.db.models.user_client_presence import AppPromoState


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload
        self.headers = {"X-Telegram-Init-Data": "signed"}

    async def json(self):
        return self.payload


class AppOfferEventTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add(User(
                id=1, telegram_id=1001, full_name="L", language="uz", level="hsk1",
                learning_mode="course", voice_mode="none", status="free",
                payment_status="none", question_limit=5, questions_used=0,
                bonus_questions=0, bonus_questions_used=0, discount_referral_count=0,
                discount_eligible=False, discount_used=False, daily_practice_streak=0,
                created_at=now, last_active_at=now))
            await session.commit()
        self.patches = [
            patch.object(main, "async_session_maker", self.sessions),
            patch.object(main, "extract_verified_webapp_user_id", lambda *_: 1001),
        ]
        for item in self.patches:
            item.start()

    async def asyncTearDown(self):
        for item in self.patches:
            item.stop()
        await self.engine.dispose()

    async def send(self, **payload):
        return await main.miniapp_event(FakeRequest(payload))

    async def state(self, platform):
        async with self.sessions() as session:
            return (await session.execute(select(AppPromoState).where(
                AppPromoState.telegram_id == 1001,
                AppPromoState.target_platform == platform))).scalar_one_or_none()

    async def test_opening_the_play_listing_records_it_and_starts_android_cooldown(self):
        result = await self.send(event="android_play_opened", source="home_prompt",
                                 target_platform="android", event_id="evt-play-1")
        self.assertTrue(result.get("ok"), result)
        state = await self.state("android")
        self.assertIsNotNone(state.last_download_requested_at)
        self.assertIsNone(await self.state("ios"))
        async with self.sessions() as session:
            names = (await session.execute(select(CourseMiniAppEvent.event_name))).scalars().all()
        self.assertEqual(names, ["android_play_opened"])
        # The same event id is one fact, not two.
        await self.send(event="android_play_opened", source="home_prompt",
                        target_platform="android", event_id="evt-play-1")
        async with self.sessions() as session:
            names = (await session.execute(select(CourseMiniAppEvent.event_name))).scalars().all()
        self.assertEqual(names, ["android_play_opened"])

    async def test_iphone_offer_seen_and_dismissed_use_their_own_cooldown(self):
        await self.send(event="desktop_promo_seen", source="home_prompt",
                        target_platform="ios", event_id="evt-ios-1")
        await self.send(event="desktop_promo_dismissed", source="home_prompt",
                        target_platform="ios", event_id="evt-ios-2")
        state = await self.state("ios")
        self.assertIsNotNone(state.last_seen_at)
        self.assertIsNotNone(state.last_dismissed_at)
        self.assertIsNone(await self.state("android"))

    async def test_server_only_handoff_events_cannot_be_forged_by_the_client(self):
        for name in ("pwa_handoff_issued", "pwa_handoff_completed"):
            await self.send(event=name, source="home_prompt", event_id="forged-" + name)
        async with self.sessions() as session:
            names = (await session.execute(select(CourseMiniAppEvent.event_name))).scalars().all()
        self.assertEqual(names, [])
        self.assertIsNone(await self.state("ios"))

    async def test_telegram_telemetry_ignores_caller_platform_markers(self):
        sent = await self.send(event="section_started", source=" PWA_COURSE_V3 ",
                               client="android", transport="iphone_pwa",
                               event_id="fixture:section", session_id="fixture:session")
        self.assertTrue(sent.get("ok"), sent)
        async with self.sessions() as session:
            row = (await session.execute(select(CourseMiniAppEvent))).scalar_one()
        self.assertEqual(row.source, "course_miniapp")
        self.assertEqual(row.user_id, 1)
        self.assertEqual(row.dedupe_key, "fixture:section")
        payload = json.loads(row.payload_json)
        self.assertFalse({"source", "transport"} & payload.keys())
        self.assertEqual(payload["client"], "telegram")

    def test_analytics_marker_never_truncates_an_existing_payload(self):
        from app.services.course_miniapp_analytics_service import (
            CourseMiniAppAnalyticsService, MAX_EVENT_PAYLOAD_CHARS,
        )

        payload = {"grading_snapshot": "字" * (MAX_EVENT_PAYLOAD_CHARS - 23)}
        serialized = CourseMiniAppAnalyticsService._payload_json(payload)
        self.assertEqual(json.loads(serialized), payload)
        self.assertEqual(
            CourseMiniAppAnalyticsService._payload_json(payload, analytics_client="iphone_pwa"),
            serialized,
        )

    async def test_telegram_map_preserves_campaign_source_but_not_reserved_pwa_source(self):
        app = FastAPI()
        app.add_api_route("/api/v3/map", main.v3_course_map, methods=["GET"])
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://synthetic.test") as client:
            for source, sid in (("pwa_course_v3", "reserved"), ("reviewed_campaign", "campaign")):
                response = await client.get(
                    "/api/v3/map", params={"source": source, "sid": sid},
                    headers={"X-Telegram-Init-Data": "signed"},
                )
                self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as session:
            rows = (await session.scalars(select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.event_name == "miniapp_opened"
            ))).all()
        self.assertEqual({row.dedupe_key: row.source for row in rows}, {
            "course-v3:miniapp-opened:reserved": "course_v3",
            "course-v3:miniapp-opened:campaign": "reviewed_campaign",
        })


if __name__ == "__main__":
    unittest.main()
