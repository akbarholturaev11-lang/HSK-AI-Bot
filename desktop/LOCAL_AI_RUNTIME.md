# Local AI runtime contract

HSK AI Desktop uses a pinned, optional local model and a bundled llama.cpp
runtime. User prompts and generated text stay between the desktop process and
the loopback-only runtime; analytics contain only an allowlisted event name,
random event ID, model ID, optional byte count, and optional duration.

## Pinned model

- Repository: `Qwen/Qwen3-4B-GGUF`
- Revision: `a9a60d009fa7ff9606305047c2bf77ac25dbec49`
- File: `Qwen3-4B-Q4_K_M.gguf`
- Size: `2497280256` bytes
- SHA-256: `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`

Installation is explicit, resumable, size-bounded, and accepted only after the
complete file matches the pinned SHA-256. The verified model lives under the
application-local data directory and is never embedded into the installer.

## Pinned runtime

- Project: `ggml-org/llama.cpp`
- Release: `b10223`
- Commit: `11924d4c17abc27383376a1ac6a24fa3e36c1c0c`

Release CI downloads only the pinned upstream assets, verifies their exact
SHA-256 digests, and then stages the runtime under Tauri resources. A developer
build intentionally remains valid without those binaries; in that case native
status reports `runtimeAvailable: false` and chat fails closed.

The runtime binds to a random `127.0.0.1` port, uses a random per-process API
key, disables its web UI and logs, and is terminated before updater restart or
normal application exit.

## Offline-auth boundary

This integration does not cache an authenticated bootstrap response. A safe
offline session needs a server-signed or locally integrity-protected,
expiry-bounded entitlement snapshot and matching UI states. Returning a stale
or editable bootstrap could incorrectly grant paid access, so that separate
auth/cache change remains intentionally fail-closed.
