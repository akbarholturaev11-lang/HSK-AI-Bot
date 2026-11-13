"""Privacy-safe failure intake: validation, admission and incident upserts (D3).

One transaction per request, owned by the caller. The owner is never read
from the request: callers pass the account their transport verified. Events
are processed in fingerprint order so concurrent workers lock incidents in
the same order.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import re
import uuid

from sqlalchemy import func, select, text
from sqlalchemy.dialects import postgresql as pg_dialect
from sqlalchemy.dialects import sqlite as sqlite_dialect

from app.db.models.diagnostic import DiagnosticIncident, DiagnosticReceipt
from app.services.monitoring import catalog

MODES = ("off", "owners", "all")
BATCH_KEYS = frozenset({"schema", "events"})
EVENT_KEYS = frozenset({
    "event_id", "client_time", "platform", "app_version", "build", "channel",
    "feature_code", "failure_code", "site_code", "outcome", "category",
})
VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,%d}" % (catalog.MAX_VERSION_LENGTH - 1))
OWNER_LOCK_NAMESPACE = 0x6D6F6E  # "mon"
MAX_BUILD = 10**12
MAX_CLIENT_TIME_MS = 4_102_444_800_000  # 2100-01-01


class IntakeRejected(ValueError):
    """The whole request is refused; nothing from it is stored or logged."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class DiagEvent:
    event_id: str
    platform: str
    feature_code: str
    failure_code: str
    site_code: str
    outcome: str
    app_version: str | None = None
    build: int | None = None
    channel: str | None = None
    category: str | None = None
    client_time: datetime | None = None
    client_time_untrusted: bool = False
    occurrences: int = 1

    @property
    def fingerprint(self):
        return fingerprint(self.platform, self.feature_code, self.failure_code, self.site_code)


@dataclass
class IngestResult:
    accepted: int = 0
    duplicates: int = 0
    rejected: int = 0
    refused: int = 0
    dropped: int = 0
    paused: bool = False
    touched: list = field(default_factory=list)  # (incident, created, inserted) for alert hooks

    def response(self):
        if self.paused:
            return {"accepted": 0, "paused": True}
        return {"accepted": self.accepted, "duplicates": self.duplicates, "rejected": self.rejected,
                "refused": self.refused, "dropped": self.dropped, "paused": False}


def current_mode(settings_obj):
    mode = str(getattr(settings_obj, "MONITORING_MODE", "off") or "off").strip().lower()
    return mode if mode in MODES else "off"


def is_owner_account(settings_obj, telegram_id):
    """`owners` stage: only the existing admin allowlist (Telegram IDs)."""
    try:
        return telegram_id is not None and int(telegram_id) in set(settings_obj.admin_id_list)
    except (TypeError, ValueError):
        return False


def fingerprint(platform, feature_code, failure_code, site_code):
    raw = f"{catalog.CATALOG_VERSION}|{platform}|{feature_code}|{failure_code}|{site_code}"
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _uuid(value):
    try:
        return str(uuid.UUID(value)) if isinstance(value, str) and len(value) == 36 else None
    except ValueError:
        return None


def parse_batch(body, *, platform, now=None):
    """Validate a client batch. Returns (events, rejected_count).

    Request-level problems (shape, size, any unknown or forbidden key, a
    client owner ID, fingerprint or severity) reject the whole request. An
    event with an unknown code or a malformed value is rejected alone.
    """
    now = now or datetime.now(timezone.utc)
    if not isinstance(body, dict) or set(body) - BATCH_KEYS or body.get("schema") != catalog.SCHEMA:
        raise IntakeRejected("invalid_body")
    items = body.get("events")
    if not isinstance(items, list) or not items:
        raise IntakeRejected("invalid_body")
    if len(items) > catalog.MAX_EVENTS_PER_BATCH:
        raise IntakeRejected("too_many_events")
    for item in items:
        if not isinstance(item, dict) or set(item) - EVENT_KEYS:
            # Covers token, cookie, initData, password, message, stack, url,
            # body, user_id, telegram_id, fingerprint, severity and the like.
            raise IntakeRejected("forbidden_field")
    events, rejected = [], 0
    skew = timedelta(days=catalog.CLOCK_SKEW_DAYS)
    for item in items:
        event = _parse_event(item, platform=platform, now=now, skew=skew)
        if event is None:
            rejected += 1
        else:
            events.append(event)
    return events, rejected


