"""Subscription and limit notices: the Android app first, Telegram second.

A learner with the Android app installed (and notifications allowed there)
gets these notices on the phone. Telegram is the fallback, used when:

* the learner has no Android install that reported notifications as allowed,
  or runs a build that predates account notices;
* no phone accepted the FCM message;
* the phone answered that it cannot show the notice;
* the phone did not confirm showing it within ``ANDROID_CONFIRM_TIMEOUT``.

FCM accepting a message only means Google took it, so the phone has to confirm.
Until then the row stays ``android_pending`` and ``send_due_fallbacks`` (run by
the minute scheduler) sends the stored Telegram copy once the deadline passes.
A phone that reads the notice after that is told not to show it, so the
learner never gets the same notice twice.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import select

from app.config import settings
from app.db.models.account_notice_delivery import AccountNoticeDelivery
from app.db.models.android_push import AndroidPushToken
from app.db.models.desktop import DesktopDevice
from app.db.models.user import User
from app.services.android_push_service import AndroidPushService, AndroidPushTarget
from app.services.bot_block_status_service import BotBlockStatusService
from app.services.course_notification_service import (
    TITLE_BY_KEY,
    clean_notification_text,
    notification_title,
)


logger = logging.getLogger(__name__)

PUSH_KIND = "account_notice"
ANDROID_CONFIRM_TIMEOUT = timedelta(minutes=10)
# A phone that has started showing the notice gets this much longer before the
# Telegram copy goes out, so a slow post does not become two messages.
CLAIM_GRACE = timedelta(minutes=2)
FALLBACK_BATCH = 100
APP_TITLE = "HSK AI"

STATUS_PENDING = "android_pending"
STATUS_SHOWN = "android_shown"
STATUS_TELEGRAM = "telegram_sent"
STATUS_FAILED = "telegram_failed"

# What deliver() reports back to the caller.
OUTCOME_ANDROID = "android"
OUTCOME_TELEGRAM = "telegram"
OUTCOME_FAILED = "failed"
OUTCOME_SKIPPED = "skipped"
DELIVERED = frozenset({OUTCOME_ANDROID, OUTCOME_TELEGRAM})

ACTIONS = frozenset({"subscription", "course"})


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def phone_copy(key: str, lang: str, text: str) -> tuple[str, str]:
    """Title and body for the phone, from the Telegram text.

    Telegram notices open with a bold headline line; that becomes the title.
    A one-line notice keeps its text as the body under the feed title for its
    key, or under the app name when the key has no title of its own.
    """
    cleaned = clean_notification_text(text)
    first, _, rest = cleaned.partition("\n")
    rest = rest.strip()
    if rest:
        return first.strip()[:160], rest
    title = notification_title(key, lang) if key in TITLE_BY_KEY else APP_TITLE
    return title[:160], first.strip() or title


@dataclass(frozen=True)
class TelegramNotice:
    """The exact Telegram message, kept so it can be sent after a delay."""

    text: str
    reply_markup: InlineKeyboardMarkup | None = None
    parse_mode: str | None = None
    media_type: str | None = None
    media_file_id: str | None = None
    disable_web_page_preview: bool | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "reply_markup": (
                self.reply_markup.model_dump(mode="json", exclude_none=True)
                if self.reply_markup is not None
                else None
            ),
            "parse_mode": self.parse_mode,
            "media_type": self.media_type,
            "media_file_id": self.media_file_id,
            "disable_web_page_preview": self.disable_web_page_preview,
        }

    @classmethod
    def from_payload(cls, payload: Any) -> "TelegramNotice":
        data = payload if isinstance(payload, dict) else {}
        markup = data.get("reply_markup")
        return cls(
            text=str(data.get("text") or ""),
            reply_markup=InlineKeyboardMarkup.model_validate(markup) if markup else None,
            parse_mode=data.get("parse_mode"),
            media_type=data.get("media_type"),
            media_file_id=data.get("media_file_id"),
            disable_web_page_preview=data.get("disable_web_page_preview"),
        )

    async def send(self, bot, chat_id: int) -> None:
        # Only the arguments the original call used are passed, so a delayed
        # copy is the same Telegram request as an immediate one.
        options: dict[str, Any] = {}
        if self.reply_markup is not None:
            options["reply_markup"] = self.reply_markup
        if self.parse_mode:
            options["parse_mode"] = self.parse_mode
        if self.media_type == "photo" and self.media_file_id:
            await bot.send_photo(
                chat_id=chat_id, photo=self.media_file_id, caption=self.text, **options
            )
            return
        if self.media_type == "video" and self.media_file_id:
            await bot.send_video(
                chat_id=chat_id, video=self.media_file_id, caption=self.text, **options
            )
            return
        if self.disable_web_page_preview is not None:
            options["disable_web_page_preview"] = self.disable_web_page_preview
        await bot.send_message(chat_id=chat_id, text=self.text, **options)


class NotificationDeliveryService:
    def __init__(self, session, settings_obj=settings):
        self.session = session
        self.settings = settings_obj
        self.push = AndroidPushService(session, settings_obj)

    @property
    def android_enabled(self) -> bool:
        return bool(getattr(self.settings, "ANDROID_PUSH_NOTICES_ENABLED", False)) and (
            self.push.configured
        )

    async def _android_targets(self, telegram_id: int) -> list[tuple[str, str]]:
        if not self.android_enabled:
            return []
        rows = (
            await self.session.execute(
                select(AndroidPushToken.token, AndroidPushToken.device_id)
                .join(DesktopDevice, AndroidPushToken.device_id == DesktopDevice.id)
                .where(
                    DesktopDevice.telegram_id == int(telegram_id),
                    DesktopDevice.platform == "android",
                    DesktopDevice.revoked_at.is_(None),
                    AndroidPushToken.notifications_allowed.is_(True),
                )
            )
        ).all()
        return [(str(token), str(device_id)) for token, device_id in rows]

    async def reachable(self, user) -> bool:
        """Whether any channel can carry a notice to this learner now.

        A learner who blocked the bot is still reachable through the app.
        """
        if not BotBlockStatusService.is_bot_blocked(user):
            return True
        return bool(await self._android_targets(int(user.telegram_id)))

    async def deliver(
        self,
        bot,
        user,
        *,
        key: str,
        lang: str,
        telegram: TelegramNotice,
        reason: str,
        title: str | None = None,
        body: str | None = None,
        action: str = "subscription",
    ) -> str:
        """Send one notice; returns android, telegram, failed or skipped.

        ``android`` means a phone accepted it and Telegram waits for the
        phone's confirmation; the caller should treat it as delivered.
        """
        telegram_id = int(user.telegram_id)
        targets = await self._android_targets(telegram_id)
        if not targets:
            return await self._send_telegram(bot, user, telegram, reason=reason)

        lang = lang if lang in ("uz", "ru", "tj") else "ru"
        phone_title, phone_body = phone_copy(key, lang, telegram.text)
        now = datetime.now(timezone.utc)
        row = AccountNoticeDelivery(
            user_id=getattr(user, "id", None),
            telegram_id=telegram_id,
            key=str(key)[:64],
            language=lang,
            title=clean_notification_text(title, 160) if title else phone_title,
            body=clean_notification_text(body) if body else phone_body,
            action=action if action in ACTIONS else "subscription",
            status=STATUS_PENDING,
            android_targets=len(targets),
            android_blocked=0,
            telegram_payload=telegram.to_payload(),
            reason=str(reason or "account_notice")[:40],
            created_at=now,
            fallback_due_at=now + ANDROID_CONFIRM_TIMEOUT,
        )
        self.session.add(row)
        # The phone reads the notice back as soon as the push lands, which can
        # be before the caller finishes its loop, so the row is committed now.
        await self.session.commit()

        results = await self.push.send_batch(
            [
                AndroidPushTarget(
                    token=token,
                    device_id=device_id,
                    data={"kind": PUSH_KIND, "notice_id": row.id, "device_id": device_id},
                )
                for token, device_id in targets
            ],
            ttl_seconds=int(ANDROID_CONFIRM_TIMEOUT.total_seconds()),
        )
        accepted = sum(1 for result in results if result.accepted)
        if accepted:
            row.android_targets = accepted
            return OUTCOME_ANDROID
        # No phone took it, so waiting would only delay the Telegram copy.
        return await self._fall_back(bot, row, user=user)

    async def _send_telegram(self, bot, user, notice: TelegramNotice, *, reason: str) -> str:
        if bot is None or BotBlockStatusService.is_bot_blocked(user):
            return OUTCOME_SKIPPED
        blocks = BotBlockStatusService(self.session)
        try:
            await notice.send(bot, int(user.telegram_id))
        except Exception as exc:  # noqa: BLE001 - a failed chat must not stop the batch
            await blocks.handle_send_exception(int(user.telegram_id), exc, reason=reason)
            return OUTCOME_FAILED
        await blocks.handle_send_success(user, reason=reason)
        return OUTCOME_TELEGRAM

    async def _fall_back(self, bot, row: AccountNoticeDelivery, *, user=None) -> str:
        if user is None:
            user = (
                await self.session.execute(
                    select(User).where(User.telegram_id == int(row.telegram_id))
                )
            ).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        row.fallback_due_at = None
        if user is None:
            row.status = STATUS_FAILED
            return OUTCOME_FAILED
        outcome = await self._send_telegram(
            bot, user, TelegramNotice.from_payload(row.telegram_payload), reason=row.reason
        )
        if outcome == OUTCOME_TELEGRAM:
            row.status = STATUS_TELEGRAM
            row.telegram_sent_at = now
        else:
            row.status = STATUS_FAILED
        return outcome

    async def send_due_fallbacks(self, bot, *, now: datetime | None = None) -> int:
        """Telegram copies for notices no phone confirmed in time."""
        now = now or datetime.now(timezone.utc)
        rows = (
            await self.session.execute(
                select(AccountNoticeDelivery)
                .where(
                    AccountNoticeDelivery.status == STATUS_PENDING,
                    AccountNoticeDelivery.fallback_due_at <= now,
                )
                .order_by(AccountNoticeDelivery.fallback_due_at, AccountNoticeDelivery.id)
                .limit(FALLBACK_BATCH)
            )
        ).scalars().all()
        sent = 0
        for row in rows:
            if await self._fall_back(bot, row) == OUTCOME_TELEGRAM:
                sent += 1
        if rows:
            await self.session.commit()
        return sent

    async def _owned(self, notice_id: int, telegram_id: int) -> AccountNoticeDelivery | None:
        row = await self.session.get(AccountNoticeDelivery, int(notice_id))
        if row is None or int(row.telegram_id) != int(telegram_id):
            return None
        return row

    async def claim(self, notice_id: int, *, telegram_id: int) -> dict[str, Any] | None:
        """The notice for the phone to show, or ``show: False`` if too late.

        None means the notice does not exist for this account.
        """
        row = await self._owned(notice_id, telegram_id)
        if row is None:
            return None
        show = row.status in (STATUS_PENDING, STATUS_SHOWN)
        if row.status == STATUS_PENDING:
            now = datetime.now(timezone.utc)
            due = _as_utc(row.fallback_due_at)
            # A phone that is already showing it holds Telegram back a little.
            if due is not None and due < now + CLAIM_GRACE:
                row.fallback_due_at = now + CLAIM_GRACE
            await self.session.commit()
        payload: dict[str, Any] = {"id": int(row.id), "show": show}
        if show:
            payload.update(
                {
                    "key": row.key,
                    "title": row.title,
                    "body": row.body,
                    "action": row.action if row.action in ACTIONS else "subscription",
                }
            )
        return payload

    async def acknowledge(
        self,
        notice_id: int,
        *,
        telegram_id: int,
        device_id: str,
        shown: bool,
    ) -> bool:
        row = await self._owned(notice_id, telegram_id)
        if row is None:
            return False
        now = datetime.now(timezone.utc)
        if shown:
            if row.status in (STATUS_PENDING, STATUS_SHOWN):
                row.status = STATUS_SHOWN
                row.fallback_due_at = None
                row.android_shown_at = row.android_shown_at or now
        else:
            # This phone cannot show notices; later ones go straight to Telegram.
            token = await self.session.get(AndroidPushToken, str(device_id))
            if token is not None:
                token.notifications_allowed = False
                token.updated_at = now
            if row.status == STATUS_PENDING:
                row.android_blocked = int(row.android_blocked or 0) + 1
                if row.android_blocked >= int(row.android_targets or 1):
                    # Every phone said no: the next scheduler tick sends Telegram.
                    row.fallback_due_at = now
        await self.session.commit()
        return True
