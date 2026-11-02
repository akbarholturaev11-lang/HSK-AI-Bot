"""Observed first-ready cohorts only; no assignment, sender or model decision."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import case, delete, or_, select, text

from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.smart_reminder import SmartReminderJob
from app.db.models.smart_reminder_analysis import SmartReminderBaselineMember, SmartReminderBaselineTotal
from app.db.models.user import User
from app.services.course_levels import legacy_content_levels, hsk30_content_levels
from app.services.smart_reminder_analysis import MAX_BATCH, RAW_RETENTION, oldest_month
from app.services.smart_reminder_coordination import _owner
from app.services.motivation_reminder_service import D1_RECOVERY_ASSIGNED_EVENT, D1_RECOVERY_EXPERIMENT, D1_RECOVERY_HOLDOUT
from app.services.smart_reminder_policy import _aware_utc, day_window
from app.services.smart_reminder_policy_context import (
    MAX_POLICY_ROWS, TERMINAL_EVENTS, VerifiedLearningEvidence, _LESSON_REF,
    corroborate_learning, read_scored_activity,
)
from app.services.smart_reminder_preferences import _utc
from app.services.smart_reminder_shadow_queue import QUEUE_VERSION

MEMBER=SmartReminderBaselineMember.__table__
TOTAL=SmartReminderBaselineTotal.__table__
VERSION="smart-baseline-calendar-v1"
LEVELS=(*legacy_content_levels(),*hsk30_content_levels())


def windows(entered_at,zone_name):
    at=_aware_utc(entered_at)
    day=at.astimezone(ZoneInfo(zone_name)).date()
    start,end=day_window(zone_name,day.isoformat())
    if not start<=at<end: raise ValueError("Invalid baseline calendar entry")
    d7_start,d7_end=day_window(zone_name,(day+timedelta(days=7)).isoformat())
    return d7_start,d7_end


async def enroll_baseline(session,user_id,now,insert):
    """Caller holds User first and has checked deletion; source SQL only."""
    if await session.scalar(select(User.status).where(User.id==user_id))=="blocked": return 0
    # All retained source history, not just recent jobs: expiry cannot reset
    # the first-ready origin or increment an old account's denominator again.
    job=(await session.execute(select(SmartReminderJob.__table__).where(
        SmartReminderJob.user_id==user_id,SmartReminderJob.policy_version==QUEUE_VERSION)
        .order_by(SmartReminderJob.created_at,SmartReminderJob.id).limit(1))).mappings().first()
    if job is None: return 0
    at=_utc(job["created_at"])
    if not now-RAW_RETENTION<at<=now or job["course_key"] not in LEVELS or job["selected_channel"] is not None: return 0
    try:
        start,end=day_window(job["timezone_name"],job["local_day"].isoformat())
        if (start!=_utc(job["day_start_utc"]) or end!=_utc(job["day_end_utc"]) or not start<=at<end): return 0
        _,matures=windows(at,job["timezone_name"])
    except (KeyError,TypeError,ValueError): return 0
    added=await session.scalar(insert(session,MEMBER).values(user_id=user_id,protocol_version=VERSION,
        source_job_id=job["id"],entered_at=at,timezone_name=job["timezone_name"],course_key=job["course_key"],
        expires_at=at+RAW_RETENTION).on_conflict_do_nothing(index_elements=["user_id","protocol_version"])
        .returning(MEMBER.c.user_id))
    if added is None: return 0
    await session.execute(insert(session,TOTAL).values(protocol_version=VERSION,
        cohort_month=at.date().replace(day=1),enrolled_accounts=1,matures_at=matures)
        .on_conflict_do_update(index_elements=["protocol_version","cohort_month"],set_={
            "enrolled_accounts":TOTAL.c.enrolled_accounts+1,
            "matures_at":case((TOTAL.c.matures_at<matures,matures),else_=TOTAL.c.matures_at)}))
    return 1


async def read_account_learning(session,user_id,since,until,evidence_at):
    """Historical account-wide original units; mutable current progress is not a clock."""
    xp=(await session.execute(select(CourseXpEvent.__table__).where(CourseXpEvent.user_id==user_id,
        CourseXpEvent.activity_type.in_(("lesson","test","training")),CourseXpEvent.created_at>=since,
        CourseXpEvent.created_at<=until).order_by(CourseXpEvent.created_at,CourseXpEvent.id)
        .limit(MAX_POLICY_ROWS+1))).mappings().all()
    limits={"reviewed_account_sources_only","historical_server_receipts"}
    if len(xp)>MAX_POLICY_ROWS:
        return VerifiedLearningEvidence(coverage_limits=tuple(sorted(limits|{"account_learning_over_limit"})))
    orders=set();sessions=set()
    for row in xp:
        match=_LESSON_REF.fullmatch(row["activity_ref"])
        if match: orders.add(int(match[2]))
        elif row["activity_ref"].endswith(":completed"): sessions.add(row["activity_ref"][:-10])
    # Bind proof to in-window original refs, including a practice result just
    # before its XP or a late server receipt. No new result time is invented.
    events=(await session.execute(select(CourseMiniAppEvent.__table__).where(
        CourseMiniAppEvent.user_id==user_id,CourseMiniAppEvent.level.in_(LEVELS),
        CourseMiniAppEvent.source.in_(("course_v3","android_course","desktop_course","course_miniapp")),
        CourseMiniAppEvent.event_name.in_(TERMINAL_EVENTS),CourseMiniAppEvent.created_at<=evidence_at,
        or_(CourseMiniAppEvent.lesson_order.in_(orders),CourseMiniAppEvent.session_id.in_(sessions)))
        .order_by(CourseMiniAppEvent.created_at,CourseMiniAppEvent.id).limit(MAX_POLICY_ROWS+1))).mappings().all()
    if len(events)>MAX_POLICY_ROWS:
        return VerifiedLearningEvidence(coverage_limits=tuple(sorted(limits|{"account_learning_over_limit"})))
    studies={}
    for level in LEVELS:
        completed=max((int(m[2]) for r in xp if (m:=_LESSON_REF.fullmatch(r["activity_ref"])) and m[1]==level),default=0)
        evidence=corroborate_learning(user_id,level=level,completed=completed,xp=xp,events=events)
        for study in evidence.studies: studies[(study.activity_type,study.reference)]=study
    return VerifiedLearningEvidence(tuple(studies.values()),tuple(sorted(limits)))


class SmartReminderBaselineService:
    """Internal bounded readout; use protected operator auth before exposing it."""
    def __init__(self,sessions,*,clock=None):
        self.sessions=sessions
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    async def report(self,cohort_month):
        if type(cohort_month) is not date or cohort_month.day!=1: raise ValueError("UTC cohort month required")
        now=_aware_utc(self.clock())
        start=datetime.combine(cohort_month,datetime.min.time(),timezone.utc)
        next_month=(cohort_month.replace(day=28)+timedelta(days=4)).replace(day=1)
        end=datetime.combine(next_month,datetime.min.time(),timezone.utc)
        result=dict(version=VERSION,cohort_month=cohort_month.isoformat(),observed_at=now.isoformat(),
            scope="observed_base_policy_ready_accounts",status="no_recorded_cohort",cohort_accounts=None,
            retained_members=None,censored_accounts=None,week_mature_accounts=0,d7_mature_accounts=0,
            d1_overlap_accounts=None,source_limited_accounts=0,
            observed_active_days_lower_bound=None,observed_units_lower_bound=None,
            observed_d7_accounts_lower_bound=None,observed_d7_percent_lower_bound=None,
            observed_active_days_per_account_lower_bound=None,observed_units_per_account_lower_bound=None,
            d7_learning_retention=None,primary_kpis_available=False,experiment_ready=False,dispatch_allowed=False,
            coverage_limits=("optional_capture_not_census","reviewed_sources_only","negative_learning_unknown",
                "no_randomized_assignment_or_causal_lift","unsupported_repeat_practice_and_voice"))
        if cohort_month<oldest_month(now): result["status"]="cohort_expired";return result
        async with self.sessions() as s:
            if s.bind.dialect.name=="postgresql":
                await s.execute(text("SET TRANSACTION READ ONLY"))
                await s.execute(text("SET LOCAL statement_timeout = '5000'"))
            total=(await s.execute(select(TOTAL).where(TOTAL.c.protocol_version==VERSION,
                TOTAL.c.cohort_month==cohort_month))).mappings().first()
            if total is None: return result
            rows=(await s.execute(select(MEMBER).where(MEMBER.c.protocol_version==VERSION,
                MEMBER.c.entered_at>=start,MEMBER.c.entered_at<end).order_by(MEMBER.c.user_id)
                .limit(MAX_BATCH+1))).mappings().all()
        n=total["enrolled_accounts"]
        result["cohort_accounts"]=n
        if len(rows)>MAX_BATCH: result["status"]="cohort_over_limit";return result
        if len(rows)>n: result["status"]="cohort_counter_conflict";return result
        result["retained_members"]=len(rows)
        result["censored_accounts"]=n-len(rows)
        active_days=units=d7_accounts=readable=overlap=0
        for row in rows:
            try: week_end,d7_end=windows(_utc(row["entered_at"]),row["timezone_name"])
            except (KeyError,TypeError,ValueError):
                result["censored_accounts"]+=1;continue
            week_mature,d7_mature=now>=week_end,now>=d7_end
            result["week_mature_accounts"]+=int(week_mature)
            result["d7_mature_accounts"]+=int(d7_mature)
            if not week_mature: continue
            async with self.sessions.begin() as s:
                with s.no_autoflush:
                    if s.bind.dialect.name=="postgresql":
                        await s.execute(text("SET LOCAL statement_timeout = '5000'"))
                    owner=(await s.execute(select(User.id,User.status,User.telegram_id).where(
                        User.id==row["user_id"]).with_for_update())).one_or_none()
                    pending=await s.scalar(select(AccountDeletionRequest.id).where(
                        AccountDeletionRequest.status=="submitted",or_(AccountDeletionRequest.user_id==row["user_id"],
                            AccountDeletionRequest.active_user_id==row["user_id"])).limit(1))
                    if owner is None or owner.status=="blocked" or pending is not None or _utc(row["expires_at"])<=now:
                        result["censored_accounts"]+=1;continue
                    cutoff=d7_end if d7_mature else week_end
                    learning=await read_account_learning(s,owner.id,_utc(row["entered_at"]),cutoff,now)
                    scored=await read_scored_activity(s,owner.id,level=None,
                        history_since=_utc(row["entered_at"]),observed_at=cutoff)
                    if any("over_limit" in reason for reason in (*learning.coverage_limits,*scored.coverage_limits)):
                        result["source_limited_accounts"]+=1
                    times={t for t in scored.times if _utc(row["entered_at"])<=t<cutoff}
                    times.update(t.accepted_at for t in learning.studies if _utc(row["entered_at"])<=t.accepted_at<cutoff)
                    zone=ZoneInfo(row["timezone_name"])
                    active_days+=len({t.astimezone(zone).date() for t in times if t<week_end})
                    units+=len({(t.activity_type,t.reference) for t in learning.studies if t.accepted_at<week_end})
                    d7_accounts+=int(d7_mature and any(week_end<=t<d7_end for t in times))
                    readable+=1
                    d1=await s.scalar(select(CourseMiniAppEvent.id).where(
                        _owner(CourseMiniAppEvent,owner.id,owner.telegram_id),
                        CourseMiniAppEvent.event_name==D1_RECOVERY_ASSIGNED_EVENT,
                        CourseMiniAppEvent.source==D1_RECOVERY_EXPERIMENT,
                        CourseMiniAppEvent.created_at>_utc(row["entered_at"])-D1_RECOVERY_HOLDOUT,
                        CourseMiniAppEvent.created_at<cutoff).limit(1))
                    overlap+=int(d1 is not None)
        result["d1_overlap_accounts"]=overlap if readable else None
        closed=now>=end and now>=_utc(total["matures_at"])
        result["status"]="observed_lower_bounds" if closed and readable else "immature_or_unavailable"
        if readable:
            result.update(observed_active_days_lower_bound=active_days if active_days or not result["source_limited_accounts"] else None,
                observed_units_lower_bound=units if units or not result["source_limited_accounts"] else None)
        if closed and readable and n>0:
            result["observed_d7_accounts_lower_bound"]=d7_accounts if d7_accounts or not result["source_limited_accounts"] else None
            if not result["source_limited_accounts"]:
                result.update(observed_d7_percent_lower_bound=100*d7_accounts/n,
                    observed_active_days_per_account_lower_bound=active_days/n,
                    observed_units_per_account_lower_bound=units/n)
            else: result["status"]="source_coverage_limited"
        return result


async def baseline_retention(session,now,*,execute,limit):
    from sqlalchemy import func, tuple_
    expired=MEMBER.c.expires_at<=now
    old=TOTAL.c.cohort_month<oldest_month(now)
    result=dict(expired_baseline_members=await session.scalar(select(func.count()).select_from(MEMBER).where(expired)),
        expired_baseline_totals=await session.scalar(select(func.count()).select_from(TOTAL).where(old)),
        removed_baseline_members=0,removed_baseline_totals=0)
    if execute:
        members=select(MEMBER.c.user_id,MEMBER.c.protocol_version).where(expired).order_by(
            MEMBER.c.expires_at,MEMBER.c.user_id,MEMBER.c.protocol_version).limit(limit)
        totals=select(TOTAL.c.protocol_version,TOTAL.c.cohort_month).where(old).order_by(
            TOTAL.c.cohort_month,TOTAL.c.protocol_version).limit(limit)
        result["removed_baseline_members"]=(await session.execute(delete(MEMBER).where(
            tuple_(MEMBER.c.user_id,MEMBER.c.protocol_version).in_(members)))).rowcount
        result["removed_baseline_totals"]=(await session.execute(delete(TOTAL).where(
            tuple_(TOTAL.c.protocol_version,TOTAL.c.cohort_month).in_(totals)))).rowcount
    return result