def _parse_event(item, *, platform, now, skew):
    event_id = _uuid(item.get("event_id"))
    feature, failure, site = item.get("feature_code"), item.get("failure_code"), item.get("site_code")
    outcome = item.get("outcome", "failed")
    if (event_id is None or feature not in catalog.FEATURES or failure not in catalog.CLIENT_FAILURES
            or site not in catalog.ALL_SITES or outcome not in catalog.OUTCOMES
            or item.get("platform", platform) != platform):
        return None
    version = item.get("app_version")
    if version is not None and not (isinstance(version, str) and VERSION.fullmatch(version)):
        return None
    build = item.get("build")
    if build is not None and not (type(build) is int and 0 <= build < MAX_BUILD):
        return None
    channel = item.get("channel")
    if channel is not None and (platform != "android" or channel not in ("play", "direct")):
        return None
    category = item.get("category")
    if category is not None and category not in catalog.CATEGORIES:
        return None
    client_time, untrusted = None, False
    raw_time = item.get("client_time")
    if raw_time is not None:
        if type(raw_time) is not int or not 0 < raw_time < MAX_CLIENT_TIME_MS:
            return None
        stamp = datetime.fromtimestamp(raw_time / 1000, tz=timezone.utc)
        if abs(stamp - now) > skew:
            untrusted = True  # server receive time keeps the ordering
        else:
            client_time = stamp
    return DiagEvent(event_id=event_id, platform=platform, feature_code=feature, failure_code=failure,
                     site_code=site, outcome=outcome, app_version=version, build=build, channel=channel,
                     category=category, client_time=client_time, client_time_untrusted=untrusted)


def _insert(db, model):
    dialect = db.bind.dialect.name if db.bind is not None else "postgresql"
    return (sqlite_dialect.insert(model) if dialect == "sqlite" else pg_dialect.insert(model)), dialect


async def _lock_owner(db, owner_user_id):
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(:ns, :owner)"),
                         {"ns": OWNER_LOCK_NAMESPACE, "owner": int(owner_user_id)})


async def _incident_for(db, event, now, severity):
    """Create the incident skeleton if absent; return it row-locked."""
    stmt, _ = _insert(db, DiagnosticIncident)
    created = (await db.execute(
        stmt.values(fingerprint=event.fingerprint, platform=event.platform, feature_code=event.feature_code,
                    failure_code=event.failure_code, site_code=event.site_code, severity=severity,
                    occurrence_count=0, refused_count=0, first_seen_at=now, last_seen_at=now,
                    alert_epoch=0)
        .on_conflict_do_nothing(index_elements=["fingerprint"])
        .returning(DiagnosticIncident.id))).scalar_one_or_none()
    incident = (await db.execute(
        select(DiagnosticIncident).where(DiagnosticIncident.fingerprint == event.fingerprint)
        .with_for_update().execution_options(populate_existing=True))).scalar_one()
    return incident, created is not None


def _raise_severity(current, candidate):
    order = catalog.SEVERITIES
    return candidate if order.index(candidate) > order.index(current) else current


