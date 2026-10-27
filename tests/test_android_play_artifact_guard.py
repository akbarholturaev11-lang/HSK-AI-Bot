"""Exercise release-artifact failures with small, secret-free binary fixtures."""

import importlib.util
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "android/tools/check_play_artifacts.py"
SPEC = importlib.util.spec_from_file_location("play_artifacts", SCRIPT)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

MANIFEST = """<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.pomp.hskai" android:versionCode="53" android:versionName="1.7.22">
    <uses-sdk android:minSdkVersion="26" android:targetSdkVersion="36" />
    <uses-permission android:name="android.permission.INTERNET" />
    <application android:allowBackup="false" />
</manifest>"""
BADGING = """package: name='com.pomp.hskai' versionCode='53' versionName='1.7.22'
sdkVersion:'26'
targetSdkVersion:'36'
"""
TREE = """N: android=http://schemas.android.com/apk/res/android
  E: manifest (line=1)
    E: application (line=4)
      A: android:allowBackup(0x01010280)=(type 0x12)0x0
      E: activity (line=5)
"""


def bundle_config():
    return {"optimizations": {
        "splitsConfig": {"splitDimension": [
            {"value": "ABI"},
            {"value": "SCREEN_DENSITY"},
            {"value": "LANGUAGE", "negate": True},
        ]},
        "uncompressNativeLibraries": {"alignment": "PAGE_ALIGNMENT_16K"},
    }}


def elf(*, bits=64, alignment=guard.PAGE_SIZE, address=0, file_offset=0, endian="<"):
    data = bytearray(256)
    data[:7] = b"\x7fELF" + bytes((2 if bits == 64 else 1, 1 if endian == "<" else 2, 1))
    if bits == 64:
        struct.pack_into(endian + "Q", data, 32, 64)
        struct.pack_into(endian + "HH", data, 54, 56, 1)
        struct.pack_into(endian + "IIQQQQQQ", data, 64, 1, 5, file_offset, address, 0, 256, 256, alignment)
    else:
        struct.pack_into(endian + "I", data, 28, 52)
        struct.pack_into(endian + "HH", data, 42, 32, 1)
        struct.pack_into(endian + "IIIIIIII", data, 52, 1, file_offset, address, 0, 256, 256, 5, alignment)
    return bytes(data)


def native_zip(path, *, bundle=False, aligned=True, compressed=False, data=None):
    name = ("base/" if bundle else "") + "lib/arm64-v8a/libfixture.so"
    entry = zipfile.ZipInfo(name)
    entry.compress_type = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED
    if aligned:
        padding = guard.PAGE_SIZE - (30 + len(name.encode()))
        entry.extra = struct.pack("<HH", 0xFFFF, padding - 4) + bytes(padding - 4)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(entry, data if data is not None else elf())


