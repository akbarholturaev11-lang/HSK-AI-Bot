"""First-party-only sampled feedback categories and PII-free bounded files.

No raw text, IDs, media, free-form labels, user-level joins, MCP tools or AI
classification. Every selected source query reads at most MAX_SOURCE_ROWS + 1
recent indexed records; coverage is explicitly marked partial when capped.
"""
import asyncio
import csv
from datetime import datetime, timedelta, timezone
import io
import json
import logging
import math
import time
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import select

from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, authenticate_admin_pwa_session
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.bot.keyboards.feedback import DISLIKED_OPTIONS
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.bot_feedback import BotFeedback
from app.db.models.release_feedback import ReleaseFeedbackResponse

logger = logging.getLogger(__name__)
MAX_SOURCE_ROWS = 500
MAX_EXPORT_BYTES = 128 * 1024
FEEDBACK_DEFINITIONS = {
    "bot": "Completed Bot feedback: stored disliked_code only; missing/unknown code is unclassified",
    "release": "Recorded 1-2 low, 3 neutral, 4-5 positive rating; unknown is unclassified_rating",
    "android": "Unexpired stored Android bug reports; no guessed issue categories; older Telegram-only reports unavailable",
}
_CODES = frozenset(DISLIKED_OPTIONS)
_MAX_QUERIES_PER_MINUTE = 30
_MAX_CONCURRENT_QUERIES = 2
_SOURCES = ("bot", "release", "android")
_RATING_BUCKETS = {1: "low_rating", 2: "low_rating", 3: "neutral_rating",
                   4: "positive_rating", 5: "positive_rating"}


class FeedbackAnalyticsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    period: Literal["weekly", "monthly"] = "weekly"
    source: Literal["all", "bot", "release", "android"] = "all"


class FeedbackAnalyticsExportRequest(FeedbackAnalyticsRequest):
    format: Literal["json", "csv"]


def _category(source, value):
    if source == "bot":
        return value if isinstance(value, str) and value in _CODES else "unclassified"
    if source == "release":
        return _RATING_BUCKETS.get(value, "unclassified_rating") if type(value) is int else "unclassified_rating"
    return "reported_issue"


async def feedback_analytics(db, query: FeedbackAnalyticsRequest, *, now=None, max_source_rows=MAX_SOURCE_ROWS):
    if not 1 <= max_source_rows <= MAX_SOURCE_ROWS:
        raise ValueError("Invalid aggregate limit")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Naive aggregate time")
    now = now.astimezone(timezone.utc)
    since = now - timedelta(days=7 if query.period == "weekly" else 30)
    source_keys = _SOURCES if query.source == "all" else (query.source,)
    sources = []
    for source in source_keys:
        if source == "bot":
            model = BotFeedback
            stamp = model.completed_at
            statement = select(model.disliked_code).where(
                model.status == "completed", stamp >= since, stamp < now,
            ).order_by(stamp.desc(), model.id.desc())
        elif source == "release":
            model = ReleaseFeedbackResponse
            stamp = model.completed_at
            statement = select(model.rating).where(
                stamp >= since, stamp < now,
            ).order_by(stamp.desc(), model.id.desc())
        else:
            model = AdminPwaNativeReport
            stamp = model.created_at
            # Native intake always sets expires_at = created_at + 30 days.
            # An existing expiry index avoids a wide created_at sort; keep
            # the created_at window and current retention predicates too.
            statement = select(model.id).where(
                stamp >= since, stamp < now, model.expires_at > now,
            ).order_by(model.expires_at.desc(), model.id.desc())
        selected = (await db.execute(statement.limit(max_source_rows + 1))).scalars().all()
        sampled = selected[:max_source_rows]
        counts = {}
        for value in sampled:
            category = _category(source, value)
            counts[category] = counts.get(category, 0) + 1
        sources.append({
            "source": source,
            "date_basis": ("bot_feedbacks.completed_at" if source == "bot"
                           else "release_feedback_responses.completed_at" if source == "release"
                           else "admin_pwa_native_reports.created_at"),
            "records_scanned": len(sampled),
            "truncated": len(selected) > max_source_rows,
            "categories": [{"category": category, "count": counts[category]}
                           for category in sorted(counts)],
        })
    return {
        "schema": "hskai_feedback_categories_v1",
        "period": query.period, "source": query.source,
        "since": since.isoformat(), "until": now.isoformat(),
        "generated_at": now.isoformat(), "sample_limit_per_source": max_source_rows,
        "coverage": "most_recent_source_records_in_window",
        "historical_android_reports_complete": False,
        "definitions": FEEDBACK_DEFINITIONS,
        "sources": sources,
    }


