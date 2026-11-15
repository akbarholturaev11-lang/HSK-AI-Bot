"""Verified source mapping for diagnostic debug evidence (design D12).

A reported location names a first-party asset by its catalog ID. Its optional
`asset_version` is the content token the learner's page loaded the script
with. The location is `verified` only when that token equals a content hash of
the file this deployment serves, so the learner ran exactly the deployed
bytes. A source link additionally needs the immutable commit the deployment
was built from. A `?v=` cache token is never treated as a commit.
"""
import hashlib
import os
import re

from app.services.monitoring import catalog

COMMIT = re.compile(r"[0-9a-f]{40}")
ASSET_VERSION = re.compile(r"[0-9a-f]{12}")
_tokens: dict[str, tuple[tuple[int, int], frozenset[str]]] = {}


def deployed_commit(settings_obj):
    """The full commit SHA this deployment was built from, or None."""
    value = str(getattr(settings_obj, "MONITORING_SOURCE_COMMIT", "") or "").strip().lower()
    return value if COMMIT.fullmatch(value) else None


def asset_tokens(asset_id):
    """Both content tokens in use for a served asset: the Git blob ID prefix
    (`<date>-<blob>` tokens) and the SHA-256 prefix (derived `?v=` tokens)."""
    path = catalog.DEBUG_ASSETS.get(asset_id)
    if path is None:
        return frozenset()
    try:
        stat = os.stat(path)
        key = (stat.st_mtime_ns, stat.st_size)
        cached = _tokens.get(asset_id)
        if cached is None or cached[0] != key:
            with open(path, "rb") as handle:
                raw = handle.read()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw,
                                usedforsecurity=False).hexdigest()
            cached = key, frozenset({blob[:12], hashlib.sha256(raw).hexdigest()[:12]})
            _tokens[asset_id] = cached
        return cached[1]
    except OSError:
        return frozenset()


def is_deployed_version(asset_id, asset_version):
    return bool(asset_version) and asset_version in asset_tokens(asset_id)


def source_url(commit, asset_id, line):
    """A GitHub link to one exact line, or None when any part is unverified."""
    path = catalog.DEBUG_ASSETS.get(asset_id)
    if (path is None or not isinstance(commit, str) or not COMMIT.fullmatch(commit)
            or type(line) is not int or not 1 <= line <= catalog.MAX_SOURCE_LINE):
        return None
    return f"https://github.com/{catalog.SOURCE_REPOSITORY}/blob/{commit}/{path}#L{line}"
