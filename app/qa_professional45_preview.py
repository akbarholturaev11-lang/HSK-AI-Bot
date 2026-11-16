"""Isolated source-backed visual QA for the real HSK AI learner PWA.

Does not import app.main, construct a Telegram bot, open a database, accept
payments, or read real learner records. Uses ORIGINAL production HTML/CSS/JS
with deterministic, non-private QA fixtures for visual/interaction review.
Never enable on hskai.app or in another Railway project.
"""
from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

STATIC = (Path(__file__).resolve().parent / "static").resolve()
PROJECT_ID = "06a405a4-9ec7-4d1f-87b6-b2f745d8fc76"
ENVIRONMENT_ID = "aa22456f-c3f7-47d8-ad90-904856fc10bd"
_ALLOWED = {"1", "true", "yes"}
_NEVER = (
    "BOT_TOKEN", "DATABASE_URL", "REDIS_URL", "LAVA_API_KEY",
    "LAVA_WEBHOOK_SECRET", "STRIPE_SECRET_KEY", "TELEGRAM_BOT_TOKEN",
    "GOOGLE_CLIENT_SECRET", "ALIPAY_SECRET", "WECHAT_PAY_PRIVATE_KEY",
    "R2_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "OPENAI_API_KEY",
)


def qa_guard() -> None:
    if str(os.environ.get("HSK_PROFESSIONAL45_QA", "")).lower() not in _ALLOWED:
        raise RuntimeError("Standalone Professional45 visual QA must be explicitly enabled")
    if os.environ.get("RAILWAY_PROJECT_ID") != PROJECT_ID:
        raise RuntimeError("Visual QA must run only inside its dedicated project")
    if os.environ.get("RAILWAY_ENVIRONMENT_ID") != ENVIRONMENT_ID:
        raise RuntimeError("Visual QA must run only inside its staging environment")
    if any(os.environ.get(key) for key in _NEVER):
        raise RuntimeError("Visual QA refuses real bot, DB, AI or payment credentials")


qa_guard()
app = FastAPI(title="HSK AI Professional45 isolated visual QA", docs_url=None, redoc_url=None, openapi_url=None)
_no_store = {"Cache-Control": "no-store", "X-HSK-QA-Preview": "visual-only",
             "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"}
_session_words: set[str] = set()
_streak_target = 14


def _response(data: dict, status_code: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status_code, headers=_no_store)


def _course_map() -> dict:
    payload = copy.deepcopy(json.loads((STATIC / "course_v3_data/hsk3.json").read_text(encoding="utf-8")))
    now = datetime.now(timezone.utc)
    local_date = now.strftime("%Y-%m-%d")
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    payload.update({
        "authenticated": True, "level": "hsk3",
        "user": {
            "name": "Алишер", "display_name": "Алишер", "avatar": "学",
            "language": "ru", "is_paid": True, "state": "PRO_ACTIVE",
            "onboarding_completed": True, "level": "hsk3",
        },
        "progress": {
            "xp": 1240, "daily_xp": 40, "weekly_xp": 185,
            "streak": 7, "longest_streak": 12, "completed": 28,
            "local_date": local_date, "week_start": week_start,
            "week_activity_dates": [local_date],
        },
        "study_setup": {
            "daily_minutes": 20, "daily_goal_xp": 60,
            "streak_target_days": _streak_target,
            "pending": False, "goal_chosen": True,
        },
    })
    return payload


_PAGE_MAP = {
    "/iphone-pwa/course": "course-v3.html",
    "/iphone-pwa/dictionary": "hsk-lugat.html",
    "/iphone-pwa/phrases": "hsk-gaplar.html",
    "/iphone-pwa/practice/recognition": "course_v3_recognition.html",
    "/iphone-pwa/practice/memorize": "course_v3_memorize.html",
    "/iphone-pwa/practice/pronunciation": "course_v3_pronunciation.html",
    "/iphone-pwa/practice/mistakes": "course_v3_mistakes.html",
    "/iphone-pwa/practice/test": "course_v3_test.html",
    "/iphone-pwa/practice/voice": "iphone-pwa-voice.html",
    "/iphone-pwa/checkout": "subscription.html",
    "/iphone-pwa/onboarding": "course_v3_onboarding.html",
    "/iphone-pwa/onboarding/li": "course_v3_li_onboarding.html",
}


@app.get("/")
async def home():
    return RedirectResponse("/iphone-pwa/course?lang=ru", status_code=302, headers=_no_store)


@app.get("/healthz")
async def health():
    return _response({"ok": True, "scope": "isolated_source_backed_visual_qa",
                      "production_services": False})


@app.get("/iphone-pwa")
async def pwa_entry():
    return RedirectResponse("/iphone-pwa/course?lang=ru", status_code=302, headers=_no_store)


@app.get("/{path:path}")
async def qa_static(path: str, request: Request):
    url_path = "/" + path
    if url_path in _PAGE_MAP:
        return FileResponse(STATIC / _PAGE_MAP[url_path], headers=_no_store)
    if url_path.startswith("/api/"):
        raise HTTPException(status_code=404, detail="No production API in visual QA")
    candidate = (STATIC / path).resolve()
    if not candidate.is_relative_to(STATIC) or not candidate.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(candidate, headers=_no_store)


# Exact fixture read endpoints; do not create a QA-owned account or a DB.
@app.get("/api/v3/pwa-auth/session")
async def session():
    return _response({"ok": True, "user_id": 900001, "csrf": "isolated-visual-qa"})


@app.get("/api/v3/pwa/map")
async def course_map():
    return _response(_course_map())


@app.get("/api/v3/pwa/profile")
async def profile():
    return _response({
        "ok": True, "stats": {
            "answer_accuracy": {
                "overall": {"percent": 79}, "today": {"percent": 83},
            },
        },
    })


@app.get("/api/v3/pwa/voice/me")
async def voice_quota():
    return _response({"ok": True, "remaining_voice_limit": 0})


@app.post("/api/v3/pwa/dictionary/saved/list")
async def dictionary_saved_list():
    return _response({"ok": True, "words": sorted(_session_words)})


@app.post("/api/v3/pwa/dictionary/saved/set")
async def dictionary_saved_set(request: Request):
    payload = await request.json()
    word, saved = payload.get("hanzi"), payload.get("saved")
    if (not isinstance(word, str) or not 1 <= len(word) <= 16
            or not all("\u3400" <= char <= "\u9fff" for char in word)
            or not isinstance(saved, bool)):
        return _response({"ok": False, "error": "invalid_word"}, 422)
    if saved:
        _session_words.add(word)
    else:
        _session_words.discard(word)
    return _response({"ok": True, "hanzi": word, "saved": saved})


@app.post("/api/v3/pwa/preferences")
async def preferences(request: Request):
    global _streak_target
    payload = await request.json()
    val = payload.get("streak_target_days")
    if val not in (7, 14, 30, 50) or isinstance(val, bool):
        return _response({"ok": False, "error": "invalid_goal"}, 422)
    _streak_target = val
    return _response({"ok": True, "profile": {"streak_target_days": val}})


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def reject_external_actions(path: str):
    return _response({"ok": False, "error": "visual_qa_only"}, 503)
