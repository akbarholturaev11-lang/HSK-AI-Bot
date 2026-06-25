import logging
import json
import httpx
from html import escape
from typing import Optional, Dict, Any
from aiogram import Bot
from app.config import settings

logger = logging.getLogger(__name__)

class RichMessageService:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    @staticmethod
    def is_rich_messages_enabled() -> bool:
        return settings.ENABLE_RICH_MESSAGES

    async def send_rich_or_fallback(
        self, 
        bot: Bot, 
        chat_id: int, 
        rich_payload: Dict[str, Any], 
        fallback_text: str, 
        reply_markup: Optional[Any] = None
    ) -> bool:
        """
        Rich Message yuborishga harakat qiladi, xatolik bo'lsa fallback xabar yuboradi.
        """
        if not self.is_rich_messages_enabled():
            await bot.send_message(chat_id, fallback_text, reply_markup=reply_markup, parse_mode="HTML")
            logger.info(f"rich_disabled_fallback_used chat_id={chat_id}")
            return False

        try:
            payload = {
                "chat_id": chat_id,
                **rich_payload
            }
            if reply_markup:
                if hasattr(reply_markup, "model_dump_json"):
                    payload["reply_markup"] = reply_markup.model_dump_json(exclude_none=True)
                else:
                    payload["reply_markup"] = reply_markup.json()

            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, timeout=10.0)
                result = response.json()
                
                if response.status_code == 200 and result.get("ok"):
                    logger.info(f"rich_message_sent chat_id={chat_id}")
                    return True
                else:
                    logger.error(f"rich_message_failed chat_id={chat_id} error={result.get('description')}")
        except Exception as e:
            logger.exception(f"rich_template_build_failed chat_id={chat_id} error={str(e)}")

        # Fallback
        try:
            await bot.send_message(chat_id, fallback_text, reply_markup=reply_markup, parse_mode="HTML")
            logger.info(f"rich_fallback_sent chat_id={chat_id}")
        except Exception as e:
            logger.error(f"final_fallback_failed chat_id={chat_id} error={str(e)}")
        
        return False

    def build_vocab_rich_message(self, word: str, pinyin: str, translation: str, examples: list, mistakes: Optional[str] = None) -> Dict[str, Any]:
        """Vocabulary Rich Message — expandable blockquote bilan."""
        examples_text = ""
        if examples:
            examples_text = "\n".join([f"• {escape(ex)}" for ex in examples])

        mistakes_text = ""
        if mistakes:
            mistakes_text = f"\n\n⚠️ <b>Eslatma:</b>\n{escape(mistakes)}"

        text = (
            f"<b>📖 Vocabulary</b>\n\n"
            f"<blockquote expandable>"
            f"<b>{escape(word)}</b>  •  <i>{escape(pinyin)}</i>\n"
            f"👉 {escape(translation)}\n\n"
            f"<b>Misollar:</b>\n"
            f"{examples_text}"
            f"{mistakes_text}"
            f"</blockquote>"
        )

        return {
            "text": text,
            "parse_mode": "HTML"
        }

    def build_grammar_rich_message(self, title: str, formula: str, explanation: str, examples: list, common_mistakes: Optional[str] = None) -> Dict[str, Any]:
        """Grammar Rich Message — expandable blockquote bilan."""
        examples_text = ""
        if examples:
            examples_text = "\n".join([f"• {escape(ex)}" for ex in examples])

        mistakes_text = ""
        if common_mistakes:
            mistakes_text = f"\n\n❌ <b>Xatolar:</b>\n{escape(common_mistakes)}"

        text = (
            f"<b>📐 Grammar</b>\n\n"
            f"<blockquote expandable>"
            f"📌 <b>{escape(title)}</b>\n"
            f"<code>{escape(formula)}</code>\n\n"
            f"{escape(explanation)}\n\n"
            f"<b>Misollar:</b>\n"
            f"{examples_text}"
            f"{mistakes_text}"
            f"</blockquote>"
        )

        return {
            "text": text,
            "parse_mode": "HTML"
        }

    def build_quiz_result_rich_message(self, score: int, total: int, weak_points: list, wrong_answers: list) -> Dict[str, Any]:
        """Quiz Result Rich Message — expandable blockquote bilan."""
        status = "✅ Zo'r!" if score / total >= 0.8 else "📈 Yana ozgina harakat qiling"

        points_text = ""
        if weak_points:
            points_text = "\n".join([f"• {escape(pt)}" for pt in weak_points])

        text = (
            f"<b>📊 Quiz natijasi</b>\n\n"
            f"<blockquote expandable>"
            f"Natija: <b>{score}/{total}</b>\n"
            f"Holat: {status}\n\n"
            f"🔍 <b>Kuchsiz tomonlar:</b>\n"
            f"{points_text}\n\n"
            f"❌ <b>Xato javoblar:</b> {len(wrong_answers)}"
            f"</blockquote>"
        )

        return {
            "text": text,
            "parse_mode": "HTML"
        }

    def build_news_rich_message(self, title: str, body: str, changelog: list, cta_text: str) -> Dict[str, Any]:
        """News Rich Message — expandable blockquote bilan."""
        changelog_text = ""
        if changelog:
            changelog_text = "\n".join([f"• {escape(item)}" for item in changelog])

        text = (
            f"<b>📢 {escape(title)}</b>\n\n"
            f"<blockquote expandable>"
            f"{escape(body)}\n\n"
            f"<b>Yangiliklar:</b>\n"
            f"{changelog_text}"
            f"</blockquote>"
        )
        if cta_text:
            text += f"\n\n✨ <b>{escape(cta_text)}</b>"

        return {
            "text": text,
            "parse_mode": "HTML"
        }
