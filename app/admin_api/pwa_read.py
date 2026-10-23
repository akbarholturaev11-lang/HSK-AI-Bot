"""Bounded real-data browser projections; no management commands or demo data."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import and_, func, or_, select, text

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, authenticate_admin_pwa_session
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.bot_feedback import BotFeedback
from app.db.models.payment import Payment
from app.db.models.release_feedback import ReleaseFeedbackResponse
from app.db.models.user import User
from app.services.admin_miniapp_service import AdminMiniAppService, _payment_user_join
from app.services.android_analytics_service import AndroidAnalyticsService
from app.services.desktop_analytics_service import DesktopAnalyticsService
from app.services.entitlements import resolve_state

logger = logging.getLogger(__name__)
Id = Annotated[int, Field(strict=True, ge=1, le=2_147_483_647)]


class ReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class StatisticsRequest(ReadRequest):
    period: Literal["weekly", "monthly", "all_time"] = "weekly"
    platform: Literal["overall", "telegram", "android", "macos", "windows", "iphone_pwa"] = "overall"


class PageRequest(ReadRequest):
    limit: Annotated[int, Field(ge=1, le=100)] = 30
    before_id: Id | None = None


class UsersRequest(PageRequest):
    query: Annotated[str, Field(max_length=80)] = ""


class FeedbackRequest(PageRequest):
    source: Literal["bot", "release"]
    user_id: Id | None = None


@asynccontextmanager
async def read_transaction(db):
    """Real PostgreSQL prevents writes and provides a coherent read snapshot."""
    async with db.begin():
        if db.get_bind().dialect.name == "postgresql":
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            await db.execute(text("SET LOCAL statement_timeout = '5000'"))
        yield


def _iso(value):
    return _utc(value).isoformat() if value else None


async def statistics(db, request: StatisticsRequest):
    now = datetime.now(timezone.utc)
    days = {"weekly": 7, "monthly": 30, "all_time": None}[request.period]
    since = now-timedelta(days=days) if days else None
    result = {"platform": request.platform, "period": request.period,
              "since": _iso(since), "generated_at": _iso(now), "timezone": "UTC",
              "platform_counts_overlap": True}
    if request.platform in {"iphone_pwa", "telegram"}:
        # No false iPhone telemetry, and no relabeling global course events as
        # proven Telegram-only activity before its attribution is audited.
        return {**result, "available": False, "metrics": None,
                "reason": "not_instrumented" if request.platform == "iphone_pwa" else "attribution_not_audited"}
    if request.platform == "android":
        snapshot = await AndroidAnalyticsService(db).snapshot(now=now, since=since)
        return {**result, "available": True, "source": "AndroidAnalyticsService.snapshot",
                "scope": {"registry": "current_linked_devices", "active": "rolling_1_7_30_days",
                          "funnel": request.period},
                "metrics": {key: snapshot[key] for key in ("registry", "active", "funnel")}}
    if request.platform in {"macos", "windows"}:
        # Only the existing rolling detail projection is returned; do not load
        # all historical funnel cohorts for a platform's 30-day counters.
        snapshot = await DesktopAnalyticsService(db).snapshot(now=now, since=now-timedelta(days=30))
        return {**result, "available": True, "source": "DesktopAnalyticsService.snapshot.platforms",
                "scope": {"metrics": "rolling_30_days", "period_filter_applied": False},
                "metrics": {key: values[request.platform] for key, values in snapshot["platforms"].items()}}
    service = AdminMiniAppService(db)
    active_since = since or now-timedelta(days=30)
    statuses = await service._payment_status_counts(since)
    totals = await service._approved_currency_totals(since)
    return {**result, "available": True, "source": "AdminMiniAppService",
            "scope": {"users_total": "all_canonical_accounts", "new_accounts": request.period,
                      "active_accounts_since": _iso(active_since),
                      "payments": "reviewed_at_or_submitted_at"},
            "metrics": {"users_total": await service._count_users(),
                        "new_accounts": await service._count_users(*([User.created_at >= since] if since else [])),
                        "active_accounts": await service._count_users(User.last_active_at >= active_since),
                        "payments_by_status": {key: statuses.get(key, {}).get("count", 0)
                                               for key in ("pending", "approved", "rejected")},
                        "approved_amounts_by_currency": [{"currency": row.currency, "amount": int(row.total_sum)}
                                                         for row in sorted(totals, key=lambda r: r.currency)]}}


async def users(db, request: UsersRequest):
    query = select(User)
    value = request.query.strip()
    if value:
        if value.isascii() and value.isdigit():
            number = int(value) if len(value) <= 10 else 0
            query = query.where(User.id == number if 0 < number <= 2_147_483_647 else False)
        else:
            value = value.removeprefix("@").lower()
            query = query.where(or_(func.lower(User.full_name).contains(value, autoescape=True),
                                   func.lower(User.username).contains(value, autoescape=True)))
    if request.before_id is not None:
        query = query.where(User.id < request.before_id)
    rows = list((await db.scalars(query.order_by(User.id.desc()).limit(request.limit+1))).all())
    page = rows[:request.limit]
    ids = [row.id for row in page]
    pending = set((await db.scalars(select(User.id).distinct().join(Payment, _payment_user_join()).where(
        User.id.in_(ids), Payment.payment_status == "pending",
        or_(Payment.user_id.is_not(None), User.telegram_id > 0),
    ))).all()) if ids else set()
    now = datetime.now(timezone.utc)
    return {"items": [{"user_id": row.id, "name": row.full_name, "username": row.username,
                       "language": row.language, "level": row.level, "status": row.status,
                       "access_state": resolve_state(row, now=now), "end_date": _iso(row.end_date),
                       "has_pending_payment": row.id in pending, "last_active_at": _iso(row.last_active_at)}
                      for row in page],
            "next_before_id": page[-1].id if len(rows) > request.limit else None,
            "numeric_query_namespace": "users.id"}


async def feedback(db, request: FeedbackRequest):
    model = BotFeedback if request.source == "bot" else ReleaseFeedbackResponse
    # BotFeedback already owns a canonical ID. Release feedback only has a
    # genuine legacy Telegram transport; never interpret it as users.id.
    join = (User.id == model.user_id if request.source == "bot"
            else and_(User.telegram_id > 0, User.telegram_id == model.user_telegram_id))
    query = select(model, User.id).outerjoin(User, join)
    if request.user_id is not None:
        query = query.where(User.id == request.user_id)
    if request.before_id is not None:
        query = query.where(model.id < request.before_id)
    rows = (await db.execute(query.order_by(model.id.desc()).limit(request.limit+1))).all()
    items = []
    for row, user_id in rows[:request.limit]:
        if request.source == "bot":
            item = {"status": row.status, "language": row.language,
                    "liked_code": row.liked_code, "liked_text": row.liked_text[:2000] if row.liked_text else None,
                    "disliked_code": row.disliked_code, "disliked_text": row.disliked_text[:2000] if row.disliked_text else None,
                    "text_truncated": any(len(value or "") > 2000 for value in (row.liked_text, row.disliked_text)),
                    "has_attachment": bool(row.disliked_attachment_file_id),
                    "created_at": _iso(row.created_at), "completed_at": _iso(row.completed_at)}
        else:
            item = {"campaign_id": row.campaign_id, "rating": row.rating,
                    "comment": row.comment_text[:2000] if row.comment_text else None,
                    "text_truncated": len(row.comment_text or "") > 2000,
                    "has_attachment": bool(row.attachment_file_id), "completed_at": _iso(row.completed_at)}
        items.append({"source": request.source, "source_id": row.id, "user_id": user_id, **item})
    return {"items": items, "next_before_id": items[-1]["source_id"] if len(rows) > request.limit else None,
            "unavailable_sources": ["android_bug_reports"], "attachment_access": "not_exposed"}


def create_admin_pwa_read_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-read"])

    async def handle(request: Request, schema, service):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            query = schema.model_validate(await _body(request, 2048))
        except ValidationError:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                async with read_transaction(db):
                    actor = await authenticate_admin_pwa_session(db, cookie, settings_obj)
                    if actor is None:
                        return _reply(401, "admin_pwa_unauthorized")
                    result = await service(db, query)
        except Exception:
            logger.exception("Admin PWA read projection unavailable")
            return _reply(503, "admin_pwa_read_unavailable")
        return JSONResponse(content={"ok": True, **result}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/statistics")
    async def read_statistics(request: Request):
        return await handle(request, StatisticsRequest, statistics)

    @router.post("/api/admin/v1/users/search")
    async def read_users(request: Request):
        return await handle(request, UsersRequest, users)

    @router.post("/api/admin/v1/feedback/list")
    async def read_feedback(request: Request):
        return await handle(request, FeedbackRequest, feedback)

    return router
