"""Private, on-demand daily statistics. Never cache authorization or commands."""
import asyncio
import copy
from datetime import datetime, timezone
import hashlib
import json
import logging
import random
import re
import time
from uuid import uuid4

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from sqlalchemy import text

from app.admin_api.pwa_read import StatisticsRequest, read_transaction, statistics
from app.admin_api.pwa_r2_aggregate_store import PrivateR2AggregateStore, R2Unavailable, R2ConfigurationError

SNAPSHOT_SECONDS = 24 * 60 * 60
logger = logging.getLogger(__name__)
_LOAD_SECONDS = 8
_LEASE_SECONDS = 45
_RETRY_SECONDS = 30
_REDIS_SOCKET_SECONDS = .25
_REDIS_IO_SECONDS = .35
_MAX_BYTES = 128 * 1024
# Owner refreshes only: at most three attempts per R2 object, and only for a
# transient failure class. Every attempt keeps the store's own 3 s bound, so one
# object costs at most about 11.5 s. Browser reads keep their single attempt.
_R2_RETRY_DELAYS = (0.5, 1.5)
# Full-refresh group: up to three windows, i.e. three R2 reads and three writes
# at the bound above, plus the unchanged loaders under their 5 s statements.
_BUNDLE_SECONDS = 120
_SOURCE_OVERVIEW = "users + payments + canonical learning events"
_SOURCE_SCOPED = "first-party stored aggregate projections"
_UNAVAILABLE_REASONS = frozenset((
    "not_instrumented", "attribution_not_audited", "not_applicable", "detail_limited", "no_data",
))
_FIELDS = {"platform", "period", "since", "generated_at", "timezone", "platform_counts_overlap",
           "available", "metrics", "source", "scope", "reason", "metric_definitions"}
_MANUAL_SECTIONS = frozenset(("course", "funnel", "money", "sources", "report"))
# A scoped section refresh may target any filter whose snapshot it owns, so an
# acceptance check never waits for a 24-hour platform snapshot (audit #44).
_REFRESH_PLATFORMS = frozenset(("overall", "android", "telegram", "iphone_pwa"))
_V10_STATE_SCOPES = frozenset(f"analytics_{section}_v2" for section in
                             ("home", "overview", "platform", *_MANUAL_SECTIONS)) | {"analytics_report_v3"}
_PUBLISH = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
    redis.call('DEL', KEYS[1])
    return 1
