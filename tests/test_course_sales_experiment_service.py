import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401 - register all metadata foreign keys
from app.db.base import Base
from app.db.models.course_miniapp_event import (
    CLIENT_COURSE_MINIAPP_EVENT_NAMES,
    COURSE_MINIAPP_EVENT_NAMES,
    CourseMiniAppEvent,
)
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.course_sales_experiment_service import (
    SALES_EXPERIMENT_CLIENT_EVENTS,
    SALES_EXPERIMENT_ID,
    SALES_OFFER_ASSIGNED_EVENT,
    CourseSalesExperimentService,
    CourseSalesExperimentSettings,
)


def _access(mode: str = "subscription"):
    return SimpleNamespace(active_mode=mode)


def _user(
    telegram_id: int,
    *,
    created_at: datetime,
    level: str = "hsk1",
    status: str = "free",
    payment_status: str = "none",
    end_date: datetime | None = None,
    discount_eligible: bool = False,
    discount_offer_started_at: datetime | None = None,
) -> User:
    return User(
        telegram_id=telegram_id,
        full_name=f"Student {telegram_id}",
        language="uz",
        level=level,
        learning_mode="course",
        voice_mode="none",
        status=status,
        payment_status=payment_status,
        end_date=end_date,
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=discount_eligible,
        discount_used=False,
        discount_offer_started_at=discount_offer_started_at,
        daily_practice_streak=0,
        created_at=created_at,
        last_active_at=created_at,
    )


class CourseSalesExperimentSettingsTests(unittest.TestCase):
    def test_invalid_stored_settings_fail_closed(self):
        self.assertEqual(
            CourseSalesExperimentSettings.from_raw("not-json").mode,
            "off",
        )
        self.assertEqual(
            CourseSalesExperimentSettings.from_raw(
                json.dumps({"mode": "ab", "treatment_percent": 75})
            ).mode,
            "off",
        )
        self.assertEqual(
            CourseSalesExperimentSettings.from_raw(
                json.dumps({"mode": "ab", "treatment_percent": 50})
            ).mode,
            "off",
        )

    def test_only_supported_modes_and_percentages_are_accepted(self):
        now = datetime(2026, 8, 14, 10, tzinfo=timezone.utc)
        for mode in ("off", "shadow", "ab", "treatment"):
            for percent in (0, 50, 90, 100):
                with self.subTest(mode=mode, percent=percent):
                    value = CourseSalesExperimentSettings.from_payload(
                        {"mode": mode, "treatment_percent": percent},
                        now=now,
                    )
                    self.assertEqual(value.mode, mode)
                    self.assertEqual(value.treatment_percent, percent)
        with self.assertRaises(ValueError):
            CourseSalesExperimentSettings.from_payload(
                {"mode": "ab", "treatment_percent": 75},
                now=now,
            )

    def test_sha_assignment_is_stable_and_balanced(self):
        buckets = [
            CourseSalesExperimentService.assignment_bucket(value)
            for value in range(1, 1001)
        ]
        self.assertEqual(
            CourseSalesExperimentService.assignment_bucket(12345),
            CourseSalesExperimentService.assignment_bucket(12345),
        )
        treatment = sum(bucket < 50 for bucket in buckets)
        self.assertGreater(treatment, 440)
        self.assertLess(treatment, 560)


class CourseSalesExperimentServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.started_at = datetime(2026, 8, 14, 10, tzinfo=timezone.utc)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _enable(self, session, *, mode="ab", percent=50):
        return await CourseSalesExperimentService(session).save_settings(
            {"mode": mode, "treatment_percent": percent},
            now=self.started_at,
            updated_by_telegram_id=999,
        )

    async def test_shadow_returns_control_contract_without_assignment(self):
        async with self.sessions() as session:
            await self._enable(session, mode="shadow", percent=50)
            user = _user(1001, created_at=self.started_at + timedelta(seconds=1))
            session.add(user)
            await session.flush()

            offer = await CourseSalesExperimentService(session).resolve_offer(
                user=user,
                level="hsk1",
                access_policy=_access(),
                now=self.started_at + timedelta(minutes=1),
            )

            self.assertEqual(
                offer,
                {
                    "experiment_id": SALES_EXPERIMENT_ID,
                    "arm": "control",
                    "trigger": "hsk1_first_checkpoint",
                },
            )
            count = await session.scalar(
                select(func.count(CourseMiniAppEvent.id)).where(
                    CourseMiniAppEvent.event_name == SALES_OFFER_ASSIGNED_EVENT
                )
            )
            self.assertEqual(count, 0)

    async def test_off_returns_no_contract_or_assignment(self):
        async with self.sessions() as session:
            user = _user(1002, created_at=self.started_at + timedelta(seconds=1))
            session.add(user)
            await session.flush()

            offer = await CourseSalesExperimentService(session).resolve_offer(
                user=user,
                level="hsk1",
                access_policy=_access(),
                now=self.started_at + timedelta(minutes=1),
            )

            self.assertIsNone(offer)
            count = await session.scalar(
                select(func.count(CourseMiniAppEvent.id)).where(
                    CourseMiniAppEvent.event_name == SALES_OFFER_ASSIGNED_EVENT
                )
            )
            self.assertEqual(count, 0)

    async def test_assignment_persists_and_survives_percentage_change(self):
        control_id = next(
            telegram_id
            for telegram_id in range(2000, 3000)
            if CourseSalesExperimentService.assignment_bucket(telegram_id) >= 50
        )
        async with self.sessions() as session:
            await self._enable(session, mode="ab", percent=50)
            user = _user(
                control_id,
                created_at=self.started_at + timedelta(seconds=1),
            )
            session.add(user)
            await session.flush()
            service = CourseSalesExperimentService(session)

            first = await service.resolve_offer(
                user=user,
                level="hsk1",
                access_policy=_access(),
                now=self.started_at + timedelta(minutes=1),
            )
            await service.save_settings(
                {"mode": "ab", "treatment_percent": 100},
                now=self.started_at + timedelta(hours=1),
            )
            second = await service.resolve_offer(
                user=user,
                level="hsk1",
                access_policy=_access(),
                now=self.started_at + timedelta(hours=1),
            )

            self.assertEqual(first["arm"], "control")
            self.assertEqual(second["arm"], "control")
            assignments = (
                await session.execute(
                    select(CourseMiniAppEvent).where(
                        CourseMiniAppEvent.telegram_id == control_id,
                        CourseMiniAppEvent.event_name == SALES_OFFER_ASSIGNED_EVENT,
                    )
                )
            ).scalars().all()
            self.assertEqual(len(assignments), 1)
            stored = json.loads(assignments[0].payload_json)
            self.assertEqual(
                stored["bucket"],
                CourseSalesExperimentService.assignment_bucket(control_id),
            )

    async def test_treatment_mode_assigns_treatment_server_side(self):
        async with self.sessions() as session:
            await self._enable(session, mode="treatment", percent=0)
            user = _user(3001, created_at=self.started_at + timedelta(seconds=1))
            session.add(user)
            await session.flush()

            offer = await CourseSalesExperimentService(session).resolve_offer(
                user=user,
                level="hsk1",
                access_policy=_access(),
                now=self.started_at + timedelta(minutes=1),
            )

            self.assertEqual(offer["arm"], "treatment")

    async def test_paid_pending_old_campaign_paywall_and_open_access_are_excluded(self):
        async with self.sessions() as session:
            await self._enable(session, mode="ab", percent=100)
            fresh = self.started_at + timedelta(seconds=1)
            paid = _user(
                4001,
                created_at=fresh,
                status="active",
                payment_status="approved",
                end_date=self.started_at + timedelta(days=30),
            )
            pending = _user(4002, created_at=fresh)
            prior_paywall = _user(4003, created_at=fresh)
            discounted = _user(4004, created_at=fresh, discount_eligible=True)
            campaign_entry = _user(4005, created_at=fresh)
            wrong_level = _user(4006, created_at=fresh, level="hsk2")
            ads_user = _user(4007, created_at=fresh)
            free_until_user = _user(4008, created_at=fresh)
            old_user = _user(4009, created_at=self.started_at - timedelta(seconds=1))
            special_checkout = _user(4010, created_at=fresh)
            active_campaign_user = _user(4011, created_at=fresh)
            session.add_all(
                [
                    paid,
                    pending,
                    prior_paywall,
                    discounted,
                    campaign_entry,
                    wrong_level,
                    ads_user,
                    free_until_user,
                    old_user,
                    special_checkout,
                    active_campaign_user,
                ]
            )
            session.add(
                DiscountCampaign(
                    title="HSK1 campaign",
                    percent=20,
                    is_active=True,
                    starts_at=self.started_at - timedelta(minutes=1),
                    ends_at=self.started_at + timedelta(days=1),
                    audience_level="hsk1",
                    payment_method="visa",
                    plan_type="1_month",
                )
            )
            session.add(
                Payment(
                    user_telegram_id=pending.telegram_id,
                    plan_type="1_month",
                    amount=10,
                    currency="somoni",
                    payment_status="pending",
                )
            )
            session.add(
                Payment(
                    user_telegram_id=special_checkout.telegram_id,
                    plan_type="1_month",
                    amount=8,
                    currency="somoni",
                    payment_status="draft",
                    discount_source="admin_campaign",
                    discount_campaign_id=77,
                )
            )
            session.add(
                CourseMiniAppEvent(
                    telegram_id=prior_paywall.telegram_id,
                    event_name="paywall_seen",
                    source="course_v3",
                    created_at=self.started_at - timedelta(minutes=1),
                )
            )
            await session.flush()
            service = CourseSalesExperimentService(session)

            cases = (
                (paid, "hsk1", _access(), None),
                (pending, "hsk1", _access(), None),
                (prior_paywall, "hsk1", _access(), None),
                (discounted, "hsk1", _access(), None),
                (campaign_entry, "hsk1", _access(), "release_feedback_campaign"),
                (wrong_level, "hsk2", _access(), None),
                (ads_user, "hsk1", _access("ads"), None),
                (free_until_user, "hsk1", _access("free_until"), None),
                (old_user, "hsk1", _access(), None),
                (special_checkout, "hsk1", _access(), None),
                (active_campaign_user, "hsk1", _access(), None),
            )
            for user, level, access_policy, source in cases:
                with self.subTest(telegram_id=user.telegram_id):
                    offer = await service.resolve_offer(
                        user=user,
                        level=level,
                        access_policy=access_policy,
                        entry_source=source,
                        now=self.started_at + timedelta(minutes=1),
                    )
                    self.assertIsNone(offer)

            count = await session.scalar(
                select(func.count(CourseMiniAppEvent.id)).where(
                    CourseMiniAppEvent.event_name == SALES_OFFER_ASSIGNED_EVENT
                )
            )
            self.assertEqual(count, 0)

    async def test_client_spoofed_arm_is_replaced_by_persisted_assignment(self):
        async with self.sessions() as session:
            await self._enable(session, mode="ab", percent=100)
            user = _user(5001, created_at=self.started_at + timedelta(seconds=1))
            session.add(user)
            await session.flush()
            service = CourseSalesExperimentService(session)
            await service.resolve_offer(
                user=user,
                level="hsk1",
                access_policy=_access(),
                now=self.started_at + timedelta(minutes=1),
            )

            context = await service.trusted_event_context(
                user=user,
                event_name="sales_bridge_cta",
                payload={
                    "experiment_id": "evil",
                    "arm": "control",
                    "bucket": 99,
                    "source": "evil",
                    "level": "hsk4",
                    "dedupe_key": "evil",
                    "language": "ru",
                    "action": "unlock_path",
                },
            )

            self.assertTrue(context["ok"])
            self.assertEqual(context["source"], SALES_EXPERIMENT_ID)
            self.assertEqual(context["level"], "hsk1")
            self.assertEqual(context["lesson_order"], 3)
            self.assertEqual(context["payload"]["experiment_id"], SALES_EXPERIMENT_ID)
            self.assertEqual(context["payload"]["arm"], "treatment")
            self.assertEqual(
                context["payload"]["bucket"],
                CourseSalesExperimentService.assignment_bucket(user.telegram_id),
            )
            self.assertEqual(context["payload"]["language"], "uz")
            self.assertEqual(context["payload"]["action"], "unlock_path")
            self.assertNotIn("source", context["payload"])

    async def test_client_context_requires_treatment_assignment_and_valid_action(self):
        control_id = next(
            telegram_id
            for telegram_id in range(6000, 7000)
            if CourseSalesExperimentService.assignment_bucket(telegram_id) >= 50
        )
        async with self.sessions() as session:
            await self._enable(session, mode="ab", percent=50)
            control = _user(
                control_id,
                created_at=self.started_at + timedelta(seconds=1),
            )
            unassigned = _user(
                control_id + 10000,
                created_at=self.started_at + timedelta(seconds=1),
            )
            session.add_all((control, unassigned))
            await session.flush()
            service = CourseSalesExperimentService(session)
            await service.resolve_offer(
                user=control,
                level="hsk1",
                access_policy=_access(),
                now=self.started_at + timedelta(minutes=1),
            )

            no_assignment = await service.trusted_event_context(
                user=unassigned,
                event_name="sales_offer_seen",
            )
            control_result = await service.trusted_event_context(
                user=control,
                event_name="sales_offer_seen",
            )

            self.assertEqual(
                no_assignment["error"],
                "sales_offer_assignment_required",
            )
            self.assertEqual(
                control_result["error"],
                "sales_offer_treatment_required",
            )

            treatment = _user(
                control_id + 20000,
                created_at=self.started_at + timedelta(seconds=1),
            )
            session.add(treatment)
            await session.flush()
            await service.save_settings(
                {"mode": "ab", "treatment_percent": 100},
                now=self.started_at + timedelta(minutes=2),
            )
            await service.resolve_offer(
                user=treatment,
                level="hsk1",
                access_policy=_access(),
                now=self.started_at + timedelta(minutes=3),
            )
            invalid_action = await service.trusted_event_context(
                user=treatment,
                event_name="sales_bridge_cta",
                payload={"action": "invented_action"},
            )
            self.assertEqual(invalid_action["error"], "sales_offer_action_invalid")

    def test_event_allowlist_keeps_assignment_server_only(self):
        self.assertIn(SALES_OFFER_ASSIGNED_EVENT, COURSE_MINIAPP_EVENT_NAMES)
        self.assertNotIn(
            SALES_OFFER_ASSIGNED_EVENT,
            CLIENT_COURSE_MINIAPP_EVENT_NAMES,
        )
        for event_name in SALES_EXPERIMENT_CLIENT_EVENTS:
            self.assertIn(event_name, COURSE_MINIAPP_EVENT_NAMES)
            self.assertIn(event_name, CLIENT_COURSE_MINIAPP_EVENT_NAMES)


if __name__ == "__main__":
    unittest.main()
