"""Authenticated Android-first bridge to the shared passive widget contract."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json

from app.services.smart_reminder_policy_context import (
    SmartReminderPolicyContextService, _personal_history_start, read_last_observed_learning,
)
from app.services.smart_reminder_policy import (
    APPROVED_HABIT_CALIBRATION, _aware_utc,
)
from app.services.smart_reminder_preferences import SmartReminderError, SmartReminderPreferencesService
from app.services.smart_widget_context import project_widget


class SmartWidgetContextService:
    def __init__(self, session, *, clock=None):
        self.session = session
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    async def project(self, actor, request, *, authenticated_until, expected_level):
        # User-first fresh P1 ownership, block/deletion and session validation;
        # no preference import, learning receipt, consent, job or provider IO.
        if actor.kind != "android":
            raise SmartReminderError("android_device_required", 403)
        authenticated_until = _aware_utc(authenticated_until)
        with self.session.no_autoflush:
            pref = await SmartReminderPreferencesService(self.session).read(actor)
            now = _aware_utc(self.clock())  # Never freeze a pre-lock clock.
            since = now - timedelta(days=APPROVED_HABIT_CALIBRATION.recent_calendar_days)
            if pref["timezone_name"]:
                try:
                    since = _personal_history_start(now, pref["timezone_name"],
                        APPROVED_HABIT_CALIBRATION.recent_calendar_days)
                except (ValueError, KeyError):
                    pass  # Unknown calendar/zone remains a policy veto.
            context = await SmartReminderPolicyContextService(self.session).load(
                actor, observed_at=now, history_since=since,
                expected_level=expected_level, personal_time=True,
            )
            if context.level != context.expected_level:
                raise SmartReminderError("course_context_changed", 409)
            last_observed = (await read_last_observed_learning(self.session, actor, self.clock())
                             if request.version == 2 else None)
            finished = _aware_utc(self.clock())
            if finished >= authenticated_until:
                raise SmartReminderError("widget_auth_expired", 401)
            # Opaque, non-authorizing correlation only; raw account/device/
            # session identifiers never enter widget snapshots or logs.
            binding = hashlib.sha256(json.dumps(
                ["smart-widget-context-v1", actor.user_id, actor.device_id, actor.session_id],
                separators=(",", ":"),
            ).encode()).hexdigest()
            projection = project_widget(replace(context, observed_at=finished), request=request,
                                  binding=binding, valid_until=authenticated_until,
                                  calibration=APPROVED_HABIT_CALIBRATION)
            if request.version == 2:
                projection = type(projection).model_validate(
                    projection.model_dump() | {'last_observed_study_at': last_observed}, strict=True)
            return projection.model_dump(mode='json')
