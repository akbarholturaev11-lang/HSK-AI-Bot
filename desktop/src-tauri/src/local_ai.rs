use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
use rand::{rngs::OsRng, RngCore};
use reqwest::{header, Client, StatusCode};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    fs as std_fs,
    io::{Read, Write},
    net::TcpListener,
    path::{Path, PathBuf},
    process::Stdio,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    time::{Duration, Instant},
};
use tauri::{Emitter, Manager};
use tokio::{
    fs,
    io::AsyncWriteExt,
    process::{Child, Command},
    sync::Mutex as AsyncMutex,
};

pub(crate) const MODEL_ID: &str = "qwen3-4b-q4-k-m";
pub(crate) const MODEL_REPOSITORY: &str = "Qwen/Qwen3-4B-GGUF";
pub(crate) const MODEL_REVISION: &str = "a9a60d009fa7ff9606305047c2bf77ac25dbec49";
pub(crate) const MODEL_FILE: &str = "qwen3-4b-q4_k_m.gguf";
pub(crate) const MODEL_SIZE_BYTES: u64 = 2_497_280_256;
pub(crate) const MODEL_SHA256: &str =
    "7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5";
const MODEL_DOWNLOAD_URL: &str = "https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/a9a60d009fa7ff9606305047c2bf77ac25dbec49/Qwen3-4B-Q4_K_M.gguf?download=true";
const MARKER_FILE: &str = "qwen3-4b-q4_k_m.verified.json";
const PART_FILE: &str = "qwen3-4b-q4_k_m.gguf.part";
const MAX_PROMPT_BYTES: usize = 16 * 1024;
const MAX_PROMPT_CHARS: usize = 4_000;
const MAX_HISTORY_MESSAGES: usize = 12;
const MAX_HISTORY_BYTES: usize = 64 * 1024;
const MAX_OUTPUT_BYTES: usize = 64 * 1024;
const DEFAULT_MAX_TOKENS: u32 = 384;
const MAX_OUTPUT_TOKENS: u32 = 512;
const CHAT_TIMEOUT: Duration = Duration::from_secs(120);
const RUNTIME_START_TIMEOUT: Duration = Duration::from_secs(120);

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct LocalAiPackStatus {
    pub model_id: &'static str,
    pub installed: bool,
    pub size_bytes: Option<u64>,
    pub expected_size_bytes: u64,
    pub downloaded_bytes: u64,
    pub state: String,
    pub runtime_available: bool,
    pub runtime_state: String,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct PackProgressEvent {
    model_id: &'static str,
    state: String,
    downloaded_bytes: u64,
    expected_size_bytes: u64,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeStatusEvent {
    state: &'static str,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct ChatDeltaEvent<'a> {
    request_id: &'a str,
    delta: &'a str,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct ChatFinishedEvent<'a> {
    request_id: &'a str,
    ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<&'a str>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct LocalAiErrorEvent<'a> {
    operation: &'a str,
    error: &'a str,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub(crate) struct LocalAiChatMessage {
    role: String,
    content: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub(crate) struct LocalAiChatRequest {
    request_id: String,
    prompt: String,
    language: String,
    #[serde(default)]
    history: Vec<LocalAiChatMessage>,
    #[serde(default = "default_max_tokens")]
    max_tokens: u32,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct LocalAiChatResult {
    request_id: String,
    text: String,
    duration_ms: u64,
}

#[derive(Debug, Serialize, Deserialize)]
struct VerificationMarker {
    schema: u8,
    model_id: String,
    repository: String,
    revision: String,
    file_name: String,
    size_bytes: u64,
    sha256: String,
}

impl VerificationMarker {
    fn pinned() -> Self {
        Self {
            schema: 1,
            model_id: MODEL_ID.into(),
            repository: MODEL_REPOSITORY.into(),
            revision: MODEL_REVISION.into(),
            file_name: MODEL_FILE.into(),
            size_bytes: MODEL_SIZE_BYTES,
            sha256: MODEL_SHA256.into(),
        }
    }

    fn is_pinned(&self) -> bool {
        self.schema == 1
            && self.model_id == MODEL_ID
            && self.repository == MODEL_REPOSITORY
            && self.revision == MODEL_REVISION
            && self.file_name == MODEL_FILE
            && self.size_bytes == MODEL_SIZE_BYTES
            && self.sha256 == MODEL_SHA256
    }
}

#[derive(Clone)]
struct RuntimeConnection {
    base_url: String,
    api_key: String,
}

struct RuntimeProcess {
    child: Child,
    connection: RuntimeConnection,
}

struct ActiveChat {
    request_id: String,
    cancelled: Arc<AtomicBool>,
}

struct Inner {
    snapshot: Mutex<LocalAiPackStatus>,
    install_running: AtomicBool,
    install_cancelled: AtomicBool,
    runtime: AsyncMutex<Option<RuntimeProcess>>,
    chat_guard: AsyncMutex<()>,
    active_chat: Mutex<Option<ActiveChat>>,
}

#[derive(Clone)]
pub(crate) struct LocalAiManager {
    inner: Arc<Inner>,
}

impl Default for LocalAiManager {
    fn default() -> Self {
        Self::new()
    }
}

impl LocalAiManager {
    pub(crate) fn new() -> Self {
        let snapshot = LocalAiPackStatus {
            model_id: MODEL_ID,
            installed: false,
            size_bytes: None,
            expected_size_bytes: MODEL_SIZE_BYTES,
            downloaded_bytes: 0,
            state: "missing".into(),
            runtime_available: false,
            runtime_state: "stopped".into(),
        };
        Self {
            inner: Arc::new(Inner {
                snapshot: Mutex::new(snapshot),
                install_running: AtomicBool::new(false),
                install_cancelled: AtomicBool::new(false),
                runtime: AsyncMutex::new(None),
                chat_guard: AsyncMutex::new(()),
                active_chat: Mutex::new(None),
            }),
        }
    }

    pub(crate) fn status(&self, app: &tauri::AppHandle) -> LocalAiPackStatus {
        let mut status = self
            .inner
            .snapshot
            .lock()
            .map(|value| value.clone())
            .unwrap_or_else(|_| unavailable_status());
        status.runtime_available = runtime_binary_path(app).is_ok();

        if self.inner.install_running.load(Ordering::SeqCst) {
            return status;
        }

        #[cfg(debug_assertions)]
        if let Some(path) = debug_model_override() {
            if let Ok(metadata) = std_fs::metadata(path) {
                if metadata.is_file() && metadata.len() > 0 {
                    status.installed = true;
                    status.size_bytes = Some(metadata.len());
                    status.downloaded_bytes = metadata.len();
                    status.state = "debug-ready".into();
                    return status;
                }
            }
        }

        let Ok(paths) = PackPaths::from_app(app) else {
            status.state = "unavailable".into();
            return status;
        };
        let part_size = std_fs::metadata(&paths.part)
            .ok()
            .filter(|metadata| metadata.is_file())
            .map(|metadata| metadata.len())
            .filter(|size| *size <= MODEL_SIZE_BYTES)
            .unwrap_or(0);
        status.downloaded_bytes = part_size;
        match pinned_install_metadata(&paths) {
            Ok(Some(size)) => {
                status.installed = true;
                status.size_bytes = Some(size);
                status.downloaded_bytes = size;
                status.state = "ready".into();
            }
            Ok(None) if part_size > 0 => {
                status.installed = false;
                status.size_bytes = None;
                status.state = "paused".into();
            }
            Ok(None) => {
                status.installed = false;
                status.size_bytes = None;
                status.state = "missing".into();
            }
            Err(_) => {
                status.installed = false;
                status.size_bytes = None;
                status.state = "invalid".into();
            }
        }
        status
    }

    pub(crate) fn start_install(&self, app: tauri::AppHandle) -> Result<LocalAiPackStatus, String> {
        if self
            .inner
            .install_running
            .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
            .is_err()
        {
            return Err("local_ai_install_busy".into());
        }
        self.inner.install_cancelled.store(false, Ordering::SeqCst);
        let mut status = self.status(&app);
        status.state = "starting".into();
        self.set_snapshot(status.clone());
        self.emit_progress(&app, &status);

        let manager = self.clone();
        tauri::async_runtime::spawn(async move {
            let _running = InstallRunningGuard(manager.inner.clone());
            crate::spawn_local_ai_analytics(
                app.clone(),
                "desktop_ai_pack_started",
                Some(MODEL_SIZE_BYTES),
                None,
            );
            if let Err(error) = manager.run_install(&app).await {
                let state = if error == "local_ai_install_cancelled" {
                    "paused"
                } else {
                    "error"
                };
                manager.update_install_state(&app, state, None);
                if error != "local_ai_install_cancelled" {
                    emit_error(&app, "install", &error);
                }
            }
        });
        Ok(status)
    }

    pub(crate) fn cancel_install(&self) -> Result<LocalAiPackStatus, String> {
        if !self.inner.install_running.load(Ordering::SeqCst) {
            return Err("local_ai_install_not_running".into());
        }
        self.inner.install_cancelled.store(true, Ordering::SeqCst);
        self.inner
            .snapshot
            .lock()
            .map(|value| value.clone())
            .map_err(|_| "local_ai_state_unavailable".to_string())
    }

    pub(crate) async fn remove(&self, app: &tauri::AppHandle) -> Result<LocalAiPackStatus, String> {
        if self.inner.install_running.load(Ordering::SeqCst) {
            return Err("local_ai_install_busy".into());
        }
        self.stop_runtime(app).await;
        let paths = PackPaths::from_app(app)?;
        for path in [&paths.model, &paths.part, &paths.marker, &paths.marker_tmp] {
            match fs::remove_file(path).await {
                Ok(()) => {}
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
                Err(_) => return Err("local_ai_remove_failed".into()),
            }
        }
        let status = LocalAiPackStatus {
            model_id: MODEL_ID,
            installed: false,
            size_bytes: None,
            expected_size_bytes: MODEL_SIZE_BYTES,
            downloaded_bytes: 0,
            state: "missing".into(),
            runtime_available: runtime_binary_path(app).is_ok(),
            runtime_state: "stopped".into(),
        };
        self.set_snapshot(status.clone());
        self.emit_progress(app, &status);
        Ok(status)
    }

    pub(crate) fn cancel_chat(&self, request_id: &str) -> Result<(), String> {
        validate_request_id(request_id)?;
        let active = self
            .inner
            .active_chat
            .lock()
            .map_err(|_| "local_ai_state_unavailable".to_string())?;
        let Some(active) = active.as_ref() else {
            return Err("local_ai_chat_not_running".into());
        };
        if active.request_id != request_id {
            return Err("local_ai_chat_request_mismatch".into());
        }
        active.cancelled.store(true, Ordering::SeqCst);
        Ok(())
    }

    pub(crate) async fn chat(
        &self,
        app: &tauri::AppHandle,
        request: LocalAiChatRequest,
    ) -> Result<LocalAiChatResult, String> {
        validate_chat_request(&request)?;
        let _chat_guard = self
            .inner
            .chat_guard
            .try_lock()
            .map_err(|_| "local_ai_chat_busy".to_string())?;
        let connection = self.ensure_runtime(app).await?;
        let cancelled = Arc::new(AtomicBool::new(false));
        {
            let mut active = self
                .inner
                .active_chat
                .lock()
                .map_err(|_| "local_ai_state_unavailable".to_string())?;
            *active = Some(ActiveChat {
                request_id: request.request_id.clone(),
                cancelled: cancelled.clone(),
            });
        }
        let _active_guard = ActiveChatGuard(self.inner.clone());
        let started = Instant::now();
        let result = match tokio::time::timeout(
            CHAT_TIMEOUT,
            stream_chat(app, &connection, &request, cancelled),
        )
        .await
        {
            Ok(result) => result,
            Err(_) => Err("local_ai_chat_timeout".to_string()),
        };

        match result {
            Ok(text) => {
                let duration_ms = duration_ms(started.elapsed());
                let _ = app.emit(
                    "local-ai://chat-finished",
                    ChatFinishedEvent {
                        request_id: &request.request_id,
                        ok: true,
                        error: None,
                    },
                );
                crate::spawn_local_ai_analytics(
                    app.clone(),
                    "desktop_offline_ai_used",
                    None,
                    Some(duration_ms),
                );
                Ok(LocalAiChatResult {
                    request_id: request.request_id,
                    text,
                    duration_ms,
                })
            }
            Err(error) => {
                let _ = app.emit(
                    "local-ai://chat-finished",
                    ChatFinishedEvent {
                        request_id: &request.request_id,
                        ok: false,
                        error: Some(&error),
                    },
                );
                emit_error(app, "chat", &error);
                Err(error)
            }
        }
    }

    pub(crate) async fn stop_runtime(&self, app: &tauri::AppHandle) {
        let mut runtime = self.inner.runtime.lock().await;
        if let Some(mut process) = runtime.take() {
            let _ = process.child.kill().await;
            let _ = process.child.wait().await;
        }
        self.set_runtime_state("stopped");
        let _ = app.emit(
            "local-ai://runtime-status",
            RuntimeStatusEvent { state: "stopped" },
        );
    }

    pub(crate) async fn stop_all(&self, app: &tauri::AppHandle) {
        self.inner.install_cancelled.store(true, Ordering::SeqCst);
        if let Ok(active) = self.inner.active_chat.lock() {
            if let Some(active) = active.as_ref() {
                active.cancelled.store(true, Ordering::SeqCst);
            }
        }
        self.stop_runtime(app).await;
    }

    async fn run_install(&self, app: &tauri::AppHandle) -> Result<(), String> {
        let paths = PackPaths::from_app(app)?;
        fs::create_dir_all(&paths.directory)
            .await
            .map_err(|_| "local_ai_storage_unavailable".to_string())?;

        if file_size(&paths.model).await == Some(MODEL_SIZE_BYTES) {
            self.update_install_state(app, "verifying", Some(MODEL_SIZE_BYTES));
            if verify_sha256(paths.model.clone()).await? {
                write_marker(&paths).await?;
                return self.finish_install(app).await;
            }
            remove_if_exists(&paths.model).await?;
            remove_if_exists(&paths.marker).await?;
        }

        if file_size(&paths.part)
            .await
            .is_some_and(|size| size > MODEL_SIZE_BYTES)
        {
            remove_if_exists(&paths.part).await?;
        }

        let mut downloaded = file_size(&paths.part).await.unwrap_or(0);
        if downloaded == MODEL_SIZE_BYTES {
            self.update_install_state(app, "verifying", Some(downloaded));
            if verify_sha256(paths.part.clone()).await? {
                return self.promote_verified_part(app, &paths).await;
            }
            remove_if_exists(&paths.part).await?;
            downloaded = 0;
        }

        let client = download_client()?;
        let mut request = client.get(MODEL_DOWNLOAD_URL);
        if downloaded > 0 {
            request = request.header(header::RANGE, format!("bytes={downloaded}-"));
        }
        let mut response = request
            .send()
            .await
            .map_err(|_| "local_ai_download_unavailable".to_string())?;
        let status = response.status();
        if downloaded > 0 && status == StatusCode::OK {
            downloaded = 0;
        } else if downloaded > 0 && status == StatusCode::PARTIAL_CONTENT {
            validate_content_range(response.headers(), downloaded)?;
        } else if downloaded == 0 && !matches!(status, StatusCode::OK | StatusCode::PARTIAL_CONTENT)
        {
            return Err("local_ai_download_failed".into());
        } else if downloaded > 0 {
            return Err("local_ai_download_resume_failed".into());
        }

        if response
            .content_length()
            .is_some_and(|length| length != MODEL_SIZE_BYTES - downloaded)
        {
            return Err("local_ai_download_size_mismatch".into());
        }

        let mut options = fs::OpenOptions::new();
        options.create(true).write(true);
        if downloaded == 0 {
            options.truncate(true);
        } else {
            options.append(true);
        }
        let mut output = options
            .open(&paths.part)
            .await
            .map_err(|_| "local_ai_storage_unavailable".to_string())?;
        self.update_install_state(app, "downloading", Some(downloaded));
        let mut last_emit = Instant::now();
        loop {
            if self.inner.install_cancelled.load(Ordering::SeqCst) {
                output
                    .flush()
                    .await
                    .map_err(|_| "local_ai_storage_unavailable".to_string())?;
                return Err("local_ai_install_cancelled".into());
            }
            let chunk = tokio::select! {
                chunk = response.chunk() => chunk
                    .map_err(|_| "local_ai_download_unavailable".to_string())?,
                _ = tokio::time::sleep(Duration::from_millis(100)) => continue,
            };
            let Some(chunk) = chunk else {
                break;
            };
            downloaded = downloaded
                .checked_add(chunk.len() as u64)
                .filter(|value| *value <= MODEL_SIZE_BYTES)
                .ok_or_else(|| "local_ai_download_size_mismatch".to_string())?;
            output
                .write_all(&chunk)
                .await
                .map_err(|_| "local_ai_storage_unavailable".to_string())?;
            if last_emit.elapsed() >= Duration::from_millis(250) || downloaded == MODEL_SIZE_BYTES {
                self.update_install_state(app, "downloading", Some(downloaded));
                last_emit = Instant::now();
            }
        }
        output
            .flush()
            .await
            .map_err(|_| "local_ai_storage_unavailable".to_string())?;
        output
            .sync_all()
            .await
            .map_err(|_| "local_ai_storage_unavailable".to_string())?;
        drop(output);
        if downloaded != MODEL_SIZE_BYTES {
            return Err("local_ai_download_size_mismatch".into());
        }
        if self.inner.install_cancelled.load(Ordering::SeqCst) {
            return Err("local_ai_install_cancelled".into());
        }
        self.update_install_state(app, "verifying", Some(downloaded));
        if !verify_sha256(paths.part.clone()).await? {
            remove_if_exists(&paths.part).await?;
            return Err("local_ai_download_hash_mismatch".into());
        }
        self.promote_verified_part(app, &paths).await
    }

    async fn promote_verified_part(
        &self,
        app: &tauri::AppHandle,
        paths: &PackPaths,
    ) -> Result<(), String> {
        remove_if_exists(&paths.model).await?;
        fs::rename(&paths.part, &paths.model)
            .await
            .map_err(|_| "local_ai_storage_unavailable".to_string())?;
        write_marker(paths).await?;
        self.finish_install(app).await
    }

    async fn finish_install(&self, app: &tauri::AppHandle) -> Result<(), String> {
        let status = LocalAiPackStatus {
            model_id: MODEL_ID,
            installed: true,
            size_bytes: Some(MODEL_SIZE_BYTES),
            expected_size_bytes: MODEL_SIZE_BYTES,
            downloaded_bytes: MODEL_SIZE_BYTES,
            state: "ready".into(),
            runtime_available: runtime_binary_path(app).is_ok(),
            runtime_state: "stopped".into(),
        };
        self.set_snapshot(status.clone());
        self.emit_progress(app, &status);
        crate::spawn_local_ai_analytics(
            app.clone(),
            "desktop_ai_pack_completed",
            Some(MODEL_SIZE_BYTES),
            None,
        );
        Ok(())
    }

    async fn ensure_runtime(&self, app: &tauri::AppHandle) -> Result<RuntimeConnection, String> {
        let mut runtime = self.inner.runtime.lock().await;
        if let Some(process) = runtime.as_mut() {
            match process.child.try_wait() {
                Ok(None) => return Ok(process.connection.clone()),
                Ok(Some(_)) | Err(_) => {
                    *runtime = None;
                }
            }
        }
        self.set_runtime_state("verifying");
        let _ = app.emit(
            "local-ai://runtime-status",
            RuntimeStatusEvent { state: "verifying" },
        );
        let model = model_path_for_runtime(app).await?;
        let executable = runtime_binary_path(app)?;
        let port = random_loopback_port()?;
        let api_key = random_secret();
        let base_url = format!("http://127.0.0.1:{port}");

        let mut command = Command::new(&executable);
        command
            .arg("--model")
            .arg(&model)
            .arg("--host")
            .arg("127.0.0.1")
            .arg("--port")
            .arg(port.to_string())
            .arg("--api-key")
            .arg(&api_key)
            .arg("--alias")
            .arg(MODEL_ID)
            .arg("--ctx-size")
            .arg("4096")
            .arg("--parallel")
            .arg("1")
            .arg("--jinja")
            .arg("--reasoning")
            .arg("off")
            .arg("--reasoning-format")
            .arg("none")
            .arg("--no-slots")
            .arg("--no-webui")
            .arg("--offline")
            .arg("--log-disable")
            .current_dir(
                executable
                    .parent()
                    .ok_or_else(|| "local_ai_runtime_missing".to_string())?,
            )
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .kill_on_drop(true);
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            command.as_std_mut().creation_flags(0x0800_0000);
        }
        let child = command
            .spawn()
            .map_err(|_| "local_ai_runtime_start_failed".to_string())?;
        let connection = RuntimeConnection { base_url, api_key };
        let mut process = RuntimeProcess {
            child,
            connection: connection.clone(),
        };
        self.set_runtime_state("loading");
        let _ = app.emit(
            "local-ai://runtime-status",
            RuntimeStatusEvent { state: "loading" },
        );
        if let Err(error) = wait_until_ready(&mut process).await {
            let _ = process.child.kill().await;
            let _ = process.child.wait().await;
            self.set_runtime_state("error");
            return Err(error);
        }
        *runtime = Some(process);
        self.set_runtime_state("ready");
        let _ = app.emit(
            "local-ai://runtime-status",
            RuntimeStatusEvent { state: "ready" },
        );
        Ok(connection)
    }

    fn set_snapshot(&self, status: LocalAiPackStatus) {
        if let Ok(mut snapshot) = self.inner.snapshot.lock() {
            *snapshot = status;
        }
    }

    fn set_runtime_state(&self, state: &str) {
        if let Ok(mut snapshot) = self.inner.snapshot.lock() {
            snapshot.runtime_state = state.into();
        }
    }

    fn update_install_state(&self, app: &tauri::AppHandle, state: &str, downloaded: Option<u64>) {
        let status = {
            let Ok(mut snapshot) = self.inner.snapshot.lock() else {
                return;
            };
            snapshot.state = state.into();
            if let Some(downloaded) = downloaded {
                snapshot.downloaded_bytes = downloaded;
            }
            snapshot.clone()
        };
        self.emit_progress(app, &status);
    }

    fn emit_progress(&self, app: &tauri::AppHandle, status: &LocalAiPackStatus) {
        let _ = app.emit(
            "local-ai://pack-progress",
            PackProgressEvent {
                model_id: MODEL_ID,
                state: status.state.clone(),
                downloaded_bytes: status.downloaded_bytes,
                expected_size_bytes: MODEL_SIZE_BYTES,
            },
        );
    }
}

struct InstallRunningGuard(Arc<Inner>);

impl Drop for InstallRunningGuard {
    fn drop(&mut self) {
        self.0.install_running.store(false, Ordering::SeqCst);
        self.0.install_cancelled.store(false, Ordering::SeqCst);
    }
}

struct ActiveChatGuard(Arc<Inner>);

impl Drop for ActiveChatGuard {
    fn drop(&mut self) {
        if let Ok(mut active) = self.0.active_chat.lock() {
            *active = None;
        }
    }
}

struct PackPaths {
    directory: PathBuf,
    model: PathBuf,
    part: PathBuf,
    marker: PathBuf,
    marker_tmp: PathBuf,
}

impl PackPaths {
    fn from_app(app: &tauri::AppHandle) -> Result<Self, String> {
        let directory = app
            .path()
            .app_local_data_dir()
            .map_err(|_| "local_ai_storage_unavailable".to_string())?
            .join("models");
        Ok(Self {
            model: directory.join(MODEL_FILE),
            part: directory.join(PART_FILE),
            marker: directory.join(MARKER_FILE),
            marker_tmp: directory.join(format!("{MARKER_FILE}.tmp")),
            directory,
        })
    }
}

fn default_max_tokens() -> u32 {
    DEFAULT_MAX_TOKENS
}

fn unavailable_status() -> LocalAiPackStatus {
    LocalAiPackStatus {
        model_id: MODEL_ID,
        installed: false,
        size_bytes: None,
        expected_size_bytes: MODEL_SIZE_BYTES,
        downloaded_bytes: 0,
        state: "unavailable".into(),
        runtime_available: false,
        runtime_state: "unavailable".into(),
    }
}

fn pinned_install_metadata(paths: &PackPaths) -> Result<Option<u64>, String> {
    let metadata = match std_fs::metadata(&paths.model) {
        Ok(metadata) if metadata.is_file() => metadata,
        Ok(_) => return Err("local_ai_model_invalid".into()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err("local_ai_storage_unavailable".into()),
    };
    if metadata.len() != MODEL_SIZE_BYTES {
        return Err("local_ai_model_invalid".into());
    }
    let marker: VerificationMarker = match std_fs::read(&paths.marker) {
        Ok(bytes) if bytes.len() <= 2_048 => {
            serde_json::from_slice(&bytes).map_err(|_| "local_ai_model_invalid".to_string())?
        }
        Ok(_) => return Err("local_ai_model_invalid".into()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err("local_ai_storage_unavailable".into()),
    };
    if marker.is_pinned() {
        Ok(Some(metadata.len()))
    } else {
        Err("local_ai_model_invalid".into())
    }
}

async fn model_path_for_runtime(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    #[cfg(debug_assertions)]
    if let Some(path) = debug_model_override() {
        let metadata = fs::metadata(&path)
            .await
            .map_err(|_| "local_ai_model_missing".to_string())?;
        if metadata.is_file() && metadata.len() > 0 {
            return Ok(path);
        }
        return Err("local_ai_model_invalid".into());
    }

    let paths = PackPaths::from_app(app)?;
    if pinned_install_metadata(&paths)? != Some(MODEL_SIZE_BYTES) {
        return Err("local_ai_model_missing".into());
    }
    if !verify_sha256(paths.model.clone()).await? {
        remove_if_exists(&paths.marker).await?;
        return Err("local_ai_model_hash_mismatch".into());
    }
    Ok(paths.model)
}

#[cfg(debug_assertions)]
fn debug_model_override() -> Option<PathBuf> {
    std::env::var_os("POMP_LOCAL_AI_MODEL_PATH")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

#[cfg(debug_assertions)]
fn runtime_binary_name() -> &'static str {
    #[cfg(target_os = "windows")]
    {
        "llama-server.exe"
    }
    #[cfg(not(target_os = "windows"))]
    {
        "llama-server"
    }
}

fn runtime_relative_path() -> Result<PathBuf, String> {
    #[cfg(target_os = "macos")]
    {
        return Ok(PathBuf::from("runtime/macos-universal/llama-server"));
    }
    #[cfg(target_os = "windows")]
    {
        return Ok(PathBuf::from("runtime/windows-x64/llama-server.exe"));
    }
    #[allow(unreachable_code)]
    Err("local_ai_runtime_unsupported".into())
}

fn runtime_binary_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    #[cfg(debug_assertions)]
    if let Some(directory) = std::env::var_os("POMP_LOCAL_AI_RUNTIME_DIR")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
    {
        let candidate = directory.join(runtime_binary_name());
        if is_executable_file(&candidate) {
            return Ok(candidate);
        }
        return Err("local_ai_runtime_missing".into());
    }

    let relative = runtime_relative_path()?;
    if let Ok(resource_dir) = app.path().resource_dir() {
        let candidate = resource_dir.join(&relative);
        if is_executable_file(&candidate) {
            return Ok(candidate);
        }
    }
    #[cfg(debug_assertions)]
    {
        let candidate = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(relative);
        if is_executable_file(&candidate) {
            return Ok(candidate);
        }
    }
    Err("local_ai_runtime_missing".into())
}

fn is_executable_file(path: &Path) -> bool {
    std_fs::metadata(path).is_ok_and(|metadata| metadata.is_file() && metadata.len() > 0)
}

fn download_client() -> Result<Client, String> {
    Client::builder()
        .https_only(true)
        .redirect(reqwest::redirect::Policy::limited(5))
        .connect_timeout(Duration::from_secs(20))
        .read_timeout(Duration::from_secs(90))
        .timeout(Duration::from_secs(60 * 60))
        .user_agent(concat!("Pomp-HSK-AI-Desktop/", env!("CARGO_PKG_VERSION")))
        .build()
        .map_err(|_| "local_ai_download_unavailable".into())
}

fn runtime_client(timeout: Duration) -> Result<Client, String> {
    Client::builder()
        .no_proxy()
        .redirect(reqwest::redirect::Policy::none())
        .connect_timeout(Duration::from_secs(2))
        .timeout(timeout)
        .build()
        .map_err(|_| "local_ai_runtime_unavailable".into())
}

fn validate_content_range(headers: &header::HeaderMap, expected_start: u64) -> Result<(), String> {
    let value = headers
        .get(header::CONTENT_RANGE)
        .and_then(|value| value.to_str().ok())
        .ok_or_else(|| "local_ai_download_resume_failed".to_string())?;
    let value = value
        .strip_prefix("bytes ")
        .ok_or_else(|| "local_ai_download_resume_failed".to_string())?;
    let (range, total) = value
        .split_once('/')
        .ok_or_else(|| "local_ai_download_resume_failed".to_string())?;
    let (start, end) = range
        .split_once('-')
        .ok_or_else(|| "local_ai_download_resume_failed".to_string())?;
    let start = start
        .parse::<u64>()
        .map_err(|_| "local_ai_download_resume_failed".to_string())?;
    let end = end
        .parse::<u64>()
        .map_err(|_| "local_ai_download_resume_failed".to_string())?;
    let total = total
        .parse::<u64>()
        .map_err(|_| "local_ai_download_resume_failed".to_string())?;
    if start != expected_start
        || end < start
        || end >= MODEL_SIZE_BYTES
        || total != MODEL_SIZE_BYTES
    {
        return Err("local_ai_download_resume_failed".into());
    }
    Ok(())
}

async fn file_size(path: &Path) -> Option<u64> {
    fs::metadata(path)
        .await
        .ok()
        .filter(|metadata| metadata.is_file())
        .map(|metadata| metadata.len())
}

async fn remove_if_exists(path: &Path) -> Result<(), String> {
    match fs::remove_file(path).await {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(_) => Err("local_ai_storage_unavailable".into()),
    }
}

async fn verify_sha256(path: PathBuf) -> Result<bool, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let mut file =
            std_fs::File::open(path).map_err(|_| "local_ai_storage_unavailable".to_string())?;
        let mut hasher = Sha256::new();
        let mut buffer = vec![0_u8; 1024 * 1024];
        loop {
            let read = file
                .read(&mut buffer)
                .map_err(|_| "local_ai_storage_unavailable".to_string())?;
            if read == 0 {
                break;
            }
            hasher.update(&buffer[..read]);
        }
        let actual = format!("{:x}", hasher.finalize());
        Ok(actual == MODEL_SHA256)
    })
    .await
    .map_err(|_| "local_ai_verification_failed".to_string())?
}

async fn write_marker(paths: &PackPaths) -> Result<(), String> {
    let bytes = serde_json::to_vec(&VerificationMarker::pinned())
        .map_err(|_| "local_ai_verification_failed".to_string())?;
    let marker_tmp = paths.marker_tmp.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let mut output = std_fs::OpenOptions::new()
            .create(true)
            .truncate(true)
            .write(true)
            .open(&marker_tmp)
            .map_err(|_| "local_ai_storage_unavailable".to_string())?;
        output
            .write_all(&bytes)
            .and_then(|_| output.sync_all())
            .map_err(|_| "local_ai_storage_unavailable".to_string())
    })
    .await
    .map_err(|_| "local_ai_storage_unavailable".to_string())??;
    remove_if_exists(&paths.marker).await?;
    fs::rename(&paths.marker_tmp, &paths.marker)
        .await
        .map_err(|_| "local_ai_storage_unavailable".to_string())
}

fn random_loopback_port() -> Result<u16, String> {
    let listener = TcpListener::bind(("127.0.0.1", 0))
        .map_err(|_| "local_ai_runtime_start_failed".to_string())?;
    let port = listener
        .local_addr()
        .map_err(|_| "local_ai_runtime_start_failed".to_string())?
        .port();
    drop(listener);
    Ok(port)
}

fn random_secret() -> String {
    let mut bytes = [0_u8; 32];
    OsRng.fill_bytes(&mut bytes);
    URL_SAFE_NO_PAD.encode(bytes)
}

async fn wait_until_ready(process: &mut RuntimeProcess) -> Result<(), String> {
    let client = runtime_client(Duration::from_secs(4))?;
    let deadline = Instant::now() + RUNTIME_START_TIMEOUT;
    loop {
        if process
            .child
            .try_wait()
            .map_err(|_| "local_ai_runtime_start_failed".to_string())?
            .is_some()
        {
            return Err("local_ai_runtime_start_failed".into());
        }
        let response = client
            .get(format!("{}/health", process.connection.base_url))
            .bearer_auth(&process.connection.api_key)
            .send()
            .await;
        if response.is_ok_and(|response| response.status().is_success()) {
            return Ok(());
        }
        if Instant::now() >= deadline {
            return Err("local_ai_runtime_timeout".into());
        }
        tokio::time::sleep(Duration::from_millis(250)).await;
    }
}

fn validate_request_id(value: &str) -> Result<(), String> {
    if !(16..=80).contains(&value.len())
        || !value
            .bytes()
            .next()
            .is_some_and(|byte| byte.is_ascii_alphanumeric())
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b':' | b'-'))
    {
        return Err("local_ai_request_invalid".into());
    }
    Ok(())
}

