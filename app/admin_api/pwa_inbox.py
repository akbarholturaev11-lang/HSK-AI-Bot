"""Bounded, read-only unified Admin PWA inbox; no remote MCP or attachment access.

This projection does not invent triage state and deliberately keeps historical
Android reports that were never stored outside its claimed coverage.
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import String, and_, func, or_, select

from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.message import Message
from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage
from app.db.models.bot_feedback import BotFeedback
from app.db.models.payment import Payment
from app.db.models.release_feedback import ReleaseFeedbackResponse
from app.db.models.user import User

Source = Literal["bot", "release", "android", "payment"]
RowId = Annotated[int, Field(strict=True, ge=1, le=2_147_483_647)]
_RANK = {"technical": 5, "payment": 4, "android": 3, "release": 2, "bot": 1}
_MAX_MESSAGE = 2000


class InboxCursor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    created_at: datetime
    source: Literal["bot", "release", "android", "payment", "technical"]
    source_id: RowId

    @field_validator("created_at", mode="before")
    @classmethod
    def require_timezone(cls, value):
        # The HTTP body has already been JSON-decoded into Python strings.
        # Strict Pydantic datetime otherwise rejects our own ISO cursor.
        if not isinstance(value, str) or not 20 <= len(value) <= 40:
            raise ValueError("Cursor must be a bounded ISO 8601 string")
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Cursor must include a timezone")
        return parsed.astimezone(timezone.utc)


class InboxRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source: Literal["all", "bot", "release", "android", "payment", "technical"] = "all"
    priority: Literal["all", "important"] = "all"
    user_id: RowId | None = None
    search: str | None = Field(default=None, min_length=3, max_length=80)
    limit: Annotated[int, Field(strict=True, ge=1, le=50)] = 30
    before: InboxCursor | None = None

    @field_validator("search")
    @classmethod
    def bound_search(cls, value):
        if value is None:
            return None
        value = value.strip()
        if not 3 <= len(value) <= 80 or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("Search must be 3–80 printable characters")
        return value


def _literal_contains(column, needle):
    # Explicit ESCAPE ensures %, _ and backslash in user input are literal.
    escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.ilike(f"%{escaped}%", escape="\\")


def _search_payment_id(value):
    # Numeric IDs only; never search payment notes, account/bank data or receipts.
    digits = value.removeprefix("#")
    return int(digits) if digits.isascii() and digits.isdecimal() and len(digits) <= 10 else None


def _utc(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _before(query, timestamp, row_id, source, cursor):
    if cursor is None:
        return query
    rank = _RANK[source]
    anchor_rank = _RANK[cursor.source]
    anchor = cursor.created_at
    # Global cursor ordering is (timestamp DESC, source rank DESC, id DESC).
    if rank > anchor_rank:
        return query.where(timestamp < anchor)
    if rank < anchor_rank:
        return query.where(timestamp <= anchor)
    return query.where(or_(timestamp < anchor, and_(timestamp == anchor, row_id < cursor.source_id)))


def _triage(row):
    return {
        "triage_status": row.triage_status or "new",
        "triage_priority": row.triage_priority or ("important" if row.source_type in ("payment", "android", "technical") else "normal"),
        "triage_assigned_to": row.triage_assignee,
        "triage_read_at": _utc(row.triage_read_at).isoformat() if row.triage_read_at else None,
        "triage_resolved_at": _utc(row.triage_resolved_at).isoformat() if row.triage_resolved_at else None,
        "triage_revision": row.triage_revision or 0,
    }


async def unified_inbox(db, request: InboxRequest):
    """Read <= limit+1 per source, merge bounded rows with a stable cursor.

    No screenshot bytes, Telegram attachment IDs, raw Telegram IDs or other
    account identifiers are returned. Source-specific delivery state is NOT
    a fabricated inbox read/assigned/resolved status.
    """
    now = datetime.now(timezone.utc)
    sources = tuple(_RANK) if request.source == "all" else (request.source,)
    gathered = []
    take = request.limit + 1
    search_start = now - timedelta(days=30) if request.search is not None else None

    if "bot" in sources:
        stamp = func.coalesce(BotFeedback.completed_at, BotFeedback.created_at)
        query = select(
            BotFeedback.id.label("source_id"), stamp.label("created_at"),
            func.cast("bot", String).label("source_type"),
            User.id.label("user_id"),
            func.substr(func.coalesce(BotFeedback.disliked_text, BotFeedback.liked_text,
                                      BotFeedback.disliked_code, BotFeedback.liked_code), 1,
                        _MAX_MESSAGE).label("message"),
            BotFeedback.disliked_attachment_file_id.is_not(None).label("has_attachment"),
            and_(BotFeedback.disliked_attachment_file_id.is_not(None),
                 BotFeedback.disliked_attachment_type.in_(("photo", "document")),
                 User.id.is_not(None)).label("image_preview_available"),
            BotFeedback.status.label("feedback_status"),
            AdminPwaInboxTriage.status.label("triage_status"),
            AdminPwaInboxTriage.priority.label("triage_priority"),
            AdminPwaInboxTriage.assigned_to_user_id.label("triage_assignee"),
            AdminPwaInboxTriage.read_at.label("triage_read_at"),
            AdminPwaInboxTriage.resolved_at.label("triage_resolved_at"),
            AdminPwaInboxTriage.revision.label("triage_revision"),
        ).outerjoin(AdminPwaInboxTriage, and_(
            AdminPwaInboxTriage.source == "bot",
            AdminPwaInboxTriage.source_id == BotFeedback.id)).outerjoin(User, User.id == BotFeedback.user_id)
        if request.priority == "important":
            query = query.where(AdminPwaInboxTriage.priority == "important")
        if request.user_id is not None:
            query = query.where(User.id == request.user_id)
        if request.search is not None:
            visible_text = func.coalesce(BotFeedback.disliked_text, BotFeedback.liked_text,
                                         BotFeedback.disliked_code, BotFeedback.liked_code)
            query = query.where(stamp >= search_start, _literal_contains(visible_text, request.search))
        query = _before(query, stamp, BotFeedback.id, "bot", request.before)
        rows = (await db.execute(query.order_by(stamp.desc(), BotFeedback.id.desc()).limit(take))).all()
        for row in rows:
            gathered.append({
                "source": "bot", "source_id": row.source_id, "created_at": _utc(row.created_at),
                "user_id": row.user_id, "message": row.message, "has_attachment": row.has_attachment,
                "image_preview_available": bool(row.image_preview_available),
                "feedback_status": row.feedback_status,
                **_triage(row),
                "rating": None, "notification_delivery": None, "app_version": None, "screen": None,
            })

    if "release" in sources:
        stamp = ReleaseFeedbackResponse.completed_at
        query = select(
            ReleaseFeedbackResponse.id.label("source_id"), stamp.label("created_at"),
            func.cast("release", String).label("source_type"),
            User.id.label("user_id"),
            func.substr(ReleaseFeedbackResponse.comment_text, 1, _MAX_MESSAGE).label("message"),
            ReleaseFeedbackResponse.attachment_file_id.is_not(None).label("has_attachment"),
            and_(ReleaseFeedbackResponse.attachment_file_id.is_not(None),
                 ReleaseFeedbackResponse.attachment_type.in_(("photo", "document")),
                 User.id.is_not(None)).label("image_preview_available"),
            ReleaseFeedbackResponse.rating.label("rating"),
            AdminPwaInboxTriage.status.label("triage_status"),
            AdminPwaInboxTriage.priority.label("triage_priority"),
            AdminPwaInboxTriage.assigned_to_user_id.label("triage_assignee"),
            AdminPwaInboxTriage.read_at.label("triage_read_at"),
            AdminPwaInboxTriage.resolved_at.label("triage_resolved_at"),
            AdminPwaInboxTriage.revision.label("triage_revision"),
        ).outerjoin(AdminPwaInboxTriage, and_(
            AdminPwaInboxTriage.source == "release",
            AdminPwaInboxTriage.source_id == ReleaseFeedbackResponse.id)).outerjoin(User, and_(User.telegram_id > 0,
                                User.telegram_id == ReleaseFeedbackResponse.user_telegram_id))
        if request.priority == "important":
            query = query.where(AdminPwaInboxTriage.priority == "important")
        if request.user_id is not None:
            query = query.where(User.id == request.user_id)
        if request.search is not None:
            query = query.where(stamp >= search_start,
                                _literal_contains(ReleaseFeedbackResponse.comment_text, request.search))
        query = _before(query, stamp, ReleaseFeedbackResponse.id, "release", request.before)
        rows = (await db.execute(query.order_by(stamp.desc(),
                                                ReleaseFeedbackResponse.id.desc()).limit(take))).all()
        for row in rows:
            gathered.append({
                "source": "release", "source_id": row.source_id, "created_at": _utc(row.created_at),
                "user_id": row.user_id, "message": row.message, "has_attachment": row.has_attachment,
                "image_preview_available": bool(row.image_preview_available),
                "feedback_status": None, "rating": row.rating, "notification_delivery": None,
                **_triage(row),
                "app_version": None, "screen": None,
            })

    if "android" in sources:
        stamp = AdminPwaNativeReport.created_at
        query = select(
            AdminPwaNativeReport.id.label("source_id"), stamp.label("created_at"),
            func.cast("android", String).label("source_type"),
            AdminPwaNativeReport.user_id.label("user_id"),
            func.substr(AdminPwaNativeReport.description, 1, _MAX_MESSAGE).label("message"),
            AdminPwaNativeReport.attachment_bytes.is_not(None).label("has_attachment"),
            AdminPwaNativeReport.notification_state.label("notification_delivery"),
            AdminPwaNativeReport.app_version.label("app_version"),
            AdminPwaNativeReport.screen.label("screen"),
            AdminPwaInboxTriage.status.label("triage_status"),
            AdminPwaInboxTriage.priority.label("triage_priority"),
            AdminPwaInboxTriage.assigned_to_user_id.label("triage_assignee"),
            AdminPwaInboxTriage.read_at.label("triage_read_at"),
            AdminPwaInboxTriage.resolved_at.label("triage_resolved_at"),
            AdminPwaInboxTriage.revision.label("triage_revision"),
        ).outerjoin(AdminPwaInboxTriage, and_(
            AdminPwaInboxTriage.source == "android",
            AdminPwaInboxTriage.source_id == AdminPwaNativeReport.id)).where(AdminPwaNativeReport.expires_at > now)
        if request.priority == "important":
            query = query.where(func.coalesce(AdminPwaInboxTriage.priority, "important") == "important")
        if request.user_id is not None:
            query = query.where(AdminPwaNativeReport.user_id == request.user_id)
        if request.search is not None:
            query = query.where(stamp >= search_start,
                                _literal_contains(AdminPwaNativeReport.description, request.search))
        query = _before(query, stamp, AdminPwaNativeReport.id, "android", request.before)
        rows = (await db.execute(query.order_by(stamp.desc(),
                                                AdminPwaNativeReport.id.desc()).limit(take))).all()
        for row in rows:
            gathered.append({
                "source": "android", "source_id": row.source_id, "created_at": _utc(row.created_at),
                "user_id": row.user_id, "message": row.message, "has_attachment": row.has_attachment,
                "feedback_status": None, "rating": None, "notification_delivery": row.notification_delivery,
                **_triage(row),
                "app_version": row.app_version, "screen": row.screen,
            })


    if "technical" in sources:
        # Existing Mini App diagnostic records include raw stack/URL/user text:
        # never SELECT content; the Admin PWA sees only a fixed safe label.
        stamp = Message.created_at
        query = select(
            Message.id.label("source_id"), stamp.label("created_at"),
            Message.user_id.label("user_id"),
            AdminPwaInboxTriage.status.label("triage_status"),
            AdminPwaInboxTriage.priority.label("triage_priority"),
            AdminPwaInboxTriage.assigned_to_user_id.label("triage_assignee"),
            AdminPwaInboxTriage.read_at.label("triage_read_at"),
            AdminPwaInboxTriage.resolved_at.label("triage_resolved_at"),
            AdminPwaInboxTriage.revision.label("triage_revision"),
        ).outerjoin(AdminPwaInboxTriage, and_(
            AdminPwaInboxTriage.source == "technical",
            AdminPwaInboxTriage.source_id == Message.id,
        )).where(
            Message.role == "assistant",
            Message.content_type == "app_error_context",
            stamp >= now - timedelta(days=30),
            stamp <= now,
        )
        if request.priority == "important":
            query = query.where(func.coalesce(AdminPwaInboxTriage.priority, "important") == "important")
        if request.user_id is not None:
            query = query.where(Message.user_id == request.user_id)
        if request.search is not None and request.search.casefold() not in "mini app technical error":
            query = query.where(Message.id == -1)
        query = _before(query, stamp, Message.id, "technical", request.before)
        rows = (await db.execute(query.order_by(stamp.desc(), Message.id.desc()).limit(take))).all()
        for row in rows:
            gathered.append({
                "source": "technical", "source_id": row.source_id,
                "created_at": _utc(row.created_at), "user_id": row.user_id,
                "message": "Mini App technical error", "has_attachment": False,
                "image_preview_available": False,
                "feedback_status": None, "rating": None, "notification_delivery": None,
                "app_version": None, "screen": None, **_triage(row),
            })

    if "payment" in sources:
        stamp = Payment.submitted_at
        # Include only a RECEIVED pending receipt; drafts/no-upload never alert.
        # Payment triage is a viewing state, never financial approval.
        join_user = or_(
            User.id == Payment.user_id,
            and_(Payment.user_id.is_(None), Payment.user_telegram_id > 0,
                 User.telegram_id == Payment.user_telegram_id),
        )
        query = select(
            Payment.id.label("source_id"), stamp.label("created_at"),
            func.cast("payment", String).label("source_type"),
            User.id.label("user_id"),
            AdminPwaInboxTriage.status.label("triage_status"),
            AdminPwaInboxTriage.priority.label("triage_priority"),
            AdminPwaInboxTriage.assigned_to_user_id.label("triage_assignee"),
            AdminPwaInboxTriage.read_at.label("triage_read_at"),
            AdminPwaInboxTriage.resolved_at.label("triage_resolved_at"),
            AdminPwaInboxTriage.revision.label("triage_revision"),
        ).outerjoin(AdminPwaInboxTriage, and_(
            AdminPwaInboxTriage.source == "payment",
            AdminPwaInboxTriage.source_id == Payment.id,
        )).outerjoin(User, join_user).where(
            Payment.payment_status == "pending",
            Payment.screenshot_file_id.is_not(None),
        )
        if request.priority == "important":
            query = query.where(func.coalesce(AdminPwaInboxTriage.priority, "important") == "important")
        if request.user_id is not None:
            query = query.where(User.id == request.user_id)
        if request.search is not None:
            number = _search_payment_id(request.search)
            query = query.where(stamp >= search_start, Payment.id == (number if number is not None else -1))
        query = _before(query, stamp, Payment.id, "payment", request.before)
        rows = (await db.execute(query.order_by(stamp.desc(), Payment.id.desc()).limit(take))).all()
        for row in rows:
            gathered.append({
                "source": "payment", "source_id": row.source_id,
                "created_at": _utc(row.created_at), "user_id": row.user_id,
                "message": None, "has_attachment": True, "feedback_status": None,
                "rating": None, "notification_delivery": None,
                "app_version": None, "screen": None, **_triage(row),
            })

    gathered.sort(key=lambda r: (r["created_at"], _RANK[r["source"]], r["source_id"]), reverse=True)
    page = gathered[:request.limit]
    next_before = None
    if len(gathered) > request.limit:
        last = page[-1]
        next_before = {"created_at": last["created_at"].isoformat(),
                       "source": last["source"], "source_id": last["source_id"]}
    for row in page:
        row["created_at"] = row["created_at"].isoformat()
    return {
        "items": page,
        "next_before": next_before,
        "search_window_days": 30 if request.search is not None else None,
        "attachment_access": "not_exposed",
        "triage_available": True,
        "historical_android_reports_complete": False,
        "history_note": "Android reports previously sent only to Telegram cannot be reconstructed",
    }


class InboxUnreadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


async def unread_inbox(db, request: InboxUnreadRequest):
    """Bounded, source-authoritative unread count, *not* the first page size.

    Stops at 100 matching rows. Untriaged source rows count as new; read,
    assigned, resolved rows are not unread. The response is a capped count
    (`99+` when at least 100), not a made-up exact total. No message fields,
    screenshot bytes or user identifiers are selected.
    """
    now = datetime.now(timezone.utc)
    maximum = 100
    found = 0
    for name, model in (("bot", BotFeedback), ("release", ReleaseFeedbackResponse),
                        ("android", AdminPwaNativeReport), ("payment", Payment),
                        ("technical", Message)):
        remaining = maximum - found
        if remaining <= 0:
            break
        query = select(model.id).outerjoin(AdminPwaInboxTriage, and_(
            AdminPwaInboxTriage.source == name,
            AdminPwaInboxTriage.source_id == model.id,
        )).where(or_(AdminPwaInboxTriage.status.is_(None),
                    AdminPwaInboxTriage.status == "new"))
        if name == "android":
            query = query.where(AdminPwaNativeReport.expires_at > now)
        if name == "technical":
            query = query.where(Message.role == "assistant",
                Message.content_type == "app_error_context",
                Message.created_at >= now - timedelta(days=30))
        if name == "payment":
            query = query.where(Payment.payment_status == "pending",
                                Payment.screenshot_file_id.is_not(None))
        # The private technical feed uses its narrow, partial timestamp index.
        ordering = ((Message.created_at.desc(), Message.id.desc()) if name == "technical"
                    else (model.id.desc(),))
        ids = (await db.execute(query.order_by(*ordering).limit(remaining))).all()
        found += len(ids)
    return {"unread_count": min(found, 99), "capped": found >= maximum,
            "count_limit": 99, "derived_from": "unread_source_rows",
            "generated_at": now.isoformat()}
