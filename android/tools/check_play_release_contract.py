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
    bool(re.search(r'targetSdk\s*=\s*(3[5-9]|[4-9][0-9])\b', gradle)),
    "Review targetSdk: this Play candidate must target API 35 or newer.",
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
require(
    re.search(r'fun\s+SubscriptionCheckoutHost\([\s\S]*?\)\s*=\s*Unit', play_checkout)
    is not None,
    "Play is currently consumption-only: do not add an unreviewed checkout.",
)
require(
    "canSubscribe = false" in play_limit,
    "The Play limit screen must not offer the direct checkout.",
)
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