fn valid_text(value: &str, max_chars: usize, max_bytes: usize) -> bool {
    let value = value.trim();
    !value.is_empty()
        && value.len() <= max_bytes
        && value.chars().count() <= max_chars
        && !value
            .chars()
            .any(|value| value.is_control() && !matches!(value, '\n' | '\r' | '\t'))
}

fn validate_chat_request(request: &LocalAiChatRequest) -> Result<(), String> {
    validate_request_id(&request.request_id)?;
    if !valid_text(&request.prompt, MAX_PROMPT_CHARS, MAX_PROMPT_BYTES)
        || !matches!(
            request.language.trim().to_ascii_lowercase().as_str(),
            "uz" | "ru" | "tj"
        )
        || request.history.len() > MAX_HISTORY_MESSAGES
        || !(1..=MAX_OUTPUT_TOKENS).contains(&request.max_tokens)
    {
        return Err("local_ai_request_invalid".into());
    }
    let mut history_bytes = 0_usize;
    for message in &request.history {
        if !matches!(message.role.as_str(), "user" | "assistant")
            || !valid_text(&message.content, 8_000, 16 * 1024)
        {
            return Err("local_ai_request_invalid".into());
        }
        history_bytes = history_bytes
            .checked_add(message.content.len())
            .ok_or_else(|| "local_ai_request_invalid".to_string())?;
    }
    if history_bytes > MAX_HISTORY_BYTES {
        return Err("local_ai_request_invalid".into());
    }
    Ok(())
}

