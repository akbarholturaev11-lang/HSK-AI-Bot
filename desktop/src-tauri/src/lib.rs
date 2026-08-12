mod local_ai;

use base64::{
    engine::general_purpose::{STANDARD, URL_SAFE_NO_PAD},
    Engine as _,
};
use rand::{rngs::OsRng, RngCore};
use reqwest::{Client, StatusCode};
use serde::{de::DeserializeOwned, Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    sync::{
        atomic::{AtomicBool, AtomicU64, Ordering},
        Arc, Mutex,
    },
    time::Duration,
};
use tauri::{Emitter, Manager};
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_updater::{Update, UpdaterExt};

use local_ai::{
    LocalAiChatRequest, LocalAiChatResult, LocalAiManager, LocalAiPackStatus, MODEL_ID,
};

const API_ORIGIN: &str = "https://telegram-chinese-bot-production.up.railway.app";
const KEYRING_SERVICE: &str = "com.pomp.hskai";
const KEYRING_REFRESH_ACCOUNT: &str = "desktop-refresh-token";
const KEYRING_INSTALLATION_ACCOUNT: &str = "desktop-installation-key";
const MAX_LESSON_ORDER: i64 = 500;
const MAX_COMPLETION_BODY_BYTES: usize = 64 * 1024;
const MAX_SUBSCRIPTION_SCREENSHOT_BYTES: usize = 8 * 1024 * 1024;
const MAX_SUBSCRIPTION_BASE64_CHARS: usize = MAX_SUBSCRIPTION_SCREENSHOT_BYTES.div_ceil(3) * 4;
const MAX_SUBSCRIPTION_SUBMIT_BODY_BYTES: usize = MAX_SUBSCRIPTION_BASE64_CHARS + 40 + (16 * 1024);
const MAX_SUBSCRIPTION_RESPONSE_BODY_BYTES: usize = 4 * 1024 * 1024;
// Voice practice. The audio ceiling mirrors MAX_AUDIO_BYTES in
// app/services/voice_practice_service.py; raising it here alone only wastes
// upload bandwidth because the server rejects the request anyway.
const MAX_VOICE_AUDIO_BYTES: usize = 5 * 1024 * 1024;
const MAX_VOICE_AUDIO_BASE64_CHARS: usize = MAX_VOICE_AUDIO_BYTES.div_ceil(3) * 4;
const MAX_VOICE_AUDIO_BODY_BYTES: usize = MAX_VOICE_AUDIO_BASE64_CHARS + 40 + (16 * 1024);
const MAX_VOICE_BODY_BYTES: usize = 32 * 1024;
const MAX_VOICE_RESPONSE_BODY_BYTES: usize = 512 * 1024;
const MAX_VOICE_TARGET_CHARS: usize = 120;
const MAX_VOICE_PINYIN_CHARS: usize = 240;
const MAX_VOICE_SESSION_ID_CHARS: usize = 64;
const MAX_RATING_RESPONSE_BODY_BYTES: usize = 256 * 1024;
const MAX_PRACTICE_BODY_BYTES: usize = 16 * 1024;
const MAX_PRACTICE_COMPLETE_BODY_BYTES: usize = 64 * 1024;
const MAX_PRACTICE_RESPONSE_BODY_BYTES: usize = 2 * 1024 * 1024;
const MAX_PRACTICE_ANSWERS: usize = 100;
const MAX_PRACTICE_SESSION_ID_CHARS: usize = 160;
// Saved words and the review queue live in a local file rather than the shared
// database: they are a desktop-only convenience and must survive a webview
// storage reset, which localStorage does not.
const VOCABULARY_FILE: &str = "vocabulary.json";
const MAX_VOCABULARY_ENTRIES: usize = 2_000;
const MAX_VOCABULARY_WORD_CHARS: usize = 24;
const MAX_REFERRAL_RESPONSE_BODY_BYTES: usize = 128 * 1024;
// The study goal has no column on the server, so it is a device-local
// preference kept beside the saved words. Onboarding is the only place that
// writes it; a missing or unknown value is what makes onboarding reopen.
const GOAL_FILE: &str = "daily-goal.json";
const GOAL_KINDS: [&str; 3] = ["conversation", "hsk", "study"];
const MAX_MISTAKES: usize = 50;
const MAX_TTS_CHARS: usize = 1_000;
const MAX_TTS_BYTES: usize = 4_000;
const MAX_UPDATE_VERSION_CHARS: usize = 64;
const MAX_UPDATE_NOTES_CHARS: usize = 8_000;
const MAX_NATIVE_EVENT_RESPONSE_BODY_BYTES: usize = 16 * 1024;
const MAX_NATIVE_EVENT_SIZE_BYTES: u64 = 20_000_000_000;
const MAX_NATIVE_EVENT_DURATION_MS: u64 = 86_400_000;

static EXIT_STOPPING: AtomicBool = AtomicBool::new(false);
static EXIT_READY: AtomicBool = AtomicBool::new(false);

#[derive(Clone)]
struct PendingLink {
    link_request_id: String,
    polling_secret: String,
    display_code: String,
    bot_deep_link: String,
    expires_in: u64,
}

struct DesktopState {
    client: Client,
    access_token: Mutex<Option<String>>,
    pending_link: Mutex<Option<PendingLink>>,
    pending_update: Mutex<Option<Update>>,
    refresh_guard: tokio::sync::Mutex<()>,
    update_guard: tokio::sync::Mutex<()>,
}

impl DesktopState {
    fn new() -> Self {
        let client = Client::builder()
            .redirect(reqwest::redirect::Policy::none())
            .https_only(true)
            .timeout(Duration::from_secs(20))
            .user_agent(concat!("Pomp-HSK-AI-Desktop/", env!("CARGO_PKG_VERSION")))
            .build()
            .expect("failed to create allowlisted desktop API client");
        Self {
            client,
            access_token: Mutex::new(None),
            pending_link: Mutex::new(None),
            pending_update: Mutex::new(None),
            refresh_guard: tokio::sync::Mutex::new(()),
            update_guard: tokio::sync::Mutex::new(()),
        }
    }
}

#[derive(Deserialize)]
struct ApiError {
    error: Option<String>,
}

#[derive(Deserialize)]
struct LinkStartResponse {
    link_request_id: String,
    display_code: String,
    polling_secret: String,
    bot_deep_link: String,
    expires_in: u64,
}

#[derive(Deserialize)]
struct LinkStatusResponse {
    status: String,
    access_token: Option<String>,
    refresh_token: Option<String>,
}

#[derive(Deserialize)]
struct RefreshResponse {
    access_token: String,
    refresh_token: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopLinkDisplay {
    status: &'static str,
    display_code: String,
    expires_in: u64,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopLinkPoll {
    status: String,
    bootstrap: Option<Value>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopAuthStatus {
    linked: bool,
    bootstrap: Option<Value>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopAppInfo {
    product_name: &'static str,
    version: &'static str,
    platform: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    launch_issue: Option<&'static str>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopTtsStatus {
    ok: bool,
    available: bool,
    error: &'static str,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopUpdateStatus {
    available: bool,
    current_version: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    notes: Option<String>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopUpdateProgress {
    downloaded_bytes: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    total_bytes: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    percent: Option<u8>,
    state: &'static str,
}

fn emit_update_progress(
    app: &tauri::AppHandle,
    downloaded_bytes: u64,
    total_bytes: Option<u64>,
    state: &'static str,
) {
    let percent = total_bytes
        .filter(|total| *total > 0)
        .map(|total| ((downloaded_bytes.saturating_mul(100) / total).min(100)) as u8);
    let _ = app.emit(
        "desktop-update://progress",
        DesktopUpdateProgress {
            downloaded_bytes,
            total_bytes,
            percent,
            state,
        },
    );
}

fn bounded_timezone_query(raw_timezone: &str) -> bool {
    let timezone = raw_timezone.parse::<i32>().ok();
    timezone.is_some_and(|value| (-720..=840).contains(&value))
        && timezone.map(|value| value.to_string()) == Some(raw_timezone.to_string())
}

fn api_url(path: &str) -> Result<String, String> {
    match path {
        "/api/v3/desktop-auth/link/start"
        | "/api/v3/desktop-auth/link/status"
        | "/api/v3/desktop-auth/refresh"
        | "/api/v3/desktop-auth/revoke"
        | "/api/v3/desktop/bootstrap"
        | "/api/v3/desktop/course/map"
        | "/api/v3/desktop/course/complete"
        | "/api/v3/desktop/events"
        | "/api/v3/desktop/preferences/language"
        | "/api/v3/desktop/preferences/notifications"
        | "/api/v3/desktop/subscription/overview"
        | "/api/v3/desktop/subscription/quote"
        | "/api/v3/desktop/subscription/submit"
        | "/api/v3/desktop/practice/start"
        | "/api/v3/desktop/practice/complete"
        | "/api/v3/desktop/voice/status"
        | "/api/v3/desktop/voice/session/start"
        | "/api/v3/desktop/voice/message"
        | "/api/v3/desktop/voice/pronounce"
        | "/api/v3/desktop/voice/session/end" => Ok(format!("{API_ORIGIN}{path}")),
        _ => {
            if path
                == format!(
                    "/api/v3/desktop/bootstrap?app_version={}",
                    env!("CARGO_PKG_VERSION")
                )
            {
                return Ok(format!("{API_ORIGIN}{path}"));
            }
            if let Some(raw_timezone) = path.strip_prefix("/api/v3/desktop/course/map?tz=") {
                if bounded_timezone_query(raw_timezone) {
                    return Ok(format!("{API_ORIGIN}{path}"));
                }
            }
            if let Some(raw_timezone) = path.strip_prefix("/api/v3/desktop/rating/leaderboard?tz=")
            {
                if bounded_timezone_query(raw_timezone) {
                    return Ok(format!("{API_ORIGIN}{path}"));
                }
            }
            if let Some(raw_timezone) = path.strip_prefix("/api/v3/desktop/referral/overview?tz=") {
                if bounded_timezone_query(raw_timezone) {
                    return Ok(format!("{API_ORIGIN}{path}"));
                }
            }
            let lesson_order = path
                .strip_prefix("/api/v3/desktop/course/lesson/")
                .filter(|raw| {
                    !raw.is_empty()
                        && raw.bytes().all(|byte| byte.is_ascii_digit())
                        && !raw.starts_with('0')
                })
                .and_then(|raw| raw.parse::<i64>().ok());
            if lesson_order.is_some_and(|value| (1..=MAX_LESSON_ORDER).contains(&value)) {
                return Ok(format!("{API_ORIGIN}{path}"));
            }
            Err("desktop_api_operation_not_allowed".into())
        }
    }
}

fn course_map_path(timezone_offset_minutes: Option<i32>) -> Result<String, String> {
    match timezone_offset_minutes {
        Some(value) if (-720..=840).contains(&value) => {
            Ok(format!("/api/v3/desktop/course/map?tz={value}"))
        }
        Some(_) => Err("desktop_timezone_invalid".into()),
        None => Ok("/api/v3/desktop/course/map".into()),
    }
}

fn validate_lesson_order(lesson_order: i64) -> Result<i64, String> {
    if (1..=MAX_LESSON_ORDER).contains(&lesson_order) {
        Ok(lesson_order)
    } else {
        Err("desktop_lesson_order_invalid".into())
    }
}

fn validate_event_id(event_id: &str) -> Result<&str, String> {
    let value = event_id.trim();
    if !(16..=80).contains(&value.len()) {
        return Err("desktop_event_id_invalid".into());
    }
    let mut bytes = value.bytes();
    if !bytes
        .next()
        .is_some_and(|byte| byte.is_ascii_alphanumeric())
        || !bytes
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b':' | b'-'))
    {
        return Err("desktop_event_id_invalid".into());
    }
    Ok(value)
}

fn validate_language(language: &str) -> Result<&'static str, String> {
    match language.trim().to_ascii_lowercase().as_str() {
        "uz" => Ok("uz"),
        "ru" => Ok("ru"),
        "tj" => Ok("tj"),
        _ => Err("desktop_language_invalid".into()),
    }
}

fn validate_subscription_plan(plan: &str) -> Result<&'static str, String> {
    match plan.trim().to_ascii_lowercase().as_str() {
        "10_days" => Ok("10_days"),
        "1_month" => Ok("1_month"),
        "3_months" => Ok("3_months"),
        _ => Err("desktop_subscription_request_invalid".into()),
    }
}

fn validate_subscription_method(method: &str) -> Result<&'static str, String> {
    match method.trim().to_ascii_lowercase().as_str() {
        "visa" => Ok("visa"),
        "alipay" => Ok("alipay"),
        "wechat" => Ok("wechat"),
        _ => Err("desktop_subscription_request_invalid".into()),
    }
}

