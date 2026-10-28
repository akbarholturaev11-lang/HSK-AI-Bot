"""Authenticated Android-first bridge to the shared passive widget contract."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json

from app.services.smart_reminder_policy_context import SmartReminderPolicyContextService
from app.services.smart_reminder_policy import _aware_utc
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
            await SmartReminderPreferencesService(self.session)._lock(actor)
            now = _aware_utc(self.clock())  # Never freeze a pre-lock clock.
            context = await SmartReminderPolicyContextService(self.session).load(
                actor, observed_at=now,
                history_since=now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7),
                expected_level=expected_level,
            )
            if context.level != context.expected_level:
                raise SmartReminderError("course_context_changed", 409)
            finished = _aware_utc(self.clock())
            if finished >= authenticated_until:
                raise SmartReminderError("widget_auth_expired", 401)
            # Opaque, non-authorizing correlation only; raw account/device/
            # session identifiers never enter widget snapshots or logs.
            binding = hashlib.sha256(json.dumps(
                ["smart-widget-context-v1", actor.user_id, actor.device_id, actor.session_id],
                separators=(",", ":"),
            ).encode()).hexdigest()
            return project_widget(replace(context, observed_at=finished), request=request,
                                  binding=binding, valid_until=authenticated_until).model_dump(mode="json")
