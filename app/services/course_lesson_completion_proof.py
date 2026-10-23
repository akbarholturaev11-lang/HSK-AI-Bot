"""Short-lived server-signed proof that a Mini App lesson was actually opened.

This proves authorization through /api/v3/lesson/start, *not* that every
exercise was answered. Server-side exercise grading is a separate concern.
No database migration, client-secret exposure, or third-party dependency.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time


PROOF_TTL_SECONDS = 24 * 60 * 60
PROOF_FUTURE_SKEW_SECONDS = 60
PROOF_VERSION = 1


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.b64decode(
        value + "=" * (-len(value) % 4), altchars=b"-_", validate=True,
    )


def _signature(payload: bytes, *, secret: str) -> bytes:
    # Domain separation keeps these tokens independent of Telegram initData.
    key = hashlib.sha256(("hskai:lesson-completion:v1:" + secret).encode()).digest()
    return hmac.new(key, payload, hashlib.sha256).digest()


def issue_lesson_completion_proof(
    *, user_id: int, level: str, lesson_order: int, secret: str, now: int | None = None,
) -> str:
    issued_at = int(time.time() if now is None else now)
    payload = json.dumps(
        [PROOF_VERSION, int(user_id), str(level), int(lesson_order),
         issued_at, secrets.token_hex(12)],
        separators=(",", ":"),
    ).encode("utf-8")
    return _encode(payload) + "." + _encode(_signature(payload, secret=secret))


def verify_lesson_completion_proof(
    token: str | None, *, user_id: int, level: str,
    lesson_order: int, secret: str, now: int | None = None,
) -> bool:
    if not isinstance(token, str) or not (20 <= len(token) <= 512) or token.count(".") != 1:
        return False
    try:
        body, signature = token.split(".", 1)
        payload = _decode(body)
        mac = _decode(signature)
        if not hmac.compare_digest(mac, _signature(payload, secret=secret)):
            return False
        data = json.loads(payload)
        if not isinstance(data, list) or len(data) != 6:
            return False
        version, subject_id, subject_level, subject_lesson, started_at, nonce = data
        if type(version) is not int or version != PROOF_VERSION:
            return False
        if type(subject_id) is not int or subject_id != int(user_id):
            return False
        if not isinstance(subject_level, str) or subject_level != level:
            return False
        if type(subject_lesson) is not int or subject_lesson != int(lesson_order):
            return False
        if type(started_at) is not int or not isinstance(nonce, str) or len(nonce) != 24:
            return False
        current = int(time.time() if now is None else now)
        return -PROOF_FUTURE_SKEW_SECONDS <= current - started_at <= PROOF_TTL_SECONDS
    except (UnicodeError, ValueError, TypeError, OverflowError):
        return False
