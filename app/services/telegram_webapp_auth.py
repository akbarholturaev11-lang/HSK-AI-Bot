import hashlib
import hmac
import json
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
