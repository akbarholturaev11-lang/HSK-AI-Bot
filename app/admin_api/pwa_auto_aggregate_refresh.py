"""Optional bounded automatic refresh of private Admin PWA overview aggregates.

GitHub polls R2 every six hours, but the Admin PWA 24-hour source cache
normally refreshes only on authenticated page views. This scheduler reuses the
exact same reader/SQL authorization boundary from a server-owned job, and
NEVER bypasses daily Redis/R2 caching or publishes user-level data.

No new HTTP endpoint, GitHub credentials, SQL writes or permanent worker.
All failures are isolated from the bot, payments and Admin PWA.
"""
import asyncio
from datetime import datetime, timezone
import logging
import re
import time

from redis.asyncio import Redis

from app.admin_api.pwa_analytics_cache import AnalyticsRequest
from app.admin_api.pwa_statistics_cache import StatisticsUnavailable

logger = logging.getLogger(__name__)
TICK_SECONDS = 3600
STARTUP_DELAY_SECONDS = 120
MAX_RUN_SECONDS = 60
REDIS_TIMEOUT_SECONDS = 2
# An hourly UTC bucket is idempotent across workers/restarts. Redis is required.
_HOURLY_KEY_TTL_SECONDS = 7200
_PERIODS = ("weekly", "monthly", "all_time")


def enabled(settings_obj):
    return all((
        getattr(settings_obj, "ADMIN_PWA_AUTO_AGGREGATE_REFRESH_ENABLED", False),
        getattr(settings_obj, "ADMIN_PWA_ENABLED", False),
        getattr(settings_obj, "ADMIN_PWA_R2_AGGREGATE_ENABLED", False),
        bool(getattr(settings_obj, "REDIS_URL", "")),
    ))


async def refresh_once(*, settings_obj, analytics_reader, now=None, redis_factory=Redis.from_url):
    """Run at most once per UTC hour across all instances sharing Redis.

    Returns a status without sensitive values. The existing daily reader
    guarantees that valid 24h aggregates do NOT run SQL again.
    """
    if not enabled(settings_obj):
        return {"status": "disabled", "refreshed_periods": ()}

    reader = getattr(analytics_reader, "_readers", {}).get("overview")
    namespace = getattr(reader, "_r2_namespace", "")
    if not isinstance(namespace, str) or re.fullmatch(r"[0-9a-f]{24}", namespace) is None:
        return {"status": "unavailable", "refreshed_periods": ()}

    utc_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    hour = utc_now.strftime("%Y%m%d%H")
    key = "hsk:admin:aggregates:automatic:v1:" + namespace + ":" + hour
    client = None
    try:
        client = redis_factory(
            settings_obj.REDIS_URL,
            socket_connect_timeout=.5, socket_timeout=.5,
            retry_on_timeout=False, max_connections=2,
        )
        async with asyncio.timeout(REDIS_TIMEOUT_SECONDS):
            claimed = await client.set(key, "1", ex=_HOURLY_KEY_TTL_SECONDS, nx=True)
        if not claimed:
            return {"status": "already_checked", "refreshed_periods": ()}
    except asyncio.CancelledError:
        raise
    except Exception:
        # Fail CLOSED when the shared lock cannot be acquired.
        logger.warning("Admin PWA automatic aggregate refresh skipped: Redis coordination unavailable")
        return {"status": "redis_unavailable", "refreshed_periods": ()}
    finally:
        if client is not None:
            try:
                await asyncio.wait_for(client.aclose(), timeout=REDIS_TIMEOUT_SECONDS)
            except (OSError, RuntimeError, TimeoutError):
                pass

    done = []
    failed = []
    for period in _PERIODS:
        try:
            # The existing daily reader selects local / Redis / R2 before SQL.
            # A cache hit does not run SQL, so hourly checks remain inexpensive.
            await analytics_reader(
                AnalyticsRequest(section="overview", period=period, platform="overall"))
            done.append(period)
        except asyncio.CancelledError:
            raise
        except (StatisticsUnavailable, TimeoutError):
            failed.append(period)
        except Exception:
            # Never log query payloads/credentials; retry on the next UTC hour.
            failed.append(period)
    if failed:
        logger.warning("Admin PWA automatic aggregate refresh incomplete: %d of %d period(s) failed",
                       len(failed), len(_PERIODS))
    else:
        logger.info("Admin PWA automatic aggregate refresh checked all 3 cached periods")
    return {"status": "partial" if failed else "ok", "refreshed_periods": tuple(done)}


async def overview_refresh_scheduler(*, settings_obj, analytics_reader,
                                     initial_delay=STARTUP_DELAY_SECONDS,
                                     tick_seconds=TICK_SECONDS,
                                     refresh=refresh_once):
    """Independent startup task, guarded by one explicit production kill switch."""
    if not enabled(settings_obj):
        return
    await asyncio.sleep(initial_delay)
    while enabled(settings_obj):
        try:
            async with asyncio.timeout(MAX_RUN_SECONDS):
                await refresh(settings_obj=settings_obj, analytics_reader=analytics_reader)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Fail safe; never take down the server or other background workers.
            logger.error("Admin PWA automatic aggregate refresh task unavailable")
        await asyncio.sleep(tick_seconds)
