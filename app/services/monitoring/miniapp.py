"""Additive monitoring adapter for the existing signed Mini App transport."""
import asyncio
import logging
from uuid import uuid4

from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.monitoring import catalog
from app.services.monitoring.intake import (
    IntakeBusy, IntakeRejected, bound_write, current_mode, diagnostic_slot, ingest, is_owner_account, parse_batch,
)
from app.services.user_access_state_service import UserAccessState, UserAccessStateService

logger = logging.getLogger(__name__)
PAUSED = {"ok": True, "accepted": 0, "paused": True}
_legacy_tasks = set()


def enabled(settings):
    return bool(getattr(settings, "MONITORING_MINIAPP_ADAPTER_ENABLED", False)) and current_mode(settings) != "off"


async def record_client_batch(db, *, telegram_id, payload, settings):
    """Caller supplies only a freshly verified Telegram identity."""
    if not enabled(settings):
        return PAUSED
    try:
        # Ignore legacy top-level user_id/telegram_id metadata, never owner
        # claims inside the diagnostic event DTO.
        if set(payload) - {"event", "schema", "events", "user_id", "telegram_id"}:
            raise IntakeRejected("forbidden_field")
        events, rejected = parse_batch({key: payload.get(key) for key in ("schema", "events")}, platform="telegram")
        user = await UserRepository(db).get_by_telegram_id(telegram_id)
        if user is None or UserAccessStateService.classify(user) == UserAccessState.BLOCKED:
            return {"ok": False, "error": "diagnostic_session_required"}
        result = await ingest(db, owner_user_id=user.id, events=events, mode=current_mode(settings),
                              owner_admitted=is_owner_account(settings, user.telegram_id), settings_obj=settings)
        result.rejected += rejected
        await db.commit()
        return {"ok": True, **result.response()}
    except IntakeRejected as exc:
        return {"ok": False, "error": exc.code}


def queue_legacy_onboarding(session_factory, *, owner_user_id, payload, settings):
    """Mirror the fixed Inbox classifications without copying legacy content."""
    if (not enabled(settings) or (payload.get("source") or payload.get("error_source")) != "course_v3_onboarding"
            or (payload.get("error_name") or payload.get("name")) != "OnboardingSaveResponseError"):
        return
    code = payload.get("error_message") or payload.get("message")
    site = ("onboarding_timeout" if code == "onboarding_save_timeout" else
            "onboarding_placement" if code == "course_level_change_requires_placement" else "onboarding_save")
    extra = payload.get("extra")
    event = {"event_id": str(uuid4()), "feature_code": "onboarding_activation",
             "failure_code": "save_unconfirmed", "site_code": site,
             "outcome": "recovered" if isinstance(extra, dict) and extra.get("recovered") is True else "failed"}
    if len(_legacy_tasks) >= catalog.BACKEND_PENDING_FINGERPRINTS:
        from app.services.monitoring.backend import reporter
        reporter.dropped += 1
        return
    # Snapshot only fixed codes and the canonical user ID from the committed
    # legacy write. Never put the original legacy payload in a background task.
    task = asyncio.create_task(_record_legacy(session_factory, owner_user_id, event, settings))
    _legacy_tasks.add(task)
    task.add_done_callback(_legacy_tasks.discard)


async def _record_legacy(session_factory, owner_user_id, event, settings):
    from app.services.monitoring.backend import reporter

    if not enabled(settings):
        return
    try:
        with diagnostic_slot(settings):
            async with session_factory() as db, db.begin():
                await bound_write(db)
                user = await db.get(User, owner_user_id)
                if user is None or UserAccessStateService.classify(user) == UserAccessState.BLOCKED:
                    return
                events, _ = parse_batch({"schema": catalog.SCHEMA, "events": [event]}, platform="telegram")
                await ingest(db, owner_user_id=user.id, events=events, mode=current_mode(settings),
                             owner_admitted=is_owner_account(settings, user.telegram_id), settings_obj=settings)
    except IntakeBusy:
        reporter.dropped += 1
    except Exception:
        reporter.dropped += 1
        logger.warning("Mini App legacy diagnostic adapter failed")


async def drain_legacy():
    if _legacy_tasks:
        await asyncio.gather(*tuple(_legacy_tasks), return_exceptions=True)
