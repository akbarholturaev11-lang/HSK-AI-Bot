"""Signed marketing commands against real isolated SQL; no live messaging."""
import json
import hashlib
import base64
from copy import deepcopy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from io import BytesIO
from unittest.mock import Mock, patch
from uuid import uuid4

import httpx
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image

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
from app.services.course_ad_translation_service import localize_ad_copy
from app.services import course_ad_service
from app.services.course_sales_experiment_service import CourseSalesExperimentService
from app.services.desktop_app_promo_settings_service import (
    DESKTOP_APP_PROMO_SETTINGS_KEY, get_desktop_app_promo_settings,
    desktop_app_promo_public_filename_allowed, save_desktop_app_promo_settings,
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

    async def execute_marketing(self, command, proof, **kwargs):
        async with self.sessions() as db:
            return await marketing.execute_marketing(db, session_cookie=fixtures.COOKIE,
                request=marketing.ExecuteMarketing(**command.model_dump(), step_up_id=proof),
                settings_obj=self.settings, **kwargs)

    @staticmethod
    def promo_png():
        output = BytesIO()
        Image.new("RGB", (3, 2), (26, 106, 117)).save(output, format="PNG")
        return output.getvalue()

    @staticmethod
    def creative_change(data, *, language="all", media_type="photo"):
        copies = {"uz": {"title": "QA 中文 kursi", "button_text": "O‘rganish"},
                  "ru": {"title": "QA курс китайского", "button_text": "Учиться"},
                  "tj": {"title": "QA курси чинӣ", "button_text": "Омӯхтан"}}
        return {"kind": "course_ad_create", "language": language,
                "copies": {lang: copy if language == "all" or language == lang else None
                           for lang, copy in copies.items()},
                "ad_type": "odiy", "placements": ["screen_center", "lesson_end"],
                "duration_seconds": 7, "link_url": "@qa_course_bot", "is_active": False,
                "media_type": media_type, "media_sha256": hashlib.sha256(data).hexdigest(),
                "media_size": len(data)}

    async def test_create_multilingual_course_ad_http_is_signed_disk_only_and_not_replayed(self):
        data = self.promo_png()
        change = self.creative_change(data)
        command = await self.prepare_marketing(change)
        operation = command.operation()
        self.assertNotIn("copies", operation["payload"]["change"])
        self.assertEqual(operation["payload"]["copy_hash"], marketing._hash(change["copies"]))
        self.assertLess(len(json.dumps(operation)), 4096)
        proof = await self.proof_marketing(command, signed=True)
        raw_command = json.dumps({**command.model_dump(), "step_up_id": proof}, ensure_ascii=False).encode()
        encoded = base64.urlsafe_b64encode(raw_command).decode().rstrip("=")
        self.assertLess(len(encoded), 8192)
        headers = {"origin": ORIGIN, "sec-fetch-site": "same-origin", "content-type": "image/png",
                   "cookie": "__Host-hskai_admin=" + fixtures.COOKIE,
                   "x-admin-pwa-command": encoded, "x-admin-pwa-command-encoding": "base64url"}
        app = FastAPI()
        app.include_router(marketing.create_admin_pwa_marketing_router(
            settings_obj=self.settings, session_factory=self.sessions))
        with tempfile.TemporaryDirectory(prefix="admin-pwa-create-ad-") as media_root:
            with patch.object(marketing, "COURSE_AD_MEDIA_ROOT", media_root):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as client:
                    for encoded_bad, encoding in (("not_base64!", "base64url"), (encoded, "unknown")):
                        rejected = await client.post("/api/admin/v1/marketing/media/save", content=data,
                            headers={**headers, "x-admin-pwa-command": encoded_bad,
                                     "x-admin-pwa-command-encoding": encoding})
                        self.assertEqual(rejected.status_code, 400)
                    result = await client.post("/api/admin/v1/marketing/media/save", headers=headers, content=data)
                    self.assertEqual(result.status_code, 200, result.text)
                    replay = await client.post("/api/admin/v1/marketing/media/save", headers=headers, content=data)
                    self.assertEqual(replay.status_code, 403)
                async with self.sessions() as db:
                    saved = await db.scalar(select(CourseAdCreative))
                    self.assertFalse(saved.is_active)
                    self.assertEqual(saved.created_by_telegram_id, 9001)
                    self.assertEqual(saved.placements, "lesson_end,screen_center")
                    self.assertEqual(saved.link_url, "https://t.me/qa_course_bot")
                    self.assertEqual(saved.media_type, "photo")
                    self.assertEqual((Path(media_root) / saved.media_path).read_bytes(), data)
                    self.assertIsNone(await db.scalar(select(CourseAdCreative.media_blob)))
                    self.assertIsNone(saved.media_size)
                    for lang, copy in change["copies"].items():
                        self.assertEqual(localize_ad_copy(saved.localized_copy, title=saved.title,
                            button_text=saved.button_text, language=lang), (copy["title"], copy["button_text"]))
                    self.assertEqual(await db.scalar(select(func.count()).select_from(CourseAdCreative)), 1)
                    self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 1)
                    self.assertEqual(await db.scalar(select(func.count()).select_from(AdCampaign)), 0)
                    audit = await db.get(AdminPwaCommandAudit, result.json()["command_id"])
                    self.assertEqual(audit.payload_hash, operation_digest(**operation))
                    for forbidden in (saved.title, saved.media_path, "Учиться", "media_blob"):
                        self.assertNotIn(forbidden, audit.result_json)

    async def test_new_creative_validation_rejects_inexact_copy_target_and_media(self):
        valid = self.creative_change(self.promo_png())
        invalid = []
        for field, value in (("language", "tg"), ("ad_type", "app"), ("placements", ["practice"]),
                             ("placements", ["screen_center", "screen_center"]),
                             ("duration_seconds", True), ("media_size", 1024 * 1024 + 1),
                             ("link_url", "javascript:alert(1)"), ("link_url", "http://example.invalid"),
                             ("link_url", "https://user:pass@example.invalid"), ("link_url", "@")):
            invalid.append({**valid, field: value})
        missing = deepcopy(valid); missing["copies"]["ru"] = None; invalid.append(missing)
        mixed = deepcopy(valid); mixed["copies"]["ru"]["button_text"] = ""; invalid.append(mixed)
        wrong_single = deepcopy(valid); wrong_single["language"] = "uz"; invalid.append(wrong_single)
        blank = deepcopy(valid); blank["copies"]["tj"]["title"] = "  "; invalid.append(blank)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                marketing.PrepareMarketing.model_validate({"change": value})

    async def test_new_creative_video_preflight_is_same_session_and_encoding_has_no_db_transaction(self):
        data = b"source-video"
        command = await self.prepare_marketing(self.creative_change(data, language="uz", media_type="video"))
        proof = await self.proof_marketing(command, signed=True)
        request = marketing.ExecuteMarketing(**command.model_dump(), step_up_id=proof)
        foreign_cookie = "V" * 64
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add(AdminPwaSession(id=str(uuid4()), user_id=101,
                token_hash=hashlib.sha256(foreign_cookie.encode()).hexdigest(), auth_method="webauthn",
                created_at=now, expires_at=now + timedelta(hours=1)))
            await db.commit()
        with tempfile.TemporaryDirectory(prefix="admin-pwa-create-video-") as media_root:
            with patch.object(marketing, "COURSE_AD_MEDIA_ROOT", media_root):
                with patch.object(marketing, "prepare_pwa_course_ad_video_file") as encode:
                    async with self.sessions() as db:
                        with self.assertRaisesRegex(marketing.CommandError, "step_up_denied"):
                            await marketing.execute_marketing(db, session_cookie=foreign_cookie,
                                request=request, settings_obj=self.settings,
                                media_bytes=data, media_content_type="video/mp4")
                    encode.assert_not_called()
                async with self.sessions() as db:
                    def fake_encode(raw, *, raw_ext, media_root):
                        self.assertFalse(db.in_transaction())
                        filename = "course_ad_pwa_0123456789abcdef0123456789abcdef.mp4"
                        (Path(media_root) / filename).write_bytes(b"encoded-mp4")
                        return filename
                    with patch.object(marketing, "prepare_pwa_course_ad_video_file", side_effect=fake_encode):
                        result = await marketing.execute_marketing(db, session_cookie=fixtures.COOKIE,
                            request=request, settings_obj=self.settings,
                            media_bytes=data, media_content_type="video/mp4")
                async with self.sessions() as db:
                    saved = await db.get(CourseAdCreative, result["result"]["id"])
                    self.assertEqual(saved.media_type, "video")
                    self.assertEqual(saved.language, "uz")
                    self.assertIsNone(saved.localized_copy)
                    self.assertFalse(saved.is_active)

    async def test_new_creative_audit_failure_rolls_back_row_proof_and_unreferenced_asset(self):
        data = self.promo_png()
        command = await self.prepare_marketing(self.creative_change(data))
        proof = await self.proof_marketing(command, signed=True)
        original = AsyncSession.flush
        async def fail_audit(db, *args, **kwargs):
            if any(isinstance(row, AdminPwaCommandAudit) for row in db.new):
                raise RuntimeError("synthetic audit failure")
            return await original(db, *args, **kwargs)
        with tempfile.TemporaryDirectory(prefix="admin-pwa-create-rollback-") as media_root:
            with patch.object(marketing, "COURSE_AD_MEDIA_ROOT", media_root), \
                    patch.object(AsyncSession, "flush", fail_audit):
                with self.assertRaisesRegex(RuntimeError, "audit failure"):
                    await self.execute_marketing(command, proof, media_bytes=data, media_content_type="image/png")
            self.assertEqual(list(Path(media_root).iterdir()), [])
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(CourseAdCreative)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")

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

    async def test_desktop_promo_image_is_hash_bound_and_clear_removes_only_after_commit(self):
        data = self.promo_png()
        with tempfile.TemporaryDirectory(prefix="admin-pwa-promo-") as media_root:
            with patch.object(marketing, "DESKTOP_APP_PROMO_MEDIA_ROOT", media_root), \
                    patch.object(marketing, "desktop_app_promo_media_full_path",
                                 lambda name: str(Path(media_root) / name) if name else None):
                change = {**PROMO_CHANGE, "media_sha256": hashlib.sha256(data).hexdigest(),
                          "media_size": len(data), "clear_media": False}
                command = await self.prepare_marketing(change)
                operation = command.operation()
                self.assertEqual(operation["target"], "desktop_promo")
                self.assertEqual(operation["payload"]["change"]["media_sha256"],
                                 hashlib.sha256(data).hexdigest())
                proof = await self.proof_marketing(command, signed=True)
                result = await self.execute_marketing(command, proof, media_bytes=data,
                                                       media_content_type="image/png")
                async with self.sessions() as db:
                    saved = await get_desktop_app_promo_settings(db)
                    self.assertEqual(saved.media_type, "photo")
                    self.assertTrue(saved.media_path.startswith("desktop_app_promo_pwa_"))
                    self.assertTrue((Path(media_root) / saved.media_path).is_file())
                    audit = await db.get(AdminPwaCommandAudit, result["command_id"])
                    self.assertEqual(audit.payload_hash, operation_digest(**operation))
                    self.assertNotIn(saved.media_path, audit.result_json)
                    self.assertNotIn(data.hex(), audit.result_json)

                clear_change = {**PROMO_CHANGE, "clear_media": True}
                clear = await self.prepare_marketing(clear_change)
                clear_proof = await self.proof_marketing(clear)
                await self.execute_marketing(clear, clear_proof)
                async with self.sessions() as db:
                    cleared = await get_desktop_app_promo_settings(db)
                    self.assertIsNone(cleared.media_path)
                    self.assertIsNone(cleared.media_type)
                self.assertFalse((Path(media_root) / saved.media_path).exists())

    async def test_desktop_promo_media_tampering_and_audit_rollback_leave_no_asset(self):
        data = self.promo_png()
        with tempfile.TemporaryDirectory(prefix="admin-pwa-promo-") as media_root:
            with patch.object(marketing, "DESKTOP_APP_PROMO_MEDIA_ROOT", media_root), \
                    patch.object(marketing, "desktop_app_promo_media_full_path",
                                 lambda name: str(Path(media_root) / name) if name else None):
                change = {**PROMO_CHANGE, "media_sha256": hashlib.sha256(data).hexdigest(),
                          "media_size": len(data), "clear_media": False}
                command = await self.prepare_marketing(change)
                proof = await self.proof_marketing(command)
                altered = data[:-1] + bytes([data[-1] ^ 1])
                with self.assertRaisesRegex(marketing.CommandError, "invalid_media"):
                    await self.execute_marketing(command, proof, media_bytes=altered,
                                                 media_content_type="image/png")
                with self.assertRaisesRegex(marketing.CommandError, "invalid_media"):
                    await self.execute_marketing(command, proof, media_bytes=data,
                                                 media_content_type="image/jpeg")
                async with self.sessions() as db:
                    self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
                    self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

                proof = await self.proof_marketing(command)
                original_flush = AsyncSession.flush

                async def fail_audit(session, *args, **kwargs):
                    if any(isinstance(item, AdminPwaCommandAudit) for item in session.new):
                        raise RuntimeError("synthetic audit failure")
                    return await original_flush(session, *args, **kwargs)

                with patch.object(AsyncSession, "flush", fail_audit):
                    with self.assertRaisesRegex(RuntimeError, "audit failure"):
                        await self.execute_marketing(command, proof, media_bytes=data,
                                                     media_content_type="image/png")
                self.assertEqual(list(Path(media_root).iterdir()), [])
                async with self.sessions() as db:
                    self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
                    self.assertEqual(await db.scalar(select(func.count()).select_from(BotSetting)), 0)

    async def test_desktop_promo_public_media_accepts_only_server_generated_names(self):
        self.assertTrue(desktop_app_promo_public_filename_allowed(
            "desktop_app_promo_123456_1761350000_0123456789.png"))
        self.assertTrue(desktop_app_promo_public_filename_allowed(
            "desktop_app_promo_pwa_0123456789abcdef0123456789abcdef.webp"))
        for filename in (".admin-pwa-0123456789abcdef.tmp", "../desktop_app_promo_1_2_0123456789.jpg",
                         "arbitrary.jpg", "desktop_app_promo_pwa_bad.jpg"):
            self.assertFalse(desktop_app_promo_public_filename_allowed(filename), filename)

    async def test_course_ad_image_replace_is_signed_disk_only_and_preserves_shared_old_file(self):
        data = self.promo_png()
        await self.seed_ads(2, shared_path=True)
        with tempfile.TemporaryDirectory(prefix="admin-pwa-course-ad-") as media_root:
            old_path = Path(media_root) / "retained-private-media.mp4"
            old_path.write_bytes(b"old shared creative")
            with patch.object(marketing, "COURSE_AD_MEDIA_ROOT", media_root), \
                    patch.object(course_ad_service, "COURSE_AD_MEDIA_ROOT", media_root):
                change = {"kind": "course_ad", "ad_id": 1, "operation": "replace_image",
                          "is_active": None, "media_sha256": hashlib.sha256(data).hexdigest(),
                          "media_size": len(data)}
                command = await self.prepare_marketing(change)
                operation = command.operation()
                proof = await self.proof_marketing(command, signed=True)
                result = await self.execute_marketing(command, proof, media_bytes=data,
                                                       media_content_type="image/png")
                async with self.sessions() as db:
                    saved = await db.get(CourseAdCreative, 1)
                    self.assertEqual(saved.media_type, "photo")
                    self.assertTrue(saved.media_path.startswith("course_ad_pwa_"))
                    self.assertIsNone(saved.media_size)
                    self.assertIsNone(saved.media_checksum)
                    self.assertIsNone(await db.scalar(select(CourseAdCreative.media_blob).where(
                        CourseAdCreative.id == 1)))
                    self.assertEqual((Path(media_root) / saved.media_path).read_bytes(), data)
                    audit = await db.get(AdminPwaCommandAudit, result["command_id"])
                    self.assertEqual(audit.payload_hash, operation_digest(**operation))
                    self.assertNotIn(saved.media_path, audit.result_json)
                self.assertTrue(old_path.is_file(), "shared old asset must remain available")
                second_change = {**change, "ad_id": 2}
                second_command = await self.prepare_marketing(second_change)
                second_proof = await self.proof_marketing(second_command)
                await self.execute_marketing(second_command, second_proof, media_bytes=data,
                                             media_content_type="image/png")
                self.assertFalse(old_path.exists(), "unreferenced old asset is removed after commit")

    async def test_course_ad_image_audit_rollback_removes_unreferenced_new_asset(self):
        data = self.promo_png()
        await self.seed_ads(1)
        with tempfile.TemporaryDirectory(prefix="admin-pwa-course-ad-rollback-") as media_root:
            old_path = Path(media_root) / "private-media-1.mp4"
            old_path.write_bytes(b"old creative")
            with patch.object(marketing, "COURSE_AD_MEDIA_ROOT", media_root), \
                    patch.object(course_ad_service, "COURSE_AD_MEDIA_ROOT", media_root):
                change = {"kind": "course_ad", "ad_id": 1, "operation": "replace_image",
                          "is_active": None, "media_sha256": hashlib.sha256(data).hexdigest(),
                          "media_size": len(data)}
                command = await self.prepare_marketing(change)
                proof = await self.proof_marketing(command)
                original_flush = AsyncSession.flush

                async def fail_audit(session, *args, **kwargs):
                    if any(isinstance(item, AdminPwaCommandAudit) for item in session.new):
                        raise RuntimeError("synthetic audit failure")
                    return await original_flush(session, *args, **kwargs)

                with patch.object(AsyncSession, "flush", fail_audit):
                    with self.assertRaisesRegex(RuntimeError, "audit failure"):
                        await self.execute_marketing(command, proof, media_bytes=data,
                                                     media_content_type="image/png")
                self.assertEqual({path.name for path in Path(media_root).iterdir()},
                                 {"private-media-1.mp4"})
                async with self.sessions() as db:
                    row = await db.get(CourseAdCreative, 1)
                    self.assertEqual(row.media_path, "private-media-1.mp4")
                    self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
                    self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_course_ad_video_replace_transcodes_before_write_and_commits_exact_media(self):
        source = b"bounded-video-source"
        await self.seed_ads(1)
        with tempfile.TemporaryDirectory(prefix="admin-pwa-course-ad-video-") as media_root:
            previous_path = Path(media_root) / "private-media-1.mp4"
            previous_path.write_bytes(b"old video")
            with patch.object(marketing, "COURSE_AD_MEDIA_ROOT", media_root), \
                    patch.object(course_ad_service, "COURSE_AD_MEDIA_ROOT", media_root):
                change = {"kind": "course_ad", "ad_id": 1, "operation": "replace_video",
                          "is_active": None, "media_sha256": hashlib.sha256(source).hexdigest(),
                          "media_size": len(source)}
                command = await self.prepare_marketing(change)
                operation = command.operation()
                proof = await self.proof_marketing(command, signed=True)

                def fake_transcode(data, *, raw_ext, media_root):
                    self.assertEqual(data, source)
                    self.assertEqual(raw_ext, ".mp4")
                    filename = "course_ad_pwa_0123456789abcdef0123456789abcdef.mp4"
                    (Path(media_root) / filename).write_bytes(b"transcoded-mp4")
                    return filename

                with patch.object(marketing, "prepare_pwa_course_ad_video_file",
                                  side_effect=fake_transcode) as transcode:
                    result = await self.execute_marketing(
                        command, proof, media_bytes=source, media_content_type="video/mp4",
                    )
                transcode.assert_called_once()

                async with self.sessions() as db:
                    saved = await db.get(CourseAdCreative, 1)
                    self.assertEqual(saved.media_type, "video")
                    self.assertEqual(saved.media_path, "course_ad_pwa_0123456789abcdef0123456789abcdef.mp4")
                    self.assertIsNone(await db.scalar(select(CourseAdCreative.media_blob).where(
                        CourseAdCreative.id == 1)))
                    self.assertEqual((Path(media_root) / saved.media_path).read_bytes(), b"transcoded-mp4")
                    audit = await db.get(AdminPwaCommandAudit, result["command_id"])
                    self.assertEqual(audit.payload_hash, operation_digest(**operation))
                    self.assertNotIn(saved.media_path, audit.result_json)
                self.assertFalse(previous_path.exists())

    async def test_course_ad_video_requires_verified_exact_passkey_before_transcoding(self):
        source = b"video-source"
        await self.seed_ads(1)
        change = {"kind": "course_ad", "ad_id": 1, "operation": "replace_video",
                  "is_active": None, "media_sha256": hashlib.sha256(source).hexdigest(),
                  "media_size": len(source)}
        command = await self.prepare_marketing(change)
        request = marketing.ExecuteMarketing(**command.model_dump(), step_up_id=str(uuid4()))
        with tempfile.TemporaryDirectory(prefix="admin-pwa-course-ad-video-proof-") as media_root:
            with patch.object(marketing, "COURSE_AD_MEDIA_ROOT", media_root), \
                    patch.object(marketing, "prepare_pwa_course_ad_video_file",
                                  side_effect=AssertionError("transcoding must require verified proof")):
                with self.assertRaisesRegex(marketing.CommandError, "step_up_denied"):
                    async with self.sessions() as db:
                        await marketing.execute_marketing(
                            db, session_cookie=fixtures.COOKIE, request=request,
                            settings_obj=self.settings, media_bytes=source,
                            media_content_type="video/mp4",
                        )
            self.assertEqual(list(Path(media_root).iterdir()), [])

    async def test_course_ad_media_payload_rejects_inexact_replace_contract(self):
        with self.assertRaises(ValidationError):
            marketing.PrepareMarketing.model_validate({"change": {
                "kind": "course_ad", "ad_id": 1, "operation": "replace_image",
                "is_active": None, "media_sha256": "0" * 64,
            }})
        with self.assertRaises(ValidationError):
            marketing.PrepareMarketing.model_validate({"change": {
                "kind": "course_ad", "ad_id": 1, "operation": "set_active",
                "is_active": True, "media_sha256": "0" * 64, "media_size": 1,
            }})

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
