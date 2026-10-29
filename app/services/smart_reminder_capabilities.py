"""Own-device study observations only; no consent, cohort, job or posting grant.

The caller owns the transaction. User-first locking and generation CAS protect
a fresh denial from a late allow response. Facts expire with verified auth;
expiry/unknown never erase the last known denial at the legacy sender veto.
"""
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from sqlalchemy import insert, select, update

from app.db.models.desktop import DesktopSession
from app.db.models.smart_reminder import SmartReminderCapability
from app.services.smart_reminder_lifecycle import SmartReminderLifecycleService
from app.services.smart_reminder_preferences import (
    MAX_REVISION, SmartReminderError, SmartReminderPreferencesService, _utc,
)

CAP = SmartReminderCapability.__table__


class SmartCapabilityPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_generation: StrictInt = Field(ge=0, lt=MAX_REVISION)
    protocol_version: StrictInt = Field(ge=0, le=1)
    autonomous_study_disabled: StrictBool | None
    study_notifications_allowed: StrictBool | None


class SmartReminderCapabilityService:
    def __init__(self, session):
        self.session = session

    async def _locked(self, actor):
        if actor.kind != "android":
            raise SmartReminderError("android_device_required", 403)
        # Recheck account/deletion and device/session ownership after User lock.
        await SmartReminderPreferencesService(self.session)._lock(actor)
        return (await self.session.execute(select(CAP).where(
            CAP.c.device_id == actor.device_id).with_for_update())).mappings().one_or_none()

    @staticmethod
    def _view(actor, row, now):
        if row is not None and row["user_id"] != actor.user_id:
            raise SmartReminderError("smart_capability_owner_conflict", 409)
        return {
            "ok": True, "version": 1,
            "generation": row["generation"] if row else 0,
            "protocol_version": row["protocol_version"] if row else 0,
            "autonomous_study_disabled": row["autonomous_study_disabled"] if row else None,
            "study_notifications_allowed": row["study_notifications_allowed"] if row else None,
            "observed_at": _utc(row["observed_at"]).isoformat() if row and row["observed_at"] else None,
            "expires_at": _utc(row["expires_at"]).isoformat() if row and row["expires_at"] else None,
            "fresh": bool(row and row["observed_at"] and row["expires_at"] and
                _utc(row["observed_at"]) <= now < _utc(row["expires_at"])),
            "observation_only": True, "dispatch_allowed": False,
        }

    async def read(self, actor):
        with self.session.no_autoflush:
            row = await self._locked(actor)
            return self._view(actor, row, datetime.now(timezone.utc))

    async def patch(self, actor, payload: SmartCapabilityPatch):
        with self.session.no_autoflush:
            old = await self._locked(actor)
            now = datetime.now(timezone.utc)
            self._view(actor, old, now)  # Never overwrite an inconsistent owner.
            generation = old["generation"] if old else 0
            if payload.expected_generation != generation or generation >= MAX_REVISION:
                raise SmartReminderError("smart_capability_generation_conflict", 409)
            if old and old["study_notifications_allowed"] is False and payload.study_notifications_allowed is None:
                raise SmartReminderError("smart_capability_denial_unresolved", 409)
            deadline = actor.access_expires_at
            if not isinstance(deadline, datetime) or deadline.tzinfo is None:
                raise SmartReminderError("smart_auth_required", 401)
            session_deadline = await self.session.scalar(select(DesktopSession.expires_at).where(
                DesktopSession.id == actor.session_id, DesktopSession.device_id == actor.device_id))
            until = min(_utc(deadline), _utc(session_deadline))
            if until <= now:
                raise SmartReminderError("smart_session_revoked", 401)
            values = dict(protocol_version=payload.protocol_version, generation=generation + 1,
                autonomous_study_disabled=payload.autonomous_study_disabled,
                study_notifications_allowed=payload.study_notifications_allowed,
                observed_at=now, expires_at=until)
            if old is None:
                await self.session.execute(insert(CAP).values(device_id=actor.device_id,
                    user_id=actor.user_id, **values))
            else:
                await self.session.execute(update(CAP).where(CAP.c.device_id == actor.device_id,
                    CAP.c.user_id == actor.user_id).values(**values))
            # Losing any prerequisite revokes existing pending authority, but
            # changes no ON/OFF intent and never relabels externalized attempts.
            lost = any(values[k] != (old[k] if old else None) for k in (
                "protocol_version", "autonomous_study_disabled", "study_notifications_allowed"))
            usable = (payload.protocol_version == 1 and payload.autonomous_study_disabled is True and
                      payload.study_notifications_allowed is True)
            if lost and not usable:
                await SmartReminderLifecycleService(self.session).invalidate(actor.user_id,
                    reason="android_study_capability_lost", advance=True)
            return self._view(actor, {"user_id": actor.user_id, **values}, datetime.now(timezone.utc))
