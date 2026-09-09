"""Local SEO preview without production DB, Telegram bot or background jobs.

Run: python -m uvicorn scripts.preview_public_site:app --host 127.0.0.1 --port 8765
"""
from fastapi import FastAPI

from app.api.public_site import create_public_site_router
from app.config import Settings

app = FastAPI()
app.include_router(create_public_site_router(settings_obj=Settings(_env_file=None)))
