"""Desktop request-load regressions.

The desktop app used to ask for the full course map every 60 seconds.  That
map performs progress locking plus multiple personalization/access queries, so
background notification polling must stay on the lightweight sync contract.
"""

import unittest
from pathlib import Path


APP = Path("desktop/ui/js/app.js").read_text(encoding="utf-8")
BRIDGE = Path("desktop/ui/js/bridge.js").read_text(encoding="utf-8")
RUST = Path("desktop/src-tauri/src/lib.rs").read_text(encoding="utf-8")


class DesktopRequestLoadTests(unittest.TestCase):
    def test_background_poll_is_five_minutes_and_uses_sync(self):
        self.assertIn("const NOTIFICATION_REFRESH_MS = 5 * 60_000;", APP)
        start = APP.index("function startNotificationRefresh()")
        end = APP.index("\nfunction stopNotificationRefresh()", start)
        body = APP[start:end]
        self.assertIn("refreshDesktopSync()", body)
        self.assertNotIn("courseMap()", body)

    def test_sync_is_suspended_while_hidden_or_in_a_lesson(self):
        start = APP.index("function desktopSyncAllowed()")
        end = APP.index("\n}", start) + 2
        body = APP[start:end]
        self.assertIn("!lesson.isOpen", body)
        self.assertIn('document.visibilityState !== "hidden"', body)
        self.assertIn("!dom.workspace.hidden", body)

    def test_focus_sync_is_deduped_and_lightweight(self):
        self.assertIn(
            "const NOTIFICATION_FOCUS_MIN_GAP_MS = 15_000;",
            APP,
        )
        self.assertIn(
            'window.addEventListener("focus", refreshDesktopSyncOnFocus)',
            APP,
        )
        self.assertIn("await desktopBridge.syncState()", APP)

    def test_full_map_runs_only_when_sync_detects_drift(self):
        start = APP.index("async function refreshDesktopSync(")
        end = APP.index("\nfunction refreshDesktopSyncOnFocus()", start)
        body = APP[start:end]
        self.assertIn("const mapChanged =", body)
        self.assertIn("if (mapChanged) {", body)
        self.assertIn("await loadCourseMap({ keepView: true });", body)

    def test_native_bridge_has_a_single_sync_command(self):
        self.assertIn('syncState: "desktop_sync"', BRIDGE)
        self.assertIn("syncState() {", BRIDGE)
        self.assertIn('async fn desktop_sync(', RUST)
        self.assertIn('authenticated_get_json(&state, "/api/v3/desktop/sync")', RUST)


if __name__ == "__main__":
    unittest.main()
