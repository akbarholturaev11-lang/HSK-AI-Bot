"""Bepul limit darvozalari — HTTP darajasida.

Bu ikki endpoint bepul foydalanuvchining har bir mashq sessiyasidan oldin
o'tadigan yagona joyi, ya'ni monetizatsiyaning eng issiq yo'li. Ular
`app/main.py` ichida turganda birorta test ularga yetib bormagan edi, chunki
hech qaysi test `app.main` ni import qilmaydi.

Bu yerda tekshiriladigan narsalar:

* imzosiz initData bilan hech narsa ochilmaydi;
* bepul urinish UMRBOD (ertaga qayta ochilmaydi);
* AI bo'limida reklama ham kuniga cheklangan, boshqasida cheksiz;
* admin "vaqtincha free" rejimi umrbod urinishni SARFLAMAYDI;
* rad javobi endi `reset_at` olib yuradi — ilgari uni faqat Android olardi.
"""

import hashlib
import hmac
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlencode

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.miniapp_entitlements import create_miniapp_entitlements_router
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.entitlement_shadow_event import EntitlementShadowEvent
from app.db.models.user import User
from app.services.course_access_policy_service import (
    COURSE_ACCESS_MODE_FREE_UNTIL,
    CourseAccessPolicyService,
)


BOT_TOKEN = "12345:gate-test-token"