fn validate_subscription_country(
    method: &str,
    country: Option<&str>,
) -> Result<Option<&'static str>, String> {
    if method != "visa" {
        return if country.is_none() {
            Ok(None)
        } else {
            Err("desktop_subscription_request_invalid".into())
        };
    }
    match country
        .map(str::trim)
        .map(str::to_ascii_lowercase)
        .as_deref()
    {
        Some("tj") => Ok(Some("tj")),
        Some("uz") => Ok(Some("uz")),
        Some("ru") => Ok(Some("ru")),
        Some("other") => Ok(Some("other")),
        _ => Err("desktop_subscription_request_invalid".into()),
    }
}

fn validate_checkout_attempt_id(value: Option<&str>) -> Result<Option<&str>, String> {
    let Some(value) = value.map(str::trim) else {
        return Ok(None);
    };
    if (16..=80).contains(&value.len())
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
    {
        Ok(Some(value))
    } else {
        Err("desktop_subscription_request_invalid".into())
    }
}

fn validate_subscription_image_data_url(value: &str) -> Result<(), String> {
    let (prefix, encoded) = value
        .split_once(',')
        .ok_or_else(|| "desktop_payment_file_type_invalid".to_string())?;
    let image_kind = match prefix {
        "data:image/jpeg;base64" | "data:image/jpg;base64" => "jpeg",
        "data:image/png;base64" => "png",
        "data:image/webp;base64" => "webp",
        _ => return Err("desktop_payment_file_type_invalid".into()),
    };
    if encoded.is_empty() || encoded.len() > MAX_SUBSCRIPTION_BASE64_CHARS {
        return Err("desktop_payment_file_too_large".into());
    }
    let decoded = STANDARD
        .decode(encoded.as_bytes())
        .map_err(|_| "desktop_payment_file_invalid".to_string())?;
    if decoded.is_empty() || decoded.len() > MAX_SUBSCRIPTION_SCREENSHOT_BYTES {
        return Err("desktop_payment_file_too_large".into());
    }
    let signature_matches = match image_kind {
        "jpeg" => decoded.starts_with(&[0xff, 0xd8, 0xff]),
        "png" => decoded.starts_with(b"\x89PNG\r\n\x1a\n"),
        "webp" => {
            decoded.len() >= 12
                && decoded.starts_with(b"RIFF")
                && decoded.get(8..12) == Some(b"WEBP")
        }
        _ => false,
    };
    if !signature_matches {
        return Err("desktop_payment_file_invalid".into());
    }
    Ok(())
}

/// Conversation roles allowed by ROLE_PROMPTS in the voice practice service.
fn validate_voice_role(role: &str) -> Result<&'static str, String> {
    match role.trim().to_ascii_lowercase().as_str() {
        "lily" => Ok("lily"),
        "chen" => Ok("chen"),
        "xiao_mei" => Ok("xiao_mei"),
        "teacher_li" => Ok("teacher_li"),
        "manager_wang" => Ok("manager_wang"),
        "friend" => Ok("friend"),
        "roommate" => Ok("roommate"),
        "seller" => Ok("seller"),
        "classmate" => Ok("classmate"),
        "social" => Ok("social"),
        _ => Err("desktop_voice_role_invalid".into()),
    }
}

fn validate_voice_level(level: &str) -> Result<&'static str, String> {
    match level.trim().to_ascii_lowercase().as_str() {
        "beginner" => Ok("beginner"),
        "hsk1" => Ok("hsk1"),
        "hsk2" => Ok("hsk2"),
        "hsk3" => Ok("hsk3"),
        // users.level stores "hsk4a"/"hsk4b" bands; both speak at HSK4.
        "hsk4" | "hsk4a" | "hsk4b" => Ok("hsk4"),
        "hsk1_2" => Ok("hsk1_2"),
        "hsk3_4" => Ok("hsk3_4"),
        _ => Err("desktop_voice_level_invalid".into()),
    }
}

fn validate_voice_voice(voice: &str) -> Result<&'static str, String> {
    match voice.trim().to_ascii_lowercase().as_str() {
        "female" => Ok("female"),
        "male" => Ok("male"),
        _ => Err("desktop_voice_request_invalid".into()),
    }
}

fn validate_voice_session_id(value: &str) -> Result<&str, String> {
    let trimmed = value.trim();
    if trimmed.len() < 8
        || trimmed.len() > MAX_VOICE_SESSION_ID_CHARS
        || !trimmed
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-')
    {
        return Err("desktop_voice_session_invalid".into());
    }
    Ok(trimmed)
}

fn validate_voice_target(value: &str) -> Result<&str, String> {
    let trimmed = value.trim();
    if trimmed.is_empty() || trimmed.chars().count() > MAX_VOICE_TARGET_CHARS {
        return Err("desktop_voice_request_invalid".into());
    }
    Ok(trimmed)
}

fn validate_voice_pinyin(value: &str) -> Result<&str, String> {
    let trimmed = value.trim();
    if trimmed.chars().count() > MAX_VOICE_PINYIN_CHARS {
        return Err("desktop_voice_request_invalid".into());
    }
    Ok(trimmed)
}

/// macOS WKWebView produces `audio/mp4`; Windows WebView2 produces
/// `audio/webm`. Both must pass or the two desktop builds behave differently.
fn validate_voice_audio_data_url(value: &str) -> Result<(), String> {
    let (prefix, encoded) = value
        .split_once(',')
        .ok_or_else(|| "desktop_voice_audio_invalid".to_string())?;
    let audio_kind = match prefix {
        "data:audio/webm;base64" => "webm",
        "data:audio/ogg;base64" => "ogg",
        "data:audio/mp4;base64" => "mp4",
        "data:audio/mpeg;base64" => "mp3",
        "data:audio/wav;base64" => "wav",
        _ => return Err("desktop_voice_audio_invalid".into()),
    };
    if encoded.is_empty() {
        return Err("desktop_voice_audio_invalid".into());
    }
    if encoded.len() > MAX_VOICE_AUDIO_BASE64_CHARS {
        return Err("desktop_voice_audio_too_large".into());
    }
    let decoded = STANDARD
        .decode(encoded.as_bytes())
        .map_err(|_| "desktop_voice_audio_invalid".to_string())?;
    if decoded.is_empty() {
        return Err("desktop_voice_audio_invalid".into());
    }
    if decoded.len() > MAX_VOICE_AUDIO_BYTES {
        return Err("desktop_voice_audio_too_large".into());
    }
    let signature_matches = match audio_kind {
        "webm" => decoded.starts_with(&[0x1a, 0x45, 0xdf, 0xa3]),
        "ogg" => decoded.starts_with(b"OggS"),
        "mp4" => decoded.len() >= 12 && decoded.get(4..8) == Some(b"ftyp"),
        "mp3" => {
            decoded.starts_with(b"ID3")
                || decoded.starts_with(&[0xff, 0xfb])
                || decoded.starts_with(&[0xff, 0xf3])
                || decoded.starts_with(&[0xff, 0xf2])
        }
        "wav" => {
            decoded.len() >= 12
                && decoded.starts_with(b"RIFF")
                && decoded.get(8..12) == Some(b"WAVE")
        }
        _ => false,
    };
    if !signature_matches {
        return Err("desktop_voice_audio_invalid".into());
    }
    Ok(())
}

fn validate_practice_mode(mode: &str) -> Result<&'static str, String> {
    match mode.trim().to_ascii_lowercase().as_str() {
        "placement" => Ok("placement"),
        "mock" => Ok("mock"),
        "training" => Ok("training"),
        _ => Err("desktop_practice_request_invalid".into()),
    }
}

fn validate_practice_skill(mode: &str, skill: &str) -> Result<&'static str, String> {
    let normalized = skill.trim().to_ascii_lowercase();
    if mode != "training" {
        return if normalized.is_empty() {
            Ok("")
        } else {
            Err("desktop_practice_request_invalid".into())
        };
    }
    match normalized.as_str() {
        "listening" => Ok("listening"),
        "writing" => Ok("writing"),
        "characters" => Ok("characters"),
        "pronunciation" => Ok("pronunciation"),
        "pinyin" => Ok("pinyin"),
        _ => Err("unknown_training_skill".into()),
    }
}

fn validate_practice_level(level: &str) -> Result<&str, String> {
    let trimmed = level.trim();
    if trimmed.is_empty()
        || trimmed.len() > 16
        || !trimmed
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_')
    {
        return Err("desktop_practice_request_invalid".into());
    }
    Ok(trimmed)
}

fn validate_practice_session_id(value: &str) -> Result<&str, String> {
    let trimmed = value.trim();
    if trimmed.len() < 8 || trimmed.len() > MAX_PRACTICE_SESSION_ID_CHARS {
        return Err("desktop_practice_request_invalid".into());
    }
    Ok(trimmed)
}

/// Answers are the only bulk payload the webview sends here, so the shape is
/// checked before it reaches the network: a list of `{question_id, selected}`.
fn validate_practice_answers(answers: &Value) -> Result<(), String> {
    let items = answers
        .as_array()
        .ok_or_else(|| "desktop_practice_request_invalid".to_string())?;
    if items.len() > MAX_PRACTICE_ANSWERS {
        return Err("desktop_practice_request_too_large".into());
    }
    for item in items {
        let entry = item
            .as_object()
            .ok_or_else(|| "desktop_practice_request_invalid".to_string())?;
        if entry.len() != 2 {
            return Err("desktop_practice_request_invalid".into());
        }
        let question_id = entry
            .get("question_id")
            .and_then(Value::as_str)
            .ok_or_else(|| "desktop_practice_request_invalid".to_string())?;
        if question_id.is_empty() || question_id.len() > 120 {
            return Err("desktop_practice_request_invalid".into());
        }
        let selected = entry
            .get("selected")
            .and_then(Value::as_i64)
            .ok_or_else(|| "desktop_practice_request_invalid".to_string())?;
        if !(-1..=32).contains(&selected) {
            return Err("desktop_practice_request_invalid".into());
        }
    }
    Ok(())
}

fn validate_bounded_json(value: &Value, depth: usize, nodes: &mut usize) -> Result<(), String> {
    *nodes += 1;
    if depth > 6 || *nodes > 2_000 {
        return Err("desktop_mistakes_invalid".into());
    }
    match value {
        Value::Null | Value::Bool(_) | Value::Number(_) => Ok(()),
        Value::String(value) if value.len() <= 2_048 => Ok(()),
        Value::String(_) => Err("desktop_mistakes_invalid".into()),
        Value::Array(items) if items.len() <= 100 => {
            for item in items {
                validate_bounded_json(item, depth + 1, nodes)?;
            }
            Ok(())
        }
        Value::Array(_) => Err("desktop_mistakes_invalid".into()),
        Value::Object(items)
            if items.len() <= 32 && items.keys().all(|key| !key.is_empty() && key.len() <= 64) =>
        {
            for item in items.values() {
                validate_bounded_json(item, depth + 1, nodes)?;
            }
            Ok(())
        }
        Value::Object(_) => Err("desktop_mistakes_invalid".into()),
    }
}

fn validate_mistakes(mistakes: &Value) -> Result<(), String> {
    let items = mistakes
        .as_array()
        .ok_or_else(|| "desktop_mistakes_invalid".to_string())?;
    if items.len() > MAX_MISTAKES || items.iter().any(|item| !item.is_object()) {
        return Err("desktop_mistakes_invalid".into());
    }
    let mut nodes = 0;
    validate_bounded_json(mistakes, 0, &mut nodes)
}

fn validate_tts_text(text: &str) -> Result<(), String> {
    let trimmed = text.trim();
    let char_count = trimmed.chars().count();
    if trimmed.is_empty()
        || char_count > MAX_TTS_CHARS
        || trimmed.len() > MAX_TTS_BYTES
        || trimmed.chars().any(char::is_control)
    {
        return Err("desktop_tts_text_invalid".into());
    }
    Ok(())
}

fn is_allowed_telegram_link(url: &str) -> bool {
    let Ok(parsed) = reqwest::Url::parse(url) else {
        return false;
    };
    let path_ok = parsed.path_segments().is_some_and(|segments| {
        let parts = segments.filter(|part| !part.is_empty()).collect::<Vec<_>>();
        parts.len() == 1
            && (5..=32).contains(&parts[0].len())
            && parts[0]
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
    });
    let mut query = parsed.query_pairs();
    let start_is_manual = query
        .next()
        .is_some_and(|(key, value)| key == "start" && value == "desktop_link");
    parsed.scheme() == "https"
        && parsed.host_str() == Some("t.me")
        && parsed.port().is_none()
        && parsed.username().is_empty()
        && parsed.password().is_none()
        && parsed.fragment().is_none()
        && path_ok
        && start_is_manual
        && query.next().is_none()
}

fn has_only_query_keys(parsed: &reqwest::Url, allowed: &[&str]) -> bool {
    parsed
        .query_pairs()
        .all(|(key, _)| allowed.iter().any(|allowed_key| key == *allowed_key))
}

fn single_query_value(parsed: &reqwest::Url, key: &str) -> Option<String> {
    let mut found = None;
    for (pair_key, value) in parsed.query_pairs() {
        if pair_key == key {
            if found.is_some() {
                return None;
            }
            found = Some(value.into_owned());
        }
    }
    found
}

