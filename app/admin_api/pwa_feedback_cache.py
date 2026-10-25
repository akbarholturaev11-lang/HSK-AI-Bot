"""Rolling 24h privacy-minimized feedback category cache, shared via Redis/R2.

Every caller must be authenticated by the first-party route before this reader
is accessed. No user/account data, raw feedback or authorization state is cached.
"""
import asyncio
from datetime import datetime, timezone
import json
import logging
import time
from uuid import uuid4

from app.admin_api.pwa_statistics_cache import (
    AdminPwaStatisticsReader, StatisticsUnavailable, _SharedUnavailable,
    _PUBLISH, _RELEASE, SNAPSHOT_SECONDS, _LEASE_SECONDS, _MAX_BYTES, _RETRY_SECONDS,
)
from app.admin_api.pwa_feedback_analytics import FeedbackAnalyticsRequest, feedback_analytics, FEEDBACK_DEFINITIONS
from app.admin_api.pwa_r2_aggregate_store import R2Unavailable

logger = logging.getLogger(__name__)


class AdminPwaFeedbackReader(AdminPwaStatisticsReader):
    """Cache-aside: process -> Redis -> R2 -> one bounded database refresh.

    A Redis lease coordinates readers across workers. When Redis fails, each
    worker can refresh once, then retain its own snapshot for 24h. A temporary
    provider error never triggers an expensive SELECT per browser request.
    """

    def __init__(self, *, settings_obj, session_factory, loader=feedback_analytics,
                 redis_client=None, r2_store=None, namespace=None, clock=time.time):
        super().__init__(settings_obj=settings_obj, session_factory=session_factory,
                         loader=loader, redis_client=redis_client, r2_store=r2_store,
                         namespace=namespace, clock=clock)
        self.prefix = self.prefix.replace("admin:stats:v1", "admin:feedback:v1")

    def _decode(self, raw, query):
        if not isinstance(raw, bytes) or not 0 < len(raw) <= _MAX_BYTES:
            return None
        try:
            envelope = json.loads(raw, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
            if (not isinstance(envelope, dict) or set(envelope) != {"version", "expires_at", "data"}
                    or envelope["version"] != 1):
                return None
            expires = envelope["expires_at"]
            data = envelope["data"]
            if (isinstance(expires, bool) or not isinstance(expires, (int, float))
                    or not self.clock() < expires <= self.clock() + SNAPSHOT_SECONDS):
                return None
            if (not isinstance(data, dict) or set(data) != {
                    "schema", "period", "source", "since", "until", "generated_at",
                    "sample_limit_per_source", "coverage", "historical_android_reports_complete",
                    "definitions", "sources",
                } or data.get("definitions") != FEEDBACK_DEFINITIONS
                    or data.get("schema") != "hskai_feedback_categories_v1"
                    or data.get("source") != query.source or data.get("period") != query.period
                    or data.get("coverage") != "most_recent_source_records_in_window"
                    or data.get("sample_limit_per_source") != 500
                    or type(data.get("historical_android_reports_complete")) is not bool
                    or data["historical_android_reports_complete"] is not False):
                return None
            generated = datetime.fromisoformat(data["generated_at"])
            if generated.tzinfo is None or abs(generated.timestamp() + SNAPSHOT_SECONDS - expires) > 1:
                return None
            since = datetime.fromisoformat(data["since"])
            until = datetime.fromisoformat(data["until"])
            if (since.tzinfo is None or until.tzinfo is None
                    or abs(until.timestamp() - generated.timestamp()) > 1
                    or abs((until - since).total_seconds() - (604800 if query.period == "weekly" else 2592000)) > 1):
                return None
            expected = ("bot", "release", "android") if query.source == "all" else (query.source,)
            sources = data["sources"]
            if not isinstance(sources, list) or len(sources) != len(expected):
                return None
            for item, source in zip(sources, expected):
                if (not isinstance(item, dict)
                        or set(item) != {"source", "date_basis", "records_scanned", "truncated", "categories"}
                        or item.get("source") != source
                        or item.get("date_basis") != {
                            "bot": "bot_feedbacks.completed_at",
                            "release": "release_feedback_responses.completed_at",
                            "android": "admin_pwa_native_reports.created_at",
                        }[source]):
                    return None
                n = item.get("records_scanned")
                cats = item.get("categories")
                if (type(n) is not int or not 0 <= n <= 500
                        or type(item.get("truncated")) is not bool
                        or not isinstance(cats, list) or len(cats) > 16):
                    return None
                for row in cats:
                    if (not isinstance(row, dict) or set(row) != {"category", "count"}
                            or type(row.get("count")) is not int
                            or not 0 <= row["count"] <= n or
                            row.get("category") not in (
                                "price", "limits", "unclear", "pace", "other", "unclassified",
                                "low_rating", "neutral_rating", "positive_rating", "unclassified_rating",
                                "reported_issue")):
                        return None
            return envelope
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
            return None

    async def __call__(self, query):
        query = FeedbackAnalyticsRequest.model_validate(query.model_dump())
        if not getattr(self.settings, "ADMIN_PWA_ENABLED", False):
            raise StatisticsUnavailable("Feedback disabled")
        variant = (query.source, query.period)
        self._local = {k: e for k, e in self._local.items()
                       if self.clock() < e["expires_at"] <= self.clock() + SNAPSHOT_SECONDS}
        cached = self._local.get(variant)
        if cached is not None:
            return self._result(cached)
        try:
            async with asyncio.timeout(16), self._mutex:
                cached = self._local.get(variant)
                if cached is not None and self.clock() < cached["expires_at"]:
                    return self._result(cached)
                key = self.prefix + ":" + query.source + ":" + query.period
                lease = self.prefix + ":refresh"
                token = uuid4().hex
                shared = True
                try:
                    cached = await self._shared(key, query)
                    if cached is not None:
                        return self._remember(variant, cached)
                    if self.clock() < self._load_retry_at:
                        raise StatisticsUnavailable("Feedback refresh cooling down")
                    while not await self._redis("set", lease, token, nx=True, ex=_LEASE_SECONDS):
                        await asyncio.sleep(.1)
                        cached = await self._shared(key, query)
                        if cached is not None:
                            return self._remember(variant, cached)
                    cached = await self._shared(key, query)
                    if cached is not None:
                        await self._redis("eval", _RELEASE, 1, lease, token)
                        return self._remember(variant, cached)
                except _SharedUnavailable:
                    shared = False

                if self._r2.enabled:
                    try:
                        raw = await self._r2.get(kind="feedback", namespace=self._r2_namespace,
                                                 variant=query.source+"_"+query.period)
                        cached = self._decode(raw, query)
                        if cached is not None:
                            if shared:
                                try:
                                    await self._redis("eval", _PUBLISH, 2, lease, key, token, raw,
                                                      max(1, int(cached["expires_at"] - self.clock())))
                                except _SharedUnavailable:
                                    pass
                            return self._remember(variant, cached)
                    except R2Unavailable:
                        logger.warning("Admin PWA private R2 feedback mirror unavailable")
                raw, envelope = await self._compute(query)
                if shared:
                    try:
                        published = await self._redis("eval", _PUBLISH, 2, lease, key, token, raw,
                                                      max(1, int(envelope["expires_at"] - self.clock())))
                        if not published:
                            self._load_retry_at = self.clock() + _RETRY_SECONDS
                            raise StatisticsUnavailable("Feedback refresh lease lost")
                    except _SharedUnavailable:
                        pass
                if self._r2.enabled:
                    try:
                        await self._r2.put(kind="feedback", namespace=self._r2_namespace,
                                           variant=query.source+"_"+query.period, raw=raw)
                    except R2Unavailable:
                        logger.warning("Admin PWA private R2 feedback mirror write unavailable")
                return self._remember(variant, envelope)
        except TimeoutError:
            raise StatisticsUnavailable("Feedback refresh busy") from None
