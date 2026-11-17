"""Presentation only: adapt existing Telegram/inbox copy for iOS Web Push.

No delivery decisions, private payment details or text persistence live here.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

from app.bot.utils.i18n import t
from app.services.notification_i18n import notification_message
from app.services.notification_template_service import NotificationTemplateService


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"br", "p", "div", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"p", "div", "li"}:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value: str) -> str:
    parser = _PlainText()
    parser.feed(str(value or ""))
    # iOS already displays the installed app name above the notification.
    text = re.sub(r"\bHSK\s+AI\b(?:['’](?:ni|ning)|-ро)?", "", "".join(parser.parts), flags=re.I)
    lines = [re.sub(r"[\t\r\f\v \u00a0]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


def push_copy(text: str, *, title: str, body: str) -> tuple[str, str]:
    """Use the Telegram headline once, followed by its full plain-text meaning."""
    cleaned = plain_text(text)
    first, _, rest = cleaned.partition("\n")
    if rest.strip():
        title, body = first, rest.strip()
    elif first:
        title, body = plain_text(title), first
    else:
        title, body = plain_text(title), plain_text(body)
    return _bounded_copy(title, body)


def _bounded_copy(title: str, body: str) -> tuple[str, str]:
    # Keep UTF-8 + JSON + Web Push encryption overhead below Apple's 4 KiB
    # payload limit, even for emoji-heavy admin-authored templates.
    if len(body.encode("utf-8")) > 2400:
        body = body.encode("utf-8")[:2397].decode("utf-8", errors="ignore").rstrip() + "…"
    return _clip(title, 80), _clip(body, 1000)


# These are presentation fallbacks for old rows without render arguments, never
# a claim that an unrecorded amount, rank, deadline or lesson is known.
def fallback_copy(key: str, language: str) -> tuple[str, str]:
    title = notification_message("pwa.push." + key + ".title", language)
    body = notification_message("pwa.push." + key + ".body", language)
    if not title:
        title = notification_message("course.title." + key, language)
    if not title or not body:
        title = notification_message("pwa.push.courseUpdate.title", language)
        body = notification_message("pwa.push.courseUpdate.body", language)
    return title, body


async def course_push_copy(session, row, language: str) -> tuple[str, str]:
    title, body = fallback_copy(row.key, language)
    params = row.params if isinstance(row.params, dict) else {}
    text = ""
    if params.get("template_service"):
        resolved = await NotificationTemplateService(session).resolve(params["template_service"], language)
        if resolved:
            try:
                fields = {
                    k: v for k, v in params.items()
                    if k != "template_service" and not k.startswith("_")
                }
                if (row.language != language and row.key in {"lesson_unfinished", "d1_lesson_recovery"}
                        and getattr(row, "level", None) and getattr(row, "lesson_order", None)):
                    fields["lesson"] = notification_message("reminder.lessonLabel", language,
                        level=row.level.upper(), lesson=row.lesson_order)
                text = resolved["text"].format(**fields)
            except (KeyError, IndexError, ValueError):
                pass
    elif params.get("template"):
        text = t(params["template"], language, **{k: v for k, v in params.items() if k != "template"})
        if isinstance(params.get("limit_context"), dict):
            from app.services.entitlements.decision import limit_text
            text = limit_text(**params["limit_context"], language=language) + "\n\n" + text
    # Legacy trial rows did not retain params (the inbox writer discarded them).
    elif row.key == "trial_expiring" and row.source == "trial_reminder":
        slot = str(row.dedupe_key or "").rsplit(":", 1)[-1]
        if slot in {"0", "2"}:
            text = t("trial_expiring_soon", language, days=2) if slot == "2" else t("trial_expired_notice", language)
    if not text and row.language == language:
        title = plain_text(row.title) or title
        text = row.body
    if re.search(r"\{[A-Za-z_][^{}]*\}", text):
        text = ""
    return push_copy(text, title=title, body=body)


def account_push_copy(row, language: str) -> tuple[str, str]:
    key = row.key
    reason = str(row.reason or "")
    if reason.startswith(("android_fix_", "android_update_")):
        from app.services.admin_feedback_resolution import fixed_notice_copy
        return fixed_notice_copy(language, "app_update" if reason.startswith("android_update_") else "server")
    title, body = fallback_copy(key, language)
    if not notification_message("pwa.push." + key + ".title", language):
        title, body = fallback_copy("accountUpdate", language)
    if key == "pwa_account_restriction":
        return title, body
    if key in {"daily_limit_renewed", "subscription_expiring"}:
        template = "subscription_expires_tomorrow" if key == "subscription_expiring" else key
        return push_copy(t(template, language), title=title, body=body)
    if key == "trial_expiring":
        payload = row.telegram_payload if isinstance(row.telegram_payload, dict) else {}
        original = plain_text(payload.get("text") or row.body)
        for template, fields in (("trial_expiring_soon", {"days": 2}), ("trial_expired_notice", {})):
            if original == plain_text(t(template, row.language, **fields)):
                return push_copy(t(template, language, **fields), title=title, body=body)
    if row.language == language:
        # The stored phone body respects campaign copy and omits Telegram-only
        # navigation instructions. It can include the headline; split it once.
        text = row.body
        payload = row.telegram_payload if isinstance(row.telegram_payload, dict) else {}
        telegram_title = plain_text(payload.get("text", "")).partition("\n")[0]
        title = plain_text(row.title)
        if not title:
            title = telegram_title or fallback_copy(key, language)[0]
        text = plain_text(text)
        if text.startswith(title + "\n"):
            text = text[len(title):].lstrip()
        return _bounded_copy(title, text or body)
    # Dynamic campaigns/old rows have no translation arguments. Do not send
    # stale foreign-language text or invent a translation of user/admin copy.
    return title, body


def payment_push_copy(payment, language: str) -> tuple[str, str]:
    from app.services.payment_notify_service import HSK30_UNLOCK_APPROVED_TEXT, HSK30_UNLOCK_REJECTED_TEXT
    approved = payment.payment_status == "approved"
    if payment.plan_type == "hsk30_unlock":
        text = (HSK30_UNLOCK_APPROVED_TEXT if approved else HSK30_UNLOCK_REJECTED_TEXT)[language]
    else:
        text = t("user_payment_approved" if approved else "user_payment_rejected", language)
    key = "paymentApproved" if approved else "paymentRejected"
    return push_copy(text,
        title=notification_message("pwa.push." + key + "Title", language),
        body=notification_message("pwa.push." + key + "Body", language))
