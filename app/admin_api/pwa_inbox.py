"""Bounded, read-only unified Admin PWA inbox; no remote MCP or attachment access.

This projection does not invent triage state and deliberately keeps historical
Android reports that were never stored outside its claimed coverage.
"""
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, func, or_, select

from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.bot_feedback import BotFeedback
from app.db.models.release_feedback import ReleaseFeedbackResponse
from app.db.models.user import User

Source = Literal["bot", "release", "android"]
RowId = Annotated[int, Field(strict=True, ge=1, le=2_147_483_647)]
_RANK = {"android": 1, "release": 2, "bot": 3}
_MAX_MESSAGE = 2000


class InboxCursor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    created_at: datetime
    source: Source
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
    source: Literal["all", "bot", "release", "android"] = "all"
    user_id: RowId | None = None
    limit: Annotated[int, Field(strict=True, ge=1, le=50)] = 30
    before: InboxCursor | None = None


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

    if "bot" in sources:
        stamp = func.coalesce(BotFeedback.completed_at, BotFeedback.created_at)
        query = select(
            BotFeedback.id.label("source_id"), stamp.label("created_at"),
            User.id.label("user_id"),
            func.substr(func.coalesce(BotFeedback.disliked_text, BotFeedback.liked_text,
                                      BotFeedback.disliked_code, BotFeedback.liked_code), 1,
                        _MAX_MESSAGE).label("message"),
            BotFeedback.disliked_attachment_file_id.is_not(None).label("has_attachment"),
            BotFeedback.status.label("feedback_status"),
        ).outerjoin(User, User.id == BotFeedback.user_id)
        if request.user_id is not None:
            query = query.where(User.id == request.user_id)
        query = _before(query, stamp, BotFeedback.id, "bot", request.before)
        rows = (await db.execute(query.order_by(stamp.desc(), BotFeedback.id.desc()).limit(take))).all()
        for row in rows:
            gathered.append({
                "source": "bot", "source_id": row.source_id, "created_at": _utc(row.created_at),
                "user_id": row.user_id, "message": row.message, "has_attachment": row.has_attachment,
                "feedback_status": row.feedback_status,
                "rating": None, "notification_delivery": None, "app_version": None, "screen": None,
            })

    if "release" in sources:
        stamp = ReleaseFeedbackResponse.completed_at
        query = select(
            ReleaseFeedbackResponse.id.label("source_id"), stamp.label("created_at"),
            User.id.label("user_id"),
            func.substr(ReleaseFeedbackResponse.comment_text, 1, _MAX_MESSAGE).label("message"),
            ReleaseFeedbackResponse.attachment_file_id.is_not(None).label("has_attachment"),
            ReleaseFeedbackResponse.rating.label("rating"),
        ).outerjoin(User, and_(User.telegram_id > 0,
                                User.telegram_id == ReleaseFeedbackResponse.user_telegram_id))
        if request.user_id is not None:
            query = query.where(User.id == request.user_id)
        query = _before(query, stamp, ReleaseFeedbackResponse.id, "release", request.before)
        rows = (await db.execute(query.order_by(stamp.desc(),
                                                ReleaseFeedbackResponse.id.desc()).limit(take))).all()
        for row in rows:
            gathered.append({
                "source": "release", "source_id": row.source_id, "created_at": _utc(row.created_at),
                "user_id": row.user_id, "message": row.message, "has_attachment": row.has_attachment,
                "feedback_status": None, "rating": row.rating, "notification_delivery": None,
                "app_version": None, "screen": None,
            })

    if "android" in sources:
        stamp = AdminPwaNativeReport.created_at
        query = select(
            AdminPwaNativeReport.id.label("source_id"), stamp.label("created_at"),
            AdminPwaNativeReport.user_id.label("user_id"),
            func.substr(AdminPwaNativeReport.description, 1, _MAX_MESSAGE).label("message"),
            AdminPwaNativeReport.attachment_bytes.is_not(None).label("has_attachment"),
            AdminPwaNativeReport.notification_state.label("notification_delivery"),
            AdminPwaNativeReport.app_version.label("app_version"),
            AdminPwaNativeReport.screen.label("screen"),
        ).where(AdminPwaNativeReport.expires_at > now)
        if request.user_id is not None:
            query = query.where(AdminPwaNativeReport.user_id == request.user_id)
        query = _before(query, stamp, AdminPwaNativeReport.id, "android", request.before)
        rows = (await db.execute(query.order_by(stamp.desc(),
                                                AdminPwaNativeReport.id.desc()).limit(take))).all()
        for row in rows:
            gathered.append({
                "source": "android", "source_id": row.source_id, "created_at": _utc(row.created_at),
                "user_id": row.user_id, "message": row.message, "has_attachment": row.has_attachment,
                "feedback_status": None, "rating": None, "notification_delivery": row.notification_delivery,
                "app_version": row.app_version, "screen": row.screen,
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
        "attachment_access": "not_exposed",
        "triage_available": False,
        "historical_android_reports_complete": False,
        "history_note": "Android reports previously sent only to Telegram cannot be reconstructed",
    }
