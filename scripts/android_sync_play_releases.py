#!/usr/bin/env python3
"""Keep only Google Play production releases that its API says are published.

Input is GET edits.tracks.get on the production track. Drafts are not counted.
Existing R2 mirror is append-only. Polls do not create another "release".
This never uploads a package, commits a Play edit, or touches Direct.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

MAX_CODE = 2_000_000_000


def confirmed_codes(track: dict) -> list[int]:
    if not isinstance(track, dict) or track.get("track") != "production":
        raise ValueError("not production track")
    releases = track.get("releases", [])
    if not isinstance(releases, list):
        raise ValueError("invalid releases")
    result = set()
    for release in releases:
        if not isinstance(release, dict):
            raise ValueError("invalid release")
        if release.get("status") not in ("completed", "inProgress"):
            continue
        codes = release.get("versionCodes")
        if not isinstance(codes, list) or not codes:
            raise ValueError("missing version codes")
        parsed = []
        for raw in codes:
            if not isinstance(raw, str) or not raw.isascii() or not raw.isdecimal():
                raise ValueError("invalid code")
            code = int(raw)
            if not 1 <= code <= MAX_CODE:
                raise ValueError("invalid code range")
            parsed.append(code)
        # Multiple APK splits in ONE release are one published release.
        result.add(max(parsed))
    return sorted(result)


def merge(track: dict, existing: dict) -> dict:
    current = confirmed_codes(track)
    if not current:
        raise ValueError("no confirmed Play production releases")
    previous = existing.get("published_version_codes", [])
    if existing:
        if (set(existing) != {"schema_version", "package_name", "track",
                              "published_version_codes", "synced_at"}
                or existing.get("schema_version") != 1
                or existing.get("package_name") != "com.pomp.hskai"
                or existing.get("track") != "production"):
            raise ValueError("invalid previous Play ledger")
        if (not isinstance(previous, list)
                or previous != sorted(set(previous))
                or any(type(c) is not int or not 1 <= c <= MAX_CODE for c in previous)):
            raise ValueError("corrupt previous Play ledger")

    latest = previous[-1] if previous else 0
    # Historical releases may remain active alongside newer releases; keep
    # their existing order, but don't retroactively add missing older codes
    # that were not previously CONFIRMED by the mirror.
    appended = [code for code in current if code > latest]
    published = (previous + appended)[-128:]
    if not published:
        raise ValueError("no publishable Play release")
    return {
        "schema_version": 1,
        "package_name": "com.pomp.hskai",
        "track": "production",
        "published_version_codes": published,
        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", type=Path, required=True)
    parser.add_argument("--existing", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = merge(json.loads(args.track.read_text()),
                   json.loads(args.existing.read_text()))
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