fn is_allowed_referral_share_link(url: &str) -> bool {
    let Ok(parsed) = reqwest::Url::parse(url) else {
        return false;
    };
    let path_ok = parsed.path_segments().is_some_and(|segments| {
        let parts = segments.filter(|part| !part.is_empty()).collect::<Vec<_>>();
        parts.len() == 1
            && (5..=32).contains(&parts[0].len())
            && parts[0]
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
    });
    let mut query = parsed.query_pairs();
    let start_ok = query.next().is_some_and(|(key, value)| {
        key == "start"
            && value.starts_with("ref_")
            && (5..=128).contains(&value.len())
            && value[4..]
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_' || byte == b'-')
    });
    parsed.scheme() == "https"
        && parsed.host_str() == Some("t.me")
        && parsed.port().is_none()
        && parsed.username().is_empty()
        && parsed.password().is_none()
        && parsed.fragment().is_none()
        && path_ok
        && start_ok
        && query.next().is_none()
}

fn is_allowed_share_text(text: &str) -> bool {
    text.chars().count() <= 1_000
        && text
            .chars()
            .all(|char| !char.is_control() || matches!(char, '\n' | '\r' | '\t'))
        && text.split_whitespace().any(is_allowed_referral_share_link)
}

fn is_allowed_external_url(url: &str) -> bool {
    if url.trim() != url || url.is_empty() || url.len() > 4_096 {
        return false;
    }
    let Ok(parsed) = reqwest::Url::parse(url) else {
        return false;
    };
    if !parsed.username().is_empty()
        || parsed.password().is_some()
        || parsed.port().is_some()
        || parsed.fragment().is_some()
    {
        return false;
    }
    let host = parsed.host_str();
    match parsed.scheme() {
        "tg" => {
            host == Some("msg_url")
                && has_only_query_keys(&parsed, &["url", "text"])
                && single_query_value(&parsed, "url")
                    .is_some_and(|value| is_allowed_referral_share_link(&value))
        }
        "whatsapp" => {
            host == Some("send")
                && has_only_query_keys(&parsed, &["text"])
                && single_query_value(&parsed, "text")
                    .is_some_and(|value| is_allowed_share_text(&value))
        }
        "https" if matches!(host, Some("t.me" | "telegram.me")) => {
            parsed.path() == "/share/url"
                && has_only_query_keys(&parsed, &["url", "text"])
                && single_query_value(&parsed, "url")
                    .is_some_and(|value| is_allowed_referral_share_link(&value))
        }
        "https" if host == Some("wa.me") => {
            matches!(parsed.path(), "" | "/")
                && has_only_query_keys(&parsed, &["text"])
                && single_query_value(&parsed, "text")
                    .is_some_and(|value| is_allowed_share_text(&value))
        }
        "https" if host == Some("api.whatsapp.com") => {
            parsed.path() == "/send"
                && has_only_query_keys(&parsed, &["text"])
                && single_query_value(&parsed, "text")
                    .is_some_and(|value| is_allowed_share_text(&value))
        }
        _ => false,
    }
}

fn keyring_entry(account: &'static str) -> Result<keyring::Entry, String> {
    keyring::Entry::new(KEYRING_SERVICE, account)
        .map_err(|_| "desktop_secure_storage_unavailable".into())
}

fn read_credential(account: &'static str) -> Result<Option<String>, String> {
    match keyring_entry(account)?.get_password() {
        Ok(value) => Ok(Some(value)),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(_) => Err("desktop_secure_storage_unavailable".into()),
    }
}

fn write_credential(account: &'static str, value: &str) -> Result<(), String> {
    keyring_entry(account)?
        .set_password(value)
        .map_err(|_| "desktop_secure_storage_unavailable".into())
}

fn delete_credential(account: &'static str) -> Result<(), String> {
    match keyring_entry(account)?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(_) => Err("desktop_secure_storage_unavailable".into()),
    }
}

fn installation_key() -> Result<String, String> {
    if let Some(existing) = read_credential(KEYRING_INSTALLATION_ACCOUNT)? {
        return Ok(existing);
    }
    let mut bytes = [0_u8; 32];
    OsRng.fill_bytes(&mut bytes);
    let generated = URL_SAFE_NO_PAD.encode(bytes);
    write_credential(KEYRING_INSTALLATION_ACCOUNT, &generated)?;
    Ok(generated)
}

fn platform() -> Result<&'static str, String> {
    #[cfg(target_os = "macos")]
    {
        return Ok("macos");
    }
    #[cfg(target_os = "windows")]
    {
        return Ok("windows");
    }
    #[allow(unreachable_code)]
    Err("desktop_platform_not_supported".into())
}

/// Report why macOS will refuse to give this launch a microphone.
///
/// A quarantined bundle (the normal state after a DMG download) is run from a
/// random read-only `/AppTranslocation/` copy. TCC cannot attribute a
/// permission to that path, so `getUserMedia` is rejected with
/// `NotAllowedError` and the system prompt never appears. Sending the learner
/// to Privacy & Security is useless there — the app is not even listed. AI
/// Voice needs the real reason so it can say "move me into /Applications".
fn launch_issue() -> Option<&'static str> {
    #[cfg(target_os = "macos")]
    {
        let executable = std::env::current_exe().ok()?;
        let path = executable.to_string_lossy();
        if path.contains("/AppTranslocation/") {
            return Some("translocated");
        }
        // Opened straight from the mounted DMG: read-only and equally unknown
        // to TCC, and the volume disappears on eject.
        if path.starts_with("/Volumes/") {
            return Some("read_only_volume");
        }
    }
    None
}

async fn decode_response<T: DeserializeOwned>(response: reqwest::Response) -> Result<T, String> {
    let status = response.status();
    if !status.is_success() {
        let error = response
            .json::<ApiError>()
            .await
            .ok()
            .and_then(|body| body.error)
            .unwrap_or_else(|| "desktop_api_failed".into());
        return Err(error);
    }
    response
        .json::<T>()
        .await
        .map_err(|_| "desktop_api_invalid_response".into())
}

async fn decode_bounded_json_response(
    mut response: reqwest::Response,
    max_body_bytes: usize,
) -> Result<Value, String> {
    let status = response.status();
    let content_type_is_json = response
        .headers()
        .get(reqwest::header::CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.split(';').next())
        .is_some_and(|value| value.trim().eq_ignore_ascii_case("application/json"));
    if !content_type_is_json {
        return Err("desktop_api_invalid_response".into());
    }
    if response
        .content_length()
        .is_some_and(|length| length > max_body_bytes as u64)
    {
        return Err("desktop_api_invalid_response".into());
    }
    let mut body = Vec::new();
    while let Some(chunk) = response
        .chunk()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?
    {
        if body.len().saturating_add(chunk.len()) > max_body_bytes {
            return Err("desktop_api_invalid_response".into());
        }
        body.extend_from_slice(&chunk);
    }
    let value: Value =
        serde_json::from_slice(&body).map_err(|_| "desktop_api_invalid_response".to_string())?;
    if !status.is_success() {
        return Err(value
            .get("error")
            .and_then(Value::as_str)
            .filter(|error| (2..=80).contains(&error.len()))
            .unwrap_or("desktop_api_failed")
            .to_string());
    }
    Ok(value)
}

fn contains_sensitive_subscription_field(value: &Value) -> bool {
    match value {
        Value::Array(items) => items.iter().any(contains_sensitive_subscription_field),
        Value::Object(items) => items.iter().any(|(key, item)| {
            matches!(
                key.as_str(),
                "access_token" | "refresh_token" | "polling_secret" | "installation_key"
            ) || contains_sensitive_subscription_field(item)
        }),
        _ => false,
    }
}

fn validate_subscription_envelope(value: &Value) -> Result<(), String> {
    let payload = value
        .as_object()
        .ok_or_else(|| "desktop_subscription_payload_invalid".to_string())?;
    if payload.get("ok").and_then(Value::as_bool) != Some(true)
        || payload.get("source").and_then(Value::as_str) != Some("desktop_subscription")
        || payload.get("mode").and_then(Value::as_str) != Some("subscription")
        || contains_sensitive_subscription_field(value)
    {
        return Err("desktop_subscription_payload_invalid".into());
    }
    Ok(())
}

fn validate_subscription_access(value: Option<&Value>) -> Result<(), String> {
    let access = value
        .and_then(Value::as_object)
        .ok_or_else(|| "desktop_subscription_payload_invalid".to_string())?;
    let state = access
        .get("state")
        .and_then(Value::as_str)
        .ok_or_else(|| "desktop_subscription_payload_invalid".to_string())?;
    let is_paid = access
        .get("is_paid")
        .and_then(Value::as_bool)
        .ok_or_else(|| "desktop_subscription_payload_invalid".to_string())?;
    if !matches!(state, "free" | "paid" | "blocked") || is_paid != (state == "paid") {
        return Err("desktop_subscription_payload_invalid".into());
    }
    match access.get("expires_at") {
        Some(Value::Null) => Ok(()),
        Some(Value::String(value)) if !value.is_empty() && value.len() <= 64 => Ok(()),
        _ => Err("desktop_subscription_payload_invalid".into()),
    }
}

fn validate_subscription_prices(value: Option<&Value>) -> Result<(), String> {
    let Some(methods) = value.and_then(Value::as_object) else {
        return Err("desktop_subscription_payload_invalid".into());
    };
    for (method, plans) in methods {
        if !matches!(method.as_str(), "visa" | "alipay" | "wechat") {
            return Err("desktop_subscription_payload_invalid".into());
        }
        let Some(plans) = plans.as_object() else {
            return Err("desktop_subscription_payload_invalid".into());
        };
        for (plan, price) in plans {
            if !matches!(plan.as_str(), "10_days" | "1_month" | "3_months") || !price.is_object() {
                return Err("desktop_subscription_payload_invalid".into());
            }
        }
    }
    Ok(())
}

fn validate_subscription_overview_response(value: &Value) -> Result<(), String> {
    validate_subscription_envelope(value)?;
    let payload = value
        .as_object()
        .ok_or_else(|| "desktop_subscription_payload_invalid".to_string())?;
    validate_subscription_access(payload.get("access"))?;
    validate_subscription_prices(payload.get("prices"))?;
    if payload
        .get("checkout_allowed")
        .and_then(Value::as_bool)
        .is_none()
    {
        return Err("desktop_subscription_payload_invalid".into());
    }
    if !matches!(
        payload.get("pending_payment"),
        Some(Value::Null) | Some(Value::Object(_))
    ) || !matches!(
        payload.get("read_only_reason"),
        Some(Value::Null) | Some(Value::String(_))
    ) {
        return Err("desktop_subscription_payload_invalid".into());
    }
    match payload.get("attempt_id") {
        Some(Value::Null) => Ok(()),
        Some(Value::String(value))
            if (16..=80).contains(&value.len())
                && value
                    .bytes()
                    .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-')) =>
        {
            Ok(())
        }
        _ => Err("desktop_subscription_payload_invalid".into()),
    }
}

fn validate_subscription_quote_response(
    value: &Value,
    expected_plan: &str,
    expected_method: &str,
) -> Result<(), String> {
    validate_subscription_envelope(value)
        .map_err(|_| "desktop_subscription_quote_invalid".to_string())?;
    let payload = value
        .as_object()
        .ok_or_else(|| "desktop_subscription_quote_invalid".to_string())?;
    validate_subscription_access(payload.get("access"))
        .map_err(|_| "desktop_subscription_quote_invalid".to_string())?;
    let quote = payload
        .get("quote")
        .and_then(Value::as_object)
        .ok_or_else(|| "desktop_subscription_quote_invalid".to_string())?;
    if quote.get("plan_type").and_then(Value::as_str) != Some(expected_plan)
        || quote.get("payment_method").and_then(Value::as_str) != Some(expected_method)
        || quote.get("final_amount").and_then(Value::as_i64).is_none()
        || quote
            .get("final_currency")
            .and_then(Value::as_str)
            .filter(|value| !value.is_empty() && value.len() <= 16)
            .is_none()
        || quote
            .get("pay_amount")
            .and_then(Value::as_str)
            .filter(|value| !value.is_empty() && value.len() <= 32)
            .is_none()
        || quote
            .get("pay_currency")
            .and_then(Value::as_str)
            .filter(|value| !value.is_empty() && value.len() <= 16)
            .is_none()
    {
        return Err("desktop_subscription_quote_invalid".into());
    }
    if expected_method == "visa" {
        let details = quote
            .get("payment_details")
            .and_then(Value::as_str)
            .unwrap_or("");
        if details.is_empty() || details.len() > 32 * 1024 {
            return Err("desktop_subscription_quote_invalid".into());
        }
    } else if let Some(qr) = quote.get("qr").and_then(Value::as_object) {
        let available = qr.get("available").and_then(Value::as_bool);
        if available.is_none() {
            return Err("desktop_subscription_quote_invalid".into());
        }
        if available == Some(true) {
            let image = qr
                .get("image_data_url")
                .and_then(Value::as_str)
                .ok_or_else(|| "desktop_subscription_quote_invalid".to_string())?;
            validate_subscription_image_data_url(image)
                .map_err(|_| "desktop_subscription_quote_invalid".to_string())?;
        }
    }
    Ok(())
}

