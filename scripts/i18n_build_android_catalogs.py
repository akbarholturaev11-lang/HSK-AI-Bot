#!/usr/bin/env python3
"""Copy canonical Android UI XML into bundled resources without changing bytes.

Author localization/android/{main,direct,play}/values*/ only. Native XML keeps
Android escaping, quantities, resource references and source-set overlays exact.
Common/course resources remain owned by their existing JSON generators.
No application imports, database, network or runtime translation are involved.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import sys
import xml.etree.ElementTree as ET

if __package__:
    from .i18n_android_resource_audit import compare_resources, parse_resources
else:
    from i18n_android_resource_audit import compare_resources, parse_resources

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("localization/android")
QUALIFIERS = ("values", "values-ru", "values-tg")
SOURCE_SETS = ("main", "direct", "play")


def read_sources(root: Path = ROOT) -> dict[str, bytes]:
    base = root / SOURCE
    manifest_path = base / "manifest.json"
    if base.is_symlink() or manifest_path.is_symlink():
        raise ValueError("Canonical Android resources must not be symlinks")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (set(manifest) != {"schema_version", "files"}
            or manifest["schema_version"] != 1
            or not isinstance(manifest["files"], list)
            or not manifest["files"]):
        raise ValueError("Invalid canonical Android manifest")
    paths = manifest["files"]
    if any(not isinstance(p, str) for p in paths) or len(set(paths)) != len(paths):
        raise ValueError("Duplicate or invalid Android source path")
    outputs, parsed = {}, {}
    resource_names = {}
    for relative in sorted(paths):
        path = PurePosixPath(relative)
        if (len(path.parts) != 3 or path.parts[0] not in SOURCE_SETS
                or path.parts[1] not in QUALIFIERS
                or path.name.startswith("hsk_") or path.suffix != ".xml"
                or not path.stem.replace("_", "").isalnum()
                or "\\" in relative or str(path) != relative):
            raise ValueError("Unsafe/unowned Android source path")
        source = base / relative
        if any(p.is_symlink() for p in (source, source.parent, source.parent.parent)):
            raise ValueError("Android source symlink")
        raw = source.read_bytes()
        text = raw.decode("utf-8")
        if "<!DOCTYPE" in text or "<!ENTITY" in text:
            raise ValueError("Android resource declarations are not supported")
        xml = ET.fromstring(text)
        if xml.tag != "resources" or not len(xml):
            raise ValueError("Empty/non-resource Android XML")
        names = resource_names.setdefault(path.parts[:2], set())
        for entry in xml:
            name = entry.attrib.get("name", "")
            identity = (entry.tag, name)
            if (entry.tag not in {"string", "plurals", "string-array"}
                    or not name or identity in names):
                raise ValueError("Unowned/duplicate Android resource")
            names.add(identity)
        parsed[relative] = parse_resources(text)
        outputs[f"android/app/src/{path.parts[0]}/res/{path.parts[1]}/{path.name}"] = raw
    actual = {str(p.relative_to(base)) for p in base.rglob("*.xml")}
    if actual != set(paths):
        raise ValueError("Unregistered canonical Android resource files")
    for relative, values in parsed.items():
        path = PurePosixPath(relative)
        if path.parts[1] != "values":
            continue
        for qualifier in QUALIFIERS[1:]:
            locale_path = f"{path.parts[0]}/{qualifier}/{path.name}"
            if locale_path not in parsed or compare_resources(values, parsed[locale_path]):
                raise ValueError("Android locale resource/placeholder parity: " + locale_path)
    for relative in parsed:
        path = PurePosixPath(relative)
        if f"{path.parts[0]}/values/{path.name}" not in parsed:
            raise ValueError("Android locale XML lacks a default resource file")
    return outputs


def generate(root: Path = ROOT, *, check: bool) -> list[str]:
    outputs = read_sources(root)  # Validate the entire batch before any writes.
    changed = []
    for relative, raw in outputs.items():
        target = root / relative
        if target.is_symlink() or any((root / p).is_symlink() for p in Path(relative).parents):
            raise ValueError("Generated Android target is a symlink")
        if not target.is_file() or target.read_bytes() != raw:
            changed.append(relative)
    if not check:
        for relative in changed:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(outputs[relative])
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        changed = generate(args.root, check=args.check)
    except (OSError, ValueError, UnicodeError, ET.ParseError) as exc:
        print("Android catalog generation failed:", exc, file=sys.stderr)
        return 1
    if args.check and changed:
        print("Stale Android catalogs:", ", ".join(changed), file=sys.stderr)
        return 1
    print("Canonical Android UI:", len(read_sources(args.root)), "files;",
          len(changed), "stale" if args.check else "written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
