"""Authenticated, audited first-party inbox triage. NEVER part of external MCP."""
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from typing import Literal
from sqlalchemy import or_, select, and_

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_inbox import RowId, Source, source_eligible, source_timestamp
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_step_up import _locked_session
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage, AdminPwaInboxTriageAudit
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.admin_api.pwa_push_outbox import enqueue_important_triage
from app.services.admin_feedback_resolution import enqueue_android_fix_notice
from app.services.android_release_service import AndroidReleaseService
from app.db.models.bot_feedback import BotFeedback
from app.db.models.payment import Payment
from app.db.models.message import Message
from app.db.models.release_feedback import ReleaseFeedbackResponse

logger = logging.getLogger(__name__)
_OPERATIONS = ("mark_read", "assign_self", "resolve", "resolve_fixed", "reopen", "mark_important", "clear_important")
_SOURCES = {"bot": BotFeedback, "release": ReleaseFeedbackResponse, "android": AdminPwaNativeReport, "payment": Payment, "technical": Message}


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source: Source
    source_id: RowId
    operation: str = Field(pattern=r"^(mark_read|assign_self|resolve|resolve_fixed|reopen|mark_important|clear_important)$")
    expected_revision: int = Field(strict=True, ge=0, le=2_147_483_646)
    fix_kind: Literal["server", "app_update"] | None = None

    @model_validator(mode="after")
    def fix_only_for_android(self):
        if self.operation == "resolve_fixed":
            if self.source != "android" or self.fix_kind is None:
                raise ValueError("fix notice requires an Android report and fix kind")
        elif self.fix_kind is not None:
            raise ValueError("fix kind must only accompany resolve_fixed")
        return self


class MarkAllReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    cutoff: str | None = Field(default=None, max_length=40)

    @field_validator("cutoff")
    @classmethod
    def valid_cutoff(cls, value):
        if value is None:
            return None
        if len(value) < 20:
            raise ValueError("invalid timestamp")
        timestamp = datetime.fromisoformat(value)
        if timestamp.utcoffset() is None:
            raise ValueError("timezone required")
        return value


async def mark_unread_batch(db, *, session_cookie, settings_obj, command, now=None):
    """One authorized, bounded, audited batch. Never delete original reports.

    Only rows created/submitted before the first request's server cutoff are
    touched; new alerts arriving during the operation stay unread.
    """
    if not getattr(settings_obj, "ADMIN_PWA_ENABLED", False):
        return None
    stamp = _utc(now or datetime.now(timezone.utc))
    cutoff = _utc(datetime.fromisoformat(command.cutoff)) if command.cutoff else stamp
    if cutoff > stamp:
        raise TriageConflict()
    batch_limit = 200
    modified = 0
    async with db.begin():
        pair = await _locked_session(db, session_cookie, settings_obj, stamp)
        if pair is None:
            return None
        _, actor = pair
        for source, model in _SOURCES.items():
            if modified >= batch_limit:
                break
            row_ids = (await db.execute(
                select(model.id).outerjoin(
                    AdminPwaInboxTriage,
                    and_(AdminPwaInboxTriage.source == source,
                         AdminPwaInboxTriage.source_id == model.id),
                ).where(
                    source_eligible(source, stamp),
                    source_timestamp(source) <= cutoff,
                    or_(AdminPwaInboxTriage.status.is_(None),
                        AdminPwaInboxTriage.status == "new"),
                ).order_by(model.id.desc()).limit(batch_limit - modified)
                .with_for_update(of=model)
            )).scalars().all()
            for source_id in row_ids:
                key = (source, source_id)
                triage = await db.get(AdminPwaInboxTriage, key, with_for_update=True)
                if triage is not None and triage.status != "new":
                    continue
                if triage is None:
                    triage = AdminPwaInboxTriage(
                        source=source, source_id=source_id, status="read",
                        priority="important" if source in ("payment", "android", "technical") else "normal",
                        revision=1, read_at=stamp, updated_at=stamp,
                        updated_by_user_id=int(actor.id),
                    )
                    db.add(triage)
                else:
                    triage.status = "read"
                    triage.read_at = triage.read_at or stamp
                    triage.updated_at = stamp
                    triage.updated_by_user_id = int(actor.id)
                    triage.revision += 1
                db.add(AdminPwaInboxTriageAudit(
                    id=str(uuid4()), source=source, source_id=source_id,
                    operation="mark_read", actor_user_id=int(actor.id), created_at=stamp,
                ))
                modified += 1
        await db.flush()
        has_more = False
        for source, model in _SOURCES.items():
            left = await db.scalar(
                select(model.id).outerjoin(
                    AdminPwaInboxTriage,
                    and_(AdminPwaInboxTriage.source == source,
                         AdminPwaInboxTriage.source_id == model.id),
                ).where(
                    source_eligible(source, stamp),
                    source_timestamp(source) <= cutoff,
                    or_(AdminPwaInboxTriage.status.is_(None),
                        AdminPwaInboxTriage.status == "new"),
                ).limit(1)
            )
            if left is not None:
                has_more = True
                break
    return {"updated": modified, "has_more": has_more,
            "cutoff": cutoff.isoformat()}