fn validate_subscription_submit_response(value: &Value) -> Result<(), String> {
    validate_subscription_envelope(value)
        .map_err(|_| "desktop_subscription_submit_invalid".to_string())?;
    let payload = value
        .as_object()
        .ok_or_else(|| "desktop_subscription_submit_invalid".to_string())?;
    validate_subscription_access(payload.get("access"))
        .map_err(|_| "desktop_subscription_submit_invalid".to_string())?;
    if payload.get("status").and_then(Value::as_str) != Some("pending")
        || payload
            .get("payment_id")
            .and_then(Value::as_i64)
            .map_or(true, |payment_id| payment_id <= 0)
        || !matches!(payload.get("already_pending"), None | Some(Value::Bool(_)))
    {
        return Err("desktop_subscription_submit_invalid".into());
    }
    Ok(())
}

fn current_access_token(state: &DesktopState) -> Result<Option<String>, String> {
    state
        .access_token
        .lock()
        .map_err(|_| "desktop_auth_state_unavailable".to_string())
        .map(|token| token.clone())
}

fn store_access_token(state: &DesktopState, token: Option<String>) -> Result<(), String> {
    *state
        .access_token
        .lock()
        .map_err(|_| "desktop_auth_state_unavailable".to_string())? = token;
    Ok(())
}

fn clear_pending_link(state: &DesktopState) -> Result<(), String> {
    *state
        .pending_link
        .lock()
        .map_err(|_| "desktop_auth_state_unavailable".to_string())? = None;
    Ok(())
}

fn clear_in_memory_auth(state: &DesktopState) -> Result<(), String> {
    let access_error = store_access_token(state, None).err();
    let pending_error = clear_pending_link(state).err();
    access_error.or(pending_error).map_or(Ok(()), Err)
}

fn clear_local_auth_with<F>(state: &DesktopState, delete_refresh: F) -> Result<(), String>
where
    F: FnOnce() -> Result<(), String>,
{
    // Attempt both boundaries even if one fails. In particular, a keyring
    // failure must not keep a usable access token alive in this process.
    let memory_error = clear_in_memory_auth(state).err();
    let credential_error = delete_refresh().err();
    memory_error.or(credential_error).map_or(Ok(()), Err)
}

fn clear_local_auth(state: &DesktopState) -> Result<(), String> {
    clear_local_auth_with(state, || delete_credential(KEYRING_REFRESH_ACCOUNT))
}

fn has_local_session(state: &DesktopState) -> Result<bool, String> {
    if current_access_token(state)?.is_some() {
        return Ok(true);
    }
    Ok(read_credential(KEYRING_REFRESH_ACCOUNT)?.is_some())
}

fn terminal_link_status(error: &str) -> Option<&'static str> {
    match error {
        "desktop_link_expired" => Some("expired"),
        // A polling secret never leaves native memory. For a request that was
        // successfully started, the backend's intentionally opaque "invalid"
        // response means that the link was cancelled or otherwise terminated.
        "desktop_link_cancelled" | "desktop_link_consumed" | "desktop_link_invalid" => {
            Some("cancelled")
        }
        _ => None,
    }
}

async fn refresh_access(
    state: &DesktopState,
    rejected_token: Option<&str>,
) -> Result<String, String> {
    let _refresh_guard = state.refresh_guard.lock().await;
    if let Some(current) = current_access_token(state)? {
        let another_request_already_refreshed =
            rejected_token.map_or(true, |rejected| rejected != current);
        if another_request_already_refreshed {
            return Ok(current);
        }
    }
    let refresh_token = read_credential(KEYRING_REFRESH_ACCOUNT)?
        .ok_or_else(|| "desktop_not_linked".to_string())?;
    let response = state
        .client
        .post(api_url("/api/v3/desktop-auth/refresh")?)
        .json(&json!({"refresh_token": refresh_token}))
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    let refreshed: RefreshResponse = match decode_response(response).await {
        Ok(value) => value,
        Err(error) => {
            if matches!(
                error.as_str(),
                "desktop_refresh_invalid"
                    | "desktop_refresh_reuse_detected"
                    | "desktop_session_revoked"
            ) {
                let _ = delete_credential(KEYRING_REFRESH_ACCOUNT);
                let _ = store_access_token(state, None);
            }
            return Err(error);
        }
    };
    if !(20..=4_096).contains(&refreshed.access_token.len())
        || !(32..=512).contains(&refreshed.refresh_token.len())
    {
        return Err("desktop_api_invalid_response".into());
    }
    write_credential(KEYRING_REFRESH_ACCOUNT, &refreshed.refresh_token)?;
    store_access_token(state, Some(refreshed.access_token.clone()))?;
    Ok(refreshed.access_token)
}

async fn bootstrap_with_token(state: &DesktopState, access_token: &str) -> Result<Value, String> {
    let response = state
        .client
        .get(api_url("/api/v3/desktop/bootstrap")?)
        .bearer_auth(access_token)
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    decode_response(response).await
}

async fn access_token(state: &DesktopState) -> Result<String, String> {
    if let Some(token) = current_access_token(state)? {
        return Ok(token);
    }
    refresh_access(state, None).await
}

async fn authenticated_get_json(state: &DesktopState, path: &str) -> Result<Value, String> {
    let mut token = access_token(state).await?;
    let mut response = state
        .client
        .get(api_url(path)?)
        .bearer_auth(&token)
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    if response.status() == StatusCode::UNAUTHORIZED {
        token = refresh_access(state, Some(&token)).await?;
        response = state
            .client
            .get(api_url(path)?)
            .bearer_auth(&token)
            .send()
            .await
            .map_err(|_| "desktop_api_unavailable".to_string())?;
    }
    decode_response(response).await
}

async fn authenticated_post_json(
    state: &DesktopState,
    path: &str,
    payload: &Value,
) -> Result<Value, String> {
    let payload_size = serde_json::to_vec(payload)
        .map_err(|_| "desktop_request_invalid".to_string())?
        .len();
    if payload_size > MAX_COMPLETION_BODY_BYTES {
        return Err("desktop_request_too_large".into());
    }

    let mut token = access_token(state).await?;
    let mut response = state
        .client
        .post(api_url(path)?)
        .bearer_auth(&token)
        .json(payload)
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    if response.status() == StatusCode::UNAUTHORIZED {
        token = refresh_access(state, Some(&token)).await?;
        response = state
            .client
            .post(api_url(path)?)
            .bearer_auth(&token)
            .json(payload)
            .send()
            .await
            .map_err(|_| "desktop_api_unavailable".to_string())?;
    }
    decode_response(response).await
}

fn local_ai_analytics_payload(
    event_name: &'static str,
    size_bytes: Option<u64>,
    duration_ms: Option<u64>,
) -> Option<Value> {
    if !matches!(
        event_name,
        "desktop_ai_pack_started" | "desktop_ai_pack_completed" | "desktop_offline_ai_used"
    ) || size_bytes.is_some_and(|value| value > MAX_NATIVE_EVENT_SIZE_BYTES)
        || duration_ms.is_some_and(|value| value > MAX_NATIVE_EVENT_DURATION_MS)
    {
        return None;
    }
    let mut random = [0_u8; 18];
    OsRng.fill_bytes(&mut random);
    Some(json!({
        "event_name": event_name,
        "event_id": format!("desktop-ai:{}", URL_SAFE_NO_PAD.encode(random)),
        "model_id": MODEL_ID,
        "size_bytes": size_bytes,
        "duration_ms": duration_ms,
    }))
}

async fn authenticated_native_event(state: &DesktopState, payload: &Value) -> Result<(), String> {
    let path = "/api/v3/desktop/events";
    let mut token = access_token(state).await?;
    let mut response = state
        .client
        .post(api_url(path)?)
        .bearer_auth(&token)
        .json(payload)
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    if response.status() == StatusCode::UNAUTHORIZED {
        token = refresh_access(state, Some(&token)).await?;
        response = state
            .client
            .post(api_url(path)?)
            .bearer_auth(&token)
            .json(payload)
            .send()
            .await
            .map_err(|_| "desktop_api_unavailable".to_string())?;
    }
    let _: Value =
        decode_bounded_json_response(response, MAX_NATIVE_EVENT_RESPONSE_BODY_BYTES).await?;
    Ok(())
}

pub(crate) fn spawn_local_ai_analytics(
    app: tauri::AppHandle,
    event_name: &'static str,
    size_bytes: Option<u64>,
    duration_ms: Option<u64>,
) {
    let Some(payload) = local_ai_analytics_payload(event_name, size_bytes, duration_ms) else {
        return;
    };
    tauri::async_runtime::spawn(async move {
        let state = app.state::<DesktopState>();
        let _ = authenticated_native_event(&state, &payload).await;
    });
}

async fn authenticated_subscription_get_json(
    state: &DesktopState,
    path: &str,
) -> Result<Value, String> {
    if path != "/api/v3/desktop/subscription/overview" {
        return Err("desktop_api_operation_not_allowed".into());
    }
    let mut token = access_token(state).await?;
    let mut response = state
        .client
        .get(api_url(path)?)
        .bearer_auth(&token)
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    if response.status() == StatusCode::UNAUTHORIZED {
        token = refresh_access(state, Some(&token)).await?;
        response = state
            .client
            .get(api_url(path)?)
            .bearer_auth(&token)
            .send()
            .await
            .map_err(|_| "desktop_api_unavailable".to_string())?;
    }
    decode_bounded_json_response(response, MAX_SUBSCRIPTION_RESPONSE_BODY_BYTES).await
}

async fn authenticated_subscription_post_json(
    state: &DesktopState,
    path: &str,
    payload: &Value,
    max_body_bytes: usize,
) -> Result<Value, String> {
    if !matches!(
        path,
        "/api/v3/desktop/subscription/quote" | "/api/v3/desktop/subscription/submit"
    ) {
        return Err("desktop_api_operation_not_allowed".into());
    }
    let payload_size = serde_json::to_vec(payload)
        .map_err(|_| "desktop_subscription_request_invalid".to_string())?
        .len();
    if payload_size > max_body_bytes {
        return Err(if path == "/api/v3/desktop/subscription/submit" {
            "desktop_payment_file_too_large".into()
        } else {
            "desktop_subscription_request_invalid".into()
        });
    }

    let mut token = access_token(state).await?;
    let mut response = state
        .client
        .post(api_url(path)?)
        .bearer_auth(&token)
        .json(payload)
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    if response.status() == StatusCode::UNAUTHORIZED {
        token = refresh_access(state, Some(&token)).await?;
        response = state
            .client
            .post(api_url(path)?)
            .bearer_auth(&token)
            .json(payload)
            .send()
            .await
            .map_err(|_| "desktop_api_unavailable".to_string())?;
    }
    decode_bounded_json_response(response, MAX_SUBSCRIPTION_RESPONSE_BODY_BYTES).await
}

async fn authenticated_voice_get_json(state: &DesktopState, path: &str) -> Result<Value, String> {
    if path != "/api/v3/desktop/voice/status" {
        return Err("desktop_api_operation_not_allowed".into());
    }
    let mut token = access_token(state).await?;
    let mut response = state
        .client
        .get(api_url(path)?)
        .bearer_auth(&token)
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    if response.status() == StatusCode::UNAUTHORIZED {
        token = refresh_access(state, Some(&token)).await?;
        response = state
            .client
            .get(api_url(path)?)
            .bearer_auth(&token)
            .send()
            .await
            .map_err(|_| "desktop_api_unavailable".to_string())?;
    }
    decode_bounded_json_response(response, MAX_VOICE_RESPONSE_BODY_BYTES).await
}

async fn authenticated_voice_post_json(
    state: &DesktopState,
    path: &str,
    payload: &Value,
    max_body_bytes: usize,
) -> Result<Value, String> {
    if !matches!(
        path,
        "/api/v3/desktop/voice/session/start"
            | "/api/v3/desktop/voice/message"
            | "/api/v3/desktop/voice/pronounce"
            | "/api/v3/desktop/voice/session/end"
    ) {
        return Err("desktop_api_operation_not_allowed".into());
    }
    let payload_size = serde_json::to_vec(payload)
        .map_err(|_| "desktop_voice_request_invalid".to_string())?
        .len();
    if payload_size > max_body_bytes {
        return Err("desktop_voice_audio_too_large".into());
    }

    let mut token = access_token(state).await?;
    let mut response = state
        .client
        .post(api_url(path)?)
        .bearer_auth(&token)
        .json(payload)
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    if response.status() == StatusCode::UNAUTHORIZED {
        token = refresh_access(state, Some(&token)).await?;
        response = state
            .client
            .post(api_url(path)?)
            .bearer_auth(&token)
            .json(payload)
            .send()
            .await
            .map_err(|_| "desktop_api_unavailable".to_string())?;
    }
    decode_bounded_json_response(response, MAX_VOICE_RESPONSE_BODY_BYTES).await
}

