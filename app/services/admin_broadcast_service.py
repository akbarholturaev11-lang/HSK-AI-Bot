"""Admin Mini App broadcast helper.

Telegram chatdagi `/broadcast` panelidagi segmentlash, AI tarjima va knopka
oqimini Mini App uchun qayta ishlatadi. TG handler (`admin_broadcast.py`)ga
tegmaydi — faqat o'sha logikani Mini App endpointlari uchun ulashadi.
"""

import asyncio

from app.repositories.user_repo import UserRepository
from app.services.bot_block_status_service import BotBlockStatusService
from app.bot.keyboards.promo_button import (
    build_promo_button_markup,
    decode_promo_button_config,
    normalize_promo_button_config,
)
from app.services.broadcast_translation_service import (
    BroadcastTranslationService,
    SUPPORTED_BROADCAST_LANGUAGES,
    encode_localized_broadcast_text,
    localized_broadcast_text_for_language,
    normalize_broadcast_languages,
)
from app.services.support_contact_service import get_admin_contact_url


# Mini App filtri TG panelidagi segmentlar bilan bir xil bo'lsin.
BROADCAST_FILTER_OPTIONS = {
    "status": ["free", "trial", "active", "expired", "blocked"],
    "level": ["beginner", "hsk1", "hsk2", "hsk3", "hsk4"],
    "mode": ["qa", "course"],
    "payment_status": ["none", "pending", "approved", "rejected"],
    "payment_method": ["visa", "alipay", "wechat"],
    "plan": ["10_days", "1_month"],
    "discount": ["eligible", "used", "none"],
    "course_promo": ["sent", "not_sent"],
    "activity": ["active_7d", "inactive_7d", "new_7d"],
}


def _clean(value, allowed: list[str]) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text if text in allowed else None


def parse_broadcast_filters(payload: dict) -> dict:
    """Mini App payloadidan xavfsiz filtr lug'atini quradi."""
    raw_langs = payload.get("languages") or []
    if isinstance(raw_langs, str):
        raw_langs = [raw_langs]
    languages = normalize_broadcast_languages(raw_langs)
    return {
        "languages": languages or None,
        "status": _clean(payload.get("status"), BROADCAST_FILTER_OPTIONS["status"]),
        "level": _clean(payload.get("level"), BROADCAST_FILTER_OPTIONS["level"]),
        "mode": _clean(payload.get("mode"), BROADCAST_FILTER_OPTIONS["mode"]),
        "payment_status": _clean(payload.get("payment_status"), BROADCAST_FILTER_OPTIONS["payment_status"]),
        "payment_method": _clean(payload.get("payment_method"), BROADCAST_FILTER_OPTIONS["payment_method"]),
        "plan": _clean(payload.get("plan"), BROADCAST_FILTER_OPTIONS["plan"]),
        "discount": _clean(payload.get("discount"), BROADCAST_FILTER_OPTIONS["discount"]),
        "course_promo": _clean(payload.get("course_promo"), BROADCAST_FILTER_OPTIONS["course_promo"]),
        "activity": _clean(payload.get("activity"), BROADCAST_FILTER_OPTIONS["activity"]),
    }


def parse_button_config(payload) -> dict | None:
    """Mini App knopka tanlovini promo_button config'iga aylantiradi."""
    if not isinstance(payload, dict):
        return None
    action = str(payload.get("action") or "").strip()
    if not action:
        return None
    return normalize_promo_button_config(
        action,
        text=payload.get("text"),
        url=payload.get("url"),
    )