class PlayManifestTests(unittest.TestCase):
    def test_production_manifest_is_accepted(self):
        facts = guard.manifest_facts(MANIFEST)
        guard.check_apk_manifest(BADGING, TREE, facts)
        guard.check_apk_manifest(BADGING.replace("sdkVersion:", "minSdkVersion:"), TREE, facts)
        self.assertEqual(facts["version_code"], 53)

    def test_unsafe_aab_manifests_are_rejected(self):
        mutations = {
            "wrong package": MANIFEST.replace("com.pomp.hskai", "com.pomp.hskai.debug"),
            "zero version": MANIFEST.replace('versionCode="53"', 'versionCode="0"'),
            "excessive version": MANIFEST.replace('versionCode="53"', 'versionCode="2100000001"'),
            "QA version": MANIFEST.replace('1.7.22', '1.7.22-qa'),
            "old target": MANIFEST.replace('targetSdkVersion="36"', 'targetSdkVersion="35"'),
            "backup": MANIFEST.replace('allowBackup="false"', 'allowBackup="true"'),
            "implicit backup": MANIFEST.replace('android:allowBackup="false"', ''),
            "debug": MANIFEST.replace('<application ', '<application android:debuggable="true" '),
            "test": MANIFEST.replace('<application ', '<application android:testOnly="true" '),
            "cleartext": MANIFEST.replace('<application ', '<application android:usesCleartextTraffic="true" '),
            "instrumentation": MANIFEST.replace('</manifest>', '<instrumentation /></manifest>'),
        }
        for label, source in mutations.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                guard.manifest_facts(source)
        for permission in guard.FORBIDDEN_PERMISSIONS:
            with self.subTest(permission=permission), self.assertRaises(ValueError):
                guard.manifest_facts(MANIFEST.replace("android.permission.INTERNET", permission))

    def test_apk_must_match_the_bundle_and_be_safe(self):
        facts = guard.manifest_facts(MANIFEST)
        cases = (
            (BADGING.replace("versionCode='53'", "versionCode='52'"), TREE),
            (BADGING.replace("targetSdkVersion:'36'", "targetSdkVersion:'35'"), TREE),
            (BADGING + "application-debuggable\n", TREE),
            (BADGING, TREE.replace("0x0", "0xffffffff")),
            (BADGING, TREE.replace("      A: android:allowBackup(0x01010280)=(type 0x12)0x0\n", "")),
            (BADGING, TREE.replace("      E: activity", "      A: android:debuggable(0x0101000f)=(type 0x12)0xffffffff\n      E: activity")),
            (BADGING, TREE + "android.permission.REQUEST_INSTALL_PACKAGES"),
        )
        for badging, tree in cases:
            with self.subTest(badging=badging, tree=tree), self.assertRaises(ValueError):
                guard.check_apk_manifest(badging, tree, facts)


