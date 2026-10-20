pub const DEFAULT_API_ORIGIN: &str = "https://telegram-chinese-bot-production.up.railway.app";

// Deliberately accept only canonical HTTPS DNS origins. No URL parsing
// ambiguity, credentials, port override, path, query or fragment is allowed.
pub fn is_valid_api_origin(value: &str) -> bool {
    let Some(host) = value.strip_prefix("https://") else {
        return false;
    };
    !host.is_empty()
        && host.len() <= 253
        && host.split('.').all(|label| {
            !label.is_empty()
                && label.len() <= 63
                && label.as_bytes()[0].is_ascii_alphanumeric()
                && label.as_bytes()[label.len() - 1].is_ascii_alphanumeric()
                && label
                    .bytes()
                    .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
        })
}

#[cfg(test)]
mod tests {
    use super::{is_valid_api_origin, DEFAULT_API_ORIGIN};

    #[test]
    fn build_origin_accepts_only_canonical_https_dns_origins() {
        assert!(is_valid_api_origin(DEFAULT_API_ORIGIN));
        assert!(is_valid_api_origin("https://hsk-qa.example.com"));
        for bad in [
            "",
            "http://qa.example",
            "https://qa.example/",
            "https://qa.example/path",
            "https://qa.example?token=secret",
            "https://qa.example#fragment",
            "https://user@qa.example",
            "https://user:pass@qa.example",
            "https://qa.example:443",
            "https://QA.example",
            "https://qa.example.",
            "https://qa..example",
            "https://-qa.example",
            "https://qa-.example",
            "https://qa.example\\evil",
            "https://qa.example\n",
            "https://[::1]",
            "https://é.example",
        ] {
            assert!(!is_valid_api_origin(bad));
        }
        assert!(!is_valid_api_origin(&format!(
            "https://{}.example",
            "x".repeat(64)
        )));
    }
}
