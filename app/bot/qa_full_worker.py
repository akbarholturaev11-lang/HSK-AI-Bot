"""Full-featured Telegram bot polling worker for isolated universal account QA.

Unlike the API (HTTP-only), this runs the *production dispatcher* on the
staging database and staging Telegram bot. Its scheduler, course seeding and
retention services are enabled to exercise non-login regressions.

All effects must be restricted to disposable staging accounts and the QA bot.
Never point this worker at production, even to troubleshoot.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os

from sqlalchemy.engine import make_url

from app.config import settings
from app.db.session import async_session_maker, engine, init_db
from app.services.course_seed_service import CourseSeedService

log = logging.getLogger(__name__)

QA_ENV = "staging"
QA_DB_HOST = "hsk-universal-qa-db.railway.internal"
QA_DB_NAME = "hsk_universal_qa_schema"
QA_HTTPS_ORIGIN = "https://hsk-universal-qa-api-staging.up.railway.app"
PRODUCTION_BOT = "darsi_chini_bot"


def validate_qa_settings(env: dict[str, str], config) -> str:
    """No bot API requests or DB writes until every safety check passes."""
    environment = env.get("RAILWAY_ENVIRONMENT_NAME", "").lower()
    standalone = environment == "qa"
    if standalone:
        if env.get("RAILWAY_PROJECT_ID") != "7f737cb9-be6a-45cd-b6b3-8263b41d1cfd":
            raise RuntimeError("qa_worker_wrong_project")
        expected_host = "postgres.railway.internal"
        expected_db = "railway"
        expected_origin = "https://hsk-qa-api-qa.up.railway.app"
    elif environment == QA_ENV:
        expected_host = QA_DB_HOST
        expected_db = QA_DB_NAME
        expected_origin = QA_HTTPS_ORIGIN
    else:
        raise RuntimeError("qa_worker_not_staging")
    if env.get("HSK_QA_FULL_FEATURES_ENABLED", "").lower() != "true":
        raise RuntimeError("qa_full_features_disabled")
    username = (config.BOT_USERNAME or "").strip().lstrip("@").lower()
    if not username or username == PRODUCTION_BOT or not username.endswith("bot"):
        raise RuntimeError("qa_worker_bad_username")
    if not config.BOT_TOKEN:
        raise RuntimeError("qa_worker_missing_token")
    try:
        parsed = make_url(config.DATABASE_URL)
    except Exception as exc:
        raise RuntimeError("qa_worker_bad_database_url") from exc
    if (parsed.host or "").lower() != expected_host or parsed.database != expected_db:
        raise RuntimeError("qa_worker_wrong_database")
    if getattr(config, "PUBLIC_SITE_URL", "") != expected_origin:
        raise RuntimeError("qa_worker_wrong_site_origin")
    if getattr(config, "MINI_APP_BASE_URL", "") != expected_origin + "/course-v3.html":
        raise RuntimeError("qa_worker_wrong_miniapp_origin")
    if getattr(config, "OAUTH_NATIVE_RETURN_SCHEME", None) != "pomp-hsk-ai-qa":
        raise RuntimeError("qa_worker_wrong_return_scheme")
    return username


async def seed_courses() -> None:
    async with async_session_maker() as session:
        count = await CourseSeedService(session).sync_all_lessons()
    log.info("QA course seed completed, count=%s", count)


async def run_full_qa_worker() -> None:
    username = validate_qa_settings(dict(os.environ), settings)

    # app.main already constructs the one full dispatcher at module import.
    # Calling create_bot() again attaches singleton routers twice and raises.
    import app.main as hsk_server
    bot, dp = hsk_server.bot, hsk_server.dp
    background_tasks: list[asyncio.Task] = []
    try:
        identity = await bot.get_me()
        if not identity.is_bot or (identity.username or "").lower() != username:
            raise RuntimeError("qa_worker_token_username_mismatch")
        # A webhook/poller owned by someone else must be fixed explicitly.
        hook = await bot.get_webhook_info()
        if hook.url:
            raise RuntimeError("qa_worker_webhook_already_set")

        await init_db()  # Writes only to verified isolated staging DB.
        # Reuse the already-loaded module; do not rebuild dispatcher/routers.
        background_tasks.append(asyncio.create_task(seed_courses(), name="qa-seed-courses"))
        if os.environ.get("HSK_QA_SCHEDULER_ENABLED", "").lower() == "true":
            background_tasks.append(asyncio.create_task(
                hsk_server._background_scheduler(bot), name="qa-all-reminder-jobs",
            ))
            background_tasks.append(asyncio.create_task(
                hsk_server._desktop_auth_retention_scheduler(), name="qa-auth-retention",
            ))
        log.info("Full HSK QA Telegram bot starting: @%s, schedulers=%s",
                 username, len(background_tasks) > 1)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(),
                               close_bot_session=False)
    finally:
        for task in background_tasks:
            task.cancel()
        for task in background_tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_full_qa_worker())
