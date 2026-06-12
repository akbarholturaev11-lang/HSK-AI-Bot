from __future__ import annotations

import re

from app.repositories.bot_setting_repo import BotSettingRepository


ADMIN_CONTACT_KEY = "admin_contact"
DEFAULT_ADMIN_CONTACT = "@akbarchina"


def normalize_admin_contact(value: str | None) -> str:
    contact = (value or "").strip()
    return contact or DEFAULT_ADMIN_CONTACT


def admin_contact_url(value: str | None) -> str:
    contact = normalize_admin_contact(value)
    lowered = contact.lower()

    if lowered.startswith(("https://", "http://", "tg://")):
        return contact
    if lowered.startswith("t.me/"):
        return f"https://{contact}"

    username = contact[1:] if contact.startswith("@") else contact
    if re.fullmatch(r"[A-Za-z0-9_]{5,32}", username):
        return f"https://t.me/{username}"

    return ""


async def get_admin_contact(session) -> str:
    stored = await BotSettingRepository(session).get(ADMIN_CONTACT_KEY)
    return normalize_admin_contact(stored)


async def get_admin_contact_url(session) -> str:
    return admin_contact_url(await get_admin_contact(session))
