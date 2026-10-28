"""Authenticated Smart preference state/CAS; no dispatcher or implicit commit.

Adapters supply a verified actor. Every operation rechecks current ownership and
account state under the user-first lock. Retry receipts are acknowledgements,
never settings snapshots or notification grants. Legacy delivery fencing is 2.4.
"""
from dataclasses import dataclass
from datetime import datetime, time, timezone
import hashlib
import json
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, model_validator
from sqlalchemy import insert, select, update

from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.smart_reminder import (
    SmartReminderCapability, SmartReminderConsent, SmartReminderMutation, SmartReminderPreference,
)
from app.db.models.user import User
from app.services.smart_reminder_legacy_backfill import SmartReminderLegacyBackfillService
from app.services.smart_reminder_legacy_evidence import (
    LegacyEvidenceUnavailable, MAX_DEVICE_OBSERVATIONS, SmartReminderLegacyEvidenceService,
)

PREF = SmartReminderPreference.__table__
CONSENT = SmartReminderConsent.__table__
MUTATION = SmartReminderMutation.__table__
MAX_REVISION = 2**31 - 1


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _clock(value):
    if len(value) != 5 or value[2] != ":":
        raise ValueError("HH:MM required")
    result = time.fromisoformat(value)
    if result.tzinfo is not None or result.second or result.microsecond:
        raise ValueError("HH:MM required")
    return result


class SmartReminderPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: StrictStr = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    expected_revision: StrictInt = Field(ge=0, lt=MAX_REVISION)
    master_enabled: StrictBool | None = None
    study_enabled: StrictBool | None = None
    time_mode: Literal["auto", "manual_locked"] | None = None
    manual_time_local: StrictStr | None = None
    timezone_name: StrictStr | None = Field(default=None, min_length=1, max_length=64)
    channel_mode: Literal["auto", "manual_locked"] | None = None
    preferred_channel: Literal["telegram", "android"] | None = None
    quiet_start: StrictStr | None = None
    quiet_end: StrictStr | None = None
    pause_until: StrictStr | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def validate_changes(self):
        fields = self.model_fields_set - {"request_id", "expected_revision"}
        if not fields:
            raise ValueError("At least one change is required")
        for key in ("master_enabled", "study_enabled", "time_mode", "channel_mode", "timezone_name"):
            if key in fields and getattr(self, key) is None:
                raise ValueError("Null intent is ambiguous")
        for key in ("manual_time_local", "quiet_start", "quiet_end"):
            value = getattr(self, key)
            if value is not None:
                _clock(value)
        if ("quiet_start" in fields) != ("quiet_end" in fields):
            raise ValueError("Both quiet endpoints are required")
        if (self.quiet_start is None) != (self.quiet_end is None) or (
                self.quiet_start is not None and self.quiet_start == self.quiet_end):
            raise ValueError("Unambiguous paired quiet window required")
        if self.timezone_name is not None:
            try:
                ZoneInfo(self.timezone_name)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("IANA zone required") from None
        if self.pause_until is not None:
            stamp = datetime.fromisoformat(self.pause_until)
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                raise ValueError("Timezone-aware pause required")
        return self


@dataclass(frozen=True)
class SmartReminderActor:
    user_id: int
    kind: Literal["telegram", "telegram_bot", "android"]
    telegram_id: int | None = None
    device_id: str | None = None
    session_id: str | None = None

    @property
    def key(self):
        return "android:" + self.device_id if self.kind == "android" else self.kind

    @property
    def source_key(self):
        return "intent:android:" + self.device_id if self.kind == "android" else "intent:telegram"


class SmartReminderError(ValueError):
    def __init__(self, code, status=422, *, revision=None):
        super().__init__(code)
        self.code, self.status, self.revision = code, status, revision