fn system_prompt(language: &str) -> &'static str {
    match language.trim().to_ascii_lowercase().as_str() {
        "ru" => "Ты офлайн-наставник HSK AI по китайскому языку. Отвечай кратко и точно на русском. Для учебных примеров показывай иероглифы, пиньинь и перевод. Не утверждай, что у тебя есть интернет, и не выдумывай актуальные данные.",
        "tj" => "Ту мураббии офлайнии HSK AI барои забони чинӣ ҳастӣ. Ба тоҷикӣ кӯтоҳ ва дақиқ ҷавоб деҳ. Дар мисолҳои омӯзишӣ иероглиф, пинйин ва тарҷумаро нишон деҳ. Дастрасӣ ба интернетро даъво накун ва маълумоти ҷориро бофта набарор.",
        _ => "Sen HSK AI ilovasidagi xitoy tili bo‘yicha offline ustozsan. O‘zbek tilida qisqa va aniq javob ber. O‘quv misollarida iyeroglif, pinyin va tarjimani ko‘rsat. Internet borligini da’vo qilma va dolzarb ma’lumotni uydirma.",
    }
}

async fn stream_chat(
    app: &tauri::AppHandle,
    connection: &RuntimeConnection,
    request: &LocalAiChatRequest,
    cancelled: Arc<AtomicBool>,
) -> Result<String, String> {
    let mut messages = Vec::with_capacity(request.history.len() + 2);
    messages.push(json!({"role": "system", "content": system_prompt(&request.language)}));
    for message in &request.history {
        messages.push(json!({"role": message.role, "content": message.content}));
    }
    messages.push(json!({
        "role": "user",
        "content": format!("/no_think\n{}", request.prompt.trim()),
    }));
    let payload = json!({
        "model": MODEL_ID,
        "messages": messages,
        "stream": true,
        "max_tokens": request.max_tokens,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "min_p": 0.0,
        "presence_penalty": 1.5,
        "reasoning_effort": "none",
        "chat_template_kwargs": {"enable_thinking": false},
    });
    let client = runtime_client(CHAT_TIMEOUT)?;
    let mut response = client
        .post(format!("{}/v1/chat/completions", connection.base_url))
        .bearer_auth(&connection.api_key)
        .json(&payload)
        .send()
        .await
        .map_err(|_| "local_ai_runtime_unavailable".to_string())?;
    if !response.status().is_success() {
        return Err("local_ai_generation_failed".into());
    }

    let mut pending = Vec::<u8>::new();
    let mut output = String::new();
    loop {
        if cancelled.load(Ordering::SeqCst) {
            return Err("local_ai_chat_cancelled".into());
        }
        let chunk = tokio::select! {
            chunk = response.chunk() => chunk
                .map_err(|_| "local_ai_generation_failed".to_string())?,
            _ = tokio::time::sleep(Duration::from_millis(50)) => continue,
        };
        let Some(chunk) = chunk else {
            break;
        };
        pending.extend_from_slice(&chunk);
        while let Some((event_end, separator_len)) = find_sse_separator(&pending) {
            let event = pending.drain(..event_end).collect::<Vec<_>>();
            pending.drain(..separator_len);
            let done = process_sse_event(app, &request.request_id, &event, &mut output)?;
            if done {
                return finish_generated_output(output);
            }
        }
        if pending.len() > 256 * 1024 {
            return Err("local_ai_generation_failed".into());
        }
    }
    if !pending.is_empty() {
        let _ = process_sse_event(app, &request.request_id, &pending, &mut output)?;
    }
    finish_generated_output(output)
}

