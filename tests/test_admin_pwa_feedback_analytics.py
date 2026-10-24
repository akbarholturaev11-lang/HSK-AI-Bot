"""Bounded, first-party-only feedback category aggregation and export."""
import csv
import io
import unittest
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select

from app.admin_api.pwa_feedback_analytics import (
    FeedbackAnalyticsRequest, create_admin_pwa_feedback_analytics_router, feedback_analytics,
)
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.bot_feedback import BotFeedback
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackResponse
from tests import test_admin_pwa_payment_review as fixtures


class FeedbackAnalyticsTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def seed(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add(ReleaseFeedbackCampaign(
                id=1, title="Synthetic campaign", feature_key="general",
                status="sent", send_at=now-timedelta(days=2)))
            db.add_all([
                BotFeedback(user_id=1, telegram_id=1001, status="completed",
                            disliked_code="price", disliked_text="PRIVATE: example@test.invalid =CMD()",
                            created_at=now, completed_at=now-timedelta(days=1)),
                BotFeedback(user_id=1, telegram_id=1001, status="completed",
                            disliked_code="=DANGEROUS", disliked_text="PRIVATE-token-123",
                            created_at=now, completed_at=now-timedelta(days=2)),
                BotFeedback(user_id=1, telegram_id=1001, status="pending",
                            disliked_code="limits", created_at=now),
                BotFeedback(user_id=1, telegram_id=1001, status="completed",
                            disliked_code="limits", created_at=now-timedelta(days=46),
                            completed_at=now-timedelta(days=46)),
                ReleaseFeedbackResponse(campaign_id=1, user_telegram_id=1001,
                                        rating=1, comment_text="PRIVATE-release", completed_at=now-timedelta(hours=1)),
                ReleaseFeedbackResponse(campaign_id=1, user_telegram_id=2002,
                                        rating=5, comment_text="PRIVATE-user", completed_at=now-timedelta(days=3)),
                AdminPwaNativeReport(
                    user_id=1, deduplication_key="q"*64, description="PRIVATE android issue",
                    app_version="secret-version", screen="private-screen",
                    notification_state="sent", created_at=now-timedelta(days=1),
                    last_attempt_at=now, expires_at=now+timedelta(days=15)),
                AdminPwaNativeReport(
                    user_id=1, deduplication_key="w"*64, description="PRIVATE expired bug",
                    app_version="secret-version", screen="private-screen",
                    notification_state="sent", created_at=now-timedelta(days=3),
                    last_attempt_at=now, expires_at=now-timedelta(seconds=1)),
            ])
            await db.commit()

    async def post(self, endpoint, payload, *, cookie=fixtures.COOKIE, headers=None):
        app=FastAPI()
        app.include_router(create_admin_pwa_feedback_analytics_router(
            settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app),base_url="https://hskai.app",
                               headers={"origin":"https://hskai.app"},
                               cookies={ADMIN_PWA_COOKIE_NAME:cookie} if cookie else {}) as client:
            return await client.post("/api/admin/v1/feedback/categories"+endpoint,
                                     json=payload,headers=headers)

    async def test_three_real_source_grains_with_no_raw_data_or_guessed_categories(self):
        await self.seed()
        response=await self.post("",{"period":"weekly","source":"all"})
        self.assertEqual(response.status_code,200,response.text)
        data=response.json()
        self.assertEqual(data["schema"],"hskai_feedback_categories_v1")
        self.assertEqual(data["coverage"],"most_recent_source_records_in_window")
        self.assertFalse(data["historical_android_reports_complete"])
        by_source={row["source"]:row for row in data["sources"]}
        self.assertEqual(by_source["bot"]["categories"],[
            {"category":"price","count":1},{"category":"unclassified","count":1}])
        self.assertEqual(by_source["release"]["categories"],[
            {"category":"low_rating","count":1},{"category":"positive_rating","count":1}])
        self.assertEqual(by_source["android"]["categories"],[
            {"category":"reported_issue","count":1}])
        self.assertTrue(all(not row["truncated"] for row in by_source.values()))
        self.assertEqual(response.headers["cache-control"],"no-store")
        for private in ("PRIVATE", "test.invalid", "secret-version", "telegram_id",
                        "attachment_bytes", "user_id", "=CMD()", "=DANGEROUS"):
            self.assertNotIn(private,response.text)

    async def test_capped_latest_only_marks_partial_instead_of_claiming_full_totals(self):
        now=datetime.now(timezone.utc)
        async with self.sessions() as db:
            for i, code in enumerate(("price","limits","unclear","pace")):
                db.add(BotFeedback(user_id=1,telegram_id=1001,status="completed",
                    disliked_code=code,created_at=now,completed_at=now-timedelta(minutes=i+1)))
            await db.commit()
        async with self.sessions() as db:
            result=await feedback_analytics(db,FeedbackAnalyticsRequest(source="bot"),
                                            now=now,max_source_rows=2)
        self.assertEqual(result["sources"][0]["records_scanned"],2)
        self.assertTrue(result["sources"][0]["truncated"])
        self.assertEqual(result["sources"][0]["categories"],[
            {"category":"limits","count":1},{"category":"price","count":1}])
        self.assertEqual(sum(r["count"] for r in result["sources"][0]["categories"]),2)

    async def test_download_json_csv_use_fixed_labels_only_and_no_formula_input(self):
        await self.seed()
        for fmt in ("json","csv"):
            response=await self.post("/export",{"format":fmt,"period":"monthly","source":"all"})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.headers["cache-control"],"no-store")
            self.assertIn(f"hskai-feedback-categories-all-monthly-",response.headers["content-disposition"])
            self.assertLess(len(response.content),128*1024)
            for text in ("PRIVATE", "test.invalid", "=CMD()", "=DANGEROUS", "secret-version",
                         "telegram_id","user_id","attachment_bytes"):
                self.assertNotIn(text,response.text)
            if fmt=="json":
                self.assertEqual(response.json()["schema"],"hskai_feedback_categories_v1")
            else:
                rows=list(csv.DictReader(io.StringIO(response.text)))
                self.assertTrue(rows)
                self.assertIn(("bot","price"),{(r["source"],r["category"]) for r in rows})
                self.assertTrue(all(not value.startswith(("=","+","-","@")) for row in rows
                                    for value in row.values() if isinstance(value,str)))

    async def test_auth_csrf_payload_and_rollout_fail_closed(self):
        await self.seed()
        query={"period":"weekly","source":"bot"}
        for invalid in ({"period":"all_time"}, {"source":"payment"}, {"user_id":1},
                        {"period":7}, {"source":"bot","format":"csv"}):
            self.assertEqual((await self.post("",invalid)).status_code,400)
        self.assertEqual((await self.post("/export",query)).status_code,400)
        self.assertEqual((await self.post("",query,cookie="")).status_code,401)
        self.assertEqual((await self.post("",query,cookie="forged")).status_code,401)
        self.assertEqual((await self.post("",query,headers={"origin":"https://evil.invalid"})).status_code,403)
        self.assertEqual((await self.post("",query,headers={"sec-fetch-site":"cross-site"})).status_code,403)
        async with self.sessions() as db:
            record=await db.get(AdminPwaSession,self.session_id)
            record.auth_method="google_telegram"
            await db.commit()
        self.assertEqual((await self.post("",query)).status_code,401)
        self.assertEqual((await self.post("/export",{**query,"format":"csv"})).status_code,401)
        async with self.sessions() as db:
            record=await db.get(AdminPwaSession,self.session_id)
            record.auth_method="webauthn"
            await db.commit()
        self.settings.admin_id_list=[]
        self.assertEqual((await self.post("",query)).status_code,401)
        self.settings.ADMIN_PWA_ENABLED=False
        self.assertEqual((await self.post("",query)).status_code,404)
        self.assertEqual((await self.post("/export",{**query,"format":"json"})).status_code,404)

    async def test_service_uses_projection_only_and_no_sql_mutations(self):
        await self.seed()
        sql=[]
        def record(conn,cursor,statement,parameters,context,many):
            sql.append(statement.lower())
        event.listen(self.engine.sync_engine,"before_cursor_execute",record)
        try:
            result=await self.post("",{"source":"bot"})
        finally:
            event.remove(self.engine.sync_engine,"before_cursor_execute",record)
        self.assertEqual(result.status_code,200,result.text)
        self.assertTrue(sql)
        self.assertFalse(any(x.lstrip().startswith(("insert ","update ","delete ")) for x in sql))
        self.assertFalse(any("disliked_text" in x or "telegram_id" in x or "attachment_bytes" in x
                             for x in sql),sql)
