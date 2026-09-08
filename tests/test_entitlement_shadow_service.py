"""Shadow solishtiruvi — ko'chirishning o'lchov asbobi.

Uchta narsa tekshiriladi va uchalasi ham ko'chirish xavfsizligi uchun:

* Solishtiruv HECH QACHON oqimni buzmaydi. Baza yiqilsa ham, ma'lumot g'alati
  bo'lsa ham, chaqiruvchi javob oladi.
* Unique kalit jadval hajmini cheklaydi: bir kunda bir foydalanuvchi × harakat
  × klient uchun ko'pi bilan bitta "mos" va bitta "nomuvofiq" qatori.
* Yoqish sozlamasi default `shadow` bo'lib qoladi: sozlama yo'q, buzilgan
  yoki noma'lum bo'lsa xatti-harakat o'zgarmaydi.
"""

import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.entitlement_shadow_event import EntitlementShadowEvent
from app.services.entitlements import actions as A
from app.services.entitlements import decision as D
from app.services.entitlements.shadow import (
    MODE_ENGINE,
    MODE_SHADOW,
    ROLLOUT_MIN_SAMPLES,
    SHADOW_ROLLOUT_KEY,
    EntitlementShadowService,
    LegacyOutcome,
)
from app.services.entitlements.state import EntitlementState


def _engine_decision(allowed: bool, *, used=1, limit=2):
    return D.LimitDecision(
        allowed=allowed,
        action=A.PRACTICE_RECOGNITION,
        state=EntitlementState.FREE,
        limit=limit,
        used=used,
        remaining=max(0, limit - used),
        window="daily",
        reason="" if allowed else D.REASON_LIMIT_REACHED,
    )


class ShadowComparisonTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)
        # Servis ataylab O'Z sessiyasida yozadi — uni shu bazaga bog'laymiz.
        self.patch = patch(
            "app.services.entitlements.shadow.async_session_maker", self.sessions
        )
        self.patch.start()
        self.user = SimpleNamespace(id=1, telegram_id=5150)

    async def asyncTearDown(self):
        self.patch.stop()
        await self.db.dispose()

    async def _rows(self):
        async with self.sessions() as session:
            result = await session.execute(select(EntitlementShadowEvent))
            return list(result.scalars().all())

    async def _service(self, session=None):
        return EntitlementShadowService(session)

    async def test_matching_decisions_are_recorded_as_agreement(self):
        service = await self._service()

        agree = await service.compare(
            user=self.user,
            action=A.PRACTICE_RECOGNITION,
            client="miniapp",
            legacy={"allowed": True, "limit": 2, "used": 1, "remaining": 1},
            engine=_engine_decision(True),
        )

        self.assertTrue(agree)
        rows = await self._rows()
        self.assertEqual(1, len(rows))
        self.assertTrue(rows[0].agree)
        self.assertEqual(EntitlementState.FREE, rows[0].state)

    async def test_a_differing_verdict_is_recorded_as_a_mismatch(self):
        service = await self._service()

        agree = await service.compare(
            user=self.user,
            action=A.PRACTICE_RECOGNITION,
            client="desktop",
            legacy={"allowed": False, "limit": 1, "used": 1, "remaining": 0},
            engine=_engine_decision(True),
        )

        self.assertFalse(agree)
        rows = await self._rows()
        self.assertFalse(rows[0].agree)
        detail = json.loads(rows[0].detail_json)
        self.assertIn("mismatch", detail)
        self.assertFalse(detail["mismatch"]["legacy_allowed"])
        self.assertTrue(detail["mismatch"]["engine_allowed"])

    async def test_only_the_verdict_counts_not_the_bookkeeping_numbers(self):
        # Eski yo'l `remaining` ni boshqacha hisoblashi mumkin; bu
        # foydalanuvchi uchun hech narsani o'zgartirmaydi va farq emas.
        service = await self._service()

        agree = await service.compare(
            user=self.user,
            action=A.PRACTICE_RECOGNITION,
            client="miniapp",
            legacy={"allowed": True, "limit": 99, "used": 42, "remaining": 57},
            engine=_engine_decision(True),
        )

        self.assertTrue(agree)

    async def test_the_daily_key_keeps_the_table_small(self):
        # Bir kunda bir foydalanuvchi 20 marta chaqirsa ham ikki qatordan
        # ortiq yozilmaydi: bitta "mos", bitta "nomuvofiq".
        service = await self._service()

        for index in range(20):
            await service.compare(
                user=self.user,
                action=A.PRACTICE_RECOGNITION,
                client="miniapp",
                legacy={"allowed": index % 2 == 0},
                engine=_engine_decision(True),
            )

        rows = await self._rows()
        self.assertEqual(2, len(rows))
        self.assertEqual({True, False}, {row.agree for row in rows})

    async def test_different_actions_and_clients_are_tracked_apart(self):
        service = await self._service()

        for action in (A.PRACTICE_RECOGNITION, A.LESSON_START):
            for client in ("miniapp", "android"):
                await service.compare(
                    user=self.user,
                    action=action,
                    client=client,
                    legacy={"allowed": True},
                    engine=_engine_decision(True),
                )

        self.assertEqual(4, len(await self._rows()))

    async def test_a_user_without_a_telegram_id_is_skipped_quietly(self):
        service = await self._service()

        agree = await service.compare(
            user=SimpleNamespace(id=9, telegram_id=None),
            action=A.PRACTICE_RECOGNITION,
            client="miniapp",
            legacy={"allowed": True},
            engine=_engine_decision(True),
        )

        self.assertTrue(agree)
        self.assertEqual([], await self._rows())

    async def test_a_write_failure_never_reaches_the_caller(self):
        # Bu chaqiruv jonli so'rov ichida turadi. Baza yiqilsa ham
        # foydalanuvchi javobini buzmasligi kerak.
        service = await self._service()

        def _boom(*_args, **_kwargs):
            raise RuntimeError("baza yo'q")

        with patch("app.services.entitlements.shadow.async_session_maker", _boom):
            agree = await service.compare(
                user=self.user,
                action=A.PRACTICE_RECOGNITION,
                client="miniapp",
                legacy={"allowed": True},
                engine=_engine_decision(True),
            )

        self.assertTrue(agree)

    async def test_broken_engine_input_never_reaches_the_caller(self):
        service = await self._service()

        agree = await service.compare(
            user=self.user,
            action=A.PRACTICE_RECOGNITION,
            client="miniapp",
            legacy={"allowed": True},
            engine=object(),  # `allowed` yo'q
        )

        self.assertTrue(agree)


class RolloutSettingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.db.dispose()

    async def test_without_a_setting_everything_stays_in_shadow(self):
        async with self.sessions() as session:
            mode = await EntitlementShadowService(session).mode_for(
                A.PRACTICE_RECOGNITION
            )
        self.assertEqual(MODE_SHADOW, mode)

    async def test_a_corrupt_setting_stays_in_shadow(self):
        async with self.sessions() as session:
            from app.repositories.bot_setting_repo import BotSettingRepository

            await BotSettingRepository(session).set(SHADOW_ROLLOUT_KEY, "{broken")
            await session.commit()
            mode = await EntitlementShadowService(session).mode_for(
                A.PRACTICE_RECOGNITION
            )
        self.assertEqual(MODE_SHADOW, mode)

    async def test_one_action_can_be_enabled_without_touching_the_rest(self):
        async with self.sessions() as session:
            service = EntitlementShadowService(session)
            await service.save_rollout(
                {"default": MODE_SHADOW, "actions": {A.PRACTICE_RECOGNITION: MODE_ENGINE}},
                updated_by_telegram_id=777,
            )
            await session.commit()

            self.assertEqual(
                MODE_ENGINE, await service.mode_for(A.PRACTICE_RECOGNITION)
            )
            self.assertEqual(MODE_SHADOW, await service.mode_for(A.LESSON_START))

    async def test_a_client_can_be_held_back_even_for_an_enabled_action(self):
        # Android build i eskirgan bo'lsa, uni alohida ushlab turish kerak.
        async with self.sessions() as session:
            service = EntitlementShadowService(session)
            await service.save_rollout(
                {
                    "default": MODE_ENGINE,
                    "clients": {"android": MODE_SHADOW},
                }
            )
            await session.commit()

            self.assertEqual(
                MODE_ENGINE, await service.mode_for(A.LESSON_START, client="miniapp")
            )
            self.assertEqual(
                MODE_SHADOW, await service.mode_for(A.LESSON_START, client="android")
            )

    async def test_an_invalid_rollout_is_refused(self):
        async with self.sessions() as session:
            service = EntitlementShadowService(session)
            for payload in (
                "nope",
                {"default": "wat"},
                {"default": MODE_SHADOW, "actions": {"nope.nope": MODE_ENGINE}},
                {"default": MODE_SHADOW, "actions": {A.LESSON_START: "wat"}},
                {"default": MODE_SHADOW, "clients": {"android": "wat"}},
            ):
                with self.subTest(payload=payload):
                    with self.assertRaises(ValueError):
                        await service.save_rollout(payload)


class DisagreementReportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.db.dispose()

    async def _seed(self, *, action, client, agree, count, days_ago=0):
        created = datetime.now(timezone.utc) - timedelta(days=days_ago)
        async with self.sessions() as session:
            for index in range(count):
                session.add(
                    EntitlementShadowEvent(
                        telegram_id=1000 + index,
                        action=action,
                        client=client,
                        agree=agree,
                        engine_allowed=True,
                        legacy_allowed=agree,
                        day_key=f"d{days_ago}",
                        created_at=created,
                    )
                )
            await session.commit()

    async def test_a_clean_and_busy_action_is_reported_ready(self):
        await self._seed(
            action=A.PRACTICE_RECOGNITION,
            client="miniapp",
            agree=True,
            count=ROLLOUT_MIN_SAMPLES,
        )

        async with self.sessions() as session:
            report = await EntitlementShadowService(session).disagreement_report()

        self.assertEqual(1, len(report))
        self.assertEqual(0, report[0]["disagreements"])
        self.assertTrue(report[0]["ready_to_enable"])

    async def test_zero_disagreements_is_not_enough_on_its_own(self):
        # "Hech kim ishlatmagan" ni "hammasi to'g'ri" deb o'qib bo'lmaydi.
        await self._seed(
            action=A.LESSON_START, client="desktop", agree=True, count=3
        )

        async with self.sessions() as session:
            report = await EntitlementShadowService(session).disagreement_report()

        self.assertEqual(3, report[0]["samples"])
        self.assertFalse(report[0]["ready_to_enable"])

    async def test_any_disagreement_blocks_the_action(self):
        await self._seed(
            action=A.PRACTICE_MEMORIZE,
            client="android",
            agree=True,
            count=ROLLOUT_MIN_SAMPLES,
        )
        await self._seed(
            action=A.PRACTICE_MEMORIZE, client="android", agree=False, count=1
        )

        async with self.sessions() as session:
            report = await EntitlementShadowService(session).disagreement_report()

        entry = report[0]
        self.assertEqual(1, entry["disagreements"])
        self.assertFalse(entry["ready_to_enable"])
        self.assertIsNotNone(entry["last_disagreement_at"])

    async def test_old_rows_fall_out_of_the_window(self):
        await self._seed(
            action=A.PRACTICE_RECOGNITION,
            client="miniapp",
            agree=False,
            count=5,
            days_ago=30,
        )

        async with self.sessions() as session:
            report = await EntitlementShadowService(session).disagreement_report(days=7)

        self.assertEqual([], report)

    async def test_examples_show_what_actually_differed(self):
        await self._seed(
            action=A.PRACTICE_MEMORIZE, client="android", agree=False, count=5
        )

        async with self.sessions() as session:
            examples = await EntitlementShadowService(session).examples(
                action=A.PRACTICE_MEMORIZE, client="android", limit=3
            )

        self.assertEqual(3, len(examples))
        self.assertIn("legacy_allowed", examples[0])
        self.assertIn("engine_allowed", examples[0])


if __name__ == "__main__":
    unittest.main()