async fn authenticated_rating_get_json(state: &DesktopState, path: &str) -> Result<Value, String> {
    if !path.starts_with("/api/v3/desktop/rating/leaderboard") {
        return Err("desktop_api_operation_not_allowed".into());
    }
    let mut token = access_token(state).await?;
    let mut response = state
        .client
        .get(api_url(path)?)
        .bearer_auth(&token)
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    if response.status() == StatusCode::UNAUTHORIZED {
        token = refresh_access(state, Some(&token)).await?;
        response = state
            .client
            .get(api_url(path)?)
            .bearer_auth(&token)
            .send()
            .await
            .map_err(|_| "desktop_api_unavailable".to_string())?;
    }
    decode_bounded_json_response(response, MAX_RATING_RESPONSE_BODY_BYTES).await
}

async fn authenticated_practice_post_json(
    state: &DesktopState,
    path: &str,
    payload: &Value,
    max_body_bytes: usize,
) -> Result<Value, String> {
    if !matches!(
        path,
        "/api/v3/desktop/practice/start" | "/api/v3/desktop/practice/complete"
    ) {
        return Err("desktop_api_operation_not_allowed".into());
    }
    let payload_size = serde_json::to_vec(payload)
        .map_err(|_| "desktop_practice_request_invalid".to_string())?
        .len();
    if payload_size > max_body_bytes {
        return Err("desktop_practice_request_too_large".into());
    }

    let mut token = access_token(state).await?;
    let mut response = state
        .client
        .post(api_url(path)?)
        .bearer_auth(&token)
        .json(payload)
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    if response.status() == StatusCode::UNAUTHORIZED {
        token = refresh_access(state, Some(&token)).await?;
        response = state
            .client
            .post(api_url(path)?)
            .bearer_auth(&token)
            .json(payload)
            .send()
            .await
            .map_err(|_| "desktop_api_unavailable".to_string())?;
    }
    decode_bounded_json_response(response, MAX_PRACTICE_RESPONSE_BODY_BYTES).await
}

async fn authenticated_referral_get_json(
    state: &DesktopState,
    path: &str,
) -> Result<Value, String> {
    if !path.starts_with("/api/v3/desktop/referral/overview") {
        return Err("desktop_api_operation_not_allowed".into());
    }
    let mut token = access_token(state).await?;
    let mut response = state
        .client
        .get(api_url(path)?)
        .bearer_auth(&token)
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    if response.status() == StatusCode::UNAUTHORIZED {
        token = refresh_access(state, Some(&token)).await?;
        response = state
            .client
            .get(api_url(path)?)
            .bearer_auth(&token)
            .send()
            .await
            .map_err(|_| "desktop_api_unavailable".to_string())?;
    }
    decode_bounded_json_response(response, MAX_REFERRAL_RESPONSE_BODY_BYTES).await
}

async fn authenticated_bootstrap(state: &DesktopState) -> Result<Value, String> {
    authenticated_get_json(
        state,
        &format!(
            "/api/v3/desktop/bootstrap?app_version={}",
            env!("CARGO_PKG_VERSION")
        ),
    )
    .await
}

async fn revoke_with_token(state: &DesktopState, token: &str) -> Result<bool, String> {
    let response = state
        .client
        .post(api_url("/api/v3/desktop-auth/revoke")?)
        .bearer_auth(token)
        .json(&json!({"revoke_device": true}))
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    if response.status() == StatusCode::UNAUTHORIZED {
        return Ok(false);
    }
    let _: Value = decode_response(response).await?;
    Ok(true)
}

fn bounded_update_text(value: &str, max_chars: usize) -> Option<String> {
    let value = value.trim();
    if value.is_empty() {
        return None;
    }
    Some(value.chars().take(max_chars).collect())
}

fn no_update_status() -> DesktopUpdateStatus {
    DesktopUpdateStatus {
        available: false,
        current_version: env!("CARGO_PKG_VERSION"),
        version: None,
        notes: None,
    }
}

fn available_update_status(version: &str, notes: Option<&str>) -> DesktopUpdateStatus {
    DesktopUpdateStatus {
        available: true,
        current_version: env!("CARGO_PKG_VERSION"),
        version: bounded_update_text(version, MAX_UPDATE_VERSION_CHARS),
        notes: notes.and_then(|value| bounded_update_text(value, MAX_UPDATE_NOTES_CHARS)),
    }
}

async fn check_for_update(app: &tauri::AppHandle) -> Result<Option<Update>, String> {
    let updater = app
        .updater()
        .map_err(|_| "desktop_update_unavailable".to_string())?;
    updater
        .check()
        .await
        .map_err(|_| "desktop_update_check_failed".to_string())
}

fn store_pending_update(state: &DesktopState, update: Option<Update>) -> Result<(), String> {
    *state
        .pending_update
        .lock()
        .map_err(|_| "desktop_update_state_unavailable".to_string())? = update;
    Ok(())
}

fn take_pending_update(state: &DesktopState) -> Result<Option<Update>, String> {
    Ok(state
        .pending_update
        .lock()
        .map_err(|_| "desktop_update_state_unavailable".to_string())?
        .take())
}

#[tauri::command]
fn desktop_app_info() -> Result<DesktopAppInfo, String> {
    Ok(DesktopAppInfo {
        product_name: "HSK AI",
        version: env!("CARGO_PKG_VERSION"),
        platform: platform()?,
        launch_issue: launch_issue(),
    })
}

#[tauri::command]
fn local_ai_model_status(
    app: tauri::AppHandle,
    manager: tauri::State<'_, LocalAiManager>,
) -> LocalAiPackStatus {
    manager.status(&app)
}

#[tauri::command]
fn local_ai_install_start(
    app: tauri::AppHandle,
    manager: tauri::State<'_, LocalAiManager>,
) -> Result<LocalAiPackStatus, String> {
    manager.start_install(app)
}

#[tauri::command]
fn local_ai_install_cancel(
    manager: tauri::State<'_, LocalAiManager>,
) -> Result<LocalAiPackStatus, String> {
    manager.cancel_install()
}

#[tauri::command]
async fn local_ai_pack_remove(
    app: tauri::AppHandle,
    manager: tauri::State<'_, LocalAiManager>,
) -> Result<LocalAiPackStatus, String> {
    manager.remove(&app).await
}

#[tauri::command]
async fn local_ai_chat(
    app: tauri::AppHandle,
    manager: tauri::State<'_, LocalAiManager>,
    request: LocalAiChatRequest,
) -> Result<LocalAiChatResult, String> {
    manager.chat(&app, request).await
}

#[tauri::command]
fn local_ai_chat_cancel(
    manager: tauri::State<'_, LocalAiManager>,
    request_id: String,
) -> Result<(), String> {
    manager.cancel_chat(&request_id)
}

#[tauri::command]
async fn desktop_update_check(
    app: tauri::AppHandle,
    state: tauri::State<'_, DesktopState>,
) -> Result<DesktopUpdateStatus, String> {
    let _guard = state
        .update_guard
        .try_lock()
        .map_err(|_| "desktop_update_busy".to_string())?;
    let update = check_for_update(&app).await?;
    let status = update
        .as_ref()
        .map(|update| available_update_status(&update.version, update.body.as_deref()))
        .unwrap_or_else(no_update_status);
    store_pending_update(&state, update)?;
    Ok(status)
}

#[tauri::command]
async fn desktop_update_install(
    app: tauri::AppHandle,
    state: tauri::State<'_, DesktopState>,
    local_ai: tauri::State<'_, LocalAiManager>,
) -> Result<(), String> {
    let _guard = state
        .update_guard
        .try_lock()
        .map_err(|_| "desktop_update_busy".to_string())?;
    let update = match take_pending_update(&state)? {
        Some(update) => Some(update),
        None => check_for_update(&app).await?,
    };
    let Some(update) = update else {
        return Err("desktop_update_not_available".into());
    };
    local_ai.stop_all(&app).await;
    emit_update_progress(&app, 0, None, "starting");
    let downloaded_bytes = Arc::new(AtomicU64::new(0));
    let chunk_counter = downloaded_bytes.clone();
    let finish_counter = downloaded_bytes.clone();
    let progress_app = app.clone();
    let finish_app = app.clone();
    if update
        .download_and_install(
            move |chunk_length, total_bytes| {
                let downloaded = chunk_counter
                    .fetch_add(chunk_length as u64, Ordering::Relaxed)
                    .saturating_add(chunk_length as u64);
                emit_update_progress(&progress_app, downloaded, total_bytes, "downloading");
            },
            move || {
                emit_update_progress(
                    &finish_app,
                    finish_counter.load(Ordering::Relaxed),
                    None,
                    "downloaded",
                );
            },
        )
        .await
        .is_err()
    {
        store_pending_update(&state, Some(update))?;
        return Err("desktop_update_install_failed".into());
    }

    emit_update_progress(
        &app,
        downloaded_bytes.load(Ordering::Relaxed),
        None,
        "installed",
    );
    // The signed package is installed before the process restarts. The UI can
    // invoke this automatically only while no lesson or local AI task is active.
    app.restart()
}

#[tauri::command]
async fn desktop_auth_status(
    state: tauri::State<'_, DesktopState>,
) -> Result<DesktopAuthStatus, String> {
    match authenticated_bootstrap(&state).await {
        Ok(bootstrap) => Ok(DesktopAuthStatus {
            linked: true,
            bootstrap: Some(bootstrap),
        }),
        Err(error) if error == "desktop_not_linked" => Ok(DesktopAuthStatus {
            linked: false,
            bootstrap: None,
        }),
        Err(error)
            if matches!(
                error.as_str(),
                "desktop_refresh_invalid"
                    | "desktop_refresh_reuse_detected"
                    | "desktop_session_revoked"
                    | "desktop_access_invalid"
                    | "desktop_access_expired"
            ) =>
        {
            Ok(DesktopAuthStatus {
                linked: false,
                bootstrap: None,
            })
        }
        Err(error) => Err(error),
    }
}

#[tauri::command]
async fn desktop_link_start(
    state: tauri::State<'_, DesktopState>,
) -> Result<DesktopLinkDisplay, String> {
    let response = state
        .client
        .post(api_url("/api/v3/desktop-auth/link/start")?)
        .json(&json!({
            "platform": platform()?,
            "app_version": env!("CARGO_PKG_VERSION"),
            "installation_key": installation_key()?,
        }))
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    let started: LinkStartResponse = decode_response(response).await?;
    let display_code_valid = started.display_code.len() == 8
        && started
            .display_code
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric());
    let request_id_valid = started.link_request_id.len() == 36
        && started
            .link_request_id
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() || byte == b'-');
    if !display_code_valid
        || !request_id_valid
        || !(32..=512).contains(&started.polling_secret.len())
        || !(1..=3_600).contains(&started.expires_in)
        || !is_allowed_telegram_link(&started.bot_deep_link)
    {
        return Err("desktop_api_invalid_response".into());
    }
    let pending = PendingLink {
        link_request_id: started.link_request_id,
        polling_secret: started.polling_secret,
        display_code: started.display_code,
        bot_deep_link: started.bot_deep_link,
        expires_in: started.expires_in,
    };
    let display = DesktopLinkDisplay {
        status: "pending",
        display_code: pending.display_code.clone(),
        expires_in: pending.expires_in,
    };
    *state
        .pending_link
        .lock()
        .map_err(|_| "desktop_auth_state_unavailable".to_string())? = Some(pending);
    Ok(display)
}

#[tauri::command]
async fn desktop_link_poll(
    state: tauri::State<'_, DesktopState>,
) -> Result<DesktopLinkPoll, String> {
    let pending = state
        .pending_link
        .lock()
        .map_err(|_| "desktop_auth_state_unavailable".to_string())?
        .clone();
    let Some(pending) = pending else {
        if !has_local_session(&state)? {
            return Err("desktop_link_not_started".into());
        }
        let bootstrap = authenticated_bootstrap(&state).await?;
        return Ok(DesktopLinkPoll {
            status: "linked".into(),
            bootstrap: Some(bootstrap),
        });
    };
    let response = state
        .client
        .post(api_url("/api/v3/desktop-auth/link/status")?)
        .json(&json!({
            "link_request_id": pending.link_request_id,
            "polling_secret": pending.polling_secret,
        }))
        .send()
        .await
        .map_err(|_| "desktop_api_unavailable".to_string())?;
    let linked: LinkStatusResponse = match decode_response(response).await {
        Ok(value) => value,
        Err(error) => {
            if let Some(status) = terminal_link_status(&error) {
                clear_pending_link(&state)?;
                return Ok(DesktopLinkPoll {
                    status: status.into(),
                    bootstrap: None,
                });
            }
            return Err(error);
        }
    };
    if linked.status == "pending" {
        return Ok(DesktopLinkPoll {
            status: "pending".into(),
            bootstrap: None,
        });
    }
    if matches!(linked.status.as_str(), "cancelled" | "expired") {
        clear_pending_link(&state)?;
        return Ok(DesktopLinkPoll {
            status: linked.status,
            bootstrap: None,
        });
    }
    if linked.status != "linked" {
        return Err("desktop_api_invalid_response".into());
    }
    let access_token = linked
        .access_token
        .filter(|value| (20..=4_096).contains(&value.len()))
        .ok_or_else(|| "desktop_api_invalid_response".to_string())?;
    let refresh_token = linked
        .refresh_token
        .filter(|value| (32..=512).contains(&value.len()))
        .ok_or_else(|| "desktop_api_invalid_response".to_string())?;
    write_credential(KEYRING_REFRESH_ACCOUNT, &refresh_token)?;
    store_access_token(&state, Some(access_token.clone()))?;
    clear_pending_link(&state)?;
    // Linking is already committed and credentials are stored. A transient
    // bootstrap failure must not turn the client back into a consumed-code
    // polling loop; the webview can retry the separate bootstrap command.
    let bootstrap = bootstrap_with_token(&state, &access_token).await.ok();
    Ok(DesktopLinkPoll {
        status: "linked".into(),
        bootstrap,
    })
}