class PlayNativeLibraryTests(unittest.TestCase):
    def test_both_elf_classes_and_byte_orders_work(self):
        for bits in (32, 64):
            for endian in ("<", ">"):
                with self.subTest(bits=bits, endian=endian):
                    guard.check_elf(elf(bits=bits, endian=endian), "fixture.so")

    def test_bad_elf_and_4k_load_segments_fail(self):
        for data in (b"bad", elf()[:60], elf(alignment=4096), elf(alignment=24576), elf(address=4096)):
            with self.subTest(length=len(data)), self.assertRaises(ValueError):
                guard.check_elf(data, "fixture.so")

    def test_every_load_segment_is_checked(self):
        data = bytearray(elf())
        struct.pack_into("<H", data, 56, 2)
        struct.pack_into("<IIQQQQQQ", data, 120, 1, 5, 0, 0, 0, 256, 256, 4096)
        with self.assertRaisesRegex(ValueError, "below 16 KB"):
            guard.check_elf(bytes(data), "second-segment.so")

    def test_aligned_apk_and_compressed_apk_libraries_work(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "play.apk"
            for compressed in (False, True):
                native_zip(path, compressed=compressed, aligned=not compressed)
                self.assertEqual(guard.check_native_libraries(path, apk=True), ["lib/arm64-v8a/libfixture.so"])

    def test_unaligned_apk_zip_fails_but_bundle_has_no_zip_alignment_requirement(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "play.apk"
            native_zip(path, aligned=False)
            with self.assertRaisesRegex(ValueError, "ZIP aligned"):
                guard.check_native_libraries(path, apk=True)
            self.assertEqual(len(guard.check_native_libraries(path, apk=False)), 1)

    def test_an_invalid_packaged_library_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "play.aab"
            native_zip(path, bundle=True, data=elf(alignment=4096))
            with self.assertRaisesRegex(ValueError, "below 16 KB"):
                guard.check_native_libraries(path, apk=False)


class PlayArtifactValidationTests(unittest.TestCase):
    def test_untrusted_bundletool_is_never_executed(self):
        with tempfile.TemporaryDirectory() as folder:
            jar = Path(folder) / "bundletool.jar"
            jar.write_bytes(b"unexpected executable")
            with patch.object(guard, "run") as command, self.assertRaisesRegex(ValueError, "SHA-256"):
                guard.validate(Path("play.apk"), Path("play.aab"), Path("aapt2"), jar)
            command.assert_not_called()

    def test_full_validation_checks_bundle_config_and_emits_artifact_facts(self):
        with tempfile.TemporaryDirectory() as folder:
            apk, aab = Path(folder) / "play.apk", Path(folder) / "play.aab"
            native_zip(apk)
            native_zip(aab, bundle=True, aligned=False)
            config = bundle_config()

            def execute(*args):
                if "manifest" in args:
                    return MANIFEST
                if "badging" in args:
                    return BADGING
                if "xmltree" in args:
                    return TREE
                if "config" in args:
                    return json.dumps(config)
                return ""

            with patch.object(guard, "sha256", return_value=guard.BUNDLETOOL_SHA256), patch.object(guard, "run", side_effect=execute) as command:
                facts = guard.validate(apk, aab, Path("aapt2"), Path("bundletool.jar"))
                self.assertEqual(facts["native_libraries"], ["lib/arm64-v8a/libfixture.so"])
                self.assertIs(facts["language_splitting_enabled"], False)
                self.assertTrue(any("validate" in call.args for call in command.call_args_list))
                config["optimizations"]["uncompressNativeLibraries"]["alignment"] = "PAGE_ALIGNMENT_4K"
                with self.assertRaisesRegex(ValueError, "PAGE_ALIGNMENT_16K"):
                    guard.validate(apk, aab, Path("aapt2"), Path("bundletool.jar"))


    def test_language_config_is_checked_even_without_native_libraries(self):
        with tempfile.TemporaryDirectory() as folder:
            apk, aab = Path(folder) / "play.apk", Path(folder) / "play.aab"
            for artifact in (apk, aab):
                with zipfile.ZipFile(artifact, "w"):
                    pass
            config = bundle_config()

            def execute(*args):
                if "manifest" in args:
                    return MANIFEST
                if "badging" in args:
                    return BADGING
                if "xmltree" in args:
                    return TREE
                if "config" in args:
                    return json.dumps(config)
                return ""

            with patch.object(guard, "sha256", return_value=guard.BUNDLETOOL_SHA256), patch.object(guard, "run", side_effect=execute):
                facts = guard.validate(apk, aab, Path("aapt2"), Path("bundletool.jar"))
                self.assertEqual(facts["native_libraries"], [])
                self.assertIs(facts["language_splitting_enabled"], False)
                # The old/default AAB config is unsafe even with no ELF files.
                del config["optimizations"]["splitsConfig"]
                with self.assertRaisesRegex(ValueError, "disable LANGUAGE splits"):
                    guard.validate(apk, aab, Path("aapt2"), Path("bundletool.jar"))


class PlayLanguageSplitTests(unittest.TestCase):
    def test_explicitly_disabled_language_splits_are_accepted(self):
        guard.check_language_splits(bundle_config())

    def test_missing_enabled_malformed_or_conflicting_language_config_is_rejected(self):
        cases = [None, [], {}, {"optimizations": None}, {"optimizations": {}},
                 {"optimizations": {"splitsConfig": None}}]
        for dimensions in (
            None, {}, [], [None], [{"value": "ABI", "negate": True}],
            [{"value": "LANGUAGE"}],
            [{"value": "LANGUAGE", "negate": False}],
            [{"value": "LANGUAGE", "negate": "true"}],
            [{"value": "LANGUAGE", "negate": 1}],
            [{"value": "LANGUAGE", "negate": True}, {"value": "LANGUAGE"}],
            [{"value": "LANGUAGE", "negate": True}, {"value": "LANGUAGE", "negate": True}],
        ):
            cases.append({"optimizations": {"splitsConfig": {"splitDimension": dimensions}}})
        for config in cases:
            with self.subTest(config=config), self.assertRaisesRegex(ValueError, "disable LANGUAGE splits"):
                guard.check_language_splits(config)


if __name__ == "__main__":
    unittest.main()
