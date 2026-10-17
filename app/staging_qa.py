"""Staging-only ASGI entrypoint for course/API source QA.

Start using uvicorn app.staging_qa:app --host 0.0.0.0 --port $PORT.
Production still uses app.main:app, with unchanged lifespan.
"""
import os
from contextlib import asynccontextmanager

from scripts.i18n_staging_boot_guard import (
    normalize_staging_db_url,
    validate_staging_environment,
)

# Railway supplies standard postgresql://; SQLAlchemy requires asyncpg.
# Validate the exact isolated QA database host after this driver conversion.
os.environ["DATABASE_URL"] = normalize_staging_db_url(
    os.environ.get("DATABASE_URL", "")
)
validate_staging_environment(os.environ)

# Deliberately fake and unusable as a real Telegram bot. Never inherit a
# production BOT_TOKEN in staging. It only enables the existing router imports.
os.environ["BOT_TOKEN"] = "100000001:" + "A" * 35

from app.db.session import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@asynccontextmanager
async def staging_qa_lifespan(_app):
    """Initialize only isolated staging database; never start bot workers."""
    await init_db()
    try:
        yield
    finally:
        await engine.dispose()


# No production bot polling, seeding, notifications, campaign sends,
# subscription-expiry background schedulers or retention cleanup.
app.router.lifespan_context = staging_qa_lifespan
