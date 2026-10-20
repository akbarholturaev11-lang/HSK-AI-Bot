"""Provider-first Telegram attachment preserves canonical data and AI limits."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.api.android_course import create_android_course_router
from app.api.desktop_course import create_desktop_course_router
from app.api.desktop_rating import create_desktop_rating_router
from app.db.models.ai_usage import AIUsageBudget, AIUsageEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_track_state import CourseTrackState
from app.db.models.desktop import DesktopSession
from app.db.models.payment import Payment
from app.db.models.referral import Referral
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.account_identity import owner_clause
from app.services.desktop_auth_service import DesktopAuthService
from app.services.study_miniapp_service import StudyMiniAppService
from app.services.voice_practice_service import VoicePracticeService
from tests import test_native_account_acceptance as acceptance
from tests.test_native_oauth_api import _Base


class TelegramTransportOwnershipTests(_Base):
    async def test_newly_attached_telegram_reads_prelink_budget_and_voice_limits(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            user = User(id=3, telegram_id=None, full_name="Provider learner")
            session.add(user)
            await session.flush()
            budget = await AIUsageBudgetService(session).create_fixed_budget(
                telegram_id=user, plan_type="pro_trial_7_days", amount=2,
                currency="usd", total_budget_usd=2,
                starts_at=now - timedelta(minutes=1), ends_at=now + timedelta(days=7),
            )
            budget.segment_1_spent_usd = 0.5
            voice = VoicePracticeSession(
                id="provider-first-voice", user_id=3, user_telegram_id=None,
                role="friend", level="hsk1", language="uz", voice="female",
                turn_count=1,
            )
            session.add_all([voice, AIUsageEvent(
                user_id=3, user_telegram_id=None, budget_id=budget.id,
                source="voice_practice_pronounce", model="fixture", cost_usd=0.5,
            )])
            await session.flush()
            # The attachment changes identity only; historical rows retain
            # their canonical owner and their original optional TG metadata.
            user.telegram_id = 9009
            await session.commit()
            found = await AIUsageBudgetService(session).get_active_budget(9009)
            self.assertIsNotNone(found, "Telegram must see the existing native budget")
            self.assertEqual((found.id, found.segment_1_spent_usd), (budget.id, 0.5))
            service = VoicePracticeService(session)
            self.assertEqual((await service._get_active_session(9009, voice.id)).id, voice.id)
            self.assertEqual(await service._session_count(9009, today_only=True), 1)
            self.assertEqual(await service._pronounce_count_today(9009), 1)
            self.assertEqual(await service._pronounce_count_today(1002), 0)

    async def test_real_telegram_id_never_authorizes_another_canonical_owners_metadata(self):
        async with self.sessions() as session:
            session.add_all([
                VoicePracticeSession(id="foreign-canonical", user_id=2,
                    user_telegram_id=1001, role="friend", level="hsk1",
                    language="uz", voice="female"),
                VoicePracticeSession(id="legacy-own", user_id=None,
                    user_telegram_id=1001, role="friend", level="hsk1",
                    language="uz", voice="female"),
                VoicePracticeSession(id="canonical-own", user_id=1,
                    user_telegram_id=None, role="friend", level="hsk1",
                    language="uz", voice="female"),
            ])
            await session.commit()
            rows = (await session.execute(select(VoicePracticeSession.id).where(
                owner_clause(VoicePracticeSession, 1001)))).scalars().all()
            self.assertCountEqual(rows, ["legacy-own", "canonical-own"])
            # Integer arguments remain real TG IDs, never users.id.
            self.assertEqual((await session.execute(select(VoicePracticeSession.id).where(
                owner_clause(VoicePracticeSession, 1)))).scalars().all(), [])


class ProviderFirstTelegramAcceptanceTests(_Base):
    settings_overrides = acceptance.NativeAccountAcceptanceTests.settings_overrides
    _signin = acceptance.NativeAccountAcceptanceTests._signin

    async def asyncSetUp(self):
        await super().asyncSetUp()
        app = self.client._transport.app
        for factory in (create_android_course_router, create_desktop_course_router,
                        create_desktop_rating_router):
            app.include_router(factory(session_factory=self.sessions, settings_obj=self.settings))

    async def _tokens(self, provider, *, platform, key):
        started, response = await self._signin(provider, platform=platform, key=key,
                                               subject="provider-first-" + provider)
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as session:
            tokens = await DesktopAuthService(session, self.settings).poll_link(
                link_request_id=started["link_request_id"], polling_secret=started["polling_secret"])
            actor = await DesktopAuthService(session, self.settings).authenticate(tokens["access_token"])
            return actor.user.id, {"Authorization": "Bearer " + tokens["access_token"]}

    async def _snapshot(self, uid):
        clauses = {
            User: User.id == uid, Payment: Payment.user_id == uid,
            AIUsageBudget: AIUsageBudget.user_id == uid,
            AIUsageEvent: AIUsageEvent.user_id == uid,
            CourseMiniAppProfile: CourseMiniAppProfile.user_id == uid,
            CourseProgress: CourseProgress.user_id == uid,
            CourseTrackState: CourseTrackState.user_id == uid,
            VoicePracticeSession: VoicePracticeSession.user_id == uid,
            Referral: Referral.invited_user_id == uid,
        }
        async with self.sessions() as session:
            result = {}
            for model, clause in clauses.items():
                rows = (await session.scalars(select(model).where(clause).order_by(model.id))).all()
                result[model.__tablename__] = [
                    {c.name: getattr(row, c.name) for c in model.__table__.columns
                     if not (model is User and c.name == "telegram_id")}
                    for row in rows
                ]
            result["user_count"] = await session.scalar(select(func.count(User.id)))
            result["session_count"] = await session.scalar(select(func.count(DesktopSession.id)))
            return result

    async def test_google_and_apple_attach_telegram_without_changing_paid_learning_or_voice_state(self):
        for provider, keys, tid in (("google", ("g", "w", "m"), 9009),
                                    ("apple", ("a", "b", "c"), 9010)):
            with self.subTest(provider=provider):
                uid, headers = await self._tokens(provider, platform="android", key=keys[0])
                now = datetime.now(timezone.utc)
                async with self.sessions() as session:
                    user = await session.get(User, uid)
                    self.assertIsNone(user.telegram_id)
                    user.status, user.payment_status, user.level = "active", "approved", "hsk1"
                    user.start_date, user.end_date = now - timedelta(days=2), now + timedelta(days=28)
                    user.payment_preview_available = False
                    user.trial_used = True
                    session.add(CourseMiniAppProfile(user_id=uid, xp_total=60))
                    pro = Payment(user_id=uid, user_telegram_id=None, plan_type="1_month",
                                  amount=95, currency="TJS", payment_status="approved", reviewed_at=now)
                    hsk = Payment(user_id=uid, user_telegram_id=None, plan_type="hsk30_unlock",
                                  amount=10, currency="TJS", payment_status="approved", reviewed_at=now)
                    session.add_all([pro, hsk])
                    await session.flush()
                    session.add_all([
                        CourseTrackState(user_id=uid, track="hsk30", level="nhsk1",
                                         unlocked_at=now, unlock_payment_id=hsk.id),
                        Referral(referrer_user_id=1, invited_user_id=uid,
                                 referrer_telegram_id=1001, invited_user_telegram_id=None,
                                 status="active", bonus_granted=True),
                        VoicePracticeSession(id="acceptance-" + provider, user_id=uid,
                            user_telegram_id=None, role="friend", level="hsk1",
                            language="uz", voice="female", turn_count=1),
                    ])
                    budget = await AIUsageBudgetService(session).create_fixed_budget(
                        telegram_id=user, plan_type="1_month", amount=95, currency="TJS",
                        total_budget_usd=5, starts_at=user.start_date, ends_at=user.end_date)
                    budget.segment_1_spent_usd = 0.25
                    await session.commit()
                completed = await self.client.post("/api/v3/android/course/complete", headers=headers,
                    json={"lesson_order": 1, "event_id": "provider-first-" + provider, "mistakes": []})
                self.assertEqual(completed.status_code, 200, completed.text)
                before = await self._snapshot(uid)
                started_response = await self.client.post("/api/v3/native-auth/identities/link/start",
                    headers=headers, json=self._start_body(provider="telegram", mode="telegram_approval",
                                                          installation_key=keys[0] * 48))
                self.assertEqual(started_response.status_code, 200, started_response.text)
                started = started_response.json()
                self.assertIn("start=tg_identity_", started["authorize_url"])
                self.assertTrue({"access_token", "refresh_token", "display_code"}.isdisjoint(started))
                async with self.sessions() as session:
                    auth = DesktopAuthService(session, self.settings)
                    preview = await auth.telegram_identity_confirmation(
                        link_request_id=started["link_request_id"], telegram_id=tid)
                    self.assertEqual(preview["user_id"], uid)
                    approved = await auth.approve_telegram_identity(
                        link_request_id=started["link_request_id"], telegram_id=tid)
                    self.assertEqual(approved["status"], "linked")
                polled = await self.client.post("/api/v3/native-auth/identities/link/status",
                    headers=headers, json={k: started[k] for k in ("link_request_id", "polling_secret")})
                self.assertEqual(polled.status_code, 200, polled.text)
                self.assertEqual(polled.json()["status"], "linked")
                self.assertTrue({"access_token", "refresh_token"}.isdisjoint(polled.json()))
                self.assertEqual(await self._snapshot(uid), before)
                methods = await self.client.get("/api/v3/native-auth/identities", headers=headers)
                self.assertTrue(methods.json()["telegram_linked"])
                async with self.sessions() as session:
                    user = await session.get(User, uid)
                    self.assertEqual(user.telegram_id, tid)
                    self.assertEqual((await AIUsageBudgetService(session).get_active_budget(tid)).id, budget.id)
                    voice = await VoicePracticeService(session)._get_active_session(tid, "acceptance-" + provider)
                    self.assertEqual(voice.user_id, uid)
                    miniapp = await StudyMiniAppService(session).get_profile_payload(tid)
                    self.assertTrue(miniapp["subscription"]["is_paid"])
                    self.assertEqual(miniapp["stats"]["completed_lessons"], 1)
                    self.assertGreater(miniapp["stats"]["xp"], 60)
                for platform, key in zip(("windows", "macos"), keys[1:]):
                    desktop_uid, desktop_headers = await self._tokens(provider, platform=platform, key=key)
                    self.assertEqual(desktop_uid, uid)
                    course = await self.client.get("/api/v3/desktop/course/map", headers=desktop_headers)
                    self.assertEqual(course.status_code, 200, course.text)
                    self.assertTrue(course.json()["user"]["is_paid"])
                    self.assertEqual(course.json()["progress"]["xp"], miniapp["stats"]["xp"])
                    self.assertEqual(course.json()["progress"]["completed"], 1)
