"""Pure, fail-closed environment verification for an isolated Railway QA boot.

No environment or secrets are loaded by importing this module.
The validation deliberately rejects production Railway and inherited BOT_TOKEN.
"""
from urllib.parse import urlsplit

def validate_staging_environment(env):
    if env.get("HSK_STAGING_QA_MODE") != "1":
        raise RuntimeError("QA boot requires explicit HSK_STAGING_QA_MODE=1")
    if env.get("RAILWAY_ENVIRONMENT_NAME") != "staging":
        raise RuntimeError("QA boot requires Railway staging environment")
    if env.get("BOT_TOKEN"):
        raise RuntimeError("QA boot refuses an inherited Telegram bot token")
    db_url = env.get("DATABASE_URL", "")
    expected_host = env.get("HSK_STAGING_DB_HOST", "")
    try:
        parsed = urlsplit(db_url)
    except ValueError:
        raise RuntimeError("QA database connection string invalid") from None
    if (parsed.scheme != "postgresql+asyncpg" or
            not parsed.hostname or not expected_host or
            parsed.hostname.lower() != expected_host.lower() or
            not parsed.username or not parsed.password or not parsed.path.strip("/")):
        raise RuntimeError("QA requires the explicitly bound staging PostgreSQL host")
    if env.get("OPENAI_API_KEY") or env.get("GEMINI_API_KEY"):
        raise RuntimeError("QA boot refuses inherited paid AI provider keys")
    if env.get("ANDROID_FCM_SERVICE_ACCOUNT_JSON") or env.get("GOOGLE_DESKTOP_CLIENT_SECRET"):
        raise RuntimeError("QA boot refuses inherited production integration credentials")
    return True