async def _record(db, incident, event, owner_user_id, now):
    stmt, _ = _insert(db, DiagnosticReceipt)
    values = dict(incident_id=incident.id, user_id=owner_user_id, event_id=event.event_id, received_at=now,
                  client_time=event.client_time, client_time_untrusted=event.client_time_untrusted,
                  app_version=event.app_version, build=event.build, channel=event.channel,
                  outcome=event.outcome, category=event.category, occurrences=event.occurrences)
    if owner_user_id is None:
        conflict = stmt.values(**values).on_conflict_do_nothing(
            index_elements=["event_id"], index_where=text("user_id IS NULL"))
    else:
        conflict = stmt.values(**values).on_conflict_do_nothing(index_elements=["user_id", "event_id"])
    inserted = (await db.execute(conflict.returning(DiagnosticReceipt.id))).scalar_one_or_none()
    if inserted is None:
        return False
    incident.occurrence_count += event.occurrences
    if incident.last_seen_at is None or now >= _aware(incident.last_seen_at):
        incident.last_seen_at = now
    if event.app_version and incident.first_version is None:
        incident.first_version = event.app_version
    if event.app_version and (event.build is None or incident.last_build is None
                              or event.build >= incident.last_build):
        incident.last_version = event.app_version
        if event.build is not None:
            incident.last_build = event.build
    recovered = event.outcome == "recovered"
    incident.severity = _raise_severity(
        incident.severity, catalog.severity_for(event.feature_code, event.failure_code, recovered=recovered))
    return True


def _aware(value):
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def _hourly_count(db, owner_user_id, now):
    return int((await db.execute(
        select(func.coalesce(func.sum(DiagnosticReceipt.occurrences), 0))
        .where(DiagnosticReceipt.user_id == owner_user_id,
               DiagnosticReceipt.received_at >= now - timedelta(hours=1)))).scalar_one())


# Hooks run inside the intake transaction after each occurrence (reopen in
# task 3.1, alert decision in task 3.2). Each receives
# (db, incident, created, inserted, event, now) and must never raise into intake.
OCCURRENCE_HOOKS = []


async def _run_hooks(db, incident, created, inserted, event, now):
    for hook in OCCURRENCE_HOOKS:
        await hook(db, incident, created, inserted, event, now)


async def ingest(db, *, owner_user_id, events, mode="all", owner_admitted=True, now=None):
    """Store validated events for one verified owner (or None for server rows).

    `mode` is the current intake mode; `owner_admitted` tells whether the
    owner passes the `owners` stage. The caller commits.
    """
    now = now or datetime.now(timezone.utc)
    result = IngestResult()
    if mode == "off":
        result.paused = True
        return result
    if owner_user_id is not None and mode == "owners" and not owner_admitted:
        result.dropped = len(events)
        return result
    ordered = sorted(events, key=lambda e: (e.fingerprint, e.event_id))
    allowance = len(ordered)
    if owner_user_id is not None:
        await _lock_owner(db, owner_user_id)
        allowance = max(0, catalog.HOURLY_CAP_PER_ACCOUNT - await _hourly_count(db, owner_user_id, now))
    for index, event in enumerate(ordered):
        severity = catalog.severity_for(event.feature_code, event.failure_code,
                                        recovered=event.outcome == "recovered")
        incident, created = await _incident_for(db, event, now, severity)
        if index >= allowance:
            # Refused by the cap: counted on its incident, never stored.
            incident.refused_count += event.occurrences
            result.refused += 1
            continue
        inserted = await _record(db, incident, event, owner_user_id, now)
        if inserted:
            result.accepted += 1
        else:
            result.duplicates += 1
        result.touched.append((incident, created, inserted))
        await _run_hooks(db, incident, created, inserted, event, now)
    await db.flush()
    return result


async def ingest_server(db, *, feature_code, failure_code, site_code, platform="server", occurrences=1,
                        mode="all", now=None):
    """One backend occurrence (or a coalesced count) without an owner."""
    if (feature_code not in catalog.FEATURES or failure_code not in catalog.SERVER_FAILURES
            or site_code not in catalog.ALL_SITES or platform not in catalog.PLATFORMS):
        raise IntakeRejected("unknown_code")
    event = DiagEvent(event_id=str(uuid.uuid4()), platform=platform, feature_code=feature_code,
                      failure_code=failure_code, site_code=site_code, outcome="failed",
                      occurrences=max(1, min(int(occurrences), 10_000)))
    return await ingest(db, owner_user_id=None, events=[event], mode=mode, now=now)