class TriageConflict(Exception):
    pass


async def mutate_triage(db, *, session_cookie, command, settings_obj, now=None):
    """One source-locked, session-locked transaction, triage+audit atomic.

    No arbitrary assignee ID or underlying feedback edits are accepted. Only a
    current canonical admin with a WebAuthn-authenticated browser session may
    mutate, even if a legacy Google+Telegram onboarding cookie still exists.
    """
    if not getattr(settings_obj, "ADMIN_PWA_ENABLED", False):
        return None
    stamp = _utc(now or datetime.now(timezone.utc))
    async with db.begin():
        pair = await _locked_session(db, session_cookie, settings_obj, stamp)
        if pair is None:
            return None
        _, actor = pair
        if command.source == "technical":
            # Message.content holds raw stack, URL and user input. Restrict
            # the locked projection to the ID of an eligible recent marker.
            # Never hydrate the raw Message ORM row during Inbox triage.
            eligible_id = await db.scalar(select(Message.id).where(
                Message.id == command.source_id,
                Message.role == "assistant",
                Message.content_type == "app_error_context",
                Message.created_at >= stamp - timedelta(days=30),
                Message.created_at <= stamp,
            ).with_for_update())
            if eligible_id is None:
                return None
            source_row = None
        else:
            # Lock only authoritative eligibility metadata. Triage never needs
            # feedback text, Telegram media IDs for Bot/Release, or the native
            # screenshot BLOB; loading those on each action adds avoidable IO.
            model = _SOURCES[command.source]
            columns = [model.id]
            if command.source == "android":
                columns.extend((model.expires_at, model.user_id, model.app_version))
            elif command.source == "payment":
                columns.extend((model.payment_status, model.screenshot_file_id))
            source_row = (await db.execute(select(*columns).where(
                model.id == command.source_id).with_for_update())).one_or_none()
            if source_row is None or (command.source == "android" and
                                      _utc(source_row.expires_at) <= stamp):
                # Do not disclose whether an unseen source ID exists.
                return None
        if command.source == "payment":
            # Inbox read-state cannot approve/reject a receipt; financial
            # decisions stay in the separately signed payment review flow.
            if (command.operation != "mark_read" or source_row.payment_status != "pending"
                    or not source_row.screenshot_file_id):
                raise TriageConflict()
        key = (command.source, command.source_id)
        row = await db.get(AdminPwaInboxTriage, key, with_for_update=True)
        revision = row.revision if row else 0
        if revision != command.expected_revision:
            raise TriageConflict()
        if row is None:
            row = AdminPwaInboxTriage(
                source=command.source, source_id=command.source_id,
                status="new", priority=("important" if command.source in ("payment", "android", "technical") else "normal"), revision=0, updated_at=stamp,
            )
            db.add(row)
        previous = (row.status, row.priority, row.assigned_to_user_id, row.read_at, row.resolved_at)
        if command.operation == "mark_read":
            if row.read_at is None:
                row.read_at = stamp
            if row.status == "new":
                row.status = "read"
        elif command.operation == "assign_self":
            if row.status == "resolved":
                raise TriageConflict()
            row.assigned_to_user_id = int(actor.id)
            row.read_at = row.read_at or stamp
            row.status = "assigned"
        elif command.operation in ("resolve", "resolve_fixed"):
            if command.operation == "resolve_fixed":
                if row.status == "resolved":
                    raise TriageConflict()
                if command.fix_kind == "app_update":
                    # Never claim an APK-only bug is fixed until a genuinely
                    # downloadable newer release is live on the update endpoint.
                    release = await AndroidReleaseService(db).serve()
                    if (release is None or not release.can_self_update or
                            release.version_name == source_row.app_version):
                        raise TriageConflict()
            row.read_at = row.read_at or stamp
            row.status = "resolved"
            row.resolved_at = row.resolved_at or stamp
        elif command.operation == "reopen":
            if row.status != "resolved":
                raise TriageConflict()
            row.resolved_at = None
            row.status = "assigned" if row.assigned_to_user_id else "read"
        elif command.operation == "mark_important":
            row.priority = "important"
        elif command.operation == "clear_important":
            row.priority = "normal"
        else:
            raise TriageConflict()
        current = (row.status, row.priority, row.assigned_to_user_id, row.read_at, row.resolved_at)
        if previous != current:
            row.updated_at = stamp
            row.updated_by_user_id = int(actor.id)
            row.revision = revision + 1
            db.add(AdminPwaInboxTriageAudit(
                id=str(uuid4()), source=command.source, source_id=command.source_id,
                operation="resolve" if command.operation == "resolve_fixed" else command.operation,
                actor_user_id=int(actor.id), created_at=stamp,
            ))
            await db.flush()
            if command.operation == "resolve_fixed":
                await enqueue_android_fix_notice(
                    db, user_id=source_row.user_id, source_id=command.source_id,
                    revision=row.revision, mode=command.fix_kind, now=stamp,
                )
            if command.operation == "mark_important" and previous[1] != "important":
                await enqueue_important_triage(
                    db, settings_obj=settings_obj, actor_id=int(actor.id),
                    source=command.source, source_id=command.source_id,
                    revision=row.revision, now=stamp,
                )
        else:
            # New no-op states should never persist a misleading triage row.
            if not revision:
                db.expunge(row)
        return {
            "source": command.source, "source_id": command.source_id, "status": row.status,
            "priority": row.priority, "assigned_to_user_id": row.assigned_to_user_id,
            "read_at": _utc(row.read_at).isoformat() if row.read_at else None,
            "resolved_at": _utc(row.resolved_at).isoformat() if row.resolved_at else None,
            "revision": row.revision,
            "notice_queued": command.operation == "resolve_fixed" and previous != current,
        }


