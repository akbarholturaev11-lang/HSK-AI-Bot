"""Private, on-demand daily statistics. Never cache authorization or commands."""
import asyncio
import copy
from datetime import datetime, timezone
import hashlib
import json
import logging
import time
from uuid import uuid4

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

from app.admin_api.pwa_read import StatisticsRequest, read_transaction, statistics

SNAPSHOT_SECONDS = 24 * 60 * 60
logger = logging.getLogger(__name__)
_LOAD_SECONDS = 8
_LEASE_SECONDS = 45
_RETRY_SECONDS = 30
_MAX_BYTES = 128 * 1024
_FIELDS = {"platform", "period", "since", "generated_at", "timezone", "platform_counts_overlap",
           "available", "metrics", "source", "scope", "reason", "metric_definitions"}
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
                 namespace=None, clock=time.time):
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
        self.prefix = "hsk:admin:stats:v1:{"+(namespace or digest)+"}"
        self._local = {}
        self._mutex = asyncio.Lock()
        self._redis_retry_at = 0.0
        self._load_retry_at = 0.0

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
                self._client = Redis.from_url(self._redis_url, socket_connect_timeout=.25,
                    socket_timeout=.25, retry=Retry(NoBackoff(), 0), max_connections=4)
            async with asyncio.timeout(.35):
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
            if (not isinstance(data, dict) or set(data)-_FIELDS or data.get("platform") != query.platform
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
        return self._result(envelope)

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
        except Exception:
            self._load_retry_at = self.clock()+_RETRY_SECONDS
            raise StatisticsUnavailable("Statistics refresh unavailable") from None

    async def __call__(self, query):
        query = StatisticsRequest.model_validate(query.model_dump())
        if not getattr(self.settings, "ADMIN_PWA_ENABLED", False):
            raise StatisticsUnavailable("Statistics disabled")
        variant = (query.platform, query.period)
        self._local = {key: entry for key, entry in self._local.items()
                       if self.clock() < entry["expires_at"] <= self.clock()+SNAPSHOT_SECONDS}
        cached = self._local.get(variant)
        if cached is not None and self.clock() < cached["expires_at"]:
            return self._result(cached)
        try:
            async with asyncio.timeout(9), self._mutex:
                cached = self._local.get(variant)
                if cached is not None and self.clock() < cached["expires_at"]:
                    return self._result(cached)
                key = self.prefix+":"+query.platform+":"+query.period
                lease = self.prefix+":refresh"
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
                return self._remember(variant, envelope)
        except TimeoutError:
            raise StatisticsUnavailable("Statistics refresh busy") from None
