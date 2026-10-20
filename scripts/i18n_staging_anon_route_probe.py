#!/usr/bin/env python3
"""Explicit-opt-in P0 anonymous staging probe for legacy static course routes.

By default this is OFFLINE and makes ZERO HTTP requests. When explicitly
enabled it uses read-only anonymous GET requests, never reads the response
body and never logs authentication, translated texts or quiz answers.
This is not an entitlement test for real Free/Pro users.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

TRACKS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")
LAST_LESSON_BY_TRACK = {
    "hsk1": 63, "hsk2": 72, "hsk3": 109, "hsk4": 181,
    "nhsk1": 103, "nhsk2": 73, "nhsk3": 145,
}
STAGING_MARKER = re.compile(r"(?:^|[.-])(?:qa|staging)(?:[.-]|$)", re.I)
FORBIDDEN_HOST = re.compile(r"(?:^|[.-])(?:prod|production|www)(?:[.-]|$)", re.I)


class RejectRedirects(HTTPRedirectHandler):
    """Never follow a redirect from a staging host to another service."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def cases() -> list[dict]:
    items = []
    for track in TRACKS:
        items.append({
            "kind": "navigation_map", "track": track,
            "path": f"/course_v3_data/{track}.json",
        })
        items.append({
            "kind": "legacy_lesson", "track": track,
            "path": f"/course_v3_data/{track}/lesson_01.json",
        })
        items.append({
            "kind": "late_legacy_lesson", "track": track,
            "path": f"/course_v3_data/{track}/lesson_{LAST_LESSON_BY_TRACK[track]}.json",
        })
    items.append({
        "kind": "private_exam_file", "track": "n/a",
        "path": "/course_v3_data/exams/p0-privacy-probe.json",
    })
    for platform in ("android", "desktop"):
        items.append({
            "kind": "native_lesson_api", "track": platform,
            "path": f"/api/v3/{platform}/course/lesson/1",
        })
    return items


def staging_origin(base_url: str, expected_host: str) -> str:
    """Require exact HTTPS host match plus clear staging/QA DNS marker."""
    parsed = urlsplit(base_url)
    if (parsed.scheme != "https" or not parsed.hostname or
            parsed.username or parsed.password or parsed.query or
            parsed.fragment or parsed.path not in ("", "/") or
            parsed.port not in (None, 443)):
        raise ValueError("Use the bare HTTPS staging origin, without path, secrets or query")
    hostname = parsed.hostname.lower()
    if not expected_host or hostname != expected_host.lower().strip():
        raise ValueError("Staging host must be confirmed by exact hostname")
    if FORBIDDEN_HOST.search(hostname) or not STAGING_MARKER.search(hostname):
        raise ValueError("Host must be QA/staging, not a production hostname")
    return "https://" + hostname + (":443" if parsed.port == 443 else "")


def _open(req: Request, timeout: float):
    # Build an opener that refuses redirects, including any HTTPS-to-HTTP.
    return build_opener(RejectRedirects()).open(req, timeout=timeout)


def probe(*, execute: bool = False, base_url: str = "",
          confirmed_host: str = "", timeout: float = 5.0,
          open_request=None) -> dict:
    pending = cases()
    if not execute:
        return {
            "schema_version": 1,
            "status": "NOT_EXECUTED_STAGING_TARGET_REQUIRED",
            "performed_requests": 0,
            "planned_requests": len(pending),
            "cases": [{**item, "http_status": None} for item in pending],
            "findings": [],
            "limits": "Dry run only; no server contacted, no HTTP availability confirmed.",
        }
    if not 1 <= timeout <= 15:
        raise ValueError("Timeout must be between 1 and 15 seconds")
    origin = staging_origin(base_url, confirmed_host)
    opening = open_request or _open
    results = []
    findings = []
    for item in pending:
        request = Request(
            origin + item["path"],
            method="GET",
            headers={
                "Accept": "application/json",
                "Cache-Control": "no-store",
                "Range": "bytes=0-0",
            },
        )
        status, error_code = None, None
        try:
            response = opening(request, timeout)
            try:
                status = response.status if hasattr(response, "status") else response.getcode()
            finally:
                response.close()
        except HTTPError as exc:
            status = exc.code
            exc.close()
        except (URLError, OSError):
            error_code = "transport_error"
        # Do not call response.read(), store headers, redirects or any body bytes.
        results.append({**item, "http_status": status, "error": error_code})
        if item["kind"] in ("legacy_lesson", "late_legacy_lesson") and status in (200, 206):
            findings.append({
                "kind": item["kind"], "track": item["track"],
                "issue": "anonymous_legacy_lesson_content_accessible",
                "review": "entitlement_and_static_content_privacy",
            })
        if item["kind"] == "private_exam_file" and status != 404:
            findings.append({
                "kind": "private_exam_file",
                "issue": "staging_exam_404_not_verified",
                "review": "stop_and_investigate_exam_route",
            })
        if item["kind"] == "native_lesson_api" and status not in (401, 403):
            findings.append({
                "kind": "native_lesson_api", "track": item["track"],
                "issue": "native_anonymous_auth_denial_not_confirmed",
                "review": "stop_and_check_bearer_auth_boundary",
            })
    return {
        "schema_version": 1,
        "status": "STAGING_ANONYMOUS_PROBED_MANUAL_REVIEW",
        "performed_requests": len(results),
        "planned_requests": len(pending),
        "exam_404_verified": any(
            item["kind"] == "private_exam_file" and item["http_status"] == 404
            for item in results
        ),
        "anonymous_lesson_success_count": sum(
            item["kind"] == "legacy_lesson" and item["http_status"] in (200, 206)
            for item in results
        ),
        "anonymous_late_lesson_success_count": sum(
            item["kind"] == "late_legacy_lesson" and item["http_status"] in (200, 206)
            for item in results
        ),
        "native_api_denied_without_bearer_count": sum(
            item["kind"] == "native_lesson_api" and item["http_status"] in (401, 403)
            for item in results
        ),
        "cases": results,
        "findings": findings,
        "limits": (
            "GET status only; body NEVER read. 200/206 is a source exposure signal, "
            "not verified paid bypass. Cannot establish Free/Trial/Pro entitlement, "
            "upstream CDN behavior for other domains, or shipped client compatibility."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true",
                        help="Allow anonymous status-only GET requests to verified staging")
    parser.add_argument("--base-url", default="", help="Explicit HTTPS staging origin")
    parser.add_argument("--confirmed-host", default="",
                        help="Exact QA/staging hostname, not a production hostname")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    try:
        result = probe(execute=args.execute, base_url=args.base_url,
                       confirmed_host=args.confirmed_host, timeout=args.timeout)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print("Staging anonymous route audit blocked:", exc, file=sys.stderr)
        return 1
    print("Staging anonymous course probe:", result["status"],
          "HTTP requests:", result["performed_requests"])
    return int(result.get("exam_404_verified") is False
               and result["performed_requests"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
