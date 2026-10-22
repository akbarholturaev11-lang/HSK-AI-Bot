#!/usr/bin/env python3
"""Static, secret-free preflight for keeping Play and sideload channels compatible.

This does not certify Play policy compliance. The signed-artifact workflow
checks the actual certificate and APK manifest before uploading an AAB.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANDROID = ROOT / "android"
APP = ANDROID / "app" / "src"
errors: list[str] = []


def read(path: Path) -> str:
    if not path.is_file():
        errors.append(f"Missing: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def require(works: bool, message: str) -> None:
    if not works:
        errors.append(message)


gradle = read(ANDROID / "app" / "build.gradle.kts")
main_manifest = read(APP / "main" / "AndroidManifest.xml")
direct_manifest = read(APP / "direct" / "AndroidManifest.xml")
play_manifest = (
    read(APP / "play" / "AndroidManifest.xml")
    if (APP / "play" / "AndroidManifest.xml").exists()
    else ""
)
play_checkout = read(
    APP / "play" / "java/com/pomp/hskai/feature/subscription/SubscriptionCheckoutHost.kt"
)
play_limit = read(
    APP / "play" / "java/com/pomp/hskai/feature/limit/LimitGateHost.kt"
)
play_update = read(
    APP / "play" / "java/com/pomp/hskai/feature/update/AppUpdateCard.kt"
)
course_screen = read(
    APP / "main" / "java/com/pomp/hskai/feature/course/CourseScreen.kt"
)
promo = read(
    APP / "main" / "java/com/pomp/hskai/feature/profile/ProfilePromoCarousel.kt"
)
assistant = read(
    APP / "main" / "java/com/pomp/hskai/feature/assistant/AssistantHost.kt"
)
feedback_dialog = read(
    APP / "main" / "java/com/pomp/hskai/feature/feedback/BugReportDialog.kt"
)
activity = read(APP / "main" / "java/com/pomp/hskai/MainActivity.kt")
profile = read(
    APP / "main" / "java/com/pomp/hskai/feature/profile/ProfileScreen.kt"
)
public_site = read(ROOT / "app/api/public_site.py")
release_workflow = read(ROOT / ".github/workflows/android-release.yml")
play_workflow = read(ROOT / ".github/workflows/android-play-preflight.yml")

require(
    bool(re.search(r'applicationId\s*=\s*"com\.pomp\.hskai"', gradle)),
    "Do not change com.pomp.hskai: installed direct APKs must be upgradeable.",
)
require(
    bool(re.search(r'versionCode\s*=\s*appVersionCode', gradle)),
    "Android must use the same versionCode for both distribution flavours.",
)
require(
    bool(re.search(r'val\s+appVersionCode\s*=\s*[1-9][0-9]*', gradle)),
    "A positive Android versionCode is required.",
)
require(
    bool(re.search(r'targetSdk\s*=\s*(3[6-9]|[4-9][0-9])\b', gradle)),
    "Review targetSdk: this 2026 Play candidate must target API 36 or newer.",
)
require(
    '"EXTERNAL_CHECKOUT_ENABLED", "false"' in gradle
    and '"DISTRIBUTION_CHANNEL", "\\"play\\""' in gradle,
    "The Play flavour must disable external checkout.",
)
require(
    '"EXTERNAL_CHECKOUT_ENABLED", "true"' in gradle
    and '"DISTRIBUTION_CHANNEL", "\\"direct\\""' in gradle,
    "Keep the direct APK as the separate sideload distribution.",
)
require(
    "REQUEST_INSTALL_PACKAGES" not in (main_manifest + play_manifest),
    "Play must never inherit the sideload APK install permission.",
)
require(
    "REQUEST_INSTALL_PACKAGES" in direct_manifest,
    "The direct APK's existing update mechanism must remain in its own flavour.",
)
# Keep the two channel entry points separate, but never require Play
# checkout to stay a no-op: it can later host Google Play Billing. Today's
# consumption-only behaviour is a product choice, NOT a permanent CI invariant.
require(
    "fun SubscriptionCheckoutHost(" in play_checkout,
    "The Play build must supply its own checkout host entry point.",
)
require(
    "fun rememberLimitGate(" in play_limit,
    "The Play build must supply its own limit gate entry point.",
)
# Both flavours must remain source-separated. check_flavor_parity.py catches
# signature drift when a future Play Billing implementation is introduced.
require(
    "Intentionally empty" in play_update,
    "Play must not provide a sideload update card.",
)
require(
    '"/privacy"' in profile
    and '"/account-deletion"' in profile
    and '@router.get("/privacy")' in public_site
    and '@router.get("/account-deletion")' in public_site,
    "Privacy and deletion links must be discoverable and routed.",
)
# Play consumption-only policy: avoid a price or purchase CTA anywhere the
# shared HSK 3.0 entry dialogs are rendered. Real entitlements still come from
# the common backend; future Play Billing must be implemented separately.
for label, source in (("course HSK 3.0 dialog", course_screen), ("profile HSK 3.0 promo", promo)):
    require(
        "BuildConfig.EXTERNAL_CHECKOUT_ENABLED" in source
        and "hsk30_play_access_status" in source,
        f"{label} must gate direct checkout wording and show status-only Play UI.",
    )
require(
    "reportTurn?.let" in assistant
    and "BugReportDialog(" in assistant
    and "assistant_report_answer" in assistant
    and 'screen = "ai_assistant"' in assistant,
    "AI answers need a visible in-app report action, linked to the feedback flow.",
)
require(
    "initialDescription: String" in feedback_dialog,
    "The AI content report must allow an explicit text-only submission.",
)
require(
    'if (BuildConfig.EXTERNAL_CHECKOUT_ENABLED && hsk30PaymentRejectionVisible)' in activity
    and 'BuildConfig.EXTERNAL_CHECKOUT_ENABLED &&\n                        decision.planType == "hsk30_unlock"' in activity,
    "Play must never show the manual-payment rejection and retry dialog.",
)
# Play source sets must not include direct APK updater mechanisms.
for path in (APP / "play").rglob("*.kt"):
    source = path.read_text(encoding="utf-8")
    require(
        "ACTION_INSTALL_PACKAGE" not in source
        and "REQUEST_INSTALL_PACKAGES" not in source
        and "SubscriptionCheckoutViewModel" not in source,
        f"Play source must not install sideload APKs or use the direct checkout: {path.relative_to(ROOT)}",
    )

match = re.search(r"(?m)^\s*RELEASE_CERT_SHA256:\s*([0-9a-f]{64})\s*$", release_workflow)
require(
    match is not None,
    "The direct release must pin a SHA-256 certificate fingerprint.",
)
require(
    "assemblePlayRelease" in play_workflow
    and "bundlePlayRelease" in play_workflow
    and "apksigner" in play_workflow
    and "jarsigner" in play_workflow
    and "RELEASE_CERT_SHA256" in play_workflow,
    "The Play preflight must build and verify both signed APK and AAB.",
)
if errors:
    for error in errors:
        print("PLAY PREFLIGHT ERROR:", error)
    raise SystemExit(1)

print("Play/direct static distribution contracts: OK")
print("Certificate pin present; run the manual Play preflight to check signed artifacts.")
print("Operator review still needed: Play signing setup, privacy, deletion, billing, testing.")
print("Play Billing may be added later without disabling the channel safety checks.")
