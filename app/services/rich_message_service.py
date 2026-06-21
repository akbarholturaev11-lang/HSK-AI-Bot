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
            # Rich Message payload tayyorlash
            payload = {
                "chat_id": chat_id,
                **rich_payload
            }
            if reply_markup:
                # aiogram reply_markup obyektini JSON ga o'tkazish
                if hasattr(reply_markup, "model_dump_json"):
                    payload["reply_markup"] = reply_markup.model_dump_json(exclude_none=True)
                else:
                    # Eskiroq aiogram versiyalari uchun
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

        # Fallback: Agar Rich Message fail bo'lsa yoki xatolik bo'lsa
        try:
            await bot.send_message(chat_id, fallback_text, reply_markup=reply_markup, parse_mode="HTML")
            logger.info(f"rich_fallback_sent chat_id={chat_id}")
        except Exception as e:
            logger.error(f"final_fallback_failed chat_id={chat_id} error={str(e)}")
        
        return False

    def build_vocab_rich_message(self, word: str, pinyin: str, translation: str, examples: list, mistakes: Optional[str] = None) -> Dict[str, Any]:
        """Vocabulary Rich Message payloadini yaratadi."""
        # Bu yerda Rich Message formati (masalan, Telegram'ning yangi xususiyatlari) bo'ladi
        # Hozircha bu placeholder, chunki Rich Message spetsifikatsiyasi loyihaga qarab o'zgarishi mumkin.
        # Biz uni HTML orqali simulyatsiya qilamiz yoki agar maxsus API bo'lsa shuni ishlatamiz.
        text = (
            f"<b>{escape(word)}</b>\n"
            f"<i>{escape(pinyin)}</i>\n"
            f"👉 {escape(translation)}\n\n"
        )
        if examples:
            text += "<b>Misollar:</b>\n"
            for ex in examples:
                text += f"• {escape(ex)}\n"
        
        if mistakes:
            text += f"\n⚠️ <b>Xatolar:</b> {escape(mistakes)}"

        return {
            "text": text,
            "parse_mode": "HTML"
        }

    def build_grammar_rich_message(self, title: str, formula: str, explanation: str, examples: list, common_mistakes: Optional[str] = None) -> Dict[str, Any]:
        """Grammar Rich Message payloadini yaratadi."""
        text = (
            f"📐 <b>{escape(title)}</b>\n"
            f"<code>{escape(formula)}</code>\n\n"
            f"{escape(explanation)}\n\n"
        )
        if examples:
            text += "<b>Misollar:</b>\n"
            for ex in examples:
                text += f"• {escape(ex)}\n"
        
        if common_mistakes:
            text += f"\n❌ <b>Ko'p uchraydigan xatolar:</b>\n{escape(common_mistakes)}"

        return {
            "text": text,
            "parse_mode": "HTML"
        }

    def build_quiz_result_rich_message(self, score: int, total: int, weak_points: list, wrong_answers: list) -> Dict[str, Any]:
        """Quiz Result Rich Message payloadini yaratadi."""
        status = "✅ Zo'r!" if score / total >= 0.8 else "📈 Yana ozgina harakat qiling"
        text = (
            f"📊 <b>Quiz natijasi</b>\n\n"
            f"Natija: <b>{score}/{total}</b>\n"
            f"Status: {status}\n\n"
        )
        if weak_points:
            text += "🔍 <b>Kuchsiz tomonlar:</b>\n"
            for pt in weak_points:
                text += f"• {escape(pt)}\n"
        
        if wrong_answers:
            text += f"\n❌ <b>Xato javoblar soni:</b> {len(wrong_answers)}"

        return {
            "text": text,
            "parse_mode": "HTML"
        }

    def build_news_rich_message(self, title: str, body: str, changelog: list, cta_text: str) -> Dict[str, Any]:
        """News Rich Message payloadini yaratadi."""
        text = (
            f"📢 <b>{escape(title)}</b>\n\n"
            f"{escape(body)}\n\n"
        )
        if changelog:
            text += "<b>Yangiliklar:</b>\n"
            for item in changelog:
                text += f"• {escape(item)}\n"
        
        if cta_text:
            text += f"\n✨ {escape(cta_text)}"

        return {
            "text": text,
            "parse_mode": "HTML"
        }