fn finish_generated_output(output: String) -> Result<String, String> {
    if output.trim().is_empty() {
        return Err("local_ai_generation_empty".into());
    }
    Ok(output)
}

fn find_sse_separator(value: &[u8]) -> Option<(usize, usize)> {
    value
        .windows(4)
        .position(|window| window == b"\r\n\r\n")
        .map(|position| (position, 4))
        .or_else(|| {
            value
                .windows(2)
                .position(|window| window == b"\n\n")
                .map(|position| (position, 2))
        })
}

fn process_sse_event(
    app: &tauri::AppHandle,
    request_id: &str,
    bytes: &[u8],
    output: &mut String,
) -> Result<bool, String> {
    let event = std::str::from_utf8(bytes).map_err(|_| "local_ai_generation_failed".to_string())?;
    for line in event.lines() {
        let Some(data) = line.strip_prefix("data:") else {
            continue;
        };
        let data = data.trim_start();
        if data == "[DONE]" {
            return Ok(true);
        }
        let value: Value =
            serde_json::from_str(data).map_err(|_| "local_ai_generation_failed".to_string())?;
        if let Some(delta) = value
            .pointer("/choices/0/delta/content")
            .and_then(Value::as_str)
            .filter(|value| !value.is_empty())
        {
            if output.len().saturating_add(delta.len()) > MAX_OUTPUT_BYTES {
                return Err("local_ai_output_too_large".into());
            }
            output.push_str(delta);
            let _ = app.emit(
                "local-ai://chat-delta",
                ChatDeltaEvent { request_id, delta },
            );
        }
    }
    Ok(false)
}