end
return 0
"""
_RELEASE = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


class StatisticsUnavailable(RuntimeError):
    pass


class _SharedUnavailable(Exception):
    pass


class AdminPwaStatisticsReader:
    """One loader per worker; a Redis lease also coordinates healthy workers.

    Redis failure degrades to a bounded daily in-process cache, not a live SQL
    query for every request. Only authorized callers may use this reader.
    """

    def __init__(self, *, settings_obj, session_factory, loader=statistics, redis_client=None,
                 namespace=None, clock=time.time, r2_store=None, cache_scope=None, refresh_mutex=None):
        self.settings = settings_obj
        self.sessions = session_factory
        self.loader = loader
        self.clock = clock
        self._client = redis_client
        self._redis_url = getattr(settings_obj, "REDIS_URL", "")
        # str(URL) hides passwords. Do not use credentials, admin IDs or tokens
        # in keys. Separate deployments/DBs must not share their snapshots.
        bind = getattr(session_factory, "kw", {}).get("bind")
        identity = str(getattr(bind, "url", ""))
        digest = hashlib.sha256((getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", "")+"|"+identity).encode()).hexdigest()[:24]
        if cache_scope is not None and (not isinstance(cache_scope,str) or not re.fullmatch(r"[a-z0-9_-]{1,48}", cache_scope)):
            raise ValueError("Invalid internal aggregate cache scope")
        base_prefix = "hsk:admin:stats:v1:{"+(namespace or digest)+"}"
        self.prefix = base_prefix + (":"+cache_scope if cache_scope else "")
        self._cache_scope = cache_scope
        self._fields = _FIELDS | {"metric_states"} if cache_scope in _V10_STATE_SCOPES else _FIELDS
        # Scoped payloads stay separate while healthy workers share one refresh
        # lease/hash slot across basic stats and on-demand analytics sections.
        self._lease_key = base_prefix+":refresh"
        self._r2_namespace = (hashlib.sha256((digest+"|"+cache_scope).encode()).hexdigest()[:24]
                              if cache_scope else digest)
        self._r2 = r2_store if r2_store is not None else PrivateR2AggregateStore(settings_obj=settings_obj)
        self._local = {}
        # Owner refresh may update R2 while another worker holds a valid local
        # analytics snapshot. Recheck approved manually refreshable sections
        # at most once per minute; do not re-run SQL on cache hits.
        self._overview_local_revalidate = cache_scope in {
            f"analytics_{section}_v{version}"
            for section in ("overview", *_MANUAL_SECTIONS) for version in (1, 2)
        }
        self._local_checked_at = {}
        self._mutex = refresh_mutex if refresh_mutex is not None else asyncio.Lock()
        self._redis_retry_at = 0.0
        self._load_retry_at = 0.0
        self._r2_retry_delays = _R2_RETRY_DELAYS
        self._last_bundle_refresh_at = {}

    async def _r2_refresh_io(self, op, **kwargs):
        """Bounded, idempotent R2 retry for owner refreshes only.

        A GET is a read; a PUT rewrites the same key with the same validated
        bytes, so repeating it after an uncertain timeout cannot corrupt data.
        Non-transient failures (provider 4xx, bad configuration, invalid
        payload) and unclassified fixture errors fail on the first attempt.
        """
        call = self._r2.get if op == "get" else self._r2.put
        for attempt, delay in enumerate((*self._r2_retry_delays, None), start=1):
            try:
                return await call(**kwargs)
            except R2Unavailable as exc:
                exc.attempts = attempt
                if delay is None or not getattr(exc, "transient", False):
                    raise
                logger.warning("Admin PWA refresh R2 %s retry: class=%s attempt=%d",
                               op, exc.failure_class, attempt)
                await asyncio.sleep(delay * random.uniform(0.8, 1.2))

    @staticmethod
    def _log_r2_refresh_failure(path, exc):
        logger.warning("%s failed: R2Unavailable op=%s class=%s attempts=%s", path,
                       getattr(exc, "op", None) or "unknown",
                       getattr(exc, "failure_class", None) or "other",
                       getattr(exc, "attempts", 1))

    async def aclose(self):
        if self._client is not None:
            try:
                await self._client.aclose()
            except (RedisError, OSError):
                pass

    async def _redis(self, method, *args, **kwargs):
        if self.clock() < self._redis_retry_at or (self._client is None and not self._redis_url):
            raise _SharedUnavailable()
        try:
            if self._client is None:
                self._client = Redis.from_url(self._redis_url, socket_connect_timeout=_REDIS_SOCKET_SECONDS,
                    socket_timeout=_REDIS_SOCKET_SECONDS, retry=Retry(NoBackoff(), 0), max_connections=4)
            async with asyncio.timeout(_REDIS_IO_SECONDS):
                return await getattr(self._client, method)(*args, **kwargs)
        except (RedisError, OSError, TimeoutError, ValueError):
            self._redis_retry_at = self.clock()+_RETRY_SECONDS
            logger.warning("Admin PWA shared statistics cache unavailable; using worker-local daily cache")
            raise _SharedUnavailable() from None

    def _decode(self, raw, query):
        if not isinstance(raw, bytes) or not raw or len(raw) > _MAX_BYTES:
            return None
        try:
            def finite(value):
                raise ValueError("Non-finite snapshot")
            envelope = json.loads(raw, parse_constant=finite)
            if set(envelope) != {"version", "expires_at", "data"} or envelope["version"] != 1:
                return None
            expires = envelope["expires_at"]
            if isinstance(expires, bool) or not isinstance(expires, (int, float)):
                return None
            if not self.clock() < expires <= self.clock()+SNAPSHOT_SECONDS:
                return None
            data = envelope["data"]
            if (not isinstance(data, dict) or set(data)-self._fields or data.get("platform") != query.platform
                    or data.get("period") != query.period or type(data.get("available")) is not bool):
                return None
            generated = datetime.fromisoformat(data["generated_at"])
            if generated.tzinfo is None or abs(expires-generated.timestamp()-SNAPSHOT_SECONDS) > 1:
                return None
            if data["available"] and not isinstance(data.get("metrics"), dict):
                return None
            if not data["available"] and data.get("metrics") is not None:
                return None
            return envelope
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
            return None

    def _remember(self, variant, envelope):
        self._local[variant] = envelope
        self._local_checked_at[variant] = self.clock()
        return self._result(envelope)

    async def _overview_local_hit(self, variant, cached, query):
        if not self._overview_local_revalidate:
            return self._result(cached)
        now = self.clock()
        if now - self._local_checked_at.get(variant, now) < 60:
            return self._result(cached)
        self._local_checked_at[variant] = now
        # A cross-worker manual refresh may have replaced this snapshot even
        # though its original 24h expiry is still valid. Redis is only a source
        # of a newer VALIDATED copy, never a reason for extra SQL recomputation.
        try:
            shared = await self._shared(self.prefix + ":" + query.platform +
                                        ":" + query.period, query)
        except _SharedUnavailable:
            shared = None
        if shared is not None and shared != cached:
            # A Redis read can lag a more recent local snapshot (e.g. after
            # R2 succeeded but Redis publication failed). Never downgrade.
            try:
                old_at = datetime.fromisoformat(cached["data"]["generated_at"])
                new_at = datetime.fromisoformat(shared["data"]["generated_at"])
                if new_at > old_at:
                    return self._remember(variant, shared)
            except (KeyError, TypeError, ValueError):
                pass
        # A manual R2-only refresh may be newer than Redis, or Redis may be
        # unavailable entirely. Recheck only the private overview R2 object
        # once per minute; never replace newer local data with older records.
        if self._r2.enabled:
            try:
                raw = await self._r2.get(
                    kind="statistics", namespace=self._r2_namespace,
                    variant=query.platform + "_" + query.period)
                mirrored = self._decode(raw, query)
                if (mirrored is not None and
                        datetime.fromisoformat(mirrored["data"]["generated_at"]) >
                        datetime.fromisoformat(cached["data"]["generated_at"])):
                    return self._remember(variant, mirrored)
            except R2Unavailable:
                pass
        return self._result(cached)

    @staticmethod
    def _result(envelope):
        data = copy.deepcopy(envelope["data"])
        data["snapshot"] = {"refresh_interval_seconds": SNAPSHOT_SECONDS,
                            "expires_at": datetime.fromtimestamp(envelope["expires_at"], timezone.utc).isoformat()}
        return data

    async def _shared(self, key, query):
        # GETRANGE bounds even a corrupt/oversized shared value before parsing.
        raw = await self._redis("getrange", key, 0, _MAX_BYTES)
        return self._decode(raw, query)

    async def _compute(self, query):
        if self.clock() < self._load_retry_at:
            raise StatisticsUnavailable("Statistics refresh cooling down")
        try:
            async with asyncio.timeout(_LOAD_SECONDS), self.sessions() as db:
                async with read_transaction(db):
                    data = await self.loader(db, query)
            expires = datetime.fromisoformat(data["generated_at"]).timestamp()+SNAPSHOT_SECONDS
            raw = json.dumps({"version": 1, "expires_at": expires, "data": data},
                             allow_nan=False, separators=(",", ":")).encode()
            envelope = self._decode(raw, query)
            if envelope is None:
                raise ValueError("Invalid statistics snapshot")
            return raw, envelope
        except asyncio.CancelledError:
            self._load_retry_at = self.clock()+_RETRY_SECONDS
            raise
        except Exception as exc:
            # Diagnostic only: the exception *type* is safe to record while
            # SQL statements, credentials, payloads and exception text are not.
            logger.warning("Admin statistics aggregate compute failed: %s",
                           type(exc).__name__)
            self._load_retry_at = self.clock()+_RETRY_SECONDS
            raise StatisticsUnavailable("Statistics refresh unavailable") from None


    async def refresh_now(self, query):
        """Explicit, authorized server-side refresh, even when daily caches are valid.

        Only the caller's trusted transport may request this method. Redis is
        required for a distributed lease; we fail closed rather than recomputing
        concurrently across workers. Never delete an existing good snapshot.
        """
        query = StatisticsRequest.model_validate(query.model_dump())
        if (not getattr(self.settings, "ADMIN_PWA_ENABLED", False)
                or not self._r2.enabled or not self._redis_url
                or query.platform != "overall"
                or query.period not in ("weekly", "monthly", "all_time")):
            raise StatisticsUnavailable("Manual statistics refresh unavailable")

        lease, token = self._lease_key, uuid4().hex
        key = self.prefix + ":" + query.platform + ":" + query.period
        variant = (query.platform, query.period)
        try:
            async with asyncio.timeout(15), self._mutex:
                try:
                    acquired = await self._redis("set", lease, token, nx=True, ex=_LEASE_SECONDS)
                except _SharedUnavailable:
                    raise StatisticsUnavailable("Manual statistics coordination unavailable") from None
                if not acquired:
                    raise StatisticsUnavailable("Statistics refresh already in progress")
                try:
                    # Deliberately skip local, Redis and R2 reads on explicit demand.
                    raw, envelope = await self._compute(query)
                    # Guard against an unexpected projection being written to
                    # private R2 before the outer HTTP handler can inspect it.
                    data = envelope["data"]
                    if (data.get("available") is not True
                            or not isinstance(data.get("scope"), dict)
                            or data["scope"].get("section") != "overview"
                            or data.get("source") != "users + payments + canonical learning events"):
                        raise StatisticsUnavailable("Unexpected overview projection")
                    # Publish the new validated snapshot only after the R2 write
                    # succeeds; on failure leave the previous cache untouched.
                    await self._r2.put(kind="statistics", namespace=self._r2_namespace,
                                       variant=query.platform + "_" + query.period, raw=raw)
                    ttl = max(1, int(envelope["expires_at"] - self.clock()))
                    if not await self._redis("eval", _PUBLISH, 2, lease, key, token, raw, ttl):
                        raise StatisticsUnavailable("Manual statistics lease lost")
                    return self._remember(variant, envelope)
                except R2Unavailable:
                    raise StatisticsUnavailable("Manual statistics R2 write unavailable") from None
                except _SharedUnavailable:
                    raise StatisticsUnavailable("Manual statistics coordination lost") from None
                finally:
                    try:
                        await self._redis("eval", _RELEASE, 1, lease, token)
                    except _SharedUnavailable:
                        pass
        except TimeoutError:
            raise StatisticsUnavailable("Manual statistics refresh timed out") from None


    async def refresh_approved_section(self, query, *, section):
        """Owner-triggered ONE aggregate period; reuse existing scoped projection.

        No Redis dependency, no event collection, no changed business outcomes.
        A short PostgreSQL advisory lock and the per-worker shared mutex bound
        concurrent recomputation. The scheduled GitHub mirror never calls SQL.
        """
        query = StatisticsRequest.model_validate(query.model_dump())
        if (section not in _MANUAL_SECTIONS
                or (self._cache_scope not in (f"analytics_{section}_v1", f"analytics_{section}_v2")
                    and not (section == "report" and self._cache_scope == "analytics_report_v3"))
                or query.platform not in _REFRESH_PLATFORMS
                or query.period not in ("weekly", "monthly", "all_time")
                or not getattr(self.settings, "ADMIN_PWA_ENABLED", False)
                or not self._r2.enabled):
            raise StatisticsUnavailable("Manual statistics refresh unavailable")
        try:
            async with asyncio.timeout(65), self._mutex:
                recent_at = getattr(self, "_last_manual_section_refresh_at", {})
                if self.clock() - recent_at.get(query.platform, 0) < 60:
                    raise StatisticsUnavailable("Manual refresh recently completed")
                async with self.sessions() as db:
                    async with read_transaction(db):
                        dialect = db.get_bind().dialect.name
                        if dialect == "postgresql":
                            # Identical lock for this scoped source across workers.
                            lock_id = int.from_bytes(
                                hashlib.blake2b(self.prefix.encode(), digest_size=8).digest(),
                                "big", signed=True)
                            locked = (await db.execute(
                                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                                {"lock_id": lock_id})).scalar()
                            if locked is not True:
                                raise StatisticsUnavailable("Manual refresh already in progress")
                        elif dialect != "sqlite":
                            raise StatisticsUnavailable("Manual refresh requires PostgreSQL")

                        variant = query.platform + "_" + query.period
                        previous = await self._r2_refresh_io(
                            "get", kind="statistics", namespace=self._r2_namespace,
                            variant=variant)
                        stored = self._decode(previous, query)
                        if stored is not None:
                            observed = datetime.fromisoformat(
                                stored["data"]["generated_at"]).timestamp()
                            if 0 <= self.clock() - observed < 60:
                                raise StatisticsUnavailable("Manual refresh recently completed")

                        data = await self.loader(db, query)
                        if (not isinstance(data, dict)
                                or data.get("available") is not True
                                or data.get("platform") != query.platform
                                or data.get("period") != query.period
                                or data.get("source") != "first-party stored aggregate projections"
                                or not isinstance(data.get("scope"), dict)
                                or data["scope"].get("section") != section):
                            raise StatisticsUnavailable("Unexpected scoped projection")
                        expires = (datetime.fromisoformat(
                            data["generated_at"]).timestamp() + SNAPSHOT_SECONDS)
                        raw = json.dumps(
                            {"version": 1, "expires_at": expires, "data": data},
                            allow_nan=False, separators=(",", ":")).encode()
                        envelope = self._decode(raw, query)
                        if envelope is None:
                            raise StatisticsUnavailable("Invalid scoped projection")
                        # Durable R2 first; no local success on failed storage.
                        await self._r2_refresh_io(
                            "put", kind="statistics", namespace=self._r2_namespace,
                            variant=variant, raw=raw)

                self._remember((query.platform, query.period), envelope)
                self._last_manual_section_refresh_at = {**recent_at, query.platform: self.clock()}
                return {
                    "section": section, "platform": query.platform, "period": query.period,
                    "generated_at": envelope["data"]["generated_at"],
                    "expires_at": datetime.fromtimestamp(
                        envelope["expires_at"], timezone.utc).isoformat(),
                }
        except R2Unavailable as exc:
            self._log_r2_refresh_failure("Manual scoped refresh", exc)
            raise StatisticsUnavailable("Manual statistics R2 write unavailable") from None
        except TimeoutError:
            raise StatisticsUnavailable("Manual statistics refresh timed out") from None
        except StatisticsUnavailable:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Manual scoped refresh failed: %s", type(exc).__name__)
            raise StatisticsUnavailable("Manual statistics refresh unavailable") from None


    async def refresh_overview_bundle(self):
        """Recompute only verified overall aggregates and publish to private R2.

        Manual owner requests do NOT require Redis. A transaction-scoped
        PostgreSQL advisory lock protects multiple API processes, while the
        existing shared asyncio lock protects sections in this worker.
        All three projections are validated before the first R2 write.
        """
        if (not self._overview_local_revalidate
                or not getattr(self.settings, "ADMIN_PWA_ENABLED", False)
                or not self._r2.enabled):
            raise StatisticsUnavailable("Manual statistics refresh unavailable")
        periods = ("weekly", "monthly", "all_time")
        try:
            async with asyncio.timeout(80), self._mutex:
                if self.clock() - getattr(self, "_last_manual_refresh_at", 0) < 60:
                    raise StatisticsUnavailable("Manual refresh recently completed")
                prepared = {}
                results = {}
                async with self.sessions() as db:
                    async with read_transaction(db):
                        dialect = db.get_bind().dialect.name
                        if dialect == "postgresql":
                            # Stable 64-bit advisory ID, scoped to this DB and
                            # exact validated aggregate namespace.
                            lock_id = int.from_bytes(
                                hashlib.blake2b(self.prefix.encode(), digest_size=8).digest(),
                                "big", signed=True)
                            locked = (await db.execute(
                                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                                {"lock_id": lock_id})).scalar()
                            if locked is not True:
                                raise StatisticsUnavailable("Manual refresh already in progress")
                        elif dialect != "sqlite":
                            raise StatisticsUnavailable("Manual refresh requires PostgreSQL")

                        # R2 is also the durable cooldown across API workers;
                        # the endpoint explicitly ignores its normal 24h TTL.
                        recent = True
                        for period in periods:
                            query = StatisticsRequest(platform="overall", period=period)
                            previous = await self._r2_refresh_io(
                                "get", kind="statistics", namespace=self._r2_namespace,
                                variant="overall_" + period)
                            stored = self._decode(previous, query)
                            if stored is None:
                                recent = False
                                continue
                            observed = datetime.fromisoformat(
                                stored["data"]["generated_at"]).timestamp()
                            if not 0 <= self.clock() - observed < 60:
                                recent = False
                        if recent:
                            raise StatisticsUnavailable("Manual refresh recently completed")

                        # One repeatable-read DB transaction provides a coherent
                        # observation across the three overlapping windows.
                        for period in periods:
                            query = StatisticsRequest(platform="overall", period=period)
                            data = await self.loader(db, query)
                            if (data.get("available") is not True
                                    or data.get("source") != "users + payments + canonical learning events"
                                    or not isinstance(data.get("scope"), dict)
                                    or data["scope"].get("section") != "overview"):
                                raise StatisticsUnavailable("Unexpected overview projection")
                            expires = (datetime.fromisoformat(
                                data["generated_at"]).timestamp() + SNAPSHOT_SECONDS)
                            raw = json.dumps({"version": 1, "expires_at": expires,
                                              "data": data}, allow_nan=False,
                                             separators=(",", ":")).encode()
                            envelope = self._decode(raw, query)
                            if envelope is None:
                                raise StatisticsUnavailable("Invalid overview projection")
                            prepared[period] = (raw, envelope)

                        # An R2 failure can leave earlier periods updated, but
                        # cannot mark this request successful. No fake numbers
                        # or old latest aliases are returned by the workflow.
                        for period in periods:
                            await self._r2_refresh_io(
                                "put", kind="statistics", namespace=self._r2_namespace,
                                variant="overall_" + period, raw=prepared[period][0])

                for period in periods:
                    envelope = prepared[period][1]
                    self._remember(("overall", period), envelope)
                    results[period] = {
                        "generated_at": envelope["data"]["generated_at"],
                        "expires_at": datetime.fromtimestamp(
                            envelope["expires_at"], timezone.utc).isoformat(),
                    }
                self._last_manual_refresh_at = self.clock()
                return results
        except R2Unavailable as exc:
            # Keep the established line for log searches; the second line adds
            # the sanitized operation (get/put) and failure class.
            logger.warning("Manual overview refresh failed: R2Unavailable")
            self._log_r2_refresh_failure("Manual overview refresh", exc)
            raise StatisticsUnavailable("Manual statistics R2 write unavailable") from None
        except TimeoutError:
            raise StatisticsUnavailable("Manual statistics refresh timed out") from None
        except StatisticsUnavailable:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Manual overview refresh failed: %s", type(exc).__name__)
            raise StatisticsUnavailable("Manual statistics refresh unavailable") from None

    async def refresh_section_bundle(self, *, section, platform, periods):
        """Full refresh (behind ADMIN_PWA_FULL_REFRESH_ENABLED): one section and
        platform, every listed window, from this reader's UNCHANGED loader.

        Unlike `refresh_approved_section`, the windows share one repeatable-read
        transaction, one advisory lock and one group cooldown, so three windows
        never meet the legacy single-window cooldown. Returns per-window outcomes.
        """
        if (not isinstance(self._cache_scope, str)
                or not self._cache_scope.startswith(f"analytics_{section}_v")
                or platform not in _REFRESH_PLATFORMS or not periods
                or len(set(periods)) != len(periods)
                or any(period not in ("weekly", "monthly", "all_time") for period in periods)):
            raise StatisticsUnavailable("Manual statistics refresh unavailable")
        expected = (_SOURCE_OVERVIEW if section in ("home", "overview") and platform == "overall"
                    else _SOURCE_SCOPED)

        def accept(data, query):
            if (not isinstance(data, dict) or data.get("platform") != query.platform
                    or data.get("period") != query.period
                    or not isinstance(data.get("scope"), dict)
                    or data["scope"].get("section") != section):
                raise StatisticsUnavailable("Unexpected bundle projection")
            if data.get("available") is not True:
                # The loader's own verdict (e.g. not_instrumented) is reported,
                # never written to R2 and never turned into zeros.
                reason = data.get("reason")
                return reason if reason in _UNAVAILABLE_REASONS else "unavailable"
            if data.get("source") != expected or not isinstance(data.get("metrics"), dict):
                raise StatisticsUnavailable("Unexpected bundle projection")
            return None

        items = [(period, StatisticsRequest(platform=platform, period=period),
                  platform + "_" + period, (platform, period)) for period in periods]
        return await self._refresh_bundle(kind="statistics", group=platform, items=items, accept=accept)

    async def _refresh_bundle(self, *, kind, group, items, accept):
        if not getattr(self.settings, "ADMIN_PWA_ENABLED", False) or not self._r2.enabled:
            raise StatisticsUnavailable("Manual statistics refresh unavailable")
        outcomes, prepared, written = {}, [], []
        try:
            async with asyncio.timeout(_BUNDLE_SECONDS), self._mutex:
                if self.clock() - self._last_bundle_refresh_at.get(group, 0) < 60:
                    raise StatisticsUnavailable("Manual refresh recently completed")
                async with self.sessions() as db:
                    async with read_transaction(db):
                        dialect = db.get_bind().dialect.name
                        if dialect == "postgresql":
                            # Same lock as every refresh of this exact namespace.
                            lock_id = int.from_bytes(
                                hashlib.blake2b(self.prefix.encode(), digest_size=8).digest(),
                                "big", signed=True)
                            locked = (await db.execute(
                                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                                {"lock_id": lock_id})).scalar()
                            if locked is not True:
                                raise StatisticsUnavailable("Manual refresh already in progress")
                        elif dialect != "sqlite":
                            raise StatisticsUnavailable("Manual refresh requires PostgreSQL")

                        # R2 timestamps are the cooldown across API workers.
                        recent = True
                        for _period, query, variant, _local in items:
                            try:
                                stored = self._decode(await self._r2_refresh_io(
                                    "get", kind=kind, namespace=self._r2_namespace,
                                    variant=variant), query)
                            except R2Unavailable as exc:
                                self._log_r2_refresh_failure("Full refresh", exc)
                                raise StatisticsUnavailable("Manual statistics R2 read unavailable") from None
                            if stored is None or not 0 <= self.clock() - datetime.fromisoformat(
                                    stored["data"]["generated_at"]).timestamp() < 60:
                                recent = False
                        if recent:
                            raise StatisticsUnavailable("Manual refresh recently completed")

                        # Prepare and validate every window before the first write.
                        for period, query, variant, local in items:
                            data = await self.loader(db, query)
                            reason = accept(data, query)
                            if reason is not None:
                                outcomes[period] = {"status": "unavailable", "reason": reason}
                                continue
                            expires = (datetime.fromisoformat(data["generated_at"]).timestamp()
                                       + SNAPSHOT_SECONDS)
                            raw = json.dumps({"version": 1, "expires_at": expires, "data": data},
                                             allow_nan=False, separators=(",", ":")).encode()
                            envelope = self._decode(raw, query)
                            if envelope is None:
                                raise StatisticsUnavailable("Invalid bundle projection")
                            prepared.append((period, variant, local, raw, envelope))

                        for period, variant, local, raw, envelope in prepared:
                            try:
                                await self._r2_refresh_io("put", kind=kind,
                                                          namespace=self._r2_namespace,
                                                          variant=variant, raw=raw)
                            except R2Unavailable as exc:
                                # Earlier windows stay written (reported), later
                                # ones are not attempted; old snapshots remain.
                                self._log_r2_refresh_failure("Full refresh", exc)
                                outcomes[period] = {"status": "failed", "reason": "r2_write",
                                                    "failure_class": exc.failure_class}
                                for later, *_ in prepared[len(written) + 1:]:
                                    outcomes[later] = {"status": "failed", "reason": "not_attempted"}
                                break
                            written.append((period, local, envelope))
                            outcomes[period] = {
                                "status": "refreshed",
                                "generated_at": envelope["data"]["generated_at"],
                                "expires_at": datetime.fromtimestamp(
                                    envelope["expires_at"], timezone.utc).isoformat(),
                            }
                for _period, local, envelope in written:
                    self._remember(local, envelope)
                if written:
                    self._last_bundle_refresh_at = {**self._last_bundle_refresh_at,
                                                    group: self.clock()}
        except TimeoutError:
            raise StatisticsUnavailable("Manual statistics refresh timed out") from None
        except (StatisticsUnavailable, asyncio.CancelledError):
            raise
        except Exception as exc:
            logger.warning("Full refresh failed: %s", type(exc).__name__)
            raise StatisticsUnavailable("Manual statistics refresh unavailable") from None
        statuses = {outcome["status"] for outcome in outcomes.values()}
        if "failed" in statuses:
            status = "partial" if "refreshed" in statuses else "failed"
        else:
            status = "refreshed" if "refreshed" in statuses else "unavailable"
        return {"status": status, "periods": {period: outcomes[period]
                                              for period, *_ in items if period in outcomes}}

    async def __call__(self, query):
        query = StatisticsRequest.model_validate(query.model_dump())
        if not getattr(self.settings, "ADMIN_PWA_ENABLED", False):
            raise StatisticsUnavailable("Statistics disabled")
        variant = (query.platform, query.period)
        self._local = {key: entry for key, entry in self._local.items()
                       if self.clock() < entry["expires_at"] <= self.clock()+SNAPSHOT_SECONDS}
        cached = self._local.get(variant)
        if cached is not None and self.clock() < cached["expires_at"]:
            return await self._overview_local_hit(variant, cached, query)
        try:
            async with asyncio.timeout(16 if self._r2.enabled else 9), self._mutex:
                cached = self._local.get(variant)
                if cached is not None and self.clock() < cached["expires_at"]:
                    return await self._overview_local_hit(variant, cached, query)
                key = self.prefix+":"+query.platform+":"+query.period
                lease = self._lease_key
                token = uuid4().hex
                shared = True
                try:
                    cached = await self._shared(key, query)
                    if cached is not None:
                        return self._remember(variant, cached)
                    if self.clock() < self._load_retry_at:
                        raise StatisticsUnavailable("Statistics refresh cooling down")
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
                # R2 stores a private, checked snapshot for restart/cross-worker
                # recovery. A Redis lease protects the expensive read path.
                if self._r2.enabled:
                    try:
                        r2_raw = await self._r2.get(kind="statistics", namespace=self._r2_namespace,
                                                   variant=query.platform+"_"+query.period)
                        r2_cached = self._decode(r2_raw, query)
                        if r2_cached is not None:
                            if shared:
                                try:
                                    await self._redis("eval", _PUBLISH, 2, lease, key, token, r2_raw,
                                                      max(1, int(r2_cached["expires_at"]-self.clock())))
                                except _SharedUnavailable:
                                    pass
                            return self._remember(variant, r2_cached)
                    except R2Unavailable:
                        logger.warning("Admin PWA R2 mirror unavailable; falling back to daily Redis cache")
                raw, envelope = await self._compute(query)
                if shared:
                    try:
                        published = await self._redis("eval", _PUBLISH, 2, lease, key, token, raw,
                                                      max(1, int(envelope["expires_at"]-self.clock())))
                        if not published:
                            self._load_retry_at = self.clock()+_RETRY_SECONDS
                            raise StatisticsUnavailable("Statistics refresh lease lost")
                    except _SharedUnavailable:
                        pass  # valid local snapshot still prevents per-request SQL
                if self._r2.enabled:
                    try:
                        await self._r2.put(kind="statistics", namespace=self._r2_namespace,
                                           variant=query.platform+"_"+query.period, raw=raw)
                    except R2Unavailable:
                        logger.warning("Admin PWA R2 mirror write unavailable; Redis snapshot remains valid")
                return self._remember(variant, envelope)
        except TimeoutError:
            raise StatisticsUnavailable("Statistics refresh busy") from None
