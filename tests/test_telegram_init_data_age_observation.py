"""Read-only Telegram initData age classification; no session expiry rollout."""
import hashlib
import hmac
import json
import unittest
from urllib.parse import urlencode

from app.services.telegram_webapp_auth import (
    classify_verified_webapp_init_data_age,
    extract_verified_webapp_user_id,
    extract_fresh_verified_webapp_user_id,
)

TOKEN = "9123456:synthetic-unusable-secret"
NOW = 1800000000
USER_ID = 14567


def signed_init_data(*, auth_date=NOW, include_date=True):
    values = {"user": json.dumps({"id": USER_ID}, separators=(",", ":"))}
    if include_date:
        values["auth_date"] = str(auth_date)
    message = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, message.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


class TelegramInitDataAgeObservationTests(unittest.TestCase):
    def test_fresh_and_old_payloads_remain_signature_valid(self):
        for time, status in ((NOW, "fresh"), (NOW - 86400, "fresh"),
                             (NOW - 86401, "stale"), (NOW + 61, "future_auth_date")):
            with self.subTest(status=status):
                signed = signed_init_data(auth_date=time)
                self.assertEqual(extract_verified_webapp_user_id(signed, TOKEN), USER_ID)
                self.assertEqual(classify_verified_webapp_init_data_age(
                    signed, TOKEN, now_timestamp=NOW), status)

    def test_bad_signature_and_missing_or_malformed_dates(self):
        self.assertEqual(classify_verified_webapp_init_data_age(
            signed_init_data(include_date=False), TOKEN, now_timestamp=NOW),
            "invalid_auth_date")
        self.assertEqual(classify_verified_webapp_init_data_age(
            signed_init_data(auth_date="not-a-time"), TOKEN, now_timestamp=NOW),
            "invalid_auth_date")
        forged = signed_init_data().replace("14567", "14568")
        self.assertEqual(classify_verified_webapp_init_data_age(
            forged, TOKEN, now_timestamp=NOW), "invalid_signature")

    def test_existing_strict_helper_still_rejects_stale_when_explicitly_used(self):
        data = signed_init_data(auth_date=NOW - 86401)
        self.assertEqual(extract_verified_webapp_user_id(data, TOKEN), USER_ID)
        self.assertIsNone(extract_fresh_verified_webapp_user_id(
            data, TOKEN, max_age_seconds=86400, now_timestamp=NOW))
        self.assertEqual(extract_fresh_verified_webapp_user_id(
            signed_init_data(), TOKEN, max_age_seconds=86400,
            now_timestamp=NOW), USER_ID)
