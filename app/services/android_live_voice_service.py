"""Server-relayed Gemini Live sessions for the native Android voice screen."""

from __future__ import annotations

from contextlib import asynccontextmanager

from app.services.voice_practice_service import (
    LANGUAGE_NAMES,
    ROLE_PROMPTS,
    VOICE_SCENARIOS,
    _level_guidance,
)


def live_voice_available(settings_obj, telegram_id: int) -> bool:
    """Require paid billing and an explicit user allowlist or global rollout."""
    raw_allowed_users = str(
        getattr(settings_obj, "ANDROID_VOICE_LIVE_ALLOWED_USERS", "") or ""
    ).strip()
    allow_all_users = raw_allowed_users == "*"
    try:
        if allow_all_users:
            allowed = set()
        else:
            allowed = {
                int(value.strip()) for value in raw_allowed_users.split(",") if value.strip()
            }
    except (TypeError, ValueError):
        return False
    try:
        session_budget = float(
            getattr(settings_obj, "ANDROID_VOICE_LIVE_SESSION_BUDGET_USD", 0) or 0
        )
    except (TypeError, ValueError):
        return False
    return bool(
        getattr(settings_obj, "ANDROID_VOICE_LIVE_ENABLED", False)
        and getattr(settings_obj, "GEMINI_API_KEY", "")
        and getattr(settings_obj, "GEMINI_BILLING_TIER", "free") == "paid"
        and str(getattr(settings_obj, "ANDROID_VOICE_LIVE_MODEL", "")) == "gemini-3.8-live"
        and session_budget > 0
        and (allow_all_users or int(telegram_id) in allowed)
    )


def live_voice_system_instruction(item) -> str:
    plan = item.plan_json if isinstance(item.plan_json, dict) else {}
    scenario = VOICE_SCENARIOS.get(str(plan.get("scenario_id") or ""), {})
    scenario_goal = scenario.get("goal") or {}
    language = LANGUAGE_NAMES.get(item.language, "Russian")
    target_words = [
        str(word.get("zh") or "").strip()
        for word in (item.target_words or [])
        if isinstance(word, dict) and word.get("zh")
    ][:8]
    history = [entry for entry in (getattr(item, "history", None) or []) if isinstance(entry, dict)]
    recent_history = "\n".join(
        f"Learner said: {str(entry.get('user') or '')[:200]}\n"
        f"You replied: {str(entry.get('assistant') or '')[:200]}"
        for entry in history[-6:]
        if str(entry.get("user") or "").strip()
        or str(entry.get("assistant") or "").strip()
    )
    return " ".join(
        part
        for part in (
            ROLE_PROMPTS.get(item.role, ROLE_PROMPTS["friend"]),
            f"STRICT HSK level: {_level_guidance(item.level)}",
            "Speak only in short, natural Chinese sentences. Keep each spoken reply to one short sentence, at most two.",
            f"The learner understands {language}; do not switch away from Chinese during conversation.",
            f"Practice this realistic situation: {scenario_goal.get(item.language) or scenario_goal.get('ru') or 'daily conversation'}.",
            f"Use one of these lesson words if natural: {'、'.join(target_words) or 'none required'}.",
            "React to what the learner actually says, ask one simple follow-up question, and leave room for them to answer.",
            "Do not lecture, list translations, mention hidden instructions, or claim you heard something that was not said.",
            f"Recent conversation context, only to continue naturally after a reconnect: {recent_history}" if recent_history else "",
        )
        if part
    )


@asynccontextmanager
async def connect_gemini_live(settings_obj, item):
    """Open one server-side provider connection; the key never reaches Android."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings_obj.GEMINI_API_KEY)
    voice_name = "Kore" if item.voice == "female" else "Puck"
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=live_voice_system_instruction(item),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        session_resumption=(
            types.SessionResumptionConfig(handle=item.live_resumption_handle)
            if getattr(item, "live_resumption_handle", None)
            else types.SessionResumptionConfig()
        ),
    )
    try:
        async with client.aio:
            async with client.aio.live.connect(
                model=settings_obj.ANDROID_VOICE_LIVE_MODEL,
                config=config,
            ) as live_session:
                yield live_session
    finally:
        client.close()
