from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BOT_TOKEN: str = ""
    OPENAI_API_KEY: str = ""

    # Gemini (asosiy AI provayder). GEMINI_API_KEY bo'lsa Gemini ishlaydi,
    # bo'lmasa yoki xato bersa OpenAI zaxira sifatida ishga tushadi.
    GEMINI_API_KEY: str = ""
    # Admin panel model tanlamagan bo'lsa ishlatiladigan standart Gemini modeli.
    GEMINI_MODEL: str = "gemini-2.5-flash"
    # Gemini'ning OpenAI-mos endpointi (matn/vision/JSON shu orqali ketadi).
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    # Gemini osilib qolsa OpenAI'ga tez o'tish uchun so'rov timeouti (soniya).
    AI_PRIMARY_TIMEOUT_SECONDS: float = 30.0

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_chinese_bot"
    REDIS_URL: str = "redis://localhost:6379/0"

    ADMIN_IDS: str = "7965751363"
    FEEDBACK_NOTIFY_CHAT_IDS: str = "-1004311413349"
    PAYMENT_DETAILS: str = ""
    BOT_USERNAME: str = ""
    MINI_APP_BASE_URL: str = "https://telegram-chinese-bot-production.up.railway.app/course-v3.html"

    DEFAULT_LANGUAGE: str = "tj"
    LOG_LEVEL: str = "INFO"
    ENABLE_RICH_MESSAGES: bool = True

    AIRTABLE_API_KEY: str = ""
    AIRTABLE_BASE_ID: str = ""
    AIRTABLE_USERS_TABLE: str = "Users"
    AIRTABLE_PAYMENTS_TABLE: str = "Payments"
    AIRTABLE_REFERRALS_TABLE: str = "Referrals"
    AIRTABLE_CHAT_SUMMARY_TABLE: str = "ChatSummary"
    AIRTABLE_CHAT_ARCHIVE_TABLE: str = "ChatArchive"    

    @property
    def admin_id_list(self) -> List[int]:
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]

    @property
    def feedback_notify_chat_id_list(self) -> List[int]:
        return [int(x.strip()) for x in self.FEEDBACK_NOTIFY_CHAT_IDS.split(",") if x.strip()]

    @property
    def ai_enabled(self) -> bool:
        """Kamida bitta AI provayder (Gemini yoki OpenAI) sozlangan bo'lsa True."""
        return bool(self.GEMINI_API_KEY or self.OPENAI_API_KEY)


settings = Settings()
COURSE_MODE_ENABLED = True
# ENABLE_RICH_MESSAGES = True  # Moved to Settings class
