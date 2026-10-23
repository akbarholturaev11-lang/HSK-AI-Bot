#!/usr/bin/env python3
"""Validate the actual Play release artifacts, without signing or publishing.

Signatures are checked separately by android-play-preflight.yml. bundletool is
the official AAB validator; the byte-level ELF/ZIP checks below also catch a
transitive SDK regressing 16 KB support. No Android/third-party Python packages
are needed. https://developer.android.com/guide/practices/page-sizes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ANDROID = "{http://schemas.android.com/apk/res/android}"
PAGE_SIZE = 16_384
# Official google/bundletool 1.18.3 release asset, pinned before execution.
BUNDLETOOL_SHA256 = "a099cfa1543f55593bc2ed16a70a7c67fe54b1747bb7301f37fdfd6d91028e29"
FORBIDDEN_PERMISSIONS = {
    "android.permission.REQUEST_INSTALL_PACKAGES",
    "android.permission.INSTALL_PACKAGES",
    "com.android.vending.BILLING",  # Current Play release is consumption-only.
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def run(*command: str) -> str:
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)


def manifest_facts(source: str) -> dict:
    manifest = ET.fromstring(source)
    application = manifest.find("application")
    sdk = manifest.find("uses-sdk")
    require(application is not None and sdk is not None, "AAB manifest is incomplete")
    permissions = sorted(
        item.attrib[ANDROID + "name"]
        for item in manifest
        if item.tag in {"uses-permission", "uses-permission-sdk-23"}
    )
    facts = {
        "package": manifest.attrib.get("package"),
        "version_code": int(manifest.attrib.get(ANDROID + "versionCode", "0")),
        "version_name": manifest.attrib.get(ANDROID + "versionName", ""),
        "min_sdk": int(sdk.attrib.get(ANDROID + "minSdkVersion", "0")),
        "target_sdk": int(sdk.attrib.get(ANDROID + "targetSdkVersion", "0")),
        "permissions": permissions,
    }
    require(facts["package"] == "com.pomp.hskai", "Wrong release applicationId")
    require(0 < facts["version_code"] <= 2_100_000_000, "Invalid release versionCode")
    require(bool(facts["version_name"]) and not re.search(
        r"(?:debug|qa)", facts["version_name"], re.I
    ), "A debug/QA version must not be submitted")
    require(facts["min_sdk"] == 26 and facts["target_sdk"] >= 36, "Unexpected release SDK contract")
    require(application.attrib.get(ANDROID + "allowBackup") == "false", "Release backup must be disabled")
    for name in ("debuggable", "testOnly", "usesCleartextTraffic"):
        require(application.attrib.get(ANDROID + name, "false") == "false", f"Unsafe release flag: {name}")
    require(not FORBIDDEN_PERMISSIONS.intersection(permissions), "Play includes an install or billing permission")
    require(not any(item.tag == "instrumentation" for item in manifest), "Release includes test instrumentation")
    return facts


def check_apk_manifest(badging: str, tree: str, facts: dict) -> None:
    package = re.search(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", badging, re.M)
    require(package is not None, "Cannot read APK package metadata")
    require(package.groups() == (facts["package"], str(facts["version_code"]), facts["version_name"]),
            "Play APK and AAB package/version differ")
    for key, label in (("min_sdk", "(?:minSdkVersion|sdkVersion)"), ("target_sdk", "targetSdkVersion")):
        require(bool(re.search(rf"(?m)^{label}:'{facts[key]}'$", badging)), f"APK/AAB {key} differ")
    require("application-debuggable" not in badging and "testOnly" not in badging,
            "APK is debuggable or test-only")
    require(not any(permission in tree for permission in FORBIDDEN_PERMISSIONS),
            "Play APK includes an install or billing permission")
    # Read only the application's own attributes, before its first child.
    application = re.search(r"(?m)^(\s*)E: application\b.*\n", tree)
    require(application is not None, "Cannot read APK application manifest")
    attributes = tree[application.end():].split("E:", 1)[0]
    for name in ("allowBackup", "debuggable", "testOnly", "usesCleartextTraffic"):
        value = re.search(rf"android:{name}(?:\([^)]*\))?=(.*)", attributes)
        if value is None:
            require(name != "allowBackup", "APK must explicitly disable backup")
        else:
            require(bool(re.fullmatch(r"(?:\(type 0x12\))?0x0\s*|false\s*", value.group(1))),
                    f"Unsafe APK flag: {name}")


def check_elf(data: bytes, name: str) -> None:
    require(len(data) >= 52 and data[:4] == b"\x7fELF", f"Invalid ELF: {name}")
    elf_class, byte_order = data[4:6]
    require(elf_class in (1, 2) and byte_order in (1, 2), f"Unsupported ELF header: {name}")
    endian = "<" if byte_order == 1 else ">"
    is64 = elf_class == 2
    require(len(data) >= (64 if is64 else 52), f"Truncated ELF header: {name}")
    offset = struct.unpack_from(endian + ("Q" if is64 else "I"), data, 32 if is64 else 28)[0]
    size, count = struct.unpack_from(endian + "HH", data, 54 if is64 else 42)
    require(size >= (56 if is64 else 32) and count > 0 and offset + size * count <= len(data),
            f"Invalid ELF program headers: {name}")
    loads = 0
    for index in range(count):
        start = offset + size * index
        if struct.unpack_from(endian + "I", data, start)[0] != 1:  # PT_LOAD
            continue
        loads += 1
        if is64:
            file_offset, address = struct.unpack_from(endian + "QQ", data, start + 8)
            alignment = struct.unpack_from(endian + "Q", data, start + 48)[0]
        else:
            file_offset, address = struct.unpack_from(endian + "II", data, start + 4)
            alignment = struct.unpack_from(endian + "I", data, start + 28)[0]
        require(alignment >= PAGE_SIZE and alignment & (alignment - 1) == 0,
                f"ELF LOAD alignment below 16 KB: {name}")
        require(file_offset % PAGE_SIZE == address % PAGE_SIZE,
                f"ELF LOAD offset/address mismatch for 16 KB: {name}")
    require(loads > 0, f"ELF has no LOAD segments: {name}")


def check_native_libraries(path: Path, *, apk: bool) -> list[str]:
    names = []
    with zipfile.ZipFile(path) as archive, path.open("rb") as raw:
        require(archive.testzip() is None, f"Corrupt artifact ZIP: {path.name}")
        for entry in archive.infolist():
            if not entry.filename.endswith(".so"):
                continue
            check_elf(archive.read(entry), entry.filename)
            names.append(entry.filename.removeprefix("base/"))
            if apk and entry.compress_type == zipfile.ZIP_STORED:
                raw.seek(entry.header_offset)
                header = raw.read(30)
                require(header[:4] == b"PK\x03\x04", f"Invalid ZIP header: {entry.filename}")
                filename_size, extra_size = struct.unpack_from("<HH", header, 26)
                data_offset = entry.header_offset + 30 + filename_size + extra_size
                require(data_offset % PAGE_SIZE == 0, f"APK library not 16 KB ZIP aligned: {entry.filename}")
    return sorted(names)


def validate(apk: Path, aab: Path, aapt2: Path, bundletool: Path) -> dict:
    require(sha256(bundletool) == BUNDLETOOL_SHA256, "bundletool SHA-256 differs from pinned official release")
    bundle_command = ("java", "-jar", str(bundletool))
    run(*bundle_command, "validate", f"--bundle={aab}")
    facts = manifest_facts(run(*bundle_command, "dump", "manifest", f"--bundle={aab}"))
    check_apk_manifest(
        run(str(aapt2), "dump", "badging", str(apk)),
        run(str(aapt2), "dump", "xmltree", "--file", "AndroidManifest.xml", str(apk)),
        facts,
    )
    libraries = check_native_libraries(aab, apk=False)
    require(libraries == check_native_libraries(apk, apk=True), "APK/AAB native libraries differ")
    if libraries:
        config = json.loads(run(*bundle_command, "dump", "config", f"--bundle={aab}"))
        alignment = config.get("optimizations", {}).get("uncompressNativeLibraries", {}).get("alignment")
        require(alignment == "PAGE_ALIGNMENT_16K", "AAB must request PAGE_ALIGNMENT_16K")
    return {**facts, "native_libraries": libraries, "apk_sha256": sha256(apk), "aab_sha256": sha256(aab)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--aab", type=Path, required=True)
    parser.add_argument("--aapt2", type=Path, required=True)
    parser.add_argument("--bundletool", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.apk, args.aab, args.aapt2, args.bundletool)
    except (ValueError, OSError, ET.ParseError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        parser.exit(1, f"PLAY ARTIFACT ERROR: {error}\n")
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Play release artifacts: OK ({report['version_name']} / {report['version_code']}; "
          f"{len(report['native_libraries'])} native libraries support 16 KB)")


if __name__ == "__main__":
    main()
