"""Versioned, additive legacy import. Internal only; never a send permission.

The caller authorizes the canonical account and commits/rolls back the whole
transaction. All Smart writers must lock User first, including OFF/deletion.
There is deliberately no API, startup/batch caller, provider or implicit flush.
"""

from dataclasses import dataclass, field
from datetime import time

from sqlalchemy import func, insert, select, update

from app.db.models.smart_reminder import SmartReminderConsent, SmartReminderPreference
from app.db.models.user import User
from app.services.smart_reminder_legacy_evidence import (
    LegacyEvidenceUnavailable, SmartReminderLegacyEvidenceService,
)


BACKFILL_VERSION = 1
SUPPORTED_EVIDENCE_VERSION = 1
PREF = SmartReminderPreference.__table__
CONSENT = SmartReminderConsent.__table__


@dataclass(frozen=True)
class LegacyBackfillResult:
    status: str
    migration_version: int
    revision: int
    inserted_consents: int = 0
    dispatch_allowed: bool = field(default=False, init=False)


def _has_intent(row) -> bool:
    return (
        row["master_enabled"] is not None or row["revision"] != 0
        or row["grant_epoch"] != 0 or row["time_mode"] != "auto"
        or row["channel_mode"] != "auto"
        or any(row[key] is not None for key in (
            "manual_time_local", "timezone_name", "preferred_channel",
            "quiet_start", "quiet_end", "pause_until", "action_source", "action_at",
        ))
    )


class SmartReminderLegacyBackfillService:
    def __init__(self, session):
        self.session = session

    async def backfill(self, user_id: int) -> LegacyBackfillResult:
        if type(user_id) is not int or user_id <= 0:
            raise LegacyEvidenceUnavailable("canonical_user_id_required")
        # Core projections/mutations avoid stale ORM state and never autoflush
        # unrelated pending writes. PostgreSQL serializes imports on this owner.
        with self.session.no_autoflush:
            owner = await self.session.scalar(select(User.id).where(
                User.id == user_id).with_for_update())
            if owner is None:
                raise LegacyEvidenceUnavailable("account_not_found")
            evidence = await SmartReminderLegacyEvidenceService(self.session).snapshot(user_id)
            if evidence.evidence_version != SUPPORTED_EVIDENCE_VERSION:
                raise LegacyEvidenceUnavailable("evidence_version_unsupported")
            row = (await self.session.execute(select(PREF).where(
                PREF.c.user_id == user_id).with_for_update())).mappings().one_or_none()
            if row is not None:
                if row["migration_version"] >= BACKFILL_VERSION:
                    return LegacyBackfillResult("already_current", row["migration_version"], row["revision"])
                if _has_intent(row):
                    return LegacyBackfillResult("intent_preserved", row["migration_version"], row["revision"])

            channels = set((await self.session.scalars(select(CONSENT.c.channel).where(
                CONSENT.c.user_id == user_id))).all())
            values = dict(migration_version=BACKFILL_VERSION, revision=1)
            telegram = evidence.telegram
            if (telegram.saved_time_local is not None and
                    (row is None or (row["legacy_time_local"] is None and
                                     row["legacy_offset_minutes"] is None))):
                try:
                    saved = time.fromisoformat(telegram.saved_time_local)
                except ValueError:
                    raise LegacyEvidenceUnavailable("legacy_time_invalid") from None
                if saved.tzinfo is not None:
                    raise LegacyEvidenceUnavailable("legacy_time_invalid")
                values.update(legacy_time_local=saved, legacy_offset_minutes=telegram.saved_offset_minutes)

            consents = []
            if "telegram" not in channels and (telegram.transport_present or telegram.setting_enabled is not None):
                consents.append(dict(
                    user_id=user_id, channel="telegram", source_key="legacy_course_v1",
                    state={"legacy_on": "on", "not_enabled": "off"}.get(telegram.study_state, "unknown"),
                    source="legacy_course_snapshot", evidence_version=SUPPORTED_EVIDENCE_VERSION,
                ))
            if "android" not in channels:
                for device in evidence.android:
                    mirror = {True: "on", False: "off", None: "missing"}[device.mirrored_setting_enabled]
                    consents.append(dict(
                        user_id=user_id, channel="android", device_id=device.device_id,
                        source_key="legacy_android:" + device.device_id, state="unknown",
                        source="legacy_android_mirror_" + mirror,
                        evidence_version=SUPPORTED_EVIDENCE_VERSION,
                    ))

            if row is None:
                await self.session.execute(insert(PREF).values(user_id=user_id, **values))
            else:
                changed = await self.session.execute(update(PREF).where(
                    PREF.c.user_id == user_id, PREF.c.revision == 0,
                    PREF.c.migration_version == row["migration_version"],
                ).values(**values, updated_at=func.now()))
                if changed.rowcount != 1:
                    raise LegacyEvidenceUnavailable("preference_revision_conflict")
            # Separate inserts preserve optional device_id defaults without
            # mixing missing and present parameters in an executemany mapping.
            for consent in consents:
                await self.session.execute(insert(CONSENT).values(**consent))
            return LegacyBackfillResult("applied", BACKFILL_VERSION, 1, len(consents))
