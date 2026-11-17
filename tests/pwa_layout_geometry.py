"""Reusable Playwright geometry assertions for learner PWA loading->ready.

Use two sets of selectors describing the SAME visual slots (e.g. skeleton
podium vs ready podium) at a fixed viewport. An opacity-only transition should
not move these anchors. Run with throttled network and capture CLS separately.
"""
from __future__ import annotations

from collections.abc import Mapping


def capture_geometry(page, anchors: Mapping[str, str]) -> dict[str, dict[str, float]]:
    """Read visible bounding boxes by semantic slot; fail on missing anchors."""
    positions: dict[str, dict[str, float]] = {}
    for label, selector in anchors.items():
        locator = page.locator(selector).first
        rect = locator.bounding_box()
        if rect is None:
            raise AssertionError(f"Geometry anchor {label!r} not visible: {selector}")
        positions[label] = {
            "x": float(rect["x"]),
            "y": float(rect["y"]),
            "width": float(rect["width"]),
            "height": float(rect["height"]),
        }
    return positions


def assert_reserved_layout(
    loading: Mapping[str, Mapping[str, float]],
    ready: Mapping[str, Mapping[str, float]],
    *,
    max_anchor_shift_px: float = 8.0,
    max_dimension_delta_px: float = 16.0,
) -> None:
    """Assert skeleton and final content occupy matching viewport geometry.

    The allowed dimension change applies to fixed visual slots, not variable
    result-list totals; capture matching first-viewport rows individually.
    Does not replace measured PerformanceObserver CLS or screenshots.
    """
    if not loading or not ready:
        raise AssertionError("Need loading and ready layout anchors")
    if set(loading) != set(ready):
        raise AssertionError(
            f"Unmatched visual slots: loading-only={sorted(set(loading)-set(ready))}, "
            f"ready-only={sorted(set(ready)-set(loading))}"
        )
    failures = []
    for name, old in loading.items():
        new = ready[name]
        for key in ("x", "y"):
            delta = abs(float(old[key]) - float(new[key]))
            if delta > max_anchor_shift_px:
                failures.append(
                    f"{name}.{key}: {delta:.1f}px shift > {max_anchor_shift_px}px"
                )
        for key in ("width", "height"):
            delta = abs(float(old[key]) - float(new[key]))
            if delta > max_dimension_delta_px:
                failures.append(
                    f"{name}.{key}: {delta:.1f}px size change > {max_dimension_delta_px}px"
                )
    if failures:
        raise AssertionError("Loading geometry differs from ready layout:\n" + "\n".join(failures))