def render_feedback_analytics_export(data, query: FeedbackAnalyticsExportRequest):
    # Only code-controlled labels, integers and fixed metadata; no arbitrary
    # client or DB strings are permitted in these files.
    if (data.get("schema") != "hskai_feedback_categories_v1"
            or data.get("period") != query.period or data.get("source") != query.source):
        raise ValueError("Mismatched feedback export")
    if query.format == "json":
        raw = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        content_type = "application/json"
    else:
        out = io.StringIO(newline="")
        writer = csv.writer(out, lineterminator="\r\n")
        writer.writerow(("schema", "period", "source_filter", "since_utc", "until_utc",
                         "source", "date_basis", "records_scanned", "truncated",
                         "category", "count"))
        for source in data["sources"]:
            for row in source["categories"]:
                writer.writerow((data["schema"], query.period, query.source, data["since"],
                                 data["until"], source["source"], source["date_basis"],
                                 source["records_scanned"], str(source["truncated"]).lower(),
                                 row["category"], row["count"]))
            if not source["categories"]:
                writer.writerow((data["schema"], query.period, query.source, data["since"],
                                 data["until"], source["source"], source["date_basis"],
                                 0, "false", "", ""))
        raw = out.getvalue().encode("utf-8")
        content_type = "text/csv"
    if len(raw) > MAX_EXPORT_BYTES:
        raise ValueError("Feedback export exceeds limit")
    stamp = datetime.fromisoformat(data["generated_at"]).strftime("%Y%m%dT%H%M%SZ")
    filename = f"hskai-feedback-categories-{query.source}-{query.period}-{stamp}.{query.format}"
    return Response(raw, media_type=content_type, headers={
        **_PRIVATE_HEADERS, "Content-Disposition": f'attachment; filename="{filename}"',
    })


class _FeedbackQueryLimit:
    """Bound expensive private feedback reads per worker, not a global quota.

    Authenticated traffic only. No cookies, identities or addresses are
    recorded; a fixed small amount of state is retained per API router.
    """

    def __init__(self, *, clock=time.monotonic):
        self.clock = clock
        self.lock = asyncio.Lock()
        self.started = clock()
        self.attempts = 0
        self.active = 0

    async def enter(self):
        async with self.lock:
            now = self.clock()
            if now - self.started >= 60:
                self.started, self.attempts = now, 0
            if self.active >= _MAX_CONCURRENT_QUERIES:
                return 1
            if self.attempts >= _MAX_QUERIES_PER_MINUTE:
                return max(1, math.ceil(60 - (now - self.started)))
            self.attempts += 1
            self.active += 1
            return 0

    async def leave(self):
        async with self.lock:
            self.active -= 1


def create_admin_pwa_feedback_analytics_router(*, settings_obj, session_factory, clock=time.monotonic, reader=None):
    router = APIRouter(tags=["admin-pwa-feedback-analytics"])
    throttle = _FeedbackQueryLimit(clock=clock)
    if reader is None:
        from app.admin_api.pwa_feedback_cache import AdminPwaFeedbackReader
        reader = AdminPwaFeedbackReader(settings_obj=settings_obj, session_factory=session_factory)

    async def handle(request: Request, *, export: bool):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            query = (FeedbackAnalyticsExportRequest if export else FeedbackAnalyticsRequest).model_validate(
                await _body(request, 2048))
        except ValidationError:
            return _reply(400, "admin_pwa_invalid_payload")
        admitted = False
        try:
            async with session_factory() as db:
                async with read_transaction(db):
                    actor = await authenticate_admin_pwa_session(db, cookie, settings_obj)
                    if actor is None or actor.auth_method != "webauthn":
                        return _reply(401, "admin_pwa_unauthorized")
                    retry_after = await throttle.enter()
                    if retry_after:
                        response = _reply(429, "admin_pwa_feedback_busy")
                        response.headers["Retry-After"] = str(retry_after)
                        return response
                    admitted = True
            # Cached aggregate IO and a possible refresh run only AFTER the
            # authentication transaction has closed; no SQL connection is
            # pinned across Redis/R2 waits. Current auth is never cached.
            result = await reader(FeedbackAnalyticsRequest(period=query.period, source=query.source))
            # Redis/R2 refresh may take time. Reject a session revoked while
            # waiting, including after a warm cache fetch; authority is live.
            failure = _guard_post(request, settings_obj)
            if failure is not None:
                return failure
            async with session_factory() as db:
                async with read_transaction(db):
                    current = await authenticate_admin_pwa_session(db, cookie, settings_obj)
                    if (current is None or current.auth_method != "webauthn"
                            or current.user_id != actor.user_id):
                        return _reply(401, "admin_pwa_unauthorized")
            if export:
                return render_feedback_analytics_export(result, query)
            return JSONResponse({"ok": True, **result}, headers=_PRIVATE_HEADERS)
        except Exception:
            logger.exception("Admin PWA feedback aggregate unavailable")
            return _reply(503, "admin_pwa_feedback_aggregate_unavailable")
        finally:
            if admitted:
                await throttle.leave()

    @router.post("/api/admin/v1/feedback/categories")
    async def categories(request: Request):
        return await handle(request, export=False)

    @router.post("/api/admin/v1/feedback/categories/export")
    async def export_categories(request: Request):
        return await handle(request, export=True)

    return router