#[tauri::command]
fn desktop_link_open_telegram(
    app: tauri::AppHandle,
    state: tauri::State<'_, DesktopState>,
) -> Result<(), String> {
    let url = state
        .pending_link
        .lock()
        .map_err(|_| "desktop_auth_state_unavailable".to_string())?
        .as_ref()
        .map(|pending| pending.bot_deep_link.clone())
        .ok_or_else(|| "desktop_link_not_started".to_string())?;
    if !is_allowed_telegram_link(&url) {
        return Err("desktop_link_invalid".into());
    }
    app.opener()
        .open_url(url, None::<&str>)
        .map_err(|_| "desktop_link_open_failed".into())
}

#[tauri::command]
fn desktop_open_external_url(app: tauri::AppHandle, url: String) -> Result<(), String> {
    let target = url.trim();
    if !is_allowed_external_url(target) {
        return Err("desktop_external_url_invalid".into());
    }
    app.opener()
        .open_url(target.to_string(), None::<&str>)
        .map_err(|_| "desktop_external_open_failed".into())
}

#[tauri::command]
async fn desktop_bootstrap(state: tauri::State<'_, DesktopState>) -> Result<Value, String> {
    authenticated_bootstrap(&state).await
}

#[tauri::command]
async fn desktop_course_map(
    state: tauri::State<'_, DesktopState>,
    timezone_offset_minutes: Option<i32>,
) -> Result<Value, String> {
    let path = course_map_path(timezone_offset_minutes)?;
    authenticated_get_json(&state, &path).await
}

#[tauri::command]
async fn desktop_lesson_data(
    state: tauri::State<'_, DesktopState>,
    lesson_order: i64,
) -> Result<Value, String> {
    let lesson_order = validate_lesson_order(lesson_order)?;
    authenticated_get_json(
        &state,
        &format!("/api/v3/desktop/course/lesson/{lesson_order}"),
    )
    .await
}

#[tauri::command]
async fn desktop_lesson_complete(
    state: tauri::State<'_, DesktopState>,
    lesson_order: i64,
    event_id: String,
    mistakes: Option<Value>,
) -> Result<Value, String> {
    let lesson_order = validate_lesson_order(lesson_order)?;
    let event_id = validate_event_id(&event_id)?;
    let mistakes = mistakes.unwrap_or_else(|| json!([]));
    validate_mistakes(&mistakes)?;
    authenticated_post_json(
        &state,
        "/api/v3/desktop/course/complete",
        &json!({
            "lesson_order": lesson_order,
            "event_id": event_id,
            "mistakes": mistakes,
        }),
    )
    .await
}

#[tauri::command]
async fn desktop_set_language(
    state: tauri::State<'_, DesktopState>,
    language: String,
) -> Result<Value, String> {
    let language = validate_language(&language)?;
    authenticated_post_json(
        &state,
        "/api/v3/desktop/preferences/language",
        &json!({"language": language}),
    )
    .await
}

#[tauri::command]
async fn desktop_set_notifications(
    state: tauri::State<'_, DesktopState>,
    enabled: bool,
) -> Result<Value, String> {
    authenticated_post_json(
        &state,
        "/api/v3/desktop/preferences/notifications",
        &json!({"enabled": enabled}),
    )
    .await
}

#[tauri::command]
async fn desktop_subscription_overview(
    state: tauri::State<'_, DesktopState>,
) -> Result<Value, String> {
    let value =
        authenticated_subscription_get_json(&state, "/api/v3/desktop/subscription/overview")
            .await?;
    validate_subscription_overview_response(&value)?;
    Ok(value)
}

#[tauri::command]
async fn desktop_subscription_quote(
    state: tauri::State<'_, DesktopState>,
    plan: String,
    method: String,
    country: Option<String>,
) -> Result<Value, String> {
    let plan = validate_subscription_plan(&plan)?;
    let method = validate_subscription_method(&method)?;
    let country = validate_subscription_country(method, country.as_deref())?;
    let value = authenticated_subscription_post_json(
        &state,
        "/api/v3/desktop/subscription/quote",
        &json!({
            "plan_type": plan,
            "payment_method": method,
            "card_country": country,
        }),
        MAX_COMPLETION_BODY_BYTES,
    )
    .await?;
    validate_subscription_quote_response(&value, plan, method)?;
    Ok(value)
}

#[tauri::command]
async fn desktop_subscription_submit(
    state: tauri::State<'_, DesktopState>,
    plan: String,
    method: String,
    country: Option<String>,
    screenshot_data_url: String,
    attempt_id: Option<String>,
) -> Result<Value, String> {
    let plan = validate_subscription_plan(&plan)?;
    let method = validate_subscription_method(&method)?;
    let country = validate_subscription_country(method, country.as_deref())?;
    let attempt_id = validate_checkout_attempt_id(attempt_id.as_deref())?;
    validate_subscription_image_data_url(&screenshot_data_url)?;
    let value = authenticated_subscription_post_json(
        &state,
        "/api/v3/desktop/subscription/submit",
        &json!({
            "plan_type": plan,
            "payment_method": method,
            "card_country": country,
            "screenshot_data_url": screenshot_data_url,
            "attempt_id": attempt_id,
        }),
        MAX_SUBSCRIPTION_SUBMIT_BODY_BYTES,
    )
    .await?;
    validate_subscription_submit_response(&value)?;
    Ok(value)
}

#[derive(Debug, Default, Serialize, Deserialize)]
struct VocabularyState {
    #[serde(default)]
    saved: Vec<String>,
    #[serde(default)]
    review: Vec<String>,
}

fn vocabulary_path(app: &tauri::AppHandle) -> Result<std::path::PathBuf, String> {
    let directory = app
        .path()
        .app_local_data_dir()
        .map_err(|_| "desktop_vocabulary_storage_unavailable".to_string())?;
    std::fs::create_dir_all(&directory)
        .map_err(|_| "desktop_vocabulary_storage_unavailable".to_string())?;
    Ok(directory.join(VOCABULARY_FILE))
}

/// Keep only well-formed CJK headwords, de-duplicated and bounded.
fn sanitize_vocabulary_list(value: Option<&Value>) -> Vec<String> {
    let mut seen = std::collections::HashSet::new();
    let mut out = Vec::new();
    let Some(items) = value.and_then(Value::as_array) else {
        return out;
    };
    for item in items {
        let Some(word) = item.as_str() else { continue };
        let trimmed = word.trim();
        let length = trimmed.chars().count();
        if trimmed.is_empty()
            || length > MAX_VOCABULARY_WORD_CHARS
            || !trimmed
                .chars()
                .all(|c| ('\u{4e00}'..='\u{9fff}').contains(&c))
        {
            continue;
        }
        if seen.insert(trimmed.to_string()) {
            out.push(trimmed.to_string());
        }
        if out.len() >= MAX_VOCABULARY_ENTRIES {
            break;
        }
    }
    out
}

#[tauri::command]
fn desktop_vocabulary_state(app: tauri::AppHandle) -> Result<Value, String> {
    let path = vocabulary_path(&app)?;
    let Ok(raw) = std::fs::read_to_string(&path) else {
        return Ok(json!({ "saved": [], "review": [] }));
    };
    // A corrupted file must not brick the dictionary; it resets to empty.
    let parsed: Value = serde_json::from_str(&raw).unwrap_or_else(|_| json!({}));
    Ok(json!({
        "saved": sanitize_vocabulary_list(parsed.get("saved")),
        "review": sanitize_vocabulary_list(parsed.get("review")),
    }))
}

#[tauri::command]
fn desktop_vocabulary_save(
    app: tauri::AppHandle,
    saved: Value,
    review: Value,
) -> Result<Value, String> {
    let state = VocabularyState {
        saved: sanitize_vocabulary_list(Some(&saved)),
        review: sanitize_vocabulary_list(Some(&review)),
    };
    let path = vocabulary_path(&app)?;
    let encoded =
        serde_json::to_vec(&state).map_err(|_| "desktop_vocabulary_save_failed".to_string())?;
    // Write to a sibling temp file first so a crash cannot truncate the list.
    let temporary = path.with_extension("json.tmp");
    std::fs::write(&temporary, &encoded)
        .map_err(|_| "desktop_vocabulary_save_failed".to_string())?;
    std::fs::rename(&temporary, &path).map_err(|_| "desktop_vocabulary_save_failed".to_string())?;
    Ok(json!({ "saved": state.saved, "review": state.review }))
}

#[tauri::command]
async fn desktop_referral_overview(
    state: tauri::State<'_, DesktopState>,
    timezone_offset: i64,
) -> Result<Value, String> {
    if !(-720..=840).contains(&timezone_offset) {
        return Err("desktop_referral_request_invalid".into());
    }
    authenticated_referral_get_json(
        &state,
        &format!("/api/v3/desktop/referral/overview?tz={timezone_offset}"),
    )
    .await
}

fn goal_path(app: &tauri::AppHandle) -> Result<std::path::PathBuf, String> {
    let directory = app
        .path()
        .app_local_data_dir()
        .map_err(|_| "desktop_goal_storage_unavailable".to_string())?;
    std::fs::create_dir_all(&directory)
        .map_err(|_| "desktop_goal_storage_unavailable".to_string())?;
    Ok(directory.join(GOAL_FILE))
}

#[tauri::command]
fn desktop_goal_state(app: tauri::AppHandle) -> Result<Value, String> {
    let path = goal_path(&app)?;
    let Ok(raw) = std::fs::read_to_string(&path) else {
        return Ok(json!({ "kind": "", "configured": false }));
    };
    let parsed: Value = serde_json::from_str(&raw).unwrap_or_else(|_| json!({}));
    let kind = parsed.get("kind").and_then(Value::as_str).unwrap_or("");
    // A file written by an older build only carries `minutes`. It stays
    // unreadable on purpose so onboarding asks for the goal once more.
    let valid = GOAL_KINDS.contains(&kind);
    Ok(json!({
        "kind": if valid { kind } else { "" },
        "configured": valid,
    }))
}

#[tauri::command]
fn desktop_goal_save(app: tauri::AppHandle, kind: String) -> Result<Value, String> {
    let kind = kind.trim();
    if !GOAL_KINDS.contains(&kind) {
        return Err("desktop_goal_request_invalid".into());
    }
    let path = goal_path(&app)?;
    let encoded = serde_json::to_vec(&json!({ "kind": kind }))
        .map_err(|_| "desktop_goal_save_failed".to_string())?;
    let temporary = path.with_extension("json.tmp");
    std::fs::write(&temporary, &encoded).map_err(|_| "desktop_goal_save_failed".to_string())?;
    std::fs::rename(&temporary, &path).map_err(|_| "desktop_goal_save_failed".to_string())?;
    Ok(json!({ "kind": kind, "configured": true }))
}

#[tauri::command]
async fn desktop_practice_start(
    state: tauri::State<'_, DesktopState>,
    mode: String,
    level: String,
    language: String,
    skill: String,
) -> Result<Value, String> {
    let mode = validate_practice_mode(&mode)?;
    let skill = validate_practice_skill(mode, &skill)?;
    let level = validate_practice_level(&level)?;
    let language = validate_language(&language)?;
    authenticated_practice_post_json(
        &state,
        "/api/v3/desktop/practice/start",
        &json!({
            "mode": mode,
            "level": level,
            "language": language,
            "skill": skill,
        }),
        MAX_PRACTICE_BODY_BYTES,
    )
    .await
}

#[tauri::command]
async fn desktop_practice_complete(
    state: tauri::State<'_, DesktopState>,
    session_id: String,
    mode: String,
    level: String,
    language: String,
    skill: String,
    answers: Value,
) -> Result<Value, String> {
    let mode = validate_practice_mode(&mode)?;
    let skill = validate_practice_skill(mode, &skill)?;
    let level = validate_practice_level(&level)?;
    let language = validate_language(&language)?;
    let session_id = validate_practice_session_id(&session_id)?;
    validate_practice_answers(&answers)?;
    authenticated_practice_post_json(
        &state,
        "/api/v3/desktop/practice/complete",
        &json!({
            "session_id": session_id,
            "mode": mode,
            "level": level,
            "language": language,
            "skill": skill,
            "answers": answers,
        }),
        MAX_PRACTICE_COMPLETE_BODY_BYTES,
    )
    .await
}

