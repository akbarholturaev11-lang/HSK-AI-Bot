"""Typed first-party settings: bounded reads, raw CAS, exact proof and audit."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import event, func, select

from app.admin_api import pwa_settings as api
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_step_up import begin_step_up, operation_digest, verify_step_up
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.bot_setting import BotSetting
from app.db.models.course_track_state import CourseTrackState
from app.db.models.payment import Payment
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.ai_provider import ACTIVE_GEMINI_MODEL_KEY, GEMINI_MODEL_OPTIONS
from app.services.help_settings_service import HELP_VIDEO_FIELD_BY_KEY
from app.services.subscription_miniapp_service import PAYMENT_DETAILS_KEY, PAYMENT_DETAILS_ALIF_KEY
from app.services.support_contact_service import ADMIN_CONTACT_KEY
from app.services.android_update_policy_service import ANDROID_UPDATE_ALLOWED_VERSIONS_KEY
from tests import test_admin_pwa_payment_review as fixtures
from tests.test_admin_pwa_webauthn_crypto_vectors import CRED_ID, make_assertion


class AdminPwaSettingsTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def prepare(self, change):
        async with self.sessions() as db:
            result = await api.prepare_settings(db, session_cookie=fixtures.COOKIE,
                request=api.PrepareSettings.model_validate({"change": change}), settings_obj=self.settings)
        return api.SettingsCommand.model_validate(result["operation"]["payload"])

    async def proof(self, command, *, signed=False):
        if signed:
            async with self.sessions() as db:
                started = await begin_step_up(db, session_cookie=fixtures.COOKIE,
                    settings_obj=self.settings, **command.operation())
            self.assertIsNotNone(started)
            async with self.sessions() as db:
                challenge = bytes((await db.get(AdminPwaStepUp, started.step_up_id)).challenge)
            async with self.sessions() as db:
                self.assertTrue(await verify_step_up(db, session_cookie=fixtures.COOKIE,
                    step_up_id=started.step_up_id, settings_obj=self.settings,
                    credential=make_assertion(self.key, challenge=challenge)))
            return started.step_up_id
        now, step_id = datetime.now(timezone.utc), str(uuid4())
        operation = command.operation()
        async with self.sessions() as db:
            db.add(AdminPwaStepUp(id=step_id, session_id=self.session_id, user_id=101,
                action=operation["action"], target=operation["target"],
                payload_hash=operation_digest(**operation), challenge=b"S"*32,
                status="verified", credential_id=CRED_ID, verified_at=now,
                created_at=now, expires_at=now+timedelta(seconds=50)))
            await db.commit()
        return step_id

    async def execute(self, command, step_id):
        async with self.sessions() as db:
            return await api.execute_settings(db, session_cookie=fixtures.COOKIE,
                request=api.ExecuteSettings(**command.model_dump(), step_up_id=step_id),
                settings_obj=self.settings)

    async def post(self, path, body, *, cookie=fixtures.COOKIE, origin="https://hskai.app", raw=False):
        app = FastAPI()
        app.include_router(api.create_admin_pwa_settings_router(
            settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app",
                headers={"origin": origin}, cookies={ADMIN_PWA_COOKIE_NAME: cookie} if cookie else {}) as client:
            return await client.post("/api/admin/v1/settings/"+path,
                **({"content": body, "headers": {"content-type": "application/json"}} if raw else {"json": body}))

    async def test_read_uses_one_fixed_key_query_never_reads_secrets_or_creates_defaults(self):
        self.settings.PAYMENT_DETAILS = "Environment bank fallback"
        async with self.sessions() as db:
            db.add_all([BotSetting(key="provider_secret", value="DO_NOT_READ"),
                        BotSetting(key=PAYMENT_DETAILS_KEY, value="   ")])
            await db.commit()
        statements = []
        def collect(conn, cursor, statement, parameters, context, executemany):
            if "bot_settings" in statement.lower():
                statements.append((statement.lower(), parameters))
        event.listen(self.engine.sync_engine, "before_cursor_execute", collect)
        try:
            response = await self.post("read", {})
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", collect)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["settings"]["payment_details"], {"dc_city": "Environment bank fallback", "alif": ""})
        self.assertEqual(len(data["settings"]["help_videos"]), 12)
        self.assertEqual(data["options"]["ai_models"], GEMINI_MODEL_OPTIONS)
        self.assertEqual(data["options"]["android_update_allowed_versions"], [1, 2, 3, 4])
        self.assertEqual(data["settings"]["android_update"], {"allowed_versions": 4})
        self.assertNotIn("DO_NOT_READ", response.text)
        self.assertEqual(len(statements), 1, statements)
        self.assertTrue(statements[0][0].lstrip().startswith("select "))
        self.assertNotIn("provider_secret", str(statements))
        self.assertEqual(set(statements[0][1][:-2]), set(api._ALL_KEYS))
        self.assertIn("no-store", response.headers["cache-control"])
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BotSetting)), 2)

    async def test_each_typed_kind_updates_only_its_setting_with_private_hash_audit(self):
        changes = [
            ({"kind": "payment_details", "bank": "dc_city", "value": " PRIVATE city bank\nAccount 123 "}, PAYMENT_DETAILS_KEY, "PRIVATE city bank\nAccount 123"),
            ({"kind": "payment_details", "bank": "alif", "value": "PRIVATE alif bank"}, PAYMENT_DETAILS_ALIF_KEY, "PRIVATE alif bank"),
            ({"kind": "ai_model", "model": GEMINI_MODEL_OPTIONS[1]}, ACTIVE_GEMINI_MODEL_KEY, GEMINI_MODEL_OPTIONS[1]),
            ({"kind": "help_contact", "value": " @private_support "}, ADMIN_CONTACT_KEY, "@private_support"),
            ({"kind": "android_update", "allowed_versions": 2}, ANDROID_UPDATE_ALLOWED_VERSIONS_KEY, "2"),
        ]
        changes += [({"kind": "help_video", "key": "course_hsk", "lang": lang,
                       "value": "t.me/private_course_"+lang},
                      HELP_VIDEO_FIELD_BY_KEY["course_hsk"].setting_key(lang),
                      "https://t.me/private_course_"+lang) for lang in ("uz", "ru", "tj")]
        async with self.sessions() as db:
            before_payments = await db.scalar(select(func.count()).select_from(Payment))
            learner = await db.get(User, 1)
            before_access = (learner.status, learner.payment_status, learner.start_date, learner.end_date)
        for index, (change, key, expected) in enumerate(changes):
            command = await self.prepare(change)
            step_id = await self.proof(command, signed=index == 0)
            result = await self.execute(command, step_id)
            self.assertEqual(result["setting"]["kind"], change["kind"])
            self.assertEqual(len(result["revision_hash"]), 64)
            async with self.sessions() as db:
                self.assertEqual((await db.get(BotSetting, key)).value, expected)
                self.assertEqual((await db.get(AdminPwaStepUp, step_id)).status, "consumed")
                audit = await db.get(AdminPwaCommandAudit, result["command_id"])
                self.assertEqual(audit.payload_hash, operation_digest(**command.operation()))
                self.assertEqual(audit.action, "settings.update")
                self.assertIsNone(audit.target_user_id)
                self.assertEqual(set(json.loads(audit.result_json)), {"kind", "previous_hash", "result_hash"})
                self.assertNotIn("PRIVATE", audit.result_json)
                self.assertNotIn("private_support", audit.result_json)
                self.assertNotIn("private_course", audit.result_json)
            with self.assertRaises(api.CommandError):
                await self.execute(command, step_id)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(Payment)), before_payments)
            self.assertEqual(await db.scalar(select(func.count()).select_from(CourseTrackState)), 0)
            learner = await db.get(User, 1)
            self.assertEqual((learner.status, learner.payment_status, learner.start_date, learner.end_date), before_access)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), len(changes))


    async def test_android_update_setting_rejects_outside_four_choices(self):
        for wrong in (0, 5, -2, 1.2, '2', None, True):
            with self.subTest(wrong=wrong):
                with self.assertRaises(ValidationError):
                    api.PrepareSettings.model_validate({
                        "change": {"kind": "android_update", "allowed_versions": wrong}
                    })

    async def test_value_or_kind_target_tampering_does_not_consume_proof(self):
        command = await self.prepare({"kind": "payment_details", "bank": "dc_city", "value": "PRIVATE original"})
        step_id = await self.proof(command)
        for altered in ({"kind": "payment_details", "bank": "dc_city", "value": "PRIVATE tampered"},
                        {"kind": "payment_details", "bank": "alif", "value": "PRIVATE original"},
                        {"kind": "help_contact", "value": "@support_qa"}):
            changed = api.SettingsCommand(change=altered, expected_hash=command.expected_hash)
            with self.assertRaises(api.CommandError) as denied:
                await self.execute(changed, step_id)
            self.assertEqual(denied.exception.status, 403)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, step_id)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(BotSetting)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_same_display_value_with_changed_raw_timestamp_fails_cas(self):
        async with self.sessions() as db:
            db.add(BotSetting(key=ADMIN_CONTACT_KEY, value="@support_qa"))
            await db.commit()
        command = await self.prepare({"kind": "help_contact", "value": "@other_support"})
        step_id = await self.proof(command)
        async with self.sessions() as db:
            row = await db.get(BotSetting, ADMIN_CONTACT_KEY)
            row.updated_at = datetime.now(timezone.utc)+timedelta(seconds=1)
            await db.commit()
        with self.assertRaises(api.CommandError) as stale:
            await self.execute(command, step_id)
        self.assertEqual(stale.exception.status, 409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, step_id)).status, "verified")
            self.assertEqual((await db.get(BotSetting, ADMIN_CONTACT_KEY)).value, "@support_qa")

    async def test_absent_to_empty_stored_state_is_not_hidden_by_display_default(self):
        command = await self.prepare({"kind": "help_contact", "value": "@support_qa"})
        step_id = await self.proof(command)
        async with self.sessions() as db:
            db.add(BotSetting(key=ADMIN_CONTACT_KEY, value=""))
            await db.commit()
        with self.assertRaises(api.CommandError) as stale:
            await self.execute(command, step_id)
        self.assertEqual(stale.exception.status, 409)

    async def test_flag_and_expired_proof_are_rechecked_after_setting_lock(self):
        command = await self.prepare({"kind": "help_contact", "value": "@support_qa"})
        step_id = await self.proof(command)
        original_lock = BotSettingRepository.lock_key
        async def disable_after_lock(repo, key):
            await original_lock(repo, key)
            self.settings.ADMIN_PWA_ENABLED = False
        try:
            with patch.object(BotSettingRepository, "lock_key", disable_after_lock):
                with self.assertRaises(api.CommandError) as denied:
                    await self.execute(command, step_id)
            self.assertEqual(denied.exception.status, 403)
        finally:
            self.settings.ADMIN_PWA_ENABLED = True
        future = datetime.now(timezone.utc)+timedelta(minutes=2)
        class AfterWaitDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return future.astimezone(tz) if tz else future.replace(tzinfo=None)
        with patch.object(api, "datetime", AfterWaitDateTime):
            with self.assertRaises(api.CommandError) as expired:
                await self.execute(command, step_id)
        self.assertEqual(expired.exception.status, 403)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, step_id)).status, "verified")
            self.assertIsNone(await db.get(BotSetting, ADMIN_CONTACT_KEY))

    async def test_ai_cache_changes_only_after_successful_commit(self):
        command = await self.prepare({"kind": "ai_model", "model": GEMINI_MODEL_OPTIONS[1]})
        step_id = await self.proof(command)
        async with self.sessions() as db:
            def committed(model):
                self.assertFalse(db.in_transaction())
                self.assertEqual(model, GEMINI_MODEL_OPTIONS[1])
            with patch.object(api, "set_active_gemini_model_cache", side_effect=committed) as cache:
                await api.execute_settings(db, session_cookie=fixtures.COOKIE,
                    request=api.ExecuteSettings(**command.model_dump(), step_up_id=step_id), settings_obj=self.settings)
                cache.assert_called_once()
        command = await self.prepare({"kind": "ai_model", "model": GEMINI_MODEL_OPTIONS[0]})
        step_id = await self.proof(command)
        async with self.sessions() as db:
            row = await db.get(BotSetting, ACTIVE_GEMINI_MODEL_KEY)
            row.updated_at = datetime.now(timezone.utc)+timedelta(seconds=1)
            await db.commit()
        with patch.object(api, "set_active_gemini_model_cache") as cache:
            with self.assertRaises(api.CommandError):
                await self.execute(command, step_id)
            cache.assert_not_called()

    async def test_routes_reject_wrong_auth_origin_flags_body_and_oversize_proof_before_passkey(self):
        for cookie, origin, expected in ((None,"https://hskai.app",401),
                ("X"*64,"https://hskai.app",401),(fixtures.COOKIE,"https://evil.invalid",403)):
            self.assertEqual((await self.post("read", {}, cookie=cookie, origin=origin)).status_code, expected)
        for body in ({"key":"provider_secret"}, {"kind":"hsk30"}, []):
            self.assertEqual((await self.post("read", body)).status_code, 400)
        self.assertEqual((await self.post("read", "{bad json", raw=True)).status_code, 400)
        self.assertEqual((await self.post("read", " "*(16*1024+1), raw=True)).status_code, 400)
        self.assertEqual((await self.post("prepare", {"change": {"kind":"payment_details",
            "bank":"dc_city", "value":"漢"*1500}})).status_code, 400)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaStepUp)), 0)
            (await db.get(User, 101)).status = "blocked"
            await db.commit()
        self.assertEqual((await self.post("read", {})).status_code, 401)
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertEqual((await self.post("read", {})).status_code, 404)

    def test_strict_kinds_and_value_bounds_preserve_fixed_setting_ownership(self):
        bad = [
            {"kind":"hsk30","enabled":True}, {"kind":"provider_secret","value":"secret"},
            {"kind":"payment_details","bank":"visa","value":"a"},
            {"kind":"payment_details","bank":"alif","value":" "},
            {"kind":"payment_details","bank":"alif","value":123},
            {"kind":"payment_details","bank":"alif","value":"x"*1501},
            {"kind":"ai_model","model":"unreviewed-provider-model"},
            {"kind":"help_contact","value":"javascript:alert(1)"},
            {"kind":"help_contact","value":"https://example.invalid/\nsecret"},
            {"kind":"help_video","key":"unknown","lang":"uz","value":""},
            {"kind":"help_video","key":"course_hsk","lang":"tg","value":""},
            {"kind":"help_video","key":"course_hsk","lang":"uz","value":"file:///etc/passwd"},
            {"kind":"help_video","key":"course_hsk","lang":"uz","value":"https://user:pass@example.invalid"},
            {"kind":"help_video","key":"course_hsk","lang":"uz","value":"https://example.invalid/\x00secret"},
            {"kind":"help_contact","value":"@support_qa","key":"api_secret"},
        ]
        for change in bad:
            with self.assertRaises(ValidationError, msg=str(change)):
                api.PrepareSettings.model_validate({"change": change})