class AdminBroadcastService:
    def __init__(self, bot, session):
        self.bot = bot
        self.session = session

    async def target_users(self, filters: dict) -> list:
        repo = UserRepository(self.session)
        return await repo.get_filtered_users(
            languages=filters.get("languages"),
            status=filters.get("status"),
            level=filters.get("level"),
            learning_mode=filters.get("mode"),
            payment_status=filters.get("payment_status"),
            payment_method=filters.get("payment_method"),
            selected_plan_type=filters.get("plan"),
            discount_filter=filters.get("discount"),
            course_promo_filter=filters.get("course_promo"),
            activity_filter=filters.get("activity"),
        )

    @staticmethod
    def deliverable_count(users, admin_ids: set[int]) -> int:
        return sum(
            1 for u in users
            if u.status != "blocked" and u.telegram_id not in admin_ids
        )

    @staticmethod
    def _actual_languages(users) -> list[str]:
        present = {
            (u.language if getattr(u, "language", None) in SUPPORTED_BROADCAST_LANGUAGES else "tj")
            for u in users
        }
        return [lang for lang in SUPPORTED_BROADCAST_LANGUAGES if lang in present]

    async def _encode_text(self, text: str, languages: list[str], content_type: str, translate: bool) -> str:
        if not text or not translate:
            return text
        max_length = 1024 if content_type in {"photo", "video"} else 4096
        target_languages = languages or list(SUPPORTED_BROADCAST_LANGUAGES)
        localized = await BroadcastTranslationService().translate_from_tajik(
            text, target_languages, max_length=max_length,
        )
        return encode_localized_broadcast_text(localized.texts)

    async def _send_one(self, chat_id, *, text, content_type, media_file_id, reply_markup):
        if content_type == "photo" and media_file_id:
            await self.bot.send_photo(chat_id, media_file_id, caption=text or None, reply_markup=reply_markup)
        elif content_type == "video" and media_file_id:
            await self.bot.send_video(chat_id, media_file_id, caption=text or None, reply_markup=reply_markup)
        else:
            await self.bot.send_message(chat_id, text, reply_markup=reply_markup)

    async def _contact_url(self, button_config) -> str | None:
        config = decode_promo_button_config(button_config) or {}
        if config.get("action") == "contact":
            return await get_admin_contact_url(self.session)
        return None

    async def send_test(
        self,
        admin_id: int,
        *,
        text: str,
        content_type: str,
        media_file_id: str | None,
        button_config: dict | None,
        translate: bool,
        languages: list[str] | None = None,
    ) -> None:
        langs = languages or list(SUPPORTED_BROADCAST_LANGUAGES)
        if not translate:
            langs = ["tj"]
        encoded = await self._encode_text(text, langs, content_type, translate)
        contact_url = await self._contact_url(button_config)
        for lang in langs:
            markup = await build_promo_button_markup(
                self.session, button_config, lang=lang,
                source="admin_miniapp_broadcast_test", contact_url=contact_url,
            )
            await self._send_one(
                admin_id,
                text=localized_broadcast_text_for_language(encoded, lang) if text else "",
                content_type=content_type,
                media_file_id=media_file_id,
                reply_markup=markup,
            )
            await asyncio.sleep(0.05)

    async def deliver(
        self,
        users: list,
        *,
        admin_ids: set[int],
        text: str,
        content_type: str,
        media_file_id: str | None,
        button_config: dict | None,
        translate: bool,
    ) -> tuple[int, int, int]:
        encoded = await self._encode_text(
            text, self._actual_languages(users), content_type, translate,
        )
        contact_url = await self._contact_url(button_config)
        block_service = BotBlockStatusService(self.session)
        sent = failed = blocked = 0
        for user in users:
            if user.status == "blocked" or user.telegram_id in admin_ids:
                continue
            try:
                markup = await build_promo_button_markup(
                    self.session, button_config, lang=user.language,
                    source="admin_miniapp_broadcast", contact_url=contact_url,
                )
                await self._send_one(
                    user.telegram_id,
                    text=localized_broadcast_text_for_language(encoded, user.language) if text else "",
                    content_type=content_type,
                    media_file_id=media_file_id,
                    reply_markup=markup,
                )
                sent += 1
                if BotBlockStatusService.is_bot_blocked(user):
                    await block_service.mark_user_unblocked(user)
            except Exception as exc:
                failed += 1
                try:
                    if await block_service.handle_send_exception(user.telegram_id, exc, reason="broadcast"):
                        blocked += 1
                except Exception:
                    pass
            await asyncio.sleep(0.03)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
        return sent, failed, blocked
