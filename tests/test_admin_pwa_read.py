"""Real-data bounded read projections and browser authorization (no demo rows)."""
import json
import unittest
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event

from app.admin_api.pwa_read import create_admin_pwa_read_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.bot_feedback import BotFeedback
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_progress import CourseProgress
from app.db.models.course_track_state import CourseTrackState
from app.db.models.desktop import DesktopDevice
from app.db.models.payment import Payment
from app.db.models.referral import Referral
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackResponse
from app.db.models.user import User
from tests import test_admin_pwa_payment_review as fixtures


class AdminPwaReadTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def post(self, path, body, *, cookie=fixtures.COOKIE, origin="https://hskai.app"):
        app=FastAPI()
        app.include_router(create_admin_pwa_read_router(settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app",
                               headers={"origin":origin},
                               cookies={ADMIN_PWA_COOKIE_NAME:cookie} if cookie else {}) as client:
            return await client.post("/api/admin/v1/"+path, json=body)

    async def test_payment_list_owner_status_paging_and_no_file_reference(self):
        async with self.sessions() as db:
            payment=await db.get(Payment,self.payment_id)
            payment.user_telegram_id=2002
            db.add(Payment(user_id=2,amount=50,currency="TJS",plan_type="1_month",payment_status="approved"))
            db.add(Payment(user_id=2,amount=5,currency="USD",plan_type="10_days",payment_status="pending"))
            await db.commit()
        response=await self.post("payments/list",{"limit":1})
        self.assertEqual(response.status_code,200,response.text)
        data=response.json()
        self.assertEqual(len(data["items"]),1)
        self.assertEqual(data["items"][0]["currency"],"USD")
        self.assertNotIn("telegram_id",response.text)
        self.assertNotIn("screenshot_file_id",response.text)
        second=(await self.post("payments/list",{"before_id":data["next_before_id"]})).json()
        self.assertEqual(second["items"][0]["user_id"],1)
        self.assertTrue(second["items"][0]["has_receipt"])
        self.assertIsNone(second["next_before_id"])
        self.assertNotIn("synthetic-receipt",str(second))
        approved=(await self.post("payments/list",{"status":"approved"})).json()
        self.assertEqual(len(approved["items"]),1)
        self.assertEqual(approved["items"][0]["user_id"],2)
        for body in ({"status":"all"},{"limit":True},{"before_id":0},{"user_id":1}):
            self.assertEqual((await self.post("payments/list",body)).status_code,400)

    async def test_overall_canonical_population_dates_and_separate_currency_totals(self):
        now=datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add_all([
                Payment(user_id=1, amount=5, currency="USD", plan_type="1_month", payment_status="approved",
                        submitted_at=now-timedelta(days=40), reviewed_at=now),
                Payment(user_id=2, user_telegram_id=2002, amount=50, currency="TJS", plan_type="1_month",
                        payment_status="approved", reviewed_at=now),
                Payment(user_id=1, amount=99, currency="USD", plan_type="1_month", payment_status="approved",
                        submitted_at=now-timedelta(days=45), reviewed_at=now-timedelta(days=40)),
            ])
            await db.commit()
        response=await self.post("statistics", {"platform":"overall", "period":"weekly"})
        self.assertEqual(response.status_code, 200, response.text)
        data=response.json()
        self.assertEqual(data["metrics"]["users_total"], 3)
        self.assertEqual(data["metrics"]["payments_by_status"], {"approved":2,"rejected":0,"pending":1})
        self.assertEqual(data["metrics"]["approved_amounts_by_currency"],
                         [{"currency":"TJS","amount":50},{"currency":"USD","amount":5}])
        self.assertTrue(data["platform_counts_overlap"])
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertNotIn("set-cookie", response.headers)
        response=await self.post("statistics", {"period":"all_time"})
        self.assertEqual(response.json()["metrics"]["approved_amounts_by_currency"][1]["amount"], 104)
        self.assertIsNotNone(response.json()["scope"]["active_accounts_since"])

    async def test_user_pagination_and_numeric_query_are_canonical_only(self):
        ids=[]
        cursor=None
        while True:
            response=await self.post("users/search", {"limit":1,"before_id":cursor})
            self.assertEqual(response.status_code, 200, response.text)
            data=response.json()
            ids.extend(row["user_id"] for row in data["items"])
            cursor=data["next_before_id"]
            if cursor is None:
                break
        self.assertEqual(ids,[101,2,1])
        self.assertEqual((await self.post("users/search", {"query":"2002"})).json()["items"],[])
        data=(await self.post("users/search", {"query":"1"})).json()
        self.assertEqual(data["numeric_query_namespace"],"users.id")
        self.assertEqual(data["items"][0]["user_id"],1)
        self.assertTrue(data["items"][0]["has_pending_payment"])
        self.assertNotIn("telegram_id",data["items"][0])

    async def test_name_search_escapes_wildcards_and_pending_owner_precedence(self):
        async with self.sessions() as db:
            (await db.get(User,1)).full_name="100% match"
            (await db.get(User,2)).full_name="100X match"
            (await db.get(Payment,self.payment_id)).user_telegram_id=2002
            await db.commit()
        data=(await self.post("users/search", {"query":"%"})).json()
        self.assertEqual([row["user_id"] for row in data["items"]],[1])
        data=(await self.post("users/search", {"query":"2"})).json()
        self.assertFalse(data["items"][0]["has_pending_payment"])

    async def test_user_profile_ownership_progress_and_private_field_redaction(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            user = await db.get(User, 1)
            user.status = "active"
            user.payment_status = "approved"
            user.end_date = now + timedelta(days=5)
            # Stale transport metadata cannot steal canonical rows from user 1.
            (await db.get(Payment, self.payment_id)).user_telegram_id = 2002
            db.add_all([
                CourseProgress(user_id=1, level="HSK1", completed_lessons_count=7),
                CourseTrackState(user_id=1, track="hsk30", level="HSK30_1",
                                 completed_lessons_count=3, unlocked_at=now),
                Referral(referrer_user_id=1, invited_user_id=2, referrer_telegram_id=2002,
                         status="active", counts_for_discount=True),
                DesktopDevice(id="private-device-id", user_id=1, telegram_id=2002, platform="android", app_version="qa",
                              installation_key_hash="private-installation-hash", last_seen_at=now),
                DesktopDevice(id="revoked-device", user_id=1, platform="android", app_version="qa",
                              installation_key_hash="private-revoked-hash", revoked_at=now),
                BotFeedback(user_id=1, telegram_id=2002, status="completed", disliked_text="private-text"),
            ])
            await db.commit()
        response = await self.post("users/detail", {"user_id": 1})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["user"]["user_id"], 1)
        self.assertIsNotNone(data["user"]["access_expires_at"])
        self.assertEqual(data["course"]["progress"]["completed_lessons"], 7)
        self.assertEqual(data["course"]["tracks"][0]["completed_lessons"], 3)
        self.assertEqual(data["referral"], {"invited_total": 1, "invited_active": 1, "discount_qualified": 1})
        self.assertEqual((data["devices"][0]["total"], data["devices"][0]["linked"]), (2, 1))
        self.assertEqual(data["feedback_counts"], {"bot": 1, "release": 0})
        self.assertEqual(data["payments"]["items"][0]["payment_id"], self.payment_id)
        for value in ("telegram_id", "installation_key_hash", "private-installation-hash",
                      "private-device-id", "private-text", "synthetic-receipt", "screenshot_file_id"):
            self.assertNotIn(value, response.text)
        other = (await self.post("users/detail", {"user_id": 2})).json()
        self.assertEqual(other["devices"], [])
        self.assertEqual(other["payments"]["items"], [])
        self.assertEqual(other["feedback_counts"]["bot"], 0)
        self.assertEqual(other["referral"]["invited_total"], 0)
        self.assertIsNone(other["course"]["progress"])
        self.assertEqual(response.headers["cache-control"], "no-store")

    async def test_user_payment_history_pages_and_legacy_identity_never_guesses_account_id(self):
        async with self.sessions() as db:
            db.add_all([
                Payment(user_id=None, user_telegram_id=2, amount=99, currency="USD", plan_type="1_month"),
                Payment(user_id=None, user_telegram_id=2002, amount=5, currency="USD", plan_type="1_month"),
                Payment(user_id=2, user_telegram_id=9001, amount=7, currency="TJS", plan_type="1_month"),
            ])
            await db.commit()
        first = (await self.post("users/payments", {"user_id": 2, "limit": 1})).json()
        self.assertEqual(first["items"][0]["amount"], 7)
        second = (await self.post("users/payments", {"user_id": 2, "limit": 1,
                                                   "before_id": first["next_before_id"]})).json()
        self.assertEqual(second["items"][0]["amount"], 5)
        self.assertIsNone(second["next_before_id"])
        for path in ("users/detail", "users/payments"):
            self.assertEqual((await self.post(path, {"user_id": 2002})).status_code, 404)
            for body in ({}, {"user_id": True}, {"user_id": "1"}, {"user_id": 0},
                         {"user_id": 1, "telegram_id": 2002}):
                self.assertEqual((await self.post(path, body)).status_code, 400)

    async def test_feedback_sources_keep_identity_campaign_and_attachment_boundaries(self):
        now=datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add(ReleaseFeedbackCampaign(id=1,title="synthetic QA campaign",send_at=now))
            await db.flush()
            db.add(ReleaseFeedbackResponse(campaign_id=1,user_telegram_id=2002,rating=4,
                comment_text="synthetic QA feedback",attachment_file_id="private-synthetic-file-reference"))
            db.add(BotFeedback(user_id=999,telegram_id=2002,status="completed",disliked_text="retained orphan",
                disliked_attachment_file_id="private-synthetic-file-reference"))
            db.add(BotFeedback(user_id=1,telegram_id=1001,status="completed",disliked_code="price"))
            await db.commit()
        release=await self.post("feedback/list", {"source":"release","user_id":2})
        self.assertEqual(release.status_code,200,release.text)
        item=release.json()["items"][0]
        self.assertEqual((item["campaign_id"],item["user_id"],item["rating"]),(1,2,4))
        self.assertTrue(item["has_attachment"])
        self.assertNotIn("private-synthetic-file-reference", release.text)
        bot=(await self.post("feedback/list", {"source":"bot","user_id":2})).json()
        self.assertEqual(bot["items"],[])
        bot=(await self.post("feedback/list", {"source":"bot","limit":1})).json()
        self.assertEqual(bot["items"][0]["user_id"],1)
        second=(await self.post("feedback/list", {"source":"bot","before_id":bot["next_before_id"]})).json()
        self.assertIsNone(second["items"][0]["user_id"])
        self.assertIn("android_bug_reports",second["unavailable_sources"])

    async def test_native_platforms_reuse_real_services_without_summing_overlapping_users(self):
        now=datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add(DesktopDevice(id="qa-android-device",user_id=1,platform="android",
                installation_key_hash="f"*64,app_version="1.0.0",first_open_at=now))
            for platform in ("macos","windows"):
                db.add(CourseMiniAppEvent(user_id=1,event_name="desktop_app_opened",source="desktop",
                    payload_json=json.dumps({"platform":platform,"device_id":platform}),created_at=now))
            db.add(CourseMiniAppEvent(user_id=1,event_name="android_app_opened",source="android",
                payload_json=json.dumps({"device_id":"qa-android-device"}),created_at=now))
            await db.commit()
        for platform in ("macos","windows"):
            response=await self.post("statistics", {"platform":platform,"period":"weekly"})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()["metrics"]["active_users_30d"],1)
            self.assertFalse(response.json()["scope"]["period_filter_applied"])
        response=await self.post("statistics", {"platform":"android"})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["metrics"]["registry"]["installed_users"],1)
        self.assertEqual(response.json()["metrics"]["active"]["mau"],1)
        self.assertEqual((await self.post("statistics",{})).json()["metrics"]["users_total"],3)

    async def test_unmeasured_platforms_are_unavailable_instead_of_fake_zero(self):
        for platform in ("telegram","iphone_pwa"):
            response=await self.post("statistics",{"platform":platform})
            self.assertFalse(response.json()["available"])
            self.assertIsNone(response.json()["metrics"])

    async def test_flag_csrf_cookie_revocation_and_strict_bounds(self):
        paths=(("payments/list",{}),("statistics",{}),("users/search",{}),("feedback/list",{"source":"bot"}),
               ("users/detail",{"user_id":1}),("users/payments",{"user_id":1}))
        for path,body in paths:
            self.assertEqual((await self.post(path,body,cookie=None)).status_code,401)
            self.assertEqual((await self.post(path,body,cookie="T"*64)).status_code,401)
            self.assertEqual((await self.post(path,body,origin="https://evil.example")).status_code,403)
            self.settings.ADMIN_PWA_ENABLED=False
            self.assertEqual((await self.post(path,body)).status_code,404)
            self.settings.ADMIN_PWA_ENABLED=True
        for path,body in (("users/search",{"limit":101}),("users/search",{"limit":True}),
                          ("users/search",{"query":"x"*81}),("users/search",{"before_id":"1"}),
                          ("statistics",{"period":"daily"}),("statistics",{"platform":"other"}),
                          ("feedback/list",{"source":"android"}),("feedback/list",{"source":"bot","sql":"select 1"})):
            self.assertEqual((await self.post(path,body)).status_code,400)
        await self.change(AdminPwaSession,revoked_at=datetime.now(timezone.utc))
        for path,body in paths:
            self.assertEqual((await self.post(path,body)).status_code,401)

    async def test_projection_sql_never_writes_and_routes_are_mounted(self):
        statements=[]
        def observe(conn,cursor,statement,parameters,context,many):
            statements.append(statement.lstrip().split()[0].upper())
        event.listen(self.engine.sync_engine,"before_cursor_execute",observe)
        try:
            for path,body in (("statistics",{}),("users/search",{}),("feedback/list",{"source":"bot"}),
                              ("users/detail",{"user_id":1}),("users/payments",{"user_id":1})):
                response=await self.post(path,body)
                self.assertEqual(response.status_code,200,response.text)
        finally:
            event.remove(self.engine.sync_engine,"before_cursor_execute",observe)
        self.assertTrue(statements)
        self.assertTrue(all(value=="SELECT" for value in statements),statements)
        from tests.test_main_imports import MainModuleImportTests
        main=MainModuleImportTests._import_main()
        paths=MainModuleImportTests._paths(main.app.routes)
        for path in ("statistics","users/search","feedback/list","users/detail","users/payments"):
            self.assertIn("/api/admin/v1/"+path,paths)
