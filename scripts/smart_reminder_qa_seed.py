"""Explicit operator-only one-time empty QA initialization and synthetic seed.

No HTTP mutation, token output, real data import, deletion/reset or auto retry.
"""
import argparse
import asyncio
from datetime import datetime, time, timedelta, timezone
import hashlib
import json
import os

from scripts import smart_reminder_qa_guard as guard


async def seed(sessions, settings, *, now, until, refresh_tokens):
    from sqlalchemy import func, select, text
    from app.db.models.user import User
    from app.db.models.desktop import DesktopDevice, DesktopSession
    from app.db.models.android_push import AndroidPushToken
    from app.db.models.course_progress import CourseProgress
    from app.db.models.course_miniapp_profile import CourseMiniAppProfile
    from app.db.models.course_miniapp_event import CourseMiniAppEvent
    from app.db.models.course_xp_event import CourseXpEvent
    from app.db.models.smart_reminder import SmartReminderPreference, SmartReminderConsent, SmartReminderCapability, SmartReminderRouting, SmartReminderJob
    from app.services.desktop_auth_service import DesktopAuthService
    from app.services.smart_reminder_android import SmartReminderAndroidService
    from app.services.smart_reminder_shadow_queue import day_window
    from app.services.smart_reminder_telegram import _android_inventory
    from app.smart_reminder_qa import qa_calibration

    if now.tzinfo is None or until.tzinfo is None or not now < until <= now+timedelta(days=1):
        raise RuntimeError("smart_qa_finite_seed_window_required")
    start,end = day_window("Etc/UTC",now.date().isoformat())
    async with sessions.begin() as session:
        if session.bind.dialect.name == "postgresql":
            await session.execute(text("SELECT pg_advisory_xact_lock(1729492030)"))
        if await session.scalar(select(func.count()).select_from(User)):
            raise RuntimeError("smart_qa_seed_refuses_existing_users")
        session.add(User(id=guard.USER_ID,telegram_id=None,full_name=guard.FIXTURE_VERSION,level="hsk1",
            status="active",payment_status="approved",end_date=until,created_at=now))
        await session.flush()
        session.add(CourseProgress(user_id=guard.USER_ID,level="hsk1",completed_lessons_count=4,
            reminder_enabled=False,reminder_tz_offset=0))
        session.add(CourseMiniAppProfile(user_id=guard.USER_ID,daily_goal_xp=20,timezone_offset_minutes=0))
        session.add(SmartReminderPreference(user_id=guard.USER_ID,master_enabled=True,revision=2,grant_epoch=1,
            migration_version=1,legacy_time_local=time(0),
            timezone_name="Etc/UTC",action_source=guard.FIXTURE_VERSION,action_at=now))
        for device in guard.DEVICE_IDS:
            session.add(DesktopDevice(id=device,user_id=guard.USER_ID,platform="android",app_version=guard.APP_VERSION,
                installation_key_hash=hashlib.sha256((guard.FIXTURE_VERSION+device).encode()).hexdigest(),created_at=now))
        await session.flush()
        auth=DesktopAuthService(session,settings)
        for index,device in enumerate(guard.DEVICE_IDS):
            session.add(DesktopSession(id=guard.SESSION_IDS[index],device_id=device,
                refresh_token_hash=auth._hash("refresh",refresh_tokens[index]),expires_at=until,created_at=now))
            session.add(SmartReminderCapability(user_id=guard.USER_ID,device_id=device,generation=1,protocol_version=1,
                autonomous_study_disabled=True,study_notifications_allowed=True,observed_at=now,expires_at=until))
            session.add(SmartReminderConsent(user_id=guard.USER_ID,channel="android",source_key="intent:android:"+device,
                device_id=device,state="on",source="user_intent"))
            session.add(AndroidPushToken(device_id=device,token="synthetic-no-provider-"+device,timezone_name="Etc/UTC",
                notifications_allowed=True,study_reminders_enabled=False))
        for order in range(1,5):
            # Match the fixture's midnight personal time. A later historical
            # hour would correctly veto midnight under the personal cadence.
            accepted=(now-timedelta(days=5-order)).replace(hour=0,minute=0,second=0,microsecond=0)
            session.add(CourseXpEvent(user_id=guard.USER_ID,activity_type="lesson",activity_ref=f"v3-part:hsk1:{order}:complete",
                xp=1,activity_date=accepted.date(),week_start=accepted.date(),created_at=accepted))
            session.add(CourseMiniAppEvent(user_id=guard.USER_ID,level="hsk1",source="course_v3",event_name="lesson_completed",
                lesson_order=order,session_id=guard.FIXTURE_VERSION,created_at=accepted,payload_json=json.dumps({"total":10,"score":8})))
        await session.flush()
        inventory,deadline=await _android_inventory(session,guard.USER_ID,now)
        if inventory is None or deadline is None or deadline <= now:
            raise RuntimeError("smart_qa_seed_inventory_invalid")
        session.add(SmartReminderRouting(user_id=guard.USER_ID,state="held",generation=1,preference_revision=2,grant_epoch=1,
            telegram_binding="a"*64,inventory_sha256=inventory,held_at=now,verified_at=now,verified_until=until,
            evidence_sha256=hashlib.sha256(guard.FIXTURE_VERSION.encode()).hexdigest()))
        version=SmartReminderAndroidService(session,calibration=qa_calibration()).policy_version
        # Finite operator fixture across a UTC midnight, never a runtime producer.
        for index,job_id in enumerate(guard.JOB_IDS):
            day=now.date()+timedelta(days=index)
            lower,upper=day_window("Etc/UTC",day.isoformat())
            if lower >= until: continue
            session.add(SmartReminderJob(id=job_id,user_id=guard.USER_ID,local_day=day,timezone_name="Etc/UTC",
                day_start_utc=lower,day_end_utc=upper,scheduled_at=lower,expires_at=min(until,upper),
                state="pending",policy_version=version,preference_revision=2,grant_epoch=1,course_key="hsk1",lesson_order=5,
                selected_channel="android",selected_device_id=guard.DEVICE_IDS[0]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initialize-empty",action="store_true",required=True)
    parser.parse_args()
    os.environ["DATABASE_URL"]=guard.validate(dict(os.environ),seed=True)
    from scripts import qa_standalone_bootstrap
    qa_standalone_bootstrap.main()
    from app.config import settings
    from app.db.session import async_session_maker,engine
    try:
        until=datetime.fromisoformat(os.environ["HSK_SMART_QA_UNTIL"].replace("Z","+00:00"))
        async def run():
            try:
                await seed(async_session_maker,settings,now=datetime.now(timezone.utc),until=until,
                    refresh_tokens=[os.environ["HSK_SMART_QA_REFRESH_"+str(n)] for n in (1,2)])
            finally:
                await engine.dispose()
        asyncio.run(run())
    except Exception:
        raise RuntimeError("smart_qa_seed_failed_quarantine_no_retry") from None
    print("SMART_QA_SYNTHETIC_FIXTURE_READY; NO_IMPORTED_DATA; NO_PROVIDER")


if __name__ == "__main__": main()