fn duration_ms(duration: Duration) -> u64 {
    duration.as_millis().min(u128::from(u64::MAX)) as u64
}

fn emit_error(app: &tauri::AppHandle, operation: &str, error: &str) {
    let _ = app.emit("local-ai://error", LocalAiErrorEvent { operation, error });
}

#[cfg(test)]
mod tests {
    use super::{
        find_sse_separator, finish_generated_output, unavailable_status, validate_chat_request,
        validate_content_range, LocalAiChatMessage, LocalAiChatRequest, VerificationMarker,
        MODEL_REVISION, MODEL_SHA256, MODEL_SIZE_BYTES,
    };
    use reqwest::header::{HeaderMap, HeaderValue, CONTENT_RANGE};
    use serde_json::json;

    fn request() -> LocalAiChatRequest {
        LocalAiChatRequest {
            request_id: "desktop-ai-test-0001".into(),
            prompt: "你好 nimani anglatadi?".into(),
            language: "uz".into(),
            history: vec![LocalAiChatMessage {
                role: "assistant".into(),
                content: "Salom".into(),
            }],
            max_tokens: 256,
        }
    }

    #[test]
    fn pinned_model_contract_cannot_drift_silently() {
        let marker = VerificationMarker::pinned();
        assert!(marker.is_pinned());
        assert_eq!(marker.revision, MODEL_REVISION);
        assert_eq!(marker.size_bytes, MODEL_SIZE_BYTES);
        assert_eq!(marker.sha256, MODEL_SHA256);
    }

