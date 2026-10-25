"""Short session-bound campaign scheduling; no new offline authority."""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import logging

from sqlalchemy import func, select

from app.admin_api.pwa_access_grants import CommandError
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_step_up import _enabled
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_outbound import AdminPwaOutboundJob as Job
from app.db.models.user import User

logger = logging.getLogger(__name__)


def utc_send_time(value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.endswith('Z'):
        raise ValueError('Explicit UTC send time required')
    stamp = datetime.fromisoformat(value[:-1] + '+00:00')
    if stamp.utcoffset() != timedelta(0):
        raise ValueError('Explicit UTC send time required')
    return stamp.isoformat().replace('+00:00', 'Z')


async def validate_schedule(db, *, cookie, send_at):
    if send_at is None:
        return None
    stamp = datetime.fromisoformat(send_at.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    expiry = await db.scalar(select(AdminPwaSession.expires_at).where(
        AdminPwaSession.token_hash == hashlib.sha256(cookie.encode()).hexdigest()))
    if expiry is None or not now < stamp <= now + timedelta(minutes=30) or stamp >= _utc(expiry):
        raise CommandError('admin_pwa_campaign_schedule_invalid', 409)
    return stamp


def create_due_campaign_poller(*, settings_obj, session_factory, drainer):
    """At most two tracked tasks; the existing drainer owns the shared IO slots.

    Selection is advisory. The transactional job claim fences other processes.
    Revoked/expired sessions are filtered out rather than starving valid jobs.
    """
    active = {}
    lock = asyncio.Lock()

    def finished(job_id, task):
        active.pop(job_id, None)
        if not task.cancelled() and task.exception() is not None:
            logger.error('Admin PWA scheduled job requires operator review')

    async def poll():
        if not _enabled(settings_obj) or drainer is None:
            return 0
        async with lock:
            capacity = 2 - len(active)
            if capacity <= 0:
                return 0
            now = datetime.now(timezone.utc)
            async with session_factory() as db:
                async with db.begin():
                    if db.get_bind().dialect.name == 'postgresql':
                        from sqlalchemy import text
                        await db.execute(text("SET LOCAL statement_timeout = '3000'"))
                    query = select(Job.id).join(AdminPwaSession, AdminPwaSession.id == Job.session_id).join(
                        User, User.id == Job.actor_user_id).where(Job.status == 'ready',
                        Job.not_before.is_not(None), Job.not_before <= now, Job.expires_at > now,
                        AdminPwaSession.user_id == Job.actor_user_id, AdminPwaSession.revoked_at.is_(None),
                        AdminPwaSession.expires_at > now, AdminPwaSession.auth_method == 'webauthn',
                        User.telegram_id.in_(settings_obj.admin_id_list), func.lower(func.trim(User.status)) != 'blocked')
                    if active:
                        query = query.where(Job.id.not_in(list(active)))
                    ids = (await db.scalars(query.order_by(Job.not_before, Job.id).limit(capacity))).all()
            for job_id in ids:
                task = asyncio.create_task(drainer(job_id))
                active[job_id] = task
                task.add_done_callback(lambda task, job_id=job_id: finished(job_id, task))
            return len(ids)

    async def close():
        tasks = list(active.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    poll.close = close
    return poll
