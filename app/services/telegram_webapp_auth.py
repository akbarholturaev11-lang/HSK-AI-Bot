import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def extract_verified_webapp_user_id(init_data: str, bot_token: str) -> int | None:
    if not init_data or not bot_token:
        return None

    params = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = params.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    try:
        user_data = json.loads(params.get("user") or "{}")
        return int(user_data["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def classify_verified_webapp_init_data_age(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 86400,
    now_timestamp: int | None = None,
    future_skew_seconds: int = 60,
) -> str:
    """Read-only age category. Never log initData, user IDs, or the HMAC.

    A status of 'stale' is NOT an authorization denial. Enforcement needs a
    separate client session-renewal strategy before changing live behavior.
    """
    if extract_verified_webapp_user_id(init_data, bot_token) is None:
        return "invalid_signature"
    try:
        params = dict(parse_qsl(init_data, keep_blank_values=True))
        auth_date = int(params["auth_date"])
        now = int(now_timestamp if now_timestamp is not None else time.time())
    except (KeyError, TypeError, ValueError):
        return "invalid_auth_date"
    if auth_date > now + max(0, int(future_skew_seconds)):
        return "future_auth_date"
    if auth_date < now - max(60, int(max_age_seconds)):
        return "stale"
    return "fresh"

def extract_fresh_verified_webapp_user_id(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int,
    now_timestamp: int | None = None,
    future_skew_seconds: int = 60,
) -> int | None:
    """Verify Telegram WebApp data and reject stale or future payloads."""

    telegram_id = extract_verified_webapp_user_id(init_data, bot_token)
    if telegram_id is None:
        return None

    try:
        params = dict(parse_qsl(init_data, keep_blank_values=True))
        auth_date = int(params["auth_date"])
        now = int(now_timestamp if now_timestamp is not None else time.time())
        max_age = max(60, int(max_age_seconds))
        future_skew = max(0, int(future_skew_seconds))
    except (KeyError, TypeError, ValueError):
        return None

    if auth_date > now + future_skew:
        return None
    if auth_date < now - max_age:
        return None
    return telegram_id