#[tauri::command]
async fn desktop_rating_leaderboard(
    state: tauri::State<'_, DesktopState>,
    timezone_offset: i64,
) -> Result<Value, String> {
    // The webview reports the local UTC offset so the weekly window matches
    // what the learner sees in the Telegram Mini App.
    if !(-720..=840).contains(&timezone_offset) {
        return Err("desktop_rating_request_invalid".into());
    }
    authenticated_rating_get_json(
        &state,
        &format!("/api/v3/desktop/rating/leaderboard?tz={timezone_offset}"),
    )
    .await
}

#[tauri::command]
async fn desktop_voice_status(state: tauri::State<'_, DesktopState>) -> Result<Value, String> {
    authenticated_voice_get_json(&state, "/api/v3/desktop/voice/status").await
}

#[tauri::command]
async fn desktop_voice_session_start(
    state: tauri::State<'_, DesktopState>,
    role: String,
    level: String,
    language: String,
    voice: String,
) -> Result<Value, String> {
    let role = validate_voice_role(&role)?;
    let level = validate_voice_level(&level)?;
    let language = validate_language(&language)?;
    let voice = validate_voice_voice(&voice)?;
    authenticated_voice_post_json(
        &state,
        "/api/v3/desktop/voice/session/start",
        &json!({
            "role": role,
            "level": level,
            "language": language,
            "voice": voice,
        }),
        MAX_VOICE_BODY_BYTES,
    )
    .await
}

#[tauri::command]
async fn desktop_voice_message(
    state: tauri::State<'_, DesktopState>,
    session_id: String,
    audio_data_url: String,
) -> Result<Value, String> {
    let session_id = validate_voice_session_id(&session_id)?;
    validate_voice_audio_data_url(&audio_data_url)?;
    authenticated_voice_post_json(
        &state,
        "/api/v3/desktop/voice/message",
        &json!({
            "session_id": session_id,
            "audio_data_url": audio_data_url,
        }),
        MAX_VOICE_AUDIO_BODY_BYTES,
    )
    .await
}

#[tauri::command]
async fn desktop_voice_pronounce(
    state: tauri::State<'_, DesktopState>,
    target: String,
    target_pinyin: String,
    language: String,
    level: String,
    audio_data_url: String,
) -> Result<Value, String> {
    let target = validate_voice_target(&target)?;
    let target_pinyin = validate_voice_pinyin(&target_pinyin)?;
    let language = validate_language(&language)?;
    let level = validate_voice_level(&level)?;
    validate_voice_audio_data_url(&audio_data_url)?;
    authenticated_voice_post_json(
        &state,
        "/api/v3/desktop/voice/pronounce",
        &json!({
            "target": target,
            "target_pinyin": target_pinyin,
            "language": language,
            "level": level,
            "audio_data_url": audio_data_url,
        }),
        MAX_VOICE_AUDIO_BODY_BYTES,
    )
    .await
}

#[tauri::command]
async fn desktop_voice_session_end(
    state: tauri::State<'_, DesktopState>,
    session_id: String,
) -> Result<Value, String> {
    let session_id = validate_voice_session_id(&session_id)?;
    authenticated_voice_post_json(
        &state,
        "/api/v3/desktop/voice/session/end",
        &json!({ "session_id": session_id }),
        MAX_VOICE_BODY_BYTES,
    )
    .await
}

#[tauri::command]
fn desktop_tts_speak(text: String) -> Result<DesktopTtsStatus, String> {
    validate_tts_text(&text)?;
    Ok(DesktopTtsStatus {
        ok: false,
        available: false,
        error: "desktop_tts_unavailable",
    })
}

#[tauri::command]
async fn desktop_logout(
    app: tauri::AppHandle,
    state: tauri::State<'_, DesktopState>,
    local_ai: tauri::State<'_, LocalAiManager>,
) -> Result<(), String> {
    local_ai.stop_all(&app).await;
    let revoke_result: Result<(), String> = async {
        let mut access_token = current_access_token(&state)?;
        if access_token.is_none() {
            access_token = Some(refresh_access(&state, None).await?);
        }
        if let Some(token) = access_token {
            if !revoke_with_token(&state, &token).await? {
                let refreshed = refresh_access(&state, Some(&token)).await?;
                if !revoke_with_token(&state, &refreshed).await? {
                    return Err("desktop_session_revoked".into());
                }
            }
        }
        Ok(())
    }
    .await;

    // A failed/offline server revoke must not leave credentials on a machine
    // after the user explicitly logs out. The server session then expires by
    // its normal TTL, while this installation can no longer refresh it.
    let local_result = clear_local_auth(&state);
    local_result?;
    revoke_result
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(DesktopState::new())
        .manage(LocalAiManager::new())
        .invoke_handler(tauri::generate_handler![
            desktop_app_info,
            local_ai_model_status,
            local_ai_install_start,
            local_ai_install_cancel,
            local_ai_pack_remove,
            local_ai_chat,
            local_ai_chat_cancel,
            desktop_update_check,
            desktop_update_install,
            desktop_auth_status,
            desktop_link_start,
            desktop_link_poll,
            desktop_link_open_telegram,
            desktop_open_external_url,
            desktop_bootstrap,
            desktop_logout,
            desktop_course_map,
            desktop_lesson_data,
            desktop_lesson_complete,
            desktop_set_language,
            desktop_set_notifications,
            desktop_subscription_overview,
            desktop_subscription_quote,
            desktop_subscription_submit,
            desktop_vocabulary_state,
            desktop_vocabulary_save,
            desktop_referral_overview,
            desktop_goal_state,
            desktop_goal_save,
            desktop_practice_start,
            desktop_practice_complete,
            desktop_rating_leaderboard,
            desktop_voice_status,
            desktop_voice_session_start,
            desktop_voice_message,
            desktop_voice_pronounce,
            desktop_voice_session_end,
            desktop_tts_speak,
        ])
        .build(tauri::generate_context!())
        .expect("failed to build HSK AI");

    app.run(|app_handle, event| {
        if let tauri::RunEvent::ExitRequested { api, code, .. } = event {
            if EXIT_READY.load(Ordering::SeqCst) {
                return;
            }
            api.prevent_exit();
            if EXIT_STOPPING.swap(true, Ordering::SeqCst) {
                return;
            }
            let app = app_handle.clone();
            let manager = app.state::<LocalAiManager>().inner().clone();
            tauri::async_runtime::spawn(async move {
                manager.stop_all(&app).await;
                EXIT_READY.store(true, Ordering::SeqCst);
                app.exit(code.unwrap_or(0));
            });
        }
    });
}

#[cfg(test)]
mod tests {
    use super::{
        api_url, available_update_status, clear_local_auth_with, course_map_path,
        current_access_token, is_allowed_external_url, is_allowed_telegram_link,
        local_ai_analytics_payload, no_update_status, terminal_link_status,
        validate_checkout_attempt_id, validate_event_id, validate_language, validate_lesson_order,
        validate_mistakes, validate_subscription_country, validate_subscription_image_data_url,
        validate_subscription_method, validate_subscription_overview_response,
        validate_subscription_plan, validate_subscription_quote_response,
        validate_subscription_submit_response, validate_tts_text, DesktopLinkDisplay, DesktopState,
        PendingLink, MAX_MISTAKES, MAX_NATIVE_EVENT_DURATION_MS, MAX_NATIVE_EVENT_SIZE_BYTES,
        MAX_UPDATE_NOTES_CHARS, MAX_UPDATE_VERSION_CHARS,
    };
    use serde_json::{json, to_value, Value};

    #[test]
    fn desktop_transport_rejects_arbitrary_urls_and_paths() {
        assert!(api_url("/api/v3/desktop/bootstrap").is_ok());
        assert!(api_url(&format!(
            "/api/v3/desktop/bootstrap?app_version={}",
            env!("CARGO_PKG_VERSION")
        ))
        .is_ok());
        assert!(api_url("/api/v3/desktop/bootstrap?app_version=999.0.0").is_err());
        assert!(api_url("/api/v3/desktop/bootstrap?app_version=1.0.0&admin=true").is_err());
        assert!(api_url("/api/v3/desktop/course/map").is_ok());
        assert!(api_url("/api/v3/desktop/course/map?tz=300").is_ok());
        assert!(api_url("/api/v3/desktop/course/map?tz=-720").is_ok());
        assert!(api_url("/api/v3/desktop/course/map?tz=841").is_err());
        assert!(api_url("/api/v3/desktop/course/map?tz=300&admin=true").is_err());
        assert!(api_url("/api/v3/desktop/course/lesson/181").is_ok());
        assert!(api_url("/api/v3/desktop/course/complete").is_ok());
        assert!(api_url("/api/v3/desktop/preferences/language").is_ok());
        assert!(api_url("/api/v3/desktop/preferences/notifications").is_ok());
        assert!(api_url("/api/v3/desktop/subscription/overview").is_ok());
        assert!(api_url("/api/v3/desktop/subscription/quote").is_ok());
        assert!(api_url("/api/v3/desktop/subscription/submit").is_ok());
        assert!(api_url("/api/v3/desktop/practice/start").is_ok());
        assert!(api_url("/api/v3/desktop/practice/complete").is_ok());
        assert!(api_url("/api/v3/desktop/rating/leaderboard?tz=300").is_ok());
        assert!(api_url("/api/v3/desktop/rating/leaderboard?tz=-720").is_ok());
        assert!(api_url("/api/v3/desktop/rating/leaderboard?tz=841").is_err());
        assert!(api_url("/api/v3/desktop/rating/leaderboard?tz=300&admin=true").is_err());
        assert!(api_url("/api/v3/desktop/referral/overview?tz=300").is_ok());
        assert!(api_url("/api/v3/desktop/referral/overview?tz=-720").is_ok());
        assert!(api_url("/api/v3/desktop/referral/overview?tz=841").is_err());
        assert!(api_url("/api/v3/desktop/referral/overview?tz=300&admin=true").is_err());
        assert!(api_url("/api/v3/desktop/voice/status").is_ok());
        assert!(api_url("/api/v3/desktop/voice/session/start").is_ok());
        assert!(api_url("/api/v3/desktop/voice/message").is_ok());
        assert!(api_url("/api/v3/desktop/voice/pronounce").is_ok());
        assert!(api_url("/api/v3/desktop/voice/session/end").is_ok());
        assert!(api_url("/api/v3/desktop/events").is_ok());
        assert!(api_url("/api/v3/desktop/subscription/event").is_err());
        assert!(api_url("/api/v3/desktop/subscription/overview?telegram_id=1").is_err());
        assert!(api_url("/api/v3/desktop/voice/status?telegram_id=1").is_err());
        assert!(api_url("https://evil.example/").is_err());
        assert!(api_url("/api/v3/map").is_err());
        assert!(api_url("/api/v3/desktop/course/lesson/0").is_err());
        assert!(api_url("/api/v3/desktop/course/lesson/501").is_err());
        assert!(api_url("/api/v3/desktop/course/lesson/1?admin=true").is_err());
        assert!(api_url("/api/v3/desktop/course/lesson/1/../../admin").is_err());
    }

    #[test]
    fn desktop_course_map_timezone_is_bounded_and_optional() {
        assert_eq!(
            course_map_path(None),
            Ok("/api/v3/desktop/course/map".into())
        );
        assert_eq!(
            course_map_path(Some(-720)),
            Ok("/api/v3/desktop/course/map?tz=-720".into())
        );
        assert_eq!(
            course_map_path(Some(840)),
            Ok("/api/v3/desktop/course/map?tz=840".into())
        );
        assert_eq!(
            course_map_path(Some(841)),
            Err("desktop_timezone_invalid".into())
        );
    }

    #[test]
    fn desktop_update_status_matches_frontend_contract() {
        let available = to_value(available_update_status(" 1.2.3 ", Some(" Security fixes ")))
            .expect("available update must serialize");
        assert_eq!(available["available"], true);
        assert_eq!(available["currentVersion"], env!("CARGO_PKG_VERSION"));
        assert_eq!(available["version"], "1.2.3");
        assert_eq!(available["notes"], "Security fixes");
        assert_eq!(available.as_object().map(|value| value.len()), Some(4));

        let unavailable =
            to_value(no_update_status()).expect("unavailable update status must serialize");
        assert_eq!(unavailable["available"], false);
        assert_eq!(unavailable["currentVersion"], env!("CARGO_PKG_VERSION"));
        assert!(unavailable.get("version").is_none());
        assert!(unavailable.get("notes").is_none());
        assert_eq!(unavailable.as_object().map(|value| value.len()), Some(2));
    }

    #[test]
    fn desktop_update_metadata_is_strictly_bounded() {
        let notes = format!(" {} ", "更".repeat(MAX_UPDATE_NOTES_CHARS + 10));
        let status = available_update_status(&"1".repeat(100), Some(&notes));
        assert_eq!(
            status
                .version
                .as_deref()
                .map(str::chars)
                .map(Iterator::count),
            Some(MAX_UPDATE_VERSION_CHARS)
        );
        assert_eq!(
            status.notes.as_deref().map(str::chars).map(Iterator::count),
            Some(MAX_UPDATE_NOTES_CHARS)
        );
        assert!(available_update_status(" ", Some(" ")).version.is_none());
        assert!(available_update_status("1.2.3", Some(" ")).notes.is_none());
    }