def create_admin_pwa_inbox_triage_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-inbox-triage"])

    @router.post("/api/admin/v1/inbox/mark-all-read")
    async def mark_all_read(request: Request):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            command = MarkAllReadRequest.model_validate(await _body(request, 1024))
        except (ValidationError, ValueError):
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                result = await mark_unread_batch(
                    db, session_cookie=cookie, settings_obj=settings_obj, command=command)
        except TriageConflict:
            return _reply(409, "admin_pwa_inbox_changed")
        except Exception:
            logger.error("Admin PWA inbox bulk read unavailable")
            return _reply(503, "admin_pwa_inbox_unavailable")
        if result is None:
            return _reply(403, "admin_pwa_inbox_denied")
        return JSONResponse({"ok": True, **result}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/inbox/triage")
    async def triage(request: Request):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            command = TriageRequest.model_validate(await _body(request, 1024))
        except ValidationError:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                result = await mutate_triage(
                    db, session_cookie=cookie, command=command, settings_obj=settings_obj)
        except TriageConflict:
            return _reply(409, "admin_pwa_inbox_changed")
        except Exception:
            # Do not log user content or source identifiers.
            logger.error("Admin PWA inbox triage unavailable")
            return _reply(503, "admin_pwa_inbox_unavailable")
        if result is None:
            return _reply(403, "admin_pwa_inbox_denied")
        return JSONResponse({"ok": True, **result}, headers=_PRIVATE_HEADERS)

    return router