    #[test]
    fn chat_input_is_strictly_bounded() {
        assert!(validate_chat_request(&request()).is_ok());
        let mut invalid = request();
        invalid.history[0].role = "system".into();
        assert!(validate_chat_request(&invalid).is_err());
        let mut invalid = request();
        invalid.prompt = "x".repeat(16_385);
        assert!(validate_chat_request(&invalid).is_err());
        let mut invalid = request();
        invalid.request_id = "short".into();
        assert!(validate_chat_request(&invalid).is_err());
    }

    #[test]
    fn tauri_chat_and_status_contracts_use_camel_case() {
        let parsed: LocalAiChatRequest = serde_json::from_value(json!({
            "requestId": "desktop-ai-contract-0001",
            "prompt": "你好",
            "language": "uz",
            "history": [{"role": "user", "content": "Salom"}],
            "maxTokens": 128
        }))
        .expect("camelCase request must deserialize");
        assert!(validate_chat_request(&parsed).is_ok());
        assert!(serde_json::from_value::<LocalAiChatRequest>(json!({
            "requestId": "desktop-ai-contract-0002",
            "prompt": "你好",
            "language": "uz",
            "history": [],
            "maxTokens": 128,
            "promptBody": "must be rejected"
        }))
        .is_err());

        let status = serde_json::to_value(unavailable_status()).expect("status must serialize");
        assert_eq!(status["modelId"], "qwen3-4b-q4-k-m");
        assert_eq!(status["expectedSizeBytes"], MODEL_SIZE_BYTES);
        assert_eq!(status["runtimeAvailable"], false);
        assert_eq!(status["runtimeState"], "unavailable");
        assert!(status.get("expected_size_bytes").is_none());
    }