    #[test]
    fn terminal_link_errors_become_explicit_ui_states() {
        assert_eq!(
            terminal_link_status("desktop_link_expired"),
            Some("expired")
        );
        assert_eq!(
            terminal_link_status("desktop_link_invalid"),
            Some("cancelled")
        );
        assert_eq!(
            terminal_link_status("desktop_link_consumed"),
            Some("cancelled")
        );
        assert_eq!(terminal_link_status("desktop_api_unavailable"), None);
    }

    #[test]
    fn local_logout_clears_memory_even_when_keyring_delete_fails() {
        let state = DesktopState::new();
        *state.access_token.lock().expect("access state") = Some("access-token".into());
        *state.pending_link.lock().expect("link state") = Some(PendingLink {
            link_request_id: "00000000-0000-0000-0000-000000000000".into(),
            polling_secret: "p".repeat(32),
            display_code: "ABCD1234".into(),
            bot_deep_link: "https://t.me/test_bot?start=desktop_link".into(),
            expires_in: 300,
        });

        let result =
            clear_local_auth_with(&state, || Err("desktop_secure_storage_unavailable".into()));

        assert_eq!(
            result,
            Err("desktop_secure_storage_unavailable".to_string())
        );
        assert_eq!(current_access_token(&state), Ok(None));
        assert!(state.pending_link.lock().expect("link state").is_none());
    }

    #[test]
    fn desktop_link_display_never_serializes_native_secrets_or_deep_link() {
        let value = to_value(DesktopLinkDisplay {
            status: "pending",
            display_code: "ABCD1234".into(),
            expires_in: 300,
        })
        .expect("display must serialize");
        assert_eq!(value["status"], "pending");
        assert_eq!(value["displayCode"], "ABCD1234");
        assert_eq!(value["expiresIn"], 300);
        assert!(value.get("botDeepLink").is_none());
        assert!(value.get("pollingSecret").is_none());
        assert!(value.get("linkRequestId").is_none());
    }

    #[test]
    fn telegram_link_is_exactly_allowlisted() {
        assert!(is_allowed_telegram_link(
            "https://t.me/darsi_chini_bot?start=desktop_link"
        ));
        assert!(!is_allowed_telegram_link(
            "https://evil.example/darsi_chini_bot?start=desktop_link"
        ));
        assert!(!is_allowed_telegram_link(
            "https://t.me/darsi_chini_bot?start=desktop_link&next=https://evil.example"
        ));
        assert!(!is_allowed_telegram_link(
            "https://t.me/a/b?start=desktop_link"
        ));
        assert!(!is_allowed_telegram_link(
            "http://t.me/darsi_chini_bot?start=desktop_link"
        ));
        assert!(!is_allowed_telegram_link(
            "https://t.me/darsi_chini_bot?start=desktop_ABCD1234"
        ));
        assert!(!is_allowed_telegram_link(
            "https://t.me/darsi_chini_bot?start=desktop_"
        ));
        assert!(!is_allowed_telegram_link(
            "https://lookalike.example@t.me/darsi_chini_bot?start=desktop_link"
        ));
        assert!(!is_allowed_telegram_link(
            "https://t.me/bot-name?start=desktop_link"
        ));
    }

    #[test]
    fn desktop_external_open_urls_are_share_only() {
        assert!(is_allowed_external_url(
            "tg://msg_url?url=https%3A%2F%2Ft.me%2Fdarsi_chini_bot%3Fstart%3Dref_abc&text=HSK%20AI"
        ));
        assert!(is_allowed_external_url(
            "whatsapp://send?text=HSK%20AI%0Ahttps%3A%2F%2Ft.me%2Fdarsi_chini_bot%3Fstart%3Dref_abc"
        ));
        assert!(is_allowed_external_url(
            "https://t.me/share/url?url=https%3A%2F%2Ft.me%2Fdarsi_chini_bot%3Fstart%3Dref_abc&text=HSK%20AI"
        ));
        assert!(is_allowed_external_url(
            "https://wa.me/?text=HSK%20AI%0Ahttps%3A%2F%2Ft.me%2Fdarsi_chini_bot%3Fstart%3Dref_abc"
        ));
        assert!(!is_allowed_external_url("https://evil.example/share"));
        assert!(!is_allowed_external_url("file:///etc/passwd"));
        assert!(!is_allowed_external_url(
            "https://lookalike.example@t.me/share/url?url=https%3A%2F%2Fevil.example"
        ));
        assert!(!is_allowed_external_url(
            "https://t.me/share/url?url=https%3A%2F%2Fevil.example&text=HSK%20AI"
        ));
        assert!(!is_allowed_external_url(
            "whatsapp://send?text=HSK%20AI%0Ahttps%3A%2F%2Fevil.example"
        ));
        assert!(!is_allowed_external_url(
            "tg://resolve?domain=darsi_chini_bot"
        ));
    }

    #[test]
    fn desktop_course_inputs_are_bounded() {
        assert_eq!(validate_lesson_order(1), Ok(1));
        assert_eq!(validate_lesson_order(500), Ok(500));
        assert!(validate_lesson_order(0).is_err());
        assert!(validate_lesson_order(501).is_err());

        assert_eq!(
            validate_event_id("desktop.lesson:abc-1234"),
            Ok("desktop.lesson:abc-1234")
        );
        assert!(validate_event_id("short").is_err());
        assert!(validate_event_id("desktop lesson event with spaces").is_err());
        assert!(validate_event_id(&"x".repeat(81)).is_err());

        assert_eq!(validate_language("uz"), Ok("uz"));
        assert_eq!(validate_language(" RU "), Ok("ru"));
        assert!(validate_language("en").is_err());
    }

    #[test]
    fn local_ai_analytics_is_allowlisted_bounded_and_content_free() {
        let payload = local_ai_analytics_payload(
            "desktop_offline_ai_used",
            None,
            Some(MAX_NATIVE_EVENT_DURATION_MS),
        )
        .expect("allowlisted event");
        assert_eq!(payload["event_name"], "desktop_offline_ai_used");
        assert_eq!(payload["model_id"], "qwen3-4b-q4-k-m");
        assert!(payload["event_id"]
            .as_str()
            .is_some_and(|value| (16..=80).contains(&value.len())));
        assert!(payload.get("prompt").is_none());
        assert!(payload.get("history").is_none());
        assert!(payload.get("text").is_none());

        assert!(local_ai_analytics_payload("desktop_ai_pack_started", Some(0), None).is_some());
        assert!(local_ai_analytics_payload(
            "desktop_ai_pack_completed",
            Some(MAX_NATIVE_EVENT_SIZE_BYTES),
            None,
        )
        .is_some());
        assert!(local_ai_analytics_payload("unexpected_event", None, None).is_none());
        assert!(local_ai_analytics_payload(
            "desktop_ai_pack_started",
            Some(MAX_NATIVE_EVENT_SIZE_BYTES + 1),
            None,
        )
        .is_none());
        assert!(local_ai_analytics_payload(
            "desktop_offline_ai_used",
            None,
            Some(MAX_NATIVE_EVENT_DURATION_MS + 1),
        )
        .is_none());
    }

    #[test]
    fn desktop_subscription_inputs_are_strictly_bounded() {
        assert_eq!(validate_subscription_plan("1_month"), Ok("1_month"));
        assert!(validate_subscription_plan("lifetime").is_err());
        assert_eq!(validate_subscription_method("visa"), Ok("visa"));
        assert!(validate_subscription_method("crypto").is_err());
        assert_eq!(
            validate_subscription_country("visa", Some("tj")),
            Ok(Some("tj"))
        );
        assert_eq!(validate_subscription_country("alipay", None), Ok(None));
        assert!(validate_subscription_country("visa", None).is_err());
        assert!(validate_subscription_country("alipay", Some("tj")).is_err());
        assert_eq!(
            validate_checkout_attempt_id(Some("desktop-checkout_1234")),
            Ok(Some("desktop-checkout_1234"))
        );
        assert_eq!(validate_checkout_attempt_id(None), Ok(None));
        assert!(validate_checkout_attempt_id(Some("short")).is_err());
        assert!(validate_checkout_attempt_id(Some("desktop checkout 1234")).is_err());

        let png = concat!(
            "data:image/png;base64,",
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk",
            "+A8AAQUBAScY42YAAAAASUVORK5CYII="
        );
        assert!(validate_subscription_image_data_url(png).is_ok());
        assert!(
            validate_subscription_image_data_url("data:image/png;base64,/9j/not-a-real-png")
                .is_err()
        );
        assert!(validate_subscription_image_data_url("data:text/plain;base64,SGVsbG8=").is_err());
    }

    #[test]
    fn desktop_subscription_responses_are_validated_before_webview_delivery() {
        let access = json!({
            "state": "free",
            "is_paid": false,
            "expires_at": null,
        });
        let overview = json!({
            "ok": true,
            "source": "desktop_subscription",
            "mode": "subscription",
            "access": access,
            "checkout_allowed": true,
            "read_only_reason": null,
            "attempt_id": "desktop-preview-checkout-0001",
            "pending_payment": null,
            "prices": {
                "visa": {
                    "1_month": {"final_amount": 129, "currency": "TJS"}
                }
            }
        });
        assert!(validate_subscription_overview_response(&overview).is_ok());

        let quote = json!({
            "ok": true,
            "source": "desktop_subscription",
            "mode": "subscription",
            "access": access,
            "quote": {
                "plan_type": "1_month",
                "payment_method": "visa",
                "final_amount": 129,
                "final_currency": "TJS",
                "pay_amount": "129",
                "pay_currency": "TJS",
                "payment_details": "0000 0000 0000 0000"
            }
        });
        assert!(validate_subscription_quote_response(&quote, "1_month", "visa").is_ok());
        assert!(validate_subscription_quote_response(&quote, "3_months", "visa").is_err());

        let submitted = json!({
            "ok": true,
            "source": "desktop_subscription",
            "mode": "subscription",
            "access": access,
            "status": "pending",
            "payment_id": 42
        });
        assert!(validate_subscription_submit_response(&submitted).is_ok());

        let mut leaked = overview;
        leaked["access_token"] = json!("must-never-reach-webview");
        assert!(validate_subscription_overview_response(&leaked).is_err());
    }

    #[test]
    fn desktop_mistakes_reject_oversized_or_unstructured_payloads() {
        assert!(validate_mistakes(&json!([])).is_ok());
        assert!(validate_mistakes(&json!([
            {"card_id": "hsk1-1-2", "answer": "你好", "kind": "choice"}
        ]))
        .is_ok());
        assert!(validate_mistakes(&json!({"not": "an array"})).is_err());
        assert!(validate_mistakes(&Value::Array(
            (0..=MAX_MISTAKES).map(|_| json!({})).collect()
        ))
        .is_err());
        assert!(validate_mistakes(&json!(["raw-string-is-not-a-mistake"])).is_err());
        assert!(validate_mistakes(&json!([{"answer": "x".repeat(2_049)}])).is_err());
    }

    #[test]
    fn tts_is_text_only_and_strictly_bounded() {
        assert!(validate_tts_text("你好，今天怎么样？").is_ok());
        assert!(validate_tts_text("").is_err());
        assert!(validate_tts_text(" \n ").is_err());
        assert!(validate_tts_text("hello\u{0000}world").is_err());
        assert!(validate_tts_text(&"汉".repeat(1_001)).is_err());
    }

    #[test]
    fn tauri_config_preserves_product_security_and_window_contract() {
        let config: Value = serde_json::from_str(include_str!("../tauri.conf.json"))
            .expect("tauri.conf.json must remain valid JSON");
        assert_eq!(config["productName"], "HSK AI");
        assert_eq!(config["identifier"], "com.pomp.hskai");
        assert_eq!(config["build"]["frontendDist"], "../ui");
        assert_eq!(config["app"]["withGlobalTauri"], true);
        assert_eq!(config["app"]["windows"][0]["label"], "main");
        assert_eq!(config["app"]["windows"][0]["width"], 1180);
        assert_eq!(config["app"]["windows"][0]["height"], 780);
        assert_eq!(config["app"]["windows"][0]["minWidth"], 720);
        assert_eq!(config["app"]["windows"][0]["minHeight"], 560);
        assert_eq!(config["bundle"]["macOS"]["minimumSystemVersion"], "13.3");
        assert_eq!(config["bundle"]["createUpdaterArtifacts"], true);
        assert_eq!(config["bundle"]["resources"]["runtime/"], "runtime/");

        let csp = config["app"]["security"]["csp"]
            .as_str()
            .expect("strict CSP must be configured");
        assert!(csp.contains("script-src 'self'"));
        assert!(csp.contains("connect-src ipc: http://ipc.localhost"));
        assert!(!csp.contains("unsafe-inline"));
    }
}
