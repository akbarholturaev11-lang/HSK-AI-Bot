"""Repeatable local/CI microbenchmark for public map template loading only.

No authenticated API requests or production DB calls. These numbers do not
measure map HTTP p50/p95, PostgreSQL row locks, or Safari first paint.
Usage: python scripts/bench_course_map_templates.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from time import perf_counter_ns

from app.services.course_map_template_cache import load_course_map_template

BASE = Path("app/static/course_v3_data")
LEVELS = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")


def median_microseconds(task, iterations=60):
    samples = []
    for _ in range(iterations):
        start = perf_counter_ns()
        task()
        samples.append((perf_counter_ns() - start) / 1000)
    return statistics.median(samples)


def uncached():
    for level in LEVELS:
        json.loads((BASE / f"{level}.json").read_text(encoding="utf-8"))


def cached():
    for level in LEVELS:
        load_course_map_template(level)


def main():
    cached()  # warm once; process-local cache should be warm in normal use
    before = median_microseconds(uncached)
    after = median_microseconds(cached)
    print(f"seven public map templates, median across 60 iterations:")
    print(f"unoptimized file read + JSON parse: {before:.1f} us")
    print(f"cached JSON-tree clone:           {after:.1f} us")
    if after > 0:
        print(f"microbenchmark ratio: {before / after:.2f}x (CI runner only)")
    print("CAUTION: not an end-to-end API or mobile UX timing")


if __name__ == "__main__":
    main()
