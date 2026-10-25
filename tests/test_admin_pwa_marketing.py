"""Signed marketing commands against real isolated SQL; no live messaging."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import httpx
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_api import pwa_marketing as marketing
from app.admin_api.pwa_step_up import begin_step_up, operation_digest, verify_step_up
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.ad_campaign import AdCampaign, AdCampaignDelivery
from app.db.models.bot_setting import BotSetting
from app.db.models.course_ad import CourseAdCreative, CourseAdView
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.course_ad_service import CourseAdService
from app.services.course_sales_experiment_service import CourseSalesExperimentService
from app.services.desktop_app_promo_settings_service import (
    DESKTOP_APP_PROMO_SETTINGS_KEY, get_desktop_app_promo_settings,
    save_desktop_app_promo_settings,
)
from app.services.broadcast_translation_service import decode_localized_broadcast_text
from app.repositories.ad_campaign_repo import AdCampaignRepository
from tests import test_admin_pwa_payment_review as fixtures
from tests.test_admin_pwa_webauthn_crypto_vectors import CRED_ID, make_assertion

ORIGIN = "https://hskai.app"
PROMO_CHANGE = {"kind": "desktop_promo", "enabled": False, "daily_limit": 2,
                "require_learning_progress": True,
                "placements": {"home_prompt": True, "lesson_end_promo": False, "ad_promo": True},
                "platforms": {"macos": True, "windows": True, "android": False, "ios": False}}
CAMPAIGN_CHANGE = {"kind": "campaign_draft", "title": "Spring course",
    "texts": {"uz": "<b>Salom</b> & xitoy tili", "ru": "Привет и китайский",
              "tj": "Салом ва забони чинӣ"},
    "languages": ["uz", "ru"], "track": "hsk30", "level": None,
    "duration_hours": 72, "include_active_subscribers": False}


class AdminPwaMarketingTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def prepare_marketing(self, change):
        async with self.sessions() as db:
            result = await marketing.prepare_marketing(db, session_cookie=fixtures.COOKIE,
                request=marketing.PrepareMarketing.model_validate({"change": change}), settings_obj=self.settings)
        return marketing.MarketingCommand.model_validate(
            result.get("execute_payload") or result["operation"]["payload"])

    async def proof_marketing(self, command, *, signed=False, **overrides):
        if signed:
            async with self.sessions() as db:
                start = await begin_step_up(db, session_cookie=fixtures.COOKIE,
                    settings_obj=self.settings, **command.operation())
            self.assertIsNotNone(start)
            async with self.sessions() as db:
                challenge = bytes((await db.get(AdminPwaStepUp, start.step_up_id)).challenge)
            async with self.sessions() as db:
                self.assertTrue(await verify_step_up(db, session_cookie=fixtures.COOKIE,
                    step_up_id=start.step_up_id, settings_obj=self.settings,
                    credential=make_assertion(self.key, challenge=challenge)))
            return start.step_up_id
        now, proof = datetime.now(timezone.utc), str(uuid4())
        values = dict(id=proof, session_id=self.session_id, user_id=101,
            action="marketing.update", target=command.operation()["target"],
            payload_hash=operation_digest(**command.operation()), challenge=b"M" * 32,
            status="verified", credential_id=CRED_ID, verified_at=now,
            created_at=now, expires_at=now + timedelta(seconds=50))
        values.update(overrides)
        async with self.sessions() as db:
            db.add(AdminPwaStepUp(**values))
            await db.commit()
        return proof

    async def execute_marketing(self, command, proof):
        async with self.sessions() as db:
            return await marketing.execute_marketing(db, session_cookie=fixtures.COOKIE,
                request=marketing.ExecuteMarketing(**command.model_dump(), step_up_id=proof),
                settings_obj=self.settings)

    async def seed_ads(self, count=1, *, shared_path=False):
        async with self.sessions() as db:
            db.add_all([CourseAdCreative(id=index, title=f"Creative {index}",
                media_path="retained-private-media.mp4" if shared_path else f"private-media-{index}.mp4",
                media_type="video", media_blob=b"private-media-bytes-canary", media_size=26,
                media_checksum="a" * 64, language="all", ad_type="odiy", is_active=True)
                for index in range(1, count + 1)])
            await db.commit()

    async def test_read_is_bounded_and_never_reads_or_exposes_media(self):
        await self.seed_ads(35)
        async with self.sessions() as db:
            await save_desktop_app_promo_settings(db, {"media_type": "photo", "media_path": "private-promo-canary.jpg"})
            await db.commit()
        statements = []

        def record_sql(connection, cursor, statement, *args):
            if statement.lstrip().lower().startswith("select"):
                statements.append(statement)

        event.listen(self.engine.sync_engine, "before_cursor_execute", record_sql)
        try:
            with patch.object(CourseAdService, "list_for_admin", side_effect=AssertionError("unbounded list forbidden")):
                async with self.sessions() as db:
                    first = await marketing.read_marketing(db, session_cookie=fixtures.COOKIE,
                        request=marketing.MarketingReadRequest(), settings_obj=self.settings)
                async with self.sessions() as db:
                    second = await marketing.read_marketing(db, session_cookie=fixtures.COOKIE,
                        request=marketing.MarketingReadRequest(before_id=first["course_ads"]["next_before_id"]),
                        settings_obj=self.settings)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", record_sql)
        self.assertEqual(len(first["course_ads"]["items"]), 30)
        self.assertEqual(len(second["course_ads"]["items"]), 5)
        self.assertIsNone(second["course_ads"]["next_before_id"])
        self.assertEqual({row["id"] for row in first["course_ads"]["items"]}.intersection(
            row["id"] for row in second["course_ads"]["items"]), set())
        self.assertEqual(first["sales_experiment"]["mode"], "off")
        self.assertTrue(first["desktop_promo"]["has_media"])
        output = json.dumps(first)
        for forbidden in ("private-promo-canary", "private-media", "media_blob", "media_path", "media_url", "updated_by_telegram_id"):
            self.assertNotIn(forbidden, output)
        self.assertFalse(any("course_ad_creatives.media_blob" in statement for statement in statements))
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BotSetting)), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_genuine_sales_proof_updates_shared_policy_without_resetting_start(self):
        command = await self.prepare_marketing({"kind": "sales_experiment", "mode": "ab", "treatment_percent": 50})
        proof = await self.proof_marketing(command, signed=True)
        result = await self.execute_marketing(command, proof)
        self.assertEqual(result["result"]["mode"], "ab")
        started_at = result["result"]["started_at"]
        self.assertIsNotNone(started_at)
        changed = await self.prepare_marketing({"kind": "sales_experiment", "mode": "treatment", "treatment_percent": 90})
        result = await self.execute_marketing(changed, await self.proof_marketing(changed))
        self.assertEqual(result["result"]["effective_treatment_percent"], 100)
        self.assertEqual(result["result"]["started_at"], started_at)
        async with self.sessions() as db:
            actual = await CourseSalesExperimentService(db).get_settings()
            self.assertEqual((actual.mode, actual.treatment_percent), ("treatment", 90))
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "consumed")
            audit = await db.get(AdminPwaCommandAudit, result["command_id"])
            self.assertEqual((audit.action, audit.target), ("marketing.update", "sales_experiment"))
            self.assertEqual(audit.payload_hash, operation_digest(**changed.operation()))
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "pending")
            self.assertIsNone((await db.get(User, 1)).end_date)
        with self.assertRaisesRegex(marketing.CommandError, "step_up_denied"):
            await self.execute_marketing(command, proof)

    async def test_desktop_configuration_preserves_existing_media_and_platform_semantics(self):
        async with self.sessions() as db:
            await save_desktop_app_promo_settings(db, {"media_type": "photo", "media_path": "private-promo-canary.jpg"})
            await db.commit()
        command = await self.prepare_marketing(PROMO_CHANGE)
        result = await self.execute_marketing(command, await self.proof_marketing(command))
        self.assertEqual(result["result"]["daily_limit"], 2)
        self.assertFalse(result["result"]["enabled"])
        self.assertEqual(result["result"]["platforms"], PROMO_CHANGE["platforms"])
        self.assertTrue(result["result"]["has_media"])
        async with self.sessions() as db:
            actual = await get_desktop_app_promo_settings(db)
            self.assertEqual(actual.media_path, "private-promo-canary.jpg")
            self.assertEqual(actual.media_type, "photo")
            self.assertTrue(actual.require_learning_progress)
            self.assertNotIn("private-promo-canary", (await db.get(AdminPwaCommandAudit, result["command_id"])).result_json)

    async def test_campaign_creation_is_localized_signed_paused_and_content_free_in_audit(self):
        command = await self.prepare_marketing(CAMPAIGN_CHANGE)
        operation = command.operation()
        self.assertEqual(operation["action"], "marketing.update")
        self.assertEqual(operation["target"], "campaign_draft")
        self.assertEqual(operation["payload"]["content_hash"], marketing._hash(CAMPAIGN_CHANGE["texts"]))
        self.assertNotIn("texts", operation["payload"]["change"])
        self.assertNotIn("Salom", json.dumps(operation, ensure_ascii=False))
        proof = await self.proof_marketing(command, signed=True)
        result = await self.execute_marketing(command, proof)
        self.assertEqual(result["result"]["status"], "paused_draft")
        self.assertFalse(result["result"]["is_active"])

        async with self.sessions() as db:
            campaign = await db.get(AdCampaign, result["result"]["id"])
            self.assertEqual(campaign.title, "Spring course")
            self.assertEqual(campaign.content_type, "text")
            self.assertIsNone(campaign.media_file_id)
            self.assertFalse(campaign.is_active)
            self.assertIsNone(campaign.next_send_at)
            self.assertEqual(campaign.send_count_total, 1)
            self.assertEqual(campaign.target_languages, "ru,uz")
            self.assertEqual(campaign.target_track, "hsk30")
            self.assertEqual(campaign.created_by_telegram_id, self.settings.admin_id_list[0])
            stored = decode_localized_broadcast_text(campaign.message_text)
            self.assertEqual(stored["uz"], "&lt;b&gt;Salom&lt;/b&gt; &amp; xitoy tili")
            self.assertEqual(stored["ru"], "Привет и китайский")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdCampaignDelivery)), 0)
            self.assertEqual(await AdCampaignRepository(db).list_due(), [])
            audit = await db.get(AdminPwaCommandAudit, result["command_id"])
            self.assertEqual(audit.step_up_id, proof)
            self.assertEqual(audit.payload_hash, operation_digest(**operation))
            self.assertEqual(json.loads(audit.result_json), {"kind": "campaign_draft",
                "campaign_id": campaign.id, "content_hash": marketing._hash(CAMPAIGN_CHANGE["texts"])})
            for private_copy in CAMPAIGN_CHANGE["texts"].values():
                self.assertNotIn(private_copy, audit.result_json)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "consumed")

    async def test_campaign_copy_tampering_and_unbounded_inputs_are_rejected(self):
        command = await self.prepare_marketing(CAMPAIGN_CHANGE)
        proof = await self.proof_marketing(command)
        changed = dict(CAMPAIGN_CHANGE, texts={**CAMPAIGN_CHANGE["texts"], "uz": "Changed copy"})
        altered = marketing.MarketingCommand.model_validate({**command.model_dump(), "change": changed})
        with self.assertRaisesRegex(marketing.CommandError, "step_up_denied"):
            await self.execute_marketing(altered, proof)
        with self.assertRaises(ValidationError):
            marketing.CampaignDraftChange.model_validate({**CAMPAIGN_CHANGE, "languages": []})
        with self.assertRaises(ValidationError):
            marketing.CampaignDraftChange.model_validate({**CAMPAIGN_CHANGE, "languages": ["uz", "uz"]})
        with self.assertRaises(ValidationError):
            marketing.CampaignDraftChange.model_validate({**CAMPAIGN_CHANGE,
                "texts": {**CAMPAIGN_CHANGE["texts"], "uz": "&" * 2000}})
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdCampaign)), 0)

    async def test_campaign_insert_rolls_back_with_command_audit(self):
        command = await self.prepare_marketing(CAMPAIGN_CHANGE)
        proof = await self.proof_marketing(command)
        original_flush = AsyncSession.flush

        async def fail_audit(session, *args, **kwargs):
            if any(isinstance(item, AdminPwaCommandAudit) for item in session.new):
                raise RuntimeError("audit storage unavailable")
            return await original_flush(session, *args, **kwargs)

        with patch.object(AsyncSession, "flush", fail_audit):
            with self.assertRaisesRegex(RuntimeError, "audit storage unavailable"):
                await self.execute_marketing(command, proof)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdCampaign)), 0)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")

    async def test_course_ad_toggle_and_delete_preserve_view_facts_with_content_free_audit(self):
        await self.seed_ads()
        async with self.sessions() as db:
            db.add(CourseAdView(ad_id=1, user_id=1, level="hsk1", lesson_order=1,
                                placement="start", completed=True))
            await db.commit()
        toggle = await self.prepare_marketing({"kind": "course_ad", "ad_id": 1,
                                                "operation": "set_active", "is_active": False})
        result = await self.execute_marketing(toggle, await self.proof_marketing(toggle))
        self.assertFalse(result["result"]["is_active"])
        delete = await self.prepare_marketing({"kind": "course_ad", "ad_id": 1,
                                                "operation": "delete", "is_active": None})
        cleanup = Mock()
        with patch.object(marketing, "_cleanup_deleted_media", cleanup):
            result = await self.execute_marketing(delete, await self.proof_marketing(delete))
        self.assertEqual(result["result"], {"deleted_id": 1})
        cleanup.assert_called_once_with("private-media-1.mp4")
        async with self.sessions() as db:
            self.assertIsNone(await db.get(CourseAdCreative, 1))
            view = await db.scalar(select(CourseAdView))
            self.assertIsNone(view.ad_id)
            self.assertTrue(view.completed)
            audit = await db.get(AdminPwaCommandAudit, result["command_id"])
            for forbidden in ("Creative", "private-media", "media_blob", "media_url"):
                self.assertNotIn(forbidden, audit.result_json)

    async def test_shared_media_is_retained_when_deleting_one_creative(self):
        await self.seed_ads(2, shared_path=True)
        command = await self.prepare_marketing({"kind": "course_ad", "ad_id": 1, "operation": "delete"})
        cleanup = Mock()
        with patch.object(marketing, "_cleanup_deleted_media", cleanup):
            await self.execute_marketing(command, await self.proof_marketing(command))
        cleanup.assert_not_called()
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(CourseAdCreative, 2))

    async def test_current_legacy_configuration_change_invalidates_the_signed_snapshot(self):
        command = await self.prepare_marketing(PROMO_CHANGE)
        proof = await self.proof_marketing(command)
        async with self.sessions() as db:
            await save_desktop_app_promo_settings(db, {"media_type": "photo", "media_path": "new-media.jpg"})
            await db.commit()
        with self.assertRaisesRegex(marketing.CommandError, "confirmation_changed") as caught:
            await self.execute_marketing(command, proof)
        self.assertEqual(caught.exception.status, 409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_ad_state_change_and_cross_command_tamper_are_rejected(self):
        await self.seed_ads()
        command = await self.prepare_marketing({"kind": "course_ad", "ad_id": 1,
                                                "operation": "set_active", "is_active": False})
        proof = await self.proof_marketing(command)
        altered = marketing.MarketingCommand.model_validate({**command.model_dump(), "change": {
            "kind": "course_ad", "ad_id": 1, "operation": "delete", "is_active": None}})
        with self.assertRaisesRegex(marketing.CommandError, "step_up_denied"):
            await self.execute_marketing(altered, proof)
        async with self.sessions() as db:
            await CourseAdService(db).set_active(1, False)
            await db.commit()
        with self.assertRaisesRegex(marketing.CommandError, "confirmation_changed"):
            await self.execute_marketing(command, proof)

    async def test_audit_failure_rolls_back_the_ad_deletion_and_proof(self):
        await self.seed_ads()
        command = await self.prepare_marketing({"kind": "course_ad", "ad_id": 1, "operation": "delete"})
        proof = await self.proof_marketing(command)
        original = AsyncSession.flush

        async def fail_audit(db, *args, **kwargs):
            if any(isinstance(row, AdminPwaCommandAudit) for row in db.new):
                raise RuntimeError("synthetic audit failure")
            return await original(db, *args, **kwargs)

        cleanup = Mock()
        with patch.object(AsyncSession, "flush", fail_audit), patch.object(marketing, "_cleanup_deleted_media", cleanup):
            with self.assertRaisesRegex(RuntimeError, "audit failure"):
                await self.execute_marketing(command, proof)
        cleanup.assert_not_called()
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(CourseAdCreative, 1))
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_target_wait_expiry_and_revoked_session_deny_writes(self):
        command = await self.prepare_marketing(PROMO_CHANGE)
        proof = await self.proof_marketing(command)
        original = marketing._target
        future = datetime.now(timezone.utc) + timedelta(minutes=2)

        class AfterWaitDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return future.astimezone(tz) if tz else future.replace(tzinfo=None)

        clock = patch.object(marketing, "datetime", AfterWaitDateTime)

        async def after_wait(db, change, *, lock=False):
            result = await original(db, change, lock=lock)
            if lock:
                clock.start()
            return result

        try:
            with patch.object(marketing, "_target", after_wait):
                with self.assertRaisesRegex(marketing.CommandError, "step_up_denied"):
                    await self.execute_marketing(command, proof)
        finally:
            clock.stop()
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(BotSetting)), 0)
            (await db.get(AdminPwaSession, self.session_id)).revoked_at = datetime.now(timezone.utc)
            await db.commit()
        with self.assertRaisesRegex(marketing.CommandError, "step_up_denied"):
            await self.execute_marketing(command, proof)

    async def test_strict_input_rejects_coercions_unknown_fields_and_outbound_actions(self):
        invalid = [
            {"kind": "sales_experiment", "mode": "ab", "treatment_percent": False},
            {"kind": "sales_experiment", "mode": "ab", "treatment_percent": "50"},
            {"kind": "sales_experiment", "mode": "ab", "treatment_percent": 75},
            {"kind": "course_ad", "ad_id": 1, "operation": "set_active"},
            {"kind": "course_ad", "ad_id": 1, "operation": "delete", "is_active": True},
            {"kind": "course_ad", "ad_id": True, "operation": "delete"},
            {"kind": "broadcast", "text": "not accepted"},
            {**PROMO_CHANGE, "daily_limit": "2"}, {**PROMO_CHANGE, "enabled": 1},
            {**PROMO_CHANGE, "media_path": "client-controlled.jpg"},
            {**PROMO_CHANGE, "platforms": {"macos": True}},
        ]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                marketing.PrepareMarketing.model_validate({"change": change})

    async def test_cleanup_never_uses_an_arbitrary_or_traversing_path(self):
        with patch.object(marketing.os, "unlink") as remove:
            for path in ("../private.mp4", "/private.mp4", "secret.txt", "a/../../private.mp4", None):
                marketing._cleanup_deleted_media(path)
            remove.assert_not_called()
            marketing._cleanup_deleted_media("course-ad-review.mp4")
            remove.assert_called_once()

    async def test_http_origin_body_auth_and_disabled_guards(self):
        app = FastAPI()
        app.include_router(marketing.create_admin_pwa_marketing_router(
            settings_obj=self.settings, session_factory=self.sessions))
        headers = {"origin": ORIGIN, "sec-fetch-site": "same-origin", "content-type": "application/json",
                   "cookie": "__Host-hskai_admin=" + fixtures.COOKIE}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as client:
            result = await client.post("/api/admin/v1/marketing/read", headers=headers, json={})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.headers["cache-control"], "no-store")
            self.assertFalse(result.headers.get_list("set-cookie"))
            for changed, status in (({"origin": "https://evil.example"}, 403),
                                    ({"sec-fetch-site": "cross-site"}, 403),
                                    ({"content-type": "text/plain"}, 415),
                                    ({"cookie": "", "authorization": "Bearer " + fixtures.COOKIE}, 401)):
                self.assertEqual((await client.post("/api/admin/v1/marketing/read",
                    headers={**headers, **changed}, json={})).status_code, status)
            for body in (b'{"change":{},"change":{}}', b'x' * 4097, b'null', b'[]'):
                self.assertEqual((await client.post("/api/admin/v1/marketing/prepare",
                    headers=headers, content=body)).status_code, 400)
            self.settings.ADMIN_PWA_ENABLED = False
            for route in ("read", "prepare", "save"):
                self.assertEqual((await client.post("/api/admin/v1/marketing/" + route,
                    headers=headers, json={})).status_code, 404)
