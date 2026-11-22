"""Situation-aware, non-repeating copy for the Smart study reminder (D33).

One selector for Telegram, iPhone PWA and Android. The day's variant key is
chosen once, stored on the job and reused by retries, the Android claim and
the inbox. Admin custom text for a language still wins over the library.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
from html import escape
import logging
import re

from sqlalchemy import func, select, update

from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.smart_reminder import SmartReminderAttempt, SmartReminderJob
from app.services.course_daily_window import local_day_key
from app.services.notification_i18n import notification_message
from app.services.notification_template_service import KEY_SMART_STUDY, NotificationTemplateService


# Situation -> number of catalog variants `smart.msg.<situation>.v<n>.title|body`.
POOLS = {"daily": 8, "streak": 6, "comeback": 8, "long_break": 10}
COMEBACK_AFTER_DAYS = 2
LONG_BREAK_AFTER_DAYS = 8
TITLE_MAX = 60
BODY_MAX = 160
logger = logging.getLogger(__name__)
_KEY = re.compile(r"(daily|streak|comeback|long_break)\.v([1-9][0-9]?)")
_MAX_KEYS = 256
JOB = SmartReminderJob.__table__
ATTEMPT = SmartReminderAttempt.__table__


@dataclass(frozen=True)
class MessageFacts:
    today: date | None = None
    last_study_day: date | None = None
    streak: int = 0


@dataclass(frozen=True)
class SmartStudyContent:
    """`text` keeps `{lesson}` so every caller formats it exactly as before."""
    text: str
    media_type: str = "none"
    media_path: str | None = None
    content_key: str | None = None
    streak: int = 0

    def params(self, lesson):
        values = {"template_service": KEY_SMART_STUDY, "lesson": lesson}
        if self.content_key:
            values |= {"content_key": self.content_key, "streak": self.streak}
        return values


def is_key(value) -> bool:
    match = _KEY.fullmatch(value) if isinstance(value, str) else None
    return bool(match) and int(match.group(2)) <= POOLS[match.group(1)]


def situation(facts: MessageFacts) -> str:
    """First match wins; the boundaries only switch tone, copy names no days."""
    gap = ((facts.today - facts.last_study_day).days
           if facts.today and facts.last_study_day else None)
    if gap is not None and gap >= LONG_BREAK_AFTER_DAYS:
        return "long_break"
    if gap is not None and gap >= COMEBACK_AFTER_DAYS:
        return "comeback"
    if gap == 1 and facts.streak >= 2:
        return "streak"
    return "daily"


def choose(pool: str, *, user_id: int, local_day: date, last_sent: dict[str, date]) -> str:
    """Never-sent first, then least recently sent; stable per account/day tie."""
    def rank(key):
        tie = hashlib.sha256(f"{user_id}:{local_day.isoformat()}:{key}".encode()).hexdigest()
        return last_sent.get(key, date.min), tie
    return min((f"{pool}.v{n}" for n in range(1, POOLS[pool] + 1)), key=rank)


def library_text(key: str, lang: str, *, streak: int) -> str | None:
    """Telegram-style `<b>title</b>\\nbody`; `{lesson}` stays for the caller.

    None when the catalog lacks the variant: callers keep the default text.
    """
    title = notification_message(f"smart.msg.{key}.title", lang, streak=streak).strip()
    body = notification_message(f"smart.msg.{key}.body", lang, streak=streak).strip()
    if not title or not body:
        logger.warning("Smart message variant unavailable; reason=smart_catalog_missing")
        return None
    return f"<b>{escape(title, quote=False)}</b>\n{escape(body, quote=False)}"


async def load_facts(session, user_id: int, *, now: datetime) -> MessageFacts:
    """The app's own streak source: profile streak and last activity day."""
    row = (await session.execute(select(
        CourseMiniAppProfile.current_streak, CourseMiniAppProfile.last_activity_date,
        CourseMiniAppProfile.timezone_offset_minutes,
    ).where(CourseMiniAppProfile.user_id == user_id))).mappings().one_or_none()
    if row is None:
        return MessageFacts()
    today = date.fromisoformat(local_day_key(row["timezone_offset_minutes"], now=now))
    last = row["last_activity_date"]
    live = last is not None and last in (today, today - timedelta(days=1))
    return MessageFacts(today, last, max(0, int(row["current_streak"] or 0)) if live else 0)


async def last_sent_days(session, user_id: int, *, exclude_job_id: str) -> dict[str, date]:
    """Latest local day per variant this account was actually sent (bounded)."""
    started = select(ATTEMPT.c.id).where(
        ATTEMPT.c.job_id == JOB.c.id, ATTEMPT.c.started_at.is_not(None)).exists()
    rows = (await session.execute(select(JOB.c.content_key, func.max(JOB.c.local_day)).where(
        JOB.c.user_id == user_id, JOB.c.category == "study", JOB.c.content_key.is_not(None),
        JOB.c.id != exclude_job_id, started,
    ).group_by(JOB.c.content_key).limit(_MAX_KEYS))).all()
    return {key: day for key, day in rows if is_key(key)}


async def smart_study_content(session, user_id: int, job, lang: str, *, now: datetime):
    """Resolve the day's text inside the caller's authorization transaction.

    Returns None when the Admin template is disabled. Custom Admin text wins
    and stores no key. Otherwise the job's variant is chosen once and kept.
    """
    resolved = await NotificationTemplateService(session).resolve(KEY_SMART_STUDY, lang)
    if resolved is None:
        return None
    media = {"media_type": resolved.get("media_type") or "none", "media_path": resolved.get("media_path")}
    if resolved.get("custom"):
        return SmartStudyContent(resolved["text"], **media)
    facts = await load_facts(session, user_id, now=now)
    key = job.get("content_key")
    stored = is_key(key)
    if not stored:
        key = choose(situation(facts), user_id=user_id, local_day=job["local_day"],
                     last_sent=await last_sent_days(session, user_id, exclude_job_id=job["id"]))
    text = library_text(key, lang, streak=facts.streak)
    if text is None:
        return SmartStudyContent(resolved["text"], **media)
    if not stored:
        await session.execute(update(JOB).where(
            JOB.c.id == job["id"], JOB.c.user_id == user_id, JOB.c.content_key.is_(None),
        ).values(content_key=key))  # Callers hold the job row lock.
    return SmartStudyContent(text, **media, content_key=key, streak=facts.streak)


async def resolve_for_feed(session, params: dict, lang: str) -> dict | None:
    """Same variant in another UZ/RU/TJ language for the inbox and PWA feed."""
    resolved = await NotificationTemplateService(session).resolve(KEY_SMART_STUDY, lang)
    key = params.get("content_key")
    if resolved is None or resolved.get("custom") or not is_key(key):
        return resolved
    streak = params.get("streak")
    text = library_text(key, lang, streak=streak if type(streak) is int else 0)
    return resolved if text is None else resolved | {"text": text}
