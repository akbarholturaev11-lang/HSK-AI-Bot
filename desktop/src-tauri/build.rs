#[path = "src/api_config.rs"]
mod api_config;

fn main() {
    println!("cargo:rerun-if-env-changed=POMP_API_ORIGIN");
    let origin =
        std::env::var("POMP_API_ORIGIN").unwrap_or_else(|_| api_config::DEFAULT_API_ORIGIN.into());
    assert!(api_config::is_valid_api_origin(&origin), "POMP_API_ORIGIN must be a canonical HTTPS origin without credentials, a port, path, query or fragment");
    println!("cargo:rerun-if-env-changed=TAURI_CONFIG");
    let overrides: serde_json::Value = std::env::var("TAURI_CONFIG")
        .ok()
        .and_then(|value| serde_json::from_str(&value).ok())
        .unwrap_or_default();
    let qa_id = overrides
        .get("identifier")
        .and_then(serde_json::Value::as_str)
        == Some("com.pomp.hskai.qa");
    let qa_scheme = overrides.pointer("/plugins/deep-link/desktop/schemes")
        == Some(&serde_json::json!(["pomp-hsk-ai-qa"]));
    if origin != api_config::DEFAULT_API_ORIGIN {
        assert!(
            qa_id && qa_scheme,
            "Nonproduction POMP_API_ORIGIN requires --config src-tauri/tauri.qa.conf.json"
        );
    } else {
        assert!(
            !qa_id && !qa_scheme,
            "The QA config requires a nonproduction POMP_API_ORIGIN"
        );
    }
    tauri_build::build()
}
