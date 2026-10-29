"""Exact, secret-free binding for one isolated Smart QA deployment."""
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone

PROJECT_ID = "adfa0e91-0905-4cf6-82cb-ddcc806fa3c3"
ENVIRONMENT_ID = "3fcae398-1bca-4162-b839-57875ac20bc6"
SERVICE_ID = "a56e0543-d4b3-44dd-a080-eb5c93174756"
DOMAIN = "smart-qa-api-qa.up.railway.app"
DB_HOST = "postgres.railway.internal"
DB_NAME = "railway"
FIXTURE_VERSION = "smart-qa-synthetic-v1"
APP_VERSION = "1.7.23-qa"
USER_ID = 900000001
DEVICE_IDS = ("00000000-0000-4000-8000-000000000101", "00000000-0000-4000-8000-000000000102")
SESSION_IDS = ("00000000-0000-4000-8000-000000000201", "00000000-0000-4000-8000-000000000202")
JOB_ID = "00000000-0000-4000-8000-000000000301"
JOB_IDS = (JOB_ID, "00000000-0000-4000-8000-000000000302")


def database_url(value):
    if value.startswith("postgresql://"):
        return "postgresql+asyncpg://" + value[len("postgresql://"):]
    return value


def validate(env, *, seed=False):
    expected = {"RAILWAY_PROJECT_ID": PROJECT_ID, "RAILWAY_ENVIRONMENT_ID": ENVIRONMENT_ID,
                "RAILWAY_ENVIRONMENT_NAME": "qa", "RAILWAY_SERVICE_ID": SERVICE_ID,
                "RAILWAY_PUBLIC_DOMAIN": DOMAIN, "HSK_SMART_QA_MODE": "1"}
    if any(env.get(k) != value for k, value in expected.items()):
        raise RuntimeError("smart_qa_deployment_binding_invalid")
    forbidden = ("BOT_TOKEN", "OPENAI_API_KEY", "GEMINI_API_KEY", "ANDROID_FCM_SERVICE_ACCOUNT_JSON",
                 "GOOGLE_DESKTOP_CLIENT_SECRET", "APPLE_PRIVATE_KEY", "TELEGRAM_BOT_TOKEN")
    if any(env.get(k) for k in forbidden):
        raise RuntimeError("smart_qa_inherited_provider_credentials")
    try:
        db = urlsplit(database_url(env.get("DATABASE_URL", "")))
        valid = (db.scheme == "postgresql+asyncpg" and db.hostname == DB_HOST and db.path == "/"+DB_NAME and
                 db.port in (None, 5432) and db.username and db.password and not db.query and not db.fragment)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise RuntimeError("smart_qa_database_binding_invalid")
    if len(env.get("DESKTOP_AUTH_SIGNING_SECRET", "")) < 48:
        raise RuntimeError("smart_qa_native_secret_required")
    if seed and any(len(env.get("HSK_SMART_QA_REFRESH_"+str(n), "")) < 64 for n in (1, 2)):
        raise RuntimeError("smart_qa_private_refresh_fixture_required")
    if seed:
        try:
            until = datetime.fromisoformat(env.get("HSK_SMART_QA_UNTIL", "").replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if until.tzinfo is None or not now < until <= now+timedelta(days=1):
                raise ValueError()
        except (TypeError, ValueError):
            raise RuntimeError("smart_qa_finite_seed_window_required") from None
    return database_url(env["DATABASE_URL"])