def _state(rows, source_key):
    """A current explicit endpoint intent can resolve its old mirror only.

    Unknown independent sources stay conservative; arbitrary existing OFF is
    never cleared by master ON or by a legacy snapshot.
    """
    intent = [r for r in rows if r["source_key"] == source_key and r["source"] == "user_intent"]
    other = [r for r in rows if r not in intent and not r["source"].startswith("legacy_")]
    if any(r["state"] == "off" for r in other):
        return "off"
    if other:
        return "unknown"
    states = [r["state"] for r in intent or rows]
    if "off" in states:
        return "off"
    return "on" if states and all(x == "on" for x in states) else "unknown"


class SmartReminderPreferencesService:
    def __init__(self, session):
        self.session = session

    async def _lock(self, actor):
        if type(actor.user_id) is not int or actor.user_id <= 0 or actor.kind not in {"android", "telegram", "telegram_bot"}:
            raise SmartReminderError("smart_auth_required", 401)
        query = select(User.id).where(User.id == actor.user_id)
        if actor.kind != "android":
            if type(actor.telegram_id) is not int or actor.telegram_id <= 0:
                raise SmartReminderError("smart_auth_required", 401)
            query = query.where(User.telegram_id == actor.telegram_id)
        if await self.session.scalar(query.with_for_update()) is None:
            raise SmartReminderError("smart_account_not_found", 404)
        if actor.kind == "android":
            # Fresh projections after the user lock, independent of any cached
            # ORM context. Do not reverse native refresh's session/device locks.
            device = (await self.session.execute(select(
                DesktopDevice.platform, DesktopDevice.revoked_at,
            ).where(DesktopDevice.id == actor.device_id, DesktopDevice.user_id == actor.user_id))).mappings().one_or_none()
            login = (await self.session.execute(select(
                DesktopSession.expires_at, DesktopSession.revoked_at,
            ).where(DesktopSession.id == actor.session_id, DesktopSession.device_id == actor.device_id))).mappings().one_or_none()
            if (device is None or login is None or device["revoked_at"] is not None
                    or login["revoked_at"] is not None or _utc(login["expires_at"]) <= datetime.now(timezone.utc)):
                raise SmartReminderError("smart_session_revoked", 401)
            if device["platform"] != "android":
                raise SmartReminderError("android_device_required", 403)
        try:
            return await SmartReminderLegacyEvidenceService(self.session).snapshot(actor.user_id)
        except LegacyEvidenceUnavailable as exc:
            code = str(exc)
            status = {"account_not_found": 404, "account_blocked": 403,
                      "account_state_unknown": 403, "account_deletion_pending": 409}.get(code, 503)
            raise SmartReminderError("smart_" + code, status) from None

    async def _preference(self, user_id):
        return (await self.session.execute(select(PREF).where(
            PREF.c.user_id == user_id).with_for_update())).mappings().one_or_none()

    async def read(self, actor):
        with self.session.no_autoflush:
            evidence = await self._lock(actor)
            row = await self._preference(actor.user_id)
            rows = (await self.session.execute(select(CONSENT).where(
                CONSENT.c.user_id == actor.user_id).limit(4 * MAX_DEVICE_OBSERVATIONS + 1))).mappings().all()
            if len(rows) > 4 * MAX_DEVICE_OBSERVATIONS:
                raise SmartReminderError("smart_consent_inventory_over_limit", 503)
            telegram = _state([r for r in rows if r["channel"] == "telegram" and r["device_id"] is None], "intent:telegram")
            if row is None:
                telegram = {"legacy_on": "on", "not_enabled": "off"}.get(evidence.telegram.study_state, "unknown")
            device_states = {}
            for device in evidence.android:
                if not device.revoked:
                    device_states[device.device_id] = _state([r for r in rows if
                        r["channel"] == "android" and r["device_id"] == device.device_id], "intent:android:" + device.device_id)
            android = "on" if "on" in device_states.values() else (
                "off" if device_states and all(v == "off" for v in device_states.values()) else "unknown")
            own = device_states.get(actor.device_id, "unknown")
            permission = "unknown"
            if actor.kind == "android":
                cap = (await self.session.execute(select(SmartReminderCapability.__table__).where(
                    SmartReminderCapability.device_id == actor.device_id,
                    SmartReminderCapability.user_id == actor.user_id))).mappings().one_or_none()
                if cap and cap["study_notifications_allowed"] is False:
                    permission = "denied"
                elif (cap and cap["study_notifications_allowed"] is True and cap["observed_at"]
                      and _utc(cap["observed_at"]) <= datetime.now(timezone.utc) < _utc(cap["expires_at"])):
                    permission = "allowed"
            pref = dict(row) if row else {}
            def value(key):
                result = pref.get(key)
                if isinstance(result, datetime):
                    return _utc(result).isoformat()
                return result.isoformat() if isinstance(result, time) else result
            return {
                "ok": True, "revision": pref.get("revision", 0),
                "migration_version": pref.get("migration_version", 0),
                "master_enabled": pref.get("master_enabled"),
                # Consent-derived configuration, never a delivery/OS grant.
                "effective_master_enabled": pref.get("master_enabled") is not False and "on" in {telegram, android},
                "time_mode": pref.get("time_mode", "auto"), "manual_time_local": value("manual_time_local"),
                "timezone_name": value("timezone_name"),
                "legacy_time_local": value("legacy_time_local") if row else evidence.telegram.saved_time_local,
                "legacy_offset_minutes": pref.get("legacy_offset_minutes") if row else evidence.telegram.saved_offset_minutes,
                "channel_mode": pref.get("channel_mode", "auto"), "preferred_channel": value("preferred_channel"),
                "quiet_start": value("quiet_start"), "quiet_end": value("quiet_end"), "pause_until": value("pause_until"),
                "channels": {
                    "telegram": {"consent": telegram, "transport_available": evidence.telegram.transport_present and not evidence.telegram.transport_blocked, "eligible": False},
                    "android": {"consent": android, "this_device_consent": own,
                                "study_os_permission": permission, "eligible": False},
                },
                "dispatch_allowed": False, "legacy_delivery_controlled": False,
            }

    async def patch(self, actor, payload: SmartReminderPatch):
        with self.session.no_autoflush:
            await self._lock(actor)
            result, _ = await self._mutate(actor, payload)
            return result

    async def _mutate(self, actor, payload, *, bot_time=None):
        body = payload.model_dump(mode="json", exclude_unset=True)
        if bot_time is not None:
            body["bot_time"] = bot_time.isoformat()
        digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        receipt = (await self.session.execute(select(MUTATION).where(
            MUTATION.c.user_id == actor.user_id, MUTATION.c.request_id == payload.request_id))).mappings().one_or_none()
        if receipt is not None:
            if receipt["actor_key"] != actor.key or receipt["body_sha256"] != digest:
                raise SmartReminderError("smart_request_id_reused", 409)
            return self._ack(payload.request_id, receipt["applied_revision"]), False
        row = await self._preference(actor.user_id)
        revision = row["revision"] if row else 0
        if payload.expected_revision != revision:
            raise SmartReminderError("smart_revision_conflict", 409, revision=revision)
        # Validate the merged lock state BEFORE additive backfill/writes.
        values = payload.model_dump(exclude_unset=True, exclude={"request_id", "expected_revision", "study_enabled"})
        for key in ("manual_time_local", "quiet_start", "quiet_end"):
            if values.get(key) is not None:
                values[key] = _clock(values[key])
        if values.get("pause_until") is not None:
            values["pause_until"] = _utc(datetime.fromisoformat(values["pause_until"]))
        merged = (dict(row) if row else {"time_mode": "auto", "channel_mode": "auto"}) | values
        if merged["time_mode"] == "manual_locked":
            if merged.get("manual_time_local") is None or merged.get("timezone_name") is None:
                raise SmartReminderError("smart_manual_time_incomplete")
        else:
            if values.get("manual_time_local") is not None:
                raise SmartReminderError("smart_manual_time_requires_lock")
            values["manual_time_local"] = None
        if merged["channel_mode"] == "manual_locked":
            if merged.get("preferred_channel") is None:
                raise SmartReminderError("smart_manual_channel_incomplete")
        else:
            if values.get("preferred_channel") is not None:
                raise SmartReminderError("smart_manual_channel_requires_lock")
            values["preferred_channel"] = None
        if row is None or row["revision"] == 0:
            await SmartReminderLegacyBackfillService(self.session).backfill(actor.user_id)
            row = await self._preference(actor.user_id)
        now = datetime.now(timezone.utc)
        epoch = row["grant_epoch"]
        if payload.master_enabled is False or payload.study_enabled is False:
            epoch += 1
        if epoch > MAX_REVISION:
            raise SmartReminderError("smart_epoch_exhausted", 409)
        if bot_time is not None:
            values["legacy_time_local"] = bot_time
        await self.session.execute(update(PREF).where(PREF.c.user_id == actor.user_id).values(
            **values, revision=revision + 1, grant_epoch=epoch,
            action_source=actor.kind, action_at=now, updated_at=now))
        if "study_enabled" in payload.model_fields_set:
            existing = await self.session.scalar(select(CONSENT.c.id).where(
                CONSENT.c.user_id == actor.user_id, CONSENT.c.source_key == actor.source_key,
                CONSENT.c.channel == ("android" if actor.kind == "android" else "telegram")))
            consent = dict(state="on" if payload.study_enabled else "off", source="user_intent",
                           revision=revision + 1, action_at=now, observed_at=now, evidence_version=1)
            if existing:
                await self.session.execute(update(CONSENT).where(CONSENT.c.id == existing).values(**consent))
            else:
                await self.session.execute(insert(CONSENT).values(
                    user_id=actor.user_id, channel="android" if actor.kind == "android" else "telegram",
                    source_key=actor.source_key, device_id=actor.device_id if actor.kind == "android" else None, **consent))
        if payload.master_enabled is False or payload.study_enabled is False:
            from app.services.smart_reminder_lifecycle import SmartReminderLifecycleService
            lifecycle = SmartReminderLifecycleService(self.session)
            await lifecycle.invalidate(actor.user_id, reason="study_off", advance=False)
            if payload.master_enabled is False:
                await lifecycle.disable_legacy(actor.user_id)
            else:
                await lifecycle.disable_legacy(actor.user_id,
                    channel="android" if actor.kind == "android" else "telegram",
                    device_id=actor.device_id if actor.kind == "android" else None)
        await self.session.execute(insert(MUTATION).values(
            user_id=actor.user_id, request_id=payload.request_id, actor_key=actor.key,
            body_sha256=digest, applied_revision=revision + 1))
        return self._ack(payload.request_id, revision + 1), True

    @staticmethod
    def _ack(request_id, revision):
        return {"ok": True, "request_id": request_id, "applied_revision": revision, "dispatch_allowed": False}

    async def bot_time(self, actor, *, nonce, binding, selected):
        """None means legacy account; False is exact retry, True is new intent."""
        with self.session.no_autoflush:
            await self._lock(actor)
            row = await self._preference(actor.user_id)
            if row is None:
                return None
            if (not isinstance(binding, dict) or binding.get("user_id") != actor.user_id
                    or not nonce or nonce != binding.get("nonce") or type(binding.get("revision")) is not int):
                raise SmartReminderError("smart_interaction_stale", 409)
            if row["master_enabled"] is False:
                raise SmartReminderError("smart_master_off", 409)
            if row["time_mode"] == "manual_locked":
                raise SmartReminderError("smart_manual_time_locked", 409)
            from uuid import UUID
            try:
                payload = SmartReminderPatch(request_id=str(UUID(nonce)), expected_revision=binding["revision"], study_enabled=True)
            except ValueError:
                raise SmartReminderError("smart_interaction_stale", 409) from None
            _, applied = await self._mutate(actor, payload, bot_time=selected)
            return applied
