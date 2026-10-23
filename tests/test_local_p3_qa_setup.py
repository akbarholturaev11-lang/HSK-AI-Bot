"""Regression guards for the full P3 local/off-Railway QA bootstrap."""
from pathlib import Path

import pytest

from scripts.local_p3_qa_runtime_guard import validate_without_network

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "ops" / "p3-local-qa"


def _valid_env():
    return {
        "HSK_P3_LOCAL_QA": "1",
        "DATABASE_URL": (
            "postgresql+asyncpg://hsk_p3_local_qa:" + "a" * 48
            + "@postgres:5432/hsk_p3_local_qa"
        ),
        "REDIS_URL": "redis://redis:6379/0",
        "PUBLIC_SITE_URL": "http://localhost:18080",
        "MINI_APP_BASE_URL": "http://localhost:18080/course-v3.html",
        "FEEDBACK_NOTIFY_CHAT_IDS": "",
        "OAUTH_NATIVE_RETURN_SCHEME": "",
        "OPENAI_API_KEY": "",
        "GEMINI_API_KEY": "",
        "ANDROID_FCM_SERVICE_ACCOUNT_JSON": "",
        "GOOGLE_DESKTOP_CLIENT_SECRET": "",
        "APPLE_PRIVATE_KEY": "",
        "GOOGLE_OAUTH_ENABLED": "false",
        "APPLE_OAUTH_ENABLED": "false",
        "BOT_TOKEN": "123456789:" + "x" * 35,
        "HSK_P3_QA_EXPECTED_BOT_USERNAME": "Gentss_3bot",
    }


def test_valid_qa_settings_are_allowed_without_network():
    validate_without_network(_valid_env())


@pytest.mark.parametrize("field,value", [
    ("DATABASE_URL", "postgresql+asyncpg://user:pass@production.db:5432/main"),
    ("REDIS_URL", "redis://production:6379/0"),
    ("PUBLIC_SITE_URL", "https://telegram-chinese-bot-production.up.railway.app"),
    ("PUBLIC_SITE_URL", "https://my.example.com/other/path"),
    ("RAILWAY_PROJECT_ID", "production-project"),
    ("FEEDBACK_NOTIFY_CHAT_IDS", "-1000000000000"),
    ("GEMINI_API_KEY", "inherited-prod"),
    ("GOOGLE_DESKTOP_CLIENT_SECRET", "inherited-prod"),
    ("OAUTH_NATIVE_RETURN_SCHEME", "pomp-hsk-ai"),
    ("HSK_P3_QA_EXPECTED_BOT_USERNAME", "another_bot"),
    ("BOT_TOKEN", "not-a-valid-test-token"),
])
def test_unsafe_config_is_rejected(field, value):
    env = _valid_env()
    env[field] = value
    with pytest.raises(RuntimeError):
        validate_without_network(env)


def test_compose_has_full_app_and_private_db():
    compose = (SETUP / "compose.yml").read_text(encoding="utf-8")
    assert "scripts/local_p3_qa_bootstrap.py" in compose
    assert "scripts/local_p3_qa_runtime_guard.py" in compose
    assert "bash scripts/start.sh" in compose
    assert "app.staging_qa" not in compose
    assert "127.0.0.1:18080:8000" in compose
    assert "REDIS_URL: redis://redis:6379/0" in compose
    assert "service_completed_successfully" in compose
    assert "Gentss_3bot" in compose
    assert "GOOGLE_OAUTH_ENABLED: \"false\"" in compose
    assert "APPLE_OAUTH_ENABLED: \"false\"" in compose


def test_bootstrap_safely_reuses_reviewed_schema_path():
    boot = (ROOT / "scripts/local_p3_qa_bootstrap.py").read_text(encoding="utf-8")
    assert "_create_empty_orm_schema()" in boot
    assert "command.stamp(cfg, EXPECTED_BASELINE)" in boot
    assert "command.upgrade(cfg, \"head\")" in boot
    assert 'if "alembic_version" not in tables:' in boot
    assert "verify_qa_tables()" in boot
