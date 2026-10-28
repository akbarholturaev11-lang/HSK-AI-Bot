#!/usr/bin/env python3
"""Mirror Google Play's published production RELEASES without opening an edit.

Input: GET applications/com.pomp.hskai/tracks/production/releases.
Only RELEASE_LIFECYCLE_STATE_PUBLISHED counts. This read-only API avoids
invalidating someone's concurrent Play Console edit, unlike edits.insert.
Existing R2 mirror remains append-only; polling never counts duplicates.
No package upload, Play release mutation, or Direct distribution change.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

MAX_CODE = 2_000_000_000
PUBLISHED = "RELEASE_LIFECYCLE_STATE_PUBLISHED"


def confirmed_codes(response: dict) -> list[int]:
    if not isinstance(response, dict) or set(response) != {"releases"}:
        raise ValueError("invalid Google Play releases response")
    releases = response["releases"]
    if not isinstance(releases, list) or len(releases) > 20:
        raise ValueError("invalid release list")
    result = set()
    for release in releases:
        if not isinstance(release, dict) or release.get("track") != "production":
            raise ValueError("unexpected Play release track")
        if release.get("releaseLifecycleState") != PUBLISHED:
            continue
        artifacts = release.get("activeArtifacts")
        if not isinstance(artifacts, list) or not artifacts:
            # Published release with missing codes cannot be safely ranked.
            raise ValueError("missing published artifacts")
        codes = []
        for item in artifacts:
            if not isinstance(item, dict):
                raise ValueError("invalid published artifact")
            code = item.get("versionCode")
            if type(code) is not int or not 1 <= code <= MAX_CODE:
                raise ValueError("invalid Play artifact code")
            codes.append(code)
        # One Play release can include several APK splits. Treat it as ONE
        # publication, with the lowest code as the safe allowed boundary.
        result.add(min(codes))
    return sorted(result)


def merge(response: dict, existing: dict) -> dict:
    current = confirmed_codes(response)
    if not current:
        raise ValueError("no verified published Play production releases")
    previous = existing.get("published_version_codes", [])
    if existing:
        if (set(existing) != {"schema_version", "package_name", "track",
                              "published_version_codes", "synced_at"}
                or existing.get("schema_version") != 1
                or existing.get("package_name") != "com.pomp.hskai"
                or existing.get("track") != "production"):
            raise ValueError("invalid previous Play ledger")
        if (not isinstance(previous, list) or previous != sorted(set(previous))
                or any(type(code) is not int or not 1 <= code <= MAX_CODE for code in previous)):
            raise ValueError("corrupt previous Play ledger")

    last_code = previous[-1] if previous else 0
    # The API returns up to 20 non-obsolete releases, not infinite history.
    # Preserve already verified prior entries, append only newer publications.
    appended = [code for code in current if code > last_code]
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
    parser.add_argument("--releases", type=Path, required=True)
    parser.add_argument("--existing", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = merge(json.loads(args.releases.read_text()),
                   json.loads(args.existing.read_text()))
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
