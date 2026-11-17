"""Bounded in-process cache of PUBLIC course-map templates only.

Never cache a personalized map, user/session data, entitlement decision, or
mutable lesson state. The caller receives a deep copy before annotating it.
File metadata keys make a replaced template visible on the next request.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

COURSE_MAP_DIRECTORY = Path("app/static/course_v3_data")


@lru_cache(maxsize=16)
def _parsed_template(path: str, mtime_ns: int, size: int) -> dict:
    # Key includes file metadata to revalidate when a template is replaced.
    # An exception is never cached: a broken/missing deploy can recover.
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("course map template must be a JSON object")
    return data


def _clone_json_tree(value):
    """Copy JSON containers without deepcopy's cycle/memo machinery.

    Templates come exclusively from json.load: a tree of dict/list and
    immutable JSON scalars, with no cyclic objects or custom Python classes.
    This always creates independent nested containers for each learner.
    """
    if isinstance(value, dict):
        return {key: _clone_json_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_json_tree(item) for item in value]
    return value


def load_course_map_template(level: str, *, directory: Path = COURSE_MAP_DIRECTORY) -> dict:
    """Return an independent mutable map; no cross-user object sharing."""
    # The production caller already normalizes levels, but keep the template
    # reader independently safe from path traversal.
    if level not in {"hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3"}:
        level = "hsk1"
    path = directory / (level + ".json")
    if not path.exists():
        path = directory / "hsk1.json"
    stat = path.stat()
    return _clone_json_tree(_parsed_template(str(path), stat.st_mtime_ns, stat.st_size))