def _init_data(telegram_id: int) -> str:
    """Telegram imzolaydigan initData ning haqiqiy shakli."""
    params = {
        "auth_date": str(int(datetime.now(timezone.utc).timestamp())),
        "user": f'{{"id":{telegram_id},"first_name":"Gate"}}',
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


def _user(telegram_id=7100, **overrides) -> User:
    now = datetime.now(timezone.utc)
    fields = dict(
        id=1,
        telegram_id=telegram_id,
        full_name="Gate tester",
        language="uz",
        level="hsk1",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        created_at=now,
        last_active_at=now,
    )
    fields.update(overrides)
    return User(**fields)


class GateApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

        async with self.sessions() as session:
            session.add(_user())
            await session.commit()

        # Shadow servis ataylab o'z sessiyasida yozadi.
        from unittest.mock import patch

        self.shadow_patch = patch(
            "app.services.entitlements.shadow.async_session_maker", self.sessions
        )
        self.shadow_patch.start()

        self.app = FastAPI()
        self.app.include_router(
            create_miniapp_entitlements_router(
                session_factory=self.sessions,
                settings_obj=SimpleNamespace(BOT_TOKEN=BOT_TOKEN),
                bot=None,
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="https://gate.test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        self.shadow_patch.stop()
        await self.db.dispose()

    async def _post(self, path, *, feature, telegram_id=7100, signed=True, ref=None):
        body = {"feature": feature}
        if ref:
            body["ref"] = ref
        headers = {}
        if signed:
            headers["X-Telegram-Init-Data"] = _init_data(telegram_id)
        return await self.client.post(path, json=body, headers=headers)

    # --- autentifikatsiya -------------------------------------------------

    async def test_an_unsigned_request_opens_nothing(self):
        response = await self._post(
            "/api/v3/practice/daily-gate", feature="recognition", signed=False
        )

        self.assertEqual(401, response.status_code)
        self.assertEqual("invalid_telegram_init_data", response.json()["error"])

    async def test_a_forged_signature_opens_nothing(self):
        response = await self.client.post(
            "/api/v3/practice/daily-gate",
            json={"feature": "recognition"},
            headers={"X-Telegram-Init-Data": "user=%7B%22id%22%3A1%7D&hash=deadbeef"},
        )

        self.assertEqual(401, response.status_code)

    async def test_an_unknown_feature_is_refused(self):
        response = await self._post(
            "/api/v3/practice/daily-gate", feature="wat"
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual("invalid_feature", response.json()["error"])

    async def test_a_user_who_never_started_the_bot_is_refused(self):
        response = await self._post(
            "/api/v3/practice/daily-gate", feature="recognition", telegram_id=9999
        )

        self.assertEqual(403, response.status_code)
        self.assertEqual("access_start_first", response.json()["error"])

    # --- bepul urinish ----------------------------------------------------

    async def test_the_free_try_is_once_per_lifetime_not_per_day(self):
        first = await self._post("/api/v3/practice/daily-gate", feature="recognition")
        second = await self._post("/api/v3/practice/daily-gate", feature="recognition")

        self.assertEqual(200, first.status_code)
        self.assertTrue(first.json()["allowed"])
        self.assertEqual(403, second.status_code)
        self.assertEqual("free_feature_limit_reached", second.json()["error"])

    async def test_the_same_ref_does_not_spend_a_second_try(self):
        # Sahifa qayta yuklanishi yoki tarmoq retry.
        first = await self._post(
            "/api/v3/practice/daily-gate", feature="memorize", ref="abc"
        )
        again = await self._post(
            "/api/v3/practice/daily-gate", feature="memorize", ref="abc"
        )

        self.assertEqual(200, first.status_code)
        self.assertEqual(200, again.status_code)

    async def test_each_section_has_its_own_free_try(self):
        await self._post("/api/v3/practice/daily-gate", feature="recognition")
        other = await self._post("/api/v3/practice/daily-gate", feature="memorize")

        self.assertEqual(200, other.status_code)

    async def test_a_refusal_now_tells_the_client_when_it_reopens(self):
        # Android bu maydonni ilgari ham olardi, Mini App esa yo'q. Endi
        # ikkala klient bir xil javob ko'radi.
        await self._post("/api/v3/practice/daily-gate", feature="recognition")
        refused = await self._post(
            "/api/v3/practice/daily-gate", feature="recognition"
        )

        self.assertIn("reset_at", refused.json())

    # --- reklama darvozasi ------------------------------------------------
    #
    # Reklama ko'rib bo'limni ochish OLIB TASHLANDI. Yo'lning o'zi saqlanadi,
    # chunki keshdagi va do'kondagi eski klientlar hali unga murojaat qiladi.

    async def test_the_ad_gate_no_longer_opens_anything(self):
        for _ in range(3):
            response = await self._post(
                "/api/v3/practice/ad-gate", feature="recognition"
            )
            self.assertEqual(403, response.status_code)
            body = response.json()
            self.assertEqual("free_feature_limit_reached", body["error"])
            self.assertFalse(body["ad"]["available"])

    async def test_the_ad_gate_answers_403_not_404_for_an_old_client(self):
        """Eski klient 404 ni "server buzildi" deb ko'rsatardi.

        403 esa u allaqachon biladigan holat — limit tugagan — va u to'g'ri
        ekran chiqaradi.
        """
        response = await self._post("/api/v3/practice/ad-gate", feature="pronunciation")

        self.assertEqual(403, response.status_code)

    async def test_a_paid_learner_is_not_refused_by_a_route_that_grants_nothing(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.status = "active"
            user.payment_status = "approved"
            user.end_date = datetime.now(timezone.utc) + timedelta(days=30)
            await session.commit()

        response = await self._post("/api/v3/practice/ad-gate", feature="recognition")

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["allowed"])

    async def test_the_daily_gate_never_claims_an_ad_is_available(self):
        """Aynan shu bayroq tufayli klientlar "Reklama bilan davom etish"
        tugmasini ko'rsatishda davom etardi."""
        await self._post("/api/v3/practice/daily-gate", feature="recognition")
        refused = await self._post("/api/v3/practice/daily-gate", feature="recognition")

        self.assertEqual(403, refused.status_code)
        self.assertFalse(refused.json()["ad"]["available"])

    # --- admin "vaqtincha free" rejimi ------------------------------------

    async def test_the_free_mode_opens_the_section_without_spending_the_try(self):
        async with self.sessions() as session:
            await CourseAccessPolicyService(session).save_policy(
                mode=COURSE_ACCESS_MODE_FREE_UNTIL, duration_days=3
            )
            await session.commit()

        opened = await self._post(
            "/api/v3/practice/daily-gate", feature="recognition"
        )
        self.assertEqual(200, opened.status_code)
        self.assertTrue(opened.json()["policy_free"])

        # Rejim tugagach o'quvchi o'z bepul urinishini YO'QOTMAGAN bo'lishi kerak.
        async with self.sessions() as session:
            await CourseAccessPolicyService(session).save_policy(mode="subscription")
            await session.commit()

        after = await self._post("/api/v3/practice/daily-gate", feature="recognition")
        self.assertEqual(200, after.status_code)

    # --- obunachi ---------------------------------------------------------

    async def test_a_paid_user_is_never_gated(self):
        async with self.sessions() as session:
            user = (
                await session.execute(select(User).where(User.telegram_id == 7100))
            ).scalar_one()
            user.status = "active"
            user.payment_status = "approved"
            user.end_date = datetime.now(timezone.utc) + timedelta(days=30)
            await session.commit()

        for _ in range(4):
            response = await self._post(
                "/api/v3/practice/daily-gate", feature="recognition"
            )
            self.assertEqual(200, response.status_code)
            self.assertTrue(response.json()["is_paid"])

    # --- shadow ------------------------------------------------------------

    async def test_every_gated_request_is_compared_against_the_engine(self):
        await self._post("/api/v3/practice/daily-gate", feature="recognition")

        async with self.sessions() as session:
            rows = list(
                (await session.execute(select(EntitlementShadowEvent))).scalars().all()
            )

        self.assertEqual(1, len(rows))
        self.assertEqual("practice.recognition", rows[0].action)
        self.assertEqual("miniapp", rows[0].client)

    async def test_the_shadow_write_never_changes_the_answer(self):
        # Solishtiruv butunlay yiqilsa ham darvoza o'z ishini qilishi kerak.
        from unittest.mock import patch

        with patch(
            "app.services.entitlements.gate_shadow.EntitlementEngine",
            side_effect=RuntimeError("dvigatel yiqildi"),
        ):
            response = await self._post(
                "/api/v3/practice/daily-gate", feature="recognition"
            )

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["allowed"])


if __name__ == "__main__":
    unittest.main()
