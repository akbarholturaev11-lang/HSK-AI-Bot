"""Trusted Telegram Bot approval adapter and browser-bound status projection.

No Bot HTTP endpoint, session issuer, account link or PWA data endpoint here.
The event MUST be an aiogram Message/CallbackQuery supplied by the verified
Bot dispatcher, never constructed from anonymous JSON or browser parameters.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from app.admin_api.pwa_approval import (
    _PROOF, _allowed, _utc, approve_pwa_approval,
)
from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.desktop_auth_service import DesktopAuthService

_REQUEST_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@dataclass(frozen=True)
class BotPwaApprovalPreview:
    request_id: str
    pairing_code: str
    expires_at: datetime


@dataclass(frozen=True)
class BrowserPwaApprovalStatus:
    status: str
    pairing_code: str
    expires_at: datetime


def _enabled(settings_obj: Any) -> bool:
    return bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False))


def _pairing_code(settings_obj: Any, request_id: str) -> str:
    # Comparison-only 8-character code; NOT a login credential.
    secret = DesktopAuthService(None, settings_obj)._signing_secret()
    return hmac.new(
        secret, ("admin-pwa-pairing:" + request_id).encode("ascii"), hashlib.sha256,
    ).hexdigest()[:8].upper()


def _private_admin_from_bot_event(event: Any, settings_obj: Any) -> int | None:
    """Accept authenticated aiogram dispatcher context, never client-supplied ID.

    The caller must not expose this API as a web route or deserialize event
    objects from untrusted input. Channel/group/forwarded callback is denied.
    """
    if not _enabled(settings_obj):
        return None
    actor = getattr(event, "from_user", None)
    message = getattr(event, "message", None) or event
    chat = getattr(message, "chat", None)
    if not actor or not chat:
        return None
    if getattr(actor, "is_bot", False) or str(getattr(chat, "type", "")) != "private":
        return None
    try:
        telegram_id = int(actor.id)
        if int(chat.id) != telegram_id or not _allowed(telegram_id, settings_obj):
            return None
        return telegram_id
    except (TypeError, ValueError, OverflowError, AttributeError):
        return None


async def _pending_for_admin(db: Any, *, request_id: str, telegram_id: int,
                             now: datetime) -> AdminPwaApproval | None:
    user = (await db.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
    if user is None or str(user.status).strip().lower() == "blocked":
        return None
    row = (await db.execute(select(AdminPwaApproval).where(
        AdminPwaApproval.id == request_id,
    ))).scalar_one_or_none()
    if row is None or row.status != "pending" or _utc(row.expires_at) <= now:
        return None
    # Preview must never encourage approval when this Google subject already
    # belongs to another canonical account.
    existing = (await db.execute(select(UserIdentity.user_id).where(
        UserIdentity.provider == "google",
        UserIdentity.subject_hash == row.google_subject_hash,
    ))).scalar_one_or_none()
    if existing is not None and int(existing) != int(user.id):
        return None
    return row


async def preview_admin_pwa_bot_request(db: Any, *, bot_event: Any,
                                        request_id: str, settings_obj: Any,
                                        now: datetime | None = None) -> BotPwaApprovalPreview | None:
    telegram_id = _private_admin_from_bot_event(bot_event, settings_obj)
    if telegram_id is None or not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
        return None
    timestamp = _utc(now or datetime.now(timezone.utc))
    row = await _pending_for_admin(db, request_id=request_id, telegram_id=telegram_id, now=timestamp)
    if row is None:
        return None
    return BotPwaApprovalPreview(row.id, _pairing_code(settings_obj, row.id), _utc(row.expires_at))


async def decide_admin_pwa_bot_request(db: Any, *, bot_event: Any,
                                       request_id: str, approve: bool,
                                       settings_obj: Any,
                                       now: datetime | None = None) -> bool:
    """Consume one pending Bot decision; denied requests cannot be revived."""
    telegram_id = _private_admin_from_bot_event(bot_event, settings_obj)
    if (telegram_id is None or not isinstance(approve, bool)
            or not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id)):
        return False
    timestamp = _utc(now or datetime.now(timezone.utc))
    if await _pending_for_admin(db, request_id=request_id, telegram_id=telegram_id, now=timestamp) is None:
        return False
    if approve:
        return await approve_pwa_approval(
            db, request_id=request_id, verified_bot_telegram_id=telegram_id,
            settings_obj=settings_obj, now=timestamp,
        )
    result = await db.execute(update(AdminPwaApproval).where(
        AdminPwaApproval.id == request_id,
        AdminPwaApproval.status == "pending",
        AdminPwaApproval.expires_at > timestamp,
    ).values(status="denied").execution_options(synchronize_session=False))
    await db.commit()
    return result.rowcount == 1


async def read_browser_pwa_approval(db: Any, *, request_id: str,
                                    browser_proof: str, settings_obj: Any,
                                    now: datetime | None = None) -> BrowserPwaApprovalStatus | None:
    """Read-only response for an HttpOnly-cookie-authenticated browser.

    Returns neither canonical admin ID nor Google subject or raw browser proof.
    """
    if (not _enabled(settings_obj) or not isinstance(request_id, str)
            or not _REQUEST_ID.fullmatch(request_id)
            or not isinstance(browser_proof, str) or not _PROOF.fullmatch(browser_proof)):
        return None
    timestamp = _utc(now or datetime.now(timezone.utc))
    row = (await db.execute(select(AdminPwaApproval).where(
        AdminPwaApproval.id == request_id,
    ))).scalar_one_or_none()
    if row is None or _utc(row.expires_at) <= timestamp:
        return None
    digest = hashlib.sha256(browser_proof.encode("ascii")).hexdigest()
    if not hmac.compare_digest(row.browser_proof_hash, digest):
        return None
    if row.status not in ("pending", "approved", "denied"):
        return None
    return BrowserPwaApprovalStatus(
        row.status, _pairing_code(settings_obj, row.id), _utc(row.expires_at),
    )
