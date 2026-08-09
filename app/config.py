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

    # Desktop release controls. Downloads remain hidden unless the flag is on
    # and at least one real, clean-machine-tested HTTPS artifact URL is set.
    DESKTOP_DOWNLOADS_ENABLED: bool = False
    DESKTOP_DOWNLOAD_BASE_URL: str = ""
    DESKTOP_MAC_DOWNLOAD_URL: str = ""
    DESKTOP_WINDOWS_DOWNLOAD_URL: str = ""
    DESKTOP_MAC_VERSION: str = ""
    DESKTOP_WINDOWS_VERSION: str = ""
    # Stable R2 latest.json URL. When set, one validated manifest supplies all
    # installer/updater URLs, signatures, versions and notes automatically.
    DESKTOP_RELEASE_MANIFEST_URL: str = ""
    DESKTOP_RELEASE_MANIFEST_CACHE_TTL_SECONDS: int = 60
    DESKTOP_RELEASE_MANIFEST_TIMEOUT_SECONDS: float = 5.0
    DESKTOP_RELEASE_MANIFEST_MAX_BYTES: int = 65536
    # Tauri updater metadata is public but remains disabled until signed release
    # archives and their detached signatures are published.
    DESKTOP_UPDATES_ENABLED: bool = False
    DESKTOP_MAC_UPDATER_URL: str = ""
    DESKTOP_MAC_UPDATER_SIGNATURE: str = ""
    DESKTOP_MAC_UPDATER_NOTES: str = ""
    DESKTOP_WINDOWS_UPDATER_URL: str = ""
    DESKTOP_WINDOWS_UPDATER_SIGNATURE: str = ""
    DESKTOP_WINDOWS_UPDATER_NOTES: str = ""
    DESKTOP_DOWNLOAD_RATE_LIMIT_COUNT: int = 3
    DESKTOP_DOWNLOAD_RATE_LIMIT_WINDOW_SECONDS: int = 900
    # Opaque request tokens only attribute the installer funnel. They remain
    # reusable for normal browser retries, but stop resolving after this TTL.
    DESKTOP_DOWNLOAD_REQUEST_TOKEN_TTL_SECONDS: int = 86400
    DESKTOP_DOWNLOAD_AUTH_MAX_AGE_SECONDS: int = 86400
    # Native desktop auth fails closed without a private 32+ character secret.
    DESKTOP_AUTH_SIGNING_SECRET: str = ""
    DESKTOP_AUTH_LINK_TTL_SECONDS: int = 600
    DESKTOP_AUTH_LINK_GLOBAL_RATE_LIMIT_COUNT: int = 120
    DESKTOP_AUTH_LINK_GLOBAL_RATE_LIMIT_WINDOW_SECONDS: int = 60
    DESKTOP_AUTH_ACCESS_TTL_SECONDS: int = 900
    DESKTOP_AUTH_REFRESH_TTL_DAYS: int = 30
    # Expired/revoked native auth rows are retained briefly for incident review,
    # then removed by the background retention job.
    DESKTOP_AUTH_RECORD_RETENTION_DAYS: int = 30
    ADMIN_MINIAPP_AUTH_MAX_AGE_SECONDS: int = 86400

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
