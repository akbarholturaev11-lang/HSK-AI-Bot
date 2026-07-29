use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
use rand::{rngs::OsRng, RngCore};
use reqwest::{Client, StatusCode};
use serde::{de::DeserializeOwned, Deserialize, Serialize};
use serde_json::{json, Value};
use std::{fs, io::ErrorKind, sync::Mutex, time::Duration};
use tauri::Manager;
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_updater::{Update, UpdaterExt};

const API_ORIGIN: &str = "https://telegram-chinese-bot-production.up.railway.app";
const KEYRING_SERVICE: &str = "com.pomp.hskai";
const KEYRING_REFRESH_ACCOUNT: &str = "desktop-refresh-token";
const KEYRING_INSTALLATION_ACCOUNT: &str = "desktop-installation-key";
const LOCAL_AI_MODEL_ID: &str = "qwen3-4b-q4-k-m";
const LOCAL_AI_MODEL_FILE: &str = "qwen3-4b-q4_k_m.gguf";
const MAX_LESSON_ORDER: i64 = 500;
const MAX_COMPLETION_BODY_BYTES: usize = 64 * 1024;
const MAX_MISTAKES: usize = 50;
const MAX_TTS_CHARS: usize = 1_000;
const MAX_TTS_BYTES: usize = 4_000;
const MAX_UPDATE_VERSION_CHARS: usize = 64;
const MAX_UPDATE_NOTES_CHARS: usize = 8_000;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct LocalAiModelStatus {
    model_id: &'static str,
    installed: bool,
    size_bytes: Option<u64>,
    state: &'static str,
}

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

