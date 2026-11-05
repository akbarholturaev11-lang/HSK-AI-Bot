"""Internal opt-in account planner. Pending selection is never posting authority.

No production registration, cohort enrollment, provider or automatic fallback.
Caller supplies existing privileged admission/coverage, never HTTP/client facts.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import re

from sqlalchemy import select, update

from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.smart_reminder import SmartReminderPreference, SmartReminderRouting
from app.db.models.user import User
from app.services.notification_template_service import KEY_SMART_STUDY, NotificationTemplateService
from app.services.smart_reminder_android import SmartReminderAndroidService
from app.services.smart_reminder_analysis import SmartReminderAnalysisObserver
from app.services.smart_reminder_destination import PWA_POLICY_VERSION, SmartReminderDestinationService
from app.services.smart_reminder_coordination import read_d1_scope
from app.services.smart_reminder_policy import APPROVED_HABIT_CALIBRATION, _aware_utc, evaluate
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderPreferencesService, _utc
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB, QUEUE_VERSION, SmartReminderShadowQueue
from app.services.smart_reminder_telegram import SmartReminderTelegramService, _android_inventory, _binding

@dataclass(frozen=True)
class PlanningResult:
    reason: str
    job_id: str | None = None
    channel: str | None = None
    device_id: str | None = None
    dispatch_allowed: bool = field(default=False, init=False)


class SmartReminderPlanner:
    def __init__(self, settings, sessions, *, enabled=False, calibration=None,
                 coverage_reader=None, android_admission_reader=None, clock=None, rollout_reader=None):
        self.settings, self.sessions, self.enabled = settings, sessions, enabled
        self.calibration, self.coverage_reader = calibration, coverage_reader
        self.android_admission_reader = android_admission_reader
        self.rollout_reader = rollout_reader
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.queue = SmartReminderShadowQueue(sessions, clock=self.clock,
            analysis_observer=SmartReminderAnalysisObserver(settings,sessions,clock=self.clock))
        self.telegram = SmartReminderTelegramService(settings,sessions,calibration=calibration,
            coverage_reader=coverage_reader,clock=self.clock,rollout_reader=rollout_reader)

    def _now(self):
        return _aware_utc(self.clock())

    def _android(self, session):
        return SmartReminderAndroidService(session,enabled=self.enabled,calibration=self.calibration,
            coverage_reader=self.coverage_reader,admission_reader=self.android_admission_reader,clock=self.clock,
            rollout_reader=self.rollout_reader)

    async def _telegram_actor(self, session, user_id):
        telegram_id = await session.scalar(select(User.telegram_id).where(User.id==user_id))
        return SmartReminderActor(user_id,'telegram_bot',telegram_id=telegram_id)

    async def _pwa_review_ready(self, session, user_id, pref):
        if pref["master_enabled"] is not True or pref["channel_mode"] == "manual_locked":
            return False
        from app.services.learner_pwa_push import active_subscriptions, sender_config
        return (sender_config(self.settings) is not None and
                bool(await active_subscriptions(session, user_id, now=self._now(), limit=1)))

    async def _reviewed(self, session, actor, *, selected_channel=None):
        pref = await SmartReminderPreferencesService(session).read(actor)
        if pref['master_enabled'] is False: return 'master_off'
        if not await NotificationTemplateService(session).is_enabled(KEY_SMART_STUDY):
            return 'admin_study_disabled'
        row = (await session.execute(select(SmartReminderRouting.__table__).where(
            SmartReminderRouting.user_id==actor.user_id).with_for_update())).mappings().one_or_none()
        epoch = await session.scalar(select(SmartReminderPreference.grant_epoch).where(
            SmartReminderPreference.user_id==actor.user_id))
        if (row is None or row['state'] not in {'held','telegram'} or
                row['preference_revision']!=pref['revision'] or row['grant_epoch']!=(epoch or 0) or
                row['verified_at'] is None or row['verified_until'] is None or
                not re.fullmatch(r'[0-9a-f]{64}',row['evidence_sha256'] or '')):
            return 'planner_review_unavailable'
        inventory, until = await _android_inventory(session,actor.user_id,self._now(),native=row['state']=='held')
        now = self._now()
        if (inventory is None or inventory!=row['inventory_sha256'] or
                not _utc(row['held_at'])<=_utc(row['verified_at'])<=now<_utc(row['verified_until']) or
                until is not None and now>=until or row['state']=='held' and until is None):
            return 'planner_review_unavailable'
        if row['state']=='telegram':
            pwa_review = selected_channel == "pwa" or (
                selected_channel is None and await self._pwa_review_ready(session, actor.user_id, pref))
            if pwa_review:
                telegram_actor = await self._telegram_actor(session, actor.user_id)
                if (type(telegram_actor.telegram_id) is not int or telegram_actor.telegram_id <= 0 or
                        row["telegram_binding"] != _binding(telegram_actor)):
                    return 'planner_review_unavailable'
            else:
                if refused := self.telegram._gate(): return refused.reason
                await self.telegram._cohort(session,await self._telegram_actor(session,actor.user_id))

    async def prepare(self, actor, *, history_since, expected_level, expires_at):
        if self.enabled is not True: return PlanningResult('planner_disabled')
        if self.calibration is None: return PlanningResult('cadence_calibration_unconfigured')
        if self.coverage_reader is None: return PlanningResult('learning_coverage_unavailable')
        # Review first: a switch/capability/absence of devices cannot enroll an account.
        async with self.sessions.begin() as session:
            if refused := await self._reviewed(session,actor): return PlanningResult(refused)
        reserved = await self.queue.reserve(actor,history_since=history_since,
            expected_level=expected_level,expires_at=expires_at)
        if reserved.job_id is None: return PlanningResult(reserved.reason)
        async with self.sessions.begin() as session:
            row = await self.queue._job(session,actor,reserved.job_id)
            if row is None: return PlanningResult('shadow_job_not_found')
            android = self._android(session)
            versions = {'android':android.policy_version,'telegram':self.telegram.policy_version,
                        'pwa':PWA_POLICY_VERSION}
            if (row['state']=='pending' and row['selected_channel'] in versions and
                    row['policy_version']==versions[row['selected_channel']]):
                return PlanningResult('already_planned',row['id'],row['selected_channel'],row['selected_device_id'])
            if (row['state']!='shadow' or row['policy_version']!=QUEUE_VERSION or
                    row['selected_channel'] is not None or row['selected_device_id'] is not None or
                    row['lease_token'] is not None or await session.scalar(select(ATTEMPT.c.id).where(
                        ATTEMPT.c.job_id==row['id']).limit(1))):
                return PlanningResult('planner_intent_frozen',row['id'])
            if refused := await self._reviewed(session,actor): return PlanningResult(refused,row['id'])
            selector = SmartReminderDestinationService(session,clock=self.clock,
                telegram_ready=self.telegram._gate() is None)
            choice = await selector.select(actor,job_id=row['id'],history_since=history_since)
            if choice.channel is None: return PlanningResult(choice.reason,row['id'])
            if choice.channel=='android':
                if refused := android._gate(): return PlanningResult(refused['reason'],row['id'])
                native_session = await session.scalar(select(DesktopSession.id).join(DesktopDevice,
                    DesktopDevice.id==DesktopSession.device_id).where(DesktopDevice.id==choice.device_id,
                    DesktopDevice.user_id==actor.user_id,DesktopDevice.platform=='android',
                    DesktopDevice.revoked_at.is_(None),DesktopSession.revoked_at.is_(None),
                    DesktopSession.expires_at>self._now()).order_by(
                        DesktopSession.expires_at.desc(),DesktopSession.id).limit(1))
                if native_session is None: return PlanningResult('android_capability_unavailable',row['id'])
                selected = SmartReminderActor(actor.user_id,'android',device_id=choice.device_id,session_id=native_session)
                admission = await android._admission(selected,row)
                if admission is None: return PlanningResult('android_admission_unavailable',row['id'])
                _, refused = await android._fresh(selected,row,admission)
                if refused: return PlanningResult(refused['reason'],row['id'])
            elif choice.channel=='telegram':
                if refused := self.telegram._gate(): return PlanningResult(refused.reason,row['id'])
                selected = await self._telegram_actor(session,actor.user_id)
                cohort = await self.telegram._cohort(session,selected)
                if refused := await self.telegram._fresh(session,selected,row,cohort,history_since):
                    return PlanningResult(refused.reason,row['id'])
            else:
                # PWA has no alternate consent source: the destination selector
                # requires account Smart ON plus a live user-enabled PWA Push
                # subscription, and manual Telegram/Android locks exclude it.
                pwa_pref = await SmartReminderPreferencesService(session).read(actor)
                if pwa_pref['master_enabled'] is not True or choice.device_id is None:
                    return PlanningResult('pwa_study_unavailable',row['id'])
                selected = actor
            # Privileged readers may take time. Never bind stale destination/review facts.
            fresh = await selector.select(actor,job_id=row['id'],history_since=history_since)
            context, refused = await self.queue._fresh(session,selected,row,self._now(),history_since)
            if refused: return PlanningResult(refused.reason,row['id'])
            if (fresh.channel,fresh.device_id,fresh.preference_revision,fresh.grant_epoch)!=(
                    choice.channel,choice.device_id,choice.preference_revision,choice.grant_epoch):
                result = await self.queue._close(session,row,'cancelled','shadow_context_changed',self._now())
                return PlanningResult(result.reason,row['id'])
            if refused := await self._reviewed(session,selected,selected_channel=choice.channel):
                return PlanningResult(refused,row['id'])
            if self.enabled is not True: return PlanningResult('planner_disabled',row['id'])
            d1 = await read_d1_scope(session,actor.user_id,self._now())
            reviewed_until = await session.scalar(select(SmartReminderRouting.verified_until).where(
                SmartReminderRouting.user_id==actor.user_id))
            if not await NotificationTemplateService(session).is_enabled(KEY_SMART_STUDY):
                result = await self.queue._close(session,row,'cancelled','admin_study_disabled',self._now())
                return PlanningResult(result.reason,row['id'])
            now = self._now()
            if d1.reason(now):
                result = await self.queue._close(session,row,'cancelled',d1.reason(now),now)
                return PlanningResult(result.reason,row['id'])
            decision = evaluate(replace(context,observed_at=now),calibration=APPROVED_HABIT_CALIBRATION,
                allow_elapsed_time=True)
            if not decision.candidate:
                result = await self.queue._close(session,row,'cancelled',decision.reason,now)
                return PlanningResult(result.reason,row['id'])
            if (choice.valid_until is None or fresh.valid_until is None or reviewed_until is None or
                    now>=min(_utc(choice.valid_until),_utc(fresh.valid_until),_utc(reviewed_until),_utc(row['expires_at']))):
                result = await self.queue._close(session,row,'expired','shadow_expired',now)
                return PlanningResult(result.reason,row['id'])
            changed = await session.execute(update(JOB).where(JOB.c.id==row['id'],JOB.c.user_id==actor.user_id,
                JOB.c.state=='shadow',JOB.c.policy_version==QUEUE_VERSION,JOB.c.selected_channel.is_(None),
                JOB.c.selected_device_id.is_(None),JOB.c.lease_token.is_(None),
                ~select(ATTEMPT.c.id).where(ATTEMPT.c.job_id==row['id']).exists()).values(
                    state='pending',policy_version=versions[choice.channel],selected_channel=choice.channel,
                    selected_device_id=choice.device_id,reason_code=choice.channel+'_planned',updated_at=now))
            if changed.rowcount!=1: return PlanningResult('planner_intent_frozen',row['id'])
            return PlanningResult('planned',row['id'],choice.channel,choice.device_id)
