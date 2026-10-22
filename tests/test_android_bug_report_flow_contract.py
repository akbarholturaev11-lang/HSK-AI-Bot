"""Regression guardrails for the Android shake-to-report UX and screenshot flow."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android/app/src/main/java/com/pomp/hskai"


class AndroidBugReportFlowContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (ANDROID / "MainActivity.kt").read_text(encoding="utf-8")
        cls.form = (ANDROID / "feature/feedback/BugReportDialog.kt").read_text(encoding="utf-8")
        cls.intro = (ANDROID / "feature/feedback/BugReportIntroSheet.kt").read_text(encoding="utf-8")
        cls.capture = (ANDROID / "feature/feedback/ReportScreenCapture.kt").read_text(encoding="utf-8")
        cls.profile = (ANDROID / "feature/profile/ProfileScreen.kt").read_text(encoding="utf-8")
        cls.assistant = (ANDROID / "feature/assistant/AssistantHost.kt").read_text(encoding="utf-8")

    def test_shake_confirmation_precedes_report_form(self):
        self.assertIn("bugReportIntroVisible = true", self.main)
        self.assertIn("BugReportIntroSheet(", self.main)
        self.assertIn("onContinue = {", self.main)
        self.assertIn("bugReportOpen = true", self.main)
        self.assertIn("ShakeToReport(", self.main)
        self.assertIn("enabled = shakeToReportEnabled &&", self.main)
        self.assertIn("onShakeChanged", self.intro)

    def test_initial_sheet_stays_visible_during_capture_and_has_fallback(self):
        self.assertLess(
            self.main.index("bugReportIntroVisible = true"),
            self.main.index("val snapshot = captureReportScreen(bugReportRootView)"),
        )
        self.assertIn("loading = bugReportCapturing", self.main)
        self.assertIn("enabled = !loading", self.intro)
        self.assertIn("CircularProgressIndicator(", self.intro)
        self.assertIn("if (!bugReportCapturing) {", self.main)
        self.assertIn("captureGeneration == introCaptureGeneration", self.main)
        self.assertIn("PixelCopy.request(", self.capture)
        self.assertIn("root.draw(canvas)", self.capture)
        self.assertIn("FLAG_SECURE", self.capture)
        self.assertIn("val screenshot = captureReportScreen(visibleDialogView)", self.profile)

    def test_existing_bug_report_defaults_screenshot_on_and_ai_report_defaults_off(self):
        self.assertIn('var attachScreenshot by remember(screen) { mutableStateOf(screen != "ai_assistant") }', self.form)
        self.assertIn("initialDescription: String = \"\"", self.form)
        self.assertIn("checked = attachScreenshot", self.form)
        self.assertIn("onCheckedChange", self.form)
        self.assertIn("screenshotDataUrl = encoded.orEmpty()", self.form)
        self.assertIn('picker.launch("image/*")', self.form)

    def test_success_requires_explicit_ok_and_closes_entire_report(self):
        self.assertIn("sent = response is ApiResult.Success && response.value.ok", self.form)
        self.assertIn("if (sent) {", self.form)
        self.assertIn("AlertDialog(", self.form)
        self.assertIn("R.string.bug_report_thanks_title", self.form)
        self.assertIn('Text("OK")', self.form)
        self.assertIn("Button(onClick = onDismiss", self.form)
        for locale in ("values", "values-ru", "values-tg"):
            strings = (ROOT / "android/app/src/main/res" / locale / "strings.xml").read_text(encoding="utf-8")
            self.assertIn('name="bug_report_thanks_title"', strings)

    def test_fixed_send_action_is_not_inside_scroll_column(self):
        scroll = self.form.index(".verticalScroll(rememberScrollState())")
        divider = self.form.index("HorizontalDivider(color = PompColors.Divider)")
        submit = self.form.index("enabled = !sent && description.trim().length >= 5 && !busy")
        self.assertLess(scroll, divider)
        self.assertLess(divider, submit)
        self.assertIn(".imePadding()", self.form)
        self.assertIn("SOFT_INPUT_ADJUST_RESIZE", self.form)


if __name__ == "__main__":
    unittest.main()