    #[test]
    fn resumable_download_requires_exact_content_range() {
        let mut headers = HeaderMap::new();
        headers.insert(
            CONTENT_RANGE,
            HeaderValue::from_str(&format!("bytes 100-999/{MODEL_SIZE_BYTES}"))
                .expect("content range"),
        );
        assert!(validate_content_range(&headers, 100).is_ok());
        assert!(validate_content_range(&headers, 101).is_err());
        headers.insert(
            CONTENT_RANGE,
            HeaderValue::from_static("bytes 100-999/999999"),
        );
        assert!(validate_content_range(&headers, 100).is_err());
    }

    #[test]
    fn sse_frames_support_lf_and_crlf() {
        assert_eq!(find_sse_separator(b"data: {}\n\nmore"), Some((8, 2)));
        assert_eq!(find_sse_separator(b"data: {}\r\n\r\nmore"), Some((8, 4)));
    }

    #[test]
    fn completed_generation_rejects_blank_output() {
        assert_eq!(
            finish_generated_output(" \n\t".into()),
            Err("local_ai_generation_empty".into())
        );
        assert_eq!(
            finish_generated_output("你好 · nǐ hǎo · salom".into()),
            Ok("你好 · nǐ hǎo · salom".into())
        );
    }

    #[test]
    fn release_workflow_pins_verified_llama_cpp_assets() {
        let workflow = include_str!("../../../.github/workflows/desktop-release.yml");
        for contract in [
            "LLAMA_CPP_RELEASE: b10223",
            "LLAMA_CPP_COMMIT: 11924d4c17abc27383376a1ac6a24fa3e36c1c0c",
            "MACOS_DEPLOYMENT_TARGET: \"13.3\"",
            "-DCMAKE_OSX_DEPLOYMENT_TARGET=\"$MACOS_DEPLOYMENT_TARGET\"",
            "-DLLAMA_BUILD_NUMBER=\"${LLAMA_CPP_RELEASE#b}\"",
            "awk '/^ *minos / { print $2 }'",
            "d5488dd5759f7a086852af5a206c6cded875c716de6a9f9d8460ea6c2dc24138",
            "74c1ded0512818d98b51940bf9150e16da8ed79cf0cbe8d85788e01cdd00ff67",
            "shasum -a 256 -c -",
            "Get-FileHash $archive -Algorithm SHA256",
            "runtime/macos-universal",
            "runtime/windows-x64",
            "libggml-metal.*.dylib",
            "otool -L \"$x64_server\"",
            "lipo \"$runtime/llama-server\" -verify_arch arm64 x86_64",
        ] {
            assert!(
                workflow.contains(contract),
                "missing workflow contract: {contract}"
            );
        }
    }
}
