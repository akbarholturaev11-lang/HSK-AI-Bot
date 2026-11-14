"""Real PostgreSQL admission and Apple outbox; never contacts a provider."""
import asyncio
import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import select

from app.db.models.admin_pwa_push import AdminPwaPushSubscription
from app.db.models.admin_pwa_push_outbox import AdminPwaPushOutbox
from app.services.admin_pwa_push_dispatch import _claim_one
from app.services.monitoring import catalog
from app.services.monitoring.intake import ingest, parse_batch
from tests.monitoring_chain import PG_URL, admin_client, client_event, pg_sessions


@unittest.skipUnless(PG_URL.startswith("postgresql+asyncpg://"), "requires disposable monitoring PostgreSQL")
class MonitoringPushTests(unittest.IsolatedAsyncioTestCase):
    async def seed_devices(self, sessions, count=2):
        async with sessions() as db, db.begin():
            db.add_all([AdminPwaPushSubscription(
                id=str(uuid4()), user_id=2, endpoint_hash=hashlib.sha256(str(i).encode()).hexdigest(),
                encrypted_payload="synthetic-never-sent", platform="iphone" if i == 0 else "mac",
                created_at=self.now, updated_at=self.now,
            ) for i in range(count)])

    async def rows(self, sessions):
        async with sessions() as db:
            return (await db.scalars(select(AdminPwaPushOutbox))).all()

    async def asyncSetUp(self):
        self.now = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.settings = SimpleNamespace(MONITORING_MODE="all", MONITORING_PUSH_ENABLED=True,
                                       ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUSH_ENABLED=True, admin_id_list=[2002])

    async def submit(self, sessions, *, owner=1, feature="auth_session", failure="api_5xx", site="login", count=1):
        body = {"schema": "diag.v1", "events": [client_event(feature, failure, site) for _ in range(count)]}
        events, rejected = parse_batch(body, platform="android")
        self.assertEqual(rejected, 0)
        async with sessions() as db, db.begin():
            return await ingest(db, owner_user_id=owner, events=events, now=self.now, settings_obj=self.settings)

    async def test_burst_coalesces_and_scope_escalates_once(self):
        async with pg_sessions(PG_URL, users=tuple((i, 2002 if i == 2 else i + 3000) for i in range(1, 7))) as sessions:
            await self.seed_devices(sessions)
            results = await asyncio.gather(*(self.submit(sessions, owner=i, count=20) for i in (1, 3, 4, 5, 6)))
            rows = await self.rows(sessions)
            self.assertEqual(sum(result.accepted for result in results), 100)
            self.assertEqual(len(rows), 2)
            self.assertEqual(len({row.event_key for row in rows}), 1)
            for i in range(1, 6):
                result = await self.submit(sessions, owner=i, feature="lessons", site="lesson_open")
                incident = result.touched[0][0]
                self.assertEqual(incident.severity, "high" if i < 5 else "critical")
                self.assertEqual(len(await self.rows(sessions)), 2 if i < 5 else 4)
            self.assertEqual(incident.last_alert_reason, "escalated")

    async def test_global_cap_allows_reopen_and_preserves_other_sources_priority(self):
        from app.admin_api.pwa_push_outbox import enqueue_automatic_alert
        from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
        from app.db.models.payment import Payment
        from app.services.admin_pwa_push_dispatch import _finish

        async with pg_sessions(PG_URL) as sessions, admin_client(sessions) as admin:
            await self.seed_devices(sessions, count=1)
            normal = (await self.submit(sessions, feature="practice", failure="restore_failed",
                                        site="practice")).touched[0][0]
            self.assertEqual(await self.rows(sessions), [])
            target = {"source": "diagnostic", "source_id": normal.id, "operation": "resolve", "expected_revision": 0}
            self.assertEqual((await admin.post("/api/admin/v1/inbox/triage", json=target)).status_code, 200)
            sites = ("app", "login", "progress", "session_restore", "lesson_open", "lesson_complete", "payment", "onboarding")
            await asyncio.gather(*(self.submit(sessions, owner=1 + i % 2, site=site) for i, site in enumerate(sites)))
            self.assertEqual(len(await self.rows(sessions)), catalog.ALERT_GLOBAL_CAP_PER_HOUR)
            # This same normal-severity incident reopens within its prior cooldown.
            for revision in (0, 2):
                self.now = datetime.now(timezone.utc)
                result = await self.submit(sessions, feature="practice", failure="restore_failed", site="practice")
                self.assertEqual(result.touched[0][0].last_alert_reason, "reopened")
                if revision == 0:
                    target["expected_revision"] = 2
                    self.assertEqual((await admin.post("/api/admin/v1/inbox/triage", json=target)).status_code, 200)
            self.assertEqual(len(await self.rows(sessions)), catalog.ALERT_GLOBAL_CAP_PER_HOUR + 2)
            async with sessions() as db, db.begin():
                payment = Payment(user_id=1, amount=10, currency="USD", plan_type="1_month", payment_method="visa",
                                  payment_status="pending", screenshot_file_id="synthetic", submitted_at=self.now)
                android = AdminPwaNativeReport(user_id=1, deduplication_key="a" * 64, description="fixture",
                    app_version="1.8.40", screen="course", notification_state="sent",
                    created_at=self.now, last_attempt_at=self.now, expires_at=self.now + timedelta(days=1))
                db.add_all([payment, android])
                await db.flush()
                for source, row in (("payment", payment), ("android", android)):
                    await enqueue_automatic_alert(db, settings_obj=self.settings, source=source, source_id=row.id, now=self.now)
            for minutes, source in ((0, "payment"), (1, "android")):
                stamp, worker = self.now + timedelta(minutes=minutes), str(uuid4())
                claimed = await _claim_one(sessions, self.settings, stamp, worker)
                self.assertEqual(claimed[-2:], (source, "important"))
                self.assertEqual(await _finish(sessions, event_id=claimed[0], subscription_id=claimed[1],
                    worker_id=worker, status=201, now=stamp), "accepted")
            self.settings.MONITORING_PUSH_ENABLED = False
            self.assertIsNone(await _claim_one(sessions, self.settings, self.now + timedelta(minutes=2), str(uuid4())))

    async def test_scope_escalates_without_push_and_a_paused_outbox_cannot_send_stale_alerts(self):
        async with pg_sessions(PG_URL, users=tuple((i, 2002 if i == 2 else i + 3000) for i in range(1, 7))) as sessions:
            await self.seed_devices(sessions, count=1)
            self.settings.MONITORING_PUSH_ENABLED = False
            for i in (1, 3, 4, 5, 6):
                result = await self.submit(sessions, owner=i, feature="lessons", site="lesson_open")
            self.assertEqual(result.touched[0][0].severity, "critical")
            self.assertEqual(await self.rows(sessions), [])

            self.settings.MONITORING_PUSH_ENABLED = True
            await self.submit(sessions)
            self.settings.MONITORING_MODE = "off"
            later = self.now + timedelta(hours=1)
            self.assertIsNone(await _claim_one(sessions, self.settings, later, str(uuid4())))
            self.assertEqual([row.state for row in await self.rows(sessions)], ["pending"])
            self.settings.MONITORING_MODE = "all"
            self.assertIsNone(await _claim_one(sessions, self.settings, later, str(uuid4())))
            self.assertEqual([row.state for row in await self.rows(sessions)], ["cancelled"])

    async def test_reopened_epoch_retries_if_enqueue_temporarily_fails(self):
        async with pg_sessions(PG_URL) as sessions, admin_client(sessions) as admin:
            await self.seed_devices(sessions, count=1)
            args = dict(feature="practice", failure="restore_failed", site="practice")
            original = (await self.submit(sessions, **args)).touched[0][0]
            target = {"source": "diagnostic", "source_id": original.id, "operation": "resolve", "expected_revision": 0}
            self.assertEqual((await admin.post("/api/admin/v1/inbox/triage", json=target)).status_code, 200)
            self.now = datetime.now(timezone.utc) + timedelta(seconds=1)
            with patch("app.services.monitoring.alerts.enqueue_automatic_alert",
                       new=AsyncMock(side_effect=RuntimeError("synthetic outage"))):
                await self.submit(sessions, **args)
            self.assertEqual(await self.rows(sessions), [])
            self.now += timedelta(seconds=1)
            await self.submit(sessions, **args)
            await self.submit(sessions, **args)
            rows = await self.rows(sessions)
            self.assertEqual([(r.source_id, r.diagnostic_kind, r.triage_revision) for r in rows],
                             [(original.id, "reopened", 1)])
            claimed = await _claim_one(sessions, self.settings, self.now, str(uuid4()))
            self.assertEqual(claimed[-2:], ("diagnostic", "reopened"))

    async def test_authenticated_android_intake_dispatches_an_encrypted_content_free_alert(self):
        import base64
        import json
        import http_ece
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.api.monitoring_intake import create_monitoring_intake_router
        from app.services.admin_pwa_push_dispatch import dispatch_batch
        from app.services.desktop_auth_service import DesktopAuthService
        from tests.test_pwa_browser_auth import settings as learner_settings

        def b64(value):
            return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

        def point(key):
            return key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

        vapid = ec.generate_private_key(ec.SECP256R1())
        receiver = ec.generate_private_key(ec.SECP256R1())
        storage_key = Fernet.generate_key()
        fernet = Fernet(storage_key)
        auth_secret = bytes(range(16))
        endpoint = "https://web.push.apple.com/synthetic-never-sent"
        sealed = fernet.encrypt(json.dumps({
            "endpoint": endpoint, "keys": {"p256dh": b64(point(receiver)), "auth": b64(auth_secret)}
        }).encode("ascii")).decode("ascii")
        settings = learner_settings(**vars(self.settings),
            ADMIN_PWA_PUSH_SEND_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app",
            ADMIN_PWA_PUSH_STORAGE_KEY=storage_key.decode("ascii"),
            ADMIN_PWA_PUSH_VAPID_PRIVATE_KEY=b64(vapid.private_numbers().private_value.to_bytes(32, "big")),
            ADMIN_PWA_PUSH_VAPID_PUBLIC_KEY=b64(point(vapid)), ADMIN_PWA_PUSH_VAPID_SUBJECT="mailto:ops@example.com")
        captured = []
        def receive_ciphertext(url, **kwargs):
            self.assertEqual(url, endpoint)
            headers = {key.lower(): value for key, value in kwargs["headers"].items()}
            self.assertEqual(headers["content-encoding"], "aes128gcm")
            self.assertTrue(headers["authorization"].lower().startswith("vapid "))
            captured.append(json.loads(http_ece.decrypt(kwargs["data"], private_key=receiver, auth_secret=auth_secret)))
            return SimpleNamespace(status_code=201, text="", headers={})

        async with pg_sessions(PG_URL) as sessions, admin_client(sessions) as admin:
            async with sessions() as db, db.begin():
                db.add(AdminPwaPushSubscription(id=str(uuid4()), user_id=2,
                    endpoint_hash=hashlib.sha256(endpoint.encode()).hexdigest(),
                    encrypted_payload=sealed, platform="iphone", created_at=self.now, updated_at=self.now))
            async with sessions() as db:
                auth = DesktopAuthService(db, settings)
                link = await auth.start_link(platform="android", app_version="1.8.0", installation_key=uuid4().hex * 2)
                await auth.approve_link(display_code=link["display_code"], telegram_id=1001)
                signed = await auth.poll_link(link_request_id=link["link_request_id"], polling_secret=link["polling_secret"])
            app = FastAPI()
            app.include_router(create_monitoring_intake_router(session_factory=sessions, settings_obj=settings))
            headers = {"Authorization": "Bearer " + signed["access_token"]}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app") as client:
                event = client_event("checkout_payments", "api_5xx", "payment", channel="direct")
                reply = await client.post("/api/v3/android/diagnostics", headers=headers,
                                          json={"schema": "diag.v1", "events": [event]})
                self.assertEqual(reply.status_code, 200, reply.text)
                self.assertEqual(reply.json()["accepted"], 1)
            inbox = await admin.post("/api/admin/v1/inbox/list", json={"source": "diagnostic"})
            item, = inbox.json()["items"]
            self.assertEqual((item["feature_code"], item["channels"]), ("checkout_payments", ["direct"]))
            with patch("requests.post", side_effect=receive_ciphertext):
                result = await dispatch_batch(sessions, settings_obj=settings)
            self.assertEqual(result["accepted"], 1)
            self.assertEqual(captured, [{"kind": "important", "source": "diagnostic"}])

    async def test_enqueue_failure_rolls_back_only_alert(self):
        async with pg_sessions(PG_URL) as sessions:
            await self.seed_devices(sessions)
            with patch("app.services.monitoring.alerts.enqueue_automatic_alert",
                       new=AsyncMock(side_effect=RuntimeError("synthetic outage"))):
                result = await self.submit(sessions)
            self.assertEqual(result.accepted, 1)
            self.assertEqual(await self.rows(sessions), [])
            self.assertEqual((await self.submit(sessions)).accepted, 1)
            self.assertEqual(len(await self.rows(sessions)), 2)