fn api_url(path: &str) -> Result<String, String> {
    match path {
        "/api/v3/desktop-auth/link/start"
        | "/api/v3/desktop-auth/link/status"
        | "/api/v3/desktop-auth/refresh"
        | "/api/v3/desktop-auth/revoke"
        | "/api/v3/desktop/bootstrap"
        | "/api/v3/desktop/course/map"
        | "/api/v3/desktop/course/complete"
        | "/api/v3/desktop/preferences/language" => Ok(format!("{API_ORIGIN}{path}")),
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
                let timezone = raw_timezone.parse::<i32>().ok();
                if timezone.is_some_and(|value| (-720..=840).contains(&value))
                    && timezone.map(|value| value.to_string()) == Some(raw_timezone.to_string())
                {
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

fn telegram_link_code(url: &str) -> Option<String> {
    let Ok(parsed) = reqwest::Url::parse(url) else {
        return None;
    };
    let path_ok = parsed
        .path_segments()
        .is_some_and(|segments| segments.filter(|part| !part.is_empty()).count() == 1);
    let mut query = parsed.query_pairs();
    let start_code = query.next().and_then(|(key, value)| {
        if key != "start" {
            return None;
        }
        let code = value.strip_prefix("desktop_")?;
        if code.len() == 8 && code.bytes().all(|byte| byte.is_ascii_alphanumeric()) {
            Some(code.to_string())
        } else {
            None
        }
    });
    let allowed = parsed.scheme() == "https"
        && parsed.host_str() == Some("t.me")
        && parsed.port().is_none()
        && parsed.username().is_empty()
        && parsed.password().is_none()
        && parsed.fragment().is_none()
        && path_ok
        && query.next().is_none();
    allowed.then_some(start_code).flatten()
}

fn is_allowed_telegram_link(url: &str) -> bool {
    telegram_link_code(url).is_some()
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

fn status(installed: bool, size_bytes: Option<u64>, state: &'static str) -> LocalAiModelStatus {
    LocalAiModelStatus {
        model_id: LOCAL_AI_MODEL_ID,
        installed,
        size_bytes,
        state,
    }
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
        product_name: "Pomp HSK AI",
        version: env!("CARGO_PKG_VERSION"),
        platform: platform()?,
    })
}

#[tauri::command]
fn local_ai_model_status(app: tauri::AppHandle) -> LocalAiModelStatus {
    let Ok(app_data_dir) = app.path().app_local_data_dir() else {
        return status(false, None, "unavailable");
    };

    let model_path = app_data_dir.join("models").join(LOCAL_AI_MODEL_FILE);

    match fs::metadata(model_path) {
        Ok(metadata) if metadata.is_file() && metadata.len() > 0 => {
            status(true, Some(metadata.len()), "ready")
        }
        Ok(_) => status(false, None, "invalid"),
        Err(error) if error.kind() == ErrorKind::NotFound => status(false, None, "missing"),
        Err(_) => status(false, None, "unavailable"),
    }
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
    if update.download_and_install(|_, _| {}, || {}).await.is_err() {
        store_pending_update(&state, Some(update))?;
        return Err("desktop_update_install_failed".into());
    }

    // The app restarts only after the user explicitly invokes this command and
    // the signed updater package has been downloaded and installed successfully.
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
        || telegram_link_code(&started.bot_deep_link).as_deref()
            != Some(started.display_code.as_str())
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
fn desktop_tts_speak(text: String) -> Result<DesktopTtsStatus, String> {
    validate_tts_text(&text)?;
    Ok(DesktopTtsStatus {
        ok: false,
        available: false,
        error: "desktop_tts_unavailable",
    })
}

#[tauri::command]
async fn desktop_logout(state: tauri::State<'_, DesktopState>) -> Result<(), String> {
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
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(DesktopState::new())
        .invoke_handler(tauri::generate_handler![
            desktop_app_info,
            local_ai_model_status,
            desktop_update_check,
            desktop_update_install,
            desktop_auth_status,
            desktop_link_start,
            desktop_link_poll,
            desktop_link_open_telegram,
            desktop_bootstrap,
            desktop_logout,
            desktop_course_map,
            desktop_lesson_data,
            desktop_lesson_complete,
            desktop_set_language,
            desktop_tts_speak,
        ])
        .run(tauri::generate_context!())
        .expect("failed to run Pomp HSK AI");
}

#[cfg(test)]
mod tests {
    use super::{
        api_url, available_update_status, clear_local_auth_with, course_map_path,
        current_access_token, is_allowed_telegram_link, no_update_status, terminal_link_status,
        validate_event_id, validate_language, validate_lesson_order, validate_mistakes,
        validate_tts_text, DesktopLinkDisplay, DesktopState, PendingLink, MAX_MISTAKES,
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
            bot_deep_link: "https://t.me/test_bot?start=desktop_ABCD1234".into(),
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
            "https://t.me/darsi_chini_bot?start=desktop_ABCD1234"
        ));
        assert!(!is_allowed_telegram_link(
            "https://evil.example/darsi_chini_bot?start=desktop_ABCD1234"
        ));
        assert!(!is_allowed_telegram_link(
            "https://t.me/darsi_chini_bot?start=desktop_ABCD1234&next=https://evil.example"
        ));
        assert!(!is_allowed_telegram_link(
            "https://t.me/a/b?start=desktop_ABCD1234"
        ));
        assert!(!is_allowed_telegram_link(
            "http://t.me/darsi_chini_bot?start=desktop_ABCD1234"
        ));
        assert!(!is_allowed_telegram_link(
            "https://t.me/darsi_chini_bot?start=desktop_"
        ));
        assert!(!is_allowed_telegram_link(
            "https://t.me/darsi_chini_bot?start=desktop_ABCD-1234"
        ));
        assert!(!is_allowed_telegram_link(
            "https://lookalike.example@t.me/darsi_chini_bot?start=desktop_ABCD1234"
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
        assert_eq!(config["productName"], "Pomp HSK AI");
        assert_eq!(config["identifier"], "com.pomp.hskai");
        assert_eq!(config["build"]["frontendDist"], "../ui");
        assert_eq!(config["app"]["withGlobalTauri"], true);
        assert_eq!(config["app"]["windows"][0]["label"], "main");
        assert_eq!(config["app"]["windows"][0]["width"], 1180);
        assert_eq!(config["app"]["windows"][0]["height"], 780);
        assert_eq!(config["app"]["windows"][0]["minWidth"], 720);
        assert_eq!(config["app"]["windows"][0]["minHeight"], 560);
        assert_eq!(config["bundle"]["macOS"]["minimumSystemVersion"], "11.0");
        assert_eq!(config["bundle"]["createUpdaterArtifacts"], true);

        let csp = config["app"]["security"]["csp"]
            .as_str()
            .expect("strict CSP must be configured");
        assert!(csp.contains("script-src 'self'"));
        assert!(csp.contains("connect-src ipc: http://ipc.localhost"));
        assert!(!csp.contains("unsafe-inline"));
    }
}
