"""Runtime safety gate for the real HSK AI app on isolated local QA.

The P3 QA Docker Compose launches the unmodified app.main:app and therefore
starts Telegram polling/schedulers. Verify the token belongs to the dedicated
test bot *before* that process starts. Never print or persist credentials.
"""
from __future__ import annotations

import json
import os
import re
from urllib.parse import urlsplit
from urllib.request import urlopen

from sqlalchemy.engine import make_url

EXPECTED_HOST = "postgres"
EXPECTED_DB = "hsk_p3_local_qa"
EXPECTED_USER = "hsk_p3_local_qa"


def validate_without_network(env: dict[str, str]) -> None:
    if env.get("HSK_P3_LOCAL_QA") != "1":
        raise RuntimeError("local_p3_qa_mode_not_enabled")
    if any(env.get(key) for key in ("RAILWAY_PROJECT_ID", "RAILWAY_ENVIRONMENT_NAME")):
        raise RuntimeError("local_p3_qa_must_not_run_inside_railway")
    try:
        db = make_url(env.get("DATABASE_URL", ""))
    except Exception:
        raise RuntimeError("local_p3_qa_database_url_invalid") from None
    if (db.drivername != "postgresql+asyncpg"
            or db.host != EXPECTED_HOST or db.port != 5432
            or db.database != EXPECTED_DB or db.username != EXPECTED_USER
            or not db.password or not re.fullmatch(r"[0-9a-f]{40,128}", db.password)):
        raise RuntimeError("local_p3_qa_database_is_not_isolated")
    if env.get("REDIS_URL") != "redis://redis:6379/0":
        raise RuntimeError("local_p3_qa_redis_is_not_isolated")
    if env.get("FEEDBACK_NOTIFY_CHAT_IDS", "").strip():
        raise RuntimeError("local_p3_qa_refuses_external_feedback_chat")
    if env.get("OAUTH_NATIVE_RETURN_SCHEME") != "":
        raise RuntimeError("local_p3_qa_requires_disabled_native_app_handoff")
    if any(env.get(k) for k in (
        "OPENAI_API_KEY", "GEMINI_API_KEY", "ANDROID_FCM_SERVICE_ACCOUNT_JSON",
        "GOOGLE_DESKTOP_CLIENT_SECRET", "APPLE_PRIVATE_KEY"
    )):
        raise RuntimeError("local_p3_qa_refuses_inherited_provider_secrets")
    if env.get("GOOGLE_OAUTH_ENABLED") != "false" or env.get("APPLE_OAUTH_ENABLED") != "false":
        raise RuntimeError("local_p3_qa_external_login_disabled")
    origin = env.get("PUBLIC_SITE_URL", "").rstrip("/")
    mini_app_url = env.get("MINI_APP_BASE_URL", "")
    try:
        parsed = urlsplit(origin)
    except ValueError:
        raise RuntimeError("local_p3_qa_origin_invalid") from None
    allowed_local = (parsed.scheme == "http"
                     and parsed.hostname in {"localhost", "127.0.0.1"}
                     and parsed.port == 18080)
    allowed_https = parsed.scheme == "https" and parsed.hostname is not None
    if not (allowed_local or allowed_https):
        raise RuntimeError("local_p3_qa_origin_must_be_https_or_localhost")
    if ("railway.app" in (parsed.hostname or "")
            or "production" in (parsed.hostname or "")
            or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment
            or mini_app_url != origin + "/course-v3.html"):
        raise RuntimeError("local_p3_qa_origin_is_not_an_isolated_test_host")
    token = env.get("BOT_TOKEN", "")
    if not re.fullmatch(r"[0-9]{6,15}:[A-Za-z0-9_-]{25,}", token):
        raise RuntimeError("local_p3_qa_requires_separate_test_bot_token")
    if env.get("HSK_P3_QA_EXPECTED_BOT_USERNAME", "").lstrip("@").lower() != "gentss_3bot":
        raise RuntimeError("local_p3_qa_bot_username_must_be_preapproved_test_bot")


def verify_telegram_bot(env: dict[str, str]) -> None:
    url = "https://api.telegram.org/bot" + env["BOT_TOKEN"] + "/getMe"
    try:
        with urlopen(url, timeout=12) as response:
            body = json.load(response)
        actual = body.get("result", {}).get("username", "").lower()
        if not body.get("ok") or actual != "gentss_3bot":
            raise ValueError("unexpected_bot_identity")
    except Exception:
        # Deliberately suppress the URL: urllib errors can expose bot tokens.
        raise RuntimeError("local_p3_qa_test_bot_verification_failed") from None


def main() -> None:
    env = dict(os.environ)
    validate_without_network(env)
    verify_telegram_bot(env)
    print("P3_LOCAL_QA_TEST_BOT_VERIFIED; ISOLATED_DB; FULL_APP_START_ALLOWED")


if __name__ == "__main__":
    main()
